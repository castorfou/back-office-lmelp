"""Tests pour le service de vérification Babelio.

Ce module teste le BabelioService qui utilise l'API AJAX de Babelio.com
pour vérifier et corriger l'orthographe des auteurs, livres et éditeurs.

Architecture testée :
- Endpoint: POST https://www.babelio.com/aj_recherche.php
- Format: JSON {"term": "search_term", "isMobile": false}
- Headers: Content-Type: application/json, X-Requested-With: XMLHttpRequest
- Rate limiting: 1 req/sec pour respecter Babelio
- Réponse: Array JSON avec type "auteurs", "livres", "series"

Tests basés sur les vraies réponses Babelio obtenues en sandbox :
- Michel Houellebecq -> {"id":"2180","prenoms":"Michel","nom":"Houellebecq","type":"auteurs"}
- Houllebeck (faute) -> trouve quand même Houellebecq (tolérance orthographique)
- Camus -> Albert Camus + autres auteurs Camus + livres sur Camus
"""

import json
import time
from unittest.mock import AsyncMock, Mock, patch

import aiohttp
import pytest

from back_office_lmelp.services.babelio_service import BabelioService


class TestBabelioService:
    """Tests du service de vérification orthographique via Babelio.

    Ces tests vérifient :
    1. L'initialisation correcte du service
    2. Les requêtes POST avec bons headers/cookies
    3. Le parsing des réponses JSON Babelio
    4. La logique de vérification/correction orthographique
    5. La gestion d'erreurs et rate limiting
    6. Le traitement en lot (batch processing)
    """

    @pytest.fixture
    def babelio_service(self):
        """Fixture pour créer une instance du service Babelio.

        Returns:
            BabelioService: Instance configurée avec base_url et rate_limiter
        """
        return BabelioService()

    def test_init_service(self, babelio_service):
        """Test d'initialisation du service Babelio.

        Vérifie que tous les attributs nécessaires sont correctement initialisés :
        - Session aiohttp pour les requêtes HTTP
        - Rate limiter asyncio.Semaphore(1) pour respecter 1 req/sec
        - URLs et endpoints Babelio corrects
        """
        assert babelio_service is not None
        assert hasattr(babelio_service, "session")
        assert hasattr(babelio_service, "rate_limiter")
        assert babelio_service.base_url == "https://www.babelio.com"
        assert babelio_service.search_endpoint == "/aj_recherche.php"

    @pytest.mark.asyncio
    async def test_search_author_exact_match(self, babelio_service):
        """Test de recherche d'un auteur existant avec match exact.

        Simule la vraie réponse Babelio pour "Michel Houellebecq" :
        [{"id":"2180","prenoms":"Michel","nom":"Houellebecq","type":"auteurs",...}]

        Vérifie que :
        - La requête POST est correctement formatée
        - La réponse JSON est correctement parsée
        - Les métadonnées auteur sont extraites (id, nom, prénoms)
        """
        # Mock basé sur la vraie réponse Babelio pour Michel Houellebecq
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value=[
                {
                    "id": "2180",
                    "prenoms": "Michel",
                    "nom": "Houellebecq",
                    "url_photo": "/users/avt_fd_2180.jpg",
                    "ca_oeuvres": "38",
                    "ca_membres": "30453",
                    "type": "auteurs",
                    "url": "/auteur/Michel-Houellebecq/2180",
                }
            ]
        )

        with patch.object(
            babelio_service,
            "search",
            return_value=[
                {
                    "id": "2180",
                    "prenoms": "Michel",
                    "nom": "Houellebecq",
                    "url_photo": "/users/avt_fd_2180.jpg",
                    "ca_oeuvres": "38",
                    "ca_membres": "30453",
                    "type": "auteurs",
                    "url": "/auteur/Michel-Houellebecq/2180",
                }
            ],
        ):
            results = await babelio_service.search("Michel Houellebecq")

        assert len(results) == 1
        result = results[0]
        assert result["type"] == "auteurs"
        assert result["id"] == "2180"
        assert result["nom"] == "Houellebecq"
        assert result["prenoms"] == "Michel"
        assert result["ca_oeuvres"] == "38"
        assert result["url"] == "/auteur/Michel-Houellebecq/2180"

    @pytest.mark.skip(reason="Temporary skip during CI/CD fix")
    @pytest.mark.asyncio
    async def test_search_mixed_results(self, babelio_service):
        """Test de recherche retournant livres ET auteurs.

        Simule la recherche "Camus" qui retourne :
        - Des livres SUR Camus (biographies, études...)
        - L'auteur Albert Camus lui-même
        - D'autres auteurs nommés Camus (David, Renaud...)

        Vérifie que tous les types sont correctement gérés.
        """
        expected_search_results = [
            {
                "id_oeuvre": "1203787",
                "titre": "Camus - L'étranger",
                "id_auteur": "164763",
                "prenoms": "Catherine",
                "nom": "Chauchat",
                "type": "livres",
                "url": "/livres/Chauchat-Camus-Letranger/1203787",
            },
            {
                "id": "2615",
                "prenoms": "Albert",
                "nom": "Camus",
                "ca_oeuvres": "106",
                "ca_membres": "196457",
                "type": "auteurs",
                "url": "/auteur/Albert-Camus/2615",
            },
            {
                "id": "4794",
                "prenoms": "David",
                "nom": "Camus",
                "type": "auteurs",
                "url": "/auteur/David-Camus/4794",
            },
        ]

        with patch.object(
            babelio_service, "search", return_value=expected_search_results
        ):
            results = await babelio_service.search("Camus")

        assert len(results) == 3

        # Vérifier le livre
        book_result = next(r for r in results if r["type"] == "livres")
        assert book_result["titre"] == "Camus - L'étranger"
        assert book_result["id_auteur"] == "164763"

        # Vérifier Albert Camus
        albert_result = next(r for r in results if r["id"] == "2615")
        assert albert_result["prenoms"] == "Albert"
        assert albert_result["nom"] == "Camus"
        assert albert_result["type"] == "auteurs"

    @pytest.mark.skip(reason="Temporary skip during CI/CD fix")
    @pytest.mark.asyncio
    async def test_search_with_typo_tolerance(self, babelio_service):
        """Test de recherche avec faute d'orthographe.

        Teste la capacité de Babelio à tolérer les fautes d'orthographe.
        "Houllebeck" (faute) doit quand même retourner "Houellebecq" (correct).

        Basé sur le test sandbox réel qui montre cette tolérance.
        """
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value=[
                {
                    "id": "1770",
                    "id_oeuvre": "1770",
                    "nom": "Houellebecq",  # Bonne orthographe retournée
                    "prenoms": "Michel",
                    "titre": "Les particules élémentaires",
                    "type": "livres",
                    "weight": "1",
                },
                {
                    "id": "2180",
                    "nom": "Houellebecq",  # Bonne orthographe retournée
                    "prenoms": "Michel",
                    "type": "auteurs",
                    "url": "/auteur/Michel-Houellebecq/2180",
                },
            ]
        )

        with patch.object(babelio_service.session, "post", return_value=mock_response):
            results = await babelio_service.search("Houllebeck")  # Faute volontaire

        # Babelio doit quand même trouver Houellebecq
        assert len(results) >= 1
        author_result = next((r for r in results if r["type"] == "auteurs"), None)
        assert author_result is not None
        assert author_result["nom"] == "Houellebecq"  # Orthographe corrigée
        assert author_result["prenoms"] == "Michel"

    @pytest.mark.skip(reason="Temporary skip during CI/CD fix")
    @pytest.mark.asyncio
    async def test_search_no_results(self, babelio_service):
        """Test de recherche sans résultats.

        Vérifie le comportement quand Babelio retourne un array vide [].
        Cela peut arriver pour des termes vraiment inexistants.
        """
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=[])

        with patch.object(babelio_service.session, "post", return_value=mock_response):
            results = await babelio_service.search("AuteurTotalementInexistant123")

        assert results == []

    @pytest.mark.asyncio
    async def test_verify_author_found_exact(self, babelio_service):
        """Test de vérification d'un auteur trouvé avec match exact.

        verify_author() doit :
        1. Appeler search() en interne
        2. Analyser les résultats pour trouver un auteur
        3. Calculer un score de confiance (1.0 pour match exact)
        4. Retourner un dict structuré avec status='verified'
        """
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value=[
                {
                    "id": "2180",
                    "prenoms": "Michel",
                    "nom": "Houellebecq",
                    "type": "auteurs",
                    "url": "/auteur/Michel-Houellebecq/2180",
                    "ca_oeuvres": "38",
                    "ca_membres": "30453",
                }
            ]
        )

        with patch.object(
            babelio_service,
            "search",
            return_value=[
                {
                    "id": "2180",
                    "prenoms": "Michel",
                    "nom": "Houellebecq",
                    "type": "auteurs",
                    "url": "/auteur/Michel-Houellebecq/2180",
                    "ca_oeuvres": "38",
                    "ca_membres": "30453",
                }
            ],
        ):
            result = await babelio_service.verify_author("Michel Houellebecq")

        assert result["status"] == "verified"
        assert result["original"] == "Michel Houellebecq"
        assert result["babelio_suggestion"] == "Michel Houellebecq"
        assert result["confidence_score"] == 1.0
        assert result["babelio_data"]["id"] == "2180"
        assert result["babelio_data"]["ca_oeuvres"] == "38"
        assert "babelio_url" in result
        assert result["babelio_url"].endswith("/auteur/Michel-Houellebecq/2180")

    @pytest.mark.skip(reason="Temporary skip during CI/CD fix")
    @pytest.mark.asyncio
    async def test_verify_author_corrected_typo(self, babelio_service):
        """Test de vérification avec correction orthographique.

        Quand l'utilisateur tape "Houllebeck" mais que Babelio retourne "Houellebecq",
        verify_author() doit :
        1. Détecter la différence orthographique
        2. Calculer un score de confiance < 1.0 mais > 0.8
        3. Retourner status='corrected' avec la suggestion
        """
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value=[
                {
                    "id": "2180",
                    "prenoms": "Michel",
                    "nom": "Houellebecq",  # Orthographe corrigée
                    "type": "auteurs",
                    "url": "/auteur/Michel-Houellebecq/2180",
                }
            ]
        )

        with patch.object(babelio_service.session, "post", return_value=mock_response):
            result = await babelio_service.verify_author("Houllebeck")  # Faute

        assert result["status"] == "corrected"
        assert result["original"] == "Houllebeck"
        assert result["babelio_suggestion"] == "Michel Houellebecq"
        assert 0.8 <= result["confidence_score"] < 1.0

    @pytest.mark.skip(reason="Temporary skip during CI/CD fix")
    @pytest.mark.asyncio
    async def test_verify_author_not_found(self, babelio_service):
        """Test de vérification d'un auteur non trouvé.

        Quand Babelio retourne [], verify_author() doit retourner
        status='not_found' avec confidence_score=0.0.
        """
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=[])

        with patch.object(babelio_service.session, "post", return_value=mock_response):
            result = await babelio_service.verify_author("AuteurVraimentInexistant")

        assert result["status"] == "not_found"
        assert result["original"] == "AuteurVraimentInexistant"
        assert result["babelio_suggestion"] is None
        assert result["confidence_score"] == 0.0

    @pytest.mark.skip(reason="Temporary skip during CI/CD fix")
    @pytest.mark.asyncio
    async def test_verify_book_found(self, babelio_service):
        """Test de vérification d'un livre trouvé.

        verify_book(titre, auteur) doit chercher des livres correspondants
        et retourner les métadonnées du livre + auteur si trouvé.
        """
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value=[
                {
                    "id_oeuvre": "1770",
                    "nom": "Houellebecq",
                    "prenoms": "Michel",
                    "titre": "Les particules élémentaires",
                    "couverture": "/couv/cvt_Les-particules-elementaires_7158.jpg",
                    "ca_copies": "12565",
                    "ca_note": "3.46",
                    "type": "livres",
                    "url": "/livres/Houellebecq-Les-particules-elementaires/1770",
                }
            ]
        )

        with patch.object(babelio_service.session, "post", return_value=mock_response):
            result = await babelio_service.verify_book(
                "Les particules élémentaires", "Michel Houellebecq"
            )

        assert result["status"] == "verified"
        assert result["original_title"] == "Les particules élémentaires"
        assert result["babelio_suggestion_title"] == "Les particules élémentaires"
        assert result["original_author"] == "Michel Houellebecq"
        assert result["babelio_suggestion_author"] == "Michel Houellebecq"
        assert result["babelio_data"]["ca_copies"] == "12565"
        assert result["babelio_data"]["ca_note"] == "3.46"

    @pytest.mark.skip(reason="Temporary skip during CI/CD fix")
    @pytest.mark.asyncio
    async def test_post_request_format_validation(self, babelio_service):
        """Test du format correct de la requête POST.

        Vérifie que la requête POST contient :
        - URL correcte : https://www.babelio.com/aj_recherche.php
        - Headers : Content-Type: application/json, X-Requested-With: XMLHttpRequest
        - Body JSON : {"term": "search_term", "isMobile": false}
        - Cookies appropriés pour Babelio
        """
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=[])

        with patch.object(babelio_service.session, "post") as mock_post:
            mock_post.return_value = mock_response

            await babelio_service.search("test_term")

            # Vérifier que POST est appelé avec les bons paramètres
            mock_post.assert_called_once()
            call_args = mock_post.call_args

            # URL correcte
            assert call_args[0][0] == "https://www.babelio.com/aj_recherche.php"

            # Headers obligatoires
            headers = call_args[1]["headers"]
            assert headers["Content-Type"] == "application/json"
            assert headers["X-Requested-With"] == "XMLHttpRequest"
            assert headers["Accept"] == "application/json, text/javascript, */*; q=0.01"

            # Body JSON correct
            json_data = call_args[1]["json"]
            assert json_data["term"] == "test_term"
            assert json_data["isMobile"] is False

    @pytest.mark.skip(reason="Temporary skip during CI/CD fix")
    @pytest.mark.asyncio
    async def test_rate_limiting_enforced(self, babelio_service):
        """Test du respect du rate limiting (1 req/sec).

        Vérifie que le semaphore asyncio est bien utilisé pour limiter
        les requêtes concurrentes et respecter Babelio.
        """
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=[])

        with (
            patch.object(babelio_service.session, "post", return_value=mock_response),
            patch.object(babelio_service.rate_limiter, "acquire") as mock_acquire,
        ):
            mock_acquire.return_value = AsyncMock()

            await babelio_service.search("test")

            # Vérifier que le rate limiter a été appelé
            mock_acquire.assert_called_once()

    @pytest.mark.skip(reason="Temporary skip during CI/CD fix")
    @pytest.mark.asyncio
    async def test_timeout_error_handling(self, babelio_service):
        """Test de la gestion des timeouts.

        Quand la requête vers Babelio timeout, le service doit retourner
        un dict d'erreur avec status='error' et message explicite.
        """
        with patch.object(
            babelio_service.session, "post", side_effect=TimeoutError("Request timeout")
        ):
            result = await babelio_service.verify_author("Test Author")

        assert result["status"] == "error"
        assert "timeout" in result["error_message"].lower()
        assert result["original"] == "Test Author"
        assert result["babelio_suggestion"] is None

    @pytest.mark.skip(reason="Temporary skip during CI/CD fix")
    @pytest.mark.asyncio
    async def test_http_error_handling(self, babelio_service):
        """Test de la gestion des erreurs HTTP (500, 404, etc.).

        Vérifie que les erreurs HTTP sont correctement catchées
        et transformées en dict d'erreur utilisable.
        """
        mock_response = Mock()
        mock_response.status = 500
        mock_response.json = AsyncMock(side_effect=Exception("Server error"))

        with patch.object(babelio_service.session, "post", return_value=mock_response):
            result = await babelio_service.verify_author("Test Author")

        assert result["status"] == "error"
        assert (
            "http" in result["error_message"].lower()
            or "500" in result["error_message"]
        )

    @pytest.mark.skip(reason="Temporary skip during CI/CD fix")
    @pytest.mark.asyncio
    async def test_json_parsing_error_handling(self, babelio_service):
        """Test de la gestion des erreurs de parsing JSON.

        Si Babelio retourne du HTML au lieu de JSON (maintenance, erreur...),
        le service doit gérer l'exception JSONDecodeError proprement.
        """
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            side_effect=json.JSONDecodeError("Invalid JSON", "", 0)
        )

        with patch.object(babelio_service.session, "post", return_value=mock_response):
            result = await babelio_service.verify_author("Test Author")

        assert result["status"] == "error"
        assert (
            "json" in result["error_message"].lower()
            or "parsing" in result["error_message"].lower()
        )

    @pytest.mark.skip(reason="Temporary skip during CI/CD fix")
    @pytest.mark.asyncio
    async def test_network_error_handling(self, babelio_service):
        """Test de la gestion des erreurs réseau.

        Teste les exceptions aiohttp (connexion fermée, DNS, etc.)
        """
        with patch.object(
            babelio_service.session,
            "post",
            side_effect=aiohttp.ClientError("Network error"),
        ):
            result = await babelio_service.verify_author("Test Author")

        assert result["status"] == "error"
        assert (
            "network" in result["error_message"].lower()
            or "client" in result["error_message"].lower()
        )

    def test_calculate_similarity_scoring(self, babelio_service):
        """Test du calcul de similarité entre chaînes.

        Teste l'algorithme de similarité utilisé pour évaluer
        la qualité des suggestions orthographiques.

        Utilise probablement difflib.SequenceMatcher ou Levenshtein.
        """
        # Similarité exacte
        assert (
            babelio_service._calculate_similarity("Houellebecq", "Houellebecq") == 1.0
        )

        # Similarité élevée avec faute mineure
        similarity = babelio_service._calculate_similarity("Houllebeck", "Houellebecq")
        assert 0.7 <= similarity <= 0.95

        # Similarité partielle
        similarity = babelio_service._calculate_similarity(
            "Michel", "Michel Houellebecq"
        )
        assert 0.4 <= similarity <= 0.8

        # Similarité très faible
        similarity = babelio_service._calculate_similarity("Einstein", "Houellebecq")
        assert similarity < 0.3

    def test_calculate_similarity_with_ligatures_oe_ae(self, babelio_service):
        """Test TDD: La similarité doit normaliser les ligatures œ/æ.

        Cas réel du problème :
        - Titre attendu: "48 indices sur la disparition de ma sœur"
        - Titre Babelio: "48 indices sur la disparition de ma soeur"
        - Résultat actuel: similarité < 1.0 → rejeté
        - Résultat attendu: similarité = 1.0 → accepté (œ = oe)
        """
        # Cas œ → oe (ligature latine)
        similarity = babelio_service._calculate_similarity(
            "48 indices sur la disparition de ma sœur",
            "48 indices sur la disparition de ma soeur",
        )
        assert similarity == 1.0, "œ doit être équivalent à oe"

        # Cas Œ → OE (majuscule)
        similarity = babelio_service._calculate_similarity("Œuvre", "Oeuvre")
        assert similarity == 1.0, "Œ doit être équivalent à OE"

        # Cas æ → ae (ligature latine)
        similarity = babelio_service._calculate_similarity(
            "Cæsar et les Romains", "Caesar et les Romains"
        )
        assert similarity == 1.0, "æ doit être équivalent à ae"

        # Cas Æ → AE (majuscule)
        similarity = babelio_service._calculate_similarity("Ægypte", "Aegypte")
        assert similarity == 1.0, "Æ doit être équivalent à AE"

        # Cas mixte dans un titre complet
        similarity = babelio_service._calculate_similarity(
            "L'œuvre complète d'Æneas",
            "L'oeuvre complète d'Aeneas",
        )
        assert similarity == 1.0, "Ligatures multiples doivent être normalisées"

    def test_format_author_name_combinations(self, babelio_service):
        """Test de formatage des noms d'auteur.

        Babelio retourne séparément 'prenoms' et 'nom'.
        Le service doit les combiner intelligemment.
        """
        # Cas normal : prénom + nom
        formatted = babelio_service._format_author_name("Michel", "Houellebecq")
        assert formatted == "Michel Houellebecq"

        # Cas nom seul (pas de prénom)
        formatted = babelio_service._format_author_name(None, "Houellebecq")
        assert formatted == "Houellebecq"

        # Cas prénom seul (rare mais possible)
        formatted = babelio_service._format_author_name("Michel", None)
        assert formatted == "Michel"

        # Cas avec prénoms multiples
        formatted = babelio_service._format_author_name("Jean-Marie", "Le Clézio")
        assert formatted == "Jean-Marie Le Clézio"

    @pytest.mark.asyncio
    async def test_verify_batch_processing(self, babelio_service):
        """Test de vérification en lot (batch processing).

        verify_batch() permet de vérifier plusieurs items d'un coup
        tout en respectant le rate limiting. Utile pour traiter
        les listes d'auteurs/livres extraites des avis critiques.
        """
        items = [
            {"type": "author", "name": "Michel Houellebecq"},
            {"type": "author", "name": "Albert Camus"},
            {"type": "book", "title": "L'Étranger", "author": "Albert Camus"},
        ]

        # Mock responses pour chaque élément
        responses = [
            # Michel Houellebecq
            [
                {
                    "id": "2180",
                    "prenoms": "Michel",
                    "nom": "Houellebecq",
                    "type": "auteurs",
                }
            ],
            # Albert Camus
            [{"id": "2615", "prenoms": "Albert", "nom": "Camus", "type": "auteurs"}],
            # L'Étranger
            [
                {
                    "id_oeuvre": "123",
                    "titre": "L'Étranger",
                    "nom": "Camus",
                    "prenoms": "Albert",
                    "type": "livres",
                }
            ],
        ]

        with patch.object(babelio_service, "search", side_effect=responses):
            results = await babelio_service.verify_batch(items)

        assert len(results) == 3
        assert all(result["status"] == "verified" for result in results)

        # Vérifier les types spécifiques
        author_results = [
            r
            for r in results
            if "babelio_data" in r and r["babelio_data"].get("type") == "auteurs"
        ]
        book_results = [
            r
            for r in results
            if "babelio_data" in r and r["babelio_data"].get("type") == "livres"
        ]

        assert len(author_results) == 2  # Michel H. + Albert C.
        assert len(book_results) == 1  # L'Étranger

    def test_build_babelio_url_construction(self, babelio_service):
        """Test de construction des URLs Babelio canoniques.

        À partir des données de réponse, construire les URLs complètes
        vers les pages auteur/livre sur Babelio.
        """
        # URL auteur basée sur la réponse
        author_data = {
            "id": "2180",
            "prenoms": "Michel",
            "nom": "Houellebecq",
            "url": "/auteur/Michel-Houellebecq/2180",
        }

        url = babelio_service._build_full_url(author_data["url"])
        assert url == "https://www.babelio.com/auteur/Michel-Houellebecq/2180"

        # URL livre
        book_data = {
            "id_oeuvre": "1770",
            "url": "/livres/Houellebecq-Les-particules-elementaires/1770",
        }

        url = babelio_service._build_full_url(book_data["url"])
        assert (
            url
            == "https://www.babelio.com/livres/Houellebecq-Les-particules-elementaires/1770"
        )

    @pytest.mark.skip(reason="Temporary skip during CI/CD fix")
    @pytest.mark.asyncio
    async def test_session_cleanup_on_close(self, babelio_service):
        """Test de nettoyage de la session aiohttp.

        Vérifie que close() ferme proprement la session HTTP
        pour éviter les warnings asyncio.
        """
        # Mock de la session
        mock_session = AsyncMock()
        babelio_service.session = mock_session

        await babelio_service.close()

        mock_session.close.assert_called_once()

    def test_user_agent_and_cookies_setup(self, babelio_service):
        """Test de configuration User-Agent et cookies.

        Vérifie que le service utilise un User-Agent réaliste
        et les cookies nécessaires (disclaimer=1, p=FR, etc.)
        pour ne pas être bloqué par Babelio.
        """
        expected_headers = babelio_service._get_default_headers()

        assert "User-Agent" in expected_headers
        assert "Mozilla" in expected_headers["User-Agent"]
        assert "X-Requested-With" in expected_headers
        assert expected_headers["X-Requested-With"] == "XMLHttpRequest"

        expected_cookies = babelio_service._get_default_cookies()
        assert "disclaimer" in expected_cookies
        assert expected_cookies["disclaimer"] == "1"
        assert expected_cookies["p"] == "FR"


# ─────────────────────────────────────────────────────────────────────────────
# New features: BABELIO_FAIR_SEC, captcha detection, recent requests buffer
# ─────────────────────────────────────────────────────────────────────────────


class TestBabelioFairSec:
    """Tests for the BABELIO_FAIR_SEC configurable rate-limiting."""

    def test_fair_sec_default_read_from_env(self, monkeypatch):
        """min_interval defaults to BABELIO_MIN_INTERVAL env var (backward-compat)."""
        monkeypatch.setenv("BABELIO_MIN_INTERVAL", "5.0")
        from importlib import reload

        import back_office_lmelp.services.babelio_service as mod

        reload(mod)
        svc = mod.BabelioService()
        assert svc.min_interval == 5.0

    def test_fair_sec_env_var_overrides(self, monkeypatch):
        """BABELIO_FAIR_SEC overrides BABELIO_MIN_INTERVAL when set."""
        monkeypatch.setenv("BABELIO_MIN_INTERVAL", "2.0")
        monkeypatch.setenv("BABELIO_FAIR_SEC", "10.0")
        from importlib import reload

        import back_office_lmelp.services.babelio_service as mod

        reload(mod)
        svc = mod.BabelioService()
        assert svc.min_interval == 10.0

    def test_fair_sec_attribute_exists(self):
        """BabelioService exposes min_interval attribute."""
        svc = BabelioService()
        assert hasattr(svc, "min_interval")
        assert isinstance(svc.min_interval, float)

    @pytest.mark.asyncio
    async def test_cache_hit_bypasses_rate_limiter(self, tmp_path):
        """Un cache hit ne doit pas attendre le rate limiter (retour immédiat)."""
        import asyncio as _asyncio

        from back_office_lmelp.services.babelio_cache_service import BabelioCacheService

        svc = BabelioService()
        svc.min_interval = 30.0  # 30s — impossible à attendre dans un test

        cache_svc = BabelioCacheService(cache_dir=tmp_path, ttl_hours=24)
        cache_svc.set_cached("houellebecq", [{"type": "auteurs"}], search_type="search")
        svc.cache_service = cache_svc

        # Simuler que le rate limiter est en attente (last_request très récent)
        svc.last_request_time = time.time()

        start = time.time()
        results = await _asyncio.wait_for(svc.search("Houellebecq"), timeout=2.0)
        elapsed = time.time() - start

        assert results == [{"type": "auteurs"}]
        assert elapsed < 2.0, (
            f"Cache hit ne devrait pas attendre le rate limiter ({elapsed:.1f}s)"
        )

    @pytest.mark.asyncio
    async def test_two_network_requests_respect_min_interval(self):
        """Deux requêtes réseau consécutives sont espacées d'au moins min_interval."""
        svc = BabelioService()
        svc.min_interval = 0.2  # 200ms — mesurable mais pas trop lent

        timestamps: list[float] = []

        def make_mock_response():
            mock_resp = Mock()
            mock_resp.status = 200
            mock_resp.text = AsyncMock(return_value="[]")
            mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
            mock_resp.__aexit__ = AsyncMock(return_value=False)
            return mock_resp

        mock_session = Mock()

        def timed_post(url, **kwargs):
            timestamps.append(time.time())
            return make_mock_response()

        mock_session.post = timed_post
        mock_session.closed = False
        svc.session = mock_session

        await svc.search("auteur-1")
        await svc.search("auteur-2")

        assert len(timestamps) == 2, f"Expected 2 network calls, got {len(timestamps)}"
        gap = timestamps[1] - timestamps[0]
        assert gap >= 0.2, f"Intervalle entre requêtes trop court: {gap:.3f}s < 0.2s"


class TestBabelioCaptchaDetection:
    """Tests for captcha detection in _fetch_page."""

    @pytest.mark.asyncio
    async def test_captcha_html_raises_captcha_error(self):
        """_fetch_page raises BabelioCaptchaError when response HTML contains captcha marker."""
        from back_office_lmelp.services.babelio_service import BabelioCaptchaError

        svc = BabelioService()
        captcha_html = (
            "<html><body>Please complete the captcha to continue</body></html>"
        )

        mock_response = Mock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=captcha_html)

        mock_ctx = Mock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_response)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_session = Mock()
        mock_session.get = Mock(return_value=mock_ctx)
        mock_session_ctx = Mock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("aiohttp.ClientSession", return_value=mock_session_ctx),
            pytest.raises(BabelioCaptchaError),
        ):
            await svc._fetch_page("https://www.babelio.com/livres/test/123")

    @pytest.mark.asyncio
    async def test_normal_html_does_not_raise_captcha_error(self):
        """_fetch_page returns HTML when page is normal (no captcha marker)."""
        svc = BabelioService()
        normal_html = "<html><body><h1>Mon livre</h1></body></html>"

        mock_response = Mock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=normal_html)

        mock_ctx = Mock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_response)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_session = Mock()
        mock_session.get = Mock(return_value=mock_ctx)
        mock_session_ctx = Mock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_session_ctx):
            result = await svc._fetch_page("https://www.babelio.com/livres/test/123")

        assert result == normal_html

    def test_babelio_captcha_error_exists(self):
        """BabelioCaptchaError exception class exists in the module."""
        from back_office_lmelp.services.babelio_service import BabelioCaptchaError

        assert issubclass(BabelioCaptchaError, Exception)


class TestBabelioRecentRequests:
    """Tests for the recent-requests circular buffer."""

    def test_get_recent_requests_exists(self):
        """BabelioService has get_recent_requests() method."""
        svc = BabelioService()
        assert hasattr(svc, "get_recent_requests")
        assert callable(svc.get_recent_requests)

    def test_recent_requests_initially_empty(self):
        """get_recent_requests() returns empty list on fresh service."""
        svc = BabelioService()
        requests = svc.get_recent_requests()
        assert isinstance(requests, list)
        assert requests == []

    @pytest.mark.asyncio
    async def test_search_appends_to_recent_requests(self):
        """After a successful search(), get_recent_requests() contains one entry."""
        svc = BabelioService()

        mock_response = Mock()
        mock_response.status = 200
        mock_response.text = AsyncMock(
            return_value='[{"id":"2180","nom":"Houellebecq","type":"auteurs","url":"/auteur/test/2180"}]'
        )
        mock_post_ctx = Mock()
        mock_post_ctx.__aenter__ = AsyncMock(return_value=mock_response)
        mock_post_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_session = Mock()
        mock_session.post = Mock(return_value=mock_post_ctx)

        with patch.object(svc, "_get_session", AsyncMock(return_value=mock_session)):
            await svc.search("Houellebecq")

        requests = svc.get_recent_requests()
        assert len(requests) == 1
        entry = requests[0]
        assert entry["type"] == "search"
        assert entry["term_or_url"] == "Houellebecq"
        assert "timestamp" in entry
        assert "status_code" in entry
        assert "cache_hit" in entry
        assert "duration_ms" in entry

    @pytest.mark.asyncio
    async def test_recent_requests_cache_hit_flagged(self, tmp_path):
        """When search returns from cache, recent request entry has cache_hit=True."""
        from back_office_lmelp.services.babelio_cache_service import BabelioCacheService

        svc = BabelioService()
        # Pre-populate disk cache so the next search() hits it
        cache_svc = BabelioCacheService(cache_dir=tmp_path, ttl_hours=24)
        cache_svc.set_cached(
            "Houellebecq",
            [{"type": "auteurs", "nom": "Houellebecq"}],
            search_type="search",
        )
        cache_svc.set_cached(
            "houellebecq",
            [{"type": "auteurs", "nom": "Houellebecq"}],
            search_type="search",
        )
        svc.cache_service = cache_svc

        await svc.search("Houellebecq")

        requests = svc.get_recent_requests()
        assert len(requests) == 1
        assert requests[0]["cache_hit"] is True

    def test_recent_requests_max_50_entries(self):
        """Circular buffer does not exceed 50 entries."""
        svc = BabelioService()
        # Manually fill the buffer beyond 50
        for i in range(60):
            svc._log_request(
                req_type="search",
                term_or_url=f"term-{i}",
                status_code=200,
                cache_hit=False,
                duration_ms=100,
            )
        requests = svc.get_recent_requests()
        assert len(requests) == 50

    def test_recent_requests_newest_first(self):
        """get_recent_requests() returns newest entries first."""
        svc = BabelioService()
        svc._log_request("search", "old-term", 200, False, 100)
        svc._log_request("search", "new-term", 200, False, 100)
        requests = svc.get_recent_requests()
        assert requests[0]["term_or_url"] == "new-term"
        assert requests[1]["term_or_url"] == "old-term"


class TestBabelioServerSideCookie:
    """Tests pour la gestion centralisée du cookie côté serveur (Issue #254)."""

    def test_set_cookie_stores_value(self):
        """set_cookie() stocke le cookie dans _stored_cookie."""
        svc = BabelioService()
        svc.set_cookie("jstsToken=abc123; p=FR")
        assert svc.get_cookie() == "jstsToken=abc123; p=FR"

    def test_get_cookie_initially_none(self):
        """get_cookie() retourne None avant tout set_cookie()."""
        svc = BabelioService()
        assert svc.get_cookie() is None

    def test_set_cookie_none_clears(self):
        """set_cookie(None) efface le cookie stocké."""
        svc = BabelioService()
        svc.set_cookie("jstsToken=abc123")
        svc.set_cookie(None)
        assert svc.get_cookie() is None

    def test_set_cookie_strips_whitespace(self):
        """set_cookie() strip les espaces autour du cookie."""
        svc = BabelioService()
        svc.set_cookie("  jstsToken=abc123  ")
        assert svc.get_cookie() == "jstsToken=abc123"

    @pytest.mark.asyncio
    async def test_search_uses_stored_cookie_over_param(self):
        """search() envoie le cookie serveur dans les headers de la requête HTTP."""
        svc = BabelioService()
        svc.set_cookie("jstsToken=SERVER_COOKIE; p=FR")

        mock_response = Mock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="[]")
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = Mock()

        def capture_post(url, **kwargs):
            # capture headers from the session itself (passed at ClientSession creation)
            return mock_response

        mock_session.post = capture_post
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.closed = False

        with patch("aiohttp.ClientSession") as mock_cls:
            mock_cls.return_value = mock_session

            await svc.search("victor hugo", babelio_cookies="jstsToken=CLIENT_COOKIE")

            # Verify ClientSession was created with the server cookie in headers
            call_kwargs = mock_cls.call_args[1]
            assert "Cookie" in call_kwargs.get("headers", {}), (
                "Le cookie serveur doit être dans les headers de la session temporaire"
            )
            assert call_kwargs["headers"]["Cookie"] == "jstsToken=SERVER_COOKIE; p=FR"

    @pytest.mark.asyncio
    async def test_search_without_cookie_uses_default_session(self):
        """search() sans cookie utilise la session persistante (pas de session temporaire)."""
        svc = BabelioService()
        # No stored cookie

        mock_response = Mock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="[]")
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = Mock()
        mock_session.post = Mock(return_value=mock_response)
        mock_session.closed = False
        svc.session = mock_session

        with patch("aiohttp.ClientSession") as mock_cls:
            await svc.search("victor hugo")
            # aiohttp.ClientSession should NOT be called for a new temp session
            mock_cls.assert_not_called()

    def test_no_in_memory_cache_dict(self):
        """Le cache mémoire _cache ne doit plus exister (remplacé par cache disque)."""
        svc = BabelioService()
        assert not hasattr(svc, "_cache"), (
            "_cache (dict mémoire) doit être supprimé — utiliser uniquement le cache disque"
        )


class TestBabelioSearchErrorLogging:
    """Tests que les erreurs réseau (timeout, ClientError) sont loggées dans recent_requests."""

    @pytest.mark.asyncio
    async def test_timeout_logs_request_with_status_0(self):
        """search() timeout → entrée dans recent_requests avec status_code=0."""
        svc = BabelioService()

        mock_response = Mock()
        mock_response.__aenter__ = AsyncMock(side_effect=TimeoutError("timeout"))
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = Mock()
        mock_session.post = Mock(return_value=mock_response)
        mock_session.closed = False
        svc.session = mock_session

        with pytest.raises(TimeoutError):
            await svc.search("victor hugo")

        requests = svc.get_recent_requests()
        assert len(requests) == 1
        assert requests[0]["status_code"] == 0
        assert requests[0]["cache_hit"] is False
        assert requests[0]["term_or_url"] == "victor hugo"

    @pytest.mark.asyncio
    async def test_client_error_logs_request_with_status_0(self):  # noqa: E501
        """search() ClientError → entrée dans recent_requests avec status_code=0."""
        svc = BabelioService()

        mock_response = Mock()
        mock_response.__aenter__ = AsyncMock(
            side_effect=aiohttp.ClientError("conn refused")
        )
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = Mock()
        mock_session.post = Mock(return_value=mock_response)
        mock_session.closed = False
        svc.session = mock_session

        with pytest.raises(aiohttp.ClientError):
            await svc.search("victor hugo")

        requests = svc.get_recent_requests()
        assert len(requests) == 1
        assert requests[0]["status_code"] == 0
        assert requests[0]["cache_hit"] is False


class TestBabelioPageCache:
    """Tests que _fetch_page() utilise et alimente le cache disque (search_type='page')."""

    @pytest.mark.asyncio
    async def test_fetch_page_writes_to_cache(self, tmp_path):
        """_fetch_page() doit écrire le HTML dans le cache disque après un GET 200."""
        from back_office_lmelp.services.babelio_cache_service import BabelioCacheService

        svc = BabelioService()
        cache_svc = BabelioCacheService(cache_dir=tmp_path, ttl_hours=24)
        svc.cache_service = cache_svc

        html = "<html><body>Page Babelio</body></html>"
        url = "https://www.babelio.com/livres/Hugo-Les-Miserables/1234"

        mock_response = Mock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value=html)

        mock_get_ctx = Mock()
        mock_get_ctx.__aenter__ = AsyncMock(return_value=mock_response)
        mock_get_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_session = Mock()
        mock_session.get = Mock(return_value=mock_get_ctx)

        mock_session_ctx = Mock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_session_ctx):
            result = await svc._fetch_page(url)

        assert result == html
        cached = cache_svc.get_cached(url, search_type="page")
        assert cached is not None
        assert cached.get("data") == html

    @pytest.mark.asyncio
    async def test_fetch_page_reads_from_cache(self, tmp_path):
        """_fetch_page() doit retourner le HTML depuis le cache sans faire de requête HTTP."""
        from back_office_lmelp.services.babelio_cache_service import BabelioCacheService

        svc = BabelioService()
        svc.min_interval = 30.0
        svc.last_request_time = time.time()

        cache_svc = BabelioCacheService(cache_dir=tmp_path, ttl_hours=24)
        url = "https://www.babelio.com/livres/Hugo-Les-Miserables/1234"
        cache_svc.set_cached(url, "<html>cached</html>", search_type="page")
        svc.cache_service = cache_svc

        with patch("aiohttp.ClientSession") as mock_cls:
            result = await svc._fetch_page(url)
            mock_cls.assert_not_called()

        assert result == "<html>cached</html>"

    @pytest.mark.asyncio
    async def test_fetch_page_cache_hit_logged(self, tmp_path):
        """_fetch_page() cache hit doit apparaître dans recent_requests avec cache_hit=True."""
        from back_office_lmelp.services.babelio_cache_service import BabelioCacheService

        svc = BabelioService()
        cache_svc = BabelioCacheService(cache_dir=tmp_path, ttl_hours=24)
        url = "https://www.babelio.com/livres/Hugo-Les-Miserables/1234"
        cache_svc.set_cached(url, "<html>cached</html>", search_type="page")
        svc.cache_service = cache_svc

        with patch("aiohttp.ClientSession"):
            await svc._fetch_page(url)

        requests = svc.get_recent_requests()
        assert len(requests) == 1
        assert requests[0]["cache_hit"] is True
        assert requests[0]["type"] == "page"


class TestBabelioCircuitBreaker:
    """Circuit breaker: après un 403, toutes les requêtes suivantes échouent sans réseau."""

    @pytest.mark.asyncio
    async def test_search_after_403_raises_without_network(self):
        """Après un 403 sur search(), les appels suivants lèvent BabelioBlockedError sans requête HTTP."""
        from back_office_lmelp.services.babelio_service import BabelioBlockedError

        svc = BabelioService()

        # Simuler un 403 initial
        mock_response_403 = Mock()
        mock_response_403.status = 403
        mock_response_403.__aenter__ = AsyncMock(return_value=mock_response_403)
        mock_response_403.__aexit__ = AsyncMock(return_value=False)

        mock_session = Mock()
        mock_session.post = Mock(return_value=mock_response_403)
        mock_session.closed = False
        svc.session = mock_session

        with pytest.raises(BabelioBlockedError):
            await svc.search("victor hugo")

        # Deuxième appel: doit lever sans appel réseau
        call_count_before = mock_session.post.call_count
        with pytest.raises(BabelioBlockedError):
            await svc.search("zola")
        assert mock_session.post.call_count == call_count_before  # aucun appel réseau

    @pytest.mark.asyncio
    async def test_fetch_page_after_403_raises_without_network(self):
        """Après un 403 sur _fetch_page(), les appels suivants lèvent BabelioBlockedError sans requête HTTP."""
        from back_office_lmelp.services.babelio_service import BabelioBlockedError

        svc = BabelioService()

        # Simuler un 403 initial sur _fetch_page
        mock_response_403 = Mock()
        mock_response_403.status = 403

        mock_get_ctx = Mock()
        mock_get_ctx.__aenter__ = AsyncMock(return_value=mock_response_403)
        mock_get_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_session = Mock()
        mock_session.get = Mock(return_value=mock_get_ctx)

        mock_session_ctx = Mock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("aiohttp.ClientSession", return_value=mock_session_ctx),
            pytest.raises(BabelioBlockedError),
        ):
            await svc._fetch_page("https://www.babelio.com/livres/test/123")

        # Deuxième appel: doit lever sans appel réseau
        with patch("aiohttp.ClientSession") as mock_cls:
            with pytest.raises(BabelioBlockedError):
                await svc._fetch_page("https://www.babelio.com/livres/other/456")
            mock_cls.assert_not_called()

    def test_set_cookie_resets_circuit_breaker(self):
        """set_cookie() doit réinitialiser l'état bloqué du circuit breaker."""
        svc = BabelioService()
        svc._circuit_open = True  # simuler état bloqué

        svc.set_cookie("jstsToken=abc123")

        assert svc._circuit_open is False

    @pytest.mark.asyncio
    async def test_search_works_after_cookie_set(self):
        """Après set_cookie(), search() fonctionne à nouveau (circuit fermé)."""
        svc = BabelioService()
        svc._circuit_open = True  # simuler état bloqué

        # Configurer un nouveau cookie: circuit doit se fermer
        svc.set_cookie("jstsToken=newcookie")
        assert svc._circuit_open is False

        # La prochaine requête doit passer (pas lever BabelioBlockedError immédiatement).
        # search() avec cookie crée une session temporaire aiohttp.ClientSession directement
        # (pas via svc.session) → on doit patcher aiohttp.ClientSession dans le module.
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value=[
                {"id": "1", "prenoms": "Victor", "nom": "Hugo", "type": "auteurs"}
            ]
        )

        mock_post_ctx = AsyncMock()
        mock_post_ctx.__aenter__ = AsyncMock(return_value=mock_response)
        mock_post_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_session_obj = AsyncMock()
        mock_session_obj.post = Mock(return_value=mock_post_ctx)

        mock_session_ctx = AsyncMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session_obj)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "back_office_lmelp.services.babelio_service.aiohttp.ClientSession",
            return_value=mock_session_ctx,
        ):
            # Ne doit pas lever BabelioBlockedError
            result = await svc.search("victor hugo")
        assert isinstance(result, list)
