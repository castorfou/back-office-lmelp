#!/bin/bash
# =============================================================================
# back-office lmelp - Configuration de l'environnement de développement
# =============================================================================
set -e

PYTHON_VERSION="3.11"

echo "🚀 Configuration de l'environnement back-office lmelp"
echo "=================================================================="

# Mise à jour du système
update_system() {
    echo "Mise à jour des paquets système..."
    export DEBIAN_FRONTEND=noninteractive
    # Empêcher tzdata de poser des questions et utiliser la timezone UTC par défaut
    export TZ="Etc/UTC"


    echo "Configuration de la source APT Yarn..."
    sudo mkdir -p /etc/apt/keyrings

    if [ ! -f /etc/apt/keyrings/yarn.gpg ]; then
        echo "Installation de la clé GPG Yarn..."
        curl -fsSL https://dl.yarnpkg.com/debian/pubkey.gpg \
            | sudo gpg --dearmor -o /etc/apt/keyrings/yarn.gpg
    fi

    echo "deb [signed-by=/etc/apt/keyrings/yarn.gpg] https://dl.yarnpkg.com/debian stable main" \
        | sudo tee /etc/apt/sources.list.d/yarn.list > /dev/null

    sudo apt-get update -qq

    # Options dpkg pour éviter les prompts de configuration
    sudo apt-get -y -qq -o Dpkg::Options::="--force-confdef" \
        -o Dpkg::Options::="--force-confnew" upgrade || {
        echo "⚠️  'apt upgrade' a échoué ; continuer sans interrompre le postCreateCommand"
        return 0
    }

    echo "Système mis à jour"
}

# outil pour ajouter une ligne dans .zshrc si elle n'existe pas déjà
ensure_zshrc_line() {
    local line="$1"
    local zshrc="$HOME/.zshrc"
    if [ ! -f "$zshrc" ]; then
        touch "$zshrc"
    fi
    if ! grep -Fxq "$line" "$zshrc" 2>/dev/null; then
        echo "$line" >> "$zshrc"
    fi
}


# Vérification et installation d'uv (priorité: devcontainer feature, fallback: installation manuelle)
ensure_uv() {
    echo "Vérification de uv..."
    if command -v uv &> /dev/null; then
        echo "✅ uv disponible ($(uv --version))"
        return 0
    fi

    echo "❌ Échec d'installation d'uv"
    echo "   Vérifiez votre connexion Docker/ghcr.io (docker login ghcr.io)"
    exit 1
}

# Création de l'environnement Python
create_python_environment() {
    echo "Configuration de l'environnement Python $PYTHON_VERSION ..."

    echo "Création de l'environnement virtuel dans /home/vscode/.venv"
    VENV_HOME="/home/vscode/.venv"
    if [ -d "$VENV_HOME" ]; then
        echo "Un venv existe déjà à $VENV_HOME, je l'utilise."
    else
        uv venv "$VENV_HOME" --python $PYTHON_VERSION
    fi

    # Activer l'environnement créé dans $HOME/.venv
    source "$VENV_HOME/bin/activate"
    echo "Installation des dépendances..."
    # Utiliser --active pour cibler l'environnement virtuel activé (hors du dossier projet)
    uv sync --active --all-extras

    echo "Environnement Python configuré"

}

# Installation de Calibre
install_calibre() {
    echo "Installation de Calibre..."

    # Installer Calibre via apt
    sudo apt-get install -y -qq calibre

    # Vérifier l'installation
    if command -v calibre &> /dev/null; then
        echo "✅ Calibre installé ($(calibre --version | head -n1))"
    else
        echo "⚠️  Calibre non installé correctement"
    fi

    echo "Installation de Calibre terminée"
}

# Configuration Node.js et npm
setup_node() {
    echo "Configuration Node.js..."

    # Vérification de l'installation de Node.js
    if command -v node &> /dev/null; then
        echo "✅ Node.js disponible ($(node --version))"
        echo "✅ npm disponible ($(npm --version))"

        # Création d'un package.json basique s'il n'existe pas
        if [ ! -f "package.json" ]; then
            echo "Création du fichier package.json..."
            cat > package.json << EOF
{
  "name": "back-office-lmelp",
  "version": "1.0.0",
  "description": "un back offic pour gerer la base de donnee du projet https://github.com/castorfou/lmelp",
  "scripts": {
    "dev": "echo 'Add your development scripts here'",
    "build": "echo 'Add your build scripts here'"
  },
  "keywords": ["data-science", "python", "node"],
  "author": "castor_fou",
  "license": "MIT",
  "devDependencies": {}
}
EOF
            echo "✅ package.json créé"
        fi

        echo "Configuration npm terminée"
    else
        echo "⚠️  Node.js non disponible - vérifiez la configuration devcontainer"
    fi
}


# Configuration Git
setup_git() {
    echo "Configuration Git..."
    if [ ! -d ".git" ]; then
        echo "Initialisation du dépôt Git..."
        git init
        git branch -M main

        # Configuration de l'utilisateur si non défini (pour éviter l'échec du commit)
        if [ -z "$(git config --global user.email)" ]; then
            echo "Configuration d'un utilisateur Git par défaut..."
            git config user.email "default@michelin.com"
            git config user.name "Default User"
        fi

        git add .
        git commit -m "Initial commit"
        echo "✅ Dépôt Git initialisé et premier commit effectué"
    else
        echo "Dépôt Git déjà existant"
    fi
}


# Configuration pre-commit
setup_pre-commit() {

    # Configuration pre-commit si disponible
    if [ -f ".pre-commit-config.yaml" ]; then
        echo "Configuration des hooks pre-commit..."
        if command -v pre-commit &> /dev/null; then
            echo "Mise à jour des hooks vers les dernières versions..."
            pre-commit autoupdate
            pre-commit install

            echo "Pré-installation des environnements pre-commit..."
            # Force l'installation des environnements maintenant pour éviter les délais futurs
            pre-commit install-hooks

            # Commiter les changements de pre-commit autoupdate + corrections formatage
            if ! git diff --quiet 2>/dev/null || ! git diff --cached --quiet 2>/dev/null; then
                echo "Commit des mises à jour et corrections pre-commit..."
                git add .pre-commit-config.yaml

                # Correction du formatage par les hooks peut générer des changements
                if ! git commit -m "chore: update pre-commit hooks to latest versions" 2>/dev/null; then
                    # Si le commit échoue à cause des hooks, ajouter les corrections
                    echo "Ajout des corrections de formatage..."
                    git add .
                    git commit -m "chore: update pre-commit hooks and fix formatting" || true
                fi
            fi

            echo "✅ Pre-commit hooks installés et mis à jour"
        else
            echo "⚠️  pre-commit non installé, ignoré"
        fi
    fi
}


# Configuration GitHub
setup_github() {
    echo "Configuration GitHub..."



    # Configuration du remote GitHub si username fourni
    if [ "castorfou" != "votre-username" ]; then

        # choisir le protocole: SSH si possible, sinon HTTPS
        if ssh -o BatchMode=yes -T git@github.com 2>&1 | grep -iq "successfully authenticated"; then
            remote_url="git@github.com:castorfou/back-office-lmelp.git"
        else
            remote_url="https://github.com/castorfou/back-office-lmelp.git"
        fi

        echo "Configuration du remote GitHub : $remote_url"
        git remote get-url origin >/dev/null 2>&1 || git remote add origin "$remote_url"

        # Configuration de l'upstream pour la branche main
        git branch --set-upstream-to=origin/main main 2>/dev/null || true

        # Configuration automatique des upstream pour futures branches (local au projet)
        git config push.autoSetupRemote true

        # Configuration de l'authentification GitHub avec gh CLI
        if command -v gh &> /dev/null; then
            echo "Configuration de l'authentification GitHub..."
            if ! gh auth status &>/dev/null; then
                echo "🔐 Authentification GitHub requise pour push/pull"
                echo "Lancement de l'authentification..."
                echo ""
                echo "ℹ️  Note : Vous devrez appuyer sur Entrée pour 'ouvrir' le navigateur."
                echo "   Le navigateur ne s'ouvrira pas (limitation devcontainer connue)."
                echo "   → Entrez manuellement l'URL et le code dans votre navigateur host."
                echo ""
                gh auth login --git-protocol https --web

                # Configuration du credential helper après authentification (local au projet)
                if gh auth status &>/dev/null; then
                    echo "Configuration du credential helper Git..."
                    git config credential.helper ""
                    git config credential."https://github.com".helper "!gh auth git-credential"
                    echo "✅ Credential helper configuré"
                fi
            else
                echo "✅ Déjà authentifié sur GitHub"
            fi
        fi

        echo "✅ Remote GitHub configuré"
    fi

    echo "Configuration Git terminée"
}

# Helper: update MkDocs repo_url from Git remote
run_mkdocs_repo_url_update() {
    if [ -f "${WORKSPACE_FOLDER}/.devcontainer/scripts/update_mkdocs_repo_url.sh" ]; then
        chmod +x "${WORKSPACE_FOLDER}/.devcontainer/scripts/update_mkdocs_repo_url.sh" || true
        ( cd "${WORKSPACE_FOLDER}" && ./.devcontainer/scripts/update_mkdocs_repo_url.sh ) \
            || echo "[postCreate] update_mkdocs_repo_url.sh exited with non-zero status"
        echo "✅ mkdocs_repo_url configurée"
    else
        echo "[postCreate] ${WORKSPACE_FOLDER}/.devcontainer/scripts/update_mkdocs_repo_url.sh not found"
    fi
}

# config zsh
config_zsh() {
    echo "Configuration de zsh..."
    # Ajouter des configurations zsh spécifiques si nécessaire

    local p10k_source=".devcontainer/resources/.p10k.zsh"
    if [ -f "$p10k_source" ]; then
        echo "Copie du thème Powerlevel10k vers $HOME/.p10k.zsh..."
        cp "$p10k_source" "$HOME/.p10k.zsh"
        chmod 0644 "$HOME/.p10k.zsh"
    else
        echo "⚠️  Thème Powerlevel10k introuvable : $p10k_source"
    fi

    cd ~
    rm -rf .oh-my-zsh

    sudo apt install -y fonts-powerline

    # get last version at https://github.com/deluan/zsh-in-docker
    sh -c "$(wget -O- https://github.com/deluan/zsh-in-docker/releases/download/v1.2.1/zsh-in-docker.sh)" -- \
        -p git \
        -p python \
        -p history \
        -p 'history-substring-search' \
        -p 'virtualenv' \
        -p https://github.com/zsh-users/zsh-autosuggestions \
        -p https://github.com/zsh-users/zsh-completions

    ensure_zshrc_line '[[ ! -f ~/.p10k.zsh ]] || source ~/.p10k.zsh'

    ensure_zshrc_line 'export PATH="$HOME/.local/bin:$PATH"'

    ensure_zshrc_line 'source /home/vscode/.venv/bin/activate'

    echo "✅ zsh configuré"
}


# Exécution des étapes
update_system
ensure_uv
# install_calibre
create_python_environment
setup_node
setup_git
setup_github
setup_pre-commit
config_zsh
run_mkdocs_repo_url_update

echo ""
echo "=================================================================="
echo "✅ Configuration terminée !"
echo "Dépôt Git initialisé avec pre-commit hooks"
echo "Node.js et npm configurés pour le développement frontend"
echo "Redémarrez le terminal pour activer l'environnement"
