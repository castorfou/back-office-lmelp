# Issue #351 — Diagnostic de ban IP Babelio par essai TCP (sans requête HTTP)

Issue : [#351](https://github.com/castorfou/back-office-lmelp/issues/351)

## Problème

Un ban IP Babelio est un blocage pare-feu : les paquets sont ignorés, la connexion
TCP n'aboutit jamais (ni 403 ni captcha). Le seul diagnostic intégré, « Rafraîchir »
dans Contrôle Babelio (`/api/babelio/status?live_check=true` → `health_check()`),
envoyait une vraie requête HTTP à la page d'accueil. Et tous les bandeaux
attribuaient un blocage à « 403, cookie probablement expiré », même pendant un ban.

## Solution

### Backend — `src/back_office_lmelp/services/babelio_service.py`

- `probe_reachability(timeout_sec=None, host=None, port=None) -> "reachable" | "unreachable"` :
  `asyncio.wait_for(asyncio.open_connection(host, 443), timeout)`, writer fermé
  aussitôt. Pas de TLS, pas de HTTP, pas de `_send()`, pas de rate limiter, pas
  d'entrée dans `_recent_requests`. Host/port dérivés de `self.base_url`.
  `TimeoutError`/`OSError` (timeout, refus, DNS) → `unreachable`.
- Constantes : `PROBE_TIMEOUT_SEC = 5.0` (Rafraîchir), `PRECHECK_PROBE_TIMEOUT_SEC = 1.0`
  (avant traitement), `BABELIO_IP_BANNED_MESSAGE`, `CIRCUIT_REASON_HTTP_403`,
  `CIRCUIT_REASON_CONNECT_TIMEOUT`.
- **Motif du disjoncteur** : `_circuit_reason`, posé par le helper `_open_circuit(reason)`
  aux 3 sites d'ouverture (403 dans `_fetch_page` et `_handle_search_response`, timeout
  de connexion dans `_open_circuit_on_connection_timeout`). `set_cookie()` le remet à None.
  `get_circuit_reason()` renvoie None si le circuit est fermé.
- **Effets de l'essai (choix validé : symétrique)** : échec → ouvre le disjoncteur
  (motif ban IP) ; succès → referme un disjoncteur ouvert par **timeout de connexion**
  seulement. Un disjoncteur ouvert par 403 ne se referme qu'avec un cookie frais.
- `_circuit_open_error()` : message spécifique au motif. Ban IP → « Babelio injoignable :
  IP bannie, inutile de changer le cookie » ; 403 → « configurez un cookie frais ».
- `get_last_probe()` : `{reachable, checked_at, duration_ms}` du dernier essai.
- Supprimés : `health_check()` et le paramètre `skip_cache` de `_fetch_page()`
  (ne servait qu'à lui), ainsi que `tests/test_babelio_health_check.py`.

### Backend — endpoints et migration

- `src/back_office_lmelp/app.py` : `GET /api/babelio/status?live_check=true` lance
  `probe_reachability(timeout_sec=PROBE_TIMEOUT_SEC)`. La réponse expose
  `circuit_reason` et `last_probe`. Nouveau `POST /api/babelio/probe` (essai de 1 s) →
  `{reachable, circuit_open, circuit_reason}`.
- `src/back_office_lmelp/utils/migration_runner.py` : `start_migration()` fait l'essai de 1 s
  **avant** `is_running = True` ; s'il échoue → `{"status": "unreachable", "message": BABELIO_IP_BANNED_MESSAGE}`
  sans lancer la tâche.

### Frontend

- `frontend/src/views/BabelioControl.vue` : ligne « Accès réseau (essai TCP) »
  (`data-test="babelio-reachability"` : Non testé / ✓ Joignable / 🚫 Injoignable — IP bannie + heure),
  motif affiché sur le badge du disjoncteur (`data-test="babelio-circuit"`).
  Le badge « État du service » passe par le computed `statusKey` : d'abord le ban IP
  (disjoncteur ouvert par `connect_timeout`), puis le `overall` de la dernière requête
  HTTP, puis l'essai TCP (« 🟢 Joignable » / « 🚫 IP bannie »), puis « ❔ Non testé ».
  « ❓ Inconnu » a disparu : l'utilisateur le trouvait peu clair.
- `frontend/src/views/LivresAuteurs.vue` : `validateWithBabelio()` appelle d'abord
  `probeBabelio()` (`POST /api/babelio/probe`) ; si injoignable → `babelioProbeUnreachable`,
  bandeau ban IP, arrêt immédiat. Si l'appel au backend échoue, la validation n'est pas
  bloquée. Computed `babelioIpBanned` (essai en échec OU `babelioStatus.circuit_reason === 'connect_timeout'`).
  Le watcher `babelioBlocked` ouvre le panneau cookie immédiatement (comportement existant
  conservé), recharge le statut, puis le referme si le motif est un ban IP.
- `frontend/src/views/BabelioMigration.vue` : bandeau adapté au motif (computed
  `babelioIpBanned`), `startMigration()` gère `status === 'unreachable'` (toast + statut relu).

## Tests

- `tests/test_babelio_probe.py` : vrai serveur `asyncio.start_server` (il reçoit une
  connexion sans aucun octet), adresse muette `192.0.2.1` (RFC 5737), port fermé, `_send`
  jamais appelé, cible par défaut `www.babelio.com:443`, toutes les règles du disjoncteur,
  messages selon le motif.
- `tests/test_babelio_control_endpoints.py` : `live_check` lance l'essai (5 s), le polling
  ne l'appelle jamais ; un vrai `BabelioService` avec `open_connection` patché prouve
  qu'aucune requête HTTP ne part ; `POST /api/babelio/probe` (1 s).
- `tests/test_migration_runner_reachability.py` : démarrage refusé si injoignable.
- Vitest : `frontend/tests/BabelioControl.reachability.test.js`,
  `frontend/tests/integration/LivresAuteurs.babelioIpBan.test.js`,
  `frontend/tests/unit/babelioMigrationIpBan.spec.js`.

## Pièges et apprentissages

- **Le nouvel essai dans `start_migration()` fait du vrai réseau dans tout test qui démarre
  la migration.** En local l'essai aboutit et tout passe ; en CI il expire → la migration
  refuse de démarrer (premier run CI : 3 échecs dans `test_migration_runner_items_count.py`,
  un fichier oublié par une fixture opt-in, car un `grep | head` avait tronqué la liste).
  Correction : fixture **autouse** `babelio_reachable` dans `tests/conftest.py`.
- **La fixture autouse ne doit importer aucun module.** Une première version importait
  `migration_runner` : importé dès le premier test, il gardait le singleton `babelio_service`
  d'avant le `importlib.reload` de `tests/test_babelio_service.py`, d'où un échec d'identité
  dans `test_should_use_shared_babelio_service_singleton_not_new_instance`. Version finale :
  patcher chaque singleton déjà présent dans `sys.modules` (copies `back_office_lmelp.` et `src.`,
  dédupliquées par `id`) avec un `ExitStack`.
- **Simuler la CI en local** : un plugin pytest jetable qui remplace `asyncio.open_connection`
  par un `TimeoutError` (`PYTHONPATH=src:<dossier> pytest -p no_network_plugin ...`) reproduit
  exactement les échecs CI ; il a validé la correction sur toute la suite.
- La fixture autouse `_reset_babelio_circuit_breaker` remet aussi `_circuit_reason` à None.
- pytest-asyncio est en mode strict : une fixture async doit utiliser `@pytest_asyncio.fixture`.
- L'essai de l'adresse muette passe dans tous les environnements : un refus (`OSError`) donne
  aussi `unreachable`, donc pas besoin de `skip` comme dans `test_real_transport_reports_connection_timeout`.
- Vérifié en réel : l'essai répond « reachable » en 43 ms, et `recent_requests_count`
  reste à 0 après « Rafraîchir ».
