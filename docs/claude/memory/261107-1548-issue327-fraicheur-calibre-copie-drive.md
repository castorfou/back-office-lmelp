# Issue #327 — Fraîcheur Calibre et lecture de la copie Drive

Issue : [#327](https://github.com/castorfou/back-office-lmelp/issues/327) — liée à
[docker-lmelp#79](https://github.com/castorfou/docker-lmelp/issues/79) (changement de montage)
et [#328](https://github.com/castorfou/back-office-lmelp/issues/328) (502 au-delà de ~50 livres,
découvert en route, non traité).

## Problème et diagnostic

« Les modifs Calibre ne sont pas immédiates dans lmelp ». Mesure faite en comparant livre par
livre la bibliothèque source (montée en lecture seule dans le devcontainer sur `/calibre`) et
la prod (`/api/calibre/books`, paginé par 50) : prod figée sur l'état de la veille, 10 livres en
retard. Le backend relit pourtant SQLite à chaque requête : le retard est en amont.

Chaîne réelle (documentée dans `docker-lmelp/docs/user/calibre-vers-app-mobile.md`) :

```
Calibre (laptop) ─Synology Drive, ~secondes─▶ copie Drive (/volume1/homes/…/Backup/…/Calibre Library)
  ─nightly-sync.sh 00:05 (stop CWA → rsync → start)─▶ bibliothèque CWA (/volume1/docker/calibre-web-automated/books)
  ─CALIBRE_HOST_PATH :ro─▶ back-office ET lmelp-export (app mobile)
```

Décision (ADR `docs/adr/0001-lmelp-lit-la-copie-drive.md`) : lmelp lit la **copie Drive**.
Changement de montage dans docker-lmelp#79 ; CWA garde sa synchro nocturne.

## Démarche de conception (skills mattpocock)

- `/mattpocock-skills:ask-matt` est `disable-model-invocation: true` : invocable seulement par
  l'utilisateur, et une slash command doit être **en tête** de message (placée en fin de
  message, elle n'est pas reconnue).
- Routage : d'abord `/diagnosing-bugs` (abandonné : ce n'était pas un bug mais une évolution),
  puis `/grill-with-docs` (grilling + domain-modeling) → `/to-spec` (issue + label
  `ready-for-agent`, créé pour l'occasion dans le repo).
- Glossaire créé dans `CONTEXT.md` (convention du repo `docs/agents/domain.md`, pas
  `GLOSSARY.md`) : bibliothèque source, copie Drive, bibliothèque CWA, copie servie,
  synchronisation Drive, synchronisation nocturne, fraîcheur Calibre, délai de mise à disposition.
- Fausse piste éliminée par l'utilisateur : « Drive ne synchronise qu'à la fermeture de Calibre ».
  Le fait décisif (le script nocturne) n'était pas dans ce repo : chercher aussi dans
  `castorfou/docker-lmelp` et `castorfou/dockers` (via `gh api repos/…/contents/…`).

## Implémentation

- `src/back_office_lmelp/services/calibre_service.py`
  - `_open_connection()` : 3 essais (`OPEN_ATTEMPTS`, `OPEN_RETRY_DELAY_SECONDS = 0.2`) de
    « connect ro + `SELECT 1 FROM books LIMIT 1` » sur `sqlite3.DatabaseError`. En lecture
    seule SQLite n'échoue qu'à la **première requête**, pas au `connect` : une relance autour du
    seul `connect` ne sert à rien. Utilisé par `_get_connection()` **et** `_check_availability()`
    (sinon un démarrage pendant un remplacement Drive désactive Calibre jusqu'au redémarrage).
  - `get_metadata_mtime()` (stat de `metadata.db`) et `_get_latest_book_change()`
    (`max(last_modified)`, filtre de bibliothèque virtuelle) ; `get_status()` remplit
    `metadata_updated_at` (UTC) et `latest_book_change`. Construction du modèle **dans** le
    `try` : une ligne inattendue donne `None` au lieu de casser tout le statut (révélé par un
    test existant mocké).
- `src/back_office_lmelp/models/calibre_models.py` : `CalibreLatestChange`, champs ajoutés à
  `CalibreStatus`.
- `src/back_office_lmelp/services/calibre_matching_service.py` `_get_data()` : cache rechargé si
  le mtime de `metadata.db` change **ou** après le TTL de 5 min, conservé comme filet pour le
  côté MongoDB (écart assumé vs la spec, qui le supprimait).
- `frontend/src/views/AboutPage.vue` : section « Calibre » (`loadCalibreStatus()` dans le
  `Promise.all`), âge relatif (`relativeAge`, arrondi à l'inférieur), date exacte en `title`,
  classe `stale` orange au-delà de `CALIBRE_STALE_SECONDS = 3600`, « Calibre indisponible ».
  `.version-label` passé de 120 à 135 px (« Environnement : » débordait déjà).

## Tests

- `tests/fixtures/calibre_library.py` : **vraie bibliothèque Calibre sur disque** (DDL des tables
  lues par `CalibreService`, copié du schéma réel sans triggers ni données ; colonne perso
  `read`). Helpers `add_book`, `rename_book`, `set_mtime` (`os.utime`). À réutiliser pour tout
  test Calibre où le fichier compte (les anciens tests mockent `sqlite3.connect`).
- `tests/test_calibre_freshness.py` (seam HTTP, `TestClient`) : fraîcheur + tag virtuel,
  indisponible → `null`, cache qui suit le mtime et reste actif sinon, relance (1er `connect`
  dirigé vers un vrai fichier d'octets aléatoires → `DatabaseError` réelle à la 1re requête),
  démarrage pendant remplacement, échec persistant.
  - Piège : écrire dans la base change son mtime ; pour simuler « rien n'est arrivé », remettre
    le mtime avec `set_mtime`.
  - Piège : un titre initial contenu dans le titre attendu (« La Serp » / « La Serpe ») matche
    par containment ; prendre un titre sans rapport.
  - Mocks Mongo : `get_all_books`/`get_all_authors` renvoient des `_id`/`auteur_id` **str**
    (conversion faite par `MongoDBService`), pas des `ObjectId`.
- `frontend/src/views/__tests__/AboutPage.spec.js` : `vi.useFakeTimers({ toFake: ['Date'] })` +
  `setSystemTime` (ne fausser que `Date` pour garder les promesses), mock calqué sur la vraie
  réponse de `/api/calibre/status`.

## Vérification

Dev local : modification d'un tag dans Calibre par l'utilisateur → `/api/calibre/status` à jour
~20 s plus tard (« Le Voyant d'Étampes »). Playwright : section visible, valeurs alignées
(mesure DOM `getBoundingClientRect`).
