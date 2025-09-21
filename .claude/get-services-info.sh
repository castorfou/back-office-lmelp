#!/bin/bash

# Utilitaire Claude Code pour auto-découverte complète des services
# Usage: ./.claude/get-services-info.sh [--json|--summary|--urls]

set -e

PROJECT_ROOT="/workspaces/back-office-lmelp"
UNIFIED_FILE="$PROJECT_ROOT/.dev-ports.json"

# Parse command line arguments
OPTION="${1:-summary}"

# Check if services are running
if [[ ! -f "$UNIFIED_FILE" ]]; then
    echo "No services discovery file found (.dev-ports.json)"
    echo "Run ./scripts/start-dev.sh to start services"
    exit 1
fi

case "$OPTION" in
    --json)
        # Output raw JSON for programmatic use
        cat "$UNIFIED_FILE"
        ;;
    --urls)
        # Output just the URLs for quick access
        python3 -c "
import json
try:
    with open('$UNIFIED_FILE') as f:
        data = json.load(f)

    backend = data.get('backend', {})
    frontend = data.get('frontend', {})

    if backend.get('url'):
        print(f\"Backend: {backend['url']}\")
    if frontend.get('url'):
        print(f\"Frontend: {frontend['url']}\")

    # Useful endpoints
    if backend.get('url'):
        base = backend['url']
        print(f\"API Docs: {base}/docs\")
        print(f\"OpenAPI: {base}/openapi.json\")
        print(f\"Health: {base}/\")
except:
    print('Error reading services info')
"
        ;;
    --summary|*)
        # Human-readable summary
        echo "=== Development Services Status ==="
        echo

        # Try to get backend info
        if "$PROJECT_ROOT/.claude/get-backend-info.sh" >/dev/null 2>&1; then
            "$PROJECT_ROOT/.claude/get-backend-info.sh"
        else
            echo "Backend: Not running"
        fi

        echo

        # Try to get frontend info
        if "$PROJECT_ROOT/.claude/get-frontend-info.sh" >/dev/null 2>&1; then
            "$PROJECT_ROOT/.claude/get-frontend-info.sh"
        else
            echo "Frontend: Not running"
        fi

        echo
        echo "=== Quick Commands for Claude Code ==="
        if "$PROJECT_ROOT/.claude/get-backend-info.sh" --url >/dev/null 2>&1; then
            BACKEND_URL=$("$PROJECT_ROOT/.claude/get-backend-info.sh" --url)
            echo "curl \"$BACKEND_URL/\"                    # Health check"
            echo "curl \"$BACKEND_URL/docs\"                # API documentation"
            echo "curl \"$BACKEND_URL/openapi.json\"        # OpenAPI spec"
        fi
        ;;
esac
