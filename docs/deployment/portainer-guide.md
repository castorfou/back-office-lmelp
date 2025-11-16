# Guide de déploiement Portainer

## Prérequis

- Portainer installé sur le NAS Synology
- Accès administrateur à Portainer
- Images Docker publiées sur ghcr.io (via GitHub Actions)
- Conteneur MongoDB existant et fonctionnel

## Étape 1 : Vérifier le réseau Docker

Avant de créer la stack, vérifiez que le conteneur MongoDB est sur le bon réseau.

### Via Portainer

1. Accéder à **Containers**
2. Cliquer sur le conteneur **mongo**
3. Vérifier la section **Network** → doit afficher `bridge`

### Via Docker CLI (optionnel)

```bash
docker network inspect bridge | grep mongo -A 10
```

## Étape 2 : Créer la stack Portainer

### Accès à Portainer

1. Ouvrir Portainer : `http://<nas-ip>:9000` (ou port configuré)
2. Se connecter avec les identifiants administrateur
3. Sélectionner l'environnement **local**

### Création de la stack

1. Dans le menu latéral : **Stacks** → **Add stack**
2. **Name**: `lmelp-back-office`
3. **Build method**: Web editor
4. Copier le contenu de `docker/deployment/docker-compose.yml`

```yaml
version: '3.8'

services:
  backend:
    image: ghcr.io/castorfou/lmelp-backend:latest
    container_name: lmelp-backend
    restart: unless-stopped

    environment:
      MONGODB_URL: mongodb://mongo:27017/masque_et_la_plume
      ENVIRONMENT: production
      API_HOST: 0.0.0.0
      API_PORT: 8000

    networks:
      - lmelp-network

    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M

    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s

  frontend:
    image: ghcr.io/castorfou/lmelp-frontend:latest
    container_name: lmelp-frontend
    restart: unless-stopped

    ports:
      - "8080:80"

    depends_on:
      - backend

    networks:
      - lmelp-network

    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 128M

    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 5s

networks:
  lmelp-network:
    external: true
    name: bridge
```

5. Cliquer sur **Deploy the stack**

## Étape 3 : Vérifier le déploiement

### Statut des conteneurs

1. Accéder à **Stacks** → **lmelp-back-office**
2. Vérifier que les 2 conteneurs affichent **running** (vert)
3. Attendre que les healthchecks passent au vert (peut prendre 30 secondes)

### Logs des conteneurs

#### Backend
1. Cliquer sur **lmelp-backend**
2. Onglet **Logs**
3. Vérifier l'absence d'erreurs
4. Chercher le message de démarrage uvicorn :
   ```
   INFO:     Uvicorn running on http://0.0.0.0:8000
   ```

#### Frontend
1. Cliquer sur **lmelp-frontend**
2. Onglet **Logs**
3. Vérifier le démarrage nginx sans erreur

### Test de connectivité

#### Depuis le NAS (SSH)

Tester le backend :
```bash
curl http://localhost:8080/api
```

Résultat attendu :
```json
{"status": "ok", "message": "Welcome to Back Office LMELP API"}
```

#### Depuis un navigateur (réseau local)

Accéder à `http://<nas-ip>:8080`

Vérifier :
- Page d'accueil Vue.js s'affiche
- Recherche fonctionne
- Onglets de navigation fonctionnent

## Étape 4 : Configurer le webhook Portainer

Le webhook permet le déploiement automatique après chaque push sur GitHub.

### Créer le webhook

1. Dans Portainer : **Stacks** → **lmelp-back-office**
2. Cliquer sur l'icône **Webhook** (🔗)
3. Activer **Enable webhook**
4. Copier l'URL générée (format : `http://<nas-ip>:9000/api/webhooks/<token>`)

### Tester le webhook manuellement

```bash
curl -X POST "http://<nas-ip>:9000/api/webhooks/<token>"
```

Vérifier dans Portainer que la stack se redéploie (pull des dernières images).

### Configurer GitHub

1. Accéder au repository GitHub : `https://github.com/castorfou/back-office-lmelp`
2. **Settings** → **Secrets and variables** → **Actions**
3. Onglet **Secrets**
4. Cliquer **New repository secret**
5. **Name**: `PORTAINER_WEBHOOK_URL`
6. **Secret**: Coller l'URL du webhook Portainer
7. Cliquer **Add secret**

**Note** : On utilise un **secret** plutôt qu'une variable pour des raisons de sécurité, car l'URL du webhook donne accès au déploiement de votre stack.

### Tester le déploiement automatique

1. Faire un commit sur la branche `main`
2. Attendre que GitHub Actions build les images (~5-10 min)
3. Vérifier dans Portainer que la stack se redéploie automatiquement
4. Consulter les logs pour voir les nouvelles images téléchargées

## Étape 5 : Configuration avancée

### Variables d'environnement personnalisées

Pour modifier les variables d'environnement sans éditer le docker-compose :

1. **Stacks** → **lmelp-back-office** → **Editor**
2. Modifier les valeurs dans la section `environment`
3. Cliquer **Update the stack**
4. Sélectionner **Re-pull image and redeploy**

### Limites de ressources

Pour ajuster les limites CPU/RAM :

```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'        # Augmenter si nécessaire
      memory: 4G
    reservations:
      cpus: '1.0'
      memory: 1G
```

### Politique de redémarrage

Options disponibles :
- `no` : Ne jamais redémarrer automatiquement
- `always` : Toujours redémarrer (même après reboot NAS)
- `unless-stopped` : Redémarrer sauf si arrêt manuel (recommandé)
- `on-failure` : Redémarrer uniquement en cas d'erreur

## Troubleshooting

### Les conteneurs ne démarrent pas

**Symptôme** : Conteneurs en état `Exited` ou `Error`

**Solutions** :

1. Vérifier les logs Portainer
2. Vérifier que les images sont bien téléchargées (pas d'erreur réseau)
3. Vérifier le réseau `bridge` existe :
   ```bash
   docker network ls | grep bridge
   ```

### Backend ne peut pas se connecter à MongoDB

**Symptôme** : Logs backend affichent `Connection refused` ou `Unknown host`

**Solutions** :

1. Vérifier que le conteneur `mongo` est démarré :
   ```bash
   docker ps | grep mongo
   ```

2. Vérifier que `mongo` est sur le même réseau :
   ```bash
   docker inspect mongo | grep -A 5 Networks
   docker inspect lmelp-backend | grep -A 5 Networks
   ```

3. Tester la résolution DNS depuis le backend :
   ```bash
   docker exec lmelp-backend ping mongo
   ```

### Frontend affiche 502 Bad Gateway

**Symptôme** : Page d'accueil charge mais API retourne 502

**Solutions** :

1. Vérifier que le backend est healthy :
   ```bash
   docker ps | grep lmelp-backend
   ```

2. Tester la connexion depuis le frontend :
   ```bash
   docker exec lmelp-frontend curl http://backend:8000/
   ```

3. Vérifier la configuration nginx :
   ```bash
   docker exec lmelp-frontend cat /etc/nginx/conf.d/default.conf
   ```

### Le webhook ne se déclenche pas

**Symptôme** : Push sur GitHub mais pas de redéploiement

**Solutions** :

1. Vérifier que `PORTAINER_WEBHOOK_URL` est configuré dans GitHub
2. Consulter les logs GitHub Actions (onglet **Actions**)
3. Tester le webhook manuellement :
   ```bash
   curl -X POST "$PORTAINER_WEBHOOK_URL"
   ```

### Images non mises à jour après webhook

**Symptôme** : Webhook fonctionne mais anciennes images utilisées

**Solutions** :

1. Forcer le pull dans Portainer :
   - **Stacks** → **lmelp-back-office** → **Editor**
   - Cocher **Re-pull images and redeploy**
   - **Update the stack**

2. Vérifier que GitHub Actions a bien publié les nouvelles images :
   - https://github.com/castorfou/back-office-lmelp/pkgs/container/lmelp-backend
   - https://github.com/castorfou/back-office-lmelp/pkgs/container/lmelp-frontend

## Rollback vers une version précédente

### Identifier les versions disponibles

1. Accéder à GitHub Container Registry :
   - Backend : https://github.com/castorfou/back-office-lmelp/pkgs/container/lmelp-backend
   - Frontend : https://github.com/castorfou/back-office-lmelp/pkgs/container/lmelp-frontend

2. Noter le tag de la version souhaitée (ex: `v1.0.0`)

### Déployer une version spécifique

1. **Stacks** → **lmelp-back-office** → **Editor**
2. Modifier les tags d'images :
   ```yaml
   backend:
     image: ghcr.io/castorfou/lmelp-backend:v1.0.0  # Au lieu de :latest
   frontend:
     image: ghcr.io/castorfou/lmelp-frontend:v1.0.0
   ```
3. Cocher **Re-pull images and redeploy**
4. **Update the stack**

## Maintenance régulière

### Nettoyage des images inutilisées

Portainer accumule les anciennes images après chaque mise à jour.

1. **Images** → Sélectionner les images `<none>`
2. Cliquer **Remove**

Ou via CLI :
```bash
docker image prune -a
```

### Vérification des healthchecks

Consulter régulièrement les healthchecks dans Portainer :
- **Containers** → Colonne **Health** doit afficher vert

### Surveillance des logs

Activer les alertes Portainer pour :
- Conteneur arrêté
- Healthcheck échoué
- Utilisation RAM > 80%

## Prochaines étapes

- [Guide de mise à jour](update-guide.md)
- [Troubleshooting avancé](troubleshooting.md)
