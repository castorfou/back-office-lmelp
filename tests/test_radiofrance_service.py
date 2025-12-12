"""Tests pour le service de recherche d'URL de page RadioFrance.

Ce module teste le RadioFranceService qui scrape la page de recherche
de RadioFrance pour trouver l'URL de la page d'un épisode de podcast.

Architecture testée :
- Endpoint: GET https://www.radiofrance.fr/franceinter/podcasts/le-masque-et-la-plume?search=...
- Format: HTML scraping avec BeautifulSoup
- Extraction du premier résultat de recherche
- Retour de l'URL complète de la page de l'épisode

Tests basés sur le comportement réel de RadioFrance :
- Recherche par titre exact → trouve l'URL de la page
- Titre inexistant → retourne None
- Erreur réseau → gestion appropriée

IMPORTANT: Les fixtures HTML sont des captures réelles de RadioFrance (Issue #85 lesson).
- search_with_results.html: Capture du 2025-11-07 avec résultats de recherche
- search_no_results.html: Capture du 2025-11-07 sans résultats
"""

import pathlib
from unittest.mock import AsyncMock, Mock, patch

import pytest

from back_office_lmelp.services.radiofrance_service import RadioFranceService


# Chemin vers les fixtures
FIXTURES_DIR = pathlib.Path(__file__).parent / "fixtures" / "radiofrance"


class TestRadioFranceService:
    """Tests du service de recherche d'URL de page RadioFrance.

    Ces tests vérifient :
    1. L'initialisation correcte du service
    2. Le scraping HTML avec BeautifulSoup
    3. L'extraction du premier lien de résultat
    4. La construction de l'URL complète
    5. La gestion d'erreurs (404, timeout, etc.)
    """

    @pytest.fixture
    def radiofrance_service(self):
        """Fixture pour créer une instance du service RadioFrance.

        Returns:
            RadioFranceService: Instance configurée avec base_url
        """
        return RadioFranceService()

    def test_init_service(self, radiofrance_service):
        """Test d'initialisation du service RadioFrance.

        Vérifie que tous les attributs nécessaires sont correctement initialisés :
        - Base URL RadioFrance
        - Endpoint de recherche
        """
        assert radiofrance_service is not None
        assert radiofrance_service.base_url == "https://www.radiofrance.fr"
        assert (
            radiofrance_service.podcast_search_base
            == "/franceinter/podcasts/le-masque-et-la-plume"
        )

    @pytest.mark.asyncio
    async def test_search_episode_page_url_exact_match(self, radiofrance_service):
        """Test de recherche d'URL de page avec titre exact (GREEN test).

        Utilise une capture HTML RÉELLE de RadioFrance (Issue #85 lesson).
        Fixture: search_with_results.html - Capture du 2025-11-07
        L'épisode recherché : "CRITIQUE I Anne Berest, Laura Vazquez..."

        Vérifie que :
        - La requête GET est correctement formatée avec query string
        - Le HTML est parsé avec BeautifulSoup
        - Le JSON-LD ItemList est parsé en priorité
        - Le premier lien est extrait correctement
        - L'URL complète est retournée
        """
        # Charger le vrai HTML capturé de RadioFrance
        real_html_path = FIXTURES_DIR / "search_with_results.html"
        with open(real_html_path, encoding="utf-8") as f:
            real_html = f.read()

        # Créer un mock response avec support async context manager
        mock_response = Mock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=real_html)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        # Créer un mock session avec support async context manager
        mock_session = Mock()
        mock_session.get = Mock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            episode_title = (
                "CRITIQUE I Anne Berest, Laura Vazquez, Cédric Sapin-Defour, "
                "Javier Cercas, Paul Gasnier, que lire cette semaine ?"
            )
            result = await radiofrance_service.search_episode_page_url(episode_title)

            # Vérification : URL complète retournée (depuis JSON-LD ItemList)
            assert result is not None
            assert result.startswith("https://www.radiofrance.fr")
            assert "le-masque-et-la-plume-du-dimanche-26-octobre-2025" in result

    @pytest.mark.asyncio
    async def test_search_episode_page_url_not_found(self, radiofrance_service):
        """Test de recherche sans résultat.

        Utilise une capture HTML RÉELLE de RadioFrance (Issue #85 lesson).
        Fixture: search_no_results.html - Capture du 2025-11-07
        Requête avec titre inexistant "Episode inexistant XYZ123"

        Vérifie que :
        - None est retourné quand aucun résultat n'est trouvé
        - Le JSON-LD est parsé mais ne contient pas de résultats
        - Le fallback HTML ne trouve pas de lien non plus
        """
        # Charger le vrai HTML capturé de RadioFrance
        real_html_path = FIXTURES_DIR / "search_no_results.html"
        with open(real_html_path, encoding="utf-8") as f:
            real_html = f.read()

        mock_response = Mock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=real_html)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = Mock()
        mock_session.get = Mock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await radiofrance_service.search_episode_page_url(
                "Episode inexistant XYZ123"
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_search_episode_page_url_network_error(self, radiofrance_service):
        """Test de gestion d'erreur réseau.

        Simule une erreur réseau (timeout, 500, etc.).

        Vérifie que :
        - L'exception est correctement gérée
        - None est retourné en cas d'erreur
        """
        mock_session = Mock()
        mock_session.get = Mock(side_effect=Exception("Network timeout"))
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await radiofrance_service.search_episode_page_url(
                "Test episode title"
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_search_episode_should_skip_contact_page(self, radiofrance_service):
        """RED TEST - Issue #129: devrait ignorer le lien /contact dans les résultats.

        Reproduit le bug où le lien /contact est retourné au lieu de l'épisode réel.
        Le lien /contact apparaît parfois en premier dans les résultats de recherche
        RadioFrance, mais ce n'est pas un épisode valide.

        Utilise une fixture HTML RÉELLE capturée avec /contact en premier résultat.
        Fixture: search_with_contact_link.html

        Vérifie que :
        - Le lien /contact est ignoré (non valide)
        - Le vrai lien d'épisode est retourné
        - URL retournée contient un slug de date (du-dimanche-DD-mois-YYYY)
        """
        # Charger la fixture HTML avec /contact en premier
        fixture_path = FIXTURES_DIR / "search_with_contact_link.html"
        with open(fixture_path, encoding="utf-8") as f:
            html_with_contact = f.read()

        # Créer un mock response
        mock_response = Mock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=html_with_contact)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = Mock()
        mock_session.get = Mock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            episode_title = "Le Masque et la plume du dimanche 10 décembre 2023"
            result = await radiofrance_service.search_episode_page_url(episode_title)

            # RED: Ce test doit ÉCHOUER avant la correction
            # Actuellement, le service retourne /contact au lieu de l'épisode
            assert result is not None
            assert "/contact" not in result, (
                f"Le lien /contact ne devrait pas être retourné. Got: {result}"
            )
            assert "le-masque-et-la-plume-du-dimanche-10-decembre-2023" in result
            assert result.startswith("https://www.radiofrance.fr")
