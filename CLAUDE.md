# CLAUDE.md

This file provides quick guidance to Claude Code (claude.ai/code) when working with code in this repository.

**📘 For detailed explanations, patterns, and best practices**, see [Claude AI Development Guide](docs/dev/claude-ai-guide.md).

## Project Overview

Full-stack application for managing database related to lmelp project:
- **Backend**: Python FastAPI with MongoDB integration + Calibre SQLite (optional)
- **Frontend**: Vue.js 3 SPA with Vite build system
- **Environment**: VS Code devcontainers (Docker-based)
- **Dual toolchains**: uv (Python) + npm (Node.js)

## Environment Setup

**IMPORTANT**: Activate the Python virtual environment once per bash session:

```bash
source /workspaces/back-office-lmelp/.venv/bin/activate
```

This enables direct use of tools like `ruff`, `mypy`, `pytest`, `mkdocs` without the `uv run` prefix.

## Essential Commands

### Backend Commands

```bash
# Install dependencies
uv pip install -e .
pre-commit install

# Run backend (automatic port selection)
PYTHONPATH=/workspaces/back-office-lmelp/src python -m back_office_lmelp.app

# Linting and formatting
ruff check . --output-format=github
ruff format .
mypy src/

# Tests
PYTHONPATH=/workspaces/back-office-lmelp/src pytest tests/ -v --cov=src --cov-report=term-missing

# Pre-commit hooks
pre-commit run --all-files
```

### Frontend Commands

**IMPORTANT**: Always use absolute paths to avoid directory confusion.

```bash
# Install dependencies
cd /workspaces/back-office-lmelp/frontend && npm ci

# Tests
cd /workspaces/back-office-lmelp/frontend && npm test -- --run

# Development server
cd /workspaces/back-office-lmelp/frontend && npm run dev

# Build for production
cd /workspaces/back-office-lmelp/frontend && npm run build
```

### Development Scripts

```bash
# Start both backend and frontend
./scripts/start-dev.sh
```

### Documentation Commands

```bash
# Serve documentation locally (port 8000)
mkdocs serve

# Build documentation
mkdocs build --strict
```

## Project Structure

```
├── src/back_office_lmelp/      # Backend Python (FastAPI, services, models)
├── frontend/                   # Frontend Vue.js (components, views, tests)
├── tests/                      # Backend tests (pytest)
├── docs/                       # Documentation (MkDocs)
├── scripts/                    # Development scripts
└── .claude/                    # Auto-discovery scripts
```

## Code Quality Standards

### Backend (Python)
- **Linting**: Ruff (replaces flake8, black, isort)
- **Type Checking**: MyPy with progressive strictness
- **Line Length**: 88 characters maximum
- **Python Version**: 3.11+

### Frontend (Vue.js/TypeScript)
- **Testing**: Vitest with @vue/test-utils
- **Build**: Vite 5.0+
- **Node Version**: 18+

### Pre-commit Hooks
**CRITICAL**: Always run before committing:
```bash
pre-commit run --all-files
```

Pre-commit automatically blocks commits if:
- Ruff linting fails
- MyPy type checking fails
- Security issues detected (detect-secrets)
- File formatting is inconsistent

## Testing

### Backend Tests
```bash
PYTHONPATH=/workspaces/back-office-lmelp/src uv run pytest tests/ -v
```

### Frontend Tests
```bash
cd /workspaces/back-office-lmelp/frontend && npm test -- --run
```

## Development Workflow

### Test-Driven Development (TDD)
**ALWAYS follow TDD for all code changes with INCREMENTAL approach**:

**CRITICAL - The Incremental TDD Cycle:**

1. **Start with ONE high-level test** that captures the real business problem
   - ❌ BAD: Writing all unit tests for non-existent functions (`_is_title_truncated`, `fetch_full_title_from_url`, etc.)
   - ✅ GOOD: Write ONE integration test showing `verify_book()` returns wrong title (business problem)

2. **Make it fail for the RIGHT reason**
   - First RED should be: "Expected 'Full Title' but got 'Truncated Title...'" (business failure)
   - NOT: "AttributeError: function doesn't exist" (technical failure)
   - Add minimal stub functions returning dummy values to see the real failure

3. **Implement incrementally, ONE function at a time**
   - Fix the high-level test by adding detection logic
   - When you need a helper function, write its test FIRST, then implement
   - Each cycle: ONE test → ONE minimal implementation → GREEN

4. **Example - Issue #88 (Truncated Titles):**
   ```python
   # Step 1: High-level test (integration)
   def test_verify_book_should_return_full_title_not_truncated():
       result = verify_book("Full Title", "Author")
       assert result["babelio_suggestion_title"] == "Full Title"
       # NOT: "Full Title..." ← This is the REAL problem to fix

   # Step 2: Run test → Fails because returns "Full Title..."
   # Step 3: Add stub: def _is_title_truncated(title): return False
   # Step 4: Test still fails (good! Real business problem visible)

   # Step 5: Write unit test for the helper
   def test_should_detect_truncated_title():
       assert _is_title_truncated("Title...") is True

   # Step 6: Run test → Fails (returns False)
   # Step 7: Implement _is_title_truncated() → GREEN
   # Step 8: Continue incrementally for scraping logic...
   ```

**Why this matters:**
- Writing all tests at once hides the real problem behind technical errors
- You can't verify each small step independently
- Harder to debug when multiple things are broken at once
- Violates the "minimal change" principle of TDD

**Never implement code without corresponding tests, and never write tests faster than you implement code.**

### Backend Testing - Key Rules

**CRITICAL Rules** (see [detailed guide](docs/dev/claude-ai-guide.md) for explanations):

1. **Mock external dependencies** (MongoDB, APIs, services) - NO real database connections in unit tests

2. **Create mocks from real API responses** - NEVER invent mock structures
   - ❌ BAD: `const mock = { _id: '123', user_name: 'John' }` (invented)
   - ✅ GOOD: First check real API/MongoDB, then copy exact structure
   - Example: `curl $API_URL/endpoint | jq '.[0]'` or `mcp__MongoDB__find --collection "..." --limit 1`
   - **Why critical**: Tests can pass with invented mocks but fail in production (see Issue #96, #148)
   - **Type handling**: MongoDB `distinct()` may return different types than `find()` - verify with real data

3. **CRITICAL: Use real data types in mocks** - Match exact types from source systems (Issue #150)
   - ❌ BAD: `mock_episode = {"date": "2022-04-24T00:00:00"}` (string, but MongoDB returns datetime)
   - ✅ GOOD: `mock_episode = {"date": datetime(2022, 4, 24)}` (actual MongoDB type)
   - **Why critical**: Type mismatches cause runtime errors that tests don't catch
   - **How to verify**: Use MCP tools or curl to inspect real data types BEFORE writing mocks
   - **Example error**: `"T" in episode_date` fails when `episode_date` is datetime, not string
   - **Prevention**: Always check `type(field_value)` on real data before mocking

4. **MANDATORY: Verify MongoDB field types with collection-schema BEFORE any implementation** (Issue #154)
   - **NEVER assume field types** - String vs ObjectId confusion causes production bugs
   - **Always run**: `mcp__MongoDB__collection-schema --database "masque_et_la_plume" --collection "collection_name"`
   - **Example**: `avis_critiques.episode_oid` is **String**, but `episodes._id` is **ObjectId** → requires conversion
   - ❌ BAD: `find({"_id": {"$in": distinct("episode_oid")}})` - Type mismatch! String ≠ ObjectId
   - ✅ GOOD: `find({"_id": {"$in": [ObjectId(id) for id in distinct("episode_oid")]}})` - Explicit conversion
   - **Critical fields to verify**:
     - `_id` fields (usually ObjectId, but check!)
     - Foreign key fields (`episode_oid`, `book_id`, etc.) - may be String or ObjectId
     - Date fields (Date vs String)
   - **When to check**: Before ANY new endpoint, query, or aggregation implementation
   - **Why mocks don't catch this**: Mocks return data directly without executing real MongoDB queries
     - ❌ `mock.find.return_value = [...]` bypasses type validation
     - ✅ Add explicit assertions in tests: `assert all(isinstance(id, ObjectId) for id in ids_list)`
     - See [test_api_critiques_endpoints.py:199-208](tests/test_api_critiques_endpoints.py#L199-L208) for example

5. **Use helper function pattern** for services with complex dependencies

6. **Patch singleton instances** directly when using local imports

7. **Verify database updates** with `mock_collection.update_one.assert_called_with(...)`

8. **Mock MongoDB cursors to match actual code patterns**:
   ```python
   # ❌ BAD - Mock doesn't match code usage
   mock_collection.find.return_value.sort.return_value.limit.return_value = data
   # Code does: list(collection.find().sort()) → .limit() never called

   # ✅ GOOD - Mock matches actual pattern
   mock_collection.find.return_value.sort.return_value = iter(data)
   # Code does: list(collection.find().sort()) → consumes iterator
   ```

9. **Skip tests conditionally for external services**:
   ```python
   skip_if_no_service = pytest.mark.skipif(
       os.getenv("SERVICE_ENDPOINT") is None,
       reason="Service non configuré (CI/CD)"
   )

   @skip_if_no_service
   def test_external_api_call(self):
       """Test s'exécute uniquement si SERVICE_ENDPOINT configuré."""
       # Test with real service credentials
   ```

### Frontend Testing - Key Rules

1. **Reset mocks between tests**: Use `vi.resetAllMocks()` in `beforeEach`
2. **Prefer `mockResolvedValueOnce`** over persistent `mockImplementation`
3. **Watch for mock pollution**: Closures in `mockImplementation` persist across tests
4. **Direct method calls over button triggers** for reliable state access:
   ```javascript
   // ❌ AVOID - wrapper.vm.error may be null after trigger
   const button = wrapper.find('button');
   await button.trigger('click');
   expect(wrapper.vm.error).toBeTruthy();  // May fail

   // ✅ PREFER - Direct method call guarantees state synchronization
   wrapper.vm.selectedValue = 'test';
   await wrapper.vm.$nextTick();
   await wrapper.vm.methodUnderTest();
   expect(wrapper.vm.error).toBeTruthy();  // Reliable
   ```

### Vue.js UI Patterns et Charte Graphique

**Pour les patterns UI détaillés et les conventions visuelles**, voir [Charte graphique et patterns UI Vue.js](docs/dev/vue-ui-patterns.md).

**Règles critiques :**
- **Chargement parallèle** : Utiliser `Promise.all()` dans `mounted()` pour afficher toutes les stats simultanément
- **Propriétés calculées** : Retourner `null` si des composants sont encore en chargement
- **Pattern à 3 états** : loading → error → data → empty

### Axios - Pattern URLs Relatives

**TOUJOURS utiliser des URLs relatives** pour les appels API axios :

```javascript
// ✅ CORRECT - URL relative (fonctionne en dev et prod)
const response = await axios.get('/api/books/duplicates/statistics');
const result = await axios.post('/api/books/duplicates/merge', {
  url_babelio: url,
  book_ids: ids
});

// ❌ MAUVAIS - URL absolue (ne fonctionne qu'avec un serveur spécifique)
const response = await axios.get('http://localhost:8000/api/books/duplicates/statistics');
```

**Pourquoi :**
- Les URLs relatives fonctionnent automatiquement en dev (proxy Vite) et en prod
- Évite le hardcoding de l'URL du backend
- Compatible avec les déploiements multi-environnements
- Le proxy Vite (configuré dans `vite.config.js`) redirige automatiquement `/api/*` vers le backend

**Configuration du proxy** (déjà en place dans `frontend/vite.config.js`) :
```javascript
server: {
  proxy: {
    '/api': 'http://localhost:8000'
  }
}
```

### FastAPI Best Practices

**CRITICAL**: Two common patterns that cause production bugs:

1. **Route Order Matters** - Specific routes MUST come BEFORE parametric routes:
   ```python
   @app.get("/api/episodes/all")        # ✅ Specific FIRST
   @app.get("/api/episodes/{id}")       # ✅ Parametric AFTER
   ```
   ❌ Wrong order causes `/api/episodes/all` to match `{id}="all"` → 404 error

2. **REST Idempotence** - Use `matched_count` not `modified_count` for MongoDB updates:
   ```python
   result = collection.update_one({"_id": id}, {"$set": {"field": value}})
   return bool(result.matched_count > 0)  # ✅ Idempotent
   # NOT: result.modified_count > 0       # ❌ Fails if already in desired state
   ```

**Details**: See [FastAPI Route Patterns](docs/dev/claude-ai-guide.md#fastapi-route-patterns) in developer guide.

### Livres avec Co-Auteurs - Limitation Modèle Actuel

**IMPORTANT** : Le modèle de données actuel ne supporte **qu'un seul auteur par livre** via le champ `auteur_id`.

**Modèle actuel** (collection `livres`) :
```python
{
  "_id": ObjectId(...),
  "titre": str,
  "auteur_id": ObjectId(...),  # ⚠️ UN SEUL auteur
  "url_babelio": str,
  "editeur": str,
  "episodes": list[str],
  ...
}
```

**Conséquences pour les livres avec co-auteurs** :
- ❌ Les livres avec plusieurs auteurs ne peuvent être correctement représentés
- ⚠️ Lors de la détection de doublons : un livre avec co-auteurs pourrait avoir plusieurs entrées (une par auteur)
- ⚠️ La fusion de doublons vérifie que `auteur_id` est identique → rejette les fusions si auteurs différents

**Stratégie actuelle** :
- **Solution de contournement** : Choisir un auteur principal par livre
- **Données Babelio** : Le scraping récupère le nom complet depuis Babelio qui peut inclure plusieurs auteurs dans le champ `nom` de la collection `auteurs`

**Évolutions futures possibles** :
- Modèle avec `auteur_ids: list[ObjectId]` pour supporter plusieurs auteurs
- Nécessiterait la migration de toutes les données existantes
- Impact sur la validation bibliographique et la détection de doublons

## Auto-Discovery System

### Service Discovery Commands

```bash
# Get service overview
/workspaces/back-office-lmelp/.claude/get-services-info.sh

# Get backend URL (most common)
/workspaces/back-office-lmelp/.claude/get-backend-info.sh --url

# Get frontend URL
/workspaces/back-office-lmelp/.claude/get-frontend-info.sh --url

# Check backend status
/workspaces/back-office-lmelp/.claude/get-backend-info.sh --status

# Check backend freshness (needs restart?)
/workspaces/back-office-lmelp/.claude/check-backend-freshness.sh
```

### API Testing Workflow

**Pattern recommandé pour Claude Code** (bash -c avec point-virgule):

```bash
# Health check
bash -c 'BACKEND_URL=$(/workspaces/back-office-lmelp/.claude/get-backend-info.sh --url); curl "$BACKEND_URL/" 2>/dev/null'

# Get stats
bash -c 'BACKEND_URL=$(/workspaces/back-office-lmelp/.claude/get-backend-info.sh --url); curl "$BACKEND_URL/api/stats" 2>/dev/null | jq'

# API schema discovery
bash -c 'BACKEND_URL=$(/workspaces/back-office-lmelp/.claude/get-backend-info.sh --url); curl "$BACKEND_URL/openapi.json" 2>/dev/null | jq ".paths | keys[]"'
```

## MongoDB Operations

### MCP MongoDB Tools

**Main Database**: `masque_et_la_plume`
**Collections**: `livres`, `auteurs`, `episodes`, `avis_critiques`, `editeurs`, `emissions`, `critiques`, `logs`

**Common operations**:
```bash
# List collections
mcp__MongoDB__list-collections --database "masque_et_la_plume"

# Get schema
mcp__MongoDB__collection-schema --database "masque_et_la_plume" --collection "livres"

# Find documents
mcp__MongoDB__find --database "masque_et_la_plume" --collection "livres" --limit 10

# Count documents
mcp__MongoDB__count --database "masque_et_la_plume" --collection "episodes"

# Aggregation
mcp__MongoDB__aggregate --database "masque_et_la_plume" --collection "livres" --pipeline '[{"$group": {"_id": "$editeur", "count": {"$sum": 1}}}]'
```

## Critical Patterns and Anti-Patterns

### MongoDB Cursor Handling

**CRITICAL**: Never mix sync cursors with async iteration

```python
# ❌ WRONG - Async iteration on sync cursor
authors = auteurs_collection.aggregate([...])  # Sync cursor
async for author in authors:  # ERROR: async iteration on sync cursor
    process(author)

# ✅ CORRECT - Materialize sync cursor first
authors = list(auteurs_collection.aggregate([...]))  # Materialize
for author in authors:  # Sync iteration
    await process(author)
```

### MongoDB Type Handling

**CRITICAL**: Verify data types from MongoDB operations - don't assume

```python
# ❌ WRONG - Assuming distinct() returns same type as find()
episode_ids_from_distinct = collection.distinct("episode_oid")  # Returns strings!
episode_ids_from_find = {ep["_id"] for ep in episodes.find()}    # Returns ObjectId!
intersection = set(episode_ids_from_distinct) & episode_ids_from_find  # Empty! str ≠ ObjectId

# ✅ CORRECT - Convert types explicitly based on real data inspection
from bson import ObjectId

episode_ids_from_distinct = {
    ObjectId(ep_id) if isinstance(ep_id, str) else ep_id
    for ep_id in collection.distinct("episode_oid")
    if ep_id is not None
}
episode_ids_from_find = {ep["_id"] for ep in episodes.find()}
intersection = episode_ids_from_distinct & episode_ids_from_find  # Works!
```

**Why**: MongoDB field types may differ from `_id` types (strings vs ObjectId). Always inspect real data with MCP tools before implementing set operations or comparisons.

### MongoDB DateTime vs String Handling

**CRITICAL**: MongoDB returns `datetime` objects, but string operations expect `str`

```python
# ❌ WRONG - Assumes date is always string
async def search_by_date(episode_date: str | None) -> str | None:
    if episode_date and episode_date.startswith("2024"):  # Crash if datetime!
        return url

# ✅ CORRECT - Accept both types and convert
from datetime import datetime

async def search_by_date(episode_date: str | datetime | None) -> str | None:
    """Accept both string and datetime from MongoDB."""
    # Convert datetime to string if necessary
    if episode_date and not isinstance(episode_date, str):
        episode_date = episode_date.strftime("%Y-%m-%d")

    # Now safe to use string operations
    if episode_date and episode_date.startswith("2024"):
        return url
```

**Why this matters**:
- MongoDB `find()` returns `datetime` objects for date fields
- String operations like `startswith()`, `split()`, `in` fail on datetime
- **Error**: `TypeError: startswith first arg must be str, not datetime.datetime`

**Pattern**: Always convert at function entry, update type hints accordingly

### Vue.js Lifecycle Cleanup

**CRITICAL**: Always clean up timers/intervals in `beforeUnmount()`

```javascript
// ✅ CORRECT
data() {
  return { pollInterval: null }
},

beforeUnmount() {
  if (this.pollInterval) {
    clearInterval(this.pollInterval);
    this.pollInterval = null;
  }
}
```

**Why**: Prevents memory leaks and continued execution after component destruction.

### Polling vs Server-Sent Events

**Prefer simple conditional polling over EventSource (SSE):**

```javascript
// ❌ AVOID - EventSource with infinite reconnection
this.eventSource = new EventSource(url);
this.eventSource.onerror = () => {
  setTimeout(() => this.connectToProgressStream(), 5000); // Infinite loop
};

// ✅ PREFER - Conditional polling with cleanup
startPolling() {
  if (this.pollInterval) return;
  this.pollInterval = setInterval(async () => {
    await this.checkProgress();
  }, 2000);
}

stopPolling() {
  if (this.pollInterval) {
    clearInterval(this.pollInterval);
    this.pollInterval = null;
  }
}
```

**Advantages**: More control, proper cleanup, no infinite reconnection.

### External API Pagination with Guard Rails

**When searching external APIs that paginate results:**

```python
async def search_with_pagination(query: str, target_date: str) -> str | None:
    """Search external API with pagination support.

    Guard rails:
    1. Max pages limit (prevent infinite loops)
    2. Stop on empty results (detect end of pagination)
    3. Timeout per page (prevent hanging)
    """
    max_pages = 10  # Guard rail 1: Prevent infinite loops
    page = 1

    while page <= max_pages:
        # Build paginated URL (?p=2, ?p=3, etc.)
        url = f"{base_url}?q={query}" if page == 1 else f"{base_url}?q={query}&p={page}"

        # Guard rail 3: Timeout per page request
        async with session.get(url, timeout=10) as response:
            if response.status != 200:
                logger.warning(f"Page {page} returned {response.status}, stopping")
                break

            results = parse_results(await response.text())

            # Guard rail 2: Stop if no results (end of pagination)
            if not results:
                logger.warning(f"Page {page} has no results, stopping pagination")
                break

            # Check each result for match
            for result in results:
                if matches_criteria(result, target_date):
                    logger.info(f"✅ Found match on page {page}")
                    return result

        page += 1

    return None  # Not found after all pages
```

**Why guard rails are critical**:
- ❌ Without max_pages: Infinite loop if item doesn't exist
- ❌ Without empty check: Unnecessary requests beyond last page
- ❌ Without timeout: Hanging requests can block entire process

### Business Logic First

**CRITICAL**: Understand domain logic before implementing

```python
# ❌ WRONG - Assuming author doesn't exist if books not found
if all_books_not_found:
    author.babelio_not_found = True  # INCORRECT assumption

# ✅ CORRECT - Business logic: author may exist even if books don't
if all_books_not_found:
    add_to_problematic_cases(author)  # Manual review required
    # Author may have other works on Babelio we don't know about
```

**Example**: Patrice Delbourg's book isn't on Babelio, but author may have other works there.

### Rate Limiting for External APIs

**CRITICAL**: Always respect external API limits

```python
# ✅ Add delays between requests
await asyncio.sleep(5)  # 5 seconds between Babelio requests
```

**Why**: Prevents ban/throttling from external services.

### Text Normalization for Accent and Typographic Insensitivity

**Pattern recommandé**: Utiliser `create_accent_insensitive_regex()` pour toutes les recherches textuelles.

**Normalisations automatiques**:
- **Accents**: é ↔ e, à ↔ a, ô ↔ o, etc.
- **Ligatures**: œ ↔ oe, æ ↔ ae
- **Tirets**: – (cadratin U+2013) ↔ - (simple U+002D)
- **Apostrophes**: ' (typographique U+2019) ↔ ' (simple U+0027)

**Backend (Python)**:
```python
from ..utils.text_utils import create_accent_insensitive_regex

# Créer un pattern regex insensible aux accents et caractères typographiques
regex_pattern = create_accent_insensitive_regex(search_term)

# Utiliser avec MongoDB $regex
search_query = {"field": {"$regex": regex_pattern, "$options": "i"}}
```

**Frontend (JavaScript)**:
```javascript
import { removeAccents } from '@/utils/textUtils';

// Normaliser pour comparaison simple
const normalized = removeAccents(searchText.toLowerCase());
const match = removeAccents(data.toLowerCase()).includes(normalized);
```

**Exemples concrets**:
- Recherche `"oeuvre"` trouve `"L'Œuvre au noir"` (ligature œ)
- Recherche `"Marie-Claire"` trouve `"Marie–Claire Blais"` (tiret cadratin)
- Recherche `"l'ami"` trouve `"L'ami retrouvé"` (apostrophe typographique)
- Recherche `"carrere"` trouve `"Carrère"` (accents)

**Références**:
- Issue #92: Recherche insensible aux accents
- Issue #173: Support des caractères typographiques (ligatures, tirets, apostrophes)

### Separation of Concerns - MongoDB Collections

**Use separate collections for different concerns:**

```python
# ✅ CORRECT - Separate collections
babelio_problematic_cases  # Manual review needed
livres                     # Normal data with babelio_not_found flag
auteurs                    # Normal data with babelio_not_found flag

# ❌ WRONG - Mixing concerns in one collection with type field
all_cases  # {type: "problematic" | "not_found" | "normal"}
```

**Why**: Clearer queries, better performance, easier maintenance.

### Fallback Strategies

**Implement graceful degradation:**

```python
# ✅ CORRECT - Try specific search, fallback to broader
result = search_title_and_author(title, author)
if not result:
    result = search_author_only(author)  # Broader search
    if result:
        result = scrape_from_author_page(result)
```

### Dynamic URL Configuration with Health Checks

**Pattern**: Multi-tier fallback for external service URLs that change frequently.

**Use case**: External services (Anna's Archive, mirrors, CDNs) change domains often due to blocks/migrations.

**Implementation** (3-tier strategy):

```python
class DynamicUrlService:
    """Service for dynamic URL configuration with health checks."""

    def __init__(self, settings, cache_service):
        self.settings = settings
        self.cache_service = cache_service
        self.hardcoded_default = "https://default.example.com"
        self._debug_log_enabled = os.getenv("SERVICE_DEBUG_LOG", "0") in ("1", "true")

    async def get_url(self) -> str:
        """Get current URL with 3-tier fallback."""
        # Priority 1: Environment variable + health check
        if self.settings.service_url:
            if await self._health_check_url(self.settings.service_url):
                return self.settings.service_url

        # Priority 2: Cached Wikipedia URL + health check
        cached = self.cache_service.get_cached("wikipedia_url", "service_name")
        if cached and (cached_url := cached.get("data")):
            if await self._health_check_url(cached_url):
                return cached_url

        # Re-scrape if cache expired or unhealthy
        scraped_url = await self._scrape_wikipedia_url()
        if scraped_url:
            self.cache_service.set_cached("wikipedia_url", scraped_url, "service_name")
            return scraped_url

        # Priority 3: Hardcoded default
        return self.hardcoded_default

    async def _health_check_url(self, url: str, timeout: int = 2) -> bool:
        """Health check with short timeout to detect dead URLs."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(url, timeout=timeout, allow_redirects=True):
                    return True
        except (TimeoutError, aiohttp.ClientError):
            return False
```

**Key principles**:

1. **Health checks**: Always verify URLs are accessible before using (2s timeout recommended)
2. **Cache with TTL**: Use 24h cache for scraped URLs to reduce Wikipedia requests
3. **Graceful degradation**: Multiple fallback levels ensure service continues even if primary sources fail
4. **Debug logging**: Control via env var for troubleshooting health check failures

**Benefits**:
- ✅ Resilience: Service continues even if Wikipedia is down
- ✅ Performance: 24h cache minimizes external requests
- ✅ Flexibility: Override via env var for specific deployments
- ✅ Automatic updates: URLs refresh from Wikipedia when cache expires

**Example**: `src/back_office_lmelp/services/annas_archive_url_service.py` (Issue #188)

### Validation - Double Layer Pattern

**For critical operations (LLM saves, payments, data modifications):**

```python
# BACKEND - Security validation (app.py)
def _validate_summary(summary: str) -> tuple[bool, str | None]:
    """Validate LLM-generated summary."""
    if not summary or not summary.strip():
        return False, "Le résumé est vide"
    if len(summary) > 50000:
        return False, "Résumé anormalement long (malformé)"
    if re.search(r' {100,}', summary):
        return False, "Trop d'espaces consécutifs (bug LLM)"
    if "SECTION_REQUISE" not in summary:
        return False, "Section requise manquante"
    return True, None

@app.post("/api/save")
async def save(data: dict):
    is_valid, error = _validate_summary(data["summary"])
    if not is_valid:
        raise HTTPException(status_code=400, detail=error)
    db.save(data)  # Save only if valid
```

```javascript
// FRONTEND - UX validation (Component.vue)
async saveSummary() {
  // Same validation criteria as backend
  const validation = this.validateSummary(this.summary);
  if (!validation.isValid) {
    this.error = validation.error;  // Show error immediately
    return;  // Stop before API call
  }

  // Call API only if frontend validation passes
  await axios.post('/api/save', { summary: this.summary });
}
```

**Benefits**:
- ✅ Frontend: Immediate feedback (no network wait)
- ✅ Backend: Security (validation enforced server-side)
- ✅ Consistency: Same validation logic both sides
- ✅ UX: Clear error messages with HTTP 400

### Debug Logging Strategy

**Pattern recommandé** : Conserver les logs debug dans le code et les contrôler via variables d'environnement.

**❌ MAUVAISE approche** (ancienne) :
```python
# Ajouter des logs debug pendant le développement
logger.info(f"🔍 [DEBUG] verify_book: search_term='{search_term}'")

# Les supprimer avant commit
# ❌ Perte d'informations de diagnostic pour le futur
```

**✅ BONNE approche** (actuelle) :
```python
# 1. Ajouter un flag de contrôle dans __init__
self._debug_log_enabled = os.getenv("FEATURE_DEBUG_LOG", "0").lower() in ("1", "true")

# 2. Garder les logs conditionnels dans le code
if self._debug_log_enabled:
    logger.info(f"🔍 [DEBUG] verify_book: search_term='{search_term}'")
    logger.info(f"🔍 [DEBUG] _find_best_book_match: {len(books)} livre(s)")

# 3. Pour contenus volumineux : écrire dans des fichiers (évite saturation terminal)
if self._debug_log_enabled:
    from pathlib import Path
    from datetime import datetime

    debug_dir = Path("/tmp/feature_debug")
    debug_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    debug_file = debug_dir / f"output_{timestamp}.txt"
    debug_file.write_text(large_content, encoding="utf-8")

    logger.info(f"📁 Fichier debug: {debug_file}")
```

**Avantages** :
- ✅ Logs disponibles pour diagnostic futur (activation via env var)
- ✅ Pas de pollution en production (désactivé par défaut)
- ✅ Facilite le debugging des problèmes complexes (matching, scraping, etc.)
- ✅ Historique conservé pour comprendre les décisions passées
- ✅ Fichiers debug partageables dans issues GitHub (diagnostics post-mortem)
- ✅ Pas de saturation terminal avec contenus volumineux (>1MB)

**Convention de nommage** :
- Pattern : `{FEATURE}_DEBUG_LOG` (ex: `AVIS_CRITIQUES_DEBUG_LOG`, `BABELIO_DEBUG_LOG`)
- Valeurs : `0` (défaut, désactivé) ou `1`/`true` (activé)
- Scope : Une variable par feature/service majeur
- Répertoire debug : `/tmp/{feature}_debug/` pour fichiers temporaires

**Configuration développement** :
```bash
# scripts/start-dev.sh active automatiquement les logs debug pertinents
export BABELIO_DEBUG_LOG=1
export AVIS_CRITIQUES_DEBUG_LOG=1

# En production : toujours désactivé (valeur par défaut)
```

**Exemples de logs debug utiles** :
- Comparaisons de similarité (matching auteur/titre)
- Étapes de scraping et parsing
- Décisions de fallback
- Résultats intermédiaires de traitements complexes
- Sorties brutes de LLM (génération de contenu)
- Contenu rejeté par validation (diagnostics d'échec)

**Documentation** :
- Variables disponibles : Voir `docs/user/debug-logging.md`
- Configuration Docker : Voir docker-lmelp issue #38
- Variables d'environnement dev : Voir `docs/dev/environment-variables.md`

## Documentation Guidelines

### Writing Documentation
- ✅ Describe **current state** (what it does now)
- ✅ Technical specifications and usage examples
- ❌ NO historical references ("Issue #X improved this...")
- ❌ NO evolution narratives ("we first implemented X, then Y...")
- ❌ NO test counts in documentation

**See [detailed guide](docs/dev/claude-ai-guide.md#documentation-guidelines) for examples.**

## Dependencies

### Backend
- FastAPI, MongoDB (motor/pymongo)
- pandas, numpy
- beautifulsoup4, html5lib
- pytest, ruff, mypy, pre-commit

### Frontend
- Vue.js 3, Vite 5.0+
- Axios, lodash.debounce
- Vitest, @vue/test-utils, jsdom

## Quick Fix Commands

```bash
# Fix formatting automatically
ruff format .

# Check linting issues
ruff check . --output-format=github

# Fix specific file
ruff format path/to/file.py
ruff check path/to/file.py --fix

# Reinstall pre-commit hooks (after adding type stubs)
pre-commit clean
pre-commit install
```

## CI/CD Pipeline

- **Backend tests**: Python 3.11 and 3.12 matrix
- **Frontend tests**: Node.js 18 with npm cache
- **Documentation**: MkDocs build and GitHub Pages deployment
- **Security scan**: detect-secrets on all files
- **Quality gate**: All test suites must pass before deployment

## Git Best Practices

- ✅ Use separate commits instead of amending pushed commits
- ❌ AVOID `git commit --amend` on branches already pushed to remote
- ✅ Use descriptive commit messages
- ❌ NEVER force push to main/master

## Additional Resources

- **Production Documentation**: https://castorfou.github.io/back-office-lmelp/
- **Detailed Development Guide**: [docs/dev/claude-ai-guide.md](docs/dev/claude-ai-guide.md)
- **API Documentation**: Start backend and visit `/docs` endpoint
- **OpenAPI Specification**: `/openapi.json` endpoint
