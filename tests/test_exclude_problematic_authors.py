"""Tests TDD pour exclure les auteurs problématiques - Issue #124.

get_all_authors_to_complete() ne doit PAS retourner les auteurs
qui sont déjà dans babelio_problematic_cases.
"""

from unittest.mock import MagicMock, patch

import pytest
from bson import ObjectId


class TestExcludeProblematicAuthors:
    """Tests pour exclure les auteurs déjà problématiques."""

    @pytest.mark.asyncio
    async def test_should_exclude_authors_already_in_problematic_cases(self):
        """Test TDD: Ne pas retourner les auteurs déjà problématiques.

        Problème production:
        - Pascale Robert-Diard est dans babelio_problematic_cases
        - get_all_authors_to_complete() le retourne quand même
        - Résultat: doublon créé dans problematic_cases

        Solution:
        - Filtrer les auteurs dont l'ID est dans problematic_cases avec type='auteur'
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

            # 2 auteurs sans URL
            auteur1_id = ObjectId()
            auteur2_id = ObjectId()

            # Auteur1 est déjà problématique
            mock_problematic.find.return_value = [
                {
                    "_id": ObjectId(),
                    "type": "auteur",
                    "auteur_id": str(auteur1_id),
                    "nom_auteur": "Pascale Robert-Diard",
                    "nb_livres": 1,
                    "livres_status": "all_problematic",
                    "raison": "Test",
                }
            ]

            # Mock aggregate pour retourner 2 auteurs
            # IMPORTANT: Doit inclure "auteur_id" projeté par l'aggregation
            mock_auteurs.aggregate.return_value = [
                {
                    "_id": auteur1_id,
                    "auteur_id": auteur1_id,  # Projeté par l'aggregation
                    "nom": "Pascale Robert-Diard",
                    "livres": [{"livre_id": ObjectId(), "titre": "La petite menteuse"}],
                },
                {
                    "_id": auteur2_id,
                    "auteur_id": auteur2_id,  # Projeté par l'aggregation
                    "nom": "S. A. Cosby",
                    "livres": [{"livre_id": ObjectId(), "titre": "Le Roi des cendres"}],
                },
            ]

            # Act
            authors = await get_all_authors_to_complete()

            # Assert
            # Seul S. A. Cosby doit être retourné (pas Pascale Robert-Diard)
            assert len(authors) == 1, (
                "Doit retourner 1 seul auteur (pas le problématique)"
            )
            assert authors[0]["nom"] == "S. A. Cosby", (
                "Doit retourner S. A. Cosby (pas Pascale Robert-Diard qui est problématique)"
            )
