# Recommandation de livres

Le système de recommandation prédit quels livres du corpus *Le Masque & la Plume*
vous êtes susceptible d'apprécier, en se basant sur les 4 000+ avis des critiques
et sur vos propres notes Calibre.

Cette page explique les concepts qui le sous-tendent — comment les algorithmes
raisonnent, pourquoi ils fonctionnent, et quelles sont leurs limites sur ce dataset.

---

## Le point de départ : une matrice presque vide

Les données se présentent comme une matrice critique × livre :

```
             Roman A  Roman B  Roman C  Roman D  Roman E  ...
Viviant         9       —        7       —        8
Lamberterie     —       8        —       6        —
Martin          7       —        9       —        7
Moi (Calibre)   —       —        8       —        9
...
```

- **Les chiffres** : notes réelles (1–10)
- **Les tirets** : le critique n'a pas noté ce livre

Avec 29 critiques et 1 615 livres, la matrice n'est remplie qu'à **9%**.
C'est le point de départ de tout système de recommandation par *collaborative filtering* :
inférer ce que vaudrait chaque case vide.

---

## Deux grandes familles d'approches

### Approche KNN — "Dis-moi qui te ressemble"

Le *K-Nearest Neighbors* cherche les critiques dont les goûts sont les plus proches des vôtres,
puis recommande ce qu'ils ont aimé.

**User-based** : on compare les critiques entre eux.

> "Vous et Nelly Kapriélian avez noté les mêmes livres de façon similaire.
> Elle a adoré *Origine* (9/10) — vous ne l'avez pas encore lu — il devrait vous plaire."

**Item-based** : on compare les livres entre eux.

> "Vous avez mis 9 à *Jacaranda*. Les critiques qui ont aimé *Jacaranda*
> ont aussi beaucoup aimé *Trois nuits dans la vie de Berthe Morisot* — voici pourquoi on vous le suggère."

**La métrique de similarité** utilisée est le *cosinus* : deux vecteurs de notes
sont "proches" s'ils pointent dans la même direction, indépendamment de leur magnitude.

```
Vous    : [9, 7, 8]   →  similarité cosinus  ←   Viviant : [8, 6, 7]

cos(θ) = (9×8 + 7×6 + 8×7) / (√(9²+7²+8²) × √(8²+6²+7²))
       = 170 / (√194 × √149)  ≈  0.998   ← très similaires
```

L'avantage du cosinus sur une simple distance : il est **insensible au niveau absolu**.
Un critique qui note systématiquement 1-2 points plus bas qu'un autre sera quand même
reconnu comme similaire — ce qui compte, c'est la *forme* du profil, pas le niveau.

**La prédiction** est ensuite une moyenne pondérée des notes des K voisins les plus proches,
où le poids de chaque voisin est sa similarité avec vous :

```
note_prédite(vous, livre) =  Σ [ sim(vous, voisin) × note(voisin, livre) ]
                             ─────────────────────────────────────────────
                                      Σ [ sim(vous, voisin) ]
```

Le **K** (= 5 par défaut dans Surprise) est le nombre de voisins considérés.
Sur ce dataset, son impact est limité : pour un livre peu noté, il n'y a souvent que 2-3
critiques disponibles — on prend alors tous ceux qu'on peut trouver.

### Approche SVD — "Trouve les goûts cachés"

*Singular Value Decomposition* — plus exactement **FunkSVD**, popularisé lors du
[Netflix Prize](https://en.wikipedia.org/wiki/Netflix_Prize) (2006–2009), la compétition
où Netflix offrait 1 million de dollars pour améliorer son système de recommandation de 10%.

L'idée : la grande matrice 29×1615 peut s'approximer comme le produit de deux petites matrices.

```
M (29 × 1615)  ≈  P (29 × 10)  ×  Q᷊ (10 × 1615)
```

- **P** (`svd.pu`) : une ligne par critique → son *profil de goût* en 10 dimensions
- **Q** (`svd.qi`) : une colonne par livre → ses *caractéristiques latentes* en 10 dimensions
- **10** : le nombre de *facteurs latents* retenu — des axes de goût que le modèle découvre tout seul

Le modèle n'est pas la vraie SVD mathématique (qui nécessite une matrice complète).
Il **apprend** P et Q par descente de gradient, uniquement sur les cases connues.
C'est pourquoi on parle plus précisément de **factorisation matricielle**.

---

## Les facteurs latents : le cœur de SVD

Le modèle ne sait pas ce que signifient ses 10 dimensions — mais on peut les imaginer
comme des axes de goût littéraire qu'il découvre automatiquement à partir des données :

```
Facteur 1 : littérature expérimentale  ←————→  récit accessible
Facteur 2 : fiction pure               ←————→  autobiographie/récit
Facteur 3 : sensible au style          ←————→  sensible à l'histoire
Facteur 4 : littérature française      ←————→  littérature étrangère
...
```

Chaque critique est représenté par 10 nombres — sa position sur ces axes.
Chaque livre aussi. La note prédite est un simple **produit scalaire** :

```
note(critique, livre) ≈ profil_critique · caractéristiques_livre
```

Si votre profil est "aime la littérature expérimentale" et qu'un livre est
"très expérimental", le produit sera élevé → forte recommandation.

---

## Pourquoi KNN seul ne suffit pas sur ce dataset

La matrice est creuse à 91%. Sur les 378 paires de critiques possibles,
**248 paires (66%) n'ont aucun livre en commun**.
KNN ne peut donc pas calculer de similarité fiable pour la majorité des paires.

Pire : avec un seul livre en commun noté 8 et 6, le cosinus vaut :

```
cos([8], [6]) = (8×6) / (|8| × |6|) = 1.0
```

Un cosinus parfait pour deux critiques qui n'ont noté qu'un seul livre ensemble —
c'est une **illusion de similarité**.

Trois pistes pour y remédier, explorées dans les notebooks de spike :

| Piste | Mécanisme | Limite |
|---|---|---|
| `min_support=N` | Ignore les paires avec < N livres communs | Perd encore plus de paires |
| Complétion SVD → KNN | Complète la matrice, puis cosinus sur 1615 dims | Régularisation → tous similaires |
| **Espace latent SVD** | Cosinus directement sur les 10 facteurs | **Meilleure approche** |

L'espace latent est plus robuste : les 10 dimensions capturent l'*essence* du goût
de chaque critique, sans le bruit des 1615 notes brutes. C'est aussi le principe
qu'utilisent les bibliothèques comme `implicit` (ALS) avec leurs `user_factors`.

---

## Évaluation : le RMSE

Le RMSE (*Root Mean Square Error*) mesure l'écart moyen entre la note réelle et la note prédite.

Sur ce dataset, les repères sont :

| Modèle | RMSE |
|---|---|
| Baseline naïve (toujours prédire la moyenne) | 2.13 |
| KNN User-Based | 1.91 |
| SVD (factorisation matricielle) | 1.77 |

Un RMSE de 1.77 signifie qu'en moyenne le modèle se trompe de ±1.77 points sur 10.
C'est correct pour un dataset aussi creux — mais rappelons que l'objectif final
n'est pas de prédire une note exacte, mais de **bien ordonner les recommandations**.

---

## Choisir le bon nombre de facteurs latents

### La contrainte théorique

Le nombre de facteurs latents (`n_factors`) ne peut pas dépasser la plus petite dimension
de la matrice. Avec 29 critiques et 1 615 livres :

```
n_factors < min(29, 1615) = 29
```

Mais ce n'est pas la seule contrainte. Plus `n_factors` est grand, plus le modèle
a de **paramètres à apprendre** :

```
Paramètres = n_factors × (n_critiques + n_livres)
             Ex. n_factors=10 : 10 × (29 + 1615) = 16 440 paramètres
             Ex. n_factors=20 : 20 × (29 + 1615) = 32 880 paramètres
```

…pour seulement 4 080 notes réelles. Le risque de **surapprentissage** (overfitting)
augmente avec `n_factors`.

### Impact sur le RMSE

| `n_factors` | RMSE (test) |
|---|---|
| 5 | 1.84 |
| **10** | **1.80** |
| 20 | 1.79 |
| 28 | 1.80 |
| 29 | 1.82 |

Le gain entre 10 et 20 facteurs est négligeable (0.01 de RMSE), et au-delà de 28
le modèle commence à se dégrader.

### Impact sur la lisibilité des visualisations

Pour comprendre l'espace latent, on le projette en 2D via une ACP (*Analyse en
Composantes Principales*). La variance capturée par ces 2 dimensions dépend de
`n_factors` :

| `n_factors` | Variance expliquée en 2D |
|---|---|
| 5 | 57% |
| **10** | **37%** |
| 20 | 25% |

Avec 20 facteurs, la projection 2D ne capture que 25% de l'information — les
visualisations deviennent moins représentatives. Avec 10 facteurs, on garde 37%
tout en ayant un RMSE quasi identique.

### Conclusion : `n_factors = 10`

**10 facteurs** offre le meilleur compromis sur ce dataset :

- RMSE aussi bon que 20 facteurs (1.80 vs 1.79)
- Visualisations 2D plus représentatives (37% vs 25% de variance)
- Moins de risque de surapprentissage (16 440 paramètres au lieu de 32 880)

---

## Architecture du système (projet #222)

```
MongoDB (avis)          Calibre (notes)
      ↓                       ↓
      └──── Matrice critique × livre ────┘
                     ↓
             Factorisation SVD
                     ↓
          ┌──────────┴──────────┐
          │                     │
    Profils critiques     Profils livres
    (espace latent 10D)   (espace latent 10D)
          │                     │
          ↓                     ↓
   Critiques similaires   Livres similaires
   (user-based CF)        (item-based CF)
          │                     │
          └──────────┬──────────┘
                     ↓
         Recommandations personnalisées
         "Mes prochaines lectures"
```

---

## Pour aller plus loin

- **Notebooks d'exploration** : `notebooks/spike_surprise_cf.ipynb` et `notebooks/spike_implicit_cf.ipynb`
- **Issue de référence** : [#223 — Spike Surprise vs implicit](https://github.com/castorfou/back-office-lmelp/issues/223)
- **Implémentation** : [#222 — Système de recommandation complet](https://github.com/castorfou/back-office-lmelp/issues/222)
- **Netflix Prize** : la compétition qui a popularisé FunkSVD — [Wikipedia](https://en.wikipedia.org/wiki/Netflix_Prize)
