# Claude AI Development Guide

This document provides in-depth guidance for Claude Code when working with this repository. For a quick reference guide, see [CLAUDE.md](https://github.com/castorfou/back-office-lmelp/blob/main/CLAUDE.md) in the project root.


## Documentation Structure

This project uses a two-tier documentation approach for Claude Code:

### CLAUDE.md (Root - Quick Reference)
**Purpose**: Fast, actionable reference for Claude Code during active development

**Should contain:**
- ✅ Essential commands (copy-paste ready)
- ✅ Project structure overview
- ✅ Key rules (what/how, not why)
- ✅ Quick cheat sheets (auto-discovery, MongoDB, Git)
- ✅ Links to detailed guide for more information

**Should NOT contain:**
- ❌ Long explanations or rationales
- ❌ Detailed examples of anti-patterns
- ❌ Historical context or issue references
- ❌ Multiple solution alternatives

**Target length**: 200-300 lines

### docs/dev/claude-ai-guide.md (This File - Comprehensive Guide)
**Purpose**: Deep reference for understanding patterns, rationales, and complex scenarios

**Should contain:**
- ✅ Detailed explanations of WHY rules exist
- ✅ Complete examples with anti-patterns
- ✅ Historical context and issue references (for learning)
- ✅ Multiple approaches with tradeoffs
- ✅ Troubleshooting guides and edge cases

**Should NOT contain:**
- ❌ Duplicate basic commands (already in CLAUDE.md)
- ❌ Project overview (keep in CLAUDE.md)

**Target approach**: Comprehensive, educational, no length limit

### When to Update Which File

**Update CLAUDE.md when:**
- Adding/changing essential commands
- Modifying project structure
- Adding new critical rules
- Updating tool versions or configurations

**Update docs/dev/claude-ai-guide.md when:**
- Discovering new testing patterns/pitfalls
- Documenting complex scenarios (like Issue #67, #75, #85)
- Adding detailed explanations for existing rules
- Expanding on best practices with examples

**Update both when:**
- Adding a new critical workflow (brief in CLAUDE.md, detailed here)
- Changing development environment setup

## Table of Contents

- [Development Workflow Best Practices](#development-workflow-best-practices)
- [Testing Patterns and Pitfalls](#testing-patterns-and-pitfalls)
- [Backend Testing Advanced Topics](#backend-testing-advanced-topics)
- [Frontend UI/UX Patterns](#frontend-uiux-patterns)
- [Documentation Guidelines](#documentation-guidelines)
- [Project Maintenance](#project-maintenance)

## Development Workflow Best Practices

### Environment Setup

**CRITICAL**: Activate the Python virtual environment once per bash session before running any Python tools:

```bash
source /workspaces/back-office-lmelp/.venv/bin/activate
```

**Why this matters:**
- Enables direct use of `ruff`, `mypy`, `pytest`, `mkdocs` without `uv run` prefix
- Ensures correct tool versions are used
- Prevents "command not found" errors
- Only needs to be done once per terminal session (not before each command)

**Without activation:**
```bash
# ❌ Won't work - command not found
ruff check .
mypy src/

# ✅ Works but verbose
uv run ruff check .
uv run mypy src/
```

**With activation:**
```bash
# ✅ Works directly after activation
source /workspaces/back-office-lmelp/.venv/bin/activate
ruff check .
mypy src/
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

### Verification Best Practices

**CRITICAL**: Always verify the actual state before marking tasks as completed.

- **Before marking any task as 'completed'**: Use appropriate tools to verify the action is actually accomplished
- **For Pull Requests**: Use `gh pr view <number>` to confirm merge status before declaring success
- **For deployments**: Check actual deployment status, not just pipeline success
- **For file changes**: Use `Read` or `ls` to verify files exist/changed as expected
- **For test results**: Verify all tests actually pass, not just assume from commands run

**Never rely solely on user declarations of intent** - always verify the real world state using available tools.

## Testing Patterns and Pitfalls

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

## Backend Testing Advanced Topics

### Mocking Services with Complex Dependencies

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

### Mocking Singleton Services with Local Imports

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

### Creating Mocks from Real API Responses

**🚨 ABSOLUTE RULE 🚨**: When writing backend tests, **NEVER invent mock response structures**. **ALWAYS call the real API first** to capture the actual response format, then create your mocks based on that real structure.

#### Why This is Critical

Invented mocks can perfectly match buggy code, causing tests to pass while real code fails in production. This creates a dangerous false sense of security where your test suite validates incorrect behavior.

**Real Example from Issue #85 - The Bug That Tests Didn't Catch:**

```python
# ❌ WRONG - Code reads wrong dictionary key
# File: books_extraction_service.py:329
confidence = verification.get("confidence", 0) if verification else 0  # ❌ Wrong key!

# ❌ WRONG - Test mock uses invented structure that matches buggy code
mock_babelio_response = {
    "confidence": 0.95,  # ❌ Invented key (matches bug!)
    "babelio_publisher": "Gallimard"
}

# What happens:
# - Code reads verification.get("confidence", 0) → Gets 0.95 from mock ✅ Test passes
# - Real API returns {"confidence_score": 0.95, ...} → Code gets 0 (default) ❌ Real code fails
# - ALL BOOKS showed confidence: 0.00 in production despite tests passing!
```

**Real API Response (discovered via manual testing):**
```json
{
  "status": "verified",
  "original_title": "Paracuellos, Intégrale",
  "babelio_suggestion_title": "Paracuellos, Intégrale",
  "original_author": "Carlos Gimenez",
  "babelio_suggestion_author": "Carlos Gimenez",
  "confidence_score": 1.0,  // ✅ Real key is "confidence_score" NOT "confidence"
  "babelio_data": {...},
  "babelio_url": "https://www.babelio.com/livres/Gimenez-Paracuellos-Integrale/112880",
  "babelio_publisher": "Audie-Fluide glacial",
  "error_message": null
}
```

#### The Correct Process - ALWAYS Follow These Steps

**Step 1: Call the Real API**

Before writing any test, manually call the actual API endpoint to see what it really returns:

```bash
# Example: Testing Babelio verify_book()
BACKEND_URL=$(/workspaces/back-office-lmelp/.claude/get-backend-info.sh --url) && \
curl -X POST "$BACKEND_URL/api/verify-babelio" \
  -H "Content-Type: application/json" \
  -d '{"type": "book", "title": "Paracuellos, Intégrale", "author": "Carlos Gimenez"}' | jq

# Save the EXACT response structure
```

**Step 2: Capture the Complete Response**

```python
# Add temporary debug logging to see real responses
print(f"DEBUG: Real API response: {json.dumps(verification, indent=2)}")
```

**Step 3: Create Mock Based on Real Structure**

```python
# ✅ CORRECT - Mock based on real API response
mock_babelio_response = {
    "status": "verified",
    "original_title": "Paracuellos, Intégrale",
    "babelio_suggestion_title": "Paracuellos, Intégrale",
    "original_author": "Carlos Gimenez",
    "babelio_suggestion_author": "Carlos Gimenez",
    "confidence_score": 0.95,  # ✅ Real key from actual API
    "babelio_url": "https://www.babelio.com/livres/Gimenez-Paracuellos-Integrale/112880",
    "babelio_publisher": "Gallimard",
    "error_message": None
}

# Now code that reads confidence_score will work correctly:
confidence = verification.get("confidence_score", 0)  # ✅ Correct key
```

#### Quick Checklist Before Writing Any Mock

Before creating a mock in your test, verify:

- [ ] Have I called the real API endpoint manually?
- [ ] Have I captured the complete response structure (use `| jq` or `json.dumps(..., indent=2)`)?
- [ ] Does my mock include ALL fields from the real response (not just what I think I need)?
- [ ] Have I tested with multiple real examples (success, partial match, error cases)?
- [ ] Have I documented where the mock structure came from (comment with curl command)?

#### Documentation Pattern for Mocks

```python
def test_verify_book_high_confidence():
    """
    GIVEN: Book with exact match in Babelio database
    WHEN: verify_book() is called
    THEN: Returns confidence_score >= 0.90 with enriched data

    Mock structure based on real API response:
    curl -X POST "$BACKEND_URL/api/verify-babelio" \
      -d '{"type": "book", "title": "Paracuellos, Intégrale", "author": "Carlos Gimenez"}'

    Real response captured: 2025-01-15
    """
    # ✅ Mock based on documented real API call
    mock_babelio_response = {
        "status": "verified",
        "confidence_score": 1.0,  # Real key from actual API
        "babelio_url": "https://www.babelio.com/livres/Gimenez-Paracuellos-Integrale/112880",
        "babelio_publisher": "Audie-Fluide glacial"
    }
```

#### Why This Rule is Non-Negotiable

1. **Prevents Silent Failures**: Tests that validate incorrect behavior are worse than no tests
2. **Catches Integration Issues**: Real API structure changes won't match invented mocks
3. **Documents Actual Behavior**: Mocks become living documentation of real API contracts
4. **Saves Debug Time**: When production fails but tests pass, you know to check mock accuracy
5. **Enforces TDD Discipline**: Can't write test before seeing real behavior

**Reference**: Issue #85 - Discovered this critical rule the hard way:
- All enrichment tests passed (5/5) ✅
- Real enrichment failed 100% (0% success rate) ❌
- Root cause: Mocks used `"confidence"` key, real API uses `"confidence_score"`
- Impact: ALL books showed confidence 0.00 in production
- Lesson: **NEVER invent mock structures, ALWAYS call real APIs first**

This rule is now a **non-negotiable requirement** for all backend testing in this project.

### Writing Proper TDD Tests with Mocks

**CRITICAL**: When writing backend tests, ALWAYS use mocks for external dependencies (MongoDB, APIs, services). NEVER use real database connections or external API calls in unit tests.

#### Why Mocking is Essential

- **CI/CD Compatibility**: Tests must run in isolated environments without external dependencies
- **Speed**: Mocked tests run in milliseconds instead of seconds
- **Reliability**: No network failures, no database setup required
- **Isolation**: Each test is independent and doesn't affect real data
- **Reproducibility**: Same results every time, no flaky tests

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

**Integration Tests (real DB)**:
- Test full workflows across services
- Slower execution (seconds)
- Require MongoDB running
- Use real database connections

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

## FastAPI Route Patterns

### Route Order - CRITICAL Pattern

**CRITICAL**: In FastAPI, route order matters. Specific routes MUST be defined BEFORE parametric routes.

#### The Problem

FastAPI matches routes in **definition order**. When you define:

```python
@app.get("/api/episodes/{episode_id}")  # Parametric route
async def get_episode(episode_id: str):
    ...

@app.get("/api/episodes/all")  # Specific route
async def get_all_episodes():
    ...
```

Calling `/api/episodes/all` will match the first route with `episode_id="all"`, causing unexpected behavior.

#### The Solution

Always define specific routes BEFORE parametric routes:

```python
@app.get("/api/episodes/all")  # Specific route FIRST
async def get_all_episodes():
    ...

@app.get("/api/episodes/{episode_id}")  # Parametric route AFTER
async def get_episode(episode_id: str):
    ...
```

#### Why Unit Tests Don't Catch This

- Unit tests typically call functions directly or use `TestClient` with exact URLs
- They don't test **route matching order** or **pattern conflicts**
- This is a **routing-level integration issue**, not a unit-level issue

#### How to Detect This Issue

**Option 1: Manual Testing**
```bash
curl /api/episodes/all  # Should return list, not 404
```

**Option 2: Integration Tests** (recommended for future)
```python
def test_specific_routes_before_parametric():
    """Verify route order to prevent matching conflicts."""
    response = client.get("/api/episodes/all")
    assert response.status_code == 200
    assert isinstance(response.json(), list)  # Not an error object
```

**Option 3: Route Order Verification Test**
```python
def test_route_definition_order():
    """Verify specific routes defined before parametric ones."""
    routes = [r for r in app.routes if hasattr(r, 'path')]
    all_index = next(i for i, r in enumerate(routes)
                     if r.path == "/api/episodes/all")
    id_index = next(i for i, r in enumerate(routes)
                    if r.path == "/api/episodes/{episode_id}")
    assert all_index < id_index, "Specific route must come before parametric"
```

### REST API Idempotence Pattern

**CRITICAL**: PATCH/PUT operations should be idempotent following REST principles.

#### MongoDB Update Behavior

When using `collection.update_one()`:
- `matched_count`: Number of documents matched by the filter (0 or 1)
- `modified_count`: Number of documents actually modified (0 or 1)

If a document is already in the desired state, `modified_count = 0` even though the operation succeeded.

#### Wrong Pattern (Non-Idempotent)

```python
result = collection.update_one({"_id": id}, {"$set": {"masked": False}})
return bool(result.modified_count > 0)  # ❌ Fails if already False
```

This returns `False` when trying to unmask an already unmasked episode, treating a successful idempotent operation as a failure.

#### Correct Pattern (Idempotent)

```python
result = collection.update_one({"_id": id}, {"$set": {"masked": False}})
return bool(result.matched_count > 0)  # ✅ Success if document exists
```

This returns `True` as long as the document exists, regardless of whether it was modified.

#### Why This Matters

REST APIs should be idempotent: calling the same operation multiple times should have the same effect as calling it once, without errors.

**Example**: Calling `PATCH /episodes/{id}/masked` with `{"masked": false}` twice should succeed both times, not fail on the second call.

## Frontend UI/UX Patterns

### Vue.js Component Design

Pour les patterns UI détaillés, la charte graphique et les conventions visuelles, voir le document dédié :

**[Charte graphique et patterns UI Vue.js](vue-ui-patterns.md)**

Ce document couvre :
- Structure des composants Vue
- Cartes de statistiques (Dashboard et pages de détail)
- États de chargement, erreur et vide
- Boutons d'action et hiérarchie visuelle
- Indicateurs de progression
- Opérations par lot
- Palette de couleurs et accessibilité
- Chargement parallèle des données
- Design responsive

### Règles critiques Frontend

**Chargement parallèle des données (CRITICAL)** :
```javascript
// ❌ MAUVAIS - Chargement séquentiel (apparition échelonnée)
async mounted() {
  await this.loadStatistics();
  await this.loadCollectionsStatistics();
  await this.loadDuplicateStatistics();
}

// ✅ CORRECT - Chargement parallèle (affichage simultané)
async mounted() {
  await Promise.all([
    this.loadStatistics(),
    this.loadCollectionsStatistics(),
    this.loadDuplicateStatistics()
  ]);
}
```

**Propriétés calculées pour statistiques combinées** :
```javascript
computed: {
  totalCount() {
    // Retourner null si un composant est encore en chargement
    if (this.booksCount === null || this.authorsCount === null) {
      return null;
    }
    return this.booksCount + this.authorsCount;
  }
}
```

**Pattern à trois états pour le chargement** :
```vue
<div v-if="loading" class="loading">Chargement...</div>
<div v-if="error" class="alert alert-error">{{ error }}</div>
<div v-if="!loading && !error && data.length > 0"><!-- Données --></div>
<div v-if="!loading && !error && data.length === 0" class="empty-state">
  Aucune donnée 🎉
</div>
```

## Documentation Guidelines

### Documentation Writing Best Practices

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

#### Example - Bad documentation:

```markdown
### Phase 0 Validation (Issue #75 - Implemented)

**New in Issue #75**: Phase 0 is now much better thanks to:
1. Double call confirmation (Issue #75)
2. Author correction (also Issue #75)

This is a major improvement over the previous implementation.
```

#### Example - Good documentation:

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

## Project Maintenance

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

### Linting and Code Quality

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
