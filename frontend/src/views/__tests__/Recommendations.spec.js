/**
 * Tests pour Recommendations.vue — colonne possession / téléchargement (Issue #325)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount } from '@vue/test-utils';
import { createRouter, createMemoryHistory } from 'vue-router';
import axios from 'axios';

vi.mock('axios');

import Recommendations from '../Recommendations.vue';

// Structure réelle de GET /api/recommendations/me (enrichie Calibre)
const mockRecommendations = [
  {
    rank: 1,
    livre_id: '6956ba2affd13096430f9cb9',
    titre: 'Le Lambeau',
    auteur_id: '6950027a26f38eb0ca5aabed',
    auteur_nom: 'Philippe Lançon',
    score_hybride: 8.2,
    svd_predict: 7.9,
    masque_mean: 9.0,
    masque_count: 4,
    calibre_in_library: true,
    calibre_read: null,
    calibre_rating: null,
    calibre_current_tags: ['guillaume'],
  },
  {
    rank: 2,
    livre_id: '6956cb23ffd13096430f9d2c',
    titre: 'La Serpe',
    auteur_id: '68e9729e7f7c718a5b6200f9',
    auteur_nom: 'Philippe Jaenada',
    score_hybride: 7.5,
    svd_predict: 7.1,
    masque_mean: 8.5,
    masque_count: 3,
    calibre_in_library: true,
    calibre_read: true,
    calibre_rating: null,
    calibre_current_tags: ['guillaume'],
  },
  {
    rank: 3,
    livre_id: '694a538a7f4fb7d4a62077dc',
    titre: "L'Œuvre au noir",
    auteur_id: '68e2c3ba1391489c77ccdee5',
    auteur_nom: 'Marguerite Yourcenar',
    score_hybride: 6.4,
    svd_predict: 6.0,
    masque_mean: 7.3,
    masque_count: 2,
    calibre_in_library: false,
    calibre_read: null,
    calibre_rating: null,
    calibre_current_tags: null,
  },
];

describe('Recommendations.vue — colonne possession', () => {
  let wrapper;
  let router;

  beforeEach(() => {
    vi.resetAllMocks();
    router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/recommendations', component: Recommendations },
        { path: '/livre/:id', component: { template: '<div />' } },
        { path: '/auteur/:id', component: { template: '<div />' } },
      ],
    });
  });

  async function mountPage() {
    axios.get.mockImplementation((url) => {
      if (url === '/api/recommendations/me') {
        return Promise.resolve({ data: mockRecommendations });
      }
      if (url === '/api/config/annas-archive-url') {
        return Promise.resolve({ data: { url: 'https://fr.annas-archive.se' } });
      }
      return Promise.reject(new Error(`Unexpected URL: ${url}`));
    });

    await router.push('/recommendations');
    await router.isReady();
    wrapper = mount(Recommendations, {
      global: { plugins: [router], stubs: { Navigation: true } },
    });
    await new Promise((r) => setTimeout(r, 10));
    await wrapper.vm.$nextTick();
  }

  it('place la colonne possession entre Auteur et Score', async () => {
    await mountPage();
    const classes = wrapper.findAll('thead th').map((th) => th.classes()[0]);
    const idx = classes.indexOf('col-possession');
    expect(idx).toBeGreaterThan(-1);
    expect(classes[idx - 1]).toBe('col-author');
    expect(classes[idx + 1]).toBe('col-score');
  });

  it('affiche ◯ pour un livre possédé non lu et ✓ Lu pour un livre lu', async () => {
    await mountPage();
    const cells = wrapper.findAll('[data-test="possession-cell"]');
    expect(cells).toHaveLength(3);
    expect(cells[0].text()).toBe('◯');
    expect(cells[0].find('[data-test="annas-archive-link"]').exists()).toBe(false);
    expect(cells[1].text()).toBe('✓ Lu');
    expect(cells[1].find('[data-test="annas-archive-link"]').exists()).toBe(false);
  });

  it("affiche un lien Anna's Archive pour un livre absent de Calibre", async () => {
    await mountPage();
    const cell = wrapper.findAll('[data-test="possession-cell"]')[2];
    const link = cell.find('[data-test="annas-archive-link"]');
    expect(link.exists()).toBe(true);
    expect(link.attributes('target')).toBe('_blank');
    expect(link.attributes('href')).toBe(
      'https://fr.annas-archive.se/search?index=&page=1&sort=&display=&q=' +
        'L%27%C5%92uvre+au+noir+-+Marguerite+Yourcenar'
    );
  });
});
