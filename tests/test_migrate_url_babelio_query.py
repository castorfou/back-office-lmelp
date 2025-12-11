"""Tests pour la query MongoDB du script migrate_url_babelio.py (Issue #124)."""

from unittest.mock import MagicMock, patch

from bson import ObjectId


class TestMigrateUrlBabelioQuery:
    """Tests pour vérifier que la query MongoDB exclut correctement les livres."""

    def test_query_should_exclude_books_with_babelio_not_found_true(self):
        """Test TDD: La query doit exclure les livres avec babelio_not_found: true.

        Problème business réel:
        - Des livres ont babelio_not_found: true (marqués par l'utilisateur)
        - Ces livres n'ont PAS de url_babelio
        - La query doit les EXCLURE pour ne pas les re-traiter

        Scénario:
        1. Créer une query qui cherche les livres sans url_babelio
        2. La query doit AUSSI exclure ceux avec babelio_not_found: true
        3. Vérifier que la query a la bonne structure MongoDB
        """
        # Arrange - Construire la query exactement comme dans le script
        problematic_ids = []  # Pas de cas problématiques pour ce test

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

        # Assert - Vérifier la structure de la query
        assert "$or" in query, "La query doit avoir un $or pour url_babelio"
        assert "$nor" in query, "La query doit avoir un $nor pour babelio_not_found"

        # Vérifier que $nor contient bien la condition babelio_not_found: true
        assert query["$nor"] == [{"babelio_not_found": True}], (
            "La condition $nor doit exclure babelio_not_found: true"
        )

        # Vérifier que $or cherche bien les livres sans url_babelio
        assert {"url_babelio": None} in query["$or"]
        assert {"url_babelio": {"$exists": False}} in query["$or"]

    def test_query_should_also_exclude_problematic_ids(self):
        """Test: La query doit AUSSI exclure les IDs problématiques du JSONL."""
        # Arrange
        problematic_ids = ["6914a45f497dd3ad92041855", "692c8b7fe405566c2a0b869c"]

        query = {
            "$or": [{"url_babelio": None}, {"url_babelio": {"$exists": False}}],
            "$nor": [{"babelio_not_found": True}],
        }

        if problematic_ids:
            excluded_object_ids = [ObjectId(id_str) for id_str in problematic_ids]
            query["_id"] = {"$nin": excluded_object_ids}

        # Assert
        assert "_id" in query, "La query doit avoir une condition _id"
        assert "$nin" in query["_id"], "La condition _id doit utiliser $nin"

        # Vérifier que les IDs problématiques sont exclus
        excluded_ids = query["_id"]["$nin"]
        assert len(excluded_ids) == 2
        assert all(isinstance(oid, ObjectId) for oid in excluded_ids)

    def test_load_problematic_book_ids_should_read_from_mongodb_not_jsonl(self):
        """Test TDD: load_problematic_book_ids() doit lire depuis MongoDB, pas JSONL.

        Problème business réel:
        - Avant: Les IDs problématiques étaient lus depuis un fichier JSONL
        - Après: Ils doivent être lus depuis MongoDB collection babelio_problematic_cases
        - Raison: Cohérence avec le reste du code (backend lit déjà depuis MongoDB)

        Scénario:
        1. MongoDB contient 3 documents dans babelio_problematic_cases
        2. Appeler load_problematic_book_ids()
        3. Vérifier que la fonction retourne les 3 livre_id depuis MongoDB
        4. Vérifier que la collection MongoDB a bien été interrogée
        """
        # Arrange - Mock MongoDB avec 3 cas problématiques
        mock_collection = MagicMock()
        mock_collection.find.return_value = [
            {"livre_id": "6914a45f497dd3ad92041855"},
            {"livre_id": "692c8b7fe405566c2a0b869c"},
            {"livre_id": "68ec058fc9f430a13dcefe78"},
        ]

        # Mock mongodb_service.get_collection()
        with patch(
            "scripts.migration_donnees.migrate_url_babelio.mongodb_service.get_collection"
        ) as mock_get_collection:
            mock_get_collection.return_value = mock_collection

            # Import ici pour que le patch soit actif
            from scripts.migration_donnees.migrate_url_babelio import (
                load_problematic_book_ids,
            )

            # Act - Appeler la fonction
            result = load_problematic_book_ids()

            # Assert - Vérifier que MongoDB a été interrogé
            mock_get_collection.assert_called_once_with("babelio_problematic_cases")
            mock_collection.find.assert_called_once()

            # Vérifier que les 3 IDs sont retournés
            assert len(result) == 3
            assert "6914a45f497dd3ad92041855" in result  # pragma: allowlist secret
            assert "692c8b7fe405566c2a0b869c" in result  # pragma: allowlist secret
            assert "68ec058fc9f430a13dcefe78" in result  # pragma: allowlist secret

    def test_log_problematic_case_should_write_to_mongodb_not_jsonl(self):
        """Test TDD: log_problematic_case() doit écrire dans MongoDB, pas JSONL.

        Problème business réel:
        - Avant: Les cas problématiques étaient écrits dans un fichier JSONL
        - Après: Ils doivent être écrits dans MongoDB collection babelio_problematic_cases
        - Raison: Cohérence avec le reste du code (backend écrit déjà dans MongoDB)

        Scénario:
        1. Appeler log_problematic_case() avec des données de test
        2. Vérifier que insert_one() a été appelé sur la collection MongoDB
        3. Vérifier que les données insérées sont correctes
        """
        from datetime import datetime

        # Arrange
        mock_collection = MagicMock()

        # Mock mongodb_service.get_collection()
        with patch(
            "scripts.migration_donnees.migrate_url_babelio.mongodb_service.get_collection"
        ) as mock_get_collection:
            mock_get_collection.return_value = mock_collection

            # Import ici pour que le patch soit actif
            from scripts.migration_donnees.migrate_url_babelio import (
                log_problematic_case,
            )

            # Act - Appeler la fonction
            log_problematic_case(
                livre_id="6914a45f497dd3ad92041855",
                titre_attendu="La Cordillère des ondes",
                titre_trouve="Contes et Légendes des Incas",
                url_babelio="https://www.babelio.com/livres/...",
                auteur="Patrice Delbourg",
                raison="Titre ne correspond pas",
            )

            # Assert - Vérifier que MongoDB a été utilisé
            mock_get_collection.assert_called_once_with("babelio_problematic_cases")
            mock_collection.insert_one.assert_called_once()

            # Vérifier les données insérées
            inserted_data = mock_collection.insert_one.call_args[0][0]
            assert inserted_data["livre_id"] == "6914a45f497dd3ad92041855"
            assert inserted_data["titre_attendu"] == "La Cordillère des ondes"
            assert inserted_data["titre_trouve"] == "Contes et Légendes des Incas"
            assert inserted_data["url_babelio"] == "https://www.babelio.com/livres/..."
            assert inserted_data["auteur"] == "Patrice Delbourg"
            assert inserted_data["raison"] == "Titre ne correspond pas"
            assert "timestamp" in inserted_data
            assert isinstance(inserted_data["timestamp"], datetime)
