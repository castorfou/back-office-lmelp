"""Tests for Calibre tags generation on livre detail page (Issue #200).

Tests the construction of Calibre-style tags from avis data:
- lmelp_yyMMdd for each emission where the book was discussed
- lmelp_prenom_nom for each critic giving a coup de coeur
- CALIBRE_VIRTUAL_LIBRARY_TAG if book found in Calibre
"""

from datetime import datetime
from unittest.mock import patch

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from back_office_lmelp.app import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


class TestCalibreTagsGeneration:
    """Tests for calibre_tags field in GET /api/livre/{livre_id} response."""

    @patch("back_office_lmelp.app.mongodb_service")
    def test_livre_detail_returns_calibre_tags_with_date_and_critic(
        self, mock_mongodb_service, client
    ):
        """Test that livre detail returns calibre_tags with lmelp_date and lmelp_critic tags."""
        # GIVEN: Un livre discuté dans une émission avec un coup de coeur
        livre_id = str(ObjectId())
        mock_mongodb_service.get_livre_with_episodes.return_value = {
            "livre_id": livre_id,
            "titre": "La Deuxième Vie",
            "auteur_id": str(ObjectId()),
            "auteur_nom": "Philippe Sollers",
            "editeur": "Chronique sociale",
            "url_babelio": "https://www.babelio.com/livres/test/123",
            "note_moyenne": 9.0,
            "nombre_emissions": 1,
            "emissions": [
                {
                    "emission_id": str(ObjectId()),
                    "date": "2024-03-24",
                    "note_moyenne": 9.0,
                    "nombre_avis": 1,
                }
            ],
            "calibre_tags": ["lmelp_240324", "lmelp_arnaud_viviant"],
        }

        # WHEN: On appelle GET /api/livre/{id}
        response = client.get(f"/api/livre/{livre_id}")

        # THEN: La réponse contient calibre_tags
        assert response.status_code == 200
        data = response.json()
        assert "calibre_tags" in data
        assert "lmelp_240324" in data["calibre_tags"]
        assert "lmelp_arnaud_viviant" in data["calibre_tags"]

    @patch("back_office_lmelp.app.mongodb_service")
    def test_livre_detail_returns_empty_calibre_tags_when_no_avis(
        self, mock_mongodb_service, client
    ):
        """Test that livre detail returns empty calibre_tags when no avis exist."""
        # GIVEN: Un livre sans avis
        livre_id = str(ObjectId())
        mock_mongodb_service.get_livre_with_episodes.return_value = {
            "livre_id": livre_id,
            "titre": "Livre Sans Avis",
            "auteur_id": str(ObjectId()),
            "auteur_nom": "Auteur Test",
            "editeur": "Editeur Test",
            "note_moyenne": None,
            "nombre_emissions": 0,
            "emissions": [],
            "calibre_tags": [],
        }

        # WHEN: On appelle GET /api/livre/{id}
        response = client.get(f"/api/livre/{livre_id}")

        # THEN: calibre_tags est vide
        assert response.status_code == 200
        data = response.json()
        assert "calibre_tags" in data
        assert data["calibre_tags"] == []


class TestCalibreVirtualLibraryTag:
    """Tests for CALIBRE_VIRTUAL_LIBRARY_TAG prepended to calibre_tags."""

    @patch("back_office_lmelp.app.calibre_service")
    @patch("back_office_lmelp.app.mongodb_service")
    def test_calibre_virtual_library_tag_prepended_when_book_in_calibre(
        self, mock_mongodb_service, mock_calibre_service, client
    ):
        """Test that CALIBRE_VIRTUAL_LIBRARY_TAG is prepended when book found in Calibre."""
        livre_id = str(ObjectId())
        mock_mongodb_service.get_livre_with_episodes.return_value = {
            "livre_id": livre_id,
            "titre": "La Deuxième Vie",
            "auteur_id": str(ObjectId()),
            "auteur_nom": "Philippe Sollers",
            "editeur": "Gallimard",
            "url_babelio": None,
            "note_moyenne": 9.0,
            "nombre_emissions": 1,
            "emissions": [],
            "calibre_tags": ["lmelp_240324", "lmelp_arnaud_viviant"],
        }

        # Calibre is available and book is found
        mock_calibre_service._available = True
        mock_calibre_service.get_all_books_summary.return_value = [
            {
                "id": 1,
                "title": "La Deuxième Vie",
                "authors": ["Sollers"],
                "read": True,
                "rating": 8,
            }
        ]

        with patch("back_office_lmelp.app.settings") as mock_settings:
            mock_settings.calibre_virtual_library_tag = "guillaume"
            response = client.get(f"/api/livre/{livre_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["calibre_tags"][0] == "guillaume"
        assert data["calibre_tags"] == [
            "guillaume",
            "lmelp_240324",
            "lmelp_arnaud_viviant",
        ]

    @patch("back_office_lmelp.app.calibre_service")
    @patch("back_office_lmelp.app.mongodb_service")
    def test_no_calibre_tag_when_calibre_unavailable(
        self, mock_mongodb_service, mock_calibre_service, client
    ):
        """Test that no virtual library tag is added when Calibre is unavailable."""
        livre_id = str(ObjectId())
        mock_mongodb_service.get_livre_with_episodes.return_value = {
            "livre_id": livre_id,
            "titre": "Test Livre",
            "auteur_id": str(ObjectId()),
            "auteur_nom": "Test Auteur",
            "editeur": "Test Editeur",
            "url_babelio": None,
            "note_moyenne": None,
            "nombre_emissions": 0,
            "emissions": [],
            "calibre_tags": ["lmelp_240101"],
        }

        mock_calibre_service._available = False

        response = client.get(f"/api/livre/{livre_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["calibre_tags"] == ["lmelp_240101"]

    @patch("back_office_lmelp.app.calibre_service")
    @patch("back_office_lmelp.app.mongodb_service")
    def test_no_calibre_tag_when_book_not_in_calibre(
        self, mock_mongodb_service, mock_calibre_service, client
    ):
        """Test that no virtual library tag is added when book not found in Calibre."""
        livre_id = str(ObjectId())
        mock_mongodb_service.get_livre_with_episodes.return_value = {
            "livre_id": livre_id,
            "titre": "Livre Inconnu",
            "auteur_id": str(ObjectId()),
            "auteur_nom": "Auteur Inconnu",
            "editeur": "Editeur Test",
            "url_babelio": None,
            "note_moyenne": None,
            "nombre_emissions": 0,
            "emissions": [],
            "calibre_tags": [],
        }

        mock_calibre_service._available = True
        mock_calibre_service.get_all_books_summary.return_value = [
            {
                "id": 1,
                "title": "Autre Livre",
                "authors": ["Autre"],
                "read": True,
                "rating": 8,
            }
        ]

        with patch("back_office_lmelp.app.settings") as mock_settings:
            mock_settings.calibre_virtual_library_tag = "guillaume"
            response = client.get(f"/api/livre/{livre_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["calibre_tags"] == []


class TestBuildCalibreTags:
    """Tests for the _build_calibre_tags helper method in MongoDBService."""

    def test_build_tags_from_programme_avis(self):
        """Test lmelp_yyMMdd tag is generated from emission date for programme avis."""
        from back_office_lmelp.services.mongodb_service import MongoDBService

        service = MongoDBService.__new__(MongoDBService)

        emission_oid = str(ObjectId())
        all_avis = [
            {
                "emission_oid": emission_oid,
                "section": "programme",
                "critique_nom_extrait": "Patricia Martin",
                "note": 7,
            }
        ]
        emissions_by_id = {
            emission_oid: {"date": datetime(2024, 3, 24)},
        }

        tags = service._build_calibre_tags(all_avis, emissions_by_id)

        assert "lmelp_240324" in tags

    def test_build_tags_from_coup_de_coeur_avis(self):
        """Test lmelp_prenom_nom tag is generated for coup de coeur critics."""
        from back_office_lmelp.services.mongodb_service import MongoDBService

        service = MongoDBService.__new__(MongoDBService)

        emission_oid = str(ObjectId())
        all_avis = [
            {
                "emission_oid": emission_oid,
                "section": "coup_de_coeur",
                "critique_nom_extrait": "Arnaud Viviant",
                "note": 9,
            }
        ]
        emissions_by_id = {
            emission_oid: {"date": datetime(2024, 3, 24)},
        }

        tags = service._build_calibre_tags(all_avis, emissions_by_id)

        assert "lmelp_240324" in tags
        assert "lmelp_arnaud_viviant" in tags

    def test_date_tags_sorted_chronologically(self):
        """Test that lmelp_date tags are sorted chronologically."""
        from back_office_lmelp.services.mongodb_service import MongoDBService

        service = MongoDBService.__new__(MongoDBService)

        em_oid1 = str(ObjectId())
        em_oid2 = str(ObjectId())
        all_avis = [
            {
                "emission_oid": em_oid2,
                "section": "programme",
                "critique_nom_extrait": "Critic A",
                "note": 7,
            },
            {
                "emission_oid": em_oid1,
                "section": "programme",
                "critique_nom_extrait": "Critic B",
                "note": 8,
            },
        ]
        emissions_by_id = {
            em_oid1: {"date": datetime(2023, 1, 15)},
            em_oid2: {"date": datetime(2024, 6, 20)},
        }

        tags = service._build_calibre_tags(all_avis, emissions_by_id)

        date_tags = [t for t in tags if t.startswith("lmelp_") and t[6:].isdigit()]
        assert date_tags == ["lmelp_230115", "lmelp_240620"]

    def test_critic_tags_sorted_alphabetically(self):
        """Test that lmelp_critic tags are sorted alphabetically."""
        from back_office_lmelp.services.mongodb_service import MongoDBService

        service = MongoDBService.__new__(MongoDBService)

        em_oid = str(ObjectId())
        all_avis = [
            {
                "emission_oid": em_oid,
                "section": "coup_de_coeur",
                "critique_nom_extrait": "Patricia Martin",
                "note": 9,
            },
            {
                "emission_oid": em_oid,
                "section": "coup_de_coeur",
                "critique_nom_extrait": "Arnaud Viviant",
                "note": 9,
            },
        ]
        emissions_by_id = {
            em_oid: {"date": datetime(2024, 3, 24)},
        }

        tags = service._build_calibre_tags(all_avis, emissions_by_id)

        critic_tags = [t for t in tags if not t[6:].isdigit()]
        assert critic_tags == ["lmelp_arnaud_viviant", "lmelp_patricia_martin"]

    def test_date_tags_before_critic_tags(self):
        """Test that date tags come before critic tags."""
        from back_office_lmelp.services.mongodb_service import MongoDBService

        service = MongoDBService.__new__(MongoDBService)

        em_oid = str(ObjectId())
        all_avis = [
            {
                "emission_oid": em_oid,
                "section": "coup_de_coeur",
                "critique_nom_extrait": "Arnaud Viviant",
                "note": 9,
            },
        ]
        emissions_by_id = {
            em_oid: {"date": datetime(2024, 3, 24)},
        }

        tags = service._build_calibre_tags(all_avis, emissions_by_id)

        assert tags == ["lmelp_240324", "lmelp_arnaud_viviant"]

    def test_empty_avis_returns_empty_tags(self):
        """Test that empty avis list returns empty tags."""
        from back_office_lmelp.services.mongodb_service import MongoDBService

        service = MongoDBService.__new__(MongoDBService)

        tags = service._build_calibre_tags([], {})

        assert tags == []

    def test_no_duplicate_date_tags(self):
        """Test that duplicate emission dates produce only one tag."""
        from back_office_lmelp.services.mongodb_service import MongoDBService

        service = MongoDBService.__new__(MongoDBService)

        em_oid = str(ObjectId())
        # Two avis on same emission (same date)
        all_avis = [
            {
                "emission_oid": em_oid,
                "section": "programme",
                "critique_nom_extrait": "Critic A",
                "note": 7,
            },
            {
                "emission_oid": em_oid,
                "section": "programme",
                "critique_nom_extrait": "Critic B",
                "note": 8,
            },
        ]
        emissions_by_id = {
            em_oid: {"date": datetime(2024, 3, 24)},
        }

        tags = service._build_calibre_tags(all_avis, emissions_by_id)

        date_tags = [t for t in tags if t[6:].isdigit()]
        assert date_tags == ["lmelp_240324"]
