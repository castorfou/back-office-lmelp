"""Tests TDD pour le retour complet de migrate_one_book_and_author() (Issue #124 - Phase 12.2).

Ce module teste que migrate_one_book_and_author() retourne TOUJOURS titre, auteur et status
pour que MigrationRunner puisse afficher les vrais noms au lieu de "Unknown - Unknown".
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bson import ObjectId


class TestMigrateUrlBabelioCompleteReturn:
    """Tests pour la valeur de retour complète de migrate_one_book_and_author()."""

    @pytest.mark.asyncio
    async def test_should_return_titre_auteur_status_when_not_found(self):
        """Test TDD: migrate_one_book_and_author() doit retourner titre, auteur, status.

        Problème business réel:
        - Frontend affiche "Unknown - Unknown" au lieu du vrai titre/auteur
        - Cause: La fonction retourne seulement book_updated/author_updated
        - Solution: Retourner aussi titre, auteur, status pour l'affichage

        Scénario:
        1. Livre trouvé en MongoDB mais not_found sur Babelio
        2. migrate_one_book_and_author() doit retourner titre, auteur, status
        3. MigrationRunner pourra afficher "Le Petit Prince - Antoine de Saint-Exupéry"
        """
        # Arrange - Mock MongoDB
        livre_id = ObjectId()
        auteur_id = ObjectId()

        mock_livres_collection = MagicMock()
        mock_auteurs_collection = MagicMock()
        mock_prob_collection = MagicMock()

        mock_livres_collection.find_one.return_value = {
            "_id": livre_id,
            "titre": "Le Petit Prince",
            "auteur_id": auteur_id,
        }

        mock_auteurs_collection.find_one.return_value = {
            "_id": auteur_id,
            "nom": "Antoine de Saint-Exupéry",
        }

        mock_prob_collection.find.return_value = []
        mock_prob_collection.insert_one = MagicMock()

        def get_collection_side_effect(name):
            collections = {
                "livres": mock_livres_collection,
                "auteurs": mock_auteurs_collection,
                "babelio_problematic_cases": mock_prob_collection,
            }
            return collections.get(name, MagicMock())

        with patch(
            "scripts.migration_donnees.migrate_url_babelio.mongodb_service.get_collection"
        ) as mock_get_collection:
            mock_get_collection.side_effect = get_collection_side_effect

            # Mock BabelioService - retourne not_found
            mock_babelio = AsyncMock()
            mock_babelio.verify_book.return_value = {"status": "not_found"}

            from scripts.migration_donnees.migrate_url_babelio import (
                migrate_one_book_and_author,
            )

            # Act
            result = await migrate_one_book_and_author(
                babelio_service=mock_babelio, dry_run=False
            )

            # Assert - DOIT contenir titre, auteur, status
            assert result is not None, "Doit retourner un dict"
            assert "titre" in result, "Doit contenir 'titre' pour l'affichage frontend"
            assert "auteur" in result, (
                "Doit contenir 'auteur' pour l'affichage frontend"
            )
            assert "status" in result, (
                "Doit contenir 'status' pour l'affichage frontend"
            )

            # Vérifier les valeurs
            assert result["titre"] == "Le Petit Prince"
            assert result["auteur"] == "Antoine de Saint-Exupéry"
            assert result["status"] == "not_found"
            assert result["livre_updated"] is False
            assert result["auteur_updated"] is False

    @pytest.mark.asyncio
    async def test_should_return_titre_auteur_status_when_success(self):
        """Test TDD: Retourner aussi titre/auteur/status quand la migration réussit."""
        # Arrange
        livre_id = ObjectId()
        auteur_id = ObjectId()

        mock_livres_collection = MagicMock()
        mock_auteurs_collection = MagicMock()
        mock_prob_collection = MagicMock()

        mock_livres_collection.find_one.return_value = {
            "_id": livre_id,
            "titre": "1984",
            "auteur_id": auteur_id,
        }

        mock_auteurs_collection.find_one.return_value = {
            "_id": auteur_id,
            "nom": "George Orwell",
        }

        mock_prob_collection.find.return_value = []

        # Mock update operations
        mock_livres_collection.update_one.return_value = MagicMock(matched_count=1)
        mock_auteurs_collection.update_one.return_value = MagicMock(matched_count=1)

        def get_collection_side_effect(name):
            collections = {
                "livres": mock_livres_collection,
                "auteurs": mock_auteurs_collection,
                "babelio_problematic_cases": mock_prob_collection,
            }
            return collections.get(name, MagicMock())

        with patch(
            "scripts.migration_donnees.migrate_url_babelio.mongodb_service.get_collection"
        ) as mock_get_collection:
            mock_get_collection.side_effect = get_collection_side_effect

            # Mock BabelioService - retourne verified avec URL
            mock_babelio = AsyncMock()
            mock_babelio.verify_book.return_value = {
                "status": "verified",
                "babelio_url": "https://www.babelio.com/livres/Orwell-1984/1234",
                "babelio_author_url": "https://www.babelio.com/auteur/George-Orwell/5678",
            }
            mock_babelio._get_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value.status = 200

            from scripts.migration_donnees.migrate_url_babelio import (
                migrate_one_book_and_author,
            )

            # Act
            result = await migrate_one_book_and_author(
                babelio_service=mock_babelio, dry_run=False
            )

            # Assert
            assert result is not None
            assert "titre" in result
            assert "auteur" in result
            assert "status" in result

            assert result["titre"] == "1984"
            assert result["auteur"] == "George Orwell"
            assert result["status"] == "verified"
            assert result["livre_updated"] is True
            assert result["auteur_updated"] is True

    @pytest.mark.asyncio
    async def test_should_return_titre_auteur_status_when_http_error(self):
        """Test TDD: Retourner titre/auteur/status même en cas d'erreur HTTP.

        Problème business réel:
        - Avant: Quand Babelio était indisponible, le frontend affichait "Unknown - Unknown"
        - Après: Même en cas d'erreur, afficher "Le Petit Prince - Antoine de Saint-Exupéry"
        - Raison: L'utilisateur doit savoir quel livre était en cours de traitement

        Scénario:
        1. MongoDB trouve un livre
        2. BabelioService.verify_book() lève une exception (timeout/réseau)
        3. migrate_one_book_and_author() doit retourner titre, auteur, status="error"
        """
        # Arrange
        livre_id = ObjectId()
        auteur_id = ObjectId()

        mock_livres_collection = MagicMock()
        mock_auteurs_collection = MagicMock()
        mock_prob_collection = MagicMock()

        mock_livres_collection.find_one.return_value = {
            "_id": livre_id,
            "titre": "Le Petit Prince",
            "auteur_id": auteur_id,
        }

        mock_auteurs_collection.find_one.return_value = {
            "_id": auteur_id,
            "nom": "Antoine de Saint-Exupéry",
        }

        mock_prob_collection.find.return_value = []

        def get_collection_side_effect(name):
            collections = {
                "livres": mock_livres_collection,
                "auteurs": mock_auteurs_collection,
                "babelio_problematic_cases": mock_prob_collection,
            }
            return collections.get(name, MagicMock())

        with patch(
            "scripts.migration_donnees.migrate_url_babelio.mongodb_service.get_collection"
        ) as mock_get_collection:
            mock_get_collection.side_effect = get_collection_side_effect

            # Mock BabelioService.verify_book() - lève une exception HTTP
            mock_babelio = AsyncMock()
            mock_babelio.verify_book.side_effect = Exception("Connection timeout")

            from scripts.migration_donnees.migrate_url_babelio import (
                migrate_one_book_and_author,
            )

            # Act
            result = await migrate_one_book_and_author(
                babelio_service=mock_babelio, dry_run=False
            )

            # Assert - DOIT contenir titre, auteur, status même en cas d'erreur
            assert result is not None
            assert "titre" in result, "Doit contenir 'titre' même en cas d'erreur HTTP"
            assert "auteur" in result, (
                "Doit contenir 'auteur' même en cas d'erreur HTTP"
            )
            assert "status" in result, (
                "Doit contenir 'status' même en cas d'erreur HTTP"
            )

            # Vérifier les valeurs
            assert result["titre"] == "Le Petit Prince"
            assert result["auteur"] == "Antoine de Saint-Exupéry"
            assert result["status"] == "error"
            assert result["livre_updated"] is False
            assert result["auteur_updated"] is False
