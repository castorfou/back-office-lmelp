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

# Start backend in background
log "Lancement du backend FastAPI..."
cd "$PROJECT_ROOT"
PYTHONPATH="$PROJECT_ROOT/src" python -m back_office_lmelp.app &
BACKEND_PID=$!
log "Backend démarré (PID: $BACKEND_PID)"

# Wait a bit for backend to start
sleep 2

# Start frontend in background
log "Lancement du frontend Vue.js..."
cd "$PROJECT_ROOT/frontend" && npm run dev &
FRONTEND_PID=$!
log "Frontend démarré (PID: $FRONTEND_PID)"

log "Backend et frontend démarrés avec succès!"
log "Appuyez sur Ctrl+C pour arrêter les deux services"

# Wait for processes to complete or be interrupted
wait
