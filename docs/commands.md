# Commands

Toutes les commandes que je suis amene a lancer souvent dans le cadre de ce projet

## resinstalle claude (apres rebuild devcontainer)

```bash
npm install -g @anthropic-ai/claude-code
claude --resume
```

## lancement backend - frontend

```bash
# backend, demarrage sur port API_PORT
python -m back_office_lmelp.app

# frontend
cd frontend && npm run dev

# en une seule commande
./scripts/start-dev.sh
```

## lancement des tests

```bash
# Tests backend uniquement
pytest -v

# Tests frontend uniquement
cd /workspaces/back-office-lmelp/frontend && npm test -- --run

# Ou en une commande :
pytest -v && cd /workspaces/back-office-lmelp/frontend && npm test -- --run
```

## "Failed to add the ECDSA host key ..." - maj du ssh known_host

Le devcontainer monte ta config SSH depuis l'hôte en bind-mount. Dans devcontainer.json on a cette ligne :

source=${localEnv:HOME}/.ssh,target=/home/vscode/.ssh,type=bind,consistency=cached,readonly
Explication courte :

Le dossier ~/.ssh de l'hôte est monté dans le conteneur (donc les clés privées sont accessibles au conteneur).
Le mount est en readonly, donc le conteneur ne peut pas écrire dans known_hosts — d'où l'erreur "Failed to add the ECDSA host key ...".

le prb

```bash
(.venv) vscode ➜ /workspaces/back-office-lmelp (main) $ git push
Failed to add the ECDSA host key for IP address '140.82.121.3' to the list of known hosts (/home/vscode/.ssh/known_hosts).
Everything up-to-date
```

à faire

```bash
# ajouter la clé publique de l'IP GitHub sur l'hôte
ssh-keyscan -H 140.82.121.3 >> ~/.ssh/known_hosts

# vérifier que l'entrée a bien été ajoutée
ssh-keygen -F 140.82.121.3
```

## reseau port utilise

```bash
# depuis le host (sous devcontainer ne rend pas la main)
lsof -i:8000

# depuis devcontainer
netstat -tlnp | grep :8000
fuser -k 8000/tcp 2>/dev/null; sleep 2; netstat -tlnp | grep :8000
```

## voir la todo de claude code

Avec `ctrl-t` pour voir les taches en cours

```text
 Creating documentation modifications… (esc to interrupt · ctrl+t to hide todos)
  ⎿  ☒ Use gh issue view to get issue 31 details
     ☒ Create feature branch from issue using gh issue develop 31
     ☒ Checkout to the feature branch locally
     ☒ Understand the problem described in the issue
     ☒ Search for relevant files in the codebase
     ☒ Implement fix using TDD - write failing tests first
     ☒ Write code to make tests pass
     ☒ Iterate between code and test execution until complete resolution
     ☒ Verify all tests, lint, and typecheck pass
     ☐ Create necessary modifications in user and developer documentation
     ☐ Commit atomically with descriptive message and push changes
     ☐ Verify CI/CD state using gh run view
     ☐ Ask user for global testing and iterate if needed
     ☐ Update README.md and CLAUDE.md if necessary
     ☐ Prepare pull request and ask user for validation, then merge using gh
     ☐ Close todo list when empty
     ☐ Switch back to main branch locally and get latest changes
     ☐ Call /stocke-memoire to finish
```
