# Issue #304 — Pouvoir relancer le traitement Babelio en cas d'erreur 403

## Contexte et périmètre

Issue #304 demandait de pouvoir corriger le cookie Babelio et relancer le
traitement en cas de blocage 403, sans devoir tout recommencer depuis zéro.
Le travail a fini par couvrir deux périmètres bien distincts, découverts
progressivement via des tests utilisateur en conditions réelles (plusieurs
rounds de bugs successifs, chacun révélé par un nouveau symptôme rapporté
par l'utilisateur avec capture d'écran/logs à l'appui).

### Périmètre 1 — Page "Livres et Auteurs" (validation bibliographique)

- `frontend/src/services/BiblioValidationService.js` : `_arbitrateResults()`
  et `_tryPhase0DirectValidation()` court-circuitent désormais le statut
  `blocked_403` en tête de traitement, pour éviter qu'il soit absorbé en
  `not_found` (qui aurait marqué le livre comme définitivement absent de
  Babelio, alors qu'il s'agit d'un blocage transitoire).
- `frontend/src/components/BiblioValidationCell.vue` : nouvel état visuel
  `blocked_403` (icône 🚫ब + bouton retry réutilisant `startValidation`).
- `frontend/src/views/LivresAuteurs.vue` : persistance ciblée par livre
  (`persistSingleBookValidation`) quand un livre transite d'un état
  bloqué/erreur vers un état stable ; watcher qui auto-ouvre le panneau
  cookie si `babelioBlocked` devient vrai.
- `src/back_office_lmelp/app.py` (`set_validation_results`) : `blocked_403`
  traité comme `error` (pas persisté comme `not_found` définitif).

### Périmètre 2 — Page "Migration Babelio" (script batch)

C'est le vrai périmètre concerné par l'issue (l'utilisateur a explicitement
signalé que le blocage se produisait pendant le traitement automatique en
masse, pas sur la page Livres et Auteurs) :

- `scripts/migration_donnees/migrate_url_babelio.py` : le bloc `else` ne
  logge plus dans `babelio_problematic_cases` quand `status == "blocked_403"`
  (sinon le livre aurait été classé "à traiter manuellement" et jamais
  retenté après correction du cookie).
- `src/back_office_lmelp/services/babelio_migration_service.py` :
  `requeue_blocked_403_cases()` — supprime les entrées `blocked_403` de
  `babelio_problematic_cases` pour permettre un nouveau passage.
- `src/back_office_lmelp/app.py` : endpoint
  `POST /api/babelio-migration/requeue-blocked-403`.
- `frontend/src/views/BabelioMigration.vue` : bandeau + bouton "Relancer
  tous les 403" (visible si des cas `blocked_403` existent).

## Bugs découverts en cascade (rounds 3 à 7)

Chaque fix a révélé un nouveau symptôme au test utilisateur suivant — un
bon rappel que le premier fix qui "compile et passe les tests" n'est pas
forcément le dernier nécessaire sur un flux aussi long (scraping → cache →
circuit breaker → boucle de traitement batch).

1. **Boucle infinie sur le même livre** : après le premier fix (ne plus
   logger `blocked_403`), `MigrationRunner` (`src/back_office_lmelp/utils/migration_runner.py`)
   retrouvait le même livre à chaque itération sans jamais s'arrêter. Fix :
   `break` sur `status in ("blocked_403", "error")` — élargi à `error`
   après un second test utilisateur montrant qu'un timeout réseau
   provoquait la même boucle (décision explicite de l'utilisateur :
   "arrêter dès le 1er timeout, comme blocked_403").

2. **Instance `BabelioService` isolée dans `MigrationRunner`** :
   `_run_python_migration()` faisait `babelio_service = BabelioService()`
   (nouvelle instance à chaque migration), jamais synchronisée avec le
   singleton `babelio_service` utilisé par les endpoints `/api/babelio/status`
   et `/api/babelio/cookie`. Symptôme observé par l'utilisateur : capture
   d'écran montrant "Circuit breaker : Fermé" malgré des 403 en cours réels.
   Fix : importer le singleton (`from back_office_lmelp.services.babelio_service import babelio_service`),
   supprimer la création locale et l'appel `.close()` en fin de migration
   (qui aurait fermé la session partagée).

3. **`health_check()` bloqué sur "Inconnu"** : servait le cache disque de
   la page d'accueil Babelio (`cache_hit: true`), jamais compté comme
   "requête récente réelle" par `/api/babelio/status`. L'utilisateur a
   lui-même diagnostiqué la cause via une capture du cache montrant
   l'entrée `https://www.babelio.com`. Fix : `_fetch_page()` a gagné un
   paramètre `skip_cache: bool = False`, et `health_check()` l'appelle
   avec `skip_cache=True` pour forcer une vraie requête réseau.

4. **Le bug racine le plus profond — vérifications HTTP directes sans
   cookie ni bons headers** (voir section dédiée ci-dessous).

## Le bug racine (round 7) : appels HTTP bruts contournant le gateway `_fetch_page()`

### Symptôme

L'utilisateur avait un cookie Babelio valide, le circuit breaker fermé, et
Babelio accessible normalement au navigateur — pourtant la migration
continuait à recevoir des 403. Preuve dans les logs partagés : un appel
`fetch_author_url_from_page()` réussissait juste avant («URL auteur
trouvée»), suivi immédiatement d'un 403 sur une URL très proche
(`⚠️ URL livre invalide (HTTP 403)`) — la même session, quasiment la même
requête, un succès puis un échec.

### Cause

`scripts/migration_donnees/migrate_url_babelio.py` contenait 4 sites qui
faisaient des appels HTTP **bruts** via
`session = await babelio_service._get_session(); session.get(url)`, au
lieu de passer par le gateway centralisé `babelio_service._fetch_page(url)`.

`_get_session()` crée une session avec `_get_default_headers()` — un
profil de headers d'**API AJAX** (`Content-Type: application/json`,
`X-Requested-With: XMLHttpRequest`, `Referer: recherche.php`) et **sans**
le cookie `jstsToken` stocké côté serveur (seuls des cookies statiques
`p`/`disclaimer`/`g_state`/`bbacml` sont posés une fois à la création de
session). `_fetch_page()`, à l'inverse, utilise `_get_page_headers()` —
des headers de navigation HTML appropriés, ET injecte le cookie stocké.
Babelio détecte et bloque ce profil de requête "API sans cookie" en 403,
même quand tout le reste (cookie stocké, circuit breaker, accessibilité
générale du site) est parfaitement sain.

### Fix

Remplacement des 4 sites par des appels à `babelio_service._fetch_page(url)` :

1. `migrate_one_book_and_author` — vérification URL livre (ÉTAPE 1).
2. `scrape_title_from_page(babelio_service, url)` — a gagné le paramètre
   `babelio_service` (n'existait pas avant).
3. `migrate_one_book_and_author` — vérification URL auteur.
4. `scrape_author_url_from_book_page(babelio_service, book_url)` — avait
   EN PLUS le bug d'instance isolée (`babelio_service = BabelioService()`
   créée localement) plutôt que de recevoir le singleton en paramètre,
   comme dans le bug n°2 ci-dessus. Propagé via `process_one_author()`
   (nouveau paramètre optionnel `babelio_service: BabelioService | None = None`)
   jusqu'à l'appel dans `migration_runner.py` (`Phase 2`), qui passe
   désormais le singleton partagé.

`process_one_book_author()` et `complete_missing_authors()` avaient le même
bug de session brute mais ne sont PAS appelées par le flux de production
réel (`migration_runner.py` n'appelle que `migrate_one_book_and_author` et
`process_one_author`) — laissées telles quelles pour ne pas modifier du
code mort et casser leurs tests dédiés sans bénéfice réel.

`_fetch_page()` lève `BabelioBlockedError` sur 403 (et ouvre lui-même le
circuit breaker en interne) au lieu de renvoyer un objet réponse avec
`.status` — chaque site corrigé attrape cette exception spécifiquement
pour retourner `status: "blocked_403"` sans logger dans
`babelio_problematic_cases` (un 403 est transitoire, pas un problème de
données).

## Piège découvert en testant le fix : duplication de module `src.` vs sans-préfixe

En ajoutant `except BabelioBlockedError:` dans le code corrigé, la suite
complète de tests (1600 tests) a révélé un échec **non-déterministe par
combinaison de fichiers** (passait en isolation, échouait selon quels
autres fichiers de test tournaient avant). Root cause : certains fichiers
de test (`tests/test_api_refactoring.py` et probablement
`test_mongodb_service_refactoring.py`/`test_episode_refactoring.py`)
importent l'application via `from src.back_office_lmelp.app import app`
(avec le préfixe `src.`), alors que le reste de la suite utilise
`from back_office_lmelp.app import app` (sans préfixe). Python charge ces
deux imports comme **deux modules complètement distincts** dans
`sys.modules`, chacun avec sa propre classe `BabelioBlockedError` —
mêmes nom qualifié, mais `is` renvoie `False` entre les deux. Comme
`migration_runner.py` fait un `sys.path.insert()` dynamique pour importer
`migrate_url_babelio` (module top-level, sans préfixe `scripts.`), la
classe `BabelioBlockedError` réellement levée dépend de quel import a été
exécuté en premier dans la session pytest.

**Fix pragmatique** (pas de refactoring des imports `src.` existants, trop
risqué à ce stade) : comparer `type(e).__name__ == "BabelioBlockedError"`
plutôt que `except BabelioBlockedError:` (isinstance), dans les deux sites
concernés de `migrate_url_babelio.py`. Ce problème de duplication de module
n'existe qu'en environnement de test (une seule copie du code tourne en
production) — documenté ici pour éviter de re-déboguer ce même symptôme
non-déterministe dans une future session si un nouveau `except <ClasseBabelio>`
est ajouté ailleurs dans ce fichier.

**Diagnostic utile pour la prochaine fois** : un test qui passe seul mais
échoue selon la combinaison d'autres fichiers exécutés, avec un message
d'erreur qui ne "colle" pas au code lu (ex: une exception censée être
catchée qui ne l'est pas) est un signal fort de désynchronisation entre
deux copies du même module en mémoire — comparer `id(ClasseA) == id(ClasseB)`
plutôt que de re-vérifier la logique du code, qui est probablement correcte.

## Autres apprentissages de la session

- **Workflow de contournement du ban IP Babelio** documenté dans
  `docs/dev/blocage_ip.md` : dump/restore MongoDB (`mongodump`/`mongorestore`
  avec `--uri` direct, pas de tunnel SSH) entre le NAS (`nas923:27018`,
  prod) et un Mongo Docker local sur le laptop (`localhost:27018`,
  conteneur `lmelp-mongo` déjà existant) — pour travailler complètement
  déconnecté du réseau domestique (hotspot mobile) le temps de contourner
  un ban IP, puis rapatrier les modifications au retour. `mongosync` jugé
  trop lourd à opérer manuellement pour ce besoin ponctuel (voir
  [[reference-mongo-dual-database-setup]] si cette mémoire existe, sinon
  se référer directement au fichier doc).
- `scripts/start-dev.sh --restart` : nouveau flag qui tue les process
  précédents (via `.dev-ports.json` + fallback `pgrep` pour les orphelins)
  avant de redémarrer.
- `.claude/get-services-info.sh` : affiche désormais l'URL MongoDB, lue
  via `python3 -c "from dotenv import load_dotenv; ..."` (même logique que
  le backend), jamais par parsing manuel du fichier `.env`.
- Navigation croisée ajoutée entre "Liaison Babelio des livres"
  (`BabelioMigration.vue`) et "Contrôle Babelio" (`BabelioControl.vue`,
  lien cliquable vers babelio.com, tooltip explicatif sur "Circuit
  breaker").
- Issue #306 créée pour clarifier la sémantique du statut du service
  Babelio (distinction demandée par l'utilisateur : timeout → suspicion de
  ban IP forte, 403 → cookie invalide/absent ou captcha, tout passe → vert).

## Fichiers clés

- `scripts/migration_donnees/migrate_url_babelio.py` — les 4 sites de
  vérification HTTP corrigés + gestion `BabelioBlockedError`.
- `src/back_office_lmelp/utils/migration_runner.py` — singleton partagé,
  arrêt sur `blocked_403`/`error`, `babelio_service=babelio_service` passé
  à `process_one_author`.
- `src/back_office_lmelp/services/babelio_service.py` — `_fetch_page(skip_cache=...)`.
- `tests/test_migrate_url_babelio_fetch_page_gateway.py`,
  `tests/test_scrape_author_url_shared_service.py`,
  `tests/test_migration_runner_blocked_403.py` — nouveaux tests TDD de ce
  round.
- `docs/dev/blocage_ip.md` — workflow de contournement du ban IP.
