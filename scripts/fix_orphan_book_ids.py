#!/usr/bin/env python3
"""
Script de détection et correction des book_id orphelins dans livresauteurs_cache.

Issue #187: Après fusion de doublons, le cache peut contenir des book_id
qui pointent vers des livres supprimés.

Ce script:
1. Détecte toutes les entrées du cache avec book_id orphelins
2. Pour chaque orphelin, cherche le livre correct par titre/auteur
3. Corrige automatiquement les entrées ou signale les cas problématiques

Usage:
    # Mode dry-run (détection seulement)
    python scripts/fix_orphan_book_ids.py --dry-run

    # Mode correction
    python scripts/fix_orphan_book_ids.py
"""

import argparse
import re
import sys
import unicodedata
from datetime import UTC, datetime

from pymongo import MongoClient


def normalize_text(text: str) -> str:
    """Normalise le texte pour comparaison (accents, casse, ponctuation)."""
    if not text:
        return ""
    # Décompose les caractères accentués
    text = unicodedata.normalize("NFD", text)
    # Supprime les accents
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    # Minuscules
    text = text.lower()
    # Supprime la ponctuation et espaces multiples
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def find_matching_book(db, titre: str, auteur: str) -> dict | None:
    """
    Cherche un livre correspondant par titre et auteur.

    Stratégie de recherche multi-niveaux:
    1. Recherche par mots-clés significatifs (min 4 caractères)
    2. Recherche par premier mot significatif + auteur
    3. Recherche élargie par auteur seul si nom long
    """
    livres = db["livres"]
    auteurs = db["auteurs"]

    # Normalise le titre pour recherche
    titre_norm = normalize_text(titre)
    auteur_norm = normalize_text(auteur)

    # Extraire les mots significatifs (>=4 caractères, pas les mots courants)
    stop_words = {"dans", "avec", "pour", "sans", "sous", "vers", "chez", "tome"}
    words = [w for w in titre_norm.split() if len(w) >= 4 and w not in stop_words]

    candidates = []

    # Stratégie 1: Recherche par tous les mots significatifs
    if words:
        regex_pattern = ".*".join(re.escape(word) for word in words)
        candidates = list(
            livres.find({"titre": {"$regex": regex_pattern, "$options": "i"}})
        )

    # Stratégie 2: Recherche par premier mot significatif seulement
    if not candidates and words:
        first_word = words[0]
        if len(first_word) >= 5:  # Mot assez long pour être discriminant
            candidates = list(
                livres.find(
                    {"titre": {"$regex": re.escape(first_word), "$options": "i"}}
                )
            )

    # Stratégie 3: Recherche par sous-chaîne du titre (pour titres partiels)
    if not candidates and len(titre_norm) >= 8:
        # Chercher les livres dont le titre contient notre recherche
        candidates = list(
            livres.find({"titre": {"$regex": re.escape(titre_norm), "$options": "i"}})
        )

    # Stratégie 3b: Recherche par dernier mot significatif (pour sous-titres)
    if not candidates and words and len(words[-1]) >= 6:
        last_word = words[-1]
        candidates = list(
            livres.find({"titre": {"$regex": re.escape(last_word), "$options": "i"}})
        )

    # Stratégie 4: Recherche par auteur si nom significatif
    if not candidates and len(auteur_norm) >= 5:
        # Chercher l'auteur d'abord
        author_words = [w for w in auteur_norm.split() if len(w) >= 4]
        if author_words:
            author_regex = ".*".join(re.escape(w) for w in author_words)
            matching_authors = list(
                auteurs.find({"nom": {"$regex": author_regex, "$options": "i"}})
            )
            if matching_authors:
                author_ids = [a["_id"] for a in matching_authors]
                candidates = list(livres.find({"auteur_id": {"$in": author_ids}}))

    if not candidates:
        return None

    if len(candidates) == 1:
        return candidates[0]

    # Plusieurs candidats: scorer par similarité titre + auteur
    best_match = None
    best_score = 0

    for book in candidates:
        score = 0
        book_titre_norm = normalize_text(book.get("titre", ""))

        # Score basé sur les mots en commun dans le titre
        book_words = set(book_titre_norm.split())
        title_words = set(titre_norm.split())
        common_words = book_words & title_words
        score += len(common_words) * 2

        # Score basé sur l'auteur
        author_doc = auteurs.find_one({"_id": book.get("auteur_id")})
        if author_doc:
            author_name_norm = normalize_text(author_doc.get("nom", ""))
            author_words_set = set(auteur_norm.split())
            author_book_words = set(author_name_norm.split())
            common_author = author_words_set & author_book_words
            score += len(common_author) * 3  # L'auteur compte plus

        if score > best_score:
            best_score = score
            best_match = book

    return best_match


def detect_orphans(db) -> list[dict]:
    """Détecte toutes les entrées du cache avec book_id orphelins."""
    pipeline = [
        {"$match": {"status": "mongo", "book_id": {"$exists": True}}},
        {
            "$lookup": {
                "from": "livres",
                "localField": "book_id",
                "foreignField": "_id",
                "as": "livre",
            }
        },
        {"$match": {"livre": {"$size": 0}}},
        {
            "$project": {
                "_id": 1,
                "titre": 1,
                "auteur": 1,
                "book_id": 1,
                "episode_oid": 1,
            }
        },
    ]
    return list(db["livresauteurs_cache"].aggregate(pipeline))


def fix_orphans(db, dry_run: bool = True) -> dict:
    """
    Détecte et corrige les book_id orphelins.

    Returns:
        {
            "total_orphans": int,
            "fixed": int,
            "skipped": int,
            "errors": list[str],
            "details": list[dict]
        }
    """
    orphans = detect_orphans(db)
    cache = db["livresauteurs_cache"]

    results = {
        "total_orphans": len(orphans),
        "fixed": 0,
        "skipped": 0,
        "errors": [],
        "details": [],
    }

    print(f"\n{'=' * 60}")
    print("🔍 Détection des book_id orphelins")
    print(f"{'=' * 60}")
    print(f"Total orphelins trouvés: {len(orphans)}\n")

    for orphan in orphans:
        titre = orphan.get("titre", "")
        auteur = orphan.get("auteur", "")
        cache_id = orphan["_id"]
        old_book_id = orphan.get("book_id")

        print(f"📚 {titre} - {auteur}")
        print(f"   Cache ID: {cache_id}")
        print(f"   Book ID orphelin: {old_book_id}")

        # Cas spéciaux à ignorer
        if titre in ["Aucun", "[Titre à venir]", ""]:
            print("   ⏭️  Ignoré (titre invalide)")
            results["skipped"] += 1
            results["details"].append(
                {
                    "cache_id": str(cache_id),
                    "titre": titre,
                    "status": "skipped",
                    "reason": "Titre invalide",
                }
            )
            print()
            continue

        # Chercher le livre correct
        matching_book = find_matching_book(db, titre, auteur)

        if not matching_book:
            print("   ❌ Aucun livre correspondant trouvé")
            results["errors"].append(f"{titre} - {auteur}: Livre non trouvé")
            results["details"].append(
                {
                    "cache_id": str(cache_id),
                    "titre": titre,
                    "status": "error",
                    "reason": "Livre non trouvé",
                }
            )
            print()
            continue

        new_book_id = matching_book["_id"]
        print(f"   ✓ Livre trouvé: {matching_book.get('titre')}")
        print(f"   → Nouveau book_id: {new_book_id}")

        if dry_run:
            print("   🔵 [DRY-RUN] Correction simulée")
            results["fixed"] += 1
        else:
            result = cache.update_one(
                {"_id": cache_id},
                {
                    "$set": {
                        "book_id": new_book_id,
                        "updated_at": datetime.now(UTC),
                    }
                },
            )
            if result.modified_count > 0:
                print("   ✅ Corrigé!")
                results["fixed"] += 1
            else:
                print("   ⚠️  Déjà à jour")
                results["skipped"] += 1

        results["details"].append(
            {
                "cache_id": str(cache_id),
                "titre": titre,
                "old_book_id": str(old_book_id),
                "new_book_id": str(new_book_id),
                "status": "fixed" if not dry_run else "dry-run",
            }
        )
        print()

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Détection et correction des book_id orphelins"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mode simulation (pas de modifications)",
    )
    parser.add_argument(
        "--mongo-uri",
        default="mongodb://localhost:27018/masque_et_la_plume",
        help="URI MongoDB",
    )
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("🔧 Script de correction des book_id orphelins (Issue #187)")
    print("=" * 60)

    if args.dry_run:
        print("⚠️  MODE DRY-RUN: Aucune modification ne sera effectuée")

    client = MongoClient(args.mongo_uri)
    db = client["masque_et_la_plume"]

    results = fix_orphans(db, dry_run=args.dry_run)

    print("=" * 60)
    print("📊 RÉSUMÉ")
    print("=" * 60)
    print(f"Total orphelins: {results['total_orphans']}")
    print(f"Corrigés: {results['fixed']}")
    print(f"Ignorés: {results['skipped']}")
    print(f"Erreurs: {len(results['errors'])}")

    if results["errors"]:
        print("\n⚠️  Erreurs:")
        for error in results["errors"]:
            print(f"   - {error}")

    if args.dry_run and results["fixed"] > 0:
        print("\n💡 Pour appliquer les corrections, relancez sans --dry-run")

    return 0 if not results["errors"] else 1


if __name__ == "__main__":
    sys.exit(main())
