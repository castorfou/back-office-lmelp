"""Tests for refresh-babelio and apply-refresh endpoints (Issue #189)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from back_office_lmelp.app import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


class TestRefreshBabelioPreview:
    """Tests pour POST /api/livres/{livre_id}/refresh-babelio."""

    @patch("back_office_lmelp.app.babelio_service")
    @patch("back_office_lmelp.app.mongodb_service")
    def test_returns_comparison_data(self, mock_mongodb, mock_babelio, client):
        """Le preview retourne les données actuelles vs Babelio."""
        livre_id = str(ObjectId())
        auteur_id = ObjectId()

        # Mock livre doc
        mock_mongodb.livres_collection = MagicMock()
        mock_mongodb.livres_collection.find_one.return_value = {
            "_id": ObjectId(livre_id),
            "titre": "Ancien Titre",
            "auteur_id": auteur_id,
            "editeur": "POL",
            "url_babelio": "https://www.babelio.com/livres/Test/12345",
        }

        # Mock auteur doc
        mock_mongodb.auteurs_collection = MagicMock()
        mock_mongodb.auteurs_collection.find_one.return_value = {
            "_id": auteur_id,
            "nom": "Ancien Auteur",
            "url_babelio": None,
        }

        # Mock Babelio scraping methods
        mock_babelio.fetch_full_title_from_url = AsyncMock(return_value="Nouveau Titre")
        mock_babelio.fetch_publisher_from_url = AsyncMock(return_value="P.O.L")
        mock_babelio.fetch_author_url_from_page = AsyncMock(
            return_value="https://www.babelio.com/auteur/Auteur/999"
        )
        mock_babelio._scrape_author_from_book_page = AsyncMock(
            return_value="Nouveau Auteur"
        )

        response = client.post(f"/api/livres/{livre_id}/refresh-babelio")

        assert response.status_code == 200
        data = response.json()
        assert data["current"]["titre"] == "Ancien Titre"
        assert data["current"]["editeur"] == "POL"
        assert data["current"]["auteur_nom"] == "Ancien Auteur"
        assert data["babelio"]["titre"] == "Nouveau Titre"
        assert data["babelio"]["editeur"] == "P.O.L"
        assert data["babelio"]["auteur_nom"] == "Nouveau Auteur"
        assert data["changes_detected"] is True

    @patch("back_office_lmelp.app.babelio_service")
    @patch("back_office_lmelp.app.mongodb_service")
    def test_returns_404_when_livre_not_found(self, mock_mongodb, mock_babelio, client):
        """Retourne 404 si le livre n'existe pas."""
        livre_id = str(ObjectId())
        mock_mongodb.livres_collection = MagicMock()
        mock_mongodb.livres_collection.find_one.return_value = None

        response = client.post(f"/api/livres/{livre_id}/refresh-babelio")

        assert response.status_code == 404

    @patch("back_office_lmelp.app.babelio_service")
    @patch("back_office_lmelp.app.mongodb_service")
    def test_returns_400_when_no_url_babelio(self, mock_mongodb, mock_babelio, client):
        """Retourne 400 si le livre n'a pas d'url_babelio."""
        livre_id = str(ObjectId())
        mock_mongodb.livres_collection = MagicMock()
        mock_mongodb.livres_collection.find_one.return_value = {
            "_id": ObjectId(livre_id),
            "titre": "Test",
            "auteur_id": ObjectId(),
            "editeur": "Test",
        }

        response = client.post(f"/api/livres/{livre_id}/refresh-babelio")

        assert response.status_code == 400

    @patch("back_office_lmelp.app.babelio_service")
    @patch("back_office_lmelp.app.mongodb_service")
    def test_changes_detected_false_when_identical(
        self, mock_mongodb, mock_babelio, client
    ):
        """changes_detected est False quand les données sont identiques ET editeur_id existe."""
        livre_id = str(ObjectId())
        auteur_id = ObjectId()
        editeur_id = ObjectId()

        mock_mongodb.livres_collection = MagicMock()
        mock_mongodb.livres_collection.find_one.return_value = {
            "_id": ObjectId(livre_id),
            "titre": "Même Titre",
            "auteur_id": auteur_id,
            "editeur_id": editeur_id,  # editeur_id existe -> déjà migré
            "url_babelio": "https://www.babelio.com/livres/Test/12345",
        }
        # Mock editeurs collection pour résoudre editeur_id -> nom
        mock_mongodb.editeurs_collection = MagicMock()
        mock_mongodb.editeurs_collection.find_one.return_value = {
            "_id": editeur_id,
            "nom": "Gallimard",
        }
        mock_mongodb.auteurs_collection = MagicMock()
        mock_mongodb.auteurs_collection.find_one.return_value = {
            "_id": auteur_id,
            "nom": "Même Auteur",
            "url_babelio": "https://www.babelio.com/auteur/Auteur/999",
        }

        # Babelio returns same data
        mock_babelio.fetch_full_title_from_url = AsyncMock(return_value="Même Titre")
        mock_babelio.fetch_publisher_from_url = AsyncMock(return_value="Gallimard")
        mock_babelio.fetch_author_url_from_page = AsyncMock(
            return_value="https://www.babelio.com/auteur/Auteur/999"
        )
        mock_babelio._scrape_author_from_book_page = AsyncMock(
            return_value="Même Auteur"
        )

        response = client.post(f"/api/livres/{livre_id}/refresh-babelio")

        assert response.status_code == 200
        data = response.json()
        assert data["changes_detected"] is False

    @patch("back_office_lmelp.app.babelio_service")
    @patch("back_office_lmelp.app.mongodb_service")
    def test_changes_detected_when_editeur_needs_migration(
        self, mock_mongodb, mock_babelio, client
    ):
        """changes_detected est True quand editeur string existe mais editeur_id manque."""
        livre_id = str(ObjectId())
        auteur_id = ObjectId()

        # Livre avec editeur string SANS editeur_id -> migration nécessaire
        mock_mongodb.livres_collection = MagicMock()
        mock_mongodb.livres_collection.find_one.return_value = {
            "_id": ObjectId(livre_id),
            "titre": "Simone Émonet",
            "auteur_id": auteur_id,
            "editeur": "Flammarion",  # string, pas d'editeur_id
            "url_babelio": "https://www.babelio.com/livres/Test/12345",
        }
        mock_mongodb.auteurs_collection = MagicMock()
        mock_mongodb.auteurs_collection.find_one.return_value = {
            "_id": auteur_id,
            "nom": "Catherine Millet",
            "url_babelio": "https://www.babelio.com/auteur/Millet/999",
        }

        # Babelio retourne les mêmes données
        mock_babelio.fetch_full_title_from_url = AsyncMock(return_value="Simone Émonet")
        mock_babelio.fetch_publisher_from_url = AsyncMock(return_value="Flammarion")
        mock_babelio.fetch_author_url_from_page = AsyncMock(
            return_value="https://www.babelio.com/auteur/Millet/999"
        )
        mock_babelio._scrape_author_from_book_page = AsyncMock(
            return_value="Catherine Millet"
        )

        response = client.post(f"/api/livres/{livre_id}/refresh-babelio")

        assert response.status_code == 200
        data = response.json()
        # Même si les noms sont identiques, la migration editeur -> editeur_id
        # est nécessaire, donc changes_detected doit être True
        assert data["changes_detected"] is True
        assert data["editeur_needs_migration"] is True

    @patch("back_office_lmelp.app.babelio_service")
    @patch("back_office_lmelp.app.mongodb_service")
    def test_handles_none_scraped_values(self, mock_mongodb, mock_babelio, client):
        """Gère les valeurs None retournées par le scraping."""
        livre_id = str(ObjectId())
        auteur_id = ObjectId()

        mock_mongodb.livres_collection = MagicMock()
        mock_mongodb.livres_collection.find_one.return_value = {
            "_id": ObjectId(livre_id),
            "titre": "Test",
            "auteur_id": auteur_id,
            "editeur": "Test",
            "url_babelio": "https://www.babelio.com/livres/Test/12345",
        }
        mock_mongodb.auteurs_collection = MagicMock()
        mock_mongodb.auteurs_collection.find_one.return_value = {
            "_id": auteur_id,
            "nom": "Auteur",
            "url_babelio": None,
        }

        # Babelio returns None for some fields (scraping failed)
        mock_babelio.fetch_full_title_from_url = AsyncMock(return_value=None)
        mock_babelio.fetch_publisher_from_url = AsyncMock(return_value=None)
        mock_babelio.fetch_author_url_from_page = AsyncMock(return_value=None)
        mock_babelio._scrape_author_from_book_page = AsyncMock(return_value=None)

        response = client.post(f"/api/livres/{livre_id}/refresh-babelio")

        assert response.status_code == 200
        data = response.json()
        assert data["babelio"]["titre"] is None
        assert data["babelio"]["editeur"] is None


class TestApplyRefresh:
    """Tests pour POST /api/livres/{livre_id}/apply-refresh."""

    @patch("back_office_lmelp.app.mongodb_service")
    def test_updates_livre_and_auteur(self, mock_mongodb, client):
        """Apply met à jour le livre et l'auteur."""
        livre_id = str(ObjectId())
        auteur_id = ObjectId()
        editeur_oid = ObjectId()

        # Mock livre doc for auteur_id lookup
        mock_mongodb.livres_collection = MagicMock()
        mock_mongodb.livres_collection.find_one.return_value = {
            "_id": ObjectId(livre_id),
            "auteur_id": auteur_id,
        }

        # Mock editeur get_or_create
        mock_mongodb.get_or_create_editeur = MagicMock(return_value=(editeur_oid, True))

        # Mock update methods
        mock_mongodb.update_livre_from_refresh = MagicMock(return_value=True)
        mock_mongodb.update_auteur_name_and_url = MagicMock(return_value=True)

        response = client.post(
            f"/api/livres/{livre_id}/apply-refresh",
            json={
                "titre": "Nouveau Titre",
                "editeur": "P.O.L",
                "auteur_nom": "Nouvel Auteur",
                "auteur_url_babelio": "https://www.babelio.com/auteur/Test/999",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

        # Verify livre update was called
        mock_mongodb.update_livre_from_refresh.assert_called_once()
        call_args = mock_mongodb.update_livre_from_refresh.call_args
        assert call_args[0][0] == livre_id
        updates = call_args[0][1]
        assert updates["titre"] == "Nouveau Titre"
        # Issue #189: editeur_id remplace editeur (string), pas de duplication
        assert updates["editeur_id"] == editeur_oid
        assert "editeur" not in updates  # string supprimé quand editeur_id fourni

        # Verify auteur update was called
        mock_mongodb.update_auteur_name_and_url.assert_called_once_with(
            str(auteur_id),
            nom="Nouvel Auteur",
            url_babelio="https://www.babelio.com/auteur/Test/999",
        )

    @patch("back_office_lmelp.app.mongodb_service")
    def test_returns_404_when_livre_not_found(self, mock_mongodb, client):
        """Retourne 404 si le livre n'existe pas."""
        livre_id = str(ObjectId())
        mock_mongodb.livres_collection = MagicMock()
        mock_mongodb.livres_collection.find_one.return_value = None

        response = client.post(
            f"/api/livres/{livre_id}/apply-refresh",
            json={"titre": "Test"},
        )

        assert response.status_code == 404

    @patch("back_office_lmelp.app.mongodb_service")
    def test_creates_editeur_when_new(self, mock_mongodb, client):
        """Apply crée un éditeur quand il n'existe pas."""
        livre_id = str(ObjectId())
        auteur_id = ObjectId()
        new_editeur_oid = ObjectId()

        mock_mongodb.livres_collection = MagicMock()
        mock_mongodb.livres_collection.find_one.return_value = {
            "_id": ObjectId(livre_id),
            "auteur_id": auteur_id,
        }
        mock_mongodb.get_or_create_editeur = MagicMock(
            return_value=(new_editeur_oid, True)
        )
        mock_mongodb.update_livre_from_refresh = MagicMock(return_value=True)
        mock_mongodb.update_auteur_name_and_url = MagicMock(return_value=True)

        response = client.post(
            f"/api/livres/{livre_id}/apply-refresh",
            json={"editeur": "Nouvel Éditeur"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["editeur_created"] is True
        mock_mongodb.get_or_create_editeur.assert_called_once_with("Nouvel Éditeur")

    @patch("back_office_lmelp.app.mongodb_service")
    def test_uses_existing_editeur(self, mock_mongodb, client):
        """Apply utilise un éditeur existant sans en créer un nouveau."""
        livre_id = str(ObjectId())
        auteur_id = ObjectId()
        existing_oid = ObjectId()

        mock_mongodb.livres_collection = MagicMock()
        mock_mongodb.livres_collection.find_one.return_value = {
            "_id": ObjectId(livre_id),
            "auteur_id": auteur_id,
        }
        mock_mongodb.get_or_create_editeur = MagicMock(
            return_value=(existing_oid, False)
        )
        mock_mongodb.update_livre_from_refresh = MagicMock(return_value=True)
        mock_mongodb.update_auteur_name_and_url = MagicMock(return_value=True)

        response = client.post(
            f"/api/livres/{livre_id}/apply-refresh",
            json={"editeur": "Gallimard"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["editeur_created"] is False

    @patch("back_office_lmelp.app.mongodb_service")
    def test_partial_update_titre_only(self, mock_mongodb, client):
        """Apply avec seulement le titre fonctionne."""
        livre_id = str(ObjectId())
        auteur_id = ObjectId()

        mock_mongodb.livres_collection = MagicMock()
        mock_mongodb.livres_collection.find_one.return_value = {
            "_id": ObjectId(livre_id),
            "auteur_id": auteur_id,
        }
        mock_mongodb.update_livre_from_refresh = MagicMock(return_value=True)
        mock_mongodb.update_auteur_name_and_url = MagicMock(return_value=True)

        response = client.post(
            f"/api/livres/{livre_id}/apply-refresh",
            json={"titre": "Nouveau Titre"},
        )

        assert response.status_code == 200
        # No editeur call
        mock_mongodb.get_or_create_editeur = MagicMock()
        # titre should be in updates
        call_args = mock_mongodb.update_livre_from_refresh.call_args
        assert call_args[0][1]["titre"] == "Nouveau Titre"
