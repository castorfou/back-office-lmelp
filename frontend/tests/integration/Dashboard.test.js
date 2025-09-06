/**
 * Tests d'intégration pour la page d'accueil (Dashboard)
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount } from '@vue/test-utils';
import { createRouter, createWebHistory } from 'vue-router';
import Dashboard from '../../src/views/Dashboard.vue';
import { episodeService, statisticsService } from '../../src/services/api.js';

// Mock du service API
vi.mock('../../src/services/api.js', () => ({
  episodeService: {
    getAllEpisodes: vi.fn(),
    getEpisodeById: vi.fn(),
    updateEpisodeDescription: vi.fn(),
    updateEpisodeTitle: vi.fn(),
  },
  statisticsService: {
    getStatistics: vi.fn(),
  }
}));

// Mock des utilitaires
vi.mock('../../src/utils/memoryGuard.js', () => ({
  memoryGuard: {
    checkMemoryLimit: vi.fn().mockReturnValue(null),
    forceShutdown: vi.fn(),
    startMonitoring: vi.fn(),
    stopMonitoring: vi.fn()
  }
}));

describe('Dashboard - Tests d\'intégration', () => {
  let wrapper;
  let router;

  const mockStatistics = {
    totalEpisodes: 142,
    episodesWithCorrectedTitles: 37,
    episodesWithCorrectedDescriptions: 45,
    lastUpdateDate: '2025-09-06T10:30:00Z'
  };

  beforeEach(async () => {
    vi.clearAllMocks();

    // Créer un router de test
    router = createRouter({
      history: createWebHistory(),
      routes: [
        { path: '/', component: Dashboard },
        { path: '/episodes', component: { template: '<div>Episodes Page</div>' } }
      ]
    });

    // Naviguer vers la page d'accueil
    await router.push('/');
  });

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount();
    }
  });

  it('affiche le titre et la description de la page d\'accueil', async () => {
    statisticsService.getStatistics.mockResolvedValue(mockStatistics);

    wrapper = mount(Dashboard, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();

    expect(wrapper.find('h1').text()).toBe('Back-office LMELP');
    expect(wrapper.text()).toContain('Gestion et correction des épisodes du Masque et la Plume');
  });

  it('affiche le bandeau d\'en-tête avec le bon style', async () => {
    statisticsService.getStatistics.mockResolvedValue(mockStatistics);

    wrapper = mount(Dashboard, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();

    const header = wrapper.find('.page-header');
    expect(header.exists()).toBe(true);
    expect(header.find('h1').text()).toBe('Back-office LMELP');
  });

  it('affiche les statistiques des épisodes', async () => {
    statisticsService.getStatistics.mockResolvedValue(mockStatistics);

    wrapper = mount(Dashboard, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 50));

    expect(wrapper.text()).toContain('142'); // Total episodes
    expect(wrapper.text()).toContain('épisode'); // Should contain the word episodes somewhere
  });

  it('affiche la fonction Episode - Modification Titre/Description comme cliquable', async () => {
    statisticsService.getStatistics.mockResolvedValue(mockStatistics);

    wrapper = mount(Dashboard, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();

    const episodeFunction = wrapper.find('[data-testid="function-episode-edit"]');
    expect(episodeFunction.exists()).toBe(true);
    expect(episodeFunction.text()).toContain('Episode - Modification Titre/Description');

    // Vérifier que c'est cliquable
    expect(episodeFunction.element.tagName.toLowerCase()).toMatch(/^(a|button|div)$/);
  });

  it('navigue vers la page d\'épisodes lors du clic sur la fonction', async () => {
    statisticsService.getStatistics.mockResolvedValue(mockStatistics);

    const push = vi.spyOn(router, 'push');

    wrapper = mount(Dashboard, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();

    const episodeFunction = wrapper.find('[data-testid="function-episode-edit"]');
    await episodeFunction.trigger('click');

    expect(push).toHaveBeenCalledWith('/episodes');
  });

  it('est responsive sur petits écrans', async () => {
    statisticsService.getStatistics.mockResolvedValue(mockStatistics);

    wrapper = mount(Dashboard, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();

    // Vérifier qu'il y a des classes CSS pour la responsivité
    const dashboard = wrapper.find('.dashboard');
    expect(dashboard.exists()).toBe(true);

    // Vérifier que les styles responsive existent (au moins une règle @media dans le style)
    const style = wrapper.find('style');
    if (style.exists()) {
      const styleText = style.element.textContent;
      expect(styleText).toMatch(/@media.*max-width.*768px/);
    }
  });

  it('gère les erreurs de chargement des statistiques', async () => {
    statisticsService.getStatistics.mockRejectedValue(new Error('Erreur réseau'));

    wrapper = mount(Dashboard, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 50));

    // Vérifier qu'un message d'erreur ou un fallback est affiché
    expect(wrapper.text()).toContain('--'); // Placeholder for failed stats
  });

  it('affiche un état de chargement pendant la récupération des statistiques', async () => {
    let resolveStats;
    const statsPromise = new Promise((resolve) => {
      resolveStats = resolve;
    });
    statisticsService.getStatistics.mockReturnValue(statsPromise);

    wrapper = mount(Dashboard, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();

    // Vérifier qu'un état de chargement est affiché
    expect(wrapper.text()).toContain('...'); // Loading indicator

    // Résoudre les statistiques
    resolveStats(mockStatistics);
    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 50));

    // Vérifier que les données sont maintenant affichées
    expect(wrapper.text()).toContain('142');
  });
});
