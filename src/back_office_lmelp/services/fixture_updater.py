"""Service for updating test fixtures from captured API calls."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]


@dataclass
class FixtureUpdateResult:
    """Result of fixture update operation."""

    updated_files: list[str]
    added_cases: int
    updated_cases: int


class FixtureUpdaterService:
    """Service to update YAML fixtures from captured API calls."""

    def __init__(self, fixtures_dir: Path | None = None):
        """Initialize with fixtures directory."""
        if fixtures_dir is None:
            self.fixtures_dir = Path("frontend/tests/fixtures")
        else:
            self.fixtures_dir = fixtures_dir

    def update_from_captured_calls(
        self, captured_calls: list[dict[str, Any]]
    ) -> FixtureUpdateResult:
        """Met à jour les fixtures YAML depuis les appels capturés."""
        # Grouper par service
        by_service = self._group_calls_by_service(captured_calls)

        updated_files = []
        stats = {"added_cases": 0, "updated_cases": 0}

        for service_name, calls in by_service.items():
            if service_name == "babelioService":
                updated_files.extend(self._update_babelio_fixtures(calls, stats))
            elif service_name == "fuzzySearchService":
                updated_files.extend(self._update_fuzzy_fixtures(calls, stats))
            elif service_name == "biblioValidationService":
                updated_files.extend(
                    self._update_biblio_validation_fixtures(calls, stats)
                )

        return FixtureUpdateResult(
            updated_files=updated_files,
            added_cases=stats["added_cases"],
            updated_cases=stats["updated_cases"],
        )

    def _group_calls_by_service(
        self, captured_calls: list[dict[str, Any]]
    ) -> dict[str, list[dict[str, Any]]]:
        """Groupe les appels capturés par service."""
        by_service: dict[str, list[dict[str, Any]]] = {}
        for call in captured_calls:
            service = call["service"]
            if service not in by_service:
                by_service[service] = []
            by_service[service].append(call)
        return by_service

    def _update_babelio_fixtures(
        self, calls: list[dict[str, Any]], stats: dict[str, int]
    ) -> list[str]:
        """Met à jour babelio-author-cases.yml et babelio-book-cases.yml."""
        updated = []

        author_calls = [c for c in calls if c["method"] == "verifyAuthor"]
        book_calls = [c for c in calls if c["method"] == "verifyBook"]

        if author_calls and self._merge_into_yaml_file(
            "babelio-author-cases.yml", author_calls, stats
        ):
            updated.append("babelio-author-cases.yml")

        if book_calls and self._merge_into_yaml_file(
            "babelio-book-cases.yml", book_calls, stats
        ):
            updated.append("babelio-book-cases.yml")

        return updated

    def _update_fuzzy_fixtures(
        self, calls: list[dict[str, Any]], stats: dict[str, int]
    ) -> list[str]:
        """Met à jour fuzzy-search-cases.yml."""
        updated = []

        if calls and self._merge_into_yaml_file("fuzzy-search-cases.yml", calls, stats):
            updated.append("fuzzy-search-cases.yml")

        return updated

    def _update_biblio_validation_fixtures(
        self, calls: list[dict[str, Any]], stats: dict[str, int]
    ) -> list[str]:
        """Met à jour biblio-validation-cases.yml."""
        updated = []

        if calls and self._merge_into_yaml_file(
            "biblio-validation-cases.yml", calls, stats
        ):
            updated.append("biblio-validation-cases.yml")

        return updated

    def _merge_into_yaml_file(
        self, filename: str, new_calls: list[dict[str, Any]], stats: dict[str, int]
    ) -> bool:
        """Merge les nouveaux appels dans un fichier YAML existant."""
        filepath = self.fixtures_dir / filename

        # Créer le répertoire si nécessaire
        filepath.parent.mkdir(parents=True, exist_ok=True)

        # Charger existant
        existing_cases = []
        if filepath.exists():
            with open(filepath) as f:
                data = yaml.safe_load(f) or {}
                existing_cases = data.get("cases", [])

        # Merger sans doublons
        merged_cases = existing_cases.copy()
        changes_made = False

        for call in new_calls:
            fixture_case = self._call_to_fixture_case(call)
            signature = self._get_case_signature(fixture_case)

            # Chercher doublon
            existing_idx = None
            for i, existing in enumerate(merged_cases):
                if self._get_case_signature(existing) == signature:
                    existing_idx = i
                    break

            if existing_idx is not None:
                # Mettre à jour si différent
                if not self._cases_equivalent(merged_cases[existing_idx], fixture_case):
                    merged_cases[existing_idx] = fixture_case
                    stats["updated_cases"] += 1
                    changes_made = True
            else:
                # Nouveau cas
                merged_cases.append(fixture_case)
                stats["added_cases"] += 1
                changes_made = True

        # Sauvegarder si changements
        if changes_made:
            with open(filepath, "w") as f:
                yaml.dump(
                    {"cases": merged_cases},
                    f,
                    default_flow_style=False,
                    allow_unicode=True,
                    indent=2,
                )

        return bool(changes_made)

    def _call_to_fixture_case(self, call: dict[str, Any]) -> dict[str, Any]:
        """Convertit un appel capturé en cas de fixture."""
        return {
            "input": call["input"],
            "output": call["output"],
            "timestamp": call["timestamp"],
        }

    def _get_case_signature(self, case: dict[str, Any]) -> str:
        """Génère une signature unique pour un cas de fixture."""
        # Utilise l'input pour déterminer l'unicité
        input_data = case["input"]
        # Trier les clés pour avoir une signature consistante
        sorted_input = {k: input_data[k] for k in sorted(input_data.keys())}
        return str(sorted_input)

    def _cases_equivalent(self, case1: dict[str, Any], case2: dict[str, Any]) -> bool:
        """Vérifie si deux cas de fixture sont équivalents."""
        # Comparer input et output
        return bool(
            case1["input"] == case2["input"] and case1["output"] == case2["output"]
        )
