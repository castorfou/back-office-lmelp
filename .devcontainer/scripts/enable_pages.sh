#!/usr/bin/env bash
# =============================================================================
# Activation de GitHub Pages au terminal zsh, après gh_login.sh (issue #116)
# docs.yml publie avec GitHub Actions mais ne peut pas activer Pages : le
# GITHUB_TOKEN n'a pas les droits admin. Ce script l'active avec le compte gh,
# seulement sur un dépôt public, sans jamais toucher à « Deploy from a branch ».
# Une fois le dépôt réglé, un marqueur dans .git/ évite tout appel réseau.
# Toujours silencieux sur stderr, toujours en sortie 0 : il ne casse pas le shell.
# =============================================================================

GUIDE="docs/cheatsheets/mkdocs.md, section « Activer GitHub Pages »"

[ -n "$WORKSPACE_FOLDER" ] && cd "$WORKSPACE_FOLDER" 2> /dev/null

command -v gh > /dev/null 2>&1 || exit 0
command -v git > /dev/null 2>&1 || exit 0

# Hors réseau : authentification, dépôt GitHub, marqueur
gh auth token > /dev/null 2>&1 || exit 0
url=$(git remote get-url origin 2> /dev/null) || exit 0
repo=$(printf '%s\n' "$url" | sed -nE 's#^(https://|ssh://git@|git@)github\.com[:/]([^/]+/[^/]+)$#\2#p')
repo=${repo%.git}
[ -n "$repo" ] || exit 0

marker=${PAGES_MARKER:-$(git rev-parse --git-path pyfoundry-pages 2> /dev/null)}
[ -n "$marker" ] || exit 0
[ "$(cat "$marker" 2> /dev/null)" = "$repo" ] && exit 0

settled() {
    echo "$repo" > "$marker" 2> /dev/null
    exit 0
}

# Dépôt pas encore créé, réseau coupé : nouvel essai au prochain terminal
info=$(timeout 5 gh api "repos/$repo" --jq '.visibility, .permissions.admin, .has_pages' 2> /dev/null) \
    || exit 0
{
    read -r visibility
    read -r admin
    read -r has_pages
} <<< "$info"

if [ "$visibility" != "public" ]; then
    echo "ℹ️  GitHub Pages non activé automatiquement (dépôt $visibility) : voir $GUIDE"
    settled
fi
if [ "$admin" != "true" ]; then
    echo "ℹ️  GitHub Pages non activé : droits admin requis sur $repo (voir $GUIDE)"
    settled
fi

if [ "$has_pages" = "true" ]; then
    build_type=$(timeout 5 gh api "repos/$repo/pages" --jq .build_type 2> /dev/null) || exit 0
    if [ "$build_type" != "workflow" ]; then
        echo "ℹ️  GitHub Pages utilise « Deploy from a branch » : pour passer à GitHub Actions, voir $GUIDE"
    fi
    settled
fi

if timeout 5 gh api -X POST "repos/$repo/pages" -f build_type=workflow > /dev/null 2>&1; then
    echo "✅ GitHub Pages activé sur $repo (source : GitHub Actions)"
    settled
fi
echo "⚠️  Activation de GitHub Pages impossible : gh api -X POST \"repos/{owner}/{repo}/pages\" -f build_type=workflow"
exit 0
