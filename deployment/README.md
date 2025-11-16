# Déploiement Production Back-Office LMELP

Ce répertoire contient les fichiers nécessaires pour déployer l'application en production sur NAS Synology (ou tout environnement Docker).

## 📦 Contenu

- **docker-compose.yml** : Configuration production (MongoDB externe)
- **.env.template** : Template de configuration à personnaliser
- **README.md** : Ce fichier

## 🚀 Déploiement rapide via Portainer

### Prérequis

- ✅ Portainer installé et accessible
- ✅ MongoDB existant et accessible (conteneur ou hôte)
- ✅ Port 8080 disponible (ou modifiable via .env)

### Étapes

#### 1. Préparer le fichier .env

```bash
# Copier le template
cp .env.template .env

# Éditer selon votre environnement
nano .env
```

**Configurations courantes :**

```bash
# NAS Synology avec conteneur mongo existant (par défaut)
MONGODB_URL=mongodb://mongo:27017/masque_et_la_plume

# PC Linux/Mac/Windows avec MongoDB sur l'hôte
MONGODB_URL=mongodb://host.docker.internal:27017/masque_et_la_plume

# MongoDB distant
MONGODB_URL=mongodb://192.168.1.100:27017/masque_et_la_plume
```

#### 2. Déployer dans Portainer

**Option A : Via Git Repository (RECOMMANDÉ)**

1. Portainer → **Stacks** → **Add stack**
2. **Name** : `lmelp-back-office`
3. **Build method** : Git Repository
4. **Repository URL** : `https://github.com/castorfou/back-office-lmelp`
5. **Repository reference** : `refs/heads/main`
6. **Compose path** : `deployment/docker-compose.yml`
7. **Environment variables** :
   - ✅ Cocher "Load variables from .env file"
   - Upload votre fichier `.env`
8. Cliquer **Deploy the stack**

**Option B : Via Web Editor**

1. Portainer → **Stacks** → **Add stack**
2. **Name** : `lmelp-back-office`
3. **Build method** : Web editor
4. Copier-coller le contenu de `docker-compose.yml`
5. **Environment variables** :
   - ✅ Cocher "Load variables from .env file"
   - Upload votre fichier `.env`
6. Cliquer **Deploy the stack**

#### 3. Vérifier le déploiement

**Statut des conteneurs :**
```bash
docker ps | grep lmelp
# Doit afficher 2 conteneurs : lmelp-backend et lmelp-frontend
```

**Healthchecks :**
```bash
docker ps --format "table {{.Names}}\t{{.Status}}"
# Les 2 conteneurs doivent afficher (healthy)
```

**Accès application :**
```
http://<nas-ip>:8080
```

#### 4. Configurer reverse proxy Synology (optionnel)

DSM → **Control Panel** → **Login Portal** → **Advanced** → **Reverse Proxy**

Créer une règle :
- **Source** : `lmelp.ascot63.synology.me` (port 443, HTTPS)
- **Destination** : `localhost` (port 8080, HTTP)

Accès final : `https://lmelp.ascot63.synology.me`

## 🔄 Mises à jour

### Automatique (webhook Portainer)

Si webhook configuré (voir [Guide Portainer](../docs/deployment/portainer-guide.md)) :

```bash
# Push sur main déclenche automatiquement :
git push origin main
→ GitHub Actions build
→ Push ghcr.io
→ Webhook Portainer
→ Auto-deploy
```

### Manuelle

Via Portainer :
1. **Stacks** → **lmelp-back-office**
2. Cliquer **Update the stack**
3. ✅ Cocher "Re-pull images and redeploy"
4. Cliquer **Update**

Via webhook manuel :
```bash
curl -X POST "$PORTAINER_WEBHOOK_URL"
```

## 🔙 Rollback

Pour revenir à une version précédente :

1. **Stacks** → **lmelp-back-office** → **Editor**
2. Modifier les tags d'images :
   ```yaml
   backend:
     image: ghcr.io/castorfou/lmelp-backend:v1.0.0  # Version stable
   frontend:
     image: ghcr.io/castorfou/lmelp-frontend:v1.0.0
   ```
3. ✅ Cocher "Re-pull images and redeploy"
4. Cliquer **Update**

## 🐛 Troubleshooting

### Backend ne se connecte pas à MongoDB

**Symptôme :** Logs affichent `Connection refused` ou `Unknown host`

**Solutions :**

```bash
# 1. Vérifier que MongoDB est démarré
docker ps | grep mongo

# 2. Vérifier la résolution DNS
docker exec lmelp-backend ping mongo

# 3. Tester la connexion
docker exec lmelp-backend curl http://mongo:27017

# 4. Vérifier MONGODB_URL
docker inspect lmelp-backend | grep MONGODB_URL
```

### Frontend affiche 502 Bad Gateway

**Symptôme :** Page charge mais API retourne 502

**Solutions :**

```bash
# 1. Vérifier que backend est healthy
docker ps | grep lmelp-backend

# 2. Tester connexion frontend → backend
docker exec lmelp-frontend curl http://backend:8000/

# 3. Consulter les logs
docker logs lmelp-backend
docker logs lmelp-frontend
```

### Conteneurs ne démarrent pas

**Symptôme :** État `Exited` ou `Error`

**Solutions :**

```bash
# 1. Consulter les logs
docker logs lmelp-backend
docker logs lmelp-frontend

# 2. Vérifier le réseau
docker network inspect bridge

# 3. Re-pull les images
docker pull ghcr.io/castorfou/lmelp-backend:latest
docker pull ghcr.io/castorfou/lmelp-frontend:latest
```

## 📚 Documentation complète

Pour des guides détaillés :

- **[Architecture Docker](../docs/deployment/docker-setup.md)** : Détails techniques complets
- **[Guide Portainer](../docs/deployment/portainer-guide.md)** : Configuration webhook, variables
- **[Guide de mise à jour](../docs/deployment/update-guide.md)** : Procédures détaillées
- **[Tests et validation](../docs/deployment/testing-guide.md)** : Checklist complète
- **[Troubleshooting](../docs/deployment/troubleshooting.md)** : Diagnostic avancé

Documentation en ligne : https://castorfou.github.io/back-office-lmelp/

## 🔗 Ressources

- **Images Docker** :
  - Backend : https://github.com/castorfou/back-office-lmelp/pkgs/container/lmelp-backend
  - Frontend : https://github.com/castorfou/back-office-lmelp/pkgs/container/lmelp-frontend
- **Repository GitHub** : https://github.com/castorfou/back-office-lmelp
- **Issues** : https://github.com/castorfou/back-office-lmelp/issues

## 📄 Licence

MIT - Voir [LICENSE](../LICENSE) pour plus de détails.
