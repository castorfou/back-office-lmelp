# Issue #188 - URL dynamique Anna's Archive avec interface française

**Date**: 2026-01-31
**Issue**: [#188](https://github.com/castorfou/back-office-lmelp/issues/188) - Rendre URL anna's archive dynamique
**Commit**: e40f43b
**Branche**: 188-rendre-url-annas-archive-dynamique

## Contexte

L'URL d'Anna's Archive était hardcodée (`https://fr.annas-archive.org`) dans le frontend. Cette URL change fréquemment (domaines bloqués, migrations), nécessitant des modifications manuelles du code à chaque changement.

**Problème identifié**: URL hardcodée dans `frontend/src/views/LivreDetail.vue:212` qui ne répondait plus.

## Solution implémentée

### Architecture hybrid avec préfixe français automatique

Stratégie à 3 niveaux avec ajout automatique du sous-domaine `fr.` pour l'interface française:

1. **Priority 1**: Variable d'environnement (`ANNAS_ARCHIVE_URL`) + health check (2s timeout)
2. **Priority 2**: Wikipedia scraping (cache 24h) + health check
3. **Priority 3**: Hardcoded default fallback (`https://fr.annas-archive.org`)

### Préfixe français automatique

**Innovation clé**: Ajout automatique du sous-domaine `fr.` pour forcer l'interface française d'Anna's Archive.

Exemples de transformation:
- `https://annas-archive.li` → `https://fr.annas-archive.li`
- `https://annas-archive.se` → `https://fr.annas-archive.se`
- `https://fr.annas-archive.org` → `https://fr.annas-archive.org` (préservé si déjà présent)

Implémenté dans `src/back_office_lmelp/services/annas_archive_url_service.py:244-268`:

```python
def _normalize_url(self, url: str) -> str:
    """Normalize URL to base domain with 'fr.' subdomain."""
    from urllib.parse import urlparse

    parsed = urlparse(url)
    netloc = parsed.netloc

    # Add 'fr.' prefix if not already present for French interface
    if not netloc.startswith("fr."):
        netloc = f"fr.{netloc}"

    return f"{parsed.scheme}://{netloc}"
```

## Composants créés

### Backend

**Nouveau service**: `src/back_office_lmelp/services/annas_archive_url_service.py` (269 lignes)

Fonctionnalités:
- **Health check** (`_health_check_url()`): Timeout 2s pour détecter URLs mortes
- **Wikipedia scraping** (`_scrape_wikipedia_url()`): 2 stratégies de parsing
  - Strategy 1: Extraction depuis infobox (`_parse_infobox()`)
  - Strategy 2: Premier lien externe dans contenu principal (`_parse_external_links()`)
- **Cache 24h**: Réutilise `BabelioCacheService` pour persister URLs scrapées
- **Normalisation URL**: Strip path/query + ajout préfixe `fr.` automatique
- **Debug logging**: Variable `ANNAS_ARCHIVE_DEBUG_LOG` pour diagnostics

**Nouveau endpoint**: `src/back_office_lmelp/app.py:2468-2489`

```python
@app.get("/api/config/annas-archive-url")
async def get_annas_archive_url() -> dict[str, str]:
    """Get current Anna's Archive base URL with French interface."""
    try:
        url = await annas_archive_url_service.get_url()
        return {"url": url}
    except Exception as e:
        logger.error(f"Error getting Anna's Archive URL: {e}")
        return {"url": "https://fr.annas-archive.org"}  # Ultimate fallback
```

**Settings**: `src/back_office_lmelp/settings.py:51-63`

Nouvelle propriété `annas_archive_url` pour accès à la variable d'environnement.

### Frontend

**Modifications**: `frontend/src/views/LivreDetail.vue`

Changements clés:
- **Nouvelle propriété data** (`annasArchiveBaseUrl`): Stocke URL dynamique avec fallback
- **Nouvelle méthode** (`loadAnnasArchiveUrl()`): Appel API pour récupérer URL
- **Chargement parallèle**: Utilisation de `Promise.all()` dans `mounted()` pour charger livre + URL simultanément
- **Méthode mise à jour** (`getAnnasArchiveUrl()`): Utilise `annasArchiveBaseUrl` au lieu de hardcoded

```javascript
// Avant (hardcoded)
return `https://fr.annas-archive.org/search?q=${encodedQuery}`;

// Après (dynamique avec préfixe fr.)
return `${this.annasArchiveBaseUrl}/search?q=${encodedQuery}`;
// annasArchiveBaseUrl = "https://fr.annas-archive.li" (depuis API)
```

### Tests

**Backend**: 16 tests (3 nouveaux + 13 existants mis à jour)

Fichiers:
- `tests/test_annas_archive_url_service.py` (304 lignes, 13 tests)
- `tests/test_settings.py` (53 lignes, 3 tests)

**Nouveaux tests pour préfixe français** (`tests/test_annas_archive_url_service.py:29-80`):

```python
class TestUrlNormalization:
    def test_normalize_url_should_add_fr_subdomain_when_missing(self, service):
        """Should add 'fr.' subdomain to domains without language prefix."""
        url = "https://annas-archive.li/search?q=test"
        result = service._normalize_url(url)
        assert result == "https://fr.annas-archive.li"

    def test_normalize_url_should_preserve_existing_fr_subdomain(self, service):
        """Should not duplicate 'fr.' if already present."""
        url = "https://fr.annas-archive.se/about"
        result = service._normalize_url(url)
        assert result == "https://fr.annas-archive.se"
```

Scénarios couverts:
- ✅ Health check avec URL accessible
- ✅ Health check avec timeout (fallback à Wikipedia)
- ✅ Cache 24h avec URL saine
- ✅ Re-scraping si URL cachée timeout
- ✅ Scraping Wikipedia après expiration cache
- ✅ Hardcoded default si Wikipedia échoue
- ✅ Parsing infobox Wikipedia
- ✅ Ajout préfixe `fr.` aux domaines sans langue
- ✅ Préservation préfixe `fr.` existant
- ✅ Suppression path/query avec ajout `fr.`

**Frontend**: 5 tests mis à jour

Fichier: `frontend/tests/unit/livreDetailAnnasArchive.spec.js`

Tous les mocks API mis à jour pour utiliser `https://fr.annas-archive.se` au lieu de `https://annas-archive.se`.

**Fixture réelle**: `tests/fixtures/annas_archive/wikipedia_page.html` (1836 lignes)

Capture HTML réelle de Wikipedia pour garantir que les tests reflètent le comportement production (leçon de l'Issue #85).

## Configuration

**Fichier**: `docker/deployment/.env.template`

```bash
# Anna's Archive URL (optional)
# Si non définie, l'URL sera automatiquement récupérée depuis Wikipedia
# Le préfixe 'fr.' est ajouté automatiquement pour l'interface française
# Exemples:
#   ANNAS_ARCHIVE_URL=https://annas-archive.li  → https://fr.annas-archive.li
#   ANNAS_ARCHIVE_URL=https://fr.annas-archive.se  → https://fr.annas-archive.se (préservé)
ANNAS_ARCHIVE_URL=
```

## Patterns et apprentissages

### 1. TDD avec tests de normalisation URL

**Phase RED**: Écriture de 3 tests pour vérifier ajout préfixe `fr.`

**Phase GREEN**: Implémentation de `_normalize_url()` avec logique conditionnelle

```python
# Pattern: Ajout conditionnel de sous-domaine
if not netloc.startswith("fr."):
    netloc = f"fr.{netloc}"
```

### 2. Stratégie de fallback robuste

**Pattern à 3 niveaux** avec health checks:

```python
async def get_url(self) -> str:
    # Level 1: Env var (if set)
    if self.settings.annas_archive_url:
        if await self._health_check_url(self.settings.annas_archive_url):
            return self.settings.annas_archive_url

    # Level 2: Cached Wikipedia URL
    cached = self.cache_service.get_cached(...)
    if cached and await self._health_check_url(cached_url):
        return cached_url

    # Re-scrape if cache expired or unhealthy
    scraped_url = await self._scrape_wikipedia_url()
    if scraped_url:
        self.cache_service.set_cached(...)
        return scraped_url

    # Level 3: Hardcoded default
    return self.hardcoded_default
```

**Avantages**:
- ✅ Résilience: Continue de fonctionner même si Wikipedia est down
- ✅ Performance: Cache 24h réduit les appels Wikipedia
- ✅ Flexibilité: Permet override via env var pour déploiements spécifiques

### 3. Health check avec timeout court

**Pattern**: Timeout 2s pour détection rapide de URLs mortes

```python
async def _health_check_url(self, url: str) -> bool:
    """Health check with 2s timeout."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.head(url, timeout=2, allow_redirects=True):
                return True
    except (TimeoutError, aiohttp.ClientError):
        return False
```

**Pourquoi 2s?** Compromis entre:
- Trop court (< 1s): Faux négatifs sur connexions lentes
- Trop long (> 5s): Ralentit fallback en cas d'URL morte

### 4. Wikipedia scraping avec 2 stratégies

**Strategy 1** (infobox): Structure stable, prioritaire

```python
def _parse_infobox(self, soup: BeautifulSoup) -> str | None:
    """Parse Wikipedia infobox for official URL."""
    infobox = soup.find("table", class_="infobox")
    for row in infobox.find_all("tr"):
        header = row.find("th")
        if "website" in header.get_text(strip=True).lower():
            link = row.find("a", href=True)
            return self._normalize_url(link["href"])
```

**Strategy 2** (external links): Fallback si infobox échoue

```python
def _parse_external_links(self, soup: BeautifulSoup) -> str | None:
    """Parse external links section for official URL."""
    content = soup.find("div", id="mw-content-text")
    for link in content.find_all("a", href=True):
        href = link["href"]
        if "annas-archive" in href:
            return self._normalize_url(href)
```

**Leçon**: Toujours avoir un fallback pour scraping (structure HTML peut changer).

### 5. Cache disk 24h réutilisé

**Pattern**: Réutilisation de `BabelioCacheService` existant au lieu de créer nouveau cache

```python
# Initialisation dans app.py
annas_archive_url_service = AnnasArchiveUrlService(
    settings=settings,
    cache_service=babelio_cache_service  # Réutilisation!
)
```

**Avantages**:
- ✅ Pas de duplication de code
- ✅ Même TTL (24h) pour tous les caches externes
- ✅ Même stratégie de persistence (disk-based)

### 6. Chargement parallèle frontend

**Pattern**: `Promise.all()` pour charger données indépendantes simultanément

```javascript
async mounted() {
  await Promise.all([
    this.loadLivre(),           // API 1: Données livre
    this.loadAnnasArchiveUrl()  // API 2: URL Anna's Archive
  ]);
}
```

**Avant** (séquentiel):
```javascript
async mounted() {
  await this.loadLivre();           // 500ms
  await this.loadAnnasArchiveUrl(); // 200ms
  // Total: 700ms
}
```

**Après** (parallèle):
```javascript
async mounted() {
  await Promise.all([...]);
  // Total: max(500ms, 200ms) = 500ms
}
```

**Gain**: 30% plus rapide dans cet exemple.

### 7. Debug logging contrôlé par env var

**Pattern**: Garder les logs debug dans le code, contrôler via variable d'environnement

```python
def __init__(self, settings, cache_service):
    self._debug_log_enabled = os.getenv("ANNAS_ARCHIVE_DEBUG_LOG", "0").lower() in ("1", "true")

async def get_url(self) -> str:
    if self._debug_log_enabled:
        logger.info(f"🔧 Testing env var ANNAS_ARCHIVE_URL: {self.settings.annas_archive_url}")
```

**Avantages**:
- ✅ Logs disponibles pour diagnostic futur (activation via env var)
- ✅ Pas de pollution en production (désactivé par défaut)
- ✅ Facilite debugging problèmes complexes (health checks, scraping)

Voir `CLAUDE.md` section "Debug Logging Strategy" pour convention complète.

## Résultats

### Tests
- **Backend**: 16/16 tests passent ✅
- **Frontend**: 5/5 tests passent ✅
- **Coverage**: Service à 66% (lignes non-error principalement)

### Linting & Type checking
- **Ruff**: ✅ Aucune erreur
- **MyPy**: ✅ Aucune erreur de type
- **Pre-commit hooks**: ✅ Tous passent

### Comportement production

**Test manuel** (confirmé par utilisateur):

```bash
curl http://localhost:8000/api/config/annas-archive-url | jq
# Résultat: {"url": "https://fr.annas-archive.li"}
```

Frontend:
- URL générée: `https://fr.annas-archive.li/search?q=Marx+en+Amérique+-+Christian+Laval`
- Interface: ✅ Affichée en français automatiquement grâce au sous-domaine `fr.`

**Avant cette issue**: URL hardcodée `https://fr.annas-archive.org` ne répondait plus
**Après**: URL automatiquement mise à jour vers `https://fr.annas-archive.li` (depuis Wikipedia)

## Métriques

- **Fichiers modifiés**: 9 (3 backend, 2 frontend, 4 tests)
- **Lignes ajoutées**: 2606
- **Nouveau service**: 269 lignes
- **Tests backend**: 357 lignes (304 + 53)
- **Fixture Wikipedia**: 1836 lignes
- **Tests frontend**: 82 lignes modifiées

## Points d'attention futurs

### 1. Monitoring health checks

Considérer l'ajout de métriques pour tracker:
- Taux de succès health checks (env var vs Wikipedia)
- Fréquence de fallback au hardcoded default
- Latence moyenne des health checks

### 2. Wikipedia scraping fragile

**Risque**: Structure HTML Wikipedia peut changer et casser le scraping.

**Mitigation actuelle**:
- 2 stratégies de parsing (infobox + external links)
- Hardcoded default en dernier recours
- Tests avec fixture HTML réelle

**Amélioration future**: Monitoring pour alerter si scraping échoue pendant >24h.

### 3. Cache invalidation manuelle

**Limitation**: Cache 24h fixe, pas de mécanisme pour invalider manuellement.

**Workaround actuel**: Redémarrer backend pour forcer re-scraping.

**Amélioration future**: Endpoint admin `/api/admin/annas-archive-url/refresh` pour forcer refresh.

### 4. Gestion des sous-domaines multi-langues

**Question**: Que faire si Anna's Archive ajoute d'autres sous-domaines (`en.`, `es.`, etc.)?

**Solution actuelle**: Préfixe `fr.` hardcodé pour interface française.

**Amélioration future**: Variable d'environnement `ANNAS_ARCHIVE_LANG_PREFIX=fr` pour flexibilité.

## Références

- **Issue GitHub**: [#188](https://github.com/castorfou/back-office-lmelp/issues/188)
- **Commit**: e40f43b
- **Leçons appliquées**:
  - Issue #85: Utiliser fixtures HTML réelles pour tests de scraping
  - CLAUDE.md "Debug Logging Strategy": Logs debug contrôlés par env var
  - CLAUDE.md "Vue.js UI Patterns": `Promise.all()` pour chargement parallèle

## Commandes utiles

```bash
# Tester l'API
curl http://localhost:8000/api/config/annas-archive-url | jq

# Activer debug logging
export ANNAS_ARCHIVE_DEBUG_LOG=1

# Forcer une URL spécifique
export ANNAS_ARCHIVE_URL=https://annas-archive.se
# → API retournera https://fr.annas-archive.se (préfixe ajouté)

# Tester health check
curl -I https://fr.annas-archive.li  # Devrait retourner 200 OK
```
