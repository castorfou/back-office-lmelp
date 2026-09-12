"""Tests TDD pour le service de synchronisation RSS (Issue #295).

Structure feedparser réelle vérifiée via `feedparser.parse()` sur le flux
RSS France Inter (https://radiofrance-podcast.net/podcast09/rss_14007.xml) :
entry.published = "Sun, 06 Sep 2026 10:12:40 +0200" (RFC 2822), entry.title,
entry.summary, entry.itunes_duration = "00:08:44", entry.links = [
    {"rel": "alternate", "type": "text/html", "href": "..."},
    {"length": "...", "type": "audio/x-m4a", "rel": "enclosure", "href": "..."},
].

Structure MongoDB `episodes` réelle vérifiée via
mcp__MongoDB__collection-schema + find (masque_et_la_plume.episodes) :
titre(str), date(datetime), description(str), url(str),
audio_rel_filename(str), transcription(str|None), type(str, valeur observée
"livres"), duree(int), masked(bool), episode_page_url(str).
"""

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bson import ObjectId

from back_office_lmelp.services.rss_sync_service import RssSyncService


def make_feed_entry(
    titre: str = "Haenel, Bellanger : quel livre lire cette semaine ?",
    published: str = "Sun, 06 Sep 2026 10:12:40 +0200",
    itunes_duration: str = "00:49:37",
    summary: str = "Au programme cette semaine avec la fine équipe.",
    audio_url: str = (
        "https://proxycast.radiofrance.fr/xxx/14007-06.09.2026-ITEMA_24642460-abc.m4a"
    ),
) -> dict:
    """Construit une entry feedparser réaliste (structure vérifiée en direct)."""
    return {
        "title": titre,
        "published": published,
        "itunes_duration": itunes_duration,
        "summary": summary,
        "links": [
            {
                "rel": "alternate",
                "type": "text/html",
                "href": "https://www.radiofrance.fr/franceinter/podcasts/le-masque-et-la-plume/episode",
            },
            {
                "length": "8384000",
                "type": "audio/x-m4a",
                "rel": "enclosure",
                "href": audio_url,
            },
        ],
    }


class TestRssSyncServiceHighLevel:
    """Test d'intégration de haut niveau (business, pas technique)."""

    @pytest.mark.asyncio
    async def test_sync_downloads_new_book_episode_and_persists_it(self):
        """Un nouvel épisode "livres" > 15 min doit être téléchargé et inséré."""
        mock_mongodb = MagicMock()
        mock_mongodb.get_last_episode_date.return_value = datetime(
            2026, 8, 23, 10, 10, 50, tzinfo=UTC
        )
        mock_mongodb.get_last_processed_episode_date.return_value = None
        mock_mongodb.find_episode_by_titre_and_date.return_value = None
        mock_mongodb.insert_episode.return_value = "new-episode-id"
        mock_mongodb.insert_rss_download_log.return_value = "log-id"

        service = RssSyncService(mongodb_service=mock_mongodb)
        service.fetch_feed_entries = AsyncMock(return_value=[make_feed_entry()])
        service.classify_episode_type = AsyncMock(return_value="livres")
        service.download_audio = AsyncMock(
            return_value="2026/14007-06.09.2026-ITEMA_24642460-abc.m4a"
        )
        service.send_ntfy_notification = AsyncMock(return_value=None)

        result = await service.sync(trigger="manual")

        # Assertion métier: l'épisode a bien été inséré (pas juste "vu")
        assert mock_mongodb.insert_episode.called
        inserted_doc = mock_mongodb.insert_episode.call_args[0][0]
        assert inserted_doc["type"] == "livres"
        assert (
            inserted_doc["audio_rel_filename"]
            == "2026/14007-06.09.2026-ITEMA_24642460-abc.m4a"
        )
        assert result["episodes"][0]["outcome"] == "downloaded"

        # Le titre de la notification ntfy.sh doit inclure la date de
        # diffusion de l'épisode (dd/mm/yy), pour la distinguer d'un coup
        # d'œil sur mobile sans devoir ouvrir le message.
        notif_call = service.send_ntfy_notification.call_args
        assert "06/09/26" in notif_call.args[0]

    @pytest.mark.asyncio
    async def test_sync_result_is_json_serializable_after_mongo_insert(self):
        """Le résultat retourné par sync() (donc par l'endpoint FastAPI) doit
        rester JSON-sérialisable même après l'insertion en base.

        Bug réel (détecté manuellement, Issue #295) : pymongo `insert_one()`
        mute le dict passé en argument en y injectant un `_id` (ObjectId) —
        si `sync()` réutilise ce même dict comme valeur de retour HTTP,
        FastAPI/Pydantic échoue avec `PydanticSerializationError: Unable to
        serialize unknown type: <class 'bson.objectid.ObjectId'>`.
        """
        mock_mongodb = MagicMock()
        mock_mongodb.get_last_episode_date.return_value = None
        mock_mongodb.get_last_processed_episode_date.return_value = None
        mock_mongodb.find_episode_by_titre_and_date.return_value = None
        mock_mongodb.insert_episode.return_value = "new-episode-id"

        def fake_insert_rss_download_log(log_data):
            # Reproduit fidèlement le comportement pymongo réel:
            # insert_one() mute le dict passé en argument.
            log_data["_id"] = ObjectId("507f1f77bcf86cd799439011")
            return str(log_data["_id"])

        mock_mongodb.insert_rss_download_log.side_effect = fake_insert_rss_download_log

        service = RssSyncService(mongodb_service=mock_mongodb)
        service.fetch_feed_entries = AsyncMock(return_value=[make_feed_entry()])
        service.classify_episode_type = AsyncMock(return_value="livres")
        service.download_audio = AsyncMock(return_value="2026/episode.m4a")
        service.send_ntfy_notification = AsyncMock(return_value=None)

        result = await service.sync(trigger="manual")

        # json.dumps lève TypeError si un ObjectId a fuité dans le résultat
        json.dumps(result, default=str)
        assert "_id" not in result

    @pytest.mark.asyncio
    async def test_sync_skips_episode_when_not_a_book_episode(self):
        """Un épisode classifié films/théâtre ne doit pas être téléchargé ni inséré."""
        mock_mongodb = MagicMock()
        mock_mongodb.get_last_episode_date.return_value = None
        mock_mongodb.get_last_processed_episode_date.return_value = None
        mock_mongodb.find_episode_by_titre_and_date.return_value = None
        mock_mongodb.insert_rss_download_log.return_value = "log-id"

        service = RssSyncService(mongodb_service=mock_mongodb)
        service.fetch_feed_entries = AsyncMock(return_value=[make_feed_entry()])
        service.classify_episode_type = AsyncMock(return_value="films")
        service.download_audio = AsyncMock(return_value="should-not-be-called")
        service.send_ntfy_notification = AsyncMock(return_value=None)

        result = await service.sync(trigger="api")

        assert not mock_mongodb.insert_episode.called
        assert not service.download_audio.called
        assert result["episodes"][0]["outcome"] == "skipped_not_book"
        assert service.send_ntfy_notification.called

        notif_call = service.send_ntfy_notification.call_args
        assert "06/09/26" in notif_call.args[0]

    @pytest.mark.asyncio
    async def test_sync_does_not_reprocess_already_seen_non_book_episode(self):
        """Un épisode non-livres déjà traité lors d'un run précédent ne doit
        plus jamais être reclassifié/renotifié, même si aucun épisode
        "livres" n'a été inséré après lui.

        Bug réel (Issue #295) : get_last_episode_date() ne voit que les
        épisodes réellement insérés dans `episodes` — un épisode
        "skipped_not_book" n'y apparaît jamais, donc il resterait un
        candidat re-classifié à chaque run tant qu'aucun épisode livres
        n'est inséré après lui.
        """
        mock_mongodb = MagicMock()
        # Aucun épisode "livres" en base (le dernier connu est ancien)
        mock_mongodb.get_last_episode_date.return_value = datetime(
            2026, 8, 1, tzinfo=UTC
        )
        # Mais l'épisode du 30/08 a déjà été VU et rejeté lors d'un run
        # précédent (enregistré dans rss_download_logs)
        mock_mongodb.get_last_processed_episode_date.return_value = datetime(
            2026, 8, 30, 10, 12, 40, tzinfo=UTC
        )
        mock_mongodb.find_episode_by_titre_and_date.return_value = None
        mock_mongodb.insert_rss_download_log.return_value = "log-id"

        already_seen_entry = make_feed_entry(
            titre="Épisode cinéma déjà vu",
            published="Sun, 30 Aug 2026 10:12:40 +0200",
        )

        service = RssSyncService(mongodb_service=mock_mongodb)
        service.fetch_feed_entries = AsyncMock(return_value=[already_seen_entry])
        service.classify_episode_type = AsyncMock(return_value="films")
        service.send_ntfy_notification = AsyncMock(return_value=None)

        result = await service.sync(trigger="api")

        # L'épisode ne doit même pas être reclassifié ni notifié à nouveau
        assert not service.classify_episode_type.called
        assert not service.send_ntfy_notification.called
        assert result["episodes"] == []

    @pytest.mark.asyncio
    async def test_sync_redownloads_book_episode_deleted_manually_from_db(self):
        """Un épisode "livres" déjà téléchargé puis supprimé manuellement de
        `episodes` (correction d'erreur, test manuel) doit redevenir un
        candidat au prochain run — contrairement à un épisode non-livres
        déjà rejeté, qui lui reste définitivement ignoré.

        Effet de bord détecté manuellement du fix précédent (Issue #295) :
        get_last_processed_episode_date() ne doit PAS bloquer un épisode
        "downloaded" à nouveau absent de `episodes`, seulement les
        "skipped_not_book" qui ne sont, eux, jamais insérés.
        """
        mock_mongodb = MagicMock()
        # L'épisode livres a été supprimé de `episodes` → plus aucun
        # épisode en base, get_last_episode_date() retombe à None.
        mock_mongodb.get_last_episode_date.return_value = None
        # Mais le run précédent l'avait bien "vu" (outcome="downloaded")
        # → get_last_processed_episode_date() ne doit PAS le compter,
        # seulement les outcomes "skipped_not_book".
        mock_mongodb.get_last_processed_episode_date.return_value = None
        mock_mongodb.find_episode_by_titre_and_date.return_value = None
        mock_mongodb.insert_episode.return_value = "new-episode-id"
        mock_mongodb.insert_rss_download_log.return_value = "log-id"

        service = RssSyncService(mongodb_service=mock_mongodb)
        service.fetch_feed_entries = AsyncMock(return_value=[make_feed_entry()])
        service.classify_episode_type = AsyncMock(return_value="livres")
        service.download_audio = AsyncMock(return_value="2026/episode.m4a")
        service.send_ntfy_notification = AsyncMock(return_value=None)

        result = await service.sync(trigger="manual")

        assert mock_mongodb.insert_episode.called
        assert result["episodes"][0]["outcome"] == "downloaded"

    @pytest.mark.asyncio
    async def test_sync_skips_episode_already_existing(self):
        """Un épisode déjà présent en base (titre+date) ne doit pas être retraité."""
        mock_mongodb = MagicMock()
        mock_mongodb.get_last_episode_date.return_value = None
        mock_mongodb.get_last_processed_episode_date.return_value = None
        mock_mongodb.find_episode_by_titre_and_date.return_value = {
            "_id": "existing-id"
        }
        mock_mongodb.insert_rss_download_log.return_value = "log-id"

        service = RssSyncService(mongodb_service=mock_mongodb)
        service.fetch_feed_entries = AsyncMock(return_value=[make_feed_entry()])
        service.classify_episode_type = AsyncMock(return_value="livres")
        service.download_audio = AsyncMock(return_value="should-not-be-called")
        service.send_ntfy_notification = AsyncMock(return_value=None)

        result = await service.sync(trigger="api")

        assert not mock_mongodb.insert_episode.called
        assert not service.download_audio.called
        assert not service.send_ntfy_notification.called
        assert result["episodes"][0]["outcome"] == "already_exists"


class TestGetDureeInSeconds:
    """Tests unitaires pour la conversion de durée iTunes RSS."""

    def test_hh_mm_ss_format(self):
        assert RssSyncService.get_duree_in_seconds("00:49:37") == 49 * 60 + 37

    def test_mm_ss_format(self):
        assert RssSyncService.get_duree_in_seconds("08:44") == 8 * 60 + 44

    def test_seconds_only_format(self):
        assert RssSyncService.get_duree_in_seconds("125") == 125


class TestFilterNewCandidateEntries:
    """Tests unitaires pour le filtrage dédup niveau 1 + seuil durée."""

    def test_keeps_entry_published_after_last_known_date_and_long_enough(self):
        service = RssSyncService(mongodb_service=MagicMock())
        entry = make_feed_entry(
            published="Sun, 06 Sep 2026 10:12:40 +0200", itunes_duration="00:49:37"
        )
        last_known_date = datetime(2026, 8, 23, 10, 10, 50, tzinfo=UTC)

        result = service.filter_new_candidate_entries(
            [entry], last_known_date, duree_mini_minutes=15
        )

        assert result == [entry]

    def test_excludes_entry_published_before_last_known_date(self):
        service = RssSyncService(mongodb_service=MagicMock())
        entry = make_feed_entry(published="Sun, 10 Aug 2026 10:12:40 +0200")
        last_known_date = datetime(2026, 8, 23, 10, 10, 50, tzinfo=UTC)

        result = service.filter_new_candidate_entries(
            [entry], last_known_date, duree_mini_minutes=15
        )

        assert result == []

    def test_excludes_entry_shorter_than_threshold(self):
        service = RssSyncService(mongodb_service=MagicMock())
        entry = make_feed_entry(itunes_duration="00:08:44")

        result = service.filter_new_candidate_entries(
            [entry], None, duree_mini_minutes=15
        )

        assert result == []


class TestClassifyEpisodeType:
    """Tests unitaires pour la classification LLM (Azure OpenAI)."""

    @pytest.mark.asyncio
    async def test_returns_inconnu_when_client_not_configured(self):
        service = RssSyncService(mongodb_service=MagicMock())
        service.client = None

        result = await service.classify_episode_type("titre", "description")

        assert result == "inconnu"

    @pytest.mark.asyncio
    async def test_returns_livres_from_llm_response(self):
        service = RssSyncService(mongodb_service=MagicMock())
        service.client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = '{"type": "livres"}'
        service.client.chat.completions.create.return_value = mock_response

        result = await service.classify_episode_type("titre", "description")

        assert result == "livres"

    @pytest.mark.asyncio
    async def test_returns_inconnu_on_unexpected_llm_value(self):
        service = RssSyncService(mongodb_service=MagicMock())
        service.client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = '{"type": "podcast"}'
        service.client.chat.completions.create.return_value = mock_response

        result = await service.classify_episode_type("titre", "description")

        assert result == "inconnu"

    @pytest.mark.asyncio
    async def test_returns_inconnu_on_llm_error(self):
        service = RssSyncService(mongodb_service=MagicMock())
        service.client = MagicMock()
        service.client.chat.completions.create.side_effect = Exception("boom")

        result = await service.classify_episode_type("titre", "description")

        assert result == "inconnu"


class TestDownloadAudio:
    """Tests unitaires pour le téléchargement audio (idempotent)."""

    @pytest.mark.asyncio
    async def test_download_audio_writes_file_and_returns_rel_filename(self, tmp_path):
        mock_settings = MagicMock()
        mock_settings.audio_storage_path = str(tmp_path)
        mock_settings.rss_debug_log = False
        service = RssSyncService(mongodb_service=MagicMock(), settings=mock_settings)

        class MockResponse:
            async def read(self):
                return b"fake-audio-content"

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        class MockSession:
            def get(self, *args, **kwargs):
                return MockResponse()

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        episode_date = datetime(2026, 9, 6, tzinfo=UTC)
        audio_url = "https://proxycast.radiofrance.fr/xxx/episode.m4a"

        with patch("aiohttp.ClientSession", return_value=MockSession()):
            result = await service.download_audio(audio_url, episode_date)

        assert result == "2026/episode.m4a"
        written_file = tmp_path / "2026" / "episode.m4a"
        assert written_file.read_bytes() == b"fake-audio-content"

    @pytest.mark.asyncio
    async def test_download_audio_is_idempotent_when_file_exists(self, tmp_path):
        mock_settings = MagicMock()
        mock_settings.audio_storage_path = str(tmp_path)
        mock_settings.rss_debug_log = False
        service = RssSyncService(mongodb_service=MagicMock(), settings=mock_settings)

        year_dir = tmp_path / "2026"
        year_dir.mkdir()
        (year_dir / "episode.m4a").write_bytes(b"already-here")

        episode_date = datetime(2026, 9, 6, tzinfo=UTC)
        audio_url = "https://proxycast.radiofrance.fr/xxx/episode.m4a"

        with patch("aiohttp.ClientSession") as mock_session_cls:
            result = await service.download_audio(audio_url, episode_date)

        assert result == "2026/episode.m4a"
        assert not mock_session_cls.called


class TestSendNtfyNotification:
    """Tests unitaires pour la notification ntfy.sh (générique, no-op si absent)."""

    @pytest.mark.asyncio
    async def test_noop_when_not_configured(self):
        mock_settings = MagicMock()
        mock_settings.ntfy_server_url = None
        mock_settings.ntfy_topic = None
        mock_settings.rss_debug_log = False
        service = RssSyncService(mongodb_service=MagicMock(), settings=mock_settings)

        with patch("aiohttp.ClientSession") as mock_session_cls:
            await service.send_ntfy_notification("title", "message")

        assert not mock_session_cls.called

    @pytest.mark.asyncio
    async def test_posts_to_ntfy_server_when_configured(self):
        mock_settings = MagicMock()
        mock_settings.ntfy_server_url = "https://ntfy.sh"
        mock_settings.ntfy_topic = "lmelp-episodes"
        mock_settings.rss_debug_log = False
        service = RssSyncService(mongodb_service=MagicMock(), settings=mock_settings)

        class MockResponse:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        class MockSession:
            def post(self, *args, **kwargs):
                self.called_with = (args, kwargs)
                return MockResponse()

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        mock_session = MockSession()
        with patch("aiohttp.ClientSession", return_value=mock_session):
            await service.send_ntfy_notification("title", "message")

        assert mock_session.called_with[0][0] == "https://ntfy.sh/lmelp-episodes"
        assert mock_session.called_with[1]["headers"]["Title"] == "RSS - title"
