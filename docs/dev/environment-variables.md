# Variables d'environnement

Ce document liste toutes les variables d'environnement supportées par l'application back-office-lmelp.

## Variables principales

### Configuration serveur

| Variable | Description | Valeur par défaut | Exemple |
|----------|-------------|------------------|---------|
| `API_HOST` | Adresse IP d'écoute du serveur FastAPI | `0.0.0.0` | `127.0.0.1` |
| `API_PORT` | Port d'écoute du serveur FastAPI | Auto-détection (54321-54350) | `8000` |
| `ENVIRONMENT` | Environnement d'exécution | `development` | `production` |

### Base de données MongoDB

| Variable | Description | Valeur par défaut | Exemple |
|----------|-------------|------------------|---------|
| `MONGODB_URL` | URL de connexion MongoDB | `mongodb://localhost:27017/masque_et_la_plume` | `mongodb://user:pass@host:port/db` | <!-- pragma: allowlist secret -->

## Variables Azure OpenAI

| Variable | Description | Valeur par défaut | Exemple |
|----------|-------------|------------------|---------|
| `AZURE_OPENAI_ENDPOINT` | URL de l'endpoint Azure OpenAI | Aucune (requis) | `https://your-resource.openai.azure.com/` |
| `AZURE_OPENAI_API_KEY` | Clé API Azure OpenAI | Aucune (requis) | `your-api-key-here` |
| `AZURE_OPENAI_API_VERSION` | Version API Azure OpenAI | `2024-02-01` | `2024-02-15-preview` |
| `AZURE_OPENAI_DEPLOYMENT_NAME` | Nom du déploiement | `gpt-4` | `gpt-35-turbo` |

## Variables de debug

| Variable | Description | Valeur par défaut | Exemple |
|----------|-------------|------------------|---------|
| `BABELIO_CACHE_LOG` | Active les logs détaillés du cache Babelio | `0` (désactivé) | `1`, `true`, `yes` |

### Usage `BABELIO_CACHE_LOG`

```bash
# Désactivé par défaut (pas de logs verbeux)
python -m back_office_lmelp.app

# Activer les logs de cache pour debug
BABELIO_CACHE_LOG=1 python -m back_office_lmelp.app

# Valeurs acceptées pour activation
BABELIO_CACHE_LOG=1       # ✅
BABELIO_CACHE_LOG=true    # ✅
BABELIO_CACHE_LOG=yes     # ✅
BABELIO_CACHE_LOG=0       # ❌ désactivé
BABELIO_CACHE_LOG=false   # ❌ désactivé
```

## Configuration frontend

| Variable | Description | Valeur par défaut | Exemple |
|----------|-------------|------------------|---------|
| `VITE_API_BASE_URL` | URL de base de l'API pour le frontend | Auto-détection | `http://localhost:8000` |

## Exemple de fichier `.env`

```bash
# Configuration serveur
API_HOST=0.0.0.0
API_PORT=54321
ENVIRONMENT=development

# Base de données
MONGODB_URL=mongodb://localhost:27017/masque_et_la_plume

# Azure OpenAI (optionnel - fallback manuel si non configuré)
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_API_VERSION=2024-02-01
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4

# Debug (désactivé par défaut)
BABELIO_CACHE_LOG=0
```

## Notes importantes

- Les variables Azure OpenAI sont **optionnelles**. Si non configurées, l'application utilise un mode fallback avec parsing manuel
- `API_PORT` utilise un système d'auto-découverte si non définie (ports 54321-54350)
- `BABELIO_CACHE_LOG` est **désactivé par défaut** depuis la v1.1 pour réduire la verbosité
- Toutes les variables peuvent être définies via fichier `.env` ou export shell

## Historique des changements

- **v1.1** : `BABELIO_CACHE_LOG` désactivé par défaut (était activé en v1.0)
- **v1.0** : Support initial des variables d'environnement
