#!/usr/bin/env bash
# =============================================================================
# Authentification GitHub (gh) au premier terminal zsh (issue #64)
# Appelé depuis ~/.zshrc : seuls les terminaux VS Code reçoivent $BROWSER, qui
# ouvre l'URL de connexion dans le navigateur de l'hôte (pas postCreateCommand).
# La config gh est partagée entre devcontainers (~/.config/gh-devcontainers sur l'hôte).
# =============================================================================

MARKER="${GH_LOGIN_MARKER:-/tmp/.gh-login-attempted}"

command -v gh > /dev/null 2>&1 || exit 0

# `gh auth token` lit hosts.yml sans réseau, contrairement à `gh auth status`
gh auth token > /dev/null 2>&1 && exit 0

# Une seule tentative par conteneur : on ne relance pas à chaque terminal
if [ -e "$MARKER" ]; then
    echo "ℹ️  GitHub CLI non authentifié : lancez 'gh auth login --web'"
    exit 0
fi
touch "$MARKER"

echo "🔐 Authentification GitHub (gh), partagée par tous vos devcontainers"
echo "   Le navigateur de l'hôte va s'ouvrir : collez-y le code affiché ci-dessous."
gh auth login --hostname github.com --git-protocol https --web --skip-ssh-key \
    || echo "⚠️  Authentification interrompue : relancez 'gh auth login --web'"
exit 0
