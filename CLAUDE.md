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
   - **Why critical**: Tests can pass with invented mocks but fail in production (see Issue #96)
3. **Use helper function pattern** for services with complex dependencies
4. **Patch singleton instances** directly when using local imports
5. **Verify database updates** with `mock_collection.update_one.assert_called_with(...)`

### Frontend Testing - Key Rules

1. **Reset mocks between tests**: Use `vi.resetAllMocks()` in `beforeEach`
2. **Prefer `mockResolvedValueOnce`** over persistent `mockImplementation`
3. **Watch for mock pollution**: Closures in `mockImplementation` persist across tests

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

### Text Normalization for Matching

**Chain normalizations for reliable matching:**

```python
def normalize_text(text: str) -> str:
    """Normalize text for reliable matching."""
    text = text.lower()
    text = text.replace('œ', 'oe').replace('æ', 'ae')  # Ligatures
    text = text.replace(''', "'")  # Typographic apostrophes
    text = re.sub(r'[^\w\s]', '', text)  # Remove punctuation
    return text
```

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
