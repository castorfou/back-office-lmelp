● Phase 2 - Planifier (Plan Complet)

  📁 Structure des dossiers et fichiers

  backend/
  ├── src/back_office_lmelp/
  │   ├── app.py                      # FastAPI app principale
  │   ├── services/
  │   │   └── mongodb_service.py      # Client MongoDB direct
  │   └── models/
  │       └── episode.py              # Modèle épisode (sans Pydantic pour l'instant)
  ├── pyproject.toml                  # Dépendances backend ici
  └── .env                            # Variables d'environnement (clés Azure OpenAI)

  frontend/
  ├── src/
  │   ├── components/
  │   │   ├── EpisodeSelector.vue     # Liste déroulante épisodes
  │   │   └── EpisodeEditor.vue       # Éditeur description avec auto-save
  │   ├── views/
  │   │   └── HomePage.vue            # Page principale
  │   ├── services/
  │   │   └── api.js                  # Client API REST
  │   ├── utils/
  │   │   └── errorHandler.js         # Gestion d'erreurs centralisée
  │   ├── App.vue
  │   └── main.js
  ├── tests/
  │   ├── unit/
  │   │   ├── EpisodeSelector.test.js
  │   │   └── EpisodeEditor.test.js
  │   └── integration/
  │       └── HomePage.test.js
  ├── package.json
  ├── vite.config.js
  └── README.md

  📦 Dépendances

  Backend - Ajout dans pyproject.toml :
  dependencies = [
      "fastapi",
      "uvicorn[standard]",
      "pymongo",
      "python-dotenv",
      "python-multipart",
      "fastapi-cors",
      "openai",                       # Pour Azure OpenAI plus tard
  ]

  Frontend (Vue.js) - package.json :
  {
    "dependencies": {
      "vue": "^3.4.0",
      "axios": "^1.6.0",
      "lodash.debounce": "^4.0.8"
    },
    "devDependencies": {
      "@vitejs/plugin-vue": "^5.0.0",
      "vite": "^5.0.0",
      "@vue/test-utils": "^2.4.0",
      "vitest": "^1.0.0",
      "jsdom": "^23.0.0"
    }
  }

  Variables d'environnement .env :
  # MongoDB
  MONGODB_URL=mongodb://localhost:27017/masque_et_la_plume

  # Azure OpenAI (pour plus tard)
  AZURE_OPENAI_API_KEY=your_key_here
  AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
  AZURE_OPENAI_API_VERSION=2024-02-15-preview

  # FastAPI
  API_HOST=0.0.0.0
  API_PORT=8000

  🏗️ Architecture du code

  Backend API :
  # Routes principales
  GET  /api/episodes          # Liste tous les épisodes (titre, date, id)
  GET  /api/episodes/{id}     # Détails épisode complet
  PUT  /api/episodes/{id}     # Mise à jour description_corrigee

  Frontend Modules :
  - EpisodeSelector : Dropdown avec recherche, tri par date (plus récent en premier)
  - EpisodeEditor : TextArea avec auto-save (debounce 2s) sur description_corrigee
  - API Client : Axios avec interceptors d'erreurs
  - State Management : Reactive data simple (pas de Vuex pour l'instant)

  🧪 Stratégie de tests

  Tests Unitaires :
  - EpisodeSelector : Affichage liste, tri, sélection
  - EpisodeEditor : Auto-save, gestion changements, erreurs
  - API Service : Calls HTTP, gestion timeout

  Tests d'Intégration :
  - HomePage : Flux complet sélection → édition → sauvegarde

  Test Backend :
  - Routes API avec base MongoDB de test

  ⚠️ Points de gestion d'erreurs

  1. Connexion MongoDB : Message "Service indisponible"
  2. Timeout API : Retry automatique × 2
  3. Épisode introuvable : Retour sélecteur
  4. Sauvegarde échouée : Notification + retry manuel
  5. Données manquantes : Affichage placeholder

  📝 Documentation

  README Utilisateur : Screenshots + guide utilisation
  README Développeur : Architecture, API, déploiement
