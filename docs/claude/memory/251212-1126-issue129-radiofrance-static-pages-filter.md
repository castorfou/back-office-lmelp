# Issue #129 - Filtrage des Pages Statiques RadioFrance et Correction Episode Model

**Date**: 2025-12-12
**Issue**: #129 - Bug lien vers épisode du 10 déc 2023 cassé
**Branch**: `129-bug-lien-vers-episode-du-10-dec-2023-cassé`
**Commits**: `5d57e52`, `e91c4f3`

## Contexte

Un utilisateur a signalé que le lien vers l'épisode du 10 décembre 2023 redirige vers `/contact` au lieu de la vraie page de l'épisode RadioFrance.

**Investigation initiale** :
- Le service RadioFrance retournait `/contact` comme URL valide
- Aucune validation des URLs dans `_parse_json_ld()` et `_parse_html_links()`
- Le lien `/contact` apparaissait en premier dans les résultats de recherche

## Problèmes Découverts

### Bug #1: RadioFrance Service - Pages Statiques Acceptées

**Symptôme** : Le service retournait `/contact`, `/a-propos` comme URLs valides d'épisodes.

**Cause Racine** :
- `_parse_json_ld()` prenait le premier résultat sans validation
- `_parse_html_links()` ne vérifiait pas si l'URL est un épisode réel
- Aucun filtrage des pages statiques

### Bug #2: Episode Model - Champ `episode_page_url` Manquant

**Découverte pendant les tests utilisateur** :
- Frontend affichait toujours `undefined` pour `episode_page_url`
- Cela causait des re-fetch inutiles à chaque affichage
- URL existait en base MongoDB mais n'était pas retournée par l'API

**Cause Racine** :
- Le champ `episode_page_url` était bien en MongoDB
- Mais `Episode.to_dict()` ne le retournait pas dans la réponse API
- Frontend voyait toujours `undefined` → nouveau fetch systématique

## Solutions Implémentées

### 1. RadioFrance Service - Validation des URLs

**Fichier** : `src/back_office_lmelp/services/radiofrance_service.py`

**Nouvelle méthode** :
```python
def _is_valid_episode_url(self, url: str) -> bool:
    """Vérifie qu'une URL est bien un épisode valide et pas une page statique."""
    # Liste des pages statiques à exclure
    static_pages = ["/contact", "/a-propos", "/rss", "/feed"]

    for static_page in static_pages:
        if url.endswith(static_page):
            return False

    # Vérifier patterns d'épisode valide
    return "-du-" in url or any(month in url for month in [
        "janvier", "fevrier", "mars", "avril", "mai", "juin",
        "juillet", "aout", "septembre", "octobre", "novembre", "decembre"
    ])
```

**Modifications** :
- `_parse_json_ld()` : Itère sur TOUS les résultats + valide chaque URL
- `_parse_html_links()` : Ajoute validation avec `_is_valid_episode_url()`

### 2. Episode Model - Ajout du Champ

**Fichier** : `src/back_office_lmelp/models/episode.py`

**Changements** :
```python
# Dans __init__
self.episode_page_url: str | None = data.get("episode_page_url")

# Dans to_dict()
return {
    # ... autres champs ...
    "episode_page_url": self.episode_page_url,
}
```

## Tests Créés

### Test RadioFrance - RED Test avec Fixture

**Fichier** : `tests/test_radiofrance_service.py`

```python
async def test_search_episode_should_skip_contact_page(self, radiofrance_service):
    """RED TEST - Issue #129: devrait ignorer le lien /contact dans les résultats."""
    fixture_path = FIXTURES_DIR / "search_with_contact_link.html"
    # ... load HTML avec /contact en premier résultat

    result = await radiofrance_service.search_episode_page_url(episode_title)

    assert result is not None
    assert "/contact" not in result
    assert "le-masque-et-la-plume-du-dimanche-10-decembre-2023" in result
```

**Fixture** : `tests/fixtures/radiofrance/search_with_contact_link.html`
- HTML réel capturé avec `/contact` en position 1
- Épisode réel en position 2

### Test Episode Model

**Fichier** : `tests/test_episode_model.py` (nouveau)

```python
def test_episode_to_dict_should_include_episode_page_url(self):
    """RED TEST - Issue #129: to_dict() devrait inclure episode_page_url."""
    episode_data = {
        "_id": "507f1f77bcf86cd799439011",
        "episode_page_url": "https://www.radiofrance.fr/.../",
    }
    episode = Episode(episode_data)
    result = episode.to_dict()

    assert "episode_page_url" in result
    assert result["episode_page_url"] == episode_data["episode_page_url"]
```

### Tests de Régression Mis à Jour

**Fichier** : `tests/test_models_validation.py`

**Problème** : Tests échouaient en CI car attendaient un ordre spécifique de champs sans `episode_page_url`

**Correction** : Ajout de `"episode_page_url": None` dans les dictionnaires `expected` :
- `test_episode_to_dict_full_data`
- `test_episode_to_dict_minimal_data`

## Processus de Debugging

### Investigation du Cache

**Question utilisateur** : "Comment se fait-il que l'URL soit recalculée si elle existe en base ?"

**Hypothèse initiale** : Backend ne vérifie pas le cache

**Méthode de vérification** :
1. Ajout de logs debug dans frontend et backend
2. Vérification de la réponse API réelle
3. Découverte : `episode_page_url` = `undefined` côté frontend

**Logs ajoutés temporairement** :
```javascript
// Frontend
console.log('[DEBUG #129] episode_page_url:', this.selectedEpisodeFull.episode_page_url);
console.log('[DEBUG #129] ✅ Cache hit - URL déjà présente');
```

```python
# Backend
logger.info(f"[DEBUG #129] Episode {episode_id} - episode_page_url in DB: {...}")
```

**Résultat** :
- Frontend : `episode_page_url: undefined`
- Backend : URL existe en base mais pas retournée par API
- → Découverte du Bug #2

**Validation cache fonctionne** :
```
[DEBUG #129] episode_page_url: https://www.radiofrance.fr/...
[DEBUG #129] Condition (!episode_page_url): false
[DEBUG #129] ✅ Cache hit - URL déjà présente
```

→ Logs retirés après validation

## Apprentissages Techniques

### 1. TDD Incrémental sur Bug Découvert Pendant Tests

**Situation** : Bug #2 découvert pendant validation manuelle du Bug #1

**Approche TDD** :
1. User testing révèle comportement inattendu (re-fetch systématique)
2. Investigation avec logs → identification cause racine
3. RED test écrit d'abord (`test_episode_to_dict_should_include_episode_page_url`)
4. Implémentation minimale (ajout champ)
5. GREEN test + validation manuelle
6. Nettoyage des logs

**Leçon** : Même pour des bugs découverts en cours de route, toujours suivre TDD :
- RED test d'abord
- Validation que le test ÉCHOUE pour la bonne raison
- Implémentation
- Validation GREEN

### 2. Tests de Régression - Ordre des Champs en Python

**Problème CI** :
```python
AssertionError: assert {'id': '...', 'episode_page_url': None}
                    == {'id': '...', 'masked': False}
```

**Cause** : Tests `test_models_validation.py` comparaient des dictionnaires complets
- Ajout de `episode_page_url` changeait la comparaison
- Python 3.7+ garantit l'ordre d'insertion des dict

**Solution** : Ajouter le nouveau champ dans les dictionnaires `expected` de TOUS les tests de validation

**Leçon** :
- Tests de validation stricte = bonne pratique pour détecter changements API
- Mais nécessitent mise à jour quand on ajoute des champs
- Alternative : tester seulement les champs critiques, pas tout le dict

### 3. Filtrage Multi-Stratégies

**Pattern appliqué** :
1. **Liste noire** : Pages statiques explicites (`/contact`, `/a-propos`)
2. **Liste blanche** : Patterns positifs (mois français, `-du-`)
3. **Combinaison** : `NOT static_pages AND (has_pattern OR has_month)`

**Avantage** :
- Robuste face aux changements HTML RadioFrance
- Facile à étendre (ajout nouvelles pages statiques)
- Explicite et testable

### 4. Fixture HTML Réelle vs Mock Inventé

**Approche** : Capture HTML réel de RadioFrance avec bug reproductible

**Avantages** :
- Test avec données réelles
- Reproduit exactement le bug en production
- Documente le problème pour futur

**Fichier** : `tests/fixtures/radiofrance/search_with_contact_link.html`
- JSON-LD avec `/contact` en position 1
- Épisode réel en position 2

### 5. Git - Éviter `git commit --amend` sur Commits Poussés

**Erreur commise** :
```bash
git commit -m "fix..."
# Pre-commit reformate
git commit --amend --no-edit  # ❌ MAUVAIS si déjà poussé
```

**Résultat** : Amend d'un commit déjà sur remote = réécriture d'historique

**Correction** :
```bash
git reset --soft HEAD@{1}  # Annuler l'amend
git commit -m "fix..."     # Nouveau commit propre
```

**Bonne pratique** :
- Vérifier `git log` avant amend
- Si commit déjà poussé → créer nouveau commit
- Amend seulement pour commits locaux

## Fichiers Modifiés

### Code Production
- `src/back_office_lmelp/services/radiofrance_service.py` - Ajout validation URLs
- `src/back_office_lmelp/models/episode.py` - Ajout champ `episode_page_url`

### Tests
- `tests/test_radiofrance_service.py` - Test RED pour filtrage pages statiques
- `tests/test_episode_model.py` - **Nouveau fichier** - Tests Episode model
- `tests/test_models_validation.py` - Mise à jour dictionnaires expected
- `tests/fixtures/radiofrance/search_with_contact_link.html` - **Nouveau fichier** - Fixture HTML

## Résultats

### Tests Locaux
- ✅ 7/7 tests RadioFrance passent
- ✅ 2/2 tests Episode model passent
- ✅ Tous tests de validation mis à jour

### CI/CD
- ✅ Run #1 (`5d57e52`) : Échec sur `test_models_validation.py`
- ✅ Run #2 (`e91c4f3`) : **Succès complet** (744 tests)
- ✅ Python 3.11 et 3.12
- ✅ Security, Frontend, Integration, Quality Gate

### Validation Utilisateur
- ✅ Lien épisode 10 déc 2023 fonctionne
- ✅ Cache fonctionne (pas de re-fetch inutile)
- ✅ Console logs montrent "Cache hit"

## Points à Retenir

1. **Validation des données externes** : Toujours valider les URLs/données scrappées
2. **Tests de régression complets** : Vérifier que tous les tests de validation sont à jour
3. **Debug méthodique** : Logs temporaires → Identification cause → TDD → Nettoyage
4. **Fixtures réelles** : Utiliser HTML réel capturé pour tests de scraping
5. **Git hygiene** : Jamais amend de commits déjà poussés
6. **TDD même sur bugs découverts** : RED test → Implementation → GREEN test
7. **Documentation du processus** : Logs de debugging documentent la pensée

## Prochaines Étapes

- [ ] Créer Pull Request
- [ ] Validation utilisateur finale
- [ ] Merge vers main
- [ ] Fermer issue #129
