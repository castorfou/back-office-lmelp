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
HTTP_ERROR_COUNT=0   # Compteur d'erreurs HTTP consécutives
MAX_HTTP_ERRORS=3    # Arrêt après 3 erreurs HTTP consécutives

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

    # Vérifier si on a eu une erreur HTTP (signe d'indisponibilité Babelio)
    if echo "$OUTPUT" | grep -q "Erreur lors de l'appel à Babelio"; then
        HTTP_ERROR_COUNT=$((HTTP_ERROR_COUNT + 1))
        echo ""
        echo "❌ Erreur HTTP détectée ($HTTP_ERROR_COUNT/$MAX_HTTP_ERRORS)"

        if [ $HTTP_ERROR_COUNT -ge $MAX_HTTP_ERRORS ]; then
            echo ""
            echo "=================================================="
            echo "⚠️  BABELIO SEMBLE INDISPONIBLE"
            echo "=================================================="
            echo "$MAX_HTTP_ERRORS erreurs HTTP consécutives détectées."
            echo "Le site Babelio est probablement temporairement indisponible."
            echo "Veuillez réessayer plus tard."
            exit 2
        fi

        echo "⏸️  Pause de 5 secondes avant de réessayer..."
        sleep 5
        continue
    fi

    # Vérifier si on a eu une erreur HTTP sur vérification URL
    if echo "$OUTPUT" | grep -q "URL livre invalide (HTTP"; then
        HTTP_ERROR_COUNT=$((HTTP_ERROR_COUNT + 1))
        echo ""
        echo "❌ Erreur HTTP détectée lors de la vérification ($HTTP_ERROR_COUNT/$MAX_HTTP_ERRORS)"

        if [ $HTTP_ERROR_COUNT -ge $MAX_HTTP_ERRORS ]; then
            echo ""
            echo "=================================================="
            echo "⚠️  BABELIO SEMBLE INDISPONIBLE"
            echo "=================================================="
            echo "$MAX_HTTP_ERRORS erreurs HTTP consécutives détectées."
            echo "Le site Babelio est probablement temporairement indisponible."
            echo "Veuillez réessayer plus tard."
            exit 2
        fi

        echo "⏸️  Pause de 5 secondes avant de réessayer..."
        sleep 5
        continue
    fi

    # Vérifier si on a eu une erreur de scraping (peut aussi indiquer un problème Babelio)
    if echo "$OUTPUT" | grep -q "Impossible de scraper le titre depuis la page"; then
        HTTP_ERROR_COUNT=$((HTTP_ERROR_COUNT + 1))
        echo ""
        echo "❌ Erreur scraping détectée ($HTTP_ERROR_COUNT/$MAX_HTTP_ERRORS)"

        if [ $HTTP_ERROR_COUNT -ge $MAX_HTTP_ERRORS ]; then
            echo ""
            echo "=================================================="
            echo "⚠️  BABELIO SEMBLE INDISPONIBLE"
            echo "=================================================="
            echo "$MAX_HTTP_ERRORS erreurs de scraping consécutives détectées."
            echo "Le site Babelio est probablement temporairement indisponible."
            echo "Veuillez réessayer plus tard."
            exit 2
        fi

        echo "⏸️  Pause de 5 secondes avant de réessayer..."
        sleep 5
        continue
    fi

    # Réinitialiser le compteur d'erreurs HTTP si succès
    if echo "$OUTPUT" | grep -q "Livre mis à jour: ✅ Oui"; then
        HTTP_ERROR_COUNT=0
        echo ""
        echo "⏸️  Pause de 1 seconde avant le prochain livre..."
        sleep 1
    elif echo "$OUTPUT" | grep -q "Titre ne correspond pas"; then
        # Erreur de validation = livre problématique (pas une erreur Babelio)
        HTTP_ERROR_COUNT=0
        echo ""
        echo "⏸️  Pause de 1 seconde avant le prochain livre..."
        sleep 1
    elif echo "$OUTPUT" | grep -q "Livre non traité"; then
        # not_found/error/autre = livre problématique (pas une erreur Babelio)
        HTTP_ERROR_COUNT=0
        echo ""
        echo "⏸️  Pause de 1 seconde avant le prochain livre..."
        sleep 1
    else
        echo ""
        echo "⚠️  Statut de migration inconnu, arrêt par sécurité"
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
