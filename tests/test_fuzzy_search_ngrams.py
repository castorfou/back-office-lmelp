"""Tests pour le fuzzy search avec N-grams contigus (Issue #76)."""

import pytest
from fastapi.testclient import TestClient

from back_office_lmelp.app import app


class TestNGramExtraction:
    """Tests pour la fonction extract_ngrams."""

    def test_extract_bigrams(self):
        """Doit extraire des bigrammes (2 mots consécutifs)."""
        from back_office_lmelp.app import extract_ngrams

        text = "L'invention de Tristan"
        bigrams = extract_ngrams(text, 2)

        assert "L'invention de" in bigrams
        assert "de Tristan" in bigrams
        assert len(bigrams) == 2

    def test_extract_trigrams(self):
        """Doit extraire des trigrammes (3 mots consécutifs)."""
        from back_office_lmelp.app import extract_ngrams

        text = "L'invention de Tristan"
        trigrams = extract_ngrams(text, 3)

        assert "L'invention de Tristan" in trigrams
        assert len(trigrams) == 1

    def test_extract_quadrigrams(self):
        """Doit extraire des quadrigrammes (4 mots consécutifs)."""
        from back_office_lmelp.app import extract_ngrams

        text = "L'invention de Tristan Adrien"
        quadrigrams = extract_ngrams(text, 4)

        assert "L'invention de Tristan Adrien" in quadrigrams
        assert len(quadrigrams) == 1

    def test_extract_ngrams_short_text(self):
        """Doit gérer les textes plus courts que N."""
        from back_office_lmelp.app import extract_ngrams

        text = "Court"
        bigrams = extract_ngrams(text, 2)

        assert bigrams == []  # Pas assez de mots

    def test_extract_ngrams_empty_text(self):
        """Doit gérer le texte vide."""
        from back_office_lmelp.app import extract_ngrams

        text = ""
        bigrams = extract_ngrams(text, 2)

        assert bigrams == []


class TestFuzzySearchWithNGrams:
    """Tests d'intégration pour l'endpoint fuzzy-search avec N-grams."""

    @pytest.fixture
    def client(self):
        """Client de test FastAPI."""
        return TestClient(app)

    @pytest.fixture
    def mock_episode(self, monkeypatch):
        """Mock d'un épisode avec titre complet dans la description."""

        def mock_get_episode(episode_id):
            return {
                "_id": episode_id,
                "titre": "Émission du 15/01/2025",
                "description": (
                    "Cette semaine nous parlons de L'invention de Tristan "
                    "par Adrien Bosc publié chez Stock"
                ),
                "type": "livres",
                "date": "2025-01-15T10:00:00Z",
            }

        monkeypatch.setattr(
            "back_office_lmelp.app.mongodb_service.get_episode_by_id",
            mock_get_episode,
        )

    def test_fuzzy_search_finds_full_title_with_ngrams(self, client, mock_episode):
        """
        Test Cas 1 (Issue #76) : Titre long multi-mots.

        Doit trouver le titre complet "L'invention de Tristan" comme un tout,
        pas comme des fragments isolés.
        """
        response = client.post(
            "/api/fuzzy-search-episode",
            json={
                "episode_id": "test_episode_1",
                "query_title": "L'invention de Tristan",
                "query_author": "Adrien Bosc",
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Vérifier qu'on a trouvé des suggestions
        assert data["found_suggestions"] is True

        # Vérifier que le titre complet est dans les suggestions
        title_matches = data["title_matches"]
        titles = [match[0] for match in title_matches]

        # Le trigram "L'invention de Tristan" doit être trouvé avec un bon score
        assert any("L'invention de Tristan" in title for title in titles), (
            f"Titre complet non trouvé. Suggestions: {titles}"
        )

        # Le score du titre complet doit être >= 95
        for title, score in title_matches:
            if "L'invention de Tristan" in title:
                assert score >= 95, f"Score trop bas pour titre complet: {score}"
                break

    def test_fuzzy_search_apostrophe_title(self, client, monkeypatch):
        """
        Test Cas 2 (Issue #76) : Titre avec apostrophe.

        Doit trouver "Peau d'ourse" comme bigram.
        """

        def mock_get_episode(episode_id):
            return {
                "_id": episode_id,
                "titre": "Émission littéraire",
                "description": "Grégory Le Floch présente Peau d'ourse chez Seuil",
                "type": "livres",
                "date": "2025-01-15T10:00:00Z",
            }

        monkeypatch.setattr(
            "back_office_lmelp.app.mongodb_service.get_episode_by_id",
            mock_get_episode,
        )

        response = client.post(
            "/api/fuzzy-search-episode",
            json={
                "episode_id": "test_episode_2",
                "query_title": "Peau d'ourse",
                "query_author": "Grégory Le Floch",
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Vérifier qu'on a trouvé le titre
        title_matches = data["title_matches"]
        titles = [match[0] for match in title_matches]

        assert any("Peau d'ourse" in title for title in titles), (
            f"Titre avec apostrophe non trouvé. Suggestions: {titles}"
        )

        # Vérifier que le score du titre trouvé est au moins 90
        for title, score in title_matches:
            if "Peau d'ourse" in title:
                assert score >= 90, f"Score trop bas: {score}"
                break

    def test_fuzzy_search_prioritizes_longer_ngrams(self, client, monkeypatch):
        """
        Doit prioriser les n-grams plus longs (trigrams > bigrams > mots).

        Le titre complet "Un autre m'attend ailleurs" doit avoir un meilleur
        score que les fragments.
        """

        def mock_get_episode(episode_id):
            return {
                "_id": episode_id,
                "titre": "Critiques littéraires",
                "description": (
                    "Christophe Bigot parle de son livre "
                    "Un autre m'attend ailleurs publié chez Gallimard"
                ),
                "type": "livres",
                "date": "2025-01-15T10:00:00Z",
            }

        monkeypatch.setattr(
            "back_office_lmelp.app.mongodb_service.get_episode_by_id",
            mock_get_episode,
        )

        response = client.post(
            "/api/fuzzy-search-episode",
            json={
                "episode_id": "test_episode_3",
                "query_title": "Un autre m'attend ailleurs",
                "query_author": "Christophe Bigot",
            },
        )

        assert response.status_code == 200
        data = response.json()

        title_matches = data["title_matches"]
        titles_with_scores = [(match[0], match[1]) for match in title_matches]

        # Le titre complet ou un long n-gram doit être dans les résultats
        assert any(
            "m'attend ailleurs" in title or "Un autre m'attend" in title
            for title, _ in titles_with_scores
        ), f"N-grams du titre non trouvés. Suggestions: {titles_with_scores}"

        # Au moins un n-gram >= 3 mots avec score >= 85
        has_good_ngram = False
        for title, score in titles_with_scores:
            if len(title.split()) >= 3 and score >= 85:
                has_good_ngram = True
                break

        assert has_good_ngram, (
            f"Aucun n-gram long avec bon score. Résultats: {titles_with_scores}"
        )
