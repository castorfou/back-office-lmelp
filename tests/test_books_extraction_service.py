"""Tests du service d'extraction des livres/auteurs/éditeurs d'un résumé."""

from unittest.mock import patch

import pytest

from back_office_lmelp.services.books_extraction_service import BooksExtractionService


@pytest.fixture
def books_service():
    """Service d'extraction pour les tests."""
    return BooksExtractionService()


@pytest.fixture
def books_service_factory():
    """Crée le service après la mise en place de l'environnement du test."""
    return BooksExtractionService


@pytest.fixture
def mock_avis_critique():
    """Mock d'un avis critique avec données bibliographiques."""
    return {
        "_id": "test_id",
        "episode_oid": "6865f995a1418e3d7c63d076",  # pragma: allowlist secret
        "episode_title": "Test Episode",
        "episode_date": "01 jan. 2025",
        "summary": """## 1. LIVRES DISCUTÉS AU PROGRAMME

| Auteur | Titre | Éditeur | Avis détaillés des critiques |
|--------|-------|---------|------------------------------|
| Test Auteur | Test Livre | Test Éditeur | **Critique**: "Très bon livre" - 8 |
| Autre Auteur | Autre Livre | Autre Éditeur | **Autre Critique**: "Passable" - 6 |

## 2. COUPS DE CŒUR DES CRITIQUES

| Auteur | Titre | Éditeur | Critique | Note | Commentaire |
|--------|-------|---------|----------|------|-------------|
""",
    }


@pytest.fixture
def mock_avis_critique_with_two_tables():
    """Mock d'un avis critique avec les 2 tableaux complets."""
    return {
        "_id": "test_id",
        "episode_oid": "6865f995a1418e3d7c63d076",  # pragma: allowlist secret
        "episode_title": "Test Episode avec 2 tableaux",
        "episode_date": "24 août 2025",
        "summary": """## 1. LIVRES DISCUTÉS AU PROGRAMME

| Auteur | Titre | Éditeur | Avis détaillés des critiques | Note moyenne | Nb critiques | Coup de cœur |
|--------|-------|---------|------------------------------|--------------|-------------|-------------|
| Antoine Vauters | Haute folie | Gallimard | **Hubert Artus**: "Sensationnel" 9 | 8.0 | 4 | Hubert Artus |
| Justine Lévy | Une drôle de peine | Stock | **Raphaël Léris**: "Bouleversant" 8 | 7.8 | 4 | |

## 2. COUPS DE CŒUR DES CRITIQUES

| Auteur | Titre | Éditeur | Critique | Note | Commentaire |
|--------|-------|---------|----------|------|-------------|
| Thibaut Delman | L'Entroubli | Tripode | Patricia Martin | 9.0 | "Saisissant" |
| Paul Gassnier | La collision | Gallimard | Arnaud Vivian | 9.0 | "Magnifique" |
| Camille Bordas | Des inconnus à qui parler | De Noël | Raphaël Léris | 9.0 | "Intelligent" |
""",
    }


@pytest.fixture
def mock_avis_critique_editeur_manquant():
    """Mock d'un avis critique avec éditeurs manquants."""
    return {
        "_id": "test_id",
        "episode_oid": "6865f995a1418e3d7c63d076",  # pragma: allowlist secret
        "episode_title": "Test Episode éditeurs manquants",
        "episode_date": "01 jan. 2025",
        "summary": """## 1. LIVRES DISCUTÉS AU PROGRAMME

| Auteur | Titre | Éditeur | Avis détaillés des critiques |
|--------|-------|---------|------------------------------|
| Auteur Sans Editeur | Livre Sans Editeur | | **Critique**: "Intéressant" - 7 |
| Auteur Avec Editeur | Livre Avec Editeur | Mon Éditeur | **Autre**: "Bien" - 8 |

## 2. COUPS DE CŒUR DES CRITIQUES

| Auteur | Titre | Éditeur | Critique | Note | Commentaire |
|--------|-------|---------|----------|------|-------------|
| Auteur Coup Coeur | Livre Coup Coeur | | Patricia Martin | 9.0 | "Excellent" |
""",
    }


class TestBooksExtractionService:
    """Tests du service d'extraction de livres."""

    def test_init(self, books_service):
        """Test l'initialisation du service."""
        assert books_service is not None
        assert hasattr(books_service, "extract_books_from_reviews")

    @pytest.mark.asyncio
    async def test_extraction_never_creates_azure_client(
        self, books_service_factory, mock_avis_critique, monkeypatch
    ):
        """L'extraction des livres n'appelle jamais un LLM (Issue #385).

        Même avec des variables Azure définies, aucun client n'est créé : les
        livres viennent des tableaux markdown du résumé.
        """
        monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com/")
        monkeypatch.setenv("AZURE_OPENAI_API_KEY", "fake-key")
        monkeypatch.setenv("AZURE_ENDPOINT", "https://example.openai.azure.com/")
        monkeypatch.setenv("AZURE_API_KEY", "fake-key")

        with patch("openai.AzureOpenAI") as mock_azure:
            service = books_service_factory()
            result = await service.extract_books_from_reviews([mock_avis_critique])

        mock_azure.assert_not_called()
        assert [(b["auteur"], b["titre"]) for b in result] == [
            ("Test Auteur", "Test Livre"),
            ("Autre Auteur", "Autre Livre"),
        ]

    @pytest.mark.asyncio
    async def test_extract_books_from_reviews_basic(
        self, books_service, mock_avis_critique
    ):
        """Les livres du tableau « au programme » sont extraits du résumé."""
        result = await books_service.extract_books_from_reviews([mock_avis_critique])

        assert len(result) == 2
        book = result[0]
        assert (
            book["episode_oid"]
            == "6865f995a1418e3d7c63d076"  # pragma: allowlist secret
        )
        assert book["episode_title"] == "Test Episode"
        assert book["episode_date"] == "01 jan. 2025"
        assert book["auteur"] == "Test Auteur"
        assert book["titre"] == "Test Livre"
        assert book["editeur"] == "Test Éditeur"
        assert book["programme"] is True
        assert result[1]["auteur"] == "Autre Auteur"

    @pytest.mark.asyncio
    async def test_extract_books_from_reviews_empty_input(self, books_service):
        """Test l'extraction avec une liste vide d'avis critiques."""
        result = await books_service.extract_books_from_reviews([])
        assert result == []

    def test_format_books_for_display(self, books_service):
        """Test le formatage des livres pour l'affichage."""
        books_data = [
            {
                "episode_oid": "6865f995a1418e3d7c63d076",  # pragma: allowlist secret
                "episode_title": "Test Episode",
                "episode_date": "01 jan. 2025",
                "auteur": "Test Auteur",
                "titre": "Test Livre",
                "editeur": "Test Éditeur",
                "note_moyenne": "8.0",  # String dans les données brutes
                "nb_critiques": "2",  # String dans les données brutes
                "coups_de_coeur": ["Critique1", "Critique2"],
            }
        ]

        result = books_service.format_books_for_display(books_data)

        assert len(result) == 1
        book = result[0]
        assert (
            book["episode_oid"]
            == "6865f995a1418e3d7c63d076"  # pragma: allowlist secret
        )
        assert book["episode_title"] == "Test Episode"
        assert book["episode_date"] == "01 jan. 2025"
        assert book["auteur"] == "Test Auteur"
        assert book["titre"] == "Test Livre"
        assert book["editeur"] == "Test Éditeur"
        assert book["note_moyenne"] == 8.0  # Converti en float
        assert book["nb_critiques"] == 2  # Converti en int
        assert book["coups_de_coeur"] == ["Critique1", "Critique2"]

    def test_format_books_for_display_empty(self, books_service):
        """Test le formatage avec une liste vide."""
        result = books_service.format_books_for_display([])
        assert result == []

    @pytest.mark.asyncio
    async def test_extract_books_preserves_episode_metadata(self, books_service):
        """Test que les métadonnées de l'épisode sont préservées dans l'extraction."""
        mock_avis = {
            "_id": "test_id_2",
            "episode_oid": "other_episode_oid",
            "episode_title": "Autre Episode",
            "episode_date": "15 fév. 2025",
            "summary": """## 1. LIVRES DISCUTÉS AU PROGRAMME

| Auteur | Titre | Éditeur |
|--------|-------|---------|
| Auteur X | Livre Y | Editeur Z |

## 2. COUPS DE CŒUR DES CRITIQUES

| Auteur | Titre | Éditeur | Critique | Note | Commentaire |
|--------|-------|---------|----------|------|-------------|
""",
        }

        result = await books_service.extract_books_from_reviews([mock_avis])

        assert len(result) == 1
        book = result[0]
        assert book["episode_oid"] == "other_episode_oid"
        assert book["episode_title"] == "Autre Episode"
        assert book["episode_date"] == "15 fév. 2025"

    def test_extract_from_two_tables_programme_and_coups_de_coeur(
        self, books_service, mock_avis_critique_with_two_tables
    ):
        """Test TDD: extraction des 2 tableaux (programme + coups de cœur)."""
        # Test que la méthode fallback extrait des 2 tableaux
        result = books_service._parse_summary_tables(
            mock_avis_critique_with_two_tables["summary"],
            mock_avis_critique_with_two_tables["episode_oid"],
            mock_avis_critique_with_two_tables["episode_title"],
            mock_avis_critique_with_two_tables["episode_date"],
        )

        # Doit extraire 5 livres au total (2 du programme + 3 des coups de cœur)
        assert len(result) == 5

        # Vérifier les livres du programme
        programme_books = [
            book
            for book in result
            if "Antoine Vauters" in book["auteur"] or "Justine Lévy" in book["auteur"]
        ]
        assert len(programme_books) == 2

        antoine_book = next(
            book for book in programme_books if book["auteur"] == "Antoine Vauters"
        )
        assert antoine_book["titre"] == "Haute folie"
        assert antoine_book["editeur"] == "Gallimard"

        # Vérifier les coups de cœur
        coups_coeur_books = [
            book
            for book in result
            if book["auteur"] in ["Thibaut Delman", "Paul Gassnier", "Camille Bordas"]
        ]
        assert len(coups_coeur_books) == 3

        thibaut_book = next(
            book for book in coups_coeur_books if book["auteur"] == "Thibaut Delman"
        )
        assert thibaut_book["titre"] == "L'Entroubli"
        assert thibaut_book["editeur"] == "Tripode"

    def test_simplified_extraction_only_essential_fields(
        self, books_service, mock_avis_critique_with_two_tables
    ):
        """Test TDD: extraction simplifiée avec seulement auteur/titre/éditeur."""
        result = books_service._parse_summary_tables(
            mock_avis_critique_with_two_tables["summary"],
            mock_avis_critique_with_two_tables["episode_oid"],
            mock_avis_critique_with_two_tables["episode_title"],
            mock_avis_critique_with_two_tables["episode_date"],
        )

        # Tous les livres doivent avoir les 3 champs essentiels
        for book in result:
            assert "auteur" in book
            assert "titre" in book
            assert "editeur" in book

            # Vérifier que les champs essentiels ne sont pas vides
            assert book["auteur"].strip() != ""
            assert book["titre"].strip() != ""
            # Éditeur peut être vide (cas normal)

            # Les métadonnées d'épisode doivent être présentes
            assert (
                book["episode_oid"]
                == "6865f995a1418e3d7c63d076"  # pragma: allowlist secret
            )
            assert book["episode_title"] == "Test Episode avec 2 tableaux"
            assert book["episode_date"] == "24 août 2025"

    def test_handles_missing_editeur_gracefully(
        self, books_service, mock_avis_critique_editeur_manquant
    ):
        """Test TDD: gestion gracieuse des éditeurs manquants."""
        result = books_service._parse_summary_tables(
            mock_avis_critique_editeur_manquant["summary"],
            mock_avis_critique_editeur_manquant["episode_oid"],
            mock_avis_critique_editeur_manquant["episode_title"],
            mock_avis_critique_editeur_manquant["episode_date"],
        )

        # Doit extraire 3 livres (2 du programme + 1 coup de cœur)
        assert len(result) == 3

        # Vérifier le livre sans éditeur
        livre_sans_editeur = next(
            book for book in result if book["titre"] == "Livre Sans Editeur"
        )
        assert livre_sans_editeur["auteur"] == "Auteur Sans Editeur"
        assert livre_sans_editeur["editeur"] == ""  # Éditeur vide

        # Vérifier le livre avec éditeur
        livre_avec_editeur = next(
            book for book in result if book["titre"] == "Livre Avec Editeur"
        )
        assert livre_avec_editeur["auteur"] == "Auteur Avec Editeur"
        assert livre_avec_editeur["editeur"] == "Mon Éditeur"

        # Vérifier le coup de cœur sans éditeur
        coup_coeur = next(
            book for book in result if book["titre"] == "Livre Coup Coeur"
        )
        assert coup_coeur["auteur"] == "Auteur Coup Coeur"
        assert coup_coeur["editeur"] == ""  # Éditeur vide

    def test_simplified_format_for_display_only_essential_fields(self, books_service):
        """Test TDD: format d'affichage simplifié avec seulement les champs essentiels."""
        books_data = [
            {
                "episode_oid": "6865f995a1418e3d7c63d076",  # pragma: allowlist secret
                "episode_title": "Test Episode",
                "episode_date": "01 jan. 2025",
                "auteur": "Test Auteur",
                "titre": "Test Livre",
                "editeur": "Test Éditeur",
                # Les champs suivants ne doivent PAS apparaître dans le format simplifié
                "note_moyenne": 8.0,
                "nb_critiques": 2,
                "coups_de_coeur": ["Critique1"],
            }
        ]

        # Cette méthode doit être modifiée pour ne retourner que les champs essentiels
        result = books_service.format_books_for_simplified_display(books_data)

        assert len(result) == 1
        book = result[0]

        # Champs essentiels présents
        assert book["auteur"] == "Test Auteur"
        assert book["titre"] == "Test Livre"
        assert book["editeur"] == "Test Éditeur"

        # Métadonnées d'épisode présentes
        assert (
            book["episode_oid"]
            == "6865f995a1418e3d7c63d076"  # pragma: allowlist secret
        )
        assert book["episode_title"] == "Test Episode"
        assert book["episode_date"] == "01 jan. 2025"

        # Champs superflus ABSENTS
        assert "note_moyenne" not in book
        assert "nb_critiques" not in book
        assert "coups_de_coeur" not in book

    def test_simplified_format_includes_book_and_author_ids(self, books_service):
        """Test TDD (Issue #96): book_id et author_id doivent être retournés pour les liens clickables."""
        from bson import ObjectId

        books_data = [
            {
                "episode_oid": "6865f995a1418e3d7c63d076",  # pragma: allowlist secret
                "auteur": "Test Auteur",
                "titre": "Test Livre",
                "editeur": "Test Éditeur",
                "programme": True,
                "status": "mongo",
                # Issue #96: Ces champs doivent être présents dans la sortie
                "book_id": ObjectId(
                    "68e2c3ba1391489c77ccdee2"  # pragma: allowlist secret
                ),
                "author_id": ObjectId(
                    "68e2c3ba1391489c77ccdee1"  # pragma: allowlist secret
                ),
            }
        ]

        result = books_service.format_books_for_simplified_display(books_data)

        assert len(result) == 1
        book = result[0]

        # Issue #96: book_id et author_id doivent être présents (convertis en string)
        assert "book_id" in book
        assert "author_id" in book
        assert book["book_id"] == "68e2c3ba1391489c77ccdee2"  # pragma: allowlist secret
        assert (
            book["author_id"] == "68e2c3ba1391489c77ccdee1"
        )  # pragma: allowlist secret

    def test_validate_markdown_format_detects_invalid_headers(self, books_service):
        """Test TDD (Issue #161): détection de format markdown invalide."""
        # Markdown avec format invalide (ancien format de l'épisode 11/04/2021)
        invalid_summary = """## 1. LIVRES DU PROGRAMME PRINCIPAL

| Auteur | Titre | Éditeur | Avis détaillés des critiques |
|--------|-------|---------|------------------------------|
| Jonathan Coe | Billy Wilder et moi | Gallimard | **Frédéric Becbedé**: Note 10 |

## 2. COUPS DE CŒUR PERSONNELS

| Auteur | Titre | Éditeur | Critique |
|--------|-------|---------|----------|
| Pierre Nora | Jeunesse | Gallimard | Olivia de Lamberterie |
"""

        validation = books_service._validate_markdown_format(invalid_summary)

        assert validation["valid"] is False
        assert len(validation["missing_sections"]) == 2
        assert "## 1. LIVRES DISCUTÉS AU PROGRAMME" in validation["missing_sections"][0]
        assert "## 2. COUPS DE CŒUR DES CRITIQUES" in validation["missing_sections"][1]
        assert "/avis_critiques" in validation["help_url"]

    def test_validate_markdown_format_accepts_valid_headers(self, books_service):
        """Test TDD (Issue #161): validation de format markdown correct."""
        # Markdown avec format valide (format attendu)
        valid_summary = """## 1. LIVRES DISCUTÉS AU PROGRAMME

| Auteur | Titre | Éditeur | Avis détaillés des critiques |
|--------|-------|---------|------------------------------|
| Jonathan Coe | Billy Wilder et moi | Gallimard | **Frédéric Becbedé**: Note 10 |

## 2. COUPS DE CŒUR DES CRITIQUES

| Auteur | Titre | Éditeur | Critique |
|--------|-------|---------|----------|
| Pierre Nora | Jeunesse | Gallimard | Olivia de Lamberterie |
"""

        validation = books_service._validate_markdown_format(valid_summary)

        assert validation["valid"] is True
        assert len(validation["missing_sections"]) == 0

    @pytest.mark.asyncio
    async def test_extract_books_raises_error_on_invalid_markdown_format(
        self, books_service
    ):
        """Test TDD (Issue #161): extraction lève une erreur sur format invalide."""
        # Avis critique avec format markdown invalide
        invalid_avis = {
            "_id": "test_invalid",
            "episode_oid": "678ccf10a414f229887781b7",  # pragma: allowlist secret
            "episode_title": "Épisode 11/04/2021",
            "episode_date": "11 avril 2021",
            "summary": """## 1. LIVRES DU PROGRAMME PRINCIPAL

| Auteur | Titre | Éditeur |
|--------|-------|---------|
| Jonathan Coe | Billy Wilder et moi | Gallimard |

## 2. COUPS DE CŒUR PERSONNELS

| Auteur | Titre | Éditeur |
|--------|-------|---------|
| Pierre Nora | Jeunesse | Gallimard |
""",
        }

        # L'extraction doit lever une ValueError avec un message explicite
        with pytest.raises(
            ValueError,
            match=r"Format markdown invalide.*Régénérez le résumé.*avis_critiques",
        ):
            await books_service.extract_books_from_reviews([invalid_avis])
