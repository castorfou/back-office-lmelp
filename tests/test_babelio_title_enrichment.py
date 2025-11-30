"""Tests pour l'enrichissement du titre complet depuis Babelio (Issue #88).

Approche TDD incrémentale :
1. Test de haut niveau d'abord : verify_book() doit retourner titre complet, pas tronqué
2. Tests unitaires ajoutés au fur et à mesure des implémentations

Fixtures créées depuis vrais appels API Babelio (2025-01-30) :
- Arnaud Villanova - "Le Chemin continue : Biographie de Georges Lambric..."
  → Titre complet attendu : "Le Chemin continue : Biographie de Georges Lambrichs"
"""

from unittest.mock import patch

import pytest

from back_office_lmelp.services.babelio_service import BabelioService


class TestTruncatedTitleDetection:
    """Tests unitaires pour la détection de titres tronqués."""

    @pytest.fixture
    def babelio_service(self):
        """Fixture pour créer une instance BabelioService."""
        return BabelioService()

    def test_should_detect_truncated_title_with_ellipsis(self, babelio_service):
        """GIVEN: Titre se terminant par '...'
        WHEN: _is_title_truncated() est appelé
        THEN: Retourne True
        """
        assert (
            babelio_service._is_title_truncated(
                "Le Chemin continue : Biographie de Georges Lambric..."
            )
            is True
        )


class TestTitleEnrichmentIntegration:
    """Tests d'intégration de haut niveau pour l'enrichissement des titres."""

    @pytest.fixture
    def babelio_service(self):
        """Fixture pour créer une instance BabelioService."""
        return BabelioService()

    @pytest.mark.asyncio
    async def test_verify_book_should_return_full_title_not_truncated(
        self, babelio_service
    ):
        """GIVEN: L'API Babelio retourne un titre tronqué "Lambric..." (vraies données)
        WHEN: verify_book() est appelé avec le titre complet
        THEN: babelio_suggestion_title doit être le titre COMPLET, pas le tronqué

        Ce test capture le VRAI problème métier de l'issue #88 :
        L'utilisateur voit "Lambric..." au lieu de "Lambrichs" (titre complet).

        Données réelles de l'API Babelio (récupérées le 2025-01-30):
        - API retourne: "Le Chemin continue : Biographie de Georges Lambric..."
        - Page Babelio contient: "Le Chemin continue : Biographie de Georges Lambrichs"
        """
        # Mock search() avec les VRAIES données API Babelio
        mock_book_data = {
            "id_oeuvre": "1498118",
            "titre": "Le Chemin continue : Biographie de Georges Lambric...",
            "prenoms": "Arnaud",
            "nom": "Villanova",
            "ca_copies": "7",
            "tri": "7",
            "ca_note": "3.88",
            "type": "livres",
            "url": "/livres/Villanova-Le-Chemin-continue--Biographie-de-Georges-Lambric/1498118",
        }

        with patch.object(babelio_service, "search", return_value=[mock_book_data]):
            result = await babelio_service.verify_book(
                "Le Chemin continue : Biographie de Georges Lambrichs",
                "Arnaud Villanova",
            )

            # Le problème MÉTIER : on veut le titre complet, pas le tronqué
            assert (
                result["babelio_suggestion_title"]
                == "Le Chemin continue : Biographie de Georges Lambrichs"
            )
            # Le titre NE DOIT PAS se terminer par "..."
            assert not result["babelio_suggestion_title"].endswith("...")

    @pytest.mark.asyncio
    async def test_verify_book_should_update_babelio_data_with_full_title(
        self, babelio_service
    ):
        """GIVEN: L'API Babelio retourne un titre tronqué dans babelio_data
        WHEN: verify_book() enrichit le titre complet
        THEN: babelio_data["titre"] doit contenir le titre COMPLET pour le frontend

        Ce test capture l'effet de bord frontend de l'issue #88 :
        Le modal de validation affiche "Lambric..." au lieu de "Lambrichs"
        car babelio_data["titre"] n'est pas mis à jour avec le titre complet.

        Données réelles de l'API Babelio (récupérées le 2025-01-30):
        - API retourne: babelio_data["titre"] = "...Lambric..."
        - Après enrichissement: babelio_data["titre"] = "...Lambrichs" (complet)
        """
        # Mock search() avec les VRAIES données API Babelio
        mock_book_data = {
            "id_oeuvre": "1498118",
            "titre": "Le Chemin continue : Biographie de Georges Lambric...",
            "prenoms": "Arnaud",
            "nom": "Villanova",
            "ca_copies": "7",
            "tri": "7",
            "ca_note": "3.88",
            "type": "livres",
            "url": "/livres/Villanova-Le-Chemin-continue--Biographie-de-Georges-Lambric/1498118",
        }

        with patch.object(babelio_service, "search", return_value=[mock_book_data]):
            result = await babelio_service.verify_book(
                "Le Chemin continue : Biographie de Georges Lambrichs",
                "Arnaud Villanova",
            )

            # CRITIQUE pour le frontend : babelio_data["titre"] doit être enrichi
            assert "babelio_data" in result
            assert "titre" in result["babelio_data"]
            assert (
                result["babelio_data"]["titre"]
                == "Le Chemin continue : Biographie de Georges Lambrichs"
            )
            # Le titre dans babelio_data NE DOIT PAS se terminer par "..."
            assert not result["babelio_data"]["titre"].endswith("...")
