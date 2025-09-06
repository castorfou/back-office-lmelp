/**
 * Configuration du routeur Vue pour l'application
 */

import { createRouter, createWebHistory } from 'vue-router';
import Dashboard from '../views/Dashboard.vue';
import EpisodePage from '../views/EpisodePage.vue';

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
  }
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

// Mettre à jour le titre de la page lors de la navigation
router.afterEach((to) => {
  document.title = to.meta.title || 'Back-office LMELP';
});

export default router;
