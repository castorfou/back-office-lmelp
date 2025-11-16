# Issue #101 - Refactoring Docker : Séparation Build/Deployment

**Date**: 2025-11-16
**Issue**: [#101 - Refactoring Docker](https://github.com/castorfou/back-office-lmelp/issues/101)
**Branch**: `101-refactoring-docker`
**Commits**: 3 commits (9f365fc, adbcd49, 1620295)

## 🎯 Objectif

Réorganiser la structure Docker pour séparer clairement :
- Les fichiers de **build** (utilisés par CI/CD GitHub Actions)
- Les fichiers de **deployment** (utilisés pour déploiement local/NAS Portainer)

Cette séparation améliore la clarté, la maintenabilité et la compréhension de la structure du projet.

## 📁 Nouvelle Structure

```
docker/
├── README.md                    # Documentation de la structure
├── build/                       # Fichiers de build (CI/CD)
│   ├── backend/
│   │   └── Dockerfile
│   └── frontend/
│       ├── Dockerfile
│       └── nginx.conf
└── deployment/                  # Fichiers de déploiement (local/NAS)
    ├── docker-compose.yml
    ├── .env.template
    └── README.md
```

### Ancienne structure (supprimée)

```
docker/
├── backend/Dockerfile           # → docker/build/backend/
├── frontend/Dockerfile          # → docker/build/frontend/
├── frontend/nginx.conf          # → docker/build/frontend/
├── docker-compose.yml           # Supprimé (obsolète)
├── docker-compose.dev.yml       # Supprimé (obsolète)
├── docker-compose.prod.yml      # Supprimé (obsolète)
├── .env.template                # Supprimé (dupliqué)
└── scripts/                     # Supprimé (obsolète)
    ├── start.sh
    ├── stop.sh
    ├── update.sh
    ├── test-build.sh
    └── logs.sh

deployment/                      # → docker/deployment/
├── docker-compose.yml
├── .env.template
└── README.md
```

## 🔄 Détail des 3 Commits

### Commit 1 : Refactoring principal (9f365fc)

**Message** : `refactor(docker): restructure Docker files for build/deployment separation`

**Modifications** : 22 fichiers changés, 77 insertions(+), 789 deletions(-)

#### Fichiers déplacés (renamed)
1. `docker/backend/Dockerfile` → `docker/build/backend/Dockerfile`
2. `docker/frontend/Dockerfile` → `docker/build/frontend/Dockerfile`
3. `docker/frontend/nginx.conf` → `docker/build/frontend/nginx.conf`
4. `deployment/.env.template` → `docker/deployment/.env.template`
5. `deployment/README.md` → `docker/deployment/README.md`
6. `deployment/docker-compose.yml` → `docker/deployment/docker-compose.yml`

#### Fichiers supprimés (deleted)
1. `docker/.env.template` (dupliqué avec deployment/)
2. `docker/docker-compose.yml` (obsolète)
3. `docker/docker-compose.dev.yml` (obsolète)
4. `docker/docker-compose.prod.yml` (obsolète)
5. `docker/scripts/logs.sh`
6. `docker/scripts/start.sh`
7. `docker/scripts/stop.sh`
8. `docker/scripts/test-build.sh`
9. `docker/scripts/update.sh`

#### Fichiers modifiés

**`.github/workflows/docker-publish.yml`**
- Ligne 73 : `file: ./docker/backend/Dockerfile` → `file: ./docker/build/backend/Dockerfile`
- Ligne 133 : `file: ./docker/frontend/Dockerfile` → `file: ./docker/build/frontend/Dockerfile`
- Lignes 201-202 : Instructions de déploiement mises à jour
  ```yaml
  echo "cd docker/deployment/" >> $GITHUB_STEP_SUMMARY
  echo "docker compose pull && docker compose up -d" >> $GITHUB_STEP_SUMMARY
  ```

**`README.md`**
```bash
# Avant (lignes 383-386)
cd docker
docker-compose -f docker-compose.prod.yml up -d

# Après (lignes 385-386)
cd docker/deployment
docker compose up -d
```

**`docker/README.md`** (réécrit complètement)
- Avant : 357 lignes (guide de déploiement détaillé)
- Après : ~74 lignes (documentation de structure)
- Nouveau contenu :
  - Explication de la structure build/ vs deployment/
  - Liens vers deployment/README.md pour le guide complet
  - Exemples d'utilisation rapide

**`docs/deployment/docker-setup.md`**
- 4 occurrences de chemins mises à jour :
  - `docker/backend/Dockerfile` → `docker/build/backend/Dockerfile`
  - `docker/frontend/Dockerfile` → `docker/build/frontend/Dockerfile`
  - `docker/docker-compose.prod.yml` → `docker/deployment/docker-compose.yml`

**`docs/deployment/portainer-guide.md`**
- Ligne 39 : Mise à jour de la référence au docker-compose
  ```markdown
  Copier le contenu de `docker/deployment/docker-compose.yml`
  ```

**`docs/deployment/testing-guide.md`**
- 2 commandes de build mises à jour :
  ```bash
  # Backend
  docker build -f docker/build/backend/Dockerfile -t lmelp-backend:test .

  # Frontend
  docker build -f docker/build/frontend/Dockerfile -t lmelp-frontend:test .
  ```

**`docs/index.md`**
- Corrections de whitespace (trailing whitespace) par pre-commit
- Pas de modifications fonctionnelles liées à Docker

### Commit 2 : Autorisation build CI/CD (adbcd49)

**Message** : `chore(ci): allowlist branch 101-refactoring-docker for Docker builds`

**Modifications** : 1 fichier changé, 3 insertions(+), 2 suppressions(-)

**But** : Permettre de tester le build Docker depuis la branche de feature avant le merge

**`.github/workflows/docker-publish.yml`**

Ajout de la branche dans les triggers :
```yaml
# Ligne 8 (ajoutée)
on:
  push:
    branches:
      - main
      - 101-refactoring-docker  # pragma: allowlist secret
```

Activation du tag `:latest` pour la branche :
```yaml
# Ligne 68 (backend)
type=raw,value=latest,enable=${{ github.ref == 'refs/heads/main' || github.ref == 'refs/heads/101-refactoring-docker' }}

# Ligne 128 (frontend)
type=raw,value=latest,enable=${{ github.ref == 'refs/heads/main' || github.ref == 'refs/heads/101-refactoring-docker' }}
```

**Note** : Cette configuration est temporaire et sera retirée après le merge.

### Commit 3 : Corrections de bugs (1620295)

**Message** : `fix(docker): update nginx.conf path and fix gitignore for docker/build`

**Modifications** : 2 fichiers changés, 2 insertions(+), 1 suppression(-)

#### Bug 1 : nginx.conf introuvable

**Erreur rencontrée** :
```
ERROR: failed to solve: "/docker/frontend/nginx.conf": not found
```

**Cause** : Le Dockerfile frontend référençait encore l'ancien chemin

**Solution** : `docker/build/frontend/Dockerfile` (ligne 30)
```dockerfile
# Avant
COPY docker/frontend/nginx.conf /etc/nginx/conf.d/default.conf

# Après
COPY docker/build/frontend/nginx.conf /etc/nginx/conf.d/default.conf
```

#### Bug 2 : docker/build/ ignoré par git

**Erreur rencontrée** :
```
The following paths are ignored by one of your .gitignore files:
docker/build
```

**Cause** : La règle générale `build/` dans `.gitignore` ignorait tous les répertoires `build/`, y compris `docker/build/`

**Solution** : `.gitignore` (ligne 12 ajoutée)
```gitignore
build/
!docker/build/   # Exception pour les Dockerfiles de build
```

## 🧪 Tests et Validation

### Tests locaux (tous passés ✅)
- **Backend** : 561 tests passés, 22 skipped
- **Frontend** : 304 tests passés
- **Ruff linting** : Aucune erreur
- **MyPy type checking** : Aucune erreur
- **Pre-commit hooks** : Tous passés

### Tests CI/CD (tous passés ✅)

#### Workflow 1 : CI/CD Pipeline
- ✅ Tests backend (Python 3.11, 3.12)
- ✅ Tests frontend (Node.js 18)
- ✅ Documentation build (MkDocs)
- ✅ Linting et type checking

#### Workflow 2 : Docker Build and Publish
- ✅ Backend image built and pushed
  - Tag `:101-refactoring-docker`
  - Tag `:latest`
- ✅ Frontend image built and pushed
  - Tag `:101-refactoring-docker`
  - Tag `:latest`
- ⏱️ Temps total : ~1m30s

**URLs des images** :
- Backend : `ghcr.io/castorfou/lmelp-backend:latest`
- Frontend : `ghcr.io/castorfou/lmelp-frontend:latest`

## 💡 Points Clés et Apprentissages

### 1. Séparation des responsabilités

| Type | Répertoire | Utilisé par | Contenu | But |
|------|-----------|-------------|---------|-----|
| **Build** | `docker/build/` | CI/CD (GitHub Actions) | Dockerfiles, nginx.conf | Construire les images |
| **Deployment** | `docker/deployment/` | Local, NAS (Portainer) | docker-compose.yml, .env | Déployer les conteneurs |

**Avantages** :
- ✅ **Clarté** : Intention évidente (build vs deploy)
- ✅ **Maintenabilité** : Modifications ciblées
- ✅ **Cohérence** : Structure logique facile à comprendre
- ✅ **Découplage** : Changements build n'affectent pas deployment

### 2. Pattern gitignore avec exceptions

Quand une règle générale doit avoir des exceptions :

```gitignore
build/           # Ignore tous les dossiers build/
!docker/build/   # SAUF docker/build/ (exception)
```

**Important** :
- L'exception doit venir **immédiatement après** la règle générale
- L'exception commence par `!` (négation)
- Chemins relatifs depuis la racine du repository

### 3. Mise à jour des chemins Docker

Lors d'un refactoring de structure Docker, vérifier **tous** les chemins :

#### Dans les Dockerfiles
- Instructions `COPY` avec chemins relatifs
- Contexte = racine du projet (où se trouve `.git/`)
- Penser aux fichiers référencés (nginx.conf, scripts, etc.)

#### Dans les workflows CI/CD
- Paramètre `file:` dans `docker/build-push-action`
- Instructions de déploiement dans `$GITHUB_STEP_SUMMARY`

#### Dans la documentation
- README.md, guides de déploiement, guides de test
- Exemples de commandes avec chemins

### 4. Tests avant merge avec branche temporaire

**Pattern pour tester des changements Docker avant merge** :

1. **Ajouter la branche** dans `docker-publish.yml` :
   ```yaml
   branches:
     - main
     - ma-branche-feature  # Temporaire
   ```

2. **Activer le tag latest** pour cette branche :
   ```yaml
   type=raw,value=latest,enable=${{ github.ref == 'refs/heads/main' || github.ref == 'refs/heads/ma-branche-feature' }}
   ```

3. **Push et vérifier** :
   - Images buildées et publiées
   - Tests locaux avec `docker pull ...`

4. **Retirer la branche après merge** :
   - Supprimer les 2 références ajoutées
   - Commit de nettoyage

**Avantages** :
- ✅ Validation complète avant merge
- ✅ Images testables en environnement réel
- ✅ Rollback facile si problème

### 5. Commits atomiques pour refactoring

**Stratégie de commit** pour ce refactoring :

1. **Commit principal** : Structure + documentation (22 fichiers)
   - Déplacements de fichiers
   - Suppressions
   - Mises à jour des références

2. **Commit configuration** : Autorisation CI/CD (1 fichier)
   - Changement de workflow isolé
   - Facile à reverter

3. **Commit correction** : Bug fixes (2 fichiers)
   - Corrections découvertes lors des tests
   - Séparé du refactoring principal

**Avantages** :
- ✅ Revue de code facilitée
- ✅ Rollback ciblé possible
- ✅ Historique git clair et compréhensible
- ✅ Bisect git efficace

### 6. Documentation synchrone

**Principe** : Mettre à jour la documentation **dans le même commit** que le code

Fichiers modifiés ensemble dans le commit principal :
- Code : Dockerfiles, docker-compose.yml
- Workflows : .github/workflows/docker-publish.yml
- Docs utilisateur : README.md
- Docs technique : docs/deployment/*.md
- Docs structure : docker/README.md

**Avantages** :
- ✅ Documentation toujours à jour
- ✅ Cohérence code/docs garantie
- ✅ Pas de "dette documentaire"

## 🐛 Problèmes Rencontrés et Solutions

### Problème 1 : nginx.conf introuvable lors du build frontend

**Symptôme** :
```
ERROR: failed to build: failed to solve: failed to compute cache key
ERROR: "/docker/frontend/nginx.conf": not found
```

**Diagnostic** :
1. Build frontend échoue sur GitHub Actions
2. Build local réussit (fichiers présents)
3. → Le Dockerfile référence un chemin inexistant dans le contexte

**Cause racine** :
```dockerfile
# docker/build/frontend/Dockerfile ligne 30
COPY docker/frontend/nginx.conf /etc/nginx/conf.d/default.conf
#     ^^^^^^^^^^^^^^^ Ancien chemin !
```

Le fichier a été déplacé vers `docker/build/frontend/nginx.conf` mais le Dockerfile n'a pas été mis à jour.

**Solution** :
```dockerfile
COPY docker/build/frontend/nginx.conf /etc/nginx/conf.d/default.conf
#     ^^^^^^^^^^^^^^^^ Nouveau chemin
```

**Leçon** : Lors d'un refactoring de structure, utiliser `grep -r` pour trouver **toutes** les références aux chemins déplacés.

### Problème 2 : docker/build/ ignoré par git

**Symptôme** :
```bash
$ git add docker/build/frontend/Dockerfile
The following paths are ignored by one of your .gitignore files:
docker/build
hint: Use -f if you really want to add them.
```

**Diagnostic** :
1. `git status` ne voit pas les modifications dans `docker/build/`
2. `.gitignore` contient une règle `build/` (ligne 11)
3. Cette règle ignore **tous** les dossiers `build/` récursivement
4. → `docker/build/` est ignoré même s'il contient des fichiers importants

**Cause racine** :
```gitignore
# .gitignore ligne 11
build/          # Ignore tous les build/ (y compris docker/build/)
```

Cette règle est destinée aux artefacts de build Python/Node, mais affecte aussi notre structure Docker.

**Solution** :
```gitignore
build/          # Ligne 11 (inchangée)
!docker/build/  # Ligne 12 (ajoutée) - Exception explicite
```

**Pattern gitignore** :
- Une règle de négation `!pattern` **annule** une règle précédente
- Elle doit venir **immédiatement après** la règle à annuler
- Chemins relatifs depuis la racine du repository

**Leçon** : Toujours vérifier `.gitignore` lors de création de nouveaux répertoires, surtout avec des noms génériques comme `build/`, `dist/`, `tmp/`.

### Problème 3 : Pre-commit modifie automatiquement docs/index.md

**Symptôme** :
Premier commit échoue avec :
```
trim trailing whitespace.................................................Failed
- files were modified by this hook
Fixing docs/index.md
```

**Diagnostic** :
1. `docs/index.md` contenait des espaces en fin de ligne
2. Hook `trailing-whitespace` les a supprimés automatiquement
3. Le commit est rejeté car les fichiers ont été modifiés

**Solution** :
```bash
# Pre-commit a déjà corrigé les fichiers
git add -A
git commit -m "..." # Retry, maintenant ça passe
```

**Leçon** :
- Pre-commit peut modifier automatiquement les fichiers
- Toujours relancer le commit après un échec de pre-commit
- Les hooks auto-fix sont bénéfiques (formatage cohérent)

## 📊 Impact et Métriques

### Changements de code
- **Fichiers modifiés** : 22 fichiers
- **Insertions** : 77 lignes
- **Suppressions** : 789 lignes
- **Net** : -712 lignes (89% de réduction !)

### Structure simplifiée
- **Avant** : 2 répertoires (`docker/` + `deployment/`) avec fichiers dupliqués
- **Après** : 1 répertoire (`docker/`) avec 2 sous-répertoires logiques
- **Scripts supprimés** : 5 scripts bash obsolètes (184 lignes)
- **Docker-compose obsolètes** : 3 fichiers supprimés (220 lignes)

### Temps de build CI/CD
- **CI/CD Pipeline** : ~2 minutes (inchangé)
- **Docker Build** : ~1m30s (inchangé)
- **Total** : ~3m30s pour validation complète

### Couverture de tests
- **Backend** : 79% coverage (561 tests)
- **Frontend** : Tests complets (304 tests)
- **Aucune régression** détectée

## 🚀 Bénéfices du Refactoring

### Pour les développeurs
- ✅ Structure claire et intuitive
- ✅ Séparation build/deploy évidente
- ✅ Moins de confusion sur quel fichier utiliser
- ✅ Documentation auto-descriptive

### Pour la CI/CD
- ✅ Chemins explicites dans les workflows
- ✅ Pas de fichiers obsolètes qui prêtent à confusion
- ✅ Build reproductible et fiable

### Pour le déploiement
- ✅ Un seul `docker/deployment/` à connaître
- ✅ Instructions claires et cohérentes
- ✅ Moins de risques d'erreur

### Pour la maintenance
- ✅ Modifications ciblées (build ou deploy, pas les deux)
- ✅ Historique git plus clair
- ✅ Onboarding facilité pour nouveaux contributeurs

## 📋 Checklist de Prochaines Étapes

### Après merge sur main
- [ ] **Retirer la branche temporaire** du workflow Docker
  - Supprimer `101-refactoring-docker` de `.github/workflows/docker-publish.yml`
  - 2 endroits : trigger branches + enable latest
- [ ] **Tester le déploiement Portainer**
  - Vérifier avec `docker/deployment/docker-compose.yml`
  - Valider le webhook de déploiement automatique
- [ ] **Supprimer la branche feature**
  - `git branch -d 101-refactoring-docker`
  - `git push origin --delete 101-refactoring-docker`

### Optionnel
- [ ] Créer un tag de version (ex: `v1.2.0`)
- [ ] Annoncer les changements dans le changelog
- [ ] Mettre à jour les guides de contribution si nécessaire

## 🔗 Références

- **Issue GitHub** : [#101](https://github.com/castorfou/back-office-lmelp/issues/101)
- **Pull Request** : À créer
- **Documentation Docker** : `docker/README.md` (à la racine du projet)
- **Guide Portainer** : [docs/deployment/portainer-guide.md](../../deployment/portainer-guide.md)
- **Testing Guide** : [docs/deployment/testing-guide.md](../../deployment/testing-guide.md)
- **Workflow CI/CD** : `.github/workflows/docker-publish.yml` (à la racine du projet)

## 📚 Documentation Créée/Mise à Jour

1. **Ce document** : Mémoire complète du refactoring
2. **docker/README.md** : Documentation de structure (réécrit)
3. **README.md** : Commandes de déploiement mises à jour
4. **docs/deployment/docker-setup.md** : Chemins Dockerfile mis à jour
5. **docs/deployment/portainer-guide.md** : Référence docker-compose mise à jour
6. **docs/deployment/testing-guide.md** : Commandes build mises à jour

Total : 6 fichiers de documentation touchés pour maintenir la cohérence.
