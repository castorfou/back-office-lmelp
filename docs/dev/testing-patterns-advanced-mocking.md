# Advanced Mocking Patterns for Backend Testing

## Overview

This document describes critical mocking patterns discovered during Issue #67 implementation. These patterns solve common testing challenges when dealing with:
- Services with complex dependency injection
- Singleton services with local imports
- MongoDB service mocking

**Context**: These patterns emerged after 12 failed test attempts using standard pytest fixtures and module-level patching. The solutions documented here are battle-tested and eliminate common "Connexion MongoDB non établie" errors.

## Pattern 1: Helper Function for Services with Dependency Injection

### Problem

Testing services that initialize dependencies in `__init__()` or use attribute assignment is difficult with pytest fixtures when methods use local imports.

```python
# ❌ PROBLEMATIC: Pytest fixture approach
@pytest.fixture
def collections_service(mock_mongodb_service):
    with patch.object(CollectionsManagementService, "mongodb_service", mock_mongodb_service):
        service = CollectionsManagementService()
        return service
```

**Why this fails:**
- Services use **local imports** inside methods (e.g., `from bson import ObjectId`)
- Patching at module level doesn't intercept calls after service instantiation
- Dependency injection happens in `__init__`, but method-level imports bypass mocks

### Solution: Create Mocked Service Helper

```python
def create_mocked_service():
    """Creates service with all mocks configured.

    Recommended pattern for testing services with injected dependencies.
    Avoids pytest fixture issues with patch.object().
    """
    from bson import ObjectId

    service = CollectionsManagementService()

    # Mock mongodb_service directly on instance
    mock_mongodb = Mock()
    mock_mongodb.create_author_if_not_exists.return_value = ObjectId("507f1f77bcf86cd799439014")
    mock_mongodb.create_book_if_not_exists.return_value = ObjectId("507f1f77bcf86cd799439015")
    mock_mongodb.update_avis_critique = Mock(return_value=True)
    mock_mongodb.get_avis_critique_by_id.return_value = None

    # Mock MongoDB collections
    mock_mongodb.avis_critiques_collection = Mock()
    mock_mongodb.livres_collection = Mock()

    # Direct injection (bypasses __init__)
    service.mongodb_service = mock_mongodb
    service._mock_mongodb = mock_mongodb  # For test access

    return service
```

### Usage in Tests

```python
def test_should_update_summary():
    # Arrange
    service = create_mocked_service()

    # Configure mock for this specific test
    service._mock_mongodb.get_avis_critique_by_id.return_value = {
        "_id": "507f...",
        "summary": "Original text"
    }

    book_data = {"auteur": "Author", "titre": "Title"}

    # Act
    service.handle_book_validation(book_data)

    # Assert
    assert service._mock_mongodb.update_avis_critique.called
```

### When to Use

**✅ Use helper functions when:**
- Service has multiple dependencies (MongoDB, cache, external APIs)
- Dependencies set via `__init__` or attribute assignment
- Methods use local imports (`from bson import ObjectId`)
- Need fine-grained control over mock configuration per test

**❌ Use fixtures when:**
- Mocking simple external modules (no dependency injection)
- Setting up test data (dictionaries, lists, constants)
- Sharing configuration across multiple tests
- No complex service initialization

## Pattern 2: Singleton Service with Local Imports

### Problem

**CRITICAL**: Standard module-level patching does NOT work for singleton services imported locally inside methods.

```python
# ❌ PROBLEMATIC: Service method with local import
class CollectionsManagementService:
    def handle_book_validation(self, book_data):
        # Local import inside method
        from ..services.livres_auteurs_cache_service import livres_auteurs_cache_service

        # This calls the REAL singleton, not the mock!
        livres_auteurs_cache_service.mark_as_processed(cache_id, author_id, book_id)
```

**Why module-level patching fails:**

```python
# ❌ This doesn't work
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

### Solution: Patch Global Singleton Instance

**✅ GOOD: Patch methods on the global instance, not the module**

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
```

### Usage in Tests

```python
def test_with_singleton_service():
    service = create_mocked_service()
    book_data = {...}

    # Apply all patches from helper
    patches = patch_cache_service()
    with patches[0], patches[1], patches[2]:
        service.handle_book_validation(book_data)

        # Assertions
        assert service._mock_mongodb.update_avis_critique.called
```

### Why Tuple of Patches?

Python's `with` statement requires each patch to be applied individually:

```python
# ✅ Correct: Unpack tuple manually
patches = patch_cache_service()
with patches[0], patches[1], patches[2]:
    # test code

# ❌ Wrong: Can't use tuple directly
with patch_cache_service():  # TypeError
    # test code
```

### When to Use

**✅ Use singleton instance patching when:**
- Service uses `from ..module import singleton_instance` **inside methods**
- Standard module patching fails with "not connected" or "not initialized" errors
- Imported object is a **singleton instance** (not a class)
- Singleton instantiated at module level (`service = Service()`)

**❌ Use standard module patching when:**
- Imports happen at **module level** (top of file)
- Importing a **class**, not an instance
- No local imports inside methods

## Complete Example: Issue #67 Summary Correction Tests

### Test File Structure

```python
# File: tests/test_avis_critique_summary_correction.py

from unittest.mock import Mock, patch
from bson import ObjectId
from back_office_lmelp.services.collections_management_service import CollectionsManagementService


def create_mocked_service():
    """Helper: Create service with mocked MongoDB dependencies."""
    service = CollectionsManagementService()

    mock_mongodb = Mock()
    mock_mongodb.create_author_if_not_exists.return_value = ObjectId("507f1f77bcf86cd799439014")
    mock_mongodb.create_book_if_not_exists.return_value = ObjectId("507f1f77bcf86cd799439015")
    mock_mongodb.update_avis_critique = Mock(return_value=True)
    mock_mongodb.get_avis_critique_by_id.return_value = None

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


class TestAvisCritiqueSummaryCorrection:
    def test_should_update_summary_with_correction(self):
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
        }

        # Act - Patch singleton before calling method with local import
        patches = patch_cache_service()
        with patches[0], patches[1], patches[2]:
            service.handle_book_validation(book_data)

        # Assert
        assert service._mock_mongodb.update_avis_critique.called
        updates = service._mock_mongodb.update_avis_critique.call_args[0][1]
        assert "Alain Mabanckou" in updates["summary"]

    def test_idempotence_skip_if_already_corrected(self):
        # Arrange
        service = create_mocked_service()
        book_data = {...}

        # Act - Use is_already_corrected=True for idempotence test
        patches = patch_cache_service(is_already_corrected=True)
        with patches[0], patches[1], patches[2]:
            service.handle_book_validation(book_data)

        # Assert - Should NOT update (already corrected)
        service._mock_mongodb.update_avis_critique.assert_not_called()
```

## Common Pitfalls to Avoid

### ❌ Pitfall 1: Patching the Wrong Path

```python
# Wrong: Patches module namespace, not singleton instance
with patch("back_office_lmelp.services.collections_management_service.livres_auteurs_cache_service"):
    pass  # Local import still gets real singleton
```

### ❌ Pitfall 2: Patching Too Late

```python
# Wrong: Service already called before patch applied
service.handle_book_validation(book_data)  # Uses real singleton
with patch("...livres_auteurs_cache_service.mark_as_processed"):
    pass  # Too late!
```

### ✅ Correct Timing

```python
patches = patch_cache_service()
with patches[0], patches[1], patches[2]:
    service.handle_book_validation(book_data)  # Patches active during call
```

## Architecture Implications

### Why Singletons with Local Imports Are Problematic

1. **Testability**: Harder to mock, requires instance-level patching
2. **Import Cycles**: Local imports often indicate circular dependencies
3. **Predictability**: Harder to reason about when dependencies are resolved

### Better Alternative: Dependency Injection

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

### When to Use Local Imports (Acceptable Cases)

- Breaking circular import cycles (temporary fix)
- Lazy loading for performance (rare)
- Type checking only (`if TYPE_CHECKING:`)

## Best Practices Summary

1. **Name helpers clearly**: `create_mocked_service()` not `get_service()`
2. **Document why**: Add docstring explaining pattern avoids fixture issues
3. **Expose mocks**: Store mock in `service._mock_xyz` for assertions
4. **Configure defaults**: Set safe default return values
5. **Per-test customization**: Override specific behaviors in each test
6. **Prefer dependency injection**: Refactor to DI when possible for easier testing

## Test Results

Using these patterns, Issue #67 achieved:
- **12/12 tests passing** (100% success rate)
- **94% coverage** of `summary_updater.py`
- **45% coverage** of `collections_management_service.py` (improved from 29%)
- **Zero "Connexion MongoDB non établie" errors**

## References

- **Issue #67**: Mise à jour du summary après validation
- **CLAUDE.md**: Lines 385-819 (full technical documentation for Claude Code)
- **Test File**: `tests/test_avis_critique_summary_correction.py`
- **Discovered**: After 12 failed test attempts with standard mocking approaches

## Maintenance

When encountering "Connexion MongoDB non établie" errors in tests:

1. Check if service uses **local imports** inside methods
2. Check if imported object is a **singleton instance**
3. Apply **Pattern 2** (singleton instance patching)
4. Use helper functions from this document
5. Verify patches applied **before** method call

This documentation serves as a reference for all future test development involving complex service dependencies and singleton patterns.
