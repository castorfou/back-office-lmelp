# Issue #111 - Nginx Health Endpoint Implementation

**Date**: 2025-11-25 06:53
**Issue**: [#111 - Configure nginx to not log healthcheck requests](https://github.com/castorfou/back-office-lmelp/issues/111)
**Status**: Implémenté, en attente de commit/PR

## Problème

Les logs nginx du conteneur frontend sont pollués par les healthchecks Docker (toutes les 30 secondes = ~120 lignes/heure sans valeur).

```
127.0.0.1 - - [23/Nov/2025:17:13:19 +0000] "GET / HTTP/1.1" 200 915 "-" "curl/8.14.1"
```

## Solution Retenue

**Option 2 : Endpoint `/health` dédié** (préféré à l'option 1 qui filtrait par IP localhost, car l'utilisateur accède aussi depuis localhost)

### Avantages
- Séparation des préoccupations (endpoint standardisé)
- Flexibilité pour enrichir le healthcheck plus tard
- Best practice largement adoptée
- Meilleure maintenabilité

## Implémentation

### 1. Configuration Nginx

**Fichier**: `docker/build/frontend/nginx.conf` (lines 14-19)

```nginx
# Health check endpoint (not logged)
location /health {
    access_log off;
    return 200 "OK\n";
    add_header Content-Type text/plain;
}
```

### 2. Script de Test

**Fichier**: `docker/build/frontend/test-health-endpoint.sh`

Script shell automatisé pour vérifier :
- `/health` retourne 200 OK avec body "OK"
- `/` continue de fonctionner
- Instructions pour vérifier le comportement de logging

### 3. Documentation

**Fichier**: `docker/build/frontend/TESTING.md`

Guide complet avec :
- Tests automatisés et manuels
- Vérification du comportement de logging
- Troubleshooting
- Instructions pour l'intégration Docker

## Points d'Attention

### 1. Déploiement en Deux Étapes

Cette modification nécessite une coordination entre deux repositories :

1. **back-office-lmelp** (cette PR) : Ajoute le endpoint `/health`
2. **docker-lmelp** ([Issue #5](https://github.com/castorfou/docker-lmelp/issues/5)) : Modifie le healthcheck pour utiliser `/health`

⚠️ **Important** : Déployer back-office-lmelp EN PREMIER, puis mettre à jour docker-lmelp.

### 2. Configuration Docker à Modifier

Dans `docker-compose.yml` (repository docker-lmelp) :

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost/health"]
  interval: 30s
  timeout: 10s
  start_period: 5s
  retries: 3
```

## Tests Effectués

- ✅ Syntaxe shell validée
- ✅ Tests frontend : 315 passed
- ✅ Tests backend : 574 passed
- ⏳ Tests de production nginx : nécessite le conteneur Docker en production

## Apprentissages

### Configuration Nginx pour Healthchecks

Pattern standard pour les healthchecks :
```nginx
location /health {
    access_log off;           # Ne pas logger
    return 200 "OK\n";        # Réponse simple
    add_header Content-Type text/plain;
}
```

### Pourquoi Éviter le Filtrage par IP

L'option 1 proposait :
```nginx
map $remote_addr $loggable {
    127.0.0.1 0;
    default 1;
}
```

❌ **Problème** : Bloque aussi les requêtes de l'utilisateur depuis localhost en développement.

### Tests de Configuration Nginx

Pour tester une configuration nginx :
```bash
# Syntaxe locale (si nginx installé)
nginx -t -c /path/to/nginx.conf

# Dans un conteneur
docker exec <container> nginx -t
```

### Coordination Multi-Repository

Lors d'un changement qui impacte plusieurs repositories :
1. Implémenter d'abord le changement compatible backward
2. Documenter les dépendances dans les issues respectives
3. Créer un commentaire dans l'issue liée avec les instructions
4. Déployer dans l'ordre : backend/frontend → configuration Docker

## Fichiers Modifiés

- `docker/build/frontend/nginx.conf` : Ajout du endpoint `/health`
- `docker/build/frontend/test-health-endpoint.sh` : Script de test (nouveau)
- `docker/build/frontend/TESTING.md` : Documentation de test (nouveau)

## Référence Croisée

- Issue back-office-lmelp : #111
- Issue docker-lmelp : castorfou/docker-lmelp#5
- Commentaire ajouté : https://github.com/castorfou/docker-lmelp/issues/5#issuecomment-3574008010

## Prochaines Étapes

1. Mettre à jour la documentation si nécessaire
2. Commit et push
3. Vérifier la CI/CD
4. Créer la PR
5. Après merge : Mettre à jour docker-lmelp pour utiliser `/health`
