import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount } from '@vue/test-utils';
import { createRouter, createMemoryHistory } from 'vue-router';
import GenerationAvisCritiques from '../GenerationAvisCritiques.vue';
import * as api from '../../services/api.js';

vi.mock('../../services/api.js', () => ({
  avisCritiquesService: {
    getEpisodesSansAvis: vi.fn(),
    getEpisodesWithSummaries: vi.fn(),
    getSummaryByEpisode: vi.fn(),
    generateAvisCritiques: vi.fn(),
    saveAvisCritiques: vi.fn()
  },
  episodeService: {
    fetchEpisodePageUrl: vi.fn()
  }
}));

describe('GenerationAvisCritiques.vue', () => {
  let wrapper;
  let router;

  beforeEach(async () => {
    vi.clearAllMocks();

    // Mock par défaut pour episodeService.fetchEpisodePageUrl
    api.episodeService.fetchEpisodePageUrl.mockResolvedValue({});

    // Mock par défaut pour getEpisodesWithSummaries
    api.avisCritiquesService.getEpisodesWithSummaries.mockResolvedValue([]);

    router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/generation-avis-critiques', component: GenerationAvisCritiques }
      ]
    });

    await router.push('/generation-avis-critiques');
  });

  it('loads episodes sans avis on mount', async () => {
    const mockEpisodesWithout = [
      {
        id: '123',
        titre: 'Episode Test',
        date: '2025-01-15T00:00:00',
        transcription_length: 5000,
        has_episode_page_url: true,
        has_summary: false
      }
    ];

    api.avisCritiquesService.getEpisodesSansAvis.mockResolvedValue(mockEpisodesWithout);
    api.avisCritiquesService.getEpisodesWithSummaries.mockResolvedValue([]);

    wrapper = mount(GenerationAvisCritiques, {
      global: { plugins: [router] }
    });

    await new Promise(resolve => setTimeout(resolve, 50));
    await wrapper.vm.$nextTick();

    expect(api.avisCritiquesService.getEpisodesSansAvis).toHaveBeenCalled();
    expect(api.avisCritiquesService.getEpisodesWithSummaries).toHaveBeenCalled();
    expect(wrapper.vm.allEpisodes.length).toBe(1);
  });

  it('displays loading state while fetching episodes', async () => {
    api.avisCritiquesService.getEpisodesSansAvis.mockImplementation(
      () => new Promise(resolve => setTimeout(() => resolve([]), 100))
    );
    api.avisCritiquesService.getEpisodesWithSummaries.mockResolvedValue([]);

    wrapper = mount(GenerationAvisCritiques, {
      global: { plugins: [router] }
    });

    await wrapper.vm.$nextTick();
    expect(wrapper.text()).toContain('Chargement');

    await new Promise(resolve => setTimeout(resolve, 150));
    await wrapper.vm.$nextTick();
  });

  it('displays error message on fetch failure', async () => {
    api.avisCritiquesService.getEpisodesSansAvis.mockRejectedValue(new Error('Erreur réseau'));
    api.avisCritiquesService.getEpisodesWithSummaries.mockResolvedValue([]);

    wrapper = mount(GenerationAvisCritiques, {
      global: { plugins: [router] }
    });

    await new Promise(resolve => setTimeout(resolve, 50));
    await wrapper.vm.$nextTick();

    expect(wrapper.text()).toContain('Erreur');
  });

  it('displays episode dropdown with options', async () => {
    const mockEpisodes = [
      {
        id: '123',
        titre: 'Episode Test 1',
        date: '2025-01-15T00:00:00',
        transcription_length: 5000,
        has_episode_page_url: true,
        has_summary: false
      },
      {
        id: '456',
        titre: 'Episode Test 2',
        date: '2025-01-10T00:00:00',
        transcription_length: 3000,
        has_episode_page_url: false,
        has_summary: true
      }
    ];

    api.avisCritiquesService.getEpisodesSansAvis.mockResolvedValue([mockEpisodes[0]]);
    api.avisCritiquesService.getEpisodesWithSummaries.mockResolvedValue([mockEpisodes[1]]);

    wrapper = mount(GenerationAvisCritiques, {
      global: { plugins: [router] }
    });

    await new Promise(resolve => setTimeout(resolve, 50));
    await wrapper.vm.$nextTick();

    const dropdown = wrapper.find('.episode-dropdown');
    expect(dropdown.exists()).toBe(true);

    // Ouvrir le dropdown
    const dropdownInput = dropdown.find('.dropdown-input');
    await dropdownInput.trigger('click');
    await wrapper.vm.$nextTick();

    // Vérifier que la liste est visible
    const dropdownList = dropdown.find('.dropdown-list');
    expect(dropdownList.isVisible()).toBe(true);

    // Vérifier le nombre d'options (2 épisodes)
    const options = dropdown.findAll('.dropdown-option');
    expect(options.length).toBe(2);
  });

  it('updates selectedEpisodeId when dropdown changes', async () => {
    const mockEpisodes = [
      {
        id: '123',
        titre: 'Episode Test',
        date: '2025-01-15T00:00:00',
        transcription_length: 5000,
        has_episode_page_url: true,
        has_summary: false
      }
    ];

    api.avisCritiquesService.getEpisodesSansAvis.mockResolvedValue(mockEpisodes);
    api.avisCritiquesService.getEpisodesWithSummaries.mockResolvedValue([]);

    wrapper = mount(GenerationAvisCritiques, {
      global: { plugins: [router] }
    });

    await new Promise(resolve => setTimeout(resolve, 50));
    await wrapper.vm.$nextTick();

    const dropdown = wrapper.find('.episode-dropdown');

    // Ouvrir le dropdown
    await dropdown.find('.dropdown-input').trigger('click');
    await wrapper.vm.$nextTick();

    // Cliquer sur l'option
    const option = dropdown.find('.dropdown-option');
    await option.trigger('click');
    await wrapper.vm.$nextTick();

    expect(wrapper.vm.selectedEpisodeId).toBe('123');
  });

  it('generates avis critiques and saves automatically on button click', async () => {
    const mockEpisodes = [
      {
        id: '123',
        titre: 'Episode Test',
        date: '2025-01-15T00:00:00',
        transcription_length: 5000,
        has_episode_page_url: true,
        has_summary: false
      }
    ];

    const validSummary = `# Résumé de l'émission

## 1. LIVRES DISCUTÉS

Liste des livres

## 2. COUPS DE CŒUR DES CRITIQUES

Les coups de coeur`;

    api.avisCritiquesService.getEpisodesSansAvis.mockResolvedValue(mockEpisodes);
    api.avisCritiquesService.getEpisodesWithSummaries.mockResolvedValue([]);
    api.avisCritiquesService.generateAvisCritiques.mockResolvedValue({
      summary: validSummary,
      summary_phase1: 'Phase 1 content',
      metadata: { corrections: {} }
    });
    api.avisCritiquesService.saveAvisCritiques.mockResolvedValue({ success: true });

    wrapper = mount(GenerationAvisCritiques, {
      global: { plugins: [router] }
    });

    await new Promise(resolve => setTimeout(resolve, 50));
    await wrapper.vm.$nextTick();

    // Sélectionner un épisode
    wrapper.vm.selectedEpisodeId = '123';
    await wrapper.vm.$nextTick();

    // Appeler directement la méthode generateAvisCritiques
    await wrapper.vm.generateAvisCritiques();

    expect(api.avisCritiquesService.generateAvisCritiques).toHaveBeenCalledWith({
      episode_id: '123'
    });

    // La sauvegarde devrait être automatique
    expect(api.avisCritiquesService.saveAvisCritiques).toHaveBeenCalledWith({
      episode_id: '123',
      summary: validSummary,
      summary_phase1: 'Phase 1 content',
      metadata: { corrections: {} }
    });
  });

  it('displays error message on generation failure', async () => {
    const mockEpisodes = [
      {
        id: '123',
        titre: 'Episode Test',
        date: '2025-01-15T00:00:00',
        transcription_length: 5000,
        has_episode_page_url: true,
        has_summary: false
      }
    ];

    api.avisCritiquesService.getEpisodesSansAvis.mockResolvedValue(mockEpisodes);
    api.avisCritiquesService.getEpisodesWithSummaries.mockResolvedValue([]);
    api.avisCritiquesService.generateAvisCritiques.mockRejectedValue(new Error('Erreur génération'));

    wrapper = mount(GenerationAvisCritiques, {
      global: { plugins: [router] }
    });

    await new Promise(resolve => setTimeout(resolve, 50));
    await wrapper.vm.$nextTick();

    wrapper.vm.selectedEpisodeId = '123';
    await wrapper.vm.$nextTick();

    // Appeler directement la méthode generateAvisCritiques
    await wrapper.vm.generateAvisCritiques();

    expect(wrapper.vm.error).toBeTruthy();
  });

  it('does NOT fetch URL if episode_page_url already exists', async () => {
    const mockEpisodes = [
      {
        id: '123',
        titre: 'Episode Test',
        date: '2025-01-15T00:00:00',
        transcription_length: 5000,
        has_episode_page_url: true,
        episode_page_url: 'https://radiofrance.fr/episode/123',
        has_summary: false
      }
    ];

    api.avisCritiquesService.getEpisodesSansAvis.mockResolvedValue(mockEpisodes);
    api.avisCritiquesService.getEpisodesWithSummaries.mockResolvedValue([]);
    api.avisCritiquesService.generateAvisCritiques.mockResolvedValue({
      summary: '# Test\n\n## Section\n\nContent',
      summary_phase1: 'Test',
      metadata: { corrections: {} }
    });
    api.avisCritiquesService.saveAvisCritiques.mockResolvedValue({ success: true });

    wrapper = mount(GenerationAvisCritiques, {
      global: { plugins: [router] }
    });

    await new Promise(resolve => setTimeout(resolve, 50));
    await wrapper.vm.$nextTick();

    wrapper.vm.selectedEpisodeId = '123';
    await wrapper.vm.$nextTick();

    const generateBtn = wrapper.find('.btn-primary');
    await generateBtn.trigger('click');
    await new Promise(resolve => setTimeout(resolve, 50));
    await wrapper.vm.$nextTick();

    // Vérifier que fetchEpisodePageUrl N'A PAS été appelé
    expect(api.episodeService.fetchEpisodePageUrl).not.toHaveBeenCalled();
  });

  it('launches fetch URL in parallel when URL is missing', async () => {
    const mockEpisodes = [
      {
        id: '123',
        titre: 'Episode Test',
        date: '2025-01-15T00:00:00',
        transcription_length: 5000,
        has_episode_page_url: false,
        has_summary: false
      }
    ];

    const validSummary = `# Résumé de l'émission

## 1. LIVRES DISCUTÉS

Liste des livres

## 2. COUPS DE CŒUR DES CRITIQUES

Les coups de coeur`;

    api.avisCritiquesService.getEpisodesSansAvis.mockResolvedValue(mockEpisodes);
    api.avisCritiquesService.getEpisodesWithSummaries.mockResolvedValue([]);
    api.episodeService.fetchEpisodePageUrl.mockResolvedValue({
      episode_page_url: 'https://radiofrance.fr/episode/123'
    });
    api.avisCritiquesService.generateAvisCritiques.mockResolvedValue({
      summary: validSummary,
      summary_phase1: 'Test',
      metadata: { corrections: {} }
    });
    api.avisCritiquesService.saveAvisCritiques.mockResolvedValue({ success: true });

    wrapper = mount(GenerationAvisCritiques, {
      global: { plugins: [router] }
    });

    await new Promise(resolve => setTimeout(resolve, 50));
    await wrapper.vm.$nextTick();

    wrapper.vm.selectedEpisodeId = '123';
    await wrapper.vm.$nextTick();

    // Appeler directement la méthode generateAvisCritiques
    await wrapper.vm.generateAvisCritiques();

    // Vérifier que fetchEpisodePageUrl A été appelé en parallèle
    expect(api.episodeService.fetchEpisodePageUrl).toHaveBeenCalledWith('123');
  });

  // Tests de validation (Issue #165)
  describe('Failed generation validation', () => {
    it('should NOT save when summary is empty', async () => {
      const mockEpisodes = [
        {
          id: '123',
          titre: 'Episode Test',
          date: '2025-01-15T00:00:00',
          transcription_length: 5000,
          has_episode_page_url: true,
          has_summary: false
        }
      ];

      api.avisCritiquesService.getEpisodesSansAvis.mockResolvedValue(mockEpisodes);
      api.avisCritiquesService.getEpisodesWithSummaries.mockResolvedValue([]);
      api.avisCritiquesService.generateAvisCritiques.mockResolvedValue({
        summary: '', // Empty summary
        summary_phase1: 'Phase 1',
        metadata: { corrections: {} }
      });

      wrapper = mount(GenerationAvisCritiques, {
        global: { plugins: [router] }
        });

      await new Promise(resolve => setTimeout(resolve, 50));
      await wrapper.vm.$nextTick();

      wrapper.vm.selectedEpisodeId = '123';
      await wrapper.vm.$nextTick();

      // Appeler directement la méthode generateAvisCritiques
      await wrapper.vm.generateAvisCritiques();

      // Vérifier qu'un message d'erreur est affiché
      expect(wrapper.vm.error).toBeTruthy();
      expect(wrapper.vm.error).toContain('vide');

      // Vérifier que saveAvisCritiques N'A PAS été appelé
      expect(api.avisCritiquesService.saveAvisCritiques).not.toHaveBeenCalled();

      // Vérifier que le badge n'a PAS changé
      const episode = wrapper.vm.allEpisodes.find(ep => ep.id === '123');
      expect(episode.has_summary).toBe(false);
    });

    it('should NOT save when summary is too long', async () => {
      const mockEpisodes = [
        {
          id: '123',
          titre: 'Episode Test',
          date: '2025-01-15T00:00:00',
          transcription_length: 5000,
          has_episode_page_url: true,
          has_summary: false
        }
      ];

      // Le seuil réel est 50000 caractères
      const tooLongSummary = '# Test\n\n' + 'x'.repeat(55000);

      api.avisCritiquesService.getEpisodesSansAvis.mockResolvedValue(mockEpisodes);
      api.avisCritiquesService.getEpisodesWithSummaries.mockResolvedValue([]);
      api.avisCritiquesService.generateAvisCritiques.mockResolvedValue({
        summary: tooLongSummary,
        summary_phase1: 'Phase 1',
        metadata: { corrections: {} }
      });

      wrapper = mount(GenerationAvisCritiques, {
        global: { plugins: [router] }
      });

      await new Promise(resolve => setTimeout(resolve, 50));
      await wrapper.vm.$nextTick();

      wrapper.vm.selectedEpisodeId = '123';
      await wrapper.vm.$nextTick();

      // Appeler directement la méthode generateAvisCritiques
      await wrapper.vm.generateAvisCritiques();

      // Vérifier qu'un message d'erreur est affiché
      expect(wrapper.vm.error).toBeTruthy();
      expect(wrapper.vm.error).toContain('trop long');

      // Vérifier que saveAvisCritiques N'A PAS été appelé
      expect(api.avisCritiquesService.saveAvisCritiques).not.toHaveBeenCalled();
    });

    it('should NOT save when summary lacks markdown structure', async () => {
      const mockEpisodes = [
        {
          id: '123',
          titre: 'Episode Test',
          date: '2025-01-15T00:00:00',
          transcription_length: 5000,
          has_episode_page_url: true,
          has_summary: false
        }
      ];

      // Manque "## 1. LIVRES DISCUTÉS" et "2. COUPS DE CŒUR DES CRITIQUES"
      const malformedSummary = '# Résumé\n\nJust some plain text without proper markdown structure';

      api.avisCritiquesService.getEpisodesSansAvis.mockResolvedValue(mockEpisodes);
      api.avisCritiquesService.getEpisodesWithSummaries.mockResolvedValue([]);
      api.avisCritiquesService.generateAvisCritiques.mockResolvedValue({
        summary: malformedSummary,
        summary_phase1: 'Phase 1',
        metadata: { corrections: {} }
      });

      wrapper = mount(GenerationAvisCritiques, {
        global: { plugins: [router] }
      });

      await new Promise(resolve => setTimeout(resolve, 50));
      await wrapper.vm.$nextTick();

      wrapper.vm.selectedEpisodeId = '123';
      await wrapper.vm.$nextTick();

      // Appeler directement la méthode generateAvisCritiques
      await wrapper.vm.generateAvisCritiques();

      // Vérifier qu'un message d'erreur est affiché
      expect(wrapper.vm.error).toBeTruthy();
      expect(wrapper.vm.error).toContain('Structure markdown manquante');

      // Vérifier que saveAvisCritiques N'A PAS été appelé
      expect(api.avisCritiquesService.saveAvisCritiques).not.toHaveBeenCalled();
    });

    it('should save and change badge when summary is valid', async () => {
      const mockEpisodes = [
        {
          id: '123',
          titre: 'Episode Test',
          date: '2025-01-15T00:00:00',
          transcription_length: 5000,
          has_episode_page_url: true,
          has_summary: false
        }
      ];

      // Summary valide avec les sections attendues
      const validSummary = `# Résumé de l'émission

## 1. LIVRES DISCUTÉS

Liste des livres

## 2. COUPS DE CŒUR DES CRITIQUES

Les coups de coeur`;

      api.avisCritiquesService.getEpisodesSansAvis.mockResolvedValue(mockEpisodes);
      api.avisCritiquesService.getEpisodesWithSummaries.mockResolvedValue([]);
      api.avisCritiquesService.generateAvisCritiques.mockResolvedValue({
        summary: validSummary,
        summary_phase1: 'Phase 1',
        metadata: { corrections: {} }
      });
      api.avisCritiquesService.saveAvisCritiques.mockResolvedValue({ success: true });

      wrapper = mount(GenerationAvisCritiques, {
        global: { plugins: [router] }
      });

      await new Promise(resolve => setTimeout(resolve, 50));
      await wrapper.vm.$nextTick();

      wrapper.vm.selectedEpisodeId = '123';
      await wrapper.vm.$nextTick();

      // Appeler directement la méthode generateAvisCritiques
      await wrapper.vm.generateAvisCritiques();

      // Vérifier que saveAvisCritiques A été appelé
      expect(api.avisCritiquesService.saveAvisCritiques).toHaveBeenCalledWith({
        episode_id: '123',
        summary: validSummary,
        summary_phase1: 'Phase 1',
        metadata: { corrections: {} }
      });

      // Vérifier que le badge a changé
      const episode = wrapper.vm.allEpisodes.find(ep => ep.id === '123');
      expect(episode.has_summary).toBe(true);
    });
  });
});
