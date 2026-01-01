"""Tests pour l'extraction de métadonnées depuis RadioFrance."""

from unittest.mock import patch

import pytest

from back_office_lmelp.services.radiofrance_service import radiofrance_service


class TestExtractEpisodeMetadata:
    """Tests pour l'extraction de métadonnées RadioFrance."""

    @pytest.mark.asyncio
    async def test_extract_episode_metadata_from_json_ld(self):
        """Test extraction métadonnées depuis JSON-LD PodcastEpisode."""
        mock_html = """
        <html>
        <head>
        <script type="application/ld+json">
        {
          "@type": "PodcastEpisode",
          "author": [{"name": "Jérôme Garcin"}],
          "datePublished": "2025-01-15",
          "image": "https://cdn.radiofrance.fr/s3/image.jpg",
          "description": "Au programme avec Patricia Martin, Arnaud Viviant",
          "name": "Le Masque et la Plume avec Patricia Martin, Arnaud Viviant"
        }
        </script>
        </head>
        </html>
        """

        # Create context manager mock properly
        class MockResponse:
            def __init__(self):
                self.status = 200

            async def text(self):
                return mock_html

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

        with patch("aiohttp.ClientSession", return_value=MockSession()):
            result = await radiofrance_service.extract_episode_metadata(
                "https://www.radiofrance.fr/franceinter/podcasts/episode"
            )

            assert result["animateur"] == "Jérôme Garcin"
            assert "Patricia Martin" in result["critiques"]
            assert "Arnaud Viviant" in result["critiques"]
            assert result["date"] == "2025-01-15"
            assert result["image_url"] == "https://cdn.radiofrance.fr/s3/image.jpg"

    @pytest.mark.asyncio
    async def test_extract_episode_metadata_returns_empty_on_404(self):
        """Test retourne dict vide si 404."""

        class MockResponse:
            def __init__(self):
                self.status = 404

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

        with patch("aiohttp.ClientSession", return_value=MockSession()):
            result = await radiofrance_service.extract_episode_metadata(
                "https://www.radiofrance.fr/invalid"
            )

            assert result == {}

    @pytest.mark.asyncio
    async def test_extract_episode_metadata_handles_timeout(self):
        """Test gère les timeouts gracefully."""

        class MockResponse:
            async def __aenter__(self):
                raise TimeoutError()

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        class MockSession:
            def get(self, *args, **kwargs):
                return MockResponse()

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                return None

        with patch("aiohttp.ClientSession", return_value=MockSession()):
            result = await radiofrance_service.extract_episode_metadata(
                "https://www.radiofrance.fr/timeout"
            )

            assert result == {}


class TestExtractMetadataWithLLM:
    """Tests pour l'extraction de métadonnées par LLM."""

    @pytest.mark.asyncio
    async def test_extract_metadata_with_llm_success(self):
        """Test extraction LLM réussit avec page text valide."""
        import json
        from unittest.mock import MagicMock

        page_text = """
        Le Masque et la Plume
        Émission du dimanche 15 décembre 2019

        L'émission culturelle de France Inter, animée par Jérôme Garcin.

        Ce soir avec Patricia Martin, Arnaud Viviant et Xavier Leherpeur.

        Au programme: discussions sur les derniers livres et films.
        """

        mock_llm_response = {
            "animateur": "Jérôme Garcin",
            "critiques": ["Patricia Martin", "Arnaud Viviant", "Xavier Leherpeur"],
            "date": "2019-12-15",
        }

        # Mock Azure OpenAI response
        mock_choice = MagicMock()
        mock_choice.message.content = json.dumps(mock_llm_response)  # JSON valide

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        with patch.object(
            radiofrance_service,
            "client",
            MagicMock(
                chat=MagicMock(
                    completions=MagicMock(create=MagicMock(return_value=mock_response))
                )
            ),
        ):
            result = await radiofrance_service._extract_metadata_with_llm(page_text)

            assert result["animateur"] == "Jérôme Garcin"
            assert "Patricia Martin" in result["critiques"]
            assert "Arnaud Viviant" in result["critiques"]
            assert "Xavier Leherpeur" in result["critiques"]

    @pytest.mark.asyncio
    async def test_extract_metadata_with_llm_handles_empty_text(self):
        """Test gère texte vide gracefully."""
        result = await radiofrance_service._extract_metadata_with_llm("")

        assert result == {}

    @pytest.mark.asyncio
    async def test_extract_metadata_with_llm_handles_llm_error(self):
        """Test gère erreur LLM gracefully."""
        from unittest.mock import MagicMock

        with patch.object(
            radiofrance_service,
            "client",
            MagicMock(
                chat=MagicMock(
                    completions=MagicMock(
                        create=MagicMock(side_effect=Exception("LLM error"))
                    )
                )
            ),
        ):
            result = await radiofrance_service._extract_metadata_with_llm("test text")

            assert result == {}

    @pytest.mark.asyncio
    async def test_extract_episode_metadata_uses_llm_fallback(self):
        """Test utilise LLM fallback quand JSON-LD absent."""
        import json
        from unittest.mock import MagicMock

        # Page sans JSON-LD (comme les vieilles pages 2019)
        mock_html = """
        <html>
        <head><title>Le Masque et la Plume</title></head>
        <body>
            <h1>Le Masque et la Plume</h1>
            <p>Émission du 15 décembre 2019</p>
            <p>Animée par Jérôme Garcin</p>
            <p>Avec Patricia Martin, Arnaud Viviant</p>
        </body>
        </html>
        """

        mock_llm_response = {
            "animateur": "Jérôme Garcin",
            "critiques": ["Patricia Martin", "Arnaud Viviant"],
            "date": "2019-12-15",
        }

        class MockResponse:
            def __init__(self):
                self.status = 200

            async def text(self):
                return mock_html

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

        mock_choice = MagicMock()
        mock_choice.message.content = json.dumps(mock_llm_response)  # JSON valide

        mock_llm = MagicMock()
        mock_llm.choices = [mock_choice]

        with (
            patch("aiohttp.ClientSession", return_value=MockSession()),
            patch.object(
                radiofrance_service,
                "client",
                MagicMock(
                    chat=MagicMock(
                        completions=MagicMock(create=MagicMock(return_value=mock_llm))
                    )
                ),
            ),
        ):
            result = await radiofrance_service.extract_episode_metadata(
                "https://www.radiofrance.fr/franceinter/podcasts/2019-episode"
            )

            assert result["animateur"] == "Jérôme Garcin"
            assert "Patricia Martin" in result["critiques"]
            assert "Arnaud Viviant" in result["critiques"]


class TestParseJsonLdPodcastEpisode:
    """Tests pour le parsing JSON-LD."""

    def test_parse_json_ld_podcast_episode_success(self):
        """Test parsing réussit avec structure valide."""
        from bs4 import BeautifulSoup

        html = """
        <script type="application/ld+json">
        {
          "@type": "PodcastEpisode",
          "author": [{"name": "Jérôme Garcin"}],
          "datePublished": "2025-01-15",
          "image": "https://cdn.radiofrance.fr/s3/image.jpg",
          "description": "Test description",
          "name": "Le Masque et la Plume avec Michel Crépu, Judith Perrignon"
        }
        </script>
        """
        soup = BeautifulSoup(html, "html.parser")

        result = radiofrance_service._parse_json_ld_podcast_episode(soup)

        assert result["animateur"] == "Jérôme Garcin"
        assert "Michel Crépu" in result["critiques"]
        assert "Judith Perrignon" in result["critiques"]

    def test_parse_json_ld_returns_empty_if_no_podcast_episode(self):
        """Test retourne dict vide si pas de PodcastEpisode."""
        from bs4 import BeautifulSoup

        html = """
        <script type="application/ld+json">
        {
          "@type": "Article",
          "headline": "Not a podcast"
        }
        </script>
        """
        soup = BeautifulSoup(html, "html.parser")

        result = radiofrance_service._parse_json_ld_podcast_episode(soup)

        assert result == {}


class TestParseCriticsFromTitle:
    """Tests pour le parsing des noms de critiques."""

    def test_parse_critics_from_title_standard_pattern(self):
        """Test parsing noms critiques depuis titre."""
        title = "Le Masque et la Plume avec Patricia Martin, Arnaud Viviant, Xavier Leherpeur"

        critics = radiofrance_service._parse_critics_from_title(title)

        assert "Patricia Martin" in critics
        assert "Arnaud Viviant" in critics
        assert "Xavier Leherpeur" in critics

    def test_parse_critics_from_title_par_pattern(self):
        """Test parsing avec pattern 'par'."""
        title = "Le Masque et la Plume par Michel Crépu, Judith Perrignon"

        critics = radiofrance_service._parse_critics_from_title(title)

        assert "Michel Crépu" in critics
        assert "Judith Perrignon" in critics

    def test_parse_critics_from_title_with_et(self):
        """Test parsing avec 'et' entre noms."""
        title = "Le Masque avec Patricia Martin et Arnaud Viviant"

        critics = radiofrance_service._parse_critics_from_title(title)

        assert "Patricia Martin" in critics
        assert "Arnaud Viviant" in critics

    def test_parse_critics_filters_short_names(self):
        """Test filtre les noms trop courts (initiales)."""
        title = "Le Masque avec A, Patricia Martin"

        critics = radiofrance_service._parse_critics_from_title(title)

        assert "Patricia Martin" in critics
        assert "A" not in critics
