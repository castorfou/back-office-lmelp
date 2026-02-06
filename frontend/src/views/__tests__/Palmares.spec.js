/**
 * Tests pour le composant Palmares.vue (Issue #195)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount } from '@vue/test-utils';
import { createRouter, createMemoryHistory } from 'vue-router';
import axios from 'axios';

// Mock axios
vi.mock('axios');

// Mock IntersectionObserver
const mockObserve = vi.fn();
const mockDisconnect = vi.fn();

global.IntersectionObserver = vi.fn().mockImplementation((callback) => ({
  observe: mockObserve,
  disconnect: mockDisconnect,
  unobserve: vi.fn(),
  _callback: callback,
}));

// Import after mocks
import Palmares from '../Palmares.vue';

const mockPalmaresData = {
  items: [
    {
      livre_id: '6956ba2affd13096430f9cb9',
      titre: 'Le Lambeau',
      auteur_id: '6950027a26f38eb0ca5aabed',
      auteur_nom: 'Philippe Lançon',
      note_moyenne: 10.0,
      nombre_avis: 4,
      url_babelio: 'https://www.babelio.com/livres/Lancon-Le-Lambeau/1036944',
    },
    {
      livre_id: '6956cb23ffd13096430f9d2c',
      titre: 'La Serpe',
      auteur_id: '68e9729e7f7c718a5b6200f9',
      auteur_nom: 'Philippe Jaenada',
      note_moyenne: 10.0,
      nombre_avis: 4,
      url_babelio: 'https://www.babelio.com/livres/Jaenada-La-Serpe/1357073',
    },
    {
      livre_id: '694a538a7f4fb7d4a62077dc',
      titre: 'Feu',
      auteur_id: '68e2c3ba1391489c77ccdee5',
      auteur_nom: 'Maria Pourchet',
      note_moyenne: 10.0,
      nombre_avis: 4,
      url_babelio: 'https://www.babelio.com/livres/Pourchet-Feu/1331996',
    },
  ],
  total: 861,
  page: 1,
  limit: 30,
  total_pages: 29,
};

describe('Palmares.vue', () => {
  let wrapper;
  let router;

  beforeEach(() => {
    vi.resetAllMocks();

    router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/palmares', name: 'Palmares', component: Palmares },
        { path: '/livre/:id', name: 'LivreDetail', component: { template: '<div />' } },
        { path: '/auteur/:id', name: 'AuteurDetail', component: { template: '<div />' } },
        { path: '/calibre', name: 'CalibreLibrary', component: { template: '<div />' } },
      ],
    });
  });

  async function mountPalmares(palmaresResponse = mockPalmaresData) {
    axios.get.mockImplementation((url) => {
      if (url === '/api/palmares') {
        return Promise.resolve({ data: palmaresResponse });
      }
      if (url === '/api/config/annas-archive-url') {
        return Promise.resolve({ data: { url: 'https://fr.annas-archive.se' } });
      }
      return Promise.reject(new Error(`Unexpected URL: ${url}`));
    });

    await router.push('/palmares');
    await router.isReady();

    wrapper = mount(Palmares, {
      global: {
        plugins: [router],
      },
    });

    // Wait for mounted() to complete
    await wrapper.vm.$nextTick();
    // Wait for the axios promises
    await vi.dynamicImportSettled?.() || await new Promise(r => setTimeout(r, 10));
    await wrapper.vm.$nextTick();
  }

  describe('Loading and display', () => {
    it('should display books from API response', async () => {
      await mountPalmares();

      const rows = wrapper.findAll('[data-test="palmares-row"]');
      expect(rows.length).toBe(3);
    });

    it('should display book title', async () => {
      await mountPalmares();

      const firstRow = wrapper.find('[data-test="palmares-row"]');
      expect(firstRow.text()).toContain('Le Lambeau');
    });

    it('should display author name', async () => {
      await mountPalmares();

      const firstRow = wrapper.find('[data-test="palmares-row"]');
      expect(firstRow.text()).toContain('Philippe Lançon');
    });

    it('should display note moyenne with badge', async () => {
      await mountPalmares();

      const badge = wrapper.find('[data-test="note-badge"]');
      expect(badge.exists()).toBe(true);
      expect(badge.text()).toContain('10.0');
    });

    it('should display rank numbers', async () => {
      await mountPalmares();

      const ranks = wrapper.findAll('[data-test="palmares-rank"]');
      expect(ranks[0].text()).toBe('1');
      expect(ranks[1].text()).toBe('2');
      expect(ranks[2].text()).toBe('3');
    });

    it('should show total count', async () => {
      await mountPalmares();

      // Count is based on filtered items (3 items loaded)
      expect(wrapper.text()).toContain('3 livres classés');
    });
  });

  describe('Links', () => {
    it('should have link to book detail page', async () => {
      await mountPalmares();

      const bookLink = wrapper.find('[data-test="livre-link"]');
      expect(bookLink.exists()).toBe(true);
      expect(bookLink.attributes('href')).toContain('/livre/6956ba2affd13096430f9cb9');
    });

    it('should have link to author detail page', async () => {
      await mountPalmares();

      const authorLink = wrapper.find('[data-test="auteur-link"]');
      expect(authorLink.exists()).toBe(true);
      expect(authorLink.attributes('href')).toContain('/auteur/6950027a26f38eb0ca5aabed');
    });

    it('should have Anna\'s Archive link', async () => {
      await mountPalmares();

      const annaLink = wrapper.find('[data-test="annas-archive-link"]');
      expect(annaLink.exists()).toBe(true);
      expect(annaLink.attributes('href')).toContain('annas-archive');
    });

    it('should have Calibre search link', async () => {
      await mountPalmares();

      const calibreLink = wrapper.find('[data-test="calibre-link"]');
      expect(calibreLink.exists()).toBe(true);
      expect(calibreLink.attributes('href')).toContain('/calibre');
    });
  });

  describe('Infinite scroll', () => {
    it('should call API with page=1 on mount', async () => {
      await mountPalmares();

      expect(axios.get).toHaveBeenCalledWith('/api/palmares', {
        params: { page: 1, limit: 30 },
      });
    });

    it('should load next page when loadMore is called', async () => {
      await mountPalmares();

      // Simulate loading more
      const page2Data = {
        ...mockPalmaresData,
        page: 2,
        items: [
          {
            livre_id: 'id4',
            titre: 'Book 4',
            auteur_id: 'a4',
            auteur_nom: 'Author 4',
            note_moyenne: 9.0,
            nombre_avis: 3,
            url_babelio: null,
          },
        ],
      };

      axios.get.mockImplementation((url) => {
        if (url === '/api/palmares') {
          return Promise.resolve({ data: page2Data });
        }
        return Promise.resolve({ data: {} });
      });

      await wrapper.vm.loadMore();
      await wrapper.vm.$nextTick();

      // Should have appended items
      expect(wrapper.vm.items.length).toBe(4);
    });

    it('should not load more when already on last page', async () => {
      const lastPageData = {
        ...mockPalmaresData,
        page: 29,
        total_pages: 29,
      };
      await mountPalmares(lastPageData);

      const callCount = axios.get.mock.calls.filter(c => c[0] === '/api/palmares').length;

      await wrapper.vm.loadMore();

      const newCallCount = axios.get.mock.calls.filter(c => c[0] === '/api/palmares').length;
      expect(newCallCount).toBe(callCount); // No new call
    });
  });

  describe('Error handling', () => {
    it('should show error message when API fails', async () => {
      axios.get.mockImplementation((url) => {
        if (url === '/api/palmares') {
          return Promise.reject(new Error('Network error'));
        }
        if (url === '/api/config/annas-archive-url') {
          return Promise.resolve({ data: { url: 'https://fr.annas-archive.org' } });
        }
        return Promise.reject(new Error('Unexpected'));
      });

      await router.push('/palmares');
      await router.isReady();

      wrapper = mount(Palmares, {
        global: { plugins: [router] },
      });

      await wrapper.vm.$nextTick();
      await new Promise(r => setTimeout(r, 10));
      await wrapper.vm.$nextTick();

      expect(wrapper.find('[data-test="error"]').exists()).toBe(true);
    });
  });

  describe('Note badge styling', () => {
    it('should apply correct CSS class based on note value', async () => {
      await mountPalmares();

      // note_moyenne is 10.0 → should be 'note-excellent'
      const badge = wrapper.find('[data-test="note-badge"]');
      expect(badge.classes()).toContain('note-excellent');
    });
  });

  describe('Filter chips', () => {
    const dataWithCalibre = {
      items: [
        {
          livre_id: 'id1',
          titre: 'Livre Lu',
          auteur_id: 'a1',
          auteur_nom: 'Auteur 1',
          note_moyenne: 10.0,
          nombre_avis: 4,
          calibre_in_library: true,
          calibre_read: true,
          calibre_rating: 8,
        },
        {
          livre_id: 'id2',
          titre: 'Livre Non Lu Calibre',
          auteur_id: 'a2',
          auteur_nom: 'Auteur 2',
          note_moyenne: 9.0,
          nombre_avis: 3,
          calibre_in_library: true,
          calibre_read: false,
          calibre_rating: null,
        },
        {
          livre_id: 'id3',
          titre: 'Livre Pas Calibre',
          auteur_id: 'a3',
          auteur_nom: 'Auteur 3',
          note_moyenne: 8.0,
          nombre_avis: 2,
          calibre_in_library: false,
          calibre_read: null,
          calibre_rating: null,
        },
      ],
      total: 3,
      page: 1,
      limit: 30,
      total_pages: 1,
    };

    it('should show all books by default (all filters active)', async () => {
      await mountPalmares(dataWithCalibre);

      const rows = wrapper.findAll('[data-test="palmares-row"]');
      expect(rows.length).toBe(3);
      expect(wrapper.vm.filterRead).toBe(true);
      expect(wrapper.vm.filterUnread).toBe(true);
      expect(wrapper.vm.filterInCalibre).toBe(true);
    });

    it('should hide read books when Lus filter is OFF', async () => {
      await mountPalmares(dataWithCalibre);

      wrapper.vm.filterRead = false;
      await wrapper.vm.$nextTick();

      const rows = wrapper.findAll('[data-test="palmares-row"]');
      expect(rows.length).toBe(2);
      expect(wrapper.text()).toContain('Livre Non Lu Calibre');
      expect(wrapper.text()).toContain('Livre Pas Calibre');
      expect(wrapper.text()).not.toContain('Livre Lu');
    });

    it('should hide unread books when Non lus filter is OFF', async () => {
      await mountPalmares(dataWithCalibre);

      wrapper.vm.filterUnread = false;
      await wrapper.vm.$nextTick();

      const rows = wrapper.findAll('[data-test="palmares-row"]');
      expect(rows.length).toBe(1);
      expect(wrapper.text()).toContain('Livre Lu');
      expect(wrapper.text()).not.toContain('Livre Non Lu Calibre');
      expect(wrapper.text()).not.toContain('Livre Pas Calibre');
    });

    it('should hide Calibre books when Dans Calibre filter is OFF', async () => {
      await mountPalmares(dataWithCalibre);

      wrapper.vm.filterInCalibre = false;
      await wrapper.vm.$nextTick();

      const rows = wrapper.findAll('[data-test="palmares-row"]');
      expect(rows.length).toBe(1);
      expect(wrapper.text()).toContain('Livre Pas Calibre');
      expect(wrapper.text()).not.toContain('Livre Lu');
      expect(wrapper.text()).not.toContain('Livre Non Lu Calibre');
    });

    it('should update displayed count dynamically', async () => {
      await mountPalmares(dataWithCalibre);

      const count = wrapper.find('[data-test="total-count"]');
      expect(count.text()).toContain('3');

      wrapper.vm.filterRead = false;
      await wrapper.vm.$nextTick();

      expect(count.text()).toContain('2');
    });

    it('should render all three filter chips', async () => {
      await mountPalmares(dataWithCalibre);

      expect(wrapper.find('[data-test="filter-read"]').exists()).toBe(true);
      expect(wrapper.find('[data-test="filter-unread"]').exists()).toBe(true);
      expect(wrapper.find('[data-test="filter-in-calibre"]').exists()).toBe(true);
    });

    it('should toggle filter on click', async () => {
      await mountPalmares(dataWithCalibre);

      const chip = wrapper.find('[data-test="filter-read"]');
      expect(wrapper.vm.filterRead).toBe(true);

      await chip.trigger('click');
      expect(wrapper.vm.filterRead).toBe(false);

      await chip.trigger('click');
      expect(wrapper.vm.filterRead).toBe(true);
    });
  });
});
