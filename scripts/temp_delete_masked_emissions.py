#!/usr/bin/env python3
"""
Script temporaire pour supprimer les émissions correspondant aux épisodes masqués.

Contexte: Après l'ajout du filtre masked=True dans auto-conversion,
il reste 2 émissions en base qui correspondent à des épisodes masqués.

Ce script:
1. Trouve les épisodes avec masked=True
2. Trouve les émissions correspondant à ces épisodes
3. Supprime ces émissions de la collection
4. Affiche un rapport détaillé

Usage:
    python scripts/temp_delete_masked_emissions.py
"""

import sys
from pathlib import Path


# Ajouter le chemin src au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from back_office_lmelp.services.mongodb_service import MongoDBService


def main():
    """Supprime les émissions correspondant aux épisodes masqués."""
    print("=" * 70)
    print("SCRIPT: Suppression des émissions pour épisodes masqués")
    print("=" * 70)

    # Connexion MongoDB
    service = MongoDBService()
    if not service.connect():
        print("\n❌ Erreur: Impossible de se connecter à MongoDB")
        return

    # 1. Trouver les épisodes masqués
    print("\n[1/4] Recherche des épisodes masqués...")
    masked_episodes = list(service.episodes_collection.find({"masked": True}))
    print(f"   ✓ Trouvé {len(masked_episodes)} épisode(s) masqué(s)")

    if len(masked_episodes) == 0:
        print("\n⚠️  Aucun épisode masqué trouvé. Rien à supprimer.")
        return

    # Afficher les épisodes masqués
    print("\n   Détails des épisodes masqués:")
    masked_episode_ids = []
    for ep in masked_episodes:
        masked_episode_ids.append(ep["_id"])
        date_str = ep.get("date", "").strftime("%Y-%m-%d") if ep.get("date") else "N/A"
        print(f"     - {ep.get('titre', 'Sans titre')} ({date_str}) [ID: {ep['_id']}]")

    # 2. Trouver les émissions correspondantes
    print("\n[2/4] Recherche des émissions associées...")
    emissions_to_delete = list(
        service.emissions_collection.find({"episode_id": {"$in": masked_episode_ids}})
    )
    print(f"   ✓ Trouvé {len(emissions_to_delete)} émission(s) à supprimer")

    if len(emissions_to_delete) == 0:
        print("\n✓ Aucune émission à supprimer. Base déjà propre.")
        return

    # Afficher les émissions à supprimer
    print("\n   Détails des émissions à supprimer:")
    emission_ids_to_delete = []
    for em in emissions_to_delete:
        emission_ids_to_delete.append(em["_id"])
        date_str = em.get("date", "").strftime("%Y-%m-%d") if em.get("date") else "N/A"
        print(
            f"     - Émission {date_str} [ID: {em['_id']}, Episode ID: {em['episode_id']}]"
        )

    # 3. Demander confirmation
    print("\n[3/4] Confirmation de suppression...")
    print(f"\n⚠️  Vous allez supprimer {len(emissions_to_delete)} émission(s).")
    response = input("   Confirmer la suppression ? (oui/non): ").strip().lower()

    if response not in ["oui", "o", "yes", "y"]:
        print("\n❌ Suppression annulée par l'utilisateur.")
        return

    # 4. Supprimer les émissions
    print("\n[4/4] Suppression des émissions...")
    result = service.emissions_collection.delete_many(
        {"_id": {"$in": emission_ids_to_delete}}
    )

    print(f"   ✓ {result.deleted_count} émission(s) supprimée(s)")

    # Vérification finale
    print("\n" + "=" * 70)
    print("RÉSUMÉ")
    print("=" * 70)
    remaining_emissions = service.emissions_collection.count_documents({})
    print(f"Émissions restantes en base: {remaining_emissions}")
    print(f"Émissions supprimées: {result.deleted_count}")
    print("\n✅ Opération terminée avec succès!")
    print("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Opération interrompue par l'utilisateur.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Erreur: {e}")
        sys.exit(1)
