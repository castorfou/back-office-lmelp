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
import Palmares from '../views/Palmares.vue';
import CalibreCorrections from '../views/CalibreCorrections.vue';
import OnKindle from '../views/OnKindle.vue';

const routes = [
  {
    path: '/',
    name: 'Dashboard',
    component: Dashboard,
    meta: {
      title: 'Accueil - Back-office LMELP'
    }
  },
  {
    path: '/episodes',
    name: 'Episodes',
    component: EpisodePage,
    meta: {
      title: 'Gestion des Épisodes - Back-office LMELP'
    }
  },
  {
    path: '/livres-auteurs',
    name: 'LivresAuteurs',
    component: LivresAuteurs,
    meta: {
      title: 'Livres et Auteurs - Back-office LMELP'
    }
  },
  {
    path: '/babelio-test',
    name: 'BabelioTest',
    component: BabelioTest,
    meta: {
      title: 'Recherche Babelio - Back-office LMELP'
    }
  },
  {
    path: '/babelio-migration',
    name: 'BabelioMigration',
    component: BabelioMigration,
    meta: {
      title: 'Migration Babelio - Back-office LMELP'
    }
  },
  {
    path: '/search',
    name: 'AdvancedSearch',
    component: AdvancedSearch,
    meta: {
      title: 'Recherche avancée - Back-office LMELP'
    }
  },
  {
    path: '/auteur/:id',
    name: 'AuteurDetail',
    component: AuteurDetail,
    meta: {
      title: 'Détail Auteur - Back-office LMELP'
    }
  },
  {
    path: '/livre/:id',
    name: 'LivreDetail',
    component: LivreDetail,
    meta: {
      title: 'Détail Livre - Back-office LMELP'
    }
  },
  {
    path: '/critique/:id',
    name: 'CritiqueDetail',
    component: () => import('../views/CritiqueDetail.vue'),
    meta: {
      title: 'Détail Critique - Back-office LMELP'
    }
  },
  {
    path: '/masquer-episodes',
    name: 'MasquerEpisodes',
    component: MasquerEpisodes,
    meta: {
      title: 'Masquer les Épisodes - Back-office LMELP'
    }
  },
  {
    path: '/calibre',
    name: 'CalibreLibrary',
    component: CalibreLibrary,
    meta: {
      title: 'Bibliothèque Calibre - Back-office LMELP'
    }
  },
  {
    path: '/identification-critiques',
    name: 'IdentificationCritiques',
    component: IdentificationCritiques,
    meta: {
      title: 'Identification des Critiques - Back-office LMELP'
    }
  },
  {
    path: '/generation-avis-critiques',
    name: 'GenerationAvisCritiques',
    component: GenerationAvisCritiques,
    meta: {
      title: 'Génération Avis Critiques - Back-office LMELP'
    }
  },
  {
    path: '/duplicates',
    name: 'DuplicateBooks',
    component: DuplicateBooks,
    meta: {
      title: 'Gestion des Doublons - Back-office LMELP'
    }
  },
  {
    path: '/palmares',
    name: 'Palmares',
    component: Palmares,
    meta: {
      title: 'Palmarès - Back-office LMELP'
    }
  },
  {
    path: '/calibre-corrections',
    name: 'CalibreCorrections',
    component: CalibreCorrections,
    meta: {
      title: 'Corrections Calibre - Back-office LMELP'
    }
  },
  {
    path: '/onkindle',
    name: 'OnKindle',
    component: OnKindle,
    meta: {
      title: 'OnKindle - Back-office LMELP'
    }
  },
  {
    path: '/emissions/:date',
    name: 'EmissionDetail',
    component: () => import('../views/Emissions.vue'),
    meta: {
      title: 'Émission - Back-office LMELP'
    }
  },
  {
    path: '/emissions',
    name: 'Emissions',
    component: () => import('../views/Emissions.vue'),
    meta: {
      title: 'Émissions - Back-office LMELP'
    }
  },
  {
    path: '/about',
    name: 'About',
    component: () => import('../views/AboutPage.vue'),
    meta: {
      title: 'À propos - Back-office LMELP'
    }
  }
];

const router = createRouter({
  history: createWebHistory(),
  routes,
  // Configuration du comportement de scroll
  scrollBehavior(to, from, savedPosition) {
    // Si l'utilisateur utilise les boutons précédent/suivant du navigateur,
    // restaurer la position de scroll sauvegardée
    if (savedPosition) {
      return savedPosition;
    }
    // Pour toute autre navigation, scroller vers le haut
    return { top: 0, behavior: 'smooth' };
  }
});

// Mettre à jour le titre de la page lors de la navigation
router.afterEach((to) => {
  document.title = to.meta.title || 'Back-office LMELP';
});

export default router;
