"""Tests TDD pour exclure les auteurs absents de Babelio - Issue #124.

get_all_authors_to_complete() ne doit PAS retourner les auteurs
qui sont marqués babelio_not_found=True.
"""

from unittest.mock import MagicMock, patch

import pytest
from bson import ObjectId


class TestExcludeNotFoundAuthors:
    """Tests pour exclure les auteurs marqués absents de Babelio."""

    @pytest.mark.asyncio
    async def test_should_exclude_authors_marked_as_not_found(self):
        """Test TDD: Ne pas retourner les auteurs avec babelio_not_found=True.

        Problème production:
        - Patrice Delbourg est marqué babelio_not_found=True
        - get_all_authors_to_complete() le retourne quand même
        - Résultat: 5 auteurs traités au lieu de 1

        Solution:
        - Filtrer les auteurs avec babelio_not_found=True dans l'aggregation
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

            # 2 auteurs sans URL retournés par l'aggregation:
            # - auteur2: pas de babelio_not_found (à inclure)
            # - auteur3: babelio_not_found=False (à inclure)
            # Note: auteur1 avec babelio_not_found=True est exclu par le $match
            auteur2_id = ObjectId()
            auteur3_id = ObjectId()

            # Aucun auteur problématique
            mock_problematic.find.return_value = []

            # Mock aggregate pour retourner 2 auteurs
            # IMPORTANT: L'aggregation doit DÉJÀ avoir filtré babelio_not_found
            # Donc on ne retourne que auteur2 et auteur3 (auteur1 exclu par le $match)
            mock_auteurs.aggregate.return_value = [
                {
                    "_id": auteur2_id,
                    "auteur_id": auteur2_id,
                    "nom": "S. A. Cosby",
                    "livres": [{"livre_id": ObjectId(), "titre": "Le Roi des cendres"}],
                },
                {
                    "_id": auteur3_id,
                    "auteur_id": auteur3_id,
                    "nom": "Another Author",
                    "livres": [{"livre_id": ObjectId(), "titre": "Another Book"}],
                },
            ]

            # Act
            authors = await get_all_authors_to_complete()

            # Assert
            # Seuls auteur2 et auteur3 doivent être retournés
            assert len(authors) == 2, (
                "Doit retourner 2 auteurs (pas ceux avec babelio_not_found=True)"
            )
            author_names = {a["nom"] for a in authors}
            assert "S. A. Cosby" in author_names
            assert "Another Author" in author_names

            # Vérifier que l'aggregation a bien été appelée avec le bon filtre
            call_args = mock_auteurs.aggregate.call_args
            pipeline = call_args[0][0]
            match_stage = pipeline[0]
            assert "$match" in match_stage
            # Vérifier que le filtre exclut babelio_not_found
            assert "$and" in match_stage["$match"]
