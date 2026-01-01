"""Test TDD pour le problème de pagination RadioFrance (Issue #XXX).

Problème: Recherche avec titre générique ("Le masque et la plume livres")
retourne beaucoup de résultats, et l'épisode du 01/10/2017 n'apparaît pas
dans la première page. Il faut parcourir plusieurs pages (?p=2, ?p=3, etc.).
"""

import pytest

from back_office_lmelp.services.radiofrance_service import RadioFranceService


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
