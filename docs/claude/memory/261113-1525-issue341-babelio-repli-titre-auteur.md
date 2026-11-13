# Issue #341 — Un livre au titre courant n'est pas trouvé sur Babelio

Issue : https://github.com/castorfou/back-office-lmelp/issues/341 (suite de #339)

## Problème

« L'héritage » de Jonathan Littell existe sur Babelio (https://www.babelio.com/livres/Littell-LHeritage/2069632), mais la validation biblio et la Liaison Babelio ne le trouvaient pas.

- `BabelioService.verify_book()` (`src/back_office_lmelp/services/babelio_service.py`) cherche le **titre seul**, choix fait pour #124 (Terminus Malaussène).
- `_find_best_book_match()` filtre ensuite les résultats sur l'auteur (similarité > 0.7).
- Pour un titre courant, Babelio ne renvoie que les homonymes populaires : Paolini, Berry, Grisham, Ragde. Le livre de Littell n'en fait pas partie, d'où `not_found`.
- Le repli existant ne se déclenchait que si `len(results) == 0`.

## Solution

### Backend — repli « titre + auteur » dans `verify_book()`

Si aucun livre de l'auteur n'est trouvé et qu'un auteur est fourni, une **seule** recherche de repli `f"{title} {author}"` est lancée, avec l'apostrophe typographique remplacée par l'apostrophe droite.

- Le livre en base s'écrit `L’Héritage`, alors que Babelio écrit `L'Héritage`.
- Le reste du flux est inchangé : score, éditeur, URL auteur et `BabelioBlockedError` → `blocked_403`.
- `verify_book` est commun à `/api/verify-babelio` (validation frontend), à l'enrichissement à l'extraction (`books_extraction_service.py`) et à la Liaison Babelio (`babelio_migration_service.py`). La correction couvre donc les trois.

Coût : une requête Babelio de plus par livre sans correspondance d'auteur, uniquement la première fois, puisque `search()` utilise un cache disque de 24 h dont la clé est le terme en minuscules. Cas observés sur l'épisode du 01/11/2026 :
- co-auteurs (« Cyril Pedrosa & Taiyo Matsumoto ») ;
- orthographe d'auteur différente (« Madeline Cash ») ;
- livre absent de Babelio (« Le génie », Martine Ravache).

### Frontend — `frontend/src/services/BiblioValidationService.js`

- Les branches `verified` portent maintenant `data.babelio_url` : phase 0, confirmée, correction d'auteur, et validation directe (Cas 3).
- La branche `ground_truth` seule (0.75) ne garde l'URL que si le titre trouvé par Babelio correspond à la suggestion du résumé : nouveau helper `_babelioUrlIfSameTitle()`, qui compare via `removeAccents` + minuscules + apostrophe droite. Un homonyme n'est jamais lié.

### Compteur Liaison Babelio — `babelio_migration_service.py` (`get_migration_status`)

Bug découvert pendant les tests : « En attente de liaison » valait **−2**.

- Une liaison lancée avec l'ancien code avait classé L'Héritage, Je et Le génie en cas problématiques. La validation de l'épisode a ensuite lié L'Héritage et Je, sans retirer leurs cas problématiques.
- `pending = total − liés − absents − problématiques` les comptait donc deux fois.
- Correction : `problematic_count` retire les cas dont le livre a `url_babelio` ou `babelio_not_found`. Le calcul fait un `distinct("livre_id")` sur les cas, convertit ces String en ObjectId, puis un `find` sur `livres`.
- `get_problematic_cases()` faisait déjà cette exclusion : le compteur et la liste sont maintenant cohérents.
- La correction est côté lecture, donc valable pour tous les chemins d'écriture de `url_babelio`.

## Capture réelle (avant les tests)

Le cookie Babelio expirait et un 403 mène au ban IP. L'utilisateur a donc fourni un cookie frais, puis **une seule** requête est passée par le backend : `POST /api/verify-babelio {type:"author", name:"L'héritage Jonathan Littell"}`. `verify_author` ne fait qu'un `search()`, qui passe par le cache disque et le disjoncteur.

Les réponses sont figées dans `tests/fixtures/babelio_search_lheritage_littell.json` (clés : `L'héritage`, `L'héritage Jonathan Littell`). Le cache disque est dans `data/processed/babelio_cache`.

## Pièges

- **`importlib.reload` du module `babelio_service`** par d'autres tests (`test_babelio_stale_cookie.py`, `test_babelio_connection_timeout_circuit.py`). Une `BabelioBlockedError` importée en tête du fichier de test devient une autre classe que celle attrapée par `verify_book`. Le test passe seul et échoue dans la suite. Correction : lire `module.BabelioBlockedError` et `module.BabelioService` à l'exécution.
- **Faux `search()` des tests** : la clé doit être insensible à la casse, comme le vrai cache disque.
- **Tests existants du statut de migration** (`test_migration_status_stats.py`) : ils enchaînent des `count_documents` mockés dans un ordre précis (`side_effect` en liste). Le nouveau calcul n'ajoute donc aucun `count_documents` sur `livres`, seulement `distinct` et `find`.
- **`detect-secrets`** signale les ObjectId en clair dans les tests JS : ajouter `// pragma: allowlist secret`.
- **Bug préexistant hors périmètre** : la suite pytest complète supprime le vrai `.dev-ports.json` alors que les services tournent. Les scripts `.claude/get-*-info.sh` ne trouvent alors plus le backend.

## Tests

- `tests/test_babelio_verify_book_common_title.py` couvre :
  - le repli trouve Littell ;
  - le repli est une seule recherche « titre + auteur » ;
  - aucun repli si l'auteur est déjà trouvé (Grisham) ;
  - aucun repli sans auteur ;
  - un 403 pendant le repli donne `blocked_403` ;
  - le cas de l'apostrophe typographique.
- `tests/test_migration_status_resolved_problematic.py` : les 3 cas problématiques réels donnent `problematic_count == 1` et `pending_count == 0`.
- `frontend/tests/unit/BiblioValidationService.babelioUrl.test.js` couvre :
  - la phase 0 `verified` porte l'URL ;
  - `ground_truth` seul garde l'URL du même livre ;
  - `ground_truth` seul ne garde pas l'URL d'un homonyme.

## Résultat bout en bout (13/11/2026)

Après « 🔄 Relancer la validation Biblio » sur l'épisode du 01/11/2026 :
- les 9 livres sont en `mongo`, dont 8 avec URL Babelio ;
- `L'Héritage` en base a `url_babelio`, `url_cover` et l'URL Babelio de l'auteur ;
- seulement 4 recherches Babelio réelles ont été faites, toutes en 200.
