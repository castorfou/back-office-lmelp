/**
 * Tests pour le composant CalibreCorrections.vue (Issue #199)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount } from '@vue/test-utils';
import { createRouter, createMemoryHistory } from 'vue-router';
import axios from 'axios';

// Mock axios
vi.mock('axios');

// Import after mocks
import CalibreCorrections from '../CalibreCorrections.vue';

const mockCorrectionsData = {
  author_corrections: [
    {
      calibre_id: 42,
      calibre_title: 'Tropique de la violence',
      calibre_authors: ['Appanah| Nathacha'],
      mongodb_author: 'Nathacha Appanah',
      mongo_livre_id: 'abc',
      match_type: 'exact',
    },
    {
      calibre_id: 88,
      calibre_title: 'Vernon Subutex',
      calibre_authors: ['Despentes| Virginie'],
      mongodb_author: 'Virginie Despentes',
      mongo_livre_id: 'def',
      match_type: 'exact',
    },
  ],
  title_corrections: [
    {
      calibre_id: 100,
      calibre_title: 'Chanson douce - Prix Goncourt 2016',
      mongodb_title: 'Chanson douce',
      author: 'Leila Slimani',
      mongo_livre_id: 'ghi_title',
      match_type: 'containment',
    },
  ],
  missing_lmelp_tags: [
    {
      calibre_id: 55,
      calibre_title: 'La seule histoire',
      current_tags: ['roman'],
      mongo_livre_id: 'ghi',
      author: 'Julian Barnes',
      expected_lmelp_tags: ['lmelp_240922'],
      all_tags_to_copy: ['lmelp_240922'],
    },
    {
      calibre_id: 66,
      calibre_title: 'Le lambeau',
      current_tags: ['roman', 'temoignage'],
      mongo_livre_id: 'jkl',
      author: 'Philippe Lancon',
      expected_lmelp_tags: ['lmelp_230315', 'lmelp_michel_crement'],
      all_tags_to_copy: ['lmelp_230315', 'lmelp_michel_crement'],
    },
  ],
  statistics: {
    total_author_corrections: 2,
    total_title_corrections: 1,
    total_missing_lmelp_tags: 2,
    total_matches: 45,
  },
};

const emptyCorrectionsData = {
  author_corrections: [],
  title_corrections: [],
  missing_lmelp_tags: [],
  statistics: {
    total_author_corrections: 0,
    total_title_corrections: 0,
    total_missing_lmelp_tags: 0,
    total_matches: 10,
  },
};

describe('CalibreCorrections.vue', () => {
  let wrapper;
  let router;

  beforeEach(() => {
    vi.resetAllMocks();

    // Mock scrollIntoView (not available in jsdom)
    Element.prototype.scrollIntoView = vi.fn();

    router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/calibre-corrections', name: 'CalibreCorrections', component: CalibreCorrections },
        { path: '/', name: 'Dashboard', component: { template: '<div />' } },
        { path: '/livre/:id', name: 'LivreDetail', component: { template: '<div />' } },
      ],
    });
  });

  async function mountComponent(responseData = mockCorrectionsData) {
    axios.get.mockResolvedValueOnce({ data: responseData });

    await router.push('/calibre-corrections');
    await router.isReady();

    wrapper = mount(CalibreCorrections, {
      global: {
        plugins: [router],
      },
    });

    // Wait for mounted() to complete
    await wrapper.vm.$nextTick();
    // Wait for the axios promise to resolve
    await new Promise(r => setTimeout(r, 10));
    await wrapper.vm.$nextTick();
  }

  describe('Loading state', () => {
    it('renders loading state initially', async () => {
      // Use a promise that never resolves to keep loading state
      axios.get.mockReturnValueOnce(new Promise(() => {}));

      await router.push('/calibre-corrections');
      await router.isReady();

      wrapper = mount(CalibreCorrections, {
        global: {
          plugins: [router],
        },
      });

      expect(wrapper.find('[data-test="loading"]').exists()).toBe(true);
      expect(wrapper.find('[data-test="content"]').exists()).toBe(false);
      expect(wrapper.find('[data-test="error"]').exists()).toBe(false);
    });
  });

  describe('Content display', () => {
    it('renders corrections data after loading', async () => {
      await mountComponent();

      expect(wrapper.find('[data-test="loading"]').exists()).toBe(false);
      expect(wrapper.find('[data-test="content"]').exists()).toBe(true);
      expect(wrapper.find('[data-test="error"]').exists()).toBe(false);

      // Verify API was called with correct URL
      expect(axios.get).toHaveBeenCalledWith('/api/calibre/corrections');
    });

    it('renders empty state when no corrections', async () => {
      await mountComponent(emptyCorrectionsData);

      expect(wrapper.find('[data-test="content"]').exists()).toBe(true);

      // All sections should show empty messages
      expect(wrapper.text()).toContain('Aucune correction');
      expect(wrapper.text()).toContain('Aucune diff');
      expect(wrapper.text()).toContain('Tous les livres ont un tag lmelp_');
    });

    it('displays total matches count in header', async () => {
      await mountComponent();

      const totalMatches = wrapper.find('[data-test="total-matches"]');
      expect(totalMatches.exists()).toBe(true);
      expect(totalMatches.text()).toContain('45');
    });
  });

  describe('Error state', () => {
    it('renders error state on API failure', async () => {
      axios.get.mockRejectedValueOnce(new Error('Network error'));

      await router.push('/calibre-corrections');
      await router.isReady();

      wrapper = mount(CalibreCorrections, {
        global: {
          plugins: [router],
        },
      });

      await wrapper.vm.$nextTick();
      await new Promise(r => setTimeout(r, 10));
      await wrapper.vm.$nextTick();

      expect(wrapper.find('[data-test="error"]').exists()).toBe(true);
      expect(wrapper.find('[data-test="content"]').exists()).toBe(false);
      expect(wrapper.find('[data-test="loading"]').exists()).toBe(false);
    });
  });

  describe('Author corrections section', () => {
    it('displays author corrections count', async () => {
      await mountComponent();

      const count = wrapper.find('[data-test="authors-count"]');
      expect(count.exists()).toBe(true);
      expect(count.text()).toBe('2');
    });

    it('displays author correction rows', async () => {
      await mountComponent();

      const rows = wrapper.findAll('[data-test="author-row"]');
      expect(rows.length).toBe(2);
      expect(rows[0].text()).toContain('Tropique de la violence');
      expect(rows[0].text()).toContain('Nathacha Appanah');
    });

    it('has copy button for each author row', async () => {
      await mountComponent();

      const copyButtons = wrapper.findAll('[data-test="copy-author-btn"]');
      expect(copyButtons.length).toBe(2);
    });

    it('has clickable links to livre detail page', async () => {
      await mountComponent();

      const links = wrapper.findAll('[data-test="author-livre-link"]');
      expect(links.length).toBe(2);
      expect(links[0].attributes('href')).toBe('/livre/abc');
    });

    it('invalidates cache when copy button is clicked', async () => {
      // Mock clipboard API
      Object.assign(navigator, {
        clipboard: { writeText: vi.fn().mockResolvedValue(undefined) },
      });
      axios.post.mockResolvedValueOnce({ data: { status: 'ok' } });

      await mountComponent();

      await wrapper.vm.copyToClipboard('Nathacha Appanah');
      await wrapper.vm.$nextTick();

      expect(axios.post).toHaveBeenCalledWith('/api/calibre/cache/invalidate');
    });
  });

  describe('Title corrections section', () => {
    it('displays title corrections count', async () => {
      await mountComponent();

      const count = wrapper.find('[data-test="titles-count"]');
      expect(count.exists()).toBe(true);
      expect(count.text()).toBe('1');
    });

    it('displays title correction rows', async () => {
      await mountComponent();

      const rows = wrapper.findAll('[data-test="title-row"]');
      expect(rows.length).toBe(1);
      expect(rows[0].text()).toContain('Chanson douce - Prix Goncourt 2016');
      expect(rows[0].text()).toContain('Chanson douce');
      expect(rows[0].text()).toContain('Leila Slimani');
    });

    it('has copy button for each title row', async () => {
      await mountComponent();

      const copyButtons = wrapper.findAll('[data-test="copy-title-btn"]');
      expect(copyButtons.length).toBe(1);
    });

    it('has clickable links to livre detail page for mongodb titles', async () => {
      await mountComponent();

      const links = wrapper.findAll('[data-test="title-livre-link"]');
      expect(links.length).toBe(1);
      expect(links[0].attributes('href')).toBe('/livre/ghi_title');
      expect(links[0].text()).toBe('Chanson douce');
    });

    it('invalidates cache when title copy button is clicked', async () => {
      Object.assign(navigator, {
        clipboard: { writeText: vi.fn().mockResolvedValue(undefined) },
      });
      axios.post.mockResolvedValueOnce({ data: { status: 'ok' } });

      await mountComponent();

      await wrapper.vm.copyToClipboard('Chanson douce');
      await wrapper.vm.$nextTick();

      expect(navigator.clipboard.writeText).toHaveBeenCalledWith('Chanson douce');
      expect(axios.post).toHaveBeenCalledWith('/api/calibre/cache/invalidate');
    });
  });

  describe('Missing tags section', () => {
    it('displays missing tags count', async () => {
      await mountComponent();

      const count = wrapper.find('[data-test="tags-count"]');
      expect(count.exists()).toBe(true);
      expect(count.text()).toBe('2');
    });

    it('displays missing tag rows with expected lmelp tags', async () => {
      await mountComponent();

      const rows = wrapper.findAll('[data-test="tag-row"]');
      expect(rows.length).toBe(2);
      expect(rows[0].text()).toContain('La seule histoire');
      expect(rows[0].text()).toContain('lmelp_240922');
      expect(rows[0].text()).toContain('Julian Barnes');

      // Second row has multiple missing tags
      expect(rows[1].text()).toContain('lmelp_230315');
      expect(rows[1].text()).toContain('lmelp_michel_crement');
    });

    it('has copy button for each tag row', async () => {
      await mountComponent();

      const copyButtons = wrapper.findAll('[data-test="copy-tags-btn"]');
      expect(copyButtons.length).toBe(2);
    });

    it('copy button copies all tags for Calibre', async () => {
      Object.assign(navigator, {
        clipboard: { writeText: vi.fn().mockResolvedValue(undefined) },
      });
      axios.post.mockResolvedValueOnce({ data: { status: 'ok' } });

      await mountComponent();

      // Click first tag row copy button
      const copyButtons = wrapper.findAll('[data-test="copy-tags-btn"]');
      await copyButtons[0].trigger('click');
      await wrapper.vm.$nextTick();

      expect(navigator.clipboard.writeText).toHaveBeenCalledWith('lmelp_240922');
      expect(axios.post).toHaveBeenCalledWith('/api/calibre/cache/invalidate');
    });

    it('has clickable links to livre detail page', async () => {
      await mountComponent();

      const links = wrapper.findAll('[data-test="tag-livre-link"]');
      expect(links.length).toBe(2);
      expect(links[0].attributes('href')).toBe('/livre/ghi');
    });
  });

  describe('Statistics section', () => {
    it('displays statistics grid', async () => {
      await mountComponent();

      const grid = wrapper.find('[data-test="statistics-grid"]');
      expect(grid.exists()).toBe(true);
    });

    it('displays correct statistics values', async () => {
      await mountComponent();

      expect(wrapper.find('[data-test="stat-total-matches"]').text()).toBe('45');
      expect(wrapper.find('[data-test="stat-author-corrections"]').text()).toBe('2');
      expect(wrapper.find('[data-test="stat-title-corrections"]').text()).toBe('1');
      expect(wrapper.find('[data-test="stat-missing-tags"]').text()).toBe('2');
    });
  });

  describe('Collapsible sections', () => {
    it('toggles section visibility on header click', async () => {
      await mountComponent();

      // Authors section is open by default
      expect(wrapper.findAll('[data-test="author-row"]').length).toBe(2);

      // Click header to collapse
      await wrapper.find('[data-test="section-authors-header"]').trigger('click');
      await wrapper.vm.$nextTick();

      // Rows should be hidden
      expect(wrapper.findAll('[data-test="author-row"]').length).toBe(0);

      // Click again to expand
      await wrapper.find('[data-test="section-authors-header"]').trigger('click');
      await wrapper.vm.$nextTick();

      // Rows should be visible again
      expect(wrapper.findAll('[data-test="author-row"]').length).toBe(2);
    });
  });

  describe('Statistics navigation', () => {
    it('clicking stat card opens collapsed section', async () => {
      await mountComponent();

      // Collapse authors section first
      await wrapper.find('[data-test="section-authors-header"]').trigger('click');
      await wrapper.vm.$nextTick();
      expect(wrapper.findAll('[data-test="author-row"]').length).toBe(0);

      // Click the authors stat card
      await wrapper.find('[data-test="stat-authors-link"]').trigger('click');
      await wrapper.vm.$nextTick();

      // Section should now be open
      expect(wrapper.findAll('[data-test="author-row"]').length).toBe(2);
    });

    it('has clickable stat cards for authors, titles, and tags', async () => {
      await mountComponent();

      expect(wrapper.find('[data-test="stat-authors-link"]').exists()).toBe(true);
      expect(wrapper.find('[data-test="stat-titles-link"]').exists()).toBe(true);
      expect(wrapper.find('[data-test="stat-tags-link"]').exists()).toBe(true);
    });
  });
});
