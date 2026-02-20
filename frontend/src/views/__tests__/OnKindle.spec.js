/**
 * Tests TDD pour OnKindle.vue (Issue #216)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { flushPromises } from '@vue/test-utils';
import { mount } from '@vue/test-utils';
import { createRouter, createMemoryHistory } from 'vue-router';
import axios from 'axios';

// Mock axios
vi.mock('axios');

// Import after mocks
import OnKindle from '../OnKindle.vue';

const mockOnKindleData = {
  total: 3,
  books: [
    {
      calibre_id: 1,
      titre: 'Le Lambeau',
      auteurs: ['Philippe Lançon'],
      calibre_rating: 10,
      calibre_read: true,
      mongo_livre_id: 'abc123',
      auteur_id: 'aut1',
      note_moyenne: 9.5,
      url_babelio: 'https://www.babelio.com/livres/Lancon-Le-Lambeau/1036944',
    },
    {
      calibre_id: 2,
      titre: 'La Serpe',
      auteurs: ['Philippe Jaenada'],
      calibre_rating: 8,
      calibre_read: false,
      mongo_livre_id: 'def456',
      auteur_id: 'aut2',
      note_moyenne: 8.0,
      url_babelio: 'https://www.babelio.com/livres/Jaenada-La-Serpe/1357073',
    },
    {
      calibre_id: 3,
      titre: 'Livre Non MongoDB',
      auteurs: ['Auteur Inconnu'],
      calibre_rating: null,
      calibre_read: null,
      mongo_livre_id: null,
      auteur_id: null,
      note_moyenne: null,
      url_babelio: null,
    },
  ],
};

describe('OnKindle.vue', () => {
  let wrapper;
  let router;

  beforeEach(() => {
    vi.resetAllMocks();

    router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/onkindle', name: 'OnKindle', component: OnKindle },
        { path: '/livre/:id', name: 'LivreDetail', component: { template: '<div />' } },
        { path: '/auteur/:id', name: 'AuteurDetail', component: { template: '<div />' } },
        { path: '/', name: 'Dashboard', component: { template: '<div />' } },
      ],
    });
  });

  async function mountWithData(apiResponse = mockOnKindleData) {
    axios.get.mockResolvedValueOnce({ data: apiResponse });

    wrapper = mount(OnKindle, {
      global: {
        plugins: [router],
      },
    });

    await router.isReady();
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();

    return wrapper;
  }

  describe('Page structure', () => {
    it('renders a table with auteur, titre, note, babelio columns in that order', async () => {
      await mountWithData();

      const headers = wrapper.findAll('th');
      const headerTexts = headers.map(h => h.text());
      expect(headerTexts.some(t => t.includes('Auteur'))).toBe(true);
      expect(headerTexts.some(t => t.includes('Titre'))).toBe(true);
      expect(headerTexts.some(t => t.includes('Note'))).toBe(true);
      expect(headerTexts.some(t => t.includes('Babelio'))).toBe(true);
      // Auteur before Titre
      const auteurIdx = headerTexts.findIndex(t => t.includes('Auteur'));
      const titreIdx = headerTexts.findIndex(t => t.includes('Titre'));
      expect(auteurIdx).toBeLessThan(titreIdx);
    });

    it('shows the total number of books', async () => {
      await mountWithData();

      expect(wrapper.text()).toContain('3');
    });

    it('displays all onkindle books as table rows', async () => {
      await mountWithData();

      const rows = wrapper.findAll('[data-test="onkindle-row"]');
      expect(rows).toHaveLength(3);
    });
  });

  describe('Author column (Emissions style)', () => {
    it('renders auteur as router-link when auteur_id is present', async () => {
      await mountWithData();

      const auteurLinks = wrapper.findAll('[data-test="auteur-link"]');
      expect(auteurLinks).toHaveLength(2);
      // Default titre-asc sort: La Serpe (aut2) before Le Lambeau (aut1)
      expect(auteurLinks[0].text()).toBe('Philippe Jaenada');
      expect(auteurLinks[0].attributes('href')).toContain('/auteur/aut2');
    });

    it('renders auteur as plain text when auteur_id is null', async () => {
      await mountWithData();

      const auteurPlain = wrapper.findAll('[data-test="auteur-plain"]');
      expect(auteurPlain).toHaveLength(1);
      expect(auteurPlain[0].text()).toBe('Auteur Inconnu');
    });
  });

  describe('Title column (Emissions style)', () => {
    it('renders titre as router-link when mongo_livre_id is present', async () => {
      await mountWithData();

      const titreLinks = wrapper.findAll('[data-test="titre-link"]');
      expect(titreLinks).toHaveLength(2);
      // Default titre-asc: La Serpe first
      expect(titreLinks[0].text()).toBe('La Serpe');
      expect(titreLinks[0].attributes('href')).toContain('/livre/def456');
    });

    it('renders titre as plain text when mongo_livre_id is null', async () => {
      await mountWithData();

      const titrePlain = wrapper.findAll('[data-test="titre-plain"]');
      expect(titrePlain).toHaveLength(1);
      expect(titrePlain[0].text()).toBe('Livre Non MongoDB');
    });
  });

  describe('Note column', () => {
    it('shows note_moyenne when available', async () => {
      await mountWithData();

      const noteElements = wrapper.findAll('[data-test="note-badge"]');
      expect(noteElements).toHaveLength(2); // 2 books have note_moyenne
    });

    it('shows empty/dash when note_moyenne is null', async () => {
      await mountWithData();

      const noteMissing = wrapper.findAll('[data-test="note-missing"]');
      expect(noteMissing).toHaveLength(1);
    });
  });

  describe('Babelio column', () => {
    it('shows babelio link when url_babelio is present', async () => {
      await mountWithData();

      const babelioLinks = wrapper.findAll('[data-test="babelio-link"]');
      expect(babelioLinks).toHaveLength(2);
      // With default titre-asc sort: La Serpe first
      expect(babelioLinks[0].attributes('href')).toBe(
        'https://www.babelio.com/livres/Jaenada-La-Serpe/1357073'
      );
    });

    it('shows nothing in babelio column when url_babelio is null', async () => {
      await mountWithData();

      const babelioMissing = wrapper.findAll('[data-test="babelio-missing"]');
      expect(babelioMissing).toHaveLength(1);
    });
  });

  describe('Error handling', () => {
    it('shows error message when API fails', async () => {
      axios.get.mockRejectedValueOnce(new Error('Network error'));

      wrapper = mount(OnKindle, {
        global: { plugins: [router] },
      });
      await router.isReady();
      await wrapper.vm.$nextTick();
      await wrapper.vm.$nextTick();

      expect(wrapper.text()).toContain('Network error');
    });

    it('shows unavailable message when Calibre is not available (503)', async () => {
      axios.get.mockRejectedValueOnce({
        response: { status: 503, data: { error: 'Calibre non disponible' } },
      });

      wrapper = mount(OnKindle, {
        global: { plugins: [router] },
      });
      await router.isReady();
      await wrapper.vm.$nextTick();
      await wrapper.vm.$nextTick();

      expect(wrapper.text()).toContain('Calibre');
    });
  });

  describe('Loading state', () => {
    it('shows loading state initially', async () => {
      axios.get.mockImplementation(() => new Promise(() => {})); // never resolves

      wrapper = mount(OnKindle, {
        global: { plugins: [router] },
      });
      await router.isReady();
      await wrapper.vm.$nextTick();

      expect(wrapper.text()).toMatch(/chargement/i);
    });
  });

  describe('Column sorting', () => {
    it('headers have a clickable sort indicator', async () => {
      await mountWithData();

      // Auteur, Titre, Note are sortable (Babelio is not)
      const headers = wrapper.findAll('th[data-test]');
      expect(headers.length).toBeGreaterThanOrEqual(3);
    });

    it('sorts by titre ascending by default', async () => {
      await mountWithData();

      const rows = wrapper.findAll('[data-test="onkindle-row"]');
      // Ascending alphabetical: La Serpe < Le Lambeau < Livre Non MongoDB
      expect(rows[0].text()).toContain('La Serpe');
      expect(rows[2].text()).toContain('Livre Non MongoDB');
    });

    it('clicking titre header sorts descending on second click', async () => {
      await mountWithData();

      // Default is titre-asc, one click → desc
      const titreHeader = wrapper.find('th[data-test="sort-titre"]');
      await titreHeader.trigger('click');
      await wrapper.vm.$nextTick();

      const rows = wrapper.findAll('[data-test="onkindle-row"]');
      // Descending: Livre Non MongoDB first
      expect(rows[0].text()).toContain('Livre Non MongoDB');
    });

    it('clicking auteur header sorts by author name', async () => {
      await mountWithData();

      const auteurHeader = wrapper.find('th[data-test="sort-auteur"]');
      await auteurHeader.trigger('click'); // ascending by auteur

      const rows = wrapper.findAll('[data-test="onkindle-row"]');
      // Ascending auteur: Auteur Inconnu < Philippe Jaenada < Philippe Lançon
      expect(rows[0].text()).toContain('Auteur Inconnu');
    });

    it('clicking note header sorts by note descending first', async () => {
      await mountWithData();

      const noteHeader = wrapper.find('th[data-test="sort-note"]');
      await noteHeader.trigger('click'); // descending (highest first)

      const rows = wrapper.findAll('[data-test="onkindle-row"]');
      // Descending: 9.5 first (Le Lambeau)
      expect(rows[0].text()).toContain('Le Lambeau');
    });

    it('shows sort direction indicator on active column', async () => {
      await mountWithData();

      // Click auteur sort header
      const auteurHeader = wrapper.find('th[data-test="sort-auteur"]');
      await auteurHeader.trigger('click');

      expect(auteurHeader.classes()).toContain('sort-active');
    });

    it('updates URL query params when sort changes', async () => {
      await mountWithData();

      await wrapper.vm.sortBy('auteur');
      await wrapper.vm.$nextTick();

      expect(router.currentRoute.value.query.sort).toBe('auteur');
      expect(router.currentRoute.value.query.dir).toBe('asc');
    });

    it('reads sort from URL query params on mount', async () => {
      axios.get.mockResolvedValueOnce({ data: mockOnKindleData });

      await router.push({ path: '/onkindle', query: { sort: 'note', dir: 'desc' } });
      await router.isReady();

      wrapper = mount(OnKindle, { global: { plugins: [router] } });
      await wrapper.vm.$nextTick();
      await wrapper.vm.$nextTick();

      expect(wrapper.vm.sortKey).toBe('note');
      expect(wrapper.vm.sortDir).toBe('desc');
    });

    it('restores sort state after page reload (URL params persist)', async () => {
      axios.get.mockResolvedValueOnce({ data: mockOnKindleData });

      await router.push({ path: '/onkindle', query: { sort: 'auteur', dir: 'asc' } });
      await router.isReady();

      wrapper = mount(OnKindle, { global: { plugins: [router] } });
      await flushPromises();

      expect(wrapper.vm.sortKey).toBe('auteur');
      const rows = wrapper.findAll('[data-test="onkindle-row"]');
      expect(rows.length).toBe(3);
      // Ascending auteur: Auteur Inconnu first
      expect(rows[0].text()).toContain('Auteur Inconnu');
    });

    it('sorts accent titles correctly — À prendre before Zola (accent-insensitive)', async () => {
      const dataWithAccent = {
        total: 2,
        books: [
          {
            calibre_id: 10,
            titre: 'Zola et son œuvre',
            auteurs: ['Yves Zola'],
            calibre_rating: null,
            calibre_read: null,
            mongo_livre_id: null,
            auteur_id: null,
            note_moyenne: null,
            url_babelio: null,
          },
          {
            calibre_id: 11,
            titre: 'À prendre ou à laisser',
            auteurs: ['Agathe Arnaud'],
            calibre_rating: null,
            calibre_read: null,
            mongo_livre_id: null,
            auteur_id: null,
            note_moyenne: null,
            url_babelio: null,
          },
        ],
      };
      await mountWithData(dataWithAccent);

      // Default is titre-asc: "À prendre" should come BEFORE "Zola"
      const rows = wrapper.findAll('[data-test="onkindle-row"]');
      expect(rows[0].text()).toContain('À prendre ou à laisser');
      expect(rows[1].text()).toContain('Zola');
    });

    it('sorts accent authors correctly — Álvarez before Zola (accent-insensitive)', async () => {
      const dataWithAccentAuteur = {
        total: 2,
        books: [
          {
            calibre_id: 20,
            titre: 'Livre Z',
            auteurs: ['Zola Émile'],
            calibre_rating: null,
            calibre_read: null,
            mongo_livre_id: null,
            auteur_id: null,
            note_moyenne: null,
            url_babelio: null,
          },
          {
            calibre_id: 21,
            titre: 'Livre A',
            auteurs: ['Álvarez Maria'],
            calibre_rating: null,
            calibre_read: null,
            mongo_livre_id: null,
            auteur_id: null,
            note_moyenne: null,
            url_babelio: null,
          },
        ],
      };
      await mountWithData(dataWithAccentAuteur);

      // Sort by auteur ascending
      await wrapper.vm.sortBy('auteur');
      await wrapper.vm.$nextTick();

      // Álvarez should come BEFORE Zola
      const rows = wrapper.findAll('[data-test="onkindle-row"]');
      expect(rows[0].text()).toContain('Álvarez');
      expect(rows[1].text()).toContain('Zola');
    });
  });
});
