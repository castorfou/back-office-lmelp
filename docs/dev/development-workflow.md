# Workflow de développement avec Docker et Portainer

Ce guide décrit le workflow recommandé pour développer back-office-lmelp tout en utilisant Portainer pour la production locale.

## Vue d'ensemble

Le workflow sépare clairement deux environnements :

- **Développement** : devcontainer (VS Code) sur une branche feature
- **Production locale** : Stack Portainer (auto-update) sur la branche main

Cette séparation évite les conflits de ports et permet une mise à jour automatique de la version "production" locale.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        MongoDB (hôte)                        │
│                    localhost:27017                           │
│              masque_et_la_plume database                     │
└─────────────┬─────────────────────────────┬─────────────────┘
              │                             │
    ┌─────────▼─────────┐         ┌────────▼─────────┐
    │   DÉVELOPPEMENT   │         │   PRODUCTION      │
    │                   │         │     LOCALE        │
    │  Devcontainer     │         │                   │
    │  (branche feature)│         │  Stack Portainer  │
    │                   │         │  (branche main)   │
    │  Backend: 8000    │         │  Frontend: 8080   │
    │  Frontend: 5173   │         │  (via nginx)      │
    │  DB: localhost    │         │  DB: mongo (DNS)  │
    └───────────────────┘         └───────────────────┘
         Actif pendant              Actif le reste
         le développement           du temps
```

## Workflow étape par étape

### 1. Démarrer un nouveau développement

**Sur une nouvelle branche feature :**

```bash
# Créer la branche feature
git checkout -b feature/ma-nouvelle-fonctionnalite

# Dans Portainer Web UI : Arrêter la stack lmelp-back-office
# Stacks → lmelp-back-office → Stop this stack
```

**Pourquoi arrêter Portainer ?**
- Libère le port 8080 pour le frontend en dev
- Évite les accès concurrents à MongoDB (bien que MongoDB les supporte)
- Environnement propre pour le développement

### 2. Développer dans devcontainer

```bash
# Ouvrir VS Code dans le repo
code .

# VS Code détecte automatiquement le devcontainer
# Accept "Reopen in Container"
```

**Dans le devcontainer :**

- Le backend se connecte à MongoDB sur l'hôte (localhost)
- Backend FastAPI sur port dynamique (8000 par défaut)
- Frontend Vue.js + Vite sur port 5173
- Hot-reload automatique des modifications (backend et frontend)
- Accès à tous les outils de dev (pytest, ruff, mypy, vitest, etc.)

**Lancer l'application :**

```bash
# Backend (avec auto-détection de port)
PYTHONPATH=/workspaces/back-office-lmelp/src python -m back_office_lmelp.app

# Frontend (dans un autre terminal)
cd /workspaces/back-office-lmelp/frontend && npm run dev

# Ou utiliser le script de démarrage
./scripts/start-dev.sh
```

**Accès :**
- Frontend : http://localhost:5173
- Backend API : http://localhost:8000
- API Docs : http://localhost:8000/docs

### 3. Développer et tester

```bash
# Modifier le code (backend Python ou frontend Vue.js)
# Les changements sont automatiquement reflétés (hot-reload)

# Formatter le code backend
ruff format .

# Linting backend
ruff check . --output-format=github

# Type checking backend
mypy src/

# Tests backend
PYTHONPATH=/workspaces/back-office-lmelp/src pytest tests/ -v

# Tests frontend
cd /workspaces/back-office-lmelp/frontend && npm test -- --run

# Lancer les pre-commit hooks
pre-commit run --all-files

# Commit réguliers
git add .
git commit -m "feat: nouvelle fonctionnalité"
git push origin feature/ma-nouvelle-fonctionnalite
```

### 4. Merger dans main

**Via Pull Request (recommandé) :**

1. Créer une PR sur GitHub
2. Review du code
3. Vérifier que les CI/CD checks passent
4. Merger dans main

**Ou directement (si seul développeur) :**

```bash
git checkout main
git pull origin main
git merge feature/ma-nouvelle-fonctionnalite
git push origin main
```

### 5. Mise à jour automatique de la production locale

**Le workflow CI/CD se déclenche automatiquement :**

```
Push sur main
     ↓
GitHub Actions build Docker images (backend + frontend)
     ↓
Images publiées sur ghcr.io/castorfou/lmelp-{backend,frontend}:latest
     ↓
Portainer webhook déclenché (si configuré)
     ↓
Pull et redéploiement automatique
     ↓
Production locale à jour ! ✅
```

**Durée totale : ~10-20 minutes**
- Build Docker (backend + frontend) : ~8-15 minutes (GitHub Actions)
- Webhook trigger : immédiat (si configuré)
- Pull et redéploiement : ~2-3 minutes

**Redémarrer la stack Portainer :**

```bash
# Dans Portainer Web UI
# Stacks → lmelp-back-office → Start this stack

# Ou forcer l'update immédiatement
# Stacks → lmelp-back-office → Pull and redeploy
```

**Accès production locale : http://localhost:8080**

### 6. Nettoyer la branche feature

```bash
# Supprimer la branche locale
git branch -d feature/ma-nouvelle-fonctionnalite

# Supprimer la branche distante
git push origin --delete feature/ma-nouvelle-fonctionnalite
```

## Avantages de ce workflow

### Séparation dev/prod claire

- **Dev** : Expérimentation libre, breakpoints, debug, hot-reload
- **Prod locale** : Version stable, testée, documentée

### Pas de conflits de ressources

- Port 8080 utilisé par un seul service à la fois
- MongoDB accessible des deux environnements (séquentiellement)

### Auto-update zéro intervention

- Push sur main → Images buildées → Portainer update
- Aucune commande manuelle à lancer
- Reproductible sur NAS Synology

### Données partagées

- Même base MongoDB pour dev et prod locale
- Pas besoin de restaurer des backups entre les deux
- Continuité des données de test

## Configuration Portainer auto-update

### Via webhook Portainer

**Pour des updates instantanées (recommandé) :**

1. Dans Portainer : **Stacks** → **lmelp-back-office** → **Webhooks** → **Create webhook**
2. Copier l'URL du webhook
3. Dans GitHub : **Settings** → **Secrets** → **Actions** → **New secret**
   - Name: `PORTAINER_WEBHOOK_URL`
   - Value: URL copiée
4. Le workflow GitHub Actions triggera automatiquement le webhook après chaque build

Le webhook est déjà configuré dans [`.github/workflows/docker-publish.yml`](../../.github/workflows/docker-publish.yml#L143-L158).

## Troubleshooting

### Port 8080 déjà utilisé

**Symptôme :** Impossible de lancer le frontend en dev

**Cause :** La stack Portainer est toujours active

**Solution :**
```bash
# Vérifier quel processus utilise le port
sudo lsof -i :8080

# Arrêter la stack Portainer
# Via Web UI : Stacks → lmelp-back-office → Stop
```

### MongoDB connection refused en dev

**Symptôme :** `pymongo.errors.ServerSelectionTimeoutError`

**Cause :** MongoDB non démarré sur l'hôte

**Solution :**
```bash
# Vérifier MongoDB (devcontainer l'auto-démarre normalement)
docker ps | grep mongo

# Si pas démarré, utiliser le script du devcontainer
# ou démarrer MongoDB via Docker
```

### Portainer n'auto-update pas

**Symptôme :** Nouvelle version pushée mais Portainer reste sur l'ancienne

**Causes possibles :**

1. **Webhook non configuré** : Vérifier `PORTAINER_WEBHOOK_URL` dans GitHub Secrets
2. **Erreur GitHub Actions** : Vérifier les logs dans l'onglet Actions
3. **Image tag incorrect** : Vérifier que le compose utilise `:latest`

**Solutions :**
```bash
# Forcer l'update manuellement
# Portainer → Stacks → lmelp-back-office → Pull and redeploy

# Vérifier les logs GitHub Actions
# https://github.com/castorfou/back-office-lmelp/actions/workflows/docker-publish.yml
```

### Image Docker pas à jour après le build

**Symptôme :** GitHub Actions build OK mais image pas mise à jour

**Cause :** GitHub Actions en cours ou échoué

**Solution :**
```bash
# Vérifier le statut du build
# https://github.com/castorfou/back-office-lmelp/actions/workflows/docker-publish.yml

# Vérifier les images publiées
# Backend: https://github.com/castorfou/back-office-lmelp/pkgs/container/lmelp-backend
# Frontend: https://github.com/castorfou/back-office-lmelp/pkgs/container/lmelp-frontend
```

## Cas d'usage avancés

### Développer sur plusieurs branches en parallèle

**Problème :** Besoin de tester deux features simultanément

**Solution :** Utiliser différents ports pour le frontend

```bash
# Feature 1 : port 5173 (par défaut)
cd /workspaces/back-office-lmelp/frontend && npm run dev

# Feature 2 : port 5174 (autre terminal, autre workspace)
cd /workspaces/back-office-lmelp-feature2/frontend && npm run dev -- --port 5174
```

Le backend utilise déjà l'auto-détection de port, donc il trouvera automatiquement un port libre.

### Tester l'image Docker localement avant le merge

```bash
# Builder les images localement
cd /workspaces/back-office-lmelp

# Backend
docker build -f docker/build/backend/Dockerfile -t lmelp-backend:test .

# Frontend
docker build -f docker/build/frontend/Dockerfile -t lmelp-frontend:test .

# Arrêter Portainer
# Dans Portainer Web UI : Stop stack lmelp-back-office

# Lancer avec docker compose localement
cd docker/deployment
# Modifier docker-compose.yml pour utiliser :test au lieu de :latest
docker compose up -d

# Accès : http://localhost:8080
```

### Reproduire le workflow sur NAS Synology

**Identique au PC, avec ces différences :**

```yaml
# docker-compose.yml sur NAS
environment:
  MONGODB_URL: mongodb://mongo:27017/masque_et_la_plume  # DNS interne Docker
```

- Pas de devcontainer sur le NAS (développement sur PC uniquement)
- Même auto-update via Portainer webhook
- MongoDB tourne dans un conteneur séparé sur le NAS

## Ressources

- [Guide Docker complet](../../docker/README.md)
- [Guide Portainer](../deployment/portainer-guide.md)
- [CI/CD GitHub Actions](../deployment/docker-setup.md#ci-cd-github-actions)
- [CLAUDE.md - Vue d'ensemble projet](../../CLAUDE.md)

## Résumé du cycle complet

```
1. Stop Portainer stack
2. Dev dans devcontainer (branche feature)
3. Test backend (pytest) + frontend (vitest)
4. Lint/format (ruff, mypy, pre-commit)
5. Commit, push
6. Merge vers main (PR ou direct)
7. CI/CD build images (auto)
8. Portainer pull images (webhook auto)
9. Start Portainer → Prod locale à jour ✅
10. Répéter pour la prochaine feature
```

**Durée du cycle :** 10-20 minutes (principalement build Docker)

**Intervention manuelle :** Stop/Start Portainer uniquement
