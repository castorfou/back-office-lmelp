"""Tests for fixture updater service and endpoint."""

from pathlib import Path
from tempfile import TemporaryDirectory

import yaml
from fastapi.testclient import TestClient

from back_office_lmelp.app import app
from back_office_lmelp.services.fixture_updater import FixtureUpdaterService


client = TestClient(app)


class TestFixtureUpdaterEndpoint:
    """Tests for /api/update-fixtures endpoint."""

    def test_update_fixtures_endpoint_accepts_captured_calls(self):
        """L'endpoint doit accepter des appels capturés valides."""
        captured_calls = [
            {
                "service": "babelioService",
                "method": "verifyAuthor",
                "input": {"name": "Emmanuel Carrère"},
                "output": {"status": "verified", "original": "Emmanuel Carrère"},
                "timestamp": 1234567890,
            }
        ]

        response = client.post("/api/update-fixtures", json={"calls": captured_calls})

        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_update_fixtures_validates_input(self):
        """L'endpoint doit valider le format des appels capturés."""
        invalid_calls = [{"invalid": "data"}]

        response = client.post("/api/update-fixtures", json={"calls": invalid_calls})

        assert response.status_code == 422  # Validation error

    def test_update_fixtures_requires_calls_field(self):
        """L'endpoint doit exiger le champ 'calls'."""
        response = client.post("/api/update-fixtures", json={})

        assert response.status_code == 422

    def test_update_fixtures_returns_proper_response_format(self):
        """L'endpoint doit retourner le format de réponse attendu."""
        captured_calls = [
            {
                "service": "babelioService",
                "method": "verifyAuthor",
                "input": {"name": "Test Author"},
                "output": {"status": "verified"},
                "timestamp": 1234567890,
            }
        ]

        response = client.post("/api/update-fixtures", json={"calls": captured_calls})

        assert response.status_code == 200
        data = response.json()

        assert "success" in data
        assert "updated_files" in data
        assert "added_cases" in data
        assert "updated_cases" in data
        assert isinstance(data["updated_files"], list)
        assert isinstance(data["added_cases"], int)
        assert isinstance(data["updated_cases"], int)


class TestFixtureUpdaterService:
    """Tests for FixtureUpdaterService."""

    def test_fixture_updater_creates_yaml_files(self):
        """Le service doit créer/mettre à jour les fichiers YAML."""
        with TemporaryDirectory() as temp_dir:
            updater = FixtureUpdaterService(fixtures_dir=Path(temp_dir))

            captured_calls = [
                {
                    "service": "babelioService",
                    "method": "verifyAuthor",
                    "input": {"name": "Test Author"},
                    "output": {"status": "verified"},
                    "timestamp": 1234567890,
                }
            ]

            result = updater.update_from_captured_calls(captured_calls)

            assert "babelio-author-cases.yml" in result.updated_files
            assert result.added_cases == 1

            # Vérifier que le fichier existe et contient les bonnes données
            yaml_file = Path(temp_dir) / "babelio-author-cases.yml"
            assert yaml_file.exists()

            with open(yaml_file) as f:
                data = yaml.safe_load(f)
                assert len(data["cases"]) >= 1
                assert data["cases"][-1]["input"]["name"] == "Test Author"

    def test_fixture_updater_handles_book_calls(self):
        """Le service doit traiter les appels de vérification de livres."""
        with TemporaryDirectory() as temp_dir:
            updater = FixtureUpdaterService(fixtures_dir=Path(temp_dir))

            captured_calls = [
                {
                    "service": "babelioService",
                    "method": "verifyBook",
                    "input": {"title": "Test Book", "author": "Test Author"},
                    "output": {"status": "verified"},
                    "timestamp": 1234567890,
                }
            ]

            result = updater.update_from_captured_calls(captured_calls)

            assert "babelio-book-cases.yml" in result.updated_files
            assert result.added_cases == 1

    def test_fixture_updater_handles_fuzzy_search_calls(self):
        """Le service doit traiter les appels de recherche floue."""
        with TemporaryDirectory() as temp_dir:
            updater = FixtureUpdaterService(fixtures_dir=Path(temp_dir))

            captured_calls = [
                {
                    "service": "fuzzySearchService",
                    "method": "searchEpisode",
                    "input": {"query": "test query"},
                    "output": {"results": []},
                    "timestamp": 1234567890,
                }
            ]

            result = updater.update_from_captured_calls(captured_calls)

            assert "fuzzy-search-cases.yml" in result.updated_files
            assert result.added_cases == 1

    def test_fixture_updater_prevents_duplicates(self):
        """Le service doit éviter les doublons dans les fixtures."""
        with TemporaryDirectory() as temp_dir:
            updater = FixtureUpdaterService(fixtures_dir=Path(temp_dir))

            # Créer un fichier existant avec un cas
            yaml_file = Path(temp_dir) / "babelio-author-cases.yml"
            existing_data = {
                "cases": [
                    {
                        "input": {"name": "Test Author"},
                        "output": {"status": "verified"},
                        "timestamp": 1234567890,
                    }
                ]
            }
            with open(yaml_file, "w") as f:
                yaml.dump(existing_data, f)

            # Essayer d'ajouter le même cas
            captured_calls = [
                {
                    "service": "babelioService",
                    "method": "verifyAuthor",
                    "input": {"name": "Test Author"},
                    "output": {"status": "verified"},
                    "timestamp": 1234567890,
                }
            ]

            result = updater.update_from_captured_calls(captured_calls)

            # Aucun nouveau cas ne devrait être ajouté
            assert result.added_cases == 0
            assert result.updated_cases == 0

    def test_fixture_updater_updates_existing_case_if_different(self):
        """Le service doit mettre à jour un cas existant si la sortie diffère."""
        with TemporaryDirectory() as temp_dir:
            updater = FixtureUpdaterService(fixtures_dir=Path(temp_dir))

            # Créer un fichier existant avec un cas
            yaml_file = Path(temp_dir) / "babelio-author-cases.yml"
            existing_data = {
                "cases": [
                    {
                        "input": {"name": "Test Author"},
                        "output": {"status": "not_found"},
                        "timestamp": 1234567890,
                    }
                ]
            }
            with open(yaml_file, "w") as f:
                yaml.dump(existing_data, f)

            # Ajouter le même cas avec une sortie différente
            captured_calls = [
                {
                    "service": "babelioService",
                    "method": "verifyAuthor",
                    "input": {"name": "Test Author"},
                    "output": {"status": "verified"},
                    "timestamp": 1234567890,
                }
            ]

            result = updater.update_from_captured_calls(captured_calls)

            # Le cas existant devrait être mis à jour
            assert result.added_cases == 0
            assert result.updated_cases == 1

            # Vérifier que le fichier a été mis à jour
            with open(yaml_file) as f:
                data = yaml.safe_load(f)
                assert data["cases"][0]["output"]["status"] == "verified"
