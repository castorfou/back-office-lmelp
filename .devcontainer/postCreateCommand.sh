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

# Fuseau de l'hôte : son /etc/localtime est monté sur /etc/localtime.host (issue #65).
# Monté directement sur /etc/localtime, lien vers zoneinfo/Etc/UTC, il écraserait Etc/UTC :
# UTC deviendrait l'heure locale et la mise à jour de tzdata échouerait.
# On fait pointer /etc/localtime vers la zone de même contenu, pour garder son nom.
setup_timezone() {
    local host_tz="${HOST_LOCALTIME:-/etc/localtime.host}"
    local zoneinfo="${ZONEINFO_DIR:-/usr/share/zoneinfo}"
    local etc_dir="${ETC_DIR:-/etc}"

    if [ ! -s "$host_tz" ]; then
        echo "⚠️  Fuseau de l'hôte introuvable ($host_tz) : le conteneur reste en UTC"
        return 0
    fi

    local zone
    zone=$(cd "$zoneinfo" && find . -type f ! -path './posix/*' ! -path './right/*' \
        -exec cmp -s "$host_tz" {} \; -print -quit)
    zone="${zone#./}"

    if [ -n "$zone" ]; then
        sudo ln -sfn "$zoneinfo/$zone" "$etc_dir/localtime"
        echo "$zone" | sudo tee "$etc_dir/timezone" > /dev/null
        echo "✅ Fuseau horaire : $zone"
    else
        sudo ln -sfn "$host_tz" "$etc_dir/localtime"
        echo "✅ Fuseau horaire : celui de l'hôte (zone non identifiée)"
    fi
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


# Active le venv dans chaque terminal, s'il existe : un terminal peut s'ouvrir avant que
# postStartCommand l'ait recréé (issue #86). Le HOME est persistant : on retire la ligne
# non protégée des versions précédentes.
setup_venv_activation() {
    local zshrc="$HOME/.zshrc"
    if [ -f "$zshrc" ]; then
        sed -i '\#^source /tmp/venv/bin/activate$#d' "$zshrc"
    fi
    ensure_zshrc_line '[[ ! -f /tmp/venv/bin/activate ]] || source /tmp/venv/bin/activate'
}

# Le HOME est un dossier de l'hôte monté sur /home/vscode : il masque celui de l'image.
# On recopie les fichiers par défaut (.bashrc, .profile...) sans écraser l'existant.
seed_home() {
    echo "Initialisation du HOME persistant..."
    # "|| true" : certaines versions de coreutils renvoient une erreur quand des fichiers existent déjà
    cp -rn /etc/skel/. "$HOME" || true
    echo "✅ HOME initialisé"
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
    # Hors du HOME persistant, dans /tmp/venv : recréé à chaque rebuild, et au démarrage
    # par postStartCommand s'il manque (scripts/ensure_venv.sh, issue #86)
    PYTHON_VERSION="$PYTHON_VERSION" bash .devcontainer/scripts/ensure_venv.sh --sync
    # Les étapes suivantes (pre-commit...) utilisent les outils du venv
    source /tmp/venv/bin/activate
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

# Installation du navigateur Chrome pour Playwright MCP
install_playwright_browsers() {
    echo "Installation du navigateur Chrome pour Playwright MCP..."

    if npx -y playwright install --with-deps chrome; then
        echo "✅ Chrome installé pour Playwright"
    else
        echo "⚠️  Échec de l'installation de Chrome pour Playwright, ignoré"
    fi

    echo "Installation des polices d'émojis (rendu correct des icônes dans les captures d'écran)..."
    if sudo apt-get install -y -qq fonts-noto-color-emoji; then
        echo "✅ Polices d'émojis installées"
    else
        echo "⚠️  Échec de l'installation des polices d'émojis, ignoré"
    fi

    echo "Installation de Playwright terminée"
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
# git commit, y compris sans identité : au premier build, le HOME est neuf et
# l'identité de l'hôte n'arrive qu'après postCreateCommand. Identité ponctuelle
# pour ce seul commit, jamais écrite dans .git/config où elle masquerait la
# globale (#94, #102). Arguments : ceux de git commit.
git_commit_with_fallback() {
    if [ -n "$(git config user.email)" ]; then
        git commit "$@"
        return
    fi
    local name="${GITHUB_USERNAME:-PyFoundry}"
    local email="${GITHUB_USERNAME:-pyfoundry}@users.noreply.github.com"
    git -c user.name="$name" -c user.email="$email" commit "$@" || return
    if [ -z "${IDENTITY_WARNED:-}" ]; then
        IDENTITY_WARNED=1
        echo "⚠️  Identité Git non configurée : commits faits sous $name <$email>"
        echo "    Configurez la vôtre avec :"
        echo "    git config --global user.name \"Prénom Nom\""
        echo "    git config --global user.email \"vous@exemple.com\""
    fi
}

setup_git() {
    echo "Configuration Git..."
    if [ ! -d ".git" ]; then
        echo "Initialisation du dépôt Git..."
        git init
        git branch -M main
        git add .
        git_commit_with_fallback -m "Initial commit"
        echo "✅ Dépôt Git initialisé et premier commit effectué"
    else
        echo "Dépôt Git déjà existant"
        # Ancienne identité par défaut écrite dans .git/config par les versions
        # précédentes : elle masque l'identité globale de l'utilisateur (#94)
        if [ "$(git config --local user.email)" = "default@michelin.com" ] \
            && [ "$(git config --local user.name)" = "Default User" ]; then
            git config --local --unset user.email
            git config --local --unset user.name
            echo "✅ Identité Git par défaut (Default User) retirée de .git/config"
        fi
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

            # Commiter la seule config mise à jour par autoupdate : `git commit -- fichier`
            # laisse intacts l'index et le travail en cours (pas de `git add .`)
            if ! git diff --quiet -- .pre-commit-config.yaml; then
                echo "Commit de la mise à jour des hooks pre-commit..."
                if ! git_commit_with_fallback -m "chore: update pre-commit hooks to latest versions" -- .pre-commit-config.yaml; then
                    echo "⚠️  Commit impossible : .pre-commit-config.yaml mis à jour mais non commité"
                fi
            fi

            echo "✅ Pre-commit hooks installés et mis à jour"
        else
            echo "⚠️  pre-commit non installé, ignoré"
        fi
    fi
}


# Git délègue l'authentification HTTPS GitHub à gh (config locale au projet).
# Configuré même sans token : il peut venir plus tard ou d'un autre devcontainer,
# la config gh étant partagée.
setup_gh_credential_helper() {
    command -v gh &> /dev/null || return 0
    git config credential.helper ""
    git config credential."https://github.com".helper "!gh auth git-credential"
    echo "✅ Credential helper Git configuré (gh)"
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

        # Authentification GitHub : pas de login interactif ici, le navigateur ne peut pas
        # s'ouvrir. Elle est proposée au premier terminal zsh (scripts/gh_login.sh).
        if command -v gh &> /dev/null; then
            setup_gh_credential_helper
            if gh auth token &>/dev/null; then
                echo "✅ Déjà authentifié sur GitHub"
            else
                echo "🔐 Authentification GitHub : ouvrez un terminal, elle y sera proposée"
            fi
        fi

        echo "✅ Remote GitHub configuré"
    fi

    echo "Configuration Git terminée"
}

# Helper: update MkDocs repo_url from Git remote
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

    setup_venv_activation

    # Propose l'authentification gh tant qu'elle manque (terminal VS Code : $BROWSER ouvre l'hôte)
    ensure_zshrc_line 'bash "$WORKSPACE_FOLDER/.devcontainer/scripts/gh_login.sh"'

    echo "✅ zsh configuré"
}


# Exécution des étapes
seed_home
update_system
setup_timezone
ensure_uv
# install_calibre
create_python_environment
setup_node
install_playwright_browsers
setup_git
setup_github
setup_pre-commit
config_zsh

echo ""
echo "=================================================================="
echo "✅ Configuration terminée !"
echo "Dépôt Git initialisé avec pre-commit hooks"
echo "Node.js et npm configurés pour le développement frontend"
echo "Redémarrez le terminal pour activer l'environnement"
