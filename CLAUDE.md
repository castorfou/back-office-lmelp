# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python data science project for managing a database related to the lmelp project. It uses **uv** for dependency management and follows modern Python development practices with comprehensive tooling for code quality.

## Development Environment

The project is designed to work in VS Code with devcontainers (Docker-based development environment). The main development workflow uses uv as the package manager.

## Essential Commands

### Setup and Installation
```bash
# Install dependencies
uv sync --extra dev

# Install pre-commit hooks (required for contributors)
pre-commit install
```

### Development Commands
```bash
# Run linting
uv run ruff check . --output-format=github

# Format code
uv run ruff format .

# Type checking
uv run mypy src/

# Run tests
uv run pytest tests/ -v --cov=src --cov-report=term-missing

# Build package
uv build

# Run pre-commit hooks manually
uv run pre-commit run --all-files
```

### Project Structure
```
├── src/                    # Main source code
├── data/                   # Data files
│   ├── raw/               # Raw data
│   └── processed/         # Processed data
├── notebooks/             # Jupyter notebooks
├── tests/                 # Test files
└── pyproject.toml         # Project configuration
```

## Code Quality Standards

- **Linting & Formatting**: Uses Ruff (replaces flake8, black, isort)
- **Type Checking**: MyPy with progressive strictness
- **Pre-commit Hooks**: Enforces code quality, security scanning, and format consistency
- **Line Length**: 88 characters (consistent with Black)
- **Python Version**: Requires Python 3.11+

## Key Configuration Notes

- Ruff configuration excludes data/, models/, logs/, and .jupyter/ directories
- MyPy ignores missing imports for common data science libraries (matplotlib, sklearn, etc.)
- Pre-commit hooks include security scanning with detect-secrets
- CI/CD runs on Python 3.11 and 3.12

## Testing

Tests are located in the `tests/` directory. The CI will create placeholder tests if none exist. Use pytest for testing with coverage reporting.

## Dependencies

Key production dependencies include:
- pandas, numpy, matplotlib (data science stack)
- ipykernel, ipywidgets (Jupyter support)
- python-dotenv, gitpython (utilities)

Development dependencies managed via uv include pytest, ruff, mypy, and pre-commit.
