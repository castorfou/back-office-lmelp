#!/usr/bin/env python3
"""Faits pour la skill /cruft-update : catégories, rejets, CHANGELOG du template.

Seule source des catégories de fichiers (ADR 0003). Bibliothèque standard
uniquement : le script tourne avant que le venv du projet soit à jour.

    template_update.py categorie CHEMIN
    template_update.py rejets
    template_update.py changelog AVANT APRES [--template-path DIR]
"""

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path


# Préfixes de dossiers (finissant par /) ou fichiers exacts, par catégorie.
# Le premier motif qui correspond l'emporte : du plus précis au plus général.
CATEGORIES: list[tuple[str, tuple[str, ...]]] = [
    (
        "template",
        (
            ".devcontainer/",
            ".github/workflows/",
            ".claude/commands/",
            ".claude/skills/",
            ".pre-commit-config.yaml",
            "docs/cheatsheets/",
            "TEMPLATE_VERSION",
        ),
    ),
    (
        "mixte",
        (
            "pyproject.toml",
            "uv.lock",
            "mkdocs.yml",
            "CLAUDE.md",
            ".gitignore",
            "docs/agents/",
            ".claude/settings.json",
        ),
    ),
    (
        "projet",
        (
            "src/",
            "tests/",
            "notebooks/",
            "data/",
            "README.md",
            "docs/user/",
            "docs/dev/",
            "docs/claude/memory/",
        ),
    ),
]

CONFLICT_MARKERS = r"^(<<<<<<<|>>>>>>>)( |$)"


def categorie(path: str) -> str:
    """Catégorie d'un chemin relatif à la racine ; un `.rej` suit son fichier."""
    path = path.removeprefix("./").removesuffix(".rej")
    for category, patterns in CATEGORIES:
        for pattern in patterns:
            if path == pattern or (pattern.endswith("/") and path.startswith(pattern)):
                return category
    return "inconnu"


def git(project: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=project, check=False, capture_output=True, text=True
    ).stdout


def rejets(project: Path) -> list[tuple[str, str, str]]:
    """Rejets laissés par cruft : fichiers `.rej` et fichiers en conflit."""
    found = [
        ("rej", path.relative_to(project).as_posix())
        for path in sorted(project.rglob("*.rej"))
        if ".git" not in path.relative_to(project).parts
    ]
    unmerged = {
        line.split("\t", 1)[1] for line in git(project, "ls-files", "-u").splitlines()
    }
    marked = set(git(project, "grep", "-l", "-E", CONFLICT_MARKERS).splitlines())
    found += [("conflit", path) for path in sorted(unmerged | marked)]
    return [(categorie(path), form, path) for form, path in found]


def added_lines(template: Path, before: str, after: str) -> list[str]:
    diff = subprocess.run(
        ["git", "diff", before, after, "--", "CHANGELOG.md"],
        cwd=template,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return [
        line[1:]
        for line in diff.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    ]


def changelog(
    project: Path, before: str, after: str, template_path: Path | None
) -> list[str]:
    """Lignes ajoutées au CHANGELOG du template entre deux de ses commits."""
    if template_path is not None:
        return added_lines(template_path, before, after)
    url = json.loads((project / ".cruft.json").read_text())["template"]
    with tempfile.TemporaryDirectory() as tmp:
        clone = Path(tmp) / "template"
        subprocess.run(
            [
                "git",
                "clone",
                "-q",
                "--filter=blob:none",
                "--no-checkout",
                url,
                str(clone),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        return added_lines(clone, before, after)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--project-dir", type=Path, default=Path.cwd())
    commands = parser.add_subparsers(dest="command", required=True)
    cat = commands.add_parser("categorie", help="catégorie d'un fichier")
    cat.add_argument("path")
    commands.add_parser("rejets", help="rejets restants, avec leur catégorie")
    log = commands.add_parser(
        "changelog", help="lignes ajoutées au CHANGELOG du template"
    )
    log.add_argument("before")
    log.add_argument("after")
    log.add_argument("--template-path", type=Path)
    args = parser.parse_args()

    if args.command == "categorie":
        print(categorie(args.path))
    elif args.command == "rejets":
        for row in rejets(args.project_dir):
            print("\t".join(row))
    else:
        try:
            lines = changelog(
                args.project_dir, args.before, args.after, args.template_path
            )
        except (subprocess.CalledProcessError, OSError, KeyError) as error:
            print(
                f"Lecture du CHANGELOG du template impossible : {error}",
                file=sys.stderr,
            )
            return 1
        print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
