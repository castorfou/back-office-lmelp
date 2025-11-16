# Guide de mise à jour

## Workflow de mise à jour automatique

Le système de déploiement automatique utilise un pipeline CI/CD complet :

```
┌──────────────┐
│ Git Push/Tag │
└──────┬───────┘
       │
       ▼
┌──────────────────┐
│ GitHub Actions   │
│ - Run tests      │
│ - Build images   │
│ - Push to ghcr   │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Trigger Webhook  │
│ (POST request)   │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Portainer        │
│ - Pull images    │
│ - Stop old       │
│ - Start new      │
└──────────────────┘
```

## Mise à jour automatique (recommandé)

### Depuis la branche main

Chaque push sur `main` déclenche automatiquement :

1. **Tests** : CI/CD vérifie que tous les tests passent
2. **Build** : Construction des images Docker
3. **Publish** : Publication sur ghcr.io avec le tag `latest`
4. **Deploy** : Webhook Portainer déclenché automatiquement

#### Processus

```bash
# 1. Développer sur une branche feature
git checkout -b feature/nouvelle-fonctionnalite
# ... faire les modifications ...
git commit -m "feat: nouvelle fonctionnalité"
git push origin feature/nouvelle-fonctionnalite

# 2. Créer une Pull Request sur GitHub
# 3. Merger la PR vers main après review

# 4. Le déploiement se fait automatiquement !
```

#### Temps de déploiement

- **GitHub Actions** : 5-10 minutes (tests + build + push)
- **Portainer webhook** : 1-2 minutes (pull + redeploy)
- **Total** : ~10-15 minutes après le merge

#### Vérification

1. Consulter GitHub Actions : https://github.com/castorfou/back-office-lmelp/actions
2. Vérifier que le workflow **Docker Build and Publish** est vert (✅)
3. Accéder à Portainer et vérifier que la stack a redémarré
4. Tester l'application : https://lmelp.ascot63.synology.me

### Depuis un tag de version

Pour déployer une release versionnée :

```bash
# 1. Créer un tag de version
git tag -a v1.0.0 -m "Release 1.0.0"
git push origin v1.0.0

# 2. GitHub Actions build automatiquement avec les tags :
#    - ghcr.io/castorfou/lmelp-backend:v1.0.0
#    - ghcr.io/castorfou/lmelp-backend:1.0
#    - ghcr.io/castorfou/lmelp-backend:1
#    - ghcr.io/castorfou/lmelp-backend:latest

# 3. Webhook déclenché automatiquement pour :latest
```

## Mise à jour manuelle

### Redéployer la stack (même version)

Utile pour forcer un redémarrage sans changement de version.

#### Via Portainer

1. **Stacks** → **lmelp-back-office**
2. Cliquer **Update the stack**
3. Cocher **Re-pull images and redeploy**
4. Cliquer **Update**

#### Via webhook manuel

```bash
curl -X POST "http://<nas-ip>:9000/api/webhooks/<token>"
```

### Déployer une version spécifique

Utile pour tester une version ou faire un rollback.

#### Via Portainer

1. **Stacks** → **lmelp-back-office** → **Editor**
2. Modifier les tags d'images :

```yaml
services:
  backend:
    image: ghcr.io/castorfou/lmelp-backend:v1.2.0  # Version spécifique
  frontend:
    image: ghcr.io/castorfou/lmelp-frontend:v1.2.0
```

3. Cocher **Re-pull images and redeploy**
4. Cliquer **Update the stack**

### Mise à jour d'un seul service

Pour mettre à jour uniquement le backend ou le frontend :

#### Via Docker CLI (SSH sur NAS)

```bash
# Mettre à jour uniquement le backend
docker pull ghcr.io/castorfou/lmelp-backend:latest
docker stop lmelp-backend
docker rm lmelp-backend
# Puis recréer depuis Portainer ou docker-compose

# Mettre à jour uniquement le frontend
docker pull ghcr.io/castorfou/lmelp-frontend:latest
docker stop lmelp-frontend
docker rm lmelp-frontend
# Puis recréer depuis Portainer ou docker-compose
```

#### Via Portainer (plus simple)

1. **Containers** → Sélectionner le conteneur
2. **Recreate**
3. Cocher **Pull latest image**
4. **Recreate**

## Rollback vers une version précédente

### Stratégie de rollback

Le rollback est simple car les anciennes images sont conservées dans ghcr.io.

#### Identifier les versions disponibles

1. Accéder aux packages GitHub :
   - Backend : https://github.com/castorfou/back-office-lmelp/pkgs/container/lmelp-backend
   - Frontend : https://github.com/castorfou/back-office-lmelp/pkgs/container/lmelp-frontend

2. Consulter les tags disponibles (ex: `v1.0.0`, `v1.1.0`, etc.)

#### Rollback complet

1. **Stacks** → **lmelp-back-office** → **Editor**
2. Modifier les images pour la version précédente :

```yaml
services:
  backend:
    image: ghcr.io/castorfou/lmelp-backend:v1.0.0  # Version stable connue
  frontend:
    image: ghcr.io/castorfou/lmelp-frontend:v1.0.0
```

3. Cocher **Re-pull images and redeploy**
4. **Update the stack**

#### Rollback d'urgence (CLI)

Si Portainer n'est pas accessible :

```bash
# SSH sur le NAS
ssh admin@<nas-ip>

# Rollback rapide backend
docker stop lmelp-backend
docker run -d \
  --name lmelp-backend \
  --network bridge \
  -e MONGODB_URL=mongodb://mongo:27017/masque_et_la_plume \
  ghcr.io/castorfou/lmelp-backend:v1.0.0

# Rollback rapide frontend
docker stop lmelp-frontend
docker run -d \
  --name lmelp-frontend \
  --network bridge \
  -p 8080:80 \
  ghcr.io/castorfou/lmelp-frontend:v1.0.0
```

## Gestion des versions

### Convention de versioning (Semantic Versioning)

Le projet suit [semver.org](https://semver.org) :

- **v1.0.0** → Version majeure (breaking changes)
- **v1.1.0** → Version mineure (nouvelles fonctionnalités compatibles)
- **v1.1.1** → Patch (corrections de bugs)

### Créer une release

```bash
# 1. S'assurer que tous les tests passent
PYTHONPATH=/workspaces/back-office-lmelp/src pytest tests/ -v
cd frontend && npm test -- --run

# 2. Mettre à jour le numéro de version
# Dans pyproject.toml :
version = "1.1.0"
# Dans frontend/package.json :
"version": "1.1.0"

# 3. Committer les changements de version
git add pyproject.toml frontend/package.json
git commit -m "chore: bump version to 1.1.0"
git push

# 4. Créer le tag
git tag -a v1.1.0 -m "Release 1.1.0: Description des changements"
git push origin v1.1.0

# 5. Le reste est automatique (GitHub Actions + webhook)
```

### Changelog

Maintenir un fichier `CHANGELOG.md` à la racine du projet :

```markdown
# Changelog

## [1.1.0] - 2025-01-15

### Added
- Nouvelle page de visualisation auteur
- Support de la recherche insensible aux accents

### Fixed
- Correction du bug de validation Babelio

## [1.0.0] - 2025-01-01

### Added
- Version initiale avec dockerisation
- Déploiement automatique via Portainer
```

## Monitoring des mises à jour

### Vérifier qu'une mise à jour a réussi

#### 1. GitHub Actions

https://github.com/castorfou/back-office-lmelp/actions

- ✅ Workflow vert = build réussi
- ❌ Workflow rouge = build échoué (mise à jour annulée)

#### 2. Portainer

**Stacks** → **lmelp-back-office**

- Vérifier que **Updated** affiche l'heure récente
- Consulter les logs pour voir les nouvelles images téléchargées

#### 3. Application en production

https://lmelp.ascot63.synology.me

- Tester les fonctionnalités principales
- Vérifier l'absence d'erreurs dans la console navigateur
- Tester les appels API

### Vérifier la version déployée

#### Backend

```bash
curl https://lmelp.ascot63.synology.me/api | jq
```

Ajouter un endpoint `/version` si besoin dans FastAPI :

```python
@app.get("/version")
async def get_version():
    return {"version": "1.1.0", "build": "2025-01-15"}
```

#### Frontend

Inspecter le code source ou ajouter un fichier `version.json` :

```json
{
  "version": "1.1.0",
  "buildDate": "2025-01-15T10:30:00Z"
}
```

## Procédure d'urgence

### Mise à jour causant une panne

Si une mise à jour automatique cause une panne :

#### 1. Rollback immédiat

```bash
# Via Portainer (méthode préférée)
Stacks → lmelp-back-office → Editor
# Changer les tags vers la version précédente stable
image: ghcr.io/castorfou/lmelp-backend:v1.0.0
```

#### 2. Désactiver le webhook temporairement

1. **Stacks** → **lmelp-back-office** → **Webhook**
2. Désactiver **Enable webhook**
3. Cela empêche les déploiements automatiques pendant l'investigation

#### 3. Investiguer le problème

- Consulter les logs backend/frontend dans Portainer
- Vérifier les GitHub Actions pour les erreurs de build
- Tester localement avec Docker

#### 4. Corriger et redéployer

```bash
# Corriger le bug sur une branche
git checkout -b hotfix/critical-bug
# ... faire les corrections ...
git commit -m "fix: correction bug critique"
git push origin hotfix/critical-bug

# Merge rapide vers main (bypass review si nécessaire)
# Créer un tag patch
git tag v1.0.1
git push origin v1.0.1

# Réactiver le webhook dans Portainer
```

### Contact et support

En cas de problème critique :

1. Consulter [Troubleshooting](troubleshooting.md)
2. Vérifier les issues GitHub : https://github.com/castorfou/back-office-lmelp/issues
3. Créer une nouvelle issue avec :
   - Logs Portainer (backend + frontend)
   - Logs GitHub Actions
   - Description du problème

## Bonnes pratiques

### Avant chaque mise à jour

- ✅ Tous les tests passent (backend + frontend)
- ✅ Code review effectué (via Pull Request)
- ✅ Documentation mise à jour si nécessaire
- ✅ Changelog mis à jour

### Déploiement progressif

Pour les changements importants :

1. **Déployer sur une branche feature** pour tester séparément
2. **Créer un tag RC (Release Candidate)** : `v1.1.0-rc1`
3. **Tester manuellement** avant de merger vers main
4. **Merger et créer le tag final** : `v1.1.0`

### Notifications

Configurer des notifications pour être averti des déploiements :

- **GitHub** : Watch repository → Custom → Releases
- **Portainer** : Configurer webhook Discord/Slack (optionnel)

## Prochaines étapes

- [Troubleshooting](troubleshooting.md)
- [Configuration Portainer](portainer-guide.md)
- [Docker Setup](docker-setup.md)
