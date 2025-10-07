# Architecture Frontend - Back-office LMELP

## Vue d'ensemble

Le frontend utilise Vue.js 3 avec le Composition API et Vue Router pour la navigation entre les pages. L'architecture suit un pattern de Single Page Application (SPA) avec routing côté client.

## Structure des composants

### Pages (Views)

#### Dashboard (`src/views/Dashboard.vue`)
Page d'accueil principale de l'application.

**Fonctionnalités :**
- Affichage des statistiques générales (nombre d'épisodes, corrections, etc.)
- Navigation vers les différentes fonctions disponibles
- Design responsive adapté aux mobiles
- Chargement asynchrone des statistiques depuis l'API

**Route :** `/`

#### EpisodePage (`src/views/EpisodePage.vue`)
Page de gestion et modification des épisodes (ancienne HomePage).

**Fonctionnalités :**
- Sélection d'épisodes via dropdown
- Modification des titres et descriptions
- Sauvegarde automatique
- Navigation de retour vers l'accueil

**Route :** `/episodes`

### Composants

#### Navigation (`src/components/Navigation.vue`)
Composant de navigation réutilisable.

**Fonctionnalités :**
- Lien de retour vers l'accueil (masqué sur la page d'accueil)
- Affichage du titre de la page courante
- Design responsive

#### EpisodeSelector (`src/components/EpisodeSelector.vue`)
Composant de sélection d'épisodes (inchangé).

#### EpisodeEditor (`src/components/EpisodeEditor.vue`)
Composant d'édition d'épisodes (inchangé).

## Routing

Le routing est géré par Vue Router 4 avec les routes suivantes :

```javascript
const routes = [
  {
    path: '/',
    name: 'Dashboard',
    component: Dashboard,
    meta: { title: 'Accueil - Back-office LMELP' }
  },
  {
    path: '/episodes',
    name: 'Episodes',
    component: EpisodePage,
    meta: { title: 'Gestion des Épisodes - Back-office LMELP' }
  }
]
```

### Navigation programmatique

```javascript
// Vers l'accueil
this.$router.push('/');

// Vers la page d'épisodes
this.$router.push('/episodes');
```

## Computed Properties

### Statistiques de validation (`LivresAuteurs.vue`)

#### `programBooksValidationStats`
Computed property qui calcule les statistiques de validation pour les livres au programme.

**Logique** :
- Filtre les livres avec `programme: true` OU `coup_de_coeur: true`
- Catégorise chaque livre selon son statut :
  - **Traités** : `status === 'mongo'` (déjà en base MongoDB)
  - **Suggested** : `suggested_author` ou `suggested_title` présents (suggestions Babelio)
  - **Not found** : Ni traité ni suggestion

**Retour** :
```javascript
{
  traites: number,    // Livres en MongoDB
  suggested: number,  // Livres avec suggestions
  not_found: number,  // Livres non trouvés
  total: number       // Total au programme
}
```

**Utilisation** :
```vue
<span v-if="programBooksValidationStats.total > 0">
  — au programme :
  {{ programBooksValidationStats.traites }} traités,
  {{ programBooksValidationStats.suggested }} suggested,
  {{ programBooksValidationStats.not_found }} not found
</span>
```

**Tests** :
- Tests unitaires : `tests/unit/ProgramBooksStats.test.js`
- Tests d'intégration : `tests/integration/LivresAuteurs.test.js`

## Services API

### statisticsService (`src/services/api.js`)
Nouveau service pour récupérer les statistiques.

```javascript
const stats = await statisticsService.getStatistics();
// Retourne:
// {
//   totalEpisodes: number,
//   episodesWithCorrectedTitles: number,
//   episodesWithCorrectedDescriptions: number,
//   criticalReviews: number,
//   lastUpdateDate: string | null
// }
```

### episodeService (inchangé)
Service existant pour la gestion des épisodes.

## Gestion des erreurs

- **Chargement des statistiques** : Affichage de placeholders (`--`) en cas d'erreur
- **Navigation** : Gestion des erreurs de routing avec Vue Router
- **API** : Intercepteurs Axios pour centraliser la gestion d'erreurs

## Responsive Design

Tous les composants sont optimisés pour les écrans mobiles :

- **Breakpoints** : 768px (tablettes), 480px (mobiles)
- **Layout** : Grilles flexibles avec `grid-template-columns: repeat(auto-fit, minmax(...))`
- **Navigation** : Adaptation automatique sur petits écrans

## Tests

### Tests d'intégration
- `tests/integration/Dashboard.test.js` : Tests de la page d'accueil
- `tests/integration/EpisodePage.test.js` : Tests de la page d'épisodes
- `tests/integration/App.test.js` : Tests du routing principal

### Tests unitaires
- `tests/unit/Navigation.test.js` : Tests du composant Navigation
- Tests existants pour EpisodeSelector et EpisodeEditor (inchangés)

## Migration depuis l'ancienne architecture

### Changements principaux
1. **HomePage → EpisodePage** : Renommage et déplacement de la logique
2. **Ajout du routing** : Vue Router pour la navigation
3. **Nouvelle page d'accueil** : Dashboard avec statistiques
4. **Navigation** : Composant de navigation réutilisable

### Compatibilité
- L'ancienne logique de gestion des épisodes reste identique
- Les composants EpisodeSelector et EpisodeEditor sont inchangés
- L'API existante reste compatible

## Développement

### Commandes utiles
```bash
# Démarrage du serveur de développement
cd frontend && npm run dev

# Tests
cd frontend && npm test -- --run

# Build de production
cd frontend && npm run build
```

### Structure des fichiers
```
frontend/src/
├── views/           # Pages principales
│   ├── Dashboard.vue    # Page d'accueil
│   └── EpisodePage.vue  # Page de gestion des épisodes
├── components/      # Composants réutilisables
│   ├── Navigation.vue   # Composant de navigation
│   ├── EpisodeSelector.vue
│   └── EpisodeEditor.vue
├── router/          # Configuration du routing
│   └── index.js     # Routes et configuration Vue Router
├── services/        # Services API
│   └── api.js       # Services episodeService et statisticsService
├── utils/           # Utilitaires
└── App.vue          # Composant racine avec router-view
```
