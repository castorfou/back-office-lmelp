#!/usr/bin/env bash
# =============================================================================
# Migration de l'historique Claude Code vers la config partagée (issue #73)
# Lancé sur l'HÔTE par initializeCommand, avant le montage : dans le conteneur,
# l'ancien ~/.claude du projet est masqué par ~/.config/claude-devcontainers.
# Copie, une fois par projet et sans rien écraser, les conversations (/resume),
# la mémoire auto, les checkpoints (/rewind) et l'historique des prompts.
# La connexion n'est pas copiée : on se reconnecte une fois pour tous les projets.
# N'échoue jamais : l'ouverture du conteneur ne doit pas en dépendre.
# =============================================================================
set -uo pipefail

WORKSPACE_FOLDER_BASENAME="${DEVCONTAINER_WORKSPACE_FOLDER_BASENAME:-$(basename "$PWD")}"
OLD="$HOME/.devcontainer/homes/$WORKSPACE_FOLDER_BASENAME-${DEVCONTAINER_ID:-}/.claude"
SHARED="$HOME/.config/claude-devcontainers"
MARKER="$OLD/.migrated-to-claude-devcontainers"

[[ -n "${DEVCONTAINER_ID:-}" && -d "$OLD" && ! -e "$MARKER" ]] || exit 0

# Copie les fichiers de $1 absents de $2. Pas de `cp -n` : selon la version de
# coreutils (9.2 à 9.4), il échoue dès qu'il saute un fichier existant.
copy_missing() {
    local src="$1" dest="$2" file
    (cd "$src" && find . -type f) | while IFS= read -r file; do
        [[ -e "$dest/$file" ]] && continue
        mkdir -p "$(dirname "$dest/$file")" && cp -p "$src/$file" "$dest/$file" || exit 1
    done
}

migrate() {
    local dir
    for dir in projects file-history; do
        [[ -d "$OLD/$dir" ]] || continue
        copy_missing "$OLD/$dir" "$SHARED/$dir" || return 1
    done
    if [[ -f "$OLD/history.jsonl" ]]; then
        cat "$OLD/history.jsonl" >> "$SHARED/history.jsonl" || return 1
    fi
}

if migrate 2>/dev/null; then
    touch "$MARKER"
    echo "✅ Historique Claude Code de $WORKSPACE_FOLDER_BASENAME copié dans $SHARED"
else
    echo "⚠️  Migration de l'historique Claude Code incomplète, nouvel essai à la prochaine ouverture"
fi
exit 0
