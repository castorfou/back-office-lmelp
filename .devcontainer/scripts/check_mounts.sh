#!/usr/bin/env bash
# =============================================================================
# Vérification des points de montage du devcontainer
# Lancé sur l'HÔTE par initializeCommand, avant que Docker ne monte les sources.
# Usage manuel, depuis la racine du projet : bash .devcontainer/scripts/check_mounts.sh --host
# =============================================================================
set -uo pipefail

# --host est accepté pour expliciter l'usage : le script ne s'exécute que sur l'hôte
if [[ "${1:-}" != "" && "${1:-}" != "--host" ]]; then
    echo "Usage: $0 [--host]" >&2
    exit 2
fi

# Variables transmises par initializeCommand ; à défaut (lancement manuel), on les déduit
WORKSPACE_FOLDER_BASENAME="${DEVCONTAINER_WORKSPACE_FOLDER_BASENAME:-$(basename "$PWD")}"
HOMES_DIR="$HOME/.devcontainer/homes"

# Propriétaire attendu des points de montage (surchargé par les tests)
OWNER_UID="${CHECK_MOUNTS_UID:-$(id -u)}"

ERRORS=0
WARNINGS=0

log_section() {
    echo ""
    echo "=== $1 ==="
    echo ""
}

log_ok() {
    echo "  [OK]   $1"
}

log_fail() {
    echo "  [FAIL] $1"
    ERRORS=$((ERRORS + 1))
}

log_warn() {
    echo "  [WARN] $1"
    WARNINGS=$((WARNINGS + 1))
}

# Propriétaire d'un chemin : uid et nom (stat GNU, sinon BSD/macOS)
owner_of() {
    stat -c '%u %U' "$1" 2>/dev/null || stat -f '%u %Su' "$1"
}

# Extrait les montages actifs de devcontainer.json : "source<TAB>target" par ligne
parse_mounts() {
    python3 - "$1" <<'PY'
import json, re, sys

with open(sys.argv[1]) as f:
    content = f.read()

# JSONC : les chaînes sont reconnues d'abord et gardées telles quelles, pour que
# // ou /* dans une chaîne (http://, **/*.pyc) ne soient pas pris pour des commentaires
STRING = r'"(?:\\.|[^"\\])*"'
content = re.sub(STRING + r'|//[^\n]*|/\*.*?\*/',
                 lambda m: m.group() if m.group().startswith('"') else '',
                 content, flags=re.DOTALL)
# Virgules finales avant ] ou }
content = re.sub('(' + STRING + r')|,(\s*[\]}])',
                 lambda m: m.group(1) or m.group(2), content)

try:
    config = json.loads(content)
except json.JSONDecodeError as error:
    print(f'{sys.argv[1]}: {error}', file=sys.stderr)
    sys.exit(1)

for mount in config.get('mounts', []):
    parts = dict(part.split('=', 1) for part in mount.split(',') if '=' in part)
    source, target = parts.get('source', ''), parts.get('target', '')
    if source and target:
        print(f'{source}\t{target}')
PY
}

# Résout les variables Dev Containers d'un chemin source
resolve_path() {
    local path="$1"
    local -a candidates=()
    local entry

    path="${path//\$\{localEnv:HOME\}/$HOME}"
    path="${path//\$\{localWorkspaceFolderBasename\}/$WORKSPACE_FOLDER_BASENAME}"

    if [[ "$path" == *'${devcontainerId}'* && -n "${DEVCONTAINER_ID:-}" ]]; then
        path="${path//\$\{devcontainerId\}/$DEVCONTAINER_ID}"
    elif [[ "$path" == *'${devcontainerId}'* ]]; then
        # Lancement manuel : on retient le HOME persistant du projet s'il est unique
        shopt -s nullglob
        for entry in "$HOMES_DIR/$WORKSPACE_FOLDER_BASENAME-"*; do
            [[ -d "$entry" ]] && candidates+=("$entry")
        done
        shopt -u nullglob
        if [[ "${#candidates[@]}" -eq 1 ]]; then
            path="${path//\$\{devcontainerId\}/${candidates[0]#"$HOMES_DIR/$WORKSPACE_FOLDER_BASENAME-"}}"
        fi
    fi
    printf '%s\n' "$path"
}

# Affiche la commande de correction de chaque permission SSH refusée par le client ssh :
# - dossier ou config modifiables par le groupe/les autres
# - clé privée (ou autre fichier) accessible au groupe/aux autres
# Les clés publiques et known_hosts ne sont pas vérifiés par ssh : on les ignore.
ssh_permission_fixes() {
    local dir="$1"
    local file mode

    mode=$(stat -c '%a' "$dir") || return 0
    (( 8#$mode & 8#022 )) && echo "chmod 700 \"$dir\""

    for file in "$dir"/*; do
        [[ -f "$file" ]] || continue
        case "$(basename "$file")" in
            *.pub|known_hosts*) continue ;;
        esac
        mode=$(stat -c '%a' "$file") || continue
        if [[ "$(basename "$file")" == config ]]; then
            (( 8#$mode & 8#022 )) && echo "chmod 600 \"$file\""
        else
            (( 8#$mode & 8#077 )) && echo "chmod 600 \"$file\""
        fi
    done
    return 0
}

echo ""
echo "============================================================"
echo " Vérification des points de montage"
echo "============================================================"

DC_JSON=".devcontainer/devcontainer.json"
if [[ ! -f "$DC_JSON" ]]; then
    echo ""
    log_fail "devcontainer.json not found in .devcontainer/"
    echo "        Lancez ce script depuis la racine du projet."
    exit 1
fi

if ! MOUNTS=$(parse_mounts "$DC_JSON"); then
    echo ""
    log_fail "$DC_JSON: impossible de lire la section mounts"
    exit 1
fi

log_section "Montages détectés"

# Cibles et sources résolues, dans l'ordre de devcontainer.json (bash 3 : pas de tableau associatif)
TARGETS=()
RESOLVED_SOURCES=()

while IFS=$'\t' read -r source target; do
    [[ -n "$source" ]] || continue
    resolved=$(resolve_path "$source")
    TARGETS+=("$target")
    RESOLVED_SOURCES+=("$resolved")
    echo "  Mount: $resolved -> $target"

    if [[ "$resolved" == *'${devcontainerId}'* ]]; then
        log_fail "$target: cannot resolve \${devcontainerId} for this host check"
        echo "        Le HOME persistant n'a pas encore été créé, ou plusieurs candidats existent."
        echo "        Attendu : un seul dossier correspondant à $HOMES_DIR/$WORKSPACE_FOLDER_BASENAME-*"
        continue
    fi

    if [[ ! -e "$resolved" && "$resolved" == *.sock ]]; then
        log_fail "$target: source does not exist ($resolved)"
        echo "        Ce socket est créé par le service Docker : vérifiez que Docker tourne sur l'hôte."
        continue
    fi

    if [[ ! -e "$resolved" ]]; then
        log_fail "$target: source does not exist ($resolved)"
        echo "        Corrigez source= dans $DC_JSON si le chemin est incorrect."
        echo "        Sinon, créez le chemin sur l'hôte avec le type attendu :"
        echo "          Répertoire : mkdir -p \"$resolved\""
        echo "          Fichier    : touch \"$resolved\""
        continue
    fi

    if [[ "$target" == */.ssh ]]; then
        fixes=$(ssh_permission_fixes "$resolved")
        if [[ -n "$fixes" ]]; then
            log_fail "$target: SSH permissions too open"
            echo "        Corrigez sur l'hôte :"
            echo "$fixes" | sed 's/^/          /'
            continue
        fi
    fi

    log_ok "$target"
done <<< "$MOUNTS"

# Un montage imbriqué dans un autre (ex. ~/.ssh dans le HOME) a son point de montage
# dans la source du parent. S'il manque, Docker le crée en root : supprimer cette source
# demande alors sudo. Le dossier reste vide sur l'hôte, donc rmdir suffit à le recréer.
log_section "Points de montage imbriqués"

# Points de montage d'un autre propriétaire, regroupés par source parente (index du montage)
FOREIGN=()
FOREIGN_OWNER=()

for i in "${!TARGETS[@]}"; do
    target="${TARGETS[$i]}"
    parent=""
    parent_index=""
    for j in "${!TARGETS[@]}"; do
        candidate="${TARGETS[$j]}"
        if [[ "$target" == "${candidate%/}/"* && ${#candidate} -gt ${#parent} ]]; then
            parent="$candidate"
            parent_index="$j"
        fi
    done
    [[ -n "$parent" ]] || continue

    relative="${target#"${parent%/}/"}"
    mountpoint="${RESOLVED_SOURCES[$parent_index]}/$relative"
    [[ "$mountpoint" != *'${'* && -d "$mountpoint" ]] || continue

    read -r uid name < <(owner_of "$mountpoint")
    if [[ "$uid" != "$OWNER_UID" ]]; then
        FOREIGN[$parent_index]="${FOREIGN[$parent_index]:-} $relative"
        FOREIGN_OWNER[$parent_index]="$name"
    else
        log_ok "$target"
    fi
done

for j in "${!FOREIGN[@]}"; do
    source_dir="${RESOLVED_SOURCES[$j]}"
    log_warn "Dossiers appartenant à ${FOREIGN_OWNER[$j]} dans $source_dir :"
    echo "          ${FOREIGN[$j]# }"
    echo "        Docker les a créés vides pour y monter des dossiers de l'hôte. Le conteneur"
    echo "        fonctionne, mais supprimer $source_dir demandera sudo."
    echo "        Pour les rendre à $(id -un) (sudo inutile) :"
    echo "          1. Fermez VS Code."
    echo "          2. Sur l'hôte, arrêtez le conteneur du projet :"
    echo "               docker stop \$(docker ps -q --filter \"label=devcontainer.local_folder=$PWD\")"
    echo "          3. Recréez les dossiers :"
    echo "               cd \"$source_dir\""
    echo "               rmdir${FOREIGN[$j]} && mkdir${FOREIGN[$j]}"
    echo "          4. Rouvrez le projet dans VS Code."
done

log_section "Résumé"

if [[ "$ERRORS" -gt 0 ]]; then
    echo "  $ERRORS erreur(s) : corrigez-les avant de démarrer le devcontainer."
    exit 1
fi

if [[ "$WARNINGS" -gt 0 ]]; then
    echo "  Tous les montages sont valides, $WARNINGS avertissement(s)."
    exit 0
fi

echo "  Tous les montages sont valides."
exit 0
