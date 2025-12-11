"""Tests TDD pour le tri des cas problématiques - Issue #124.

get_problematic_cases() doit retourner les livres PUIS les auteurs.
"""

from unittest.mock import MagicMock

from bson import ObjectId


class TestProblematicCasesSorting:
    """Tests pour le tri des cas problématiques."""

    def test_should_return_books_before_authors(self):
        """Test TDD: Retourner les livres problématiques AVANT les auteurs.

        Problème UI:
        - Les cas sont mélangés (livres et auteurs)
        - Difficile de distinguer les livres des auteurs
        - Besoin d'afficher les livres en premier

        Solution:
        - Trier par type: "livre" d'abord, puis "auteur"
        """
        # Arrange
        from back_office_lmelp.services.babelio_migration_service import (
            BabelioMigrationService,
        )

        mock_mongodb_service = MagicMock()
        mock_babelio_service = MagicMock()

        # Mock collections
        mock_problematic = MagicMock()
        mock_livres = MagicMock()
        mock_db = {
            "babelio_problematic_cases": mock_problematic,
            "livres": mock_livres,
        }
        mock_mongodb_service.db = mock_db

        # Simuler 2 livres et 1 auteur problématiques (dans le désordre)
        livre1_id = str(ObjectId())
        livre2_id = str(ObjectId())
        auteur1_id = str(ObjectId())

        mock_problematic.find.return_value = [
            # Auteur en premier (désordre volontaire)
            {
                "_id": ObjectId(),
                "type": "auteur",
                "auteur_id": auteur1_id,
                "nom_auteur": "Pascale Robert-Diard",
                "nb_livres": 1,
                "raison": "Livres problématiques: ['La petite menteuse']",
            },
            # Livre 1
            {
                "_id": ObjectId(),
                "type": "livre",
                "livre_id": livre1_id,
                "titre_attendu": "Titre A",
                "raison": "Test",
            },
            # Livre 2
            {
                "_id": ObjectId(),
                "type": "livre",
                "livre_id": livre2_id,
                "titre_attendu": "Titre B",
                "raison": "Test",
            },
        ]

        # Mock livres - aucun résolu
        mock_livres.find_one.return_value = None

        service = BabelioMigrationService(mock_mongodb_service, mock_babelio_service)

        # Act
        cases = service.get_problematic_cases()

        # Assert
        assert len(cases) == 3, "Doit retourner 3 cas"

        # Vérifier l'ordre: livres d'abord, puis auteurs
        assert cases[0]["type"] == "livre", "Premier cas doit être un livre"
        assert cases[1]["type"] == "livre", "Deuxième cas doit être un livre"
        assert cases[2]["type"] == "auteur", "Troisième cas doit être un auteur"

        # Vérifier le contenu de l'auteur
        auteur_case = cases[2]
        assert auteur_case["nom_auteur"] == "Pascale Robert-Diard"
        assert auteur_case["nb_livres"] == 1
