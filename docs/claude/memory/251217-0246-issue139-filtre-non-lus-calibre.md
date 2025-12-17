# Issue #139 - Correction du filtre "Non lus" dans Bibliothèque Calibre

**Date**: 2025-12-17 02:46
**Issue**: [#139](https://github.com/castorfou/back-office-lmelp/issues/139)
**Statut**: ✅ Résolu

## Problème

Le filtre "Non lus" de la bibliothèque Calibre retournait une liste vide alors qu'il devrait afficher 217 livres non lus.

## Cause racine

Dans [CalibreLibrary.vue:203](frontend/src/views/CalibreLibrary.vue#L203), le filtre utilisait une égalité stricte :

```javascript
result = result.filter(book => book.read === this.readFilter);
```

Quand `readFilter === false` (filtre "Non lus"), les livres avec `read === null` (statut inconnu) étaient exclus car `null === false` retourne `false`.

## Solution implémentée

### 1. Test TDD (RED)

Modifié le test existant dans [CalibreLibrary.test.js:300-331](frontend/tests/unit/CalibreLibrary.test.js#L300-L331) :

```javascript
it('should filter unread books when clicking "Non lus" button', async () => {
  calibreService.getBooks.mockResolvedValue({
    total: 5,
    books: [
      { id: 1, title: 'Book 1', authors: ['A'], read: true },
      { id: 2, title: 'Book 2', authors: ['B'], read: false },
      { id: 3, title: 'Book 3', authors: ['C'], read: true },
      { id: 4, title: 'Book 4', authors: ['D'], read: false },
      { id: 5, title: 'Book 5', authors: ['E'], read: null }  // ← Ajouté
    ]
  });

  // ...

  expect(wrapper.vm.filteredBooks).toHaveLength(3);  // ← 2 false + 1 null
  expect(wrapper.vm.filteredBooks.every(b => b.read === false || b.read === null)).toBe(true);
  expect(wrapper.vm.filteredBooks.some(b => b.id === 5 && b.read === null)).toBe(true);
});
```

**Résultat** : Test échoue (attendait 3 livres, obtenait 2) ✅ RED

### 2. Code fix (GREEN)

Modifié la logique de filtrage dans [CalibreLibrary.vue:202-210](frontend/src/views/CalibreLibrary.vue#L202-L210) :

```javascript
if (this.readFilter !== null) {
  if (this.readFilter === false) {
    // For "unread" filter, include books with read === false OR read === null
    result = result.filter(book => book.read === false || book.read === null);
  } else {
    // For "read" filter, only include books with read === true
    result = result.filter(book => book.read === true);
  }
}
```

**Résultat** : Tous les tests passent (18/18 pour CalibreLibrary, 361/361 pour tout le frontend) ✅ GREEN

## Logique métier

### Interprétation du statut `read: null`

Les livres avec `read === null` représentent un **statut de lecture inconnu**. La décision de les inclure dans "Non lus" repose sur :

1. **Approche par défaut raisonnable** : Si on ne sait pas si un livre a été lu, il est plus prudent de le considérer comme "non lu"
2. **Expérience utilisateur** : L'utilisateur s'attend à voir tous les livres potentiellement non lus
3. **Cohérence** : Le filtre "Lus" n'inclut QUE les livres explicitement marqués comme lus (`read === true`)

### Comportement des filtres

| Filtre    | Statut inclus           | Logique                                  |
|-----------|-------------------------|------------------------------------------|
| Tous      | `true`, `false`, `null` | Aucun filtre appliqué                    |
| Lus       | `true` uniquement       | `book.read === true`                     |
| Non lus   | `false` ET `null`       | `book.read === false \|\| book.read === null` |

## Fichiers modifiés

1. **Frontend**
   - [CalibreLibrary.vue](frontend/src/views/CalibreLibrary.vue) - Logique de filtrage corrigée
   - [CalibreLibrary.test.js](frontend/tests/unit/CalibreLibrary.test.js) - Test amélioré avec cas `null`

## Tests

- ✅ Test unitaire spécifique : `should filter unread books when clicking "Non lus" button`
- ✅ Tous les tests CalibreLibrary : 18/18
- ✅ Tous les tests frontend : 361/361
- ✅ Test utilisateur validé

## Apprentissages clés

### 1. TDD strict pour les bugs de filtrage

**Pattern appliqué** :
1. Identifier le cas limite manquant (`read: null`)
2. Ajouter ce cas au test existant
3. Vérifier que le test échoue (RED)
4. Corriger le code
5. Vérifier que le test passe (GREEN)

**Pourquoi c'est important** : Les bugs de filtrage sont souvent dus à des cas limites non testés (valeurs `null`, `undefined`, tableaux vides, etc.).

### 2. Égalité stricte vs logique métier

**Anti-pattern** :
```javascript
result = result.filter(book => book.read === this.readFilter);
```

**Problème** : L'égalité stricte ne gère pas les valeurs `null` de manière appropriée pour la logique métier.

**Pattern correct** :
```javascript
if (this.readFilter === false) {
  result = result.filter(book => book.read === false || book.read === null);
} else {
  result = result.filter(book => book.read === true);
}
```

### 3. Valeurs null dans les données Calibre

Les livres Calibre peuvent avoir des colonnes personnalisées avec des valeurs `null`. Il faut toujours gérer ce cas :

- Dans les filtres (comme ici)
- Dans l'affichage (`v-if="book.read !== null"` dans le template)
- Dans les statistiques (calcul du nombre de livres non lus)

## Références

- **Issue GitHub** : [#139](https://github.com/castorfou/back-office-lmelp/issues/139)
- **Branche** : `139-bug-sous-bibliotheque-calibre-filtre-non-lus-ne-fonctionne-pas`
- **Contexte** : Intégration Calibre (Issue #119)
