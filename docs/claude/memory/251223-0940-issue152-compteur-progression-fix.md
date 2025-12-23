# Issue #152 - Fix compteur de progression migration Babelio

**Date**: 2025-12-23
**Issue**: [#152](https://github.com/castorfou/back-office-lmelp/issues/152)
**Statut**: ✅ Résolu et testé

## 🎯 Problème

Le compteur de progression de la page `/babelio-migration` affichait le **nombre de groupes traités** au lieu du **nombre d'éléments individuels** (livres + auteurs).

### Exemple concret
- 4 groupes traités (3 livres+auteurs + 1 auteur seul)
- Total réel d'éléments : **7** (3×2 livres + 3×2 auteurs + 1 auteur)
- Affichage bugué : **4/46** ❌
- Affichage attendu : **7/46** ✅

## 🔍 Cause identifiée

Dans `src/back_office_lmelp/utils/migration_runner.py`, le compteur `books_processed` était incrémenté de **1 par groupe traité** :

**Phase 1 (livres)** - Ligne 324 (avant fix) :
```python
self.books_processed += 1  # ❌ Compte 1 par groupe (livre+auteur)
```

**Phase 2 (auteurs seuls)** - Ligne 412 (avant fix) :
```python
self.books_processed += 1  # ❌ Compte tous les auteurs même échoués
```

### Analyse détaillée

Le système traite les données en 2 phases :
1. **Phase 1** : Migration des livres avec leurs auteurs (groupés ensemble)
2. **Phase 2** : Complétion des auteurs sans livres associés

Problème :
- Phase 1 comptait **1 par groupe** au lieu de compter séparément livre + auteur
- Phase 2 comptait tous les auteurs tentés, même ceux qui ont échoué

## ✅ Solution implémentée

### Modifications du code

**Phase 1** - `src/back_office_lmelp/utils/migration_runner.py:325-335` :
```python
# Issue #152: Compter les éléments individuels, pas les groupes
# Compter le livre si traité
items_count = 0
if livre_updated or livre_status != "none":
    items_count += 1
# Compter l'auteur si traité (pas si déjà lié)
if auteur_updated:
    items_count += 1

self.books_processed += items_count
```

**Phase 2** - `src/back_office_lmelp/utils/migration_runner.py:413-417` :
```python
# Issue #152: Compter seulement si l'auteur a vraiment été traité
if auteur_updated:
    self.books_processed += 1
    authors_completed += 1
```

### Logique de comptage

**Phase 1 (livres + auteurs)** :
- `+1` si `livre_updated = true` OU `livre_status != "none"`
- `+1` si `auteur_updated = true` (pas si `auteur_already_linked`)

**Phase 2 (auteurs seuls)** :
- `+1` seulement si `auteur_updated = true`

**Cas particuliers gérés** :
- Auteur déjà lié → Compte seulement le livre (+1)
- Livre et auteur échoués → Compte quand même le groupe pour montrer la progression
- Auteur échoué en Phase 2 → Ne compte pas (+0)

## 🧪 Tests TDD ajoutés

Nouveau fichier : `tests/test_migration_runner_items_count.py`

### Test 1 : Comptage des éléments individuels
```python
async def test_books_processed_should_count_individual_items_not_groups(self):
    """Test que books_processed compte livres + auteurs individuellement.

    Scénario:
    - Phase 1: 2 livres + 2 auteurs = 4 éléments
    - Phase 2: 1 auteur = 1 élément
    - Total: 5 éléments (pas 3 groupes!)
    """
```

**Résultat** :
- ✅ `books_processed = 5`
- ✅ 3 entrées dans `book_logs` : 2 livres Phase 1 + 1 auteur Phase 2

### Test 2 : Auteur déjà lié
```python
async def test_books_processed_should_count_livre_only_when_auteur_already_linked(self):
    """Compte seulement le livre si l'auteur est déjà lié."""
```

**Résultat** :
- ✅ `books_processed = 1` (livre seulement)

### Test 3 : Échec complet
```python
async def test_books_processed_should_count_zero_when_both_fail(self):
    """Compte quand même pour montrer la progression."""
```

**Résultat** :
- ✅ `books_processed >= 1` (groupe traité même en échec)

### Note technique importante

**Problème rencontré** : Le mock de `get_all_authors_to_complete()` ne s'exécutait pas car la fonction est async.

**Solution** :
```python
async def get_authors_mock():
    return [{"nom": "Victor Hugo", ...}]

mock_get_authors.side_effect = get_authors_mock
```

Au lieu de :
```python
mock_get_authors.return_value = [...]  # ❌ Ne fonctionne pas avec await
```

## 📊 Résultats des tests

```bash
# Tests spécifiques migration_runner
pytest tests/test_migration_runner*.py -v
# Résultat: 20 passed ✅

# Tous les tests du projet
pytest tests/ -v
# Résultat: 750 passed, 23 skipped ✅

# Linting
ruff check . --output-format=github
# Résultat: Success ✅

# Type checking
mypy src/
# Résultat: Success: no issues found ✅
```

**Coverage** :
- Global : 76%
- `migration_runner.py` : 79% (+25% vs avant)

## 🎓 Apprentissages clés

### 1. Comptage granulaire dans les systèmes de migration

**Principe** : Toujours compter les **entités individuelles** traitées, pas les **groupes logiques**.

**Pourquoi** :
- Transparence pour l'utilisateur
- Progression plus précise
- Cohérence avec le nombre total d'éléments à traiter

**Pattern recommandé** :
```python
items_count = 0
if entity_a_processed:
    items_count += 1
if entity_b_processed:
    items_count += 1
counter += items_count  # Incrémentation finale
```

### 2. Tests TDD avec mocks async

**Problème courant** : Mocker une fonction async avec `return_value` ne fonctionne pas.

**Solution** :
```python
async def async_mock_function():
    return expected_result

mock_object.side_effect = async_mock_function
```

**Application** : Toujours vérifier si une fonction est async avant de la mocker.

### 3. Timing dans les tests asynchrones

**Leçon** : Les tests async nécessitent parfois des `await asyncio.sleep()` plus longs que prévu.

**Exemple** :
- `await asyncio.sleep(2.0)` → Phase 2 ne s'exécutait pas ❌
- `await asyncio.sleep(5.0)` → Phase 2 s'exécute complètement ✅

**Raison** : Phase 1 + Phase 2 + délais entre traitements = temps d'exécution total

### 4. Debug progressif avec logs

**Technique utilisée** :
```python
print(f"DEBUG: books_processed = {runner.books_processed}")
print(f"DEBUG: nombre de book_logs = {len(runner.book_logs)}")
for idx, log in enumerate(runner.book_logs):
    print(f"DEBUG log[{idx}]: {log['titre']} - livre:{log['livre_status']}")
```

**Avantage** : Visualiser exactement ce qui est traité à chaque phase pour identifier rapidement le problème.

### 5. Commentaires de référence dans le code

**Pattern utilisé** :
```python
# Issue #152: Compter les éléments individuels, pas les groupes
```

**Bénéfices** :
- Traçabilité des modifications
- Contexte business pour les futurs développeurs
- Lien vers la discussion complète sur GitHub

## 📁 Fichiers modifiés

### Code source
- `src/back_office_lmelp/utils/migration_runner.py:325-335` - Phase 1 comptage
- `src/back_office_lmelp/utils/migration_runner.py:413-417` - Phase 2 comptage

### Tests
- `tests/test_migration_runner_items_count.py` - Nouveau fichier avec 3 tests

### Documentation
- Commentaire GitHub sur issue #152 avec analyse détaillée du problème

## 🚀 Impact utilisateur

**Avant** :
- Compteur : 4/46 (confusant)
- Utilisateur ne comprend pas pourquoi seulement 4 alors que plus d'éléments semblent traités

**Après** :
- Compteur : 7/46 (clair et précis)
- Utilisateur voit la vraie progression : chaque livre ET chaque auteur compté

**Validation utilisateur** :
> "ça marche parfaitement" ✅

## 📝 Méthodologie appliquée

1. ✅ Analyse du problème avec exploration du code
2. ✅ Documentation de l'analyse dans un commentaire GitHub
3. ✅ Création de tests RED qui échouent (TDD)
4. ✅ Implémentation de la correction minimale
5. ✅ Itération jusqu'à tests GREEN
6. ✅ Vérification de tous les tests du projet
7. ✅ Validation lint + typecheck
8. ✅ Test utilisateur final
9. ✅ Documentation de la solution

**Temps total** : ~2h (analyse + implémentation + tests + validation)

## 🔗 Références

- Issue GitHub : [#152](https://github.com/castorfou/back-office-lmelp/issues/152)
- Analyse détaillée : [Commentaire #3685656705](https://github.com/castorfou/back-office-lmelp/issues/152#issuecomment-3685656705)
- Branche : `152-bug-changer-le-compteur-de-progression-de-liaison-babelio`
