
Retour par Claude

  1. Le serveur MCP MongoDB est fonctionnel - je peux maintenant explorer la base masque_et_la_plume avec ses 8 collections
  2. Le projet LMELP est un système de recommandation littéraire basé sur l'affinité avec les critiques du Masque et la Plume
  3. Le back-office est nécessaire pour nettoyer et structurer les données MongoDB existantes
  4. Les priorités sont claires : nettoyer les transcriptions et extraire toutes les entités (livres, auteurs, éditeurs, critiques,
  avis)

  Maintenant que le serveur MCP est opérationnel, nous pouvons progresser sur la création de l'interface moderne pour gérer cette base
  de données. La prochaine étape serait d'explorer plus en détail le contenu des collections pour mieux comprendre la structure et les
  besoins de nettoyage.

## ⚠️ Point Critique : Hiérarchie de Fiabilité des Données

**Données FIABLES** (source France Inter) :
- `episodes.titre` et `episodes.description` - Texte surveillé et solide

**Données SUSPECTES** (source Whisper sur MP3) :
- `episodes.transcription` - Erreurs possibles sur noms propres (auteurs, critiques)
- `avis_critiques` - Générés depuis transcriptions potentiellement erronées

## 🔧 Stratégie de Nettoyage

**Approche retenue** : Extraire entités erronées → Corriger entités → Stocker propre
- Partir de la transcription légèrement erronée
- Extraire les auteurs (avec erreurs type "Neige Sinnault")
- Corriger les auteurs extraits
- Stocker les auteurs propres en base
- Optionnellement corriger après coup la transcription (→ collection `emissions`)

## 🏗️ Architecture Technique

### Stack Technologique
- **Backend** : FastAPI + Pydantic
- **Frontend** : Vue.js ou React
- **Base de données** : MongoDB (accès direct + MCP pour exploration)
- **LLM** : Azure OpenAI (GPT-4o) pour correction d'entités
- **Validation** : Pydantic pour type safety et validation

### Structure du Projet

```
src/back_office_lmelp/
├── models/
│   ├── entities.py          # Auteur, Livre, Episode (Pydantic)
│   ├── corrections.py       # Modèles correction/validation
│   └── api_models.py        # Request/Response models
├── services/
│   ├── mongodb_service.py   # Client MongoDB direct
│   ├── azure_openai_service.py  # Client Azure OpenAI
│   └── correction_service.py    # Logique correction entités
├── api/
│   └── endpoints.py         # Routes FastAPI
└── app.py                   # Application FastAPI principale

frontend/                     # Interface Vue.js/React
├── src/
│   ├── components/          # Composants réutilisables
│   │   ├── EntityEditor.vue # Éditeur d'entités
│   │   └── DataTable.vue    # Tableaux de données
│   └── views/              # Pages principales
│       ├── Dashboard.vue    # Vue d'ensemble collections
│       ├── EntitiesRepair.vue  # ⭐ Correction entités
│       ├── Episodes.vue     # Gestion épisodes
│       └── DataExport.vue   # Export données nettoyées
└── package.json
```

### Fonctionnalités Clés
1. **Dashboard** : Statistiques collections, qualité données
2. **Entities Repair** : Interface de correction des noms d'auteurs/entités erronés ⭐
3. **Episodes Management** : Gestion épisodes + transcriptions
4. **Data Export** : Export données nettoyées vers nouvelles collections

### Avantages Architecture
- **FastAPI** : Performance, documentation auto-générée
- **Pydantic** : Validation robuste, type safety
- **Vue.js/React** : Interface moderne et réactive
- **Séparation claire** : Backend API + Frontend découplé
