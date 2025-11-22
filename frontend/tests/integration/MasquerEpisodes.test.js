import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount } from '@vue/test-utils';
import { createRouter, createWebHistory } from 'vue-router';
import MasquerEpisodes from '../../src/views/MasquerEpisodes.vue';
import { episodeService } from '../../src/services/api.js';

// Mock du service API
vi.mock('../../src/services/api.js', () => ({
  episodeService: {
    getAllEpisodesIncludingMasked: vi.fn(),
    updateEpisodeMaskedStatus: vi.fn(),
  }
}));

describe('MasquerEpisodes - Tests d\'intégration', () => {
  let wrapper;
  let router;

  const mockEpisodes = [
    { id: '1', titre: 'Episode 1', date: '2024-01-01', masked: false },
    { id: '2', titre: 'Episode 2', date: '2025-01-01', masked: true },
    { id: '3', titre: 'Episode 3', date: '2023-01-01', masked: false }
  ];

  beforeEach(async () => {
    vi.clearAllMocks();
    episodeService.getAllEpisodesIncludingMasked.mockResolvedValue(mockEpisodes);

    router = createRouter({
      history: createWebHistory(),
      routes: [
        { path: '/masquer-episodes', component: MasquerEpisodes }
      ]
    });

    await router.push('/masquer-episodes');
  });

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount();
    }
  });

  it('trie les épisodes par date décroissante par défaut', async () => {
    wrapper = mount(MasquerEpisodes, {
      global: {
        plugins: [router]
      }
    });

    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 50));

    const rows = wrapper.findAll('tbody tr');
    expect(rows.length).toBe(3);

    // Ordre attendu : 2025 (Episode 2), 2024 (Episode 1), 2023 (Episode 3)
    expect(rows[0].text()).toContain('Episode 2');
    expect(rows[1].text()).toContain('Episode 1');
    expect(rows[2].text()).toContain('Episode 3');
  });
});
