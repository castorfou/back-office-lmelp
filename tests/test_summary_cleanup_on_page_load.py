"""Tests TDD pour le ramasse-miettes de summary (Issue #67 - Phase 2).

Ce module teste le cleanup automatique des summaries lors de l'affichage
de la page /livres-auteurs pour un épisode donné.
"""

from unittest.mock import Mock

from bson import ObjectId

from back_office_lmelp.services.collections_management_service import (
    CollectionsManagementService,
)


def create_mocked_service():
    """Crée un service avec mocks MongoDB configurés.

    Pattern recommandé pour tester des services avec dépendances injectées.
    """
    service = CollectionsManagementService()

    # Mock mongodb_service
    mock_mongodb = Mock()
    mock_mongodb.get_avis_critique_by_id.return_value = None
    mock_mongodb.update_avis_critique = Mock(return_value=True)
    mock_mongodb.avis_critiques_collection = Mock()
    mock_mongodb.livres_collection = Mock()

    service.mongodb_service = mock_mongodb
    service._mock_mongodb = mock_mongodb

    return service


def patch_cache_service():
    """Returns patches for livres_auteurs_cache_service singleton."""
    from unittest.mock import patch as mock_patch

    return (
        mock_patch(
            "back_office_lmelp.services.livres_auteurs_cache_service.livres_auteurs_cache_service.get_books_by_episode_oid",
            return_value=[],
        ),
        mock_patch(
            "back_office_lmelp.services.livres_auteurs_cache_service.livres_auteurs_cache_service.is_summary_corrected",
            return_value=False,
        ),
        mock_patch(
            "back_office_lmelp.services.livres_auteurs_cache_service.livres_auteurs_cache_service.mark_summary_corrected",
            return_value=True,
        ),
    )


class TestSummaryCleanupOnPageLoad:
    """Tests pour le ramasse-miettes automatique lors du chargement de page."""

    def test_should_cleanup_mongo_books_without_summary_corrected_flag(self):
        """
        Test 1: Cleanup des livres mongo non corrigés.

        GIVEN un épisode avec 2 livres status=mongo
        AND 1 livre sans flag summary_corrected
        AND ce livre a une correction (auteur original != suggested_author)
        WHEN on appelle cleanup_uncorrected_summaries_for_episode()
        THEN le summary de l'avis_critique est mis à jour avec l'auteur corrigé
        AND le flag summary_corrected est marqué à true
        """
        # Arrange
        service = create_mocked_service()
        episode_oid = "68a3911df8b628e552fdf11f"  # pragma: allowlist secret

        # Mock de l'avis_critique existant
        service._mock_mongodb.get_avis_critique_by_id.return_value = {
            "_id": "68a428c7a2bec98cf44a405f",  # pragma: allowlist secret
            "summary": "## Programme\n\n| Auteur | Titre |\n|--------|-------|\n| Alexandre Lamboreau | Pâture |",
        }

        # Mock des livres de l'épisode
        books = [
            {
                "_id": ObjectId(
                    "68e4760abf26cd8dd9a0a371"  # pragma: allowlist secret
                ),
                "avis_critique_id": ObjectId(
                    "68a428c7a2bec98cf44a405f"  # pragma: allowlist secret
                ),
                "auteur": "Alexandre Lamboreau",  # Original (OCR)
                "titre": "Pâture",
                "suggested_author": "Alexandre Lamborot",  # Corrigé (Phase 0)
                "suggested_title": "Pâture",
                "status": "mongo",
                "summary_corrected": None,  # Pas encore traité
            },
            {
                "_id": ObjectId(
                    "68e4760abf26cd8dd9a0a372"  # pragma: allowlist secret
                ),
                "avis_critique_id": ObjectId(
                    "68a428c7a2bec98cf44a405f"  # pragma: allowlist secret
                ),
                "auteur": "Autre Auteur",
                "titre": "Autre Livre",
                "status": "mongo",
                "summary_corrected": True,  # Déjà traité
            },
        ]

        patches = patch_cache_service()
        with (
            patches[0] as mock_get_books,
            patches[1] as mock_is_corrected,
            patches[2] as mock_mark,
        ):
            mock_get_books.return_value = books
            mock_is_corrected.side_effect = lambda cache_id: cache_id == ObjectId(
                "68e4760abf26cd8dd9a0a372"  # pragma: allowlist secret
            )

            # Act
            stats = service.cleanup_uncorrected_summaries_for_episode(episode_oid)

            # Assert
            assert stats["total_books"] == 2
            assert stats["corrected"] == 1
            assert stats["already_corrected"] == 1
            assert service._mock_mongodb.update_avis_critique.called
            mock_mark.assert_called()

    def test_should_skip_books_already_corrected(self):
        """
        Test 2: Idempotence - Ne pas retraiter les livres déjà corrigés.

        GIVEN un livre status=mongo avec summary_corrected=true
        WHEN on appelle cleanup deux fois
        THEN le summary n'est mis à jour qu'UNE seule fois (idempotence)
        """
        # Arrange
        service = create_mocked_service()
        episode_oid = "68a3911df8b628e552fdf11f"  # pragma: allowlist secret

        books = [
            {
                "_id": ObjectId(
                    "68e4760abf26cd8dd9a0a371"  # pragma: allowlist secret
                ),
                "avis_critique_id": ObjectId(
                    "68a428c7a2bec98cf44a405f"  # pragma: allowlist secret
                ),
                "auteur": "Alexandre Lamboreau",
                "titre": "Pâture",
                "status": "mongo",
                "summary_corrected": True,  # Déjà traité
            }
        ]

        patches = patch_cache_service()
        with (
            patches[0] as mock_get_books,
            patches[1] as mock_is_corrected,
            patches[2],
        ):
            mock_get_books.return_value = books
            mock_is_corrected.return_value = True

            # Act
            stats = service.cleanup_uncorrected_summaries_for_episode(episode_oid)

            # Assert
            assert stats["total_books"] == 1
            assert stats["already_corrected"] == 1
            assert stats["corrected"] == 0
            assert not service._mock_mongodb.update_avis_critique.called

    def test_should_skip_books_without_correction(self):
        """
        Test 3: Ignorer les livres sans correction nécessaire.

        GIVEN un livre où auteur == suggested_author (pas de correction)
        WHEN on appelle cleanup
        THEN le summary n'est PAS mis à jour
        AND le flag summary_corrected est quand même marqué (pour éviter re-vérif)
        """
        # Arrange
        service = create_mocked_service()
        episode_oid = "68a3911df8b628e552fdf11f"  # pragma: allowlist secret

        books = [
            {
                "_id": ObjectId(
                    "68e4760abf26cd8dd9a0a371"  # pragma: allowlist secret
                ),
                "avis_critique_id": ObjectId(
                    "68a428c7a2bec98cf44a405f"  # pragma: allowlist secret
                ),
                "auteur": "Alexandre Lamborot",
                "titre": "Pâture",
                "suggested_author": "Alexandre Lamborot",  # Identique (Phase 0)
                "suggested_title": "Pâture",  # Identique
                "status": "mongo",
                "summary_corrected": None,
            }
        ]

        patches = patch_cache_service()
        with (
            patches[0] as mock_get_books,
            patches[1] as mock_is_corrected,
            patches[2] as mock_mark,
        ):
            mock_get_books.return_value = books
            mock_is_corrected.return_value = False

            # Act
            stats = service.cleanup_uncorrected_summaries_for_episode(episode_oid)

            # Assert
            assert stats["total_books"] == 1
            assert stats["no_correction_needed"] == 1
            assert stats["corrected"] == 0
            assert not service._mock_mongodb.update_avis_critique.called
            # Marquer quand même pour éviter de re-vérifier
            mock_mark.assert_called_once_with(
                ObjectId("68e4760abf26cd8dd9a0a371")  # pragma: allowlist secret
            )

    def test_should_not_block_page_load_on_cleanup_error(self):
        """
        Test 4: Gestion des erreurs sans bloquer.

        GIVEN un livre sans flag et une erreur MongoDB simulée
        WHEN on appelle cleanup
        THEN l'API ne plante pas (pas d'exception propagée)
        AND l'erreur est comptée dans les stats
        """
        # Arrange
        service = create_mocked_service()
        episode_oid = "68a3911df8b628e552fdf11f"  # pragma: allowlist secret

        # Simuler une erreur MongoDB
        service._mock_mongodb.get_avis_critique_by_id.side_effect = Exception(
            "MongoDB error"
        )

        books = [
            {
                "_id": ObjectId(
                    "68e4760abf26cd8dd9a0a371"  # pragma: allowlist secret
                ),
                "avis_critique_id": ObjectId(
                    "68a428c7a2bec98cf44a405f"  # pragma: allowlist secret
                ),
                "auteur": "Alexandre Lamboreau",
                "titre": "Pâture",
                "suggested_author": "Alexandre Lamborot",
                "status": "mongo",
                "summary_corrected": None,
            }
        ]

        patches = patch_cache_service()
        with (
            patches[0] as mock_get_books,
            patches[1] as mock_is_corrected,
            patches[2],
        ):
            mock_get_books.return_value = books
            mock_is_corrected.return_value = False

            # Act - Ne doit pas lever d'exception
            stats = service.cleanup_uncorrected_summaries_for_episode(episode_oid)

            # Assert
            assert stats["total_books"] == 1
            assert stats["errors"] == 1
            assert stats["corrected"] == 0

    def test_should_cleanup_multiple_books_in_same_episode(self):
        """
        Test 5: Traitement multiple dans le même épisode.

        GIVEN 3 livres status=mongo sans flag
        WHEN on appelle cleanup
        THEN les 3 summaries sont mis à jour
        """
        # Arrange
        service = create_mocked_service()
        episode_oid = "68a3911df8b628e552fdf11f"  # pragma: allowlist secret

        service._mock_mongodb.get_avis_critique_by_id.return_value = {
            "_id": "68a428c7a2bec98cf44a405f",  # pragma: allowlist secret
            "summary": "## Programme\n\n| Auteur | Titre |\n|--------|-------|\n| Lamboreau | Pâture |\n| Fabcaro | Figurec |\n| Hinker | Crimi |",
        }

        books = [
            {
                "_id": ObjectId(
                    "68e4760abf26cd8dd9a0a371"  # pragma: allowlist secret
                ),
                "avis_critique_id": ObjectId(
                    "68a428c7a2bec98cf44a405f"  # pragma: allowlist secret
                ),
                "auteur": "Lamboreau",
                "titre": "Pâture",
                "suggested_author": "Lamborot",
                "suggested_title": "Pâture",
                "status": "mongo",
            },
            {
                "_id": ObjectId(
                    "68e4760abf26cd8dd9a0a372"  # pragma: allowlist secret
                ),
                "avis_critique_id": ObjectId(
                    "68a428c7a2bec98cf44a405f"  # pragma: allowlist secret
                ),
                "auteur": "Fabcaro",
                "titre": "Figurec",
                "suggested_author": "Fabrice Caro",
                "suggested_title": "Figurec",
                "status": "mongo",
            },
            {
                "_id": ObjectId(
                    "68e4760abf26cd8dd9a0a373"  # pragma: allowlist secret
                ),
                "avis_critique_id": ObjectId(
                    "68a428c7a2bec98cf44a405f"  # pragma: allowlist secret
                ),
                "auteur": "Hinker",
                "titre": "Crimi",
                "suggested_author": "Alex Hinker",
                "suggested_title": "Crimi",
                "status": "mongo",
            },
        ]

        patches = patch_cache_service()
        with (
            patches[0] as mock_get_books,
            patches[1] as mock_is_corrected,
            patches[2] as mock_mark,
        ):
            mock_get_books.return_value = books
            mock_is_corrected.return_value = False

            # Act
            stats = service.cleanup_uncorrected_summaries_for_episode(episode_oid)

            # Assert
            assert stats["total_books"] == 3
            assert stats["corrected"] == 3
            assert service._mock_mongodb.update_avis_critique.call_count == 3
            assert mock_mark.call_count == 3

    def test_should_handle_books_from_different_avis_critiques(self):
        """
        Test 6: Livres de plusieurs avis_critiques différents.

        GIVEN 2 livres de 2 avis_critiques différents
        WHEN on appelle cleanup
        THEN les 2 avis_critiques sont mis à jour correctement
        """
        # Arrange
        service = create_mocked_service()
        episode_oid = "68a3911df8b628e552fdf11f"  # pragma: allowlist secret

        # Mock pour retourner différents summaries selon l'avis_critique_id
        def mock_get_avis(avis_id):
            if avis_id == "68a428c7a2bec98cf44a405f":  # pragma: allowlist secret
                return {
                    "_id": avis_id,
                    "summary": "| Lamboreau | Pâture |",
                }
            elif avis_id == "68a428c7a2bec98cf44a405e":  # pragma: allowlist secret
                return {
                    "_id": avis_id,
                    "summary": "| Fabcaro | Figurec |",
                }
            return None

        service._mock_mongodb.get_avis_critique_by_id.side_effect = mock_get_avis

        books = [
            {
                "_id": ObjectId(
                    "68e4760abf26cd8dd9a0a371"  # pragma: allowlist secret
                ),
                "avis_critique_id": ObjectId(
                    "68a428c7a2bec98cf44a405f"  # pragma: allowlist secret
                ),
                "auteur": "Lamboreau",
                "titre": "Pâture",
                "suggested_author": "Lamborot",
                "suggested_title": "Pâture",
                "status": "mongo",
            },
            {
                "_id": ObjectId(
                    "68e4760abf26cd8dd9a0a372"  # pragma: allowlist secret
                ),
                "avis_critique_id": ObjectId(
                    "68a428c7a2bec98cf44a405e"  # pragma: allowlist secret
                ),
                "auteur": "Fabcaro",
                "titre": "Figurec",
                "suggested_author": "Fabrice Caro",
                "suggested_title": "Figurec",
                "status": "mongo",
            },
        ]

        patches = patch_cache_service()
        with (
            patches[0] as mock_get_books,
            patches[1] as mock_is_corrected,
            patches[2] as mock_mark,
        ):
            mock_get_books.return_value = books
            mock_is_corrected.return_value = False

            # Act
            stats = service.cleanup_uncorrected_summaries_for_episode(episode_oid)

            # Assert
            assert stats["total_books"] == 2
            assert stats["corrected"] == 2
            # Vérifier que les 2 avis_critiques ont été appelés
            assert service._mock_mongodb.update_avis_critique.call_count == 2
            assert mock_mark.call_count == 2
