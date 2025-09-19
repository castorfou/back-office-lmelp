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

### Verification Best Practices
**CRITICAL**: Always verify the actual state before marking tasks as completed.

- **Before marking any task as 'completed'**: Use appropriate tools to verify the action is actually accomplished
- **For Pull Requests**: Use `gh pr view <number>` to confirm merge status before declaring success
- **For deployments**: Check actual deployment status, not just pipeline success
- **For file changes**: Use `Read` or `ls` to verify files exist/changed as expected
- **For test results**: Verify all tests actually pass, not just assume from commands run

**Never rely solely on user declarations of intent** - always verify the real world state using available tools.

## API Discovery and Testing

### Backend API Discovery Method
When working with the backend API, use this systematic approach to discover endpoints and avoid trial-and-error:

#### Step 1: Discover Service Ports
```bash
# Check if services are running and on which ports
# TODO: This will be improved with Issue #56 (automatic port discovery)
# For now, common ports are: 54321, 54322, 8000

# Test if backend is running
curl -s "http://localhost:54321/" || curl -s "http://localhost:54322/" || curl -s "http://localhost:8000/"
```

#### Step 2: Get Complete API Schema
```bash
# Get the OpenAPI specification (replace PORT with actual port)
curl "http://localhost:PORT/openapi.json" | jq '.' > api-schema.json

# Quick endpoint discovery
curl "http://localhost:PORT/openapi.json" | jq -r '.paths | keys[]'
```

#### Step 3: Find Specific Endpoints
```bash
# Search for specific functionality
curl "http://localhost:PORT/openapi.json" | jq -r '.paths | keys[]' | grep -i KEYWORD

# Examples:
curl "http://localhost:54321/openapi.json" | jq -r '.paths | keys[]' | grep -i babelio
curl "http://localhost:54321/openapi.json" | jq -r '.paths | keys[]' | grep -i fuzzy
curl "http://localhost:54321/openapi.json" | jq -r '.paths | keys[]' | grep -i verify
```

#### Step 4: Get Endpoint Details
```bash
# Get request schema for a specific endpoint
curl "http://localhost:PORT/openapi.json" | jq '.paths["/api/endpoint"].post.requestBody'

# Get response schema
curl "http://localhost:PORT/openapi.json" | jq '.paths["/api/endpoint"].post.responses'

# Get component schemas
curl "http://localhost:PORT/openapi.json" | jq '.components.schemas.SchemaName'
```

#### Step 5: Test Endpoint with Correct Schema
```bash
# Use the discovered schema to make proper requests
curl -X POST "http://localhost:PORT/api/endpoint" \
  -H "Content-Type: application/json" \
  -d '{"field": "value"}'
```

### Common Backend Endpoints
Based on current API discovery:

```bash
# API health check
GET /

# API documentation
GET /docs
GET /openapi.json

# Babelio verification
POST /api/verify-babelio
# Required: {"type": "author|book", "name": "...", "title": "...", "author": "..."}

# TODO: Document other endpoints as discovered
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

**Note**: This methodology will be enhanced with Issue #56 to include automatic port discovery.

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
- **Automatic deployment**: GitHub Actions on docs changes

## Project Maintenance Guidelines

### Test Count Management
**NEVER include specific test counts** in documentation (README.md, CLAUDE.md). These numbers become stale quickly and provide no real value:
- ❌ "Run backend tests (176 tests)"
- ✅ "Run backend tests"
- ❌ "Total: 276 tests validés"
- ✅ "Tests complets validés"

Rationale: Test counts change frequently and require constant maintenance without adding meaningful information for users or developers.
