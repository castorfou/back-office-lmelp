# Docker Setup - Architecture et Configuration

## Vue d'ensemble

L'application back-office-lmelp est déployée sous forme de conteneurs Docker sur un NAS Synology DS 923+. L'architecture utilise trois conteneurs interconnectés.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    NAS Synology DS 923+                     │
│                                                             │
│  ┌────────────────────────────────────────────────────┐   │
│  │         Application Portal (Reverse Proxy)          │   │
│  │      lmelp.ascot63.synology.me (HTTPS)             │   │
│  └──────────────────┬─────────────────────────────────┘   │
│                     │                                       │
│                     ▼ port 8080                            │
│  ┌────────────────────────────────────────────────────┐   │
│  │  Frontend Container (nginx:alpine)                  │   │
│  │  - Sert fichiers statiques Vue.js                   │   │
│  │  - Proxy /api/* vers backend                        │   │
│  │  - Image: ghcr.io/castorfou/lmelp-frontend:latest  │   │
│  └──────────────────┬─────────────────────────────────┘   │
│                     │                                       │
│                     ▼ /api/* → backend:8000                │
│  ┌────────────────────────────────────────────────────┐   │
│  │  Backend Container (FastAPI + uvicorn)              │   │
│  │  - API REST Python                                  │   │
│  │  - Connexion MongoDB                                │   │
│  │  - Image: ghcr.io/castorfou/lmelp-backend:latest   │   │
│  └──────────────────┬─────────────────────────────────┘   │
│                     │                                       │
│                     ▼ mongodb://mongo:27017                │
│  ┌────────────────────────────────────────────────────┐   │
│  │  MongoDB Container (mongo:7)                        │   │
│  │  - Base de données masque_et_la_plume               │   │
│  │  - Conteneur EXISTANT (ne pas recréer)             │   │
│  │  - Géré séparément avec Watchtower                 │   │
│  └────────────────────────────────────────────────────┘   │
│                                                             │
│  Tous les conteneurs sur réseau bridge Docker              │
└─────────────────────────────────────────────────────────────┘
```

## Prérequis NAS Synology

### Spécifications matérielles
- **Modèle**: Synology DS 923+
- **RAM**: 40 Go disponibles (backend: 2 Go max, frontend: 512 Mo max)
- **Stockage**: 20 To disponibles
- **Réseau**: Accès Internet avec domaine configuré

### Logiciels requis
- **DSM 7.0+**: Système d'exploitation Synology
- **Container Manager**: Package Synology pour gérer Docker
- **Portainer**: Interface web pour gérer les stacks Docker
- **Application Portal**: Pour le reverse proxy HTTPS

## Configuration réseau Docker

### Réseau bridge existant

Le conteneur MongoDB existant fonctionne sur le réseau Docker `bridge` par défaut. Les nouveaux conteneurs doivent rejoindre ce même réseau.

```yaml
# Dans docker-compose.prod.yml
networks:
  lmelp-network:
    external: true
    name: bridge
```

### Vérification réseau

Pour vérifier que le conteneur `mongo` est bien sur le réseau bridge :

```bash
docker inspect mongo | grep -A 10 Networks
```

## Images Docker

### Repositories GitHub Container Registry

Les images sont hébergées sur ghcr.io et construites automatiquement via GitHub Actions :

- **Backend**: `ghcr.io/castorfou/lmelp-backend`
- **Frontend**: `ghcr.io/castorfou/lmelp-frontend`

### Tags disponibles

- `latest`: Dernière version stable (auto-déployée depuis la branche `main`)
- `v1.0.0`, `v1.1.0`, etc.: Versions spécifiques (créées via tags Git)
- `main`: Build de la branche principale (identique à `latest`)

### Accès aux images

Les images sont publiques et accessibles sans authentification. Pour les télécharger manuellement :

```bash
docker pull ghcr.io/castorfou/lmelp-backend:latest
docker pull ghcr.io/castorfou/lmelp-frontend:latest
```

## Variables d'environnement

### Backend

| Variable | Valeur recommandée | Description |
|----------|-------------------|-------------|
| `MONGODB_URL` | `mongodb://mongo:27017/masque_et_la_plume` | URL de connexion MongoDB |
| `ENVIRONMENT` | `production` | Environnement d'exécution |
| `API_HOST` | `0.0.0.0` | Interface réseau à écouter |
| `API_PORT` | `8000` | Port interne du conteneur |

### Frontend

Aucune variable d'environnement requise. La configuration est gérée par nginx.conf.

## Healthchecks

### Backend
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 10s
```

### Frontend
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost/"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 5s
```

## Limites de ressources

### Backend
- **CPU**: 1.0 CPU max (0.5 réservé)
- **RAM**: 2 Go max (512 Mo réservé)
- **Restart policy**: `unless-stopped`

### Frontend
- **CPU**: 0.5 CPU max (0.25 réservé)
- **RAM**: 512 Mo max (128 Mo réservé)
- **Restart policy**: `unless-stopped`

## Ports exposés

- **Frontend**: 8080:80 (accès depuis Application Portal)
- **Backend**: Pas de port exposé (accessible uniquement depuis frontend via réseau interne)

## Sécurité

### Secrets et authentification

Actuellement, MongoDB n'a pas d'authentification (accès localhost uniquement). Si l'authentification est activée à l'avenir :

1. Créer un secret dans Portainer pour le mot de passe MongoDB
2. Modifier `MONGODB_URL` pour inclure les credentials :
   ```
  mongodb://username:password@mongo:27017/masque_et_la_plume # pragma: allowlist secret
   ```

### Headers de sécurité

Le frontend nginx ajoute automatiquement les headers de sécurité :
- `X-Frame-Options: SAMEORIGIN`
- `X-Content-Type-Options: nosniff`
- `X-XSS-Protection: 1; mode=block`

## Backup

### Données MongoDB

Le backup MongoDB est géré **séparément** par la configuration NAS existante. Ne pas créer de nouveau système de backup.

### Configuration application

Les fichiers de configuration Docker sont versionnés dans Git :
- `docker/deployment/docker-compose.yml` - Configuration de déploiement
- `docker/build/backend/Dockerfile` - Build backend (CI/CD)
- `docker/build/frontend/Dockerfile` - Build frontend (CI/CD)
- `docker/build/frontend/nginx.conf` - Configuration nginx frontend

## Logs

### Accéder aux logs

Via Portainer :
```
Stacks → lmelp-back-office → Container logs
```

Via Docker CLI (si accès SSH) :
```bash
docker logs lmelp-backend
docker logs lmelp-frontend
```

### Rotation des logs

Configurer la rotation des logs Docker dans Portainer ou via daemon.json :

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

## Monitoring

### Vérifications santé

- Frontend accessible : `https://lmelp.ascot63.synology.me`
- API backend : `https://lmelp.ascot63.synology.me/api`
- Documentation API : `https://lmelp.ascot63.synology.me/docs`

### Métriques Portainer

Portainer affiche automatiquement :
- Utilisation CPU
- Utilisation RAM
- Utilisation réseau
- Utilisation disque

### Alertes recommandées

Configurer des alertes Portainer pour :
- Conteneur arrêté de manière inattendue
- Utilisation RAM > 80%
- Healthcheck échoué > 5 fois consécutives

## Prochaines étapes

1. [Configuration Portainer](portainer-guide.md)
2. [Guide de mise à jour](update-guide.md)
3. [Troubleshooting](troubleshooting.md)
