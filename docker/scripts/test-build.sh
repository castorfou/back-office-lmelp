#!/bin/bash
#
# Script de test de build local Back-Office LMELP
# Usage: ./test-build.sh
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKER_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$DOCKER_DIR")"

echo "🧪 Test de build local Back-Office LMELP..."
echo ""

cd "$PROJECT_ROOT"

# Build backend
echo "🔨 Build image backend..."
docker build -f docker/backend/Dockerfile -t lmelp-backend:test .

# Vérifier taille image backend
BACKEND_SIZE=$(docker images lmelp-backend:test --format "{{.Size}}")
echo "✅ Backend buildé avec succès (taille: $BACKEND_SIZE)"
echo ""

# Build frontend
echo "🔨 Build image frontend..."
docker build -f docker/frontend/Dockerfile -t lmelp-frontend:test .

# Vérifier taille image frontend
FRONTEND_SIZE=$(docker images lmelp-frontend:test --format "{{.Size}}")
echo "✅ Frontend buildé avec succès (taille: $FRONTEND_SIZE)"
echo ""

echo "📊 Images créées:"
docker images | grep lmelp
echo ""

echo "✅ Tests de build terminés avec succès!"
echo ""
echo "💡 Pour tester en local:"
echo "   1. Créer docker/.env avec votre configuration"
echo "   2. Modifier docker-compose.prod.yml pour utiliser les images :test"
echo "   3. Lancer avec ./scripts/start.sh"
