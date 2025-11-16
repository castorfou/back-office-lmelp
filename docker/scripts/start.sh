#!/bin/bash
#
# Script de démarrage Back-Office LMELP
# Usage: ./start.sh
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKER_DIR="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$DOCKER_DIR/docker-compose.prod.yml"

echo "🚀 Démarrage de Back-Office LMELP..."

# Vérifier que docker-compose.prod.yml existe
if [ ! -f "$COMPOSE_FILE" ]; then
    echo "❌ Fichier $COMPOSE_FILE introuvable"
    exit 1
fi

# Vérifier si .env existe, sinon utiliser les valeurs par défaut
if [ ! -f "$DOCKER_DIR/.env" ]; then
    echo "⚠️  Fichier .env introuvable, utilisation des valeurs par défaut"
    echo "💡 Copiez .env.template vers .env pour personnaliser la configuration"
fi

# Démarrer les conteneurs
cd "$DOCKER_DIR"
docker-compose -f docker-compose.prod.yml up -d

echo ""
echo "✅ Back-Office LMELP démarré avec succès!"
echo ""
echo "📊 Statut des conteneurs:"
docker-compose -f docker-compose.prod.yml ps
echo ""
echo "🌐 Accès application: http://localhost:8080"
echo "📝 Voir les logs: ./scripts/logs.sh"
echo "🛑 Arrêter: ./scripts/stop.sh"
