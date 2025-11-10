"""Tests pour l'endpoint de recherche avancée avec filtres et pagination."""


class TestAdvancedSearchFilters:
    """Tests pour les filtres par entité de la recherche avancée."""

    def test_advanced_search_all_entities_by_default(
        self, client, mock_mongodb_service
    ):
        """
        GIVEN: Une requête de recherche sans filtre d'entités
        WHEN: L'endpoint /api/advanced-search est appelé
        THEN: Retourne les résultats de toutes les entités (auteurs, livres, éditeurs, épisodes)
        """
        # Mock des méthodes de recherche MongoDB
        mock_mongodb_service.search_episodes.return_value = {
            "episodes": [{"titre": "Test Episode", "date": "2025-01-01"}],
            "total_count": 1,
        }
        mock_mongodb_service.search_auteurs.return_value = {
            "auteurs": [{"nom": "Albert Camus"}],
            "total_count": 1,
        }
        mock_mongodb_service.search_livres.return_value = {
            "livres": [{"titre": "L'Étranger"}],
            "total_count": 1,
        }
        mock_mongodb_service.search_critical_reviews_for_authors_books.return_value = {
            "editeurs": [{"nom": "Gallimard"}]
        }

        response = client.get("/api/advanced-search?q=Camus")

        assert response.status_code == 200
        data = response.json()

        # Vérifier la structure de la réponse
        assert "query" in data
        assert data["query"] == "Camus"
        assert "results" in data

        results = data["results"]
        # Toutes les catégories doivent être présentes
        assert "auteurs" in results
        assert "livres" in results
        assert "editeurs" in results
        assert "episodes" in results

    def test_advanced_search_filter_episodes_only(self, client, mock_mongodb_service):
        """
        GIVEN: Une requête avec filtre entities=episodes
        WHEN: L'endpoint /api/advanced-search est appelé
        THEN: Retourne uniquement les épisodes, autres catégories vides
        """
        # Mock uniquement search_episodes
        mock_mongodb_service.search_episodes.return_value = {
            "episodes": [{"titre": "Test Episode", "date": "2025-01-01"}],
            "total_count": 1,
        }

        response = client.get("/api/advanced-search?q=Camus&entities=episodes")

        assert response.status_code == 200
        data = response.json()

        results = data["results"]
        # Seuls les épisodes doivent avoir des résultats
        assert "episodes" in results
        assert len(results["episodes"]) > 0
        # Les autres catégories doivent être des listes vides
        assert results.get("auteurs", []) == []
        assert results.get("livres", []) == []
        assert results.get("editeurs", []) == []

    def test_advanced_search_filter_multiple_entities(
        self, client, mock_mongodb_service
    ):
        """
        GIVEN: Une requête avec filtre entities=auteurs,livres
        WHEN: L'endpoint /api/advanced-search est appelé
        THEN: Retourne uniquement auteurs et livres, autres catégories vides
        """
        # Mock auteurs et livres
        mock_mongodb_service.search_auteurs.return_value = {
            "auteurs": [{"nom": "Albert Camus"}],
            "total_count": 1,
        }
        mock_mongodb_service.search_livres.return_value = {
            "livres": [{"titre": "L'Étranger"}],
            "total_count": 1,
        }

        response = client.get("/api/advanced-search?q=Camus&entities=auteurs,livres")

        assert response.status_code == 200
        data = response.json()

        results = data["results"]
        # Auteurs et livres peuvent avoir des résultats
        assert "auteurs" in results
        assert "livres" in results
        assert len(results["auteurs"]) > 0
        assert len(results["livres"]) > 0
        # Épisodes et éditeurs doivent être vides
        assert results.get("episodes", []) == []
        assert results.get("editeurs", []) == []

    def test_advanced_search_invalid_entity_filter(self, client):
        """
        GIVEN: Une requête avec une entité invalide
        WHEN: L'endpoint /api/advanced-search est appelé
        THEN: Retourne une erreur 400
        """
        response = client.get("/api/advanced-search?q=Camus&entities=invalid_entity")

        assert response.status_code == 400
        assert "entité invalide" in response.json()["detail"].lower()

    def test_advanced_search_minimum_query_length(self, client):
        """
        GIVEN: Une requête avec moins de 3 caractères
        WHEN: L'endpoint /api/advanced-search est appelé
        THEN: Retourne une erreur 400
        """
        response = client.get("/api/advanced-search?q=Ca")

        assert response.status_code == 400
        assert "3 caractères" in response.json()["detail"]


class TestAdvancedSearchPagination:
    """Tests pour la pagination de la recherche avancée."""

    def test_advanced_search_default_pagination(self, client, mock_mongodb_service):
        """
        GIVEN: Une requête sans paramètres de pagination
        WHEN: L'endpoint /api/advanced-search est appelé
        THEN: Retourne la première page avec 20 résultats par défaut
        """
        # Mock avec résultats vides
        mock_mongodb_service.search_episodes.return_value = {
            "episodes": [],
            "total_count": 0,
        }
        mock_mongodb_service.search_auteurs.return_value = {
            "auteurs": [],
            "total_count": 0,
        }
        mock_mongodb_service.search_livres.return_value = {
            "livres": [],
            "total_count": 0,
        }
        mock_mongodb_service.search_critical_reviews_for_authors_books.return_value = {
            "editeurs": []
        }

        response = client.get("/api/advanced-search?q=livre")

        assert response.status_code == 200
        data = response.json()

        # Vérifier la structure de pagination
        assert "pagination" in data
        pagination = data["pagination"]
        assert pagination["page"] == 1
        assert pagination["limit"] == 20

    def test_advanced_search_custom_pagination(self, client, mock_mongodb_service):
        """
        GIVEN: Une requête avec page=2 et limit=10
        WHEN: L'endpoint /api/advanced-search est appelé
        THEN: Retourne la deuxième page avec 10 résultats
        """
        # Mock avec résultats vides
        mock_mongodb_service.search_episodes.return_value = {
            "episodes": [],
            "total_count": 0,
        }
        mock_mongodb_service.search_auteurs.return_value = {
            "auteurs": [],
            "total_count": 0,
        }
        mock_mongodb_service.search_livres.return_value = {
            "livres": [],
            "total_count": 0,
        }
        mock_mongodb_service.search_critical_reviews_for_authors_books.return_value = {
            "editeurs": []
        }

        response = client.get("/api/advanced-search?q=livre&page=2&limit=10")

        assert response.status_code == 200
        data = response.json()

        pagination = data["pagination"]
        assert pagination["page"] == 2
        assert pagination["limit"] == 10

    def test_advanced_search_pagination_total_counts(
        self, client, mock_mongodb_service
    ):
        """
        GIVEN: Une requête de recherche avec résultats
        WHEN: L'endpoint /api/advanced-search est appelé
        THEN: Retourne les compteurs totaux pour chaque catégorie
        """
        # Mock avec compteurs totaux
        mock_mongodb_service.search_episodes.return_value = {
            "episodes": [],
            "total_count": 42,
        }
        mock_mongodb_service.search_auteurs.return_value = {
            "auteurs": [],
            "total_count": 10,
        }
        mock_mongodb_service.search_livres.return_value = {
            "livres": [],
            "total_count": 25,
        }
        mock_mongodb_service.search_critical_reviews_for_authors_books.return_value = {
            "editeurs": []
        }

        response = client.get("/api/advanced-search?q=Camus")

        assert response.status_code == 200
        data = response.json()

        results = data["results"]
        # Chaque catégorie doit avoir un compteur total
        assert "auteurs_total_count" in results
        assert "livres_total_count" in results
        assert "episodes_total_count" in results
        assert results["auteurs_total_count"] == 10
        assert results["livres_total_count"] == 25
        assert results["episodes_total_count"] == 42

    def test_advanced_search_invalid_page_number(self, client):
        """
        GIVEN: Une requête avec page=0 (invalide)
        WHEN: L'endpoint /api/advanced-search est appelé
        THEN: Retourne une erreur 400
        """
        response = client.get("/api/advanced-search?q=livre&page=0")

        assert response.status_code == 400
        assert "page" in response.json()["detail"].lower()

    def test_advanced_search_invalid_limit(self, client):
        """
        GIVEN: Une requête avec limit=0 (invalide)
        WHEN: L'endpoint /api/advanced-search est appelé
        THEN: Retourne une erreur 400
        """
        response = client.get("/api/advanced-search?q=livre&limit=0")

        assert response.status_code == 400
        assert "limit" in response.json()["detail"].lower()

    def test_advanced_search_limit_too_large(self, client):
        """
        GIVEN: Une requête avec limit=200 (> 100)
        WHEN: L'endpoint /api/advanced-search est appelé
        THEN: Retourne une erreur 400
        """
        response = client.get("/api/advanced-search?q=livre&limit=200")

        assert response.status_code == 400
        assert "limit" in response.json()["detail"].lower()

    def test_advanced_search_pagination_page2_returns_different_results(
        self, client, mock_mongodb_service
    ):
        """
        GIVEN: Une recherche avec 44 livres au total et limit=20
        WHEN: Page 1 puis page 2 sont demandées
        THEN: Page 2 contient des résultats différents de page 1
        """
        # Simuler 44 livres totaux
        all_livres = [
            {"_id": f"livre{i}", "titre": f"Livre {i}", "auteur_nom": "Auteur"}
            for i in range(1, 45)
        ]

        # Page 1: livres 1-20
        mock_mongodb_service.search_livres.return_value = {
            "livres": all_livres[0:20],  # offset=0, limit=20
            "total_count": 44,
        }

        response_page1 = client.get(
            "/api/advanced-search?q=les&entities=livres&page=1&limit=20"
        )

        assert response_page1.status_code == 200
        data_page1 = response_page1.json()
        assert len(data_page1["results"]["livres"]) == 20
        assert data_page1["results"]["livres"][0]["_id"] == "livre1"

        # Page 2: livres 21-40
        mock_mongodb_service.search_livres.return_value = {
            "livres": all_livres[20:40],  # offset=20, limit=20
            "total_count": 44,
        }

        response_page2 = client.get(
            "/api/advanced-search?q=les&entities=livres&page=2&limit=20"
        )

        assert response_page2.status_code == 200
        data_page2 = response_page2.json()
        assert len(data_page2["results"]["livres"]) == 20
        assert data_page2["results"]["livres"][0]["_id"] == "livre21"
        # Vérifier que page 2 est différente de page 1
        assert (
            data_page2["results"]["livres"][0]["_id"]
            != data_page1["results"]["livres"][0]["_id"]
        )


class TestAdvancedSearchResponse:
    """Tests pour la structure et le contenu des réponses."""

    def test_advanced_search_response_structure(self, client, mock_mongodb_service):
        """
        GIVEN: Une requête de recherche valide
        WHEN: L'endpoint /api/advanced-search est appelé
        THEN: Retourne une structure de réponse complète et valide
        """
        # Mock avec résultats
        mock_mongodb_service.search_episodes.return_value = {
            "episodes": [],
            "total_count": 0,
        }
        mock_mongodb_service.search_auteurs.return_value = {
            "auteurs": [],
            "total_count": 0,
        }
        mock_mongodb_service.search_livres.return_value = {
            "livres": [],
            "total_count": 0,
        }
        mock_mongodb_service.search_critical_reviews_for_authors_books.return_value = {
            "editeurs": []
        }

        response = client.get("/api/advanced-search?q=Camus")

        assert response.status_code == 200
        data = response.json()

        # Structure globale
        assert "query" in data
        assert "results" in data
        assert "pagination" in data

        # Structure des résultats
        results = data["results"]
        assert all(
            key in results
            for key in [
                "auteurs",
                "auteurs_total_count",
                "livres",
                "livres_total_count",
                "editeurs",
                "episodes",
                "episodes_total_count",
            ]
        )

        # Structure de la pagination
        pagination = data["pagination"]
        assert all(key in pagination for key in ["page", "limit", "total_pages"])

    def test_advanced_search_episode_detailed_info(self, client, mock_mongodb_service):
        """
        GIVEN: Une requête de recherche retournant des épisodes
        WHEN: L'endpoint /api/advanced-search est appelé
        THEN: Les épisodes contiennent des métadonnées détaillées
        """
        # Mock avec un épisode détaillé
        mock_mongodb_service.search_episodes.return_value = {
            "episodes": [
                {
                    "titre": "Test Episode",
                    "titre_corrige": "Test Episode Corrigé",
                    "description": "Test description",
                    "description_corrigee": "Test description corrigée",
                    "date": "2025-01-01",
                    "_id": "507f1f77bcf86cd799439011",  # pragma: allowlist secret
                    "score": 0.95,
                    "match_type": "exact",
                    "search_context": "Context text",
                }
            ],
            "total_count": 1,
        }

        response = client.get("/api/advanced-search?q=test&entities=episodes")

        assert response.status_code == 200
        data = response.json()

        results = data["results"]
        assert len(results["episodes"]) > 0
        episode = results["episodes"][0]
        # Vérifier les champs détaillés
        assert "titre" in episode
        assert "description" in episode
        assert "date" in episode
        assert "_id" in episode
        # Champs de contexte de recherche
        assert "search_context" in episode
        assert "score" in episode

    def test_advanced_search_editeurs_with_pagination(
        self, client, mock_mongodb_service
    ):
        """
        GIVEN: Une recherche d'éditeurs avec 30 résultats et limit=10
        WHEN: Page 1 puis page 2 sont demandées
        THEN: Page 2 contient des éditeurs différents de page 1
        """
        # Simuler 30 éditeurs
        all_editeurs = [{"nom": f"Éditeur {i}"} for i in range(1, 31)]

        # Page 1: éditeurs 1-10 (offset=0, limit=10)
        mock_mongodb_service.search_editeurs.return_value = {
            "editeurs": all_editeurs[:10],  # Retourne les 10 premiers
            "total_count": 30,
        }

        response_page1 = client.get(
            "/api/advanced-search?q=edit&entities=editeurs&page=1&limit=10"
        )

        assert response_page1.status_code == 200
        data_page1 = response_page1.json()
        # Devrait retourner éditeurs 1-10 (10 premiers)
        assert len(data_page1["results"]["editeurs"]) == 10
        assert data_page1["results"]["editeurs"][0]["nom"] == "Éditeur 1"
        assert data_page1["results"]["editeurs"][9]["nom"] == "Éditeur 10"

        # Page 2: éditeurs 11-20 (offset=10, limit=10)
        mock_mongodb_service.search_editeurs.return_value = {
            "editeurs": all_editeurs[10:20],  # Retourne les 10 suivants
            "total_count": 30,
        }

        response_page2 = client.get(
            "/api/advanced-search?q=edit&entities=editeurs&page=2&limit=10"
        )

        assert response_page2.status_code == 200
        data_page2 = response_page2.json()
        # Devrait retourner éditeurs 11-20 (10 suivants)
        assert len(data_page2["results"]["editeurs"]) == 10
        assert data_page2["results"]["editeurs"][0]["nom"] == "Éditeur 11"
        assert data_page2["results"]["editeurs"][9]["nom"] == "Éditeur 20"

        # Vérifier que page 2 est différente de page 1
        assert (
            data_page2["results"]["editeurs"][0]["nom"]
            != data_page1["results"]["editeurs"][0]["nom"]
        )
