/**
 * Tests d'intégration pour la page d'accueil (Dashboard)
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount } from '@vue/test-utils';
import { createRouter, createWebHistory } from 'vue-router';
import Dashboard from '../../src/views/Dashboard.vue';
import { episodeService, statisticsService, livresAuteursService } from '../../src/services/api.js';

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
  },
  livresAuteursService: {
    getCollectionsStatistics: vi.fn(),
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
    criticalReviews: 28,
    lastUpdateDate: '2025-09-06T10:30:00Z'
  };

  const mockCollectionsStatistics = {
    episodes_non_traites: 5,
    couples_en_base: 42,
    couples_verified_pas_en_base: 18,
    couples_suggested_pas_en_base: 12,
    couples_not_found_pas_en_base: 8
  };

  beforeEach(async () => {
    vi.clearAllMocks();

    // Setup default mocks
    statisticsService.getStatistics.mockResolvedValue(mockStatistics);
    livresAuteursService.getCollectionsStatistics.mockResolvedValue(mockCollectionsStatistics);

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
    expect(wrapper.text()).toContain('28'); // Critical reviews
    expect(wrapper.text()).toContain('épisode'); // Should contain the word episodes somewhere
  });

  it('affiche le nombre d\'avis critiques dans les statistiques', async () => {
    statisticsService.getStatistics.mockResolvedValue(mockStatistics);

    wrapper = mount(Dashboard, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 50));

    // Vérifier que la valeur des avis critiques est affichée
    expect(wrapper.text()).toContain('28'); // Critical reviews count
    // Vérifier que le libellé correspondant est présent
    expect(wrapper.text()).toMatch(/avis.*critique/i); // Should contain text related to critical reviews
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

  // ========== TESTS TDD POUR LES STATISTIQUES DES COLLECTIONS ==========

  it('appelle getCollectionsStatistics au montage du composant', async () => {
    statisticsService.getStatistics.mockResolvedValue(mockStatistics);
    livresAuteursService.getCollectionsStatistics.mockResolvedValue(mockCollectionsStatistics);

    wrapper = mount(Dashboard, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();
    // Attendre que les appels asynchrones se terminent
    await new Promise(resolve => setTimeout(resolve, 50));

    expect(livresAuteursService.getCollectionsStatistics).toHaveBeenCalledTimes(1);
  });

  it('affiche les statistiques des collections dans les cartes existantes', async () => {
    statisticsService.getStatistics.mockResolvedValue(mockStatistics);
    livresAuteursService.getCollectionsStatistics.mockResolvedValue(mockCollectionsStatistics);

    wrapper = mount(Dashboard, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 50));

    // Vérifier que les valeurs des collections sont affichées
    expect(wrapper.text()).toContain('42'); // couples_en_base
    expect(wrapper.text()).toContain('18'); // couples_verified_pas_en_base
    expect(wrapper.text()).toContain('12'); // couples_suggested_pas_en_base
    expect(wrapper.text()).toContain('8');  // couples_not_found_pas_en_base
  });

  it('affiche les libellés des statistiques des collections', async () => {
    statisticsService.getStatistics.mockResolvedValue(mockStatistics);
    livresAuteursService.getCollectionsStatistics.mockResolvedValue(mockCollectionsStatistics);

    wrapper = mount(Dashboard, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 50));

    // Vérifier que les libellés des collections sont présents
    expect(wrapper.text()).toMatch(/livres.*base/i);
    expect(wrapper.text()).toMatch(/livres.*vérifiés/i);
    expect(wrapper.text()).toMatch(/livres.*suggérés/i);
    expect(wrapper.text()).toMatch(/livres.*non.*trouvés/i);
  });

  it('gère les erreurs de chargement des statistiques des collections', async () => {
    statisticsService.getStatistics.mockResolvedValue(mockStatistics);
    livresAuteursService.getCollectionsStatistics.mockRejectedValue(new Error('Erreur réseau'));

    wrapper = mount(Dashboard, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 50));

    // Les statistiques principales doivent toujours s'afficher même si les collections échouent
    expect(wrapper.text()).toContain('142');
    // Les statistiques des collections doivent afficher des valeurs par défaut
    expect(wrapper.text()).toContain('--');
  });

  it('affiche des indicateurs de chargement pour les statistiques des collections', async () => {
    statisticsService.getStatistics.mockResolvedValue(mockStatistics);

    let resolveCollectionsStats;
    const collectionsStatsPromise = new Promise(resolve => {
      resolveCollectionsStats = resolve;
    });
    livresAuteursService.getCollectionsStatistics.mockReturnValue(collectionsStatsPromise);

    wrapper = mount(Dashboard, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();

    // Vérifier qu'un état de chargement est affiché pour les collections
    expect(wrapper.text()).toContain('...'); // Loading indicator

    // Résoudre les statistiques des collections
    resolveCollectionsStats(mockCollectionsStatistics);
    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 50));

    // Vérifier que les données sont maintenant affichées
    expect(wrapper.text()).toContain('42');
  });
});
