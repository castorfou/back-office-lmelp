#!/usr/bin/env bash
# Update MkDocs repo_url based on current Git remote origin
set -euo pipefail

MKDOCS_FILE="mkdocs.yml"

# If mkdocs file doesn't exist, nothing to do
if [ ! -f "$MKDOCS_FILE" ]; then
  exit 0
fi

# Get remote URL (origin)
remote_url="$(git remote get-url origin 2>/dev/null || true)"
if [ -z "$remote_url" ]; then
  # No origin configured
  exit 0
fi

# Normalize SSH/HTTPS and strip .git suffix
normalized_url="$remote_url"
# SSH form: git@gitlab.example.com:group/project.git -> https://gitlab.example.com/group/project
normalized_url="$(printf '%s
' "$normalized_url" | sed -E 's#^git@(.*):(.*)\.git$#https://\1/\2#; s#\.git$##')"

# Basic sanity check
case "$normalized_url" in
  http://*|https://*) ;;
  *)
    # Not an HTTP(S) URL, do nothing
    exit 0
    ;;
esac

# We want repo_url to appear right after site_url at the top of the file.
# Strategy:
# 1) Remove any existing repo_url lines.
# 2) Insert new repo_url line immediately after the first site_url line.

# Create a temp file for safe editing
tmp_file="${MKDOCS_FILE}.tmp.$$"

# First, remove any existing repo_url lines
grep -vE '^repo_url:' "$MKDOCS_FILE" > "$tmp_file"

# Now insert repo_url after the first site_url line
awk -v url="$normalized_url" '
  /^site_url:/ && !inserted {
    print $0
    print "repo_url: " url
    inserted = 1
    next
  }
  { print $0 }
' "$tmp_file" > "$MKDOCS_FILE"

rm -f "$tmp_file"
