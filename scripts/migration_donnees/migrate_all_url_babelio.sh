#!/bin/bash
# Script de migration complète des URL Babelio (Issue #124)
#
# Lance le script de migration en boucle jusqu'à ce que tous les livres
# aient leur URL Babelio, avec une pause de 1 seconde entre chaque requête
# pour ne pas surcharger le serveur Babelio.
#
# Usage:
#   ./scripts/migration_donnees/migrate_all_url_babelio.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MIGRATION_SCRIPT="$SCRIPT_DIR/migrate_url_babelio.py"
PYTHONPATH="/workspaces/back-office-lmelp/src"

echo "🚀 Démarrage de la migration complète des URL Babelio"
echo "⏸️  Pause de 1 seconde entre chaque livre pour respecter le serveur"
echo ""

COUNTER=0
MAX_ITERATIONS=1000  # Sécurité pour éviter une boucle infinie

while [ $COUNTER -lt $MAX_ITERATIONS ]; do
    COUNTER=$((COUNTER + 1))
    echo "=================================================="
    echo "📚 Migration #$COUNTER"
    echo "=================================================="

    # Lancer le script de migration
    OUTPUT=$(PYTHONPATH=$PYTHONPATH python "$MIGRATION_SCRIPT" 2>&1)

    # Afficher la sortie
    echo "$OUTPUT"

    # Vérifier si tous les livres ont été traités
    if echo "$OUTPUT" | grep -q "Tous les livres ont déjà une URL Babelio"; then
        echo ""
        echo "=================================================="
        echo "✅ MIGRATION TERMINÉE"
        echo "=================================================="
        echo "Tous les livres ont maintenant leur URL Babelio!"
        exit 0
    fi

    # Vérifier si le livre a été mis à jour
    if echo "$OUTPUT" | grep -q "Livre mis à jour: ✅ Oui"; then
        echo ""
        echo "⏸️  Pause de 1 seconde avant le prochain livre..."
        sleep 1
    else
        echo ""
        echo "⚠️  Aucun livre mis à jour, arrêt de la migration"
        exit 1
    fi
done

echo ""
echo "=================================================="
echo "⚠️  LIMITE DE $MAX_ITERATIONS ITÉRATIONS ATTEINTE"
echo "=================================================="
echo "La migration s'est arrêtée par sécurité."
echo "Relancez le script si nécessaire."
exit 1
