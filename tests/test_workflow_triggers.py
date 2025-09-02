"""Tests pour vérifier les déclencheurs de workflows GitHub Actions."""

from pathlib import Path

import yaml


def test_ci_cd_workflow_triggers_on_feature_branches():
    """Test que le workflow CI/CD se déclenche sur les branches de feature."""
    workflow_path = Path(".github/workflows/ci-cd.yml")
    assert workflow_path.exists(), "Workflow CI/CD non trouvé"

    with open(workflow_path) as f:
        workflow = yaml.safe_load(f)

    # Vérifier la structure "on.push.branches" (PyYAML parse 'on:' comme True)
    on_section = workflow.get("on") or workflow.get(True)
    assert on_section is not None, "Section 'on' manquante"
    assert "push" in on_section, "Trigger 'push' manquant"

    push_branches = on_section["push"]["branches"]

    # Le workflow doit se déclencher sur toutes les branches
    assert push_branches == ["**"], (
        f"Branches push incorrectes: {push_branches}. Attendu: ['**']"
    )


def test_ci_cd_workflow_pr_triggers():
    """Test que le workflow CI/CD garde les bons triggers pour les PR."""
    workflow_path = Path(".github/workflows/ci-cd.yml")

    with open(workflow_path) as f:
        workflow = yaml.safe_load(f)

    # PyYAML parse 'on:' comme True
    on_section = workflow.get("on") or workflow.get(True)

    # Les PR doivent toujours cibler main uniquement
    pr_branches = on_section["pull_request"]["branches"]
    assert pr_branches == ["main"], f"PR branches incorrectes: {pr_branches}"


def test_docs_workflow_remains_selective():
    """Test que le workflow docs reste sélectif (pas besoin de tourner sur toutes les branches)."""
    workflow_path = Path(".github/workflows/docs.yml")

    with open(workflow_path) as f:
        workflow = yaml.safe_load(f)

    # PyYAML parse 'on:' comme True
    on_section = workflow.get("on") or workflow.get(True)

    # Le workflow docs doit avoir des paths filter
    assert "paths" in on_section["push"], "Filtre 'paths' manquant pour docs push"
    assert "paths" in on_section["pull_request"], "Filtre 'paths' manquant pour docs PR"

    # Et doit inclure les patterns de docs
    push_paths = on_section["push"]["paths"]
    assert "docs/**" in push_paths, "Pattern 'docs/**' manquant"
    assert "mkdocs.yml" in push_paths, "Pattern 'mkdocs.yml' manquant"


def test_deployment_jobs_only_on_main():
    """Test que les déploiements ne se font que sur main."""
    workflow_path = Path(".github/workflows/ci-cd.yml")

    with open(workflow_path) as f:
        workflow = yaml.safe_load(f)

    deploy_jobs = [
        job
        for job_name, job in workflow["jobs"].items()
        if job_name.startswith("deploy-")
    ]

    for job in deploy_jobs:
        # Tous les jobs de déploiement doivent être conditionnés sur main
        condition = job.get("if", "")
        assert "refs/heads/main" in condition, (
            f"Job de déploiement non conditionné sur main: {condition}"
        )


def test_concurrency_configuration():
    """Test que la configuration de concurrence permet plusieurs branches."""
    workflow_path = Path(".github/workflows/ci-cd.yml")

    with open(workflow_path) as f:
        workflow = yaml.safe_load(f)

    # Vérifier la concurrence par branche/ref
    concurrency = workflow.get("concurrency", {})
    assert "group" in concurrency, "Configuration de concurrence manquante"

    group = concurrency["group"]
    # Doit inclure github.ref pour isoler par branche
    assert "github.ref" in group, f"Concurrence mal configurée: {group}"

    # cancel-in-progress doit être true pour éviter les runs multiples
    assert concurrency.get("cancel-in-progress") is True, (
        "cancel-in-progress devrait être True"
    )
