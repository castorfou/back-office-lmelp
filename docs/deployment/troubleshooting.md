# Troubleshooting - Diagnostic et résolution de problèmes

## Outils de diagnostic

### Accès aux logs

#### Via Portainer
1. **Containers** → Sélectionner le conteneur
2. Onglet **Logs**
3. Utiliser les filtres pour rechercher des erreurs

#### Via Docker CLI (SSH)
```bash
# Logs en temps réel
docker logs -f lmelp-backend
docker logs -f lmelp-frontend

# Dernières 100 lignes
docker logs --tail 100 lmelp-backend

# Logs depuis 1 heure
docker logs --since 1h lmelp-backend
```

### Inspecter un conteneur

```bash
# Informations détaillées
docker inspect lmelp-backend

# Vérifier le réseau
docker inspect lmelp-backend | grep -A 10 Networks

# Vérifier les variables d'environnement
docker inspect lmelp-backend | grep -A 20 Env
```

### Exécuter des commandes dans un conteneur

```bash
# Shell interactif backend
docker exec -it lmelp-backend /bin/bash

# Shell interactif frontend
docker exec -it lmelp-frontend /bin/sh

# Commande unique
docker exec lmelp-backend curl http://localhost:8000/
```

### Vérifier les healthchecks

```bash
# Statut complet avec healthcheck
docker ps --format "table {{.Names}}\t{{.Status}}"

# Inspecter le healthcheck
docker inspect --format='{{json .State.Health}}' lmelp-backend | jq
```

## Problèmes courants

### Backend ne démarre pas

#### Symptôme
```
docker ps | grep lmelp-backend
# Aucun résultat ou status "Exited"
```

#### Causes possibles et solutions

**1. Erreur MongoDB connection**

Logs affichent :
```
pymongo.errors.ServerSelectionTimeoutError: mongo:27017
```

Solutions :
```bash
# Vérifier que MongoDB est démarré
docker ps | grep mongo

# Vérifier le réseau
docker network inspect bridge | grep -E "mongo|lmelp-backend"

# Tester la résolution DNS
docker exec lmelp-backend ping mongo

# Vérifier la variable d'environnement
docker inspect lmelp-backend | grep MONGODB_URL
```

**2. Port déjà utilisé**

Logs affichent :
```
OSError: [Errno 98] Address already in use
```

Solutions :
```bash
# Trouver quel processus utilise le port
netstat -tulpn | grep 8000

# Changer le port dans docker-compose ou arrêter le processus conflictuel
```

**3. Image corrompue**

Solutions :
```bash
# Supprimer l'image locale
docker rmi ghcr.io/castorfou/lmelp-backend:latest

# Re-télécharger
docker pull ghcr.io/castorfou/lmelp-backend:latest

# Redémarrer depuis Portainer
```

### Frontend affiche page blanche

#### Symptôme
Browser affiche une page blanche ou erreur 404

#### Diagnostic

```bash
# Vérifier que nginx démarre
docker logs lmelp-frontend | grep nginx

# Vérifier les fichiers statiques
docker exec lmelp-frontend ls -la /usr/share/nginx/html
```

#### Solutions

**1. Build frontend échoué**

Vérifier GitHub Actions :
- https://github.com/castorfou/back-office-lmelp/actions
- Consulter les logs du job `build-frontend`

**2. nginx mal configuré**

```bash
# Tester la configuration nginx
docker exec lmelp-frontend nginx -t

# Vérifier nginx.conf
docker exec lmelp-frontend cat /etc/nginx/conf.d/default.conf

# Recopier la bonne configuration si nécessaire
```

**3. Permissions fichiers**

```bash
# Vérifier les permissions
docker exec lmelp-frontend ls -la /usr/share/nginx/html

# Si problème de permissions, rebuild l'image
```

### API retourne 502 Bad Gateway

#### Symptôme
Frontend charge mais les appels API retournent 502

#### Diagnostic

```bash
# Tester l'API depuis le frontend
docker exec lmelp-frontend curl http://backend:8000/

# Vérifier que backend répond
docker exec lmelp-backend curl http://localhost:8000/
```

#### Solutions

**1. Backend n'est pas healthy**

```bash
# Vérifier le healthcheck
docker ps | grep lmelp-backend
# Si "unhealthy", consulter les logs

docker logs lmelp-backend | tail -50
```

**2. Problème de réseau**

```bash
# Vérifier que frontend et backend sont sur le même réseau
docker network inspect bridge

# Vérifier la résolution DNS
docker exec lmelp-frontend ping backend
```

**3. Timeout nginx**

Si les requêtes sont lentes, augmenter les timeouts dans `nginx.conf` :

```nginx
proxy_connect_timeout 120s;
proxy_send_timeout 120s;
proxy_read_timeout 120s;
```

### Webhook Portainer ne fonctionne pas

#### Symptôme
Push sur GitHub mais pas de redéploiement automatique

#### Diagnostic

```bash
# Tester le webhook manuellement
curl -X POST "http://<nas-ip>:9000/api/webhooks/<token>"

# Vérifier les logs GitHub Actions
# https://github.com/castorfou/back-office-lmelp/actions
```

#### Solutions

**1. URL webhook mal configurée**

Vérifier dans GitHub :
- **Settings** → **Secrets and variables** → **Actions** → **Variables**
- `PORTAINER_WEBHOOK_URL` doit être exacte (pas de slash final)

**2. Portainer n'est pas accessible depuis Internet**

Si GitHub Actions ne peut pas atteindre le webhook :
- Vérifier que Portainer est accessible depuis Internet
- Ou configurer un tunnel/VPN
- Ou désactiver le webhook et déployer manuellement

**3. Webhook désactivé dans Portainer**

Vérifier dans Portainer :
- **Stacks** → **lmelp-back-office** → **Webhook**
- **Enable webhook** doit être coché

### Images non mises à jour

#### Symptôme
Webhook fonctionne mais anciennes images utilisées

#### Diagnostic

```bash
# Vérifier la version de l'image utilisée
docker inspect lmelp-backend | grep "Image"

# Comparer avec ghcr.io
# https://github.com/castorfou/back-office-lmelp/pkgs/container/lmelp-backend
```

#### Solutions

**1. Cache Docker**

```bash
# Forcer le re-pull dans Portainer
# Stacks → lmelp-back-office → Editor
# Cocher "Re-pull images and redeploy"

# Ou en CLI
docker pull ghcr.io/castorfou/lmelp-backend:latest
docker pull ghcr.io/castorfou/lmelp-frontend:latest
```

**2. Tag latest non mis à jour**

Vérifier dans GitHub Actions que le build a réussi :
- Workflow **Docker Build and Publish** doit être vert ✅

### Performance dégradée

#### Symptôme
Application lente, timeouts fréquents

#### Diagnostic

```bash
# Vérifier l'utilisation ressources
docker stats lmelp-backend lmelp-frontend

# Vérifier les limites configurées
docker inspect lmelp-backend | grep -A 10 Memory
```

#### Solutions

**1. Limite RAM atteinte**

Si le conteneur utilise 100% de sa RAM allouée :

```yaml
# Augmenter dans docker-compose.prod.yml
deploy:
  resources:
    limits:
      memory: 4G  # Au lieu de 2G
```

**2. CPU insuffisant**

```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'  # Au lieu de 1.0
```

**3. MongoDB lent**

```bash
# Vérifier les performances MongoDB
docker exec mongo mongosh --eval "db.serverStatus().connections"

# Vérifier les index
docker exec mongo mongosh masque_et_la_plume --eval "db.livres.getIndexes()"
```

**4. Trop de logs**

Configurer la rotation des logs :

```bash
# Éditer /etc/docker/daemon.json sur le NAS
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}

# Redémarrer Docker
sudo systemctl restart docker
```

### Application inaccessible depuis Internet

#### Symptôme
Application fonctionne en local mais pas via `lmelp.ascot63.synology.me`

#### Diagnostic

```bash
# Tester en local
curl http://<nas-ip>:8080

# Tester depuis Internet (depuis un autre réseau)
curl https://lmelp.ascot63.synology.me
```

#### Solutions

**1. Reverse proxy Synology mal configuré**

Vérifier dans DSM :
- **Control Panel** → **Login Portal** → **Advanced** → **Reverse Proxy**
- Créer une règle :
  - Source : `lmelp.ascot63.synology.me`, port 443
  - Destination : `localhost`, port 8080

**2. Certificat SSL invalide**

Vérifier le certificat dans DSM :
- **Control Panel** → **Security** → **Certificate**
- Renouveler Let's Encrypt si expiré

**3. Pare-feu bloque le trafic**

Vérifier dans DSM :
- **Control Panel** → **Security** → **Firewall**
- Autoriser le port 443 (HTTPS)

**4. DNS mal configuré**

Vérifier la résolution DNS :
```bash
nslookup lmelp.ascot63.synology.me
# Doit retourner l'IP publique du NAS
```

### Erreurs MongoDB

#### Symptôme
Logs backend affichent des erreurs MongoDB

#### Erreurs courantes

**1. Connection refused**

```
pymongo.errors.ServerSelectionTimeoutError
```

Solutions :
```bash
# Vérifier que MongoDB est démarré
docker ps | grep mongo
docker start mongo

# Vérifier le port
docker port mongo
```

**2. Authentication failed**

```
pymongo.errors.OperationFailure: Authentication failed
```

Solutions :
```bash
# Si MongoDB a l'authentification activée, mettre à jour MONGODB_URL
MONGODB_URL=mongodb://username:password@mongo:27017/masque_et_la_plume # pragma: allowlist secret

**3. Database not found**

Créer la base de données :
```bash
docker exec -it mongo mongosh
use masque_et_la_plume
db.createCollection("livres")
exit
```

## Procédures de maintenance

### Redémarrage complet

```bash
# Arrêter tous les conteneurs
docker stop lmelp-frontend lmelp-backend

# Redémarrer
docker start lmelp-backend
sleep 5  # Attendre que backend démarre
docker start lmelp-frontend
```

### Nettoyage espace disque

```bash
# Supprimer les images inutilisées
docker image prune -a

# Supprimer les conteneurs arrêtés
docker container prune

# Supprimer les volumes inutilisés (ATTENTION: ne pas supprimer mongo-data)
docker volume ls
docker volume prune  # Confirmer avant
```

### Mise à jour forcée

```bash
# Forcer le téléchargement des dernières images
docker pull ghcr.io/castorfou/lmelp-backend:latest
docker pull ghcr.io/castorfou/lmelp-frontend:latest

# Recréer les conteneurs depuis Portainer
# Stacks → lmelp-back-office → Update → Re-pull and redeploy
```

### Backup de configuration

Sauvegarder régulièrement :

```bash
# Exporter la stack Portainer
# Stacks → lmelp-back-office → Editor → Copier le YAML

# Sauvegarder les variables d'environnement
docker inspect lmelp-backend | grep -A 20 Env > backend-env-backup.txt
```

## Commandes utiles

### Monitoring en temps réel

```bash
# Stats ressources
docker stats

# Logs en direct
docker logs -f lmelp-backend

# Events Docker
docker events --filter container=lmelp-backend
```

### Tests de connectivité

```bash
# Test backend depuis NAS
curl http://localhost:8080/api

# Test backend depuis frontend
docker exec lmelp-frontend curl http://backend:8000/

# Test MongoDB depuis backend
docker exec lmelp-backend curl http://mongo:27017/
```

### Inspection réseau

```bash
# Lister les réseaux
docker network ls

# Inspecter le réseau bridge
docker network inspect bridge

# Vérifier les IP des conteneurs
docker network inspect bridge | grep -E "Name|IPv4"
```

## Contact et escalade

### Documentation

- [Docker Setup](docker-setup.md)
- [Portainer Guide](portainer-guide.md)
- [Update Guide](update-guide.md)

### Support GitHub

Créer une issue : https://github.com/castorfou/back-office-lmelp/issues

Inclure :
- Description du problème
- Logs backend/frontend
- Output de `docker ps`
- Résultat des tests de diagnostic

### Logs à fournir

```bash
# Collecter tous les logs
docker logs lmelp-backend > backend.log 2>&1
docker logs lmelp-frontend > frontend.log 2>&1
docker ps -a > containers-status.txt
docker network inspect bridge > network-info.txt

# Créer une archive
tar -czf debug-logs.tar.gz *.log *.txt
```
