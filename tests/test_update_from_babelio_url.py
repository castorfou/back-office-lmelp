"""Tests TDD pour update_from_babelio_url - Issue #124.

Permet à l'utilisateur d'entrer manuellement une URL Babelio et scraper les données.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from bson import ObjectId


class TestUpdateFromBabelioUrl:
    """Tests pour update_from_babelio_url()."""

    @pytest.mark.asyncio
    async def test_should_update_livre_from_babelio_url(self):
        """Test TDD: Scraper une URL Babelio et réutiliser accept_suggestion().

        Problème UI:
        - L'utilisateur connaît l'URL Babelio du livre mais le système ne l'a pas trouvée
        - Il veut entrer manuellement l'URL et récupérer les données

        Solution:
        - Valider l'URL Babelio
        - Scraper la page (fetch_full_title_from_url, fetch_author_url_from_page)
        - Réutiliser accept_suggestion() pour mettre à jour livre + auteur
        """
        # Arrange
        from back_office_lmelp.services.babelio_migration_service import (
            BabelioMigrationService,
        )

        mock_mongodb_service = MagicMock()
        mock_babelio_service = MagicMock()
        mock_mongodb_service.db = MagicMock()

        # Mock scraping Babelio (méthodes existantes)
        mock_babelio_service.fetch_full_title_from_url = AsyncMock(
            return_value="Le Titre Correct"
        )
        mock_babelio_service.fetch_author_url_from_page = AsyncMock(
            return_value="https://www.babelio.com/auteur/Nom-Auteur/12345"
        )

        service = BabelioMigrationService(mock_mongodb_service, mock_babelio_service)

        # Mock accept_suggestion (méthode existante)
        service.accept_suggestion = MagicMock(return_value=True)

        livre_id = str(ObjectId())

        # Act
        result = await service.update_from_babelio_url(
            item_id=livre_id,
            babelio_url="https://www.babelio.com/livres/auteur/titre/123456",
            item_type="livre",
        )

        # Assert
        assert result["success"] is True, "Doit retourner success=True"
        assert result["scraped_data"]["titre"] == "Le Titre Correct"
        assert (
            result["scraped_data"]["auteur_url_babelio"]
            == "https://www.babelio.com/auteur/Nom-Auteur/12345"
        )

        # Vérifier l'appel au scraping
        mock_babelio_service.fetch_full_title_from_url.assert_called_once_with(
            "https://www.babelio.com/livres/auteur/titre/123456"
        )
        mock_babelio_service.fetch_author_url_from_page.assert_called_once_with(
            "https://www.babelio.com/livres/auteur/titre/123456"
        )

        # Vérifier la réutilisation de accept_suggestion
        service.accept_suggestion.assert_called_once_with(
            livre_id=livre_id,
            babelio_url="https://www.babelio.com/livres/auteur/titre/123456",
            babelio_author_url="https://www.babelio.com/auteur/Nom-Auteur/12345",
            corrected_title="Le Titre Correct",
        )

    @pytest.mark.asyncio
    async def test_should_update_auteur_from_babelio_url(self):
        """Test TDD: Mettre à jour l'URL d'un auteur (garde le nom existant)."""
        # Arrange
        from back_office_lmelp.services.babelio_migration_service import (
            BabelioMigrationService,
        )

        mock_mongodb_service = MagicMock()
        mock_babelio_service = MagicMock()

        mock_auteurs = MagicMock()
        mock_problematic = MagicMock()
        mock_db = {
            "auteurs": mock_auteurs,
            "babelio_problematic_cases": mock_problematic,
        }
        mock_mongodb_service.db = mock_db

        auteur_id = str(ObjectId())
        auteur_oid = ObjectId(auteur_id)

        # Mock auteur existant
        mock_auteurs.find_one.return_value = {
            "_id": auteur_oid,
            "nom": "Nom Auteur Initial",
        }

        # Mock updates
        mock_auteurs.update_one.return_value = MagicMock(matched_count=1)
        mock_problematic.delete_one.return_value = MagicMock(deleted_count=1)

        service = BabelioMigrationService(mock_mongodb_service, mock_babelio_service)

        # Act
        result = await service.update_from_babelio_url(
            item_id=auteur_id,
            babelio_url="https://www.babelio.com/auteur/Nom-Auteur/12345",
            item_type="auteur",
        )

        # Assert
        assert result["success"] is True
        assert (
            result["scraped_data"]["nom"] == "Nom Auteur Initial"
        )  # Garde le nom existant
        assert (
            result["scraped_data"]["url_babelio"]
            == "https://www.babelio.com/auteur/Nom-Auteur/12345"
        )

        # Vérifier la mise à jour de l'auteur
        mock_auteurs.update_one.assert_called_once()
        call_args = mock_auteurs.update_one.call_args
        assert call_args[0][0] == {"_id": auteur_oid}
        update_data = call_args[0][1]["$set"]
        assert (
            update_data["url_babelio"]
            == "https://www.babelio.com/auteur/Nom-Auteur/12345"
        )
        assert isinstance(update_data["updated_at"], datetime)

        # Vérifier le retrait de problematic_cases
        mock_problematic.delete_one.assert_called_once_with({"auteur_id": auteur_id})

    @pytest.mark.asyncio
    async def test_should_validate_babelio_url_format(self):
        """Test TDD: Valider que l'URL est bien une URL Babelio."""
        # Arrange
        from back_office_lmelp.services.babelio_migration_service import (
            BabelioMigrationService,
        )

        mock_mongodb_service = MagicMock()
        mock_babelio_service = MagicMock()
        mock_mongodb_service.db = {}

        service = BabelioMigrationService(mock_mongodb_service, mock_babelio_service)

        # Act
        result = await service.update_from_babelio_url(
            item_id=str(ObjectId()),
            babelio_url="https://www.google.com/search?q=livre",
            item_type="livre",
        )

        # Assert
        assert result["success"] is False
        assert "invalide" in result["error"].lower()
        assert "babelio" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_should_return_error_if_scraping_fails(self):
        """Test TDD: Retourner une erreur si le scraping échoue."""
        # Arrange
        from back_office_lmelp.services.babelio_migration_service import (
            BabelioMigrationService,
        )

        mock_mongodb_service = MagicMock()
        mock_babelio_service = MagicMock()
        mock_mongodb_service.db = MagicMock()

        # Mock scraping qui échoue
        mock_babelio_service.fetch_full_title_from_url = AsyncMock(
            side_effect=Exception("Page introuvable")
        )

        service = BabelioMigrationService(mock_mongodb_service, mock_babelio_service)

        livre_id = str(ObjectId())

        # Act
        result = await service.update_from_babelio_url(
            item_id=livre_id,
            babelio_url="https://www.babelio.com/livres/auteur/titre/999999",
            item_type="livre",
        )

        # Assert
        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_should_return_error_if_item_not_found(self):
        """Test TDD: Retourner une erreur si l'item n'existe pas dans MongoDB (auteur)."""
        # Arrange
        from back_office_lmelp.services.babelio_migration_service import (
            BabelioMigrationService,
        )

        mock_mongodb_service = MagicMock()
        mock_babelio_service = MagicMock()

        mock_auteurs = MagicMock()
        mock_db = {"auteurs": mock_auteurs}
        mock_mongodb_service.db = mock_db

        auteur_id = str(ObjectId())
        mock_auteurs.find_one.return_value = None  # Auteur non trouvé

        service = BabelioMigrationService(mock_mongodb_service, mock_babelio_service)

        # Act
        result = await service.update_from_babelio_url(
            item_id=auteur_id,
            babelio_url="https://www.babelio.com/auteur/Nom-Auteur/12345",
            item_type="auteur",
        )

        # Assert
        assert result["success"] is False
        assert "non trouvé" in result["error"].lower()
