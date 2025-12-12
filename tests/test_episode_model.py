"""Tests pour le modèle Episode.

Ce module teste la classe Episode et sa méthode to_dict().

Bug découvert pendant Issue #129:
- Le champ episode_page_url n'était pas inclus dans to_dict()
- Cela causait un re-fetch systématique côté frontend même quand l'URL existait en base
"""

from datetime import datetime

from back_office_lmelp.models.episode import Episode


class TestEpisodeModel:
    """Tests du modèle Episode."""

    def test_episode_to_dict_should_include_episode_page_url(self):
        """RED TEST - Issue #129: to_dict() devrait inclure episode_page_url.

        GIVEN: Un épisode avec episode_page_url en base MongoDB
        WHEN: to_dict() est appelé
        THEN: Le dictionnaire retourné contient episode_page_url

        Ce bug causait un re-fetch systématique côté frontend car le champ
        n'était jamais retourné par l'API GET /api/episodes/{id}.
        """
        # Arrange: Données MongoDB avec episode_page_url
        episode_data = {
            "_id": "507f1f77bcf86cd799439011",  # pragma: allowlist secret
            "titre": "Test Episode",
            "date": datetime(2023, 12, 10),
            "type": "podcast",
            "description": "Test description",
            "episode_page_url": "https://www.radiofrance.fr/franceinter/podcasts/le-masque-et-la-plume/test-123",
        }

        # Act
        episode = Episode(episode_data)
        result = episode.to_dict()

        # Assert: episode_page_url doit être dans le dictionnaire retourné
        assert "episode_page_url" in result
        assert result["episode_page_url"] == episode_data["episode_page_url"]

    def test_episode_to_dict_should_handle_missing_episode_page_url(self):
        """Test que to_dict() gère l'absence de episode_page_url (None).

        GIVEN: Un épisode sans episode_page_url en base
        WHEN: to_dict() est appelé
        THEN: Le dictionnaire contient episode_page_url=None
        """
        # Arrange: Données MongoDB sans episode_page_url
        episode_data = {
            "_id": "507f1f77bcf86cd799439011",  # pragma: allowlist secret
            "titre": "Test Episode",
            "date": datetime(2023, 12, 10),
            "type": "podcast",
            "description": "Test description",
            # Pas de episode_page_url
        }

        # Act
        episode = Episode(episode_data)
        result = episode.to_dict()

        # Assert: episode_page_url doit être None
        assert "episode_page_url" in result
        assert result["episode_page_url"] is None
