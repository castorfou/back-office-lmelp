#!/bin/bash

# Utilitaire Claude Code pour auto-découverte des services
# Usage: ./.claude/get-backend-info.sh [--url|--port|--host|--status|--all]

set -e

PROJECT_ROOT="/workspaces/back-office-lmelp"
UNIFIED_FILE="$PROJECT_ROOT/.dev-ports.json"
LEGACY_FILE="$PROJECT_ROOT/.backend-port.json"

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

# Function to get backend info from files
get_backend_info() {
    local backend_info=""

    # Try unified file first
    if [[ -f "$UNIFIED_FILE" ]]; then
        backend_info=$(python3 -c "
import json
import time
try:
    with open('$UNIFIED_FILE') as f:
        data = json.load(f)
    backend = data.get('backend', {})
    if backend:
        # Check if stale (older than 24 hours)
        age = time.time() - backend.get('started_at', 0)
        if age < 24 * 60 * 60:
            print(json.dumps(backend))
        else:
            print('')
except:
    print('')
" 2>/dev/null)
    fi

    # Fall back to legacy file if unified not available or stale
    if [[ -z "$backend_info" && -f "$LEGACY_FILE" ]]; then
        backend_info=$(python3 -c "
import json
import time
try:
    with open('$LEGACY_FILE') as f:
        data = json.load(f)
    # Check if stale
    age = time.time() - data.get('timestamp', 0)
    if age < 24 * 60 * 60:
        # Convert legacy format to unified format
        unified = {
            'port': data.get('port'),
            'host': data.get('host'),
            'url': data.get('url'),
            'started_at': data.get('timestamp'),
            'pid': None
        }
        print(json.dumps(unified))
    else:
        print('')
except:
    print('')
" 2>/dev/null)
    fi

    echo "$backend_info"
}

# Parse command line arguments
OPTION="${1:-all}"

# Get backend information
BACKEND_JSON=$(get_backend_info)

if [[ -z "$BACKEND_JSON" ]]; then
    echo "ERROR: No active backend service found" >&2
    echo "HINT: Run ./scripts/start-dev.sh to start services" >&2
    exit 1
fi

# Parse JSON and extract requested information
case "$OPTION" in
    --url)
        echo "$BACKEND_JSON" | python3 -c "import json, sys; data=json.load(sys.stdin); print(data.get('url', ''))"
        ;;
    --port)
        echo "$BACKEND_JSON" | python3 -c "import json, sys; data=json.load(sys.stdin); print(data.get('port', ''))"
        ;;
    --host)
        echo "$BACKEND_JSON" | python3 -c "import json, sys; data=json.load(sys.stdin); print(data.get('host', ''))"
        ;;
    --status)
        PID=$(echo "$BACKEND_JSON" | python3 -c "import json, sys; data=json.load(sys.stdin); print(data.get('pid', ''))")
        check_service_status "$PID"
        ;;
    --pid)
        echo "$BACKEND_JSON" | python3 -c "import json, sys; data=json.load(sys.stdin); print(data.get('pid', ''))"
        ;;
    --age)
        echo "$BACKEND_JSON" | python3 -c "
import json, sys, time
data=json.load(sys.stdin)
started = data.get('started_at', 0)
age = int(time.time() - started)
print(f'{age}s ago')
"
        ;;
    --all|*)
        echo "Backend Service Information:"
        echo "URL: $(echo "$BACKEND_JSON" | python3 -c "import json, sys; data=json.load(sys.stdin); print(data.get('url', 'unknown'))")"
        echo "Host: $(echo "$BACKEND_JSON" | python3 -c "import json, sys; data=json.load(sys.stdin); print(data.get('host', 'unknown'))")"
        echo "Port: $(echo "$BACKEND_JSON" | python3 -c "import json, sys; data=json.load(sys.stdin); print(data.get('port', 'unknown'))")"
        PID=$(echo "$BACKEND_JSON" | python3 -c "import json, sys; data=json.load(sys.stdin); print(data.get('pid', ''))")
        echo "PID: ${PID:-unknown}"
        echo "Status: $(check_service_status "$PID")"
        echo "Started: $(echo "$BACKEND_JSON" | python3 -c "
import json, sys, time
data=json.load(sys.stdin)
started = data.get('started_at', 0)
age = int(time.time() - started)
print(f'{age}s ago')
")"
        ;;
esac
