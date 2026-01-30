"""Migration pour enrichir les avis existants avec le champ 'editeur' depuis MongoDB.

CONTEXTE:
- Les avis créés avant le fix d'enrichissement (Issue #185) n'ont pas le champ 'editeur'
- Ils contiennent seulement 'editeur_extrait' (depuis le summary, avec fautes possibles)
- Cette migration ajoute le champ 'editeur' depuis les livres MongoDB

USAGE:
    python -m back_office_lmelp.utils.migrate_enrich_avis_editeur

CRITÈRES:
- Ne migre QUE les avis avec livre_oid (matchés)
- Skip les avis déjà avec le champ 'editeur' (idempotence)
- Ne touche PAS aux avis sans livre_oid (non matchés)
"""

import logging

from bson import ObjectId

from ..services.mongodb_service import MongoDBService


logger = logging.getLogger(__name__)


def migrate_enrich_avis_with_editeur() -> int:
    """
    Enrichit les avis existants avec le champ 'editeur' depuis MongoDB.

    Returns:
        Nombre d'avis mis à jour
    """
    mongodb_service = MongoDBService()
    mongodb_service.connect()  # Établir la connexion MongoDB
    avis_collection = mongodb_service.get_collection("avis")
    livres_collection = mongodb_service.get_collection("livres")

    # Trouver tous les avis matchés SANS le champ 'editeur'
    query = {
        "livre_oid": {"$ne": None},  # Avis matchés seulement
        "editeur": {"$exists": False},  # Sans champ editeur (créés avant fix)
    }

    avis_to_update = list(avis_collection.find(query))
    logger.info(f"📊 Trouvé {len(avis_to_update)} avis à enrichir")

    updated_count = 0

    # Grouper par livre_oid pour optimiser les requêtes MongoDB
    livres_cache: dict[str, dict] = {}

    for avis in avis_to_update:
        livre_oid = avis.get("livre_oid")

        if not livre_oid:
            continue

        # Récupérer le livre depuis le cache ou MongoDB
        if livre_oid not in livres_cache:
            try:
                livre = livres_collection.find_one({"_id": ObjectId(livre_oid)})
                if livre:
                    livres_cache[livre_oid] = livre
                else:
                    logger.warning(
                        f"⚠️ Livre non trouvé pour livre_oid={livre_oid}, skip avis {avis['_id']}"
                    )
                    continue
            except Exception as e:
                logger.error(
                    f"❌ Erreur lors de la récupération du livre {livre_oid}: {e}"
                )
                continue

        livre = livres_cache[livre_oid]
        editeur = livre.get("editeur", "")

        # Mettre à jour l'avis avec le champ editeur
        try:
            result = avis_collection.update_one(
                {"_id": avis["_id"]}, {"$set": {"editeur": editeur}}
            )

            if result.modified_count > 0:
                updated_count += 1
                logger.debug(f"✅ Avis {avis['_id']} enrichi avec editeur='{editeur}'")
        except Exception as e:
            logger.error(
                f"❌ Erreur lors de la mise à jour de l'avis {avis['_id']}: {e}"
            )
            continue

    logger.info(f"✅ Migration terminée: {updated_count} avis mis à jour")
    return updated_count


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )
    migrate_enrich_avis_with_editeur()
