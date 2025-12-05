"""Test TDD pour le cas Terminus Malaussène avec auteur (Issue #124).

Problème business réel :
- Script migration appelle: verify_book("Terminus Malaussène", "Daniel Pennac")
- Actuellement retourne: "Monsieur Malaussène" (confidence 0.779) ❌
- Devrait retourner: "Le cas Malaussène, tome 2 : Terminus Malaussène" ✅

Solution: verify_book() doit retourner le bon livre même quand l'auteur est fourni.
"""

import pytest

from back_office_lmelp.services.babelio_service import BabelioService


class TestBabelioTerminusCase:
    """Tests pour le cas Terminus Malaussène."""

    @pytest.fixture
    def babelio_service(self):
        """Fixture pour créer une instance du service Babelio."""
        return BabelioService()

    @pytest.mark.asyncio
    async def test_verify_book_should_return_terminus_not_monsieur(
        self, babelio_service
    ):
        """Test TDD: verify_book doit retourner Terminus (pas Monsieur).

        Scénario business réel (appel migration) :
        - verify_book("Terminus Malaussène", "Daniel Pennac")
        - Résultat attendu: Titre contient "Terminus" (pas "Monsieur")
        - Status: verified ou corrected (peu importe)

        Ce test utilise la VRAIE API Babelio (pas de mock) car c'est le comportement
        réel qu'on veut valider.
        """
        # Act
        result = await babelio_service.verify_book(
            "Terminus Malaussène", "Daniel Pennac"
        )

        # Assert - Le BON livre doit être retourné
        assert result["status"] in ["verified", "corrected"]

        # Le titre doit contenir "Terminus"
        assert "Terminus" in result["babelio_suggestion_title"], (
            f"Titre trouvé: {result['babelio_suggestion_title']} "
            f"(devrait contenir 'Terminus', pas 'Monsieur')"
        )

        # Le titre ne doit PAS contenir "Monsieur"
        assert "Monsieur" not in result["babelio_suggestion_title"], (
            f"Titre trouvé: {result['babelio_suggestion_title']} "
            f"(ne devrait PAS contenir 'Monsieur')"
        )

        # L'auteur doit être Daniel Pennac
        assert "Pennac" in result["babelio_suggestion_author"]
