# Tests de Validation Bibliographique - Architecture et Hiérarchie

## Vue d'ensemble

La validation bibliographique (auteur-titre) dans l'application suit une architecture en couches testée à 4 niveaux distincts, du plus haut niveau (interface utilisateur) au plus bas niveau (services de base).

## Hiérarchie des Tests (du plus haut au plus bas niveau)

### Niveau 1 - Interface Utilisateur
**Fichier :** `tests/integration/LivresAuteurs.test.js`
**Responsabilité :** Vérifier que l'interface `/livres-auteurs` affiche correctement la colonne "Validation Babelio"
**Tests :**
- Affichage de la colonne "Validation Babelio" dans le tableau
- Utilisation du bon composant `BiblioValidationCell` avec les bonnes props

### Niveau 2 - Composant d'Affichage
**Fichier :** `tests/unit/BiblioValidationCell.test.js`
**Responsabilité :** Vérifier que le composant affiche les bons indicateurs visuels selon le résultat de validation
**Tests :**
- ✅ **Validé** : Quand `status: 'validated'`
- 🔄 **Suggestion** : Quand `status: 'suggestion'` avec affichage original → suggéré
- ❓ **Non trouvé** : Quand `status: 'not_found'`
- ⚠️ **Erreur** : Gestion des erreurs avec bouton retry
- **Cas réels** : Caroline Dussain → Caroline du Saint, Alain Mabancou → Alain Mabanckou

### Niveau 3 - Logique Métier
**Fichier :** `tests/unit/BiblioValidationService.test.js`
**Responsabilité :** Vérifier que le service retourne les bons statuts selon la logique d'arbitrage
**Tests :**
- **Ground truth priority** : Priorité aux suggestions d'épisodes quand disponibles
- **Direct validation** : `validated` quand original = suggestions Babelio
- **Babelio suggestions** : `suggestion` quand Babelio propose des corrections
- **Conflicting sources** : Arbitrage entre ground truth et Babelio
- **Not found** : `not_found` quand aucune source ne trouve de match fiable
- **Cas réels** : Logique complète Caroline Dussain, Alain Mabancou

### Niveau 4 - Services de Base (Backend, non testés en frontend)
**Services :**
- `babelioService.verifyAuthor(name)` → Vérification auteur via API Babelio
- `babelioService.verifyBook(title, author)` → Vérification livre via API Babelio
- `fuzzySearchService.searchEpisode(episodeId, {author, title})` → Recherche ground truth

## Principe de Mocking par Niveau

**Chaque niveau mocke le niveau inférieur pour tester sa propre logique isolément :**

1. **LivresAuteurs** mocke → `BiblioValidationCell` (vérifie juste l'intégration)
2. **BiblioValidationCell** mocke → `BiblioValidationService.validateBiblio()`
3. **BiblioValidationService** mocke → `babelioService.verifyAuthor/verifyBook()` + `fuzzySearchService.searchEpisode()`
4. **Services backend** → Tests backend séparés (non couverts ici)

## Logique de Validation (Statuts de Retour)

### ✅ `validated`
**Critère :** Les données originales de `/livres-auteurs` sont exactement identiques aux retours Babelio
**Exemple :** `Christophe Bigot - Un autre Matin ailleurs` → Aucune modification nécessaire

### 🔄 `suggestion`
**Critère :** Le système propose une modification basée sur ground truth et/ou Babelio
**Exemples :**
- `Caroline Dussain - Un déni français` → `Caroline du Saint - Un Déni français - Enquête sur l'élevage industrie...`
- `Alain Mabancou - Ramsès de Paris` → `Alain Mabanckou - Ramsès de Paris`

### ❓ `not_found`
**Critère :** Le système ne peut pas proposer de suggestion fiable
**Exemple :** `Agnès Michaud - Huitsemences vivantes` → Aucune correspondance fiable trouvée

## Architecture de Décision

```
Input: Auteur + Titre (+ Publisher + EpisodeId optionnel)
    ↓
1. Ground Truth Search (si episodeId fourni)
    ↓
2. Babelio Author Verification
    ↓
3. Babelio Book Verification (avec auteur original ou suggéré)
    ↓
4. Arbitrage Intelligent:
   - Priorité ground truth validé par Babelio
   - Sinon validation directe si identique
   - Sinon suggestion Babelio
   - Sinon not_found
```

## Cas de Tests Critiques

### Caroline Dussain (Cascade de suggestions)
1. `verifyAuthor('Caroline Dussain')` → suggère `Caroline Dawson`
2. `verifyBook('Un déni français', 'Caroline Dawson')` → suggère `Caroline du Saint` + titre complet
3. **Résultat final :** `Caroline du Saint - Un Déni français - Enquête sur l'élevage industrie...`

### Alain Mabancou (Suggestion simple)
1. `verifyAuthor('Alain Mabancou')` → suggère `Alain Mabanckou` (status: verified)
2. `verifyBook('Ramsès de Paris', 'Alain Mabanckou')` → confirmé identique
3. **Résultat final :** `Alain Mabanckou - Ramsès de Paris` (juste l'auteur corrigé)

Ces cas tests garantissent que la logique d'arbitrage fonctionne correctement dans les scénarios complexes.
