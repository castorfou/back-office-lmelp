"""Tests TDD pour vérifier que l'auteur est bien mis à jour (Issue #124 - Phase 13).

Ce module teste que migrate_one_book_and_author() met à jour AUSSI l'auteur,
pas seulement le livre.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bson import ObjectId


class TestMigrateUrlBabelioAuthorUpdate:
    """Tests pour vérifier que l'auteur est mis à jour avec le livre."""

    @pytest.mark.asyncio
    async def test_should_update_both_book_and_author_when_verified(self):
        """Test TDD: La migration doit mettre à jour LE LIVRE ET L'AUTEUR.

        Problème business réel:
        - Un livre a UN auteur lié via auteur_id
        - Quand Babelio retourne verified, on doit mettre à jour:
          1. Le LIVRE avec url_babelio (page livre)
          2. L'AUTEUR avec url_babelio (page auteur)
        - Les deux doivent être traités dans la même migration

        Scénario:
        1. Livre "1984" avec auteur "George Orwell" trouvé
        2. Babelio retourne verified avec URL livre ET URL auteur
        3. migrate_one_book_and_author() doit:
           - Mettre à jour le livre dans MongoDB
           - Mettre à jour l'auteur dans MongoDB
           - Retourner livre_updated=True ET auteur_updated=True
        """
        # Arrange
        livre_id = ObjectId()
        auteur_id = ObjectId()

        mock_livres_collection = MagicMock()
        mock_auteurs_collection = MagicMock()
        mock_prob_collection = MagicMock()

        # Livre sans url_babelio
        mock_livres_collection.find_one.return_value = {
            "_id": livre_id,
            "titre": "1984",
            "auteur_id": auteur_id,
        }

        # Auteur sans url_babelio
        mock_auteurs_collection.find_one.return_value = {
            "_id": auteur_id,
            "nom": "George Orwell",
        }

        mock_prob_collection.find.return_value = []

        # Mock des opérations de mise à jour
        mock_livres_collection.update_one.return_value = MagicMock(matched_count=1)
        mock_auteurs_collection.update_one.return_value = MagicMock(matched_count=1)

        def get_collection_side_effect(name):
            collections = {
                "livres": mock_livres_collection,
                "auteurs": mock_auteurs_collection,
                "babelio_problematic_cases": mock_prob_collection,
            }
            return collections.get(name, MagicMock())

        with (
            patch(
                "scripts.migration_donnees.migrate_url_babelio.mongodb_service.get_collection"
            ) as mock_get_collection,
            patch(
                "scripts.migration_donnees.migrate_url_babelio.scrape_title_from_page"
            ) as mock_scrape,
            patch(
                "scripts.migration_donnees.migrate_url_babelio.normalize_title"
            ) as mock_normalize,
            patch(
                "scripts.migration_donnees.migrate_url_babelio.wait_rate_limit"
            ) as mock_wait,
        ):
            mock_get_collection.side_effect = get_collection_side_effect

            # Mock wait_rate_limit (async function)
            async def mock_wait_async():
                pass

            mock_wait.side_effect = mock_wait_async

            # Mock scrape_title_from_page (async function) pour retourner le titre exact
            async def mock_scrape_async(*args, **kwargs):
                return "1984"

            mock_scrape.side_effect = mock_scrape_async

            # Mock normalize_title pour retourner la même valeur
            mock_normalize.side_effect = lambda x: x

            # Mock BabelioService qui retourne LIVRE + AUTEUR
            mock_babelio = AsyncMock()
            mock_babelio.verify_book.return_value = {
                "status": "verified",
                "babelio_url": "https://www.babelio.com/livres/Orwell-1984/1234",
                "babelio_author_url": "https://www.babelio.com/auteur/George-Orwell/5678",
            }

            # Mock HTTP 200 pour les deux URLs
            mock_response_livre = MagicMock()
            mock_response_livre.status = 200
            mock_response_livre.__aenter__ = AsyncMock(return_value=mock_response_livre)
            mock_response_livre.__aexit__ = AsyncMock(return_value=None)

            mock_response_auteur = MagicMock()
            mock_response_auteur.status = 200
            mock_response_auteur.__aenter__ = AsyncMock(
                return_value=mock_response_auteur
            )
            mock_response_auteur.__aexit__ = AsyncMock(return_value=None)

            mock_session = MagicMock()
            # Premier appel = URL livre, deuxième appel = URL auteur
            mock_session.get.side_effect = [mock_response_livre, mock_response_auteur]

            mock_babelio._get_session = AsyncMock(return_value=mock_session)

            from scripts.migration_donnees.migrate_url_babelio import (
                migrate_one_book_and_author,
            )

            # Act
            result = await migrate_one_book_and_author(
                babelio_service=mock_babelio, dry_run=False
            )

            # Assert - Les DEUX doivent être mis à jour
            assert result is not None, "Doit retourner un résultat"
            assert result["livre_updated"] is True, "Le LIVRE doit être mis à jour"
            assert result["auteur_updated"] is True, "L'AUTEUR doit être mis à jour"

            # Vérifier que update_one a été appelé pour le LIVRE
            mock_livres_collection.update_one.assert_called_once()
            livre_update_call = mock_livres_collection.update_one.call_args
            assert livre_update_call[0][0] == {"_id": livre_id}
            assert "url_babelio" in livre_update_call[0][1]["$set"], (
                "Doit mettre à jour url_babelio du livre"
            )
            assert (
                livre_update_call[0][1]["$set"]["url_babelio"]
                == "https://www.babelio.com/livres/Orwell-1984/1234"
            )

            # Vérifier que update_one a été appelé pour L'AUTEUR
            mock_auteurs_collection.update_one.assert_called_once()
            auteur_update_call = mock_auteurs_collection.update_one.call_args
            assert auteur_update_call[0][0] == {"_id": auteur_id}
            assert "url_babelio" in auteur_update_call[0][1]["$set"], (
                "Doit mettre à jour url_babelio de l'auteur"
            )
            assert (
                auteur_update_call[0][1]["$set"]["url_babelio"]
                == "https://www.babelio.com/auteur/George-Orwell/5678"
            )

    @pytest.mark.asyncio
    async def test_should_not_update_author_if_already_has_url(self):
        """Test TDD: Ne pas mettre à jour l'auteur s'il a déjà une URL Babelio.

        Scénario:
        1. Livre sans URL Babelio
        2. Auteur qui a DÉJÀ une URL Babelio
        3. migrate_one_book_and_author() doit:
           - Mettre à jour le livre
           - NE PAS mettre à jour l'auteur (il a déjà son URL)
           - Retourner livre_updated=True, auteur_updated=False
        """
        # Arrange
        livre_id = ObjectId()
        auteur_id = ObjectId()

        mock_livres_collection = MagicMock()
        mock_auteurs_collection = MagicMock()
        mock_prob_collection = MagicMock()

        # Livre sans url_babelio
        mock_livres_collection.find_one.return_value = {
            "_id": livre_id,
            "titre": "1984",
            "auteur_id": auteur_id,
        }

        # Auteur qui a DÉJÀ une URL Babelio
        mock_auteurs_collection.find_one.return_value = {
            "_id": auteur_id,
            "nom": "George Orwell",
            "url_babelio": "https://www.babelio.com/auteur/George-Orwell/EXISTING",
        }

        mock_prob_collection.find.return_value = []

        # Mock des opérations de mise à jour
        mock_livres_collection.update_one.return_value = MagicMock(matched_count=1)

        def get_collection_side_effect(name):
            collections = {
                "livres": mock_livres_collection,
                "auteurs": mock_auteurs_collection,
                "babelio_problematic_cases": mock_prob_collection,
            }
            return collections.get(name, MagicMock())

        with (
            patch(
                "scripts.migration_donnees.migrate_url_babelio.mongodb_service.get_collection"
            ) as mock_get_collection,
            patch(
                "scripts.migration_donnees.migrate_url_babelio.scrape_title_from_page"
            ) as mock_scrape,
            patch(
                "scripts.migration_donnees.migrate_url_babelio.normalize_title"
            ) as mock_normalize,
            patch(
                "scripts.migration_donnees.migrate_url_babelio.wait_rate_limit"
            ) as mock_wait,
        ):
            mock_get_collection.side_effect = get_collection_side_effect

            # Mock wait_rate_limit (async function)
            async def mock_wait_async():
                pass

            mock_wait.side_effect = mock_wait_async

            # Mock scrape_title_from_page (async function) pour retourner le titre exact
            async def mock_scrape_async(*args, **kwargs):
                return "1984"

            mock_scrape.side_effect = mock_scrape_async

            # Mock normalize_title pour retourner la même valeur
            mock_normalize.side_effect = lambda x: x

            # Mock BabelioService
            mock_babelio = AsyncMock()
            mock_babelio.verify_book.return_value = {
                "status": "verified",
                "babelio_url": "https://www.babelio.com/livres/Orwell-1984/1234",
                "babelio_author_url": "https://www.babelio.com/auteur/George-Orwell/5678",
            }

            # Mock HTTP 200 pour l'URL livre
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)

            mock_session = MagicMock()
            mock_session.get.return_value = mock_response

            mock_babelio._get_session = AsyncMock(return_value=mock_session)

            from scripts.migration_donnees.migrate_url_babelio import (
                migrate_one_book_and_author,
            )

            # Act
            result = await migrate_one_book_and_author(
                babelio_service=mock_babelio, dry_run=False
            )

            # Assert
            assert result["livre_updated"] is True, "Le livre doit être mis à jour"
            assert result["auteur_updated"] is False, (
                "L'auteur ne doit PAS être mis à jour (il a déjà son URL)"
            )

            # Vérifier que update_one a été appelé SEULEMENT pour le livre
            mock_livres_collection.update_one.assert_called_once()
            mock_auteurs_collection.update_one.assert_not_called()
