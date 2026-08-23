# Issue #267 — Améliorer les infos "Émissions avec Problème" + détection doublons casse-insensible

## Contexte métier

Sur l'écran Emissions, quand `livres_summary` (titres uniques extraits de l'avis critique) diffère de `livres_mongo` (livres MongoDB liés à l'épisode via `episodes[]`), un avertissement s'affichait avec deux compteurs opaques et une troisième notion ("Livres discutés", alimentée par le cache validé `livresauteurs_cache`), sans dire à l'utilisateur **quels** livres posent problème ni pourquoi les trois nombres diffèrent. Cas réel : émission du 24/04/2022, écart de 11 vs 13 livres.

## V1 — Lister explicitement les livres en écart

- Nouveau champ `matching_stats.livres_mongo_non_cites` retourné par `/api/avis/by-emission/{emission_id}` (`src/back_office_lmelp/app.py`) : liste des livres MongoDB liés à l'épisode (`episodes` contient `episode_id`) dont aucun `avis.livre_oid` ne pointe vers eux.
- Libellés clarifiés dans `frontend/src/views/Emissions.vue` : "Livres summary" → "Livres cités dans l'avis critique", "Livres Mongo" → "Livres liés à cet épisode en base".
- La liste `livres_mongo_non_cites` s'affiche sous l'avertissement avec liens vers chaque livre.

## V2 — Diagnostic du cas concret : doublons à casse différente

En testant la V1, l'utilisateur a identifié que les 2 livres "en écart" (`L'affaire Alaska Sanders`, `La promesse`) étaient en réalité des **doublons** des livres déjà cités, différant uniquement par la casse du titre et de l'URL Babelio (ex: `Dicker-Laffaire-Alaska-Sanders` vs `Dicker-LAffaire-Alaska-Sanders`).

**Cause racine** : `MongoDBService.create_book_if_not_exists()` (`src/back_office_lmelp/services/mongodb_service.py:1923`) dédupliquait par `find_one({"titre": ..., "auteur_id": ...})` avec égalité **stricte**. Lors d'une ré-extraction d'avis, un re-scraping Babelio a renvoyé un titre à la casse légèrement différente → non reconnu comme existant → nouveau livre créé, avec sa propre URL Babelio (elle-même en casse différente).

**Conséquence en cascade** : le service `DuplicateBooksService.find_duplicate_groups_by_url()` (page `/duplicate-books`) groupe par égalité stricte de `url_babelio` → ne détectait pas non plus ces doublons casse-différente (page affichait "0 groupe" alors que 2 doublons existaient réellement).

### Fix Boucle A — création de livres

`create_book_if_not_exists` (`mongodb_service.py:1923`) utilise maintenant `normalize_for_matching()` (déjà dans `text_utils.py`) pour comparer les titres après avoir récupéré tous les livres du même `auteur_id` via `find()` (plus `find_one()` avec égalité stricte). Empêche la création de futurs doublons casse-différente.

### Fix Boucle B — détection élargie côté service

Nouvelle méthode `DuplicateBooksService.find_duplicate_groups_by_url_case_insensitive()` (`src/back_office_lmelp/services/duplicate_books_service.py`) : pipeline MongoDB groupant par `{"$toLower": "$url_babelio"}` au lieu de l'URL brute. Retourne `url_babelio` = **une URL réelle du groupe** (`group["urls"][0]`, casse préservée) — jamais la version normalisée en minuscules, qui pourrait ne pas exister sur Babelio et casserait le re-scraping lors de la fusion. `get_duplicate_statistics()` mis à jour avec le même `$toLower` pour rester cohérent avec la liste de groupes.

### Fix Boucle C — UI Emissions

Dans l'endpoint `/api/avis/by-emission`, chaque entrée de `livres_mongo_non_cites` reçoit un champ `doublon_probable_de` (le `livre_oid` cité correspondant) quand son titre+auteur normalisés matchent un livre déjà cité, plus `url_babelio` pour permettre la fusion directe. Côté `Emissions.vue` : badge "Doublon probable" + bouton "🔗 Fusionner" qui appelle `avisService.mergeDuplicateBooks(urlBabelio, [livre_oid, doublon_probable_de])` (nouvelle méthode dans `frontend/src/services/api.js`, réutilisant l'endpoint existant `/api/books/duplicates/merge`). Après fusion réussie, les avis de l'émission sont rechargés automatiquement.

### Fix Boucle D — page /duplicate-books

L'endpoint `/api/books/duplicates/groups` (`app.py:2883`) pointe maintenant vers `find_duplicate_groups_by_url_case_insensitive()` au lieu de `find_duplicate_groups_by_url()` — cette méthode est une sur-ensemble légitime (une casse identique est un cas particulier d'insensible à la casse), donc source unique de vérité pour cette page.

## Points TDD notables

- Le passage de `find_one()` à `find()` dans `create_book_if_not_exists` a cassé plusieurs tests existants qui mockaient `find_one.return_value` (`tests/test_livre_episodes_array_bug.py`, `tests/test_editeur_management.py`, `tests/test_auto_process_verified_with_babelio_enrichment.py`) — corrigés en `find.return_value = [doc]`. Prévoir cette check à chaque changement de `find_one`→`find` sur `livres_collection`.
- Le service de fusion `merge_duplicate_group` (existant depuis Issue #178) n'a nécessité **aucune modification** : il est déjà robuste (fusionne `episodes`/`avis_critiques`, met à jour `auteurs.livres`, met à jour le cache `livresauteurs_cache.book_id`). Seule la **détection** des groupes de doublons manquait la casse-insensible.

## Fichiers modifiés

- `src/back_office_lmelp/app.py` : endpoint `/api/avis/by-emission` (champs `livres_mongo_non_cites`, `doublon_probable_de`, `url_babelio`), endpoint `/api/books/duplicates/groups` (bascule vers détection casse-insensible), import `normalize_for_matching`.
- `src/back_office_lmelp/services/mongodb_service.py:1923` : `create_book_if_not_exists` avec comparaison normalisée.
- `src/back_office_lmelp/services/duplicate_books_service.py` : nouvelle méthode `find_duplicate_groups_by_url_case_insensitive`, `get_duplicate_statistics` mis à jour.
- `frontend/src/views/Emissions.vue` : libellés clarifiés, liste des livres en écart, badge doublon, bouton fusion, CSS associé.
- `frontend/src/services/api.js` : `avisService.mergeDuplicateBooks()`.
- Tests : `tests/test_create_book_case_insensitive_dedup.py` (nouveau), `tests/test_api_avis_endpoints.py`, `tests/test_duplicate_books_service.py`, `frontend/tests/unit/Emissions.matchingStats.test.js`, plus corrections de mocks dans 3 fichiers de tests existants.

## Résultat validé par l'utilisateur

Testé en conditions réelles sur l'émission du 24/04/2022 : les 2 doublons (Dicker, Galgut) détectés avec badge + bouton fonctionnel sur l'écran Emissions, page `/duplicate-books` passée de "0 groupe" à "2 groupes / 2 livres en doublon", fusion réussie via le bouton — doublons nettoyés en base. Suite complète backend : 1460 passed, 24 skipped. Suite frontend : 661 passed, 14 skipped. Pre-commit vert.
