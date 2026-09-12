# Issue #313 — Test end-to-end de l'automatisation PGX : 8 corrections découvertes

## Contexte

Suite de #302 (portage) et #309/#310/#312 (automatisation + retry +
historique + déploiement NAS). L'issue #313 demandait un test manuel
complet en conditions réelles : déclenchement via curl, suppression
manuelle en base d'une transcription pour reforcer le retraitement,
vérification des messages ntfy.sh et de l'historisation dans
`/transcription-pgx` — sur laptop d'abord, puis NAS. Contrairement aux
issues précédentes de cette série, ce n'était **pas** une demande de
correctif ciblé mais un test exploratoire, qui a révélé 6 bugs/défauts
réels invisibles en tests unitaires (mocks trop optimistes) mais
immédiats en usage réel.

Travail encore non commité au moment de cette mémoire — working tree sur
la branche
`313-transcription-automatique-tester-de-bout-en-bout-lautomatisation-de-la-transcription`.

## Découverte n°1 — `/api/pgx/logs` plantait systématiquement (bug critique, historique vide en silence)

`GET /api/pgx/logs` renvoyait `{"error": "Object of type datetime is not
JSON serializable"}` dès qu'un document existait dans
`pgx_transcription_logs`. Cause : `_build_log_document()` dans
`src/back_office_lmelp/utils/pgx_transcription_runner.py` stockait
`started_at`/`finished_at` comme `datetime` Python brut (pas `.isoformat()`),
contrairement à `attempted_at` dans `retry_attempts` qui, lui, était déjà
correctement formaté en string. Fix : `.isoformat()` sur les deux champs
avant persistance Mongo.

**Pourquoi les tests ne l'ont jamais attrapé** : tous les mocks de test
existants (`TestGetPgxLogs`/`TestGetPgxLogById` dans
`tests/test_pgx_endpoints.py`) inventaient des dicts avec seulement
`_id`/`trigger`/`status` — jamais `started_at`/`finished_at` avec un vrai
type `datetime`, donc le chemin de sérialisation réel n'était jamais
exercé. Symptôme en usage réel : la page `/transcription-pgx` affichait
silencieusement "Aucune transcription enregistrée" (l'appel axios échouait
sans afficher d'erreur visible) — un board vide qui *semble* juste être
un état normal "pas encore de cycle", pas une erreur.

Test RED ajouté : `TestPgxTranscriptionLogPersistence::test_should_persist_json_serializable_log_document`
(`tests/test_pgx_transcription_runner.py`) — appelle `json.dumps(log_doc)`
sur le document réellement construit par `_run()`, pas un mock inventé.

## Découverte n°2 — Détail de l'historique vide (titre/date absents par épisode)

Le clic sur une ligne d'historique affichait `• — succès` au lieu de
`06/09/26 **Titre** — succès` (pattern RSS attendu, demande explicite de
l'utilisateur : "je veux garder exactement le même pattern que pour le
flux RSS"). Cause : `self.processed` dans `_run()` ne stockait que
`{episode_id, success, error}` — le template Vue
(`frontend/src/views/PgxTranscription.vue`) lisait `ep.titre`/`ep.date`
qui n'existaient simplement pas dans le document Mongo persisté.

Fix backend : ajout de `titre` et `date` (`.isoformat()`, même piège que
découverte n°1) dans les deux branches (succès et `except PgxError`) de la
boucle `for` de `_run()`. Fix frontend : ajout d'un
`<span class="episode-date">{{ formatEpisodeDate(ep.date) }}</span>` dans
le template de détail (`PgxTranscription.vue:152`) — la méthode
`formatEpisodeDate()` existait déjà (réutilisée pour la liste des
épisodes en attente), seul le template de détail ne l'appelait pas.

4 assertions d'égalité stricte existantes sur `runner.processed == [...]`
ont dû être mises à jour pour inclure les nouveaux champs (TDD complet :
RED confirmé sur le comportement business avant modification du code
puis des tests).

## Découverte n°3 — Titres ntfy incohérents avec le pattern RSS + demande de préfixes

Demande explicite : le titre de succès PGX
(`"Transcription PGX terminée — {date}"`) devait matcher le pattern RSS
(`"Nouvel épisode Le Masque et la Plume téléchargé — {date}"`), en
remplaçant juste le verbe → `"Nouvel épisode Le Masque et la Plume
transcrit — {date}"`. Puis demande complémentaire, mi-session : préfixer
tous les messages ntfy par la source, pour la lisibilité sur mobile —
`"RSS - "` pour le flux RSS, `"PGX - "` pour la transcription.

**Piège de conception découvert en cours d'implémentation** : le premier
essai a préfixé dans `PgxTranscriptionRunner._send_notification()` — mais
les tests `TestPgxNtfyNotifications` mockent `_send_notification`
directement (`patch.object(runner, "_send_notification", ...)`), donc le
préfixe n'y était jamais exercé, RED pour la mauvaise raison (les
assertions de test qui vérifiaient le préfixe passaient à cet endroit-là
alors que le vrai code de prod ne l'appliquait jamais en pratique — le
bug inverse de d'habitude). Fix : préfixe déplacé une couche plus bas,
dans le générique `src/back_office_lmelp/utils/ntfy.py::send_ntfy_notification()`
(`title = f"PGX - {title}"`) — seul consommateur de ce module (confirmé
par grep), donc sans risque pour RSS. Le préfixe RSS symétrique est ajouté
directement dans `RssSyncService.send_ntfy_notification()`
(`src/back_office_lmelp/services/rss_sync_service.py`), qui a sa propre
implémentation HTTP dupliquée (décision historique de #309 : ne jamais
toucher au code RSS).

## Découverte n°4 — Message ntfy d'échec exposait un détail SSH brut illisible

En testant une vraie coupure réseau (machine PGX en cours d'extinction,
port 22 encore ouvert mais la session SSH se réinitialise en plein milieu
d'une opération), le message ntfy reçu était :

```
PGX - Échec transcription PGX — 06/09/26
Haenel, Bellanger, ... : Échec de la création du répertoire distant sur PGX:
kex_exchange_identification: read: Connection reset by peer
Connection reset by 192.168.50.151 port 22
```

Retour utilisateur : "pas compréhensible à un non initié". Cause :
`await self._send_notification(title, f"{titre} : {exc}")` interpolait
l'exception brute (stderr SSH multi-lignes) directement dans le corps du
message push. Fix : message générique
`f"{titre} : erreur technique, voir l'historique dans Back-office LMELP
pour le détail"` — le détail technique reste dans les logs applicatifs et
dans `episodes[].error` de l'historique `/transcription-pgx` (usage
diagnostic), plus dans la notification poussée à l'utilisateur final.

**Décision explicite de ne PAS étendre le retry à ce cas** (demande posée
via AskUserQuestion) : une connexion réinitialisée *en cours de transfert*
reste un échec définitif de l'épisode pour ce cycle ; seul l'échec du
health-check initial (`wait_for_pgx_reachable` avant tout envoi) déclenche
le mécanisme de retry horaire de #309. Distinction jugée pertinente par
l'utilisateur : le retry existant suffit à couvrir "PGX est éteint", pas
la peine de généraliser aux erreurs SSH en cours de session.

Test RED :
`TestPgxNtfyNotifications::test_should_not_leak_raw_ssh_error_detail_in_failure_notification`
— reproduit l'exacte chaîne d'erreur SSH observée en conditions réelles
(pas un message d'erreur inventé, cf. règle CLAUDE.md sur les mocks
réalistes), asserte l'absence de `"kex_exchange_identification"` /
`"Connection reset by peer"` dans le message envoyé.

## Découverte n°5 — Intervalle de retry codé en dur dans le message ntfy ("toutes les heures")

Le message "allumez PGX" (premier échec de joignabilité, cf. #309)
contenait le texte littéral **"toutes les heures"**, alors que l'intervalle
réel est piloté par `settings.pgx_transcription_retry_interval_hours`
(configurable via `PGX_TRANSCRIPTION_RETRY_INTERVAL_HOURS`). Découvert en
testant avec un intervalle accéléré à 5 min
(`PGX_TRANSCRIPTION_RETRY_INTERVAL_HOURS=0.0833` temporaire dans `.env`,
non commité — fichier gitignored) pour ne pas attendre 1h en conditions de
test : le message continuait à afficher "toutes les heures" malgré un
retry réel toutes les 5 min. Fix : interpolation dynamique
`f"tentative automatique toutes les {interval_h}h pendant {max_h}h."` dans
`_wait_for_reachable_with_retry()`. Test RED avec des valeurs distinctes
de test (`1.0`/`3.0`) pour détecter une régression vers un texte figé.

## Découverte n°6 — Logs affichés en UTC brut, utilisateur basé à Paris

`PgxTranscriptionRunner._log()` formatait `datetime.now(UTC)` directement
sans conversion de fuseau — les lignes affichées dans le panneau de
progression de `/transcription-pgx` (`pgxProgress.logs`, liste de strings
déjà pré-formatées, contrairement à `next_attempt_at` qui est un ISO
timestamp formaté côté frontend avec `toLocaleString('fr-FR', ...)` donc
déjà correct). Vérification faite que RSS n'a **pas** d'équivalent direct
à copier (`RssSyncService` ne persiste que des documents structurés
formatés côté frontend, pas de liste de strings pré-formatées comme
`pgxProgress.logs` — le mécanisme `_log()` est spécifique à PGX, sans
pattern RSS à répliquer ici).

Option écartée : s'appuyer sur le fuseau horaire du conteneur (proposée
par l'utilisateur) — vérifié que ni le devcontainer (`/etc/timezone` =
`Etc/UTC` malgré `date` affichant CEST via horloge système) ni le
Dockerfile de prod (`docker/build/backend/Dockerfile`, aucun `ENV TZ`) ne
garantissent un fuseau Paris fiable. Fix retenu : conversion explicite via
stdlib `zoneinfo.ZoneInfo("Europe/Paris")` dans `_log()`
(`now.astimezone(ZoneInfo("Europe/Paris"))` avant le `strftime`), robuste
quel que soit le fuseau système et gère automatiquement CET/CEST — aucune
dépendance externe (zoneinfo est stdlib depuis Python 3.9).
`self.last_update` reste en UTC (usage API interne uniquement, pas
affiché tel quel).

## Découverte n°7 (mineure, UI) — pluriel "épisode(s)" non accordé + bloc clé SSH toujours visible

Deux ajustements UI demandés en cours de session sur
`frontend/src/views/PgxTranscription.vue` :

- `"{{ pgxEpisodes.length }} épisode(s) seront traités :"` (littéral, jamais
  accordé) → nouvelle computed `pgxEpisodesCountLabel` :
  `"{n} épisodes seront traités :"` si `n > 1`, `"{n} épisode sera traité
  :"` sinon.
- Le bloc "Clé SSH dédiée — à autoriser sur PGX" restait affiché même une
  fois l'authentification SSH validée (`status: "ok"` sur tous les
  diagnostics) — inutile une fois la config fonctionnelle. Nouvelle
  computed `sshAuthOk` (cherche le diagnostic dont le `name` commence par
  `"Authentification SSH"`, vérifie `status === 'ok'`) ; condition du bloc
  passée de `v-if="sshPublicKey"` à `v-if="sshPublicKey && !sshAuthOk"`.

## Validation manuelle en conditions réelles (pas seulement en tests unitaires)

Séquence de test qui a permis de découvrir ces bugs (impossible à
reproduire uniquement via mocks) :
1. Processus backend orphelin détecté au démarrage de session (PID actif,
   `.dev-ports.json` absent) — tué proprement après confirmation qu'il ne
   répondait pas à un `kill` simple (`kill -9` ciblé sur ce PID précis
   seulement après ce constat).
2. Diagnostic `/api/pgx/diagnostics` confirmant PGX injoignable
   (port 22 fermé) → découverte n°1 exercée via un cycle "cache local"
   (fichier `.txt` déjà présent à côté du `.m4a`, court-circuite l'aller-
   retour SSH réel — cf. `_run()` lignes ~250-256).
3. Suppression du `.txt` local (sauvegardé au préalable dans le
   scratchpad) + `$unset` du champ `transcription` en base par
   l'utilisateur (pas d'outil MCP MongoDB en écriture disponible dans
   cette session) → force un vrai passage par `pgx_service`.
4. PGX rallumée par l'utilisateur *pendant* une tentative → révélé
   découverte n°4 (connexion réinitialisée mi-session SSH, distincte d'un
   simple timeout de reachability check).
5. Retry accéléré temporairement à 5 min (`.env`, non commité) → cycle
   complet avec `retry_attempts: [{attempted_at, reachable: true}]` et
   reprise automatique réussie, confirmant que le retry de #309 fonctionne
   correctement de bout en bout (reprise à l'index courant de la boucle
   `for`, pas de réimplémentation — décision de conception de #309
   validée en conditions réelles).
6. Vérification finale via Playwright MCP (headless) sur
   `/transcription-pgx` après chaque fix : historique affiché
   correctement, détail avec date/titre, bloc SSH masqué une fois OK,
   pluriel correct — captures supprimées après chaque vérification.

## Découverte n°8 — Historique statique pendant les longues attentes de retry (retour utilisateur en cours de test)

Après les 6 premières découvertes, l'utilisateur a continué le test manuel
et posé une question clé : "que se passe-t-il dans cette liste si je la
consulte pendant qu'un cycle attend son retry ?". Réponse observée : le
document en base n'existait tout simplement pas encore — `_finalize_cycle`
n'insérait qu'un seul document, **à la toute fin** du cycle
(`insert_pgx_transcription_log`, jamais de mise à jour intermédiaire). Un
cycle qui attend un retry pendant potentiellement 24h restait donc
invisible dans `/api/pgx/logs`, alors que le panneau de progression
au-dessus montrait bien `retry_pending: true`. Décision explicite de
l'utilisateur : "ajoutons une entrée pour cette demande avec un
déclenchement api, un statut pgx_deconnecté, episodes 1, et dans le détail
ce qu'on a aujourd'hui, et au fur et à mesure de l'avancement ajouter des
entrées dans le détail et changer le statut général si besoin."

**Refonte du flux de persistance** — passage d'un unique `insert` final à
`insert` anticipé + `update` au fil de l'eau + `update` final :
- Nouvelle méthode `mongodb_service.update_pgx_transcription_log(log_id,
  log_data)` (`$set` par `_id`), symétrique à `insert_pgx_transcription_log`.
- Nouvel attribut `self.current_log_id: str | None` sur
  `PgxTranscriptionRunner`, réinitialisé dans `_initialize()` et
  `start_transcription()`.
- `_persist_pending_retry_cycle(trigger)` : appelée une seule fois, au
  premier échec de joignabilité (`first_attempt` dans
  `_wait_for_reachable_with_retry()`), juste après la notification "allumez
  PGX". Insère le document avec statut `"pgx"`, garde l'`_id` retourné dans
  `self.current_log_id`.
- `_sync_retry_attempts_to_log()` : appelée après **chaque** ajout à
  `self.retry_attempts` dans la boucle de retry — fait un `update` ciblé
  sur `current_log_id` (pas un nouvel insert).
- `_finalize_cycle()` : si `current_log_id` est déjà défini (un retry a eu
  lieu), fait un `update` plutôt qu'un `insert` — sinon comportement
  inchangé (cycle nominal sans retry, jamais visible avant la fin, ce qui
  reste acceptable car rapide).

**Statuts simplifiés en 3 valeurs** (demande explicite, "si je veux voir
le detail j'ouvre, succes/error/pgx en vert et rouge") — l'ancien jeu de 4
statuts (`success`/`partial_error`/`error`/`pgx_unreachable_abandoned`)
prêtait à confusion (`partial_error` sur un cycle à 1 seul épisode qui
échoue *totalement* n'a rien de "partiel"). Nouveau mapping dans `_run()` :
`success` (aucun échec), `error` (au moins un épisode tenté a échoué —
regroupe l'ancien `partial_error` ET l'ancien `error` total),
`pgx` (regroupe l'ancien `pgx_unreachable_abandoned` ET le nouveau statut
intermédiaire "en cours de retry"). Le badge frontend
(`pgxLogStatusBadgeClass`) n'a presque pas changé : `success` → vert,
tout le reste → rouge (le fallback existant couvrait déjà `error`/`pgx`).
Toute la granularité fine (résultat par épisode, `retry_attempts`) reste
disponible dans le détail au clic — seul le badge résumé est simplifié.

**Piège de conception découvert dans cette refonte — RED pour la mauvaise
raison, deux fois** : contrairement au reste de la session (où les tests
RED échouaient bien pour la raison métier attendue), deux tests de
comptage se sont révélés faux dans leur propre logique, pas dans le code :
- Le test `test_should_persist_log_as_soon_as_retry_starts_then_update_per_attempt`
  attendait `update_pgx_transcription_log.call_count == 2` pour un
  scénario `side_effect=[False, False, True]` (3 tentatives) — oubli que
  `_sync_retry_attempts_to_log()` est appelée à **chaque** tentative, y
  compris la dernière réussie, donc 3 appels, pas 2.
- Le test de récapitulatif de retry côté frontend (Playwright manuel,
  capture utilisateur) a révélé que "12/09/2026 13:39 — PGX injoignable"
  (le tout premier échec du health-check, celui qui déclenche l'entrée en
  retry) n'apparaissait **jamais** dans `retry_attempts` — seules les
  tentatives faites *dans* la boucle `while` (après le premier `sleep`)
  y étaient ajoutées. Fix : `self.retry_attempts.append({"attempted_at":
  ..., "reachable": False})` ajouté juste avant la boucle `while` dans
  `_wait_for_reachable_with_retry()`, avant même l'appel à
  `_persist_pending_retry_cycle()` — donc ce document initial contient
  déjà cette 1re entrée dès l'insertion. A décalé le compte attendu dans
  les deux tests concernés (`inserted_doc["retry_attempts"]` a 1 élément
  dès l'insert, pas 0 ; le total final passe de 3 à 4 pour le scénario
  `[False, False, True]`).

**Piège `finished_at` trompeur découvert par capture utilisateur** —
`_build_log_document()` calculait systématiquement `finished_at =
datetime.now(UTC)`, y compris pour le document *intermédiaire* "pgx" pas
encore terminé — donnant l'heure de la 1re tentative ratée comme fausse
"date de fin". Une fois que le frontend a été corrigé pour afficher
`finished_at` (au lieu de `started_at`) dans la colonne Date du tableau —
demande explicite : "l'heure générale devrait changer aussi, l'heure de
fin pas l'heure de début" — ce `finished_at` prématuré serait devenu
visible et trompeur. Fix : nouveau paramètre `finished: bool = True` sur
`_build_log_document()` ; `_persist_pending_retry_cycle()` appelle avec
`finished=False` (→ `finished_at: None` dans le document intermédiaire),
`_finalize_cycle()` garde le défaut `True`. Frontend : colonne Date passe
de `formatDateTime(log.started_at)` à
`formatDateTime(log.finished_at || log.started_at)` (repli sur
`started_at` tant que `finished_at` est `null`, cas d'un cycle encore en
cours).

**Détail ouvert non resynchronisé — bug de UX découvert par capture
utilisateur, pas par les tests** : le tableau parent (`pgxLogs`) se
rafraîchissait bien au clic sur "Rafraîchir" et pendant le polling, mais le
**détail déjà ouvert** (`detailedPgxLog`, chargé une seule fois au clic
initial sur la ligne via `togglePgxLogDetail`) restait figé sur son état
au moment de l'ouverture — capture utilisateur montrant le badge général
passé à "success" mais le détail toujours bloqué sur "toujours
injoignable, 1 tentative". Fix : nouvelle méthode
`refreshExpandedPgxLogDetailSilently()` (no-op si `expandedPgxLogId` est
`null`), appelée à la fois dans `checkPgxProgress()` (polling 2s pendant
un cycle actif) et dans `loadPgxLogs()` (clic manuel sur "Rafraîchir").
Extraction similaire côté liste : `refreshPgxLogsSilently()` isolé de
`loadPgxLogs()` pour ne pas re-basculer `loadingPgxLogs` à chaque tick de
polling (éviterait un clignotement du "Chargement..." toutes les 2s).

**Séquence de vérification manuelle** (2e round, PGX rallumée par
l'utilisateur entre chaque étape) : cycle démarré à PGX éteinte → entrée
"PGX injoignable" immédiate visible dans le détail dès ouverture → PGX
rallumée manuellement → capture "statut général encore `pgx`, détail
figé" (bug détail non resynchronisé, ci-dessus) → clic "Rafraîchir" →
capture "statut passé à `success`, détail toujours figé sur l'ancien état,
colonne Date affichant l'heure de début pas de fin" (2 bugs supplémentaires
ci-dessus) → 3 fixes appliqués → nouvelle capture Playwright confirmant les
3 corrections simultanément : `11:44` en colonne Date (heure de fin),
"12/09/2026 11:39 — PGX injoignable" en 1re ligne du détail, "repris après
2 tentatives" dans le récapitulatif.

## Fichiers modifiés

Backend :
- `src/back_office_lmelp/utils/pgx_transcription_runner.py` — isoformat
  `started_at`/`finished_at`/`date` par épisode, titre ntfy succès aligné
  RSS, message ntfy échec sans détail technique, intervalle dynamique dans
  le message retry, conversion `zoneinfo` dans `_log()`, `current_log_id`
  + `_persist_pending_retry_cycle()` + `_sync_retry_attempts_to_log()`
  (persistance anticipée), statuts simplifiés à 3 valeurs, paramètre
  `finished` sur `_build_log_document()`, 1re entrée `retry_attempts`
  ajoutée avant la boucle de retry.
- `src/back_office_lmelp/utils/ntfy.py` — préfixe `"PGX - "`.
- `src/back_office_lmelp/services/rss_sync_service.py` — préfixe
  `"RSS - "` dans `send_ntfy_notification()`.
- `src/back_office_lmelp/services/mongodb_service.py` — nouvelle méthode
  `update_pgx_transcription_log(log_id, log_data)`.
- `src/back_office_lmelp/utils/memory_guard.py` — seuil pytest 500→1000MB
  (flakiness pré-existante sans lien avec l'issue, cf. section dédiée).
- `src/back_office_lmelp/app.py` — annotation de type explicite sur
  `_server_instance: "uvicorn.Server | None"` (fix mypy pré-existant
  révélé en touchant `memory_guard.py`, sans lien fonctionnel avec #313).

Frontend :
- `frontend/src/views/PgxTranscription.vue` — `formatEpisodeDate(ep.date)`
  dans le détail d'historique, computed `sshAuthOk`, computed
  `pgxEpisodesCountLabel`, `refreshPgxLogsSilently()` /
  `refreshExpandedPgxLogDetailSilently()` (rafraîchissement automatique
  liste + détail pendant le polling et au clic manuel "Rafraîchir"),
  `retryAttemptsSummary()`, colonne Date sur `finished_at || started_at`,
  badge simplifié (`success` vs tout le reste).

Tests (TDD strict, RED confirmé avant chaque fix) :
- `tests/test_pgx_transcription_runner.py` — nouveaux tests dans
  `TestPgxTranscriptionLogPersistence` (sérialisation JSON, statuts
  simplifiés, `finished_at: None` sur le document intermédiaire),
  `TestPgxNtfyNotifications` (anti-fuite détail SSH),
  `TestApiRetryScheduling` (intervalle dynamique, persistance anticipée +
  mise à jour par tentative, 1re entrée retry_attempts) ; assertions
  d'égalité stricte sur `runner.processed` mises à jour (titre/date
  ajoutés).
- `tests/test_mongodb_service_pgx.py` — test dédié à
  `update_pgx_transcription_log`.
- `tests/test_ntfy.py` / `tests/test_rss_sync_service.py` — assertion sur
  le header `Title` mise à jour avec le préfixe attendu.
- `tests/test_memory_guard_simple.py` — assertion mise à jour sur le
  nouveau seuil (1000MB).
- `frontend/src/views/__tests__/PgxTranscription.spec.js` — nouveaux tests
  détail avec titre/date, masquage bloc SSH, pluriel singulier/pluriel,
  rafraîchissement auto de la liste et du détail pendant le polling et via
  le bouton "Rafraîchir", colonne Date sur `finished_at`.

## Vérifications effectuées

- Backend : 1704 tests passent, 24 skipped, aucune régression — stable
  sur 2 exécutions consécutives de la suite complète après augmentation
  du garde-fou mémoire (cf. découverte flakiness ci-dessous).
- Frontend : 764 tests passent, 14 skipped, aucune régression.
- `pre-commit run --files <tous les fichiers modifiés>` : tous verts.
- **Flakiness pré-existante découverte et corrigée en cours de session** :
  ~24 tests échouaient de façon intermittente sur l'exécution complète de
  la suite (jamais en isolation ni en sous-ensemble) — root cause :
  `memory_guard.py` (garde-fou mémoire RSS du process pytest lui-même,
  seuil 500MB conçu pour la prod NAS) déclenchait parfois un vrai
  `SystemExit(1)` pendant les ~1700 tests de la suite complète. Confirmé
  pré-existant (2 runs consécutifs de la baseline stashée passent
  parfaitement), aggravé par la croissance de code de cette session.
  Décision utilisateur : augmenter le seuil à 1000MB plutôt
  qu'investiguer une vraie fuite mémoire (30GB de RAM système
  disponibles, seuil arbitraire sans rapport avec une contrainte réelle
  de ce contexte de test).
- Test manuel via curl + MongoDB MCP (lecture seule) + Playwright MCP,
  sur 3 rounds successifs avec l'utilisateur : historique JSON valide,
  détail avec titre/date, notifications ntfy avec préfixe correct et
  message d'échec assaini, retry avec reprise automatique réussie
  observée en conditions réelles (PGX rallumée par l'utilisateur pendant
  l'attente) à 3 reprises distinctes, persistance anticipée + mise à jour
  au fil de l'eau confirmée en base et à l'écran, rafraîchissement
  automatique de la liste ET du détail ouvert confirmé.

## Reste à faire (au moment de cette mémoire)

- Test NAS (deuxième volet demandé par l'issue #313, via Automatisch) —
  reporté, pas fait dans cette session (laptop uniquement).
- Mise à jour éventuelle de `docs/user/transcription-pgx.md` /
  `docs/dev/pgx-transcription.md` si les messages ntfy y sont documentés
  textuellement, et pour documenter les 3 statuts simplifiés
  (`success`/`error`/`pgx`).
- Commit atomique + push.
- `mkdocs build --strict`.
- Vérification CI/CD.
- Préparation et validation de la PR.
