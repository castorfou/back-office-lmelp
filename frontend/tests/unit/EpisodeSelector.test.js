/**
 * Tests unitaires pour le composant EpisodeSelector
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount } from '@vue/test-utils';
import EpisodeSelector from '../../src/components/EpisodeSelector.vue';
import { episodeService } from '../../src/services/api.js';

// Mock du service API
vi.mock('../../src/services/api.js', () => ({
  episodeService: {
    getAllEpisodes: vi.fn(),
    getEpisodeById: vi.fn(),
  }
}));

describe('EpisodeSelector', () => {
  let wrapper;

  const mockEpisodes = [
    {
      id: '1',
      titre: 'Episode Test 1',
      date: '2024-01-15T09:00:00Z',
      type: 'livres'
    },
    {
      id: '2',
      titre: 'Episode Test 2',
      date: '2024-01-10T09:00:00Z',
      type: 'cinema'
    }
  ];

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount();
    }
  });

  it('affiche le message de chargement au démarrage', async () => {
    episodeService.getAllEpisodes.mockImplementation(() =>
      new Promise(resolve => setTimeout(() => resolve(mockEpisodes), 100))
    );

    wrapper = mount(EpisodeSelector);

    expect(wrapper.find('.loading').text()).toContain('Chargement des épisodes');
  });

  it('charge et affiche la liste des épisodes', async () => {
    episodeService.getAllEpisodes.mockResolvedValue(mockEpisodes);

    wrapper = mount(EpisodeSelector);

    // Attendre que les épisodes se chargent
    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 10));

    expect(episodeService.getAllEpisodes).toHaveBeenCalledOnce();
    expect(wrapper.vm.episodes).toEqual(mockEpisodes);
  });

  it('affiche les options dans le select', async () => {
    episodeService.getAllEpisodes.mockResolvedValue(mockEpisodes);

    wrapper = mount(EpisodeSelector);
    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 10));

    const options = wrapper.findAll('option');

    // Option par défaut + 2 épisodes
    expect(options).toHaveLength(3);
    expect(options[1].text()).toContain('Episode Test 1');
    expect(options[2].text()).toContain('Episode Test 2');
  });

  it('émet un événement quand un épisode est sélectionné', async () => {
    const mockEpisodeDetail = {
      ...mockEpisodes[0],
      description: 'Description test'
    };

    episodeService.getAllEpisodes.mockResolvedValue(mockEpisodes);
    episodeService.getEpisodeById.mockResolvedValue(mockEpisodeDetail);

    wrapper = mount(EpisodeSelector);
    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 10));

    // Sélectionner un épisode
    const select = wrapper.find('select');
    await select.setValue('1');

    // Attendre la résolution de la promesse
    await new Promise(resolve => setTimeout(resolve, 10));

    expect(episodeService.getEpisodeById).toHaveBeenCalledWith('1');
    expect(wrapper.emitted('episode-selected')).toBeTruthy();
  });

  it('gère les erreurs de chargement', async () => {
    const error = new Error('Erreur réseau');
    episodeService.getAllEpisodes.mockRejectedValue(error);

    wrapper = mount(EpisodeSelector);
    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 10));

    expect(wrapper.find('.alert-error').exists()).toBe(true);
    expect(wrapper.vm.error).toBeTruthy();
  });

  it('formate correctement les options d\'épisode', () => {
    wrapper = mount(EpisodeSelector);

    const formatted = wrapper.vm.formatEpisodeOption(mockEpisodes[0]);

    expect(formatted).toContain('15/01/2024');
    expect(formatted).toContain('[livres]');
    expect(formatted).toContain('Episode Test 1');
  });

  it('permet de réessayer après une erreur', async () => {
    episodeService.getAllEpisodes
      .mockRejectedValueOnce(new Error('Erreur'))
      .mockResolvedValueOnce(mockEpisodes);

    wrapper = mount(EpisodeSelector);
    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 10));

    // Vérifier qu'il y a une erreur
    expect(wrapper.find('.alert-error').exists()).toBe(true);

    // Cliquer sur réessayer
    const retryButton = wrapper.find('.alert-error button');
    await retryButton.trigger('click');
    await new Promise(resolve => setTimeout(resolve, 10));

    // Vérifier que les épisodes sont maintenant chargés
    expect(wrapper.vm.episodes).toEqual(mockEpisodes);
    expect(wrapper.find('.alert-error').exists()).toBe(false);
  });
});
