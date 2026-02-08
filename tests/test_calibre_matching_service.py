"""Tests pour le service de matching MongoDB-Calibre (Issue #199)."""

from unittest.mock import MagicMock

from back_office_lmelp.utils.text_utils import normalize_for_matching


class TestNormalizeForMatching:
    """Tests pour la fonction normalize_for_matching."""

    def test_simple_lowercase(self):
        """Normalise en minuscules."""
        assert normalize_for_matching("Le Lambeau") == "le lambeau"

    def test_removes_accents(self):
        """Retire les accents."""
        assert normalize_for_matching("L'Ordre du jour") == "l'ordre du jour"
        assert normalize_for_matching("Carrère") == "carrere"

    def test_handles_ligatures_oe(self):
        """Normalise la ligature oe."""
        assert normalize_for_matching("L'Œuvre au noir") == "l'oeuvre au noir"

    def test_handles_ligatures_ae(self):
        """Normalise la ligature ae."""
        assert normalize_for_matching("Encyclopædia") == "encyclopaedia"

    def test_normalizes_dashes(self):
        """Normalise le tiret cadratin en tiret simple."""
        assert normalize_for_matching("Marie\u2013Claire") == "marie-claire"

    def test_normalizes_apostrophes(self):
        """Normalise l'apostrophe typographique en apostrophe simple."""
        assert normalize_for_matching("L\u2019ami retrouvé") == "l'ami retrouve"

    def test_strips_whitespace(self):
        """Retire les espaces en début et fin."""
        assert normalize_for_matching("  Feu  ") == "feu"

    def test_collapses_multiple_spaces(self):
        """Réduit les espaces multiples."""
        assert normalize_for_matching("Le   Grand   Meaulnes") == "le grand meaulnes"

    def test_empty_string(self):
        """Gère les chaînes vides."""
        assert normalize_for_matching("") == ""

    def test_complex_title(self):
        """Titre complexe combinant accents, ligatures et tirets."""
        result = normalize_for_matching("L'Œuvre–journal de Gaspard Kœnig")
        assert result == "l'oeuvre-journal de gaspard koenig"


class TestCalibreMatchingServiceNormalizeAuthor:
    """Tests pour la normalisation des noms d'auteurs."""

    def test_normalize_author_simple(self):
        """Nom simple en format naturel."""
        from back_office_lmelp.services.calibre_matching_service import (
            CalibreMatchingService,
        )

        service = CalibreMatchingService.__new__(CalibreMatchingService)
        parts = service._normalize_author_parts("Mohamed Mbougar Sarr")
        assert "sarr" in parts
        assert "mohamed" in parts

    def test_normalize_author_calibre_pipe_format(self):
        """Format Calibre avec pipe : 'Nom| Prénom'."""
        from back_office_lmelp.services.calibre_matching_service import (
            CalibreMatchingService,
        )

        service = CalibreMatchingService.__new__(CalibreMatchingService)
        parts = service._normalize_author_parts("Appanah| Nathacha")
        assert "appanah" in parts
        assert "nathacha" in parts

    def test_normalize_author_calibre_comma_format(self):
        """Format Calibre avec virgule : 'Nom, Prénom'."""
        from back_office_lmelp.services.calibre_matching_service import (
            CalibreMatchingService,
        )

        service = CalibreMatchingService.__new__(CalibreMatchingService)
        parts = service._normalize_author_parts("Sarr, Mohamed Mbougar")
        assert "sarr" in parts
        assert "mohamed" in parts

    def test_normalize_author_with_ligature(self):
        """Nom avec ligature."""
        from back_office_lmelp.services.calibre_matching_service import (
            CalibreMatchingService,
        )

        service = CalibreMatchingService.__new__(CalibreMatchingService)
        parts = service._normalize_author_parts("Kœnig| Gaspard")
        assert "koenig" in parts
        assert "gaspard" in parts

    def test_normalize_author_with_initials(self):
        """Nom avec initiales (E. J. vs E.J.)."""
        from back_office_lmelp.services.calibre_matching_service import (
            CalibreMatchingService,
        )

        service = CalibreMatchingService.__new__(CalibreMatchingService)
        parts1 = service._normalize_author_parts("E. J. Levy")
        parts2 = service._normalize_author_parts("E.J. Levy")
        # Both should contain "levy" as the main surname
        assert "levy" in parts1
        assert "levy" in parts2


class TestCalibreMatchingServiceAuthorsMatch:
    """Tests pour la comparaison tolérante des auteurs."""

    def _make_service(self):
        from back_office_lmelp.services.calibre_matching_service import (
            CalibreMatchingService,
        )

        return CalibreMatchingService.__new__(CalibreMatchingService)

    def test_exact_same_name(self):
        """Même nom exact."""
        service = self._make_service()
        assert service._authors_match("Mohamed Mbougar Sarr", ["Mohamed Mbougar Sarr"])

    def test_inverted_format(self):
        """Calibre format inversé vs MongoDB format naturel."""
        service = self._make_service()
        assert service._authors_match("Nathacha Appanah", ["Appanah| Nathacha"])

    def test_ligature_difference(self):
        """Ligature dans un nom."""
        service = self._make_service()
        assert service._authors_match("Gaspard Koenig", ["Kœnig| Gaspard"])

    def test_different_authors_no_match(self):
        """Auteurs complètement différents."""
        service = self._make_service()
        assert not service._authors_match("Victor Hugo", ["Albert Camus"])

    def test_co_author_partial_match(self):
        """Co-auteur : au moins un auteur Calibre matche."""
        service = self._make_service()
        assert service._authors_match("Stephen King", ["King, Stephen", "King, Owen"])

    def test_dash_in_name(self):
        """Tiret dans le nom (Mbougar-Sarr vs Mbougar Sarr)."""
        service = self._make_service()
        assert service._authors_match(
            "Mohamed Mbougar Sarr", ["Sarr, Mohamed Mbougar-Sarr"]
        )


class TestCalibreMatchingServiceMatchAll:
    """Tests pour le matching complet MongoDB-Calibre."""

    def _make_service(self, calibre_books, mongo_livres, mongo_authors):
        from back_office_lmelp.services.calibre_matching_service import (
            CalibreMatchingService,
        )

        mock_calibre = MagicMock()
        mock_calibre._available = True
        mock_calibre.get_all_books_with_tags.return_value = calibre_books

        mock_mongodb = MagicMock()
        mock_mongodb.get_all_books.return_value = mongo_livres
        mock_mongodb.get_all_authors.return_value = mongo_authors

        service = CalibreMatchingService(mock_calibre, mock_mongodb)
        return service

    def test_exact_title_match(self):
        """Matching exact par titre normalisé."""
        calibre_books = [
            {
                "id": 42,
                "title": "Le Lambeau",
                "authors": ["Lançon, Philippe"],
                "tags": ["roman"],
                "read": True,
                "rating": 8,
            }
        ]
        mongo_livres = [{"_id": "abc123", "titre": "Le Lambeau", "auteur_id": "auth1"}]
        mongo_authors = [{"_id": "auth1", "nom": "Philippe Lançon"}]

        service = self._make_service(calibre_books, mongo_livres, mongo_authors)
        matches = service.match_all()

        assert len(matches) == 1
        assert matches[0]["match_type"] == "exact"
        assert matches[0]["calibre_id"] == 42
        assert matches[0]["mongo_livre_id"] == "abc123"

    def test_containment_match_subtitle(self):
        """Matching par containment : sous-titre dans Calibre."""
        calibre_books = [
            {
                "id": 100,
                "title": "Chanson douce - Prix Goncourt 2016",
                "authors": ["Slimani, Leïla"],
                "tags": [],
                "read": False,
                "rating": None,
            }
        ]
        mongo_livres = [
            {"_id": "def456", "titre": "Chanson douce", "auteur_id": "auth2"}
        ]
        mongo_authors = [{"_id": "auth2", "nom": "Leïla Slimani"}]

        service = self._make_service(calibre_books, mongo_livres, mongo_authors)
        matches = service.match_all()

        assert len(matches) == 1
        assert matches[0]["match_type"] == "containment"

    def test_containment_match_tome(self):
        """Matching par containment : tome dans MongoDB."""
        calibre_books = [
            {
                "id": 200,
                "title": "L'amie prodigieuse",
                "authors": ["Ferrante, Elena"],
                "tags": [],
                "read": True,
                "rating": 6,
            }
        ]
        mongo_livres = [
            {
                "_id": "ghi789",
                "titre": "L'amie prodigieuse, tome 3 : Celle qui fuit et celle qui reste",
                "auteur_id": "auth3",
            }
        ]
        mongo_authors = [{"_id": "auth3", "nom": "Elena Ferrante"}]

        service = self._make_service(calibre_books, mongo_livres, mongo_authors)
        matches = service.match_all()

        assert len(matches) == 1
        assert matches[0]["match_type"] == "containment"

    def test_no_match_different_books(self):
        """Pas de matching pour des livres différents."""
        calibre_books = [
            {
                "id": 1,
                "title": "Les Misérables",
                "authors": ["Hugo, Victor"],
                "tags": [],
                "read": False,
                "rating": None,
            }
        ]
        mongo_livres = [{"_id": "xyz", "titre": "La Peste", "auteur_id": "auth4"}]
        mongo_authors = [{"_id": "auth4", "nom": "Albert Camus"}]

        service = self._make_service(calibre_books, mongo_livres, mongo_authors)
        matches = service.match_all()

        assert len(matches) == 0

    def test_short_title_requires_author_validation(self):
        """Titre court (< 4 chars normalisés) ne matche pas par containment seul."""
        calibre_books = [
            {
                "id": 300,
                "title": "Feu",
                "authors": ["Pourchet, Maria"],
                "tags": [],
                "read": False,
                "rating": None,
            },
            {
                "id": 301,
                "title": "Feuilleton du dimanche",
                "authors": ["Dupont, Jean"],
                "tags": [],
                "read": False,
                "rating": None,
            },
        ]
        mongo_livres = [{"_id": "m1", "titre": "Feu", "auteur_id": "a1"}]
        mongo_authors = [{"_id": "a1", "nom": "Maria Pourchet"}]

        service = self._make_service(calibre_books, mongo_livres, mongo_authors)
        matches = service.match_all()

        # Should match "Feu" exactly, NOT "Feuilleton du dimanche"
        assert len(matches) == 1
        assert matches[0]["calibre_id"] == 300
        assert matches[0]["match_type"] == "exact"

    def test_calibre_unavailable_returns_empty(self):
        """Calibre non disponible retourne une liste vide."""
        from back_office_lmelp.services.calibre_matching_service import (
            CalibreMatchingService,
        )

        mock_calibre = MagicMock()
        mock_calibre._available = False

        mock_mongodb = MagicMock()

        service = CalibreMatchingService(mock_calibre, mock_mongodb)
        matches = service.match_all()

        assert matches == []


class TestCalibreMatchingServiceContainmentBugFixes:
    """Tests pour les corrections de bugs du matching par containment."""

    def _make_service(self, calibre_books, mongo_livres, mongo_authors):
        from back_office_lmelp.services.calibre_matching_service import (
            CalibreMatchingService,
        )

        mock_calibre = MagicMock()
        mock_calibre._available = True
        mock_calibre.get_all_books_with_tags.return_value = calibre_books

        mock_mongodb = MagicMock()
        mock_mongodb.get_all_books.return_value = mongo_livres
        mock_mongodb.get_all_authors.return_value = mongo_authors

        service = CalibreMatchingService(mock_calibre, mock_mongodb)
        return service

    def test_equal_length_different_titles_no_false_match(self):
        """Deux titres de même longueur mais différents ne doivent PAS matcher.

        Bug: min(a, b, key=len) et max(a, b, key=len) retournent le même string
        quand len(a) == len(b), donc 'shorter in longer' est toujours True.
        """
        # "la prochaine fois que tu mordras la poussiere" (45 chars)
        # "tante alice enquete - 02 - meurtres en chaine" (45 chars)
        calibre_books = [
            {
                "id": 1827,
                "title": "Tante Alice enquête - 02 - Meurtres en chaîne",
                "authors": ["Ali Rebeihi"],
                "tags": [],
                "read": False,
                "rating": None,
            }
        ]
        mongo_livres = [
            {
                "_id": "pascot1",
                "titre": "La prochaine fois que tu mordras la poussière",
                "auteur_id": "a_pascot",
            }
        ]
        mongo_authors = [{"_id": "a_pascot", "nom": "Panayotis Pascot"}]

        service = self._make_service(calibre_books, mongo_livres, mongo_authors)
        matches = service.match_all()

        # These are completely different books - should NOT match
        assert len(matches) == 0

    def test_single_containment_candidate_requires_author_validation(self):
        """Un seul candidat containment doit aussi valider l'auteur.

        Bug: les candidats uniques en containment sautent la validation auteur,
        contrairement aux candidats multiples.
        """
        calibre_books = [
            {
                "id": 500,
                "title": "Les fleurs du mal - Édition annotée",
                "authors": ["Baudelaire, Charles"],
                "tags": [],
                "read": True,
                "rating": 8,
            }
        ]
        mongo_livres = [
            {
                "_id": "m_wrong",
                "titre": "Les fleurs du mal",
                "auteur_id": "a_wrong",
            }
        ]
        # Different author - should still match because title containment is valid
        # and author does match (Baudelaire contains baudelaire)
        mongo_authors = [{"_id": "a_wrong", "nom": "Charles Baudelaire"}]

        service = self._make_service(calibre_books, mongo_livres, mongo_authors)
        matches = service.match_all()

        # Valid containment + matching author = should match
        assert len(matches) == 1
        assert matches[0]["match_type"] == "containment"

    def test_single_containment_candidate_wrong_author_no_match(self):
        """Un candidat containment avec un auteur différent ne doit PAS matcher."""
        calibre_books = [
            {
                "id": 501,
                "title": "Les fleurs du mal - Édition annotée",
                "authors": ["Baudelaire, Charles"],
                "tags": [],
                "read": True,
                "rating": 8,
            }
        ]
        mongo_livres = [
            {
                "_id": "m_wrong",
                "titre": "Les fleurs du mal",
                "auteur_id": "a_wrong",
            }
        ]
        # Completely different author
        mongo_authors = [{"_id": "a_wrong", "nom": "Victor Hugo"}]

        service = self._make_service(calibre_books, mongo_livres, mongo_authors)
        matches = service.match_all()

        # Containment is valid, but wrong author = no match
        assert len(matches) == 0


class TestCalibreMatchingServiceCorrections:
    """Tests pour les corrections Calibre."""

    def _make_service(
        self, calibre_books, mongo_livres, mongo_authors, expected_tags=None
    ):
        from back_office_lmelp.services.calibre_matching_service import (
            CalibreMatchingService,
        )

        mock_calibre = MagicMock()
        mock_calibre._available = True
        mock_calibre.get_all_books_with_tags.return_value = calibre_books

        mock_mongodb = MagicMock()
        mock_mongodb.get_all_books.return_value = mongo_livres
        mock_mongodb.get_all_authors.return_value = mongo_authors
        mock_mongodb.get_expected_calibre_tags.return_value = (
            expected_tags if expected_tags is not None else {}
        )

        service = CalibreMatchingService(mock_calibre, mock_mongodb)
        return service

    def test_author_correction_detected(self):
        """Détecte les différences de noms d'auteurs."""
        calibre_books = [
            {
                "id": 42,
                "title": "Tropique de la violence",
                "authors": ["Appanah| Nathacha"],
                "tags": ["lmelp_220101"],
                "read": True,
                "rating": 8,
            }
        ]
        mongo_livres = [
            {
                "_id": "abc",
                "titre": "Tropique de la violence",
                "auteur_id": "a1",
            }
        ]
        mongo_authors = [{"_id": "a1", "nom": "Nathacha Appanah"}]

        service = self._make_service(calibre_books, mongo_livres, mongo_authors)
        corrections = service.get_corrections()

        assert len(corrections["author_corrections"]) == 1
        assert corrections["author_corrections"][0]["calibre_authors"] == [
            "Appanah| Nathacha"
        ]
        assert corrections["author_corrections"][0]["mongodb_author"] == (
            "Nathacha Appanah"
        )

    def test_title_correction_detected(self):
        """Détecte les différences de titres."""
        calibre_books = [
            {
                "id": 100,
                "title": "Chanson douce - Prix Goncourt 2016",
                "authors": ["Slimani, Leïla"],
                "tags": [],
                "read": False,
                "rating": None,
            }
        ]
        mongo_livres = [{"_id": "def", "titre": "Chanson douce", "auteur_id": "a2"}]
        mongo_authors = [{"_id": "a2", "nom": "Leïla Slimani"}]

        service = self._make_service(calibre_books, mongo_livres, mongo_authors)
        corrections = service.get_corrections()

        assert len(corrections["title_corrections"]) == 1
        assert corrections["title_corrections"][0]["calibre_title"] == (
            "Chanson douce - Prix Goncourt 2016"
        )
        assert corrections["title_corrections"][0]["mongodb_title"] == ("Chanson douce")

    def test_missing_lmelp_tags_detected(self):
        """Détecte les livres matchés sans tag lmelp_."""
        calibre_books = [
            {
                "id": 55,
                "title": "La seule histoire",
                "authors": ["Barnes, Julian"],
                "tags": ["roman", "anglais"],
                "read": True,
                "rating": 6,
            }
        ]
        mongo_livres = [{"_id": "ghi", "titre": "La seule histoire", "auteur_id": "a3"}]
        mongo_authors = [{"_id": "a3", "nom": "Julian Barnes"}]

        service = self._make_service(
            calibre_books,
            mongo_livres,
            mongo_authors,
            expected_tags={"ghi": ["lmelp_240922"]},
        )
        corrections = service.get_corrections()

        assert len(corrections["missing_lmelp_tags"]) == 1
        assert corrections["missing_lmelp_tags"][0]["calibre_id"] == 55
        assert corrections["missing_lmelp_tags"][0]["current_tags"] == [
            "roman",
            "anglais",
        ]

    def test_missing_lmelp_tags_includes_expected_tags(self):
        """Les entrées missing_lmelp_tags contiennent les tags attendus et à copier."""

        calibre_books = [
            {
                "id": 55,
                "title": "La seule histoire",
                "authors": ["Barnes, Julian"],
                "tags": ["roman"],
                "read": True,
                "rating": 6,
            }
        ]
        mongo_livres = [{"_id": "ghi", "titre": "La seule histoire", "auteur_id": "a3"}]
        mongo_authors = [{"_id": "a3", "nom": "Julian Barnes"}]

        # Mock get_expected_calibre_tags to return expected lmelp_ tags
        mock_mongodb = MagicMock()
        mock_mongodb.get_all_books.return_value = mongo_livres
        mock_mongodb.get_all_authors.return_value = mongo_authors
        mock_mongodb.get_expected_calibre_tags.return_value = {
            "ghi": ["lmelp_240922", "lmelp_michel_crement"],
        }

        mock_calibre = MagicMock()
        mock_calibre._available = True
        mock_calibre.get_all_books_with_tags.return_value = calibre_books

        from back_office_lmelp.services.calibre_matching_service import (
            CalibreMatchingService,
        )

        service = CalibreMatchingService(mock_calibre, mock_mongodb)
        corrections = service.get_corrections()

        entry = corrections["missing_lmelp_tags"][0]
        # Should contain the expected lmelp_ tags (what's missing)
        assert entry["expected_lmelp_tags"] == ["lmelp_240922", "lmelp_michel_crement"]
        # all_tags_to_copy = exactly what _build_calibre_tags() returns (same as livre detail)
        assert entry["all_tags_to_copy"] == [
            "lmelp_240922",
            "lmelp_michel_crement",
        ]

    def test_missing_lmelp_tags_partial_existing(self):
        """Un livre avec certains lmelp_ déjà présents mais pas tous apparaît quand même."""
        calibre_books = [
            {
                "id": 55,
                "title": "La seule histoire",
                "authors": ["Barnes, Julian"],
                "tags": ["roman", "lmelp_240922"],  # lmelp_240922 already exists
                "read": True,
                "rating": 6,
            }
        ]
        mongo_livres = [{"_id": "ghi", "titre": "La seule histoire", "auteur_id": "a3"}]
        mongo_authors = [{"_id": "a3", "nom": "Julian Barnes"}]

        mock_mongodb = MagicMock()
        mock_mongodb.get_all_books.return_value = mongo_livres
        mock_mongodb.get_all_authors.return_value = mongo_authors
        mock_mongodb.get_expected_calibre_tags.return_value = {
            "ghi": ["lmelp_240922", "lmelp_michel_crement"],
        }

        mock_calibre = MagicMock()
        mock_calibre._available = True
        mock_calibre.get_all_books_with_tags.return_value = calibre_books

        from back_office_lmelp.services.calibre_matching_service import (
            CalibreMatchingService,
        )

        service = CalibreMatchingService(mock_calibre, mock_mongodb)
        corrections = service.get_corrections()

        # This book has lmelp_240922 but is missing lmelp_michel_crement
        # So it should still appear in missing_lmelp_tags
        assert len(corrections["missing_lmelp_tags"]) == 1
        entry = corrections["missing_lmelp_tags"][0]
        # Only the missing tag
        assert entry["expected_lmelp_tags"] == ["lmelp_michel_crement"]
        # all_tags_to_copy = exactly what _build_calibre_tags() returns (all expected lmelp_)
        assert entry["all_tags_to_copy"] == [
            "lmelp_240922",
            "lmelp_michel_crement",
        ]

    def test_no_missing_lmelp_tags_when_all_present(self):
        """Un livre avec tous les lmelp_ attendus n'apparaît pas dans missing."""
        calibre_books = [
            {
                "id": 55,
                "title": "La seule histoire",
                "authors": ["Barnes, Julian"],
                "tags": ["roman", "lmelp_240922", "lmelp_michel_crement"],
                "read": True,
                "rating": 6,
            }
        ]
        mongo_livres = [{"_id": "ghi", "titre": "La seule histoire", "auteur_id": "a3"}]
        mongo_authors = [{"_id": "a3", "nom": "Julian Barnes"}]

        mock_mongodb = MagicMock()
        mock_mongodb.get_all_books.return_value = mongo_livres
        mock_mongodb.get_all_authors.return_value = mongo_authors
        mock_mongodb.get_expected_calibre_tags.return_value = {
            "ghi": ["lmelp_240922", "lmelp_michel_crement"],
        }

        mock_calibre = MagicMock()
        mock_calibre._available = True
        mock_calibre.get_all_books_with_tags.return_value = calibre_books

        from back_office_lmelp.services.calibre_matching_service import (
            CalibreMatchingService,
        )

        service = CalibreMatchingService(mock_calibre, mock_mongodb)
        corrections = service.get_corrections()

        # All expected lmelp_ tags already exist → should NOT appear
        assert len(corrections["missing_lmelp_tags"]) == 0

    def test_all_tags_to_copy_includes_virtual_library_tag(self):
        """all_tags_to_copy inclut CALIBRE_VIRTUAL_LIBRARY_TAG en position 0 si configuré."""
        calibre_books = [
            {
                "id": 55,
                "title": "La seule histoire",
                "authors": ["Barnes, Julian"],
                "tags": ["roman"],
                "read": True,
                "rating": 6,
            }
        ]
        mongo_livres = [{"_id": "ghi", "titre": "La seule histoire", "auteur_id": "a3"}]
        mongo_authors = [{"_id": "a3", "nom": "Julian Barnes"}]

        mock_mongodb = MagicMock()
        mock_mongodb.get_all_books.return_value = mongo_livres
        mock_mongodb.get_all_authors.return_value = mongo_authors
        mock_mongodb.get_expected_calibre_tags.return_value = {
            "ghi": ["lmelp_240922", "lmelp_michel_crement"],
        }

        mock_calibre = MagicMock()
        mock_calibre._available = True
        mock_calibre.get_all_books_with_tags.return_value = calibre_books

        from back_office_lmelp.services.calibre_matching_service import (
            CalibreMatchingService,
        )

        service = CalibreMatchingService(
            mock_calibre, mock_mongodb, virtual_library_tag="guillaume"
        )
        corrections = service.get_corrections()

        entry = corrections["missing_lmelp_tags"][0]
        # "guillaume" should be prepended to all_tags_to_copy
        assert entry["all_tags_to_copy"] == [
            "guillaume",
            "lmelp_240922",
            "lmelp_michel_crement",
        ]

    def test_all_tags_to_copy_without_virtual_library_tag(self):
        """all_tags_to_copy ne contient pas de virtual library tag si non configuré."""
        calibre_books = [
            {
                "id": 55,
                "title": "La seule histoire",
                "authors": ["Barnes, Julian"],
                "tags": ["roman"],
                "read": True,
                "rating": 6,
            }
        ]
        mongo_livres = [{"_id": "ghi", "titre": "La seule histoire", "auteur_id": "a3"}]
        mongo_authors = [{"_id": "a3", "nom": "Julian Barnes"}]

        mock_mongodb = MagicMock()
        mock_mongodb.get_all_books.return_value = mongo_livres
        mock_mongodb.get_all_authors.return_value = mongo_authors
        mock_mongodb.get_expected_calibre_tags.return_value = {
            "ghi": ["lmelp_240922"],
        }

        mock_calibre = MagicMock()
        mock_calibre._available = True
        mock_calibre.get_all_books_with_tags.return_value = calibre_books

        from back_office_lmelp.services.calibre_matching_service import (
            CalibreMatchingService,
        )

        # No virtual_library_tag → no prepend
        service = CalibreMatchingService(mock_calibre, mock_mongodb)
        corrections = service.get_corrections()

        entry = corrections["missing_lmelp_tags"][0]
        assert entry["all_tags_to_copy"] == ["lmelp_240922"]

    def test_all_tags_to_copy_preserves_notable_tags(self):
        """all_tags_to_copy inclut les tags notables (lu, onkindle) déjà présents dans Calibre."""
        calibre_books = [
            {
                "id": 55,
                "title": "La seule histoire",
                "authors": ["Barnes, Julian"],
                "tags": ["roman", "lu", "onkindle"],
                "read": True,
                "rating": 6,
            }
        ]
        mongo_livres = [{"_id": "ghi", "titre": "La seule histoire", "auteur_id": "a3"}]
        mongo_authors = [{"_id": "a3", "nom": "Julian Barnes"}]

        mock_mongodb = MagicMock()
        mock_mongodb.get_all_books.return_value = mongo_livres
        mock_mongodb.get_all_authors.return_value = mongo_authors
        mock_mongodb.get_expected_calibre_tags.return_value = {
            "ghi": ["lmelp_240922"],
        }

        mock_calibre = MagicMock()
        mock_calibre._available = True
        mock_calibre.get_all_books_with_tags.return_value = calibre_books

        from back_office_lmelp.services.calibre_matching_service import (
            CalibreMatchingService,
        )

        service = CalibreMatchingService(
            mock_calibre, mock_mongodb, virtual_library_tag="guillaume"
        )
        corrections = service.get_corrections()

        entry = corrections["missing_lmelp_tags"][0]
        # Order: virtual_library_tag, notable tags (lu, onkindle), lmelp_ tags
        assert entry["all_tags_to_copy"] == [
            "guillaume",
            "lu",
            "onkindle",
            "lmelp_240922",
        ]

    def test_all_tags_to_copy_preserves_only_present_notable_tags(self):
        """all_tags_to_copy n'inclut que les tags notables effectivement présents."""
        calibre_books = [
            {
                "id": 55,
                "title": "La seule histoire",
                "authors": ["Barnes, Julian"],
                "tags": ["roman", "onkindle"],  # lu absent
                "read": True,
                "rating": 6,
            }
        ]
        mongo_livres = [{"_id": "ghi", "titre": "La seule histoire", "auteur_id": "a3"}]
        mongo_authors = [{"_id": "a3", "nom": "Julian Barnes"}]

        mock_mongodb = MagicMock()
        mock_mongodb.get_all_books.return_value = mongo_livres
        mock_mongodb.get_all_authors.return_value = mongo_authors
        mock_mongodb.get_expected_calibre_tags.return_value = {
            "ghi": ["lmelp_240922"],
        }

        mock_calibre = MagicMock()
        mock_calibre._available = True
        mock_calibre.get_all_books_with_tags.return_value = calibre_books

        from back_office_lmelp.services.calibre_matching_service import (
            CalibreMatchingService,
        )

        service = CalibreMatchingService(mock_calibre, mock_mongodb)
        corrections = service.get_corrections()

        entry = corrections["missing_lmelp_tags"][0]
        # Only onkindle present, no lu, no virtual_library_tag
        assert entry["all_tags_to_copy"] == ["onkindle", "lmelp_240922"]

    def test_all_tags_to_copy_no_notable_tags_when_absent(self):
        """all_tags_to_copy sans tags notables si aucun n'est présent dans Calibre."""
        calibre_books = [
            {
                "id": 55,
                "title": "La seule histoire",
                "authors": ["Barnes, Julian"],
                "tags": ["roman", "anglais"],  # ni lu ni onkindle
                "read": True,
                "rating": 6,
            }
        ]
        mongo_livres = [{"_id": "ghi", "titre": "La seule histoire", "auteur_id": "a3"}]
        mongo_authors = [{"_id": "a3", "nom": "Julian Barnes"}]

        mock_mongodb = MagicMock()
        mock_mongodb.get_all_books.return_value = mongo_livres
        mock_mongodb.get_all_authors.return_value = mongo_authors
        mock_mongodb.get_expected_calibre_tags.return_value = {
            "ghi": ["lmelp_240922"],
        }

        mock_calibre = MagicMock()
        mock_calibre._available = True
        mock_calibre.get_all_books_with_tags.return_value = calibre_books

        from back_office_lmelp.services.calibre_matching_service import (
            CalibreMatchingService,
        )

        service = CalibreMatchingService(mock_calibre, mock_mongodb)
        corrections = service.get_corrections()

        entry = corrections["missing_lmelp_tags"][0]
        # No notable tags present → just lmelp_ tags
        assert entry["all_tags_to_copy"] == ["lmelp_240922"]

    def test_all_tags_to_copy_preserves_babelio_tag(self):
        """all_tags_to_copy inclut le tag babelio s'il est présent dans Calibre."""
        calibre_books = [
            {
                "id": 55,
                "title": "La seule histoire",
                "authors": ["Barnes, Julian"],
                "tags": ["roman", "babelio", "lu"],
                "read": True,
                "rating": 6,
            }
        ]
        mongo_livres = [{"_id": "ghi", "titre": "La seule histoire", "auteur_id": "a3"}]
        mongo_authors = [{"_id": "a3", "nom": "Julian Barnes"}]

        mock_mongodb = MagicMock()
        mock_mongodb.get_all_books.return_value = mongo_livres
        mock_mongodb.get_all_authors.return_value = mongo_authors
        mock_mongodb.get_expected_calibre_tags.return_value = {
            "ghi": ["lmelp_240922"],
        }

        mock_calibre = MagicMock()
        mock_calibre._available = True
        mock_calibre.get_all_books_with_tags.return_value = calibre_books

        from back_office_lmelp.services.calibre_matching_service import (
            CalibreMatchingService,
        )

        service = CalibreMatchingService(
            mock_calibre, mock_mongodb, virtual_library_tag="guillaume"
        )
        corrections = service.get_corrections()

        entry = corrections["missing_lmelp_tags"][0]
        # Order: virtual_library_tag, notable tags (babelio, lu, onkindle), lmelp_ tags
        assert entry["all_tags_to_copy"] == [
            "guillaume",
            "babelio",
            "lu",
            "lmelp_240922",
        ]

    def test_no_corrections_when_all_good(self):
        """Pas de corrections quand tout est cohérent."""
        calibre_books = [
            {
                "id": 42,
                "title": "Le Lambeau",
                "authors": ["Philippe Lançon"],
                "tags": ["lmelp_190101"],
                "read": True,
                "rating": 8,
            }
        ]
        mongo_livres = [{"_id": "abc", "titre": "Le Lambeau", "auteur_id": "a1"}]
        mongo_authors = [{"_id": "a1", "nom": "Philippe Lançon"}]

        service = self._make_service(calibre_books, mongo_livres, mongo_authors)
        corrections = service.get_corrections()

        assert len(corrections["author_corrections"]) == 0
        assert len(corrections["title_corrections"]) == 0
        assert len(corrections["missing_lmelp_tags"]) == 0


class TestCalibreMatchingServiceEnrichPalmares:
    """Tests pour l'enrichissement du palmarès."""

    def test_enrich_with_matched_book(self):
        """Enrichit un item palmarès avec les données Calibre."""
        from back_office_lmelp.services.calibre_matching_service import (
            CalibreMatchingService,
        )

        service = CalibreMatchingService.__new__(CalibreMatchingService)

        calibre_index = {
            "le lambeau": {
                "id": 42,
                "title": "Le Lambeau",
                "authors": ["Lançon, Philippe"],
                "read": True,
                "rating": 8,
                "tags": ["roman"],
            }
        }

        item = {"titre": "Le Lambeau", "auteur_nom": "Philippe Lançon"}
        service.enrich_palmares_item(item, calibre_index)

        assert item["calibre_in_library"] is True
        assert item["calibre_read"] is True
        assert item["calibre_rating"] == 8

    def test_enrich_unmatched_book(self):
        """Item palmarès non trouvé dans Calibre."""
        from back_office_lmelp.services.calibre_matching_service import (
            CalibreMatchingService,
        )

        service = CalibreMatchingService.__new__(CalibreMatchingService)

        calibre_index = {}

        item = {"titre": "Un livre inconnu", "auteur_nom": "Auteur Inconnu"}
        service.enrich_palmares_item(item, calibre_index)

        assert item["calibre_in_library"] is False
        assert item["calibre_read"] is None
        assert item["calibre_rating"] is None

    def test_enrich_rating_only_if_read(self):
        """La note Calibre n'est affichée que si le livre est lu."""
        from back_office_lmelp.services.calibre_matching_service import (
            CalibreMatchingService,
        )

        service = CalibreMatchingService.__new__(CalibreMatchingService)

        calibre_index = {
            "le lambeau": {
                "id": 42,
                "title": "Le Lambeau",
                "authors": ["Lançon, Philippe"],
                "read": False,
                "rating": 8,
                "tags": [],
            }
        }

        item = {"titre": "Le Lambeau", "auteur_nom": "Philippe Lançon"}
        service.enrich_palmares_item(item, calibre_index)

        assert item["calibre_in_library"] is True
        assert item["calibre_read"] is False
        assert item["calibre_rating"] is None  # Not shown because not read
