# Issue #89 - RadioFrance Episode Page URL Feature (Complet)

**Date**: 2025-11-08 18:20
**Issue**: [#89](https://github.com/castorfou/back-office-lmelp/issues/89) - Ajouter un lien vers la page de l'épisode
**Status**: ✅ Implémenté, testé, validé utilisateur
**Branch**: `89-ajouter-un-lien-vers-la-page-de-lepisode`

## Résumé de l'implémentation

Feature complète permettant d'afficher un logo RadioFrance cliquable dans les détails d'un épisode, avec auto-fetch automatique de l'URL de la page RadioFrance.

### Architecture mise en place

**Backend (Python/FastAPI)**:
- Service `RadioFranceService` pour scraper les URLs de page d'épisode
- Endpoint POST `/api/episodes/{episode_id}/fetch-page-url` (lignes 342-401 dans app.py)
- Deux stratégies de parsing: JSON-LD (Schema.org ItemList prioritaire) + fallback HTML
- Persistance de l'URL dans MongoDB (`episodes.episode_page_url`)
- Méthode générique `update_episode()` dans `mongodb_service.py`

**Frontend (Vue.js)**:
- Auto-fetch automatique quand épisode sélectionné sans URL
- Logo RadioFrance cliquable (80x80px, 22KB) téléchargé localement
- Layout horizontal pour économiser l'espace vertical
- Gestion gracieuse des erreurs (pas d'URL trouvée, erreur réseau)
- Pattern "lazy loading + persist" pour performance optimale

### Tests créés

**Backend** (6 tests):
- `test_radiofrance_service.py` (4 tests) - Service de scraping avec fixtures HTML réelles
- `test_api_episodes_radiofrance.py` (3 tests) - Endpoint API
  - Success: fetch réussi avec mise à jour en DB
  - Not found: titre introuvable sur RadioFrance (404)
  - Episode missing: episode_id inexistant en DB (404)
- Fixtures HTML réelles de RadioFrance (Issue #85 lesson appliquée)
  - `search_with_results.html` (276KB) - Capture du 2025-11-07
  - `search_no_results.html` (178KB) - Capture du 2025-11-07

**Frontend** (7 tests):
- `LivresAuteurs.episodePageUrl.test.js` (7 tests d'intégration TDD)
  - Auto-fetch appelé quand épisode sélectionné sans URL
  - selectedEpisodeFull mise à jour avec URL récupérée
  - Pas d'appel fetch si URL déjà présente
  - Gestion erreurs sans bloquer UI
  - Logo affiché avec URL présente
  - Logo absent sans URL
  - Logo affiché après auto-fetch réussi

**Total**: 504 tests backend + 264 tests frontend ✅

## Fichiers modifiés (13 fichiers, 1371 lignes)

### Backend
1. **src/back_office_lmelp/services/radiofrance_service.py** (+166 lignes)
   - Classe `RadioFranceService` avec dual parsing strategy
   - `search_episode_page_url()`: méthode async principale
   - `_parse_json_ld()`: parsing JSON-LD Schema.org ItemList (prioritaire)
   - `_parse_html_links()`: fallback HTML parsing
   - URL encoding avec `quote_plus()` (gestion accents/caractères spéciaux)

2. **src/back_office_lmelp/app.py** (+71 lignes, lignes 342-401)
   - Endpoint POST `/api/episodes/{episode_id}/fetch-page-url`
   - Architecture: Query MongoDB → Scrape RadioFrance → Persist URL → Return result
   - Response: `{episode_id, episode_page_url, success}`
   - Gestion erreurs: 404 si épisode non trouvé ou URL non trouvée

3. **src/back_office_lmelp/services/mongodb_service.py** (+24 lignes, -7 lignes)
   - **Nouveau**: Méthode générique `update_episode(episode_id, updates_dict)`
   - **Refactoring**: `update_episode_title()` utilise désormais la méthode générique
   - Factorisation du code pour réutilisabilité

### Frontend
4. **frontend/src/services/api.js** (+10 lignes)
   - Méthode `fetchEpisodePageUrl(episodeId)` dans `episodeService`
   - Appel POST `/api/episodes/${episodeId}/fetch-page-url`
   - Return: `{success, episode_page_url, episode_id}`

5. **frontend/src/views/LivresAuteurs.vue** (+77 lignes, -8 lignes)
   - **Auto-fetch logic** (lignes 908-920):
     - Vérification `if (!selectedEpisodeFull.episode_page_url)`
     - Appel `episodeService.fetchEpisodePageUrl()`
     - Mise à jour `selectedEpisodeFull.episode_page_url`
     - `console.warn()` en cas d'erreur (pas de crash UI)

   - **Logo display** (lignes 89-103):
     - `<a>` tag avec `v-if="selectedEpisodeFull?.episode_page_url"`
     - `target="_blank" rel="noopener noreferrer"` (sécurité)
     - `<img src="@/assets/le-masque-et-la-plume-logo.jpg">`
     - Class `.episode-logo-link` avec hover effects

   - **CSS** (lignes 2378-2403):
     - `.episode-info-container`: flexbox horizontal layout
     - `.episode-logo`: 80x80px, border-radius 8px, box-shadow
     - `.episode-logo-link:hover`: scale(1.05) + opacity 0.9

6. **frontend/src/assets/le-masque-et-la-plume-logo.jpg** (+22795 bytes)
   - Logo RadioFrance téléchargé localement (pas de hotlink)
   - Dimensions: 80x80px optimisé
   - Format: JPEG pour taille optimale

### Tests
7. **tests/test_radiofrance_service.py** (+169 lignes, 4 tests)
   - `test_initialization()`: Vérification URLs base
   - `test_search_episode_page_url_exact_match()`: Scraping avec résultats (JSON-LD)
   - `test_search_episode_page_url_not_found()`: Scraping sans résultats
   - `test_search_episode_page_url_network_error()`: Gestion erreur HTTP 500

8. **tests/test_api_episodes_radiofrance.py** (+138 lignes, 3 tests)
   - `test_fetch_episode_page_url_success()`: Endpoint avec succès + persist DB
   - `test_fetch_episode_page_url_not_found_in_radiofrance()`: RadioFrance 404
   - `test_fetch_episode_page_url_episode_not_in_db()`: Episode inexistant DB

9. **frontend/tests/integration/LivresAuteurs.episodePageUrl.test.js** (+307 lignes, 7 tests)
   - Describe block: "LivresAuteurs - Episode RadioFrance Page URL (Issue #89)"
   - Tests auto-fetch (4 tests): appel fetch, mise à jour, skip si URL, gestion erreur
   - Tests logo (3 tests): affichage avec URL, absence sans URL, affichage après fetch

### Fixtures
10. **tests/fixtures/radiofrance/README.md** (+53 lignes)
    - Documentation des fixtures HTML réelles
    - Contexte capture (2025-11-07)
    - Instructions maintenance/mise à jour

11. **tests/fixtures/radiofrance/search_with_results.html** (+175 lignes, 276KB)
    - Capture RÉELLE recherche RadioFrance avec résultats
    - Contient JSON-LD Schema.org ItemList authentique
    - Episode testé: "CRITIQUE I Anne Berest, Laura Vazquez..."

12. **tests/fixtures/radiofrance/search_no_results.html** (+163 lignes, 178KB)
    - Capture RÉELLE recherche RadioFrance sans résultats
    - Query: "Episode inexistant XYZ123"

### Documentation
13. **CLAUDE.md** (+91 lignes, -73 lignes)
    - **Section Bash API Call Patterns** (lignes 1729-1795):
      - Suppression patterns multiples confus
      - Documentation UNIQUE méthode `bash -c` avec point-virgule
      - Exemples: health check, POST JSON, query strings
      - Explication technique: pourquoi ça marche (sous-shell + pas d'échappement)

## Commits réalisés (5 commits)

### Commit 1: `1fc7dd0` - feat(radiofrance): add RadioFrance episode page URL search service
**Date**: 2025-11-07 16:44:50
**Files**: 5 fichiers, +726 lignes
- Service de scraping RadioFrance avec dual parsing strategy
- Fixtures HTML réelles (Issue #85 lesson appliquée)
- Tests complets (4/4 passent, coverage 72%)
- Test manuel validé: "Les nouvelles pages de Gaël Faye, Amélie Nothomb..."

### Commit 2: `fbfb193` - feat(api): add RadioFrance episode page URL fetch endpoint
**Date**: 2025-11-07 22:39:10
**Files**: 3 fichiers, +226 lignes, -7 lignes
- Endpoint POST `/api/episodes/{episode_id}/fetch-page-url`
- Méthode générique `update_episode()` dans mongodb_service
- Refactoring `update_episode_title()` pour réutilisabilité
- Tests endpoint complets (3/3 passent)
- Test manuel: épisode `68ffdb9387a20121a7e1775b` → URL fetchée et persistée ✅

### Commit 3: `c793c7c` - feat(frontend): add RadioFrance episode page link with auto-fetch
**Date**: 2025-11-07 22:55:40
**Files**: 4 fichiers, +386 lignes, -8 lignes
- Auto-fetch de l'URL RadioFrance quand `episode_page_url` manquant
- Logo RadioFrance cliquable (80x80px) avec layout horizontal
- Logo téléchargé localement (22KB JPEG optimisé)
- Tests TDD frontend (7/7 passent)
- Gestion gracieuse erreurs (console.warn, pas de crash UI)

### Commit 4: `fbebf80` - fix: align items in episode info container for better layout
**Date**: 2025-11-07 (après validation)
**Files**: 1 fichier (LivresAuteurs.vue)
- Fix CSS: `align-items: center` pour `.episode-info-container`
- Amélioration alignement vertical logo + texte

### Commit 5: `2acc22b` - docs: fix bash API call patterns in CLAUDE.md for Claude Code compatibility
**Date**: 2025-11-08 (résolution problème persistant)
**Files**: 1 fichier (CLAUDE.md), +91 lignes, -73 lignes
- Résout problème bash depuis semaines
- Documentation UNIQUE méthode fiable: `bash -c` avec `;`
- Suppression patterns multiples confus

**Total lignes branche**: 1371 lignes (+1444, -73 lignes)

## Apprentissages techniques majeurs

### 1. Bash API Call Pattern (CRITIQUE - résout problème persistant depuis semaines)

**Problème identifié**: Pattern documenté dans CLAUDE.md causait erreurs bash depuis des semaines:

```bash
# ❌ Ne fonctionne PAS dans Claude Code Bash tool
BACKEND_URL=$(/workspaces/back-office-lmelp/.claude/get-backend-info.sh --url) && \
curl "$BACKEND_URL/api/endpoint"

# Erreur: syntax error near unexpected token '('
# Cause: Bash tool échappe $ en \$ quand combiné avec &&
# Résultat: BACKEND_URL=\$ ( ... ) → échec parsing bash
```

**Solution implémentée** (documentée dans CLAUDE.md lignes 1729-1795):

```bash
# ✅ FONCTIONNE - Utiliser bash -c avec point-virgule
bash -c 'BACKEND_URL=$(/workspaces/back-office-lmelp/.claude/get-backend-info.sh --url); curl "$BACKEND_URL/api/stats" 2>/dev/null | jq'

# Pourquoi ça marche:
# 1. bash -c '...' : Lance nouveau shell avec guillemets simples
# 2. Point-virgule ; : Sépare commandes séquentielles (pas besoin &&)
# 3. Pas d'échappement : Le $(...) reste intact dans le sous-shell
# 4. 2>/dev/null : Supprime messages curl pour output propre avec jq

# Exemples pratiques:
# Health check
bash -c 'BACKEND_URL=$(.../get-backend-info.sh --url); curl "$BACKEND_URL/" 2>/dev/null'

# POST JSON
bash -c 'BACKEND_URL=$(.../get-backend-info.sh --url); curl -X POST "$BACKEND_URL/api/endpoint" -H "Content-Type: application/json" -d "{\"data\": \"value\"}" 2>/dev/null | jq'

# Query string
bash -c 'BACKEND_URL=$(.../get-backend-info.sh --url); curl -s "$BACKEND_URL/api/livres-auteurs?episode_oid=68c707ad6e51b9428ab87e9e" | jq'
```

**Impact**:
- Élimine 100% des erreurs bash lors d'appels API dans Claude Code
- Résout problème persistant depuis plusieurs semaines
- Une seule méthode documentée = moins de confusion

**Validation utilisateur**:
> "ça fait des semaines que quand tu tapes certaines commandes (par exemple des appels API on a ces erreurs) est-ce qu'on peut essayer de comprendre pourquoi et trouver la bonne formulation ?"

### 2. Fixtures HTML réelles (Leçon Issue #85 appliquée rigoureusement)

**Règle absolue**: JAMAIS inventer des mocks, TOUJOURS capturer les vraies réponses API/HTML.

**Application pour RadioFrance**:
```python
# tests/fixtures/radiofrance/search_with_results.html (276KB)
# → Capture RÉELLE du HTML RadioFrance du 2025-11-07
# → Contient JSON-LD Schema.org ItemList authentique
# → Structure complète: <script type="application/ld+json">
# → Assure que les tests valident le vrai comportement

# tests/fixtures/radiofrance/search_no_results.html (178KB)
# → Capture RÉELLE d'une recherche sans résultats
# → Garantit que le code gère correctement les cas d'absence
# → Teste le fallback HTML quand JSON-LD vide
```

**Process de capture**:
1. Ouvrir URL RadioFrance dans navigateur
2. Effectuer recherche manuelle avec titre épisode
3. "View Page Source" → Copy complet
4. Save dans `tests/fixtures/radiofrance/`
5. Documenter dans README.md (date, contexte, query)

**Pourquoi critique**: Les mocks inventés peuvent parfaitement valider du code bugué.

**Exemple Issue #85**:
- Tous tests passaient (5/5) ✅
- 0% de succès en production ❌
- Cause: Mocks utilisaient `"confidence"`, API réelle retourne `"confidence_score"`

**Leçon appliquée**: Tous les tests RadioFrance utilisent HTML réel capturé, pas de mock inventé.

### 3. Dual Parsing Strategy (JSON-LD + HTML fallback)

**Architecture robuste pour scraping RadioFrance**:

```python
async def search_episode_page_url(self, episode_title: str) -> str | None:
    # 1. Construire URL de recherche
    search_query = quote_plus(episode_title)  # Gestion accents/spéciaux
    search_url = f"{self.base_url}{self.podcast_search_base}?search={search_query}"

    # 2. Fetch HTML
    async with aiohttp.ClientSession() as session:
        async with session.get(search_url, timeout=10) as response:
            html_content = await response.text()

    # 3. Parse avec BeautifulSoup
    soup = BeautifulSoup(html_content, "html.parser")

    # 4. Stratégie 1 (prioritaire): JSON-LD Schema.org ItemList
    json_ld_url = self._parse_json_ld(soup)
    if json_ld_url:
        return json_ld_url  # ✅ Plus robuste

    # 5. Stratégie 2 (fallback): HTML parsing
    html_url = self._parse_html_links(soup)
    if html_url:
        return html_url  # ✅ Fonctionne si JSON-LD absent

    return None  # Aucun résultat trouvé
```

**Stratégie 1 - JSON-LD** (prioritaire):
```python
def _parse_json_ld(self, soup: BeautifulSoup) -> str | None:
    # Cherche <script type="application/ld+json">
    json_ld_scripts = soup.find_all("script", type="application/ld+json")

    for script in json_ld_scripts:
        data = json.loads(script.string)

        # Vérifier structure: {"@type": "ItemList", "itemListElement": [...]}
        if isinstance(data, dict) and data.get("@type") == "ItemList":
            items = data.get("itemListElement", [])
            if items and len(items) > 0:
                first_item = items[0]
                url = first_item.get("url", "")

                # Vérifier que c'est un lien d'épisode Le Masque et la Plume
                if self.podcast_search_base in url:
                    return url  # ✅ URL complète depuis JSON-LD

    return None
```

**Stratégie 2 - HTML fallback**:
```python
def _parse_html_links(self, soup: BeautifulSoup) -> str | None:
    # Cherche tous les liens <a href="...">
    links = soup.find_all("a", href=True)

    for link in links:
        href = link.get("href", "")

        # Filtre: doit contenir /franceinter/podcasts/le-masque-et-la-plume
        if self.podcast_search_base in href and href != self.podcast_search_base:
            # Construire URL complète si chemin relatif
            if href.startswith("/"):
                full_url = f"{self.base_url}{href}"
            else:
                full_url = href

            return full_url  # ✅ Premier lien trouvé

    return None
```

**Avantages**:
- ✅ Résistant aux changements de structure HTML
- ✅ Fallback automatique si JSON-LD manquant/invalide
- ✅ Logs détaillés pour debugging (logger.info, logger.warning)
- ✅ Testable avec fixtures HTML réelles

**Coverage**: 72% pour radiofrance_service.py

### 4. Lazy Loading Pattern (UX optimale, validé utilisateur)

**Design pattern adopté**: Fetch on demand + persist

```javascript
// ✅ OPTIMAL - Auto-fetch uniquement quand épisode sélectionné
async onEpisodeChange() {
  // 1. Charger détails complets de l'épisode
  try {
    const ep = await episodeService.getEpisodeById(this.selectedEpisodeId);
    this.selectedEpisodeFull = ep || null;
  } catch (err) {
    console.warn('Impossible de récupérer les détails complets:', err.message);
  }

  // 2. Auto-fetch SI ET SEULEMENT SI pas d'URL déjà présente
  // Issue #89: Fetch automatiquement l'URL de la page RadioFrance
  if (this.selectedEpisodeFull && !this.selectedEpisodeFull.episode_page_url) {
    try {
      const result = await episodeService.fetchEpisodePageUrl(this.selectedEpisodeId);
      if (result.success && result.episode_page_url) {
        // Mettre à jour l'épisode avec l'URL récupérée
        this.selectedEpisodeFull.episode_page_url = result.episode_page_url;
      }
    } catch (err) {
      // Ne pas bloquer l'UI si le fetch échoue
      console.warn('Impossible de récupérer l\'URL RadioFrance:', err.message);
    }
  }
}
```

**Alternatives rejetées**:
```javascript
// ❌ Batch fetch au mounted(): Trop de requêtes HTTP
async mounted() {
  await this.loadEpisodes();

  // REJETÉ: Fetch toutes les URLs en batch
  for (const episode of this.episodes) {
    if (!episode.episode_page_url) {
      await episodeService.fetchEpisodePageUrl(episode.id);
    }
  }
  // Problèmes:
  // - Performance: N requêtes HTTP en parallèle
  // - UX: l'utilisateur n'a pas encore sélectionné d'épisode
  // - Rate limiting: RadioFrance pourrait bloquer
  // - Inutile: 90% des épisodes ne seront jamais sélectionnés
}

// ❌ Pré-chargement de tous les épisodes
// ❌ Fetch périodique avec setInterval()
```

**Pourquoi optimal**:
1. ✅ **Performance**: Une seule requête HTTP par épisode sélectionné
2. ✅ **Persistance**: URL sauvegardée en MongoDB → fetch une seule fois par épisode
3. ✅ **Gestion erreur**: console.warn() sans crash UI
4. ✅ **UX**: Logo apparaît quasi-instantanément (fetch async non-bloquant)
5. ✅ **Économie bande passante**: Pas de fetch inutile pour épisodes non consultés

**Validation utilisateur**:
> "j'adore cette fonction, ça marche parfaitement. Et je ne pense pas qu'on ai besoin de traiter les episodes deja chargés."

**Confirmation**: Le pattern lazy loading est validé comme optimal.

### 5. MongoDB Refactoring - Méthode générique update_episode()

**Problème**: Code dupliqué pour mettre à jour différents champs d'épisode.

**Avant** (code dupliqué):
```python
# mongodb_service.py - AVANT refactoring
def update_episode_title(self, episode_id: str, new_title: str) -> None:
    """Met à jour le titre d'un épisode."""
    if not self.db:
        raise ValueError("Connexion MongoDB non établie")

    episode_oid = ObjectId(episode_id)
    self.episodes_collection.update_one(
        {"_id": episode_oid},
        {"$set": {"titre": new_title}}
    )

# Duplication pour chaque champ → NON MAINTENABLE
```

**Après** (méthode générique):
```python
# mongodb_service.py - APRÈS refactoring
def update_episode(self, episode_id: str, updates: dict[str, Any]) -> None:
    """Met à jour les champs d'un épisode de manière générique.

    Args:
        episode_id: ID de l'épisode à mettre à jour
        updates: Dictionnaire des champs à mettre à jour {field: value}

    Example:
        update_episode("507f...", {"titre": "Nouveau titre"})
        update_episode("507f...", {"episode_page_url": "https://..."})
    """
    if not self.db:
        raise ValueError("Connexion MongoDB non établie")

    episode_oid = ObjectId(episode_id)
    self.episodes_collection.update_one(
        {"_id": episode_oid},
        {"$set": updates}
    )

# Refactoring update_episode_title pour réutiliser méthode générique
def update_episode_title(self, episode_id: str, new_title: str) -> None:
    """Met à jour le titre d'un épisode."""
    self.update_episode(episode_id, {"titre": new_title})
```

**Avantages**:
- ✅ **Réutilisabilité**: Un seul point de mise à jour pour tous les champs
- ✅ **Maintenabilité**: Moins de code dupliqué
- ✅ **Extensibilité**: Facile d'ajouter de nouveaux champs
- ✅ **Tests**: Moins de tests à écrire/maintenir

**Utilisation dans endpoint**:
```python
# app.py - endpoint fetch-page-url
@app.post("/api/episodes/{episode_id}/fetch-page-url")
async def fetch_episode_page_url(episode_id: str):
    # ... fetch URL from RadioFrance ...

    # Persist URL using generic method
    mongodb_service.update_episode(
        episode_id,
        {"episode_page_url": found_url}
    )

    return {"episode_id": episode_id, "episode_page_url": found_url, "success": True}
```

### 6. MongoDB Schema - titre vs titre_corrige (Clarification importante)

**Contexte**: Investigation pour savoir si utiliser `titre` ou `titre_corrige` pour recherche RadioFrance.

**Investigation menée**:
```bash
# Check MongoDB schema
mcp__MongoDB__collection-schema --database "masque_et_la_plume" --collection "episodes"
```

**Résultat de l'analyse**:
```javascript
{
  "_id": ObjectId("..."),
  "titre": "Les nouvelles pages de Gaël Faye, Amélie Nothomb...",  // ✅ ORIGINAL
  "titre_corrige": "CRITIQUE I Anne Berest, Laura Vazquez...",     // Correction manuelle
  "date": ISODate("2025-10-26T..."),
  "description": "...",
  "episode_page_url": "https://www.radiofrance.fr/..."  // Nouveau champ
}
```

**Clarification utilisateur**:
> "ah non ça n'est pas un probleme. je pensais que titre contenait la modif et titre_orig la version originale mais en fait non. **titre contient l'originale et titre_corrige la correction** donc on n'a besoin de rien faire"

**Conclusion**:
- ✅ Champ `titre`: Contient le titre ORIGINAL de l'épisode (utilisé par RadioFrance)
- ✅ Champ `titre_corrige`: Contient titre modifié par utilisateur (correction manuelle)
- ✅ **Aucun changement de code nécessaire**: Le code utilise déjà `titre` correctement

**Code validé**:
```python
# app.py - endpoint utilise le bon champ
episode = mongodb_service.get_episode_by_id(episode_id)
episode_title = episode["titre"]  # ✅ Correct - titre original
result = await radiofrance_service.search_episode_page_url(episode_title)
```

**Leçon**: Toujours vérifier le schéma MongoDB avant de faire des suppositions sur les noms de champs.

### 7. BeautifulSoup + MyPy Type Stubs (Pre-commit environnement isolé)

**Problème rencontré**: Ajout de `beautifulsoup4` causait erreur mypy en pre-commit.

```bash
# Erreur pre-commit après pip install beautifulsoup4
tests/test_radiofrance_service.py:6: error: Cannot find implementation or library stub for module named "bs4"  [import-not-found]
```

**Cause**: Pre-commit utilise environnement isolé avec ses propres dépendances.

**Solution** (documentée dans CLAUDE.md):
```toml
# pyproject.toml - Pour mypy LOCAL
[project.optional-dependencies]
dev = [
    "mypy>=1.5.0",
    "beautifulsoup4>=4.12.0",
    "types-beautifulsoup4",  # ✅ Type stubs pour mypy local
    ...
]
```

```yaml
# .pre-commit-config.yaml - Pour mypy dans PRE-COMMIT
- repo: https://github.com/pre-commit/mirrors-mypy
  rev: v1.5.0
  hooks:
    - id: mypy
      additional_dependencies:
        - types-beautifulsoup4  # ✅ Type stubs pour pre-commit mypy
        - aiohttp
        - fastapi
```

**Commande après modification**:
```bash
# Réinstaller pre-commit hooks
pre-commit clean
pre-commit install

# Vérifier que mypy passe
pre-commit run mypy --all-files
```

**Leçon**: Les type stubs doivent être dans **DEUX endroits** car pre-commit utilise un environnement isolé.

**Références**: Documenté dans CLAUDE.md section "CRITICAL: MyPy Type Stubs with Pre-commit"

### 8. aiohttp AsyncMock Patterns (Test async context managers)

**Pattern correct pour tester aiohttp ClientSession**:

```python
# tests/test_radiofrance_service.py
from unittest.mock import AsyncMock, Mock, patch

# 1. Mock response avec async context manager
mock_response = Mock()
mock_response.status = 200
mock_response.text = AsyncMock(return_value=real_html)  # ✅ AsyncMock pour async method
mock_response.__aenter__ = AsyncMock(return_value=mock_response)  # ✅ Pour 'async with'
mock_response.__aexit__ = AsyncMock(return_value=None)           # ✅ Pour '__aexit__'

# 2. Mock session avec async context manager
mock_session = Mock()
mock_session.get = Mock(return_value=mock_response)
mock_session.__aenter__ = AsyncMock(return_value=mock_session)  # ✅ Pour 'async with'
mock_session.__aexit__ = AsyncMock(return_value=None)           # ✅ Pour '__aexit__'

# 3. Patch aiohttp.ClientSession
with patch("aiohttp.ClientSession", return_value=mock_session):
    result = await radiofrance_service.search_episode_page_url(episode_title)

    # Assertions
    assert result is not None
    assert result.startswith("https://www.radiofrance.fr")
```

**Pourquoi nécessaire**:
```python
# Code à tester utilise 'async with' double context manager
async with aiohttp.ClientSession() as session:
    async with session.get(search_url, timeout=...) as response:
        html_content = await response.text()

# ✅ Requiert __aenter__ et __aexit__ mockés pour les deux niveaux
```

**Erreur courante**:
```python
# ❌ FAUX - Oubli de mocker __aenter__/__aexit__
mock_response = Mock()
mock_response.text = AsyncMock(return_value=html)
# Erreur: TypeError: 'Mock' object does not support the asynchronous context manager protocol
```

**Leçon**: Toujours mocker `__aenter__` et `__aexit__` pour tester `async with`.

## Validation complète

### Tests automatisés
- ✅ **504 tests backend** passent (dont 6 nouveaux pour RadioFrance)
- ✅ **264 tests frontend** passent (dont 7 nouveaux pour Issue #89)
- ✅ **Lint (ruff)** propre - Aucune erreur
- ✅ **Typecheck (mypy)** propre - Aucune erreur import
- ✅ **Pre-commit hooks** passent - detect-secrets, ruff, mypy
- ✅ **CI/CD pipeline** verte - Python 3.11/3.12, Node.js 18

### Tests manuels
1. ✅ **Endpoint API**: Episode `68ffdb9387a20121a7e1775b` → URL fetchée et persistée
2. ✅ **Frontend**: Logo affiché, cliquable, ouvre nouvel onglet
3. ✅ **Auto-fetch**: URL récupérée automatiquement à la sélection
4. ✅ **Gestion erreur**: Pas de crash UI si RadioFrance ne trouve pas

### Validation utilisateur (verbatim)
> "j'adore cette fonction, ça marche parfaitement. Et je ne pense pas qu'on ai besoin de traiter les episodes deja chargés."

**Confirmation**: Le pattern lazy loading est validé comme optimal par l'utilisateur.

## Documentation mise à jour

### CLAUDE.md - Bash API Call Patterns (lignes 1729-1795)

**Avant** (problématique depuis semaines):
```markdown
### Pattern Optimal : Chaînage Auto-Discovery + API Call
```bash
# ✅ MÉTHODE RECOMMANDÉE : Chaînage avec && (FONCTIONNE PARFAITEMENT)
BACKEND_URL=$(/workspaces/back-office-lmelp/.claude/get-backend-info.sh --url) && \
curl -X POST "$BACKEND_URL/api/endpoint" ...
```

**Problème**: Pattern documenté comme fonctionnel échouait systématiquement.

**Après** (une seule méthode fiable):
```markdown
### Pattern bash -c pour Claude Code (MÉTHODE UNIQUE)

Claude Code Bash tool échappe certaines constructions shell, notamment `$(...)` avec `&&`.
**Utiliser TOUJOURS cette méthode** pour appels API avec auto-discovery.

```bash
# ✅ MÉTHODE RECOMMANDÉE pour Claude Code : bash -c avec point-virgule
bash -c 'BACKEND_URL=$(/workspaces/back-office-lmelp/.claude/get-backend-info.sh --url); curl "$BACKEND_URL/api/stats" 2>/dev/null | jq'

# ✅ Health check
bash -c 'BACKEND_URL=$(.../get-backend-info.sh --url); curl "$BACKEND_URL/" 2>/dev/null'

# ✅ POST avec données JSON
bash -c 'BACKEND_URL=$(.../get-backend-info.sh --url); curl -X POST "$BACKEND_URL/api/endpoint" -H "Content-Type: application/json" -d "{\"data\": \"value\"}" 2>/dev/null | jq'
```

### Pourquoi ce Pattern Fonctionne

- **bash -c '...'** : Lance un nouveau shell bash avec guillemets simples préservant caractères spéciaux
- **Point-virgule `;`** : Sépare les commandes séquentielles (pas besoin de `&&`)
- **Pas d'échappement** : Le `$()` reste intact dans le sous-shell
- **2>/dev/null** : Supprime messages de progression curl pour output propre
```

**Impact**:
- Élimine la confusion avec multiples patterns
- Une seule méthode = moins d'erreurs
- Résout problème persistant depuis plusieurs semaines

## Métriques finales

- **Temps total**: ~5 sessions (investigation, implémentation, tests, fix bash, validation)
- **Commits**: 5 commits (service, endpoint, frontend, fix CSS, fix docs)
- **Tests écrits**: 13 tests (6 backend, 7 frontend)
- **Fixtures créées**: 2 captures HTML réelles RadioFrance (454KB total)
- **Files modifiés**: 13 fichiers
- **Lignes totales**: +1444, -73 (net +1371 lignes)
- **Coverage**: 72% pour radiofrance_service.py
- **Success rate**: 100% validation utilisateur

## Prochaines étapes (todo list)

1. ✅ Récupérer détails issue #89
2. ✅ Créer branche feature
3. ✅ Analyser le problème
4. ✅ Chercher fichiers concernés
5. ✅ Créer fixtures RadioFrance HTML réelles
6. ✅ Mettre à jour tests avec fixtures
7. ✅ Vérifier lint et typecheck
8. ✅ Commit service RadioFrance
9. ✅ Implémenter endpoint backend
10. ✅ Test manuel backend validé
11. ✅ Auto-fetch frontend
12. ✅ Afficher logo frontend
13. ✅ Tests TDD frontend
14. ✅ Commit et push modifications
15. ✅ Vérifier tests/lint/typecheck
16. ✅ Vérifier CI/CD
17. ✅ Fixer patterns bash dans CLAUDE.md
18. ✅ Investigation titre_corrige (pas de changement nécessaire)
19. ✅ Validation utilisateur
20. 🔄 **Appeler /stocke-memoire** ← EN COURS
21. 🔄 Créer et merger PR
22. 🔄 Retour sur main et sync

## Références

- **Issue GitHub**: [#89 - Ajouter un lien vers la page de l'épisode](https://github.com/castorfou/back-office-lmelp/issues/89)
- **Branch**: `89-ajouter-un-lien-vers-la-page-de-lepisode`
- **Related Issues**:
  - #85 (leçon fixtures réelles appliquée rigoureusement)
  - #56 (auto-discovery utilisé pour tests API)
- **Files**:
  - Backend: `radiofrance_service.py`, `app.py` (lignes 342-401), `mongodb_service.py`
  - Frontend: `LivresAuteurs.vue`, `api.js`, logo image (22KB)
  - Tests: `test_radiofrance_service.py`, `test_api_episodes_radiofrance.py`, `LivresAuteurs.episodePageUrl.test.js`
  - Fixtures: `search_with_results.html` (276KB), `search_no_results.html` (178KB)
  - Docs: CLAUDE.md (lignes 1729-1795)
