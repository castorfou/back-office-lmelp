"""Unit tests for BooksExtractionService fallback parser (program vs coups de coeur)."""

from back_office_lmelp.services.books_extraction_service import (
    BooksExtractionService,
)


def test_parse_program_and_coups_de_coeur_tables():
    service = BooksExtractionService()

    # Simulate a summary with both sections
    summary = """
## 1. LIVRES DISCUTÉS AU PROGRAMME

| Auteur | Titre | Éditeur |
| --- | --- | --- |
| Auteur A | Livre A | Editeur A |

## 2. COUPS DE CŒUR DES CRITIQUES

| Auteur | Titre | Éditeur |
| --- | --- | --- |
| Auteur B | Livre B | Editeur B |
"""

    result = service._extract_books_from_summary_fallback(
        summary, "oid1", "Titre", "2025-01-01"
    )

    # We expect two books with flags set accordingly
    assert any(b for b in result if b["titre"] == "Livre A" and b["programme"] is True)
    assert any(
        b for b in result if b["titre"] == "Livre B" and b["coup_de_coeur"] is True
    )
