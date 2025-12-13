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
    maskedEpisodes: 5,
    episodesWithCorrectedTitles: 37,
    episodesWithCorrectedDescriptions: 45,
    criticalReviews: 28,
    lastUpdateDate: '2025-09-06T10:30:00Z'
  };

  const mockCollectionsStatistics = {
    episodes_non_traites: 5,
    couples_en_base: 42,
    couples_suggested_pas_en_base: 12,
    couples_not_found_pas_en_base: 8,
    // Issue #128: Nouvelles métriques
    episodes_without_avis_critiques: 117,
    avis_critiques_without_analysis: 0,
    last_episode_date: '2024-12-10T20:00:00',
    books_without_url_babelio: 5,
    authors_without_url_babelio: 3
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

  // Tests obsolètes supprimés - Issue #128 a retiré ces statistiques:
  // - Épisodes total (142)
  // - Avis critiques total (28)
  // - Épisodes masqués (5)

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

  // Tests obsolètes supprimés - Issue #128:
  // - Test "gère les erreurs de chargement des statistiques" cherchait '142'
  // - Test "affiche un état de chargement" cherchait '142'

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

    // Vérifier que les valeurs des collections sont affichées (Issue #128)
    expect(wrapper.text()).toContain('12'); // couples_suggested_pas_en_base
    expect(wrapper.text()).toContain('8');  // couples_not_found_pas_en_base
    expect(wrapper.text()).toContain('117'); // episodes_without_avis_critiques
    expect(wrapper.text()).toContain('0');   // avis_critiques_without_analysis
  });

  it('affiche les libellés des statistiques des collections (Issue #128)', async () => {
    statisticsService.getStatistics.mockResolvedValue(mockStatistics);
    livresAuteursService.getCollectionsStatistics.mockResolvedValue(mockCollectionsStatistics);

    wrapper = mount(Dashboard, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 50));

    // Vérifier que les nouveaux libellés Issue #128 sont présents
    expect(wrapper.text()).toMatch(/livres.*suggérés/i);
    expect(wrapper.text()).toMatch(/livres.*non.*trouvés/i);
    expect(wrapper.text()).toMatch(/épisodes.*sans.*avis.*critiques/i);
    expect(wrapper.text()).toMatch(/avis.*critiques.*sans.*analyse/i);
    expect(wrapper.text()).toMatch(/livres.*sans.*lien.*babelio/i);
    expect(wrapper.text()).toMatch(/auteurs.*sans.*lien.*babelio/i);
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

    // Vérifier que les données sont maintenant affichées (Issue #128)
    expect(wrapper.text()).toContain('117'); // episodes_without_avis_critiques
  });

  // ========== TESTS TDD POUR ISSUE #128 - NOUVELLES MÉTRIQUES ==========

  it('affiche "Avis critiques sans analyse" (Issue #128)', async () => {
    statisticsService.getStatistics.mockResolvedValue(mockStatistics);
    livresAuteursService.getCollectionsStatistics.mockResolvedValue(mockCollectionsStatistics);

    wrapper = mount(Dashboard, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 50));

    // Test TDD: "Avis critiques sans analyse" doit être présent
    expect(wrapper.text()).toMatch(/avis.*critiques.*sans.*analyse/i);

    // Test TDD: "Livres vérifiés" NE DOIT PAS être présent
    expect(wrapper.text()).not.toMatch(/livres.*vérifiés/i);
  });

  it('affiche "Épisodes sans avis critiques" (Issue #128)', async () => {
    statisticsService.getStatistics.mockResolvedValue(mockStatistics);
    livresAuteursService.getCollectionsStatistics.mockResolvedValue(mockCollectionsStatistics);

    wrapper = mount(Dashboard, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 50));

    // Test TDD: "Épisodes sans avis critiques" doit être présent avec valeur 117
    expect(wrapper.text()).toMatch(/épisodes.*sans.*avis.*critiques/i);
    expect(wrapper.text()).toContain('117');
  });

  it('gère l\'absence de nouvelles métriques Issue #128 dans la réponse API', async () => {
    const incompleteStats = {
      episodes_non_traites: 5,
      couples_en_base: 42,
      couples_suggested_pas_en_base: 12,
      couples_not_found_pas_en_base: 8
      // Nouvelles métriques Issue #128 manquantes volontairement
    };

    statisticsService.getStatistics.mockResolvedValue(mockStatistics);
    livresAuteursService.getCollectionsStatistics.mockResolvedValue(incompleteStats);

    wrapper = mount(Dashboard, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 50));

    // Test TDD: Doit afficher '...' quand les nouvelles métriques sont absentes
    const text = wrapper.text();
    expect(text).toMatch(/avis.*critiques.*sans.*analyse/i);
    expect(text).toMatch(/épisodes.*sans.*avis.*critiques/i);

    // Rechercher les cartes et vérifier qu'elles affichent '...'
    const statCards = wrapper.findAll('.stat-card');
    let foundAvisCritiquesCard = false;
    let foundEpisodesCard = false;

    for (let card of statCards) {
      const cardText = card.text();
      if (cardText.includes('Avis critiques sans analyse')) {
        expect(cardText).toContain('...');
        foundAvisCritiquesCard = true;
      }
      if (cardText.includes('Épisodes sans avis critiques')) {
        expect(cardText).toContain('...');
        foundEpisodesCard = true;
      }
    }

    expect(foundAvisCritiquesCard).toBe(true);
    expect(foundEpisodesCard).toBe(true);
  });
});
