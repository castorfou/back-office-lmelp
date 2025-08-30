# Commands

Toutes les commandes que je suis amene a lancer souvent dans le cadre de ce projet

## resinstalle claude (apres rebuild devcontainer)

```bash
npm install -g @anthropic-ai/claude-code
claude
```

## reseau port utilise

```bash
# depuis le host (sous devcontainer ne rend pas la main)
lsof -i:8000

# depuis devcontainer
netstat -tlnp | grep :8000
fuser -k 8000/tcp 2>/dev/null; sleep 2; netstat -tlnp | grep :8000
```

## lancement backend - frontend

```bash
# backend, demarrage sur port API_PORT
API_PORT=54322 python -m back_office_lmelp.app

# frontend
cd frontend && npm run dev
```

## lancement des tests

```bash
# Tests backend uniquement
PYTHONPATH=/workspaces/back-office-lmelp/src uv run pytest -v

# Tests frontend uniquement
cd frontend && npm test

# Ou en une commande :
PYTHONPATH=/workspaces/back-office-lmelp/src uv run pytest -v && cd frontend && npm test -- --run
```
