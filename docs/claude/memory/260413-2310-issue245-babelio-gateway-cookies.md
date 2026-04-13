---
name: Issue #245 — Gateway Babelio unifié + propagation cookies
description: Refactoring architectural de BabelioService avec gateway HTTP centralisé, rate limiting universel et propagation des cookies de session navigateur
type: project
---

# Issue #245 — Gateway Babelio unifié + propagation cookies

## Problème résolu

Babelio a ajouté une protection anti-bot (captcha). Les requêtes serveur échouaient avec
des timeouts 30s ou retournaient `null, null`. Deux causes racines identifiées :

1. **Cookies manquants** : les requêtes HTTP n'incluaient pas les cookies de session du navigateur
2. **Burst de requêtes non maîtrisé** : seul `search()` était rate-limité (5s). Un seul appel
   `extract_from_babelio_url` générait 4 requêtes immédiates → captcha

**Why:** Implémentation du rate limiting partielle (seulement `search()`), pas de mécanisme
de propagation des cookies navigateur vers le backend.

**How to apply:** Pour tout nouveau scraping Babelio, utiliser `_fetch_page()` — jamais
`aiohttp.ClientSession` directement.

---

## Architecture mise en place : Gateway `_fetch_page()`

### Nouveau gateway dans `src/back_office_lmelp/services/babelio_service.py`

**`_get_page_headers(babelio_cookies=None)`** — headers Firefox navigateur :
- `User-Agent: Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:142.0) Gecko/20100101 Firefox/142.0`
- `Sec-Fetch-Dest`, `Sec-Fetch-Mode`, `Sec-Fetch-Site`, `Sec-Fetch-User`
- `Cookie` header injecté si `babelio_cookies` fourni

**`_fetch_page(url, babelio_cookies=None) → str | None`** — gateway centralisé :
- Passe **toujours** par `self.rate_limiter` + `self.min_interval`
- Timeout aiohttp : `total=30, connect=10` (was 10/5)
- Retourne HTML décodé `cp1252` ou `None` si status != 200
- Session temporaire par appel (headers navigateur différents de la session persistante AJAX)

**`min_interval`** : configurable via `BABELIO_MIN_INTERVAL` env var (défaut `2.0`, was `5.0`
search-only). S'applique maintenant à TOUTES les requêtes de pages.

### Méthodes refactorisées pour utiliser `_fetch_page()`

Toutes acceptent maintenant `babelio_cookies: str | None = None` :
- `fetch_full_title_from_url`
- `fetch_publisher_from_url`
- `fetch_author_url_from_page`
- `_scrape_author_from_book_page`
- `fetch_cover_url_from_babelio_page` (DRY — suppression de la session inline)

### Propagation cookies end-to-end

**Backend** :
- `babelio_migration_service.py` : `extract_from_babelio_url(babelio_url, babelio_cookies=None)`
- `app.py` : `ExtractFromBabelioUrlRequest` + `RefreshBabelioRequest` modèles Pydantic
- Endpoint `/api/babelio/extract-from-url` : reçoit et propage `babelio_cookies`
- Endpoint `/api/livres/{livre_id}/refresh-babelio` : body optionnel `RefreshBabelioRequest`

**Frontend** :
- `frontend/src/views/LivresAuteurs.vue` : POST inclut `babelio_cookies: sessionStorage.getItem('babelio_cookies') || null`
- `frontend/src/views/LivreDetail.vue` : idem pour refresh-babelio

Les cookies se configurent dans `BabelioMigration.vue` et sont stockés dans `sessionStorage('babelio_cookies')`.

---

## Fix timeout axios frontend

**Problème découvert en test** : `verify_book` prend maintenant 36-42s (rate limiting 2s ×
plusieurs requêtes) mais le timeout axios par défaut était 30s → affichage "Inconnu" dans
`BiblioValidationCell.vue`.

**Fix** : `frontend/src/services/api.js` — `verifyAuthor`, `verifyBook`, `verifyPublisher`
utilisent maintenant `EXTENDED_TIMEOUT` (240s) au lieu du défaut 30s.

---

## Tests

**Nouveau fichier** `tests/test_babelio_cookies_propagation.py` — 16 tests TDD :
- `test_get_page_headers_*` — headers navigateur, injection cookie
- `test_fetch_page_*` — rate limiting, status non-200, cookies, retour HTML
- `test_fetch_*_uses_fetch_page_gateway` — 4 méthodes de scraping délèguent à `_fetch_page`
- `test_extract_from_babelio_url_*` — propagation cookies dans migration service
- `test_extract_from_url_endpoint_*` — endpoint FastAPI → service
- `test_refresh_babelio_endpoint_passes_cookies` — endpoint refresh → service

**Tests existants mis à jour** : tous les tests mockant `_get_session` pour les méthodes
de scraping de pages ont été migrés vers `patch.object(service, "_fetch_page", new=AsyncMock(...))` :
- `tests/test_babelio_title_scraping.py`
- `tests/test_babelio_encoding.py`
- `tests/test_babelio_newlines_sanitization.py`
- `tests/test_babelio_publisher_enrichment.py`
- `tests/test_babelio_author_url_extraction.py`
- `tests/test_babelio_cover_title_validation.py` (mocke `aiohttp.ClientSession` → `_fetch_page`)

**Résultat** : 1364 passed, 23 skipped, 6 échecs pré-existants non liés (workflow/websocket tests)

---

## Documentation

`docs/dev/environment-variables.md` : nouvelle section "Configuration Babelio" avec
`BABELIO_MIN_INTERVAL` (défaut `2.0`, usage, exemples).

---

## Pattern à retenir pour futurs tests de scraping Babelio

```python
# ✅ CORRECT — mocker _fetch_page directement
with patch.object(service, "_fetch_page", new=AsyncMock(return_value=html_content)):
    result = await service.fetch_publisher_from_url(url)

# ❌ OBSOLÈTE — _get_session n'est plus utilisé par les méthodes de scraping de pages
with patch.object(service, "_get_session", return_value=mock_session):
    result = await service.fetch_publisher_from_url(url)
```

`_get_session` reste utilisé uniquement par `search()` (requête AJAX POST).

---

## Observation importante sur le captcha

En test réel, le rate limiting seul (2s entre requêtes + headers Firefox) s'est avéré
suffisant pour éviter le captcha sans fournir de cookies. Les cookies restent disponibles
en option si Babelio renforce sa protection.
