#!/bin/bash

# Script de lancement unifié pour backend et frontend
# Usage: ./scripts/start-dev.sh

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Project root directory
PROJECT_ROOT="/workspaces/back-office-lmelp"

# Log function with colors
log() {
    echo -e "${GREEN}[$(date +'%H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%H:%M:%S')] ERROR: $1${NC}"
}

# Function to capture port from process output
capture_port_from_output() {
    local service_name="$1"
    local pid="$2"
    local port_var="${service_name}_PORT"
    local host_var="${service_name}_HOST"

    # For backend, wait for unified port discovery file to be created (with retry logic)
    if [[ "$service_name" == "BACKEND" ]]; then
        local max_attempts=15  # 15 seconds total
        local attempt=0

        while [[ $attempt -lt $max_attempts ]]; do
            if [[ -f "$PROJECT_ROOT/.dev-ports.json" ]]; then
                local backend_port=$(python3 -c "import json; data=json.load(open('$PROJECT_ROOT/.dev-ports.json')); print(data.get('backend', {}).get('port', ''))" 2>/dev/null)
                local backend_host=$(python3 -c "import json; data=json.load(open('$PROJECT_ROOT/.dev-ports.json')); print(data.get('backend', {}).get('host', ''))" 2>/dev/null)

                if [[ -n "$backend_port" && -n "$backend_host" ]]; then
                    eval "${port_var}=$backend_port"
                    eval "${host_var}=$backend_host"
                    log "Detected $service_name on $backend_host:$backend_port (after ${attempt}s)"
                    return 0
                fi
            fi

            sleep 1
            attempt=$((attempt + 1))
        done

        warn "Backend port discovery file not found after ${max_attempts}s"
        warn "Backend may still be starting - check logs"
        # Don't return error to avoid stopping script with set -e
        return 0
    fi

    # For frontend, try to detect from common ports or process
    if [[ "$service_name" == "FRONTEND" ]]; then
        # Vite typically uses port 5173 by default
        eval "${port_var}=5173"
        eval "${host_var}=0.0.0.0"
        log "Using default $service_name port 5173"
        return 0
    fi

    return 1
}

# Function to write unified port discovery file
write_unified_port_discovery() {
    local backend_port="$1"
    local backend_host="$2"
    local backend_pid="$3"
    local frontend_port="$4"
    local frontend_host="$5"
    local frontend_pid="$6"

    # Use Python to create unified port discovery file
    python3 << EOF
import json
import time
from pathlib import Path

port_data = {}

if "$backend_port" and "$backend_host":
    port_data["backend"] = {
        "port": int("$backend_port"),
        "host": "$backend_host",
        "pid": int("$backend_pid"),
        "started_at": time.time(),
        "url": "http://$backend_host:$backend_port"
    }

if "$frontend_port" and "$frontend_host":
    port_data["frontend"] = {
        "port": int("$frontend_port"),
        "host": "$frontend_host",
        "pid": int("$frontend_pid"),
        "started_at": time.time(),
        "url": "http://$frontend_host:$frontend_port"
    }

# Write unified discovery file
port_file = Path("$PROJECT_ROOT") / ".dev-ports.json"
with open(port_file, 'w') as f:
    json.dump(port_data, f, indent=2)

print(f"📡 Unified port discovery file created: {port_file}")
EOF
}

# Function to kill process group (including children)
kill_process_group() {
    local pid=$1
    local name=$2

    # Get process group ID
    local pgid=$(ps -o pgid= -p $pid 2>/dev/null | tr -d ' ')

    if [[ -n $pgid ]]; then
        # Kill entire process group (negative PGID)
        kill -TERM -$pgid 2>/dev/null || true
        log "Signal TERM envoyé au groupe de processus $name (PGID: $pgid)"
    else
        # Fallback to killing just the process
        kill -TERM $pid 2>/dev/null || true
    fi
}

# Function to wait for process to exit with timeout
wait_for_process() {
    local pid=$1
    local name=$2
    local timeout=5
    local elapsed=0

    while kill -0 $pid 2>/dev/null && [[ $elapsed -lt $timeout ]]; do
        sleep 0.5
        elapsed=$((elapsed + 1))
    done

    # Force kill if still running (kill entire process group)
    if kill -0 $pid 2>/dev/null; then
        warn "$name (PID: $pid) ne répond pas - force kill du groupe"
        local pgid=$(ps -o pgid= -p $pid 2>/dev/null | tr -d ' ')
        if [[ -n $pgid ]]; then
            kill -9 -$pgid 2>/dev/null || true
        else
            kill -9 $pid 2>/dev/null || true
        fi
        sleep 0.5
    fi
}

# Function to clean up processes on exit
cleanup() {
    log "Arrêt des processus..."

    if [[ -n $BACKEND_PID ]]; then
        log "Arrêt du backend (PID: $BACKEND_PID)"
        kill_process_group $BACKEND_PID "Backend"
        wait_for_process $BACKEND_PID "Backend"
    fi

    if [[ -n $FRONTEND_PID ]]; then
        log "Arrêt du frontend (PID: $FRONTEND_PID)"
        kill_process_group $FRONTEND_PID "Frontend"
        wait_for_process $FRONTEND_PID "Frontend"
    fi

    # Clean up unified discovery file
    if [[ -f "$PROJECT_ROOT/.dev-ports.json" ]]; then
        rm -f "$PROJECT_ROOT/.dev-ports.json"
        log "🧹 Unified port discovery file cleaned up"
    fi

    log "✅ Processus arrêtés proprement"
    exit 0
}

# Trap signals for clean shutdown
trap cleanup SIGINT SIGTERM

# Check if we're in the right directory
if [[ ! -f "$PROJECT_ROOT/pyproject.toml" ]] || [[ ! -d "$PROJECT_ROOT/frontend" ]]; then
    error "Ce script doit être exécuté depuis la racine du projet back-office-lmelp"
    exit 1
fi

# Check if frontend dependencies are installed
if [[ ! -d "$PROJECT_ROOT/frontend/node_modules" ]]; then
    warn "Les dépendances frontend ne sont pas installées"
    log "Installation des dépendances frontend..."
    cd "$PROJECT_ROOT/frontend" && npm ci
fi

# Clean up old port discovery file to avoid stale data
if [[ -f "$PROJECT_ROOT/.dev-ports.json" ]]; then
    log "🧹 Nettoyage du fichier de découverte des ports précédent..."
    rm -f "$PROJECT_ROOT/.dev-ports.json"
fi

log "Démarrage du backend et du frontend..."

# If BABELIO_CACHE_LOG is set, inform the user that verbose cache logging is enabled
if [[ -n "$BABELIO_CACHE_LOG" ]]; then
    log "Note: BABELIO_CACHE_LOG is set -> Babelio disk cache logging enabled (INFO)."
    warn "Les résultats stockés en cache peuvent varier d'une exécution à l'autre; utilisez avec prudence."
fi

# Start backend in background
log "Lancement du backend FastAPI..."
cd "$PROJECT_ROOT"
export BABELIO_DEBUG_LOG=1
PYTHONPATH="$PROJECT_ROOT/src" python -m back_office_lmelp.app &
BACKEND_PID=$!
log "Backend démarré (PID: $BACKEND_PID)"

# Capture backend port information
capture_port_from_output "BACKEND" "$BACKEND_PID"

# Start frontend in background
log "Lancement du frontend Vue.js..."
cd "$PROJECT_ROOT/frontend" && npm run dev &
FRONTEND_PID=$!
log "Frontend démarré (PID: $FRONTEND_PID)"

# Capture frontend port information
capture_port_from_output "FRONTEND" "$FRONTEND_PID"

# Note: The backend writes .dev-ports.json automatically, so we don't overwrite it here
# We just log the detected information

log "Backend et frontend démarrés avec succès!"
log "📍 Backend: ${BACKEND_HOST:-unknown}:${BACKEND_PORT:-unknown}"
log "📍 Frontend: ${FRONTEND_HOST:-unknown}:${FRONTEND_PORT:-unknown}"
log "📡 Port discovery: .dev-ports.json created for Claude Code auto-discovery"
log "Appuyez sur Ctrl+C pour arrêter les deux services"

# Wait for processes to complete or be interrupted
wait
