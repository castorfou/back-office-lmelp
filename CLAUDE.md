# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **full-stack application** for managing a database related to the lmelp project, consisting of:
- **Backend**: Python FastAPI application with MongoDB integration
- **Frontend**: Vue.js 3 SPA with Vite build system
- **Architecture**: Hybrid project with separate backend (Python/uv) and frontend (Node.js/npm) toolchains

## Development Environment

The project is designed to work in VS Code with devcontainers (Docker-based development environment). It uses **dual toolchains**:
- **Backend**: uv for Python dependency management
- **Frontend**: npm for Node.js dependency management

## Essential Commands

### Backend Setup and Commands
```bash
# Install Python dependencies
uv pip install -e .

# Install pre-commit hooks (required for contributors)
pre-commit install

# Run backend application (automatic port selection)
PYTHONPATH=/workspaces/back-office-lmelp/src python -m back_office_lmelp.app

# Or specify a specific port if needed
API_PORT=54321 PYTHONPATH=/workspaces/back-office-lmelp/src python -m back_office_lmelp.app

# Run backend linting
ruff check . --output-format=github

# Format backend code
ruff format .

# Type checking
mypy src/

# Run backend tests
PYTHONPATH=/workspaces/back-office-lmelp/src pytest tests/ -v --cov=src --cov-report=term-missing

# Run pre-commit hooks manually
pre-commit run --all-files
```

### Frontend Setup and Commands
```bash
# Install frontend dependencies
cd frontend && npm ci

# Run frontend tests
# IMPORTANT: Always specify full path to avoid directory confusion
cd /workspaces/back-office-lmelp/frontend && npm test -- --run

# Start development server
cd /workspaces/back-office-lmelp/frontend && npm run dev

# Build for production
cd /workspaces/back-office-lmelp/frontend && npm run build

# Preview production build
cd /workspaces/back-office-lmelp/frontend && npm run preview
```

### Command Execution Best Practices
**IMPORTANT**: To avoid directory confusion when switching between backend/frontend:

1. **Always use absolute paths** in commands:
   ```bash
   # ✅ Good - absolute paths
   cd /workspaces/back-office-lmelp/frontend && npm test -- --run
   PYTHONPATH=/workspaces/back-office-lmelp/src pytest tests/ -v

   # ❌ Bad - relative paths can cause confusion
   cd frontend && npm test -- --run
   cd ../backend && pytest tests/
   ```

2. **Verify working directory** before executing commands:
   ```bash
   pwd  # Always check current directory
   ```

3. **Use single-command execution** with `&&` to chain directory changes:
   ```bash
   cd /workspaces/back-office-lmelp/frontend && npm test -- --run && cd /workspaces/back-office-lmelp
   ```

4. **Return to project root** after frontend operations:
   ```bash
   cd /workspaces/back-office-lmelp  # Always return to project root when done
   ```

### Full Test Suite
```bash
# Run all tests (backend + frontend)
PYTHONPATH=/workspaces/back-office-lmelp/src pytest tests/ -v && cd frontend && npm test -- --run
```

### Development Scripts
```bash
# Start both backend and frontend with unified script (recommended)
./scripts/start-dev.sh
```

### Documentation Commands
```bash
# Serve documentation locally (port 8000)
mkdocs serve

# Build documentation (for deployment)
mkdocs build --strict

# View production documentation
open https://castorfou.github.io/back-office-lmelp/
```

## Project Structure
```
├── src/                        # Backend Python source code
│   └── back_office_lmelp/      # Main FastAPI application
│       ├── app.py              # FastAPI app and routes
│       ├── models/             # Data models
│       ├── services/           # Business logic (MongoDB, etc.)
│       └── utils/              # Utilities (memory guard, etc.)
├── frontend/                   # Frontend Vue.js application
│   ├── src/                    # Vue.js source code
│   │   ├── components/         # Vue components (EpisodeSelector, EpisodeEditor)
│   │   ├── views/              # Vue views/pages
│   │   ├── services/           # Frontend services (API calls)
│   │   └── utils/              # Frontend utilities
│   ├── tests/                  # Frontend tests (Vitest)
│   │   ├── unit/               # Unit tests (EpisodeSelector, EpisodeEditor)
│   │   └── integration/        # Integration tests (HomePage)
│   ├── package.json            # Frontend dependencies
│   ├── package-lock.json       # Locked frontend dependencies
│   └── vite.config.js          # Vite configuration
├── scripts/                    # Development and utility scripts
│   └── start-dev.sh           # Unified development server launcher
├── tests/                      # Backend tests (pytest)
├── docs/                       # Documentation (MkDocs)
│   ├── dev/                   # Developer documentation
│   ├── user/                  # User documentation
│   └── index.md               # Documentation homepage
├── data/                       # Data files
│   ├── raw/                   # Raw data
│   └── processed/             # Processed data
├── notebooks/                  # Jupyter notebooks
├── pyproject.toml             # Backend Python configuration
├── mkdocs.yml                 # MkDocs configuration
├── .github/workflows/         # CI/CD pipeline (includes docs deployment)
└── CLAUDE.md                  # This file
```

## Code Quality Standards

### Backend (Python)
- **Linting & Formatting**: Uses Ruff (replaces flake8, black, isort)
- **Type Checking**: MyPy with progressive strictness
- **Line Length**: 88 characters (consistent with Black)
- **Python Version**: Requires Python 3.11+

### Frontend (Vue.js/TypeScript)
- **Testing Framework**: Vitest with @vue/test-utils
- **Build Tool**: Vite 5.0+
- **Node Version**: 18+ (specified in CI/CD)
- **Package Management**: npm with package-lock.json committed

### Shared Standards
- **Pre-commit Hooks**: Enforces code quality, security scanning, and format consistency
- **CI/CD Pipeline**: Validates both backend and frontend tests (38 total)
- **Security**: detect-secrets scanning on all commits

## Linting and Code Quality Requirements

### CRITICAL: Pre-commit Validation
**ALWAYS run linting and formatting checks before committing any changes**:

```bash
# Backend linting (MUST pass)
ruff check . --output-format=github

# Backend formatting (auto-fix)
ruff format .

# Type checking (MUST pass)
mypy src/

# Run all pre-commit hooks
pre-commit run --all-files
```

### Expected Linting Standards

#### Backend (Python) - Ruff Configuration
- **No linting errors allowed**: All `ruff check` issues must be resolved
- **Auto-formatting required**: Always run `ruff format .` before committing
- **Line length**: 88 characters maximum (Black-compatible)
- **Import sorting**: Automatic via Ruff (replaces isort)
- **Code style**: PEP 8 compliance with modern Python practices

#### Common Linting Issues to Avoid
- **W291**: Trailing whitespace - remove all trailing spaces
- **W293**: Blank line contains whitespace - ensure blank lines are completely empty
- **E501**: Line too long - keep lines under 88 characters
- **F401**: Unused imports - remove or mark with `# noqa: F401` if intentional
- **F841**: Unused variables - remove or prefix with `_` if intentional

#### Type Checking Requirements
- **MyPy compliance**: All type annotations must be valid
- **Progressive typing**: New code should include type hints
- **Import resolution**: Use proper module imports for type checking

#### CRITICAL: MyPy Type Stubs with Pre-commit

**Problem**: When adding a new Python library that requires type stubs (e.g., `beautifulsoup4`), mypy in pre-commit may fail with `import-not-found` even if the types are installed in your local environment.

**Root Cause**: Pre-commit runs mypy in an **isolated environment** with its own dependencies defined in `.pre-commit-config.yaml`. Installing type stubs via `pyproject.toml` or locally does NOT make them available to pre-commit's mypy.

**❌ WRONG Solution (avoid this)**:
```python
# Don't use type: ignore to suppress the error
from bs4 import BeautifulSoup  # type: ignore[import-untyped]
```

**✅ CORRECT Solution (always do this)**:

1. Add type stubs to **both** `pyproject.toml` dev dependencies AND `.pre-commit-config.yaml`:

```toml
# pyproject.toml
[project.optional-dependencies]
dev = [
    "mypy",
    "types-beautifulsoup4",  # ✅ For local mypy runs
    ...
]
```

```yaml
# .pre-commit-config.yaml
- repo: https://github.com/pre-commit/mirrors-mypy
  hooks:
    - id: mypy
      additional_dependencies:
        - types-beautifulsoup4  # ✅ For pre-commit mypy runs
        ...
```

2. Reinstall pre-commit hooks to pick up new dependencies:
```bash
pre-commit clean
pre-commit install
```

**Why this matters**:
- Maintains type safety without suppressing errors
- Ensures CI/CD and local environments have same type checking
- Avoids accumulating `type: ignore` comments that hide real issues

**Example from Issue #85**:
- Added `beautifulsoup4` for scraping
- Initial error: `Cannot find implementation or library stub for module named "bs4"`
- Fixed by adding `types-beautifulsoup4` to both locations
- Result: Clean type checking in both local and pre-commit environments

#### Pre-commit Hook Enforcement
The project uses pre-commit hooks that will **automatically block commits** if:
- Ruff linting fails
- MyPy type checking fails
- Security issues detected by detect-secrets
- File formatting is inconsistent

#### Quick Fix Commands
```bash
# Fix most formatting issues automatically
ruff format .

# Check what still needs manual fixing
ruff check . --output-format=github

# Fix specific file
ruff format path/to/file.py
ruff check path/to/file.py --fix
```

## Key Configuration Notes

### Backend Configuration
- Ruff configuration excludes data/, models/, logs/, and .jupyter/ directories
- MyPy ignores missing imports for common data science libraries
- pytest with coverage reporting (85% current coverage)

### Frontend Configuration
- Vitest configuration in frontend/vite.config.js
- Tests use jsdom environment for DOM manipulation
- Vue Test Utils for component testing

### CI/CD Pipeline
- **Backend tests**: Python 3.11 and 3.12 matrix
- **Frontend tests**: Node.js 18 with npm cache
- **Documentation**: MkDocs build and GitHub Pages deployment
- **Security scan**: detect-secrets on all files
- **Quality gate**: All test suites must pass before deployment

## Testing

### Backend Tests (116 tests)
- Location: `tests/` directory
- Framework: pytest with coverage
- Command: `PYTHONPATH=/workspaces/back-office-lmelp/src uv run pytest tests/ -v`
- Coverage: API endpoints, MongoDB service, memory guard utilities

### Frontend Tests (31 tests)
- Location: `frontend/tests/` directory
- Framework: Vitest with @vue/test-utils
- Command: `cd frontend && npm test -- --run`
- Coverage:
  - **Unit tests**: EpisodeSelector (7), EpisodeEditor (12)
  - **Integration tests**: HomePage (7)

## Development Workflow

### Test-Driven Development (TDD)
**IMPORTANT**: Always follow TDD methodology for ALL code changes, including small modifications and UX improvements.

#### TDD Process (Red-Green-Refactor)
1. **Write failing tests first** - Even for small changes, write tests that capture the expected behavior
2. **Implement minimal code** to make tests pass
3. **Refactor** while keeping tests green
4. **Update tests** if behavior changes, but always test-first

#### Examples requiring TDD approach:
- Adding new component properties or methods
- Modifying UI behavior (save status, validation, etc.)
- Changing API responses or database interactions
- UX improvements that alter component state

#### Why TDD for all changes:
- Prevents regression bugs
- Documents expected behavior
- Ensures code quality consistency
- Maintains test coverage
- Facilitates safe refactoring

**Never implement code changes without corresponding tests, regardless of change size.**

### Vitest Mock Pollution - Critical Testing Pitfall

**IMPORTANT**: When writing Vitest tests, be aware of mock pollution between tests, especially with `mockImplementation`.

#### The Problem: Persistent Mock Implementations

```javascript
// ❌ DANGER: mockImplementation is PERSISTENT across tests
mockService.method.mockImplementation((arg) => {
  const someVariable = getCurrentTestData(); // Creates a closure
  return someVariable;
});
```

**What happens:**
1. `mockImplementation` creates a **closure** that captures variables from the test scope
2. This implementation persists for **all subsequent tests** until explicitly reset
3. The next test inherits stale closures from previous tests

**Real example from Issue #75 debugging:**
- Test "Adrien Bosque" configured `mockBabelioService.verifyBook.mockImplementation` with closure capturing `authorResponse = "Adrien Bosc"`
- Test "Fabrice Caro" ran next and inherited the closure, returning "Adrien Bosc" instead of "Fabcaro"
- Result: Test failed with mysterious wrong data

#### The Solution: Always Reset Mocks

```javascript
// ✅ GOOD: Reset mocks before tests that need clean state
it('my independent test', async () => {
  vi.resetAllMocks();  // Clears implementations + call history

  // Re-inject service with fresh mocks if needed
  service = new Service({ dependency: mockDependency });

  // Now configure your mocks...
});
```

#### Mock Types Comparison

```javascript
// CONSUMABLE (used once, then gone)
mock.mockResolvedValueOnce(value)     // ✅ Safe, auto-cleaned
mock.mockRejectedValueOnce(error)     // ✅ Safe, auto-cleaned

// PERSISTENT (stays until reset)
mock.mockImplementation(fn)            // ⚠️ DANGER: closure pollution
mock.mockResolvedValue(value)          // ⚠️ DANGER: persists across tests
mock.mockRejectedValue(error)          // ⚠️ DANGER: persists across tests

// CLEANUP METHODS
vi.clearAllMocks()    // Clears call history ONLY (keeps implementations)
vi.resetAllMocks()    // Clears EVERYTHING (implementations + history) ✅
vi.restoreAllMocks()  // Restores original implementations
```

#### Best Practices

1. **Always use `vi.resetAllMocks()` in `beforeEach`** or at the start of tests that need isolation
2. **Prefer `mockResolvedValueOnce`** over `mockImplementation` when possible
3. **Document persistent mocks** with comments explaining why `mockImplementation` is needed
4. **Test in isolation**: If a test mysteriously uses wrong data, check for mock pollution from previous tests
5. **Watch for closures**: Variables captured in `mockImplementation` callbacks persist across tests

#### Quick Debugging Checklist

If a test fails with unexpected data:
- [ ] Check if previous test used `mockImplementation`
- [ ] Add `vi.resetAllMocks()` at start of failing test
- [ ] Log mock call history: `console.log(mock.mock.calls)`
- [ ] Verify mock configuration order
- [ ] Check if `beforeEach` actually runs between tests

**Reference**: Issue #75 - Mock pollution between "Captured Cases" and "Fabrice Caro" test

### Verification Best Practices
**CRITICAL**: Always verify the actual state before marking tasks as completed.

- **Before marking any task as 'completed'**: Use appropriate tools to verify the action is actually accomplished
- **For Pull Requests**: Use `gh pr view <number>` to confirm merge status before declaring success
- **For deployments**: Check actual deployment status, not just pipeline success
- **For file changes**: Use `Read` or `ls` to verify files exist/changed as expected
- **For test results**: Verify all tests actually pass, not just assume from commands run

**Never rely solely on user declarations of intent** - always verify the real world state using available tools.

### Backend Testing - Mocking Services with Complex Dependencies

**CRITICAL**: When testing services with multiple injected dependencies (MongoDB, cache services, external APIs), use the **helper function pattern** instead of pytest fixtures for mocking.

#### The Problem: Pytest Fixtures Don't Work Well with Dependency Injection

```python
# ❌ PROBLEMATIC: Pytest fixtures with @patch can fail with local imports
@pytest.fixture
def collections_service(mock_mongodb_service):
    with patch.object(CollectionsManagementService, "mongodb_service", mock_mongodb_service):
        service = CollectionsManagementService()
        return service
```

**Why this fails:**
1. Services often use **local imports** inside methods (e.g., `from bson import ObjectId`)
2. Patching at module level doesn't intercept calls made after service instantiation
3. Dependency injection happens in `__init__`, but method-level imports bypass mocks
4. Error: `"Connexion MongoDB non établie"` - the mock never gets injected properly

#### The Solution: Helper Function Pattern

**✅ GOOD: Create mocked services with direct attribute assignment**

```python
def create_mocked_service():
    """Crée un service avec tous les mocks configurés.

    Pattern recommandé pour tester des services avec dépendances injectées.
    Évite les problèmes de pytest fixtures avec patch.object().
    """
    from bson import ObjectId

    service = CollectionsManagementService()

    # Mock mongodb_service directement sur l'instance
    mock_mongodb = Mock()
    mock_mongodb.create_author_if_not_exists.return_value = ObjectId("507f1f77bcf86cd799439014")
    mock_mongodb.create_book_if_not_exists.return_value = ObjectId("507f1f77bcf86cd799439015")
    mock_mongodb.update_book_validation.return_value = None
    mock_mongodb.update_avis_critique = Mock(return_value=True)
    mock_mongodb.get_avis_critique_by_id.return_value = None

    # Injection directe (bypass du __init__)
    service.mongodb_service = mock_mongodb
    service._mock_mongodb = mock_mongodb  # Pour accès dans les tests

    return service


class TestMyService:
    def test_my_feature(self):
        # Arrange
        service = create_mocked_service()

        # Configurer le mock pour ce test spécifique
        service._mock_mongodb.get_avis_critique_by_id.return_value = {
            "_id": "507f...",
            "summary": "Original text"
        }

        # Mock des services externes (livres_auteurs_cache_service)
        with patch("back_office_lmelp.services.collections_management_service.livres_auteurs_cache_service") as mock_cache:
            mock_cache.mark_as_processed.return_value = True
            mock_cache.is_summary_corrected.return_value = False

            # Act
            service.handle_book_validation(book_data)

            # Assert
            assert service._mock_mongodb.update_avis_critique.called
            call_args = service._mock_mongodb.update_avis_critique.call_args[0]
            assert call_args[1]["summary"] == "Expected corrected text"
```

#### When to Use Helper Functions vs Fixtures

**Use helper functions when:**
- ✅ Service has multiple dependencies (MongoDB, cache, external APIs)
- ✅ Dependencies are set via `__init__` or attribute assignment
- ✅ Methods use local imports (`from bson import ObjectId`)
- ✅ You need fine-grained control over mock configuration per test

**Use fixtures when:**
- ✅ Mocking simple external modules (no dependency injection)
- ✅ Setting up test data (dictionaries, lists, test cases)
- ✅ Sharing configuration across multiple tests
- ✅ No complex service initialization

#### Best Practices

1. **Name helper clearly**: `create_mocked_service()` not `get_service()`
2. **Document why**: Add docstring explaining the pattern avoids fixture issues
3. **Expose mock for tests**: Store mock in `service._mock_xyz` for assertions
4. **Configure defaults**: Set safe default return values (empty lists, None, etc.)
5. **Per-test customization**: Override specific mock behaviors in each test

#### Example: Testing Service with MongoDB + Cache Dependencies

```python
def create_mocked_service():
    """Pattern pour tester CollectionsManagementService avec mocks MongoDB + cache."""
    service = CollectionsManagementService()

    # Mock MongoDB service
    mock_mongodb = Mock()
    mock_mongodb.create_author_if_not_exists.return_value = ObjectId("507f1f77bcf86cd799439014")
    mock_mongodb.create_book_if_not_exists.return_value = ObjectId("507f1f77bcf86cd799439015")
    mock_mongodb.get_avis_critique_by_id.return_value = None  # Default: pas d'avis
    mock_mongodb.update_avis_critique = Mock(return_value=True)

    service.mongodb_service = mock_mongodb
    service._mock_mongodb = mock_mongodb

    return service


def test_should_update_summary_with_correction():
    # Arrange
    service = create_mocked_service()

    # Override pour ce test spécifique
    service._mock_mongodb.get_avis_critique_by_id.return_value = {
        "_id": "507f...",
        "summary": "Original | Alain Mabancou | Book |"
    }

    book_data = {
        "cache_id": "507f...",
        "avis_critique_id": "507f...",
        "auteur": "Alain Mabancou",
        "titre": "Book",
        "user_validated_author": "Alain Mabanckou",  # Correction
        "user_validated_title": "Book"
    }

    with patch("...livres_auteurs_cache_service") as mock_cache:
        mock_cache.is_summary_corrected.return_value = False
        mock_cache.mark_summary_corrected.return_value = True

        # Act
        service.handle_book_validation(book_data)

        # Assert
        assert service._mock_mongodb.update_avis_critique.called
        updates = service._mock_mongodb.update_avis_critique.call_args[0][1]
        assert "Alain Mabanckou" in updates["summary"]
        assert "Alain Mabancou" not in updates["summary"]
```

#### Common Pitfalls to Avoid

**❌ Don't use module-level patching for injected services**
```python
# ❌ NE FONCTIONNE PAS avec dependency injection
@patch("back_office_lmelp.services.collections_management_service.mongodb_service")
def test_something(mock_mongodb):
    service = CollectionsManagementService()  # mongodb_service n'est pas mock
```

**❌ Don't rely on fixtures for complex service mocking**
```python
# ❌ FRAGILE: Fixtures + patch.object = problèmes avec imports locaux
@pytest.fixture
def service(mock_mongodb):
    with patch.object(Service, "mongodb_service", mock_mongodb):
        return Service()
```

**✅ Use helper functions with direct attribute assignment**
```python
# ✅ ROBUSTE: Helper function + attribute injection
def create_mocked_service():
    service = Service()
    service.mongodb_service = Mock()  # Injection directe
    return service
```

**Reference**: Issue #67 - Learned this pattern while implementing summary correction tests

### Backend Testing - Mocking Singleton Services with Local Imports

**CRITICAL**: When testing code that uses **singleton services imported locally inside methods**, standard module-level patching does NOT work. This is a common pitfall that causes "Connexion MongoDB non établie" errors even when mocks are properly configured.

#### The Problem: Local Imports Bypass Module-Level Patches

```python
# ❌ PROBLEMATIC: Service method with local import of singleton
class CollectionsManagementService:
    def handle_book_validation(self, book_data):
        # Local import inside method
        from ..services.livres_auteurs_cache_service import livres_auteurs_cache_service

        # This calls the REAL singleton, not the mock!
        livres_auteurs_cache_service.mark_as_processed(cache_id, author_id, book_id)
```

**Why module-level patching fails:**
```python
# ❌ This doesn't work because import happens AFTER patch is applied
def test_something():
    with patch("back_office_lmelp.services.collections_management_service.livres_auteurs_cache_service"):
        service.handle_book_validation(book_data)  # Import happens here, bypasses mock!
```

**What happens:**
1. Test starts, applies patch to module namespace
2. Method executes `from ..services.livres_auteurs_cache_service import livres_auteurs_cache_service`
3. Python resolves import from **original module**, not patched namespace
4. Real singleton instance is used, tries to access real MongoDB
5. Error: `"Connexion MongoDB non établie"`

#### The Solution: Patch the Global Singleton Instance Directly

**✅ GOOD: Patch methods on the global instance, not the module**

```python
# Pattern 1: Direct patching (verbose but explicit)
def test_with_singleton_service():
    with (
        patch("back_office_lmelp.services.livres_auteurs_cache_service.livres_auteurs_cache_service.mark_as_processed", return_value=True),
        patch("back_office_lmelp.services.livres_auteurs_cache_service.livres_auteurs_cache_service.is_summary_corrected", return_value=False),
        patch("back_office_lmelp.services.livres_auteurs_cache_service.livres_auteurs_cache_service.mark_summary_corrected", return_value=True),
    ):
        service.handle_book_validation(book_data)
        assert service._mock_mongodb.update_avis_critique.called
```

**Pattern 2: Helper function (recommended for DRY)**

```python
def patch_cache_service(is_already_corrected=False):
    """Returns tuple of patches for livres_auteurs_cache_service singleton.

    Usage:
        patches = patch_cache_service()
        with patches[0], patches[1], patches[2]:
            # test code
    """
    from unittest.mock import patch as mock_patch

    return (
        mock_patch("back_office_lmelp.services.livres_auteurs_cache_service.livres_auteurs_cache_service.mark_as_processed", return_value=True),
        mock_patch("back_office_lmelp.services.livres_auteurs_cache_service.livres_auteurs_cache_service.is_summary_corrected", return_value=is_already_corrected),
        mock_patch("back_office_lmelp.services.livres_auteurs_cache_service.livres_auteurs_cache_service.mark_summary_corrected", return_value=True),
    )


def test_with_helper():
    service = create_mocked_service()
    book_data = {...}

    # Apply all patches from helper
    patches = patch_cache_service()
    with patches[0], patches[1], patches[2]:
        service.handle_book_validation(book_data)

        # Assertions
        assert service._mock_mongodb.update_avis_critique.called
```

#### When to Use This Pattern

**Use singleton instance patching when:**
- ✅ Service uses `from ..module import singleton_instance` **inside methods**
- ✅ Standard module patching fails with "not connected" or "not initialized" errors
- ✅ The imported object is a **singleton instance** (not a class)
- ✅ The singleton is instantiated at module level (`service = Service()`)

**Use standard module patching when:**
- ✅ Imports happen at **module level** (top of file)
- ✅ Importing a **class**, not an instance
- ✅ No local imports inside methods

#### Complete Example: Testing with Singleton + Local Imports

```python
# File: tests/test_avis_critique_summary_correction.py

from unittest.mock import Mock, patch
from bson import ObjectId
from back_office_lmelp.services.collections_management_service import CollectionsManagementService


def create_mocked_service():
    """Helper: Create service with mocked MongoDB dependencies."""
    service = CollectionsManagementService()

    # Mock mongodb_service
    mock_mongodb = Mock()
    mock_mongodb.create_author_if_not_exists.return_value = ObjectId("507f1f77bcf86cd799439014")
    mock_mongodb.create_book_if_not_exists.return_value = ObjectId("507f1f77bcf86cd799439015")
    mock_mongodb.update_avis_critique = Mock(return_value=True)
    mock_mongodb.get_avis_critique_by_id.return_value = None

    # Mock collections
    mock_mongodb.avis_critiques_collection = Mock()
    mock_mongodb.livres_collection = Mock()

    service.mongodb_service = mock_mongodb
    service._mock_mongodb = mock_mongodb

    return service


def patch_cache_service(is_already_corrected=False):
    """Returns patches for livres_auteurs_cache_service singleton."""
    from unittest.mock import patch as mock_patch

    return (
        mock_patch("back_office_lmelp.services.livres_auteurs_cache_service.livres_auteurs_cache_service.mark_as_processed", return_value=True),
        mock_patch("back_office_lmelp.services.livres_auteurs_cache_service.livres_auteurs_cache_service.is_summary_corrected", return_value=is_already_corrected),
        mock_patch("back_office_lmelp.services.livres_auteurs_cache_service.livres_auteurs_cache_service.mark_summary_corrected", return_value=True),
    )


def test_should_update_summary_with_correction():
    # Arrange
    service = create_mocked_service()
    service._mock_mongodb.get_avis_critique_by_id.return_value = {
        "_id": "507f...",
        "summary": "Original | Alain Mabancou | Book |"
    }

    book_data = {
        "cache_id": "507f...",
        "avis_critique_id": "507f...",
        "auteur": "Alain Mabancou",
        "titre": "Book",
        "user_validated_author": "Alain Mabanckou",  # Correction
        "user_validated_title": "Book"
    }

    # Act - Patch singleton before calling method with local import
    patches = patch_cache_service()
    with patches[0], patches[1], patches[2]:
        service.handle_book_validation(book_data)

    # Assert
    assert service._mock_mongodb.update_avis_critique.called
    updates = service._mock_mongodb.update_avis_critique.call_args[0][1]
    assert "Alain Mabanckou" in updates["summary"]
    assert "Alain Mabancou" not in updates["summary"]
```

#### Why Tuple of Patches?

Python's `with` statement requires each patch to be applied individually:

```python
# ✅ Correct: Unpack tuple manually
patches = patch_cache_service()
with patches[0], patches[1], patches[2]:
    # test code

# ❌ Wrong: Can't use tuple directly
with patch_cache_service():  # TypeError: tuple doesn't support context manager protocol
    # test code

# ❌ Wrong: Can't unpack with *
with (*patch_cache_service(),):  # Syntax error / TypeError
    # test code
```

**Alternative**: Use `contextlib.ExitStack` for dynamic patch management:

```python
from contextlib import ExitStack

def test_with_exit_stack():
    patches = patch_cache_service()
    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)

        # test code
```

#### Common Pitfalls

**❌ Patching the wrong path**
```python
# Wrong: Patches module namespace, not singleton instance
with patch("back_office_lmelp.services.collections_management_service.livres_auteurs_cache_service"):
    pass  # Local import still gets real singleton
```

**❌ Patching too late**
```python
# Wrong: Service already called method before patch applied
service.handle_book_validation(book_data)  # Uses real singleton
with patch("...livres_auteurs_cache_service.mark_as_processed"):
    pass  # Too late!
```

**✅ Correct timing**
```python
patches = patch_cache_service()
with patches[0], patches[1], patches[2]:
    service.handle_book_validation(book_data)  # Patches active during call
```

#### Architecture Implications

**Why singletons with local imports are problematic:**
1. **Testability**: Harder to mock, requires instance-level patching
2. **Import cycles**: Local imports often indicate circular dependencies
3. **Predictability**: Harder to reason about when dependencies are resolved

**Better alternatives:**
```python
# ✅ Better: Dependency injection
class CollectionsManagementService:
    def __init__(self, cache_service=None):
        self.cache_service = cache_service or livres_auteurs_cache_service

    def handle_book_validation(self, book_data):
        # No local import, use injected dependency
        self.cache_service.mark_as_processed(cache_id, author_id, book_id)

# Test with easy mocking
def test_with_di():
    mock_cache = Mock()
    service = CollectionsManagementService(cache_service=mock_cache)
    service.handle_book_validation(book_data)
    mock_cache.mark_as_processed.assert_called_once()
```

**When to use local imports (acceptable cases):**
- Breaking circular import cycles (temporary fix)
- Lazy loading for performance (rare)
- Type checking only (`if TYPE_CHECKING:`)

**Reference**: Issue #67 - Discovered this pattern after 12 failed test attempts with standard mocking approaches. This documentation serves as a critical reference for future test writing when dealing with singleton services.

### Backend Testing - Writing Proper TDD Tests with Mocks

**CRITICAL**: When writing backend tests, ALWAYS use mocks for external dependencies (MongoDB, APIs, services). NEVER use real database connections or external API calls in unit tests.

#### Why Mocking is Essential

- **CI/CD Compatibility**: Tests must run in isolated environments without external dependencies
- **Speed**: Mocked tests run in milliseconds instead of seconds
- **Reliability**: No network failures, no database setup required
- **Isolation**: Each test is independent and doesn't affect real data
- **Reproducibility**: Same results every time, no flaky tests

#### Anti-Pattern: Real Database Connections

**❌ MAUVAIS - Tests avec connexion MongoDB réelle**

```python
# ❌ NE JAMAIS FAIRE CELA
@pytest.mark.asyncio
async def test_with_real_mongodb():
    # Mauvais: Utilise la vraie connexion MongoDB
    cache_collection = livres_auteurs_cache_service.mongodb_service.db["livresauteurs_cache"]

    # Mauvais: Insère dans la vraie base de données
    test_id = cache_collection.insert_one({
        "auteur": "Albert Camus",
        "titre": "L'Étranger",
        "episode_oid": "test123"
    }).inserted_id

    # Mauvais: Appelle la vraie API Babelio
    books = await service.get_books_by_episode_oid_async("test123")

    # Problèmes:
    # - Requiert MongoDB actif
    # - Requiert connexion Internet
    # - Pollution de la base de données
    # - Tests lents et fragiles
    # - Impossible en CI/CD
```

**Pourquoi c'est inacceptable:**
1. Échoue en CI/CD (pas de MongoDB disponible)
2. Pollue la base de données avec des données de test
3. Dépend de services externes (Babelio API)
4. Tests lents (attente réseau, I/O disque)
5. Non reproductible (données changeantes)

#### Correct Pattern: Full Mocking

**✅ BON - Tests avec mocks complets**

```python
from unittest.mock import Mock, patch, AsyncMock
from bson import ObjectId
import pytest


@pytest.mark.asyncio
async def test_when_url_without_publisher_should_scrape_and_update_cache():
    """
    Quand babelio_url présente sans publisher, scrape et update cache.
    """
    from back_office_lmelp.services.livres_auteurs_cache_service import (
        LivresAuteursCacheService,
    )

    # Arrange - Données de test
    test_id = ObjectId()
    test_episode_oid = "68c707ad6e51b9428ab87e9e" # pragma: allowlist secret
    cache_entry = {
        "_id": test_id,
        "auteur": "Albert Camus",
        "titre": "L'Étranger",
        "episode_oid": test_episode_oid,
        "babelio_url": "https://www.babelio.com/livres/Camus-Letranger/3874",
        # Pas de champ babelio_publisher (champ absent, pas None)
    }

    # Mock MongoDB collection
    mock_collection = Mock()
    mock_collection.find.return_value = [cache_entry]
    mock_collection.update_one = Mock()  # Pour vérifier les appels

    # Mock MongoDB service
    service = LivresAuteursCacheService()
    service.mongodb_service = Mock()
    service.mongodb_service.get_collection.return_value = mock_collection

    # Mock Babelio service (singleton importé localement)
    with patch("back_office_lmelp.services.babelio_service.babelio_service") as mock_babelio:
        mock_babelio.fetch_publisher_from_url = AsyncMock(return_value="Gallimard")

        # Act
        books = await service.get_books_by_episode_oid_async(test_episode_oid)

        # Assert - Vérifier que fetch_publisher_from_url a été appelé
        mock_babelio.fetch_publisher_from_url.assert_called_once_with(
            "https://www.babelio.com/livres/Camus-Letranger/3874"
        )

        # Assert - Vérifier que update_one a été appelé pour persister
        mock_collection.update_one.assert_called_once_with(
            {"_id": test_id},
            {"$set": {"babelio_publisher": "Gallimard"}}
        )

        # Assert - Vérifier le résultat retourné
        assert len(books) == 1
        assert books[0]["babelio_publisher"] == "Gallimard"
```

**Pourquoi c'est correct:**
1. ✅ Aucune connexion MongoDB requise
2. ✅ Aucun appel API externe
3. ✅ Rapide (millisecondes)
4. ✅ Fonctionne en CI/CD
5. ✅ Vérifie la persistance via `update_one.assert_called_once_with(...)`
6. ✅ Reproductible à 100%

#### What to Mock in Backend Tests

**Always mock these:**
- ✅ MongoDB collections (`find`, `update_one`, `insert_one`, `delete_one`)
- ✅ External API services (Babelio, Google Books, etc.)
- ✅ Singleton services imported locally
- ✅ File I/O operations
- ✅ Network requests
- ✅ Time-dependent functions (`datetime.now()`)

**Never mock these:**
- ❌ Pure functions (calculations, transformations)
- ❌ The service under test itself
- ❌ Simple data structures (dicts, lists)
- ❌ Standard library utilities (unless I/O related)

#### How to Verify Database Updates

**CRITICAL**: Always verify that database updates are persisted by checking mock calls.

```python
# ✅ BON - Vérifier la persistance
mock_collection.update_one.assert_called_once_with(
    {"_id": test_id},  # Filter
    {"$set": {"babelio_publisher": "Gallimard"}}  # Update
)

# ✅ BON - Vérifier plusieurs appels dans l'ordre
assert mock_collection.update_one.call_count == 2
first_call = mock_collection.update_one.call_args_list[0]
assert first_call[0][0] == {"_id": test_id}  # Premier appel
assert first_call[0][1] == {"$set": {"field1": "value1"}}

# ❌ MAUVAIS - Ne vérifier que le retour de fonction
books = await service.get_books(episode_oid)
assert books[0]["publisher"] == "Gallimard"  # Pas de vérification de persistance!
```

#### Patching External Services Correctly

**Pattern 1: Patching singleton services**

```python
# ✅ BON - Patch le singleton au bon endroit
with patch("back_office_lmelp.services.babelio_service.babelio_service") as mock_babelio:
    mock_babelio.verify_book = AsyncMock(return_value={
        "status": "verified",
        "babelio_url": "https://...",
        "babelio_publisher": "Gallimard"
    })

    # Test code...
```

**Pattern 2: Multiple patches**

```python
# ✅ BON - Multiples patches avec parenthèses
with (
    patch("module.service1") as mock_service1,
    patch("module.service2") as mock_service2,
):
    mock_service1.method.return_value = "value1"
    mock_service2.method.return_value = "value2"

    # Test code...
```

#### Testing Error Cases

**Always test both success and error paths:**

```python
@pytest.mark.asyncio
async def test_when_scraping_fails_should_log_error_and_continue():
    """
    Quand le scraping échoue, log l'erreur mais continue le traitement.
    """
    # Arrange
    service = create_mocked_service()
    cache_entry = {...}

    mock_collection = Mock()
    mock_collection.find.return_value = [cache_entry]
    service.mongodb_service.get_collection.return_value = mock_collection

    # Mock Babelio service pour lever une exception
    with patch("back_office_lmelp.services.babelio_service.babelio_service") as mock_babelio:
        mock_babelio.fetch_publisher_from_url = AsyncMock(
            side_effect=Exception("Network error")
        )

        # Act - Ne doit pas lever d'exception
        books = await service.get_books_by_episode_oid_async("episode123")

        # Assert - Le livre est retourné sans publisher
        assert len(books) == 1
        assert "babelio_publisher" not in books[0]

        # Assert - update_one n'a PAS été appelé (échec du scraping)
        mock_collection.update_one.assert_not_called()
```

#### Common Mocking Mistakes

**❌ Mistake 1: Patching the wrong import path**
```python
# ❌ Mauvais - Patch où le service est utilisé, pas où il est défini
with patch("back_office_lmelp.services.cache_service.babelio_service"):
    pass  # Ne fonctionne pas avec imports locaux

# ✅ Bon - Patch à la source
with patch("back_office_lmelp.services.babelio_service.babelio_service"):
    pass
```

**❌ Mistake 2: Not using AsyncMock for async functions**
```python
# ❌ Mauvais - Mock au lieu de AsyncMock
mock_service.async_method = Mock(return_value="value")  # Erreur!

# ✅ Bon - AsyncMock pour fonctions async
mock_service.async_method = AsyncMock(return_value="value")
```

**❌ Mistake 3: Not verifying side effects**
```python
# ❌ Mauvais - Oubli de vérifier update_one
books = service.get_books("episode123")
assert books[0]["publisher"] == "Gallimard"  # Vérifie uniquement le retour

# ✅ Bon - Vérifie aussi la persistance
mock_collection.update_one.assert_called_once()
```

**❌ Mistake 4: Using real ObjectIds when not needed**
```python
# ❌ Mauvais - Génère des ObjectIds différents à chaque test
test_id = ObjectId()  # ID change à chaque exécution

# ✅ Bon - Utilise des IDs fixes pour reproductibilité
test_id = ObjectId("507f1f77bcf86cd799439011")
```

#### Unit Tests vs Integration Tests

**Ratio recommandé: 90% unit tests (mocks), 10% integration tests (real DB)**

**Unit Tests (mocks)**:
- Test individual service methods
- Fast execution (milliseconds)
- Run in CI/CD without infrastructure
- Use `Mock`, `AsyncMock`, `patch`
- Example: `test_babelio_cache_enrichment.py`

**Integration Tests (real DB)**:
- Test full workflows across services
- Slower execution (seconds)
- Require MongoDB running
- Use real database connections
- Example: End-to-end API tests with TestClient

**When to write integration tests:**
- Testing complex multi-service workflows
- Validating MongoDB aggregation pipelines
- Testing transaction consistency
- Verifying database indexes work correctly

**When to write unit tests (mocks):**
- Testing business logic
- Testing error handling
- Testing data transformations
- Testing individual service methods
- **Default choice for 90% of tests**

#### Quick Checklist for Backend Tests

Before committing tests, verify:
- [ ] No real MongoDB connections (`mongodb_service` is mocked)
- [ ] No external API calls (services are mocked)
- [ ] Database updates verified via `mock_collection.update_one.assert_called_with(...)`
- [ ] Both success and error cases tested
- [ ] AsyncMock used for async functions
- [ ] Correct patch path (source module, not usage module)
- [ ] Tests run in <100ms (no network/disk I/O)
- [ ] Tests pass in CI/CD environment

**Reference**: Issue #85 - Learned this the hard way after initially writing tests with real MongoDB connections, which was completely wrong for CI/CD compatibility.

## Claude Code Auto-Discovery System

### Overview
This project includes a comprehensive auto-discovery system that eliminates the need for Claude Code to guess ports or manually discover running services. Issue #56 has been fully implemented with TDD methodology.

### Key Features
- **Unified Port Discovery**: Single `.dev-ports.json` file tracks both backend and frontend services
- **Auto-Discovery Scripts**: Claude Code can instantly find running services from any directory
- **Process Validation**: Confirms services are actually running (not just port files exist)
- **Stale File Cleanup**: Automatically handles outdated discovery information
- **Cross-Directory Support**: Works from project root, frontend/, or any subdirectory

### Available Auto-Discovery Commands

#### Service Overview
```bash
# Get comprehensive overview of all running services
/workspaces/back-office-lmelp/.claude/get-services-info.sh

# JSON output for programmatic use
/workspaces/back-office-lmelp/.claude/get-services-info.sh --json

# URLs only for quick access
/workspaces/back-office-lmelp/.claude/get-services-info.sh --urls
```

#### Backend Service Discovery
```bash
# Get backend URL (most common use case)
/workspaces/back-office-lmelp/.claude/get-backend-info.sh --url

# Get backend port only
/workspaces/back-office-lmelp/.claude/get-backend-info.sh --port

# Check backend status
/workspaces/back-office-lmelp/.claude/get-backend-info.sh --status

# Get all backend information
/workspaces/back-office-lmelp/.claude/get-backend-info.sh --all
```

#### Frontend Service Discovery
```bash
# Get frontend URL
/workspaces/back-office-lmelp/.claude/get-frontend-info.sh --url

# Get frontend port only
/workspaces/back-office-lmelp/.claude/get-frontend-info.sh --port

# Check frontend status
/workspaces/back-office-lmelp/.claude/get-frontend-info.sh --status

# Get all frontend information
/workspaces/back-office-lmelp/.claude/get-frontend-info.sh --all
```

### Usage Examples for Claude Code

#### API Testing Workflow
```bash
# 1. Discover backend automatically
BACKEND_URL=$(/workspaces/back-office-lmelp/.claude/get-backend-info.sh --url)

# 2. Test API endpoints directly
curl "$BACKEND_URL/"                    # Health check
curl "$BACKEND_URL/docs"                # API documentation
curl "$BACKEND_URL/openapi.json"        # OpenAPI spec

# 3. Make API calls with discovered URL
curl -X POST "$BACKEND_URL/api/verify-babelio" \
  -H "Content-Type: application/json" \
  -d '{"type": "author", "name": "Albert Camus"}'
```

#### Service Status Verification
```bash
# Check if services are actually running (not just port files exist)
/workspaces/back-office-lmelp/.claude/get-backend-info.sh --status    # Returns: active/inactive
/workspaces/back-office-lmelp/.claude/get-frontend-info.sh --status   # Returns: active/inactive

# Comprehensive status check
/workspaces/back-office-lmelp/.claude/get-services-info.sh --summary
```

### Unified Port Discovery File Format
The `.dev-ports.json` file contains both backend and frontend information:

```json
{
  "backend": {
    "port": 54321,
    "host": "0.0.0.0",
    "pid": 12345,
    "started_at": 1640995200.0,
    "url": "http://0.0.0.0:54321"
  },
  "frontend": {
    "port": 5173,
    "host": "0.0.0.0",
    "pid": 12346,
    "started_at": 1640995200.0,
    "url": "http://0.0.0.0:5173"
  }
}
```

### Benefits for Claude Code
- **No More Port Guessing**: Eliminates "Connection refused" errors
- **Instant Service Discovery**: Find running services in milliseconds
- **Reliable API Testing**: Always use correct URLs for API calls
- **Cross-Directory Compatibility**: Works from frontend/, root, or any subdirectory
- **Process Validation**: Confirms services are actually running
- **Development Efficiency**: Reduces trial-and-error in service discovery
- **Smart Restart Detection**: Automatically detects when backend should be restarted

### Advanced Claude Code Scripts

#### Backend Freshness Detection

For situations where you've modified backend code and need to determine if a restart is required:

```bash
# Check if backend needs restart (default: 10 minutes threshold)
/workspaces/back-office-lmelp/.claude/check-backend-freshness.sh

# Check with custom threshold (5 minutes)
/workspaces/back-office-lmelp/.claude/check-backend-freshness.sh 5
```

**Exit codes:**
- `0`: Backend is fresh and probably up-to-date
- `1`: No backend detected (needs to be started)
- `2`: Backend is stale (restart recommended)

**Example workflow:**
```bash
# 1. Check backend freshness after making code changes
FRESHNESS_CHECK=$(/workspaces/back-office-lmelp/.claude/check-backend-freshness.sh 10)
EXIT_CODE=$?

if [[ $EXIT_CODE -eq 2 ]]; then
    echo "🔄 Backend is stale, restarting..."
    pkill -f 'python.*back_office_lmelp'
    ./scripts/start-dev.sh &
    sleep 5
fi

# 2. Get backend URL for API testing
BACKEND_URL=$(/workspaces/back-office-lmelp/.claude/get-backend-info.sh --url)

# 3. Test your modifications
curl "$BACKEND_URL/api/episodes" | jq
```

This eliminates the guesswork of "Do I need to restart the backend after my changes?"

## API Discovery and Testing

### Backend API Discovery Method
When working with the backend API, use this systematic approach to discover endpoints and avoid trial-and-error:

#### Step 1: Automatic Service Discovery (Issue #56 - ✅ Implemented)
Claude Code now includes automatic port discovery to eliminate port guessing:

```bash
# Use Claude Code auto-discovery scripts (recommended - work from anywhere in project)
/workspaces/back-office-lmelp/.claude/get-services-info.sh            # Overview of all services
/workspaces/back-office-lmelp/.claude/get-backend-info.sh --url       # Get backend URL directly
/workspaces/back-office-lmelp/.claude/get-frontend-info.sh --url      # Get frontend URL directly

# Manual discovery using unified port file
cat /workspaces/back-office-lmelp/.dev-ports.json | jq -r '.backend.url'     # Backend URL
cat /workspaces/back-office-lmelp/.dev-ports.json | jq -r '.frontend.url'    # Frontend URL

# Legacy fallback (if auto-discovery fails)
curl -s "http://localhost:54321/" || curl -s "http://localhost:54322/" || curl -s "http://localhost:8000/"
```

#### Step 2: Get Complete API Schema
```bash
# Get backend URL automatically
BACKEND_URL=$(/workspaces/back-office-lmelp/.claude/get-backend-info.sh --url)

# Get the OpenAPI specification using auto-discovered URL
curl "$BACKEND_URL/openapi.json" | jq '.' > api-schema.json

# Quick endpoint discovery
curl "$BACKEND_URL/openapi.json" | jq -r '.paths | keys[]'
```

#### Step 3: Find Specific Endpoints
```bash
# Get backend URL automatically
BACKEND_URL=$(/workspaces/back-office-lmelp/.claude/get-backend-info.sh --url)

# Search for specific functionality
curl "$BACKEND_URL/openapi.json" | jq -r '.paths | keys[]' | grep -i KEYWORD

# Examples:
curl "$BACKEND_URL/openapi.json" | jq -r '.paths | keys[]' | grep -i babelio
curl "$BACKEND_URL/openapi.json" | jq -r '.paths | keys[]' | grep -i fuzzy
curl "$BACKEND_URL/openapi.json" | jq -r '.paths | keys[]' | grep -i verify
```

#### Step 4: Get Endpoint Details
```bash
# Get backend URL automatically
BACKEND_URL=$(/workspaces/back-office-lmelp/.claude/get-backend-info.sh --url)

# Get request schema for a specific endpoint
curl "$BACKEND_URL/openapi.json" | jq '.paths["/api/endpoint"].post.requestBody'

# Get response schema
curl "$BACKEND_URL/openapi.json" | jq '.paths["/api/endpoint"].post.responses'

# Get component schemas
curl "$BACKEND_URL/openapi.json" | jq '.components.schemas.SchemaName'
```

#### Step 5: Test Endpoint with Correct Schema
```bash
# Get backend URL automatically
BACKEND_URL=$(/workspaces/back-office-lmelp/.claude/get-backend-info.sh --url)

# Use the discovered schema to make proper requests
curl -X POST "$BACKEND_URL/api/endpoint" \
  -H "Content-Type: application/json" \
  -d '{"field": "value"}'
```

### Common Backend Endpoints
Using auto-discovery for reliable API testing:

```bash
# Get backend URL automatically
BACKEND_URL=$(/workspaces/back-office-lmelp/.claude/get-backend-info.sh --url)

# API health check
curl "$BACKEND_URL/"

# API documentation
curl "$BACKEND_URL/docs"                # Interactive API docs
curl "$BACKEND_URL/openapi.json"        # OpenAPI specification

# Babelio verification
curl -X POST "$BACKEND_URL/api/verify-babelio" \
  -H "Content-Type: application/json" \
  -d '{"type": "author", "name": "Albert Camus"}'

# Example with book verification
curl -X POST "$BACKEND_URL/api/verify-babelio" \
  -H "Content-Type: application/json" \
  -d '{"type": "book", "title": "L'\''Étranger", "author": "Albert Camus"}'
```

### Stats

to autonomously get stats data (Informations Generales blocks)

```bash
# Get backend URL automatically
BACKEND_URL=$(/workspaces/back-office-lmelp/.claude/get-backend-info.sh --url)

# stats
curl "$BACKEND_URL/api/stats" | jq
```

### API Testing Best Practices
- **Always check the API documentation first**: Visit `/docs` for interactive testing
- **Use jq for JSON parsing**: Makes endpoint discovery much faster
- **Save common schemas**: Store frequently used request bodies as examples
- **Verify response format**: Check actual response structure before using in code
- **Handle different environments**: Port may vary between local/dev/prod

### Troubleshooting API Issues
- **Connection refused**: Check if backend is running and on correct port
- **404 Not Found**: Verify endpoint path with OpenAPI schema
- **422 Validation Error**: Check required fields in request schema
- **Missing field errors**: Use OpenAPI schema to verify all required fields

**Note**: Issue #56 has been fully implemented - automatic port discovery is now available via the Claude Code Auto-Discovery System (see section above).

## Auto-Discovery Best Practices for API Testing

### Pattern Optimal : Chaînage Auto-Discovery + API Call
```bash
# ✅ MÉTHODE RECOMMANDÉE : Chaînage avec && (FONCTIONNE PARFAITEMENT)
BACKEND_URL=$(/workspaces/back-office-lmelp/.claude/get-backend-info.sh --url) && \
curl -X POST "$BACKEND_URL/api/endpoint" \
  -H "Content-Type: application/json" \
  -d '{"data": "value"}'

# ✅ Health check automatique avec chaînage
BACKEND_URL=$(/workspaces/back-office-lmelp/.claude/get-backend-info.sh --url) && \
curl "$BACKEND_URL/"

# ✅ Test API avec query string (testé et validé)
BACKEND_URL=$(/workspaces/back-office-lmelp/.claude/get-backend-info.sh --url) && \
curl -s "$BACKEND_URL/api/livres-auteurs?episode_oid=68c707ad6e51b9428ab87e9e" | jq

# ✅ Validation d'endpoint avec données POST
BACKEND_URL=$(/workspaces/back-office-lmelp/.claude/get-backend-info.sh --url) && \
curl "$BACKEND_URL/api/livres-auteurs/validate-suggestion" \
  -H "Content-Type: application/json" \
  -d '{"cache_id": "test"}' | jq
```

### Pattern Alternatif : Substitution Directe
```bash
# ✅ Alternative compacte : Substitution directe (aussi validé)
curl "$(/workspaces/back-office-lmelp/.claude/get-backend-info.sh --url)/api/endpoint"

# ✅ Avec JSON formatting
curl -s "$(/workspaces/back-office-lmelp/.claude/get-backend-info.sh --url)/api/stats" | jq
```

### Pattern 2-étapes (si chaînage pose problème)
```bash
# ✅ Fallback : Séparer en deux étapes
BACKEND_URL=$(/workspaces/back-office-lmelp/.claude/get-backend-info.sh --url)
curl "$BACKEND_URL/api/endpoint"
```

### ⚠️ Note Importante sur l'Échappement
**Le chaînage fonctionne parfaitement en ligne de commande normale**. Si des erreurs d'échappement apparaissent dans certains environnements (interfaces, IDE, etc.), utiliser la substitution directe ou la méthode 2-étapes comme fallback.

### Pattern Robuste : Validation + Fallback
```bash
# Vérifier que le backend est actif avant test
BACKEND_STATUS=$(/workspaces/back-office-lmelp/.claude/get-backend-info.sh --status)
if [ "$BACKEND_STATUS" = "active" ]; then
    BACKEND_URL=$(/workspaces/back-office-lmelp/.claude/get-backend-info.sh --url)
    curl "$BACKEND_URL/api/test"
else
    echo "❌ Backend not running"
    exit 1
fi
```

### Anti-Patterns à Éviter
```bash
# ❌ Hardcoder les ports (fragile)
curl "http://localhost:54321/api/endpoint"

# ❌ Deviner les ports (inefficace)
curl "http://localhost:8000/api/endpoint" || curl "http://localhost:5000/api/endpoint"

# ❌ Ne pas valider l'état du service
curl "http://localhost:$RANDOM/api/endpoint"
```

### Workflow TDD avec Auto-Discovery
```bash
# 1. Vérifier l'état des services
/workspaces/back-office-lmelp/.claude/get-services-info.sh

# 2. Tester le cas d'erreur (Red phase)
BACKEND_URL=$(/workspaces/back-office-lmelp/.claude/get-backend-info.sh --url) && \
curl "$BACKEND_URL/api/validate" -d '{"invalid": null}' # → 422

# 3. Après correction, tester le cas de succès (Green phase)
BACKEND_URL=$(/workspaces/back-office-lmelp/.claude/get-backend-info.sh --url) && \
curl "$BACKEND_URL/api/validate" -d '{"valid": "data"}' # → 200
```

**Avantages** :
- ✅ Élimine 90% des erreurs "Connection refused"
- ✅ S'adapte automatiquement aux changements de port
- ✅ Tests plus robustes et maintenables
- ✅ Workflow de debug plus efficace

## MongoDB Database Operations

### MCP MongoDB Tools Integration
This project includes MCP (Model Context Protocol) tools for MongoDB operations. These tools provide direct database access capabilities for the `masque_et_la_plume` database.

#### Project Database Structure
- **Main Database**: `masque_et_la_plume`
- **Collections**: `livres`, `emissions`, `editeurs`, `episodes`, `avis_critiques`, `logs`, `auteurs`, `critiques`

#### Available MongoDB MCP Tools
- `mcp__MongoDB__connect`: Connect to MongoDB instance
- `mcp__MongoDB__list-databases`: List all databases
- `mcp__MongoDB__list-collections`: List collections in a database
- `mcp__MongoDB__collection-schema`: Get collection schema structure
- `mcp__MongoDB__collection-indexes`: View collection indexes
- `mcp__MongoDB__find`: Query documents with filters, sorting, projection
- `mcp__MongoDB__aggregate`: Run aggregation pipelines
- `mcp__MongoDB__count`: Count documents with optional filters
- `mcp__MongoDB__collection-storage-size`: Get collection storage information
- `mcp__MongoDB__explain`: Analyze query execution plans
- `mcp__MongoDB__export`: Export query results in EJSON format
- `mcp__MongoDB__db-stats`: Database statistics
- `mcp__MongoDB__mongodb-logs`: View MongoDB server logs

#### Common MongoDB Operations for This Project

**Database Discovery:**
```bash
# List all databases
mcp__MongoDB__list-databases

# List collections in main database
mcp__MongoDB__list-collections --database "masque_et_la_plume"

# Get schema for specific collections
mcp__MongoDB__collection-schema --database "masque_et_la_plume" --collection "livres"
mcp__MongoDB__collection-schema --database "masque_et_la_plume" --collection "auteurs"
mcp__MongoDB__collection-schema --database "masque_et_la_plume" --collection "episodes"
```

**Data Querying Examples:**
```bash
# Find books
mcp__MongoDB__find --database "masque_et_la_plume" --collection "livres" --filter '{"status": "active"}' --limit 10

# Find authors
mcp__MongoDB__find --database "masque_et_la_plume" --collection "auteurs" --limit 5

# Count episodes
mcp__MongoDB__count --database "masque_et_la_plume" --collection "episodes"

# Find recent episodes
mcp__MongoDB__find --database "masque_et_la_plume" --collection "episodes" --sort '{"date": -1}' --limit 10
```

**Aggregation Examples:**
```bash
# Books by publisher
mcp__MongoDB__aggregate --database "masque_et_la_plume" --collection "livres" --pipeline '[{"$group": {"_id": "$editeur", "count": {"$sum": 1}}}]'

# Episodes by emission
mcp__MongoDB__aggregate --database "masque_et_la_plume" --collection "episodes" --pipeline '[{"$group": {"_id": "$emission_id", "count": {"$sum": 1}}}]'
```

**Performance Analysis:**
```bash
# Explain book queries
mcp__MongoDB__explain --database "masque_et_la_plume" --collection "livres" --method '[{"name": "find", "arguments": {"filter": {"titre": "some title"}}}]'

# View collection indexes
mcp__MongoDB__collection-indexes --database "masque_et_la_plume" --collection "livres"
mcp__MongoDB__collection-indexes --database "masque_et_la_plume" --collection "auteurs"

# Get storage statistics
mcp__MongoDB__collection-storage-size --database "masque_et_la_plume" --collection "livres"
```

#### Integration with Backend Development
- **Schema Validation**: Use `collection-schema` to understand data structures before coding
- **Query Optimization**: Use `explain` to optimize MongoDB queries in backend services
- **Data Analysis**: Use `aggregate` for complex data transformations and reporting
- **Debugging**: Use `mongodb-logs` to troubleshoot database connectivity issues

#### Best Practices for MongoDB MCP Tools
- Always use `collection-schema` for `livres`, `auteurs`, and `episodes` collections before writing queries
- Test queries with `find` before implementing them in backend code
- Use `explain` to optimize query performance for book/author searches
- Use `aggregate` for complex reporting across collections (books by author, episodes by emission, etc.)

## Dependencies

### Backend Dependencies
- **FastAPI**: Web framework with MongoDB integration
- **Core**: pandas, numpy (data processing)
- **Database**: MongoDB via motor/pymongo
- **Documentation**: MkDocs with Material theme
- **Development**: pytest, ruff, mypy, pre-commit

### Frontend Dependencies
- **Vue.js 3**: Progressive framework with Composition API
- **Build**: Vite 5.0+ with @vitejs/plugin-vue
- **HTTP**: Axios for API communication
- **Utilities**: lodash.debounce for UI interactions
- **Testing**: Vitest, @vue/test-utils, jsdom

## Documentation

### MkDocs Setup
- **Theme**: Material Design with French language support
- **Features**: Navigation, search, code highlighting
- **Local development**: `mkdocs serve` on port 8000
- **Production**: https://castorfou.github.io/back-office-lmelp/

### Structure
- **User documentation**: docs/user/ (guides, troubleshooting)
- **Developer documentation**: docs/dev/ (architecture, API, security)
- **Environment variables**: docs/dev/environment-variables.md (complete reference)
- **Automatic deployment**: GitHub Actions on docs changes

## Project Maintenance Guidelines

### Test Count Management
**NEVER include specific test counts** in documentation (README.md, CLAUDE.md). These numbers become stale quickly and provide no real value:
- ❌ "Run backend tests (176 tests)"
- ✅ "Run backend tests"
- ❌ "Total: 276 tests validés"
- ✅ "Tests complets validés"

Rationale: Test counts change frequently and require constant maintenance without adding meaningful information for users or developers.

### Git Commit Best Practices
**AVOID using `git commit --amend`** on branches that are already pushed to remote repositories:

- ❌ **Don't amend pushed commits**: `git commit --amend` changes the commit SHA, causing conflicts with remote
- ✅ **Use separate commits**: Create new commits instead of amending existing ones
- ⚠️ **Force push complications**: Amended commits require `git push --force-with-lease` which can be risky

**Recommended workflow:**
```bash
# Instead of amending
git add fixes.py
git commit -m "fix: address code review feedback"

# NOT: git commit --amend (if already pushed)
```

**Exception:** Only amend commits that have **never been pushed** to any remote repository.

Rationale: Amended commits create history rewriting that complicates collaboration and can lead to lost work or merge conflicts.

### Documentation Writing Guidelines
**CRITICAL**: Documentation should describe the **current state** of the application, not its construction history.

**DO NOT include** in documentation:
- ❌ References to GitHub issues in feature descriptions (e.g., "Issue #75 improved this...")
- ❌ Historical comparisons (e.g., "This is now much better than before...")
- ❌ Evolution narratives (e.g., "We first implemented X, then added Y...")
- ❌ "New feature" or "Recently added" markers (features are current, not new)
- ❌ Development timeline references (e.g., "3 commits ago", "last week we added...")

**DO include** in documentation:
- ✅ Current functionality and how it works
- ✅ Technical specifications and architecture
- ✅ Usage examples and best practices
- ✅ Configuration options and parameters
- ✅ Known limitations and constraints

**Issue references - when acceptable:**
- ✅ In a dedicated "History" or "Development Notes" section at the end
- ✅ In commit messages and pull requests
- ✅ In code comments when explaining technical decisions
- ❌ NOT in the main functional documentation

**Example - Bad documentation:**
```markdown
### Phase 0 Validation (Issue #75 - Implemented)

**New in Issue #75**: Phase 0 is now much better thanks to:
1. Double call confirmation (Issue #75)
2. Author correction (also Issue #75)

This is a major improvement over the previous implementation.
```

**Example - Good documentation:**
```markdown
### Phase 0 Validation

Phase 0 uses two enrichment mechanisms to maximize success rate:
1. **Double call confirmation**: When Babelio returns confidence 0.85-0.99, a second call confirms the suggestion
2. **Author correction**: When book is not found, Phase 0 attempts author correction before fallback

Typical success rate: ~45% of books processed automatically.
```

**Rationale:**
- Documentation readers want to understand **what the system does now**, not how it evolved
- Issue references create noise and reduce readability
- Historical context becomes stale and irrelevant over time
- Clean documentation is more maintainable and professional
