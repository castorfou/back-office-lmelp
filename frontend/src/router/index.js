/**
 * Configuration du routeur Vue pour l'application
 */

import { createRouter, createWebHistory } from 'vue-router';
import Dashboard from '../views/Dashboard.vue';
import EpisodePage from '../views/EpisodePage.vue';
import LivresAuteurs from '../views/LivresAuteurs.vue';

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
