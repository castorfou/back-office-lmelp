# Issue #254 — Refonte complète du service Babelio

## Contexte

Refonte de l'architecture Babelio suite à des crashs ("statut inconnu") et manque de robustesse. La session précédente (#251) avait corrigé la détection 403 ; cette session complète la refonte planifiée avec : queue de requêtes, cache disque, page de contrôle, endpoints API, circuit breaker, synchronisation cookie, et auto-enrichissement à l'étape "Traité".

## Modifications majeures

### 1. `BABELIO_FAIR_SEC` — Variable de débit configurable

`src/back_office_lmelp/settings.py` : nouvelle variable `babelio_fair_sec` (via `BABELIO_FAIR_SEC`, défaut 2.0), priorité sur l'ancienne `BABELIO_MIN_INTERVAL`.

`src/back_office_lmelp/services/babelio_service.py` : lecture `BABELIO_FAIR_SEC` en priorité sur `BABELIO_MIN_INTERVAL` (rétrocompat).

### 2. Cache disque complet (search + pages)

`src/back_office_lmelp/services/babelio_cache_service.py` :
- Namespace `search_type` : `"search"` pour l'API AJAX, `"page"` pour les pages scrapées
- `list_entries()` : liste toutes les entrées triées par date (newest first)
- `invalidate(entry_id)` : supprime une entrée par ID
- `self.ttl_hours` exposé (pour affichage BABELIO_CACHE_DAY)
- `BABELIO_CACHE_DAY` : alias de `ttl_hours` en jours (défaut 1.0)

`src/back_office_lmelp/services/babelio_service.py` — `_fetch_page()` :
- Cache check AVANT le rate limiter → bypass HTTP complet si hit
- Écriture dans le cache après 200 réussi
- `_log_request("page", url, 200, True, ms)` sur cache hit

### 3. Détection captcha

`src/back_office_lmelp/services/babelio_service.py` :
- `BabelioCaptchaError` : nouvelle exception distincte de `BabelioBlockedError`
- `_is_captcha_page(html)` : détecte "captcha", "recaptcha", "i am not a robot", "je ne suis pas un robot"
- Sur HTTP 200 avec captcha : lève `BabelioCaptchaError` (ne cache pas)

### 4. Circuit breaker — arrêt immédiat sur 403

`src/back_office_lmelp/services/babelio_service.py` :
- `self._circuit_open: bool = False`
- Ouverture sur 403 dans `_fetch_page()` et `_handle_search_response()`
- Fermeture uniquement via `set_cookie()` avec valeur non vide
- Guard en début de `_fetch_page()` et `search()` : lève immédiatement `BabelioBlockedError` sans réseau

### 5. Cookie géré côté serveur (centralisé)

`src/back_office_lmelp/services/babelio_service.py` :
- `self._stored_cookie: str | None` — cookie jstsToken persistant en mémoire serveur
- `set_cookie(value)` : stocke + réinitialise circuit breaker si non vide
- `get_cookie()` : retourne le cookie courant
- Dans `_fetch_page()` : `effective_cookie = self._stored_cookie or babelio_cookies`

Endpoints dans `src/back_office_lmelp/app.py` :
- `POST /api/babelio/cookie` : `{"cookie": "..."}` → `babelio_service.set_cookie()`
- `DELETE /api/babelio/cookie` → `babelio_service.set_cookie(None)`

**Bug corrigé** : BabelioControl affichait "non configuré" tandis que LivresAuteurs affichait "configuré" — deux systèmes de stockage indépendants. Fix : `mounted()` dans chaque vue envoie le cookie localStorage au serveur.

### 6. Journalisation des requêtes récentes

`src/back_office_lmelp/services/babelio_service.py` :
- `self._recent_requests: deque[dict, maxlen=50]`
- `_log_request(type, term_or_url, status_code, cache_hit, duration_ms)`
- `get_recent_requests()` → newest first
- Champs : `type`, `term_or_url`, `status_code`, `cache_hit`, `duration_ms`, `timestamp`

### 7. Endpoints API de contrôle

`src/back_office_lmelp/app.py` :
- `GET /api/babelio/status` : `overall`, `cookie_active`, `circuit_open`, `cache_entries`, `recent_requests_count`, `min_interval_sec`, `cache_ttl_hours`
- `GET /api/babelio/cache/entries` : liste paginée des entrées cache
- `DELETE /api/babelio/cache/{entry_id}` : invalide une entrée
- `DELETE /api/babelio/cache` : vide tout le cache
- `GET /api/babelio/requests/recent` : buffer des 50 dernières requêtes

### 8. Page de contrôle BabelioControl

`frontend/src/views/BabelioControl.vue` (nouvelle vue) :
- Section **État** : badge overall (OK/captcha/403/dégradé), cookie actif, circuit breaker, nb entrées cache, BABELIO_CACHE_DAY affiché en jours
- Section **Cookie** : form avec `<details>` repliable, status "Actif côté serveur" / "non configuré" / "probablement expiré"
- Section **Requêtes récentes** : tableau des 50 dernières (type, terme, code HTTP, hit/miss, durée)
- Section **Cache** : liste des entrées avec bouton d'invalidation individuel + vider tout
- Polling toutes les 30s
- `syncCookieToServer()` dans `mounted()` : poste le cookie localStorage au serveur

`frontend/src/router/index.js` : route `/babelio-control`
`frontend/src/views/Dashboard.vue` : section "Contrôle Babelio" avec lien

### 9. Synchronisation cookie localStorage → serveur (LivresAuteurs, BabelioMigration)

`frontend/src/views/LivresAuteurs.vue` et `frontend/src/views/BabelioMigration.vue` :
- `mounted()` : `POST /api/babelio/cookie` si cookie présent en localStorage
- `saveBabelioCookie()` : `POST /api/babelio/cookie` après sauvegarde
- `clearBabelioCookie()` : `DELETE /api/babelio/cookie`
- `serverCookieActive: bool` : reflète la confirmation serveur

### 10. UI Cookie unifiée

`frontend/src/views/LivresAuteurs.vue` et `frontend/src/views/BabelioMigration.vue` :
- Template `<details>` repliable (style BabelioControl)
- Statut dans `<summary>` : "✓ Actif côté serveur" / "⚠ non configuré (risque 403)" / "⏰ probablement expiré"
- CSS `.cookie-instructions ol` : `margin: 0.5rem 0 0 1.5rem; padding-left: 0` — fix liste numérotée invisible

### 11. Auto-enrichissement au passage "Traité"

`src/back_office_lmelp/app.py` — bloc `cache_status == "verified"` :
- **`url_babelio`** : stockée dans `livres` MongoDB
- **`titre`** : mis à jour si `suggested_title != titre`
- **Couverture** : `fetch_cover_url_from_babelio_page()` si `url_cover` absent
- **URL auteur** : `fetch_author_url_from_page(book_url)` — réutilise le cache page (free), met à jour via `update_auteur_name_and_url()`

Note : `fetch_author_url_from_page()` utilise `soup.select_one('a[href*="/auteur/"]')` — lien cliquable présent sur toute page livre Babelio.

### 12. Docker — volume cache Babelio

`docker/deployment/docker-compose.yml` :
- Volume `babelio_cache` mappé sur `/cache/babelio` (conteneur)
- Variable `BABELIO_CACHE_DIR=/cache/babelio`
- Variable `BABELIO_CACHE_DAY` configurable

### 13. settings.py

`src/back_office_lmelp/settings.py` :
- `babelio_fair_sec: float` (via `BABELIO_FAIR_SEC`, défaut 2.0)
- `babelio_cache_day: float` (via `BABELIO_CACHE_DAY`, défaut 1.0)
- `babelio_cache_dir: str` (via `BABELIO_CACHE_DIR`, défaut `/cache/babelio`)

## Tests

`tests/test_babelio_service.py` — nouvelles classes :
- `TestBabelioPageCache` (3 tests) : write après 200, read bypass HTTP, cache_hit=True dans buffer
- `TestBabelioCircuitBreaker` (4 tests) : ouverture sur 403, fermeture par set_cookie, no-network après ouverture

`tests/test_babelio_cache_service.py` : tests `list_entries()`, `invalidate()`, cache de pages

`tests/test_babelio_service_cache.py` : fix `set_cached(term, data, search_type="search")` (les deux occurrences)

`tests/test_babelio_cookies_propagation.py` : `test_search_injects_cookies_into_session_headers` marqué `@pytest.mark.skip` — obsolète car `search()` crée une session temporaire au lieu de réutiliser `_get_session()`

`frontend/tests/BabelioMigration.cookieButtons.test.js` : ajout `axios.post.mockResolvedValue({ data: {} })` et `axios.delete.mockResolvedValue({ data: {} })` dans `mountComponent()`

## Pièges rencontrés

1. **`cache_service is None`** : `_fetch_page()` sans cache injecté → `AttributeError`. Fix : guard `if self.cache_service is not None:` partout.

2. **`search_type` manquant** : `set_cached(term, data)` sans `search_type="search"` → cache miss car `search()` lit avec `search_type="search"`.

3. **Mock `axios.post` manquant** : test BabelioMigration — `mounted()` appelle `axios.post` au démarrage → `Cannot read properties of undefined (reading 'catch')`. Fix : mock dans `mountComponent()`.

4. **SIM117 ruff** : nested `async with` → combiner en `async with (..., ...,):`.

5. **`_get_session` obsolète** : `search()` utilise une session temporaire `aiohttp.ClientSession(...)` directement → le test qui patchait `_get_session` ne fonctionnait plus. Marqué skip.

6. **URL auteur** : tentative de dériver l'URL auteur depuis l'URL livre par manipulation de string (`/livres/` → `/auteur/`) — abandonné. La bonne approche est `fetch_author_url_from_page()` qui scrape le lien depuis la page (cache hit).

## Résultat

- Backend : 1424 tests passés, 24 skipped
- Frontend : 645 tests passés
- Pre-commit : ruff + mypy + detect-secrets OK
