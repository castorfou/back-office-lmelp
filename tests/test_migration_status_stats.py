"""Tests TDD pour les statistiques de migration - Issue #124.

Les auteurs doivent avoir leur propre compteur "à traiter manuellement" et "absents de Babelio".
"""

from unittest.mock import MagicMock


class TestMigrationStatusStats:
    """Tests pour les compteurs de problematic authors/books."""

    def test_should_count_problematic_books_by_type_livre(self):
        """Test TDD: problematic_count doit compter uniquement les entrées avec type='livre'.

        Problème production:
        - problematic_count compte TOUS les documents de babelio_problematic_cases
        - Inclut les auteurs problématiques dans le compte des livres
        - Le compteur "Livres à traiter manuellement" est faux

        Solution:
        - Compter uniquement les documents avec type='livre'
        """
        # Arrange
        from back_office_lmelp.services.babelio_migration_service import (
            BabelioMigrationService,
        )
        from back_office_lmelp.services.babelio_service import BabelioService
        from back_office_lmelp.services.mongodb_service import MongoDBService

        mock_mongodb_service = MagicMock(spec=MongoDBService)
        mock_babelio_service = MagicMock(spec=BabelioService)

        # Mock individual collections
        mock_livres = MagicMock()
        mock_auteurs = MagicMock()
        mock_problematic = MagicMock()

        # Setup DB getter to return correct collections
        def get_collection_mock(key):
            collections = {
                "livres": mock_livres,
                "auteurs": mock_auteurs,
                "babelio_problematic_cases": mock_problematic,
            }
            return collections.get(key)

        mock_db = MagicMock()
        mock_db.__getitem__.side_effect = get_collection_mock
        mock_mongodb_service.db = mock_db

        service = BabelioMigrationService(mock_mongodb_service, mock_babelio_service)

        # Simuler 3 livres problématiques
        mock_problematic.count_documents.return_value = 3

        # Simuler les autres compteurs
        mock_livres.count_documents.side_effect = [
            500,
            490,
            5,
        ]  # total, migrated, not_found
        mock_auteurs.count_documents.side_effect = [
            400,
            380,
            0,
        ]  # total, with_url, not_found
        mock_livres.find_one.return_value = None

        # Mock get_problematic_cases pour retourner 3 livres
        service.get_problematic_cases = MagicMock(
            return_value=[{"livre_id": "1"}, {"livre_id": "2"}, {"livre_id": "3"}]
        )

        # Act
        status = service.get_migration_status()

        # Assert
        assert status["problematic_count"] == 3, (
            "Doit compter uniquement les livres problématiques (type='livre')"
        )
        # Vérifier que count_documents a été appelé avec le bon filtre
        calls = mock_problematic.count_documents.call_args_list
        assert any(call[0][0] == {"type": "livre"} for call in calls), (
            "Doit appeler count_documents avec type='livre'"
        )

    def test_should_add_problematic_authors_count(self):
        """Test TDD: Ajouter problematic_authors_count pour les auteurs à traiter.

        Nouveau champ nécessaire pour l'UI:
        - "Auteurs à traiter manuellement"
        - Compte les documents avec type='auteur' dans babelio_problematic_cases
        """
        # Arrange
        from back_office_lmelp.services.babelio_migration_service import (
            BabelioMigrationService,
        )
        from back_office_lmelp.services.babelio_service import BabelioService
        from back_office_lmelp.services.mongodb_service import MongoDBService

        mock_mongodb_service = MagicMock(spec=MongoDBService)
        mock_babelio_service = MagicMock(spec=BabelioService)

        # Mock individual collections
        mock_livres = MagicMock()
        mock_auteurs = MagicMock()
        mock_problematic = MagicMock()

        def get_collection_mock(key):
            collections = {
                "livres": mock_livres,
                "auteurs": mock_auteurs,
                "babelio_problematic_cases": mock_problematic,
            }
            return collections.get(key)

        mock_db = MagicMock()
        mock_db.__getitem__.side_effect = get_collection_mock
        mock_mongodb_service.db = mock_db

        service = BabelioMigrationService(mock_mongodb_service, mock_babelio_service)

        # Simuler 1 livre et 2 auteurs problématiques
        mock_problematic.count_documents.side_effect = [1, 2]  # livre, auteur

        # Simuler les autres compteurs
        mock_livres.count_documents.side_effect = [
            500,
            490,
            5,
        ]  # total, migrated, not_found
        mock_auteurs.count_documents.side_effect = [
            400,
            380,
            0,
        ]  # total, with_url, not_found
        mock_livres.find_one.return_value = None

        service.get_problematic_cases = MagicMock(return_value=[{"livre_id": "1"}])

        # Act
        status = service.get_migration_status()

        # Assert
        assert "problematic_authors_count" in status, (
            "Doit retourner problematic_authors_count"
        )
        assert status["problematic_authors_count"] == 2, (
            "Doit compter 2 auteurs problématiques (type='auteur')"
        )
        # Vérifier les appels
        calls = mock_problematic.count_documents.call_args_list
        assert any(call[0][0] == {"type": "livre"} for call in calls), (
            "Doit appeler count_documents avec type='livre'"
        )
        assert any(call[0][0] == {"type": "auteur"} for call in calls), (
            "Doit appeler count_documents avec type='auteur'"
        )

    def test_should_add_authors_not_found_count(self):
        """Test TDD: Ajouter authors_not_found_count (auteurs absents de Babelio).

        Équivalent de not_found_count pour les livres:
        - Compter les auteurs avec babelio_not_found=True
        """
        # Arrange
        from back_office_lmelp.services.babelio_migration_service import (
            BabelioMigrationService,
        )
        from back_office_lmelp.services.babelio_service import BabelioService
        from back_office_lmelp.services.mongodb_service import MongoDBService

        mock_mongodb_service = MagicMock(spec=MongoDBService)
        mock_babelio_service = MagicMock(spec=BabelioService)

        # Mock individual collections
        mock_livres = MagicMock()
        mock_auteurs = MagicMock()
        mock_problematic = MagicMock()

        def get_collection_mock(key):
            collections = {
                "livres": mock_livres,
                "auteurs": mock_auteurs,
                "babelio_problematic_cases": mock_problematic,
            }
            return collections.get(key)

        mock_db = MagicMock()
        mock_db.__getitem__.side_effect = get_collection_mock
        mock_mongodb_service.db = mock_db

        service = BabelioMigrationService(mock_mongodb_service, mock_babelio_service)

        # Simuler les compteurs
        mock_problematic.count_documents.side_effect = [1, 0]  # livre, auteur
        mock_livres.count_documents.side_effect = [
            500,
            490,
            5,
        ]  # total, migrated, not_found
        mock_auteurs.count_documents.side_effect = [
            400,
            380,
            3,
        ]  # total, with_url, not_found ← Ce que nous testons
        mock_livres.find_one.return_value = None

        service.get_problematic_cases = MagicMock(return_value=[{"livre_id": "1"}])

        # Act
        status = service.get_migration_status()

        # Assert
        assert "authors_not_found_count" in status, (
            "Doit retourner authors_not_found_count"
        )
        assert status["authors_not_found_count"] == 3, (
            "Doit compter 3 auteurs marqués babelio_not_found"
        )
        # Vérifier que count_documents a été appelé avec le bon filtre
        calls = mock_auteurs.count_documents.call_args_list
        assert any(call[0][0] == {"babelio_not_found": True} for call in calls), (
            "Doit appeler count_documents avec babelio_not_found=True"
        )

    def test_should_recalculate_authors_without_url_babelio(self):
        """Test TDD: authors_without_url_babelio doit exclure les not_found et problématiques.

        Logique:
        authors_without_url_babelio = total - with_url - not_found - problematic
        (équivalent de pending_count pour les livres)
        """
        # Arrange
        from back_office_lmelp.services.babelio_migration_service import (
            BabelioMigrationService,
        )
        from back_office_lmelp.services.babelio_service import BabelioService
        from back_office_lmelp.services.mongodb_service import MongoDBService

        mock_mongodb_service = MagicMock(spec=MongoDBService)
        mock_babelio_service = MagicMock(spec=BabelioService)

        # Mock individual collections
        mock_livres = MagicMock()
        mock_auteurs = MagicMock()
        mock_problematic = MagicMock()

        def get_collection_mock(key):
            collections = {
                "livres": mock_livres,
                "auteurs": mock_auteurs,
                "babelio_problematic_cases": mock_problematic,
            }
            return collections.get(key)

        mock_db = MagicMock()
        mock_db.__getitem__.side_effect = get_collection_mock
        mock_mongodb_service.db = mock_db

        service = BabelioMigrationService(mock_mongodb_service, mock_babelio_service)

        # Simuler les compteurs
        mock_problematic.count_documents.side_effect = [
            1,
            2,
        ]  # livre, auteur (problematic)
        mock_livres.count_documents.side_effect = [
            500,
            490,
            5,
        ]  # total, migrated, not_found
        mock_auteurs.count_documents.side_effect = [
            400,
            380,
            3,
        ]  # total, with_url, not_found
        mock_livres.find_one.return_value = None

        service.get_problematic_cases = MagicMock(return_value=[{"livre_id": "1"}])

        # Act
        status = service.get_migration_status()

        # Assert
        # total=400, with_url=380, not_found=3, problematic=2
        # without_url = 400 - 380 - 3 - 2 = 15
        assert status["authors_without_url_babelio"] == 15, (
            "Doit calculer authors_without_url = total - with_url - not_found - problematic"
        )
