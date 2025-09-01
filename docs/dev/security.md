# Sécurité

Cette section couvre les aspects de sécurité du back-office LMELP.

## Mesures de sécurité

### Analyse automatique
- **detect-secrets** : Détection de secrets dans le code
- **Dependabot** : Mise à jour automatique des dépendances
- **CI/CD** : Vérifications de sécurité à chaque commit

### Configuration sécurisée
- **Variables d'environnement** : Secrets externalisés
- **CORS** : Configuration restrictive pour l'API
- **Validation** : Entrées utilisateur validées

## Gestion des secrets

### Variables d'environnement
```bash
# Fichier .env (ne jamais committer)
MONGODB_URL=mongodb://localhost:27017
API_SECRET_KEY=your-secret-key
OPENAI_API_KEY=your-openai-key
```

### Pre-commit hooks
Le hook `detect-secrets` analyse :
- Clés API potentielles
- Mots de passe en dur
- Tokens d'authentification
- Autres secrets sensibles

## Bonnes pratiques

### Code
- ✅ Utiliser des variables d'environnement
- ✅ Valider toutes les entrées utilisateur
- ✅ Échapper les données avant affichage
- ❌ Jamais de secrets en dur dans le code

### Déploiement
- ✅ HTTPS uniquement en production
- ✅ Mise à jour régulière des dépendances
- ✅ Logs sécurisés (pas de données sensibles)
- ❌ Jamais de mode debug en production

## Audit de sécurité

### Outils utilisés
- **Ruff** : Analyse statique de code
- **MyPy** : Vérification de types
- **detect-secrets** : Détection de secrets
- **npm audit** : Vulnérabilités JavaScript

### Processus
1. Analyse automatique à chaque commit
2. Revue de code obligatoire
3. Tests de sécurité en CI/CD
4. Mise à jour régulière des dépendances
