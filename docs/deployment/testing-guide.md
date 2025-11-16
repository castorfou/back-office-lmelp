# Guide de tests et validation

## Tests locaux avant déploiement

### Prérequis

- Docker et Docker Compose installés
- Images buildées localement ou accès à ghcr.io
- Port 8080 disponible sur la machine locale

### Build des images locales

#### Backend

```bash
# Depuis la racine du projet
docker build -f docker/backend/Dockerfile -t lmelp-backend:test .

# Vérifier la taille de l'image
docker images | grep lmelp-backend

# Taille attendue : ~200-400 Mo
```

#### Frontend

```bash
# Depuis la racine du projet
docker build -f docker/frontend/Dockerfile -t lmelp-frontend:test .

# Vérifier la taille de l'image
docker images | grep lmelp-frontend

# Taille attendue : ~50-100 Mo (nginx + fichiers statiques)
```

### Test avec docker-compose local

#### Créer docker-compose.test.yml

```yaml
version: '3.8'

services:
  mongo:
    image: mongo:7
    container_name: lmelp-mongo-test
    ports:
      - "27017:27017"
    volumes:
      - mongo-test-data:/data/db

  backend:
    image: lmelp-backend:test
    container_name: lmelp-backend-test
    depends_on:
      - mongo
    environment:
      MONGODB_URL: mongodb://mongo:27017/masque_et_la_plume
      ENVIRONMENT: test
      API_HOST: 0.0.0.0
      API_PORT: 8000
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/"]
      interval: 10s
      timeout: 5s
      retries: 3

  frontend:
    image: lmelp-frontend:test
    container_name: lmelp-frontend-test
    depends_on:
      - backend
    ports:
      - "8080:80"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost/"]
      interval: 10s
      timeout: 5s
      retries: 3

volumes:
  mongo-test-data:
```

#### Lancer les tests

```bash
# Démarrer la stack de test
docker-compose -f docker-compose.test.yml up -d

# Attendre que les healthchecks passent au vert
docker-compose -f docker-compose.test.yml ps

# Vérifier les logs
docker-compose -f docker-compose.test.yml logs backend
docker-compose -f docker-compose.test.yml logs frontend

# Arrêter et nettoyer
docker-compose -f docker-compose.test.yml down -v
```

## Tests de validation

### 1. Test healthcheck backend

```bash
# Test direct du healthcheck
curl http://localhost:8080/api

# Résultat attendu
{
  "status": "ok",
  "message": "Welcome to Back Office LMELP API"
}
```

### 2. Test healthcheck frontend

```bash
curl http://localhost:8080/

# Doit retourner le HTML de la page Vue.js
# Status code : 200
```

### 3. Test connexion MongoDB

```bash
# Depuis le conteneur backend
docker exec lmelp-backend-test curl http://localhost:8000/api/stats

# Résultat attendu : statistiques MongoDB
{
  "total_books": 123,
  "total_authors": 45,
  ...
}
```

### 4. Test proxy nginx → backend

```bash
# Appel API via frontend (nginx)
curl http://localhost:8080/api/stats

# Doit retourner les mêmes données que le test précédent
```

### 5. Test routes Vue.js (SPA)

```bash
# Tester qu'une route Vue.js retourne index.html
curl http://localhost:8080/search

# Status : 200
# Content : HTML avec <div id="app">

# Tester route inexistante (fallback à index.html)
curl http://localhost:8080/random-route

# Status : 200 (pas 404, car SPA)
```

### 6. Test fichiers statiques

```bash
# Vérifier qu'un asset CSS/JS existe
curl http://localhost:8080/assets/index.js

# Status : 200
# Content-Type : application/javascript
```

## Tests de charge

### Prérequis

Installer Apache Bench ou wrk :

```bash
# Ubuntu/Debian
sudo apt-get install apache2-utils

# macOS
brew install wrk
```

### Test backend API

```bash
# 100 requêtes, 10 concurrentes
ab -n 100 -c 10 http://localhost:8080/api/

# Résultat attendu
# - Requests per second : > 50
# - Failed requests : 0
```

### Test frontend

```bash
# 1000 requêtes, 50 concurrentes
ab -n 1000 -c 50 http://localhost:8080/

# Résultat attendu
# - Requests per second : > 200
# - Failed requests : 0
```

### Test MongoDB queries

```bash
# Test endpoint de recherche
ab -n 100 -c 10 'http://localhost:8080/api/books?query=test'

# Résultat attendu
# - Requests per second : > 20
# - Failed requests : 0
```

## Tests sur NAS Synology

### Pré-déploiement

Avant de déployer en production, valider sur le NAS :

#### 1. Vérifier les ressources disponibles

```bash
# SSH sur le NAS
ssh admin@<nas-ip>

# Vérifier RAM disponible
free -h

# Vérifier espace disque
df -h

# Vérifier CPU
top
```

#### 2. Vérifier MongoDB existant

```bash
# Vérifier que MongoDB est accessible
docker exec mongo mongosh --eval "db.adminCommand('ping')"

# Résultat attendu : { ok: 1 }
```

#### 3. Tester le réseau bridge

```bash
# Lister les conteneurs sur bridge
docker network inspect bridge | grep Name

# Vérifier que mongo est présent
```

### Post-déploiement

Après déploiement via Portainer :

#### 1. Vérifier que les conteneurs démarrent

```bash
docker ps | grep lmelp

# Résultat attendu : 2 conteneurs (backend + frontend) avec status "Up"
```

#### 2. Vérifier les healthchecks

```bash
docker ps --format "table {{.Names}}\t{{.Status}}"

# Résultat attendu : (healthy) pour les 2 conteneurs
```

#### 3. Tester la connectivité interne

```bash
# Backend vers MongoDB
docker exec lmelp-backend curl http://localhost:8000/api/stats

# Frontend vers backend
docker exec lmelp-frontend curl http://backend:8000/
```

#### 4. Tester l'accès externe

Depuis un navigateur (réseau local) :
```
http://<nas-ip>:8080
```

Vérifier :
- ✅ Page d'accueil s'affiche
- ✅ Recherche fonctionne
- ✅ API retourne des données

### Test reverse proxy Synology

#### 1. Vérifier la configuration

DSM → **Control Panel** → **Login Portal** → **Advanced** → **Reverse Proxy**

Vérifier la règle :
- Source : `lmelp.ascot63.synology.me` (port 443)
- Destination : `localhost` (port 8080)

#### 2. Test HTTPS

```bash
# Depuis Internet (ou autre réseau)
curl https://lmelp.ascot63.synology.me

# Vérifier certificat SSL
curl -v https://lmelp.ascot63.synology.me 2>&1 | grep "SSL certificate"
```

#### 3. Test API via reverse proxy

```bash
curl https://lmelp.ascot63.synology.me/api | jq
```

## Checklist de validation complète

### Build et images

- [ ] Backend image build sans erreur
- [ ] Frontend image build sans erreur
- [ ] Taille des images raisonnable (< 500 Mo chacune)
- [ ] Images publiées sur ghcr.io

### Tests locaux

- [ ] docker-compose.test.yml démarre sans erreur
- [ ] Backend healthcheck passe
- [ ] Frontend healthcheck passe
- [ ] MongoDB accessible depuis backend
- [ ] nginx proxy fonctionne (frontend → backend)
- [ ] Routes Vue.js retournent index.html
- [ ] Fichiers statiques servis correctement

### Tests performance

- [ ] Backend : > 50 req/s
- [ ] Frontend : > 200 req/s
- [ ] MongoDB queries : > 20 req/s
- [ ] Temps de réponse API : < 500ms

### Déploiement NAS

- [ ] Conteneurs démarrent sans erreur
- [ ] Healthchecks passent au vert
- [ ] Logs sans erreurs critiques
- [ ] Utilisation RAM < 50% des limites
- [ ] Application accessible en local (port 8080)

### Reverse proxy

- [ ] HTTPS fonctionne
- [ ] Certificat SSL valide
- [ ] Application accessible depuis Internet
- [ ] API accessible via reverse proxy

### Webhook et CI/CD

- [ ] GitHub Actions build réussit
- [ ] Images publiées sur ghcr.io
- [ ] Webhook Portainer déclenché
- [ ] Déploiement automatique fonctionne

## Tests de régression

Après chaque mise à jour, valider les fonctionnalités principales :

### Fonctionnalités backend

- [ ] Endpoint racine (`/`) retourne status OK
- [ ] Stats API (`/api/stats`) retourne données
- [ ] Recherche livres (`/api/books?query=...`)
- [ ] Recherche auteurs (`/api/authors?query=...`)
- [ ] Détails livre (`/api/books/{id}`)
- [ ] Détails auteur (`/api/authors/{id}`)

### Fonctionnalités frontend

- [ ] Page d'accueil charge
- [ ] Recherche fonctionne
- [ ] Navigation entre onglets
- [ ] Affichage détails livre
- [ ] Affichage détails auteur
- [ ] Validation Babelio
- [ ] Import épisode RadioFrance

## Monitoring continu

### Métriques à surveiller

Via Portainer ou CLI :

```bash
# CPU usage
docker stats --no-stream lmelp-backend lmelp-frontend

# Memory usage
docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}"

# Disk usage
docker system df
```

### Alertes recommandées

Configurer des alertes pour :

- ⚠️ Conteneur arrêté de manière inattendue
- ⚠️ Healthcheck échoué > 3 fois consécutives
- ⚠️ Utilisation RAM > 80% des limites
- ⚠️ Utilisation CPU > 90%
- ⚠️ Espace disque < 10 Go disponibles

### Logs à surveiller

```bash
# Errors backend
docker logs lmelp-backend | grep -i error

# Errors frontend (nginx)
docker logs lmelp-frontend | grep -i error

# Errors MongoDB
docker logs mongo | grep -i error
```

## Rollback testing

Tester la procédure de rollback :

### 1. Déployer une version spécifique

```bash
# Via Portainer : changer les tags vers v1.0.0
# Vérifier que l'application démarre correctement
```

### 2. Revenir à latest

```bash
# Via Portainer : remettre les tags à :latest
# Vérifier que l'application démarre correctement
```

### 3. Mesurer le temps de rollback

Le rollback complet doit prendre :
- < 2 minutes pour pull des images
- < 1 minute pour restart des conteneurs
- **Total : < 5 minutes**

## Documentation des incidents

En cas de problème en production, documenter :

1. **Symptôme** : Qu'est-ce qui ne fonctionne pas ?
2. **Impact** : Quels utilisateurs/fonctionnalités affectés ?
3. **Timeline** : Quand le problème est apparu ?
4. **Logs** : Copier les logs pertinents
5. **Actions** : Qu'avez-vous fait pour résoudre ?
6. **Résolution** : Comment le problème a été résolu ?
7. **Prévention** : Comment éviter ce problème à l'avenir ?

Template incident :
```markdown
## Incident YYYY-MM-DD

**Symptôme** : 502 Bad Gateway sur /api/*

**Impact** : Tous les utilisateurs, fonctionnalités API indisponibles

**Timeline** :
- 10:00 : Déploiement v1.2.0
- 10:05 : Première alerte 502
- 10:10 : Investigation logs

**Logs** :
```
[logs here]
```

**Actions** :
1. Consulté logs backend
2. Identifié erreur MongoDB connection
3. Rollback vers v1.1.0

**Résolution** : Rollback vers v1.1.0, application fonctionnelle

**Prévention** : Ajouter test de connexion MongoDB dans CI/CD
```

## Prochaines étapes

- [Troubleshooting](troubleshooting.md)
- [Update Guide](update-guide.md)
- [Portainer Guide](portainer-guide.md)
