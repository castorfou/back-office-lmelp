"""Tests pour le helper de notification ntfy.sh générique (Issue #309).

Extraction du pattern déjà validé dans RssSyncService.send_ntfy_notification
(Issue #295) vers une fonction standalone réutilisable par d'autres services
(ici, la transcription PGX) sans dupliquer la logique HTTP/aiohttp.
"""

from unittest.mock import patch

import pytest

from back_office_lmelp.utils.ntfy import send_ntfy_notification


class TestSendNtfyNotification:
    """Tests unitaires pour la notification ntfy.sh (générique, no-op si absent)."""

    @pytest.mark.asyncio
    async def test_noop_when_server_url_missing(self):
        with patch("aiohttp.ClientSession") as mock_session_cls:
            await send_ntfy_notification(None, "lmelp-pgx", "title", "message")

        assert not mock_session_cls.called

    @pytest.mark.asyncio
    async def test_noop_when_topic_missing(self):
        with patch("aiohttp.ClientSession") as mock_session_cls:
            await send_ntfy_notification("https://ntfy.sh", None, "title", "message")

        assert not mock_session_cls.called

    @pytest.mark.asyncio
    async def test_posts_to_ntfy_server_when_configured(self):
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
            await send_ntfy_notification(
                "https://ntfy.sh", "lmelp-pgx", "title", "message"
            )

        assert mock_session.called_with[0][0] == "https://ntfy.sh/lmelp-pgx"
        assert mock_session.called_with[1]["headers"]["Title"] == "PGX - title"

    @pytest.mark.asyncio
    async def test_posts_with_tags_header_when_provided(self):
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
            await send_ntfy_notification(
                "https://ntfy.sh",
                "lmelp-pgx",
                "title",
                "message",
                tags=["warning", "pgx"],
            )

        assert mock_session.called_with[1]["headers"]["Tags"] == "warning,pgx"

    @pytest.mark.asyncio
    async def test_swallows_exception_on_post_failure(self):
        with patch("aiohttp.ClientSession", side_effect=RuntimeError("boom")):
            # Ne doit pas lever - l'échec de notification ne doit jamais
            # casser le flux appelant.
            await send_ntfy_notification(
                "https://ntfy.sh", "lmelp-pgx", "title", "message"
            )
