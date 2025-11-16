# Docker - Configuration Développement

Ce répertoire contient les fichiers Docker pour le développement et le déploiement de Back-Office LMELP.

## 📂 Structure

```
docker/
├── backend/
│   └── Dockerfile              # Image backend (Python 3.11 + FastAPI)
├── frontend/
│   ├── Dockerfile              # Image frontend (Vue.js + nginx)
│   └── nginx.conf              # Configuration nginx
├── scripts/
│   ├── start.sh                # Démarrer l'application
│   ├── stop.sh                 # Arrêter l'application
│   ├── update.sh               # Mettre à jour les images
│   ├── logs.sh                 # Afficher les logs
│   └── test-build.sh           # Tester les builds localement
├── docker-compose.prod.yml     # Configuration production
├── .env.template               # Template configuration
└── README.md                   # Ce fichier
```

## 🚀 Démarrage rapide

### Prérequis

- Docker et Docker Compose installés
- MongoDB accessible (conteneur ou hôte)
- Port 8080 disponible

### Configuration

1. **Copier le template de configuration :**
   ```bash
   cp .env.template .env
   ```

2. **Éditer .env selon votre environnement :**

   **Linux avec MongoDB sur l'hôte :**
   ```bash
   MONGODB_URL=mongodb://172.17.0.1:27017/masque_et_la_plume
   ```

   **Mac/Windows avec MongoDB sur l'hôte :**
   ```bash
   MONGODB_URL=mongodb://host.docker.internal:27017/masque_et_la_plume
   ```

   **MongoDB dans un conteneur Docker :**
   ```bash
   MONGODB_URL=mongodb://mongo:27017/masque_et_la_plume
   ```

3. **Démarrer l'application :**
   ```bash
   ./scripts/start.sh
   ```

4. **Accéder à l'application :**
   ```
   http://localhost:8080
   ```

## 🛠️ Scripts utilitaires

### Démarrer
```bash
./scripts/start.sh
```
Démarre les conteneurs backend et frontend.

### Arrêter
```bash
./scripts/stop.sh
```
Arrête tous les conteneurs.

### Mettre à jour
```bash
./scripts/update.sh
```
Télécharge les dernières images et redémarre les conteneurs.

### Logs
```bash
# Tous les logs
./scripts/logs.sh

# Backend uniquement
./scripts/logs.sh backend

# Frontend uniquement
./scripts/logs.sh frontend
```

### Test de build local
```bash
./scripts/test-build.sh
```
Build les images localement pour tester les Dockerfiles.

## 🐳 Images Docker

### Backend (FastAPI)

**Dockerfile :** `backend/Dockerfile`

**Architecture :**
- **Stage 1 (builder)** : Installation uv + dépendances Python
- **Stage 2 (runtime)** : Copie code + virtual env

**Taille :** ~300-400 Mo

**Build :**
```bash
docker build -f backend/Dockerfile -t lmelp-backend:test .
```

**Run :**
```bash
docker run -d \
  --name lmelp-backend \
  -e MONGODB_URL=mongodb://host.docker.internal:27017/masque_et_la_plume \
  lmelp-backend:test
```

### Frontend (Vue.js + nginx)

**Dockerfile :** `frontend/Dockerfile`

**Architecture :**
- **Stage 1 (builder)** : Build Vue.js avec npm
- **Stage 2 (runtime)** : Servir avec nginx

**Taille :** ~50-100 Mo

**Build :**
```bash
docker build -f frontend/Dockerfile -t lmelp-frontend:test .
```

**Run :**
```bash
docker run -d \
  --name lmelp-frontend \
  -p 8080:80 \
  lmelp-frontend:test
```

## 🔧 Configuration MongoDB

### MongoDB local dans Docker

```bash
# Démarrer MongoDB
docker run -d \
  --name mongo \
  -p 27017:27017 \
  -v mongo-data:/data/db \
  mongo:7

# Vérifier
docker ps | grep mongo

# Configuration .env
MONGODB_URL=mongodb://172.17.0.1:27017/masque_et_la_plume  # Linux
MONGODB_URL=mongodb://host.docker.internal:27017/masque_et_la_plume  # Mac/Windows
```

### MongoDB distant

```bash
# Configuration .env
MONGODB_URL=mongodb://192.168.1.100:27017/masque_et_la_plume
```

### Tester la connexion

```bash
# Depuis le conteneur backend
docker exec lmelp-backend curl http://localhost:8000/api/stats

# Depuis le host
curl http://localhost:8080/api/stats
```

## 🧪 Tests et validation

### Healthchecks

Vérifier que les healthchecks passent :

```bash
docker ps --format "table {{.Names}}\t{{.Status}}"
```

Résultat attendu : `(healthy)` pour les 2 conteneurs

### Test backend

```bash
# Healthcheck endpoint
curl http://localhost:8080/api

# Stats
curl http://localhost:8080/api/stats | jq
```

### Test frontend

```bash
# Page d'accueil
curl http://localhost:8080

# Fichier statique
curl http://localhost:8080/assets/index.js
```

### Logs

```bash
# Vérifier les erreurs
./scripts/logs.sh | grep -i error

# Backend uniquement
./scripts/logs.sh backend

# Dernières 50 lignes
docker-compose -f docker-compose.prod.yml logs --tail=50
```

## 📊 Monitoring

### Ressources

```bash
# Stats en temps réel
docker stats lmelp-backend lmelp-frontend

# Utilisation disque
docker system df
```

### Limites configurées

**Backend :**
- CPU : 1.0 core max (0.5 réservé)
- RAM : 2 Go max (512 Mo réservé)

**Frontend :**
- CPU : 0.5 core max (0.25 réservé)
- RAM : 512 Mo max (128 Mo réservé)

## 🔄 Développement avec hot-reload

Pour le développement actif avec rechargement automatique, utiliser les commandes natives plutôt que Docker :

```bash
# Backend (dans un terminal)
source .venv/bin/activate
PYTHONPATH=/workspaces/back-office-lmelp/src python -m back_office_lmelp.app

# Frontend (dans un autre terminal)
cd frontend && npm run dev
```

Docker est recommandé pour :
- Tests d'intégration
- Simulation de production
- Validation avant déploiement

## 🐛 Troubleshooting

### Les conteneurs ne démarrent pas

```bash
# Vérifier les logs
./scripts/logs.sh

# Vérifier la configuration
cat .env

# Vérifier MongoDB
docker ps | grep mongo
```

### Backend ne se connecte pas à MongoDB

```bash
# Tester résolution DNS
docker exec lmelp-backend ping mongo

# Tester connexion directe
docker exec lmelp-backend curl http://mongo:27017

# Vérifier variable d'environnement
docker inspect lmelp-backend | grep MONGODB_URL
```

### Frontend retourne 502

```bash
# Vérifier que backend est healthy
docker ps | grep lmelp-backend

# Tester depuis frontend
docker exec lmelp-frontend curl http://backend:8000/

# Vérifier nginx config
docker exec lmelp-frontend cat /etc/nginx/conf.d/default.conf
```

### Images trop volumineuses

```bash
# Nettoyer les images inutilisées
docker image prune -a

# Vérifier tailles
docker images | grep lmelp

# Reconstruire sans cache
docker build --no-cache -f backend/Dockerfile -t lmelp-backend:test .
```

## 📚 Documentation complète

Pour plus de détails :

- **[Déploiement production](../deployment/README.md)** : Guide Portainer
- **[Architecture Docker](../docs/deployment/docker-setup.md)** : Spécifications techniques
- **[Guide de mise à jour](../docs/deployment/update-guide.md)** : Procédures complètes
- **[Troubleshooting](../docs/deployment/troubleshooting.md)** : Diagnostic avancé

Documentation en ligne : https://castorfou.github.io/back-office-lmelp/

## 🔗 Ressources

- **Images Docker** :
  - Backend : https://github.com/castorfou/back-office-lmelp/pkgs/container/lmelp-backend
  - Frontend : https://github.com/castorfou/back-office-lmelp/pkgs/container/lmelp-frontend
- **GitHub Actions** : https://github.com/castorfou/back-office-lmelp/actions
- **Repository** : https://github.com/castorfou/back-office-lmelp
