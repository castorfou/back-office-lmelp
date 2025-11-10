# CLAUDE.md

This file provides quick guidance to Claude Code (claude.ai/code) when working with code in this repository.

**📘 For detailed explanations, patterns, and best practices**, see [Claude AI Development Guide](docs/dev/claude-ai-guide.md).

## Project Overview

Full-stack application for managing database related to lmelp project:
- **Backend**: Python FastAPI with MongoDB integration
- **Frontend**: Vue.js 3 SPA with Vite build system
- **Environment**: VS Code devcontainers (Docker-based)
- **Dual toolchains**: uv (Python) + npm (Node.js)

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
**ALWAYS follow TDD for all code changes**:
1. Write failing tests first (RED)
2. Implement minimal code to pass (GREEN)
3. Refactor while keeping tests green (REFACTOR)

**Never implement code without corresponding tests.**

### Backend Testing - Key Rules

**CRITICAL Rules** (see [detailed guide](docs/dev/claude-ai-guide.md) for explanations):

1. **Mock external dependencies** (MongoDB, APIs, services) - NO real database connections in unit tests
2. **Create mocks from real API responses** - NEVER invent mock structures
3. **Use helper function pattern** for services with complex dependencies
4. **Patch singleton instances** directly when using local imports
5. **Verify database updates** with `mock_collection.update_one.assert_called_with(...)`

### Frontend Testing - Key Rules

1. **Reset mocks between tests**: Use `vi.resetAllMocks()` in `beforeEach`
2. **Prefer `mockResolvedValueOnce`** over persistent `mockImplementation`
3. **Watch for mock pollution**: Closures in `mockImplementation` persist across tests

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
