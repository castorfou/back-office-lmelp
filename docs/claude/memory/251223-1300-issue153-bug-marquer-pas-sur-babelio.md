# Issue #153 - Fix bug "Pas sur Babelio" pour type livre_auteur_groupe

**Date**: 2025-12-23 13:00
**Issue**: #153 - [bug] si livre pas sur babelio, erreur de traitement
**Type**: Bug Fix
**Complexité**: Simple (normalisation de type)

## 🎯 Problème

Lorsqu'un utilisateur clique sur le bouton "Pas sur Babelio" pour un cas de type `livre_auteur_groupe` dans la page de migration Babelio, une erreur se produit et rien ne se passe.

### Symptômes observés

- Page: `/babelio-migration`
- Action: Clic sur "✗ Pas sur Babelio" pour un cas groupé (livre + auteur)
- Résultat: Erreur backend et échec du marquage

## 🔍 Cause racine

**Fichier problématique**: `frontend/src/views/BabelioMigration.vue:512`

```javascript
// ❌ Code bugué (ligne 512)
const itemType = cas.type || 'livre';
```

**Problème**:
- Pour un cas `type='livre_auteur_groupe'`, la variable `itemType` devient `'livre_auteur_groupe'`
- Ce type est ensuite envoyé au backend via l'API `POST /api/babelio-migration/mark-not-found`
- Le backend (`babelio_migration_service.py:358-368`) ne reconnaît que deux types:
  - `'livre'`
  - `'auteur'`
- Pour tout autre type, le service retourne `False` (ligne 368)
- L'endpoint retourne alors une erreur 404

**Chaîne de l'erreur**:
1. Frontend `BabelioMigration.vue:512` → envoie `item_type='livre_auteur_groupe'`
2. Backend `app.py:1762` → reçoit la requête
3. Service `babelio_migration_service.py:334-391` → rejette le type invalide
4. Retour erreur 404 → Frontend affiche l'erreur

## ✅ Solution implémentée

### Normalisation du type dans le frontend

**Fichier**: `frontend/src/views/BabelioMigration.vue:513`

```javascript
// ✅ Code corrigé (ligne 513)
// Issue #153: Normaliser 'livre_auteur_groupe' vers 'livre' pour le backend
const itemType = cas.type === 'auteur' ? 'auteur' : 'livre';
```

**Logique**:
- Si `cas.type === 'auteur'` → envoyer `item_type='auteur'`
- Pour tous les autres types (`'livre'`, `'livre_auteur_groupe'`) → envoyer `item_type='livre'`

**Justification**:
- Un cas `livre_auteur_groupe` représente un **livre** et son auteur associé
- Marquer comme "Pas sur Babelio" s'applique au **livre** (et implicitement à l'auteur)
- Le backend traite correctement `item_type='livre'` pour ce scénario

## 🧪 Tests ajoutés

### Tests frontend

**Nouveau fichier**: `frontend/tests/unit/babelioMarkNotFound.spec.js` (175 lignes)

**4 tests TDD créés**:

1. **Test RED → GREEN**: `should send item_type="livre" for livre_auteur_groupe type`
   - Vérifie que pour un cas `type='livre_auteur_groupe'`
   - L'appel axios envoie `item_type='livre'` (pas `'livre_auteur_groupe'`)
   - ✅ **Statut**: PASSED

2. **Test de non-régression**: `should send item_type="livre" for livre type`
   - Vérifie que les cas `type='livre'` continuent de fonctionner
   - ✅ **Statut**: PASSED

3. **Test de non-régression**: `should send item_type="auteur" for auteur type`
   - Vérifie que les cas `type='auteur'` continuent de fonctionner
   - ✅ **Statut**: PASSED

4. **Test de gestion d'erreur**: `should handle errors gracefully`
   - Vérifie que les erreurs backend sont affichées via toast
   - ✅ **Statut**: PASSED

### Tests backend

**Fichier modifié**: `tests/test_mark_not_found_endpoint.py:148-180`

**1 nouveau test ajouté**:

```python
def test_should_reject_invalid_item_type(self, client):
    """Test TDD: Le backend doit rejeter les types invalides comme 'livre_auteur_groupe'."""
```

- Vérifie que le backend retourne 404 pour `item_type='livre_auteur_groupe'`
- Confirme que seuls `'livre'` et `'auteur'` sont acceptés
- ✅ **Statut**: PASSED

## 📊 Résultats des validations

### Tests

- ✅ **Backend**: 5/5 tests passent (dont 1 nouveau)
- ✅ **Frontend**: 365/365 tests passent (dont 4 nouveaux)
- ✅ **Total nouveaux tests**: 5 tests TDD

### Qualité du code

- ✅ **Ruff lint**: Aucune erreur
- ✅ **MyPy typecheck**: Success (29 fichiers)

### Validation utilisateur

- ✅ **Test manuel**: Confirmé par l'utilisateur - "parfait ca a marche"

## 🎓 Apprentissages clés

### 1. Normalisation des types pour compatibilité API

**Principe**: Toujours normaliser les types métier côté client avant l'envoi au backend.

**Mauvaise pratique**:
```javascript
// ❌ Envoyer directement le type métier
const itemType = cas.type; // Peut être 'livre_auteur_groupe'
```

**Bonne pratique**:
```javascript
// ✅ Mapper vers les types acceptés par l'API
const itemType = cas.type === 'auteur' ? 'auteur' : 'livre';
```

**Pourquoi**:
- Le frontend peut avoir des types métier plus granulaires (`livre_auteur_groupe`)
- Le backend a souvent une API plus générique (`livre` ou `auteur`)
- La normalisation évite les erreurs de communication

### 2. Tests TDD pour validation de types

**Pattern utilisé**:
1. **Test RED** (échoue d'abord): Vérifier que le type `livre_auteur_groupe` envoie bien `'livre'`
2. **Implémentation**: Modifier la ligne 513 pour normaliser le type
3. **Test GREEN** (passe): Le test passe après la correction

**Exemple de test RED qui échoue**:
```javascript
// Attendu: item_type: 'livre'
// Reçu: item_type: 'livre_auteur_groupe' ❌
expect(axios.post).toHaveBeenCalledWith(
  '/api/babelio-migration/mark-not-found',
  expect.objectContaining({
    item_type: 'livre'  // FAIL avant le fix
  })
)
```

### 3. Gestion des types dans une architecture full-stack

**Constat**:
- Frontend: Peut avoir 3+ types métier (`livre`, `auteur`, `livre_auteur_groupe`)
- Backend: API générique avec 2 types (`livre`, `auteur`)

**Solution de design**:
- Option A (choisie): Normaliser côté frontend avant l'appel API
- Option B (alternative): Backend accepte tous les types et normalise en interne
- Option C (évitée): Étendre l'API backend pour accepter `livre_auteur_groupe`

**Justification du choix A**:
- ✅ Simplicité: Pas de changement backend
- ✅ Performance: Pas de logique supplémentaire côté serveur
- ✅ Séparation des préoccupations: Le frontend gère sa complexité métier
- ❌ Inconvénient: Duplication si plusieurs clients frontend

### 4. Documentation des cas limites

**Pattern de commentaire utilisé**:
```javascript
// Issue #153: Normaliser 'livre_auteur_groupe' vers 'livre' pour le backend
const itemType = cas.type === 'auteur' ? 'auteur' : 'livre';
```

**Éléments clés**:
- ✅ Référence à l'issue pour traçabilité
- ✅ Explication du "pourquoi" (normalisation pour compatibilité)
- ✅ Concis (1 ligne de commentaire pour 1 ligne de code)

## 📁 Fichiers modifiés

### Code source

1. **`frontend/src/views/BabelioMigration.vue`**
   - Ligne 513: Normalisation du type `livre_auteur_groupe` → `livre`
   - Impact: Fix du bug de marquage "Pas sur Babelio"

### Tests

2. **`frontend/tests/unit/babelioMarkNotFound.spec.js`** (NOUVEAU)
   - 175 lignes
   - 4 tests TDD pour validation de la normalisation des types

3. **`tests/test_mark_not_found_endpoint.py`**
   - Lignes 148-180: Nouveau test pour rejeter les types invalides
   - Confirme le comportement backend attendu

## 🔗 Références

- **Issue GitHub**: #153
- **Pull Request**: (à créer)
- **Documentation backend**: `src/back_office_lmelp/services/babelio_migration_service.py:334-391`
- **Endpoint API**: `POST /api/babelio-migration/mark-not-found`

## 📋 Checklist de déploiement

- ✅ Tests backend passent (5/5)
- ✅ Tests frontend passent (365/365)
- ✅ Ruff lint OK
- ✅ MyPy typecheck OK
- ✅ Test manuel validé par utilisateur
- ⏳ Documentation mise à jour (en cours)
- ⏳ Commit et push
- ⏳ CI/CD validation
- ⏳ Pull Request créée

## 🎯 Impact

**Bugs corrigés**: 1 (erreur lors du marquage "Pas sur Babelio" pour les cas groupés)

**Utilisateurs impactés**: Tous les utilisateurs de la fonctionnalité de migration Babelio

**Compatibilité**:
- ✅ Rétrocompatible: Les cas `livre` et `auteur` fonctionnent toujours
- ✅ Pas de changement d'API backend
- ✅ Pas de migration de données nécessaire
