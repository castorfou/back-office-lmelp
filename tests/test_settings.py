"""Tests pour le module settings.

Ce module teste la classe Settings et ses propriétés d'environnement.
"""

import os

from back_office_lmelp.settings import Settings


class TestSettings:
    """Tests de la classe Settings."""

    def test_annas_archive_url_should_return_env_value_when_set(self):
        """Test que annas_archive_url retourne la valeur de l'env var quand définie."""
        # GIVEN: Env var ANNAS_ARCHIVE_URL définie
        os.environ["ANNAS_ARCHIVE_URL"] = "https://fr.annas-archive.se"

        try:
            # WHEN: On crée une instance Settings
            settings = Settings()

            # THEN: La propriété retourne la valeur de l'env var
            assert settings.annas_archive_url == "https://fr.annas-archive.se"
        finally:
            # Cleanup
            os.environ.pop("ANNAS_ARCHIVE_URL", None)

    def test_annas_archive_url_should_return_none_when_not_set(self):
        """Test que annas_archive_url retourne None si env var non définie."""
        # GIVEN: Env var ANNAS_ARCHIVE_URL non définie
        os.environ.pop("ANNAS_ARCHIVE_URL", None)

        # WHEN: On crée une instance Settings
        settings = Settings()

        # THEN: La propriété retourne None
        assert settings.annas_archive_url is None

    def test_annas_archive_url_should_return_none_when_empty_string(self):
        """Test que annas_archive_url retourne None si env var est vide."""
        # GIVEN: Env var ANNAS_ARCHIVE_URL vide
        os.environ["ANNAS_ARCHIVE_URL"] = ""

        try:
            # WHEN: On crée une instance Settings
            settings = Settings()

            # THEN: La propriété retourne None (pas une chaîne vide)
            assert settings.annas_archive_url is None
        finally:
            # Cleanup
            os.environ.pop("ANNAS_ARCHIVE_URL", None)
