# Issue #212 - Masquer les stats du dashboard à 0

## Contexte

Le dashboard affichait 12 cartes de statistiques en permanence, même quand certaines avaient une valeur de 0. L'objectif est d'économiser de la place en masquant les cartes inutiles.

## Modifications

### Frontend - Dashboard.vue

- Ajout de directives `v-if` sur les 11 cartes de statistiques (toutes sauf "Dernière mise à jour")
- Chaque carte est masquée quand sa valeur est exactement `0`
- Les cartes restent visibles pendant le chargement (valeur `null` : `null !== 0` est `true`)
- Fichier : `frontend/src/views/Dashboard.vue:31-130`

### Pattern v-if utilisé

Pour les stats issues de `collectionsStatistics` :
```html
v-if="collectionsStatistics && collectionsStatistics.field_name !== 0"
```

Pour les compteurs standalone (`critiquesManquantsCount`, `episodesSansEmissionCount`, `totalDuplicatesCount`) :
```html
v-if="fieldName !== 0"
```

### Tests ajoutés

3 nouveaux tests dans `frontend/tests/integration/Dashboard.test.js` :
1. **Masquage des cartes à 0** : fournit des mock data avec plusieurs stats à 0, vérifie que ces cartes ne sont pas rendues
2. **Affichage des cartes non-zéro** : vérifie que toutes les cartes avec valeur > 0 sont bien visibles
3. **Cartes en chargement** : vérifie que les cartes avec valeur `null` (pendant le chargement) restent visibles avec `...`

1 test existant mis à jour : suppression de l'assertion `expect(wrapper.text()).toContain('0')` pour `avis_critiques_without_analysis` (cette carte à 0 est maintenant masquée).

## Point technique

La clé du pattern est que `null !== 0` retourne `true` en JavaScript, donc les cartes en chargement (initialisées à `null` dans `data()`) restent visibles avec l'indicateur `...`. Quand la donnée arrive avec une valeur de `0`, la carte disparaît. Pour les valeurs non-zéro, la carte s'affiche normalement.
