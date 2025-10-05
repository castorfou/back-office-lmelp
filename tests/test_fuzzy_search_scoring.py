"""Tests pour l'amélioration du scoring du fuzzy search (amélioration issue #76)."""

import pytest
from fastapi.testclient import TestClient

from back_office_lmelp.app import app


class TestFuzzySearchScoring:
    """Tests pour vérifier que le scoring favorise les matches complets."""

    @pytest.fixture
    def client(self):
        """Client de test FastAPI."""
        return TestClient(app)

    @pytest.fixture
    def mock_episode_adrien_bosc(self, monkeypatch):
        """Mock d'un épisode avec 'Adrien Bosc' dans le titre."""

        def mock_get_episode(episode_id):
            return {
                "_id": episode_id,
                "titre": "Au menu littéraire : Armistead Maupin, Grégoire Delacourt, Arnaud Cathrine, Sheena Patel, Adrien Bosc",
                "description": (
                    "durée : 00:47:33 - Le Masque et la Plume - "
                    "Une enquête sur la vie de Tristan Egolf ; "
                    "Une obsession rageuse sur les réseaux sociaux"
                ),
                "type": "livres",
                "date": "2025-06-22T10:00:00Z",
            }

        monkeypatch.setattr(
            "back_office_lmelp.app.mongodb_service.get_episode_by_id",
            mock_get_episode,
        )

    def test_author_scoring_prefers_complete_match_over_fragment(
        self, client, mock_episode_adrien_bosc
    ):
        """
        Test que "Adrien Bosc" (match complet) a un meilleur score que "Adrien" (fragment).

        Problème actuel :
        - Query: "Adrien Bosque"
        - Candidat 1: "Adrien Bosc" (1 char différent) → devrait avoir le meilleur score
        - Candidat 2: "Adrien" (fragment partiel) → devrait avoir un score inférieur

        Avec l'ancien algorithme (ratio), "Adrien" peut avoir un meilleur score
        car le dénominateur est plus petit.

        Avec WRatio, "Adrien Bosc" devrait gagner.
        """
        response = client.post(
            "/api/fuzzy-search-episode",
            json={
                "episode_id": "test_episode_scoring",
                "query_title": "",  # Pas de recherche de titre
                "query_author": "Adrien Bosque",  # Recherche d'auteur avec faute
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Vérifier qu'on a trouvé des suggestions d'auteur
        assert data["found_suggestions"] is True
        author_matches = data["author_matches"]
        assert len(author_matches) > 0

        # Créer un dictionnaire {match: score}
        matches_dict = {match[0]: match[1] for match in author_matches}

        # Vérifier que "Adrien Bosc" est dans les résultats
        adrien_bosc_matches = [
            (match, score)
            for match, score in matches_dict.items()
            if "Adrien Bosc" in match
        ]
        assert len(adrien_bosc_matches) > 0, (
            f"'Adrien Bosc' devrait être trouvé. Matches: {list(matches_dict.keys())}"
        )

        # Vérifier que "Adrien" seul est dans les résultats
        adrien_only_matches = [
            (match, score)
            for match, score in matches_dict.items()
            if match == "Adrien" or (match.strip() == "Adrien")
        ]

        if adrien_only_matches:
            # Si les deux sont présents, "Adrien Bosc" doit avoir un meilleur score
            best_adrien_bosc_score = max(score for _, score in adrien_bosc_matches)
            best_adrien_only_score = max(score for _, score in adrien_only_matches)

            assert best_adrien_bosc_score > best_adrien_only_score, (
                f"'Adrien Bosc' (score: {best_adrien_bosc_score}) devrait avoir un meilleur score "
                f"que 'Adrien' seul (score: {best_adrien_only_score}). "
                f"Tous les matches: {author_matches}"
            )

    def test_author_scoring_with_trigram(self, client, mock_episode_adrien_bosc):
        """
        Test que les trigrams contenant l'auteur complet ont un bon score.

        Query: "Adrien Bosque"
        Trigram: "Sheena Patel, Adrien Bosc" (contient l'auteur complet)

        Ce trigram devrait avoir un score raisonnable car il contient "Adrien Bosc".
        """
        response = client.post(
            "/api/fuzzy-search-episode",
            json={
                "episode_id": "test_episode_scoring",
                "query_title": "",
                "query_author": "Adrien Bosque",
            },
        )

        assert response.status_code == 200
        data = response.json()

        author_matches = data["author_matches"]

        # Le meilleur match devrait être un n-gram contenant "Adrien Bosc"
        # (soit "Adrien Bosc" seul, soit un trigram le contenant)
        top_match = author_matches[0]
        top_match_text, top_score = top_match

        # Le top match doit contenir "Adrien Bosc" ou au minimum "Adrien"
        assert "Adrien" in top_match_text, (
            f"Le meilleur match devrait contenir 'Adrien'. "
            f"Top match: {top_match_text} (score: {top_score})"
        )

        # Le score doit être >= 80 pour un match aussi proche
        # (83.3 pour "Adrien Bosc" vs "Adrien Bosque" est un bon score)
        assert top_score >= 80, (
            f"Le meilleur score devrait être >= 80 pour une faute d'orthographe mineure. "
            f"Score obtenu: {top_score} pour '{top_match_text}'"
        )

    def test_results_sorted_by_score_descending(self, client, mock_episode_adrien_bosc):
        """
        Test que les résultats sont triés par score décroissant.

        Les matches avec les meilleurs scores doivent apparaître en premier.
        """
        response = client.post(
            "/api/fuzzy-search-episode",
            json={
                "episode_id": "test_episode_scoring",
                "query_title": "",
                "query_author": "Adrien Bosque",
            },
        )

        assert response.status_code == 200
        data = response.json()

        author_matches = data["author_matches"]

        # Vérifier que les scores sont en ordre décroissant
        scores = [score for _, score in author_matches]
        assert scores == sorted(scores, reverse=True), (
            f"Les résultats devraient être triés par score décroissant. "
            f"Scores actuels: {scores}"
        )

    def test_title_scoring_with_no_match_returns_low_scores(
        self, client, mock_episode_adrien_bosc
    ):
        """
        Test que la recherche d'un titre absent retourne des scores bas.

        Query: "L'invention de Tristan" (absent de la description)
        Les scores devraient être bas pour indiquer qu'il n'y a pas de bon match.
        """
        response = client.post(
            "/api/fuzzy-search-episode",
            json={
                "episode_id": "test_episode_scoring",
                "query_title": "L'invention de Tristan",
                "query_author": "",
            },
        )

        assert response.status_code == 200
        data = response.json()

        title_matches = data["title_matches"]

        if title_matches:
            # Si des matches sont retournés, aucun ne devrait avoir un score > 75
            # car le titre complet n'est pas dans les métadonnées
            # Note: "de Tristan" peut matcher à ~74 car c'est un bigram présent
            top_score = max(score for _, score in title_matches)
            assert top_score < 75, (
                f"Le meilleur score devrait être < 75 car le titre complet n'est pas présent. "
                f"Score obtenu: {top_score}. Matches: {title_matches[:3]}"
            )
