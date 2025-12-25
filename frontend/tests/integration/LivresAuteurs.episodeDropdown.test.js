/**
 * Tests pour l'amélioration de l'affichage de la liste déroulante des épisodes
 * Issue #164
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount } from '@vue/test-utils';
import { createRouter, createWebHistory } from 'vue-router';
import LivresAuteurs from '../../src/views/LivresAuteurs.vue';
import { livresAuteursService, episodeService } from '../../src/services/api.js';

// Mock du service API
vi.mock('../../src/services/api.js', () => ({
  livresAuteursService: {
    getLivresAuteurs: vi.fn(),
    getEpisodesWithReviews: vi.fn(),
    getCollectionsStatistics: vi.fn(),
    autoProcessVerifiedBooks: vi.fn(),
    autoProcessVerified: vi.fn(),
    getBooksByValidationStatus: vi.fn(),
    validateSuggestion: vi.fn(),
    addManualBook: vi.fn(),
    getAllAuthors: vi.fn(),
    getAllBooks: vi.fn(),
    setValidationResults: vi.fn(),
    deleteCacheByEpisode: vi.fn(),
  },
  episodeService: {
    getAllEpisodes: vi.fn(),
    getEpisodeById: vi.fn(),
    updateEpisodeDescription: vi.fn(),
    updateEpisodeTitle: vi.fn(),
    fetchEpisodePageUrl: vi.fn(),
  },
  statisticsService: {
    getStatistics: vi.fn(),
  },
  babelioService: {
    verifyAuthor: vi.fn(),
    verifyBook: vi.fn(),
    verifyPublisher: vi.fn(),
  },
  fuzzySearchService: {
    searchEpisode: vi.fn()
  }
}));

describe('LivresAuteurs - Episode Dropdown Improvements (Issue #164)', () => {
  let wrapper;
  let router;

  const mockEpisodesWithReviews = [
    {
      id: 'episode-1',
      date: '2024-01-15',
      titre: 'Épisode avec tous livres traités',
      titre_corrige: null,
      has_cached_books: true,
      has_incomplete_books: false,
      avis_critique_id: 'avis-1'
    },
    {
      id: 'episode-2',
      date: '2024-01-08',
      titre: 'Épisode non traité',
      titre_corrige: null,
      has_cached_books: false,
      has_incomplete_books: false,
      avis_critique_id: 'avis-2'
    },
    {
      id: 'episode-3',
      date: '2024-01-01',
      titre: 'Épisode avec problème',
      titre_corrige: null,
      has_cached_books: false,
      has_incomplete_books: true,
      avis_critique_id: 'avis-3'
    }
  ];

  beforeEach(async () => {
    vi.resetAllMocks();

    // Mock API responses
    livresAuteursService.getEpisodesWithReviews.mockResolvedValue(mockEpisodesWithReviews);
    livresAuteursService.getLivresAuteurs.mockResolvedValue([]);
    episodeService.getEpisodeById.mockResolvedValue({
      id: 'episode-1',
      titre: 'Épisode test',
      description: 'Description test'
    });
    episodeService.fetchEpisodePageUrl.mockResolvedValue({
      success: false
    });

    // Créer le router
    router = createRouter({
      history: createWebHistory(),
      routes: [
        { path: '/', component: LivresAuteurs },
        { path: '/livres-auteurs', component: LivresAuteurs }
      ]
    });

    // Monter le composant
    wrapper = mount(LivresAuteurs, {
      global: {
        plugins: [router]
      }
    });

    // Attendre que le composant soit monté et les épisodes chargés
    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 10));
  });

  describe('Indicateurs visuels avec pastilles de couleur', () => {
    it('should display green circle 🟢 for episodes with cached books (all treated)', () => {
      const formattedOption = wrapper.vm.formatEpisodeOption(mockEpisodesWithReviews[0]);
      expect(formattedOption).toContain('🟢');
      expect(formattedOption).not.toContain('* ');
    });

    it('should display gray circle ⚪ for untreated episodes', () => {
      const formattedOption = wrapper.vm.formatEpisodeOption(mockEpisodesWithReviews[1]);
      expect(formattedOption).toContain('⚪');
      expect(formattedOption).not.toContain('🟢');
      expect(formattedOption).not.toContain('🔴');
    });

    it('should display red circle 🔴 for episodes with incomplete books (problems)', () => {
      const formattedOption = wrapper.vm.formatEpisodeOption(mockEpisodesWithReviews[2]);
      expect(formattedOption).toContain('🔴');
      expect(formattedOption).not.toContain('⚠️');
    });
  });

  describe('Comportement de la liste déroulante custom', () => {
    it('should render EpisodeDropdown component', () => {
      const dropdown = wrapper.findComponent({ name: 'EpisodeDropdown' });
      expect(dropdown.exists()).toBe(true);
    });

    it('should pass episodes to EpisodeDropdown', () => {
      const dropdown = wrapper.findComponent({ name: 'EpisodeDropdown' });
      expect(dropdown.props('episodes')).toEqual(mockEpisodesWithReviews);
    });

    it('should bind selectedEpisodeId via v-model', async () => {
      wrapper.vm.selectedEpisodeId = 'episode-2';
      await wrapper.vm.$nextTick();
      const dropdown = wrapper.findComponent({ name: 'EpisodeDropdown' });
      expect(dropdown.props('modelValue')).toBe('episode-2');
    });
  });

  describe('Auto-centrage sur épisode sélectionné', () => {
    it('should emit update:modelValue when episode is selected', async () => {
      const dropdown = wrapper.findComponent({ name: 'EpisodeDropdown' });

      // Simuler la sélection d'un épisode
      await dropdown.vm.$emit('update:modelValue', 'episode-2');
      await wrapper.vm.$nextTick();

      // Vérifier que l'événement est bien émis
      expect(dropdown.emitted('update:modelValue')).toBeTruthy();
      expect(dropdown.emitted('update:modelValue')[0]).toEqual(['episode-2']);
    });
  });
});
