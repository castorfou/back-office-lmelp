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

    # Give the service time to start and output port information
    sleep 3

    # Try to extract port from process output/logs
    # For backend, check if unified port discovery file was created
    if [[ "$service_name" == "BACKEND" ]] && [[ -f "$PROJECT_ROOT/.dev-ports.json" ]]; then
        local backend_port=$(python3 -c "import json; data=json.load(open('$PROJECT_ROOT/.dev-ports.json')); print(data.get('backend', {}).get('port', ''))")
        local backend_host=$(python3 -c "import json; data=json.load(open('$PROJECT_ROOT/.dev-ports.json')); print(data.get('backend', {}).get('host', ''))")
        if [[ -n "$backend_port" && -n "$backend_host" ]]; then
            eval "${port_var}=$backend_port"
            eval "${host_var}=$backend_host"
            log "Detected $service_name on $backend_host:$backend_port"
            return 0
        fi
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

# Function to clean up processes on exit
cleanup() {
    log "Arrêt des processus..."

    if [[ -n $BACKEND_PID ]]; then
        log "Arrêt du backend (PID: $BACKEND_PID)"
        kill -TERM $BACKEND_PID 2>/dev/null || true
        wait $BACKEND_PID 2>/dev/null || true
    fi

    if [[ -n $FRONTEND_PID ]]; then
        log "Arrêt du frontend (PID: $FRONTEND_PID)"
        kill -TERM $FRONTEND_PID 2>/dev/null || true
        wait $FRONTEND_PID 2>/dev/null || true
    fi

    # Clean up unified discovery file
    if [[ -f "$PROJECT_ROOT/.dev-ports.json" ]]; then
        rm -f "$PROJECT_ROOT/.dev-ports.json"
        log "🧹 Unified port discovery file cleaned up"
    fi

    log "Processus arrêtés proprement"
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

log "Démarrage du backend et du frontend..."

# If BABELIO_CACHE_LOG is set, inform the user that verbose cache logging is enabled
if [[ -n "$BABELIO_CACHE_LOG" ]]; then
    log "Note: BABELIO_CACHE_LOG is set -> Babelio disk cache logging enabled (INFO)."
    warn "Les résultats stockés en cache peuvent varier d'une exécution à l'autre; utilisez avec prudence."
fi

# Start backend in background
log "Lancement du backend FastAPI..."
cd "$PROJECT_ROOT"
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

# Create unified port discovery file
write_unified_port_discovery "$BACKEND_PORT" "$BACKEND_HOST" "$BACKEND_PID" "$FRONTEND_PORT" "$FRONTEND_HOST" "$FRONTEND_PID"

log "Backend et frontend démarrés avec succès!"
log "📍 Backend: ${BACKEND_HOST:-unknown}:${BACKEND_PORT:-unknown}"
log "📍 Frontend: ${FRONTEND_HOST:-unknown}:${FRONTEND_PORT:-unknown}"
log "📡 Port discovery: .dev-ports.json created for Claude Code auto-discovery"
log "Appuyez sur Ctrl+C pour arrêter les deux services"

# Wait for processes to complete or be interrupted
wait
