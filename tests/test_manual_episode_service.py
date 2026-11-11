"""Tests de l'ajout manuel d'une émission depuis sa page radiofrance.fr (Issue #334).

Fixture réelle : `tests/fixtures/radiofrance/episode_2024_07_21_full_episode.html`
contient le JSON-LD capturé le 2026-11-11 sur
https://www.radiofrance.fr/franceinter/podcasts/le-masque-et-la-plume/le-masque-et-la-plume-du-dimanche-21-juillet-2024-6686255
(`RadioEpisode.dateCreated = "2024-07-21T08:11:50.000Z"`,
`mainEntity.duration = "P0Y0M0DT0H46M49S"`, `mainEntity.contentUrl` = m4a
complet de 68 Mo).

Structure MongoDB `episodes` vérifiée via mcp__MongoDB__find : titre(str),
date(datetime), description(str), url(str), audio_rel_filename(str),
transcription(None), type("livres"), duree(int), masked(bool),
episode_page_url(str).
"""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer

from back_office_lmelp.services.manual_episode_service import (
    ManualEpisodeError,
    ManualEpisodeService,
)


FIXTURES_DIR = Path(__file__).parent / "fixtures" / "radiofrance"
PAGE_URL_2024_07_21 = (
    "https://www.radiofrance.fr/franceinter/podcasts/le-masque-et-la-plume/"
    "le-masque-et-la-plume-du-dimanche-21-juillet-2024-6686255"
)
FULL_AUDIO_URL_2024_07_21 = (
    "https://media.radiofrance-podcast.net/podcast09/"
    "14007-21.07.2024-ITEMA_23808923-2024F4007S0203-27.m4a"
)


def read_fixture(name: str) -> str:
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


def make_service(
    html: str, existing_episode: dict | None = None
) -> tuple[ManualEpisodeService, MagicMock, MagicMock]:
    """Service avec MongoDB et téléchargement mockés, page HTML fournie."""
    mock_mongodb = MagicMock()
    mock_mongodb.find_episode_on_same_day.return_value = existing_episode
    mock_mongodb.insert_episode.return_value = "new-episode-id"

    mock_rss = MagicMock()
    mock_rss.download_audio = AsyncMock(
        return_value="2024/14007-21.07.2024-ITEMA_23808923-2024F4007S0203-27.m4a"
    )

    mock_runner = MagicMock()
    mock_runner.start_transcription = AsyncMock(
        return_value={"status": "started", "episode_count": 1}
    )

    service = ManualEpisodeService(
        mongodb_service=mock_mongodb,
        rss_sync_service=mock_rss,
        transcription_runner=mock_runner,
        notify=AsyncMock(return_value=None),
    )
    service.fetch_page_html = AsyncMock(return_value=html)  # type: ignore[method-assign]
    return service, mock_mongodb, mock_rss


class TestParseRadiofranceEpisodePage:
    """Lecture du JSON-LD `RadioEpisode` d'une page radiofrance.fr réelle."""

    def test_reads_title_date_duration_and_full_audio_url(self):
        parsed = ManualEpisodeService.parse_radiofrance_episode_page(
            read_fixture("episode_2024_07_21_full_episode.html")
        )

        assert parsed["titre"].startswith("Zadie Smith, Emmanuelle Salasc")
        assert parsed["date"] == datetime(2024, 7, 21, 8, 11, 50, tzinfo=UTC)
        assert parsed["duree"] == 2809
        assert parsed["audio_url"] == FULL_AUDIO_URL_2024_07_21
        assert parsed["description"].startswith("Cet été, pour vos vacances")

    def test_page_without_radio_episode_raises_clear_error(self):
        with pytest.raises(ManualEpisodeError, match="RadioEpisode"):
            ManualEpisodeService.parse_radiofrance_episode_page(
                read_fixture("search_no_results.html")
            )

    def test_episode_without_audio_url_raises_clear_error(self):
        """La fixture séquence réelle (Aqua) n'a pas de `contentUrl`."""
        with pytest.raises(ManualEpisodeError, match="audio"):
            ManualEpisodeService.parse_radiofrance_episode_page(
                read_fixture("episode_2026_02_13_clip_aqua.html")
            )


class TestAddFromRadiofrancePage:
    """Comportement métier de bout en bout (MongoDB et HTTP mockés)."""

    @pytest.mark.asyncio
    async def test_adds_full_episode_of_2024_07_21_from_its_page(self):
        """La page du 21/07/2024 doit produire l'épisode complet (46 min 49 s),
        avec l'audio du JSON-LD et non une séquence."""
        service, mock_mongodb, mock_rss = make_service(
            read_fixture("episode_2024_07_21_full_episode.html")
        )

        result = await service.add_from_radiofrance_page(PAGE_URL_2024_07_21)

        mock_rss.download_audio.assert_awaited_once_with(
            FULL_AUDIO_URL_2024_07_21, datetime(2024, 7, 21, 8, 11, 50, tzinfo=UTC)
        )
        inserted = mock_mongodb.insert_episode.call_args[0][0]
        assert inserted == {
            "titre": (
                "Zadie Smith, Emmanuelle Salasc, Yasmina Liassine, "
                # Espace insécable réelle avant « ? » (titre radiofrance brut)
                "Julien Blanc-Gras... Que lire cet été ?"
            ),
            "date": datetime(2024, 7, 21, 8, 11, 50, tzinfo=UTC),
            "description": inserted["description"],
            "url": FULL_AUDIO_URL_2024_07_21,
            "audio_rel_filename": (
                "2024/14007-21.07.2024-ITEMA_23808923-2024F4007S0203-27.m4a"
            ),
            "transcription": None,
            "type": "livres",
            "duree": 46 * 60 + 49,
            "masked": False,
            "episode_page_url": PAGE_URL_2024_07_21,
            "source": "radiofrance_page",
        }
        assert inserted["description"].startswith("Cet été, pour vos vacances")
        assert result["episode_id"] == "new-episode-id"
        assert result["date"] == "2024-07-21"
        assert result["duree"] == 2809

    @pytest.mark.asyncio
    async def test_then_follows_the_rss_path_notification_and_transcription(self):
        """Comme Automatisch après /api/rss/sync : notification ntfy, puis
        transcription PGX en mode « api » (réessai horaire si PGX dort)."""
        service, mock_mongodb, _ = make_service(
            read_fixture("episode_2024_07_21_full_episode.html")
        )

        result = await service.add_from_radiofrance_page(PAGE_URL_2024_07_21)

        title, message = service.notify.await_args.args
        assert "21/07/24" in title
        assert "Zadie Smith" in message
        assert service.notify.await_args.kwargs == {"prefix": "Ajout manuel"}
        service.transcription_runner.start_transcription.assert_awaited_once_with(
            trigger="api"
        )
        assert result["transcription_status"] == "started"

    @pytest.mark.asyncio
    async def test_transcription_start_failure_does_not_undo_the_addition(self):
        service, mock_mongodb, _ = make_service(
            read_fixture("episode_2024_07_21_full_episode.html")
        )
        service.transcription_runner.start_transcription.side_effect = RuntimeError(
            "boom"
        )

        result = await service.add_from_radiofrance_page(PAGE_URL_2024_07_21)

        assert mock_mongodb.insert_episode.called
        assert result["episode_id"] == "new-episode-id"
        assert result["transcription_status"] == "error"


def make_short_episode_html() -> str:
    """Page réelle du 21/07/2024 dont seule la durée est ramenée à 7 min 37 s,
    durée réelle de la séquence Salasc que l'issue donnait comme URL audio."""
    return read_fixture("episode_2024_07_21_full_episode.html").replace(
        "P0Y0M0DT0H46M49S", "P0Y0M0DT0H7M37S"
    )


class TestGuardsBeforeDownload:
    """Les refus arrivent avant tout téléchargement et toute insertion."""

    @pytest.mark.asyncio
    async def test_refuses_short_audio_as_a_clip(self):
        service, mock_mongodb, mock_rss = make_service(make_short_episode_html())

        with pytest.raises(ManualEpisodeError, match="7 min 37 s") as exc_info:
            await service.add_from_radiofrance_page(PAGE_URL_2024_07_21)

        assert exc_info.value.status_code == 422
        assert not mock_rss.download_audio.called
        assert not mock_mongodb.insert_episode.called

    @pytest.mark.asyncio
    async def test_refuses_when_an_episode_exists_the_same_day(self):
        existing = {
            "_id": "existing-id",
            "titre": "Titre corrigé à la main",
            "date": datetime(2024, 7, 21, 0, 0),
        }
        service, mock_mongodb, mock_rss = make_service(
            read_fixture("episode_2024_07_21_full_episode.html"),
            existing_episode=existing,
        )

        with pytest.raises(ManualEpisodeError, match="Titre corrigé") as exc_info:
            await service.add_from_radiofrance_page(PAGE_URL_2024_07_21)

        assert exc_info.value.status_code == 409
        mock_mongodb.find_episode_on_same_day.assert_called_once_with(
            datetime(2024, 7, 21, 8, 11, 50, tzinfo=UTC)
        )
        assert not mock_rss.download_audio.called
        assert not mock_mongodb.insert_episode.called

    @pytest.mark.asyncio
    async def test_failed_audio_download_inserts_nothing(self):
        import aiohttp

        service, mock_mongodb, mock_rss = make_service(
            read_fixture("episode_2024_07_21_full_episode.html")
        )
        mock_rss.download_audio.side_effect = aiohttp.ClientPayloadError(
            "Response payload is not completed"
        )

        with pytest.raises(ManualEpisodeError, match="audio") as exc_info:
            await service.add_from_radiofrance_page(PAGE_URL_2024_07_21)

        assert exc_info.value.status_code == 502
        assert not mock_mongodb.insert_episode.called

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "bad_url",
        [
            "https://example.com/le-masque-et-la-plume/x",
            "https://www.radiofrance.fr/franceculture/podcasts/la-grande-table/x",
            "http://www.radiofrance.fr/franceinter/podcasts/le-masque-et-la-plume/x",
            "pas une url",
        ],
    )
    async def test_refuses_url_that_is_not_a_masque_et_la_plume_page(self, bad_url):
        service, mock_mongodb, mock_rss = make_service("")

        with pytest.raises(ManualEpisodeError, match="Le Masque et la Plume"):
            await service.add_from_radiofrance_page(bad_url)

        assert not service.fetch_page_html.called
        assert not mock_rss.download_audio.called


class TestFetchPageHtml:
    """Téléchargement de la page contre un vrai serveur HTTP local."""

    @staticmethod
    async def _serve(status: int, body: str) -> "TestServer":

        async def handler(request):
            return web.Response(status=status, text=body, content_type="text/html")

        app = web.Application()
        app.router.add_get("/page", handler)
        server = TestServer(app)
        await server.start_server()
        return server

    @pytest.mark.asyncio
    async def test_returns_page_html(self):
        html = read_fixture("episode_2024_07_21_full_episode.html")
        server = await self._serve(200, html)
        service = ManualEpisodeService(
            mongodb_service=MagicMock(), rss_sync_service=MagicMock()
        )
        try:
            result = await service.fetch_page_html(str(server.make_url("/page")))
        finally:
            await server.close()

        assert result == html

    @pytest.mark.asyncio
    async def test_unreachable_page_raises_bad_gateway_error(self):
        server = await self._serve(404, "Not Found")
        service = ManualEpisodeService(
            mongodb_service=MagicMock(), rss_sync_service=MagicMock()
        )
        try:
            with pytest.raises(ManualEpisodeError, match="404") as exc_info:
                await service.fetch_page_html(str(server.make_url("/page")))
        finally:
            await server.close()

        assert exc_info.value.status_code == 502
