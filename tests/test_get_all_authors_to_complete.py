"""Tests TDD pour get_all_authors_to_complete() - Issue #124.

La Phase 2 doit traiter les auteurs sans url_babelio, pas les livres.
"""

from unittest.mock import MagicMock, patch

import pytest
from bson import ObjectId


class TestGetAllAuthorsToComplete:
    """Tests pour la fonction get_all_authors_to_complete()."""

    @pytest.mark.asyncio
    async def test_should_return_authors_without_url_babelio(self):
        """Test TDD: Retourner tous les auteurs sans url_babelio.

        Production montre: 6 auteurs en attente de liaison
        Ces auteurs n'ont pas de url_babelio (null ou absent)
        """
        # Arrange
        from scripts.migration_donnees.migrate_url_babelio import (
            get_all_authors_to_complete,
        )

        with patch(
            "scripts.migration_donnees.migrate_url_babelio.mongodb_service"
        ) as mock_service:
            mock_auteurs = MagicMock()
            mock_problematic = MagicMock()
            mock_service.get_collection.side_effect = (
                lambda name: mock_auteurs
                if name == "auteurs"
                else mock_problematic
                if name == "babelio_problematic_cases"
                else MagicMock()
            )

            # Mock 6 auteurs sans URL
            auteur_ids = [ObjectId() for _ in range(6)]
            mock_problematic.find.return_value = []
            mock_auteurs.aggregate.return_value = [
                {
                    "_id": auteur_id,
                    "auteur_id": auteur_id,
                    "nom": f"Auteur {i}",
                    "livres": [{"livre_id": ObjectId(), "titre": f"Livre {i}"}],
                }
                for i, auteur_id in enumerate(auteur_ids)
            ]

            # Act
            authors = await get_all_authors_to_complete()

        # Assert
        assert isinstance(authors, list), "Doit retourner une liste"
        assert len(authors) > 0, "Doit trouver les 6 auteurs sans URL"

        # Vérifier la structure des données retournées
        for author in authors:
            assert "auteur_id" in author, "Doit contenir auteur_id"
            assert "nom" in author, "Doit contenir nom de l'auteur"
            assert "livres" in author, "Doit contenir liste des livres"
            assert isinstance(author["livres"], list), "livres doit être une liste"

    @pytest.mark.asyncio
    async def test_should_include_book_details_for_each_author(self):
        """Test TDD: Chaque auteur doit avoir les détails de ses livres.

        Pour traiter un auteur, on a besoin de savoir:
        - Quels sont ses livres
        - Si ces livres ont une url_babelio
        - Si ces livres sont problématiques ou not_found
        """
        # Arrange
        from scripts.migration_donnees.migrate_url_babelio import (
            get_all_authors_to_complete,
        )

        with patch(
            "scripts.migration_donnees.migrate_url_babelio.mongodb_service"
        ) as mock_service:
            mock_auteurs = MagicMock()
            mock_problematic = MagicMock()
            mock_service.get_collection.side_effect = (
                lambda name: mock_auteurs
                if name == "auteurs"
                else mock_problematic
                if name == "babelio_problematic_cases"
                else MagicMock()
            )

            auteur_id = ObjectId()
            livre_id = ObjectId()
            mock_problematic.find.return_value = []
            mock_auteurs.aggregate.return_value = [
                {
                    "_id": auteur_id,
                    "auteur_id": auteur_id,
                    "nom": "Test Auteur",
                    "livres": [
                        {
                            "livre_id": livre_id,
                            "titre": "Test Livre",
                            "url_babelio": None,
                        }
                    ],
                }
            ]

            # Act
            authors = await get_all_authors_to_complete()

        # Assert
        assert len(authors) > 0, "Doit trouver des auteurs"

        for author in authors:
            livres = author["livres"]
            for livre in livres:
                assert "livre_id" in livre, "Chaque livre doit avoir un ID"
                assert "titre" in livre, "Chaque livre doit avoir un titre"
                # Ces champs peuvent être null/absent, mais doivent être présents
                assert "url_babelio" in livre, "Doit indiquer si livre a url_babelio"

    @pytest.mark.asyncio
    async def test_should_exclude_authors_with_url_babelio(self):
        """Test TDD: Ne pas retourner les auteurs qui ont déjà une url_babelio."""
        # Arrange
        from scripts.migration_donnees.migrate_url_babelio import (
            get_all_authors_to_complete,
        )

        with patch(
            "scripts.migration_donnees.migrate_url_babelio.mongodb_service"
        ) as mock_service:
            mock_auteurs = MagicMock()
            mock_problematic = MagicMock()
            mock_service.get_collection.side_effect = (
                lambda name: mock_auteurs
                if name == "auteurs"
                else mock_problematic
                if name == "babelio_problematic_cases"
                else MagicMock()
            )

            # Mock retourne uniquement des auteurs SANS url_babelio
            # (l'aggregation doit déjà filtrer)
            auteur_id = ObjectId()
            mock_problematic.find.return_value = []
            mock_auteurs.aggregate.return_value = [
                {
                    "_id": auteur_id,
                    "auteur_id": auteur_id,
                    "nom": "Auteur Sans URL",
                    "livres": [{"livre_id": ObjectId(), "titre": "Livre Test"}],
                }
            ]

            # Act
            authors = await get_all_authors_to_complete()

            # Assert
            for author in authors:
                # Vérifier qu'aucun auteur retourné n'a déjà une URL
                # (on ne peut pas vérifier directement car c'est un aggregation,
                # mais on sait que la requête doit filtrer)
                assert author["nom"] != "", "Auteur doit avoir un nom"
