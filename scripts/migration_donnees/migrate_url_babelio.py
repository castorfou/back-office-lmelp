#!/usr/bin/env python3
"""Script de migration pour backfill les URL Babelio (Issue #124).

Ce script met à jour UN livre et son auteur correspondant pour ajouter
le champ url_babelio en utilisant l'API Babelio.

Usage:
    PYTHONPATH=/workspaces/back-office-lmelp/src python scripts/migrate_url_babelio.py [--dry-run]

Options:
    --dry-run    Affiche les modifications sans les appliquer
"""

import argparse
import asyncio
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path


# Ajouter le chemin src au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from back_office_lmelp.services.babelio_service import BabelioService
from back_office_lmelp.services.mongodb_service import mongodb_service


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def migrate_one_book_and_author(
    babelio_service: BabelioService, dry_run: bool = False
) -> dict[str, bool]:
    """Migre UN livre et son auteur pour ajouter url_babelio.

    Args:
        babelio_service: Instance du service Babelio
        dry_run: Si True, affiche sans modifier

    Returns:
        Statut de la migration {book_updated, author_updated}
    """
    logger.info("🔍 Recherche d'un livre sans URL Babelio...")

    livres_collection = mongodb_service.get_collection("livres")
    auteurs_collection = mongodb_service.get_collection("auteurs")

    # Trouver UN livre sans url_babelio
    livre = livres_collection.find_one(
        {"$or": [{"url_babelio": None}, {"url_babelio": {"$exists": False}}]}
    )

    if not livre:
        logger.info("✅ Tous les livres ont déjà une URL Babelio")
        return {"book_updated": False, "author_updated": False}

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
    result = await babelio_service.verify_book(titre, nom_auteur)

    book_updated = False
    author_updated = False

    # Traiter le résultat pour le livre
    if result.get("status") in ["verified", "corrected"]:
        url_babelio_livre = result.get("babelio_url")
        url_babelio_auteur = result.get("babelio_author_url")

        if url_babelio_livre:
            logger.info(f"📖 URL Babelio livre: {url_babelio_livre}")

            # Vérification HTTP 200 pour l'URL livre
            try:
                session = await babelio_service._get_session()
                async with session.get(url_babelio_livre) as response:
                    if response.status == 200:
                        logger.info(f"✅ URL livre vérifiée (HTTP {response.status})")
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
                    else:
                        logger.warning(
                            f"⚠️  URL livre invalide (HTTP {response.status})"
                        )
            except Exception as e:
                logger.error(f"❌ Erreur vérification URL livre: {e}")
        else:
            logger.warning("⚠️  URL Babelio livre manquante dans la réponse")

        # Mettre à jour l'auteur si trouvé
        if auteur and url_babelio_auteur:
            # Vérifier si l'auteur n'a pas déjà une URL
            if not auteur.get("url_babelio"):
                logger.info(f"👤 URL Babelio auteur: {url_babelio_auteur}")

                # Vérification HTTP 200 pour l'URL auteur
                try:
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
        elif auteur and not url_babelio_auteur:
            logger.warning("⚠️  URL Babelio auteur manquante dans la réponse")
    else:
        logger.warning(
            f"❌ Livre non trouvé sur Babelio (status: {result.get('status')})"
        )

    return {"book_updated": book_updated, "author_updated": author_updated}


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
