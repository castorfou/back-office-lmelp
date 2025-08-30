# Back-office LMELP - Frontend

Interface Vue.js pour la gestion et correction des épisodes du Masque et la Plume.

## 🚀 Démarrage rapide

### Prérequis
- Node.js 18+
- npm ou yarn
- Backend FastAPI en cours d'exécution (port 8000)

### Installation et lancement

```bash
# Installation des dépendances
npm install

# Lancement en mode développement
npm run dev

# L'application sera accessible sur http://localhost:5173
```

### Autres commandes utiles

```bash
# Construction pour la production
npm run build

# Prévisualisation du build de production
npm run preview

# Lancement des tests
npm run test

# Tests avec interface graphique
npm run test:ui
```

## 📋 Guide utilisateur

### 1. Sélection d'épisode

![Sélecteur d'épisode](docs/images/selector.png)

- **Liste déroulante** : Tous les épisodes disponibles (217 au total)
- **Tri automatique** : Par date décroissante (plus récents en premier)
- **Format d'affichage** : `Date [Type] - Titre`
- **Gestion d'erreurs** : Bouton "Réessayer" en cas d'échec de chargement

### 2. Édition de description

![Éditeur d'épisode](docs/images/editor.png)

**Zone supérieure (lecture seule)** :
- Description originale issue de France Inter
- Informations : titre, date, type d'émission

**Zone d'édition** :
- Champ de saisie pour la description corrigée
- **Sauvegarde automatique** : 2 secondes après la dernière modification
- **Indicateur de statut** : Sauvegarde en cours / Sauvegardé / Erreur

### 3. Fonctionnalités

✅ **Visualisation** : Description originale vs corrigée
✏️ **Édition** : Modification libre du texte
💾 **Auto-save** : Pas besoin de cliquer "Sauvegarder"
🔄 **Gestion d'erreurs** : Retry automatique et messages explicites
📱 **Responsive** : Interface adaptative mobile/desktop

## 🔧 Configuration

### Variables d'environnement

Le frontend se connecte automatiquement au backend via le proxy Vite configuré dans `vite.config.js` :

```javascript
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8000',  // Backend FastAPI
      changeOrigin: true
    }
  }
}
```

### Personnalisation

**Délai d'auto-save** : Modifier la valeur dans `EpisodeEditor.vue` :
```javascript
debouncedSave: debounce(function() {
  this.saveDescription();
}, 2000), // 2000ms = 2 secondes
```

**Timeout des requêtes** : Modifier dans `src/services/api.js` :
```javascript
const api = axios.create({
  timeout: 10000, // 10 secondes
});
```

## 🧪 Tests

### Structure des tests

```
tests/
├── unit/                   # Tests unitaires des composants
│   ├── EpisodeSelector.test.js
│   └── EpisodeEditor.test.js
└── integration/            # Tests d'intégration
    └── HomePage.test.js
```

### Lancement des tests

```bash
# Tous les tests
npm run test

# Tests en mode watch (re-exécution automatique)
npm run test -- --watch

# Tests avec couverture
npm run test -- --coverage

# Interface graphique des tests
npm run test:ui
```

### Couverture de tests

Les tests couvrent :
- ✅ Chargement et affichage des épisodes
- ✅ Sélection et changement d'épisode
- ✅ Édition et sauvegarde automatique
- ✅ Gestion d'erreurs et retry
- ✅ Formatage des dates et données
- ✅ Flux d'utilisation complets

## 🔨 Développement

### Architecture des composants

```
src/
├── components/
│   ├── EpisodeSelector.vue     # Sélection d'épisode
│   └── EpisodeEditor.vue       # Édition de description
├── views/
│   └── HomePage.vue            # Page principale
├── services/
│   └── api.js                  # Client API REST
└── utils/
    └── errorHandler.js         # Gestion centralisée des erreurs
```

### Ajout de nouvelles fonctionnalités

1. **Nouveau composant** : Créer dans `src/components/`
2. **Nouveaux tests** : Ajouter dans `tests/unit/`
3. **Nouvelle route API** : Étendre `src/services/api.js`
4. **Gestion d'erreurs** : Utiliser `errorMixin` ou `ErrorHandler`

### Conventions de code

- **Vue.js 3** avec Composition API optionnelle
- **JavaScript ES6+** (pas de TypeScript pour simplifier)
- **CSS scoped** dans chaque composant
- **Tests unitaires** obligatoires pour chaque composant
- **Gestion d'erreurs** centralisée via `errorHandler.js`

## 🚀 Déploiement

### Build de production

```bash
npm run build
```

Les fichiers de production seront générés dans le dossier `dist/`.

### Serveur web

L'application peut être servie par n'importe quel serveur web statique :

```bash
# Avec serve
npx serve dist

# Avec Python
python -m http.server -d dist 8080

# Avec nginx (configuration exemple)
# À placer dans /etc/nginx/sites-available/
server {
    listen 80;
    server_name your-domain.com;
    root /path/to/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://localhost:8000;
    }
}
```

### Variables d'environnement de production

Pour changer l'URL du backend en production, modifier `vite.config.js` ou utiliser des variables d'environnement :

```javascript
// vite.config.js
export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: process.env.VITE_API_URL || 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})
```

## 📞 Support

Pour toute question ou problème :

1. **Documentation** : Consultez ce README et le code source commenté
2. **Tests** : Lancez `npm run test` pour vérifier l'installation
3. **Logs** : Consultez la console du navigateur (F12) pour les erreurs
4. **Issues** : Créez une issue sur le repository GitHub

## 🔄 Évolution

### Fonctionnalités prévues

- 🔍 Recherche avancée dans les épisodes
- 📊 Statistiques de correction
- 🤖 Intégration avec Azure OpenAI pour suggestions
- 📤 Export des données corrigées
- 👥 Gestion multi-utilisateurs

### Architecture évolutive

Le code est conçu pour faciliter l'ajout de nouvelles fonctionnalités :

- **Services modulaires** : `api.js` extensible
- **Composants réutilisables** : Pattern Vue.js standard
- **Gestion d'erreurs centralisée** : `errorHandler.js`
- **Tests complets** : Confiance pour les refactorings
