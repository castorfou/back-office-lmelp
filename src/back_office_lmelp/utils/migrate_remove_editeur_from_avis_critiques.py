"""Script de migration pour supprimer le champ 'editeur' de la collection avis_critiques.

Ce script corrige le bug de l'Issue #174 où le champ 'editeur' était ajouté à tort
dans la collection avis_critiques lors de l'enrichissement Babelio sur la page /livres-auteurs.

Le champ 'editeur' appartient uniquement à la collection 'livres', PAS à 'avis_critiques'.

Usage:
    PYTHONPATH=/workspaces/back-office-lmelp/src python -m back_office_lmelp.utils.migrate_remove_editeur_from_avis_critiques
"""

from back_office_lmelp.services.mongodb_service import mongodb_service


def remove_editeur_from_avis_critiques() -> None:
    """Supprime le champ 'editeur' de tous les documents de avis_critiques.

    Cette migration est safe car :
    1. Le champ 'editeur' dans avis_critiques n'est jamais lu par le code
    2. L'éditeur est déjà stocké correctement dans la collection 'livres'
    3. L'éditeur est visible dans le 'summary' (markdown) de l'avis_critique
    4. L'opération $unset est atomique et ne nécessite pas d'arrêt du backend
    """
    # Établir la connexion MongoDB
    if not mongodb_service.connect():
        print("❌ Erreur: Impossible de se connecter à MongoDB")
        return

    collection = mongodb_service.avis_critiques_collection

    if collection is None:
        print("❌ Erreur: Collection avis_critiques non disponible")
        return

    # Compter combien de documents ont le champ 'editeur'
    count_with_editeur = collection.count_documents({"editeur": {"$exists": True}})
    print(f"📊 {count_with_editeur} avis_critiques contiennent le champ 'editeur'")

    if count_with_editeur == 0:
        print("✅ Aucun document à migrer")
        return

    # Afficher quelques exemples avant migration
    print("\n📋 Exemples de documents affectés :")
    sample_docs = collection.find({"editeur": {"$exists": True}}).limit(3)
    for idx, doc in enumerate(sample_docs, 1):
        episode_title = doc.get("episode_title", "N/A")
        editeur_value = doc.get("editeur", "N/A")
        print(f"  {idx}. Episode: {episode_title}, editeur: {editeur_value}")

    # Supprimer le champ 'editeur' de tous les documents
    print(f"\n🔧 Suppression du champ 'editeur' dans {count_with_editeur} documents...")
    result = collection.update_many(
        {"editeur": {"$exists": True}},
        {"$unset": {"editeur": ""}},  # $unset supprime le champ
    )

    print(f"✅ {result.modified_count} documents mis à jour")

    # Vérification post-migration
    remaining = collection.count_documents({"editeur": {"$exists": True}})
    if remaining == 0:
        print("✅ Migration réussie : plus aucun champ 'editeur' dans avis_critiques")
    else:
        print(f"⚠️ {remaining} documents ont encore le champ 'editeur'")


if __name__ == "__main__":
    print("=" * 70)
    print("Migration: Suppression du champ 'editeur' de avis_critiques (Issue #174)")
    print("=" * 70)
    remove_editeur_from_avis_critiques()
    print("\n" + "=" * 70)
    print("Migration terminée")
    print("=" * 70)
