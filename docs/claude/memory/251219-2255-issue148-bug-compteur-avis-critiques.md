# Issue #148 - Bug compteur "Avis critiques sans analyse" affichait 0 au lieu de 7

**Date**: 2025-12-19 22:55
**Issue**: #148
**Type**: Bug fix
**Branche**: `148-bug-stat-avis-critiques-sans-analyse`

## Problème identifié

Le compteur "Avis critiques sans analyse" dans le dashboard affichait **0** alors qu'il devrait afficher **7 épisodes**.

### Cause racine

Incohérence de types dans les collections MongoDB:
- Le champ `episode_oid` dans les collections `avis_critiques` et `livresauteurs_cache` est stocké comme **STRING** dans MongoDB
- Les `_id` de la collection `episodes` sont des **ObjectId**
- L'intersection de sets `episodes_with_avis & non_masked_episode_ids` retournait 0 éléments car les types ne matchaient pas (`str ≠ ObjectId`)

### Diagnostic

```python
# Découverte via tests MongoDB directs
Type de _id depuis find(): <class 'bson.objectid.ObjectId'>
Type de episode_oid depuis distinct(): <class 'str'>
ep_id_from_find == ep_id_from_distinct: False  # ❌ Pas de match!
```

Résultat: l'intersection des sets retournait toujours un ensemble vide, d'où le compteur à 0.

## Solution implémentée

Ajout de conversion explicite dans `src/back_office_lmelp/services/stats_service.py:174-195`:

```python
from bson import ObjectId

# Récupérer les épisodes distincts qui ont des avis critiques
# IMPORTANT (Issue #148): episode_oid est stocké comme STRING dans la base,
# on doit le convertir en ObjectId pour matcher avec les IDs de episodes.find()
episodes_with_avis = {
    ObjectId(ep_id) if isinstance(ep_id, str) else ep_id
    for ep_id in avis_critiques_collection.distinct("episode_oid")
    if ep_id is not None
}

# Même conversion pour les épisodes analysés
episodes_analyzed = {
    ObjectId(ep_id) if isinstance(ep_id, str) else ep_id
    for ep_id in cache_collection.distinct("episode_oid")
    if ep_id is not None
}
```

## Leçon critique - Mocks basés sur données réelles

**Règle CLAUDE.md**: *Create mocks from real API/MongoDB responses - NEVER invent mock structures*

### Problème initial
- Les mocks de tests utilisaient des `ObjectId` partout (inventés)
- La vraie base utilise des **strings** pour `episode_oid`
- Résultat: **tests passaient ✅ mais code réel échouait ❌**

### Solution appliquée
1. Récupération données réelles via `mcp__MongoDB__aggregate`
2. Découverte du type réel: `distinct("episode_oid")` retourne des **STRINGs**
3. Modification des mocks dans `tests/test_stats_service.py:456-492`:

```python
# IDs d'épisodes NON masqués - en ObjectId comme dans episodes.find()
non_masked_episode_ids = [ObjectId() for _ in range(100)]

# IDs d'épisodes avec avis - STOCKÉS COMME STRINGS (comme dans la vraie base!)
episodes_with_avis_str = [str(eid) for eid in non_masked_episode_ids[:69]]

# Mock retourne des STRINGS (comme dans la vraie base!)
mock_avis_critiques_collection.distinct = lambda field: episodes_with_avis_str + [...]
```

## Processus TDD appliqué

1. **Analyse réelle MongoDB** via MCP tools
2. **Découverte bug**: `distinct("episode_oid")` retourne STRINGs, pas ObjectId
3. **Phase RED**: Modification test avec mocks STRING → échec (attendu 7, obtenu 0)
4. **Implémentation**: Ajout conversion `ObjectId(ep_id) if isinstance(ep_id, str)`
5. **Phase GREEN**: Test passe ✅
6. **Validation**: 25 tests stats passent, linting OK, backend affiche 7 ✅

## Fichiers modifiés

- `src/back_office_lmelp/services/stats_service.py:174-195` - Ajout conversions ObjectId
- `tests/test_stats_service.py:441-500` - Nouveau test avec mocks STRING basés sur données réelles

## Résultat

Dashboard affiche maintenant correctement **7 épisodes** avec avis critiques sans analyse.

## Points d'attention futurs

1. **Toujours vérifier les types** retournés par `distinct()` dans MongoDB
2. **Ne jamais inventer** la structure des mocks - toujours copier depuis données réelles
3. **Documenter les incohérences** de types dans le schéma MongoDB (episode_oid stocké comme string)
