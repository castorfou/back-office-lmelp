# Issue #143 - Correction compteur "Avis critiques sans analyse"

**Date**: 2025-12-19
**Contexte**: Correction d'un bug dans le Dashboard où le compteur "Avis critiques sans analyse" incluait les épisodes masqués

## Problème identifié

Le compteur affichait **1** alors qu'il devrait afficher **0**, car il comptait un avis critique d'un épisode masqué :
- **Épisode masqué**: "Houris" de Kamel Daoud (26 août 2024)
- **Episode ID**: `678cce5da414f229887780ab`
- **Avis critique ID**: `686c4fdda028dcd690c5c140`
- **Statut**: `masked: true`

## Solution implémentée

### Approche TDD suivie

1. **RED Phase**: Test écrit vérifiant que les épisodes masqués sont exclus
2. **GREEN Phase**: Code modifié pour filtrer les avis critiques par épisodes non masqués
3. **Validation**: Tous les tests passent + lint + typecheck

### Modifications de code

**Fichier**: `src/back_office_lmelp/services/stats_service.py:147-181`

Ancienne logique (bugguée):
```python
def _count_avis_critiques_without_analysis(self) -> int:
    # ❌ Comptait TOUS les avis critiques sans filtrer par épisode masqué
    total_avis = avis_critiques_collection.count_documents({})
    analyzed_avis = cache_collection.distinct("avis_critique_id")
    analyzed_count = len([a for a in analyzed_avis if a is not None])
    return max(0, total_avis - analyzed_count)
```

Nouvelle logique (corrigée):
```python
def _count_avis_critiques_without_analysis(self) -> int:
    # ✅ Filtre les avis critiques par épisodes NON masqués
    episodes_collection = self.mongodb_service.get_collection("episodes")

    # Récupérer les IDs des épisodes NON masqués
    non_masked_episodes = episodes_collection.find(
        {"$or": [{"masked": False}, {"masked": {"$exists": False}}]},
        {"_id": 1}
    )
    non_masked_episode_ids = [ep["_id"] for ep in non_masked_episodes]

    # Compter uniquement les avis des épisodes non masqués
    total_avis = avis_critiques_collection.count_documents(
        {"episode_oid": {"$in": non_masked_episode_ids}}
    )

    analyzed_avis = cache_collection.distinct("avis_critique_id")
    analyzed_count = len([a for a in analyzed_avis if a is not None])
    return max(0, total_avis - analyzed_count)
```

### Pattern réutilisé

La solution suit le même pattern que `_count_episodes_without_avis_critiques()` (`stats_service.py:123-145`) :
- Filtrer d'abord les épisodes non masqués avec `{"$or": [{"masked": False}, {"masked": {"$exists": False}}]}`
- Récupérer leurs IDs
- Utiliser ces IDs pour filtrer la collection cible avec `{"episode_oid": {"$in": non_masked_episode_ids}}`

### Test unitaire ajouté

**Fichier**: `tests/test_stats_service.py:376-436`

```python
def test_count_avis_critiques_without_analysis_should_exclude_masked_episodes(self):
    """Le compteur doit exclure les avis critiques des épisodes masqués (Issue #143)."""
    non_masked_episode_id = ObjectId("678cce5da414f229887780aa")
    mock_episodes = [{"_id": non_masked_episode_id}]

    # Configuration des mocks avec pattern dictionary
    collection_map = {
        "episodes": mock_episodes_collection,
        "avis_critiques": mock_avis_critiques_collection,
        "livresauteurs_cache": mock_cache_collection,
    }

    # Vérifications:
    # 1. find() appelé avec filtre épisodes non masqués
    # 2. count_documents() filtre sur IDs d'épisodes non masqués
    # 3. Résultat = avis non masqués - avis analysés
```

## Points techniques clés

### Mock testing avec multiple collections

Lorsqu'un service utilise plusieurs collections MongoDB, utiliser un dictionnaire pour mapper les noms aux mocks :

```python
collection_map = {
    "episodes": mock_episodes_collection,
    "avis_critiques": mock_avis_critiques_collection,
    "livresauteurs_cache": mock_cache_collection,
}

def get_collection_side_effect(collection_name):
    return collection_map.get(collection_name)

mock_mongodb.get_collection.side_effect = get_collection_side_effect
```

**Avantages** :
- ✅ Évite les if/elif successifs (violation SIM116 ruff)
- ✅ Plus lisible et maintenable
- ✅ Retourne automatiquement None pour collections inconnues

### Cohérence des filtres MongoDB

**Pattern établi** pour filtrer les épisodes non masqués dans tout le projet :

```python
{"$or": [{"masked": False}, {"masked": {"$exists": False}}]}
```

Ce pattern gère deux cas :
1. `masked: False` - Épisode explicitement non masqué
2. `masked` n'existe pas - Anciens épisodes avant introduction du champ

**Utilisation** :
- `_count_episodes_without_avis_critiques()` - Stats épisodes sans avis
- `_count_avis_critiques_without_analysis()` - Stats avis critiques sans analyse

### TDD strict avec phase RED explicite

**Approche critique** :
1. Écrire le test AVANT le code
2. Vérifier que le test échoue (RED) pour la bonne raison
3. Implémenter le minimum de code pour passer au GREEN
4. Vérifier que tous les tests existants passent toujours

**Validation** :
```bash
# Phase RED - Test doit échouer
pytest tests/test_stats_service.py::TestStatsService::test_count_avis_critiques_without_analysis_should_exclude_masked_episodes -v
# Résultat: AssertionError: Expected 'find' to be called once. Called 0 times.

# Phase GREEN - Test doit passer
pytest tests/test_stats_service.py::TestStatsService::test_count_avis_critiques_without_analysis_should_exclude_masked_episodes -v
# Résultat: PASSED
```

## Validation complète

### Tests locaux
```bash
# Tous les tests (760 tests)
PYTHONPATH=/workspaces/back-office-lmelp/src pytest tests/ -v --cov=src
# Résultat: 760 passed

# Linting
ruff check . --output-format=github
# Résultat: No issues

# Type checking
mypy src/
# Résultat: Success: no issues found

# Documentation build
mkdocs build --strict
# Résultat: Documentation built in 4.99 seconds
```

### CI/CD GitHub Actions
Pipeline complet passé avec succès :
- ✅ Security scan (detect-secrets)
- ✅ Frontend tests (Vitest)
- ✅ Backend tests Python 3.11 et 3.12
- ✅ Integration tests
- ✅ Quality gate

## Impact utilisateur

**Avant** : Compteur affichait 1 (incorrect - incluait épisode masqué)
**Après** : Compteur affiche 0 (correct - exclut épisodes masqués)

Le Dashboard affiche maintenant des statistiques cohérentes avec le principe "les épisodes masqués n'apparaissent pas dans les compteurs à traiter".

## Références

- **Issue GitHub**: #143
- **Fichiers modifiés**:
  - `src/back_office_lmelp/services/stats_service.py` (lignes 147-181)
  - `tests/test_stats_service.py` (lignes 376-436)
- **Commit**: `a4d4c1b` - "fix(stats): Exclure les épisodes masqués du compteur 'Avis critiques sans analyse'"
- **Pattern similaire**: `_count_episodes_without_avis_critiques()` (lignes 123-145)

## Apprentissages

1. **Cohérence des filtres** : Réutiliser les mêmes patterns de filtrage MongoDB dans toute l'application
2. **Mock testing avancé** : Utiliser des dictionnaires pour mapper plusieurs collections
3. **TDD strict** : Toujours vérifier la phase RED avant d'implémenter
4. **Documentation du code** : Inclure les numéros d'issue dans les docstrings pour traçabilité
