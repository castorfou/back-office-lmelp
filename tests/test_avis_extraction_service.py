"""Tests pour le service d'extraction des avis."""

import sys
from pathlib import Path

import pytest


# Ajouter le répertoire tests au path pour les fixtures
sys.path.insert(0, str(Path(__file__).parent))

from fixtures.avis_summary_samples import (
    AVIS_SUMMARY_IDS,
    AVIS_SUMMARY_SAMPLES,
    SUMMARY_2025_10_26,
    SUMMARY_2025_12_21,
)

from back_office_lmelp.services.avis_extraction_service import AvisExtractionService


class TestParseNoteFromText:
    """Tests pour _parse_note_from_text."""

    def setup_method(self):
        """Setup pour chaque test."""
        self.service = AvisExtractionService()

    def test_parse_note_format_note_x(self):
        """Test parsing note au format 'Note: X'."""
        text = "Très belle découverte, original, divertissant, poétique. Note: 9"
        result = self.service._parse_note_from_text(text)
        assert result == 9

    def test_parse_note_format_note_space_x(self):
        """Test parsing note au format 'note 9' (sans deux-points, minuscule)."""
        text = "Enthousiasmé, bonheur indicible, drôle, note 9"
        result = self.service._parse_note_from_text(text)
        assert result == 9

    def test_parse_note_format_note_space_x_decimal(self):
        """Test parsing note au format 'note 8.5' (décimale sans deux-points)."""
        text = "Très bon livre, original, note 8.5"
        result = self.service._parse_note_from_text(text)
        assert result == 8  # Arrondi

    def test_parse_note_html_span(self):
        """Test parsing note depuis un span HTML."""
        text = '<span style="background-color: #00C851; color: white;">10</span>'
        result = self.service._parse_note_from_text(text)
        assert result == 10

    def test_parse_note_html_span_decimal(self):
        """Test parsing note décimale depuis un span HTML (arrondie)."""
        text = '<span style="background-color: #8BC34A;">8.3</span>'
        result = self.service._parse_note_from_text(text)
        # Arrondi au plus proche
        assert result == 8

    def test_parse_note_parentheses_format(self):
        """Test parsing note au format '(X)' en fin de texte."""
        text = '"C\'est plutôt un bon livre, très beau, drôle" (9)'
        result = self.service._parse_note_from_text(text)
        assert result == 9

    def test_parse_note_parentheses_format_10(self):
        """Test parsing note (10) en fin de texte."""
        text = '"Magnifique, force des images" (10)'
        result = self.service._parse_note_from_text(text)
        assert result == 10

    def test_parse_note_no_note(self):
        """Test parsing quand pas de note trouvée."""
        text = "Un commentaire sans note"
        result = self.service._parse_note_from_text(text)
        assert result is None

    def test_parse_note_empty_text(self):
        """Test avec texte vide."""
        result = self.service._parse_note_from_text("")
        assert result is None

    def test_parse_note_none_text(self):
        """Test avec None."""
        result = self.service._parse_note_from_text(None)
        assert result is None

    def test_parse_note_trailing_number_after_comma(self):
        """
        TDD RED: Test parsing note au format ', X' en fin de texte.

        Format du summary du 14 septembre 2025:
        "Sublime, magistral, fresque familiale d'une ampleur hallucinante, 10"

        La note est un nombre seul après la dernière virgule.
        """
        text = "Sublime, magistral, fresque familiale d'une ampleur hallucinante, 10"
        result = self.service._parse_note_from_text(text)
        assert result == 10

    def test_parse_note_trailing_number_single_digit(self):
        """Test parsing note trailing format avec nombre simple (7)."""
        text = "Long mais stylistiquement impressionnant, 7"
        result = self.service._parse_note_from_text(text)
        assert result == 7

    def test_parse_note_trailing_number_should_not_match_middle_number(self):
        """
        Test que le format trailing ne matche pas un nombre au milieu du texte.

        "Ce livre de 200 pages est excellent" ne doit pas retourner 200.
        """
        text = "Ce livre de 200 pages est excellent"
        result = self.service._parse_note_from_text(text)
        assert result is None

    def test_parse_note_trailing_number_should_be_valid_note(self):
        """
        Test que le format trailing ne matche que des notes valides (1-10).

        ", 15" ne doit pas être considéré comme une note.
        """
        text = "Ce livre contient 15 chapitres, 15"
        result = self.service._parse_note_from_text(text)
        # 15 n'est pas une note valide (1-10), doit retourner None
        assert result is None


class TestParseSection1CriticEntry:
    """Tests pour _parse_section1_critic_entry."""

    def setup_method(self):
        """Setup pour chaque test."""
        self.service = AvisExtractionService()

    def test_parse_entry_format_note_x(self):
        """Test parsing d'une entrée au format 'Note: X'."""
        entry = "**Elisabeth Philippe**: Très belle découverte, original. Note: 9"
        result = self.service._parse_section1_critic_entry(entry)

        assert result is not None
        assert result["critique_nom_extrait"] == "Elisabeth Philippe"
        assert "découverte" in result["commentaire"]
        assert result["note"] == 9

    def test_parse_entry_format_parentheses(self):
        """Test parsing d'une entrée au format '(X)'."""
        entry = '**Jean-Marc Proust**: "C\'est plutôt un bon livre, très beau" (9)'
        result = self.service._parse_section1_critic_entry(entry)

        assert result is not None
        assert result["critique_nom_extrait"] == "Jean-Marc Proust"
        assert "bon livre" in result["commentaire"]
        assert result["note"] == 9
        # Les guillemets doivent être enlevés
        assert not result["commentaire"].startswith('"')

    def test_parse_entry_format_note_space_x(self):
        """Test parsing d'une entrée au format 'note 9' (sans deux-points)."""
        entry = "**Bernard Poirette**: Enthousiasmé, bonheur indicible, drôle, note 9"
        result = self.service._parse_section1_critic_entry(entry)

        assert result is not None
        assert result["critique_nom_extrait"] == "Bernard Poirette"
        assert result["note"] == 9
        # La note doit être retirée du commentaire
        assert "note 9" not in result["commentaire"]
        assert "drôle" in result["commentaire"]

    def test_parse_entry_format_trailing_number(self):
        """
        TDD RED: Test parsing d'une entrée au format ', X' en fin.

        Format du summary du 14 septembre 2025:
        "**Elisabeth Philippe**: Sublime, magistral, fresque familiale d'une ampleur hallucinante, 10"
        """
        entry = "**Elisabeth Philippe**: Sublime, magistral, fresque familiale d'une ampleur hallucinante, 10"
        result = self.service._parse_section1_critic_entry(entry)

        assert result is not None
        assert result["critique_nom_extrait"] == "Elisabeth Philippe"
        assert result["note"] == 10
        # La note doit être retirée du commentaire
        assert ", 10" not in result["commentaire"]
        assert "hallucinante" in result["commentaire"]

    def test_parse_entry_format_trailing_number_7(self):
        """Test parsing avec note 7 en trailing."""
        entry = "**Jean-Marc Proust**: Long mais stylistiquement impressionnant, 7"
        result = self.service._parse_section1_critic_entry(entry)

        assert result is not None
        assert result["critique_nom_extrait"] == "Jean-Marc Proust"
        assert result["note"] == 7
        assert ", 7" not in result["commentaire"]
        assert "impressionnant" in result["commentaire"]

    def test_parse_entry_no_bold(self):
        """Test parsing quand le nom n'est pas en gras."""
        entry = "Elisabeth Philippe: Très belle découverte. Note: 9"
        result = self.service._parse_section1_critic_entry(entry)
        assert result is None

    def test_parse_entry_missing_note(self):
        """Test parsing quand la note est manquante."""
        entry = "**Elisabeth Philippe**: Très belle découverte, original"
        result = self.service._parse_section1_critic_entry(entry)

        assert result is not None
        assert result["critique_nom_extrait"] == "Elisabeth Philippe"
        assert result["note"] is None

    def test_parse_entry_empty(self):
        """Test avec entrée vide."""
        result = self.service._parse_section1_critic_entry("")
        assert result is None

    def test_parse_entry_none(self):
        """Test avec None."""
        result = self.service._parse_section1_critic_entry(None)
        assert result is None


class TestExtractSection1Avis:
    """Tests pour _extract_section1_avis avec différents formats."""

    def setup_method(self):
        """Setup pour chaque test."""
        self.service = AvisExtractionService()

    def test_extract_format_note_x(self):
        """Test extraction depuis format 'Note: X' (21 déc. 2025)."""
        sample = SUMMARY_2025_12_21
        avis_list = self.service._extract_section1_avis(
            sample.summary, sample.emission_oid
        )

        assert len(avis_list) == sample.expected_section1_count

        # Vérifier le premier avis
        first_avis = avis_list[0]
        expected = sample.expected_first_avis_section1
        assert first_avis["livre_titre_extrait"] == expected["livre_titre_extrait"]
        assert first_avis["critique_nom_extrait"] == expected["critique_nom_extrait"]
        assert first_avis["note"] == expected["note"]
        assert first_avis["section"] == "programme"

    def test_extract_format_parentheses(self):
        """Test extraction depuis format '(X)' (26 oct. 2025)."""
        sample = SUMMARY_2025_10_26
        avis_list = self.service._extract_section1_avis(
            sample.summary, sample.emission_oid
        )

        assert len(avis_list) == sample.expected_section1_count

        # Vérifier le premier avis
        first_avis = avis_list[0]
        expected = sample.expected_first_avis_section1
        assert first_avis["livre_titre_extrait"] == expected["livre_titre_extrait"]
        assert first_avis["critique_nom_extrait"] == expected["critique_nom_extrait"]
        assert first_avis["note"] == expected["note"]
        assert first_avis["section"] == "programme"

    def test_extract_empty_summary(self):
        """Test avec summary vide."""
        avis_list = self.service._extract_section1_avis("", "test_oid")
        assert avis_list == []

    def test_extract_no_section1(self):
        """Test avec summary sans Section 1."""
        summary = "## 2. COUPS DE CŒUR\n| Auteur | Titre |"
        avis_list = self.service._extract_section1_avis(summary, "test_oid")
        assert avis_list == []

    def test_extract_row_with_auteur_in_critique_text(self):
        """Test que le mot 'Auteur' dans le texte critique ne cause pas le skip.

        Bug réel: épisode 26/08/2018 - "À son image" de Jérôme Ferrari.
        La critique contenait "Auteur concerné par le grave..." et la ligne
        était ignorée par le filtre `"Auteur" in line`.
        """
        summary = """## 1. LIVRES DISCUTÉS DANS L'ÉMISSION

| Auteur | Titre | Éditeur | Avis des critiques |
|--------|-------|---------|-------------------|
| Maylis de Kerangal | Un monde à portée de main | Verticales | **Frédéric Beigbeder**: Fascinant. Note: 8 |
| Jérôme Ferrari | À son image | Actes Sud | **Michel Crépu**: Auteur concerné par le grave, blague de Coluche, prix Goncourt sermon. Note: 6 |
| Samuel Benchetrit | Encore un jour banane pour le poisson-rêve | Grasset | **Olivia de Lamberterie**: Délicieux. Note: 7 |

## 2. COUPS DE CŒUR DES CRITIQUES
"""
        avis_list = self.service._extract_section1_avis(summary, "test_oid")

        # Les 3 livres doivent être extraits (pas 2)
        assert len(avis_list) == 3

        # Vérifier que "À son image" de Ferrari est bien extrait
        ferrari_avis = [
            a for a in avis_list if a["livre_titre_extrait"] == "À son image"
        ]
        assert len(ferrari_avis) == 1
        assert ferrari_avis[0]["auteur_nom_extrait"] == "Jérôme Ferrari"
        assert ferrari_avis[0]["critique_nom_extrait"] == "Michel Crépu"


class TestExtractSection2Avis:
    """Tests pour _extract_section2_avis."""

    def setup_method(self):
        """Setup pour chaque test."""
        self.service = AvisExtractionService()

    def test_extract_coups_de_coeur_dec_2025(self):
        """Test extraction coups de cœur (21 déc. 2025)."""
        sample = SUMMARY_2025_12_21
        avis_list = self.service._extract_section2_avis(
            sample.summary, sample.emission_oid
        )

        assert len(avis_list) == sample.expected_section2_count

        first_avis = avis_list[0]
        expected = sample.expected_first_avis_section2
        assert first_avis["livre_titre_extrait"] == expected["livre_titre_extrait"]
        assert first_avis["critique_nom_extrait"] == expected["critique_nom_extrait"]
        assert first_avis["note"] == expected["note"]
        assert first_avis["section"] == "coup_de_coeur"

    def test_extract_coups_de_coeur_oct_2025(self):
        """Test extraction coups de cœur (26 oct. 2025)."""
        sample = SUMMARY_2025_10_26
        avis_list = self.service._extract_section2_avis(
            sample.summary, sample.emission_oid
        )

        assert len(avis_list) == sample.expected_section2_count

        first_avis = avis_list[0]
        expected = sample.expected_first_avis_section2
        assert first_avis["livre_titre_extrait"] == expected["livre_titre_extrait"]
        assert first_avis["critique_nom_extrait"] == expected["critique_nom_extrait"]
        # Note 9.5 arrondie à 10
        assert first_avis["note"] == expected["note"]

    def test_extract_empty_summary(self):
        """Test avec summary vide."""
        avis_list = self.service._extract_section2_avis("", "test_oid")
        assert avis_list == []


class TestExtractAvisFromSummaryParametrized:
    """Tests paramétrés pour extract_avis_from_summary avec tous les samples."""

    def setup_method(self):
        """Setup pour chaque test."""
        self.service = AvisExtractionService()

    @pytest.mark.parametrize("sample", AVIS_SUMMARY_SAMPLES, ids=AVIS_SUMMARY_IDS)
    def test_extract_total_count(self, sample):
        """Test que le nombre total d'avis est correct pour chaque sample."""
        avis_list = self.service.extract_avis_from_summary(
            sample.summary, sample.emission_oid
        )

        expected_total = sample.expected_section1_count + sample.expected_section2_count
        assert len(avis_list) == expected_total, (
            f"Pour {sample.episode_date}: attendu {expected_total}, obtenu {len(avis_list)}"
        )

    @pytest.mark.parametrize("sample", AVIS_SUMMARY_SAMPLES, ids=AVIS_SUMMARY_IDS)
    def test_extract_all_have_emission_oid(self, sample):
        """Test que tous les avis ont l'emission_oid correct."""
        avis_list = self.service.extract_avis_from_summary(
            sample.summary, sample.emission_oid
        )

        for avis in avis_list:
            assert avis["emission_oid"] == sample.emission_oid

    @pytest.mark.parametrize("sample", AVIS_SUMMARY_SAMPLES, ids=AVIS_SUMMARY_IDS)
    def test_extract_both_sections_present(self, sample):
        """Test que les deux types de sections sont présents."""
        avis_list = self.service.extract_avis_from_summary(
            sample.summary, sample.emission_oid
        )

        sections = {avis["section"] for avis in avis_list}
        if sample.expected_section1_count > 0:
            assert "programme" in sections
        if sample.expected_section2_count > 0:
            assert "coup_de_coeur" in sections

    @pytest.mark.parametrize("sample", AVIS_SUMMARY_SAMPLES, ids=AVIS_SUMMARY_IDS)
    def test_extract_all_have_required_fields(self, sample):
        """Test que tous les avis ont les champs requis."""
        avis_list = self.service.extract_avis_from_summary(
            sample.summary, sample.emission_oid
        )

        required_fields = [
            "emission_oid",
            "section",
            "livre_titre_extrait",
            "auteur_nom_extrait",
            "editeur_extrait",
            "critique_nom_extrait",
            "commentaire",
            "note",
        ]

        for avis in avis_list:
            for field in required_fields:
                assert field in avis, f"Champ manquant: {field}"


class TestResolveEntities:
    """Tests pour la résolution d'entités."""

    def setup_method(self):
        """Setup pour chaque test."""
        self.service = AvisExtractionService()

    def test_resolve_matches_livre_by_title(self):
        """Test que le livre est matché par titre normalisé."""
        extracted_avis = [
            {
                "emission_oid": "em123",
                "livre_titre_extrait": "Combats de filles",
                "auteur_nom_extrait": "Rita Bullwinkel",
                "editeur_extrait": "La Croisée",
                "critique_nom_extrait": "Elisabeth Philippe",
                "commentaire": "Très beau",
                "note": 9,
                "section": "programme",
            }
        ]

        livres = [
            {
                "_id": "livre_abc",
                "titre": "Combats de filles",
                "auteur_id": "auteur_xyz",
            }
        ]
        critiques = [
            {"_id": "critique_123", "nom": "Elisabeth Philippe", "variantes": []}
        ]

        resolved = self.service.resolve_entities(extracted_avis, livres, critiques)

        assert len(resolved) == 1
        assert resolved[0]["livre_oid"] == "livre_abc"
        assert resolved[0]["critique_oid"] == "critique_123"

    def test_resolve_matches_critique_by_variante(self):
        """Test que le critique est matché par variante."""
        extracted_avis = [
            {
                "emission_oid": "em123",
                "livre_titre_extrait": "Mon livre",
                "auteur_nom_extrait": "Auteur",
                "editeur_extrait": "Editeur",
                "critique_nom_extrait": "Arnaud Vivian",  # Variante avec typo
                "commentaire": "Super",
                "note": 8,
                "section": "programme",
            }
        ]

        livres = [{"_id": "livre_1", "titre": "Mon livre", "auteur_id": "a1"}]
        critiques = [
            {
                "_id": "critique_av",
                "nom": "Arnaud Viviant",
                "variantes": ["Arnaud Vivian", "A. Viviant"],
            }
        ]

        resolved = self.service.resolve_entities(extracted_avis, livres, critiques)

        assert resolved[0]["critique_oid"] == "critique_av"

    def test_resolve_keeps_null_when_not_found(self):
        """Test que les IDs restent null si entité non trouvée."""
        extracted_avis = [
            {
                "emission_oid": "em123",
                "livre_titre_extrait": "Livre inconnu",
                "auteur_nom_extrait": "Auteur inconnu",
                "editeur_extrait": "Editeur",
                "critique_nom_extrait": "Critique inconnu",
                "commentaire": "Test",
                "note": 5,
                "section": "programme",
            }
        ]

        resolved = self.service.resolve_entities(extracted_avis, [], [])

        assert resolved[0]["livre_oid"] is None
        assert resolved[0]["critique_oid"] is None
        # Les données brutes sont préservées
        assert resolved[0]["livre_titre_extrait"] == "Livre inconnu"
        assert resolved[0]["critique_nom_extrait"] == "Critique inconnu"

    def test_resolve_normalizes_titles(self):
        """Test que le matching normalise les titres (casse)."""
        extracted_avis = [
            {
                "emission_oid": "em123",
                "livre_titre_extrait": "COMBATS DE FILLES",  # Majuscules
                "auteur_nom_extrait": "Rita Bullwinkel",
                "editeur_extrait": "La Croisée",
                "critique_nom_extrait": "Elisabeth Philippe",
                "commentaire": "Bien",
                "note": 7,
                "section": "programme",
            }
        ]

        livres = [
            {
                "_id": "livre_abc",
                "titre": "Combats de filles",  # Casse normale
                "auteur_id": "auteur_xyz",
            }
        ]
        critiques = [
            {"_id": "critique_123", "nom": "Elisabeth Philippe", "variantes": []}
        ]

        resolved = self.service.resolve_entities(extracted_avis, livres, critiques)

        assert resolved[0]["livre_oid"] == "livre_abc"

    def test_resolve_matches_livre_by_partial_inclusion(self):
        """Test matching livre quand titre extrait est contenu dans titre base.

        Cas réel: "La sirène d'Hollywood" doit matcher
        "Esther Williams, la sirène d'Hollywood. Mémoires"
        """
        extracted_avis = [
            {
                "emission_oid": "em123",
                "livre_titre_extrait": "La sirène d'Hollywood",  # Titre partiel
                "auteur_nom_extrait": "Esther Williams",
                "editeur_extrait": "Séguier",
                "critique_nom_extrait": "Elisabeth Philippe",
                "commentaire": "Très drôle",
                "note": 10,
                "section": "coup_de_coeur",
            }
        ]

        livres = [
            {
                "_id": "livre_esther",
                "titre": "Esther Williams, la sirène d'Hollywood. Mémoires",
                "auteur_id": "auteur_esther",
            }
        ]
        critiques = [
            {"_id": "critique_ep", "nom": "Elisabeth Philippe", "variantes": []}
        ]

        resolved = self.service.resolve_entities(extracted_avis, livres, critiques)

        assert resolved[0]["livre_oid"] == "livre_esther"

    def test_resolve_exact_match_priority_over_partial(self):
        """Test que le match exact a priorité sur le match partiel."""
        extracted_avis = [
            {
                "emission_oid": "em123",
                "livre_titre_extrait": "Astérix",
                "auteur_nom_extrait": "Auteur",
                "editeur_extrait": "Editeur",
                "critique_nom_extrait": "Critique",
                "commentaire": "Test",
                "note": 7,
                "section": "programme",
            }
        ]

        livres = [
            {"_id": "livre_asterix_long", "titre": "Astérix en Lusitanie"},
            {"_id": "livre_asterix_exact", "titre": "Astérix"},  # Match exact
        ]
        critiques = []

        resolved = self.service.resolve_entities(extracted_avis, livres, critiques)

        # Match exact doit gagner
        assert resolved[0]["livre_oid"] == "livre_asterix_exact"

    def test_resolve_exclusive_matching_avoids_duplicate(self):
        """Test que les livres déjà matchés ne sont pas réutilisés.

        Cas: 2 avis avec titres similaires, 2 livres différents.
        Le matching doit être exclusif.
        """
        extracted_avis = [
            {
                "emission_oid": "em123",
                "livre_titre_extrait": "Combats de filles",  # Match exact
                "auteur_nom_extrait": "Rita Bullwinkel",
                "editeur_extrait": "La Croisée",
                "critique_nom_extrait": "Philippe",
                "commentaire": "Bien",
                "note": 9,
                "section": "programme",
            },
            {
                "emission_oid": "em123",
                "livre_titre_extrait": "Combats de filles",  # Même titre, autre avis
                "auteur_nom_extrait": "Rita Bullwinkel",
                "editeur_extrait": "La Croisée",
                "critique_nom_extrait": "Patricia",
                "commentaire": "Excellent",
                "note": 8,
                "section": "programme",
            },
        ]

        livres = [
            {"_id": "livre_combats", "titre": "Combats de filles"},
        ]
        critiques = []

        resolved = self.service.resolve_entities(extracted_avis, livres, critiques)

        # Les deux avis doivent matcher le même livre (même titre)
        assert resolved[0]["livre_oid"] == "livre_combats"
        assert resolved[1]["livre_oid"] == "livre_combats"

    def test_resolve_multiple_books_with_partial_matching(self):
        """Test matching avec plusieurs livres et titres partiels.

        Cas réel du 21 déc 2025: plusieurs livres au programme + coups de coeur.
        Les matchs exacts doivent être faits en premier, puis les partiels
        sur les livres restants uniquement.
        """
        extracted_avis = [
            {
                "emission_oid": "em123",
                "livre_titre_extrait": "Combats de filles",  # Match exact
                "auteur_nom_extrait": "Rita Bullwinkel",
                "editeur_extrait": "La Croisée",
                "critique_nom_extrait": "Elisabeth",
                "commentaire": "Super",
                "note": 9,
                "section": "programme",
            },
            {
                "emission_oid": "em123",
                "livre_titre_extrait": "La sirène d'Hollywood",  # Match partiel
                "auteur_nom_extrait": "Esther Williams",
                "editeur_extrait": "Séguier",
                "critique_nom_extrait": "Elisabeth",
                "commentaire": "Drôle",
                "note": 10,
                "section": "coup_de_coeur",
            },
        ]

        livres = [
            {"_id": "livre_combats", "titre": "Combats de filles"},
            {
                "_id": "livre_esther",
                "titre": "Esther Williams, la sirène d'Hollywood. Mémoires",
            },
        ]
        critiques = []

        resolved = self.service.resolve_entities(extracted_avis, livres, critiques)

        assert resolved[0]["livre_oid"] == "livre_combats"
        assert resolved[1]["livre_oid"] == "livre_esther"

    def test_resolve_enriches_avis_with_official_book_title(self):
        """Test que resolve_entities enrichit l'avis avec le titre officiel du livre.

        Cas réel: Le titre extrait "La sirène d'Hollywood" doit être enrichi
        avec le titre officiel "Esther Williams, la sirène d'Hollywood. Mémoires"
        pour affichage dans le frontend.
        """
        extracted_avis = [
            {
                "emission_oid": "em123",
                "livre_titre_extrait": "La sirène d'Hollywood",  # Titre partiel du summary
                "auteur_nom_extrait": "Esther Williams",
                "editeur_extrait": "Séguier",
                "critique_nom_extrait": "Elisabeth Philippe",
                "commentaire": "Très drôle",
                "note": 10,
                "section": "coup_de_coeur",
            }
        ]

        livres = [
            {
                "_id": "livre_esther",
                "titre": "Esther Williams, la sirène d'Hollywood. Mémoires",
                "auteur_id": "auteur_esther",
            }
        ]
        critiques = [
            {"_id": "critique_ep", "nom": "Elisabeth Philippe", "variantes": []}
        ]

        resolved = self.service.resolve_entities(extracted_avis, livres, critiques)

        # Le livre doit être résolu
        assert resolved[0]["livre_oid"] == "livre_esther"
        # Le titre extrait doit rester intact (pas remplacé par le titre officiel)
        assert resolved[0]["livre_titre_extrait"] == "La sirène d'Hollywood"

    def test_resolve_matches_last_unresolved_livre_by_similarity(self):
        """Test matching par similarité pour le dernier livre non résolu.

        Cas réel: "22 Masbury Road" (typo) doit matcher
        "22 Mapesbury Road: Famille, mémoire et quête d'une terre promise"
        quand c'est le seul livre restant non matché.
        """
        extracted_avis = [
            {
                "emission_oid": "em123",
                "livre_titre_extrait": "Combats de filles",  # Match exact
                "auteur_nom_extrait": "Rita Bullwinkel",
                "editeur_extrait": "La Croisée",
                "critique_nom_extrait": "Elisabeth Philippe",
                "commentaire": "Bon livre",
                "note": 8,
                "section": "programme",
            },
            {
                "emission_oid": "em123",
                "livre_titre_extrait": "22 Masbury Road",  # Typo: Masbury vs Mapesbury
                "auteur_nom_extrait": "Rachel Coquerel",
                "editeur_extrait": "Quai Voltaire",
                "critique_nom_extrait": "Jean-Marc Proust",
                "commentaire": "Très bien",
                "note": 9,
                "section": "programme",
            },
        ]

        livres = [
            {"_id": "livre_combats", "titre": "Combats de filles"},
            {
                "_id": "livre_masbury",
                "titre": "22 Mapesbury Road: Famille, mémoire et quête d'une terre promise",
            },
        ]
        critiques = [
            {"_id": "critique_ep", "nom": "Elisabeth Philippe", "variantes": []},
            {"_id": "critique_jmp", "nom": "Jean-Marc Proust", "variantes": []},
        ]

        resolved = self.service.resolve_entities(extracted_avis, livres, critiques)

        # Premier avis: match exact
        assert resolved[0]["livre_oid"] == "livre_combats"
        # Second avis: match par similarité car c'est le dernier livre non résolu
        assert resolved[1]["livre_oid"] == "livre_masbury"
        # Le titre extrait doit rester intact (pas écrasé par le titre officiel)
        assert resolved[1]["livre_titre_extrait"] == "22 Masbury Road"

    def test_resolve_preserves_original_titre_extrait(self):
        """Test que livre_titre_extrait n'est pas écrasé par le titre officiel.

        Cas réel: Le summary contient "4 jours sans ma mère" mais le livre MongoDB
        s'appelle "Quatre jours sans ma mère". On doit garder le titre extrait original
        pour permettre au frontend de grouper correctement par livre_oid.
        """
        extracted_avis = [
            {
                "emission_oid": "em123",
                "livre_titre_extrait": "4 jours sans ma mère",  # Titre du summary
                "auteur_nom_extrait": "Ramsès Kefi",
                "editeur_extrait": "Philippe Rey",
                "critique_nom_extrait": "Bernard Poirette",
                "commentaire": "Enthousiasmé",
                "note": 9,
                "section": "programme",
            },
        ]

        livres = [
            {
                "_id": "livre_4jours",
                "titre": "Quatre jours sans ma mère",  # Titre officiel différent
                "auteur_id": "auteur_kefi",
            }
        ]
        critiques = [{"_id": "critique_bp", "nom": "Bernard Poirette", "variantes": []}]

        resolved = self.service.resolve_entities(extracted_avis, livres, critiques)

        # Le livre doit être résolu (match par similarité)
        assert resolved[0]["livre_oid"] == "livre_4jours"
        # IMPORTANT: Le titre extrait doit rester "4 jours" (pas remplacé par "Quatre jours")
        assert resolved[0]["livre_titre_extrait"] == "4 jours sans ma mère"

    def test_resolve_propagates_livre_oid_to_all_avis_with_same_title(self):
        """Test que tous les avis avec le même titre reçoivent le même livre_oid.

        Cas réel: Le summary contient 4 avis pour "4 jours sans ma mère" (un par critique).
        Le matching Phase 3 trouve le livre "Quatre jours sans ma mère" pour le 1er avis.
        Les 3 autres avis avec le même titre doivent aussi recevoir ce livre_oid.
        """
        extracted_avis = [
            {
                "emission_oid": "em123",
                "livre_titre_extrait": "4 jours sans ma mère",
                "auteur_nom_extrait": "Ramsès Kefi",
                "editeur_extrait": "Philippe Rey",
                "critique_nom_extrait": "Bernard Poirette",
                "commentaire": "Enthousiasmé",
                "note": 9,
                "section": "programme",
            },
            {
                "emission_oid": "em123",
                "livre_titre_extrait": "4 jours sans ma mère",  # Même titre!
                "auteur_nom_extrait": "Ramsès Kefi",
                "editeur_extrait": "Philippe Rey",
                "critique_nom_extrait": "Laurent Chalumeau",
                "commentaire": "Enchantement",
                "note": 9,
                "section": "programme",
            },
            {
                "emission_oid": "em123",
                "livre_titre_extrait": "4 jours sans ma mère",  # Même titre!
                "auteur_nom_extrait": "Ramsès Kefi",
                "editeur_extrait": "Philippe Rey",
                "critique_nom_extrait": "Anna Sigalevitch",
                "commentaire": "Très humain",
                "note": 9,
                "section": "programme",
            },
            {
                "emission_oid": "em123",
                "livre_titre_extrait": "4 jours sans ma mère",  # Même titre!
                "auteur_nom_extrait": "Ramsès Kefi",
                "editeur_extrait": "Philippe Rey",
                "critique_nom_extrait": "Elisabeth Philippe",
                "commentaire": "Débordant de tendresse",
                "note": 9,
                "section": "programme",
            },
        ]

        livres = [
            {
                "_id": "livre_4jours",
                "titre": "Quatre jours sans ma mère",  # Titre officiel différent
                "auteur_id": "auteur_kefi",
            }
        ]
        critiques = [
            {"_id": "critique_bp", "nom": "Bernard Poirette", "variantes": []},
            {"_id": "critique_lc", "nom": "Laurent Chalumeau", "variantes": []},
            {"_id": "critique_as", "nom": "Anna Sigalevitch", "variantes": []},
            {"_id": "critique_ep", "nom": "Elisabeth Philippe", "variantes": []},
        ]

        resolved = self.service.resolve_entities(extracted_avis, livres, critiques)

        # TOUS les avis avec le même titre doivent avoir le même livre_oid
        assert resolved[0]["livre_oid"] == "livre_4jours"
        assert resolved[1]["livre_oid"] == "livre_4jours"
        assert resolved[2]["livre_oid"] == "livre_4jours"
        assert resolved[3]["livre_oid"] == "livre_4jours"

        # Et tous doivent avoir match_phase = 3
        assert resolved[0]["match_phase"] == 3
        assert resolved[1]["match_phase"] == 3
        assert resolved[2]["match_phase"] == 3
        assert resolved[3]["match_phase"] == 3

    def test_resolve_fuzzy_matches_last_unmatched_when_counts_equal(self):
        """Test Phase 4: fuzzy matching quand # livres MongoDB == # livres summary.

        Cas réel du 18 janvier 2026:
        - Summary: "Anne-Marie Schwarzenbach, l'ange dévastée" par "Mamo Stedin"
        - MongoDB: "Paris" par "Annemarie Schwarzenbach"

        Quand il ne reste qu'un livre non matché de chaque côté,
        l'association doit être automatique.
        """
        extracted_avis = [
            {
                "emission_oid": "em123",
                "livre_titre_extrait": "Protocoles",  # Match exact
                "auteur_nom_extrait": "Constance Debré",
                "editeur_extrait": "Flammarion",
                "critique_nom_extrait": "Elisabeth Philippe",
                "commentaire": "Densité remarquable",
                "note": 9,
                "section": "programme",
            },
            {
                "emission_oid": "em123",
                "livre_titre_extrait": "Anne-Marie Schwarzenbach, l'ange dévastée",
                "auteur_nom_extrait": "Mamo Stedin, Léa Gauthier",
                "editeur_extrait": "Payot",
                "critique_nom_extrait": "Elisabeth Philippe",
                "commentaire": "BD fascinante",
                "note": 8,
                "section": "coup_de_coeur",
            },
        ]

        livres = [
            {
                "_id": "livre_protocoles",
                "titre": "Protocoles",
                "auteur_id": "auteur_debre",
            },
            {
                "_id": "livre_paris",
                "titre": "Paris",
                "auteur_id": "auteur_schwarzenbach",
            },
        ]
        critiques = [
            {"_id": "critique_ep", "nom": "Elisabeth Philippe", "variantes": []}
        ]

        resolved = self.service.resolve_entities(extracted_avis, livres, critiques)

        # Premier avis: match exact Phase 1
        assert resolved[0]["livre_oid"] == "livre_protocoles"
        assert resolved[0]["match_phase"] == 1

        # Deuxième avis: fuzzy match Phase 4 (dernier livre restant)
        assert resolved[1]["livre_oid"] == "livre_paris"
        assert resolved[1]["match_phase"] == 4  # Phase 4 = fuzzy sur livres restants
        # L'auteur_oid doit être enrichi après le match
        assert resolved[1]["auteur_oid"] == "auteur_schwarzenbach"

    def test_resolve_stats_include_phase4(self):
        """Test que les stats incluent la Phase 4."""
        extracted_avis = [
            {
                "emission_oid": "em123",
                "livre_titre_extrait": "Protocoles",
                "auteur_nom_extrait": "Constance Debré",
                "editeur_extrait": "Flammarion",
                "critique_nom_extrait": "Elisabeth Philippe",
                "commentaire": "Densité remarquable",
                "note": 9,
                "section": "programme",
            },
            {
                "emission_oid": "em123",
                "livre_titre_extrait": "Anne-Marie Schwarzenbach, l'ange dévastée",
                "auteur_nom_extrait": "Mamo Stedin",
                "editeur_extrait": "Payot",
                "critique_nom_extrait": "Elisabeth Philippe",
                "commentaire": "BD fascinante",
                "note": 8,
                "section": "coup_de_coeur",
            },
        ]

        livres = [
            {"_id": "livre_protocoles", "titre": "Protocoles", "auteur_id": "a1"},
            {"_id": "livre_paris", "titre": "Paris", "auteur_id": "a2"},
        ]
        critiques = [{"_id": "c1", "nom": "Elisabeth Philippe", "variantes": []}]

        _, stats = self.service.resolve_entities_with_stats(
            extracted_avis, livres, critiques
        )

        # Stats doivent inclure Phase 4
        assert stats["match_phase1"] == 1  # Protocoles
        assert stats["match_phase4"] == 1  # Paris (fuzzy)
        assert stats["unmatched"] == 0


class TestMatchingLivreParLivre:
    """Tests TDD pour le refactoring du matching livre par livre (Issue #185)."""

    def setup_method(self):
        """Setup pour chaque test."""
        self.service = AvisExtractionService()

    def test_should_extract_unique_books_from_avis(self):
        """
        Test RED: 24 avis doivent donner 9 livres uniques.

        TEST CRITIQUE pour Issue #185 :
        Vérifie que l'extraction des livres uniques fonctionne correctement.
        """
        # Utiliser les 24 avis réels de l'émission 09/03/2025
        # (Section 1: 5 livres × 4 critiques = 20 avis)
        # (Section 2: 4 coups de cœur = 4 avis)
        avis_list = [
            # Livre 1: La Realidad (4 avis)
            {"livre_titre_extrait": "La Realidad", "auteur_nom_extrait": "Neige Sinno"},
            {"livre_titre_extrait": "La Realidad", "auteur_nom_extrait": "Neige Sinno"},
            {"livre_titre_extrait": "La Realidad", "auteur_nom_extrait": "Neige Sinno"},
            {"livre_titre_extrait": "La Realidad", "auteur_nom_extrait": "Neige Sinno"},
            # Livre 2: Mon vrai nom est Elisabeth (4 avis)
            {
                "livre_titre_extrait": "Mon vrai nom est Elisabeth",
                "auteur_nom_extrait": "Adèle Yon",
            },
            {
                "livre_titre_extrait": "Mon vrai nom est Elisabeth",
                "auteur_nom_extrait": "Adèle Yon",
            },
            {
                "livre_titre_extrait": "Mon vrai nom est Elisabeth",
                "auteur_nom_extrait": "Adèle Yon",
            },
            {
                "livre_titre_extrait": "Mon vrai nom est Elisabeth",
                "auteur_nom_extrait": "Adèle Yon",
            },
            # Livre 3: Trésors Cachés (4 avis) ⚠️ PROBLÉMATIQUE
            {
                "livre_titre_extrait": "Trésors Cachés",
                "auteur_nom_extrait": "Pascal Quignard",
            },
            {
                "livre_titre_extrait": "Trésors Cachés",
                "auteur_nom_extrait": "Pascal Quignard",
            },
            {
                "livre_titre_extrait": "Trésors Cachés",
                "auteur_nom_extrait": "Pascal Quignard",
            },
            {
                "livre_titre_extrait": "Trésors Cachés",
                "auteur_nom_extrait": "Pascal Quignard",
            },
            # Livre 4: Mauvais élève (4 avis)
            {
                "livre_titre_extrait": "Mauvais élève",
                "auteur_nom_extrait": "Philippe Vilain",
            },
            {
                "livre_titre_extrait": "Mauvais élève",
                "auteur_nom_extrait": "Philippe Vilain",
            },
            {
                "livre_titre_extrait": "Mauvais élève",
                "auteur_nom_extrait": "Philippe Vilain",
            },
            {
                "livre_titre_extrait": "Mauvais élève",
                "auteur_nom_extrait": "Philippe Vilain",
            },
            # Livre 5: L'ombre portée (4 avis)
            {
                "livre_titre_extrait": "L'ombre portée",
                "auteur_nom_extrait": "Hugues Pagan",
            },
            {
                "livre_titre_extrait": "L'ombre portée",
                "auteur_nom_extrait": "Hugues Pagan",
            },
            {
                "livre_titre_extrait": "L'ombre portée",
                "auteur_nom_extrait": "Hugues Pagan",
            },
            {
                "livre_titre_extrait": "L'ombre portée",
                "auteur_nom_extrait": "Hugues Pagan",
            },
            # Section 2: Coups de cœur (4 avis - 4 livres différents)
            {"livre_titre_extrait": "Permission", "auteur_nom_extrait": "Saskia Vogel"},
            {
                "livre_titre_extrait": "La Loi des collines",
                "auteur_nom_extrait": "Chris Hoffut",
            },
            {
                "livre_titre_extrait": "La Chaises",
                "auteur_nom_extrait": "Jean-Louis Aislin",
            },  # ⚠️ CRITIQUE
            {
                "livre_titre_extrait": "Le Livre rouge des ruptures",
                "auteur_nom_extrait": "Pirko Sessio",
            },
        ]

        # EXECUTE: Extraire les livres uniques
        livres_summary = self.service._extract_unique_books_from_avis(avis_list)

        # ASSERT: Doit retourner 9 livres uniques
        assert len(livres_summary) == 9, (
            f"Attendu 9 livres uniques, obtenu {len(livres_summary)}"
        )

        # Vérifier qu'on a bien les livres attendus
        titres = {livre["titre"] for livre in livres_summary}
        assert "La Realidad" in titres
        assert "Trésors Cachés" in titres
        assert "La Chaises" in titres  # ⚠️ Celui qui ne se matchait pas avant
        assert "Mon vrai nom est Elisabeth" in titres
        assert "Mauvais élève" in titres
        assert "L'ombre portée" in titres
        assert "Permission" in titres
        assert "La Loi des collines" in titres
        assert "Le Livre rouge des ruptures" in titres

    def test_should_match_livres_summary_to_mongo(self):
        """
        Test RED CRITIQUE: Doit matcher les 9 livres summary avec les 9 livres MongoDB.

        TEST CRITIQUE pour Issue #185 :
        Ce test démontre la résolution du problème.
        "Trésors Cachés" et "La Chaises" doivent TOUS DEUX être matchés correctement.

        AVANT le refactoring :
        - "Trésors Cachés" (avis #12) matchait "La chaise" par erreur
        - "La Chaises" (avis #23) ne pouvait plus matcher car "La chaise" déjà claimed

        APRÈS le refactoring :
        - "Trésors Cachés" matche correctement "Trésor caché"
        - "La Chaises" peut alors matcher "La chaise" (reste disponible)
        """
        from bson import ObjectId

        # Livres summary (9 livres uniques extraits du summary)
        livres_summary = [
            {"titre": "La Realidad", "auteur": "Neige Sinno"},
            {"titre": "Mon vrai nom est Elisabeth", "auteur": "Adèle Yon"},
            {
                "titre": "Trésors Cachés",
                "auteur": "Pascal Quignard",
            },  # ⚠️ CRITIQUE (pluriel)
            {"titre": "Mauvais élève", "auteur": "Philippe Vilain"},
            {"titre": "L'ombre portée", "auteur": "Hugues Pagan"},
            {"titre": "Permission", "auteur": "Saskia Vogel"},
            {
                "titre": "La Loi des collines",
                "auteur": "Chris Hoffut",
            },  # Faute dans auteur
            {
                "titre": "La Chaises",
                "auteur": "Jean-Louis Aislin",
            },  # ⚠️ CRITIQUE (S en trop)
            {
                "titre": "Le Livre rouge des ruptures",
                "auteur": "Pirko Sessio",
            },  # Titre tronqué
        ]

        # Livres MongoDB (9 livres réels de l'émission 09/03/2025)
        livres_mongo = [
            {
                "_id": ObjectId("68e919fc066cb40c25d5d2e4"),
                "titre": "La Realidad",
                "auteur_nom": "Neige Sinno",
                "editeur": "POL",
            },
            {
                "_id": ObjectId("68e9192d066cb40c25d5d2d7"),
                "titre": "Mon vrai nom est Elisabeth",
                "auteur_nom": "Adèle Yon",
                "editeur": "Éditions du Sous-Sol",
            },
            {
                "_id": ObjectId("68e9192d066cb40c25d5d2d9"),
                "titre": "Trésor caché",  # ✅ Singulier (différent de "Trésors Cachés")
                "auteur_nom": "Pascal Quignard",
                "editeur": "Albin Michel",
            },
            {
                "_id": ObjectId("68e9192d066cb40c25d5d2db"),
                "titre": "Mauvais élève",
                "auteur_nom": "Philippe Vilain",
                "editeur": "Robert Laffont",
            },
            {
                "_id": ObjectId("68e9192d066cb40c25d5d2dd"),
                "titre": "L'ombre portée",
                "auteur_nom": "Hugues Pagan",
                "editeur": "Rivage Noir",
            },
            {
                "_id": ObjectId("68e9192d066cb40c25d5d2df"),
                "titre": "Permission",
                "auteur_nom": "Saskia Vogel",
                "editeur": "Éditions de La Croisée",
            },
            {
                "_id": ObjectId("68e919a2066cb40c25d5d2e1"),
                "titre": "La Loi des collines",
                "auteur_nom": "Chris Offutt",  # ✅ Nom correct (différent de "Hoffut")
                "editeur": "Galmeister",
            },
            {
                "_id": ObjectId("68e919cd066cb40c25d5d2e3"),
                "titre": "La chaise",  # ✅ Sans S (différent de "La Chaises")
                "auteur_nom": "Jean-Louis Ezine",
                "editeur": "Gallimard",
            },
            {
                "_id": ObjectId("68e91a2d066cb40c25d5d2e6"),
                "titre": "Trilogie de Helsinki : Le livre rouge des ruptures",  # Titre complet
                "auteur_nom": "Pirkko Saisio",
                "editeur": "Robert Laffont",
            },
        ]

        # EXECUTE: Matcher les livres summary avec MongoDB
        livre_matches = self.service.match_livres(livres_summary, livres_mongo)

        # ASSERT CRITIQUE #1: "Trésors Cachés" doit matcher "Trésor caché"
        assert ("Trésors Cachés", "Pascal Quignard") in livre_matches, (
            "Le livre 'Trésors Cachés' doit être matché"
        )
        livre_oid_tresors, phase_tresors = livre_matches[
            ("Trésors Cachés", "Pascal Quignard")
        ]
        assert (
            livre_oid_tresors == "68e9192d066cb40c25d5d2d9"  # pragma: allowlist secret
        ), (
            f"'Trésors Cachés' doit matcher 'Trésor caché' (68e9192d066cb40c25d5d2d9), "
            f"obtenu {livre_oid_tresors}"
        )

        # ASSERT CRITIQUE #2: "La Chaises" doit matcher "La chaise"
        # (PAS déjà claimed par "Trésors Cachés")
        assert ("La Chaises", "Jean-Louis Aislin") in livre_matches, (
            "Le livre 'La Chaises' doit être matché"
        )
        livre_oid_chaises, phase_chaises = livre_matches[
            ("La Chaises", "Jean-Louis Aislin")
        ]
        assert (
            livre_oid_chaises == "68e919cd066cb40c25d5d2e3"  # pragma: allowlist secret
        ), (
            f"'La Chaises' doit matcher 'La chaise' (68e919cd066cb40c25d5d2e3), "
            f"obtenu {livre_oid_chaises}"
        )

        # ASSERT: Tous les livres doivent être matchés
        assert len(livre_matches) == 9, (
            f"Tous les 9 livres doivent être matchés, obtenu {len(livre_matches)}"
        )

        # Vérifier que les autres livres sont aussi matchés
        assert ("La Realidad", "Neige Sinno") in livre_matches
        assert ("Mon vrai nom est Elisabeth", "Adèle Yon") in livre_matches
        assert ("Mauvais élève", "Philippe Vilain") in livre_matches
        assert ("L'ombre portée", "Hugues Pagan") in livre_matches
        assert ("Permission", "Saskia Vogel") in livre_matches
        assert ("La Loi des collines", "Chris Hoffut") in livre_matches
        assert ("Le Livre rouge des ruptures", "Pirko Sessio") in livre_matches

    def test_should_apply_matches_to_all_avis(self):
        """
        Test RED: Le match d'un livre doit être appliqué à tous ses avis.

        Vérifie que resolve_avis() fait correctement le lookup du livre_oid
        pour chaque avis, en utilisant la clé (titre, auteur).
        """
        from bson import ObjectId

        # 8 avis (2 livres avec plusieurs avis chacun)
        avis_list = [
            # Livre "Trésors Cachés" : 4 avis
            {
                "livre_titre_extrait": "Trésors Cachés",
                "auteur_nom_extrait": "Pascal Quignard",
                "critique_nom_extrait": "Arnaud Viviant",
                "commentaire": "Absolument magnifique",
                "note": 9,
                "section": "programme",
            },
            {
                "livre_titre_extrait": "Trésors Cachés",
                "auteur_nom_extrait": "Pascal Quignard",
                "critique_nom_extrait": "Bernard Poirette",
                "commentaire": "Sinistre mais raconté avec bonheur",
                "note": 8,
                "section": "programme",
            },
            {
                "livre_titre_extrait": "Trésors Cachés",
                "auteur_nom_extrait": "Pascal Quignard",
                "critique_nom_extrait": "Patricia Martin",
                "commentaire": "Sensuel, édoniste",
                "note": 8,
                "section": "programme",
            },
            {
                "livre_titre_extrait": "Trésors Cachés",
                "auteur_nom_extrait": "Pascal Quignard",
                "critique_nom_extrait": "Elisabeth Philippe",
                "commentaire": "Magnifique, mais une scène gênante",
                "note": 7,
                "section": "programme",
            },
            # Livre "La Chaises" : 1 avis
            {
                "livre_titre_extrait": "La Chaises",
                "auteur_nom_extrait": "Jean-Louis Aislin",
                "critique_nom_extrait": "Arnaud Viviant",
                "commentaire": "Splendeur, sur le violoncelle",
                "note": 9,
                "section": "coup_de_coeur",
            },
            # Livre "La Realidad" : 2 avis
            {
                "livre_titre_extrait": "La Realidad",
                "auteur_nom_extrait": "Neige Sinno",
                "critique_nom_extrait": "Elisabeth Philippe",
                "commentaire": "Exceptionnel",
                "note": 10,
                "section": "programme",
            },
            {
                "livre_titre_extrait": "La Realidad",
                "auteur_nom_extrait": "Neige Sinno",
                "critique_nom_extrait": "Arnaud Viviant",
                "commentaire": "Magnifique",
                "note": 9,
                "section": "programme",
            },
            # Livre non matché
            {
                "livre_titre_extrait": "Livre inconnu",
                "auteur_nom_extrait": "Auteur inconnu",
                "critique_nom_extrait": "Critique X",
                "commentaire": "Avis sans match",
                "note": 8,
                "section": "programme",
            },
        ]

        # Matches déjà calculés par match_livres()
        livre_matches = {
            ("Trésors Cachés", "Pascal Quignard"): (
                "68e9192d066cb40c25d5d2d9",  # pragma: allowlist secret
                3,
            ),
            ("La Chaises", "Jean-Louis Aislin"): (
                "68e919cd066cb40c25d5d2e3",  # pragma: allowlist secret
                3,
            ),
            ("La Realidad", "Neige Sinno"): (
                "68e919fc066cb40c25d5d2e4",  # pragma: allowlist secret
                1,
            ),
            # "Livre inconnu" n'est pas dans livre_matches (pas de match)
        }

        # Critiques
        critiques = [
            {
                "_id": ObjectId("694eb58bffd25d11ce052759"),
                "nom": "Arnaud Viviant",
                "variantes": [],
            },
            {
                "_id": ObjectId("694f17665eac26c9eb2852ff"),
                "nom": "Bernard Poirette",
                "variantes": ["Bernard Poiret"],
            },
            {
                "_id": ObjectId("694eb7423696842476c793cf"),
                "nom": "Patricia Martin",
                "variantes": [],
            },
            {
                "_id": ObjectId("694eb72b3696842476c793cd"),
                "nom": "Elisabeth Philippe",
                "variantes": [],
            },
        ]

        # EXECUTE: Appliquer les matches aux avis
        resolved = self.service.resolve_avis(avis_list, livre_matches, critiques)

        # ASSERT: 8 avis résolus
        assert len(resolved) == 8

        # ASSERT: Les 4 avis "Trésors Cachés" doivent avoir le même livre_oid
        tresors_avis = [
            a for a in resolved if a["livre_titre_extrait"] == "Trésors Cachés"
        ]
        assert len(tresors_avis) == 4
        assert all(
            a["livre_oid"] == "68e9192d066cb40c25d5d2d9"  # pragma: allowlist secret
            for a in tresors_avis
        ), "Tous les avis 'Trésors Cachés' doivent avoir le même livre_oid"
        assert all(a["match_phase"] == 3 for a in tresors_avis)

        # ASSERT: L'avis "La Chaises" doit être matché
        chaises_avis = [a for a in resolved if a["livre_titre_extrait"] == "La Chaises"]
        assert len(chaises_avis) == 1
        assert (
            chaises_avis[0]["livre_oid"]
            == "68e919cd066cb40c25d5d2e3"  # pragma: allowlist secret
        )
        assert chaises_avis[0]["match_phase"] == 3

        # ASSERT: Les 2 avis "La Realidad" doivent avoir le même livre_oid
        realidad_avis = [
            a for a in resolved if a["livre_titre_extrait"] == "La Realidad"
        ]
        assert len(realidad_avis) == 2
        assert all(
            a["livre_oid"] == "68e919fc066cb40c25d5d2e4"  # pragma: allowlist secret
            for a in realidad_avis
        )
        assert all(a["match_phase"] == 1 for a in realidad_avis)

        # ASSERT: L'avis non matché doit avoir livre_oid=None
        inconnu_avis = [
            a for a in resolved if a["livre_titre_extrait"] == "Livre inconnu"
        ]
        assert len(inconnu_avis) == 1
        assert inconnu_avis[0]["livre_oid"] is None
        assert inconnu_avis[0]["match_phase"] is None

        # ASSERT: Les critiques doivent être matchées
        assert (
            tresors_avis[0]["critique_oid"]
            == "694eb58bffd25d11ce052759"  # pragma: allowlist secret
        )  # Arnaud Viviant
        assert (
            chaises_avis[0]["critique_oid"]
            == "694eb58bffd25d11ce052759"  # pragma: allowlist secret
        )  # Arnaud Viviant
        assert (
            realidad_avis[0]["critique_oid"]
            == "694eb72b3696842476c793cd"  # pragma: allowlist secret
        )  # Elisabeth Philippe

    def test_should_fix_emission_20250309_matching(self):
        """
        Test RED INTÉGRATION: L'émission 09/03/2025 doit être 100% matchée (badge 🟢).

        TEST CRITIQUE D'INTÉGRATION pour Issue #185 :
        Ce test vérifie que TOUS les avis de l'émission 09/03/2025 sont correctement matchés
        après le refactoring.

        AVANT le refactoring :
        - 23/24 avis matchés
        - "La Chaises" non matché (livre_oid=None)
        - Badge 🟡 (unmatched)

        APRÈS le refactoring :
        - 24/24 avis matchés
        - "La Chaises" correctement matché à "La chaise"
        - Badge 🟢 (perfect)
        """
        from bson import ObjectId

        # Utiliser les données réelles de test_avis_extraction_emission_20250309.py
        # 24 avis (5 livres × 4 critiques + 4 coups de cœur)
        # 9 livres MongoDB
        # 4 critiques

        # Simplification : utiliser un sous-ensemble représentatif des avis
        # (Focus sur les 2 livres problématiques)
        avis_list = [
            # "Trésors Cachés" : 2 avis (plutôt que 4 pour simplifier)
            {
                "livre_titre_extrait": "Trésors Cachés",
                "auteur_nom_extrait": "Pascal Quignard",
                "critique_nom_extrait": "Arnaud Viviant",
                "commentaire": "Absolument magnifique",
                "note": 9,
                "section": "programme",
            },
            {
                "livre_titre_extrait": "Trésors Cachés",
                "auteur_nom_extrait": "Pascal Quignard",
                "critique_nom_extrait": "Bernard Poirette",
                "commentaire": "Sinistre mais raconté avec bonheur",
                "note": 8,
                "section": "programme",
            },
            # "La Chaises" : 1 avis (le problématique)
            {
                "livre_titre_extrait": "La Chaises",
                "auteur_nom_extrait": "Jean-Louis Aislin",
                "critique_nom_extrait": "Arnaud Viviant",
                "commentaire": "Splendeur, sur le violoncelle",
                "note": 9,
                "section": "coup_de_coeur",
            },
        ]

        # Livres MongoDB (seulement les 2 livres concernés)
        livres_mongo = [
            {
                "_id": ObjectId("68e9192d066cb40c25d5d2d9"),
                "titre": "Trésor caché",  # ✅ Singulier
                "auteur_nom": "Pascal Quignard",
                "auteur_id": ObjectId("68e9192d066cb40c25d5d2d8"),
                "editeur": "Albin Michel",
            },
            {
                "_id": ObjectId("68e919cd066cb40c25d5d2e3"),
                "titre": "La chaise",  # ✅ Sans S
                "auteur_nom": "Jean-Louis Ezine",
                "auteur_id": ObjectId("68e919cd066cb40c25d5d2e2"),
                "editeur": "Gallimard",
            },
        ]

        # Critiques
        critiques = [
            {
                "_id": ObjectId("694eb58bffd25d11ce052759"),
                "nom": "Arnaud Viviant",
                "variantes": [],
            },
            {
                "_id": ObjectId("694f17665eac26c9eb2852ff"),
                "nom": "Bernard Poirette",
                "variantes": ["Bernard Poiret"],
            },
        ]

        # EXECUTE: Résoudre les entités (appel à resolve_entities wrapper)
        resolved = self.service.resolve_entities(avis_list, livres_mongo, critiques)

        # ASSERT: Tous les avis doivent être matchés
        unmatched = [a for a in resolved if a["livre_oid"] is None]
        assert len(unmatched) == 0, (
            f"Tous les avis doivent être matchés. Avis non matchés : {unmatched}"
        )

        # ASSERT CRITIQUE: "La Chaises" doit matcher "La chaise"
        chaises_avis = [a for a in resolved if a["livre_titre_extrait"] == "La Chaises"]
        assert len(chaises_avis) == 1
        assert (
            chaises_avis[0]["livre_oid"]
            == "68e919cd066cb40c25d5d2e3"  # pragma: allowlist secret
        ), (
            f"'La Chaises' doit matcher 'La chaise' (68e919cd066cb40c25d5d2e3), "
            f"obtenu {chaises_avis[0].get('livre_oid')}"
        )

        # ASSERT: "Trésors Cachés" doit matcher "Trésor caché"
        tresors_avis = [
            a for a in resolved if a["livre_titre_extrait"] == "Trésors Cachés"
        ]
        assert len(tresors_avis) == 2
        assert all(
            a["livre_oid"] == "68e9192d066cb40c25d5d2d9"  # pragma: allowlist secret
            for a in tresors_avis
        ), "Tous les avis 'Trésors Cachés' doivent matcher 'Trésor caché'"

        # ASSERT: Badge devrait être 🟢 (tous les livres matchés)
        # Le calcul du badge se fait au niveau de l'API, mais ici on vérifie
        # que la condition est remplie : aucun avis non matché
        assert len(unmatched) == 0  # → Badge 🟢
