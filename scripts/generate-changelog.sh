#!/bin/bash
# Génère build_info.json et changelog.json pour le Docker build (Issue #205)
# Exécuté dans le pipeline CI/CD avant la construction des images Docker.

set -e

COMMIT_HASH=$(git rev-parse HEAD)
COMMIT_SHORT=$(git rev-parse --short HEAD)
COMMIT_DATE=$(git log -1 --format=%ci)
BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

echo "🏷️  Generating build info: $COMMIT_SHORT ($COMMIT_DATE)"

# build_info.json
cat > build_info.json << EOF
{
  "commit_hash": "$COMMIT_HASH",
  "commit_short": "$COMMIT_SHORT",
  "commit_date": "$COMMIT_DATE",
  "build_date": "$BUILD_DATE"
}
EOF

echo "📋 Generating changelog (commits referencing issues/PRs)..."

# changelog.json - commits first-parent qui référencent une issue/PR
# Format git: hash|date|message, filtré par #[0-9]+, converti en JSON
git log --first-parent --format='%h|%ci|%s' \
  | grep -E '#[0-9]+' \
  | python3 -c "
import sys, json
entries = []
for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    parts = line.split('|', 2)
    if len(parts) == 3:
        entries.append({
            'hash': parts[0],
            'date': parts[1],
            'message': parts[2]
        })
json.dump(entries, sys.stdout, ensure_ascii=False, indent=2)
" > changelog.json

ENTRY_COUNT=$(python3 -c "import json; print(len(json.load(open('changelog.json'))))")
echo "✅ Generated: build_info.json + changelog.json ($ENTRY_COUNT entries)"
