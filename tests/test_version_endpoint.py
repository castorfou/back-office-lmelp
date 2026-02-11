"""Tests pour les endpoints /api/version et /api/changelog (Issue #205)."""

from fastapi.testclient import TestClient

from back_office_lmelp.app import app


class TestVersionEndpoint:
    """Tests pour l'endpoint /api/version."""

    def test_version_endpoint_returns_200(self):
        """L'endpoint /api/version doit retourner 200."""
        client = TestClient(app)
        response = client.get("/api/version")
        assert response.status_code == 200

    def test_version_endpoint_has_expected_keys(self):
        """La réponse doit contenir toutes les clés attendues."""
        client = TestClient(app)
        response = client.get("/api/version")
        data = response.json()
        required_keys = [
            "commit_hash",
            "commit_short",
            "commit_date",
            "build_date",
            "commit_url",
            "environment",
        ]
        for key in required_keys:
            assert key in data, f"Clé manquante: {key}"

    def test_version_endpoint_commit_short_is_7_chars_or_unknown(self):
        """commit_short doit faire 7 caractères ou être 'unknown'."""
        client = TestClient(app)
        response = client.get("/api/version")
        data = response.json()
        short = data["commit_short"]
        assert len(short) == 7 or short == "unknown"


class TestChangelogEndpoint:
    """Tests pour l'endpoint /api/changelog."""

    def test_changelog_endpoint_returns_200(self):
        """L'endpoint /api/changelog doit retourner 200."""
        client = TestClient(app)
        response = client.get("/api/changelog")
        assert response.status_code == 200

    def test_changelog_endpoint_returns_list(self):
        """La réponse doit être une liste."""
        client = TestClient(app)
        response = client.get("/api/changelog")
        data = response.json()
        assert isinstance(data, list)

    def test_changelog_entries_have_expected_keys(self):
        """Chaque entrée du changelog doit avoir hash, date, message."""
        client = TestClient(app)
        response = client.get("/api/changelog")
        data = response.json()
        # En dev, on a des commits avec #XXX (le repo a des issues)
        if len(data) > 0:
            entry = data[0]
            assert "hash" in entry
            assert "date" in entry
            assert "message" in entry

    def test_changelog_entries_reference_issues(self):
        """Toutes les entrées doivent référencer une issue/PR (#XXX)."""
        client = TestClient(app)
        response = client.get("/api/changelog")
        data = response.json()
        import re

        for entry in data:
            assert re.search(r"#\d+", entry["message"]), (
                f"Pas de ref issue/PR dans: {entry['message']}"
            )
