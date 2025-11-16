#!/bin/bash
#
# Script d'arrêt Back-Office LMELP
# Usage: ./stop.sh
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKER_DIR="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$DOCKER_DIR/docker-compose.prod.yml"

echo "🛑 Arrêt de Back-Office LMELP..."

cd "$DOCKER_DIR"
docker-compose -f docker-compose.prod.yml down

echo ""
echo "✅ Back-Office LMELP arrêté avec succès!"
echo ""
echo "💡 Pour redémarrer: ./scripts/start.sh"
