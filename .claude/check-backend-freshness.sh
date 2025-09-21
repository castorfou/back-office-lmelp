#!/bin/bash

# Script Claude Code pour détecter automatiquement si le backend doit être relancé
# Usage: ./.claude/check-backend-freshness.sh [--max-age-minutes]

set -e

PROJECT_ROOT="/workspaces/back-office-lmelp"
MAX_AGE_MINUTES="${1:-10}"  # Par défaut 10 minutes
MAX_AGE_SECONDS=$((MAX_AGE_MINUTES * 60))

echo "🔍 Vérification de la fraîcheur du backend..."
echo "📊 Seuil d'obsolescence : ${MAX_AGE_MINUTES} minutes"

# Vérifier si le backend est actif
BACKEND_INFO=$("$PROJECT_ROOT/.claude/get-backend-info.sh" --all 2>/dev/null)

if [[ $? -ne 0 ]]; then
    echo "❌ Aucun backend détecté"
    echo "🔧 Suggestion: ./scripts/start-dev.sh"
    exit 1
fi

# Extraire l'âge en secondes depuis le JSON
AGE_SECONDS=$(echo "$BACKEND_INFO" | grep "Started:" | sed 's/Started: \([0-9]*\)s ago/\1/')

if [[ -z "$AGE_SECONDS" ]] || [[ ! "$AGE_SECONDS" =~ ^[0-9]+$ ]]; then
    echo "⚠️ Impossible de déterminer l'âge du backend"
    echo "📄 Info backend:"
    echo "$BACKEND_INFO"
    exit 1
fi

AGE_MINUTES=$((AGE_SECONDS / 60))

echo "⏰ Backend démarré il y a: ${AGE_SECONDS}s (${AGE_MINUTES} min)"

# Décision automatique
if [[ $AGE_SECONDS -gt $MAX_AGE_SECONDS ]]; then
    echo ""
    echo "🚨 BACKEND POTENTIELLEMENT OBSOLÈTE"
    echo "   Démarré il y a ${AGE_MINUTES} minutes (seuil: ${MAX_AGE_MINUTES} min)"
    echo ""
    echo "💡 Après des modifications du code backend, un redémarrage est recommandé:"
    echo "   pkill -f 'python.*back_office_lmelp' && ./scripts/start-dev.sh"
    echo ""
    echo "✅ Si aucune modification récente, le backend est probablement OK"
    exit 2  # Code spécial pour "redémarrage recommandé"
else
    echo "✅ Backend récent (${AGE_MINUTES} min) - Probablement à jour"

    # Afficher l'URL pour Claude Code
    BACKEND_URL=$("$PROJECT_ROOT/.claude/get-backend-info.sh" --url)
    echo "🌐 URL backend: $BACKEND_URL"
    echo "🧪 Test API: curl \"$BACKEND_URL/\""
    exit 0
fi
