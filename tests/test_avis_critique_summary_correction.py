"""Tests pour issue #67: Mise à jour du summary après validation.

Quand un livre/auteur est validé, on doit:
1. Sauvegarder le summary original dans summary_origin (si pas déjà fait)
2. Mettre à jour le summary avec les données corrigées
3. Préserver l'intégrité des tableaux markdown (pas de casse)
"""

from unittest.mock import Mock, patch

from back_office_lmelp.services.collections_management_service import (
    CollectionsManagementService,
)
from tests.fixtures.avis_critique_summary_samples import TEST_CASES


def create_mocked_service():
    """Crée un service avec tous les mocks configurés.

    Pattern recommandé pour tester des services avec dépendances injectées.
    Évite les problèmes de pytest fixtures avec patch.object().
    """
    from bson import ObjectId

    service = CollectionsManagementService()

    # Mock mongodb_service
    mock_mongodb = Mock()
    mock_mongodb.create_author_if_not_exists.return_value = ObjectId(
        "507f1f77bcf86cd799439014"  # pragma: allowlist secret
    )
    mock_mongodb.create_book_if_not_exists.return_value = ObjectId(
        "507f1f77bcf86cd799439015"  # pragma: allowlist secret
    )
    mock_mongodb.update_book_validation.return_value = None
    mock_mongodb.update_avis_critique = Mock(return_value=True)
    mock_mongodb.get_avis_critique_by_id.return_value = None

    # Mock les collections MongoDB nécessaires
    mock_mongodb.avis_critiques_collection = Mock()
    mock_mongodb.livres_collection = Mock()
    mock_mongodb.auteurs_collection = Mock()

    service.mongodb_service = mock_mongodb
    service._mock_mongodb = mock_mongodb  # Pour accès dans les tests

    return service


def patch_cache_service(is_already_corrected=False):
    """Retourne un context manager qui patche l'instance globale livres_auteurs_cache_service.

    IMPORTANT: Utiliser avec le pattern de patch multiple car il retourne 3 patches:
        with patch_cache_service():
            # code...

    Args:
        is_already_corrected: Si True, is_summary_corrected() retourne True (test idempotence)

    Returns:
        Context manager pour patcher les 3 méthodes du cache service
    """
    from unittest.mock import patch as mock_patch

    return (
        mock_patch(
            "back_office_lmelp.services.livres_auteurs_cache_service.livres_auteurs_cache_service.mark_as_processed",
            return_value=True,
        ),
        mock_patch(
            "back_office_lmelp.services.livres_auteurs_cache_service.livres_auteurs_cache_service.is_summary_corrected",
            return_value=is_already_corrected,
        ),
        mock_patch(
            "back_office_lmelp.services.livres_auteurs_cache_service.livres_auteurs_cache_service.mark_summary_corrected",
            return_value=True,
        ),
    )


class TestAvisCritiqueSummaryCorrection:
    """Tests pour la mise à jour du summary après validation (Issue #67)."""

    def test_should_backup_summary_to_summary_origin_on_first_validation(self):
        """
        Test TDD: Lors de la première validation, sauvegarder summary → summary_origin.
        """
        # Arrange
        service = create_mocked_service()
        test_case = TEST_CASES["single_book_author_error"]
        original_summary = test_case["original"]

        book_data = {
            "cache_id": "507f1f77bcf86cd799439011",  # pragma: allowlist secret
            "avis_critique_id": "507f1f77bcf86cd799439012",  # pragma: allowlist secret
            "episode_oid": "507f1f77bcf86cd799439013",  # pragma: allowlist secret
            "auteur": test_case["book"]["auteur"],
            "titre": test_case["book"]["titre"],
            "editeur": test_case["book"]["editeur"],
            "user_validated_author": test_case["correction"]["auteur"],
            "user_validated_title": test_case["correction"]["titre"],
        }

        # Mock pour simuler qu'il n'y a pas encore de summary_origin
        service._mock_mongodb.get_avis_critique_by_id.return_value = {
            "_id": "507f1f77bcf86cd799439012",  # pragma: allowlist secret
            "episode_oid": "507f1f77bcf86cd799439013",  # pragma: allowlist secret
            "summary": original_summary,
            # Pas de summary_origin
        }

        # Patcher l'instance globale de livres_auteurs_cache_service
        patches = patch_cache_service()
        with patches[0], patches[1], patches[2]:
            # Act
            service.handle_book_validation(book_data)

            # Assert
            # Vérifier qu'on a appelé update_avis_critique
            assert service._mock_mongodb.update_avis_critique.called
            call_args = service._mock_mongodb.update_avis_critique.call_args[0]
            avis_id = call_args[0]
            updates = call_args[1]

            assert avis_id == "507f1f77bcf86cd799439012"  # pragma: allowlist secret
            assert "summary_origin" in updates
            assert updates["summary_origin"] == original_summary

    def test_should_not_overwrite_existing_summary_origin(self):
        """
        Test: Si summary_origin existe déjà, ne pas l'écraser (idempotence).
        """
        # Arrange
        service = create_mocked_service()
        test_case = TEST_CASES["single_book_author_error"]

        book_data = {
            "cache_id": "507f1f77bcf86cd799439011",  # pragma: allowlist secret
            "avis_critique_id": "507f1f77bcf86cd799439012",  # pragma: allowlist secret
            "episode_oid": "507f1f77bcf86cd799439013",  # pragma: allowlist secret
            "auteur": test_case["book"]["auteur"],
            "titre": test_case["book"]["titre"],
            "editeur": test_case["book"]["editeur"],
            "user_validated_author": test_case["correction"]["auteur"],
            "user_validated_title": test_case["correction"]["titre"],
        }

        # Mock avec summary_origin déjà présent
        service._mock_mongodb.get_avis_critique_by_id.return_value = {
            "_id": "507f1f77bcf86cd799439012",  # pragma: allowlist secret
            "episode_oid": "507f1f77bcf86cd799439013",  # pragma: allowlist secret
            "summary": test_case["corrected"],  # Déjà corrigé
            "summary_origin": test_case["original"],  # Original préservé
        }

        # Patcher l'instance globale de livres_auteurs_cache_service
        patches = patch_cache_service()
        with patches[0], patches[1], patches[2]:
            # Act
            service.handle_book_validation(book_data)

            # Assert
            call_args = service._mock_mongodb.update_avis_critique.call_args[0]
            updates = call_args[1]

            # summary_origin ne doit PAS être dans les updates (déjà présent)
            assert "summary_origin" not in updates

    def test_should_update_summary_with_corrected_author(self):
        """
        Test TDD: Mettre à jour summary avec l'auteur corrigé.
        """
        # Arrange
        service = create_mocked_service()
        test_case = TEST_CASES["single_book_author_error"]

        book_data = {
            "cache_id": "507f1f77bcf86cd799439011",  # pragma: allowlist secret
            "avis_critique_id": "507f1f77bcf86cd799439012",  # pragma: allowlist secret
            "episode_oid": "507f1f77bcf86cd799439013",  # pragma: allowlist secret
            "auteur": test_case["book"]["auteur"],
            "titre": test_case["book"]["titre"],
            "editeur": test_case["book"]["editeur"],
            "user_validated_author": test_case["correction"]["auteur"],
            "user_validated_title": test_case["correction"]["titre"],
        }

        service._mock_mongodb.get_avis_critique_by_id.return_value = {
            "_id": "507f1f77bcf86cd799439012",  # pragma: allowlist secret
            "episode_oid": "507f1f77bcf86cd799439013",  # pragma: allowlist secret
            "summary": test_case["original"],
        }

        # Patcher l'instance globale de livres_auteurs_cache_service
        patches = patch_cache_service()
        with patches[0], patches[1], patches[2]:
            # Act
            service.handle_book_validation(book_data)

            # Assert
            call_args = service._mock_mongodb.update_avis_critique.call_args[0]
            updates = call_args[1]

            assert "summary" in updates
            # Le summary doit correspondre exactement au résultat attendu
            assert updates["summary"] == test_case["corrected"]

    def test_should_preserve_markdown_table_structure(self):
        """
        Test CRITIQUE: Vérifier que la mise à jour ne casse pas les tableaux markdown.
        """
        # Arrange
        service = create_mocked_service()
        test_case = TEST_CASES["single_book_author_error"]

        book_data = {
            "cache_id": "507f1f77bcf86cd799439011",  # pragma: allowlist secret
            "avis_critique_id": "507f1f77bcf86cd799439012",  # pragma: allowlist secret
            "episode_oid": "507f1f77bcf86cd799439013",  # pragma: allowlist secret
            "auteur": test_case["book"]["auteur"],
            "titre": test_case["book"]["titre"],
            "editeur": test_case["book"]["editeur"],
            "user_validated_author": test_case["correction"]["auteur"],
            "user_validated_title": test_case["correction"]["titre"],
        }

        service._mock_mongodb.get_avis_critique_by_id.return_value = {
            "_id": "507f1f77bcf86cd799439012",  # pragma: allowlist secret
            "episode_oid": "507f1f77bcf86cd799439013",  # pragma: allowlist secret
            "summary": test_case["original"],
        }

        # Patcher l'instance globale de livres_auteurs_cache_service
        patches = patch_cache_service()
        with patches[0], patches[1], patches[2]:
            # Act
            service.handle_book_validation(book_data)

            # Assert
            call_args = service._mock_mongodb.update_avis_critique.call_args[0]
            updated_summary = call_args[1]["summary"]

            # Vérifier que le nombre de pipes (|) n'a pas changé
            original_pipe_count = test_case["original"].count("|")
            updated_pipe_count = updated_summary.count("|")
            assert updated_pipe_count == original_pipe_count, (
                "Le nombre de pipes a changé, la structure du tableau est cassée"
            )

            # Vérifier que le nombre de lignes n'a pas changé
            original_line_count = test_case["original"].count("\n")
            updated_line_count = updated_summary.count("\n")
            assert updated_line_count == original_line_count, (
                "Le nombre de lignes a changé"
            )

    def test_should_handle_multiple_books_selectively(self):
        """
        Test: Mettre à jour seulement le livre validé, pas les autres.
        """
        # Arrange
        service = create_mocked_service()
        test_case = TEST_CASES["multiple_books_first_corrected"]

        book_data = {
            "cache_id": "507f1f77bcf86cd799439011",  # pragma: allowlist secret
            "avis_critique_id": "507f1f77bcf86cd799439012",  # pragma: allowlist secret
            "episode_oid": "507f1f77bcf86cd799439013",  # pragma: allowlist secret
            "auteur": test_case["book"]["auteur"],
            "titre": test_case["book"]["titre"],
            "editeur": test_case["book"]["editeur"],
            "user_validated_author": test_case["correction"]["auteur"],
            "user_validated_title": test_case["correction"]["titre"],
        }

        service._mock_mongodb.get_avis_critique_by_id.return_value = {
            "_id": "507f1f77bcf86cd799439012",  # pragma: allowlist secret
            "episode_oid": "507f1f77bcf86cd799439013",  # pragma: allowlist secret
            "summary": test_case["original"],
        }

        # Patcher l'instance globale de livres_auteurs_cache_service
        patches = patch_cache_service()
        with patches[0], patches[1], patches[2]:
            # Act
            service.handle_book_validation(book_data)

            # Assert
            call_args = service._mock_mongodb.update_avis_critique.call_args[0]
            updated_summary = call_args[1]["summary"]

            # Le premier livre doit être corrigé
            assert "Alain Mabanckou" in updated_summary
            assert "Alain Mabancou" not in updated_summary

            # Les autres livres ne doivent PAS être modifiés
            assert "Adrien Bosque" in updated_summary  # Pas encore corrigé
            assert "Amélie Nothomb" in updated_summary  # Correct dès le départ

    def test_should_handle_title_case_correction(self):
        """
        Test: Correction de la casse d'un titre (majuscules/minuscules).
        """
        # Arrange
        service = create_mocked_service()
        test_case = TEST_CASES["title_case_correction"]

        book_data = {
            "cache_id": "507f1f77bcf86cd799439011",  # pragma: allowlist secret
            "avis_critique_id": "507f1f77bcf86cd799439012",  # pragma: allowlist secret
            "episode_oid": "507f1f77bcf86cd799439013",  # pragma: allowlist secret
            "auteur": test_case["book"]["auteur"],
            "titre": test_case["book"]["titre"],
            "editeur": test_case["book"]["editeur"],
            "user_validated_author": test_case["correction"]["auteur"],
            "user_validated_title": test_case["correction"]["titre"],
        }

        service._mock_mongodb.get_avis_critique_by_id.return_value = {
            "_id": "507f1f77bcf86cd799439012",  # pragma: allowlist secret
            "episode_oid": "507f1f77bcf86cd799439013",  # pragma: allowlist secret
            "summary": test_case["original"],
        }

        # Patcher l'instance globale de livres_auteurs_cache_service
        patches = patch_cache_service()
        with patches[0], patches[1], patches[2]:
            # Act
            service.handle_book_validation(book_data)

            # Assert
            call_args = service._mock_mongodb.update_avis_critique.call_args[0]
            updated_summary = call_args[1]["summary"]

            assert updated_summary == test_case["corrected"]
            # "La Maison Vide" → "La Maison vide"
            assert "La Maison vide" in updated_summary
            assert "La Maison Vide" not in updated_summary

    def test_should_handle_summary_with_coups_de_coeur_section(self):
        """
        Test: Mettre à jour un summary avec section "Coups de cœur".
        """
        # Arrange
        service = create_mocked_service()
        test_case = TEST_CASES["with_coups_de_coeur"]

        book_data = {
            "cache_id": "507f1f77bcf86cd799439011",  # pragma: allowlist secret
            "avis_critique_id": "507f1f77bcf86cd799439012",  # pragma: allowlist secret
            "episode_oid": "507f1f77bcf86cd799439013",  # pragma: allowlist secret
            "auteur": test_case["book"]["auteur"],
            "titre": test_case["book"]["titre"],
            "editeur": test_case["book"]["editeur"],
            "user_validated_author": test_case["correction"]["auteur"],
            "user_validated_title": test_case["correction"]["titre"],
        }

        service._mock_mongodb.get_avis_critique_by_id.return_value = {
            "_id": "507f1f77bcf86cd799439012",  # pragma: allowlist secret
            "episode_oid": "507f1f77bcf86cd799439013",  # pragma: allowlist secret
            "summary": test_case["original"],
        }

        # Patcher l'instance globale de livres_auteurs_cache_service
        patches = patch_cache_service()
        with patches[0], patches[1], patches[2]:
            # Act
            service.handle_book_validation(book_data)

            # Assert
            call_args = service._mock_mongodb.update_avis_critique.call_args[0]
            updated_summary = call_args[1]["summary"]

            # Auteur corrigé dans section 1
            assert "Aslak Nordström" in updated_summary
            assert "| Aslak Nord |" not in updated_summary  # Exact match avec pipes

            # Section 2 "Coups de cœur" préservée intacte
            assert "## 2. COUPS DE CŒUR DES CRITIQUES" in updated_summary
            assert "Jérôme Leroy" in updated_summary

    def test_should_skip_summary_update_if_no_avis_critique_id(self):
        """
        Test: Si pas d'avis_critique_id, ne pas essayer de mettre à jour le summary.
        """
        # Arrange
        service = create_mocked_service()

        book_data = {
            "cache_id": "507f1f77bcf86cd799439011",  # pragma: allowlist secret
            # Pas d'avis_critique_id
            "episode_oid": "507f1f77bcf86cd799439013",  # pragma: allowlist secret
            "auteur": "Alain Mabancou",
            "titre": "Ramsès de Paris",
            "editeur": "Seuil",
            "user_validated_author": "Alain Mabanckou",
        }

        # Patcher l'instance globale de livres_auteurs_cache_service
        patches = patch_cache_service()
        with patches[0], patches[1], patches[2]:
            # Act
            service.handle_book_validation(book_data)

            # Assert
            # Ne doit PAS appeler update_avis_critique
            service._mock_mongodb.update_avis_critique.assert_not_called()
            # Mais doit quand même créer l'auteur et le livre
            service._mock_mongodb.create_author_if_not_exists.assert_called_once()
            service._mock_mongodb.create_book_if_not_exists.assert_called_once()

    def test_should_mark_summary_corrected_true_in_cache_after_update(self):
        """
        Test TDD: Après mise à jour du summary, marquer summary_corrected=True dans le cache.
        """
        # Arrange
        service = create_mocked_service()
        test_case = TEST_CASES["single_book_author_error"]

        book_data = {
            "cache_id": "507f1f77bcf86cd799439011",  # pragma: allowlist secret
            "avis_critique_id": "507f1f77bcf86cd799439012",  # pragma: allowlist secret
            "episode_oid": "507f1f77bcf86cd799439013",  # pragma: allowlist secret
            "auteur": test_case["book"]["auteur"],
            "titre": test_case["book"]["titre"],
            "editeur": test_case["book"]["editeur"],
            "user_validated_author": test_case["correction"]["auteur"],
            "user_validated_title": test_case["correction"]["titre"],
        }

        service._mock_mongodb.get_avis_critique_by_id.return_value = {
            "_id": "507f1f77bcf86cd799439012",  # pragma: allowlist secret
            "episode_oid": "507f1f77bcf86cd799439013",  # pragma: allowlist secret
            "summary": test_case["original"],
        }

        # Patcher l'instance globale + vérifier mark_summary_corrected appelé
        patches = patch_cache_service()
        with (
            patches[0],
            patches[1],
            patch(
                "back_office_lmelp.services.livres_auteurs_cache_service.livres_auteurs_cache_service.mark_summary_corrected"
            ) as mock_mark,
        ):
            mock_mark.return_value = True

            # Act
            service.handle_book_validation(book_data)

            # Assert
            # Vérifier que summary_corrected a été marqué à True
            mock_mark.assert_called_once()
            call_args = mock_mark.call_args[0]
            cache_id = call_args[0]
            assert str(cache_id) == "507f1f77bcf86cd799439011"

    def test_should_skip_summary_update_if_already_corrected(self):
        """
        Test IDEMPOTENCE: Si summary_corrected=True, ne pas re-traiter le summary.
        """
        # Arrange
        service = create_mocked_service()
        test_case = TEST_CASES["single_book_author_error"]

        book_data = {
            "cache_id": "507f1f77bcf86cd799439011",  # pragma: allowlist secret
            "avis_critique_id": "507f1f77bcf86cd799439012",  # pragma: allowlist secret
            "episode_oid": "507f1f77bcf86cd799439013",  # pragma: allowlist secret
            "auteur": test_case["book"]["auteur"],
            "titre": test_case["book"]["titre"],
            "editeur": test_case["book"]["editeur"],
            "user_validated_author": test_case["correction"]["auteur"],
            "user_validated_title": test_case["correction"]["titre"],
        }

        # Mock avis_critique déjà corrigé
        service._mock_mongodb.get_avis_critique_by_id.return_value = {
            "_id": "507f1f77bcf86cd799439012",  # pragma: allowlist secret
            "episode_oid": "507f1f77bcf86cd799439013",  # pragma: allowlist secret
            "summary": test_case["corrected"],  # Déjà corrigé
            "summary_origin": test_case["original"],
        }

        # Patcher avec is_already_corrected=True pour test idempotence
        patches = patch_cache_service(is_already_corrected=True)
        with patches[0], patches[1], patches[2]:
            # Act
            service.handle_book_validation(book_data)

            # Assert
            # Ne doit PAS mettre à jour le summary (déjà fait)
            service._mock_mongodb.update_avis_critique.assert_not_called()

    def test_should_update_summary_if_corrected_false(self):
        """
        Test: Si summary_corrected=False, traiter le summary.
        """
        # Arrange
        service = create_mocked_service()
        test_case = TEST_CASES["single_book_author_error"]

        book_data = {
            "cache_id": "507f1f77bcf86cd799439011",  # pragma: allowlist secret
            "avis_critique_id": "507f1f77bcf86cd799439012",  # pragma: allowlist secret
            "episode_oid": "507f1f77bcf86cd799439013",  # pragma: allowlist secret
            "auteur": test_case["book"]["auteur"],
            "titre": test_case["book"]["titre"],
            "editeur": test_case["book"]["editeur"],
            "user_validated_author": test_case["correction"]["auteur"],
            "user_validated_title": test_case["correction"]["titre"],
        }

        service._mock_mongodb.get_avis_critique_by_id.return_value = {
            "_id": "507f1f77bcf86cd799439012",  # pragma: allowlist secret
            "episode_oid": "507f1f77bcf86cd799439013",  # pragma: allowlist secret
            "summary": test_case["original"],
        }

        # Patcher l'instance globale (is_summary_corrected=False par défaut)
        patches = patch_cache_service()
        with patches[0], patches[1], patches[2]:
            # Act
            service.handle_book_validation(book_data)

            # Assert
            # DOIT mettre à jour le summary
            assert service._mock_mongodb.update_avis_critique.called

    def test_should_update_summary_if_corrected_field_missing(self):
        """
        Test: Si le champ summary_corrected n'existe pas, traiter le summary.
        """
        # Arrange
        service = create_mocked_service()
        test_case = TEST_CASES["single_book_author_error"]

        book_data = {
            "cache_id": "507f1f77bcf86cd799439011",  # pragma: allowlist secret
            "avis_critique_id": "507f1f77bcf86cd799439012",  # pragma: allowlist secret
            "episode_oid": "507f1f77bcf86cd799439013",  # pragma: allowlist secret
            "auteur": test_case["book"]["auteur"],
            "titre": test_case["book"]["titre"],
            "editeur": test_case["book"]["editeur"],
            "user_validated_author": test_case["correction"]["auteur"],
            "user_validated_title": test_case["correction"]["titre"],
        }

        service._mock_mongodb.get_avis_critique_by_id.return_value = {
            "_id": "507f1f77bcf86cd799439012",  # pragma: allowlist secret
            "episode_oid": "507f1f77bcf86cd799439013",  # pragma: allowlist secret
            "summary": test_case["original"],
        }

        # Patcher l'instance globale (is_summary_corrected=False par défaut = champ manquant)
        patches = patch_cache_service()
        with patches[0], patches[1], patches[2]:
            # Act
            service.handle_book_validation(book_data)

            # Assert
            # DOIT mettre à jour le summary
            assert service._mock_mongodb.update_avis_critique.called
