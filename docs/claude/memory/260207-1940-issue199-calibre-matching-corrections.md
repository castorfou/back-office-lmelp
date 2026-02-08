# Issue #199 - Liaison MongoDB-Calibre : Matching et Page de Corrections

**Branche** : `199-liaison-mongodb-calibre-matching-des-livres-et-page-de-corrections`
**Commit** : `14a3e3a` — 21 fichiers, 3632 insertions, 132 suppressions

## Contexte

Le matching existant entre MongoDB (1605 livres) et Calibre (~537 livres filtrés par tag `guillaume`) utilisait une simple normalisation NFKD dans `app.py` (`_normalize_title`) produisant ~137 matchs exacts. L'issue demandait un matching amélioré, une page de corrections, et plusieurs bugfixes découverts en cours de route.

## Nouveau service : CalibreMatchingService

Fichier : `src/back_office_lmelp/services/calibre_matching_service.py` (417 lignes)

### Algorithme de matching à 3 niveaux

1. **Exact** : titre normalisé identique (via `normalize_for_matching()`)
2. **Containment** : un titre contient l'autre (min 4 chars) + validation auteur
3. **Author-validated** : candidats multiples par containment, départagés par auteur

### Normalisation auteur (`_normalize_author_parts`)

Gère les formats :
- Naturel MongoDB : `"Mohamed Mbougar Sarr"`
- Calibre pipe : `"Appanah| Nathacha"`
- Calibre virgule : `"Sarr, Mohamed Mbougar"`
- Ligatures, tirets composés

Le matching auteur compare les ensembles de tokens normalisés (intersection non-vide = match).

### Détection des corrections (`get_corrections`)

Retourne 3 catégories :
- **author_corrections** : noms d'auteurs qui diffèrent entre MongoDB et Calibre
- **title_corrections** : titres qui diffèrent (après match)
- **missing_lmelp_tags** : livres Calibre avec tags `lmelp_` manquants, incluant `all_tags_to_copy` prêt pour copier-coller

### Tags à copier (`all_tags_to_copy`)

Ordre : `[virtual_library_tag]` + `[notable_tags: babelio, lu, onkindle]` + `[lmelp_*]`

Les tags notables ne sont inclus que s'ils sont déjà présents dans Calibre. Constante `NOTABLE_TAGS = ("babelio", "lu", "onkindle")`.

### Enrichissement palmarès (`enrich_palmares_item`)

Remplace les anciennes fonctions `_normalize_title()`, `_build_calibre_index()`, `_enrich_with_calibre()` supprimées de `app.py`.

### Cache interne

TTL de 5 minutes (`_cache_ttl = 300`). Endpoint `POST /api/calibre/cache/invalidate` pour forcer le rechargement après correction.

## Fonction normalize_for_matching

Ajoutée dans `src/back_office_lmelp/utils/text_utils.py:117-160`.

Pipeline : ligatures (oe/ae) -> NFD + retrait accents -> tirets/apostrophes typographiques -> lowercase + strip + collapse whitespace.

Différence avec `create_accent_insensitive_regex()` : produit une chaîne plain text (pas un regex), utilisée pour les comparaisons d'égalité et containment.

## CalibreService : get_all_books_with_tags

Ajoutée dans `src/back_office_lmelp/services/calibre_service.py:514-600`.

Étend `get_all_books_summary()` avec les tags. Requêtes SQLite séquentielles par livre : authors, tags, rating, read status. Applique le filtre virtual library si configuré.

## MongoDBService : changements critiques

### critique_oid -> nom officiel du critique

`mongodb_service.py:1114-1138` : Résolution de `critique_oid` (String) vers `critiques._id` (ObjectId) pour obtenir le nom officiel au lieu de `critique_nom_extrait` (nom LLM parfois erroné).

Conversion obligatoire : `BsonObjectId(str_id)` car `critique_oid` est String mais `critiques._id` est ObjectId.

### Normalisation des accents dans les tags critiques

`_build_calibre_tags` utilise maintenant `normalize_for_matching()` pour les noms de critiques :
- Avant : `"lmelp_nelly_kapriélian"` (avec accent)
- Après : `"lmelp_nelly_kaprielian"` (ASCII-safe pour Calibre)

### get_expected_calibre_tags (bulk)

`mongodb_service.py` : Nouvelle méthode pour calculer les tags `lmelp_` attendus en bulk pour une liste de `livre_ids`. Utilisée par `CalibreMatchingService.get_corrections()`.

## Endpoints API (app.py)

- `GET /api/calibre/matching` : résultats du matching + statistiques
- `GET /api/calibre/corrections` : corrections par catégorie
- `POST /api/calibre/cache/invalidate` : invalidation cache

Routes placées AVANT `/api/calibre/books/{book_id}` (route order matters en FastAPI).

## Frontend : CalibreCorrections.vue

`frontend/src/views/CalibreCorrections.vue` (693 lignes)

Pattern 3 états (loading/error/content). 4 sections repliables :
1. Auteurs (noms différents MongoDB vs Calibre)
2. Titres (différences de titres)
3. Tags manquants (avec bouton Copier → `all_tags_to_copy` formaté en comma-separated)
4. Statistiques globales

Liens vers la page livre detail pour chaque correction. Invalidation du cache après copie d'un tag.

Route : `/calibre-corrections` dans `frontend/src/router/index.js`.
Carte dans `frontend/src/views/Dashboard.vue`.

## Bugfix : Anna's Archive URL morte

Le domaine par défaut `https://fr.annas-archive.org` était mort (connection refused). Changé en `https://fr.annas-archive.li` dans 4 fichiers :
- `frontend/src/views/Palmares.vue:214`
- `frontend/src/views/LivreDetail.vue:248`
- `src/back_office_lmelp/services/annas_archive_url_service.py:47`
- `src/back_office_lmelp/app.py:2612` (endpoint fallback)

## Bugfix : Tag guillaume (virtual library)

Le tag `guillaume` n'était ajouté que si le livre existait dans la bibliothèque Calibre. Erreur fonctionnelle : le tag doit toujours être ajouté quand `calibre_tags` est non-vide, pour permettre le copier-coller dans Calibre.

Avant (`app.py:2213-2222`) :
```python
if calibre_service._available and settings.calibre_virtual_library_tag and "calibre_tags" in livre_data:
    calibre_index = _build_calibre_index()
    norm_title = _normalize_title(livre_data.get("titre", ""))
    if norm_title in calibre_index:
        livre_data["calibre_tags"].insert(0, settings.calibre_virtual_library_tag)
```

Après :
```python
if settings.calibre_virtual_library_tag and livre_data.get("calibre_tags"):
    livre_data["calibre_tags"].insert(0, settings.calibre_virtual_library_tag)
```

## Tests

### Backend (1152 tests total)
- `tests/test_calibre_matching_service.py` : 37 tests (matching, corrections, tags, notables)
- `tests/test_api_calibre_matching.py` : tests endpoints API
- `tests/test_livre_detail_tags.py` : 17 tests (virtual library tag, critique names, accents)
- `tests/test_calibre_service.py` : `get_all_books_with_tags` tests
- `tests/test_mongodb_service_simple.py` : `get_expected_calibre_tags` tests
- `tests/test_api_palmares.py` : enrichissement via nouveau service

### Frontend (532 tests total)
- `frontend/src/views/__tests__/CalibreCorrections.spec.js` : 421 lignes
- `frontend/src/views/__tests__/Palmares.spec.js` : 2 tests Anna's Archive URL
- `frontend/tests/unit/livreDetailAnnasArchive.spec.js` : assertion URL mise à jour

## Lecons apprises

1. **Tag fonctionnel vs conditionnel** : Le tag `guillaume` a une vocation de copier-coller dans Calibre. Il ne doit pas dépendre de l'existence du livre dans Calibre - c'est justement pour les livres absents qu'il est le plus utile.

2. **URLs externes mortes** : Les domaines d'Anna's Archive changent fréquemment. Le pattern 3-tier (env var + Wikipedia + hardcoded) est bon mais le hardcoded default doit être maintenu à jour.

3. **Normalisation text vs regex** : Deux fonctions distinctes dans `text_utils.py` :
   - `create_accent_insensitive_regex()` : pour les recherches MongoDB `$regex`
   - `normalize_for_matching()` : pour les comparaisons d'égalité/containment (plain text)

4. **Conversion String/ObjectId obligatoire** : Les champs `*_oid` dans `avis_critiques` sont String, mais les `_id` dans les collections référencées sont ObjectId. Toujours convertir avec `BsonObjectId()`.

5. **Tags notables Calibre** : Les tags `babelio`, `lu`, `onkindle` sont préservés dans `all_tags_to_copy` uniquement s'ils existent déjà dans Calibre. Cela évite de perdre des métadonnées lors du remplacement de tags.
