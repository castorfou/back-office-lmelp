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
uv sync --extra dev

# Install pre-commit hooks (required for contributors)
pre-commit install

# Run backend application (port 54322 to avoid conflicts)
PYTHONPATH=/workspaces/back-office-lmelp/src API_PORT=54322 python -m back_office_lmelp.app

# Run backend linting
uv run ruff check . --output-format=github

# Format backend code
uv run ruff format .

# Type checking
uv run mypy src/

# Run backend tests (12 tests)
PYTHONPATH=/workspaces/back-office-lmelp/src uv run pytest tests/ -v --cov=src --cov-report=term-missing

# Run pre-commit hooks manually
uv run pre-commit run --all-files
```

### Frontend Setup and Commands
```bash
# Install frontend dependencies
cd frontend && npm ci

# Run frontend tests (26 tests)
cd frontend && npm test -- --run

# Start development server
cd frontend && npm run dev

# Build for production
cd frontend && npm run build

# Preview production build
cd frontend && npm run preview
```

### Full Test Suite
```bash
# Run all tests (38 total: 12 backend + 26 frontend)
PYTHONPATH=/workspaces/back-office-lmelp/src uv run pytest tests/ -v && cd frontend && npm test -- --run
```

### Documentation Commands
```bash
# Serve documentation locally (port 8000)
uv run mkdocs serve

# Build documentation (for deployment)
uv run mkdocs build --strict

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

## Key Configuration Notes

### Backend Configuration
- Ruff configuration excludes data/, models/, logs/, and .jupyter/ directories
- MyPy ignores missing imports for common data science libraries
- pytest with coverage reporting (40% current coverage)

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

### Backend Tests (12 tests)
- Location: `tests/` directory
- Framework: pytest with coverage
- Command: `PYTHONPATH=/workspaces/back-office-lmelp/src uv run pytest tests/ -v`
- Coverage: API endpoints, MongoDB service, memory guard utilities

### Frontend Tests (26 tests)
- Location: `frontend/tests/` directory
- Framework: Vitest with @vue/test-utils
- Command: `cd frontend && npm test -- --run`
- Coverage:
  - **Unit tests**: EpisodeSelector (7), EpisodeEditor (12)
  - **Integration tests**: HomePage (7)

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
- **Local development**: `uv run mkdocs serve` on port 8000
- **Production**: https://castorfou.github.io/back-office-lmelp/

### Structure
- **User documentation**: docs/user/ (guides, troubleshooting)
- **Developer documentation**: docs/dev/ (architecture, API, security)
- **Automatic deployment**: GitHub Actions on docs changes
