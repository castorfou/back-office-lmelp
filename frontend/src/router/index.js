/**
 * Configuration du routeur Vue pour l'application
 */

import { createRouter, createWebHistory } from 'vue-router';
import Dashboard from '../views/Dashboard.vue';
import EpisodePage from '../views/EpisodePage.vue';
import LivresAuteurs from '../views/LivresAuteurs.vue';
import BabelioTest from '../views/BabelioTest.vue';
import BabelioMigration from '../views/BabelioMigration.vue';
import AdvancedSearch from '../views/AdvancedSearch.vue';
import AuteurDetail from '../views/AuteurDetail.vue';
import LivreDetail from '../views/LivreDetail.vue';
import MasquerEpisodes from '../views/MasquerEpisodes.vue';
import CalibreLibrary from '../views/CalibreLibrary.vue';
import IdentificationCritiques from '../views/IdentificationCritiques.vue';
import GenerationAvisCritiques from '../views/GenerationAvisCritiques.vue';
import DuplicateBooks from '../views/DuplicateBooks.vue';
import OrphanedAvis from '../views/OrphanedAvis.vue';
import Palmares from '../views/Palmares.vue';
import CalibreCorrections from '../views/CalibreCorrections.vue';
import OnKindle from '../views/OnKindle.vue';
import Recommendations from '../views/Recommendations.vue';
import BabelioControl from '../views/BabelioControl.vue';
import RssMonitoring from '../views/RssMonitoring.vue';
import PgxTranscription from '../views/PgxTranscription.vue';

const routes = [
  {
    path: '/',
    name: 'Dashboard',
    component: Dashboard,
    meta: {
      title: 'Accueil - lmelp'
    }
  },
  {
    path: '/episodes',
    name: 'Episodes',
    component: EpisodePage,
    meta: {
      title: 'Gestion des Épisodes - lmelp'
    }
  },
  {
    path: '/livres-auteurs',
    name: 'LivresAuteurs',
    component: LivresAuteurs,
    meta: {
      title: 'Livres et Auteurs - lmelp'
    }
  },
  {
    path: '/babelio-test',
    name: 'BabelioTest',
    component: BabelioTest,
    meta: {
      title: 'Recherche Babelio - lmelp'
    }
  },
  {
    path: '/babelio-migration',
    name: 'BabelioMigration',
    component: BabelioMigration,
    meta: {
      title: 'Migration Babelio - lmelp'
    }
  },
  {
    path: '/search',
    name: 'AdvancedSearch',
    component: AdvancedSearch,
    meta: {
      title: 'Recherche avancée - lmelp'
    }
  },
  {
    path: '/auteur/:id',
    name: 'AuteurDetail',
    component: AuteurDetail,
    meta: {
      title: 'Détail Auteur - lmelp'
    }
  },
  {
    path: '/livre/:id',
    name: 'LivreDetail',
    component: LivreDetail,
    meta: {
      title: 'Détail Livre - lmelp'
    }
  },
  {
    path: '/critiques',
    name: 'Critiques',
    component: () => import('../views/Critiques.vue'),
    meta: {
      title: 'Critiques - lmelp'
    }
  },
  {
    path: '/critique/:id',
    name: 'CritiqueDetail',
    component: () => import('../views/CritiqueDetail.vue'),
    meta: {
      title: 'Détail Critique - lmelp'
    }
  },
  {
    path: '/masquer-episodes',
    name: 'MasquerEpisodes',
    component: MasquerEpisodes,
    meta: {
      title: 'Masquer les Épisodes - lmelp'
    }
  },
  {
    path: '/calibre',
    name: 'CalibreLibrary',
    component: CalibreLibrary,
    meta: {
      title: 'Bibliothèque Calibre - lmelp'
    }
  },
  {
    path: '/identification-critiques',
    name: 'IdentificationCritiques',
    component: IdentificationCritiques,
    meta: {
      title: 'Identification des Critiques - lmelp'
    }
  },
  {
    path: '/generation-avis-critiques',
    name: 'GenerationAvisCritiques',
    component: GenerationAvisCritiques,
    meta: {
      title: 'Génération Avis Critiques - lmelp'
    }
  },
  {
    path: '/duplicates',
    name: 'DuplicateBooks',
    component: DuplicateBooks,
    meta: {
      title: 'Gestion des Doublons - lmelp'
    }
  },
  {
    path: '/avis-orphelins',
    name: 'OrphanedAvis',
    component: OrphanedAvis,
    meta: {
      title: 'Avis Orphelins - lmelp'
    }
  },
  {
    path: '/palmares',
    name: 'Palmares',
    component: Palmares,
    meta: {
      title: 'Palmarès - lmelp'
    }
  },
  {
    path: '/calibre-corrections',
    name: 'CalibreCorrections',
    component: CalibreCorrections,
    meta: {
      title: 'Corrections Calibre - lmelp'
    }
  },
  {
    path: '/onkindle',
    name: 'OnKindle',
    component: OnKindle,
    meta: {
      title: 'OnKindle - lmelp'
    }
  },
  {
    path: '/recommendations',
    name: 'Recommendations',
    component: Recommendations,
    meta: {
      title: 'Mes Recommandations - lmelp'
    }
  },
  {
    path: '/emissions/:date',
    name: 'EmissionDetail',
    component: () => import('../views/Emissions.vue'),
    meta: {
      title: 'Émission - lmelp'
    }
  },
  {
    path: '/emissions',
    name: 'Emissions',
    component: () => import('../views/Emissions.vue'),
    meta: {
      title: 'Émissions - lmelp'
    }
  },
  {
    path: '/babelio-control',
    name: 'BabelioControl',
    component: BabelioControl,
    meta: {
      title: 'Contrôle Babelio - lmelp'
    }
  },
  {
    path: '/rss-monitoring',
    name: 'RssMonitoring',
    component: RssMonitoring,
    meta: {
      title: 'Monitoring RSS - lmelp'
    }
  },
  {
    path: '/transcription-pgx',
    name: 'PgxTranscription',
    component: PgxTranscription,
    meta: {
      title: 'Transcription PGX - lmelp'
    }
  },
  {
    path: '/about',
    name: 'About',
    component: () => import('../views/AboutPage.vue'),
    meta: {
      title: 'À propos - lmelp'
    }
  }
];

const router = createRouter({
  history: createWebHistory(),
  routes,
  // Configuration du comportement de scroll
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) {
      return savedPosition;
    }
    if (to.hash) {
      return { el: to.hash, behavior: 'smooth' };
    }
    return { top: 0, behavior: 'smooth' };
  }
});

// Mettre à jour le titre de la page lors de la navigation
router.afterEach((to) => {
  document.title = to.meta.title || 'lmelp';
});

export default router;
