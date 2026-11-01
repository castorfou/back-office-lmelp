#!/usr/bin/env bash
# =============================================================================
# Venv du projet dans /tmp/venv, recréé s'il manque (issue #86)
# Appelé par postStartCommand à chaque démarrage, et par postCreateCommand.sh (--sync).
# Avec docker-in-docker, /tmp est un tmpfs remonté à chaque démarrage : un simple
# redémarrage du conteneur, sans rebuild, efface le venv. Le cache uv est persistant,
# la recréation est rapide.
# Le venv est installé depuis uv.lock sans jamais le réécrire (issue #87).
#   --sync : synchronise les dépendances même si le venv existe déjà
# =============================================================================

VENV_HOME="${VENV_HOME:-/tmp/venv}"
PYTHON_VERSION="${PYTHON_VERSION:-3.11}"

fail() {
    echo "❌ $1"
    echo "   Pour le recréer à la main :"
    echo "   uv venv $VENV_HOME --python $PYTHON_VERSION && uv sync --frozen --active --all-extras"
    exit 1
}

sync=false
[ "$1" = "--sync" ] && sync=true

# On teste l'interpréteur, pas le dossier : un venv à moitié créé est refait
if [ ! -x "$VENV_HOME/bin/python" ]; then
    echo "Création de l'environnement virtuel dans $VENV_HOME (Python $PYTHON_VERSION)"
    # --python explicite : UV_PYTHON pointe sur l'interpréteur du venv, absent ici
    uv venv "$VENV_HOME" --python "$PYTHON_VERSION" || fail "Création du venv impossible"
    sync=true
fi

if [ "$sync" = true ]; then
    echo "Installation des dépendances..."
    # --frozen : installe uv.lock tel quel, sans le mettre à jour ni changer son format.
    # Sans uv.lock (projet neuf), le premier sync le crée.
    # (pas de tableau bash : la syntaxe de sa longueur ouvre un commentaire Jinja)
    frozen=""
    [ -f uv.lock ] && frozen="--frozen"
    # --active : cible le venv hors du dossier projet
    VIRTUAL_ENV="$VENV_HOME" uv sync ${frozen:+"$frozen"} --active --all-extras \
        || fail "Installation des dépendances impossible"
    echo "✅ Environnement Python prêt ($VENV_HOME)"
    # --check n'écrit rien ; une différence de format seule ne le fait pas échouer
    if [ -n "$frozen" ] && ! VIRTUAL_ENV="$VENV_HOME" uv lock --check >/dev/null 2>&1; then
        echo "⚠️  uv.lock n'est plus à jour avec pyproject.toml : le venv suit uv.lock."
        echo "   Lancez « uv lock », puis « uv sync --active --all-extras », et commitez uv.lock."
    fi
fi
