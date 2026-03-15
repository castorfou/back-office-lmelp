"""Service de vérification orthographique via Babelio.com

Ce service utilise l'API AJAX de Babelio pour vérifier et corriger l'orthographe
des auteurs, livres et éditeurs extraits des avis critiques.

Architecture :
- Endpoint : POST https://www.babelio.com/aj_recherche.php
- Format : JSON {"term": "search_term", "isMobile": false}
- Headers : Content-Type: application/json, X-Requested-With: XMLHttpRequest
- Cookies : disclaimer=1, p=FR (nécessaires pour éviter les blocages)
- Rate limiting : 5.0 sec entre requêtes (éviter le rate limiting Babelio - Issue #124)

Découverte technique basée sur l'analyse DevTools :
- Babelio tolère les fautes d'orthographe (Houllebeck -> Houellebecq)
- Retourne des résultats mixtes : auteurs, livres, séries
- Format de réponse : Array JSON avec type "auteurs"/"livres"/"series"
- IDs uniques Babelio pour construire les URLs canoniques

Usage :
    service = BabelioService()
    result = await service.verify_author("Michel Houellebecq")
    # result['status'] = 'verified'|'corrected'|'not_found'|'error'
    await service.close()  # Fermer la session HTTP
"""

import asyncio
import json
import logging
import os
from difflib import SequenceMatcher
from typing import Any

import aiohttp
from bs4 import BeautifulSoup


logger = logging.getLogger(__name__)


class BabelioService:
    """Service de vérification orthographique via l'API AJAX de Babelio.

    Ce service respecte les bonnes pratiques :
    - Rate limiting à 5.0 sec entre requêtes (éviter blocage - Issue #124)
    - Headers et cookies appropriés pour éviter les blocages
    - Gestion d'erreur robuste (timeout, réseau, parsing JSON)
    - Session HTTP réutilisable et fermeture propre
    - Calcul de scores de confiance pour les suggestions

    Attributes:
        base_url: URL de base de Babelio
        search_endpoint: Endpoint AJAX pour la recherche
        session: Session aiohttp réutilisable
        rate_limiter: Semaphore pour limiter à 1 req simultanée
        min_interval: Délai minimum entre requêtes (5.0 sec par défaut)
    """

    def __init__(self):
        """Initialise le service Babelio avec configuration appropriée."""
        self.base_url = "https://www.babelio.com"
        self.search_endpoint = "/aj_recherche.php"
        self.session: aiohttp.ClientSession | None = None
        self.rate_limiter = asyncio.Semaphore(1)  # 1 requête simultanée max
        self.last_request_time = 0  # Timestamp de la dernière requête
        self.min_interval = 5.0  # Délai minimum de 5.0 secondes entre requêtes (Issue #124: éviter rate limiting)
        self._cache = {}  # Cache simple terme -> résultats (limité en taille)
        # Optional disk-backed cache service injected at app startup
        self.cache_service: Any | None = None
        # Contrôle des logs temporaires pour le cache disque (utile en dev)
        # Si la variable d'environnement BABELIO_CACHE_LOG est '1' ou 'true',
        # on exposera des logs plus verbeux (info) pour hit/miss et écriture.
        self._cache_log_enabled = os.getenv("BABELIO_CACHE_LOG", "0").lower() in (
            "1",
            "true",
            "yes",
        )
        # Logs de debug pour analyser les requêtes et résultats Babelio
        # Activé avec BABELIO_DEBUG_LOG=1 (utile pour diagnostiquer problèmes de matching)
        self._debug_log_enabled = os.getenv("BABELIO_DEBUG_LOG", "0").lower() in (
            "1",
            "true",
            "yes",
        )
        # If verbose cache logging is enabled, make sure our module logger
        # will emit INFO messages to stdout (useful when running under uvicorn)
        if self._cache_log_enabled or self._debug_log_enabled:
            try:
                logger.setLevel(logging.INFO)
                # add a stdout handler only if no handlers are configured for this logger
                if not logger.handlers:
                    handler = logging.StreamHandler()
                    handler.setLevel(logging.INFO)
                    handler.setFormatter(
                        logging.Formatter(
                            "%(asctime)s %(levelname)s %(name)s: %(message)s"
                        )
                    )
                    logger.addHandler(handler)
            except Exception:
                # Don't fail startup if logging setup has issues
                pass

    async def _get_session(self) -> aiohttp.ClientSession:
        """Récupère ou crée la session HTTP avec configuration appropriée."""
        if self.session is None or self.session.closed:
            # Timeout configuration respectueuse
            timeout = aiohttp.ClientTimeout(total=10, connect=5)

            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers=self._get_default_headers(),
                cookies=self._get_default_cookies(),
            )
        return self.session

    def _get_default_headers(self) -> dict[str, str]:
        """Retourne les headers nécessaires pour Babelio.

        Basé sur l'analyse des vraies requêtes DevTools.
        """
        return {
            "Content-Type": "application/json",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:142.0) Gecko/20100101 Firefox/142.0",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://www.babelio.com/recherche.php",
            "Origin": "https://www.babelio.com",
            "Accept-Language": "fr,en-US;q=0.7,en;q=0.3",
            "DNT": "1",
            "Sec-GPC": "1",
        }

    def _get_default_cookies(self) -> dict[str, str]:
        """Retourne les cookies nécessaires pour Babelio.

        Ces cookies évitent les blocages et disclaimers.
        """
        return {
            "p": "FR",  # Pays = France
            "disclaimer": "1",  # Disclaimer accepté
            "g_state": '{"i_l":0}',  # État Google (JSON string)
            "bbacml": "0",  # Cookie marketing
        }

    async def search(self, term: str) -> list[dict[str, Any]]:
        """Effectue une recherche sur Babelio.

        Args:
            term: Terme à rechercher (auteur, livre, etc.)

        Returns:
            list[dict]: Résultats JSON de Babelio, format:
                [
                    {
                        "id": "2180",
                        "prenoms": "Michel",
                        "nom": "Houellebecq",
                        "type": "auteurs",
                        "url": "/auteur/Michel-Houellebecq/2180",
                        "ca_oeuvres": "38",
                        "ca_membres": "30453"
                    },
                    {
                        "id_oeuvre": "1770",
                        "titre": "Les particules élémentaires",
                        "nom": "Houellebecq",
                        "prenoms": "Michel",
                        "type": "livres",
                        "url": "/livres/Houellebecq-Les-particules-elementaires/1770"
                    }
                ]

        Raises:
            Aucune exception - retourne [] en cas d'erreur
        """
        if not term or not term.strip():
            return []

        # Vérifier le cache disque/in-memory d'abord
        cache_key = term.strip().lower()

        # Support pour un service de cache disque injecté (BabelioCacheService)
        cache_service = getattr(self, "cache_service", None)
        if cache_service is not None:
            try:
                # disk IO can block; run in threadpool to avoid blocking event loop
                wrapper = await asyncio.to_thread(cache_service.get_cached, term)
                # choose log function based on env control
                log_fn = (
                    logger.info
                    if getattr(self, "_cache_log_enabled", False)
                    else logger.debug
                )

                if wrapper is not None:
                    # original-term hit
                    items = None
                    if isinstance(wrapper, dict):
                        items = len(wrapper.get("data") or [])
                    log_fn(
                        f"[BabelioCache] HIT (orig) key='{term}' items={items} ts={getattr(wrapper, 'get', lambda *_: None)('ts')}"
                    )
                    if self._debug_log_enabled:
                        logger.info(
                            f"🔍 [DEBUG] search: CACHE HIT (orig) - returning {items} cached result(s)"
                        )
                    # Ensure we always return a list (function annotated -> list[dict])
                    if isinstance(wrapper, dict):
                        return list(wrapper.get("data") or [])
                    return list(wrapper or [])

                # try lowercased key too for compatibility
                wrapper = await asyncio.to_thread(cache_service.get_cached, cache_key)
                if wrapper is not None:
                    items = None
                    if isinstance(wrapper, dict):
                        items = len(wrapper.get("data") or [])
                    log_fn(
                        f"[BabelioCache] HIT (norm) key='{cache_key}' items={items} ts={getattr(wrapper, 'get', lambda *_: None)('ts')}"
                    )
                    if self._debug_log_enabled:
                        logger.info(
                            f"🔍 [DEBUG] search: CACHE HIT (norm) - returning {items} cached result(s)"
                        )
                    # Ensure we always return a list (function annotated -> list[dict])
                    if isinstance(wrapper, dict):
                        return list(wrapper.get("data") or [])
                    return list(wrapper or [])

                # both misses
                log_fn(f"[BabelioCache] MISS keys=(orig='{term}', norm='{cache_key}')")
            except Exception:
                # on any cache error, treat as cache miss and continue
                logger.exception(
                    "Erreur lors de l'accès au cache disque; fallback réseau"
                )

        # Backwards-compatible in-memory cache
        if cache_key in self._cache:
            logger.debug(f"Cache mémoire hit pour: {term}")
            return self._cache[cache_key]  # type: ignore[no-any-return]

        # Respect du rate limiting avec délai obligatoire
        async with self.rate_limiter:
            # Calculer le temps d'attente nécessaire
            import time

            current_time = time.time()
            time_since_last = current_time - self.last_request_time

            if time_since_last < self.min_interval:
                wait_time = self.min_interval - time_since_last
                logger.debug(f"Rate limiting: attente de {wait_time:.1f}s")
                await asyncio.sleep(wait_time)

            self.last_request_time = time.time()
            session = await self._get_session()
            url = f"{self.base_url}{self.search_endpoint}"

            # Format JSON exact découvert via DevTools
            payload = {"term": term.strip(), "isMobile": False}

            try:
                logger.debug(f"Recherche Babelio pour: {term}")
                if self._debug_log_enabled:
                    logger.info(f"🔍 [DEBUG] search: POST {url} payload={payload}")

                async with session.post(url, json=payload) as response:
                    if self._debug_log_enabled:
                        logger.info(
                            f"🔍 [DEBUG] search: Response status={response.status}"
                        )

                    if response.status == 200:
                        try:
                            # Babelio retourne du JSON valide mais avec le mauvais Content-Type
                            # On récupère le texte brut puis on parse le JSON manuellement
                            # Utiliser Windows-1252 car Babelio déclare ISO-8859-1 mais utilise
                            # des caractères Windows-1252 comme le tiret cadratin (0x96) (Issue #167)
                            text_content = await response.text(encoding="cp1252")
                            results: list[dict[str, Any]] = json.loads(text_content)

                            if self._debug_log_enabled:
                                logger.info(
                                    f"🔍 [DEBUG] search: Parsed {len(results)} result(s)"
                                )
                            logger.debug(f"Babelio retourne {len(results)} résultats")

                            # Mettre en cache mémoire (limiter la taille du cache)
                            if len(self._cache) < 100:  # Limite à 100 entrées
                                self._cache[cache_key] = results

                            # Écrire dans le cache disque si disponible
                            cache_service = getattr(self, "cache_service", None)
                            if cache_service is not None:
                                try:
                                    # store both original term and normalized key for robustness
                                    # write cache in threadpool to avoid blocking event loop
                                    await asyncio.to_thread(
                                        cache_service.set_cached, term, results
                                    )
                                    await asyncio.to_thread(
                                        cache_service.set_cached, cache_key, results
                                    )
                                    # log write with same verbosity control
                                    log_fn = (
                                        logger.info
                                        if getattr(self, "_cache_log_enabled", False)
                                        else logger.debug
                                    )
                                    log_fn(
                                        f"[BabelioCache] WROTE keys=(orig='{term}', norm='{cache_key}') items={len(results)}"
                                    )
                                except Exception:
                                    logger.exception(
                                        "Impossible d'écrire dans le cache disque (ignored)"
                                    )

                            return results
                        except json.JSONDecodeError:
                            # Si ce n'est vraiment pas du JSON, log pour debugging
                            content_type = response.headers.get(
                                "content-type", "unknown"
                            )
                            logger.error(f"Babelio réponse non-JSON pour {term}")
                            logger.error(f"Content-Type: {content_type}")
                            logger.error(f"Début: {text_content[:200]}...")
                            return []
                    elif response.status == 503:
                        logger.warning(
                            f"Babelio HTTP 503 (Service Unavailable) pour: {term} - rate limited"
                        )
                        return []
                    else:
                        logger.warning(f"Babelio HTTP {response.status} pour: {term}")
                        return []

            except TimeoutError as e:
                logger.error(f"Timeout Babelio pour: {term}")
                # Propager l'erreur pour que l'appelant sache qu'il y a eu un problème réseau
                raise TimeoutError(
                    f"Timeout lors de la recherche Babelio: {term}"
                ) from e
            except aiohttp.ClientError as e:
                logger.error(f"Erreur réseau Babelio pour {term}: {e}")
                # Propager l'erreur pour que l'appelant sache qu'il y a eu un problème réseau
                raise aiohttp.ClientError(
                    f"Erreur réseau lors de la recherche Babelio: {term}"
                ) from e
            except Exception as e:
                logger.error(f"Erreur inattendue Babelio pour {term}: {e}")
                # Pour les autres erreurs, on retourne [] pour compatibilité
                return []

    async def verify_author(self, author_name: str) -> dict[str, Any]:
        """Vérifie et corrige l'orthographe d'un nom d'auteur.

        Args:
            author_name: Nom de l'auteur à vérifier

        Returns:
            Dict avec format standardisé:
                {
                    'status': 'verified'|'corrected'|'not_found'|'error',
                    'original': str,
                    'babelio_suggestion': str|None,
                    'confidence_score': float (0.0-1.0),
                    'babelio_data': dict|None,  # Données brutes Babelio
                    'babelio_url': str|None,   # URL canonique
                    'error_message': str|None  # Si status='error'
                }
        """
        if not author_name or not author_name.strip():
            return self._create_error_result(author_name, "Nom d'auteur vide")

        try:
            results = await self.search(author_name)

            # Chercher le meilleur match auteur
            best_author = self._find_best_author_match(results, author_name)

            if best_author is None:
                return {
                    "status": "not_found",
                    "original": author_name,
                    "babelio_suggestion": None,
                    "confidence_score": 0.0,
                    "babelio_data": None,
                    "babelio_url": None,
                    "error_message": None,
                }

            # Construire le nom suggéré
            suggested_name = self._format_author_name(
                best_author.get("prenoms"), best_author.get("nom")
            )

            # Calculer score de confiance
            confidence = self._calculate_similarity(author_name, suggested_name)

            # Déterminer le statut
            status = "verified" if confidence >= 0.95 else "corrected"

            return {
                "status": status,
                "original": author_name,
                "babelio_suggestion": suggested_name,
                "confidence_score": confidence,
                "babelio_data": best_author,
                "babelio_url": self._build_full_url(best_author.get("url", "")),
                "error_message": None,
            }

        except (TimeoutError, aiohttp.ClientError):
            # Propager les erreurs réseau/timeout pour que le script de migration
            # puisse les détecter et arrêter le traitement
            raise
        except Exception as e:
            logger.error(f"Erreur verify_author pour {author_name}: {e}")
            return self._create_error_result(author_name, str(e))

    async def verify_book(
        self, title: str, author: str | None = None
    ) -> dict[str, Any]:
        """Vérifie et corrige l'orthographe d'un titre de livre.

        Args:
            title: Titre du livre à vérifier
            author: Nom de l'auteur (optionnel, améliore la précision)

        Returns:
            Dict avec format:
                {
                    'status': 'verified'|'corrected'|'not_found'|'error',
                    'original_title': str,
                    'babelio_suggestion_title': str|None,
                    'original_author': str|None,
                    'babelio_suggestion_author': str|None,
                    'confidence_score': float,
                    'babelio_data': dict|None,
                    'babelio_url': str|None,
                    'error_message': str|None
                }
        """
        if not title or not title.strip():
            return self._create_book_error_result(title, author, "Titre vide")

        try:
            # Recherche par titre uniquement (Issue #124: Terminus Malaussène)
            # L'auteur sera utilisé pour filtrer les résultats, pas dans la query
            search_term = title

            if self._debug_log_enabled:
                logger.info(
                    f"🔍 [DEBUG] verify_book: search_term='{search_term}' "
                    f"(author filter: '{author or 'None'}')"
                )

            results = await self.search(search_term)

            if self._debug_log_enabled:
                books_count = len([r for r in results if r.get("type") == "livres"])
                authors_count = len([r for r in results if r.get("type") == "auteurs"])
                logger.info(
                    f"🔍 [DEBUG] verify_book: {len(results)} résultat(s) - {books_count} livre(s), {authors_count} auteur(s)"
                )

            # Chercher le meilleur match livre
            best_book = self._find_best_book_match(results, title, author)

            if self._debug_log_enabled:
                if best_book:
                    logger.info(
                        f"🔍 [DEBUG] verify_book: Match '{best_book.get('titre')}' par {self._format_author_name(best_book.get('prenoms'), best_book.get('nom'))}"
                    )
                else:
                    logger.info(
                        "🔍 [DEBUG] verify_book: Aucun match dans _find_best_book_match"
                    )

            if best_book is None:
                # Stratégie de fallback: Si "titre + auteur" ne donne rien ET qu'on a un auteur,
                # on réessaye avec juste le titre, puis on vérifie l'auteur par scraping
                if author and len(results) == 0:
                    if self._debug_log_enabled:
                        logger.info(
                            f"🔍 [DEBUG] verify_book: Fallback - recherche avec titre seul '{title}'"
                        )

                    # Recherche avec titre seul
                    title_only_results = await self.search(title)

                    if self._debug_log_enabled:
                        books_count = len(
                            [r for r in title_only_results if r.get("type") == "livres"]
                        )
                        logger.info(
                            f"🔍 [DEBUG] verify_book: Fallback trouvé {books_count} livre(s)"
                        )

                    # Pour chaque livre trouvé, scraper la page pour vérifier l'auteur
                    books = [r for r in title_only_results if r.get("type") == "livres"]
                    for book in books:
                        book_url_relative = book.get("url")
                        if not book_url_relative:
                            continue

                        book_url = self._build_full_url(book_url_relative)

                        # Scraper l'auteur depuis la page
                        scraped_author = await self._scrape_author_from_book_page(
                            book_url
                        )

                        if scraped_author:
                            # Calculer la similarité entre l'auteur attendu et l'auteur scraped
                            similarity = self._calculate_similarity(
                                author, scraped_author
                            )

                            if self._debug_log_enabled:
                                logger.info(
                                    f"🔍 [DEBUG] verify_book: Fallback - '{book.get('titre')}' author '{author}' vs scraped '{scraped_author}' = {similarity:.2f}"
                                )

                            # Si l'auteur correspond (seuil > 0.7), on a trouvé le bon livre
                            if similarity > 0.7:
                                if self._debug_log_enabled:
                                    logger.info(
                                        "🔍 [DEBUG] verify_book: Fallback SUCCESS - match trouvé avec auteur scraped"
                                    )

                                # Utiliser le livre trouvé comme best_book
                                best_book = book
                                # Ajouter les champs auteur manquants (puisque scraping retourne juste le nom)
                                # On ne peut pas extraire prénom/nom séparément du scraping, donc on utilise le nom complet
                                best_book["prenoms"] = None
                                best_book["nom"] = scraped_author
                                break

                # Si toujours pas de résultat après fallback
                if best_book is None:
                    return {
                        "status": "not_found",
                        "original_title": title,
                        "babelio_suggestion_title": None,
                        "original_author": author,
                        "babelio_suggestion_author": None,
                        "confidence_score": 0.0,
                        "babelio_data": None,
                        "babelio_url": None,
                        "babelio_author_url": None,
                        "error_message": None,
                    }

            # Extraire titre et auteur suggérés
            # Nettoyer les sauts de ligne et espaces multiples (Issue #96)
            suggested_title_raw = best_book.get("titre", title)
            suggested_title = (
                " ".join(suggested_title_raw.split()) if suggested_title_raw else title
            )

            # Nettoyer les sauts de ligne dans les champs auteur avant formatage
            prenoms_raw = best_book.get("prenoms")
            nom_raw = best_book.get("nom")
            prenoms_clean = " ".join(str(prenoms_raw).split()) if prenoms_raw else None
            nom_clean = " ".join(str(nom_raw).split()) if nom_raw else None

            suggested_author = self._format_author_name(prenoms_clean, nom_clean)

            # Nettoyer aussi les données brutes pour éviter les newlines dans babelio_data
            babelio_data_clean = {}
            for key, value in best_book.items():
                if isinstance(value, str):
                    babelio_data_clean[key] = " ".join(value.split())
                else:
                    babelio_data_clean[key] = value

            # Score basé sur le titre principalement
            title_confidence = self._calculate_similarity(title, suggested_title)

            # Bonus si l'auteur match aussi
            author_confidence = 1.0
            if author and suggested_author:
                author_confidence = self._calculate_similarity(author, suggested_author)

            # Score combiné (titre poids 70%, auteur 30%)
            confidence = 0.7 * title_confidence + 0.3 * author_confidence

            status = "verified" if confidence >= 0.90 else "corrected"

            # Construire l'URL complète Babelio
            babelio_url = self._build_full_url(best_book.get("url", ""))

            # Enrichissement éditeur: scraper si confiance >= 0.90 (Issue #85)
            babelio_publisher = None
            if confidence >= 0.90 and babelio_url:
                try:
                    babelio_publisher = await self.fetch_publisher_from_url(babelio_url)
                except Exception as e:
                    # Erreur de scraping non fatale, on continue sans éditeur
                    logger.debug(
                        f"Impossible de scraper l'éditeur pour {babelio_url}: {e}"
                    )

            # Enrichissement titre: scraper si titre tronqué détecté (Issue #88)
            if self._is_title_truncated(suggested_title) and babelio_url:
                try:
                    full_title = await self.fetch_full_title_from_url(babelio_url)
                    if full_title:
                        suggested_title = full_title
                        # Mettre à jour aussi babelio_data pour le frontend (Issue #88)
                        babelio_data_clean["titre"] = full_title
                except Exception as e:
                    # Erreur de scraping non fatale, on continue avec titre tronqué
                    logger.debug(
                        f"Impossible de scraper le titre complet pour {babelio_url}: {e}"
                    )

            # Enrichissement URL auteur: scraper depuis la page du livre (Issue #124)
            # On scrape toujours l'URL auteur si on a trouvé un livre sur Babelio,
            # indépendamment du score de confiance (contrairement à l'éditeur/titre)
            babelio_author_url = None
            if babelio_url:
                try:
                    babelio_author_url = await self.fetch_author_url_from_page(
                        babelio_url
                    )
                except Exception as e:
                    # Erreur de scraping non fatale, on continue sans URL auteur
                    logger.debug(
                        f"Impossible de scraper l'URL auteur pour {babelio_url}: {e}"
                    )

            return {
                "status": status,
                "original_title": title,
                "babelio_suggestion_title": suggested_title,
                "original_author": author,
                "babelio_suggestion_author": suggested_author,
                "confidence_score": confidence,
                "babelio_data": babelio_data_clean,
                "babelio_url": babelio_url,
                "babelio_author_url": babelio_author_url,
                "babelio_publisher": babelio_publisher,
                "error_message": None,
            }

        except (TimeoutError, aiohttp.ClientError):
            # Propager les erreurs réseau/timeout pour que le script de migration
            # puisse les détecter et arrêter le traitement
            raise
        except Exception as e:
            logger.error(f"Erreur verify_book pour {title}/{author}: {e}")
            return self._create_book_error_result(title, author, str(e))

    def _is_title_truncated(self, title: str | None) -> bool:
        """Détecte si un titre est tronqué (se termine par '...').

        Args:
            title: Titre à vérifier

        Returns:
            True si le titre se termine par '...', False sinon
        """
        if not title:
            return False
        return title.strip().endswith("...")

    async def fetch_full_title_from_url(self, babelio_url: str) -> str | None:
        """Scrape le titre complet depuis une page Babelio.

        Args:
            babelio_url: URL complète Babelio (ex: https://www.babelio.com/livres/...)

        Returns:
            Titre complet ou None si non trouvé

        Exemple:
            full_title = await service.fetch_full_title_from_url(
                "https://www.babelio.com/livres/Villanova-Le-Chemin-continue--Biographie-de-Georges-Lambric/1498118"
            )
            # → "Le Chemin continue : Biographie de Georges Lambrichs"

        Note:
            Utilise BeautifulSoup4 avec les sélecteurs:
            1. <meta property="og:title"> (prioritaire, nettoie le suffixe " - Babelio")
            2. <h1> (fallback)
        """
        if not babelio_url or not babelio_url.strip():
            return None

        try:
            session = await self._get_session()

            async with session.get(babelio_url) as response:
                if response.status != 200:
                    logger.warning(
                        f"Babelio HTTP {response.status} pour scraping titre: {babelio_url}"
                    )
                    return None

                # Utiliser Windows-1252 car Babelio déclare ISO-8859-1 mais utilise
                # des caractères Windows-1252 comme le tiret cadratin (0x96) (Issue #167)
                html = await response.text(encoding="cp1252")
                soup = BeautifulSoup(html, "lxml")

                # Priorité 1: h1 (contient juste le titre, sans nom d'auteur)
                h1_tag = soup.find("h1")
                if h1_tag:
                    title_raw = str(h1_tag.get_text())
                    # Nettoyer les sauts de ligne et espaces multiples
                    title_final = " ".join(title_raw.split())
                    logger.debug(
                        f"Titre complet trouvé (h1) pour {babelio_url}: {title_final}"
                    )
                    return title_final

                # Priorité 2: og:title (fallback, peut contenir "Titre - Auteur - Babelio")
                og_title_tag = soup.find("meta", property="og:title")
                if og_title_tag and hasattr(og_title_tag, "get"):
                    content = og_title_tag.get("content")
                    if content:
                        title_raw = str(content)
                        # Nettoyer le suffixe " - Babelio" et les espaces multiples
                        title_clean = title_raw.replace(" - Babelio", "").strip()
                        title_final = " ".join(title_clean.split())
                        logger.debug(
                            f"Titre complet trouvé (og:title) pour {babelio_url}: {title_final}"
                        )
                        return title_final

                logger.debug(f"Titre complet non trouvé pour {babelio_url}")
                return None

        except Exception as e:
            logger.error(f"Erreur scraping titre pour {babelio_url}: {e}")
            return None

    async def fetch_publisher_from_url(self, babelio_url: str) -> str | None:
        """Scrape l'éditeur depuis une page Babelio.

        Args:
            babelio_url: URL complète Babelio (ex: https://www.babelio.com/livres/...)

        Returns:
            Nom de l'éditeur ou None si non trouvé

        Exemple:
            publisher = await service.fetch_publisher_from_url(
                "https://www.babelio.com/livres/Assouline-Des-visages-et-des-mains-150-portraits-decrivain/1635414"
            )
            # → "Herscher"

        Note:
            Utilise BeautifulSoup4 avec le sélecteur CSS:
            a.tiny_links.dark[href*="/editeur/"]
        """
        if not babelio_url or not babelio_url.strip():
            return None

        try:
            session = await self._get_session()

            async with session.get(babelio_url) as response:
                if response.status != 200:
                    logger.warning(
                        f"Babelio HTTP {response.status} pour scraping éditeur: {babelio_url}"
                    )
                    return None

                # Utiliser Windows-1252 car Babelio déclare ISO-8859-1 mais utilise
                # des caractères Windows-1252 comme le tiret cadratin (0x96) (Issue #167)
                html = await response.text(encoding="cp1252")
                soup = BeautifulSoup(html, "lxml")

                # Sélecteur CSS pour l'éditeur: lien avec classe tiny_links dark
                # pointant vers /editeur/
                editeur_link = soup.select_one('a.tiny_links.dark[href*="/editeur/"]')

                if editeur_link:
                    # Nettoyer les sauts de ligne et espaces multiples
                    # (le HTML peut contenir des <br> ou des retours à la ligne)
                    publisher_raw: str = str(editeur_link.text)
                    publisher = " ".join(
                        publisher_raw.split()
                    )  # Split + join pour nettoyer
                    logger.debug(f"Éditeur trouvé pour {babelio_url}: {publisher}")
                    return publisher
                else:
                    logger.debug(f"Éditeur non trouvé pour {babelio_url}")
                    return None

        except Exception as e:
            logger.error(f"Erreur scraping éditeur pour {babelio_url}: {e}")
            return None

    async def fetch_cover_url_from_babelio_page(
        self,
        babelio_url: str,
        expected_title: str | None = None,
        babelio_cookies: str | None = None,
    ) -> str | None:
        """Scrape l'URL de couverture depuis une page Babelio (Issue #238).

        Args:
            babelio_url: URL complète Babelio (ex: https://www.babelio.com/livres/...)
            expected_title: Titre attendu du livre. Si fourni, vérifie que la page
                affiche bien ce livre (détecte les redirections Babelio vers un autre livre).

        Returns:
            URL de la couverture (str), None si non trouvée, ou "TITLE_MISMATCH:<page_title>"
            si le titre de la page ne correspond pas au titre attendu.

        Exemple:
            cover_url = await service.fetch_cover_url_from_babelio_page(
                "https://www.babelio.com/livres/Millet-Simone-monet/1870367",
                expected_title="Simone Émonet",
            )
            # → "https://www.babelio.com/couv/CVT_Simone-monet_42.jpg"

        Note:
            Utilise BeautifulSoup4 avec les sélecteurs:
            1. <meta property="og:image"> (prioritaire)
            2. <img src*="/couv/CVT_"> (fallback)
        """
        from ..utils.text_utils import normalize_for_matching

        if not babelio_url or not babelio_url.strip():
            return None

        try:
            # Headers identiques à un vrai navigateur Firefox (Sec-Fetch-* requis par Babelio)
            page_headers = {
                "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:148.0) Gecko/20100101 Firefox/148.0",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "fr,en-US;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate",
                "Referer": "https://www.babelio.com/",
                "DNT": "1",
                "Sec-GPC": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin",
                "Sec-Fetch-User": "?1",
            }
            if babelio_cookies:
                page_headers["Cookie"] = babelio_cookies

            timeout = aiohttp.ClientTimeout(total=10, connect=5)
            async with (
                aiohttp.ClientSession(
                    headers=page_headers, timeout=timeout
                ) as tmp_session,
                tmp_session.get(babelio_url) as response,
            ):
                if response.status != 200:
                    logger.warning(
                        f"Babelio HTTP {response.status} pour scraping couverture: {babelio_url}"
                    )
                    return None

                # Utiliser Windows-1252 car Babelio déclare ISO-8859-1 mais utilise
                # des caractères Windows-1252 comme le tiret cadratin (0x96) (Issue #167)
                html = await response.text(encoding="cp1252")
                soup = BeautifulSoup(html, "lxml")

                # Validation du titre : vérifier que la page correspond au livre demandé
                # (Babelio redirige parfois vers un autre livre via des URLs obsolètes)
                if expected_title:
                    h1 = soup.find("h1")
                    if h1:
                        page_title = normalize_for_matching(h1.get_text())
                        norm_expected = normalize_for_matching(expected_title)
                        if (
                            norm_expected not in page_title
                            and page_title not in norm_expected
                        ):
                            page_title_raw = h1.get_text().strip()
                            logger.warning(
                                f"Titre Babelio ne correspond pas pour {babelio_url}: "
                                f"attendu='{expected_title}', page='{page_title_raw}'"
                            )
                            return f"TITLE_MISMATCH:{page_title_raw}"

                # Priorité 1: og:image (peut pointer vers babelio.com ou un CDN comme Amazon)
                og_image = soup.find("meta", property="og:image")
                if og_image and hasattr(og_image, "get"):
                    content = og_image.get("content")
                    if content and str(content).startswith("http"):
                        cover_url = str(content)
                        logger.debug(
                            f"Couverture trouvée (og:image) pour {babelio_url}: {cover_url}"
                        )
                        return cover_url

                # Priorité 2: img avec src contenant /couv/CVT_
                cover_img = soup.select_one('img[src*="/couv/CVT_"]')
                if cover_img and hasattr(cover_img, "get"):
                    src = cover_img.get("src")
                    if src:
                        src_str = str(src)
                        if src_str.startswith("http"):
                            logger.debug(
                                f"Couverture trouvée (img CVT_) pour {babelio_url}: {src_str}"
                            )
                            return src_str
                        # URL relative → construire URL absolue
                        cover_url = "https://www.babelio.com" + src_str
                        logger.debug(
                            f"Couverture trouvée (img CVT_ relative) pour {babelio_url}: {cover_url}"
                        )
                        return cover_url

                logger.debug(f"Couverture non trouvée pour {babelio_url}")
                return None

        except Exception as e:
            logger.error(f"Erreur scraping couverture pour {babelio_url}: {e}")
            return None

    async def fetch_author_name_from_url(self, babelio_url: str) -> str | None:
        """Scrape le nom d'auteur depuis une page auteur Babelio.

        Args:
            babelio_url: URL complète Babelio auteur (ex: https://www.babelio.com/auteur/...)

        Returns:
            Nom de l'auteur ou None si non trouvé

        Exemple:
            author_name = await service.fetch_author_name_from_url(
                "https://www.babelio.com/auteur/Christian-Thorel/165895"
            )
            # → "Christian Thorel"

        Note:
            Utilise BeautifulSoup4 avec le sélecteur h1
            pour extraire le nom depuis la page auteur.
        """
        if not babelio_url or not babelio_url.strip():
            return None

        try:
            session = await self._get_session()

            async with session.get(babelio_url) as response:
                if response.status != 200:
                    logger.warning(
                        f"Babelio HTTP {response.status} pour scraping auteur: {babelio_url}"
                    )
                    return None

                # Utiliser Windows-1252 car Babelio déclare ISO-8859-1 mais utilise
                # des caractères Windows-1252 comme le tiret cadratin (0x96)
                html = await response.text(encoding="cp1252")
                soup = BeautifulSoup(html, "lxml")

                # Sur une page auteur, le h1 contient le nom de l'auteur
                h1_tag = soup.find("h1")
                if h1_tag:
                    author_raw = str(h1_tag.get_text())
                    # Nettoyer les sauts de ligne et espaces multiples
                    author_name = " ".join(author_raw.split())
                    logger.debug(f"Nom auteur trouvé pour {babelio_url}: {author_name}")
                    return author_name

                logger.debug(f"Nom auteur non trouvé pour {babelio_url}")
                return None

        except Exception as e:
            logger.error(f"Erreur scraping auteur pour {babelio_url}: {e}")
            return None

    async def verify_publisher(self, publisher_name: str) -> dict[str, Any]:
        """Vérifie l'orthographe d'un nom d'éditeur.

        Note: Babelio ne semble pas avoir d'API spécifique pour les éditeurs,
        cette fonction cherche dans les résultats généraux.

        Args:
            publisher_name: Nom de l'éditeur à vérifier

        Returns:
            Dict au même format que verify_author
        """
        # Pour l'instant, utilise la même logique que les auteurs
        # Pourrait être affinée plus tard si Babelio expose mieux les éditeurs
        return await self.verify_author(publisher_name)

    async def verify_batch(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Vérifie plusieurs éléments en lot tout en respectant le rate limiting.

        Args:
            items: Liste d'éléments au format:
                [
                    {"type": "author", "name": "Michel Houellebecq"},
                    {"type": "book", "title": "L'Étranger", "author": "Albert Camus"},
                    {"type": "publisher", "name": "Gallimard"}
                ]

        Returns:
            list[dict]: Résultats de vérification dans le même ordre
        """

        async def _verify_one(item: dict[str, Any]) -> dict[str, Any]:
            item_type = item.get("type")

            if item_type == "author":
                return await self.verify_author(item.get("name", ""))
            elif item_type == "book":
                return await self.verify_book(item.get("title", ""), item.get("author"))
            elif item_type == "publisher":
                return await self.verify_publisher(item.get("name", ""))
            else:
                return self._create_error_result(
                    str(item), f"Type non supporté: {item_type}"
                )

        # Dispatch all verifications concurrently; each verification still
        # respects the internal rate_limiter in search(). Using gather keeps
        # ordering of results consistent with the input list.
        tasks = [asyncio.create_task(_verify_one(it)) for it in items]
        results = await asyncio.gather(*tasks)
        return list(results)

    def _find_best_author_match(
        self, results: list[dict], search_term: str
    ) -> dict | None:
        """Trouve le meilleur match auteur dans les résultats Babelio."""
        authors = [r for r in results if r.get("type") == "auteurs"]

        if not authors:
            return None

        # Trier par pertinence (nombre de membres/œuvres si disponible)
        authors.sort(
            key=lambda a: (
                int(a.get("ca_membres", 0) or 0),
                int(a.get("ca_oeuvres", 0) or 0),
            ),
            reverse=True,
        )

        return authors[0]

    def _find_best_book_match(
        self, results: list[dict], title: str, author: str | None = None
    ) -> dict | None:
        """Trouve le meilleur match livre dans les résultats Babelio."""
        books = [r for r in results if r.get("type") == "livres"]

        if not books:
            if self._debug_log_enabled:
                logger.info("🔍 [DEBUG] _find_best_book_match: Aucun livre trouvé")
            return None

        if self._debug_log_enabled:
            logger.info(
                f"🔍 [DEBUG] _find_best_book_match: {len(books)} livre(s) avant filtrage"
            )

        # Si on a l'auteur, filtrer par auteur d'abord
        if author:
            author_filtered = []
            for book in books:
                book_author = self._format_author_name(
                    book.get("prenoms"), book.get("nom")
                )
                similarity = (
                    self._calculate_similarity(author, book_author)
                    if book_author
                    else 0.0
                )

                if self._debug_log_enabled:
                    logger.info(
                        f"🔍 [DEBUG] _find_best_book_match: '{book.get('titre')}' - author '{author}' vs '{book_author}' = {similarity:.2f}"
                    )

                if book_author and similarity > 0.7:
                    author_filtered.append(book)

            if self._debug_log_enabled:
                logger.info(
                    f"🔍 [DEBUG] _find_best_book_match: {len(author_filtered)} livre(s) après filtre auteur (seuil>0.7)"
                )

            if author_filtered:
                books = author_filtered
            else:
                # Aucun livre ne correspond à l'auteur → not_found
                return None

        # Trier par pertinence (copies, notes si disponibles)
        books.sort(
            key=lambda b: (
                int(b.get("ca_copies", 0) or 0),
                float(b.get("ca_note", 0) or 0),
            ),
            reverse=True,
        )

        return books[0]

    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calcule la similarité entre deux chaînes (0.0 à 1.0).

        Utilise difflib.SequenceMatcher qui implémente l'algorithme
        de Ratcliff-Obershelp pour la similarité de séquences.

        Normalise également les ligatures latines (œ→oe, æ→ae) pour
        éviter les faux négatifs sur les titres français.
        """
        if not str1 or not str2:
            return 0.0

        # Normaliser : minuscules, espaces supprimés
        s1 = str1.lower().strip()
        s2 = str2.lower().strip()

        # Normaliser les ligatures latines (œ→oe, æ→ae)
        # Cas minuscules
        s1 = s1.replace("œ", "oe").replace("æ", "ae")
        s2 = s2.replace("œ", "oe").replace("æ", "ae")
        # Cas majuscules (déjà passées en minuscules, mais gardons pour cohérence)
        s1 = s1.replace("Œ".lower(), "oe").replace("Æ".lower(), "ae")
        s2 = s2.replace("Œ".lower(), "oe").replace("Æ".lower(), "ae")

        if s1 == s2:
            return 1.0

        return SequenceMatcher(None, s1, s2).ratio()

    def _format_author_name(self, prenoms: Any, nom: Any) -> str:
        """Formate un nom d'auteur à partir des données Babelio."""
        prenoms_str = str(prenoms).strip() if prenoms else ""
        nom_str = str(nom).strip() if nom else ""

        # Nettoyer les virgules et espaces en fin de chaîne (bug Babelio)
        prenoms_str = prenoms_str.rstrip(", ")
        nom_str = nom_str.rstrip(", ")

        if prenoms_str and nom_str:
            return f"{prenoms_str} {nom_str}"
        elif nom_str:
            return nom_str
        elif prenoms_str:
            return prenoms_str
        else:
            return ""

    def _build_full_url(self, relative_url: str) -> str:
        """Construit une URL complète Babelio."""
        if not relative_url:
            return ""
        if relative_url.startswith("http"):
            return relative_url
        return f"{self.base_url}{relative_url}"

    async def fetch_author_url_from_page(self, babelio_url: str) -> str | None:
        """Scrape l'URL auteur depuis une page livre Babelio (Issue #124).

        Args:
            babelio_url: URL complète Babelio du livre

        Returns:
            URL complète de l'auteur ou None si non trouvée

        Exemple:
            author_url = await service.fetch_author_url_from_page(
                "https://www.babelio.com/livres/Garreta-Sphinx/149981"
            )
            # → "https://www.babelio.com/auteur/Anne-F-Garreta/20464"

        Note:
            Utilise BeautifulSoup4 avec le sélecteur CSS:
            a[href*="/auteur/"]
        """
        if not babelio_url or not babelio_url.strip():
            return None

        try:
            session = await self._get_session()

            if self._debug_log_enabled:
                logger.info(
                    f"🔍 [DEBUG] fetch_author_url_from_page: Fetching {babelio_url}"
                )

            async with session.get(babelio_url) as response:
                if response.status != 200:
                    logger.warning(
                        f"Babelio HTTP {response.status} pour scraping auteur: {babelio_url}"
                    )
                    if self._debug_log_enabled:
                        logger.info(
                            f"🔍 [DEBUG] fetch_author_url_from_page: HTTP error {response.status}"
                        )
                    return None

                # Utiliser Windows-1252 car Babelio déclare ISO-8859-1 mais utilise
                # des caractères Windows-1252 comme le tiret cadratin (0x96) (Issue #167)
                html = await response.text(encoding="cp1252")
                soup = BeautifulSoup(html, "lxml")

                # Sélecteur CSS pour l'auteur: premier lien pointant vers /auteur/
                auteur_link = soup.select_one('a[href*="/auteur/"]')

                if auteur_link and hasattr(auteur_link, "get"):
                    href = auteur_link.get("href")
                    if href and isinstance(href, str):
                        # Construire l'URL complète
                        author_url = self._build_full_url(href)
                        if self._debug_log_enabled:
                            logger.info(
                                f"🔍 [DEBUG] fetch_author_url_from_page: URL auteur trouvée '{author_url}'"
                            )
                        return author_url
                    else:
                        if self._debug_log_enabled:
                            logger.info(
                                "🔍 [DEBUG] fetch_author_url_from_page: Lien auteur sans href valide"
                            )
                        return None
                else:
                    if self._debug_log_enabled:
                        logger.info(
                            "🔍 [DEBUG] fetch_author_url_from_page: Aucun lien auteur trouvé avec sélecteur 'a[href*=\"/auteur/\"]'"
                        )
                    return None

        except Exception as e:
            logger.error(f"Erreur scraping URL auteur pour {babelio_url}: {e}")
            if self._debug_log_enabled:
                logger.info(
                    f"🔍 [DEBUG] fetch_author_url_from_page: Exception {type(e).__name__}: {e}"
                )
            return None

    def _create_error_result(self, original: str, error_message: str) -> dict[str, Any]:
        """Crée un résultat d'erreur standardisé pour auteur."""
        return {
            "status": "error",
            "original": original,
            "babelio_suggestion": None,
            "confidence_score": 0.0,
            "babelio_data": None,
            "babelio_url": None,
            "error_message": error_message,
        }

    def _create_book_error_result(
        self, title: str, author: str | None, error_message: str
    ) -> dict[str, Any]:
        """Crée un résultat d'erreur standardisé pour livre."""
        return {
            "status": "error",
            "original_title": title,
            "babelio_suggestion_title": None,
            "original_author": author,
            "babelio_suggestion_author": None,
            "confidence_score": 0.0,
            "babelio_data": None,
            "babelio_url": None,
            "babelio_author_url": None,
            "error_message": error_message,
        }

    async def _scrape_author_from_book_page(self, babelio_url: str) -> str | None:
        """Scrape le nom de l'auteur depuis une page livre Babelio.

        Args:
            babelio_url: URL complète Babelio du livre

        Returns:
            Nom de l'auteur ou None si non trouvé

        Note:
            Utilise BeautifulSoup pour extraire le nom de l'auteur
            depuis le lien avec classe 'livre_auteur' ou href contenant '/auteur/'.
        """
        if not babelio_url or not babelio_url.strip():
            return None

        try:
            session = await self._get_session()

            if self._debug_log_enabled:
                logger.info(
                    f"🔍 [DEBUG] _scrape_author_from_book_page: Fetching {babelio_url}"
                )

            async with session.get(babelio_url) as response:
                if response.status != 200:
                    logger.warning(
                        f"Babelio HTTP {response.status} pour scraping auteur: {babelio_url}"
                    )
                    return None

                # Utiliser Windows-1252 car Babelio déclare ISO-8859-1 mais utilise
                # des caractères Windows-1252 comme le tiret cadratin (0x96) (Issue #167)
                html = await response.text(encoding="cp1252")
                soup = BeautifulSoup(html, "lxml")

                # Stratégie 1: Chercher un lien avec classe 'livre_auteur'
                auteur_link = soup.select_one("a.livre_auteur")

                # Stratégie 2: Si non trouvé, chercher le premier lien vers /auteur/
                if not auteur_link:
                    auteur_link = soup.select_one('a[href*="/auteur/"]')

                if auteur_link:
                    # Utiliser separator=' ' pour forcer un espace entre les éléments HTML
                    # Cela évite les noms collés comme "DarioFranceschini" (Issue #159)
                    author_name = auteur_link.get_text(separator=" ", strip=True)
                    if author_name:
                        if self._debug_log_enabled:
                            logger.info(
                                f"🔍 [DEBUG] _scrape_author_from_book_page: Found author '{author_name}'"
                            )
                        return author_name

                if self._debug_log_enabled:
                    logger.info(
                        f"🔍 [DEBUG] _scrape_author_from_book_page: No author found on {babelio_url}"
                    )
                return None

        except Exception as e:
            logger.error(
                f"Erreur scraping auteur pour {babelio_url}: {e}", exc_info=True
            )
            return None

    async def close(self):
        """Ferme proprement la session HTTP.

        À appeler à la fin de l'utilisation pour éviter les warnings asyncio.
        """
        if self.session and not self.session.closed:
            await self.session.close()


# Instance globale du service (pattern singleton pour réutiliser la session)
babelio_service = BabelioService()
