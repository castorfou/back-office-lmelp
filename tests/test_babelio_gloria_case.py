"""Test TDD pour le cas Gloria avec stratégie de fallback (Issue #124).

Problème business réel :
- Recherche "Gloria, Gloria" + "Grégory Le Floch" → not_found (0 résultats)
- Recherche "Gloria, Gloria" seul → verified (3 résultats dont le bon livre)

Solution : Fallback avec scraping d'auteur
"""

from unittest.mock import patch

import pytest

from back_office_lmelp.services.babelio_service import BabelioService


class TestBabelioGloriaCase:
    """Tests pour le cas Gloria avec stratégie de fallback."""

    @pytest.fixture
    def babelio_service(self):
        """Fixture pour créer une instance du service Babelio."""
        return BabelioService()

    @pytest.mark.asyncio
    async def test_verify_book_should_find_gloria_with_author_using_fallback(
        self, babelio_service
    ):
        """Test TDD: verify_book doit trouver Gloria en utilisant le fallback titre seul.

        Scénario business réel :
        - L'utilisateur cherche "Gloria, Gloria" par "Grégory Le Floch"
        - Recherche "titre + auteur" → 0 résultats (problème API Babelio)
        - Fallback: Recherche "titre seul" → 3 résultats
        - Vérification: Scrape la page pour confirmer l'auteur
        - Résultat attendu: verified (pas not_found)
        """
        # Arrange
        with patch.object(babelio_service, "search") as mock_search:
            # Premier appel: "titre + auteur" → 0 résultats (comportement réel de l'API)
            # Deuxième appel: "titre seul" → 3 résultats (comportement réel de l'API)
            mock_search.side_effect = [
                [],  # Recherche "Gloria, Gloria Grégory Le Floch" → vide
                [  # Recherche "Gloria, Gloria" → 3 résultats
                    {
                        "id_oeuvre": "1465214",
                        "titre": "Gloria, Gloria",
                        "couverture": "/couv/cvt_Gloria-Gloria_4289.jpg",
                        "type": "livres",
                        "url": "/livres/LeFloch-Gloria-Gloria/1465214",
                    },
                    {
                        "id": "9687",
                        "nom": "Gloria Victis",
                        "ca_copies": "134",
                        "type": "livres",
                    },
                    {
                        "id": "20957",
                        "libelle": "épave du del gloria",
                        "categorie": "1",
                        "type": "livres",
                    },
                ],
            ]

            # Mock du scraping de la page pour extraire l'auteur
            # Simule le comportement réel: extraire "Grégory Le Floch" de la page HTML
            with patch.object(
                babelio_service, "_scrape_author_from_book_page"
            ) as mock_scrape:
                mock_scrape.return_value = (
                    "Grégory Le Floch"  # Auteur trouvé sur la page
                )

                # Act
                result = await babelio_service.verify_book(
                    "Gloria, Gloria", "Grégory Le Floch"
                )

                # Assert - BUSINESS SUCCESS attendu (GREEN phase)
                assert result["status"] == "verified"
                assert result["babelio_suggestion_title"] == "Gloria, Gloria"
                assert result["babelio_suggestion_author"] == "Grégory Le Floch"
                assert (
                    result["babelio_url"]
                    == "https://www.babelio.com/livres/LeFloch-Gloria-Gloria/1465214"
                )

                # Vérifier que search() a été appelé 2 fois (titre+auteur puis titre seul)
                assert mock_search.call_count == 2
                mock_search.assert_any_call("Gloria, Gloria Grégory Le Floch")
                mock_search.assert_any_call("Gloria, Gloria")

                # Vérifier que le scraping a été appelé pour vérifier l'auteur
                mock_scrape.assert_called_once_with(
                    "https://www.babelio.com/livres/LeFloch-Gloria-Gloria/1465214"
                )
