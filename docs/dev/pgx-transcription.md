# Transcription PGX (développeur)

Ce document décrit l'implémentation du pipeline de transcription automatisée via la
station GPU dédiée PGX (Issue #302, portage depuis `castorfou/lmelp`, `nbs/pgx.py`).

## Vue d'ensemble

Deux modules collaborent :

- **`src/back_office_lmelp/services/pgx_service.py`** — fonctions I/O pures (SSH/SCP),
  sans état ni dépendance MongoDB. Portage quasi 1:1 du module `pgx.py` de lmelp, adapté
  en asyncio (`asyncio.create_subprocess_exec` au lieu de `subprocess.run`,
  `asyncio.open_connection` au lieu de `socket` bloquant) — voir la section
  "Subprocess Calls to External System Tools" dans `CLAUDE.md` pour la justification.
- **`src/back_office_lmelp/utils/pgx_transcription_runner.py`** — singleton
  `PgxTranscriptionRunner` qui orchestre le traitement de la file d'épisodes et
  l'écriture MongoDB, calqué sur `MigrationRunner`
  (`src/back_office_lmelp/utils/migration_runner.py`, pattern
  singleton + `asyncio.create_task` + polling GET, déjà utilisé pour la migration
  Babelio).

## Pipeline par épisode

Pour chaque épisode de la file (traités **séquentiellement**, une seule machine PGX) :

1. **Cache local** : si `<audio>.txt` existe déjà à côté du fichier audio local
   (`settings.audio_storage_path`), lire son contenu directement — aucun appel réseau.
   Reproduit `set_transcription()` de lmelp.
2. Sinon, pipeline réseau complet :
   - Vérification de joignabilité PGX (**lazy** : une seule fois pour toute la file, au
     premier épisode qui en a réellement besoin — pas en amont de la boucle, sinon un
     run entièrement servi par le cache local échouerait inutilement si PGX est
     injoignable).
   - Envoi du fichier audio par `scp` (`send_audio_to_pgx`, qui crée d'abord le
     répertoire distant `<remote_audio_root>/<année>/` via `ssh mkdir -p` — `scp` ne
     crée pas les répertoires manquants).
   - Attente de la transcription générée par le watcher PGX
     (`wait_for_pgx_transcription`, poll SSH `test -f`, timeout
     `PGX_TRANSCRIPTION_TIMEOUT_S`).
   - Rapatriement du fichier de transcription par `scp`
     (`fetch_transcription_from_pgx`), écrit en local à `<audio>.txt` (alimente le
     cache pour un run futur).
3. Écriture du champ `episodes.transcription` en base MongoDB, via
   `mongodb_service.episodes_collection` — passe donc par le `MongoClient` de ce
   backend, observé nativement par `DashboardStatsInvalidationListener` (voir
   `docs/dev/dashboard-stats-cache.md`).

Un échec (`PgxError`) sur un épisode n'interrompt **pas** le traitement des suivants de
la file — sauf l'échec de joignabilité initial (avant tout épisode traité), qui arrête
toute la file immédiatement (un nouvel essai réseau par épisode ne résoudrait rien tant
que PGX reste éteinte).

## Diagnostics

`run_pgx_diagnostics()` (`pgx_service.py`) exécute une checklist en cascade — chaque
étape court-circuite les suivantes si elle échoue :

1. **Joignabilité** (`wait_for_pgx_reachable`, poll TCP port 22).
2. **Authentification SSH** (`_check_ssh_auth`, connexion SSH réelle testée, pas
   seulement le port ouvert — le message d'échec inclut le `stderr` réel de la tentative,
   jamais un message générique statique, pour distinguer permissions de clé, clé absente
   d'`authorized_keys`, etc.).
3. **Répertoire audio distant** existe.
4. **Répertoire transcriptions distant** existe.

`get_pgx_config_missing_vars()` doit être vérifié **avant** tout appel à
`run_pgx_diagnostics()` — `wait_for_pgx_reachable()` lève sinon une erreur non catchée
si `host` est `None`. C'est ce que fait l'endpoint `GET /api/pgx/diagnostics`.

Côté frontend (`PgxTranscription.vue`), la checklist reste **toujours visible**, y compris
quand `missing_vars` n'est pas vide (Issue #310) : la computed `pgxDiagnosticsDisplay`
affiche dans ce cas les 4 étapes connues avec un statut `skipped` forcé côté client (le
backend renvoie une liste vide, cohérent avec le court-circuit ci-dessus), plutôt que de
masquer toute la section derrière le seul message d'avertissement de config incomplète.

## Endpoints

- `GET /api/pgx/diagnostics` — checklist ci-dessus. Retourne `{"diagnostics": [],
  "missing_vars": [...]}` sans appel réseau si la config est incomplète.
- `GET /api/pgx/ssh-key` — retourne `{"public_key": str | None, "missing_config": bool}`.
  Appelle `pgx_service.ensure_pgx_ssh_key(settings.pgx_ssh_key_path)` (génère la paire de
  clés si absente, idempotent) uniquement si `PGX_SSH_KEY_PATH` est défini — pas d'appel
  si `missing_config` serait `True`, même piège que `get_pgx_config_missing_vars()` pour
  `run_pgx_diagnostics()`. Consommé par `/transcription-pgx` pour afficher la clé publique
  et la commande `authorized_keys` (Issue #310 : cette route n'existait pas dans le
  portage initial #302, alors que `ensure_pgx_ssh_key()` était déjà écrite et testée —
  gap entre service et endpoint, jamais détecté par la suite pytest puisque les deux sont
  mockés indépendamment).
- `GET /api/pgx/episodes-without-transcription` — liste (id/titre/date) des épisodes non
  masqués sans transcription, via `stats_service.get_episodes_without_transcription()`
  (même filtre Mongo que le compteur caché `episodes_without_transcription_count`, mais
  `find()` au lieu de `count_documents()`).
- `POST /api/pgx/transcription/start` — accepte un body optionnel
  `{"trigger": "manual" | "api"}` (défaut `"manual"` ; un POST sans corps du tout reste
  valide, voir la section "Déclenchement automatique" ci-dessous). Traite **toute** la
  file courante des épisodes en attente (décision produit : une action déclenche tout le
  backlog plutôt qu'un sélecteur par épisode). Retourne `{"status": "already_running" |
  "nothing_to_do" | "started", "episode_count": N}`.
- `GET /api/pgx/transcription/progress` — statut consommé par polling (2s côté
  frontend), même pattern que `GET /api/babelio-migration/progress`. Expose désormais
  aussi `retry_pending` (bool) et `next_attempt_at` (ISO 8601 ou `null`).
- `GET /api/pgx/logs` — historique des cycles de transcription persistés, plus récent en
  premier (`?limit=50` par défaut). Voir "Historique persisté" ci-dessous.
- `GET /api/pgx/logs/{log_id}` — détail d'un cycle (404 si non trouvé).

Pas d'endpoint `stop` (décision explicite, cohérent avec lmelp qui n'en avait pas non
plus — un pipeline SSH en cours n'est pas trivialement interruptible proprement).

## Logs — en mémoire pour le run courant, historique persisté par cycle

Les logs ligne-par-ligne d'un run **en cours** (`PgxTranscriptionRunner.logs`) restent
en mémoire dans le singleton, réinitialisés à chaque nouveau `start_transcription()`
(`self.logs = []`) — comportement inchangé depuis #302, adapté à un suivi en direct
plutôt qu'à un historique.

Chaque ligne est horodatée (`_log()`, préfixe `dd/mm/yy HH:MM:SS`) — date incluse, pas
seulement l'heure, un run de plusieurs épisodes pouvant s'étaler sur des dizaines de
minutes voire chevaucher minuit.

Depuis l'Issue #309, un **résumé par cycle** (pas les logs bruts) est en revanche
persisté dans la collection MongoDB `pgx_transcription_logs`, sur le modèle de
`rss_download_logs` (#295) — voir "Déclenchement automatique" ci-dessous.

## Déclenchement automatique (Issue #309)

`POST /api/pgx/transcription/start` accepte un paramètre `trigger`, même pattern que
`rss_sync_service.py` (`TriggerRssSyncRequest`) :

- `"manual"` (défaut, bouton UI de `/transcription-pgx`) : comportement inchangé depuis
  #302 — si PGX est injoignable, le cycle s'arrête immédiatement, sans retry (l'utilisateur
  est devant l'écran, il peut relancer lui-même).
- `"api"` (n8n/Automatisch) : si PGX est injoignable **avant qu'aucun épisode n'ait été
  traité**, le backend programme lui-même un retry interne toutes les heures
  (`PGX_TRANSCRIPTION_RETRY_INTERVAL_HOURS`, défaut 1h) jusqu'à ce que PGX redevienne
  joignable ou jusqu'à un plafond de 24h (`PGX_TRANSCRIPTION_RETRY_MAX_HOURS`) — sans
  nouvel appel externe nécessaire. Au-delà du plafond, le cycle est marqué `pgx`.

### Mécanisme de retry — une couche au-dessus de `_run()`, pas une réimplémentation

`PgxTranscriptionRunner._wait_for_reachable_with_retry()` enveloppe uniquement le test
de joignabilité déjà présent dans la boucle `for` de `_run()` — dès que PGX redevient
joignable, le traitement **reprend dans la même boucle, au même index**, sans redémarrer
ni dupliquer la logique d'envoi/attente/rapatriement. `is_running` reste `True` pendant
toute l'attente (y compris les `asyncio.sleep`), donc le garde-fou existant
(`already_running`) couvre nativement le cas d'un appel Automatisch pendant une fenêtre
de retry en cours — aucun nouveau verrou. Voir la règle CLAUDE.md "Retry Scheduling as a
Wrapper, Never a Reimplementation of the Loop It Retries" pour le pattern générique.

### Historique persisté — `pgx_transcription_logs`

Un document par **cycle complet** (déclenchement → succès ou abandon), pas un document
par tentative de retry individuelle (les tentatives sont imbriquées dans `retry_attempts`) :

```python
{
    "started_at": str | None,          # ISO 8601 UTC, début du cycle
    "finished_at": str | None,         # ISO 8601 UTC, fin du cycle — None tant que le
                                        # cycle n'est pas terminé (cf. persistance
                                        # anticipée ci-dessous)
    "trigger": str,                    # "manual" | "api"
    "status": str,                     # "success" | "error" | "pgx"
    "episode_ids": list[str],          # snapshot de la file au démarrage
    "episodes": [                      # un par épisode réellement tenté (vide si abandon avant tout traitement)
        {"episode_id": str, "titre": str, "date": str, "success": bool, "error": str | None},
    ],
    "retry_attempts": [                # vide pour trigger="manual" ou si PGX joignable direct
        {"attempted_at": str, "reachable": bool},
    ],
    "notification_sent": bool,
    "error_message": str | None,       # exception inattendue de haut niveau, sinon None
}
```

**Statuts simplifiés à 3 valeurs** (Issue #313) : `success` (aucun échec), `error` (au
moins un épisode tenté a échoué — qu'il s'agisse d'un échec total ou partiel du cycle),
`pgx` (problème de connexion à la machine PGX elle-même — retry en cours ou abandon
après le plafond de 24h). Le badge résumé n'affiche que ces 3 valeurs (vert pour
`success`, rouge sinon) ; la granularité fine (résultat par épisode, tentatives de
retry) reste disponible dans le détail au clic sur une ligne.

**Persistance anticipée dès l'entrée en retry** (Issue #313) : contrairement au
comportement initial de #309 (un seul `insert_pgx_transcription_log()` en toute fin de
cycle), un cycle qui bascule en retry (`trigger="api"`, PGX injoignable au démarrage)
est persisté dès la première tentative ratée — statut `"pgx"`, `finished_at: None`,
`retry_attempts` déjà peuplé de cette 1re tentative. Le document est ensuite mis à jour
(`update_pgx_transcription_log()`, pas un nouvel insert) à chaque tentative de retry
suivante, puis une dernière fois avec le statut définitif à la fin du cycle. Sans cette
persistance anticipée, un cycle en attente pendant plusieurs heures resterait invisible
dans l'historique alors qu'il travaille activement en arrière-plan (seul le panneau de
progression, via polling `GET /api/pgx/transcription/progress`, montrait cet état).

S'applique aussi bien aux cycles `"manual"` qu'`"api"` — vue unifiée dans la section
"📋 Historique des transcriptions" de `/transcription-pgx` (table + détail expansible au
clic, sur le modèle de `/rss-monitoring`). La liste et le détail ouvert se rafraîchissent
automatiquement pendant le polling de progression (2s) et au clic manuel sur
"🔄 Rafraîchir" — la colonne "Date" du tableau affiche `finished_at` (repli sur
`started_at` tant que le cycle n'est pas terminé).

### Notifications ntfy.sh

Réutilise `send_ntfy_notification()`, extrait de `RssSyncService` (#295) vers
`src/back_office_lmelp/utils/ntfy.py` (fonction standalone, `rss_sync_service.py` non
modifié). Même logique que RSS : **une notification par événement**, au fil de l'eau,
pas de résumé groupé en fin de cycle :

1. **Par épisode transcrit avec succès** — titre `"PGX - Nouvel épisode Le Masque et
   la Plume transcrit — {date}"`, message = titre de l'épisode (aligné sur le pattern
   RSS, `"RSS - Nouvel épisode Le Masque et la Plume téléchargé — {date}"`). Le préfixe
   `"PGX - "`/`"RSS - "` (Issue #313) est ajouté par la couche d'envoi générique
   (`send_ntfy_notification()` pour PGX, `RssSyncService.send_ntfy_notification()` pour
   RSS), pas au niveau des appelants.
2. **Par épisode en échec** (`PgxError`, ex: timeout scp) — titre `"Échec
   transcription PGX — {date}"`, message générique ("erreur technique, voir
   l'historique... pour le détail") — **sans jamais exposer le détail technique brut**
   (ex: stderr SSH multi-lignes type `kex_exchange_identification`) dans la
   notification poussée ; ce détail reste dans `episodes[].error` de l'historique, à
   usage diagnostic.
3. Au **premier** échec de joignabilité déclenchant un retry (`trigger="api"`
   uniquement) — une seule fois, pour signaler qu'il faut allumer PGX, sans attendre
   24h en silence. Message dynamique reprenant les valeurs réelles de
   `PGX_TRANSCRIPTION_RETRY_INTERVAL_HOURS`/`PGX_TRANSCRIPTION_RETRY_MAX_HOURS`.

Aucune notification sur `nothing_to_do`, ni de synthèse groupée en fin de cycle (y
compris sur abandon après plafond de retry — seule la notification du premier échec de
joignabilité, point 3, couvre ce cas).

## Piège réel rencontré : `datetime` non JSON-sérialisable

**Bug trouvé lors du test en conditions réelles** (pas par les tests mockés, dont les
mocks utilisaient initialement une string pour `date` au lieu d'un vrai `datetime`) :
`stats_service.get_episodes_without_transcription()` retournait le champ `date` tel quel
(objet `datetime` MongoDB) → `JSONResponse` de FastAPI levait `"Object of type datetime
is not JSON serializable"` sur `GET /api/pgx/episodes-without-transcription`. Fix :
conversion `.isoformat()` explicite si `isinstance(date_value, datetime)`.

```python
# ❌ WRONG — passthrough du datetime MongoDB, non sérialisable
"date": episode.get("date"),

# ✅ CORRECT — conversion ISO explicite
date_value = episode.get("date")
"date": date_value.isoformat() if isinstance(date_value, datetime) else date_value,
```

Cf. la règle CLAUDE.md "MongoDB DateTime vs String Handling" — ici, le piège se
cachait dans un mock de test qui contredisait cette règle plutôt que dans le code de
production lui-même, d'où sa découverte tardive.

## Piège réel rencontré : `retry_attempts` initial manquant, `finished_at` prématuré

**Bugs trouvés lors du test manuel en conditions réelles (Issue #313)**, sur le
mécanisme de persistance anticipée décrit ci-dessus :

- La toute première tentative de joignabilité (le health-check initial qui déclenche
  l'entrée en retry, avant même le premier `asyncio.sleep`) n'était jamais ajoutée à
  `retry_attempts` — seules les tentatives faites *dans* la boucle `while` de
  `_wait_for_reachable_with_retry()` l'étaient. Résultat : le détail affichait
  "1 tentative" pour un cycle qui en avait en réalité fait 2 (l'échec initial + la
  reprise). Fix : `self.retry_attempts.append({"attempted_at": ..., "reachable":
  False})` ajouté avant la boucle, donc déjà présent dans le document au moment de
  l'insertion initiale.
- `_build_log_document()` calculait systématiquement `finished_at =
  datetime.now(UTC)`, y compris pour le document intermédiaire "pgx" pas encore
  terminé — donnant la date de la 1re tentative ratée comme fausse "date de fin"
  visible dans la colonne Date du tableau. Fix : paramètre `finished: bool = True` ;
  le document intermédiaire est construit avec `finished=False` (`finished_at: None`).

Les deux bugs n'ont été découverts que par capture d'écran de l'utilisateur en
conditions réelles — les tests unitaires initiaux du mécanisme de persistance
anticipée vérifiaient le comportement "insert puis update", sans vérifier le contenu
exact du tout premier document inséré.

## Cache dashboard

`episodes_without_transcription_count` fait partie du payload caché standard
(`StatsService.get_cache_statistics()`, consommé par `GET /api/dashboard/stats`). Voir
`docs/dev/dashboard-stats-cache.md` pour le mécanisme d'invalidation automatique — plus
besoin d'endpoint dédié non caché ni de logique de comparaison de compteur, contrairement
à l'implémentation initiale de la tuile (Issue #298), car l'écriture du champ
`transcription` passe désormais nativement par le `MongoClient` de ce backend.

**Isolation par métrique (Issue #310)** : `get_cache_statistics()` enveloppe chaque calcul
de métrique (dont `_count_episodes_without_transcription()`) dans un helper `_safe()` qui
catch toute exception et retourne `None` — sans cette isolation, une seule métrique en
échec (ex: collection `episodes` temporairement inaccessible) faisait planter tout le
payload `/api/dashboard/stats` en 500 via `asyncio.gather()`, cassant les 14 tuiles du
dashboard plutôt que la seule tuile concernée. Voir CLAUDE.md, section "Cache Invalidation
Without a Write Abstraction Layer", pour le pattern complet (backend + fallback frontend
correspondant dans `Dashboard.vue`).

## Prérequis Docker : `openssh-client` dans l'image runtime

**Piège rencontré au premier déploiement NAS (Issue #310)** : `pgx_service.py` shell-out
vers `ssh`/`scp`/`ssh-keygen` via `asyncio.create_subprocess_exec`. Si ces binaires ne
sont pas installés dans l'image Docker du service `backend`, chaque appel lève
`FileNotFoundError: [Errno 2] No such file or directory` — indiscernable dans les logs
d'un problème de configuration PGX (host/clé/réseau). Invisible en devcontainer (`ssh` y
est déjà présent nativement) et dans la suite pytest (tous les subprocess sont mockés) :
seul un déploiement réel de l'image le révèle.

`docker/build/backend/Dockerfile` installe désormais `openssh-client` dans le stage
runtime, à la suite de `curl`/`gosu`. Si ce service est un jour porté vers une autre
image de base ou un autre pipeline de build, vérifier que ce paquet suit.

## Configuration

Voir `docs/dev/environment-variables.md` pour le détail des variables `PGX_HOST`,
`PGX_USER`, `PGX_SSH_KEY_PATH`, `PGX_REMOTE_AUDIO_ROOT`,
`PGX_REMOTE_TRANSCRIPTION_ROOT`, `PGX_TRANSCRIPTION_TIMEOUT_S`, `PGX_POLL_INTERVAL_S`,
`PGX_TRANSCRIPTION_RETRY_INTERVAL_HOURS`, `PGX_TRANSCRIPTION_RETRY_MAX_HOURS`.

## Tests

Tous les tests mockent `asyncio.create_subprocess_exec`/`asyncio.open_connection` —
aucun accès réseau réel, et le retry horaire est testé en mockant `asyncio.sleep` +
en réduisant les intervalles de retry (settings patchés à des heures fractionnaires
minuscules) plutôt qu'en attendant de vraies heures :

- `tests/test_pgx_service.py` — fonctions pures et pipeline SSH/SCP mockées.
- `tests/test_pgx_transcription_runner.py` — orchestration de la file (singleton,
  `already_running`/`nothing_to_do`, cascade d'échecs, cache local, retry horaire
  (`TestApiRetryScheduling`), persistance de l'historique par statut
  (`TestPgxTranscriptionLogPersistence`)).
- `tests/test_pgx_endpoints.py` — endpoints FastAPI (mocks du service/runner),
  y compris le piège FastAPI body-absent (`TestStartPgxTranscriptionTrigger`)
  et les nouveaux endpoints `GET /api/pgx/logs`/`GET /api/pgx/logs/{id}`.
- `tests/test_mongodb_service_pgx.py` — CRUD de la collection `pgx_transcription_logs`.
- `tests/test_ntfy.py` — helper de notification standalone extrait de RSS.

Le pipeline complet a aussi été validé en conditions réelles (vraie station PGX, base
MongoDB locale de test — voir `docs/dev/blocage_ip.md` pour le mécanisme de base locale
séparée de la prod), sur 2 épisodes réels : envoi scp, attente (~3-4 min chacun),
rapatriement, écriture Mongo, puis re-test confirmant le cache local (traitement
quasi instantané sans appel réseau).

## Voir aussi

- `src/back_office_lmelp/services/pgx_service.py`
- `src/back_office_lmelp/utils/pgx_transcription_runner.py`
- `src/back_office_lmelp/utils/migration_runner.py` (pattern singleton + polling source)
- `frontend/src/views/PgxTranscription.vue` (page dédiée `/transcription-pgx`)
- `docs/user/transcription-pgx.md` (documentation utilisateur)
- `docs/dev/rss-sync.md` — `audio_rel_filename` (format `<année>/<basename(url)>`,
  écrit par `RssSyncService.download_audio()`) est le champ consommé par ce pipeline
  pour localiser le fichier audio local de chaque épisode.
