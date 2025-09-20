# Vérification orthographique Babelio

## Vue d'ensemble

L'intégration Babelio permet de vérifier et corriger l'orthographe des noms d'auteurs et titres de livres en utilisant la base de données collaborative de Babelio.com.

## Fonctionnalités

### ✅ Auteurs
- **Vérification exacte** : Confirme l'orthographe correcte des noms d'auteurs
- **Correction automatique** : Propose des corrections pour les fautes de frappe
- **Données enrichies** : Fournit des informations supplémentaires (nombre d'œuvres, popularité)
- **Lien Babelio** : URL directe vers la page auteur sur Babelio

**Exemple :**
- Saisie : "Houllebeck" → Correction : "Michel Houellebecq"
- Saisie : "Amélie Nothomb" → Vérification : ✅ Orthographe correcte

### ✅ Livres
- **Vérification titre + auteur** : Validation croisée titre/auteur
- **Correction intelligente** : Suggestions pour titres mal orthographiés
- **Métadonnées complètes** : Couverture, notes, nombre d'exemplaires
- **Lien direct** : URL vers la page livre sur Babelio

**Exemple :**
- Titre : "Le Petit Prince", Auteur : "Antoine de Saint-Exupéry" → ✅ Vérifié

### ⚠️ Éditeurs
- **Fonctionnalité limitée** : Recherche basique dans les données auteurs
- **Nécessite amélioration** : Approche alternative en développement

## Interface utilisateur

### Page Livres et Auteurs (Validation intégrée)

**Accès principal :** Via la navigation → **Livres et Auteurs**

La validation bibliographique est désormais **intégrée directement** dans l'interface de consultation des livres :

1. **Sélection d'épisode** : Choisissez un épisode avec avis critiques
2. **Tableau enrichi** : Colonne "Validation Biblio" avec indicateurs visuels :
   - ✅ **Validé** : Données confirmées par Babelio
   - 🔄 **Suggestion** : Correction proposée (cliquez pour voir les détails)
   - ❓ **Non trouvé** : Aucune correspondance fiable trouvée
   - ⚠️ **Erreur** : Problème de connexion (bouton retry disponible)

3. **Validation automatique** : Chaque livre est vérifié automatiquement au chargement
4. **Validation intelligente** : Combine plusieurs sources :
   - Données exactes de l'épisode (ground truth)
   - Corrections orthographiques Babelio
   - Vérification croisée auteur/livre

### Page de test Babelio (Développeurs)

**Accès technique :** **http://localhost:5174/babelio-test**

Interface de débogage avec trois formulaires distincts :

1. **Formulaire Auteur**
   - Champ : Nom de l'auteur
   - Exemples : "Amélie Nothomb", "Houllebeck" (faute intentionnelle)

2. **Formulaire Livre**
   - Champs : Titre du livre, Auteur (optionnel)
   - Exemple : "Le Petit Prince" / "Antoine de Saint-Exupéry"

3. **Formulaire Éditeur**
   - Champ : Nom de l'éditeur
   - Exemple : "Gallimard"

### Résultats

Pour chaque vérification, vous obtenez :
- **Status** : `verified` (exact), `corrected` (corrigé), `not_found` (non trouvé)
- **Score de confiance** : De 0.0 à 1.0 (1.0 = correspondance parfaite)
- **Suggestion** : Orthographe corrigée si nécessaire
- **Données Babelio** : Informations complètes de la base de données
- **URL** : Lien direct vers la page Babelio

## Cas d'usage

### Pour les utilisateurs finaux
1. **Navigation** : Aller dans "Livres et Auteurs"
2. **Sélection** : Choisir un épisode avec avis critiques
3. **Consultation** : Observer les indicateurs de validation dans le tableau
4. **Correction** : Consulter les suggestions (🔄) pour identifier les erreurs orthographiques

### Pour les correcteurs d'épreuves
1. **Validation automatique** : Les données sont vérifiées automatiquement
2. **Suggestions intelligentes** : Corrections basées sur les données de l'épisode ET Babelio
3. **Fiabilité** : Score de confiance et validation croisée auteur/livre
4. **Contexte** : Priorise les données exactes de l'épisode (ground truth)

### Pour l'enrichissement de données
1. Vérifier les métadonnées existantes dans le tableau
2. Récupérer des informations complémentaires via les suggestions
3. Obtenir des liens canoniques vers Babelio

## Limitations actuelles

- **Éditeurs** : Recherche limitée, nécessite une approche spécialisée
- **Rate limiting** : 1 requête par seconde pour respecter Babelio
- **Dépendance externe** : Nécessite une connexion internet active

## Support et dépannage

En cas de problème :
1. Vérifiez votre connexion internet
2. Consultez les logs du serveur backend
3. Reportez les bugs via les issues GitHub du projet
