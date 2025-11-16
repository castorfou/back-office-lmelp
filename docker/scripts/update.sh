#!/bin/bash
#
# Script de mise à jour Back-Office LMELP
# Usage: ./update.sh
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKER_DIR="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$DOCKER_DIR/docker-compose.prod.yml"

echo "🔄 Mise à jour de Back-Office LMELP..."
echo ""

cd "$DOCKER_DIR"

# Pull des dernières images
echo "📦 Téléchargement des dernières images..."
docker-compose -f docker-compose.prod.yml pull

echo ""
echo "🔄 Redémarrage des conteneurs..."
docker-compose -f docker-compose.prod.yml up -d

echo ""
echo "⏳ Attente du démarrage (healthchecks)..."
sleep 10

echo ""
echo "✅ Mise à jour terminée avec succès!"
echo ""
echo "📊 Statut des conteneurs:"
docker-compose -f docker-compose.prod.yml ps
echo ""
echo "📝 Voir les logs: ./scripts/logs.sh"
