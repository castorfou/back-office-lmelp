"""Tests pour summary_updater - Remplacement du publisher (Issue #85).

Tests unitaires pour vérifier que la fonction replace_book_in_summary()
peut aussi remplacer l'éditeur dans le tableau markdown lors de l'enrichissement Babelio.
"""

from back_office_lmelp.utils.summary_updater import replace_book_in_summary


class TestReplaceBookInSummaryWithPublisher:
    """Tests pour le remplacement d'auteur, titre ET éditeur."""

    def test_should_replace_author_title_and_publisher(self):
        """GIVEN: Livre avec auteur/titre/éditeur incorrect dans le summary
        WHEN: replace_book_in_summary() est appelée avec les trois paramètres
        THEN: Les trois champs doivent être remplacés dans la même ligne"""

        summary = """## 1. LIVRES DISCUTÉS AU PROGRAMME du 01 jan. 2025

| Auteur | Titre | Éditeur | Avis détaillés |
|--------|-------|---------|----------------|
| Emmanuel Carrere | Kolkhoze | POL | Excellente critique |
"""

        # Appel avec éditeur en paramètre
        result = replace_book_in_summary(
            summary=summary,
            original_author="Emmanuel Carrere",
            original_title="Kolkhoze",
            corrected_author="Emmanuel Carrère",  # Accent corrigé
            corrected_title="Kolkhoze",
            original_publisher="POL",  # Éditeur original
            corrected_publisher="P.O.L.",  # Éditeur corrigé
        )

        # Vérification
        assert "Emmanuel Carrère" in result
        assert "P.O.L." in result
        assert "POL" not in result  # L'ancien éditeur ne doit plus être là
        # Vérifier que la ligne est bien formée
        assert "| Emmanuel Carrère | Kolkhoze | P.O.L. |" in result

    def test_should_replace_only_publisher_if_provided(self):
        """GIVEN: Livre avec éditeur incorrect
        WHEN: replace_book_in_summary() est appelée avec publisher en paramètre
        THEN: Seul l'éditeur doit être remplacé, auteur/titre inchangés"""

        summary = """## 1. LIVRES DISCUTÉS AU PROGRAMME du 01 jan. 2025

| Auteur | Titre | Éditeur | Avis |
|--------|-------|---------|------|
| Emmanuel Carrère | Kolkhoze | POL | Bon |
"""

        # Appel avec publisher uniquement (auteur et titre restent identiques)
        result = replace_book_in_summary(
            summary=summary,
            original_author="Emmanuel Carrère",
            original_title="Kolkhoze",
            corrected_author="Emmanuel Carrère",
            corrected_title="Kolkhoze",
            original_publisher="POL",
            corrected_publisher="P.O.L.",
        )

        assert "| Emmanuel Carrère | Kolkhoze | P.O.L. |" in result
        assert "POL" not in result

    def test_should_not_replace_if_original_author_title_mismatch(self):
        """GIVEN: Recherche d'auteur/titre qui n'existent pas
        WHEN: replace_book_in_summary() est appelée
        THEN: Le summary doit rester inchangé"""

        summary = """## 1. LIVRES DISCUTÉS AU PROGRAMME du 01 jan. 2025

| Auteur | Titre | Éditeur | Avis |
|--------|-------|---------|------|
| Emmanuel Carrère | Kolkhoze | POL | Bon |
"""

        result = replace_book_in_summary(
            summary=summary,
            original_author="Unknown Author",  # N'existe pas
            original_title="Kolkhoze",
            corrected_author="Unknown Author",
            corrected_title="Kolkhoze",
            original_publisher="POL",
            corrected_publisher="P.O.L.",
        )

        # Le summary doit rester inchangé
        assert result == summary
        assert "POL" in result  # L'ancien éditeur doit rester

    def test_should_handle_special_chars_in_publisher(self):
        """GIVEN: Éditeur avec caractères spéciaux (accents, apostrophes)
        WHEN: replace_book_in_summary() est appelée
        THEN: L'éditeur doit être remplacé correctement"""

        summary = """## 1. LIVRES DISCUTÉS AU PROGRAMME du 01 jan. 2025

| Auteur | Titre | Éditeur | Avis |
|--------|-------|---------|------|
| Alain Mabancou | Ramsès | Seuil | Très bon |
"""

        result = replace_book_in_summary(
            summary=summary,
            original_author="Alain Mabancou",
            original_title="Ramsès",
            corrected_author="Alain Mabanckou",
            corrected_title="Ramsès",
            original_publisher="Seuil",
            corrected_publisher="Éditions de Minuit",
        )

        assert "Éditions de Minuit" in result
        assert "| Alain Mabanckou | Ramsès | Éditions de Minuit |" in result

    def test_should_preserve_other_lines(self):
        """GIVEN: Summary avec plusieurs livres
        WHEN: replace_book_in_summary() remplace un seul livre
        THEN: Les autres lignes doivent rester inchangées"""

        summary = """## 1. LIVRES DISCUTÉS AU PROGRAMME du 01 jan. 2025

| Auteur | Titre | Éditeur | Avis |
|--------|-------|---------|------|
| Emmanuel Carrère | Kolkhoze | POL | Excellente |
| Alain Mabancou | Ramsès | Seuil | Très bon |
"""

        result = replace_book_in_summary(
            summary=summary,
            original_author="Emmanuel Carrère",
            original_title="Kolkhoze",
            corrected_author="Emmanuel Carrère",
            corrected_title="Kolkhoze",
            original_publisher="POL",
            corrected_publisher="P.O.L.",
        )

        # Le premier livre doit être corrigé
        assert "| Emmanuel Carrère | Kolkhoze | P.O.L. |" in result
        # Le deuxième livre doit rester inchangé
        assert "| Alain Mabancou | Ramsès | Seuil |" in result


class TestReplaceBookInSummaryBackwardCompatibility:
    """Tests pour s'assurer que l'extension ne casse pas la fonction existante."""

    def test_should_work_without_publisher_parameter(self):
        """GIVEN: Fonction appelée sans publisher (backward compatibility)
        WHEN: replace_book_in_summary() remplace auteur et titre
        THEN: Doit fonctionner comme avant"""

        summary = """## 1. LIVRES DISCUTÉS AU PROGRAMME du 01 jan. 2025

| Auteur | Titre | Éditeur | Avis |
|--------|-------|---------|------|
| Alain Mabancou | Ramsès | Seuil | Bon |
"""

        # Appel SANS publisher (comme avant)
        result = replace_book_in_summary(
            summary=summary,
            original_author="Alain Mabancou",
            original_title="Ramsès",
            corrected_author="Alain Mabanckou",
            corrected_title="Ramsès de Paris",
        )

        assert "Alain Mabanckou" in result
        assert "Ramsès de Paris" in result
        assert "Alain Mabancou" not in result
