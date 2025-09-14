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

# Run backend tests (116 tests)
PYTHONPATH=/workspaces/back-office-lmelp/src pytest tests/ -v --cov=src --cov-report=term-missing

# Run pre-commit hooks manually
pre-commit run --all-files
```

### Frontend Setup and Commands
```bash
# Install frontend dependencies
cd frontend && npm ci

# Run frontend tests (31 tests)
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
# Run all tests (147 total: 116 backend + 31 frontend)
PYTHONPATH=/workspaces/back-office-lmelp/src pytest tests/ -v && cd frontend && npm test -- --run
```

### Development Scripts
```bash
# Start both backend and frontend with unified script
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
