# Script de Développement Unifié

## Vue d'ensemble

Le script `scripts/start-dev.sh` permet de lancer simultanément le backend et le frontend avec une seule commande, améliorant significativement l'expérience développeur.

## Usage

```bash
# Depuis la racine du projet
./scripts/start-dev.sh
```

## Fonctionnalités

### Lancement Automatique
- **Backend FastAPI** : Démarré en arrière-plan avec la configuration automatique du port
- **Frontend Vue.js** : Lancé en mode développement avec rechargement à chaud
- **Gestion des Dépendances** : Vérification et installation automatique des dépendances frontend si nécessaire

### Arrêt Propre
- **Signal Trapping** : Capture des signaux SIGINT et SIGTERM pour un arrêt propre
- **Nettoyage des Processus** : Terminaison correcte des processus backend et frontend
- **Ctrl+C** : Arrête les deux services simultanément

### Logging Coloré
- **Messages Informatifs** : Affichage en vert pour les informations
- **Avertissements** : Affichage en jaune pour les warnings
- **Erreurs** : Affichage en rouge pour les erreurs
- **Timestamps** : Horodatage de tous les messages

## Architecture Technique

### Variables d'Environnement
- `PROJECT_ROOT` : Chemin vers la racine du projet (`/workspaces/back-office-lmelp`)
- `PYTHONPATH` : Configuration automatique pour le backend

### Processus de Démarrage
1. Vérification de l'environnement et de la structure du projet
2. Contrôle des dépendances frontend (installation si nécessaire)
3. Lancement du backend en arrière-plan
4. Attente de 2 secondes pour la stabilisation du backend
5. Lancement du frontend en arrière-plan
6. Attente des processus ou interruption utilisateur

### Gestion des Erreurs
- Vérification de la présence des fichiers essentiels (`pyproject.toml`, répertoire `frontend/`)
- Installation automatique des dépendances manquantes
- Arrêt sécurisé en cas d'erreur

## Tests

Le script est couvert par une suite de tests automatisés (`tests/test_start_dev_script.py`) qui vérifient :
- Existence et permissions exécutables
- Syntaxe bash valide
- Présence des commandes essentielles
- Gestion correcte des signaux

## Dépannage

### Script Non Exécutable
```bash
chmod +x scripts/start-dev.sh
```

### Dépendances Frontend Manquantes
Le script les installe automatiquement, mais vous pouvez le faire manuellement :
```bash
cd frontend && npm ci
```

### Problèmes de Port
Le backend utilise la sélection automatique de port. Consultez les logs pour connaître le port utilisé.

## Comparaison Avant/Après

### Avant (2 terminaux nécessaires)
```bash
# Terminal 1
PYTHONPATH=/workspaces/back-office-lmelp/src python -m back_office_lmelp.app

# Terminal 2
cd /workspaces/back-office-lmelp/frontend && npm run dev
```

### Après (1 seule commande)
```bash
./scripts/start-dev.sh
```

Cette amélioration simplifie considérablement le processus de développement et réduit les erreurs de configuration.
