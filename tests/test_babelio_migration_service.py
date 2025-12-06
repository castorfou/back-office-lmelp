"""Tests pour BabelioMigrationService (Issue #124)."""

import json
from unittest.mock import MagicMock, patch

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
        self, migration_service, mock_mongodb_service, tmp_path
    ):
        """Test TDD: get_problematic_cases() doit exclure les livres avec babelio_not_found=true.

        Problème business réel:
        - Le fichier JSONL contient 5 livres problématiques
        - 3 de ces livres ont déjà babelio_not_found: true dans MongoDB
        - Ces 3 livres ne devraient PAS être retournés par get_problematic_cases()
        - Seuls les 2 livres vraiment problématiques devraient être retournés

        Scénario:
        1. Créer un fichier JSONL avec 5 cas problématiques
        2. Mock MongoDB pour dire que 3 ont babelio_not_found: true
        3. Appeler get_problematic_cases()
        4. Vérifier que seuls 2 cas sont retournés (pas les 3 "not found")
        """
        # Arrange - Créer un fichier JSONL temporaire
        temp_jsonl = tmp_path / "migration_problematic_cases.jsonl"
        cases = [
            {
                "timestamp": "2025-12-05T09:25:40.528467+00:00",
                "livre_id": "6914a45f497dd3ad92041855",
                "titre_attendu": "La Cordillère des ondes",
                "raison": "Titre ne correspond pas",
            },
            {
                "timestamp": "2025-12-05T09:28:10.362279+00:00",
                "livre_id": "692c8b7fe405566c2a0b869c",
                "titre_attendu": "Cours de poétique",
                "raison": "Titre ne correspond pas",
            },
            {
                "timestamp": "2025-12-05T21:47:22.849163+00:00",
                "livre_id": "68ec058fc9f430a13dcefe78",
                "titre_attendu": "Sur les lieux de Georges Pérec",
                "raison": "Livre non traité - status: not_found",
            },
            {
                "timestamp": "2025-12-05T21:47:24.707196+00:00",
                "livre_id": "68ec0746c9f430a13dcefe81",
                "titre_attendu": "Club des Poètes",
                "raison": "Livre non traité - status: not_found",
            },
            {
                "timestamp": "2025-12-05T21:47:26.486887+00:00",
                "livre_id": "690d91eb2246ccf9a62179bd",
                "titre_attendu": "Bookmakers",
                "raison": "Livre non traité - status: not_found",
            },
        ]

        with open(temp_jsonl, "w", encoding="utf-8") as f:
            for case in cases:
                f.write(json.dumps(case) + "\n")

        # Mock MongoDB: les 3 derniers ont babelio_not_found=true

        def mock_find_one(filter_dict):
            livre_id_str = str(filter_dict["_id"])
            # Les 3 derniers livres ont babelio_not_found: true
            if livre_id_str in [
                "68ec058fc9f430a13dcefe78",  # pragma: allowlist secret
                "68ec0746c9f430a13dcefe81",  # pragma: allowlist secret
                "690d91eb2246ccf9a62179bd",  # pragma: allowlist secret
            ]:
                return {"_id": filter_dict["_id"], "babelio_not_found": True}
            # Les 2 premiers n'ont pas le flag
            return {"_id": filter_dict["_id"]}

        mock_mongodb_service.db["livres"].find_one.side_effect = mock_find_one

        # Act - Appeler get_problematic_cases() avec le fichier temporaire
        with patch(
            "back_office_lmelp.services.babelio_migration_service.PROBLEMATIC_CASES_FILE",
            temp_jsonl,
        ):
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
