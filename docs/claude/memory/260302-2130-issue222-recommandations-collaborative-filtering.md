# Issue #222 — Recommandations de livres par Collaborative Filtering SVD

## Contexte

Implémentation d'un moteur de recommandations basé sur la matrice critique×livre (4 080 avis notés, 1 612 livres, 22 critiques) combiné aux notes personnelles Calibre (~133 livres notés).

Décisions du spike #235 : SVD Surprise, scoring hybride 0.7×SVD + 0.3×masque_mean, calcul temps réel.

## Fichiers créés/modifiés

### Nouveaux fichiers
- `src/back_office_lmelp/services/recommendation_service.py` — Service SVD complet
- `tests/test_recommendation_service.py` — 16 tests TDD
- `frontend/src/views/Recommendations.vue` — Page tableau avec bandeau expérimental

### Fichiers modifiés
- `src/back_office_lmelp/app.py` — import + instanciation + route `GET /api/recommendations/me`
- `frontend/src/router/index.js` — route `/recommendations`
- `frontend/src/views/Dashboard.vue` — carte ⭐ dans section Consultation
- `pyproject.toml` — ajout override mypy pour `pandas.*`, `surprise.*`, `implicit.*` + module `back_office_lmelp.services.recommendation_service`

## Architecture du service

### Pipeline `get_recommendations(top_n=20)`
1. Charger notes Calibre → `_load_calibre_notes()` → `{titre_norm: note}`
2. Charger avis MongoDB (`avis` collection, pipeline aggregation)
3. Filtrer critiques avec < 10 avis → `_filter_active_critiques()`
4. Matcher Calibre → MongoDB via normalisation titres → `_match_calibre_to_livre_oids()`
5. Calculer moyennes Masque par livre → `_compute_masque_means()`
6. Entraîner SVD Surprise (n_factors=20, n_epochs=50, lr_all=0.01, reg_all=0.1)
7. Calculer `score = 0.7 × svd_predict + 0.3 × masque_mean` pour livres non vus avec ≥ 2 critiques
8. Enrichir avec titres/auteurs MongoDB → `_enrich_with_livre_auteur()`

### Constantes importantes
```python
USER_ID = "Moi"
SVD_PARAMS = {"n_factors": 20, "n_epochs": 50, "lr_all": 0.01, "reg_all": 0.1}
MIN_AVIS_PER_CRITIQUE = 10
MIN_CRITIQUES_PER_LIVRE = 2
HYBRID_WEIGHT_SVD = 0.7
HYBRID_WEIGHT_MASQUE = 0.3
```

## Bug critique résolu : Rating Calibre mal converti

**Symptôme** : scores SVD ~2.5 au lieu de ~7-9, classement incohérent avec le spike.

**Cause** : le code utilisait `rating / 10.0` croyant que Calibre stockait 0-100. En réalité, Calibre stocke `2, 4, 6, 8, 10` (par pas de 2, déjà sur échelle 1-10).

**Fix** :
```python
# ❌ MAUVAIS
note = rating / 10.0  # 8 → 0.8 (hors échelle SVD !)

# ✅ CORRECT (notebook dataset_avis.py : note_calibre = int(rating))
note = float(rating)  # 8 → 8.0 (cohérent avec échelle 1-10 du Masque)
```

**Référence notebook** : `notebooks/dataset_avis.py` ligne `note_calibre = int(rating)` — pas de conversion.

## Types MongoDB vérifiés (collection `avis`)
- `critique_oid` = **String** (pas ObjectId)
- `livre_oid` = **String** (pas ObjectId)
- `note` = **Number** (int)
- Lors de l'enrichissement : `livres._id` = ObjectId → conversion `ObjectId(str)` nécessaire

## Pattern d'initialisation (app.py)
```python
from .services.recommendation_service import RecommendationService
recommendation_service = RecommendationService(calibre_service, mongodb_service)
```
Singleton instancié après `calibre_matching_service`, avant les routes.

## Override mypy requis (pyproject.toml)
```toml
[[tool.mypy.overrides]]
module = "back_office_lmelp.services.recommendation_service"
disable_error_code = ["import-untyped"]
```
Et ajout de `"pandas.*"`, `"surprise.*"`, `"implicit.*"` dans la liste `ignore_missing_imports = true`.

## Frontend
- Route : `/recommendations` → `Recommendations.vue`
- Bandeau warning jaune : "Recommandations expérimentales — Hit Rate @20 ~1.4%"
- Timeout axios : 60 000 ms (calcul SVD ~5-10s)
- Tableau : # | Titre (→ /livre/:id) | Auteur (→ /auteur/:id) | Score | SVD | Masque | N critiques
- Badge couleur : ≥8 vert, ≥6 orange, <6 gris

## Tests (16 tests, tous verts)
- `TestRecommendationServiceInit` — init service
- `TestFilterCritiques` — filtre MIN_AVIS_PER_CRITIQUE
- `TestCalibreNotesLoading` — chargement notes, pas de conversion rating
- `TestHybridScoreFormula` — formule 0.7/0.3
- `TestGetRecommendations` — liste, champs requis, tri, top_n, cas vides
