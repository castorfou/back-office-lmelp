"""Tests pour BabelioMigrationService (Issue #124)."""

import json
from unittest.mock import MagicMock

import pytest

from back_office_lmelp.services.babelio_migration_service import (
    BabelioMigrationService,
)


class TestBabelioMigrationService:
    """Tests pour le service de migration Babelio."""

    @pytest.fixture
    def mock_mongodb_service(self):
        """Mock du service MongoDB."""
        mock = MagicMock()
        mock.db = MagicMock()
        return mock

    @pytest.fixture
    def mock_babelio_service(self):
        """Mock du service Babelio."""
        return MagicMock()

    @pytest.fixture
    def migration_service(self, mock_mongodb_service, mock_babelio_service):
        """Instance du service de migration avec mocks."""
        return BabelioMigrationService(mock_mongodb_service, mock_babelio_service)

    def test_get_problematic_cases_should_exclude_books_already_marked_not_found(
        self, migration_service, mock_mongodb_service
    ):
        """Test TDD: get_problematic_cases() doit exclure les livres avec babelio_not_found=true.

        Problème business réel:
        - La collection MongoDB contient 5 cas problématiques
        - 3 de ces livres ont déjà babelio_not_found: true dans MongoDB
        - Ces 3 livres ne devraient PAS être retournés par get_problematic_cases()
        - Seuls les 2 livres vraiment problématiques devraient être retournés

        Scénario:
        1. Mock MongoDB avec 5 cas problématiques
        2. Mock MongoDB pour dire que 3 ont babelio_not_found: true
        3. Appeler get_problematic_cases()
        4. Vérifier que seuls 2 cas sont retournés (pas les 3 "not found")
        """
        from datetime import UTC, datetime

        from bson import ObjectId

        # Arrange - Mock MongoDB avec 5 cas problématiques
        mock_problematic_collection = MagicMock()
        mock_livres_collection = MagicMock()
        mock_mongodb_service.db.__getitem__.side_effect = lambda name: {
            "babelio_problematic_cases": mock_problematic_collection,
            "livres": mock_livres_collection,
        }[name]

        cases = [
            {
                "_id": ObjectId("674e9a8f1234567890abcde1"),
                "timestamp": datetime(2025, 12, 5, 9, 25, 40, 528467, tzinfo=UTC),
                "livre_id": "6914a45f497dd3ad92041855",
                "titre_attendu": "La Cordillère des ondes",
                "raison": "Titre ne correspond pas",
            },
            {
                "_id": ObjectId("674e9a8f1234567890abcde2"),
                "timestamp": datetime(2025, 12, 5, 9, 28, 10, 362279, tzinfo=UTC),
                "livre_id": "692c8b7fe405566c2a0b869c",
                "titre_attendu": "Cours de poétique",
                "raison": "Titre ne correspond pas",
            },
            {
                "_id": ObjectId("674e9a8f1234567890abcde3"),
                "timestamp": datetime(2025, 12, 5, 21, 47, 22, 849163, tzinfo=UTC),
                "livre_id": "68ec058fc9f430a13dcefe78",
                "titre_attendu": "Sur les lieux de Georges Pérec",
                "raison": "Livre non traité - status: not_found",
            },
            {
                "_id": ObjectId("674e9a8f1234567890abcde4"),
                "timestamp": datetime(2025, 12, 5, 21, 47, 24, 707196, tzinfo=UTC),
                "livre_id": "68ec0746c9f430a13dcefe81",
                "titre_attendu": "Club des Poètes",
                "raison": "Livre non traité - status: not_found",
            },
            {
                "_id": ObjectId("674e9a8f1234567890abcde5"),
                "timestamp": datetime(2025, 12, 5, 21, 47, 26, 486887, tzinfo=UTC),
                "livre_id": "690d91eb2246ccf9a62179bd",
                "titre_attendu": "Bookmakers",
                "raison": "Livre non traité - status: not_found",
            },
        ]

        mock_problematic_collection.find.return_value = cases

        # Mock MongoDB: les 3 derniers ont babelio_not_found=true
        # On utilise une liste pour side_effect pour éviter les problèmes de conversion ObjectId/str
        # L'ordre correspond à l'ordre de la liste 'cases' ci-dessus
        mock_livres_collection.find_one.side_effect = [
            {"_id": cases[0]["livre_id"]},  # Pas de flag
            {"_id": cases[1]["livre_id"]},  # Pas de flag
            {"_id": cases[2]["livre_id"], "babelio_not_found": True},
            {"_id": cases[3]["livre_id"], "babelio_not_found": True},
            {"_id": cases[4]["livre_id"], "babelio_not_found": True},
        ]

        # Act - Appeler get_problematic_cases()
        result = migration_service.get_problematic_cases()

        # Assert - Seuls 2 cas devraient être retournés (pas les 3 "not found")
        assert len(result) == 2, (
            f"Attendu 2 cas problématiques (sans les 3 'not_found'), "
            f"mais reçu {len(result)}"
        )

        # Vérifier que ce sont bien les 2 bons livres
        livre_ids = [case["livre_id"] for case in result]
        assert "6914a45f497dd3ad92041855" in livre_ids  # pragma: allowlist secret
        assert "692c8b7fe405566c2a0b869c" in livre_ids  # pragma: allowlist secret

        # Vérifier que les 3 "not found" ne sont PAS retournés
        assert "68ec058fc9f430a13dcefe78" not in livre_ids  # pragma: allowlist secret
        assert "68ec0746c9f430a13dcefe81" not in livre_ids  # pragma: allowlist secret
        assert "690d91eb2246ccf9a62179bd" not in livre_ids  # pragma: allowlist secret

    def test_get_problematic_cases_should_read_from_mongodb_not_jsonl(
        self, migration_service, mock_mongodb_service
    ):
        """Test TDD: get_problematic_cases() doit lire depuis MongoDB, pas JSONL.

        Problème business réel:
        - Avant: Les cas problématiques étaient stockés dans un fichier JSONL
        - Après: Ils doivent être stockés dans une collection MongoDB
        - Raison: Plus facile à gérer, transactions atomiques, historique

        Scénario:
        1. MongoDB contient 2 documents dans babelio_problematic_cases
        2. Appeler get_problematic_cases()
        3. Vérifier que la méthode retourne les 2 cas depuis MongoDB
        4. Vérifier que la collection babelio_problematic_cases a bien été appelée
        """
        from datetime import UTC, datetime

        # Arrange - Mock de la collection babelio_problematic_cases
        mock_problematic_collection = MagicMock()
        mock_livres_collection = MagicMock()

        # 2 cas dans MongoDB
        mock_problematic_cases = [
            {
                "_id": "mock_id_1",
                "timestamp": datetime.now(UTC),
                "livre_id": "6914a45f497dd3ad92041855",
                "titre_attendu": "La Cordillère des ondes",
                "titre_trouve": "Contes et Légendes des Incas...",
                "url_babelio": "https://www.babelio.com/livres/...",
                "auteur": "Patrice Delbourg",
                "raison": "Titre ne correspond pas",
            },
            {
                "_id": "mock_id_2",
                "timestamp": datetime.now(UTC),
                "livre_id": "692c8b7fe405566c2a0b869c",
                "titre_attendu": "Cours de poétique",
                "titre_trouve": "Naissance de la biopolitique...",
                "url_babelio": "https://www.babelio.com/livres/...",
                "auteur": "Paul Valéry",
                "raison": "Titre ne correspond pas",
            },
        ]

        # Mock find() pour retourner les cas
        mock_problematic_collection.find.return_value = mock_problematic_cases

        # Mock find_one() de livres pour dire qu'aucun n'est résolu
        mock_livres_collection.find_one.return_value = {"_id": "mock_livre_id"}

        # Mock db["babelio_problematic_cases"] et db["livres"]
        def mock_getitem(key):
            if key == "babelio_problematic_cases":
                return mock_problematic_collection
            elif key == "livres":
                return mock_livres_collection
            return MagicMock()

        mock_mongodb_service.db.__getitem__.side_effect = mock_getitem

        # Act - Appeler get_problematic_cases()
        result = migration_service.get_problematic_cases()

        # Assert - Vérifier que la méthode a appelé la bonne collection
        mock_mongodb_service.db.__getitem__.assert_any_call("babelio_problematic_cases")
        mock_problematic_collection.find.assert_called_once()

        # Vérifier que les 2 cas sont retournés
        assert len(result) == 2
        assert result[0]["livre_id"] == "6914a45f497dd3ad92041855"
        assert result[1]["livre_id"] == "692c8b7fe405566c2a0b869c"

    def test_get_migration_status_should_exclude_problematic_from_pending_count(
        self, migration_service, mock_mongodb_service
    ):
        """Test TDD: pending_count doit exclure les cas problématiques.

        Problème business réel:
        - Total: 100 livres
        - Migrés: 70 livres (avec url_babelio)
        - Absents: 20 livres (babelio_not_found: true)
        - Problématiques: 5 livres (dans collection babelio_problematic_cases)
        - Pending ACTUEL: 100 - 70 - 20 = 10 (INCORRECT - inclut les 5 problématiques)
        - Pending ATTENDU: 100 - 70 - 20 - 5 = 5 (CORRECT - exclut les problématiques)

        Scénario:
        1. MongoDB contient 100 livres total
        2. 70 ont url_babelio
        3. 20 ont babelio_not_found: true
        4. 5 sont dans babelio_problematic_cases (non résolus)
        5. Appeler get_migration_status()
        6. Vérifier que pending_count = 5 (pas 10)
        """
        from datetime import UTC, datetime

        # Arrange - Mock des collections
        mock_livres_collection = MagicMock()
        mock_auteurs_collection = MagicMock()
        mock_problematic_collection = MagicMock()

        # Total: 100 livres
        def count_documents_side_effect(query):
            if query == {}:
                return 100  # Total
            elif "url_babelio" in query and "$exists" in query["url_babelio"]:
                return 70  # Migrés
            elif "babelio_not_found" in query:
                return 20  # Absents
            return 0

        mock_livres_collection.count_documents.side_effect = count_documents_side_effect

        # Mock auteurs collection
        def auteurs_count_side_effect(query):
            if query == {}:
                return 50  # total_authors
            elif "url_babelio" in query and "$exists" in query["url_babelio"]:
                return 40  # authors_with_url
            elif "babelio_not_found" in query:
                return 0  # authors_not_found
            return 0

        mock_auteurs_collection.count_documents.side_effect = auteurs_count_side_effect

        # 5 cas problématiques dans MongoDB (non résolus)
        # Note: Les livre_id doivent être des ObjectIds valides (24 caractères hex)
        valid_object_ids = [
            "60a7f1234567890abcdef000",  # pragma: allowlist secret
            "60a7f1234567890abcdef001",  # pragma: allowlist secret
            "60a7f1234567890abcdef002",  # pragma: allowlist secret
            "60a7f1234567890abcdef003",  # pragma: allowlist secret
            "60a7f1234567890abcdef004",  # pragma: allowlist secret
        ]
        mock_problematic_cases = [
            {
                "_id": f"mock_id_{i}",
                "timestamp": datetime.now(UTC),
                "livre_id": valid_object_ids[i],
                "titre_attendu": f"Titre {i}",
                "raison": "Test",
            }
            for i in range(5)
        ]
        mock_problematic_collection.find.return_value = mock_problematic_cases

        # Mock count_documents for problematic collection (5 livres, 0 auteurs)
        def problematic_count_side_effect(query):
            if query.get("type") == "livre":
                return 5
            elif query.get("type") == "auteur":
                return 0
            return 0

        mock_problematic_collection.count_documents.side_effect = (
            problematic_count_side_effect
        )

        # Mock find_one pour dire qu'aucun n'est résolu
        from bson import ObjectId

        mock_livres_collection.find_one.return_value = {
            "_id": ObjectId("507f1f77bcf86cd799439011")  # pragma: allowlist secret
        }

        # Mock db collections
        def mock_getitem(key):
            collections = {
                "livres": mock_livres_collection,
                "auteurs": mock_auteurs_collection,
                "babelio_problematic_cases": mock_problematic_collection,
            }
            return collections.get(key, MagicMock())

        mock_mongodb_service.db.__getitem__.side_effect = mock_getitem

        # Act - Appeler get_migration_status()
        result = migration_service.get_migration_status()

        # Assert - Vérifier que pending_count exclut les problématiques
        assert result["total_books"] == 100
        assert result["migrated_count"] == 70
        assert result["not_found_count"] == 20
        assert result["problematic_count"] == 5

        # LE TEST CRITIQUE: pending_count doit être 5, pas 10
        assert result["pending_count"] == 5, (
            f"pending_count devrait être 5 (100 - 70 - 20 - 5), "
            f"mais reçu {result['pending_count']}"
        )

    def test_mark_as_not_found_should_remove_from_mongodb_collection(
        self, migration_service, mock_mongodb_service
    ):
        """Test TDD: mark_as_not_found() doit retirer de la collection MongoDB.

        Problème business réel:
        - Un livre est dans la collection babelio_problematic_cases
        - L'utilisateur le marque comme "pas sur Babelio"
        - Le livre doit être retiré de babelio_problematic_cases
        - Le livre doit avoir babelio_not_found: true dans livres

        Scénario:
        1. Livre existe dans collection livres
        2. Appeler mark_as_not_found(livre_id, reason)
        3. Vérifier que livres.update_one a été appelé avec babelio_not_found: true
        4. Vérifier que babelio_problematic_cases.delete_one a été appelé
        """
        from bson import ObjectId

        # Arrange
        livre_id = "6914a45f497dd3ad92041855"  # pragma: allowlist secret
        reason = "Livre trop ancien, pas référencé sur Babelio"

        mock_livres_collection = MagicMock()
        mock_problematic_collection = MagicMock()

        # Mock update_one pour retourner matched_count = 1 (succès)
        mock_update_result = MagicMock()
        mock_update_result.matched_count = 1
        mock_livres_collection.update_one.return_value = mock_update_result

        # Mock delete_one pour retourner deleted_count = 1 (succès)
        mock_delete_result = MagicMock()
        mock_delete_result.deleted_count = 1
        mock_problematic_collection.delete_one.return_value = mock_delete_result

        # Mock db collections
        def mock_getitem(key):
            if key == "livres":
                return mock_livres_collection
            elif key == "babelio_problematic_cases":
                return mock_problematic_collection
            return MagicMock()

        mock_mongodb_service.db.__getitem__.side_effect = mock_getitem

        # Act
        result = migration_service.mark_as_not_found(livre_id, reason)

        # Assert - Vérifier que l'opération a réussi
        assert result is True

        # Vérifier que livres.update_one a été appelé avec les bons arguments
        mock_livres_collection.update_one.assert_called_once()
        call_args = mock_livres_collection.update_one.call_args
        assert call_args[0][0] == {"_id": ObjectId(livre_id)}  # Filter
        assert call_args[0][1]["$set"]["babelio_not_found"] is True
        assert call_args[0][1]["$set"]["babelio_not_found_reason"] == reason

        # CRITIQUE: Vérifier que babelio_problematic_cases.delete_one a été appelé
        mock_problematic_collection.delete_one.assert_called_once_with(
            {"livre_id": livre_id}
        )

    def test_correct_title_should_update_livre_and_remove_from_problematic(
        self, migration_service, mock_mongodb_service
    ):
        """Test TDD: correct_title() doit mettre à jour le titre et retirer de problematic.

        Problème business réel:
        - Un livre a un titre incorrect dans MongoDB
        - Il est dans babelio_problematic_cases car la recherche a échoué
        - L'utilisateur corrige le titre manuellement
        - Le livre doit être mis à jour avec le nouveau titre
        - Le livre doit être retiré de babelio_problematic_cases
        - Le livre redevient éligible pour migration automatique

        Scénario:
        1. Appeler correct_title(livre_id, new_title)
        2. Vérifier que livres.update_one a été appelé avec le nouveau titre
        3. Vérifier que babelio_problematic_cases.delete_one a été appelé
        4. Vérifier que la méthode retourne True
        """
        from bson import ObjectId

        # Arrange
        livre_id = "6914a45f497dd3ad92041855"  # pragma: allowlist secret
        new_title = "La Cordillère des ondes"  # Titre corrigé

        mock_livres_collection = MagicMock()
        mock_problematic_collection = MagicMock()

        # Mock update_one pour retourner matched_count = 1 (succès)
        mock_update_result = MagicMock()
        mock_update_result.matched_count = 1
        mock_livres_collection.update_one.return_value = mock_update_result

        # Mock delete_one
        mock_delete_result = MagicMock()
        mock_delete_result.deleted_count = 1
        mock_problematic_collection.delete_one.return_value = mock_delete_result

        # Mock db collections
        def mock_getitem(key):
            if key == "livres":
                return mock_livres_collection
            elif key == "babelio_problematic_cases":
                return mock_problematic_collection
            return MagicMock()

        mock_mongodb_service.db.__getitem__.side_effect = mock_getitem

        # Act
        result = migration_service.correct_title(livre_id, new_title)

        # Assert
        assert result is True

        # Vérifier que livres.update_one a été appelé avec le bon titre
        mock_livres_collection.update_one.assert_called_once()
        call_args = mock_livres_collection.update_one.call_args
        assert call_args[0][0] == {"_id": ObjectId(livre_id)}
        assert call_args[0][1]["$set"]["titre"] == new_title
        assert "updated_at" in call_args[0][1]["$set"]

        # Vérifier que le livre a été retiré de problematic_cases
        mock_problematic_collection.delete_one.assert_called_once_with(
            {"livre_id": livre_id}
        )

    def test_get_problematic_cases_should_return_json_serializable_data(
        self, mock_mongodb_service
    ):
        """Test que get_problematic_cases() retourne des données sérialisables en JSON.

        Les ObjectId et datetime doivent être convertis en strings pour Pydantic/FastAPI.
        """
        # GIVEN: Des cas problématiques avec ObjectId et datetime dans MongoDB
        mock_db = MagicMock()
        mock_mongodb_service.db = mock_db

        mock_problematic_collection = MagicMock()
        mock_livres_collection = MagicMock()
        mock_db.__getitem__.side_effect = lambda name: {
            "babelio_problematic_cases": mock_problematic_collection,
            "livres": mock_livres_collection,
        }[name]

        # Cas avec ObjectId et datetime (comme MongoDB les retourne)
        from datetime import UTC, datetime

        from bson import ObjectId

        livre_id_1 = "692c8b7fe405566c2a0b869c"
        auteur_id_1 = ObjectId("507f1f77bcf86cd799439011")
        timestamp_1 = datetime(2025, 12, 5, 9, 28, 10, 362279, tzinfo=UTC)

        mock_problematic_collection.find.return_value = [
            {
                "_id": ObjectId("674e9a8f1234567890abcdef"),
                "timestamp": timestamp_1,
                "livre_id": livre_id_1,
                "titre_attendu": "Cours de poétique",
                "titre_trouve": "Naissance de la biopolitique",
                "url_babelio": "https://www.babelio.com/livres/Foucault-Naissance/3580",
                "auteur_attendu": "Paul Valéry",
                "auteur_trouve": "Michel Foucault",
                "auteur_id": auteur_id_1,
                "url_babelio_auteur": "https://www.babelio.com/auteur/Michel-Foucault/2958",
                "raison": "Titre ne correspond pas",
            }
        ]

        # Livre non résolu (pas de babelio_not_found, pas d'url_babelio)
        mock_livres_collection.find_one.return_value = {
            "_id": ObjectId(livre_id_1),
            "titre": "Cours de poétique",
            "babelio_not_found": False,
        }

        service = BabelioMigrationService(mock_mongodb_service, MagicMock())

        # WHEN: On récupère les cas problématiques
        cases = service.get_problematic_cases()

        # THEN: Les données doivent être sérialisables en JSON
        assert len(cases) == 1
        case = cases[0]

        # _id doit être une string, pas ObjectId
        assert isinstance(case["_id"], str)
        assert case["_id"] == "674e9a8f1234567890abcdef"

        # timestamp doit être une string ISO, pas datetime
        assert isinstance(case["timestamp"], str)
        assert case["timestamp"] == "2025-12-05T09:28:10.362279+00:00"

        # auteur_id doit être une string, pas ObjectId
        assert isinstance(case["auteur_id"], str)
        assert case["auteur_id"] == "507f1f77bcf86cd799439011"

        # Les autres champs doivent rester inchangés
        assert case["livre_id"] == livre_id_1
        assert case["titre_attendu"] == "Cours de poétique"
        assert case["auteur_attendu"] == "Paul Valéry"

        # Vérifier que le résultat est sérialisable en JSON

        try:
            json.dumps(cases)
        except TypeError as e:
            pytest.fail(f"Cases not JSON serializable: {e}")
