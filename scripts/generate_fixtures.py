#!/usr/bin/env python3
"""
Générateur automatique de fixtures BiblioValidation
Capture les vraies réponses API pour créer des fixtures test précises
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import click
import requests
import yaml


class FixtureGenerator:
    def __init__(self, backend_port: int):
        self.base_url = f"http://localhost:{backend_port}"
        self.session = requests.Session()
        self.session.timeout = 10

    def test_connection(self) -> bool:
        """Test la connectivité avec le backend"""
        try:
            response = self.session.get(f"{self.base_url}/")
            return response.status_code == 200
        except requests.RequestException:
            return False

    def call_fuzzy_search(
        self, episode_id: str, author: str, title: str
    ) -> dict[str, Any] | None:
        """Appelle l'API fuzzy search"""
        try:
            payload = {
                "episode_id": episode_id,
                "query_title": title,
                "query_author": author,
            }

            click.echo(f"🔍 Fuzzy search: {author} - {title}")
            response = self.session.post(
                f"{self.base_url}/api/fuzzy-search-episode", json=payload
            )

            if response.status_code == 200:
                data = response.json()
                click.echo(
                    f"   ✅ Found suggestions: {data.get('found_suggestions', False)}"
                )
                return data
            else:
                click.echo(f"   ❌ HTTP {response.status_code}: {response.text}")
                return None

        except requests.RequestException as e:
            click.echo(f"   ❌ Network error: {e}")
            return None

    def call_babelio_author(self, author: str) -> dict[str, Any] | None:
        """Appelle l'API Babelio pour vérifier l'auteur"""
        try:
            payload = {"type": "author", "name": author}

            click.echo(f"👤 Babelio author: {author}")
            response = self.session.post(
                f"{self.base_url}/api/verify-babelio", json=payload
            )

            if response.status_code == 200:
                data = response.json()
                click.echo(f"   ✅ Status: {data.get('status', 'unknown')}")
                if data.get("babelio_suggestion"):
                    click.echo(f"   💡 Suggestion: {data.get('babelio_suggestion')}")
                return data
            else:
                click.echo(f"   ❌ HTTP {response.status_code}: {response.text}")
                return None

        except requests.RequestException as e:
            click.echo(f"   ❌ Network error: {e}")
            return None

    def call_babelio_book(self, title: str, author: str) -> dict[str, Any] | None:
        """Appelle l'API Babelio pour vérifier le livre"""
        try:
            payload = {"type": "book", "title": title, "author": author}

            click.echo(f"📖 Babelio book: {title} + {author}")
            response = self.session.post(
                f"{self.base_url}/api/verify-babelio", json=payload
            )

            if response.status_code == 200:
                data = response.json()
                click.echo(f"   ✅ Status: {data.get('status', 'unknown')}")
                if data.get("babelio_suggestion_title"):
                    click.echo(f"   💡 Title: {data.get('babelio_suggestion_title')}")
                if data.get("babelio_suggestion_author"):
                    click.echo(f"   💡 Author: {data.get('babelio_suggestion_author')}")
                return data
            else:
                click.echo(f"   ❌ HTTP {response.status_code}: {response.text}")
                return None

        except requests.RequestException as e:
            click.echo(f"   ❌ Network error: {e}")
            return None


class FixtureUpdater:
    def __init__(self):
        self.fixtures_dir = Path("frontend/tests/fixtures")
        self.fixtures_dir.mkdir(parents=True, exist_ok=True)

    def load_fixture_file(self, filename: str) -> dict[str, Any]:
        """Charge un fichier fixture YAML"""
        filepath = self.fixtures_dir / filename
        if filepath.exists():
            with open(filepath, encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {"cases": []}

    def save_fixture_file(self, filename: str, data: dict[str, Any]):
        """Sauvegarde un fichier fixture YAML"""
        filepath = self.fixtures_dir / filename

        # Backup si le fichier existe
        if filepath.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = filepath.with_suffix(f".backup_{timestamp}.yml")
            filepath.rename(backup_path)
            click.echo(f"📁 Backup: {backup_path.name}")

        with open(filepath, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, indent=2)

        click.echo(f"💾 Saved: {filepath.name}")

    def add_fuzzy_search_case(
        self,
        name: str,
        episode_id: str,
        author: str,
        title: str,
        api_response: dict[str, Any],
    ):
        """Ajoute un cas au fichier fuzzy-search-cases.yml"""
        fixtures = self.load_fixture_file("fuzzy-search-cases.yml")

        new_case = {
            "name": name,
            "input": {
                "episode_id": episode_id,
                "query_author": author,
                "query_title": title,
            },
            "output": {
                "found_suggestions": api_response.get("found_suggestions", False),
                "title_matches": api_response.get("title_matches", []),
                "author_matches": api_response.get("author_matches", []),
            },
        }

        # Remplacer si existe, sinon ajouter
        existing_index = self._find_case_index(fixtures["cases"], name)
        if existing_index >= 0:
            fixtures["cases"][existing_index] = new_case
            click.echo(f"🔄 Updated existing case: {name}")
        else:
            fixtures["cases"].append(new_case)
            click.echo(f"➕ Added new case: {name}")

        self.save_fixture_file("fuzzy-search-cases.yml", fixtures)

    def add_babelio_author_case(
        self, name: str, author: str, api_response: dict[str, Any]
    ):
        """Ajoute un cas au fichier babelio-author-cases.yml"""
        fixtures = self.load_fixture_file("babelio-author-cases.yml")

        new_case = {
            "name": name,
            "input": {"name": author},
            "output": {
                "status": api_response.get("status", "not_found"),
                "original": api_response.get("original", author),
                "babelio_suggestion": api_response.get("babelio_suggestion"),
                "confidence_score": api_response.get("confidence_score", 0),
            },
        }

        # Remplacer si existe, sinon ajouter
        existing_index = self._find_case_index(fixtures["cases"], name)
        if existing_index >= 0:
            fixtures["cases"][existing_index] = new_case
            click.echo(f"🔄 Updated existing case: {name}")
        else:
            fixtures["cases"].append(new_case)
            click.echo(f"➕ Added new case: {name}")

        self.save_fixture_file("babelio-author-cases.yml", fixtures)

    def add_babelio_book_case(
        self, name: str, title: str, author: str, api_response: dict[str, Any]
    ):
        """Ajoute un cas au fichier babelio-book-cases.yml"""
        fixtures = self.load_fixture_file("babelio-book-cases.yml")

        new_case = {
            "name": name,
            "input": {"title": title, "author": author},
            "output": {
                "status": api_response.get("status", "not_found"),
                "original_title": api_response.get("original_title", title),
                "original_author": api_response.get("original_author", author),
                "babelio_suggestion_title": api_response.get(
                    "babelio_suggestion_title"
                ),
                "babelio_suggestion_author": api_response.get(
                    "babelio_suggestion_author"
                ),
                "confidence_score": api_response.get("confidence_score", 0),
            },
        }

        # Remplacer si existe, sinon ajouter
        existing_index = self._find_case_index(fixtures["cases"], name)
        if existing_index >= 0:
            fixtures["cases"][existing_index] = new_case
            click.echo(f"🔄 Updated existing case: {name}")
        else:
            fixtures["cases"].append(new_case)
            click.echo(f"➕ Added new case: {name}")

        self.save_fixture_file("babelio-book-cases.yml", fixtures)

    def _find_case_index(self, cases: list, name: str) -> int:
        """Trouve l'index d'un cas par nom"""
        for i, case in enumerate(cases):
            if case.get("name") == name:
                return i
        return -1


@click.command()
def main():
    """Générateur interactif de fixtures BiblioValidation"""

    click.echo("🎯 Générateur automatique de fixtures BiblioValidation\n")

    # 1. Demander le port backend
    backend_port = click.prompt("Port du backend (ex: 54322)", type=int, default=54322)

    # Test connexion
    generator = FixtureGenerator(backend_port)
    if not generator.test_connection():
        click.echo(
            f"❌ Impossible de se connecter au backend sur le port {backend_port}"
        )
        click.echo("Vérifiez que le backend est démarré et accessible.")
        sys.exit(1)

    click.echo(f"✅ Backend connecté sur le port {backend_port}\n")

    # 2. Demander les paramètres du cas de test
    episode_id = click.prompt("Episode ID (ex: 68bd9ed3582cf994fb66f1d6)")
    author = click.prompt("Auteur (tel qu'affiché dans /livres-auteurs)")
    title = click.prompt("Titre (tel qu'affiché dans /livres-auteurs)")

    # Générer un nom de cas unique
    case_name = f"{author} - {title}"

    click.echo(f"\n🚀 Génération des fixtures pour: {case_name}\n")

    # 3. Appels API automatiques
    updater = FixtureUpdater()

    # Fuzzy search
    fuzzy_result = generator.call_fuzzy_search(episode_id, author, title)
    if fuzzy_result:
        updater.add_fuzzy_search_case(
            case_name, episode_id, author, title, fuzzy_result
        )

    # Babelio author
    author_result = generator.call_babelio_author(author)
    if author_result:
        author_case_name = f"{author} - API response"
        updater.add_babelio_author_case(author_case_name, author, author_result)

    # Babelio book
    book_result = generator.call_babelio_book(title, author)
    if book_result:
        book_case_name = f"{title} + {author} - API response"
        updater.add_babelio_book_case(book_case_name, title, author, book_result)

    click.echo(f"\n🎉 Génération terminée pour: {case_name}")
    click.echo("Les fixtures ont été mises à jour avec les vraies données API.")
    click.echo("\n💡 Prochaines étapes:")
    click.echo("1. Lancer les tests pour voir les nouveaux échecs")
    click.echo("2. Ajuster l'algorithme BiblioValidationService")
    click.echo("3. Relancer les tests jusqu'à ce qu'ils passent")


if __name__ == "__main__":
    main()
