# Déploiement Production Back-Office LMELP

Ce répertoire contient la configuration pour déployer **back-office-lmelp** via Portainer en utilisant votre **MongoDB existant**.

## 📦 Contenu

- **docker-compose.yml** : Configuration production (MongoDB externe)
- **.env.template** : Template de configuration à personnaliser
- **README.md** : Ce fichier

## 📋 Prérequis

- Docker et Docker Compose installés
- Portainer installé et accessible (http://localhost:9000 ou https://localhost:9443)
- **MongoDB déjà installé** (sur l'hôte ou dans un conteneur Docker)

## 🔧 Configuration

### 1. Créer votre fichier .env local

```bash
# Créer un répertoire pour votre config
mkdir -p ~/bin/back-office-lmelp/docker
cd ~/bin/back-office-lmelp/docker

# Copier le template depuis le repo Git
cp /path/to/back-office-lmelp/deployment/.env.template .env

# Sécuriser le fichier
chmod 600 .env

# Éditer avec votre configuration
nano .env
```
### 2. Configurer les variables obligatoires

Éditez `.env` et configurez selon votre environnement :

**NAS Synology avec conteneur mongo existant :**
```env
MONGODB_URL=mongodb://mongo:27017/masque_et_la_plume
FRONTEND_PORT=8080
```

**PC Linux avec MongoDB sur l'hôte :**
```env
MONGODB_URL=mongodb://172.17.0.1:27017/masque_et_la_plume
FRONTEND_PORT=8080
```

**PC Mac/Windows avec MongoDB sur l'hôte :**
```env
MONGODB_URL=mongodb://host.docker.internal:27017/masque_et_la_plume
FRONTEND_PORT=8080
```

**MongoDB distant :**
```env
MONGODB_URL=mongodb://192.168.1.100:27017/masque_et_la_plume
FRONTEND_PORT=8080
```

**Propriétaire des fichiers sur le volume de cache** (évite des fichiers `root:root`) :
```env
PUID=1000  # ← Remplacer par votre UID (ex: 1027 sur NAS) - trouvez le vôtre avec `id -u`
PGID=1000  # ← Remplacer par votre GID - trouvez le vôtre avec `id -g`
```

**Vérifier que MongoDB est accessible :**
```bash
# Test de connexion
mongosh --host localhost --port 27017 --eval "db.adminCommand('ping')"
```

## 🔑 Personal Access Token GitHub

### Créer un token (une seule fois)

Cette étape est nécessaire pour déployer via Git Repository dans Portainer.

1. Aller sur : https://github.com/settings/tokens/new
2. **Note** : "Portainer back-office-lmelp deployment"
3. **Expiration** : No expiration (ou selon vos préférences de sécurité)
4. **Scopes** : Cocher **`repo`** (Full control of private repositories)
   - Même si le repo est public, ce scope est requis par Portainer
5. Cliquer **Generate token**
6. **Copier le token** (vous ne pourrez plus le voir après)

⚠️ **Conservez ce token en sécurité** - Il donne accès à vos repositories GitHub

## 🚀 Déploiement dans Portainer

### Via Git Repository

Cette méthode permet les mises à jour automatiques via webhook ou pull manuel.

**1. Créer un Personal Access Token GitHub (une seule fois)**

- Aller sur : https://github.com/settings/tokens/new
- **Note** : "Portainer lmelp deployment"
- **Expiration** : No expiration (ou selon vos préférences)
- **Scopes** : Cocher `repo` (Full control of private repositories)
- **Generate token** et **copier le token**

**2. Déployer la stack dans Portainer**

- **Stacks** → **Add stack**
- **Name** : `lmelp-back-office`
- **Build method** : **Repository**
- **Authentication** : **On**
  - **Username** : votre_username_github
  - **Personal Access Token** : coller le token créé à l'étape 1
- **Repository URL** : `https://github.com/castorfou/back-office-lmelp`
- **Repository reference** : `refs/heads/main`
- **Compose path** : `deployment/docker-compose.yml`
- **Environment variables** :
  - Cocher **"Load variables from .env file"**
  - Cliquer sur **"Upload"** et sélectionner votre fichier `.env`
  - ✅ Portainer va automatiquement charger toutes les variables
- **Deploy the stack**

**3. Vérifier le déploiement**

- Accéder à l'application : **http://localhost:5173**
- Vérifier les logs : `docker logs lmelp-backend`, `docker logs lmelp-frontend`
- Healthchecks:
  ```bash
  docker ps --format "table {{.Names}}\t{{.Status}}"
  # Les 2 conteneurs doivent afficher (healthy)
  ```

Cette méthode permet les mises à jour automatiques via webhook (watchtower) ou pull manuel.


**3. Configurer reverse proxy Synology (optionnel)**

DSM → **Control Panel** → **Login Portal** → **Advanced** → **Reverse Proxy**

Créer une règle :
- **Source** : `lmelp-backoffice.ascot63.synology.me` (port 443, HTTPS)
- **Destination** : `localhost` (port 5173, HTTP)

Accès final : `https://lmelp-backoffice.ascot63.synology.me`

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

### Erreur "reference not found" lors du déploiement Git Repository

**Symptôme :**
```
Unable to clone git repository: failed to clone git repository: reference not found
```

**Cause :** La référence de branche est mal saisie dans Portainer.

**Solution :** Vérifiez le champ **Repository reference** dans Portainer :

- ✅ **Correct** : `refs/heads/main` (ou `refs/heads/nom-de-votre-branche`)
- ❌ **Incorrect** :
  - `main` (sans préfixe `refs/heads/`)
  - `ref/heads/main` (faute de frappe : `ref` au lieu de `refs`)
  - `refs/head/main` (faute de frappe : `head` au lieu de `heads`)

**Exemples de références valides :**
- Branche main : `refs/heads/main`
- Branche de développement : `refs/heads/feature/ma-branche`
- Tag : `refs/tags/v1.0.0`

**Astuce** : Copiez-collez la référence depuis cette documentation pour éviter les erreurs de frappe.

### Erreur "manifest unknown" (image non trouvée)

**Symptôme :**
```
Error response from daemon: manifest for ghcr.io/castorfou/lmelp-backend:latest not found
```

**Cause :** Les images Docker n'ont pas encore été publiées sur GitHub Container Registry.

**Solution :**
1. Vérifier que le workflow GitHub Actions a bien été exécuté : https://github.com/castorfou/back-office-lmelp/actions
2. S'assurer que les packages sont publics :
   - Backend : https://github.com/castorfou/back-office-lmelp/pkgs/container/lmelp-backend
   - Frontend : https://github.com/castorfou/back-office-lmelp/pkgs/container/lmelp-frontend
3. Si les packages existent mais sont privés, les rendre publics dans les settings du package

### Backend ne se connecte pas à MongoDB

**Symptôme :** Logs affichent `Connection refused` ou `Unknown host`

**Solutions :**

```bash
# 2. Vérifier la résolution DNS
docker exec lmelp-backend ping mongo

# 3. Tester la connexion
docker exec lmelp-backend curl http://mongo:27017

# 4. Vérifier MONGODB_URL
docker inspect lmelp-backend | grep MONGODB_URL
```

### Fichiers root:root sur le volume de cache Babelio

Depuis [#258](https://github.com/castorfou/back-office-lmelp/issues/258), le
conteneur backend tourne sous un utilisateur non-root dont l'UID/GID sont
configurables via `PUID`/`PGID` dans votre `.env` (défaut : `1000`/`1000` si
non défini).

**Si vous avez déjà des fichiers `root:root` sur votre volume de cache**
(créés avant ce fix, ou avec un `PUID`/`PGID` mal configuré) : un simple
redémarrage du conteneur suffit à corriger leur propriété — le conteneur
ajuste automatiquement les permissions vers `PUID`/`PGID` à chaque démarrage.

```bash
# 1. Vérifiez/ajustez PUID et PGID dans votre .env (id -u / id -g)
# 2. Redémarrez le conteneur
docker restart lmelp-backend
# 3. Vérifiez côté hôte que les fichiers appartiennent bien à votre utilisateur
ls -la /chemin/vers/votre/cache/babelio/
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

### Port 8080 déjà utilisé

**Symptôme :**
```
Error: bind: address already in use
```

**Cause :** Un autre service utilise déjà le port 8080.

**Solutions :**

**Option 1 : Modifier le port dans .env (recommandé)**
```bash
# Dans votre fichier .env
FRONTEND_PORT=8081  # Ou tout autre port disponible
```

Puis redéployer la stack dans Portainer.

**Option 2 : Modifier directement dans docker-compose.yml**
```yaml
ports:
  - "8081:80"  # Utiliser le port 8081 à la place
```

**Trouver quel processus utilise le port :**
```bash
# Linux/Mac
lsof -i :8080

# Arrêter le processus si nécessaire
sudo kill <PID>
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
