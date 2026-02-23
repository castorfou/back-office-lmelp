"""
Script de migration: fusionne Eric Neuhoff (doublon) → Éric Neuhoff (primaire).

Bug #226: deux entrées critiques pour le même critique, créées parce que
normalize_critique_name() n'était pas insensible aux accents:
- "eric neuhoff" != "éric neuhoff" → nouvelle entrée créée au lieu de matcher l'existante

Logique:
- Primary (à conserver): "Éric Neuhoff" id=695679b0b49e0e1c6b6e3161 (6 avis)
- Duplicate (à supprimer): "Eric Neuhoff" id=695433bcea74a1c06226cd73 (18 avis)

Note: on garde celui qui a le plus d'avis comme primaire.
Ici c'est "Eric Neuhoff" (18 avis) qui a le plus d'avis,
mais on choisit "Éric Neuhoff" comme nom canonique (avec accent correct).
→ On migre les avis vers "Éric Neuhoff" et on supprime "Eric Neuhoff".

Actions:
1. Vérifier que les deux critiques existent
2. Afficher les counts d'avis
3. Migrer tous les avis de "Eric Neuhoff" → "Éric Neuhoff"
4. Supprimer le doublon "Eric Neuhoff" de la collection critiques
"""

import os

from bson import ObjectId
from pymongo import MongoClient


# Le projet utilise MONGODB_URL (avec database dans l'URI)
MONGO_URI = os.getenv(
    "MONGODB_URL",
    os.getenv("MONGODB_URI", "mongodb://localhost:27018/masque_et_la_plume"),
)
DB_NAME = "masque_et_la_plume"

# "Éric Neuhoff" → nom canonique avec accent (primaire, à conserver)
PRIMARY_ID = "695679b0b49e0e1c6b6e3161"
# "Eric Neuhoff" → doublon sans accent (à supprimer)
DUPLICATE_ID = "695433bcea74a1c06226cd73"


def main() -> None:
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]

    # Step 1: Vérifier que les deux critiques existent
    primary = db.critiques.find_one({"_id": ObjectId(PRIMARY_ID)})
    duplicate = db.critiques.find_one({"_id": ObjectId(DUPLICATE_ID)})

    if not primary:
        print(f"ERREUR: Primaire non trouvé: {PRIMARY_ID}")
        print("Le merge a peut-être déjà été effectué.")
        return

    if not duplicate:
        print(f"ERREUR: Doublon non trouvé: {DUPLICATE_ID}")
        print("Le merge a peut-être déjà été effectué.")
        return

    print(f"Primaire (à conserver): {primary['nom']} (id={PRIMARY_ID})")
    print(f"Doublon (à supprimer): {duplicate['nom']} (id={DUPLICATE_ID})")

    # Step 2: Afficher les counts d'avis
    primary_avis_count = db.avis.count_documents({"critique_oid": PRIMARY_ID})
    duplicate_avis_count = db.avis.count_documents({"critique_oid": DUPLICATE_ID})
    print("\nAvis actuels:")
    print(f"  {primary['nom']}: {primary_avis_count} avis")
    print(f"  {duplicate['nom']}: {duplicate_avis_count} avis")
    print(f"  Total après merge: {primary_avis_count + duplicate_avis_count} avis")

    # Step 3: Migrer les avis du doublon vers le primaire
    # Note: avis.critique_oid est de type String (pas ObjectId)
    result = db.avis.update_many(
        {"critique_oid": DUPLICATE_ID},
        {"$set": {"critique_oid": PRIMARY_ID}},
    )
    print(f"\nMigration: {result.modified_count} avis migrés vers {primary['nom']}")

    # Step 4: Supprimer le doublon
    db.critiques.delete_one({"_id": ObjectId(DUPLICATE_ID)})
    print(f"Suppression: doublon '{duplicate['nom']}' supprimé")

    # Vérification finale
    final_count = db.avis.count_documents({"critique_oid": PRIMARY_ID})
    print(f"\nVérification finale: {primary['nom']} a maintenant {final_count} avis")
    orphan_count = db.avis.count_documents({"critique_oid": DUPLICATE_ID})
    print(f"Avis orphelins (critique_oid={DUPLICATE_ID}): {orphan_count}")

    print("\nDone.")
    client.close()


if __name__ == "__main__":
    main()
