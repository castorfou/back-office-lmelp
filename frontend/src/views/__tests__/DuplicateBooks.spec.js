import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount } from '@vue/test-utils';
import { createRouter, createMemoryHistory } from 'vue-router';
import DuplicateBooks from '../DuplicateBooks.vue';
import axios from 'axios';

vi.mock('axios');

describe('DuplicateBooks.vue', () => {
  let wrapper;
  let router;

  const mockStatistics = {
    total_groups: 10,
    total_duplicates: 15,
    merged_count: 2,
    pending_count: 8,
    skipped_count: 0
  };

  const mockDuplicateGroups = [
    {
      url_babelio: 'https://www.babelio.com/livres/book1',
      count: 2,
      book_ids: ['id1', 'id2'],
      titres: ['Titre 1', 'Titre 1 variant'],
      auteur_ids: ['author1', 'author1']
    },
    {
      url_babelio: 'https://www.babelio.com/livres/book2',
      count: 3,
      book_ids: ['id3', 'id4', 'id5'],
      titres: ['Titre 2', 'Titre 2 v2', 'Titre 2 v3'],
      auteur_ids: ['author2', 'author2', 'author2']
    }
  ];

  beforeEach(async () => {
    vi.clearAllMocks();
    vi.resetAllMocks();

    // Default mocks for axios
    axios.get = vi.fn();
    axios.post = vi.fn();

    router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/duplicates', component: DuplicateBooks }
      ]
    });

    await router.push('/duplicates');
  });

  it('loads statistics and groups on mount', async () => {
    axios.get.mockImplementation((url) => {
      if (url.includes('/statistics')) {
        return Promise.resolve({ data: mockStatistics });
      }
      if (url.includes('/groups')) {
        return Promise.resolve({ data: mockDuplicateGroups });
      }
      return Promise.reject(new Error('Unknown URL'));
    });

    wrapper = mount(DuplicateBooks, {
      global: { plugins: [router] }
    });

    await new Promise(resolve => setTimeout(resolve, 50));
    await wrapper.vm.$nextTick();

    expect(axios.get).toHaveBeenCalledTimes(2);
    expect(wrapper.vm.statistics).toEqual(mockStatistics);
    expect(wrapper.vm.duplicateGroups).toEqual(mockDuplicateGroups);
  });

  it('displays loading state while fetching data', async () => {
    axios.get.mockImplementation(() =>
      new Promise(resolve => setTimeout(() => resolve({ data: [] }), 100))
    );

    wrapper = mount(DuplicateBooks, {
      global: { plugins: [router] }
    });

    await wrapper.vm.$nextTick();
    expect(wrapper.text()).toContain('Chargement');

    await new Promise(resolve => setTimeout(resolve, 150));
    await wrapper.vm.$nextTick();
  });

  it('displays error message on fetch failure', async () => {
    axios.get.mockRejectedValue(new Error('Network error'));

    wrapper = mount(DuplicateBooks, {
      global: { plugins: [router] }
    });

    await new Promise(resolve => setTimeout(resolve, 50));
    await wrapper.vm.$nextTick();

    expect(wrapper.vm.error).toContain('Erreur');
  });

  it('displays statistics card with correct values', async () => {
    axios.get.mockImplementation((url) => {
      if (url.includes('/statistics')) {
        return Promise.resolve({ data: mockStatistics });
      }
      if (url.includes('/groups')) {
        return Promise.resolve({ data: mockDuplicateGroups });
      }
      return Promise.reject(new Error('Unknown URL'));
    });

    wrapper = mount(DuplicateBooks, {
      global: { plugins: [router] }
    });

    await new Promise(resolve => setTimeout(resolve, 50));
    await wrapper.vm.$nextTick();

    const statsCard = wrapper.find('.statistics-card');
    expect(statsCard.exists()).toBe(true);
    expect(statsCard.text()).toContain('10'); // total_groups
    expect(statsCard.text()).toContain('15'); // total_duplicates
  });

  it('displays duplicate groups list', async () => {
    axios.get.mockImplementation((url) => {
      if (url.includes('/statistics')) {
        return Promise.resolve({ data: mockStatistics });
      }
      if (url.includes('/groups')) {
        return Promise.resolve({ data: mockDuplicateGroups });
      }
      return Promise.reject(new Error('Unknown URL'));
    });

    wrapper = mount(DuplicateBooks, {
      global: { plugins: [router] }
    });

    await new Promise(resolve => setTimeout(resolve, 50));
    await wrapper.vm.$nextTick();

    const groups = wrapper.findAll('.group-card');
    expect(groups).toHaveLength(2);
    expect(groups[0].text()).toContain('Titre 1');
    expect(groups[1].text()).toContain('Titre 2');
  });

  it('toggles skip checkbox correctly', async () => {
    axios.get.mockImplementation((url) => {
      if (url.includes('/statistics')) {
        return Promise.resolve({ data: mockStatistics });
      }
      if (url.includes('/groups')) {
        return Promise.resolve({ data: mockDuplicateGroups });
      }
      return Promise.reject(new Error('Unknown URL'));
    });

    wrapper = mount(DuplicateBooks, {
      global: { plugins: [router] }
    });

    await new Promise(resolve => setTimeout(resolve, 50));
    await wrapper.vm.$nextTick();

    const url = mockDuplicateGroups[0].url_babelio;

    // Initially not in skip list
    expect(wrapper.vm.skipList).not.toContain(url);

    // Toggle skip
    await wrapper.vm.toggleSkip(url);
    expect(wrapper.vm.skipList).toContain(url);

    // Toggle again
    await wrapper.vm.toggleSkip(url);
    expect(wrapper.vm.skipList).not.toContain(url);
  });

  it('merges a group successfully', async () => {
    axios.get.mockImplementation((url) => {
      if (url.includes('/statistics')) {
        return Promise.resolve({ data: mockStatistics });
      }
      if (url.includes('/groups')) {
        return Promise.resolve({ data: mockDuplicateGroups });
      }
      return Promise.reject(new Error('Unknown URL'));
    });

    const mockMergeResponse = {
      status: 'success',
      result: {
        success: true,
        primary_book_id: 'id1',
        deleted_book_ids: ['id2'],
        episodes_merged: 3,
        avis_critiques_merged: 2
      }
    };

    axios.post.mockResolvedValue({ data: mockMergeResponse });

    wrapper = mount(DuplicateBooks, {
      global: { plugins: [router] }
    });

    await new Promise(resolve => setTimeout(resolve, 50));
    await wrapper.vm.$nextTick();

    const group = mockDuplicateGroups[0];
    await wrapper.vm.mergeGroup(group);

    expect(axios.post).toHaveBeenCalledWith(
      expect.stringContaining('/merge'),
      {
        url_babelio: group.url_babelio,
        book_ids: group.book_ids
      }
    );

    expect(wrapper.vm.mergeResults[group.url_babelio]).toBeDefined();
    expect(wrapper.vm.mergeResults[group.url_babelio].success).toBe(true);
  });

  it('handles merge error correctly', async () => {
    axios.get.mockImplementation((url) => {
      if (url.includes('/statistics')) {
        return Promise.resolve({ data: mockStatistics });
      }
      if (url.includes('/groups')) {
        return Promise.resolve({ data: mockDuplicateGroups });
      }
      return Promise.reject(new Error('Unknown URL'));
    });

    axios.post.mockRejectedValue({
      response: {
        data: {
          detail: 'auteur_id mismatch'
        }
      }
    });

    wrapper = mount(DuplicateBooks, {
      global: { plugins: [router] }
    });

    await new Promise(resolve => setTimeout(resolve, 50));
    await wrapper.vm.$nextTick();

    const group = mockDuplicateGroups[0];
    await wrapper.vm.mergeGroup(group);

    expect(wrapper.vm.mergeResults[group.url_babelio]).toBeDefined();
    expect(wrapper.vm.mergeResults[group.url_babelio].success).toBe(false);
    expect(wrapper.vm.mergeResults[group.url_babelio].error).toContain('auteur_id');
  });

  it('calculates batch progress percentage correctly', async () => {
    axios.get.mockImplementation((url) => {
      if (url.includes('/statistics')) {
        return Promise.resolve({ data: mockStatistics });
      }
      if (url.includes('/groups')) {
        return Promise.resolve({ data: [] });
      }
      return Promise.reject(new Error('Unknown URL'));
    });

    wrapper = mount(DuplicateBooks, {
      global: { plugins: [router] }
    });

    await new Promise(resolve => setTimeout(resolve, 50));
    await wrapper.vm.$nextTick();

    wrapper.vm.batchProgress = { current: 5, total: 10 };
    expect(wrapper.vm.batchProgressPercent).toBe(50);

    wrapper.vm.batchProgress = { current: 0, total: 0 };
    expect(wrapper.vm.batchProgressPercent).toBe(0);
  });

  it('displays empty state when no duplicates', async () => {
    axios.get.mockImplementation((url) => {
      if (url.includes('/statistics')) {
        return Promise.resolve({ data: { ...mockStatistics, total_groups: 0 } });
      }
      if (url.includes('/groups')) {
        return Promise.resolve({ data: [] });
      }
      return Promise.reject(new Error('Unknown URL'));
    });

    wrapper = mount(DuplicateBooks, {
      global: { plugins: [router] }
    });

    await new Promise(resolve => setTimeout(resolve, 50));
    await wrapper.vm.$nextTick();

    expect(wrapper.find('.empty-state').exists()).toBe(true);
    expect(wrapper.text()).toContain('Aucun doublon');
  });

  it('disables merge button during processing', async () => {
    axios.get.mockImplementation((url) => {
      if (url.includes('/statistics')) {
        return Promise.resolve({ data: mockStatistics });
      }
      if (url.includes('/groups')) {
        return Promise.resolve({ data: mockDuplicateGroups });
      }
      return Promise.reject(new Error('Unknown URL'));
    });

    wrapper = mount(DuplicateBooks, {
      global: { plugins: [router] }
    });

    await new Promise(resolve => setTimeout(resolve, 50));
    await wrapper.vm.$nextTick();

    wrapper.vm.processingGroup = mockDuplicateGroups[0].url_babelio;
    await wrapper.vm.$nextTick();

    const mergeButtons = wrapper.findAll('.btn-merge');
    expect(mergeButtons[0].element.disabled).toBe(true);
  });
});
