# Issue #223 — Spike Collaborative Filtering : Surprise vs implicit

## Contexte

Spike exploratoire pour choisir entre Surprise et implicit avant d'implémenter le système de recommandation complet (#222).

## Fichiers créés

- `notebooks/dataset_avis.py` — utilitaire commun : extraction MongoDB (collection `avis`), injection Calibre ("Moi (Calibre)" comme 30ème critique fictif)
- `notebooks/spike_surprise_cf.ipynb` — KNN user-based/item-based, SVD, espace latent, recommandations pour Viviant et "Moi (Calibre)"
- `notebooks/spike_svd_latent_cf.ipynb` — analyse approfondie de l'espace latent SVD : heatmap, K-Means, biplot, ACP
- `notebooks/spike_implicit_cf.ipynb` — ALS, BPR, GridSearch hyperparamètres, heatmap, clustering, biplot, recommandations pour Viviant et "Moi (Calibre)"
- `docs/user/recommandation-livres.md` — documentation utilisateur complète : KNN, SVD, implicit (ALS/BPR), Précision@K, tableau comparatif

## Dépendances ajoutées

`pyproject.toml` section `[project.optional-dependencies]` avec `ml = [scikit-surprise, implicit, pandas, matplotlib, scikit-learn]`

## Découverte critique : convention implicit v0.7

**IMPORTANT** : `implicit.als.AlternatingLeastSquares.fit()` attend `user × item` (lignes = users, colonnes = items).

```python
# ✅ CORRECT — passer mat_critique_livre directement (29 × 1615)
model.fit(mat_critique_livre.tocsr())
# → user_factors.shape = (29, factors)   ← critiques
# → item_factors.shape = (1615, factors) ← livres

# ❌ MAUVAIS — passer la transposée (1615 × 29)
model.fit(mat_critique_livre.T.tocsr())
# → user_factors.shape = (1615, factors) ← LIVRES (inversé !)
# → item_factors.shape = (29, factors)   ← CRITIQUES (inversé !)
```

**Symptôme de l'erreur** : `IndexError: index 32 is out of bounds for axis 1 with size 29` dans `model.recommend(u_idx, mat[u_idx], ...)` — `u_idx` est un indice critique (ex: 32) mais `mat[u_idx]` est de shape `(1, 29)` au lieu de `(1, 1615)`.

**Cause** : Quand on passe la transposée, `recommend()` attend `user_items` de shape `(1, n_users)` car il traite les livres comme users.

## Appel model.recommend() — syntaxe correcte

```python
mat_full_csr = mat_critique_livre.tocsr()  # shape (n_c, n_l)
user_row = mat_full_csr[u_idx]             # shape (1, n_l) — CSR row slice
item_ids, scores = model.recommend(u_idx, user_row, N=10, filter_already_liked_items=True)
```

- `user_row` doit être une **CSR sparse matrix** (pas un array dense)
- `user_row` doit contenir **1 ligne** (la ligne de l'utilisateur)
- `u_idx` doit être l'index dans `mat_full_csr` (mêmes encoders que lors du fit)

## RMSE vs Précision@K

- **Surprise SVD** : optimise la prédiction de note → RMSE approprié (1.77 sur ce dataset)
- **implicit ALS/BPR** : optimisent le ranking → **RMSE sans sens** (produit scalaire ≠ note 1-10)
- **Précision@K** pour implicit : fraction des top-K recs vraiment aimées (note ≥ 7 en test)
  - ALS ~0.30, BPR ~0.25 (Précision@10)

## GridSearch implicit — pattern

```python
from itertools import product

best_params, best_score = {}, -1
for factors, reg, iters in product(factors_list, reg_list, iters_list):
    model = AlternatingLeastSquares(factors=factors, regularization=reg, iterations=iters)
    model.fit(mat_train, show_progress=False)
    score = precision_at_k(model, df_test, critique_encoder, livre_encoder, mat_train)
    if score > best_score:
        best_score, best_params = score, {"factors": factors, "regularization": reg, "iterations": iters}
```

## Choix final : SVD (Surprise) pour #222

SVD reste le meilleur choix car :
- Objectif aligné : prédire une note 1-10 (nos données sont des notes réelles)
- RMSE mesurable et comparable (1.77 vs baseline 2.13)
- Espace latent interprétable (`svd.pu`, `svd.qi`)
- n_factors=10 : meilleur compromis RMSE (1.80) / variance ACP (37%)

## Patterns dataset_avis.py

```python
# Extraction MongoDB
client = MongoClient(os.getenv("MONGODB_URL", "mongodb://localhost:27017"))
db = client.get_default_database()
avis = list(db.avis.find({}, {"critique_oid": 1, "livre_oid": 1, "note": 1, ...}))

# Injection Calibre — notes en base 0-10 par pas de 2 (0=pas de note)
# rating Calibre = étoiles × 2, scale 1-10 : garder rating directement (2=1*, 10=5*)
calibre_notes = calibre_service.get_calibre_ratings()  # filtre rating > 0

# Encodage — StringLabelEncoder sur critique_oid et livre_oid (tous deux String)
critique_encoder = LabelEncoder().fit(df['critique_oid'])
livre_encoder = LabelEncoder().fit(df['livre_oid'])
```

## Note : avis collection — champs String

`avis.critique_oid`, `avis.livre_oid` sont des **String** (pas ObjectId).
Pas besoin de conversion pour les encodeurs.
