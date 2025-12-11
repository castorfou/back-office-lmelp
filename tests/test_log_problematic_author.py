"""Tests TDD pour log_problematic_author() - Issue #124.

Séparer le logging des auteurs problématiques des livres problématiques.
"""

from unittest.mock import MagicMock, patch

from bson import ObjectId


class TestLogProblematicAuthor:
    """Tests pour logger un auteur problématique dans MongoDB."""

    def test_should_log_author_with_type_auteur(self):
        """Test TDD: Logger un auteur doit créer un document avec type='auteur'.

        Problème production:
        - Auteurs loggés avec les champs de livre (livre_id, titre_attendu)
        - Impossible de distinguer livres et auteurs dans la collection

        Solution:
        - Champ type='auteur' pour identifier le document
        - auteur_id au lieu de livre_id
        - nom_auteur au lieu de titre_attendu
        """
        # Arrange
        from scripts.migration_donnees.migrate_url_babelio import (
            log_problematic_author,
        )

        auteur_id = ObjectId()
        nom_auteur = "Club des Poètes"
        nb_livres = 1
        livres_status = "all_not_found"
        raison = "Tous les livres sont absents de Babelio"

        with patch(
            "scripts.migration_donnees.migrate_url_babelio.mongodb_service"
        ) as mock_service:
            mock_collection = MagicMock()
            mock_service.get_collection.return_value = mock_collection

            # Act
            log_problematic_author(
                auteur_id=auteur_id,
                nom_auteur=nom_auteur,
                nb_livres=nb_livres,
                livres_status=livres_status,
                raison=raison,
            )

            # Assert
            mock_collection.insert_one.assert_called_once()
            inserted_doc = mock_collection.insert_one.call_args[0][0]

            assert inserted_doc["type"] == "auteur", "Doit avoir type='auteur'"
            assert inserted_doc["auteur_id"] == str(auteur_id), (
                "Doit stocker auteur_id en string"
            )
            assert inserted_doc["nom_auteur"] == nom_auteur
            assert inserted_doc["nb_livres"] == nb_livres
            assert inserted_doc["livres_status"] == livres_status
            assert inserted_doc["raison"] == raison
            assert "timestamp" in inserted_doc, "Doit avoir un timestamp"

    def test_should_handle_orphan_author(self):
        """Test TDD: Logger un auteur orphelin (sans livres)."""
        # Arrange
        from scripts.migration_donnees.migrate_url_babelio import (
            log_problematic_author,
        )

        auteur_id = ObjectId()
        nom_auteur = "aucun"
        nb_livres = 0
        livres_status = "orphelin"
        raison = "Auteur sans livres liés"

        with patch(
            "scripts.migration_donnees.migrate_url_babelio.mongodb_service"
        ) as mock_service:
            mock_collection = MagicMock()
            mock_service.get_collection.return_value = mock_collection

            # Act
            log_problematic_author(
                auteur_id=auteur_id,
                nom_auteur=nom_auteur,
                nb_livres=nb_livres,
                livres_status=livres_status,
                raison=raison,
            )

            # Assert
            inserted_doc = mock_collection.insert_one.call_args[0][0]
            assert inserted_doc["nb_livres"] == 0
            assert inserted_doc["livres_status"] == "orphelin"

    def test_should_use_same_collection_as_books(self):
        """Test TDD: Doit utiliser la même collection que les livres."""
        # Arrange
        from scripts.migration_donnees.migrate_url_babelio import (
            log_problematic_author,
        )

        with patch(
            "scripts.migration_donnees.migrate_url_babelio.mongodb_service"
        ) as mock_service:
            mock_collection = MagicMock()
            mock_service.get_collection.return_value = mock_collection

            # Act
            log_problematic_author(
                auteur_id=ObjectId(),
                nom_auteur="Test",
                nb_livres=1,
                livres_status="all_not_found",
                raison="Test",
            )

            # Assert
            mock_service.get_collection.assert_called_once_with(
                "babelio_problematic_cases"
            )
