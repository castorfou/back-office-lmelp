# Issue #240 — Colonne Reco dans la page OnKindle

## Contexte

La page `/onkindle` liste les livres Calibre tagués "onkindle". La page `/recommendations`
calcule un score hybride SVD par livre non encore noté. La demande : afficher ce score de
recommandation dans la page OnKindle pour répondre à "quel livre de ma liseuse ai-je le
plus de chances d'aimer ?".

## Solution retenue : Frontend parallel loading

Pas de modification backend. Le frontend appelle deux endpoints en parallèle :
- `/api/calibre/onkindle` → chargement rapide, table visible immédiatement
- `/api/recommendations/me?top_n=1000` → calcul SVD ~10s, charge en arrière-plan

Jointure côté client : `book.mongo_livre_id === recommendation.livre_id`

## Bug découvert : SVD non-déterministe

**Symptôme** : les scores diffèrent entre la page Recommandations et la page OnKindle
(deux appels indépendants → deux entraînements SVD avec graines aléatoires différentes).

**Fix** : ajout de `"random_state": 42` dans `SVD_PARAMS` dans
`src/back_office_lmelp/services/recommendation_service.py:31-36`.

Le SVD Surprise supporte ce paramètre natif. Avec une graine fixe et les mêmes données,
les scores sont identiques d'un appel à l'autre.

## Fichiers modifiés

### `frontend/src/views/OnKindle.vue`
- Nouvelle colonne **Reco** dans le tableau (entre Note et Babelio)
- `data()` : ajout de `recommendations: []`, `recommendationsLoading: false`
- Tri par défaut changé : `sortKey: 'score'`, `sortDir: 'desc'`
- `'score'` ajouté dans les clés de tri valides (URL params)
- `computed.recommendationsByLivreId` : map `{livre_id: score_hybride}`
- `computed.sortedBooks` : gestion du tri par score avec **null toujours en bas**
  et tri secondaire par titre pour ordre déterministe quand tous les scores sont null
- `methods.loadRecommendations()` : appel `/api/recommendations/me?top_n=1000`
  avec timeout 60s, dégradation gracieuse si erreur
- `methods.recoClass(score)` : badges colorés (vert ≥8, jaune ≥6, gris sinon)
- `mounted()` : `await loadOnKindleBooks()` puis `loadRecommendations()` sans await
- CSS : `.col-score`, `.score-badge`, `.score-high/.score-medium/.score-low`

### `frontend/src/views/__tests__/OnKindle.spec.js`
- `mountWithData(apiResponse, recoResponse=[])` : 2e paramètre pour mock recommandations
  (2 `mockResolvedValueOnce` en séquence : onkindle puis recommendations)
- Passage de `await $nextTick x2` à `await flushPromises()` pour fiabilité
- Tests mis à jour pour refléter le nouveau tri par défaut (`score-desc`)
- Nouveau `describe('Recommendation score column (Issue #240)')` : 11 nouveaux tests
  couvrant badge, valeur, tri, null-last, dégradation gracieuse, chargement asynchrone

### `src/back_office_lmelp/services/recommendation_service.py`
- `SVD_PARAMS` : ajout de `"random_state": 42`

### `tests/test_recommendation_service.py`
- Nouveau test `test_get_recommendations_are_reproducible` : vérifie que deux appels
  successifs avec les mêmes données produisent des scores identiques

## Patterns importants

### Chargement asynchrone indépendant
```python
async mounted() {
  await this.loadOnKindleBooks();  // bloquant : table visible dès que fini
  this.loadRecommendations();      // non-bloquant : enrichit en arrière-plan
}
```

### Tri null-en-bas avec secondaire déterministe
```javascript
if (scoreA === null && scoreB === null) {
  // Tri secondaire par titre pour ordre déterministe
  return (a.titre || '').localeCompare(b.titre || '', 'fr', { sensitivity: 'base' });
}
if (scoreA === null) return 1;
if (scoreB === null) return -1;
```

### top_n=1000 pour couvrir tous les livres onkindle
La page Recommandations utilise `top_n=20`. OnKindle demande `top_n=1000` pour s'assurer
que tous les livres onkindle soient inclus (la liste est bornée à ~30 livres en pratique).

### Tests avec 2 appels axios
Quand le composant appelle 2 APIs, le helper de test doit enregistrer 2 mocks :
```javascript
axios.get.mockResolvedValueOnce({ data: onkindleResponse });
axios.get.mockResolvedValueOnce({ data: recoResponse }); // [] par défaut
```
Utiliser `flushPromises()` plutôt que `$nextTick x2` pour attendre toutes les promesses.
