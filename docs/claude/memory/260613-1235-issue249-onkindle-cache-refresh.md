# Issue #249 - OnKindle : bouton Actualiser + message cache 5 min

## Contexte

Les données de la page OnKindle proviennent du cache in-memory de `CalibreMatchingService`
(`_cache_ttl = 300s`). Quand l'utilisateur modifie des tags `onkindle` dans Calibre, les
changements n'apparaissent pas immédiatement dans l'app (jusqu'à 5 minutes de délai).

L'utilisateur avait constaté un écart de 3 livres entre l'app et le Kindle réel — en réalité
les tags avaient été supprimés dans Calibre mais le cache de l'app était encore valide.

## Cause racine

`CalibreMatchingService._get_data()` met en cache les données Calibre pendant 5 minutes.
`get_onkindle_books()` consomme ce cache via `_get_data()`. Le endpoint d'invalidation
`POST /api/calibre/cache/invalidate` existait déjà (`app.py:890`) mais n'était pas exposé
à l'utilisateur depuis la page OnKindle.

## Fix implémenté

Fichier modifié : `frontend/src/views/OnKindle.vue`

### 1. Message informatif dans le header

Ajout d'un span `"Mise en cache 5 min"` à côté du compteur de livres.
CSS : classe `.cache-info` (texte gris italique, `margin-left: auto` pour pousser à droite).

### 2. Bouton Actualiser

- Attribut `data-test="refresh-button"` pour les tests
- Désactivé (`:disabled="refreshing"`) pendant l'opération
- Texte dynamique : `"Actualiser"` → `"Actualisation…"`

### 3. Méthode `refreshData()`

```javascript
async refreshData() {
  this.refreshing = true;
  this.error = null;
  try {
    await axios.post('/api/calibre/cache/invalidate');
    await this.loadOnKindleBooks();
  } catch (err) {
    this.error = err.message || 'Erreur lors de l\'actualisation';
  } finally {
    this.refreshing = false;
  }
},
```

Séquence : POST invalidate → GET onkindle → affichage rafraîchi.

## Tests ajoutés

Fichier : `frontend/src/views/__tests__/OnKindle.spec.js`
Section : `describe('Cache refresh (Issue #249)', ...)`

5 tests TDD (RED → GREEN) :
1. Affiche un message mentionnant "5 min"
2. Affiche un bouton `[data-test="refresh-button"]`
3. Clic bouton → appelle `POST /api/calibre/cache/invalidate` puis `GET /api/calibre/onkindle`
4. Bouton désactivé pendant le refresh (`disabled` attribute présent)
5. Affiche une erreur si l'invalidation échoue

## Architecture existante réutilisée

- `POST /api/calibre/cache/invalidate` (`app.py:890`) : endpoint déjà présent, appelé directement
- `loadOnKindleBooks()` : méthode existante réutilisée après invalidation
- `data.error` + `[data-test="error"]` : pattern d'affichage d'erreur déjà en place

## Leçon

Le cache 5 min de `CalibreMatchingService` est intentionnel (performance). Pour les pages
qui lisent ce cache, toujours exposer un bouton de refresh qui appelle
`POST /api/calibre/cache/invalidate`. Le endpoint d'invalidation est générique et invalide
tout le cache matching (utile pour OnKindle mais aussi pour les corrections Calibre).
