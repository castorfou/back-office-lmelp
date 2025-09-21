#!/bin/bash

# Utilitaire Claude Code pour auto-découverte du frontend
# Usage: ./.claude/get-frontend-info.sh [--url|--port|--host|--status|--all]

set -e

PROJECT_ROOT="/workspaces/back-office-lmelp"
UNIFIED_FILE="$PROJECT_ROOT/.dev-ports.json"

# Function to check if a service is active
check_service_status() {
    local pid="$1"
    if [[ -z "$pid" ]]; then
        echo "inactive"
        return
    fi

    if kill -0 "$pid" 2>/dev/null; then
        echo "active"
    else
        echo "inactive"
    fi
}

# Function to get frontend info from unified file
get_frontend_info() {
    if [[ ! -f "$UNIFIED_FILE" ]]; then
        echo ""
        return
    fi

    python3 -c "
import json
import time
try:
    with open('$UNIFIED_FILE') as f:
        data = json.load(f)
    frontend = data.get('frontend', {})
    if frontend:
        # Check if stale (older than 24 hours)
        age = time.time() - frontend.get('started_at', 0)
        if age < 24 * 60 * 60:
            print(json.dumps(frontend))
        else:
            print('')
    else:
        print('')
except:
    print('')
" 2>/dev/null
}

# Parse command line arguments
OPTION="${1:-all}"

# Get frontend information
FRONTEND_JSON=$(get_frontend_info)

if [[ -z "$FRONTEND_JSON" ]]; then
    echo "ERROR: No active frontend service found" >&2
    echo "HINT: Run ./scripts/start-dev.sh to start services" >&2
    exit 1
fi

# Parse JSON and extract requested information
case "$OPTION" in
    --url)
        echo "$FRONTEND_JSON" | python3 -c "import json, sys; data=json.load(sys.stdin); print(data.get('url', ''))"
        ;;
    --port)
        echo "$FRONTEND_JSON" | python3 -c "import json, sys; data=json.load(sys.stdin); print(data.get('port', ''))"
        ;;
    --host)
        echo "$FRONTEND_JSON" | python3 -c "import json, sys; data=json.load(sys.stdin); print(data.get('host', ''))"
        ;;
    --status)
        PID=$(echo "$FRONTEND_JSON" | python3 -c "import json, sys; data=json.load(sys.stdin); print(data.get('pid', ''))")
        check_service_status "$PID"
        ;;
    --pid)
        echo "$FRONTEND_JSON" | python3 -c "import json, sys; data=json.load(sys.stdin); print(data.get('pid', ''))"
        ;;
    --age)
        echo "$FRONTEND_JSON" | python3 -c "
import json, sys, time
data=json.load(sys.stdin)
started = data.get('started_at', 0)
age = int(time.time() - started)
print(f'{age}s ago')
"
        ;;
    --all|*)
        echo "Frontend Service Information:"
        echo "URL: $(echo "$FRONTEND_JSON" | python3 -c "import json, sys; data=json.load(sys.stdin); print(data.get('url', 'unknown'))")"
        echo "Host: $(echo "$FRONTEND_JSON" | python3 -c "import json, sys; data=json.load(sys.stdin); print(data.get('host', 'unknown'))")"
        echo "Port: $(echo "$FRONTEND_JSON" | python3 -c "import json, sys; data=json.load(sys.stdin); print(data.get('port', 'unknown'))")"
        PID=$(echo "$FRONTEND_JSON" | python3 -c "import json, sys; data=json.load(sys.stdin); print(data.get('pid', ''))")
        echo "PID: ${PID:-unknown}"
        echo "Status: $(check_service_status "$PID")"
        echo "Started: $(echo "$FRONTEND_JSON" | python3 -c "
import json, sys, time
data=json.load(sys.stdin)
started = data.get('started_at', 0)
age = int(time.time() - started)
print(f'{age}s ago')
")"
        ;;
esac
