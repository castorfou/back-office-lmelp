# Issue #205 — Afficher un numéro de version

## Contexte

L'utilisateur déploie sur un NAS avec auto-upgrade (Watchtower). Sans releases ni tags GitHub, il n'avait aucun moyen de savoir quelle version était déployée. Solution : afficher le commit hash git comme identifiant de version, avec un changelog complet des commits référençant des issues/PRs.

## Architecture implémentée

Architecture à 3 couches :

1. **CI/CD** : Script `scripts/generate-changelog.sh` génère `build_info.json` + `changelog.json` au build Docker
2. **Backend** : Endpoints `GET /api/version` et `GET /api/changelog`, données cached au démarrage
3. **Frontend** : Footer discret sur Dashboard → page dédiée `/about` avec changelog complet

## Fichiers créés

- `src/back_office_lmelp/utils/build_info.py` — Utilitaire avec fallback 3 niveaux :
  - Priorité 1 : `build_info.json` à `/app/build_info.json` (Docker production)
  - Priorité 2 : `subprocess git` (dev local)
  - Priorité 3 : valeurs "unknown" (fallback)
- `tests/test_build_info.py` — 8 tests unitaires (build info + changelog)
- `tests/test_version_endpoint.py` — 7 tests endpoints `/api/version` et `/api/changelog`
- `frontend/src/views/AboutPage.vue` — Page About avec version courante + tableau changelog
- `frontend/src/views/__tests__/AboutPage.spec.js` — 5 tests frontend
- `scripts/generate-changelog.sh` — Génère les JSON au build CI (utilise `git log --first-parent`)

## Fichiers modifiés

- `src/back_office_lmelp/app.py` — Import `get_build_info`/`get_changelog`, cached `_build_info`/`_changelog`, 2 endpoints, root `/` mis à jour avec commit_short dynamique, `FastAPI(version=...)` dynamique
- `src/back_office_lmelp/utils/startup_logging.py` — Log version au démarrage (import local `from .build_info import get_build_info`)
- `tests/test_api_routes.py:42` — Assertion `== "0.1.0"` → `"version" in data`
- `docker/build/backend/Dockerfile` — `COPY build_info.json changelog.json /app/`
- `.github/workflows/docker-publish.yml` — Étape `generate-changelog.sh` + `fetch-depth: 0`
- `frontend/src/router/index.js` — Route `/about` (lazy-loaded)
- `frontend/src/views/Dashboard.vue` — Footer version avec `router-link` vers `/about`, computed `formattedCommitDate`/`versionTooltip`, méthode `loadVersionInfo()` dans `Promise.all()`
- `.gitignore` — Exclusion `build_info.json` et `changelog.json`

## Points techniques notables

### Changelog filtré
- Seuls les commits first-parent référençant `#[0-9]+` sont inclus (~106 sur 314 commits totaux)
- Format : `{hash, date, message}` — les `#XXX` sont rendus comme liens cliquables vers les issues GitHub

### Sécurité XSS dans AboutPage
- `linkifyIssues()` échappe le HTML (`&amp;`, `&lt;`, `&gt;`) avant d'injecter les liens `<a>` pour les numéros d'issues

### CI/CD - fetch-depth: 0
- Le `actions/checkout@v4` dans `docker-publish.yml` utilise maintenant `fetch-depth: 0` pour le build backend, nécessaire pour que `git log --first-parent` ait l'historique complet

### Simulation Docker testée
- Copié les JSON dans `/app/` pour vérifier que `get_build_info()` retourne `environment: "docker"` — validé

## Tests

- 20 nouveaux tests (8 build_info + 7 endpoint + 5 frontend)
- Tous les tests existants passent (1201 backend, 546 frontend)
- Pre-commit clean (ruff, mypy, detect-secrets)
