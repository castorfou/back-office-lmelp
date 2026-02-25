# Issue #227 — Page liste des critiques + merge de doublons

**Branche** : `227-feat-page-liste-des-critiques-avec-accès-direct-à-critiquedetail`
**Date** : 2026-02-25

---

## Contexte

L'accès à `CritiqueDetail` (`/critique/:id`) n'était possible qu'en passant par une émission ou un livre. L'issue demandait :
1. Page `/critiques` listant tous les critiques (triable, clic → détail)
2. Carte Dashboard "Critiques" dans la section Consultation
3. Liens cliquables dans `/identification-critiques` pour les critiques existants
4. Fonctionnalité de **merge** de deux critiques doublons avec confirmation obligatoire

En parallèle : correction du dataset CF pour exclure les critiques avec trop peu d'avis (bruit dans la matrice sparse).

---

## Fichiers modifiés

### Backend Python

**`src/back_office_lmelp/services/mongodb_service.py`**
- Nouvelle méthode `get_all_critiques()` : pipeline `$lookup` avec `$toString` pour convertir `critiques._id` (ObjectId) en String pour matcher `avis.critique_oid` (String)
- Nouvelle méthode `merge_critiques(source_id, target_id)` : repointe `avis.update_many`, fusionne variantes, supprime source
- Le pipeline retourne `nombre_avis`, `note_moyenne`, trié par `nom` ASC

**`src/back_office_lmelp/services/critiques_extraction_service.py`**
- `find_matching_critique()` retourne désormais `id` (str) en plus de `nom` et `match_type`
- Nécessaire pour les router-links dans `IdentificationCritiques.vue`

**`src/back_office_lmelp/app.py`**
- `GET /api/critiques` : AVANT `/api/critique/{id}` (ordre critique pour éviter conflit FastAPI)
- `POST /api/critiques/merge` : avec `MergeCritiquesRequest` (Pydantic), validation `target_nom`, retourne 400/404 appropriés
- Endpoint `get_detected_critiques` : ajoute `matched_critique_id` dans la réponse pour les critiques existants

### Frontend Vue.js

**`frontend/src/views/Critiques.vue`** (créé)
- Table triable par nom/avis/note avec `localeCompare('fr', {sensitivity:'base'})`
- Lignes cliquables → `/critique/:id` (curseur pointer, nom bleu + flèche `→` au hover, fond bleu pâle)
- Section merge : select source/cible, champ confirmation (nom exact du target), bouton désactivé sans confirmation
- États loading/error/empty

**`frontend/src/router/index.js`**
- Route `/critiques` ajoutée **avant** `/critique/:id` (ordre essentiel)

**`frontend/src/views/Dashboard.vue`**
- Carte "Critiques" 🎙️ dans la section Consultation
- Méthode `navigateToCritiques()`

**`frontend/src/views/IdentificationCritiques.vue`**
- `<router-link :to="/critique/${matched_critique_id}">` conditionnel sur `matched_critique_id`
- Fallback `<span>` si pas d'id
- Style `.critique-link` (bleu, souligné au hover)

### Notebooks / dataset CF

**`notebooks/dataset_avis.py`**
- Section 4b : filtre `MIN_AVIS_PAR_CRITIQUE = 10` après fusion des sources
- Critères : `avis_par_critique >= MIN_AVIS_PAR_CRITIQUE`
- Résultat réel : 3 critiques exclus sur 25 (22 conservés)
- Calcul sparsity protégé contre division par zéro

**`notebooks/spike_surprise_cf.ipynb`, `spike_svd_latent_cf.ipynb`, `spike_implicit_cf.ipynb`**
- Ré-exécutés avec le nouveau filtre (commit séparé par l'utilisateur)

---

## Tests

### Backend (20 tests nouveaux)
**`tests/test_api_critiques_list_merge.py`** :
- `TestGetAllCritiques` (6) : endpoint 200, champs requis, animateur, note_moyenne null, liste vide, pas de conflit route
- `TestMergeCritiques` (6) : succès, mauvaise confirmation 400, source/target 404, même id 400, appel service
- `TestMongoDBServiceGetAllCritiques` (2) : agrégation, champs nombre_avis/note_moyenne
- `TestMongoDBServiceMergeCritiques` (4) : update_many avis, delete source, fusion variantes, résumé retourné
- `TestCritiquesExtractionReturnsId` (2) : id présent pour exact et variante

**`tests/test_critiques_extraction_service.py`** : ajout de `_id: ObjectId(...)` dans tous les mocks `find_matching_critique` (champ requis après modification)

### Dataset CF (17 tests total)
**`tests/test_dataset_avis.py`** :
- `TestFiltrageMinAvis` (3 nouveaux) : exclu si < 10, conservé si = 10, n_critiques reflète filtrage
- Fixtures `avis_simple` migrées à 10 avis par critique (seuil minimum)
- Helper `_avis_deux_critiques` complète automatiquement jusqu'au seuil avec avis de remplissage

### Frontend (11 tests)
**`frontend/src/views/__tests__/Critiques.spec.js`** :
- Rendu liste, nb avis/note, loading, error, empty
- Tri ASC par défaut, DESC au clic
- Navigation au clic sur ligne
- Merge : bouton désactivé sans complet, activé avec tout rempli, POST avec bons params

---

## Patterns importants retenus

### Type mismatch MongoDB — $toString dans $lookup
`avis.critique_oid` est **String**, `critiques._id` est **ObjectId** → la jointure nécessite `$toString` dans le pipeline :
```python
pipeline: list[dict[str, Any]] = [
    {"$lookup": {
        "from": "avis",
        "let": {"cid": {"$toString": "$_id"}},
        "pipeline": [{"$match": {"$expr": {"$eq": ["$critique_oid", "$$cid"]}}}],
        "as": "avis_list",
    }},
    ...
]
```

### Route ordering FastAPI
`GET /api/critiques` **DOIT** être déclaré avant `GET /api/critique/{id}` sinon "critiques" est capturé comme paramètre `id`.

### Merge critiques — périmètre
- `avis.critique_oid` (String) : `update_many` → remappé sur target
- `critiques.variantes` : fusionnées (sans doublons, en excluant le nom du target lui-même)
- `avis_critiques` : **non impacté** (contient des noms extraits, pas d'OIDs)

### Dataset CF — filtrage sparse
Critiques avec < `MIN_AVIS_PAR_CRITIQUE` (=10) avis exclus pour réduire le bruit. Le seuil est **inclusif** (10 = conservé). La sparsity doit être protégée contre la division par zéro si df est vide après filtrage.

### Indicateurs visuels de cliquabilité (Vue.js)
```css
.critique-row { cursor: pointer; }
.critique-row:hover { background-color: #f0f4ff; }
.critique-row:hover .critique-nom-link { color: #2b6cb0; text-decoration: underline; }
.critique-row:hover .row-arrow { opacity: 1; }
.row-arrow { opacity: 0; transition: opacity 0.15s ease; }
```
Flèche `→` invisible par défaut, apparaît au hover — pattern propre sans ajouter de texte permanent.
