"""Tests TDD pour la validation du titre lors de l'extraction de couverture (Issue #238).

Problème business :
- Babelio redirige parfois vers un autre livre (ex: demande "On ne sait rien de toi"
  mais retourne la fiche de "Fauves")
- L'og:image retournée est donc celle du mauvais livre
- Il faut valider que le titre de la page correspond au livre demandé

Solution :
- fetch_cover_url_from_babelio_page() accepte un paramètre `expected_title`
- Compare le h1 de la page avec expected_title via normalize_for_matching
- Retourne TITLE_MISMATCH:<page_title> si le titre ne correspond pas
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestFetchCoverUrlTitleValidation:
    """Tests pour la validation du titre dans fetch_cover_url_from_babelio_page()."""

    @pytest.fixture
    def mock_babelio_service(self):
        """Service Babelio avec session mockée."""
        from back_office_lmelp.services.babelio_service import BabelioService

        service = BabelioService.__new__(BabelioService)
        service.session = None
        service._debug_log_enabled = False
        return service

    def _make_html(self, h1_title: str, og_image: str) -> str:
        """Génère un HTML minimal avec h1 et og:image."""
        return f"""<html><head>
        <meta property="og:image" content="{og_image}" />
        </head><body>
        <h1>{h1_title}</h1>
        </body></html>"""

    def _make_mock_session(self, html: str):
        """Crée un mock aiohttp.ClientSession retournant le HTML donné."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=html)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get.return_value = mock_response
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        return mock_session

    @pytest.mark.asyncio
    async def test_returns_cover_url_when_title_matches(self, mock_babelio_service):
        """retourne l'URL de couverture quand le titre de la page correspond."""
        html = self._make_html(
            h1_title="On ne sait rien de toi",
            og_image="https://www.babelio.com/couv/CVT_On-ne-sait-rien_1234.jpg",
        )
        mock_session = self._make_mock_session(html)

        with patch(
            "back_office_lmelp.services.babelio_service.aiohttp.ClientSession",
            return_value=mock_session,
        ):
            result = await mock_babelio_service.fetch_cover_url_from_babelio_page(
                "https://www.babelio.com/livres/X/123",
                expected_title="On ne sait rien de toi",
            )

        assert result == "https://www.babelio.com/couv/CVT_On-ne-sait-rien_1234.jpg"

    @pytest.mark.asyncio
    async def test_returns_none_when_title_does_not_match(self, mock_babelio_service):
        """retourne TITLE_MISMATCH quand la page affiche un livre différent (redirection Babelio).

        Scénario réel : demande "On ne sait rien de toi" mais Babelio retourne "Fauves"
        """
        html = self._make_html(
            h1_title="Fauves",
            og_image="https://www.babelio.com/couv/CVT_Fauves_6863.jpg",
        )
        mock_session = self._make_mock_session(html)

        with patch(
            "back_office_lmelp.services.babelio_service.aiohttp.ClientSession",
            return_value=mock_session,
        ):
            result = await mock_babelio_service.fetch_cover_url_from_babelio_page(
                "https://www.babelio.com/livres/X/999",
                expected_title="On ne sait rien de toi",
            )

        assert isinstance(result, str) and result.startswith("TITLE_MISMATCH:"), (
            "Doit retourner TITLE_MISMATCH:<titre_page> quand la page affiche un livre différent"
        )
        assert "Fauves" in result

    @pytest.mark.asyncio
    async def test_returns_cover_url_without_expected_title(self, mock_babelio_service):
        """sans expected_title, retourne l'URL sans validation de titre."""
        html = self._make_html(
            h1_title="N'importe quel titre",
            og_image="https://www.babelio.com/couv/CVT_Quelconque_999.jpg",
        )
        mock_session = self._make_mock_session(html)

        with patch(
            "back_office_lmelp.services.babelio_service.aiohttp.ClientSession",
            return_value=mock_session,
        ):
            result = await mock_babelio_service.fetch_cover_url_from_babelio_page(
                "https://www.babelio.com/livres/X/999",
                expected_title=None,
            )

        assert result == "https://www.babelio.com/couv/CVT_Quelconque_999.jpg"

    @pytest.mark.asyncio
    async def test_title_matching_is_accent_insensitive(self, mock_babelio_service):
        """la comparaison de titres doit être insensible aux accents.

        Scénario : le titre en base est "L'Éternel mirage" mais Babelio affiche "L'Eternel mirage"
        → doit quand même matcher.
        """
        html = self._make_html(
            h1_title="L'Eternel mirage",
            og_image="https://www.babelio.com/couv/CVT_Eternel-mirage_1234.jpg",
        )
        mock_session = self._make_mock_session(html)

        with patch(
            "back_office_lmelp.services.babelio_service.aiohttp.ClientSession",
            return_value=mock_session,
        ):
            result = await mock_babelio_service.fetch_cover_url_from_babelio_page(
                "https://www.babelio.com/livres/X/123",
                expected_title="L'Éternel mirage",
            )

        assert result == "https://www.babelio.com/couv/CVT_Eternel-mirage_1234.jpg", (
            "La comparaison doit être insensible aux accents"
        )

    @pytest.mark.asyncio
    async def test_title_matching_uses_containment_for_subtitles(
        self, mock_babelio_service
    ):
        """un titre partiel doit matcher si l'un contient l'autre.

        Scénario : titre en base = "Sphinx" mais Babelio affiche "Sphinx : roman"
        → doit matcher car "sphinx" est contenu dans "sphinx : roman"
        """
        html = self._make_html(
            h1_title="Sphinx : roman",
            og_image="https://www.babelio.com/couv/CVT_Sphinx_5678.jpg",
        )
        mock_session = self._make_mock_session(html)

        with patch(
            "back_office_lmelp.services.babelio_service.aiohttp.ClientSession",
            return_value=mock_session,
        ):
            result = await mock_babelio_service.fetch_cover_url_from_babelio_page(
                "https://www.babelio.com/livres/X/123",
                expected_title="Sphinx",
            )

        assert result == "https://www.babelio.com/couv/CVT_Sphinx_5678.jpg", (
            "Doit matcher si le titre court est contenu dans le titre long de la page"
        )
