# Issues #285, #286, #287 — Diagnostic ban IP Babelio + badge d'état trompeur

## Contexte

Signalement initial (#285) : les images de couverture Babelio ne s'affichaient plus sur la page détail livre, alors qu'ouvrir l'URL de l'image dans un nouvel onglet fonctionnait.

## Issue #285 — Diagnostic (fermée sans code)

Investigation conjointe avec l'utilisateur, en plusieurs itérations car les premières hypothèses (blocage anti-hotlink Babelio ciblé sur les images, doublons de clé de cache) se sont révélées fausses :

- Le NAS (backend) et le navigateur de l'utilisateur (hors VPN) partagent la **même IP publique domicile**.
- Confirmé par l'utilisateur : `babelio.com` est entièrement inaccessible (page HTML **et** images) sans VPN — c'est un **ban IP global** côté Babelio, pas un blocage ciblé sur le flux d'images (Babelio ne surveille pas spécifiquement les requêtes d'images selon l'utilisateur — pas de captcha/cookie sur ce flux).
- Avec un VPN navigateur (IP différente), l'image s'affichait correctement — cohérent avec un ban IP, exclut un bug CORS/CSP/mixed-content côté frontend.
- Le problème touche toutes les couvertures, partout dans l'app — cohérent avec une cause réseau externe globale, pas un bug applicatif localisé.
- Vérifié que le rate-limiter centralisé de `src/back_office_lmelp/services/babelio_service.py` (singleton `babelio_service`, 1 req simultanée, 5s min entre requêtes, circuit breaker sur 403) n'est contourné par aucun code du travail récent (#279, #282) — un seul autre `BabelioService()` existe, dans `src/back_office_lmelp/utils/migration_runner.py`, avec son propre rate-limiter séparé, mais ce script de migration ne se lance que manuellement.
- Cause exacte du déclenchement du ban non identifiée avec certitude (décision opaque côté Babelio) — une capture de la page "Contrôle Babelio" montrait des requêtes encore "Valide" à 09:52-09:54 le matin même, donc le ban est survenu après.

**Décision utilisateur** : ban IP externe temporaire, indépendant du code — fermeture de l'issue sans changement de code, après avoir posté le diagnostic complet en commentaire.

**Piège méthodologique répété** : plusieurs hypothèses ont été proposées puis explicitement invalidées par l'utilisateur avant d'arriver au bon diagnostic (doublon de clé de cache search — invalidé après lecture du code montrant que `set_cached` écrit sous les deux clés en une seule requête ; proxy backend comme solution — invalidé car Babelio ne surveille pas le flux images, un ban global toucherait aussi bien le proxy backend). **Leçon** : quand l'utilisateur dit "je l'ai déjà dit N fois", arrêter de re-proposer des variantes de la même hypothèse déjà écartée et repartir strictement des faits confirmés.

## Issue #286 — Étude de faisabilité VPN (créée, non implémentée)

À la demande de l'utilisateur, création d'une issue d'étude d'architecture (pas de code) pour :
- VPN permanent au niveau service/conteneur (pas par connexion client), avec kill switch et reconnexion dynamique en cas de nouveau ban.
- **Tension identifiée par l'utilisateur** : si l'IP domicile est bannie, l'utilisateur ne peut plus du tout accéder à `babelio.com` pour résoudre manuellement le captcha et copier le cookie anti-403 (mécanisme actuel de `babelio_service.py` — `set_cookie()`/`_stored_cookie`) — il faudrait que ce renouvellement de cookie passe aussi par le tunnel applicatif.
- Comparatif de solutions VPN (Mullvad, ProtonVPN, NordVPN, Surfshark, AirVPN, VPS auto-hébergé, proxy résidentiel) avec prix/compatibilité Docker-serveur/CGU.
- Extension du proxy interne à tout le flux Babelio (pas seulement les covers, qui étaient le point de départ du problème).

## Issue #287 — Badge "État du service Babelio" trompeur (implémentée)

Découvert en marge du diagnostic #285 : la page "Contrôle Babelio" (`frontend/src/views/BabelioControl.vue`) affichait un badge **"✅ OK"** alors que l'IP était bannie, avec "Requêtes récentes enregistrées : 0".

### Cause racine

Dans `GET /api/babelio/status` (`src/back_office_lmelp/app.py`), le calcul de `overall` :

```python
overall = "unknown"
last_real = next((r for r in recent if not r.get("cache_hit")), None)
if last_real is None:
    overall = "ok"   # ← bug : aucune requête tentée récemment ne devrait pas dire "ok"
```

Le buffer `_recent_requests` (deque de 50, en mémoire, vidé au redémarrage backend) était vide → `last_real is None` → retournait `"ok"` par défaut, alors que `"unknown"` existait déjà dans le code mais n'était jamais atteint. Le frontend gérait déjà cet état (`❓ Inconnu`, classe `status-unknown`).

### Fix implémenté (TDD)

1. **Fix minimal** : `last_real is None` → `overall = "unknown"` (au lieu de `"ok"`).
2. **Nouvelle méthode `BabelioService.health_check()`** (`src/back_office_lmelp/services/babelio_service.py`, après `_fetch_page`) : effectue un GET léger sur `self.base_url` (page d'accueil Babelio, jamais mise en cache par ailleurs dans le code → garantit une vraie requête réseau) via `_fetch_page`, capturé dans son propre try/except (nécessaire : `_fetch_page` ne catch pas en interne `TimeoutError`/`aiohttp.ClientError` comme le fait `search()`). Cas circuit déjà ouvert géré explicitement (log manuel car `_fetch_page` lève avant tout log dans ce cas). Ne lève jamais d'exception — retourne `{"ok": bool}`.
3. **Endpoint** : `GET /api/babelio/status?live_check=true` (paramètre `live_check: bool = False`) — si vrai, appelle `await babelio_service.health_check()` avant de relire le buffer, pour peupler une entrée fraîche.
4. **Frontend** : nouvelle méthode `refreshStatus()` dans `BabelioControl.vue`, appelée uniquement par le bouton "🔄 Rafraîchir" (`live_check=true`) — **distincte** de `loadStatus()` utilisée par le polling silencieux (`setInterval` 30s, `BabelioControl.vue:288`) qui reste sans paramètre pour ne jamais spammer Babelio automatiquement.

### Tests ajoutés

- `tests/test_babelio_health_check.py` (nouveau, 8 tests) : succès, 403, circuit déjà ouvert (avec/sans log), timeout, `BabelioBlockedError` jamais propagée.
- `tests/test_babelio_control_endpoints.py` (+3 tests) : `overall="unknown"` sur buffer vide, `live_check` absent n'appelle pas `health_check`, `live_check=true` l'appelle et reflète le résultat frais.
- `frontend/tests/BabelioControl.liveCheck.test.js` (nouveau, 3 tests) : chargement initial sans `live_check`, clic Rafraîchir avec `live_check=true`, polling silencieux sans `live_check`.

### Piège d'environnement rencontré (sans lien avec le fix)

Plusieurs fichiers de test préexistants (`tests/test_babelio_gloria_case.py`, `test_babelio_publisher_enrichment.py`, `test_babelio_title_enrichment.py`, `test_babelio_403_detection.py`, `test_babelio_terminus_case.py`) sont devenus très lents ou en timeout **sur `main` sans rapport avec ce fix**, confirmé en testant sur `git stash` — cohérent avec le ban IP Babelio actuel de #285 qui affecte des tests faisant de vrais appels réseau non mockés proprement. La suite complète (1552 tests) a mis plus de 30 minutes et n'a jamais fini naturellement sur ce ban. **Vérification retenue comme suffisante** : tests ciblés (fichiers modifiés + `test_babelio_service.py`/`test_babelio_service_cache.py`) tous GREEN (66 passed, 0 failed), suite complète à 79%+ sans aucun `F` avant coupure, frontend complet GREEN (699 passed, 14 skipped).

## Fichiers modifiés (#287)

- `src/back_office_lmelp/app.py` — `get_babelio_status(live_check: bool = False)`.
- `src/back_office_lmelp/services/babelio_service.py` — nouvelle méthode `health_check()`.
- `frontend/src/views/BabelioControl.vue` — nouvelle méthode `refreshStatus()`, bouton Rafraîchir de la section statut rebranché dessus.
- `tests/test_babelio_control_endpoints.py`, `tests/test_babelio_health_check.py` (nouveau), `frontend/tests/BabelioControl.liveCheck.test.js` (nouveau).
