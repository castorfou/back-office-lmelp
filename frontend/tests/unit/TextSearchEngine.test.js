/**
 * Tests unitaires pour le composant TextSearchEngine
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount } from '@vue/test-utils';
import TextSearchEngine from '../../src/components/TextSearchEngine.vue';

// Mock du service API
vi.mock('../../src/services/api.js', () => ({
  searchService: {
    search: vi.fn()
  }
}));

import { searchService } from '../../src/services/api.js';

describe('TextSearchEngine', () => {
  let wrapper;

  beforeEach(() => {
    vi.clearAllMocks();
    searchService.search.mockClear();
  });

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount();
    }
  });

  it('renders search input field', () => {
    wrapper = mount(TextSearchEngine);

    const searchInput = wrapper.find('input[type="text"]');
    expect(searchInput.exists()).toBe(true);
    expect(searchInput.attributes('placeholder')).toContain('Rechercher dans le contenu');
  });

  it('shows search icon', () => {
    wrapper = mount(TextSearchEngine);

    expect(wrapper.text()).toContain('🔍');
  });

  it('does not trigger search for less than 3 characters', async () => {
    wrapper = mount(TextSearchEngine);

    const input = wrapper.find('input');
    await input.setValue('ab');

    // Attendre le debounce
    await new Promise(resolve => setTimeout(resolve, 400));

    expect(searchService.search).not.toHaveBeenCalled();
  });

  it('triggers search after 3 characters with debounce', async () => {
    searchService.search.mockResolvedValue({
      query: 'camus',
      results: {
        auteurs: [],
        livres: [],
        editeurs: [],
        episodes: []
      }
    });

    wrapper = mount(TextSearchEngine);

    const input = wrapper.find('input');
    await input.setValue('camus');

    // Attendre le debounce (300ms)
    await new Promise(resolve => setTimeout(resolve, 400));

    expect(searchService.search).toHaveBeenCalledWith('camus', 10);
  });

  it('displays loading state during search', async () => {
    // Mock d'une promesse qui ne se résout pas immédiatement
    let resolveSearch;
    const searchPromise = new Promise(resolve => {
      resolveSearch = resolve;
    });
    searchService.search.mockReturnValue(searchPromise);

    wrapper = mount(TextSearchEngine);

    const input = wrapper.find('input');
    await input.setValue('test');

    // Déclencher la recherche
    await new Promise(resolve => setTimeout(resolve, 400));

    // Vérifier l'état de loading
    expect(wrapper.text()).toContain('Recherche en cours');

    // Résoudre la promesse
    resolveSearch({
      query: 'test',
      results: { auteurs: [], livres: [], editeurs: [], episodes: [] }
    });
    await wrapper.vm.$nextTick();
  });

  it('displays search results by categories', async () => {
    const mockResults = {
      query: 'camus',
      results: {
        auteurs: [
          { nom: 'Albert Camus', score: 1.0, match_type: 'exact' }
        ],
        livres: [
          { titre: 'L\'Étranger', score: 0.8, match_type: 'partial' }
        ],
        editeurs: [],
        episodes: [
          { titre: 'Épisode sur Camus', score: 0.9, match_type: 'partial', date: '2024-03-15' }
        ],
        episodes_total_count: 1
      }
    };

    searchService.search.mockResolvedValue(mockResults);

    wrapper = mount(TextSearchEngine);

    const input = wrapper.find('input');
    await input.setValue('camus');

    await new Promise(resolve => setTimeout(resolve, 400));
    await wrapper.vm.$nextTick();

    // Vérifier l'affichage des catégories
    expect(wrapper.text()).toContain('👤 AUTEURS (1)');
    expect(wrapper.text()).toContain('📚 LIVRES (1)');
    // Note: 🏢 ÉDITEURS (0) n'apparaît plus car les catégories vides sont masquées
    expect(wrapper.text()).toContain('🎙️ ÉPISODES (1/1)'); // Nouveau format avec count total

    // Vérifier les résultats
    expect(wrapper.text()).toContain('Albert Camus');
    expect(wrapper.text()).toContain('L\'Étranger');
    expect(wrapper.text()).toContain('Épisode sur Camus');
  });

  it('displays book results with author name when available', async () => {
    const mockResults = {
      query: 'simone',
      results: {
        auteurs: [],
        livres: [
          {
            titre: 'Simone Emonet',
            auteur_nom: 'Catherine Millet',
            auteur_id: '123',
            editeur: 'Gallimard'
          }
        ],
        editeurs: [],
        episodes: [],
        episodes_total_count: 0
      }
    };

    searchService.search.mockResolvedValue(mockResults);

    wrapper = mount(TextSearchEngine);

    const input = wrapper.find('input');
    await input.setValue('simone');

    await new Promise(resolve => setTimeout(resolve, 400));
    await wrapper.vm.$nextTick();

    // Vérifier que le livre est affiché avec le format "auteur - titre"
    expect(wrapper.text()).toContain('Catherine Millet - Simone Emonet');
    expect(wrapper.text()).not.toMatch(/^Simone Emonet$/);
  });

  it('shows no results message when search returns empty', async () => {
    const mockResults = {
      query: 'xyz123',
      results: {
        auteurs: [],
        livres: [],
        editeurs: [],
        episodes: []
      }
    };

    searchService.search.mockResolvedValue(mockResults);

    wrapper = mount(TextSearchEngine);

    const input = wrapper.find('input');
    await input.setValue('xyz123');

    await new Promise(resolve => setTimeout(resolve, 400));
    await wrapper.vm.$nextTick();

    expect(wrapper.text()).toContain('Aucun résultat trouvé');
  });

  it('handles search errors gracefully', async () => {
    searchService.search.mockRejectedValue(new Error('Network error'));

    wrapper = mount(TextSearchEngine);

    const input = wrapper.find('input');
    await input.setValue('test');

    await new Promise(resolve => setTimeout(resolve, 400));
    await wrapper.vm.$nextTick();

    expect(wrapper.text()).toContain('Erreur lors de la recherche');
  });

  it('clears results when input is cleared', async () => {
    // D'abord effectuer une recherche
    searchService.search.mockResolvedValue({
      query: 'camus',
      results: {
        auteurs: [{ nom: 'Albert Camus', score: 1.0, match_type: 'exact' }],
        livres: [],
        editeurs: [],
        episodes: []
      }
    });

    wrapper = mount(TextSearchEngine);

    const input = wrapper.find('input');
    await input.setValue('camus');
    await new Promise(resolve => setTimeout(resolve, 400));
    await wrapper.vm.$nextTick();

    // Vérifier que les résultats sont affichés
    expect(wrapper.text()).toContain('Albert Camus');

    // Vider l'input
    await input.setValue('');
    await wrapper.vm.$nextTick();

    // Vérifier que les résultats sont cachés
    expect(wrapper.text()).not.toContain('Albert Camus');
    expect(wrapper.text()).not.toContain('👤 AUTEURS');
  });

  it('respects the limit prop when provided', async () => {
    wrapper = mount(TextSearchEngine, {
      props: {
        limit: 5
      }
    });

    const input = wrapper.find('input');
    await input.setValue('test');

    await new Promise(resolve => setTimeout(resolve, 400));

    expect(searchService.search).toHaveBeenCalledWith('test', 5);
  });
});
