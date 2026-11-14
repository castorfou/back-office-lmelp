"""Tests de la réparation des tableaux markdown (Issue #347)."""

import pytest

from back_office_lmelp.utils.markdown_tables import ensure_table_separators


class TestEnsureTableSeparators:
    def test_inserts_separator_under_header(self):
        text = "## Titre\n\n| A|B|\n|1|2|\n"

        assert ensure_table_separators(text) == "## Titre\n\n| A|B|\n|---|---|\n|1|2|\n"

    def test_counts_empty_header_cells(self):
        text = "| A | | C |\n| 1 | | 3 |"

        assert ensure_table_separators(text).split("\n")[1] == "|---|---|---|"

    @pytest.mark.parametrize(
        "separator",
        ["|---|---|", "|--------|-------|", "| :--- | ---: |", "|:-:|:-:|", "---|---"],
    )
    def test_keeps_existing_separator(self, separator):
        text = f"| A | B |\n{separator}\n| 1 | 2 |"

        assert ensure_table_separators(text) == text

    def test_repairs_each_table(self):
        text = "| A|B|\n|1|2|\n\n## 2.\n\n| C|D|E|\n|1|2|3|"

        result = ensure_table_separators(text)

        assert result == (
            "| A|B|\n|---|---|\n|1|2|\n\n## 2.\n\n| C|D|E|\n|---|---|---|\n|1|2|3|"
        )

    def test_is_idempotent(self):
        text = "| A|B|\n|1|2|"

        once = ensure_table_separators(text)

        assert ensure_table_separators(once) == once

    def test_leaves_text_without_table_unchanged(self):
        text = "Réponse de l'IA tronquée. Veuillez réessayer."

        assert ensure_table_separators(text) == text
