# Issue #115 - Backend: Logs pollués par healthchecks + améliorer format de log

**Date**: 2025-11-26 12:41
**Issue**: [#115 - Backend: Logs pollués par healthchecks + améliorer format de log](https://github.com/castorfou/back-office-lmelp/issues/115)
**Status**: Implémenté, testé avec succès

## Contexte

Suite à l'[Issue #111](https://github.com/castorfou/back-office-lmelp/issues/111) qui a résolu le problème pour le frontend nginx, le backend FastAPI souffrait du même problème : les logs uvicorn étaient pollués par les healthchecks Docker (toutes les 30 secondes = ~120 lignes/heure sans valeur).

## Problèmes identifiés

1. **Logs pollués** : Les healthchecks répétés rendaient difficile l'identification des vraies requêtes utilisateur
2. **Format de log pauvre** : Le format uvicorn par défaut manquait d'informations utiles (timestamp détaillé, user-agent, taille de réponse, temps de traitement)

**Ancien format** :
```
INFO:     127.0.0.1:50936 - "GET / HTTP/1.1" 200 OK
```

## Solution implémentée

### 1. Endpoint `/health` dédié

**Fichier**: [app.py:204-212](src/back_office_lmelp/app.py#L204-L212)

```python
@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint for Docker healthchecks (Issue #115).

    This endpoint is designed for automated monitoring and Docker healthchecks.
    It returns a simple status without database connectivity check to keep
    response time minimal and avoid polluting logs.
    """
    return {"status": "ok"}
```

**Avantages** :
- Simple et rapide (< 100ms)
- Pas de vérification MongoDB pour minimiser le temps de réponse
- Compatible backward (l'endpoint `/` continue de fonctionner)

### 2. Middleware de logging enrichi

**Fichier**: [middleware/logging_middleware.py](src/back_office_lmelp/middleware/logging_middleware.py)

Nouveau module avec un middleware FastAPI custom qui :
- **Filtre automatiquement `/health`** du logging (pas de pollution)
- **Format enrichi** similaire à nginx :
  ```
  2025-11-26T11:41:13+0000 "GET /api/stats HTTP/1.1" 200 166 0.008s "curl/7.74.0"
  ```
- **Logging adaptatif** : INFO pour 2xx/3xx, WARNING pour 4xx, ERROR pour 5xx

**Éléments du format** :
- Timestamp ISO 8601 avec timezone
- Méthode et chemin HTTP
- Code statut
- Taille de la réponse (bytes)
- Temps de traitement (secondes)
- User-Agent

### 3. Configuration du logger

**Fichier**: [app.py:165-173](src/back_office_lmelp/app.py#L165-L173)

Configuration explicite du logger `back_office_lmelp.access` avec un handler console pour afficher les logs dans stdout.

### 4. Tests complets

**Nouveaux fichiers** :
- [tests/test_health_endpoint.py](tests/test_health_endpoint.py) : 4 tests pour `/health`
- [tests/test_logging_middleware.py](tests/test_logging_middleware.py) : 7 tests pour le middleware

**Coverage** : 96% sur le middleware, tous les tests passent (585 passed)

## Tests effectués

### Test 1 : Endpoint `/health`
```bash
curl http://localhost:54321/health
# Résultat : {"status":"ok"}
# Temps : < 100ms
```

### Test 2 : Format de log enrichi
```bash
# Requêtes de test
curl http://localhost:54321/
curl http://localhost:54321/api/stats

# Logs observés :
2025-11-26T11:41:13+0000 "GET / HTTP/1.1" 200 53 0.001s "curl/7.74.0"
2025-11-26T11:41:13+0000 "GET /api/stats HTTP/1.1" 200 166 0.008s "curl/7.74.0"
```

### Test 3 : Filtrage `/health`
```bash
# 5 appels à /health
for i in {1..5}; do curl -s http://localhost:54321/health > /dev/null; done

# Résultat : AUCUNE ligne de log pour /health ✅
```

## Apprentissages

### 1. Middleware FastAPI pour logging custom

**Pattern utilisé** :
```python
from starlette.middleware.base import BaseHTTPMiddleware

class EnrichedLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # Filtrer certains endpoints
        if request.url.path == "/health":
            return await call_next(request)

        # Mesurer le temps
        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time

        # Logger avec format custom
        access_logger.info(log_message)

        return response
```

### 2. Configuration du logger Python

**Important** : Le logger custom doit être configuré explicitement avec un handler console :
```python
access_logger = logging.getLogger("back_office_lmelp.access")
access_logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
access_logger.addHandler(console_handler)
access_logger.propagate = False  # Éviter duplication
```

### 3. Type hints pour middleware

MyPy nécessite des annotations précises pour les middlewares :
```python
from collections.abc import Awaitable, Callable

async def dispatch(
    self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
```

### 4. Approche TDD validée

**RED → GREEN → REFACTOR** :
1. ✅ Écriture des tests qui échouent (RED)
2. ✅ Implémentation minimale pour passer les tests (GREEN)
3. ✅ Refactoring et amélioration du code
4. ✅ Vérification lint/typecheck

### 5. IP source non pertinente

Décision de ne **pas inclure l'IP source** dans le format de log car :
- Les requêtes passent par le proxy nginx frontend
- L'IP serait toujours celle du container frontend, pas celle du client final
- Simplifie le format et réduit le bruit

## Déploiement

**Déploiement en 2 étapes** (comme pour Issue #111) :

1. **back-office-lmelp** (cette issue) : ✅ Endpoint `/health` + middleware de logging enrichi
2. **docker-lmelp** (à faire) : Modifier le healthcheck Docker pour utiliser `/health`

```yaml
# À ajouter dans docker-compose.yml (repository docker-lmelp)
healthcheck:
  test: ["CMD", "curl", "-f", "http://backend:8000/health"]
  interval: 30s
  timeout: 10s
  start_period: 5s
  retries: 3
```

⚠️ **Important** : Déployer back-office-lmelp EN PREMIER pour assurer la compatibilité backward.

## Fichiers modifiés

### Nouveaux fichiers
- `src/back_office_lmelp/middleware/__init__.py`
- `src/back_office_lmelp/middleware/logging_middleware.py`
- `tests/test_health_endpoint.py`
- `tests/test_logging_middleware.py`

### Fichiers modifiés
- `src/back_office_lmelp/app.py` : Import logging, configuration logger, endpoint `/health`, ajout middleware

## Avantages

1. **Logs propres** : Seules les vraies requêtes utilisateur sont loggées
2. **Format enrichi** : Plus d'informations pour le debugging et monitoring
3. **Performance** : `/health` est ultra-rapide (pas de DB check)
4. **Cohérence** : Même approche que le frontend nginx (Issue #111)
5. **Best practice** : Endpoint `/health` est un standard industriel
6. **Monitoring** : Le format enrichi facilite l'analyse des logs

## Statistiques

- **Tests** : 585 passed, 22 skipped
- **Nouveaux tests** : 11 (4 pour `/health`, 7 pour middleware)
- **Coverage** : 78% global, 96% sur le middleware
- **Lint** : ✅ Ruff OK
- **Type check** : ✅ MyPy OK

## Référence

- Issue #115 (backend) : https://github.com/castorfou/back-office-lmelp/issues/115
- Issue #111 (frontend) : https://github.com/castorfou/back-office-lmelp/issues/111
- Documentation Issue #111 : `docs/claude/memory/251125-0653-issue111-nginx-health-endpoint.md`

## Prochaines étapes

1. ✅ Implémentation backend (cette issue)
2. ⏳ Mettre à jour docker-lmelp pour utiliser `/health`
3. ⏳ Vérifier en production que les logs ne sont plus pollués
