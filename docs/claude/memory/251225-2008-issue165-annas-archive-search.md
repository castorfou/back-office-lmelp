# Issue #165 - Recherche Anna's Archive depuis la page livre

**Date** : 25 décembre 2024
**Contexte** : Ajout d'une fonctionnalité permettant de rechercher un livre sur Anna's Archive directement depuis la page de détail du livre.

## Points saillants

### 1. Encodage URL pour Anna's Archive

**Apprentissage important** : Anna's Archive utilise un format d'encodage URL spécifique qui diffère légèrement de `encodeURIComponent()` standard :

- Espaces → `+` (au lieu de `%20`)
- Apostrophes → `%27` (encodées explicitement)
- Points d'exclamation → `%21` (encodés explicitement)

**Solution finale** (voir `frontend/src/views/LivreDetail.vue:187-190`) :

```javascript
const encodedQuery = encodeURIComponent(searchQuery)
  .replace(/%20/g, '+')      // Espaces → +
  .replace(/'/g, '%27')       // Apostrophes → %27
  .replace(/!/g, '%21');      // Points d'exclamation → %21
```

**Validation** : L'encodage a été testé avec l'URL réelle d'Anna's Archive et correspond exactement au format attendu.

### 2. Tests avec caractères réels du codebase

Pour valider l'encodage, nous avons exploré la base MongoDB et testé avec des chaînes contenant TOUS les caractères spéciaux présents dans les données réelles :

- **Accents** : é, è, ê, ô, à, û, ù, ï
- **Ligatures** : œ, æ
- **Ponctuation** : ', :, &, !
- **Pattern de test final** : `L'Étrange café-théâtre : à côté du cœur & de l'âme ! - Jean-François Kïœf-Séraphîn`

Cette approche garantit que l'encodage fonctionne avec toutes les données réelles de la base.

### 3. Création d'icône SVG optimisée

**Évolution** : PNG 80x80 → SVG vectoriel

**Avantages** :
- Meilleure résolution sur tous les écrans (pas de pixelisation)
- Taille de fichier réduite
- Cohérence avec l'icône Babelio (déjà en SVG)

**Technique pour SVG ultra-bold** : Utilisation de `stroke-width` pour épaissir le texte et obtenir un rendu proche du logo original d'Anna's Archive :

```svg
<text fill="#000000" stroke="#000000" stroke-width="4" paint-order="stroke">A</text>
```

Le paramètre `paint-order="stroke"` assure que le stroke est dessiné en premier, créant un effet d'épaississement uniforme.

### 4. Architecture composant - Support multi-icônes

**Refactorisation de la structure** pour supporter plusieurs icônes externes :

**Avant** (voir `frontend/src/views/LivreDetail.vue:28-42`) :
- Icône Babelio seule avec classe `.babelio-logo-link`

**Après** (voir `frontend/src/views/LivreDetail.vue:27-60`) :
- Conteneur `.external-links` avec `display: flex`
- Support de multiples icônes côte à côte
- Styles génériques `.external-logo-link` et `.external-logo`

**Avantage** : Permet d'ajouter facilement d'autres services à l'avenir (Goodreads, LibraryThing, etc.) sans refactorisation majeure.

### 5. Approche TDD complète

**Cycle TDD respecté** :
1. **RED** : Écriture de 4 tests qui échouent
2. **GREEN** : Implémentation minimale pour faire passer les tests
3. **REFACTOR** : Ajustement de l'encodage URL après validation avec données réelles

**Tests implémentés** (voir `frontend/tests/unit/livreDetailAnnasArchive.spec.js`) :
- Affichage de l'icône Anna's Archive
- Génération correcte de l'URL avec encodage (exemple Marx en Amérique)
- Ouverture en nouvel onglet (`target="_blank"`)
- Gestion des caractères spéciaux (accents, ligatures, ponctuation)

## Fichiers modifiés

- `frontend/src/views/LivreDetail.vue` : Ajout icône + méthode `getAnnasArchiveUrl()`
- `frontend/src/assets/annas-archive-icon.svg` : Nouvelle icône SVG (création)
- `frontend/tests/unit/livreDetailAnnasArchive.spec.js` : 4 tests TDD complets (création)

## Résultats

- ✅ 4 tests spécifiques passent
- ✅ 371 tests frontend passent (aucune régression)
- ✅ Encodage URL validé contre format réel Anna's Archive
- ✅ Icône SVG nette et optimisée

## Leçons apprises

### Encodage URL : Toujours valider avec le service cible

**Erreur initiale** : Utilisation de `encodeURIComponent()` seul, qui encode les espaces en `%20`.

**Solution** : Tester avec une URL réelle du service cible (Anna's Archive) pour identifier les différences :
- Anna's Archive utilise `+` pour les espaces
- Certains caractères comme `'` et `!` doivent être explicitement encodés

**Apprentissage** : Ne jamais supposer qu'un service utilise l'encodage URL standard. Toujours valider avec une URL réelle.

### SVG : Technique stroke-width pour épaissir du texte

Pour obtenir un texte ultra-gras en SVG sans dépendre de polices spécifiques :

```svg
<text stroke="#000000" stroke-width="4" paint-order="stroke">A</text>
```

Cette technique est plus fiable que `font-weight="900"` qui dépend de la disponibilité des polices sur le système.

### Architecture : Anticipation de l'évolution

La refactorisation pour créer un conteneur `.external-links` générique (au lieu de classes spécifiques à Babelio) permet :
- Ajout facile de nouvelles icônes
- Maintenance simplifiée (styles partagés)
- Évolutivité sans dette technique

**Principe** : Quand on ajoute un deuxième élément similaire au premier, c'est le moment de généraliser la structure.
