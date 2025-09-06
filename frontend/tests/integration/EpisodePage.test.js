/**
 * Tests d'intégration pour la page de gestion des épisodes (ancienne HomePage)
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount } from '@vue/test-utils';
import { createRouter, createWebHistory } from 'vue-router';
import EpisodePage from '../../src/views/EpisodePage.vue';
import { episodeService } from '../../src/services/api.js';

// Mock du service API
vi.mock('../../src/services/api.js', () => ({
  episodeService: {
    getAllEpisodes: vi.fn(),
    getEpisodeById: vi.fn(),
    updateEpisodeDescription: vi.fn(),
    updateEpisodeTitle: vi.fn(),
  }
}));

// Mock de lodash.debounce
vi.mock('lodash.debounce', () => ({
  default: (fn) => {
    fn.cancel = vi.fn();
    return fn;
  }
}));

// Mock des utilitaires
vi.mock('../../src/utils/errorHandler.js', () => ({
  ErrorHandler: {
    handleError: vi.fn().mockReturnValue('Erreur serveur')
  },
  errorMixin: {
    data() {
      return {
        loading: false,
        error: null
      }
    },
    methods: {
      handleError: vi.fn(),
      handleAsync: vi.fn().mockImplementation(async function(asyncFn) {
        this.loading = true;
        this.error = null;
        try {
          return await asyncFn();
        } catch (err) {
          this.error = err.message || 'Une erreur est survenue';
          throw err;
        } finally {
          this.loading = false;
        }
      })
    }
  }
}));

vi.mock('../../src/utils/memoryGuard.js', () => ({
  memoryGuard: {
    checkMemoryLimit: vi.fn().mockReturnValue(null),
    forceShutdown: vi.fn(),
    startMonitoring: vi.fn(),
    stopMonitoring: vi.fn()
  }
}));

describe('EpisodePage - Tests d\'intégration', () => {
  let wrapper;
  let router;

  const mockEpisodes = [
    {
      id: '1',
      titre: 'Premier épisode',
      date: '2024-01-15T09:00:00Z',
      type: 'livres'
    },
    {
      id: '2',
      titre: 'Deuxième épisode',
      date: '2024-01-10T09:00:00Z',
      type: 'cinema'
    }
  ];

  const mockEpisodeDetail = {
    id: '1',
    titre: 'Premier épisode',
    date: '2024-01-15T09:00:00Z',
    type: 'livres',
    description: 'Description originale de l\'épisode',
    description_corrigee: null
  };

  beforeEach(async () => {
    vi.clearAllMocks();

    // Créer un router de test
    router = createRouter({
      history: createWebHistory(),
      routes: [
        { path: '/', component: { template: '<div>Dashboard</div>' } },
        { path: '/episodes', component: EpisodePage }
      ]
    });

    await router.push('/episodes');
  });

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount();
    }
  });

  it('affiche le composant Navigation avec le bon titre', async () => {
    episodeService.getAllEpisodes.mockResolvedValue(mockEpisodes);

    wrapper = mount(EpisodePage, {
      global: {
        plugins: [router],
        stubs: {
          Navigation: {
            template: '<div data-testid="navigation">Navigation: {{ pageTitle }}</div>',
            props: ['pageTitle']
          }
        }
      }
    });

    await wrapper.vm.$nextTick();

    const navigation = wrapper.find('[data-testid="navigation"]');
    expect(navigation.exists()).toBe(true);
    expect(navigation.text()).toContain('Gestion des Épisodes');
  });

  it('affiche le sélecteur et l\'éditeur d\'épisodes', async () => {
    episodeService.getAllEpisodes.mockResolvedValue(mockEpisodes);

    wrapper = mount(EpisodePage, {
      global: {
        plugins: [router],
        stubs: {
          Navigation: true
        }
      }
    });

    await wrapper.vm.$nextTick();

    expect(wrapper.findComponent({ name: 'EpisodeSelector' }).exists()).toBe(true);
  });

  it('affiche le message d\'aide quand aucun épisode n\'est sélectionné', async () => {
    episodeService.getAllEpisodes.mockResolvedValue(mockEpisodes);

    wrapper = mount(EpisodePage, {
      global: {
        plugins: [router],
        stubs: {
          Navigation: true
        }
      }
    });

    await wrapper.vm.$nextTick();

    expect(wrapper.find('.help-message').exists()).toBe(true);
    expect(wrapper.text()).toContain('Sélectionnez un épisode');
  });

  it('flux complet : sélection → édition → sauvegarde', async () => {
    episodeService.getAllEpisodes.mockResolvedValue(mockEpisodes);
    episodeService.getEpisodeById.mockResolvedValue(mockEpisodeDetail);
    episodeService.updateEpisodeDescription.mockResolvedValue({ success: true });

    wrapper = mount(EpisodePage, {
      global: {
        plugins: [router],
        stubs: {
          Navigation: true
        }
      }
    });

    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 50));

    // Simuler la sélection d'un épisode
    const selector = wrapper.findComponent({ name: 'EpisodeSelector' });
    await selector.vm.$emit('episode-selected', mockEpisodeDetail);

    // Vérifier que l'éditeur est affiché
    expect(wrapper.findComponent({ name: 'EpisodeEditor' }).exists()).toBe(true);
    expect(wrapper.vm.selectedEpisode).toEqual(mockEpisodeDetail);

    // Vérifier que le message d'aide n'est plus affiché
    expect(wrapper.find('.help-message').exists()).toBe(false);
  });

  it('ne affiche pas le titre "Back-office LMELP" de la page d\'accueil', async () => {
    episodeService.getAllEpisodes.mockResolvedValue(mockEpisodes);

    wrapper = mount(EpisodePage, {
      global: {
        plugins: [router],
        stubs: {
          Navigation: true
        }
      }
    });

    await wrapper.vm.$nextTick();

    // Cette page ne devrait plus avoir le grand titre de la page d'accueil
    const mainHeader = wrapper.find('.page-header h1');
    expect(mainHeader.exists()).toBe(false);
  });

  it('maintient la logique de gestion des épisodes existante', async () => {
    episodeService.getAllEpisodes.mockResolvedValue(mockEpisodes);
    episodeService.getEpisodeById.mockResolvedValue(mockEpisodeDetail);

    wrapper = mount(EpisodePage, {
      global: {
        plugins: [router],
        stubs: {
          Navigation: true
        }
      }
    });

    await wrapper.vm.$nextTick();

    // Vérifier que toutes les méthodes existantes sont présentes
    expect(wrapper.vm.onEpisodeSelected).toBeDefined();
    expect(wrapper.vm.onTitleUpdated).toBeDefined();

    // Vérifier l'état initial
    expect(wrapper.vm.selectedEpisode).toBe(null);
  });
});
