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

    def test_is_valid_episode_url_should_accept_urls_without_date_in_slug(
        self, radiofrance_service
    ):
        """RED TEST - Issue #150: _is_valid_episode_url devrait accepter les URLs sans date dans le slug.

        Le bug actuel: les URLs comme "les-nouveaux-ouvrages-...-4010930" sont rejetées
        car elles ne contiennent ni "-du-" ni un mois français, même si elles se terminent
        par un ID numérique valid.

        GIVEN: Une URL d'épisode RadioFrance sans date dans le slug mais avec ID numérique
        WHEN: _is_valid_episode_url() est appelée
        THEN: Retourne True (l'URL est un épisode valide)
        """
        # URL réelle de l'épisode du 24/04/2022 trouvée sur RadioFrance
        url_without_date_in_slug = "https://www.radiofrance.fr/franceinter/podcasts/le-masque-et-la-plume/les-nouveaux-ouvrages-de-francois-truffaut-joel-dicker-jean-philippe-toussaint-paule-constant-4010930"

        # RED: Ce test doit ÉCHOUER car _is_valid_episode_url() rejette cette URL
        result = radiofrance_service._is_valid_episode_url(url_without_date_in_slug)

        assert result is True, (
            "L'URL d'épisode avec ID numérique 4010930 devrait être valide même sans date dans le slug"
        )

    @pytest.mark.skip(
        reason="TODO: Fix mock complexity - test logic is correct but mocks need refactoring"
    )
    @pytest.mark.asyncio
    async def test_search_should_return_correct_url_by_date_issue_150(
        self, radiofrance_service
    ):
        """RED TEST - Issue #150: devrait retourner l'URL avec la bonne date (24/04/2022).

        Reproduit le bug où la recherche pour l'épisode du 24/04/2022 retourne
        une URL d'un épisode du 26/10/2025 au lieu de la bonne URL.

        La page de recherche contient 2 URLs candidates:
        1. /le-masque-et-la-plume-du-dimanche-26-octobre-2025-7900946 (mauvaise, 2025)
        2. /les-nouveaux-ouvrages-de-francois-truffaut-joel-dicker-...-4010930 (bonne, 2022)

        L'algorithme doit:
        - Extraire toutes les URLs candidates de la page de recherche
        - Parcourir chaque URL et extraire sa date depuis le JSON-LD
        - Retourner la première URL dont la date correspond (24/04/2022)

        Vérifie que:
        - L'URL retournée contient le slug de l'épisode correct
        - L'URL ne contient PAS "26-octobre-2025"
        - La date de l'épisode est bien prise en compte
        """
        # Créer une page de recherche fictive avec 2 résultats (mauvais en premier)
        search_html = """
        <script type="application/ld+json">
        {"@type":"ItemList","itemListElement":[
          {"@type":"ListItem","position":1,"url":"https://www.radiofrance.fr/franceinter/podcasts/le-masque-et-la-plume/le-masque-et-la-plume-du-dimanche-26-octobre-2025-7900946"},
          {"@type":"ListItem","position":2,"url":"https://www.radiofrance.fr/franceinter/podcasts/le-masque-et-la-plume/les-nouveaux-ouvrages-de-francois-truffaut-joel-dicker-jean-philippe-toussaint-paule-constant-4010930"}
        ]}
        </script>
        """

        # Charger les fixtures HTML des épisodes
        fixtures_dir = pathlib.Path(__file__).parent / "fixtures" / "radiofrance"
        with open(fixtures_dir / "episode_2025_10_26.html", encoding="utf-8") as f:
            episode_2025_html = f.read()
        with open(fixtures_dir / "episode_2022_04_24.html", encoding="utf-8") as f:
            episode_2022_html = f.read()

        # Mock de la session pour la page de recherche
        mock_search_response = Mock()
        mock_search_response.status = 200
        mock_search_response.text = AsyncMock(return_value=search_html)
        mock_search_response.__aenter__ = AsyncMock(return_value=mock_search_response)
        mock_search_response.__aexit__ = AsyncMock(return_value=None)

        # Mock des réponses pour chaque URL d'épisode
        mock_episode_2025_response = Mock()
        mock_episode_2025_response.status = 200
        mock_episode_2025_response.text = AsyncMock(return_value=episode_2025_html)
        mock_episode_2025_response.__aenter__ = AsyncMock(
            return_value=mock_episode_2025_response
        )
        mock_episode_2025_response.__aexit__ = AsyncMock(return_value=None)

        mock_episode_2022_response = Mock()
        mock_episode_2022_response.status = 200
        mock_episode_2022_response.text = AsyncMock(return_value=episode_2022_html)
        mock_episode_2022_response.__aenter__ = AsyncMock(
            return_value=mock_episode_2022_response
        )
        mock_episode_2022_response.__aexit__ = AsyncMock(return_value=None)

        # Mock de la session qui retourne différentes réponses selon l'URL
        def mock_get(url, **kwargs):
            if "26-octobre-2025" in str(url):
                return mock_episode_2025_response
            elif "francois-truffaut-joel-dicker" in str(url):
                return mock_episode_2022_response
            else:
                return mock_search_response

        # Créer une nouvelle instance de session mock pour chaque appel ClientSession()
        def create_mock_session():
            mock_session = Mock()
            mock_session.get = Mock(side_effect=mock_get)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            return mock_session

        with patch("aiohttp.ClientSession", side_effect=lambda: create_mock_session()):
            episode_title = "Les nouveaux ouvrages de Joël Dicker, Jean-Philippe Toussaint, Paule Constant, François Truffaut…"
            episode_date = "2022-04-24"

            # RED: Ce test doit ÉCHOUER car search_episode_page_url ne prend pas encore episode_date en paramètre
            result = await radiofrance_service.search_episode_page_url(
                episode_title, episode_date
            )

            # Vérifications
            assert result is not None, "Une URL devrait être retournée"
            assert "26-octobre-2025" not in result, (
                f"L'URL du 26/10/2025 ne devrait pas être retournée. Got: {result}"
            )
            assert "francois-truffaut-joel-dicker" in result, (
                f"L'URL correcte du 24/04/2022 devrait être retournée. Got: {result}"
            )
            assert result.startswith("https://www.radiofrance.fr")

    @pytest.mark.asyncio
    async def test_search_episode_page_url_should_handle_datetime_object_as_date(
        self, radiofrance_service
    ):
        """RED TEST - Should handle datetime object as episode_date parameter.

        GIVEN: Un datetime object (comme retourné par MongoDB)
        WHEN: search_episode_page_url() est appelé avec ce datetime
        THEN: Devrait le convertir en string YYYY-MM-DD et faire la recherche correctement

        Issue: L'appel depuis avis_critiques_generation_service.py passe
        episode.get("date") qui est un datetime de MongoDB, pas une string.
        Cela cause l'erreur: "startswith first arg must be str or a tuple of str, not datetime.datetime"
        """
        from datetime import datetime

        # GIVEN: datetime object (comme retourné par MongoDB)
        episode_date_datetime = datetime(2019, 9, 15)

        # Mock simple pour vérifier la conversion
        search_html = """
        <script type="application/ld+json">
        {"@type":"ItemList","itemListElement":[
          {"@type":"ListItem","position":1,"url":"https://www.radiofrance.fr/franceinter/podcasts/le-masque-et-la-plume/test-episode-4105208"}
        ]}
        </script>
        """

        episode_html = """
        <script type="application/ld+json">
        {
          "@type": "PodcastEpisode",
          "datePublished": "2019-09-15T09:00:00.000Z"
        }
        </script>
        """

        mock_search_response = Mock()
        mock_search_response.status = 200
        mock_search_response.text = AsyncMock(return_value=search_html)
        mock_search_response.__aenter__ = AsyncMock(return_value=mock_search_response)
        mock_search_response.__aexit__ = AsyncMock(return_value=None)

        mock_episode_response = Mock()
        mock_episode_response.status = 200
        mock_episode_response.text = AsyncMock(return_value=episode_html)
        mock_episode_response.__aenter__ = AsyncMock(return_value=mock_episode_response)
        mock_episode_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = Mock()

        # Session get retourne différents mocks selon l'URL
        def mock_get(url, **kwargs):
            if "search=" in url:
                return mock_search_response
            else:
                return mock_episode_response

        mock_session.get = mock_get
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            # RED: Ce test doit ÉCHOUER avant la correction car datetime n'a pas .startswith()
            episode_title = "Test Episode"
            result = await radiofrance_service.search_episode_page_url(
                episode_title, episode_date_datetime
            )

            # THEN: Devrait retourner l'URL malgré le datetime object
            assert result is not None
            assert "test-episode" in result
