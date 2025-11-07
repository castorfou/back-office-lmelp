# MyPy Type Stubs with Pre-commit - Best Practices

## Problem Statement

When adding a new Python library that requires type stubs (e.g., `beautifulsoup4`, `requests`, `aiohttp`), developers may encounter mypy `import-not-found` errors in pre-commit hooks, even though type stubs are correctly installed in the local development environment.

**Typical error message:**
```
mypy (type check)........................................................Failed
- hook id: mypy
- exit code: 1

src/module/file.py:34: error: Cannot find implementation or library stub for module named "bs4"  [import-not-found]
```

## Root Cause

Pre-commit runs mypy in an **isolated environment** separate from your project's virtual environment. This isolated environment has its own Python installation and dependency set, defined exclusively in `.pre-commit-config.yaml`.

**Key insight**: Installing type stubs via `pip install`, `uv pip install`, or adding them to `pyproject.toml` only affects your **local environment**, not pre-commit's isolated environment.

## Anti-Pattern: Type Ignore Comments

**❌ WRONG Solution**:
```python
from bs4 import BeautifulSoup  # type: ignore[import-untyped]
```

**Why this is bad:**
- Suppresses legitimate type checking errors
- Accumulates technical debt (`type: ignore` comments proliferate)
- Breaks in CI/CD if the type stub is actually missing
- Hides real import issues
- Violates mypy strict mode principles

## Correct Solution: Dual Declaration

Type stubs must be declared in **TWO locations**:

### 1. Add to `pyproject.toml` (local mypy runs)

```toml
[project.optional-dependencies]
dev = [
    "mypy>=1.5.0",
    "types-beautifulsoup4",     # ✅ For local mypy runs
    "types-requests",            # Example: types for requests library
    "types-aiohttp",             # Example: types for aiohttp library
    ...
]
```

### 2. Add to `.pre-commit-config.yaml` (pre-commit mypy runs)

```yaml
- repo: https://github.com/pre-commit/mirrors-mypy
  rev: v1.18.2
  hooks:
    - id: mypy
      name: mypy (type check)
      files: ^src/.*\.py$
      additional_dependencies:
        - pandas-stubs
        - types-python-dateutil
        - types-requests
        - rapidfuzz
        - types-beautifulsoup4      # ✅ For pre-commit mypy runs
      args: [--config-file=pyproject.toml]
```

### 3. Reinstall Pre-commit Hooks

After modifying `.pre-commit-config.yaml`, pre-commit needs to rebuild its isolated environment:

```bash
# Clean pre-commit cache
pre-commit clean

# Reinstall hooks with new dependencies
pre-commit install

# Test manually
pre-commit run mypy --all-files
```

## Verification Workflow

After adding new type stubs:

```bash
# 1. Install locally
uv pip install -e ".[dev]"

# 2. Verify local mypy works
mypy src/

# 3. Clean pre-commit cache
pre-commit clean

# 4. Test pre-commit mypy
pre-commit run mypy --all-files

# 5. Full pre-commit test
pre-commit run --all-files
```

## Complete Example: Adding BeautifulSoup4 (Issue #85)

### Scenario
Adding `beautifulsoup4` for HTML scraping in `babelio_service.py`:

```python
from bs4 import BeautifulSoup
```

### Step-by-Step Fix

**1. Identify the type stub package:**
- For `beautifulsoup4`, the type stub is `types-beautifulsoup4`
- Check PyPI or use: `pip search types-beautifulsoup4`

**2. Add to `pyproject.toml`:**
```toml
[project.dependencies]
dependencies = [
    ...
    "beautifulsoup4>=4.12.0",
    "lxml>=4.9.0"
]

[project.optional-dependencies]
dev = [
    ...
    "types-beautifulsoup4",  # ← Add this
]
```

**3. Add to `.pre-commit-config.yaml`:**
```yaml
- repo: https://github.com/pre-commit/mirrors-mypy
  hooks:
    - id: mypy
      additional_dependencies:
        - types-beautifulsoup4  # ← Add this
```

**4. Install and test:**
```bash
# Install dev dependencies
uv pip install -e ".[dev]"

# Clean pre-commit cache
pre-commit clean

# Test mypy locally
mypy src/

# Test mypy in pre-commit
pre-commit run mypy --all-files
```

## Why This Architecture?

### Benefits
- ✅ **Consistent type checking** between local dev and CI/CD
- ✅ **No suppression comments** cluttering code
- ✅ **Explicit dependencies** visible in both environments
- ✅ **CI/CD mirrors local** - same mypy behavior everywhere

### Trade-offs
- Requires updating two files (small maintenance cost)
- Pre-commit environment takes longer to initialize first time
- Must remember to clean pre-commit cache after changes

## Common Type Stub Packages

| Library | Type Stub Package | Use Case |
|---------|------------------|----------|
| `beautifulsoup4` | `types-beautifulsoup4` | HTML/XML parsing |
| `requests` | `types-requests` | HTTP client |
| `aiohttp` | `types-aiohttp` | Async HTTP |
| `psutil` | `types-psutil` | System monitoring |
| `redis` | `types-redis` | Redis client |
| `Pillow` | `types-Pillow` | Image processing |

## Troubleshooting

### "Cannot find implementation or library stub"

**Symptom**: Pre-commit mypy fails with `import-not-found` but local mypy passes.

**Solution**:
1. Check if type stub is in `.pre-commit-config.yaml` → `additional_dependencies`
2. Run `pre-commit clean` to rebuild environment
3. Verify stub name matches PyPI package (e.g., `types-beautifulsoup4`, not `beautifulsoup4-stubs`)

### "Stashed changes conflicted with hook auto-fixes"

**Symptom**: Pre-commit shows this warning and rolls back changes.

**Cause**: Ruff or other formatters modified files during pre-commit run.

**Solution**:
1. Stage the modified files: `git add -A`
2. Re-run commit: `git commit`

### Pre-commit Mypy Stuck on Old Version

**Symptom**: Changes to `.pre-commit-config.yaml` don't take effect.

**Solution**:
```bash
# Force rebuild of pre-commit environment
pre-commit clean
pre-commit install --install-hooks
```

## References

- [Pre-commit Documentation](https://pre-commit.com/)
- [MyPy Type Stubs](https://mypy.readthedocs.io/en/stable/stubs.html)
- [Issue #85 - BeautifulSoup4 Type Stubs](https://github.com/castorfou/back-office-lmelp/issues/85)
- [Pre-commit Isolated Environments](https://pre-commit.com/#pre-commit-run)
