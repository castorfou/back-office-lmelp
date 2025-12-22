# Issue #150 - RadioFrance URL date filtering implementation

**Date**: 2025-12-22
**Issue**: [#150](https://github.com/castorfou/back-office-lmelp/issues/150)
**Status**: ✅ Résolu
**Type**: Bug fix + Enhancement

## 📋 Résumé

Fix du bug où la recherche RadioFrance retournait des URLs avec des dates incorrectes. L'épisode du 24/04/2022 retournait une URL d'un épisode du 26/10/2025.

**Root cause**: Deux bugs combinés:
1. La validation d'URL rejetait les URLs sans date dans le slug (comme `les-nouveaux-ouvrages-...-4010930`)
2. L'endpoint ne transmettait pas la date de l'épisode au service de recherche pour filtrer par date

## 🎯 Implémentation

### 1. Filtrage par date dans RadioFranceService

**Fichier**: `src/back_office_lmelp/services/radiofrance_service.py`

**Modifications**:
- Ajout paramètre `episode_date: str | None` à `search_episode_page_url()` (ligne 30-32)
- Stratégie de filtrage par date (lignes 67-93):
  1. Extraire toutes les URLs candidates depuis la page de recherche
  2. Parcourir chaque URL et extraire sa date depuis le JSON-LD
  3. Retourner la première URL dont la date correspond

**Méthodes ajoutées**:
- `_extract_all_candidate_urls()` (lignes 216-266): Extrait toutes les URLs candidates (JSON-LD ItemList + fallback HTML)
- `_extract_episode_date()` (lignes 268-322): Extrait la date depuis une page épisode RadioFrance (JSON-LD datePublished)

### 2. Transmission de la date depuis l'endpoint

**Fichier**: `src/back_office_lmelp/app.py:482-494`

**Modifications**:
- Extraction de `episode_data.get("date")` depuis MongoDB
- **CRITIQUE**: MongoDB retourne `datetime.datetime`, PAS une string ISO
- Conversion en format `YYYY-MM-DD` avec `.strftime()` si `datetime`, sinon parsing string
- Transmission de la date au `RadioFranceService`

```python
# MongoDB retourne datetime.datetime → convertir en "YYYY-MM-DD"
if isinstance(episode_date_raw, datetime):
    episode_date = episode_date_raw.strftime("%Y-%m-%d")
else:
    # Fallback si string (ne devrait pas arriver avec vraie DB)
    date_str = str(episode_date_raw)
    episode_date = date_str.split("T")[0].split(" ")[0]
```

### 3. Fix validation URL (Bug secondaire)

**Fichier**: `src/back_office_lmelp/services/radiofrance_service.py:107-115`

**Problème**: La validation cherchait `-du-` OU mois français dans l'URL, rejetant les URLs sans date dans le slug.

**Solution**: Validation basée sur l'ID numérique final:
```python
import re
return bool(re.search(r"-\d{4,}$", url))
```

**Exemples d'URLs valides**:
- `/le-masque-et-la-plume-du-dimanche-10-decembre-2023-5870209` (avec date)
- `/les-nouveaux-ouvrages-de-francois-truffaut-joel-dicker-...-4010930` (sans date)

## 🧪 Tests

### Tests unitaires

**Fichier**: `tests/test_radiofrance_service.py`

**Nouveau test** (lignes 217-238):
```python
def test_is_valid_episode_url_should_accept_urls_without_date_in_slug(
    self, radiofrance_service
):
    """RED TEST - Issue #150: _is_valid_episode_url devrait accepter les URLs sans date dans le slug."""
    url_without_date_in_slug = "https://www.radiofrance.fr/franceinter/podcasts/le-masque-et-la-plume/les-nouveaux-ouvrages-de-francois-truffaut-joel-dicker-jean-philippe-toussaint-paule-constant-4010930"

    result = radiofrance_service._is_valid_episode_url(url_without_date_in_slug)

    assert result is True, (
        "L'URL d'épisode avec ID numérique 4010930 devrait être valide même sans date dans le slug"
    )
```

**Test endpoint** (`tests/test_api_episodes_radiofrance.py:140-189`):
```python
def test_fetch_episode_page_url_should_pass_date_to_service_issue_150(self, client):
    """RED TEST - Issue #150: L'endpoint doit transmettre la date au RadioFranceService."""
    # Mock episode avec datetime.datetime (type réel MongoDB)
    mock_episode = {
        "_id": episode_id,
        "titre": episode_title,
        "date": datetime(2022, 4, 24),  # Type réel MongoDB
        "emission": "Le Masque et la Plume",
    }

    # Vérifier que search_episode_page_url est appelé avec titre ET date
    mock_search.assert_called_once_with(episode_title, episode_date)
```

**Résultats**:
- ✅ 10 tests passent (1 skipped - complexité mocks)
- ✅ Tous les tests RadioFrance et API passent

### Test en environnement réel

**Épisode testé**: `678ccedda414f22988778163` (24/04/2022)

**Résultat**:
```json
{
  "episode_id": "678ccedda414f22988778163",
  "episode_page_url": "https://www.radiofrance.fr/franceinter/podcasts/le-masque-et-la-plume/les-nouveaux-ouvrages-de-francois-truffaut-joel-dicker-jean-philippe-toussaint-paule-constant-4010930",
  "success": true
}
```

✅ Date extraite depuis la page: `2022-04-24` → **CORRECT**

## 🔍 Validation des URLs existantes

### Script de validation temporaire

**Script créé puis supprimé**: `scripts/validate_episode_urls.py`

**Fonctionnalités** (script utilisé puis retiré pour éviter code mort):
- Récupérait tous les épisodes avec `episode_page_url` (47 épisodes)
- Extrayait la date depuis chaque page RadioFrance
- Comparait avec la date de l'épisode en base
- Affichait les URLs incorrectes avec commandes pour corriger

**Raison suppression**: Une fois la validation effectuée et les 3 URLs corrigées, le script n'était plus nécessaire. Conservé uniquement dans la mémoire pour référence future si besoin de re-valider.

### Résultats de la validation

**Première exécution** (avant corrections):
- ✅ 44 URLs correctes (93.6%)
- ❌ 1 URL incorrecte (date ne correspond pas)
- ⚠️ 2 erreurs (URL `/contact` au lieu de l'épisode - Bug #129)

**URLs corrigées**:
1. Episode `694835beb48d4df8f0bada3c` (2025-12-21): Date trouvée 2025-10-05 → Corrigé
2. Episode `678cceb8a414f2298877812f` (2022-12-11): URL `/contact` → Corrigé
3. Episode `678cce74a414f229887780cb` (2024-05-05): URL `/contact` → Corrigé

**Deuxième exécution** (après corrections):
```
✅ URLs correctes: 47
❌ URLs incorrectes: 0
⚠️  Erreurs: 0

✅ Toutes les URLs sont correctes!
```

## 📚 Apprentissages critiques

### 1. Types MongoDB vs Mocks

**CRITIQUE**: MongoDB retourne des objets `datetime.datetime`, PAS des strings ISO.

**Problème rencontré**:
```python
# ❌ MAUVAIS - Mock avec string (ne correspond pas au type réel)
mock_episode = {
    "date": "2022-04-24T00:00:00"
}

# Erreur runtime: TypeError: argument of type 'datetime.datetime' is not iterable
# Car le code fait: if "T" in episode_date_raw
```

**Solution**:
```python
# ✅ BON - Mock avec datetime.datetime (type réel MongoDB)
from datetime import datetime

mock_episode = {
    "date": datetime(2022, 4, 24)
}
```

**Documentation ajoutée** dans `CLAUDE.md:195-201`:
```markdown
3. **CRITICAL: Use real data types in mocks** - Match exact types from source systems (Issue #150)
   - ❌ BAD: `mock_episode = {"date": "2022-04-24T00:00:00"}` (string, but MongoDB returns datetime)
   - ✅ GOOD: `mock_episode = {"date": datetime(2022, 4, 24)}` (actual MongoDB type)
   - **Why critical**: Type mismatches cause runtime errors that tests don't catch
   - **How to verify**: Use MCP tools or curl to inspect real data types BEFORE writing mocks
```

### 2. Validation d'URL trop restrictive

**Erreur**: Validation basée sur pattern d'URL (présence de date dans le slug)

**Problème**: Certains épisodes RadioFrance ont des slugs descriptifs sans date:
- `/les-nouveaux-ouvrages-de-francois-truffaut-joel-dicker-...-4010930`

**Solution**: Validation basée sur l'ID numérique final (pattern `r"-\d{4,}$"`)

**Leçon**: Préférer les invariants structurels aux patterns de contenu pour la validation.

### 3. TDD avec données réelles

**Approche suivie**:
1. Télécharger la vraie page de recherche RadioFrance (277KB)
2. Sauvegarder comme fixture: `tests/fixtures/radiofrance/search_joel_dicker_2022.html`
3. Créer RED test avec fixture réelle
4. Implémenter fix → GREEN

**Éviter**: Inventer des fixtures fictives qui ne correspondent pas à la structure réelle.

### 4. Approche itérative pour debugging

**Problème initial**: "No episode page URL found matching date 2022-04-24"

**Étapes de résolution**:
1. Ajout logs debug pour comprendre le flux
2. Découverte: 10 URLs candidates vérifiées, aucune de 2022
3. Hypothèse: URLs 2022 filtrées avant vérification de date
4. Téléchargement page réelle → confirmation URL présente
5. Analyse code validation → découverte du bug

**Leçon**: Utiliser des logs temporaires pour comprendre le flux avant de corriger.

### 5. Code mort et maintenance

**Pratique appliquée**: Suppression du script `validate_episode_urls.py` après utilisation.

**Raison**:
- Script créé pour une tâche ponctuelle (validation initiale)
- Tâche accomplie (47 URLs validées et corrigées)
- Pas de besoin récurrent identifié
- Documentation de l'approche conservée dans mémoire pour référence future

**Leçon**: Ne pas conserver du code "au cas où". Si besoin futur, le script peut être recréé à partir de cette documentation.

## 📊 Métriques

- **Tests**: 10 passed, 1 skipped
- **URLs validées**: 47/47 (100%)
- **URLs corrigées**: 3 (dont 2 bug #129 découverts rétroactivement)
- **Fichiers modifiés**: 5
- **Fichiers créés**: 3 (fixtures HTML)
- **Lignes de code**: ~200 lignes ajoutées
- **Tests ajoutés**: 2 tests RED/GREEN

## 🔗 Fichiers modifiés

### Code source
- `src/back_office_lmelp/services/radiofrance_service.py`: Filtrage par date + validation URL
- `src/back_office_lmelp/app.py`: Transmission date à RadioFranceService

### Tests
- `tests/test_radiofrance_service.py`: Test validation URL sans date dans slug
- `tests/test_api_episodes_radiofrance.py`: Test transmission date à service

### Fixtures
- `tests/fixtures/radiofrance/search_joel_dicker_2022.html`: Page recherche réelle (277KB) - NOUVEAU
- `tests/fixtures/radiofrance/episode_2022_04_24.html`: Page épisode 2022 - NOUVEAU
- `tests/fixtures/radiofrance/episode_2025_10_26.html`: Page épisode 2025 - EXISTANT

### Documentation
- `CLAUDE.md`: Ajout règle critique sur types MongoDB vs mocks (Rule #3)

## 🎓 Best practices renforcées

1. **Toujours vérifier les types réels** des données avant de créer des mocks
2. **Utiliser MCP tools** (`mcp__MongoDB__find`) pour inspecter les types MongoDB
3. **Télécharger des fixtures réelles** plutôt que d'inventer des structures
4. **Valider par invariants structurels** (ID numérique) plutôt que par patterns de contenu
5. **Créer des scripts de validation temporaires** pour tâches ponctuelles, puis les supprimer
6. **Documenter les erreurs critiques** immédiatement pour éviter répétition
7. **Supprimer le code mort** après utilisation (scripts ponctuels, code temporaire)

## ✅ Validation finale

- [x] Issue #150 résolu: Episode 24/04/2022 retourne la bonne URL
- [x] 47/47 URLs validées et corrigées
- [x] Tests unitaires et intégration passent
- [x] Lint et typecheck OK
- [x] Documentation CLAUDE.md mise à jour
- [x] 3 URLs incorrectes détectées et corrigées rétroactivement
- [x] Script de validation utilisé puis supprimé (pas de code mort)
