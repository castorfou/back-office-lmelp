#!/bin/bash
#
# Script d'affichage des logs Back-Office LMELP
# Usage: ./logs.sh [backend|frontend]
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKER_DIR="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$DOCKER_DIR/docker-compose.prod.yml"

cd "$DOCKER_DIR"

SERVICE="${1:-}"

if [ -z "$SERVICE" ]; then
    echo "📝 Logs de tous les conteneurs (Ctrl+C pour quitter):"
    echo ""
    docker-compose -f docker-compose.prod.yml logs -f --tail=100
elif [ "$SERVICE" = "backend" ]; then
    echo "📝 Logs du backend (Ctrl+C pour quitter):"
    echo ""
    docker-compose -f docker-compose.prod.yml logs -f --tail=100 backend
elif [ "$SERVICE" = "frontend" ]; then
    echo "📝 Logs du frontend (Ctrl+C pour quitter):"
    echo ""
    docker-compose -f docker-compose.prod.yml logs -f --tail=100 frontend
else
    echo "❌ Service inconnu: $SERVICE"
    echo "Usage: ./logs.sh [backend|frontend]"
    exit 1
fi
