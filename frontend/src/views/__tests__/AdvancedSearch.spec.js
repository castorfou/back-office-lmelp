/**
 * Tests pour le composant AdvancedSearch.vue
 * Focus sur la navigation et la gestion de l'URL (Issue #219)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount } from '@vue/test-utils';
import { createRouter, createMemoryHistory } from 'vue-router';
import AdvancedSearch from '../AdvancedSearch.vue';
import { searchService } from '@/services/api';

// Mock des services API
vi.mock('@/services/api', () => ({
  searchService: {
    advancedSearch: vi.fn(),
  },
}));

// Mock du composant Navigation pour isoler le test
vi.mock('@/components/Navigation.vue', () => ({
  default: {
    name: 'Navigation',
    template: '<div />',
    props: ['pageTitle'],
  },
}));

const mockSearchResults = {
  results: {
    auteurs: [],
    auteurs_total_count: 0,
    livres: [],
    livres_total_count: 0,
    editeurs: [],
    episodes: [],
    episodes_total_count: 0,
    emissions: [
      {
        _id: 'emission1',
        emission_date: '20260213',
        search_context: 'Julian Barnes - Départ(s) : roman qui donne envie',
      },
    ],
    emissions_total_count: 1,
  },
  pagination: {
    page: 1,
    limit: 20,
    total_pages: 1,
  },
};

describe('AdvancedSearch.vue - Navigation URL (Issue #219)', () => {
  let router;

  beforeEach(() => {
    vi.resetAllMocks();

    router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/search', name: 'search', component: AdvancedSearch },
        { path: '/emissions/:date', name: 'emission', component: { template: '<div />' } },
      ],
    });

    searchService.advancedSearch.mockResolvedValue(mockSearchResults);
  });

  it('should update URL via Vue Router when performing a search', async () => {
    // Navigate to /search first
    await router.push('/search');

    const wrapper = mount(AdvancedSearch, {
      global: { plugins: [router] },
    });

    // Set a search query and perform search
    wrapper.vm.searchQuery = 'Roman qui donne envie';
    await wrapper.vm.performSearch();
    // Wait for router navigation to complete
    await new Promise((r) => setTimeout(r, 50));

    // The URL should be updated via Vue Router (not pushState)
    // so it appears in the router's current route
    const currentQuery = router.currentRoute.value.query.q;
    expect(currentQuery).toBe('Roman qui donne envie');
  });

  it('should restore search query from $route.query on created()', async () => {
    // Navigate to /search?q=Roman qui donne envie
    await router.push('/search?q=Roman%20qui%20donne%20envie');

    const wrapper = mount(AdvancedSearch, {
      global: { plugins: [router] },
    });

    // The component should read the query from $route.query, not window.location
    expect(wrapper.vm.searchQuery).toBe('Roman qui donne envie');
    // And should have triggered a search
    expect(searchService.advancedSearch).toHaveBeenCalledWith(
      'Roman qui donne envie',
      expect.any(Array),
      1,
      20,
    );
  });

  it('should preserve URL query in router history when navigating away and back', async () => {
    // Navigate to /search
    await router.push('/search');

    const wrapper = mount(AdvancedSearch, {
      global: { plugins: [router] },
    });

    // Perform a search to update URL to /search?q=Roman qui donne envie
    wrapper.vm.searchQuery = 'Roman qui donne envie';
    await wrapper.vm.performSearch();
    await new Promise((r) => setTimeout(r, 50));

    // Verify URL is /search?q=...
    expect(router.currentRoute.value.query.q).toBe('Roman qui donne envie');

    // Navigate to emission page (simulates user clicking a result)
    await router.push('/emissions/20260213');
    expect(router.currentRoute.value.path).toBe('/emissions/20260213');

    // Press back - Vue Router navigates back
    await router.back();
    await new Promise((r) => setTimeout(r, 10)); // allow router to settle

    // Should be back on /search with the query preserved
    expect(router.currentRoute.value.path).toBe('/search');
    expect(router.currentRoute.value.query.q).toBe('Roman qui donne envie');
  });

  it('should clear URL query when clearSearch is called', async () => {
    // Navigate to /search with a query
    await router.push('/search?q=Roman%20qui%20donne%20envie');

    const wrapper = mount(AdvancedSearch, {
      global: { plugins: [router] },
    });

    // Wait for created() async initialization to complete (performSearch from created())
    await new Promise((r) => setTimeout(r, 100));

    // Clear the search
    await wrapper.vm.clearSearch();
    await new Promise((r) => setTimeout(r, 50));

    // URL should have no query param
    expect(router.currentRoute.value.query.q).toBeUndefined();
  });
});
