# Issue #350 — Cookie Babelio : le serveur est la seule source du cookie

Issue : [castorfou/back-office-lmelp#350](https://github.com/castorfou/back-office-lmelp/issues/350)
Suite ouverte pendant le test : [#352](https://github.com/castorfou/back-office-lmelp/issues/352) (mettre à jour le tableau Livres et Auteurs au fil de la validation Babelio).

## Problème

- Le panneau « 🔑 Cookie Babelio » pré-remplissait son champ avec `localStorage['babelio_cookies']` et affichait « ✓ Configuré » dès que la clé existait, même quand le serveur n'avait aucun cookie.
- Le serveur date le cookie **à sa réception** (`BabelioService.set_cookie()` → `_cookie_set_at`). Recliquer « Enregistrer » sur un vieux `jstsToken` le faisait passer pour frais : `BABELIO_COOKIE_MAX_AGE_SEC` ne le bloquait pas, Babelio répondait 403, donc ban IP ~24 h (contournait #340).

## Second chemin découvert pendant l'exploration (le plus dangereux)

- Le même cookie `localStorage` partait dans le corps de 6 appels : `babelioService.verifyAuthor/verifyBook` (`frontend/src/services/api.js`), extract-from-url (`LivresAuteurs.vue`), update-from-url et extract-cover-url (`BabelioMigration.vue`), refresh-babelio (`LivreDetail.vue`, via `sessionStorage`).
- Côté serveur, `_fetch_page()` et `search()` faisaient `effective_cookie = self._stored_cookie or babelio_cookies` : sans cookie serveur, le cookie client partait vers Babelio **sans aucun contrôle d'âge** (`_ensure_cookie_fresh()` ne regarde que `_stored_cookie`).

## Solution (décisions validées par l'utilisateur)

### Backend

- Paramètre `babelio_cookies` **supprimé de toute la chaîne** (`babelio_service.py`, `babelio_migration_service.py`, endpoints de `app.py`). `_get_page_headers()` n'a plus de paramètre : il lit `self._stored_cookie`. `search()` envoie `self._stored_cookie or self._default_cookie_header()`.
- Modèles Pydantic : champ `babelio_cookies` retiré (`BabelioVerificationRequest`, update-from-url, `ExtractFromBabelioUrlRequest`, extract-cover-url). Pydantic ignore par défaut un champ inconnu : un ancien client qui l'envoie ne casse pas. `RefreshBabelioRequest` supprimé (la route `/api/livres/{id}/refresh-babelio` n'a plus de corps).
- `BabelioService.get_cookie_age_sec()` ; `GET /api/babelio/status` expose `cookie_age_sec` (arrondi, `null` sans cookie), `cookie_max_age_sec`, `cookie_expired`.
- `normalize_cookie_header(raw)` (fonction de module dans `src/back_office_lmelp/services/babelio_service.py`) : une seule ligne, paires `nom=valeur` séparées par `;` (nom = token HTTP RFC 6265), refuse les attributs `Set-Cookie` (`path`, `expires`, `HttpOnly`…), exige `jstsToken` non vide, retire un préfixe `Cookie:`. `POST /api/babelio/cookie` répond **400** avec le motif et ne remplace pas le cookie existant ; un cookie vide efface toujours.
- `DELETE /api/babelio/cookie` conservé (dépannage `curl`), mais plus de bouton dans l'UI.

### Frontend

- Nouveau composant partagé `frontend/src/components/BabelioCookiePanel.vue`, utilisé par `LivresAuteurs.vue`, `BabelioMigration.vue` et `BabelioControl.vue` (prop `collapsible=false` dans sa carte). Props : `status` (réponse de `/api/babelio/status`, possédée par la page), `open`, `collapsible` ; slot pour un texte d'aide ; événement `saved` (la page recharge son statut).
- Badge dérivé **uniquement** du statut serveur : `missing` / `expired` / `active`. Actif : « ✓ Actif côté serveur · enregistré à HH:MM · expire dans ~N min ». Horloge locale (`setInterval` 5 s, nettoyé en `beforeUnmount`) : vieillit le cookie entre deux statuts sans appel serveur ; à l'échéance → « ⏰ périmé » et le champ réapparaît.
- Cookie actif → **pas de champ** : bouton « Entrer un cookie plus récent » qui ouvre un champ vide (+ « Annuler »). Sans cookie ou périmé → champ affiché d'emblée. Après enregistrement réussi, le champ se referme.
- Bouton « Effacer » retiré (demande utilisateur) : sans cookie, le serveur interroge Babelio avec des cookies génériques, effacer ne protège de rien.
- Au montage, purge des clés héritées `babelio_cookies` et `babelio_cookies_saved_at` de `localStorage` (try/catch).
- `frontend/src/utils/babelioCookie.js` (`checkBabelioCookie`) : même règle que `normalize_cookie_header()`, message sous le champ pendant la saisie et « Enregistrer » désactivé ; un refus 400 du serveur affiche son `detail`.
- BabelioControl : la ligne « Cookie serveur » affiche aussi « ⏰ Périmé ».

## Tests

- RED haut niveau : `frontend/tests/BabelioPages.noStaleCookie.test.js` (`it.each` sur les 3 pages : `localStorage` rempli + serveur sans cookie → champ vide, badge ni « Configuré » ni « Actif », clés purgées ; cas périmé et actif).
- `frontend/src/components/__tests__/BabelioCookiePanel.test.js` (badge, échéance avec `vi.useFakeTimers`/`setSystemTime`, remplacement, pas de bouton Effacer, erreurs de format, motif 400).
- `frontend/src/utils/__tests__/babelioCookie.test.js`, `frontend/tests/unit/babelioNoBrowserCookie.test.js` (api.js n'envoie plus de cookie + garde statique : aucun `babelio_cookies:` dans `frontend/src`).
- Backend : `tests/test_babelio_server_cookie_only.py` (cookie client ignoré sur verify-babelio et extract-from-url avec un vrai `BabelioService` dont `_send` est mocké ; champs d'âge du statut), `tests/test_babelio_cookie_format.py` (cookie factice reprenant la structure d'un vrai en-tête Firefox).
- Adaptés : `tests/test_babelio_cookies_propagation.py` (réécrit : gateway + cookie serveur), `tests/test_babelio_control_endpoints.py` (fixtures : `get_cookie_age_sec`, `cookie_max_age_sec`), et 6 autres fichiers qui passaient `babelio_cookies`. Supprimé : `frontend/tests/BabelioMigration.cookieButtons.test.js` (couvert par le composant).

## Pièges rencontrés

- `vi.resetAllMocks()` efface aussi les `mockResolvedValue` posés dans une factory `vi.mock(...)` : `LivresAuteurs` plantait (`episodesWithReviews.find` sur `undefined`). Re-poser les valeurs dans `beforeEach`.
- `extract-from-url` passe par `babelio_migration_service.babelio_service`, pas par `app.babelio_service` : patcher les deux (`patch.object(babelio_migration_service, "babelio_service", service)`).
- Un `MagicMock` qui remplace tout `babelio_service` renvoie un `MagicMock` pour toute nouvelle méthode : comparer `>=` deux `MagicMock` lève `TypeError`. Ajouter les nouveaux attributs aux fixtures existantes.
- Vérification Playwright de l'état « actif » sans toucher au vrai cookie : `page.route('**/api/babelio/status*')` qui réécrit la réponse, et `route.abort()` sur `/api/babelio/cookie`. Ne jamais enregistrer de cookie factice sur le vrai backend (risque de 403 → ban).
- `gh issue view` restait bloqué ; `gh api repos/<owner>/<repo>/issues/<n>` fonctionne.
- « Le champ a disparu » après enregistrement n'était pas un bug (POST 200 dans le log) mais une UX trompeuse : d'où le champ masqué quand le cookie est actif.
