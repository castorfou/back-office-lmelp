# Issue #331 — Actions GitHub sous Node 24 (ci-cd.yml, docker-publish.yml)

## Problème

Les runs CI affichaient « Node.js 20 is deprecated » : `ci-cd.yml` et
`docker-publish.yml` épinglaient des majeures Node 20 (`checkout@v4`,
`setup-python@v5`, `setup-uv@v2`, `setup-node@v3`, `codecov-action@v4`,
`docker/*@v3/v5`). Ces deux workflows sont propres au projet : `cruft update`
n'y touche pas (seul `docs.yml` vient du template PyFoundry, déjà à jour).

## Décisions (avec l'utilisateur)

- **Codecov retiré** (comme PyFoundry #126) : étape d'upload et
  `--cov-report=xml` supprimés. La couverture reste dans le log
  (`--cov-report=term-missing`). À noter : l'upload marchait en tokenless
  (aucun secret `CODECOV_TOKEN`, dépôt public), mais personne ne le consultait.
- **Pas de Dependabot** : une PR Dependabot sur `docs.yml` (fichier du template)
  créerait des rejets au prochain `cruft update`. Le test garde-fou suffit.

## Versions retenues

| Action | Avant | Après | 1re majeure Node 24 |
|---|---|---|---|
| actions/checkout | v4 | v7 | 5 |
| actions/setup-python | v5 | v7 | 6 |
| astral-sh/setup-uv | v2 | v10.3.3 | 7 |
| actions/setup-node | v3 | v7 | 5 |
| docker/setup-buildx-action | v3 | v4 | 4 |
| docker/login-action | v3 | v4 | 4 |
| docker/metadata-action | v5 | v6 | 6 |
| docker/build-push-action | v5 | v7 | 7 |

Méthode de vérification du runtime : lire `runs.using` dans l'`action.yml` du tag
(`gh api "repos/<owner>/<action>/contents/action.yml?ref=<tag>"`).

## Points saillants / pièges

- **setup-uv ne publie plus de tag flottant depuis v8** : `@v10` n'existe pas,
  il faut un tag exact (`v10.3.3`). Le test l'impose (`EXACT_TAG_ONLY`).
- **metadata-action v6 garde un `#` en fin de ligne dans la valeur** d'une liste
  (`tags: |`). La ligne `type=raw,value=latest,enable=${{ ... }} # pragma: allowlist secret`
  aurait produit un `enable` invalide → tag `latest` cassé. Le `# pragma` a été
  retiré de ces lignes ; detect-secrets ne les flagge pas (les `# pragma` sur les
  lignes `tags: |` et dans la liste `branches:` restent, ils sont hors valeur).
- Breaking changes relus sans impact : setup-uv (cache `auto` par défaut, venv
  non activé automatiquement — on utilise `uv sync`/`uv run`), setup-node v5/v6
  (cache auto via `packageManager`, absent ; `cache: 'npm'` explicite conservé),
  setup-python v7 (retrait de `pip-install`), build-push v6 (build summary par
  défaut), v7 (retrait d'env `DOCKER_BUILD_*` non utilisées).
- `docker-publish.yml` ne tourne pas sur une PR : à vérifier sur `main` après merge.

## Fichiers modifiés

- `.github/workflows/ci-cd.yml` : bumps, retrait Codecov.
- `.github/workflows/docker-publish.yml` : bumps, `# pragma` retiré des tags.
- `tests/test_github_actions.py` (nouveau, adapté de PyFoundry) : collecte des
  `uses:` des workflows, `MIN_MAJOR` par action (action inconnue refusée),
  aucune majeure sous Node 20, tag exact pour setup-uv, une version par action
  dans tout le dépôt, pas de Codecov, pas de `#` dans les tags metadata-action.

## Pour ajouter une action à un workflow

Vérifier son `runs.using` (node24 ou composite), puis l'ajouter à `MIN_MAJOR`
dans `tests/test_github_actions.py`, sinon `test_every_action_has_a_known_minimum`
échoue.
