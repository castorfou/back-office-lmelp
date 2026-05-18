# Issue #247 — Fix Babelio 403 sur la recherche AJAX

## Contexte du problème

Les logs montraient `WARNING - Babelio HTTP 403 pour: {titre}` en masse pour les titres
comme "Murmuration", "Très brève théorie de l'enfer", etc.

**Root cause** : Le système anti-bot Babelio bloque les IPs inconnues. Il utilise un cookie
`jstsToken` (Max-Age=300, validité 5 min) obtenu uniquement en résolvant un captcha dans un vrai
navigateur. Issue #245 avait corrigé les 403 sur le **scraping de pages** via `_fetch_page()`,
mais la méthode `search()` (POST AJAX vers `/aj_recherche.php`) n'avait pas été mise à jour.

## Ce qui a été découvert lors de l'expérimentation

- **Bootstrap automatique impossible** : GET sur la homepage Babelio retourne aussi 403 si l'IP
  est bloquée — impossible d'auto-récupérer les cookies.
- **Env var rejetée** : L'appli tourne dans Docker, l'utilisateur ne veut pas redéployer à chaque
  expiration du cookie (5 min).
- **Bonne nouvelle** : Le devcontainer et Firefox partagent la même IP → un `jstsToken` obtenu
  dans Firefox est valide depuis le devcontainer.
- **brotli manquant** : `aiohttp` ne pouvait pas décoder les réponses Babelio compressées en
  brotli. Corrigé avec `uv add --active brotli`.

## Solution retenue : propagation du cookie depuis l'UI

L'utilisateur résout le captcha Babelio dans Firefox une fois, copie la valeur du header
`Cookie` depuis Firefox DevTools (onglet Network), et la colle dans un champ UI de la page
LivresAuteurs. Le cookie est stocké en `sessionStorage` et propagé à tous les appels Babelio.

## Chaîne de propagation complète

```
LivresAuteurs.vue (UI cookie field)
  → sessionStorage('babelio_cookies')
  → api.js verifyBook() / verifyAuthor()  [babelio_cookies param dans le POST]
  → /verify-babelio endpoint (app.py)     [BabelioVerificationRequest.babelio_cookies]
  → babelio_service.verify_book()         [babelio_cookies kwarg]
  → babelio_service.verify_author()       [babelio_cookies kwarg]
  → babelio_service.search()              [headers["Cookie"] = babelio_cookies]
  → babelio_service.fetch_publisher_from_url()  [via _fetch_page()]
  → babelio_service.fetch_full_title_from_url() [via _fetch_page()]
  → babelio_service.fetch_author_url_from_page() [via _fetch_page()]
```

## Fichiers modifiés

### Backend

**`src/back_office_lmelp/services/babelio_service.py`** :
- `search(term, babelio_cookies=None)` : injecte `Cookie` header dans le POST si fourni
  - Pattern : `extra_headers or None` pour ne pas écraser les headers de session si vide
- `verify_author(author_name, babelio_cookies=None)` : passe cookies à `search()`
- `verify_book(title, author=None, babelio_cookies=None)` : passe cookies à `search()`,
  `fetch_publisher_from_url()`, `fetch_full_title_from_url()`, `fetch_author_url_from_page()`

**`src/back_office_lmelp/app.py`** :
- `BabelioVerificationRequest` : ajout champ `babelio_cookies: str | None = None`
- `verify_babelio` endpoint : passe `babelio_cookies` à `verify_author()` et `verify_book()`

### Frontend

**`frontend/src/services/api.js`** :
- `verifyAuthor()` et `verifyBook()` : ajout `babelio_cookies: sessionStorage.getItem('babelio_cookies') || null`

**`frontend/src/views/LivresAuteurs.vue`** :
- Section `<details>` collapsible "🔑 Cookie Babelio" avant la légende
- Status visuel : ✓ configuré (vert) / ⚠ non configuré (orange)
- Méthodes `saveBabelioCookie()` et `clearBabelioCookie()`
- Data : `babelioCookieInput`, `babelioCookieStored`

### Tests

**`tests/test_babelio_cookies_propagation.py`** : 8 nouveaux tests TDD :
- `test_search_accepts_babelio_cookies_parameter`
- `test_search_injects_cookies_into_session_headers`
- `test_search_no_cookie_header_when_none`
- `test_verify_book_propagates_cookies_to_search`
- `test_verify_author_propagates_cookies_to_search`
- `test_verify_book_propagates_cookies_to_fetch_page_calls`
- `test_verify_babelio_endpoint_accepts_babelio_cookies`
- `test_verify_babelio_book_endpoint_passes_cookies`

**`tests/test_babelio_gloria_case.py`** : assertion mise à jour :
`mock_search.assert_called_once_with("Gloria, Gloria", babelio_cookies=None)`

**`tests/test_babelio_newlines_sanitization.py`** : signature mock mise à jour :
`async def mock_search(query, babelio_cookies=None):`

## Pièges rencontrés

1. **`test_verify_book_propagates_cookies_to_search`** : `search()` est appelé **deux fois**
   dans `verify_book()` (appel principal + fallback titre seul). `assert_called_once_with()`
   échoue. Corriger avec : `for call in mock_search.call_args_list: assert call.kwargs.get("babelio_cookies") == cookies`

2. **`headers={}` vs `headers=None`** : Passer un dict vide override les headers de session.
   Toujours utiliser `headers=extra_headers or None`.

3. **Mock hand-rolled avec `babelio_cookies`** : Toute fonction mock qui simule `search()` doit
   accepter `babelio_cookies=None` en kwarg sinon `TypeError: unexpected keyword argument`.

4. **brotli** : `uv add --active brotli` (pas `pip install`) — sinon non persisté dans le venv.

## Dépendance ajoutée

`brotli` dans `pyproject.toml` — nécessaire pour que `aiohttp` décode les réponses Babelio.

## Notes opérationnelles

- Le `jstsToken` expire toutes les 5 minutes
- Si les 403 reviennent : aller sur babelio.com dans Firefox, résoudre le captcha, copier le
  header Cookie depuis DevTools → Network → n'importe quelle requête → Request Headers
- La section cookie est collapsible et n'apparaît que si un épisode est sélectionné
