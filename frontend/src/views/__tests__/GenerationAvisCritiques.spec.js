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

    // Mock par défaut pour episodeService.fetchEpisodePageUrl (éviter erreurs dans tests existants)
    api.episodeService.fetchEpisodePageUrl.mockResolvedValue({});

    // Mock par défaut pour getEpisodesWithSummaries (éviter erreurs dans tests existants)
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
    const mockEpisodesWith = [];

    api.avisCritiquesService.getEpisodesSansAvis.mockResolvedValue(mockEpisodesWithout);
    api.avisCritiquesService.getEpisodesWithSummaries.mockResolvedValue([]);
    api.avisCritiquesService.getEpisodesWithSummaries.mockResolvedValue(mockEpisodesWith);

    wrapper = mount(GenerationAvisCritiques, {
      global: { plugins: [router] }
    });

    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 50));

    expect(api.avisCritiquesService.getEpisodesSansAvis).toHaveBeenCalledTimes(1);
    expect(api.avisCritiquesService.getEpisodesWithSummaries).toHaveBeenCalledTimes(1);
    expect(wrapper.vm.allEpisodes).toEqual(mockEpisodesWithout);
  });

  it('displays loading state while fetching episodes', async () => {
    let resolvePromise;
    const promise = new Promise(resolve => {
      resolvePromise = resolve;
    });

    api.avisCritiquesService.getEpisodesSansAvis.mockReturnValue(promise);

    wrapper = mount(GenerationAvisCritiques, {
      global: { plugins: [router] }
    });

    // Wait for component to be mounted and start loading
    await wrapper.vm.$nextTick();

    expect(wrapper.find('.loading').exists()).toBe(true);
    expect(wrapper.text()).toContain('Chargement des épisodes');

    // Resolve the promise to finish the test
    resolvePromise([]);
    await promise;
    await wrapper.vm.$nextTick();
  });

  it('displays error message on fetch failure', async () => {
    const errorMessage = 'Erreur réseau';
    api.avisCritiquesService.getEpisodesSansAvis.mockRejectedValue(new Error(errorMessage));

    wrapper = mount(GenerationAvisCritiques, {
      global: { plugins: [router] }
    });

    await new Promise(resolve => setTimeout(resolve, 50));
    await wrapper.vm.$nextTick();

    expect(wrapper.find('.alert-error').exists()).toBe(true);
    expect(wrapper.text()).toContain(errorMessage);
  });

  it('displays episode dropdown with options', async () => {
    const mockEpisodes = [
      {
        id: '123',
        titre: 'Episode Test 1',
        date: '2025-01-15T00:00:00',
        transcription_length: 5000,
        has_episode_page_url: true
      },
      {
        id: '456',
        titre: 'Episode Test 2',
        date: '2025-01-10T00:00:00',
        transcription_length: 3000,
        has_episode_page_url: false
      }
    ];

    api.avisCritiquesService.getEpisodesSansAvis.mockResolvedValue(mockEpisodes);
    api.avisCritiquesService.getEpisodesWithSummaries.mockResolvedValue([]);

    wrapper = mount(GenerationAvisCritiques, {
      global: { plugins: [router] }
    });

    await new Promise(resolve => setTimeout(resolve, 50));
    await wrapper.vm.$nextTick();

    const select = wrapper.find('.episode-dropdown');
    expect(select.exists()).toBe(true);

    const options = select.findAll('option');
    // 1 default option + 2 episodes
    expect(options.length).toBe(3);
    expect(options[0].text()).toContain('Sélectionner un épisode');
    expect(options[1].text()).toContain('Episode Test 1');
    expect(options[2].text()).toContain('Episode Test 2');
  });

  it('disables dropdown when no episodes available', async () => {
    api.avisCritiquesService.getEpisodesSansAvis.mockResolvedValue([]);
    api.avisCritiquesService.getEpisodesWithSummaries.mockResolvedValue([]);

    wrapper = mount(GenerationAvisCritiques, {
      global: { plugins: [router] }
    });

    await new Promise(resolve => setTimeout(resolve, 50));
    await wrapper.vm.$nextTick();

    const select = wrapper.find('.episode-dropdown');
    expect(select.attributes('disabled')).toBeDefined();
  });

  it('updates selectedEpisodeId when dropdown changes', async () => {
    const mockEpisodes = [
      {
        id: '123',
        titre: 'Episode Test',
        date: '2025-01-15T00:00:00',
        transcription_length: 5000,
        has_episode_page_url: true
      }
    ];

    api.avisCritiquesService.getEpisodesSansAvis.mockResolvedValue(mockEpisodes);
    api.avisCritiquesService.getEpisodesWithSummaries.mockResolvedValue([]);

    wrapper = mount(GenerationAvisCritiques, {
      global: { plugins: [router] }
    });

    await new Promise(resolve => setTimeout(resolve, 50));
    await wrapper.vm.$nextTick();

    const select = wrapper.find('.episode-dropdown');
    await select.setValue('123');

    expect(wrapper.vm.selectedEpisodeId).toBe('123');
  });

  it('formats date correctly in dropdown', async () => {
    const mockEpisodes = [
      {
        id: '123',
        titre: 'Episode Test',
        date: '2025-01-15T00:00:00',
        transcription_length: 5000,
        has_episode_page_url: true
      }
    ];

    api.avisCritiquesService.getEpisodesSansAvis.mockResolvedValue(mockEpisodes);
    api.avisCritiquesService.getEpisodesWithSummaries.mockResolvedValue([]);

    wrapper = mount(GenerationAvisCritiques, {
      global: { plugins: [router] }
    });

    await new Promise(resolve => setTimeout(resolve, 50));
    await wrapper.vm.$nextTick();

    const options = wrapper.findAll('option');
    expect(options[1].text()).toContain('15/01/2025');
  });

  it('generates avis critiques on button click', async () => {
    const mockEpisodes = [
      { id: '123', titre: 'Test', date: '2025-01-15', transcription_length: 5000, has_episode_page_url: true, episode_page_url: 'https://url' }
    ];
    const mockGenerationResult = {
      success: true,
      summary: '## 1. LIVRES DISCUTÉS...',
      summary_phase1: '## 1. LIVRES DISCUTÉS...',
      metadata: {},
      corrections_applied: [],
      warnings: []
    };

    api.avisCritiquesService.getEpisodesSansAvis.mockResolvedValue(mockEpisodes);
    api.avisCritiquesService.getEpisodesWithSummaries.mockResolvedValue([]);
    api.avisCritiquesService.generateAvisCritiques.mockResolvedValue(mockGenerationResult);

    wrapper = mount(GenerationAvisCritiques, {
      global: { plugins: [router] }
    });

    await new Promise(resolve => setTimeout(resolve, 50));
    await wrapper.vm.$nextTick();

    wrapper.vm.selectedEpisodeId = '123';
    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 50));

    const generateBtn = wrapper.find('button.btn-primary');
    expect(generateBtn.exists()).toBe(true);

    await generateBtn.trigger('click');
    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 100));

    expect(api.avisCritiquesService.generateAvisCritiques).toHaveBeenCalledWith({ episode_id: '123' });
    expect(wrapper.vm.generationResult).toEqual(mockGenerationResult);
  });

  it('disables generate button when no episode selected', async () => {
    const mockEpisodes = [
      { id: '123', titre: 'Test', date: '2025-01-15', transcription_length: 5000, has_episode_page_url: true, episode_page_url: 'https://url' }
    ];

    api.avisCritiquesService.getEpisodesSansAvis.mockResolvedValue(mockEpisodes);
    api.avisCritiquesService.getEpisodesWithSummaries.mockResolvedValue([]);

    wrapper = mount(GenerationAvisCritiques, {
      global: { plugins: [router] }
    });

    await new Promise(resolve => setTimeout(resolve, 50));
    await wrapper.vm.$nextTick();

    const generateBtn = wrapper.find('button.btn-primary');
    expect(generateBtn.attributes('disabled')).toBeDefined();
  });

  it('displays generating state while generation in progress', async () => {
    const mockEpisodes = [
      { id: '123', titre: 'Test', date: '2025-01-15', transcription_length: 5000, has_episode_page_url: true, episode_page_url: 'https://url' }
    ];

    let resolveGeneration;
    const generationPromise = new Promise(resolve => {
      resolveGeneration = resolve;
    });

    api.avisCritiquesService.getEpisodesSansAvis.mockResolvedValue(mockEpisodes);
    api.avisCritiquesService.getEpisodesWithSummaries.mockResolvedValue([]);
    api.avisCritiquesService.generateAvisCritiques.mockReturnValue(generationPromise);

    wrapper = mount(GenerationAvisCritiques, {
      global: { plugins: [router] }
    });

    await new Promise(resolve => setTimeout(resolve, 50));
    await wrapper.vm.$nextTick();

    wrapper.vm.selectedEpisodeId = '123';
    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 50));

    const generateBtn = wrapper.find('button.btn-primary');
    await generateBtn.trigger('click');
    await wrapper.vm.$nextTick();

    expect(wrapper.text()).toContain('Génération en cours');
    expect(wrapper.find('.progress').exists()).toBe(true);

    resolveGeneration({
      success: true,
      summary: '## 1. LIVRES',
      summary_phase1: '## 1. LIVRES',
      metadata: {},
      corrections_applied: [],
      warnings: []
    });
    await generationPromise;
    await wrapper.vm.$nextTick();
  });

  it('displays markdown preview after generation', async () => {
    const mockEpisodes = [
      { id: '123', titre: 'Test', date: '2025-01-15', transcription_length: 5000, has_episode_page_url: true, episode_page_url: 'https://url' }
    ];
    const mockGenerationResult = {
      success: true,
      summary: '## 1. LIVRES DISCUTÉS\n\nTest content',
      summary_phase1: '## 1. LIVRES DISCUTÉS\n\nTest content',
      metadata: {},
      corrections_applied: [],
      warnings: []
    };

    api.avisCritiquesService.getEpisodesSansAvis.mockResolvedValue(mockEpisodes);
    api.avisCritiquesService.getEpisodesWithSummaries.mockResolvedValue([]);
    api.avisCritiquesService.generateAvisCritiques.mockResolvedValue(mockGenerationResult);

    wrapper = mount(GenerationAvisCritiques, {
      global: { plugins: [router] }
    });

    await new Promise(resolve => setTimeout(resolve, 50));
    await wrapper.vm.$nextTick();

    wrapper.vm.selectedEpisodeId = '123';
    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 50));

    const generateBtn = wrapper.find('button.btn-primary');
    await generateBtn.trigger('click');
    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 100));

    expect(wrapper.find('.results').exists()).toBe(true);
    expect(wrapper.find('.markdown-preview').exists()).toBe(true);
  });

  it('displays error message on generation failure', async () => {
    const mockEpisodes = [
      { id: '123', titre: 'Test', date: '2025-01-15', transcription_length: 5000, has_episode_page_url: true, episode_page_url: 'https://url' }
    ];
    const errorMessage = 'Erreur génération LLM';

    api.avisCritiquesService.getEpisodesSansAvis.mockResolvedValue(mockEpisodes);
    api.avisCritiquesService.getEpisodesWithSummaries.mockResolvedValue([]);
    api.avisCritiquesService.generateAvisCritiques.mockRejectedValue(new Error(errorMessage));

    wrapper = mount(GenerationAvisCritiques, {
      global: { plugins: [router] }
    });

    await new Promise(resolve => setTimeout(resolve, 50));
    await wrapper.vm.$nextTick();

    wrapper.vm.selectedEpisodeId = '123';
    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 50));

    const generateBtn = wrapper.find('button.btn-primary');
    await generateBtn.trigger('click');
    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 100));

    expect(wrapper.find('.alert-error').exists()).toBe(true);
    expect(wrapper.text()).toContain(errorMessage);
  });

  it('displays comparison tabs after generation', async () => {
    const mockEpisodes = [
      { id: '123', titre: 'Test', date: '2025-01-15', transcription_length: 5000, has_episode_page_url: true, episode_page_url: 'https://url' }
    ];
    const mockGenerationResult = {
      success: true,
      summary: '## 1. LIVRES DISCUTÉS (Phase 2)',
      summary_phase1: '## 1. LIVRES DISCUTÉS (Phase 1)',
      metadata: {},
      corrections_applied: [{ field: 'critique', before: 'Patricia Martine', after: 'Patricia Martin' }],
      warnings: []
    };

    api.avisCritiquesService.getEpisodesSansAvis.mockResolvedValue(mockEpisodes);
    api.avisCritiquesService.getEpisodesWithSummaries.mockResolvedValue([]);
    api.avisCritiquesService.generateAvisCritiques.mockResolvedValue(mockGenerationResult);

    wrapper = mount(GenerationAvisCritiques, {
      global: { plugins: [router] }
    });

    await new Promise(resolve => setTimeout(resolve, 50));
    await wrapper.vm.$nextTick();

    wrapper.vm.selectedEpisodeId = '123';
    await wrapper.vm.generateAvisCritiques();
    await wrapper.vm.$nextTick();

    expect(wrapper.find('.tabs').exists()).toBe(true);
    expect(wrapper.findAll('.tabs button')).toHaveLength(3);
  });

  it('switches between tabs correctly', async () => {
    const mockEpisodes = [
      { id: '123', titre: 'Test', date: '2025-01-15', transcription_length: 5000, has_episode_page_url: true, episode_page_url: 'https://url' }
    ];
    const mockGenerationResult = {
      success: true,
      summary: '## 1. LIVRES DISCUTÉS (Phase 2)',
      summary_phase1: '## 1. LIVRES DISCUTÉS (Phase 1)',
      metadata: {},
      corrections_applied: [],
      warnings: []
    };

    api.avisCritiquesService.getEpisodesSansAvis.mockResolvedValue(mockEpisodes);
    api.avisCritiquesService.getEpisodesWithSummaries.mockResolvedValue([]);
    api.avisCritiquesService.generateAvisCritiques.mockResolvedValue(mockGenerationResult);

    wrapper = mount(GenerationAvisCritiques, {
      global: { plugins: [router] }
    });

    await new Promise(resolve => setTimeout(resolve, 50));
    await wrapper.vm.$nextTick();

    wrapper.vm.selectedEpisodeId = '123';
    await wrapper.vm.generateAvisCritiques();
    await wrapper.vm.$nextTick();

    // Default tab is phase2
    expect(wrapper.vm.activeTab).toBe('phase2');

    // Switch to phase1
    const tabs = wrapper.findAll('.tabs button');
    await tabs[0].trigger('click');
    expect(wrapper.vm.activeTab).toBe('phase1');

    // Switch to diff
    await tabs[2].trigger('click');
    expect(wrapper.vm.activeTab).toBe('diff');
  });

  it('displays corrections applied in phase2 tab', async () => {
    const mockEpisodes = [
      { id: '123', titre: 'Test', date: '2025-01-15', transcription_length: 5000, has_episode_page_url: true, episode_page_url: 'https://url' }
    ];
    const mockGenerationResult = {
      success: true,
      summary: '## 1. LIVRES DISCUTÉS',
      summary_phase1: '## 1. LIVRES DISCUTÉS',
      metadata: {},
      corrections_applied: [
        { field: 'critique', before: 'Patricia Martine', after: 'Patricia Martin' }
      ],
      warnings: []
    };

    api.avisCritiquesService.getEpisodesSansAvis.mockResolvedValue(mockEpisodes);
    api.avisCritiquesService.getEpisodesWithSummaries.mockResolvedValue([]);
    api.avisCritiquesService.generateAvisCritiques.mockResolvedValue(mockGenerationResult);

    wrapper = mount(GenerationAvisCritiques, {
      global: { plugins: [router] }
    });

    await new Promise(resolve => setTimeout(resolve, 50));
    await wrapper.vm.$nextTick();

    wrapper.vm.selectedEpisodeId = '123';
    await wrapper.vm.generateAvisCritiques();
    await wrapper.vm.$nextTick();

    expect(wrapper.find('.corrections').exists()).toBe(true);
    expect(wrapper.text()).toContain('Corrections appliquées');
    expect(wrapper.text()).toContain('Patricia Martine');
    expect(wrapper.text()).toContain('Patricia Martin');
  });

  it('displays warnings when present', async () => {
    const mockEpisodes = [
      { id: '123', titre: 'Test', date: '2025-01-15', transcription_length: 5000, has_episode_page_url: true, episode_page_url: 'https://url' }
    ];
    const mockGenerationResult = {
      success: true,
      summary: '## 1. LIVRES DISCUTÉS',
      summary_phase1: '## 1. LIVRES DISCUTÉS',
      metadata: {},
      corrections_applied: [],
      warnings: ['Pas d\'URL RadioFrance, Phase 2 skippée']
    };

    api.avisCritiquesService.getEpisodesSansAvis.mockResolvedValue(mockEpisodes);
    api.avisCritiquesService.getEpisodesWithSummaries.mockResolvedValue([]);
    api.avisCritiquesService.generateAvisCritiques.mockResolvedValue(mockGenerationResult);

    wrapper = mount(GenerationAvisCritiques, {
      global: { plugins: [router] }
    });

    await new Promise(resolve => setTimeout(resolve, 50));
    await wrapper.vm.$nextTick();

    wrapper.vm.selectedEpisodeId = '123';
    await wrapper.vm.generateAvisCritiques();
    await wrapper.vm.$nextTick();

    expect(wrapper.find('.warnings').exists()).toBe(true);
    expect(wrapper.text()).toContain('Avertissements');
    expect(wrapper.text()).toContain('Phase 2 skippée');
  });

  it('saves avis critiques to MongoDB', async () => {
    const mockEpisodes = [
      { id: '123', titre: 'Test', date: '2025-01-15', transcription_length: 5000, has_episode_page_url: true, episode_page_url: 'https://url' }
    ];
    const mockGenerationResult = {
      success: true,
      summary: 'Summary Phase 2',
      summary_phase1: 'Summary Phase 1',
      metadata: { animateur: 'Jérôme Garcin', critiques: ['Patricia Martin'] },
      corrections_applied: [],
      warnings: []
    };

    api.avisCritiquesService.getEpisodesSansAvis.mockResolvedValue(mockEpisodes);
    api.avisCritiquesService.getEpisodesWithSummaries.mockResolvedValue([]);
    api.avisCritiquesService.generateAvisCritiques.mockResolvedValue(mockGenerationResult);
    api.avisCritiquesService.saveAvisCritiques.mockResolvedValue({ success: true, avis_critique_id: 'avis123' });

    // Mock alert
    global.alert = vi.fn();

    wrapper = mount(GenerationAvisCritiques, {
      global: { plugins: [router] }
    });

    await new Promise(resolve => setTimeout(resolve, 50));
    await wrapper.vm.$nextTick();

    wrapper.vm.selectedEpisodeId = '123';
    await wrapper.vm.generateAvisCritiques();
    await wrapper.vm.$nextTick();

    const saveBtn = wrapper.find('button.btn-success');
    expect(saveBtn.exists()).toBe(true);

    await saveBtn.trigger('click');
    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 100));

    expect(api.avisCritiquesService.saveAvisCritiques).toHaveBeenCalledWith({
      episode_id: '123',
      summary: 'Summary Phase 2',
      summary_phase1: 'Summary Phase 1',
      metadata: { animateur: 'Jérôme Garcin', critiques: ['Patricia Martin'] }
    });

    expect(global.alert).toHaveBeenCalledWith('✅ Avis critique sauvegardé !');
  });

  it('resets state after successful save', async () => {
    const mockEpisodes = [
      { id: '123', titre: 'Test', date: '2025-01-15', transcription_length: 5000, has_episode_page_url: true, episode_page_url: 'https://url' }
    ];
    const mockGenerationResult = {
      success: true,
      summary: 'Summary Phase 2',
      summary_phase1: 'Summary Phase 1',
      metadata: {},
      corrections_applied: [],
      warnings: []
    };

    api.avisCritiquesService.getEpisodesSansAvis.mockResolvedValue(mockEpisodes);
    api.avisCritiquesService.getEpisodesWithSummaries.mockResolvedValue([]);
    api.avisCritiquesService.generateAvisCritiques.mockResolvedValue(mockGenerationResult);
    api.avisCritiquesService.saveAvisCritiques.mockResolvedValue({ success: true });

    global.alert = vi.fn();

    wrapper = mount(GenerationAvisCritiques, {
      global: { plugins: [router] }
    });

    await new Promise(resolve => setTimeout(resolve, 50));
    await wrapper.vm.$nextTick();

    wrapper.vm.selectedEpisodeId = '123';
    await wrapper.vm.generateAvisCritiques();
    await wrapper.vm.$nextTick();

    const saveBtn = wrapper.find('button.btn-success');
    await saveBtn.trigger('click');
    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 100));

    expect(wrapper.vm.selectedEpisodeId).toBe('');
    expect(wrapper.vm.generationResult).toBeNull();
    expect(wrapper.vm.activeTab).toBe('phase2');
  });

  it('displays error message on save failure', async () => {
    const mockEpisodes = [
      { id: '123', titre: 'Test', date: '2025-01-15', transcription_length: 5000, has_episode_page_url: true, episode_page_url: 'https://url' }
    ];
    const mockGenerationResult = {
      success: true,
      summary: 'Summary',
      summary_phase1: 'Summary',
      metadata: {},
      corrections_applied: [],
      warnings: []
    };
    const errorMessage = 'Erreur sauvegarde MongoDB';

    api.avisCritiquesService.getEpisodesSansAvis.mockResolvedValue(mockEpisodes);
    api.avisCritiquesService.getEpisodesWithSummaries.mockResolvedValue([]);
    api.avisCritiquesService.generateAvisCritiques.mockResolvedValue(mockGenerationResult);
    api.avisCritiquesService.saveAvisCritiques.mockRejectedValue(new Error(errorMessage));

    wrapper = mount(GenerationAvisCritiques, {
      global: { plugins: [router] }
    });

    await new Promise(resolve => setTimeout(resolve, 50));
    await wrapper.vm.$nextTick();

    wrapper.vm.selectedEpisodeId = '123';
    await wrapper.vm.generateAvisCritiques();
    await wrapper.vm.$nextTick();

    const saveBtn = wrapper.find('button.btn-success');
    await saveBtn.trigger('click');
    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 100));

    expect(wrapper.find('.alert-error').exists()).toBe(true);
    expect(wrapper.text()).toContain(errorMessage);
  });

  it('does NOT fetch URL if episode_page_url already exists when clicking Générer', async () => {
    const mockEpisodes = [
      {
        id: '123',
        titre: 'Episode Test',
        date: '2025-01-15T00:00:00',
        transcription_length: 5000,
        has_episode_page_url: true,
        episode_page_url: 'https://www.radiofrance.fr/existing-url'  // URL déjà présente
      }
    ];

    const mockGenerationResult = {
      success: true,
      summary: '## 1. LIVRES (Phase 2)',
      summary_phase1: '## 1. LIVRES (Phase 1)',
      metadata: { animateur: 'Jérôme Garcin' },
      corrections_applied: [],
      warnings: []
    };

    api.avisCritiquesService.getEpisodesSansAvis.mockResolvedValue(mockEpisodes);
    api.avisCritiquesService.getEpisodesWithSummaries.mockResolvedValue([]);
    api.avisCritiquesService.generateAvisCritiques.mockResolvedValue(mockGenerationResult);
    api.episodeService.fetchEpisodePageUrl.mockResolvedValue({});

    wrapper = mount(GenerationAvisCritiques, {
      global: { plugins: [router] }
    });

    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 50));

    // Sélectionner un épisode
    wrapper.vm.selectedEpisodeId = '123';
    await wrapper.vm.$nextTick();

    // Cliquer sur Générer
    const generateBtn = wrapper.find('button.btn-primary');
    await generateBtn.trigger('click');
    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 100));

    // Ne devrait PAS appeler le fetch car URL déjà présente
    expect(api.episodeService.fetchEpisodePageUrl).not.toHaveBeenCalled();

    // Génération doit être appelée avec l'épisode qui a déjà l'URL
    expect(api.avisCritiquesService.generateAvisCritiques).toHaveBeenCalledWith({
      episode_id: '123'
    });

    // Résultat doit contenir les métadonnées (Phase 2 exécutée)
    expect(wrapper.vm.generationResult.metadata).toEqual({ animateur: 'Jérôme Garcin' });
  });

  it('launches fetch URL + Phase 1 in parallel when URL is missing', async () => {
    const mockEpisodes = [
      {
        id: '123',
        titre: 'Episode Test',
        date: '2025-01-15T00:00:00',
        transcription_length: 5000,
        has_episode_page_url: false,
        episode_page_url: null
      }
    ];

    const mockGenerationResult = {
      success: true,
      summary: '## 1. LIVRES (Phase 2)',
      summary_phase1: '## 1. LIVRES (Phase 1)',
      metadata: { animateur: 'Jérôme Garcin' },
      corrections_applied: [],
      warnings: []
    };

    api.avisCritiquesService.getEpisodesSansAvis.mockResolvedValue(mockEpisodes);
    api.avisCritiquesService.getEpisodesWithSummaries.mockResolvedValue([]);
    api.avisCritiquesService.generateAvisCritiques.mockResolvedValue(mockGenerationResult);

    // Mock fetch URL avec délai
    api.episodeService.fetchEpisodePageUrl.mockImplementation(() =>
      new Promise(resolve => setTimeout(() => resolve({
        episode_id: '123',
        episode_page_url: 'https://www.radiofrance.fr/franceinter/podcasts/episode-123',
        success: true
      }), 100))
    );

    wrapper = mount(GenerationAvisCritiques, {
      global: { plugins: [router] }
    });

    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 50));

    wrapper.vm.selectedEpisodeId = '123';
    await wrapper.vm.$nextTick();

    const generateBtn = wrapper.find('button.btn-primary');
    await generateBtn.trigger('click');
    await wrapper.vm.$nextTick();

    // Vérifier que fetch URL a été lancé
    expect(api.episodeService.fetchEpisodePageUrl).toHaveBeenCalledWith('123');

    // Vérifier que la génération a été lancée
    expect(api.avisCritiquesService.generateAvisCritiques).toHaveBeenCalledWith({
      episode_id: '123'
    });

    // Attendre que le fetch URL se termine
    await new Promise(resolve => setTimeout(resolve, 150));

    // Vérifier que l'URL a été mise à jour dans la liste
    expect(wrapper.vm.episodesSansAvis[0].episode_page_url).toBe(
      'https://www.radiofrance.fr/franceinter/podcasts/episode-123'
    );
  });

  it('handles fetch URL error gracefully without blocking generation', async () => {
    const mockEpisodes = [
      {
        id: '123',
        titre: 'Episode Test',
        date: '2025-01-15T00:00:00',
        transcription_length: 5000,
        has_episode_page_url: false,
        episode_page_url: null
      }
    ];

    const mockGenerationResult = {
      success: true,
      summary: '## 1. LIVRES (Phase 1 only)',
      summary_phase1: '## 1. LIVRES (Phase 1 only)',
      metadata: {},
      corrections_applied: [],
      warnings: ['Pas d\'URL RadioFrance, Phase 2 skippée']
    };

    api.avisCritiquesService.getEpisodesSansAvis.mockResolvedValue(mockEpisodes);
    api.avisCritiquesService.getEpisodesWithSummaries.mockResolvedValue([]);
    api.avisCritiquesService.generateAvisCritiques.mockResolvedValue(mockGenerationResult);
    api.episodeService.fetchEpisodePageUrl.mockRejectedValue(new Error('Network error'));

    wrapper = mount(GenerationAvisCritiques, {
      global: { plugins: [router] }
    });

    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 50));

    wrapper.vm.selectedEpisodeId = '123';
    await wrapper.vm.$nextTick();

    const generateBtn = wrapper.find('button.btn-primary');
    await generateBtn.trigger('click');
    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 150));

    // Vérifier que la génération s'est terminée malgré l'erreur de fetch URL
    expect(wrapper.vm.generationResult).toBeTruthy();
    expect(wrapper.vm.generationResult.summary).toBe('## 1. LIVRES (Phase 1 only)');

    // L'épisode doit garder episode_page_url null
    expect(wrapper.vm.episodesSansAvis[0].episode_page_url).toBeNull();
  });

  it('displays warning alert when summary is empty', async () => {
    const mockEpisodes = [
      {
        id: '123',
        titre: 'Episode Test',
        date: '2025-01-15T00:00:00',
        transcription_length: 5000,
        has_episode_page_url: true,
        episode_page_url: 'https://radiofrance.fr/test'
      }
    ];

    api.avisCritiquesService.getEpisodesSansAvis.mockResolvedValue(mockEpisodes);
    api.avisCritiquesService.getEpisodesWithSummaries.mockResolvedValue([]);

    // Mock génération avec summary VIDE (échec LLM)
    api.avisCritiquesService.generateAvisCritiques.mockResolvedValue({
      summary: '',  // VIDE !
      summary_phase1: '## 1. LIVRES',
      metadata: {},
      corrections_applied: [],
      warnings: []
    });

    wrapper = mount(GenerationAvisCritiques, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 100));

    wrapper.vm.selectedEpisodeId = '123';
    await wrapper.vm.$nextTick();

    const generateBtn = wrapper.find('button.btn-primary');
    await generateBtn.trigger('click');
    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 100));

    // Vérifier que l'alerte warning s'affiche
    const alertWarning = wrapper.find('.alert-warning');
    expect(alertWarning.exists()).toBe(true);
    expect(alertWarning.text()).toContain('La génération a échoué (summary vide)');
    expect(alertWarning.text()).toContain('Régénérer');

    // Vérifier que isSummaryEmpty est true
    expect(wrapper.vm.isSummaryEmpty).toBe(true);
  });

  it('disables save button when summary is empty', async () => {
    const mockEpisodes = [
      {
        id: '123',
        titre: 'Episode Test',
        date: '2025-01-15T00:00:00',
        transcription_length: 5000,
        has_episode_page_url: true,
        episode_page_url: 'https://radiofrance.fr/test'
      }
    ];

    api.avisCritiquesService.getEpisodesSansAvis.mockResolvedValue(mockEpisodes);
    api.avisCritiquesService.getEpisodesWithSummaries.mockResolvedValue([]);

    // Mock génération avec summary VIDE
    api.avisCritiquesService.generateAvisCritiques.mockResolvedValue({
      summary: '   ',  // Que des espaces
      summary_phase1: '## 1. LIVRES',
      metadata: {},
      corrections_applied: [],
      warnings: []
    });

    wrapper = mount(GenerationAvisCritiques, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 100));

    wrapper.vm.selectedEpisodeId = '123';
    await wrapper.vm.$nextTick();

    const generateBtn = wrapper.find('button.btn-primary');
    await generateBtn.trigger('click');
    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 100));

    // Le bouton "Sauvegarder" doit être désactivé
    const saveBtn = wrapper.find('button.btn-success');
    expect(saveBtn.attributes('disabled')).toBeDefined();
  });

  it('regenerates when clicking Régénérer button', async () => {
    const mockEpisodes = [
      {
        id: '123',
        titre: 'Episode Test',
        date: '2025-01-15T00:00:00',
        transcription_length: 5000,
        has_episode_page_url: true,
        episode_page_url: 'https://radiofrance.fr/test'
      }
    ];

    api.avisCritiquesService.getEpisodesSansAvis.mockResolvedValue(mockEpisodes);
    api.avisCritiquesService.getEpisodesWithSummaries.mockResolvedValue([]);

    // Première génération: échec (summary vide)
    api.avisCritiquesService.generateAvisCritiques.mockResolvedValueOnce({
      summary: '',
      summary_phase1: '## 1. LIVRES',
      metadata: {},
      corrections_applied: [],
      warnings: []
    });

    // Deuxième génération (après Régénérer): succès
    api.avisCritiquesService.generateAvisCritiques.mockResolvedValueOnce({
      summary: '## 1. LIVRES\n\nContenu généré avec succès',
      summary_phase1: '## 1. LIVRES',
      metadata: {},
      corrections_applied: [],
      warnings: []
    });

    wrapper = mount(GenerationAvisCritiques, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 100));

    wrapper.vm.selectedEpisodeId = '123';
    await wrapper.vm.$nextTick();

    // Première génération
    const generateBtn = wrapper.find('button.btn-primary');
    await generateBtn.trigger('click');
    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 100));

    // Vérifier que summary est vide
    expect(wrapper.vm.isSummaryEmpty).toBe(true);

    // Cliquer sur Régénérer
    const regenerateBtn = wrapper.find('button.btn-regenerate');
    expect(regenerateBtn.exists()).toBe(true);
    await regenerateBtn.trigger('click');
    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 100));

    // Vérifier que summary n'est plus vide
    expect(wrapper.vm.isSummaryEmpty).toBe(false);
    expect(wrapper.vm.generationResult.summary).toContain('Contenu généré avec succès');

    // Vérifier que generateAvisCritiques a été appelé 2 fois
    expect(api.avisCritiquesService.generateAvisCritiques).toHaveBeenCalledTimes(2);
  });

  it('hides warning alert when summary is not empty', async () => {
    const mockEpisodes = [
      {
        id: '123',
        titre: 'Episode Test',
        date: '2025-01-15T00:00:00',
        transcription_length: 5000,
        has_episode_page_url: true,
        episode_page_url: 'https://radiofrance.fr/test'
      }
    ];

    api.avisCritiquesService.getEpisodesSansAvis.mockResolvedValue(mockEpisodes);
    api.avisCritiquesService.getEpisodesWithSummaries.mockResolvedValue([]);

    // Génération avec summary VALIDE
    api.avisCritiquesService.generateAvisCritiques.mockResolvedValue({
      summary: '## 1. LIVRES\n\nContenu valide',
      summary_phase1: '## 1. LIVRES',
      metadata: {},
      corrections_applied: [],
      warnings: []
    });

    wrapper = mount(GenerationAvisCritiques, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 100));

    wrapper.vm.selectedEpisodeId = '123';
    await wrapper.vm.$nextTick();

    const generateBtn = wrapper.find('button.btn-primary');
    await generateBtn.trigger('click');
    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 100));

    // Vérifier que l'alerte warning ne s'affiche PAS
    const alertWarning = wrapper.find('.alert-warning');
    expect(alertWarning.exists()).toBe(false);

    // Vérifier que isSummaryEmpty est false
    expect(wrapper.vm.isSummaryEmpty).toBe(false);

    // Le bouton Sauvegarder doit être activé
    const saveBtn = wrapper.find('button.btn-success');
    expect(saveBtn.attributes('disabled')).toBeUndefined();
  });

  describe('Failed generation validation', () => {
    it('should NOT save and NOT change badge when summary is empty', async () => {
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
      const mockEpisodesWith = [];

      api.avisCritiquesService.getEpisodesSansAvis.mockResolvedValue(mockEpisodesWithout);
    api.avisCritiquesService.getEpisodesWithSummaries.mockResolvedValue([]);
      api.avisCritiquesService.getEpisodesWithSummaries.mockResolvedValue(mockEpisodesWith);

      // Mock génération avec summary vide
      api.avisCritiquesService.generateAvisCritiques.mockResolvedValue({
        summary: '',  // VIDE
        summary_phase1: 'Phase 1 summary',
        metadata: {}
      });

      wrapper = mount(GenerationAvisCritiques, {
        global: {
          plugins: [router]
        }
      });

      await wrapper.vm.$nextTick();
      await new Promise(resolve => setTimeout(resolve, 100));

      wrapper.vm.selectedEpisodeId = '123';
      await wrapper.vm.$nextTick();

      const generateBtn = wrapper.find('button.btn-primary');
      await generateBtn.trigger('click');
      await wrapper.vm.$nextTick();
      await new Promise(resolve => setTimeout(resolve, 100));

      // Vérifier que saveAvisCritiques n'a PAS été appelé
      expect(api.avisCritiquesService.saveAvisCritiques).not.toHaveBeenCalled();

      // Vérifier que la pastille n'a PAS changé (toujours false)
      expect(wrapper.vm.allEpisodes[0].has_summary).toBe(false);

      // Vérifier qu'un message d'erreur est affiché
      expect(wrapper.vm.error).toBeTruthy();
      expect(wrapper.vm.error).toContain('Summary vide');
    });

    it('should NOT save and NOT change badge when summary is too long (malformed)', async () => {
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
      const mockEpisodesWith = [];

      api.avisCritiquesService.getEpisodesSansAvis.mockResolvedValue(mockEpisodesWithout);
    api.avisCritiquesService.getEpisodesWithSummaries.mockResolvedValue([]);
      api.avisCritiquesService.getEpisodesWithSummaries.mockResolvedValue(mockEpisodesWith);

      // Mock génération avec summary trop long (> 50000 caractères)
      const longSummary = 'A'.repeat(60000);
      api.avisCritiquesService.generateAvisCritiques.mockResolvedValue({
        summary: longSummary,
        summary_phase1: 'Phase 1 summary',
        metadata: {}
      });

      wrapper = mount(GenerationAvisCritiques, {
        global: {
          plugins: [router]
        }
      });

      await wrapper.vm.$nextTick();
      await new Promise(resolve => setTimeout(resolve, 100));

      wrapper.vm.selectedEpisodeId = '123';
      await wrapper.vm.$nextTick();

      const generateBtn = wrapper.find('button.btn-primary');
      await generateBtn.trigger('click');
      await wrapper.vm.$nextTick();
      await new Promise(resolve => setTimeout(resolve, 100));

      // Vérifier que saveAvisCritiques n'a PAS été appelé
      expect(api.avisCritiquesService.saveAvisCritiques).not.toHaveBeenCalled();

      // Vérifier que la pastille n'a PAS changé (toujours false)
      expect(wrapper.vm.allEpisodes[0].has_summary).toBe(false);

      // Vérifier qu'un message d'erreur est affiché
      expect(wrapper.vm.error).toBeTruthy();
      expect(wrapper.vm.error).toContain('trop long');
    });

    it('should NOT save and NOT change badge when summary lacks expected markdown structure', async () => {
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
      const mockEpisodesWith = [];

      api.avisCritiquesService.getEpisodesSansAvis.mockResolvedValue(mockEpisodesWithout);
    api.avisCritiquesService.getEpisodesWithSummaries.mockResolvedValue([]);
      api.avisCritiquesService.getEpisodesWithSummaries.mockResolvedValue(mockEpisodesWith);

      // Mock génération avec summary sans structure attendue
      api.avisCritiquesService.generateAvisCritiques.mockResolvedValue({
        summary: 'Some random text without proper markdown structure',
        summary_phase1: 'Phase 1 summary',
        metadata: {}
      });

      wrapper = mount(GenerationAvisCritiques, {
        global: {
          plugins: [router]
        }
      });

      await wrapper.vm.$nextTick();
      await new Promise(resolve => setTimeout(resolve, 100));

      wrapper.vm.selectedEpisodeId = '123';
      await wrapper.vm.$nextTick();

      const generateBtn = wrapper.find('button.btn-primary');
      await generateBtn.trigger('click');
      await wrapper.vm.$nextTick();
      await new Promise(resolve => setTimeout(resolve, 100));

      // Vérifier que saveAvisCritiques n'a PAS été appelé
      expect(api.avisCritiquesService.saveAvisCritiques).not.toHaveBeenCalled();

      // Vérifier que la pastille n'a PAS changé (toujours false)
      expect(wrapper.vm.allEpisodes[0].has_summary).toBe(false);

      // Vérifier qu'un message d'erreur est affiché
      expect(wrapper.vm.error).toBeTruthy();
      expect(wrapper.vm.error).toContain('Structure markdown manquante');
    });

    it('should save and change badge when summary is valid', async () => {
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
      const mockEpisodesWith = [];

      api.avisCritiquesService.getEpisodesSansAvis.mockResolvedValue(mockEpisodesWithout);
    api.avisCritiquesService.getEpisodesWithSummaries.mockResolvedValue([]);
      api.avisCritiquesService.getEpisodesWithSummaries.mockResolvedValue(mockEpisodesWith);

      // Mock génération avec summary VALIDE
      const validSummary = '## 1. LIVRES DISCUTÉS\n\nTitre: Test Book\nAuteur: Test Author';
      api.avisCritiquesService.generateAvisCritiques.mockResolvedValue({
        summary: validSummary,
        summary_phase1: 'Phase 1 summary',
        metadata: {}
      });

      api.avisCritiquesService.saveAvisCritiques.mockResolvedValue({});

      wrapper = mount(GenerationAvisCritiques, {
        global: {
          plugins: [router]
        }
      });

      await wrapper.vm.$nextTick();
      await new Promise(resolve => setTimeout(resolve, 100));

      wrapper.vm.selectedEpisodeId = '123';
      await wrapper.vm.$nextTick();

      const generateBtn = wrapper.find('button.btn-primary');
      await generateBtn.trigger('click');
      await wrapper.vm.$nextTick();
      await new Promise(resolve => setTimeout(resolve, 100));

      // Vérifier que saveAvisCritiques A été appelé
      expect(api.avisCritiquesService.saveAvisCritiques).toHaveBeenCalledWith({
        episode_id: '123',
        summary: validSummary,
        summary_phase1: 'Phase 1 summary',
        metadata: {}
      });

      // Vérifier que la pastille A changé (devient true)
      expect(wrapper.vm.allEpisodes[0].has_summary).toBe(true);

      // Vérifier qu'il n'y a PAS de message d'erreur
      expect(wrapper.vm.error).toBe(null);
    });
  });
});
