#!/usr/bin/env python3
"""
Script exploratoire pour analyser une bibliothèque Calibre.

Ce script interroge la base Calibre pour :
1. Vérifier la connexion
2. Compter les livres
3. Afficher les métadonnées d'exemples
4. Lister les colonnes personnalisées disponibles
5. Analyser la structure des données

Usage:
    python scripts/explore_calibre.py /chemin/vers/Calibre Library

Ou avec variable d'environnement:
    CALIBRE_LIBRARY_PATH="/chemin/vers/Calibre Library" python scripts/explore_calibre.py

Le script charge automatiquement le fichier .env à la racine du projet.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv


def main():
    # Charger les variables d'environnement depuis .env
    dotenv_path = Path(__file__).parent.parent / ".env"
    if dotenv_path.exists():
        load_dotenv(dotenv_path)
        print(f"✅ Fichier .env chargé depuis {dotenv_path}\n")

    # Récupérer le chemin de la bibliothèque
    if len(sys.argv) > 1:
        library_path = sys.argv[1]
    else:
        library_path = os.environ.get("CALIBRE_LIBRARY_PATH")

    if not library_path:
        print("❌ Erreur: Aucun chemin de bibliothèque fourni")
        print("\nUsage:")
        print("  python scripts/explore_calibre.py /chemin/vers/Calibre Library")
        print("  ou")
        print(
            '  CALIBRE_LIBRARY_PATH="/chemin/vers/Calibre Library" python scripts/explore_calibre.py'
        )
        sys.exit(1)

    # Vérifier que le chemin existe
    lib_path = Path(library_path)
    if not lib_path.exists():
        print(f"❌ Erreur: Le chemin {library_path} n'existe pas")
        sys.exit(1)

    if not lib_path.is_dir():
        print(f"❌ Erreur: {library_path} n'est pas un dossier")
        sys.exit(1)

    # Vérifier metadata.db
    metadata_file = lib_path / "metadata.db"
    if not metadata_file.exists():
        print(f"❌ Erreur: {library_path} ne contient pas metadata.db")
        print("Ce n'est pas une bibliothèque Calibre valide")
        sys.exit(1)

    print("=" * 70)
    print("EXPLORATION DE LA BIBLIOTHÈQUE CALIBRE")
    print("=" * 70)
    print(f"\n📂 Chemin: {library_path}")
    print(f"📄 Fichier metadata: {metadata_file}")
    print()

    # Importer Calibre
    try:
        from calibre.library import db

        print("✅ Module calibre.library importé avec succès")
    except ImportError as e:
        print(f"❌ Erreur d'import Calibre: {str(e)}")
        print("\n💡 Pour installer Calibre:")
        print("   pip install calibre")
        sys.exit(1)

    # Connexion à la bibliothèque
    try:
        library = db(library_path)
        print("✅ Connexion à la bibliothèque réussie\n")
    except Exception as e:
        print(f"❌ Erreur de connexion: {str(e)}")
        sys.exit(1)

    try:
        # Statistiques générales
        print("-" * 70)
        print("STATISTIQUES GÉNÉRALES")
        print("-" * 70)

        book_ids = library.all_book_ids()
        total_books = len(book_ids)
        print(f"📚 Nombre total de livres: {total_books}")

        # Analyser les colonnes personnalisées
        print("\n" + "-" * 70)
        print("COLONNES PERSONNALISÉES DISPONIBLES")
        print("-" * 70)

        custom_columns = library.field_metadata.custom_field_metadata()
        if custom_columns:
            print(f"\n✅ {len(custom_columns)} colonnes personnalisées trouvées:\n")
            for col_id, col_info in custom_columns.items():
                print(f"  • {col_id}")
                print(f"    - Label: {col_info.get('name', 'N/A')}")
                print(f"    - Type: {col_info.get('datatype', 'N/A')}")
                print(
                    f"    - Description: {col_info.get('display', {}).get('description', 'N/A')}"
                )
                print()
        else:
            print("ℹ️  Aucune colonne personnalisée trouvée")

        # Analyser les champs standards disponibles
        print("-" * 70)
        print("CHAMPS STANDARDS DISPONIBLES")
        print("-" * 70)

        all_fields = library.field_metadata
        standard_fields = {
            key: value for key, value in all_fields.items() if not key.startswith("#")
        }

        print(f"\n✅ {len(standard_fields)} champs standards:\n")
        interesting_fields = [
            "title",
            "authors",
            "isbn",
            "tags",
            "rating",
            "publisher",
            "pubdate",
            "series",
            "comments",
            "languages",
        ]

        for field in interesting_fields:
            if field in standard_fields:
                field_info = standard_fields[field]
                print(f"  • {field}: {field_info.get('datatype', 'unknown')}")

        # Afficher des exemples de livres
        print("\n" + "-" * 70)
        print("EXEMPLES DE LIVRES (5 premiers)")
        print("-" * 70)

        num_examples = min(5, total_books)
        for i, book_id in enumerate(book_ids[:num_examples], 1):
            metadata = library.get_metadata(book_id)

            print(f"\n📖 Livre {i} (ID: {book_id})")
            print(f"   Titre: {metadata.title}")
            print(
                f"   Auteur(s): {', '.join(metadata.authors) if metadata.authors else 'N/A'}"
            )
            print(f"   ISBN: {metadata.isbn or 'N/A'}")
            print(f"   Éditeur: {metadata.publisher or 'N/A'}")
            print(f"   Date de publication: {metadata.pubdate or 'N/A'}")
            print(f"   Note: {metadata.rating or 'N/A'}")
            print(f"   Tags: {', '.join(metadata.tags) if metadata.tags else 'N/A'}")
            print(f"   Série: {metadata.series or 'N/A'}")

            # Afficher les colonnes personnalisées pour ce livre
            if custom_columns:
                print("   Colonnes personnalisées:")
                for col_id in custom_columns:
                    try:
                        value = metadata.get(col_id)
                        if value is not None:
                            print(f"     - {col_id}: {value}")
                    except Exception:
                        pass

        # Analyse des métadonnées utiles pour LMELP
        print("\n" + "-" * 70)
        print("ANALYSE POUR INTÉGRATION LMELP")
        print("-" * 70)

        # Compter les livres avec ISBN
        books_with_isbn = sum(
            1 for book_id in book_ids if library.get_metadata(book_id).isbn
        )
        print(
            f"\n📊 Livres avec ISBN: {books_with_isbn}/{total_books} ({books_with_isbn / total_books * 100:.1f}%)"
        )

        # Compter les livres avec notes
        books_with_rating = sum(
            1 for book_id in book_ids if library.get_metadata(book_id).rating
        )
        print(
            f"⭐ Livres avec note: {books_with_rating}/{total_books} ({books_with_rating / total_books * 100:.1f}%)"
        )

        # Compter les livres avec tags
        books_with_tags = sum(
            1 for book_id in book_ids if library.get_metadata(book_id).tags
        )
        print(
            f"🏷️  Livres avec tags: {books_with_tags}/{total_books} ({books_with_tags / total_books * 100:.1f}%)"
        )

        # Analyser les tags uniques
        all_tags = set()
        for book_id in book_ids:
            metadata = library.get_metadata(book_id)
            if metadata.tags:
                all_tags.update(metadata.tags)

        print(f"🏷️  Tags uniques: {len(all_tags)}")
        if all_tags:
            print(f"   Exemples: {', '.join(list(all_tags)[:10])}")

        # Recommandations pour l'intégration
        print("\n" + "-" * 70)
        print("RECOMMANDATIONS POUR L'INTÉGRATION")
        print("-" * 70)

        print("\n✅ Champs utilisables immédiatement:")
        print("   • title, authors (pour affichage et recherche)")
        print("   • isbn (pour liaison avec MongoDB et Babelio)")
        print("   • rating (pour comparaison avec critiques LMELP)")
        print("   • tags (pour catégorisation)")
        print("   • publisher, pubdate (métadonnées enrichies)")

        if custom_columns:
            print("\n📋 Colonnes personnalisées à vérifier:")
            for col_id in custom_columns:
                print(f"   • {col_id} - à mapper selon vos besoins")

        if books_with_isbn / total_books < 0.8:
            print("\n⚠️  Note: Beaucoup de livres sans ISBN")
            print(
                "   → Utiliser matching fuzzy Titre+Auteur pour liaison MongoDB/Babelio"
            )

        print("\n💡 Prochaines étapes:")
        print("   1. Vérifier les colonnes personnalisées pour 'Lu', 'Date lecture'")
        print("   2. Tester les requêtes de performance sur votre bibliothèque")
        print("   3. Définir la stratégie de cache (5min TTL recommandé)")
        print("   4. Implémenter l'API backend avec les champs identifiés")

    finally:
        # Fermeture propre
        library.close()
        print("\n" + "=" * 70)
        print("✅ Exploration terminée - Bibliothèque fermée proprement")
        print("=" * 70)


if __name__ == "__main__":
    main()
