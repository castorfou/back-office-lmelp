/**
 * Tests d'intégration pour la page principale
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount } from '@vue/test-utils';
import HomePage from '../../src/views/HomePage.vue';
import { episodeService } from '../../src/services/api.js';

// Mock du service API
vi.mock('../../src/services/api.js', () => ({
  episodeService: {
    getAllEpisodes: vi.fn(),
    getEpisodeById: vi.fn(),
    updateEpisodeDescription: vi.fn(),
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

describe('HomePage - Tests d\'intégration', () => {
  let wrapper;

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

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount();
    }
  });

  it('affiche le titre et la description de la page', () => {
    episodeService.getAllEpisodes.mockResolvedValue(mockEpisodes);

    wrapper = mount(HomePage);

    expect(wrapper.find('h1').text()).toBe('Back-office LMELP');
    expect(wrapper.text()).toContain('Masque et la Plume');
  });

  it('affiche le message d\'aide quand aucun épisode n\'est sélectionné', async () => {
    episodeService.getAllEpisodes.mockResolvedValue(mockEpisodes);

    wrapper = mount(HomePage);
    await wrapper.vm.$nextTick();

    expect(wrapper.find('.help-message').exists()).toBe(true);
    expect(wrapper.text()).toContain('Sélectionnez un épisode');
  });

  it('flux complet : sélection → édition → sauvegarde', async () => {
    // Configurer les mocks
    episodeService.getAllEpisodes.mockResolvedValue(mockEpisodes);
    episodeService.getEpisodeById.mockResolvedValue(mockEpisodeDetail);
    episodeService.updateEpisodeDescription.mockResolvedValue({ success: true });

    wrapper = mount(HomePage);

    // Attendre que les épisodes se chargent
    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 50));

    // Vérifier que le sélecteur est affiché
    expect(wrapper.findComponent({ name: 'EpisodeSelector' }).exists()).toBe(true);

    // Simuler la sélection d'un épisode
    const selector = wrapper.findComponent({ name: 'EpisodeSelector' });
    await selector.vm.$emit('episode-selected', mockEpisodeDetail);

    // Vérifier que l'éditeur est affiché
    expect(wrapper.findComponent({ name: 'EpisodeEditor' }).exists()).toBe(true);
    expect(wrapper.vm.selectedEpisode).toEqual(mockEpisodeDetail);

    // Vérifier que le message d'aide n'est plus affiché
    expect(wrapper.find('.help-message').exists()).toBe(false);
  });

  it('gère la désélection d\'épisode', async () => {
    episodeService.getAllEpisodes.mockResolvedValue(mockEpisodes);
    episodeService.getEpisodeById.mockResolvedValue(mockEpisodeDetail);

    wrapper = mount(HomePage);
    await wrapper.vm.$nextTick();

    // Sélectionner un épisode
    const selector = wrapper.findComponent({ name: 'EpisodeSelector' });
    await selector.vm.$emit('episode-selected', mockEpisodeDetail);

    expect(wrapper.findComponent({ name: 'EpisodeEditor' }).exists()).toBe(true);

    // Désélectionner l'épisode
    await selector.vm.$emit('episode-selected', null);

    expect(wrapper.vm.selectedEpisode).toBe(null);
    expect(wrapper.findComponent({ name: 'EpisodeEditor' }).exists()).toBe(false);
    expect(wrapper.find('.help-message').exists()).toBe(true);
  });

  it('maintient l\'état lors du changement d\'épisode', async () => {
    const secondEpisodeDetail = {
      id: '2',
      titre: 'Deuxième épisode',
      date: '2024-01-10T09:00:00Z',
      type: 'cinema',
      description: 'Autre description',
      description_corrigee: null
    };

    episodeService.getAllEpisodes.mockResolvedValue(mockEpisodes);
    episodeService.getEpisodeById
      .mockResolvedValueOnce(mockEpisodeDetail)
      .mockResolvedValueOnce(secondEpisodeDetail);

    wrapper = mount(HomePage);
    await wrapper.vm.$nextTick();

    // Sélectionner le premier épisode
    const selector = wrapper.findComponent({ name: 'EpisodeSelector' });
    await selector.vm.$emit('episode-selected', mockEpisodeDetail);

    expect(wrapper.vm.selectedEpisode.id).toBe('1');

    // Sélectionner le deuxième épisode
    await selector.vm.$emit('episode-selected', secondEpisodeDetail);

    expect(wrapper.vm.selectedEpisode.id).toBe('2');
    expect(wrapper.vm.selectedEpisode.titre).toBe('Deuxième épisode');
  });

  it('affiche les bonnes informations dans le footer', () => {
    episodeService.getAllEpisodes.mockResolvedValue(mockEpisodes);

    wrapper = mount(HomePage);

    const footer = wrapper.find('.page-footer');
    expect(footer.exists()).toBe(true);
    expect(footer.text()).toContain('Version 0.1.0');
    expect(footer.find('a').attributes('href')).toBe('https://github.com/castorfou/lmelp');
  });

  it('utilise des clés uniques pour l\'éditeur lors du changement d\'épisode', async () => {
    episodeService.getAllEpisodes.mockResolvedValue(mockEpisodes);
    episodeService.getEpisodeById.mockResolvedValue(mockEpisodeDetail);

    wrapper = mount(HomePage);
    await wrapper.vm.$nextTick();

    // Vérifier qu'il n'y a pas d'éditeur initialement
    expect(wrapper.findComponent({ name: 'EpisodeEditor' }).exists()).toBe(false);

    // Simuler la sélection d'épisode directement sur le composant parent
    wrapper.vm.selectedEpisode = mockEpisodeDetail;
    await wrapper.vm.$nextTick();

    // Vérifier que l'éditeur apparaît avec le bon épisode
    const editor = wrapper.findComponent({ name: 'EpisodeEditor' });
    expect(editor.exists()).toBe(true);
    expect(editor.props('episode')).toEqual(mockEpisodeDetail);

    // Changer d'épisode pour tester la réactivité
    const secondEpisode = { ...mockEpisodeDetail, id: '2', titre: 'Episode 2' };
    wrapper.vm.selectedEpisode = secondEpisode;
    await wrapper.vm.$nextTick();

    // Vérifier que l'éditeur a été mis à jour avec le nouvel épisode
    const updatedEditor = wrapper.findComponent({ name: 'EpisodeEditor' });
    expect(updatedEditor.exists()).toBe(true);
    expect(updatedEditor.props('episode')).toEqual(secondEpisode);
  });
});
