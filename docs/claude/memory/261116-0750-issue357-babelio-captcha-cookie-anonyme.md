# Issue #357 — Babelio : un cookie anonyme déclenche un captcha (403)

## Problème

Un cookie Babelio copié sans être connecté au compte faisait répondre Babelio
**403** dès la première requête, avec une page « Vérification de sécurité »
(curseur à glisser, en-tête `x-debug-message: 003`, `set-cookie jstsToken…
Max-Age=300`). L'app ouvrait le disjoncteur en `http_403` et affichait « cookie
probablement expiré » : mauvaise consigne, un cookie frais anonyme échoue pareil.

## Ce qui a été fait

### Backend — `src/back_office_lmelp/services/babelio_service.py`

- Nouveau motif de disjoncteur `CIRCUIT_REASON_CAPTCHA = "captcha"`, à côté de
  `http_403` et `connect_timeout`.
- `_reason_for_403(response)` : décode le corps du 403 avec `_decode_blocked_body()`
  et renvoie `captcha` si le titre « vérification de sécurité » y figure (ou si
  `_is_captcha_page()` le reconnaît), sinon `http_403`. Appelé par `_fetch_page()`
  et `_handle_search_response()` à la place de `_open_circuit(CIRCUIT_REASON_HTTP_403)`.
- `_circuit_open_error()` : message `BABELIO_CAPTCHA_MESSAGE` (« Babelio demande une
  vérification humaine : connectez-vous à Babelio, puis collez un nouveau cookie »).
- Fermeture : `set_cookie()` referme tout motif ; `probe_reachability()` ne referme que
  `connect_timeout` → un circuit `captcha` reste ouvert jusqu'au cookie suivant.
- `is_anonymous_cookie(cookie)` (fonction module) : True si pas d'`id_user` non vide.
  `get_cookie_anonymous()` : None sans cookie. Constante
  `BABELIO_ANONYMOUS_COOKIE_WARNING`.

### Backend — `src/back_office_lmelp/app.py`

- `POST /api/babelio/cookie` : jamais de refus pour un cookie anonyme, renvoie
  `warning` (texte ci-dessus) ou `None`.
- `GET /api/babelio/status` : nouveau champ `cookie_anonymous` (bool | None) ;
  `overall = "captcha"` quand le motif du disjoncteur est `captcha`.

### Frontend

- `frontend/src/components/BabelioCookiePanel.vue` :
  - aide « Comment obtenir le cookie ? » : 1re étape « Connectez-vous à votre compte
    Babelio… jusqu'à voir votre avatar : un bouton « Continuer en tant que… » affiché
    ne suffit pas » ;
  - avertissement `data-test="cookie-anonymous-warning"` (réponse du POST, sinon
    `status.cookie_anonymous`), et « ⚠ anonyme » dans le badge (visible replié) ;
  - bouton « Vider » (`data-test="cookie-input-clear"`) : vide le champ et ses erreurs,
    ne touche jamais au cookie serveur (pas d'effacement serveur, choix conservé).
- Bandeau « vérification humaine » quand `circuit_reason === 'captcha'` :
  `frontend/src/views/LivresAuteurs.vue` (computed `babelioCaptcha`),
  `frontend/src/views/BabelioMigration.vue` (computed `babelioCaptcha`),
  `frontend/src/views/BabelioControl.vue` (ligne Circuit breaker ; le statut global
  « ⚠️ Captcha » existait déjà via `overall`).

### Tests

- `tests/test_babelio_captcha_403.py` : vrai serveur local (`aiohttp.test_utils.TestServer`)
  servant `tests/fixtures/babelio_captcha_403.html` en 403 ; captcha via `search()` et
  `_fetch_page()`, 403 ordinaire reste `http_403`, fermeture par cookie et pas par essai
  TCP, statut `captcha`.
- `tests/test_babelio_cookie_format.py` : avertissement anonyme, pas d'avertissement avec
  `id_user`, `cookie_anonymous` None sans cookie, limite `id_user` résiduel.
- Frontend : `BabelioCookiePanel.test.js`, `LivresAuteurs.babelioIpBan.test.js`,
  `babelioMigrationIpBan.spec.js`, `BabelioControl.reachability.test.js`.

## Apprentissages

- **`id_user` et `bbac` survivent à une déconnexion Babelio.** Comparaison réelle
  (même navigateur) : cookie déconnecté et cookie connecté ont les **mêmes noms** et le
  même `id_user` ; seules les valeurs de `bbac` et `PHPSESSID` changent (session côté
  serveur), plus un `g_csrf_token` transitoire de Google One Tap. Aucun critère sur le
  cookie ne prouve une session ouverte : l'avertissement ne couvre que le cas net
  (navigateur jamais connecté, pas d'`id_user` — cas de la prod du 15/11). Le diagnostic
  fiable reste le motif `captcha` après le 403.
- « Continuer en tant que… » (Google One Tap) sur babelio.com ne signifie **pas** être
  connecté : il faut voir son avatar.
- La capture réelle du 403 n'était plus disponible (`GET /api/babelio/blocked-responses`
  est un tampon en mémoire, vidé au redémarrage) : fixture reconstruite à partir des
  extraits de l'issue ; la détection s'appuie sur le titre observé.
- La suite pytest complète a supprimé `.dev-ports.json` pendant que les services
  tournaient (un des tests de découverte de ports touche le vrai fichier) : services
  intacts, mais `get-backend-info.sh` ne les trouve plus. Hors périmètre.
