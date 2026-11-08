"""Versions des actions GitHub utilisées par les workflows (Issue #331).

Node.js 20 est retiré des runners GitHub : chaque action externe doit être
épinglée sur une majeure qui tourne sous Node 24. Avant d'ajouter une action,
vérifier le champ ``runs.using`` de son ``action.yml`` puis l'ajouter à
``MIN_MAJOR``.
"""

import re
from pathlib import Path

import yaml


WORKFLOWS_DIR = Path(__file__).parent.parent / ".github" / "workflows"

# Première majeure de chaque action qui tourne sous Node 24 (runs.using).
MIN_MAJOR = {
    "actions/checkout": 5,
    "actions/setup-python": 6,
    "actions/setup-node": 5,
    "astral-sh/setup-uv": 7,
    "actions/configure-pages": 6,
    "actions/upload-pages-artifact": 5,  # composite, utilise upload-artifact v7
    "actions/deploy-pages": 5,
    "docker/setup-buildx-action": 4,
    "docker/login-action": 4,
    "docker/metadata-action": 6,
    "docker/build-push-action": 7,
}

# Actions qui ne publient plus de tag flottant (`@v10` n'existe pas).
EXACT_TAG_ONLY = {"astral-sh/setup-uv"}

USES_RE = re.compile(r"^\s*-?\s*uses:\s*([^\s#]+)", re.MULTILINE)


def action_refs() -> list[tuple[str, str, str]]:
    """(fichier, action, référence) de chaque action externe des workflows."""
    refs = []
    for path in sorted(WORKFLOWS_DIR.glob("*.yml")):
        for uses in USES_RE.findall(path.read_text()):
            if uses.startswith("./"):
                continue  # workflow réutilisable local
            action, _, ref = uses.partition("@")
            refs.append((path.name, action, ref))
    return refs


def major(ref: str) -> int:
    match = re.fullmatch(r"v(\d+)(\.\d+){0,2}", ref)
    assert match, f"référence {ref!r} : attendu vN, vN.M ou vN.M.P"
    return int(match.group(1))


def workflow_steps(name: str) -> list[dict]:
    workflow = yaml.safe_load((WORKFLOWS_DIR / name).read_text())
    return [step for job in workflow["jobs"].values() for step in job.get("steps", [])]


def test_workflows_reference_actions():
    assert action_refs(), "aucune action trouvée : la collecte des `uses:` est cassée"


def test_every_action_has_a_known_minimum():
    unknown = sorted({a for _, a, _ in action_refs() if a not in MIN_MAJOR})
    assert not unknown, (
        f"actions sans version minimale : {unknown}. Vérifier leur version de "
        "Node (runs.using) puis les ajouter à MIN_MAJOR"
    )


def test_no_action_targets_node20():
    too_old = [
        f"{f}: {a}@{r} (minimum v{MIN_MAJOR[a]})"
        for f, a, r in action_refs()
        if a in MIN_MAJOR and major(r) < MIN_MAJOR[a]
    ]
    assert not too_old, "majeures sous Node 20 :\n" + "\n".join(too_old)


def test_exact_tag_for_actions_without_floating_tags():
    floating = [
        f"{f}: {a}@{r}"
        for f, a, r in action_refs()
        if a in EXACT_TAG_ONLY and not re.fullmatch(r"v\d+\.\d+\.\d+", r)
    ]
    assert not floating, "tag exact vX.Y.Z attendu :\n" + "\n".join(floating)


def test_same_action_uses_one_version_across_workflows():
    refs: dict[str, set[str]] = {}
    for _, a, r in action_refs():
        refs.setdefault(a, set()).add(r)
    mixed = {a: sorted(r) for a, r in refs.items() if len(r) > 1}
    assert not mixed, f"une même action sous plusieurs versions : {mixed}"


def test_codecov_upload_removed():
    """La couverture reste affichée dans le log (--cov-report=term-missing)."""
    assert not [a for _, a, _ in action_refs() if a.startswith("codecov/")]
    assert "--cov-report=xml" not in (WORKFLOWS_DIR / "ci-cd.yml").read_text()


def test_metadata_action_tags_contain_no_inline_comment():
    """metadata-action v6 garde un `#` en fin de ligne dans la valeur du tag."""
    with_comment = [
        line
        for step in workflow_steps("docker-publish.yml")
        if step.get("uses", "").startswith("docker/metadata-action@")
        for line in step["with"]["tags"].splitlines()
        if "#" in line
    ]
    assert not with_comment, "commentaire dans un tag :\n" + "\n".join(with_comment)
