# Issue #309 — Automatiser la transcription PGX (API + retry horaire + historique persisté)

## Contexte

Suite de l'issue #302 (portage du pipeline PGX). L'endpoint
`POST /api/pgx/transcription/start` était uniquement déclenchable
manuellement (bouton UI), avec abandon immédiat et définitif si PGX était
injoignable. L'issue #309 rend ce déclenchement automatisable par un outil
externe (n8n/Automatisch), sur le modèle déjà en place pour
`POST /api/rss/sync` (`trigger: "manual" | "api"`), avec un retry
automatique côté backend puisque PGX est allumée manuellement et
irrégulièrement (pas de réveil à distance).

Travail encore non commité au moment de cette mémoire — tout en working
tree sur la branche `309-automatiser-le-déclenchement-de-la-transcription-pgx-api-+-retry-horaire-+-historique-persisté`.

## Décision de conception clé : retry en couche par-dessus `_run()`, zéro duplication

Le point le plus délicat de conception était d'éviter de réimplémenter la
boucle de traitement des épisodes. Solution retenue dans
`src/back_office_lmelp/utils/pgx_transcription_runner.py` :

- `start_transcription()` et `_run()` reçoivent un paramètre `trigger`
  (défaut `"manual"`).
- Pour `trigger="manual"` : comportement inchangé, abandon immédiat si
  `pgx_service.wait_for_pgx_reachable()` échoue.
- Pour `trigger="api"` : sur le même échec, appel à une nouvelle coroutine
  `_wait_for_reachable_with_retry(host)` qui boucle
  `sleep(PGX_TRANSCRIPTION_RETRY_INTERVAL_HOURS × 3600)` → re-teste la
  joignabilité, jusqu'à `PGX_TRANSCRIPTION_RETRY_MAX_HOURS` (défaut 24h,
  budget en temps réel via `datetime.now(UTC) < retry_deadline`, pas un
  compteur de tentatives). Si joignable entretemps, **la boucle `for`
  existante de `_run()` continue à l'index courant** — aucune
  réimplémentation de l'envoi/attente/rapatriement.
- `is_running` reste `True` pendant tout le retry (y compris les
  `asyncio.sleep`) : le garde-fou déjà existant dans `start_transcription()`
  (`already_running`) empêche nativement tout chevauchement, sans nouveau
  verrou.

**Piège de test rencontré** : mocker `asyncio.sleep` (instantané) ne suffit
pas à faire converger rapidement la condition d'arrêt `datetime.now(UTC) <
retry_deadline`, car le temps *réel* qui s'écoule entre deux itérations
mockées reste minuscule — avec `retry_max_hours=2` en test, la boucle a
tourné ~17s de temps réel avant d'atteindre le deadline. Fix : dans les
tests qui doivent vraiment épuiser le cap, utiliser des valeurs d'heures
fractionnaires minuscules (`retry_interval_hours=0.0001`,
`retry_max_hours=0.0001-0.0002`) plutôt que mocker `datetime.now`
directement (mock fragile car `_wait_for_reachable_with_retry` appelle
`datetime.now(UTC)` 4 fois par itération). Voir
`tests/test_pgx_transcription_runner.py::TestApiRetryScheduling::test_should_abandon_after_max_hours_reached`
et `TestPgxTranscriptionLogPersistence::test_should_persist_pgx_unreachable_abandoned_status_after_retry_cap`.

## Notifications — deux révisions successives suite à retours utilisateur

**Révision 1 (en cours de plan)** : le plan initial ne prévoyait qu'une
notification à la fin du cycle (succès/échec/abandon groupé). L'utilisateur
a demandé une notification dès le **premier** échec de joignabilité, sinon
aucun moyen de savoir qu'il faut allumer PGX avant l'épuisement silencieux
des 24h. Ajout d'un flag `first_attempt` dans
`_wait_for_reachable_with_retry()` — notification une seule fois au tout
premier échec, jamais répétée aux tentatives suivantes.

**Révision 2 (après implémentation complète, sur capture d'écran ntfy
fournie par l'utilisateur)** : le message de fin de cycle groupé
("Transcription PGX terminée / Tous les épisodes ont été traités") a été
jugé "pas terrible" en comparaison du fil de notifications RSS, qui
affiche **une ligne par épisode** avec son titre exact
("Nouvel épisode Le Masque et la Plume téléchargé — {date}" / titre du
livre). Demande explicite : "je voudrais exactement la même logique que
pour RSS". Décision retenue après clarification (AskUserQuestion) :
- **Suppression complète** de la notification de fin de cycle groupée et
  de `_notification_content()`/l'ancien appel dans `_finalize_cycle()`.
- **Notification par épisode transcrit avec succès**, envoyée au fil de
  l'eau dans la boucle `for` de `_run()` (pas en fin de cycle) : titre
  `"Transcription PGX terminée — {date}"`, message = titre de l'épisode —
  copie conforme de `RssSyncService._format_episode_date()` +
  `send_ntfy_notification()`. Nouvelle méthode statique
  `_format_episode_date()` ajoutée au runner, dupliquée depuis
  `rss_sync_service.py` (même raison que l'extraction `ntfy.py` : éviter
  de toucher au code RSS existant).
- **Notification par épisode en échec** (`PgxError`, ex: timeout scp),
  même granularité que le succès — décision explicite de l'utilisateur
  ("Notifier aussi cet échec isolé"), contrairement à RSS qui ne notifie
  pas sur `outcome: "error"`.
- **Notification "allumez PGX"** (premier échec de joignabilité) inchangée
  de la révision 1 — reste le seul signal pour le cas
  `pgx_unreachable_abandoned` (pas de notif finale distincte pour ce cas).
- **Piège de code corrigé en passant** : la variable `episode` (utilisée
  pour formater la date dans la notif d'échec) pouvait référencer
  l'épisode de l'itération *précédente* de la boucle si
  `mongodb_service.get_episode_by_id()` renvoyait `None` pour l'épisode
  courant (le `raise PgxError` intervient avant toute affectation locale)
  — fix : `episode = None` / `titre = episode_id` réinitialisés en tête de
  chaque itération, garde `if episode is not None` avant d'appeler
  `_format_episode_date(episode["date"])` dans la branche `except PgxError`.

Cette révision a nécessité de retoucher `tests/test_pgx_transcription_runner.py`
(nouvelle classe `TestPgxNtfyNotifications`, 3 tests ; 4 tests existants de
`TestPgxTranscriptionLogPersistence` simplifiés — `notification_sent`
retiré des assertions, le champ reste dans le document Mongo mais son
calcul n'est plus lié à l'envoi d'une notif de fin de cycle qui n'existe
plus) — TDD strict respecté (RED confirmé avant implémentation).

## Schéma `pgx_transcription_logs` — un document par cycle complet

Nouvelle collection MongoDB, pattern calqué sur `rss_download_logs` (#295) :
`started_at`, `finished_at`, `trigger`, `status`
(`success`|`partial_error`|`error`|`pgx_unreachable_abandoned` — ce dernier
sans équivalent RSS), `episode_ids` (snapshot complet de la file, utile car
`episodes` est vide sur abandon), `episodes` (sous-ensemble réellement
tenté), `retry_attempts` (nested, pas un document par tentative — décision
explicite de l'issue), `notification_sent`, `error_message`.

Persisté dans `_finalize_cycle()`, appelé dans le `finally` de `_run()`
uniquement si `self.start_time is not None` (jamais sur `nothing_to_do`,
qui ne passe pas par `_run()`). La persistance est elle-même protégée par
un `try/except` qui ne doit jamais casser le run (log seulement).

## Extraction ntfy en module partagé sans toucher au code RSS

Nouveau `src/back_office_lmelp/utils/ntfy.py` — fonction standalone
`send_ntfy_notification(server_url, topic, title, message, tags=None)`
extraite du pattern de `RssSyncService.send_ntfy_notification`. Décision
explicite de **ne pas toucher** `rss_sync_service.py` (trop risqué pour
cette issue) — le code RSS garde sa propre méthode d'instance inchangée,
duplication mineure acceptée en échange de zéro risque de régression RSS.

## Piège FastAPI — body Pydantic optionnel vs body totalement absent

`POST /api/pgx/transcription/start` devait rester appelable **sans corps
du tout** (l'appel UI actuel, `axios.post(url)` sans second argument), tout
en acceptant `{"trigger": "api"}`. Un paramètre `request:
TriggerPgxTranscriptionRequest` sans défaut sur le paramètre lui-même
renvoie 422 sur un body absent, **même si tous les champs du modèle ont un
défaut** — piège FastAPI documenté dans l'issue avant implémentation. Fix :
`request: TriggerPgxTranscriptionRequest = <instance par défaut>`. Ruff
(`B008`) refuse ensuite l'appel de fonction dans les arguments par défaut
(`TriggerPgxTranscriptionRequest()` inline) — résolu en créant une instance
singleton module-level `_default_trigger_pgx_transcription_request` juste
après la déclaration de la classe, dans `src/back_office_lmelp/app.py`.
Test dédié qui aurait détecté une régression :
`tests/test_pgx_endpoints.py::TestStartPgxTranscriptionTrigger::test_should_accept_missing_body_and_default_to_manual`
(POST sans `json=` kwarg du tout, assert 200 pas 422).

## Fichiers modifiés/créés (backend)

- `src/back_office_lmelp/utils/pgx_transcription_runner.py` — cœur du
  changement : `trigger` param, `_wait_for_reachable_with_retry()`,
  `_build_log_document()`, `_finalize_cycle()`, `_send_notification()`,
  `get_status()` étendu avec `retry_pending`/`next_attempt_at`.
- `src/back_office_lmelp/settings.py` — `pgx_transcription_retry_interval_hours`
  (`PGX_TRANSCRIPTION_RETRY_INTERVAL_HOURS`, défaut `1`),
  `pgx_transcription_retry_max_hours` (`PGX_TRANSCRIPTION_RETRY_MAX_HOURS`,
  défaut `24`).
- `src/back_office_lmelp/utils/ntfy.py` (nouveau).
- `src/back_office_lmelp/services/mongodb_service.py` — trio
  `insert_pgx_transcription_log`/`get_pgx_transcription_logs`/
  `get_pgx_transcription_log_by_id`, collection `pgx_transcription_logs_collection`.
- `src/back_office_lmelp/app.py` — `TriggerPgxTranscriptionRequest`,
  route `start` étendue, nouvelles routes `GET /api/pgx/logs` et
  `GET /api/pgx/logs/{log_id}` (convention `JSONResponse`+try/except du
  fichier PGX, pas `HTTPException` comme RSS — cohérence avec les 5 routes
  PGX existantes).

## Fichiers modifiés/créés (tests backend)

- `tests/test_settings.py` — 4 nouveaux tests dans `TestPgxSettings`.
- `tests/test_ntfy.py` (nouveau) — 5 tests, repris de
  `TestSendNtfyNotification` (`tests/test_rss_sync_service.py`).
- `tests/test_mongodb_service_pgx.py` (nouveau, cohérent avec la
  convention par domaine `_rss_sync`/`_avis`/`_emissions` du projet —
  `test_mongodb_service.py` est `.disabled`) — 4 tests CRUD.
- `tests/test_pgx_transcription_runner.py` — classes ajoutées :
  `TestTriggerParameter`, `TestApiRetryScheduling`,
  `TestConcurrentStartDuringRetry`, `TestPgxTranscriptionLogPersistence` ;
  `TestGetStatus` mis à jour (nouvelles clés).
- `tests/test_pgx_endpoints.py` — classes ajoutées :
  `TestStartPgxTranscriptionTrigger`, `TestGetPgxLogs`, `TestGetPgxLogById`.

## Frontend

- `frontend/src/views/PgxTranscription.vue` — extension en place (pas de
  sous-composant, cohérent avec `RssMonitoring.vue`) : nouvelle section
  "📋 Historique des transcriptions" (table + détail expansible au clic,
  badges par statut), bandeau `pgx-retry-banner` si `retry_pending` dans
  le panneau de progression existant.
- `frontend/src/views/__tests__/PgxTranscription.spec.js` — `mockApi()`
  étendu pour `/api/pgx/logs` et `/api/pgx/logs/{id}`, nouveau bloc
  `describe('Historique (Issue #309)')` avec 6 tests.

## Vérifications effectuées

- Backend : 1695 tests passent (suite complète), 24 skipped, aucune
  régression.
- Frontend : 753 tests passent (suite complète), 14 skipped, aucune
  régression.
- `pre-commit run --files <tous les fichiers modifiés>` : ruff lint (après
  fix B008), ruff format, mypy, detect-secrets — tous verts.
- Vérification visuelle Playwright MCP sur `/transcription-pgx` : nouvelle
  section historique bien rendue, état vide correct (`Aucune transcription
  enregistrée`) — capture supprimée après vérification.
- Test manuel via curl : `POST /api/pgx/transcription/start` sans body ET
  avec `{"trigger":"api"}` répondent tous deux `200` (pas de régression du
  piège FastAPI en conditions réelles, pas seulement en test).

## Documentation produite (hors repo, à copier manuellement)

`docs/dev/automatisch-pgx-transcription.md` — rédigé sur le modèle exact
de la section "Étape 10 : Automatiser la synchronisation RSS via
Automatisch" du guide `docker-lmelp` (repo externe, non accessible depuis
cette session). Contenu à copier manuellement par l'utilisateur dans
`migration-nas.md` de `docker-lmelp`. Adaptations propres à PGX : caractère
asynchrone (fire-and-forget, contrairement à `/api/rss/sync` synchrone),
mécanisme de retry horaire/24h, statut `pgx_unreachable_abandoned`, deux
moments de notification ntfy.

## Reste à faire (au moment de cette mémoire)

- Mise à jour de `docs/dev/pgx-transcription.md`,
  `docs/user/transcription-pgx.md`, `docs/dev/environment-variables.md`
  (section principale de doc dev/utilisateur de CE repo, distincte du
  fichier Automatisch ci-dessus).
- Commit atomique + push.
- `mkdocs build --strict`.
- Vérification CI/CD.
- Préparation et validation de la PR.
