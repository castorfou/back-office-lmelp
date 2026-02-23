# Issue #229 — Fix CI/CD : gcc manquant dans le Docker builder

## Problème

Le build Docker CI/CD échouait avec :
```
error: command 'gcc' failed: No such file or directory
```

**Cause racine** : `scikit-surprise==1.1.4` est une dépendance principale du projet (dans `pyproject.toml`) mais :
1. Il n'existe **pas de wheel binaire** pour ce package (sdist uniquement → compilation C nécessaire)
2. Le builder stage Docker utilise `python:3.11-slim` → pas de `gcc` installé par défaut
3. `scikit-surprise` n'est utilisé que dans des notebooks d'exploration (`notebooks/spike_surprise_cf.ipynb`, `notebooks/spike_svd_latent_cf.ipynb`), **pas dans le code production**

## Solution appliquée (Option B — Quick fix Dockerfile)

Ajout de `gcc` et `python3-dev` dans le **builder stage uniquement** du Dockerfile multi-stage.

Fichier modifié : `docker/build/backend/Dockerfile`

```dockerfile
# Install build tools needed for packages requiring C compilation (e.g. scikit-surprise)
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc python3-dev && \
    rm -rf /var/lib/apt/lists/*
```

Inséré **après** l'installation de uv et **avant** `WORKDIR /app`.

**Pourquoi c'est sûr** : Multi-stage build → gcc est dans le builder stage UNIQUEMENT. Le stage runtime (`python:3.11-slim`) reçoit seulement le `.venv` compilé, pas les outils de build. L'image finale reste légère.

## Option non choisie (Option A)

Déplacer `scikit-surprise` dans un groupe `[project.optional-dependencies]` (ex: `notebooks`). Cette solution est plus propre architecturalement mais l'utilisateur a préféré le fix Dockerfile pour sa simplicité.

## Pattern à retenir

Quand un package Python nécessite compilation C et que le Dockerfile builder utilise `*-slim` :
→ Ajouter `gcc python3-dev` dans le builder stage (pas le runtime stage).

## Tests

- 1249 tests backend ✅
- 594 tests frontend ✅
- pre-commit ✅
- Vérification CI/CD via `gh run watch` après push
