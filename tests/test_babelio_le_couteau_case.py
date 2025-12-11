"""Test TDD pour le cas Le couteau avec auteur incorrect (Issue #124).

Problème business réel :
- Recherche "Le couteau" par "Salman Rushdie" → Babelio ne retourne PAS le livre de Rushdie
- Résultats: Jo Nesbø, Agatha Christie, Vuk Draskovic, etc.
- Actuellement retourne: "Le couteau sur la nuque" d'Agatha Christie (2079 copies) ❌
- Devrait retourner: not_found (aucun livre ne correspond à l'auteur) ✅

Solution: Quand author filtering retourne 0 résultats, retourner not_found.
"""

import pytest

from back_office_lmelp.services.babelio_service import BabelioService


class TestBabelioLeCouteauCase:
    """Tests pour le cas Le couteau avec auteur introuvable."""

    @pytest.fixture
    def babelio_service(self):
        """Fixture pour créer une instance du service Babelio."""
        return BabelioService()

    def test_find_best_book_match_should_return_none_when_author_filter_rejects_all(
        self, babelio_service
    ):
        """Test TDD: _find_best_book_match doit retourner None si aucun livre ne correspond à l'auteur.

        Scénario business réel :
        - Recherche "Le couteau" par "Salman Rushdie"
        - Babelio retourne: Jo Nesbø, Agatha Christie, Vuk Draskovic
        - Aucun livre ne correspond à l'auteur (similarity < 0.7)
        - Résultat attendu: None (pas de match trouvé)

        Ce test utilise des données réelles de l'API Babelio pour "Le couteau".
        """
        # Arrange - Résultats réels de l'API Babelio pour "Le couteau"
        results = [
            {
                "id_oeuvre": "565058",
                "titre": "Le grand escalier",
                "prenoms": "Paul",
                "nom": "Couteau",
                "ca_copies": "14",
                "type": "livres",
            },
            {
                "id_oeuvre": "1137081",
                "titre": "Le couteau",
                "prenoms": "Jo",
                "nom": "Nesbø",
                "ca_copies": "1759",
                "type": "livres",
            },
            {
                "id_oeuvre": "1432702",
                "titre": "Le couteau sur la nuque",
                "prenoms": "Agatha",
                "nom": "Christie",
                "ca_copies": "2079",
                "type": "livres",
            },
            {
                "id_oeuvre": "1428119",
                "titre": "Le couteau",
                "prenoms": "Vuk",
                "nom": "Draskovic",
                "ca_copies": "3",
                "type": "livres",
            },
        ]

        # Act
        result = babelio_service._find_best_book_match(
            results, "Le couteau", "Salman Rushdie"
        )

        # Assert - Aucun livre ne devrait être retourné
        assert result is None, (
            f"Expected None when no author matches, but got: "
            f"'{result.get('titre') if result else None}' by "
            f"'{result.get('prenoms') if result else None} {result.get('nom') if result else None}'"
        )
