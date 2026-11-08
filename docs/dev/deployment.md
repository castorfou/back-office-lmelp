# Déploiement

Cette section couvre les aspects de déploiement de lmelp.

## Environnements

### Développement
- **Local** : Port 54322 (backend) + 5173 (frontend)
- **Docker** : Via devcontainer VS Code

### Production
- **Backend** : FastAPI avec uvicorn
- **Frontend** : Build statique via npm
- **Base de données** : MongoDB

## Configuration

### Variables d'environnement
```bash
# Backend
API_PORT=54322
PYTHONPATH=/workspaces/back-office-lmelp/src

# Base de données
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=lmelp
```

### Commandes de déploiement
```bash
# Backend
uv run python -m back_office_lmelp.app

# Frontend
cd frontend && npm run build
```

## CI/CD

Le déploiement automatique est géré par GitHub Actions :
- **Tests** : Python 3.11/3.12 + Node.js 18 ; la couverture s'affiche dans le log du job (`--cov-report=term-missing`)
- **Qualité** : Ruff, MyPy, pre-commit
- **Sécurité** : Analyse des secrets (detect-secrets)

| Workflow | Déclencheur | Rôle |
|----------|-------------|------|
| `ci-cd.yml` | push sur toute branche, PR vers `main` | tests backend et frontend, pre-commit, detect-secrets |
| `docker-publish.yml` | push sur `main`, tags `v*`, manuel | build et publication des images sur ghcr.io, mise à jour du NAS (Watchtower) |
| `docs.yml` | changements de doc | build MkDocs et publication GitHub Pages (fichier du template PyFoundry) |

### Versions des actions

Chaque action doit être épinglée sur une majeure qui tourne sous Node 24.
`tests/test_github_actions.py` le vérifie :

- chaque action utilisée doit figurer dans `MIN_MAJOR`, avec sa première majeure Node 24 ;
- `astral-sh/setup-uv` s'épingle sur un tag exact (`vX.Y.Z`), le projet ne publie plus de tag flottant ;
- une même action garde la même version dans tous les workflows ;
- un bloc `tags: |` de `docker/metadata-action` ne contient pas de commentaire en fin de ligne : depuis la v6, il ferait partie de la valeur du tag.

Pour ajouter ou monter une action, lire le champ `runs.using` de son `action.yml` au tag visé :

```bash
gh api "repos/docker/build-push-action/contents/action.yml?ref=v7.4.0" -q .content | base64 -d | grep using
```

Puis mettre à jour `MIN_MAJOR`. Les mises à jour sont manuelles (pas de Dependabot) : une PR Dependabot sur `docs.yml`, qui vient du template, créerait des rejets au `cruft update` suivant.
