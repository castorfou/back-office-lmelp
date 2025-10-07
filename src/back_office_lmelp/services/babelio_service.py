"""Service de vérification orthographique via Babelio.com

Ce service utilise l'API AJAX de Babelio pour vérifier et corriger l'orthographe
des auteurs, livres et éditeurs extraits des avis critiques.

Architecture :
- Endpoint : POST https://www.babelio.com/aj_recherche.php
- Format : JSON {"term": "search_term", "isMobile": false}
- Headers : Content-Type: application/json, X-Requested-With: XMLHttpRequest
- Cookies : disclaimer=1, p=FR (nécessaires pour éviter les blocages)
- Rate limiting : 0.8 sec entre requêtes (respectueux de Babelio)

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


logger = logging.getLogger(__name__)


class BabelioService:
    """Service de vérification orthographique via l'API AJAX de Babelio.

    Ce service respecte les bonnes pratiques :
    - Rate limiting à 0.8 sec entre requêtes
    - Headers et cookies appropriés pour éviter les blocages
    - Gestion d'erreur robuste (timeout, réseau, parsing JSON)
    - Session HTTP réutilisable et fermeture propre
    - Calcul de scores de confiance pour les suggestions

    Attributes:
        base_url: URL de base de Babelio
        search_endpoint: Endpoint AJAX pour la recherche
        session: Session aiohttp réutilisable
        rate_limiter: Semaphore pour limiter à 1 req/sec
    """

    def __init__(self):
        """Initialise le service Babelio avec configuration appropriée."""
        self.base_url = "https://www.babelio.com"
        self.search_endpoint = "/aj_recherche.php"
        self.session: aiohttp.ClientSession | None = None
        self.rate_limiter = asyncio.Semaphore(1)  # 1 requête simultanée max
        self.last_request_time = 0  # Timestamp de la dernière requête
        self.min_interval = 0.8  # Délai minimum de 0.8 secondes entre requêtes
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
        # If verbose cache logging is enabled, make sure our module logger
        # will emit INFO messages to stdout (useful when running under uvicorn)
        if self._cache_log_enabled:
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

                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        try:
                            # Babelio retourne du JSON valide mais avec le mauvais Content-Type
                            # On récupère le texte brut puis on parse le JSON manuellement
                            text_content = await response.text()
                            results: list[dict[str, Any]] = json.loads(text_content)
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

            except TimeoutError:
                logger.error(f"Timeout Babelio pour: {term}")
                return []
            except aiohttp.ClientError as e:
                logger.error(f"Erreur réseau Babelio pour {term}: {e}")
                return []
            except Exception as e:
                logger.error(f"Erreur inattendue Babelio pour {term}: {e}")
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
            # Recherche combinée titre + auteur si disponible
            search_term = f"{title} {author}" if author else title
            results = await self.search(search_term)

            # Chercher le meilleur match livre
            best_book = self._find_best_book_match(results, title, author)

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
                    "error_message": None,
                }

            # Extraire titre et auteur suggérés
            suggested_title = best_book.get("titre", title)
            suggested_author = self._format_author_name(
                best_book.get("prenoms"), best_book.get("nom")
            )

            # Score basé sur le titre principalement
            title_confidence = self._calculate_similarity(title, suggested_title)

            # Bonus si l'auteur match aussi
            author_confidence = 1.0
            if author and suggested_author:
                author_confidence = self._calculate_similarity(author, suggested_author)

            # Score combiné (titre poids 70%, auteur 30%)
            confidence = 0.7 * title_confidence + 0.3 * author_confidence

            status = "verified" if confidence >= 0.90 else "corrected"

            return {
                "status": status,
                "original_title": title,
                "babelio_suggestion_title": suggested_title,
                "original_author": author,
                "babelio_suggestion_author": suggested_author,
                "confidence_score": confidence,
                "babelio_data": best_book,
                "babelio_url": self._build_full_url(best_book.get("url", "")),
                "error_message": None,
            }

        except Exception as e:
            logger.error(f"Erreur verify_book pour {title}/{author}: {e}")
            return self._create_book_error_result(title, author, str(e))

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
            return None

        # Si on a l'auteur, filtrer par auteur d'abord
        if author:
            author_filtered = []
            for book in books:
                book_author = self._format_author_name(
                    book.get("prenoms"), book.get("nom")
                )
                if (
                    book_author
                    and self._calculate_similarity(author, book_author) > 0.7
                ):
                    author_filtered.append(book)

            if author_filtered:
                books = author_filtered

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
        """
        if not str1 or not str2:
            return 0.0

        # Normaliser : minuscules, espaces supprimés
        s1 = str1.lower().strip()
        s2 = str2.lower().strip()

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
            "error_message": error_message,
        }

    async def close(self):
        """Ferme proprement la session HTTP.

        À appeler à la fin de l'utilisation pour éviter les warnings asyncio.
        """
        if self.session and not self.session.closed:
            await self.session.close()


# Instance globale du service (pattern singleton pour réutiliser la session)
babelio_service = BabelioService()
