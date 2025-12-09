"""Tests TDD pour le cas auteur_already_linked (Issue #124).

Ce module teste que quand un auteur a déjà une URL Babelio,
le système retourne auteur_already_linked=True et affiche un message informatif
au lieu d'un message d'erreur.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bson import ObjectId


class TestAuthorAlreadyLinked:
    """Tests pour le cas où l'auteur a déjà une URL Babelio."""

    @pytest.mark.asyncio
    async def test_should_return_author_already_linked_when_author_has_url(self):
        """Test TDD: Retourner auteur_already_linked=True quand l'auteur a déjà une URL.

        Problème business réel (Issue #124):
        - Livre "Chien 51" par Laurent Gaudé
        - Le livre a été mis à jour avec URL Babelio
        - L'auteur avait DÉJÀ une URL Babelio avant la migration
        - Le message "❌ Auteur non migré" est trompeur
        - On doit afficher "ℹ️ Auteur déjà lié à Babelio"

        Scénario:
        1. Un livre sans URL est trouvé
        2. Babelio retourne une URL valide pour le livre
        3. L'auteur a DÉJÀ une URL Babelio (auteur.url_babelio existe)
        4. migrate_one_book_and_author doit retourner auteur_already_linked=True
        5. Le livre doit être mis à jour (livre_updated=True)
        6. L'auteur ne doit PAS être mis à jour (auteur_updated=False)
        """
        # Arrange
        livre_id = ObjectId()
        auteur_id = ObjectId()

        mock_livres_collection = MagicMock()
        mock_auteurs_collection = MagicMock()

        # Livre SANS URL Babelio
        mock_livres_collection.find_one.return_value = {
            "_id": livre_id,
            "titre": "Chien 51",
            "auteur_id": auteur_id,
        }

        # Auteur AVEC URL Babelio (déjà lié)
        mock_auteurs_collection.find_one.return_value = {
            "_id": auteur_id,
            "nom": "Laurent Gaudé",
            "url_babelio": "https://www.babelio.com/auteur/Laurent-Gaude/3559",
        }

        mock_livres_collection.update_one.return_value = MagicMock(matched_count=1)

        def get_collection_side_effect(name):
            if name == "livres":
                return mock_livres_collection
            elif name == "auteurs":
                return mock_auteurs_collection
            return MagicMock()

        # Mock BabelioService
        mock_babelio_service = MagicMock()
        mock_babelio_service.verify_book = AsyncMock(
            return_value={
                "status": "verified",
                "babelio_url": "https://www.babelio.com/livres/Gaude-Chien-51/1425651",
                "babelio_author_url": "https://www.babelio.com/auteur/Laurent-Gaude/3559",
            }
        )

        # Mock HTTP session pour vérification URL (200 OK)
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get.return_value = mock_response

        mock_babelio_service._get_session = AsyncMock(return_value=mock_session)

        with (
            patch(
                "scripts.migration_donnees.migrate_url_babelio.mongodb_service.get_collection"
            ) as mock_get_collection,
            patch(
                "scripts.migration_donnees.migrate_url_babelio.wait_rate_limit"
            ) as mock_wait,
            patch(
                "scripts.migration_donnees.migrate_url_babelio.scrape_title_from_page"
            ) as mock_scrape_title,
        ):
            mock_get_collection.side_effect = get_collection_side_effect
            mock_wait.side_effect = AsyncMock()

            # Mock async function scrape_title_from_page
            async def mock_scrape_title_async(service, url):
                return "Chien 51"

            mock_scrape_title.side_effect = mock_scrape_title_async

            from scripts.migration_donnees.migrate_url_babelio import (
                migrate_one_book_and_author,
            )

            # Act
            result = await migrate_one_book_and_author(
                babelio_service=mock_babelio_service, dry_run=False
            )

            # Assert
            assert result is not None, "Doit retourner un résultat"
            assert result["livre_updated"] is True, "Livre doit être mis à jour"
            assert result["auteur_updated"] is False, (
                "Auteur ne doit PAS être mis à jour (déjà lié)"
            )
            assert result["auteur_already_linked"] is True, (
                "auteur_already_linked doit être True"
            )
            assert result["status"] == "verified"

            # Vérifier que le livre a été mis à jour
            mock_livres_collection.update_one.assert_called_once()

            # Vérifier que l'auteur n'a PAS été mis à jour (déjà lié)
            mock_auteurs_collection.update_one.assert_not_called()
