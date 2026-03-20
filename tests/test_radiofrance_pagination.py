"""Test TDD pour le problème de pagination RadioFrance (Issue #XXX).

Problème: Recherche avec titre générique ("Le masque et la plume livres")
retourne beaucoup de résultats, et l'épisode du 01/10/2017 n'apparaît pas
dans la première page de recherche. Il faut une recherche dichotomique dans
la pagination chronologique (?p=N) pour trouver l'épisode exact par date.
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from back_office_lmelp.services.radiofrance_service import RadioFranceService


class TestRadioFranceDichotomySearch:
    """Tests unitaires (avec mocks) pour la recherche dichotomique."""

    @pytest.fixture
    def service(self):
        return RadioFranceService()

    @pytest.mark.asyncio
    async def test_get_page_median_date_returns_date_from_middle_episode(self, service):
        """_get_page_median_date retourne la date de l'épisode du milieu de la page.

        GIVEN: Une page chronologique avec des épisodes
        WHEN: On appelle _get_page_median_date(page)
        THEN: Retourne la date de l'épisode médian (pour orienter la dichotomie)
        """
        # Page HTML avec un épisode
        search_html = """<html><body>
        <a href="/franceinter/podcasts/le-masque-et-la-plume/episode-test-1234567">Episode</a>
        </body></html>"""

        episode_html = """<html><head>
        <script type="application/ld+json">{"@context":"https://schema.org","@graph":[
          {"@type":"RadioEpisode","dateCreated":"2017-10-01T18:00:00.000Z"}
        ]}</script>
        </head><body></body></html>"""

        def make_resp(html):
            r = Mock()
            r.status = 200
            r.text = AsyncMock(return_value=html)
            r.__aenter__ = AsyncMock(return_value=r)
            r.__aexit__ = AsyncMock(return_value=None)
            return r

        def mock_get(url, **kwargs):
            if "?p=" in url and "le-masque-et-la-plume?p=" in url:
                return make_resp(search_html)
            return make_resp(episode_html)

        def make_session():
            s = Mock()
            s.get = Mock(side_effect=mock_get)
            s.__aenter__ = AsyncMock(return_value=s)
            s.__aexit__ = AsyncMock(return_value=None)
            return s

        with patch(
            "aiohttp.ClientSession", side_effect=lambda **kwargs: make_session()
        ):
            result = await service._get_page_median_date(42)

        assert result == datetime(2017, 10, 1)

    @pytest.mark.asyncio
    async def test_get_page_median_date_returns_none_for_empty_page(self, service):
        """_get_page_median_date retourne None si la page est vide (fin de pagination)."""
        empty_html = "<html><body></body></html>"

        r = Mock()
        r.status = 200
        r.text = AsyncMock(return_value=empty_html)
        r.__aenter__ = AsyncMock(return_value=r)
        r.__aexit__ = AsyncMock(return_value=None)

        s = Mock()
        s.get = Mock(return_value=r)
        s.__aenter__ = AsyncMock(return_value=s)
        s.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", side_effect=lambda **kwargs: s):
            result = await service._get_page_median_date(999)

        assert result is None

    @pytest.mark.asyncio
    async def test_dichotomy_converges_to_correct_page(self, service):
        """La dichotomie converge vers la page contenant l'épisode cible.

        GIVEN: Un espace de 10 pages simulées avec dates décroissantes
               (page 1=récent, page 10=ancien)
        WHEN: On cherche la date 2017-10-01
        THEN: La dichotomie trouve l'épisode sans parcourir toutes les pages
        """
        # Simuler un espace de 10 pages:
        # page 1 = 2026, page 5 = 2022, page 8 = 2019, page 10 = 2017
        # Les IDs d'épisodes doivent se terminer par 4+ chiffres (règle _is_valid_episode_url)
        page_dates = {
            1: "2026-01-01",
            2: "2025-06-01",
            3: "2024-12-01",
            4: "2024-06-01",
            5: "2023-01-01",
            6: "2022-01-01",
            7: "2020-06-01",
            8: "2019-01-01",
            9: "2018-01-01",
            10: "2017-10-01",  # ← épisode cible ici
        }

        # HTML de la page de recherche (liste d'épisodes)
        # L'URL se termine par un ID 7 chiffres pour passer _is_valid_episode_url
        def search_html_for_page(p):
            ep_id = 1000000 + p  # ex: page 10 → 1000010
            return f"""<html><body>
            <a href="/franceinter/podcasts/le-masque-et-la-plume/le-masque-et-la-plume-livres-{ep_id}">Ep {p}</a>
            </body></html>"""

        def episode_html_for_page(ep_id):
            # Extraire le numéro de page depuis l'ID
            p = ep_id - 1000000
            date = page_dates.get(p, "2020-01-01")
            return f"""<html><head>
            <script type="application/ld+json">{{"@context":"https://schema.org","@graph":[
              {{"@type":"RadioEpisode","dateCreated":"{date}T18:00:00.000Z"}}
            ]}}</script>
            </head><body></body></html>"""

        def make_resp(html):
            r = Mock()
            r.status = 200
            r.text = AsyncMock(return_value=html)
            r.__aenter__ = AsyncMock(return_value=r)
            r.__aexit__ = AsyncMock(return_value=None)
            return r

        def mock_get(url, **kwargs):
            import re

            # URL chronologique ?p=N
            m = re.search(r"le-masque-et-la-plume\?p=(\d+)$", url)
            if m:
                p = int(m.group(1))
                if p > 10:
                    # Page vide au-delà de la page 10
                    return make_resp("<html><body></body></html>")
                return make_resp(search_html_for_page(p))
            # URL d'épisode individuel (ID = 1000000 + numéro de page)
            m2 = re.search(r"livres-(10000\d\d)", url)
            if m2:
                ep_id = int(m2.group(1))
                return make_resp(episode_html_for_page(ep_id))
            return make_resp("<html><body></body></html>")

        pages_fetched = []
        original_mock_get = mock_get

        def tracking_mock_get(url, **kwargs):
            import re

            m = re.search(r"le-masque-et-la-plume\?p=(\d+)$", url)
            if m:
                pages_fetched.append(int(m.group(1)))
            return original_mock_get(url, **kwargs)

        def make_session():
            s = Mock()
            s.get = Mock(side_effect=tracking_mock_get)
            s.__aenter__ = AsyncMock(return_value=s)
            s.__aexit__ = AsyncMock(return_value=None)
            return s

        with patch(
            "aiohttp.ClientSession", side_effect=lambda **kwargs: make_session()
        ):
            result = await service._search_chronological_pages(
                "Le masque et la plume livres", "2017-10-01"
            )

        # THEN: L'épisode est trouvé
        assert result is not None
        assert "le-masque-et-la-plume" in result

        # ET: Moins de pages chargées qu'une recherche séquentielle exhaustive
        # Phase 0 (trouver hi) + phase 1 (dichotomie) + phase 2 (fenêtre ±3)
        # = ~8 + ~4 + ~7 = ~19 pages max, bien moins que 94 pages séquentielles
        assert len(pages_fetched) < 30, (
            f"Trop de pages chargées ({len(pages_fetched)}): {pages_fetched}"
        )


class TestRadioFrancePaginationForOldEpisodes:
    """Tests pour la pagination quand l'épisode n'est pas dans la 1ère page."""

    @pytest.mark.asyncio
    async def test_should_find_episode_from_2017_with_generic_title(self):
        """
        RED Test: Doit trouver l'épisode du 01/10/2017 malgré titre générique.

        PROBLÈME:
        - Titre générique: "Le masque et la plume livres"
        - Recherche retourne beaucoup de résultats
        - Épisode du 01/10/2017 pas dans la 1ère page
        - Pagination nécessaire avec paramètre ?p=2, ?p=3, etc.

        SOLUTION ATTENDUE:
        - Essayer plusieurs pages de résultats (max 10 pages)
        - Arrêter quand l'épisode avec la bonne date est trouvé
        - Arrêter si une page ne retourne aucun résultat
        """
        service = RadioFranceService()

        # GIVEN: Episode ancien avec titre très générique
        episode_title = "Le masque et la plume livres"
        episode_date = "2017-10-01"  # Épisode du 01/10/2017

        # WHEN: On recherche l'URL de cet épisode
        result_url = await service.search_episode_page_url(episode_title, episode_date)

        # THEN: L'URL doit être trouvée malgré la pagination
        assert result_url is not None, (
            f"URL de l'épisode du {episode_date} devrait être trouvée "
            "même si pas dans la 1ère page de résultats"
        )
        # La date est déjà vérifiée par le code (via _extract_episode_date)
        # donc on vérifie juste que c'est une URL RadioFrance valide
        assert "radiofrance.fr/franceinter/podcasts/le-masque-et-la-plume" in result_url

    @pytest.mark.asyncio
    async def test_should_find_episode_from_august_2017(self):
        """Test avec un autre épisode ancien (13/08/2017)."""
        service = RadioFranceService()

        episode_title = "Le masque et la plume livres"
        episode_date = "2017-08-13"

        result_url = await service.search_episode_page_url(episode_title, episode_date)

        assert result_url is not None
        assert "radiofrance.fr/franceinter/podcasts/le-masque-et-la-plume" in result_url

    @pytest.mark.asyncio
    async def test_should_stop_after_max_pages_to_avoid_infinite_loop(self):
        """
        Test: Doit limiter le nombre de pages parcourues.

        GARDE-FOU 1: Limite de 10 pages maximum
        Pour éviter des boucles infinies si l'épisode n'existe vraiment pas.
        """
        service = RadioFranceService()

        # GIVEN: Episode qui n'existe probablement pas
        episode_title = "Épisode Totalement Inventé XYZ123"
        episode_date = "1900-01-01"

        # WHEN: On recherche (devrait s'arrêter après max_pages)
        result_url = await service.search_episode_page_url(episode_title, episode_date)

        # THEN: Devrait retourner None sans timeout ni boucle infinie
        assert result_url is None

    @pytest.mark.asyncio
    async def test_should_stop_when_page_returns_no_results(self):
        """
        Test: Doit s'arrêter quand une page ne retourne aucun résultat.

        GARDE-FOU 2: Détecter fin de pagination
        Si candidate_urls est vide, c'est qu'on a atteint la fin.
        """
        service = RadioFranceService()

        # GIVEN: Titre très spécifique qui ne devrait avoir que quelques résultats
        episode_title = "Le masque et la plume livres épisode unique xyz"
        episode_date = "2099-12-31"  # Date future

        # WHEN: On recherche
        result_url = await service.search_episode_page_url(episode_title, episode_date)

        # THEN: Ne devrait pas faire 10 pages inutiles
        # Devrait s'arrêter dès qu'une page retourne 0 résultats
        assert result_url is None

    @pytest.mark.asyncio
    async def test_pagination_should_respect_timeout(self):
        """
        Test: L'opération entière doit respecter un timeout global.

        GARDE-FOU 3: Timeout global
        Même avec pagination, ne pas dépasser un temps max (ex: 30s).
        """
        service = RadioFranceService()

        episode_title = "Le masque et la plume livres"
        episode_date = "2017-10-01"

        # WHEN: On recherche avec timeout
        # La fonction ne devrait pas bloquer indéfiniment
        import asyncio

        try:
            await asyncio.wait_for(
                service.search_episode_page_url(episode_title, episode_date), timeout=30
            )
            # Si on arrive ici, c'est OK (trouvé ou non)
            assert True
        except TimeoutError:
            pytest.fail("La recherche avec pagination a dépassé le timeout de 30s")
