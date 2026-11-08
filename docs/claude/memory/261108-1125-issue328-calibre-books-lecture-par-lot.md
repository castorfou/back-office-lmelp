# Issue #328 — GET /api/calibre/books : 502 en prod, diagnostic + lecture par lot

## Constat initial
Le 7/11 vers 15:15, `GET /api/calibre/books?limit=1000|200` → 502 (page HTML du reverse
proxy Synology), `limit=50` → 200.

## Diagnostic (8/11)
- **Non reproductible** en prod : `limit` de 50 à 10000 → toujours 200. Bibliothèque
  `guillaume` : 572 livres, ≈ 977 Ko de JSON, 0,2–0,6 s. Un seul appel à 5,2 s, au
  rechargement du cache de matching (TTL 5 min, `CalibreMatchingService._get_data()`).
- Un 502 du proxy Synology veut dire « amont injoignable », indépendant de `limit`.
  15:15 tombe juste après le merge de #326 (15:04), donc publication de l'image puis
  redéploiement Watchtower. Cause la plus probable : le redéploiement.
- Un appelant demande bien toute la bibliothèque : `frontend/src/views/CalibreLibrary.vue:312`
  (`limit: 10000`). Laissé tel quel (1 Mo passe bien).
- Méthode : sonder la prod avec `curl -w "%{http_code} %{size_download} %{time_total}"`
  sur une série de `limit`. Endpoint public en lecture seule.

## Défauts réels corrigés (choix utilisateur : « diagnostic + durcissement »)
1. **N+1 SQLite** : `_build_book_from_row()` faisait ≈ 16 requêtes par livre (902 requêtes
   pour 60 livres). Remplacé par `CalibreService._build_books_from_rows(rows, conn)` dans
   `src/back_office_lmelp/services/calibre_service.py` :
   - une requête par relation `WHERE book IN ({ids})`, regroupée par livre ;
   - paquets de `BATCH_SIZE = 500` ids (limite de 999 variables des vieux SQLite) ;
   - helpers internes `values_by_book`, `first_by_book`, `custom_column` ;
   - `get_books()` et `get_book()` passent par cette méthode (`get_book` = lot d'un livre).

   Résultat : `get_books(1000)` passe de 0,139 s à 0,025 s en local.
2. **Boucle asyncio bloquée** : `get_calibre_books` dans `src/back_office_lmelp/app.py`,
   `async def` → `def`. FastAPI l'exécute en threadpool : la lecture SQLite et le matching
   Mongo synchrones ne gèlent plus les autres requêtes. Ne marche que parce que le corps
   ne contient aucun `await`.

## Sémantique préservée (vérifiée par diff JSON avant/après sur `/calibre`, 1000 livres)
- auteurs triés par `bal.id`, tags par `t.name` ;
- éditeur, série, note, ISBN, commentaire, colonnes simples : 1ʳᵉ valeur (`ORDER BY` id) ;
- `read`/`paper` → `bool`/`None` ;
- `ko_status` lu via `books_custom_column_N_link`.

**Seule différence** : l'ordre des langues pour 2 livres. L'ancienne requête n'avait pas
d'`ORDER BY`, donc un ordre arbitraire. Il est maintenant `ORDER BY bll.item_order, bll.id`,
l'ordre Calibre.

## Tests
- Nouveau `tests/test_calibre_books_batch.py`, sur une vraie bibliothèque :
  - nombre de requêtes borné, compté avec `conn.set_trace_callback` en enveloppant
    `service._open_connection` ;
  - valeurs complètes via `get_books` et `get_book` (paramétré) ;
  - pas de mélange entre livres ;
  - découpage en paquets (`patch BATCH_SIZE=7`) ;
  - pagination ;
  - endpoint non-coroutine (`inspect.iscoroutinefunction`).
- `tests/fixtures/calibre_library.py` :
  - colonnes personnalisées ajoutées au schéma, DDL copié du vrai `metadata.db` : paper(2),
    text(3), ko_progfloat(4), ko_status(5, énumérée + table de lien), ko_start(7),
    ko_finish(8) ;
  - helper `add_details()` : co-auteurs, éditeur, série, note, ISBN, commentaire, langues
    avec `item_order`, colonnes perso.
- 3 tests retirés de `tests/test_calibre_service.py` (`test_get_book_returns_book_when_found`,
  `test_get_book_exposes_koreader_fields`, `test_get_book_works_without_isbn_column`).
  Leurs mocks `execute` par mot-clé supposaient une requête par relation et par livre.
  Leurs cas sont couverts sur le vrai fichier (la fixture n'a pas de colonne `books.isbn`,
  comme Calibre récent).

## Pièges rencontrés
- mypy : une variable de boucle (`value`) réutilisée dans deux `for` successifs garde le
  type inféré du premier → renommer (`col_value`).
- `start-dev.sh` lancé via `nohup` sans `source /tmp/venv/bin/activate` → backend en échec
  `ModuleNotFoundError: dotenv`, le frontend démarre quand même (proxy vers le port par
  défaut, 500 partout). Toujours activer le venv dans la même commande que le `nohup`.
