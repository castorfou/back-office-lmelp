# Docker Setup - Architecture et Configuration

## Vue d'ensemble

lmelp tourne en production sur un NAS Synology DS 923+, dans la stack Docker unifiée
**[docker-lmelp](https://github.com/castorfou/docker-lmelp)** : un seul
`docker-compose.yml` regroupe MongoDB, le backend, le frontend et les services annexes.
Cette stack est la **source de vérité** pour le déploiement NAS (services, variables,
volumes, procédure) : voir sa documentation, en particulier
[Migration vers le NAS](https://castorfou.github.io/docker-lmelp/user/migration-nas/).

Ce dépôt publie les images du backend et du frontend, et fournit aussi une variante de
**déploiement autonome** (backend + frontend seuls, branchés sur un MongoDB existant) :
voir [Déploiement autonome](#deploiement-autonome).

## Architecture NAS

```
┌──────────────────────────────────────────────────────────────┐
│                    NAS Synology DS 923+                      │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Reverse proxy DSM (accès réseau local, HTTPS)         │  │
│  │  lmelp.ascot63.synology.me:443 → localhost:8081        │  │
│  └───────────────────────────┬────────────────────────────┘  │
│                              ▼ FRONTEND_PORT (8081)          │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  lmelp-backoffice-frontend (nginx)                     │  │
│  │  - fichiers statiques Vue.js (PWA « lmelp »)           │  │
│  │  - proxy /api/* → backend:8000                         │  │
│  │  - image ghcr.io/castorfou/lmelp-frontend:latest       │  │
│  └───────────────────────────┬────────────────────────────┘  │
│                              ▼ /api/*                        │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  lmelp-backoffice-backend (FastAPI + uvicorn)          │  │
│  │  - image ghcr.io/castorfou/lmelp-backend:latest        │  │
│  └───────────────────────────┬────────────────────────────┘  │
│                              ▼ mongodb://mongo:27017         │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  lmelp-mongo (ghcr.io/castorfou/lmelp-mongo:latest)    │  │
│  │  - base masque_et_la_plume, backups et rotation logs   │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  Réseau Docker commun : lmelp-network                        │
└──────────────────────────────────────────────────────────────┘
```

Services de la stack utilisés par lmelp :

| Service compose | Conteneur | Image | Port hôte |
|---|---|---|---|
| `mongo` | `lmelp-mongo` | `ghcr.io/castorfou/lmelp-mongo:latest` | `MONGO_PORT` (27018) |
| `backend` | `lmelp-backoffice-backend` | `ghcr.io/castorfou/lmelp-backend:latest` | `BACKEND_PORT` (8000) |
| `frontend` | `lmelp-backoffice-frontend` | `ghcr.io/castorfou/lmelp-frontend:latest` | `FRONTEND_PORT` (8081 sur le NAS) |
| `pgx-keys-watchdog` | `lmelp-pgx-keys-watchdog` | `alpine` | — |
| `lmelp-export` | `lmelp-export` | `ghcr.io/castorfou/lmelp-mobile-export:latest` | — |

!!! note "Port du frontend"
    La valeur par défaut de `FRONTEND_PORT` est 8080, mais ce port est souvent déjà pris
    sur un NAS Synology : le NAS utilise **8081** (`.env.nas.example` de docker-lmelp).

## Reverse proxy DSM

DSM → **Portail de connexion** → **Avancé** → **Proxy inversé** → règle **lmelp** :

| | Protocole | Nom d'hôte | Port |
|---|---|---|---|
| Source | HTTPS (HSTS activé) | `lmelp.ascot63.synology.me` | 443 |
| Destination | HTTP | `localhost` | 8081 (`FRONTEND_PORT`) |

- Profil de contrôle d'accès : **réseau local** (l'application n'est pas exposée sur Internet).
- Aucun en-tête personnalisé nécessaire : l'application ne dépend pas des WebSockets.
- Le frontend relaie lui-même `/api/*` vers le backend : une seule règle suffit pour l'interface, l'API (`/api`) et sa documentation (`/docs`).
- L'HTTPS est indispensable pour installer la PWA sur un téléphone (voir [Accès mobile](../user/mobile-access.md)).

## Images Docker

### Repositories GitHub Container Registry

Les images sont hébergées sur ghcr.io et construites automatiquement via GitHub Actions
depuis ce dépôt :

- **Backend**: `ghcr.io/castorfou/lmelp-backend`
- **Frontend**: `ghcr.io/castorfou/lmelp-frontend`

L'image MongoDB `ghcr.io/castorfou/lmelp-mongo` est construite par docker-lmelp.

### Tags disponibles

- `latest`: Dernière version stable (auto-déployée depuis la branche `main`)
- `v1.0.0`, `v1.1.0`, etc.: Versions spécifiques (créées via tags Git)
- `main`: Build de la branche principale (identique à `latest`)

### Accès aux images

Les images sont publiques et accessibles sans authentification :

```bash
docker pull ghcr.io/castorfou/lmelp-backend:latest
docker pull ghcr.io/castorfou/lmelp-frontend:latest
```

## Variables d'environnement

La liste complète (NAS) est dans `.env.nas.example` de docker-lmelp. Variables propres au
backend :

| Variable | Valeur recommandée | Description |
|----------|-------------------|-------------|
| `MONGODB_URL` | `mongodb://mongo:27017/masque_et_la_plume` | URL de connexion MongoDB |
| `ENVIRONMENT` | `production` | Environnement d'exécution |
| `API_HOST` | `0.0.0.0` | Interface réseau à écouter |
| `API_PORT` | `8000` | Port interne du conteneur |
| `PUID` | UID de l'utilisateur hôte (défaut `1000`) | Utilisateur non-root utilisé pour les fichiers écrits sur `/cache` |
| `PGID` | GID de l'utilisateur hôte (défaut `1000`) | Groupe non-root utilisé pour les fichiers écrits sur `/cache` |

Le frontend n'a besoin d'aucune variable : sa configuration est dans `nginx.conf`.

## Healthchecks

### Backend
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 10s
```

### Frontend

Le frontend expose un endpoint `/health` dédié : il renvoie `200 OK` (corps `OK`) et
n'est pas écrit dans les logs d'accès nginx.

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 5s
```

Procédures de vérification : `docker/build/frontend/TESTING.md`.

## Utilisateur non-root (backend)

Le conteneur backend démarre en root pour pouvoir remapper dynamiquement un
utilisateur non-root (`appuser`) vers l'UID/GID de l'hôte (`PUID`/`PGID`),
puis chowner le volume `/cache` bind-monté, avant de dropper les privilèges
via `gosu` et lancer l'application. Aucune directive `USER` statique dans le
`Dockerfile` : le remap se fait entièrement dans
`docker/build/backend/entrypoint.sh`.

Ce mécanisme permet de réutiliser la même image (publiée une fois sur
`ghcr.io`) sur des machines ayant des UID différents (ex: `1000` sur un PC
Linux, `1027` sur un NAS Synology), sans laisser de fichiers `root:root` sur
le volume de cache. Un simple redémarrage du conteneur corrige
automatiquement la propriété des fichiers déjà `root:root`.

## Sécurité

### Secrets et authentification

MongoDB n'a pas d'authentification : il n'est joignable que depuis le réseau local et le
réseau Docker de la stack. Si l'authentification est activée :

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

Les backups MongoDB (hebdomadaires, via anacron dans `lmelp-mongo`) et leur restauration
sont gérés par docker-lmelp : voir
[Backups & Restauration](https://castorfou.github.io/docker-lmelp/user/backup-restore/).

## Logs

Via Portainer : **Containers** → `lmelp-backoffice-backend` / `lmelp-backoffice-frontend` → **Logs**.

Via Docker CLI (accès SSH au NAS) :
```bash
docker logs lmelp-backoffice-backend
docker logs lmelp-backoffice-frontend
```

La rotation des logs Docker (`json-file`, `max-size: 10m`, `max-file: 3`) est déclarée
service par service dans le `docker-compose.yml` de docker-lmelp.

## Monitoring

### Vérifications santé

- Interface : `https://lmelp.ascot63.synology.me`
- API backend : `https://lmelp.ascot63.synology.me/api`
- Documentation API : `https://lmelp.ascot63.synology.me/docs`
- Accès direct sans reverse proxy : `http://<nas-ip>:8081`

### Alertes recommandées

Configurer des alertes Portainer pour :

- Conteneur arrêté de manière inattendue
- Utilisation RAM > 80%
- Healthcheck échoué > 5 fois consécutives

## Déploiement autonome

`docker/deployment/docker-compose.yml` (ce dépôt) déploie **uniquement** le backend
(`lmelp-backend`) et le frontend (`lmelp-frontend`, port `FRONTEND_PORT`, défaut 8080),
branchés sur un MongoDB déjà en place. C'est l'option pour une machine qui n'utilise pas
la stack docker-lmelp. Les guides suivants décrivent cette variante :

1. [Guide Portainer](portainer-guide.md)
2. [Guide de mise à jour](update-guide.md)
3. [Tests et validation](testing-guide.md)
4. [Troubleshooting](troubleshooting.md)
