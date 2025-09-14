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

### Page de test Babelio

Accédez à la page de test via : **http://localhost:5174/babelio-test**

L'interface propose trois formulaires distincts :

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

### Pour les correcteurs d'épreuves
1. Saisir le nom d'auteur à vérifier
2. Consulter la suggestion si différente de la saisie
3. Valider avec le score de confiance et les données Babelio

### Pour l'enrichissement de données
1. Vérifier les métadonnées existantes
2. Récupérer des informations complémentaires (couvertures, notes)
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
