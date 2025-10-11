"""
Tests pour le ramasse-miette (garbage collector) du système de validation.

Ces tests utilisent les données réelles de l'épisode du 28/09/2025 pour valider
la logique de correction des summaries basée sur la comparaison stricte entre
auteur/titre original et suggested_author/suggested_title.

Logique (Issue #67):
- Si auteur == suggested_author ET titre == suggested_title → marquer summary_corrected=true (pas de modif)
- Sinon → corriger summary puis marquer summary_corrected=true
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml

from back_office_lmelp.services.collections_management_service import (
    CollectionsManagementService,
)


def load_episode_28_09_books():
    """Charge les fixtures depuis le fichier YAML."""
    fixtures_path = Path(__file__).parent / "fixtures" / "episode_28_09_2025_books.yml"
    with open(fixtures_path) as f:
        data = yaml.safe_load(f)
    return data


@pytest.fixture
def episode_28_09_data():
    """Fixture contenant les données réelles de l'épisode 28/09."""
    return load_episode_28_09_books()


@pytest.fixture
def mock_mongodb_service():
    """Mock du service MongoDB."""
    mock = Mock()
    mock.get_collection.return_value = Mock()
    return mock


@pytest.fixture
def mock_cache_service():
    """Mock du service de cache livres/auteurs."""
    mock = Mock()
    mock.is_summary_corrected.return_value = False
    mock.mark_summary_corrected.return_value = True
    return mock


def create_service_with_mocks(mock_mongodb):
    """Helper pour créer un service avec des mocks injectés."""
    service = CollectionsManagementService()
    service.mongodb_service = mock_mongodb
    return service


def patch_cache_service_singleton(mock_cache):
    """
    Retourne les patches pour le singleton livres_auteurs_cache_service.

    Le service utilise des imports locaux, donc il faut patcher l'instance globale.
    """
    return (
        patch(
            "back_office_lmelp.services.livres_auteurs_cache_service.livres_auteurs_cache_service.get_books_by_episode_oid",
            mock_cache.get_books_by_episode_oid,
        ),
        patch(
            "back_office_lmelp.services.livres_auteurs_cache_service.livres_auteurs_cache_service.is_summary_corrected",
            mock_cache.is_summary_corrected,
        ),
        patch(
            "back_office_lmelp.services.livres_auteurs_cache_service.livres_auteurs_cache_service.mark_summary_corrected",
            mock_cache.mark_summary_corrected,
        ),
    )


class TestGarbageCollectorStrictComparison:
    """
    Tests de la logique de comparaison stricte du ramasse-miette.

    Règle :
    - Si auteur == suggested_author ET titre == suggested_title → marquer summary_corrected=true (pas de modif)
    - Sinon → corriger summary puis marquer summary_corrected=true
    """

    def test_should_mark_corrected_when_strictly_identical(
        self, episode_28_09_data, mock_mongodb_service, mock_cache_service
    ):
        """
        Cas : Auteur et titre strictement identiques aux suggestions.

        Exemple: Amélie Nothomb - Tant mieux (livre 5)
        - auteur: "Amélie Nothomb" == suggested_author: "Amélie Nothomb"
        - titre: "Tant mieux" == suggested_title: "Tant mieux"

        Attendu: Marquer summary_corrected=true SANS modifier le summary.
        """
        service = create_service_with_mocks(mock_mongodb_service)

        # Livre 5 : aucune correction nécessaire
        book = next(
            b for b in episode_28_09_data["books"] if b["auteur"] == "Amélie Nothomb"
        )

        # Simuler que le cache retourne ce livre
        mock_cache_service.get_books_by_episode_oid.return_value = [book]

        # Act - Appliquer les patches du singleton
        patches = patch_cache_service_singleton(mock_cache_service)
        with patches[0], patches[1], patches[2]:
            stats = service.cleanup_uncorrected_summaries_for_episode(
                episode_28_09_data["episode_oid"]
            )

        # Assert
        assert stats["no_correction_needed"] == 1
        assert stats["corrected"] == 0
        assert mock_cache_service.mark_summary_corrected.called
        # Vérifier qu'aucune mise à jour de summary n'a été faite
        assert not mock_mongodb_service.update_avis_critique.called

    def test_should_correct_summary_when_author_differs(
        self, episode_28_09_data, mock_mongodb_service, mock_cache_service
    ):
        """
        Cas : Auteur diffère de la suggestion.

        Exemple: Sybille Grimbert → Sibylle Grimbert (livre 6)
        - auteur: "Sybille" != suggested_author: "Sibylle"
        - titre: "Au pays des Pnines" == suggested_title: "Au pays des Pnines"

        Attendu: Corriger le summary puis marquer summary_corrected=true.
        """
        service = create_service_with_mocks(mock_mongodb_service)

        # Livre 6 : correction auteur seulement
        book = next(
            b for b in episode_28_09_data["books"] if b["auteur"] == "Sybille Grimbert"
        )

        # Mock avis critique existant
        mock_mongodb_service.get_avis_critique_by_id.return_value = {
            "_id": book["avis_critique_id"],
            "summary": "... Sybille Grimbert Au pays des Pnines ...",
        }

        mock_cache_service.get_books_by_episode_oid.return_value = [book]

        # Act
        patches = patch_cache_service_singleton(mock_cache_service)
        with patches[0], patches[1], patches[2]:
            stats = service.cleanup_uncorrected_summaries_for_episode(
                episode_28_09_data["episode_oid"]
            )

        # Assert
        assert stats["corrected"] == 1
        assert mock_mongodb_service.update_avis_critique.called
        assert mock_cache_service.mark_summary_corrected.called

    def test_should_correct_summary_when_title_differs(
        self, episode_28_09_data, mock_mongodb_service, mock_cache_service
    ):
        """
        Cas : Titre diffère de la suggestion.

        Exemple: Catherine Millet - Simone Emonet → Simone Émonet (livre 1)
        - auteur: "Catherine Millet" == suggested_author: "Catherine Millet"
        - titre: "Simone Emonet" != suggested_title: "Simone Émonet"

        Attendu: Corriger le summary puis marquer summary_corrected=true.
        """
        service = create_service_with_mocks(mock_mongodb_service)

        # Livre 1 : correction titre (accent)
        book = next(
            b for b in episode_28_09_data["books"] if b["auteur"] == "Catherine Millet"
        )

        # Mock avis critique existant
        mock_mongodb_service.get_avis_critique_by_id.return_value = {
            "_id": book["avis_critique_id"],
            "summary": "... Catherine Millet Simone Emonet ...",
        }

        mock_cache_service.get_books_by_episode_oid.return_value = [book]

        # Act
        patches = patch_cache_service_singleton(mock_cache_service)
        with patches[0], patches[1], patches[2]:
            stats = service.cleanup_uncorrected_summaries_for_episode(
                episode_28_09_data["episode_oid"]
            )

        # Assert
        assert stats["corrected"] == 1
        assert mock_mongodb_service.update_avis_critique.called
        assert mock_cache_service.mark_summary_corrected.called

    def test_should_correct_summary_when_both_differ(
        self, episode_28_09_data, mock_mongodb_service, mock_cache_service
    ):
        """
        Cas : Auteur ET titre diffèrent des suggestions.

        Exemple: Bruno Cabane → Bruno Cabanes + Pelléliou → Peleliu (livre 9)

        Attendu: Corriger le summary puis marquer summary_corrected=true.
        """
        service = create_service_with_mocks(mock_mongodb_service)

        # Livre 9 : corrections auteur + titre
        book = next(
            b for b in episode_28_09_data["books"] if b["auteur"] == "Bruno Cabane"
        )

        # Mock avis critique existant
        mock_mongodb_service.get_avis_critique_by_id.return_value = {
            "_id": book["avis_critique_id"],
            "summary": "... Bruno Cabane Les fantômes de l'île de Pelléliou ...",
        }

        mock_cache_service.get_books_by_episode_oid.return_value = [book]

        # Act
        patches = patch_cache_service_singleton(mock_cache_service)
        with patches[0], patches[1], patches[2]:
            stats = service.cleanup_uncorrected_summaries_for_episode(
                episode_28_09_data["episode_oid"]
            )

        # Assert
        assert stats["corrected"] == 1
        assert mock_mongodb_service.update_avis_critique.called
        assert mock_cache_service.mark_summary_corrected.called


class TestGarbageCollectorIgnoreValidatedFields:
    """
    Tests vérifiant que validated_author/validated_title sont IGNORÉS.

    Le ramasse-miette doit utiliser UNIQUEMENT suggested_author/suggested_title,
    jamais validated_author/validated_title.
    """

    def test_should_use_suggested_not_validated(
        self, episode_28_09_data, mock_mongodb_service, mock_cache_service
    ):
        """
        Cas : Livre avec validated_author/validated_title différents de suggested.

        Exemple: Sorge Chalandon (livre 2)
        - auteur: "Sorge Chalandon"
        - suggested_author: "Sorj Chalandon"
        - validated_author: "Sorj Chalandon"

        Attendu: Utiliser suggested_author ("Sorj"), PAS validated_author.
        """
        service = create_service_with_mocks(mock_mongodb_service)

        # Livre 2 : avec validated_* présents
        book = next(
            b for b in episode_28_09_data["books"] if b["auteur"] == "Sorge Chalandon"
        )

        # Mock avis critique existant
        mock_mongodb_service.get_avis_critique_by_id.return_value = {
            "_id": book["avis_critique_id"],
            "summary": "... Sorge Chalandon Le livre de Kels ...",
        }

        mock_cache_service.get_books_by_episode_oid.return_value = [book]

        # Act
        patches = patch_cache_service_singleton(mock_cache_service)
        with patches[0], patches[1], patches[2]:
            stats = service.cleanup_uncorrected_summaries_for_episode(
                episode_28_09_data["episode_oid"]
            )

        # Assert
        assert stats["corrected"] == 1
        # Vérifier que update_avis_critique a été appelé
        assert mock_mongodb_service.update_avis_critique.called
        # Vérifier que mark_summary_corrected a été appelé
        assert mock_cache_service.mark_summary_corrected.called


class TestGarbageCollectorStatistics:
    """
    Tests des statistiques retournées par le ramasse-miette.
    """

    def test_should_return_correct_statistics(
        self, episode_28_09_data, mock_mongodb_service, mock_cache_service
    ):
        """
        Cas : Traiter un mélange de livres (identiques + à corriger).

        Episode 28/09 :
        - 2 livres identiques (Amélie Nothomb, Sigrid Nunez)
        - 8 livres à corriger

        Attendu: Stats correctes (no_correction_needed=2, corrected=8).
        """
        service = create_service_with_mocks(mock_mongodb_service)

        # Mock avis critique pour tous les livres
        def get_avis_mock(avis_id):
            return {
                "_id": avis_id,
                "summary": "Summary générique avec auteurs et titres...",
            }

        mock_mongodb_service.get_avis_critique_by_id.side_effect = get_avis_mock
        mock_cache_service.get_books_by_episode_oid.return_value = episode_28_09_data[
            "books"
        ]

        # Act
        patches = patch_cache_service_singleton(mock_cache_service)
        with patches[0], patches[1], patches[2]:
            stats = service.cleanup_uncorrected_summaries_for_episode(
                episode_28_09_data["episode_oid"]
            )

        # Assert
        assert stats["total_books"] == 10
        assert (
            stats["no_correction_needed"] >= 2
        )  # Au moins Amélie Nothomb + Sigrid Nunez
        assert stats["corrected"] >= 6  # Les livres avec vraies différences
