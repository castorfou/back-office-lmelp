#!/usr/bin/env python3
"""Script de migration pour backfill les URL Babelio (Issue #124).

Ce script met à jour UN livre et son auteur correspondant pour ajouter
le champ url_babelio en utilisant l'API Babelio.

IMPORTANT: Ce script respecte un délai de 5 secondes entre CHAQUE requête HTTP
vers Babelio pour éviter le rate limiting et le bannissement d'IP.

Usage:
    PYTHONPATH=/workspaces/back-office-lmelp/src python scripts/migrate_url_babelio.py [--dry-run]

Options:
    --dry-run    Affiche les modifications sans les appliquer
"""

import argparse
import asyncio
import logging
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from bs4 import BeautifulSoup
from bson import ObjectId


# Ajouter le chemin src au PYTHONPATH
# Fix Issue #135: Corriger le calcul du chemin vers /workspaces/back-office-lmelp/src
# (ou /app/src en production) au lieu de /workspaces/back-office-lmelp/scripts/src
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from back_office_lmelp.services.babelio_service import BabelioService
from back_office_lmelp.services.mongodb_service import mongodb_service


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Délai minimum entre requêtes HTTP vers Babelio (en secondes)
# CRITIQUE: Même valeur que BabelioService.min_interval pour cohérence
MIN_REQUEST_INTERVAL = 5.0

# Timestamp de la dernière requête HTTP (global pour tout le script)
last_request_time = 0.0


def normalize_title(title: str) -> str:
    """Normalise un titre pour comparaison (minuscules, sans accents, espaces, ligatures, ponctuation).

    Args:
        title: Titre à normaliser

    Returns:
        Titre normalisé

    Note:
        Doit être cohérent avec BabelioService._calculate_similarity()
    """
    import unicodedata

    # Minuscules d'abord
    title_lower = title.lower()

    # Normaliser les apostrophes typographiques (', ', ‛, ‚) vers '
    # CRITIQUE: Babelio utilise souvent des apostrophes typographiques
    title_lower = (
        title_lower.replace("\u2019", "'")  # ' (right single quotation mark)
        .replace("\u2018", "'")  # ' (left single quotation mark)
        .replace("\u201b", "'")  # ‛ (single high-reversed-9 quotation mark)
        .replace("\u201a", "'")  # ‚ (single low-9 quotation mark)
    )

    # Normaliser les ligatures latines (œ→oe, æ→ae)
    # CRITIQUE: Doit être fait AVANT la suppression des accents
    title_lower = title_lower.replace("œ", "oe").replace("æ", "ae")

    # Retirer les accents
    title_no_accents = "".join(
        c
        for c in unicodedata.normalize("NFD", title_lower)
        if unicodedata.category(c) != "Mn"
    )

    # Retirer la ponctuation (virgules, points, tirets, etc.)
    # mais garder les lettres, chiffres et espaces
    import re

    title_no_punct = re.sub(r"[^\w\s]", " ", title_no_accents)

    # Espaces multiples
    return " ".join(title_no_punct.split())


async def wait_rate_limit() -> None:
    """Attend le délai nécessaire pour respecter le rate limiting.

    CRITIQUE: Doit être appelé AVANT chaque requête HTTP vers Babelio.
    """
    global last_request_time

    current_time = time.time()
    time_since_last = current_time - last_request_time

    if time_since_last < MIN_REQUEST_INTERVAL:
        wait_time = MIN_REQUEST_INTERVAL - time_since_last
        logger.info(
            f"⏱️  Rate limiting: attente de {wait_time:.1f}s avant prochaine requête..."
        )
        await asyncio.sleep(wait_time)

    last_request_time = time.time()


async def scrape_title_from_page(
    babelio_service: BabelioService, url: str
) -> str | None:
    """Scrape le titre depuis une page Babelio.

    Args:
        babelio_service: Instance du service Babelio
        url: URL de la page Babelio

    Returns:
        Titre extrait ou None si erreur
    """
    try:
        # CRITIQUE: Attendre le délai avant la requête HTTP
        await wait_rate_limit()

        session = await babelio_service._get_session()
        async with session.get(url) as response:
            if response.status != 200:
                return None

            html = await response.text()
            soup = BeautifulSoup(html, "lxml")

            # Le titre est dans le premier <h1> de la page
            title_elem = soup.find("h1")
            if title_elem:
                return title_elem.get_text(strip=True)

            return None
    except Exception as e:
        logger.error(f"❌ Erreur scraping titre depuis {url}: {e}")
        return None


def load_problematic_book_ids() -> set[str]:
    """Charge les IDs des livres déjà identifiés comme problématiques depuis MongoDB.

    Returns:
        Set des livre_id déjà loggés dans la collection babelio_problematic_cases
    """
    problematic_ids = set()

    # Lire depuis la collection MongoDB babelio_problematic_cases
    problematic_collection = mongodb_service.get_collection("babelio_problematic_cases")

    for case in problematic_collection.find():
        livre_id = case.get("livre_id")
        if livre_id:
            problematic_ids.add(livre_id)

    return problematic_ids


def log_problematic_case(
    livre_id: str,
    titre_attendu: str,
    titre_trouve: str | None,
    url_babelio: str,
    auteur: str,
    raison: str,
) -> None:
    """Log un cas problématique dans MongoDB collection babelio_problematic_cases.

    Args:
        livre_id: ID du livre dans MongoDB
        titre_attendu: Titre attendu
        titre_trouve: Titre trouvé sur Babelio (ou None)
        url_babelio: URL Babelio retournée
        auteur: Nom de l'auteur
        raison: Raison du rejet
    """
    case = {
        "type": "livre",  # Identificateur de type
        "timestamp": datetime.now(UTC),
        "livre_id": str(livre_id),
        "titre_attendu": titre_attendu,
        "titre_trouve": titre_trouve,
        "url_babelio": url_babelio,
        "auteur": auteur,
        "raison": raison,
    }

    # Écrire dans MongoDB collection babelio_problematic_cases
    problematic_collection = mongodb_service.get_collection("babelio_problematic_cases")
    problematic_collection.insert_one(case)

    logger.warning(f"⚠️  Cas problématique loggé: {raison}")


def log_problematic_author(
    auteur_id,  # ObjectId ou str
    nom_auteur: str,
    nb_livres: int,
    livres_status: str,  # "all_not_found" | "orphelin" | "all_problematic"
    raison: str,
) -> None:
    """Log un cas problématique d'AUTEUR dans MongoDB collection babelio_problematic_cases.

    Args:
        auteur_id: ID de l'auteur dans MongoDB (ObjectId ou str)
        nom_auteur: Nom de l'auteur
        nb_livres: Nombre de livres liés à cet auteur
        livres_status: Statut des livres ("all_not_found", "orphelin", "all_problematic")
        raison: Raison du problème
    """
    case = {
        "type": "auteur",  # Identificateur de type
        "timestamp": datetime.now(UTC),
        "auteur_id": str(auteur_id),  # Convertir ObjectId en string
        "nom_auteur": nom_auteur,
        "nb_livres": nb_livres,
        "livres_status": livres_status,
        "raison": raison,
    }

    # Écrire dans MongoDB collection babelio_problematic_cases
    problematic_collection = mongodb_service.get_collection("babelio_problematic_cases")
    problematic_collection.insert_one(case)

    logger.warning(f"⚠️  Auteur problématique loggé: {raison}")


async def migrate_one_book_and_author(
    babelio_service: BabelioService, dry_run: bool = False
) -> dict[str, bool | str]:
    """Migre UN livre et son auteur pour ajouter url_babelio.

    Args:
        babelio_service: Instance du service Babelio
        dry_run: Si True, affiche sans modifier

    Returns:
        Statut de la migration {book_updated, author_updated, error_type}
        error_type peut être: None, 'http_error', 'scraping_error', 'validation_error'
    """
    logger.info("🔍 Recherche d'un livre sans URL Babelio...")

    livres_collection = mongodb_service.get_collection("livres")
    auteurs_collection = mongodb_service.get_collection("auteurs")

    # Charger les IDs des livres déjà identifiés comme problématiques
    problematic_ids = load_problematic_book_ids()
    if problematic_ids:
        logger.info(
            f"ℹ️  {len(problematic_ids)} livre(s) problématique(s) seront ignorés"
        )

    # Construire la query pour exclure les cas problématiques
    from bson import ObjectId

    query = {
        "$or": [{"url_babelio": None}, {"url_babelio": {"$exists": False}}],
        # CRITIQUE: Exclure les livres déjà marqués "not found" par l'utilisateur
        # Sinon ils seront re-traités et re-ajoutés au JSONL à chaque migration
        "$nor": [{"babelio_not_found": True}],
    }

    if problematic_ids:
        # Exclure les livres déjà loggés comme problématiques
        excluded_object_ids = [ObjectId(id_str) for id_str in problematic_ids]
        query["_id"] = {"$nin": excluded_object_ids}

    # Trouver UN livre sans url_babelio (en excluant les problématiques)
    livre = livres_collection.find_one(query)

    if not livre:
        logger.info("✅ Tous les livres ont déjà une URL Babelio")
        return None  # Aucun livre à traiter - MigrationRunner arrêtera la boucle

    titre = livre.get("titre", "")
    auteur_id = livre.get("auteur_id")

    logger.info(f"📚 Livre trouvé: '{titre}' (ID: {livre['_id']})")

    # Trouver l'auteur correspondant
    auteur = None
    if auteur_id:
        auteur = auteurs_collection.find_one({"_id": auteur_id})
        if auteur:
            nom_auteur = auteur.get("nom", "")
            logger.info(f"✍️  Auteur: '{nom_auteur}' (ID: {auteur['_id']})")
        else:
            logger.warning(f"⚠️  Auteur ID {auteur_id} non trouvé dans la collection")
            nom_auteur = ""
    else:
        logger.warning(f"⚠️  Livre {livre['_id']} n'a pas d'auteur_id")
        nom_auteur = ""

    # Vérifier le livre via Babelio
    logger.info(f"🌐 Vérification sur Babelio: '{titre}' par '{nom_auteur}'")

    # Initialiser les statuts
    author_already_linked = False

    try:
        # Note: verify_book() contient déjà le rate limiting via search()
        # donc pas besoin d'appeler wait_rate_limit() ici
        result = await babelio_service.verify_book(titre, nom_auteur)
    except Exception as e:
        # Erreur réseau/timeout = problème temporaire Babelio, PAS un problème du livre
        # On ne log PAS dans problematic_cases car ce n'est pas un problème de données
        logger.error(f"❌ Erreur lors de l'appel à Babelio (timeout/réseau): {e}")
        logger.warning(
            "⚠️  Ceci indique probablement que Babelio est temporairement indisponible"
        )
        return {
            "livre_updated": False,
            "auteur_updated": False,
            "titre": titre,
            "auteur": nom_auteur,
            "status": "error",
        }

    book_updated = False
    author_updated = False

    # Traiter le résultat pour le livre
    if result.get("status") in ["verified", "corrected"]:
        url_babelio_livre = result.get("babelio_url")
        url_babelio_auteur = result.get("babelio_author_url")

        if url_babelio_livre:
            logger.info(f"📖 URL Babelio livre: {url_babelio_livre}")

            # ÉTAPE 1: Vérification HTTP 200
            try:
                # CRITIQUE: Attendre le délai avant la requête HTTP
                await wait_rate_limit()

                session = await babelio_service._get_session()
                async with session.get(url_babelio_livre) as response:
                    if response.status != 200:
                        logger.warning(
                            f"⚠️  URL livre invalide (HTTP {response.status})"
                        )
                        # Ne logger que les 404 (vraiment introuvable)
                        # 500/503 = problème serveur Babelio, pas un problème de données
                        if response.status == 404:
                            log_problematic_case(
                                livre["_id"],
                                titre,
                                None,
                                url_babelio_livre,
                                nom_auteur,
                                f"HTTP {response.status} (Not Found)",
                            )
                        else:
                            logger.warning(
                                "⚠️  Ceci indique probablement que Babelio est temporairement indisponible"
                            )
                        return {
                            "livre_updated": False,
                            "auteur_updated": False,
                            "titre": titre,
                            "auteur": nom_auteur,
                            "status": "error",
                        }

                logger.info("✅ URL livre vérifiée (HTTP 200)")

                # ÉTAPE 2: Scraper le titre depuis la page et valider
                titre_page = await scrape_title_from_page(
                    babelio_service, url_babelio_livre
                )

                if titre_page is None:
                    logger.error("❌ Impossible de scraper le titre depuis la page")
                    logger.warning(
                        "⚠️  Ceci peut indiquer que Babelio est temporairement indisponible"
                    )
                    logger.warning(
                        "⚠️  Ou bien que la structure HTML de Babelio a changé"
                    )
                    # Ne PAS logger dans problematic_cases car on ne sait pas si c'est
                    # un problème de données ou un problème temporaire Babelio
                    return {
                        "livre_updated": False,
                        "auteur_updated": False,
                        "titre": titre,
                        "auteur": nom_auteur,
                        "status": "error",
                    }

                # Comparaison normalisée des titres
                titre_normalise_attendu = normalize_title(titre)
                titre_normalise_trouve = normalize_title(titre_page)

                logger.info(
                    f"📖 Titre attendu: '{titre}' → normalisé: '{titre_normalise_attendu}'"
                )
                logger.info(
                    f"📄 Titre trouvé: '{titre_page}' → normalisé: '{titre_normalise_trouve}'"
                )

                if titre_normalise_attendu != titre_normalise_trouve:
                    logger.error(
                        f"❌ TITRE INCORRECT ! Attendu: '{titre}', Trouvé: '{titre_page}'"
                    )
                    log_problematic_case(
                        livre["_id"],
                        titre,
                        titre_page,
                        url_babelio_livre,
                        nom_auteur,
                        "Titre ne correspond pas",
                    )
                    return {
                        "livre_updated": False,
                        "auteur_updated": False,
                        "titre": titre,
                        "auteur": nom_auteur,
                        "status": "not_found",
                    }

                logger.info("✅ Titre validé !")

                # ÉTAPE 3: Mettre à jour le livre dans MongoDB
                if not dry_run:
                    livres_collection.update_one(
                        {"_id": livre["_id"]},
                        {
                            "$set": {
                                "url_babelio": url_babelio_livre,
                                "updated_at": datetime.now(UTC),
                            }
                        },
                    )
                    logger.info("✅ Livre mis à jour dans MongoDB")
                else:
                    logger.info("🔍 [DRY-RUN] Livre SERAIT mis à jour")
                book_updated = True

            except Exception as e:
                logger.error(f"❌ Erreur vérification URL livre: {e}")
                log_problematic_case(
                    livre["_id"],
                    titre,
                    None,
                    url_babelio_livre,
                    nom_auteur,
                    f"Exception: {str(e)}",
                )
                return {
                    "livre_updated": False,
                    "auteur_updated": False,
                    "titre": titre,
                    "auteur": nom_auteur,
                    "status": "error",
                }
        else:
            logger.warning("⚠️  URL Babelio livre manquante dans la réponse")

        # Mettre à jour l'auteur si trouvé
        if auteur and url_babelio_auteur:
            # Vérifier si l'auteur n'a pas déjà une URL
            if not auteur.get("url_babelio"):
                logger.info(f"👤 URL Babelio auteur: {url_babelio_auteur}")

                # Vérification HTTP 200 pour l'URL auteur
                try:
                    # CRITIQUE: Attendre le délai avant la requête HTTP
                    await wait_rate_limit()

                    session = await babelio_service._get_session()
                    async with session.get(url_babelio_auteur) as response:
                        if response.status == 200:
                            logger.info(
                                f"✅ URL auteur vérifiée (HTTP {response.status})"
                            )
                            if not dry_run:
                                auteurs_collection.update_one(
                                    {"_id": auteur["_id"]},
                                    {
                                        "$set": {
                                            "url_babelio": url_babelio_auteur,
                                            "updated_at": datetime.now(UTC),
                                        }
                                    },
                                )
                                logger.info("✅ Auteur mis à jour dans MongoDB")
                            else:
                                logger.info("🔍 [DRY-RUN] Auteur SERAIT mis à jour")
                            author_updated = True
                        else:
                            logger.warning(
                                f"⚠️  URL auteur invalide (HTTP {response.status})"
                            )
                except Exception as e:
                    logger.error(f"❌ Erreur vérification URL auteur: {e}")
            else:
                logger.info(
                    f"ℹ️  Auteur a déjà une URL Babelio: {auteur.get('url_babelio')}"
                )
                # Indiquer que l'auteur était déjà lié (pas une erreur)
                author_already_linked = True
        elif auteur and not url_babelio_auteur:
            logger.warning("⚠️  URL Babelio auteur manquante dans la réponse")
    else:
        # Livre not_found, error, ou autre statut non géré
        status = result.get("status")
        logger.warning(f"❌ Livre non traité (status: {status})")

        # Logger TOUS les cas non-success pour éviter de les re-traiter indéfiniment
        # Ceci inclut: not_found, error, et tout autre statut inattendu
        log_problematic_case(
            livre["_id"],
            titre,
            None,
            "N/A",
            nom_auteur,
            f"Livre non traité - status: {status}",
        )

    # Retourner les infos complètes pour MigrationRunner
    return {
        "livre_updated": book_updated,
        "auteur_updated": author_updated,
        "auteur_already_linked": author_already_linked,
        "titre": titre,
        "auteur": nom_auteur,
        "status": result.get("status", "error"),
    }


async def scrape_author_url_from_book_page(book_url: str) -> str | None:
    """Scrape l'URL auteur depuis la page Babelio d'un livre.

    Args:
        book_url: URL de la page Babelio du livre

    Returns:
        URL de l'auteur ou None si non trouvé

    Example:
        >>> url = await scrape_author_url_from_book_page(
        ...     "https://www.babelio.com/livres/Orwell-1984/1234"
        ... )
        >>> print(url)
        https://www.babelio.com/auteur/George-Orwell/5678
    """
    try:
        # CRITIQUE: Attendre le délai avant la requête HTTP
        await wait_rate_limit()

        # Récupérer le service Babelio pour utiliser sa session HTTP
        from back_office_lmelp.services.babelio_service import BabelioService

        babelio_service = BabelioService()
        session = await babelio_service._get_session()

        async with session.get(book_url) as response:
            if response.status != 200:
                logger.warning(
                    f"⚠️  Erreur HTTP {response.status} lors du scraping de {book_url}"
                )
                return None

            html = await response.text()
            soup = BeautifulSoup(html, "lxml")

            # Chercher le lien auteur dans la page
            # Format: <a href="/auteur/Nom-Prenom/12345" class="...">
            author_link = soup.find("a", href=lambda x: x and "/auteur/" in x)
            if author_link and author_link.get("href"):
                author_path = author_link["href"]
                # Convertir path relatif en URL absolue
                if author_path.startswith("/"):
                    author_url = f"https://www.babelio.com{author_path}"
                    logger.info(f"✅ URL auteur trouvée: {author_url}")
                    return author_url

            logger.warning(f"⚠️  Aucune URL auteur trouvée dans {book_url}")
            return None

    except Exception as e:
        logger.error(f"❌ Erreur lors du scraping de {book_url}: {e}")
        return None


async def get_all_books_to_complete() -> list[dict]:
    """Récupère TOUS les livres dont les auteurs doivent être complétés.

    Approche batch: charge tous les livres en UNE FOIS pour éviter
    de rejouer plusieurs fois sur le même livre en cas d'erreur.

    Returns:
        Liste de dicts avec: livre_id, titre, auteur, auteur_id, url_babelio

    Example:
        >>> books = await get_all_books_to_complete()
        >>> print(len(books))
        15
        >>> print(books[0])
        {
            "livre_id": ObjectId("..."),
            "titre": "1984",
            "auteur": "George Orwell",
            "auteur_id": ObjectId("..."),
            "url_babelio": "https://www.babelio.com/livres/..."
        }
    """
    livres_collection = mongodb_service.get_collection("livres")
    prob_collection = mongodb_service.get_collection("babelio_problematic_cases")

    # Récupérer les IDs de livres déjà loggés comme problématiques
    problematic_cases = prob_collection.find({}, {"livre_id": 1})
    # CRITICAL: Convertir les IDs de STRING vers ObjectId pour le filtre MongoDB
    # log_problematic_case() stocke livre_id en string mais MongoDB _id est ObjectId
    problematic_livre_ids = [ObjectId(case["livre_id"]) for case in problematic_cases]

    # Chercher TOUS les livres qui ont une URL Babelio mais dont l'auteur n'en a pas
    # Pipeline d'aggregation pour joindre livres et auteurs
    pipeline = [
        # Livres avec URL Babelio ET non loggés dans problematic_cases
        {
            "$match": {
                "url_babelio": {"$exists": True, "$ne": None},
                "_id": {"$nin": problematic_livre_ids},
            }
        },
        # Joindre avec auteurs
        {
            "$lookup": {
                "from": "auteurs",
                "localField": "auteur_id",
                "foreignField": "_id",
                "as": "auteur_info",
            }
        },
        # Déplier le tableau auteur_info
        {"$unwind": "$auteur_info"},
        # Filtrer: auteur SANS URL Babelio
        {
            "$match": {
                "$or": [
                    {"auteur_info.url_babelio": {"$exists": False}},
                    {"auteur_info.url_babelio": None},
                ]
            }
        },
        # Pas de limit: récupérer TOUS les livres
    ]

    livre_cursor = livres_collection.aggregate(pipeline)

    # Construire la liste de tous les livres à traiter
    books_to_process = []
    for livre in livre_cursor:
        auteur_info = livre.get("auteur_info", {})
        books_to_process.append(
            {
                "livre_id": livre["_id"],
                "titre": livre.get("titre", "Unknown"),
                "auteur": auteur_info.get("nom", "Unknown"),
                "auteur_id": auteur_info.get("_id"),
                "url_babelio": livre.get("url_babelio"),
            }
        )

    logger.info(f"📋 {len(books_to_process)} livres à traiter en batch")
    return books_to_process


async def get_all_authors_to_complete() -> list[dict]:
    """Récupère TOUS les auteurs sans url_babelio à traiter.

    Pour chaque auteur, récupère aussi ses livres avec leurs détails
    (url_babelio, babelio_not_found) pour pouvoir déterminer comment
    traiter l'auteur.

    Returns:
        Liste de dicts avec:
        {
            "auteur_id": ObjectId,
            "nom": str,
            "livres": [
                {
                    "livre_id": ObjectId,
                    "titre": str,
                    "url_babelio": str | None,
                    "babelio_not_found": bool | None
                }
            ]
        }
    """
    auteurs_collection = mongodb_service.get_collection("auteurs")

    # Pipeline: auteurs sans url_babelio + leurs livres
    pipeline = [
        # Auteurs sans URL Babelio ET pas marqués "not found"
        {
            "$match": {
                "$and": [
                    {
                        "$or": [
                            {"url_babelio": {"$exists": False}},
                            {"url_babelio": None},
                        ]
                    },
                    # Exclure les auteurs marqués "absent de Babelio"
                    {
                        "$or": [
                            {"babelio_not_found": {"$exists": False}},
                            {"babelio_not_found": False},
                        ]
                    },
                ]
            }
        },
        # Joindre avec livres
        {
            "$lookup": {
                "from": "livres",
                "localField": "_id",
                "foreignField": "auteur_id",
                "as": "livres_info",
            }
        },
        # Projeter les champs nécessaires
        {
            "$project": {
                "auteur_id": "$_id",
                "nom": 1,
                "livres": {
                    "$map": {
                        "input": "$livres_info",
                        "as": "livre",
                        "in": {
                            "livre_id": "$$livre._id",
                            "titre": "$$livre.titre",
                            "url_babelio": "$$livre.url_babelio",
                            "babelio_not_found": "$$livre.babelio_not_found",
                        },
                    }
                },
            }
        },
    ]

    auteur_cursor = auteurs_collection.aggregate(pipeline)

    # IMPORTANT: Convertir le curseur en liste pour éviter qu'il soit épuisé
    all_authors = list(auteur_cursor)
    logger.info(f"🔍 {len(all_authors)} auteurs sans URL trouvés dans MongoDB")

    # Récupérer les IDs des auteurs déjà problématiques
    problematic_collection = mongodb_service.get_collection("babelio_problematic_cases")
    problematic_authors = list(problematic_collection.find({"type": "auteur"}))
    problematic_author_ids = {
        ObjectId(doc["auteur_id"]) for doc in problematic_authors if "auteur_id" in doc
    }
    logger.info(
        f"⚠️  {len(problematic_author_ids)} auteurs déjà problématiques à exclure"
    )

    # Construire la liste en excluant les auteurs déjà problématiques
    authors_to_process = []
    for auteur in all_authors:
        auteur_id = auteur.get("auteur_id")
        if auteur_id not in problematic_author_ids:
            authors_to_process.append(auteur)
        else:
            logger.info(
                f"⏭️  Auteur '{auteur.get('nom')}' (ID={auteur_id}) déjà dans problematic_cases, ignoré"
            )

    logger.info(f"📋 {len(authors_to_process)} auteurs à traiter après filtrage")
    return authors_to_process


async def process_one_author(author_data: dict, dry_run: bool = False) -> dict:
    """Traite un auteur sans url_babelio en examinant ses livres.

    Args:
        author_data: Dict avec auteur_id, nom, livres (liste)
        dry_run: Si True, affiche sans modifier

    Returns:
        Dict avec status, auteur_updated, nom_auteur, raison

    Logique:
    1. Si l'auteur a un livre avec url_babelio → scraper l'URL auteur
    2. Si tous les livres sont problématiques → marquer auteur problématique
    3. Si tous les livres sont not_found → marquer auteur absent de Babelio
    4. Si auteur orphelin (pas de livres) → marquer problématique
    """
    auteur_id = author_data["auteur_id"]
    nom_auteur = author_data["nom"]
    livres = author_data["livres"]

    logger.info(f"🔄 Traitement auteur: '{nom_auteur}' ({len(livres)} livres)")

    # Cas 1: Auteur orphelin (pas de livres)
    if not livres:
        logger.warning(
            f"⚠️  Auteur orphelin: '{nom_auteur}' - Logging problematic author"
        )
        log_problematic_author(
            auteur_id=auteur_id,
            nom_auteur=nom_auteur,
            nb_livres=0,
            livres_status="orphelin",
            raison="Auteur sans livres liés",
        )
        return {
            "status": "error",
            "auteur_updated": False,
            "nom_auteur": nom_auteur,
            "raison": "Auteur orphelin (pas de livres)",
        }

    # Chercher un livre avec url_babelio
    livre_avec_url = None
    for livre in livres:
        if livre.get("url_babelio"):
            livre_avec_url = livre
            break

    # Cas 2: Un livre a une url_babelio → scraper l'URL de l'auteur
    if livre_avec_url:
        logger.info(
            f"📚 Livre trouvé avec URL: '{livre_avec_url['titre']}' - "
            f"Scraping URL auteur..."
        )
        await wait_rate_limit()
        author_url = await scrape_author_url_from_book_page(
            livre_avec_url["url_babelio"]
        )

        if author_url is None:
            logger.warning(
                f"❌ Impossible de récupérer l'URL auteur pour '{nom_auteur}' - "
                f"Logging problematic case"
            )
            log_problematic_case(
                livre_id=str(livre_avec_url["livre_id"]),
                titre_attendu=livre_avec_url["titre"],
                titre_trouve=None,
                url_babelio=livre_avec_url["url_babelio"],
                auteur=nom_auteur,
                raison="Impossible de récupérer l'URL de l'auteur depuis la page du livre",
            )
            return {
                "status": "error",
                "auteur_updated": False,
                "nom_auteur": nom_auteur,
                "raison": "Scraping failed",
            }

        # Succès - mettre à jour l'auteur
        if dry_run:
            logger.info(
                f"[DRY RUN] Mettre à jour auteur '{nom_auteur}' avec URL: {author_url}"
            )
            return {
                "status": "success",
                "auteur_updated": False,
                "nom_auteur": nom_auteur,
                "raison": "Dry run",
            }

        auteurs_collection = mongodb_service.get_collection("auteurs")
        result = auteurs_collection.update_one(
            {"_id": auteur_id}, {"$set": {"url_babelio": author_url}}
        )

        if result.matched_count > 0:
            logger.info(f"✅ Auteur '{nom_auteur}' mis à jour avec URL: {author_url}")
            return {
                "status": "success",
                "auteur_updated": True,
                "nom_auteur": nom_auteur,
                "raison": "URL trouvée et mise à jour",
            }
        logger.error(f"❌ Échec mise à jour auteur '{nom_auteur}'")
        return {
            "status": "error",
            "auteur_updated": False,
            "nom_auteur": nom_auteur,
            "raison": "Update failed",
        }

    # Cas 3: Vérifier si tous les livres sont not_found
    all_not_found = all(livre.get("babelio_not_found") for livre in livres)
    if all_not_found:
        logger.warning(
            f"⚠️  Tous les livres de '{nom_auteur}' sont absents de Babelio - "
            f"Logging problematic author (traitement manuel requis)"
        )
        # Ne PAS marquer l'auteur comme not_found car l'auteur peut exister
        # sur Babelio même si ses livres n'y sont pas
        log_problematic_author(
            auteur_id=auteur_id,
            nom_auteur=nom_auteur,
            nb_livres=len(livres),
            livres_status="all_not_found",
            raison=f"Tous les livres sont absents de Babelio: {[livre['titre'] for livre in livres]}",
        )
        return {
            "status": "error",
            "auteur_updated": False,
            "nom_auteur": nom_auteur,
            "raison": "Tous les livres sont absents de Babelio",
        }

    # Cas 4: Livres sont dans problematic_cases ou mix
    logger.warning(
        f"⚠️  Auteur '{nom_auteur}': livres problématiques ou mix - "
        f"Logging problematic author"
    )
    log_problematic_author(
        auteur_id=auteur_id,
        nom_auteur=nom_auteur,
        nb_livres=len(livres),
        livres_status="all_problematic",
        raison=f"Livres problématiques: {[livre['titre'] for livre in livres]}",
    )
    return {
        "status": "error",
        "auteur_updated": False,
        "nom_auteur": nom_auteur,
        "raison": "Livres problématiques",
    }


async def process_one_book_author(book_data: dict, dry_run: bool = False) -> dict:
    """Traite un livre du batch et complète l'URL Babelio de son auteur.

    Cette fonction est appelée pour chaque livre dans la liste retournée
    par get_all_books_to_complete(). Elle ne fait PAS de requête MongoDB
    pour chercher le livre, elle utilise directement les données fournies.

    Args:
        book_data: Dict contenant livre_id, titre, auteur, auteur_id, url_babelio
        dry_run: Si True, affiche les modifications sans les appliquer

    Returns:
        Dict avec status, auteur_updated, titre, auteur

    Example:
        >>> book = {
        ...     "livre_id": ObjectId("..."),
        ...     "titre": "1984",
        ...     "auteur": "George Orwell",
        ...     "auteur_id": ObjectId("..."),
        ...     "url_babelio": "https://www.babelio.com/livres/Orwell-1984/1234"
        ... }
        >>> result = await process_one_book_author(book, dry_run=False)
        >>> result["status"]
        'success'
    """
    livre_id = book_data["livre_id"]
    titre = book_data["titre"]
    auteur = book_data["auteur"]
    auteur_id = book_data["auteur_id"]
    url_babelio = book_data["url_babelio"]

    logger.info(f"🔄 Traitement livre: '{titre}' par {auteur}")

    # Scraper l'URL de l'auteur depuis la page du livre
    await wait_rate_limit()
    author_url = await scrape_author_url_from_book_page(url_babelio)

    if author_url is None:
        # Échec du scraping - logger le cas problématique
        logger.warning(
            f"❌ Impossible de récupérer l'URL auteur pour '{titre}' - "
            f"Logging problematic case"
        )
        log_problematic_case(
            livre_id=str(livre_id),
            titre_attendu=titre,
            titre_trouve=None,
            url_babelio=url_babelio,
            auteur=auteur,
            raison="Impossible de récupérer l'URL de l'auteur depuis la page du livre",
        )
        return {
            "status": "error",
            "auteur_updated": False,
            "titre": titre,
            "auteur": auteur,
        }

    # Succès - mettre à jour l'auteur dans MongoDB
    if dry_run:
        logger.info(f"[DRY RUN] Mettre à jour auteur '{auteur}' avec URL: {author_url}")
        return {
            "status": "success",
            "auteur_updated": False,  # False car pas vraiment mis à jour en dry_run
            "titre": titre,
            "auteur": auteur,
        }

    auteurs_collection = mongodb_service.get_collection("auteurs")
    result = auteurs_collection.update_one(
        {"_id": auteur_id}, {"$set": {"url_babelio": author_url}}
    )

    if result.matched_count > 0:
        logger.info(f"✅ Auteur '{auteur}' mis à jour avec URL: {author_url}")
        return {
            "status": "success",
            "auteur_updated": True,
            "titre": titre,
            "auteur": auteur,
        }
    logger.error(f"❌ Échec mise à jour auteur '{auteur}' (ID: {auteur_id})")
    return {
        "status": "error",
        "auteur_updated": False,
        "titre": titre,
        "auteur": auteur,
    }


async def complete_missing_authors(dry_run: bool = False) -> dict | None:
    """Complète les auteurs manquants pour les livres qui ont déjà une URL Babelio.

    Cette fonction traite les livres qui ont déjà une url_babelio
    mais dont l'auteur n'en a pas encore. Elle scrape la page du livre
    pour récupérer l'URL de l'auteur.

    Args:
        dry_run: Si True, affiche les modifications sans les appliquer

    Returns:
        Dict avec les infos de traitement ou None si aucun auteur à compléter

    Example:
        >>> result = await complete_missing_authors(dry_run=False)
        >>> print(result)
        {
            "auteur_updated": True,
            "titre": "1984",
            "auteur": "George Orwell",
            "status": "success"
        }
    """
    livres_collection = mongodb_service.get_collection("livres")
    auteurs_collection = mongodb_service.get_collection("auteurs")
    prob_collection = mongodb_service.get_collection("babelio_problematic_cases")

    # Récupérer les IDs de livres déjà loggés comme problématiques
    problematic_cases = prob_collection.find({}, {"livre_id": 1})
    # CRITICAL: Convertir les IDs de STRING vers ObjectId pour le filtre MongoDB
    # log_problematic_case() stocke livre_id en string (line 189) mais MongoDB _id est ObjectId
    problematic_livre_ids = [ObjectId(case["livre_id"]) for case in problematic_cases]

    # Chercher un livre qui a une URL Babelio mais dont l'auteur n'en a pas
    # Pipeline d'aggregation pour joindre livres et auteurs
    pipeline = [
        # Livres avec URL Babelio ET non loggés dans problematic_cases
        {
            "$match": {
                "url_babelio": {"$exists": True, "$ne": None},
                "_id": {"$nin": problematic_livre_ids},
            }
        },
        # Joindre avec auteurs
        {
            "$lookup": {
                "from": "auteurs",
                "localField": "auteur_id",
                "foreignField": "_id",
                "as": "auteur_info",
            }
        },
        # Déplier le tableau auteur_info
        {"$unwind": "$auteur_info"},
        # Filtrer: auteur SANS URL Babelio
        {
            "$match": {
                "$or": [
                    {"auteur_info.url_babelio": {"$exists": False}},
                    {"auteur_info.url_babelio": None},
                ]
            }
        },
        # Limiter à 1 résultat
        {"$limit": 1},
    ]

    livre_cursor = livres_collection.aggregate(pipeline)
    livre = None
    for doc in livre_cursor:
        livre = doc
        break

    if not livre:
        logger.info("✅ Aucun auteur à compléter")
        return None

    titre = livre.get("titre", "Unknown")
    auteur_info = livre.get("auteur_info", {})
    nom_auteur = auteur_info.get("nom", "Unknown")
    auteur_id = auteur_info.get("_id")
    url_babelio_livre = livre.get("url_babelio")

    logger.info(f"📚 Livre: {titre} ({nom_auteur})")
    logger.info(f"🔗 URL livre: {url_babelio_livre}")
    logger.info(f"👤 Auteur sans URL Babelio: {nom_auteur}")

    # Scraper la page du livre pour récupérer l'URL auteur
    url_babelio_auteur = await scrape_author_url_from_book_page(url_babelio_livre)

    if not url_babelio_auteur:
        logger.warning("❌ Impossible de récupérer l'URL auteur")
        # Logger le cas problématique pour éviter de le re-traiter en boucle
        log_problematic_case(
            livre["_id"],
            titre,
            None,
            url_babelio_livre,
            nom_auteur,
            "Failed to scrape author URL from book page",
        )
        return {
            "auteur_updated": False,
            "titre": titre,
            "auteur": nom_auteur,
            "status": "error",
        }

    # Mettre à jour l'auteur dans MongoDB
    if not dry_run:
        auteurs_collection.update_one(
            {"_id": auteur_id},
            {
                "$set": {
                    "url_babelio": url_babelio_auteur,
                    "updated_at": datetime.now(UTC),
                }
            },
        )
        logger.info(f"✅ Auteur {nom_auteur} mis à jour avec URL Babelio")
    else:
        logger.info(f"🔍 [DRY-RUN] Auteur SERAIT mis à jour: {url_babelio_auteur}")

    return {
        "auteur_updated": not dry_run,
        "titre": titre,
        "auteur": nom_auteur,
        "status": "success",
    }


async def main():
    """Point d'entrée principal du script de migration."""
    parser = argparse.ArgumentParser(
        description="Backfill URL Babelio pour UN livre et son auteur"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mode dry-run: affiche sans modifier",
    )
    args = parser.parse_args()

    if args.dry_run:
        logger.info("🔍 MODE DRY-RUN ACTIVÉ - Aucune modification ne sera appliquée")

    # Initialiser la connexion MongoDB
    if not mongodb_service.connect():
        logger.error("❌ Impossible de se connecter à MongoDB")
        return

    logger.info("✅ Connexion MongoDB établie")

    # Initialiser le service Babelio
    babelio_service = BabelioService()

    try:
        # Migrer un livre et son auteur
        result = await migrate_one_book_and_author(babelio_service, args.dry_run)

        # Afficher le résumé
        logger.info("\n" + "=" * 60)
        logger.info("RÉSUMÉ DE LA MIGRATION")
        logger.info("=" * 60)
        logger.info(
            f"📚 Livre mis à jour: {'✅ Oui' if result['book_updated'] else '❌ Non'}"
        )
        logger.info(
            f"✍️  Auteur mis à jour: {'✅ Oui' if result['author_updated'] else '❌ Non'}"
        )
        logger.info("=" * 60)

    finally:
        await babelio_service.close()


if __name__ == "__main__":
    asyncio.run(main())
