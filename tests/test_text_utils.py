"""Tests unitaires pour normalize_for_cover_title_matching() (Issue #238)."""

from back_office_lmelp.utils.text_utils import normalize_for_cover_title_matching


class TestNormalizeForCoverTitleMatching:
    """Tests pour normalize_for_cover_title_matching()."""

    def test_basic_accent_normalization_preserved(self):
        """hérite des normalisations d'accents de normalize_for_matching."""
        assert normalize_for_cover_title_matching("Carrère") == "carrere"

    def test_ligature_normalization_preserved(self):
        """hérite de la normalisation des ligatures."""
        assert normalize_for_cover_title_matching("L'Œuvre") == "l'oeuvre"

    def test_hyphen_becomes_space(self):
        """tiret → espace (cas 'Faites-moi plaisir' vs 'Faites moi plaisir')."""
        assert (
            normalize_for_cover_title_matching("Faites-moi plaisir")
            == "faites moi plaisir"
        )

    def test_comma_stripped(self):
        """virgule supprimée (cas 'La Chair est triste, hélas')."""
        assert (
            normalize_for_cover_title_matching("La Chair est triste, hélas")
            == "la chair est triste helas"
        )

    def test_colon_stripped(self):
        """deux-points supprimés (cas '22 Mapesbury Road: Famille')."""
        assert (
            normalize_for_cover_title_matching("22 Mapesbury Road: Famille")
            == "22 mapesbury road famille"
        )

    def test_colon_with_spaces_stripped(self):
        """deux-points avec espaces supprimés (format Babelio ' : ')."""
        assert (
            normalize_for_cover_title_matching("22 Mapesbury Road : Famille")
            == "22 mapesbury road famille"
        )

    def test_guillemets_stripped(self):
        """guillemets français supprimés (« »)."""
        assert (
            normalize_for_cover_title_matching("Les « Penn Sardin »")
            == "les penn sardin"
        )

    def test_parentheses_stripped(self):
        """parenthèses supprimées (année entre parenthèses vs virgule)."""
        assert (
            normalize_for_cover_title_matching("Douarnenez (1924)") == "douarnenez 1924"
        )

    def test_trailing_period_stripped(self):
        """point final supprimé."""
        assert (
            normalize_for_cover_title_matching("Douarnenez, 1924.") == "douarnenez 1924"
        )

    def test_case1_penn_sardin_full(self):
        """cas réel Penn Sardin : guillemets + espacement deux-points + parenthèses."""
        expected = "Une belle grève de femmes: Retour sur la lutte des « Penn Sardin », Douarnenez, 1924."
        page = "Une belle grève de femmes : Retour sur la lutte des Penn Sardin, Douarnenez (1924)"
        assert normalize_for_cover_title_matching(
            expected
        ) == normalize_for_cover_title_matching(page)

    def test_case2_chair_triste_comma(self):
        """cas réel : virgule absente sur Babelio."""
        assert normalize_for_cover_title_matching(
            "La Chair est triste, hélas"
        ) == normalize_for_cover_title_matching("La chair est triste hélas")

    def test_case3_mapesbury_colon_spacing(self):
        """cas réel : espacement autour des deux-points."""
        assert normalize_for_cover_title_matching(
            "22 Mapesbury Road: Famille, mémoire et quête d'une terre promise"
        ) == normalize_for_cover_title_matching(
            "22 Mapesbury Road : Famille, mémoire et quête d'une terre promise"
        )

    def test_case5_faites_moi_hyphen(self):
        """cas réel : tiret vs espace."""
        assert normalize_for_cover_title_matching(
            "Faites-moi plaisir"
        ) == normalize_for_cover_title_matching("Faites moi plaisir")

    def test_true_mismatch_still_detected(self):
        """les vrais mauvais titres ne doivent pas matcher."""
        norm_expected = normalize_for_cover_title_matching("On ne sait rien de toi")
        norm_page = normalize_for_cover_title_matching("Fauves")
        assert norm_expected != norm_page
        assert norm_page not in norm_expected
        assert norm_expected not in norm_page
