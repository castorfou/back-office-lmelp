/**
 * Tests unitaires pour la vue Calibre Library (TDD)
 *
 * Ces tests vérifient:
 * - Détection et affichage du statut Calibre (disponible/non disponible)
 * - Affichage de la liste des livres avec pagination
 * - Filtres (Lu/Non lu)
 * - Affichage des statistiques
 * - Gestion des erreurs
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { createRouter, createWebHistory } from 'vue-router';

// Mock du service API
vi.mock('../../src/services/api.js', () => ({
  calibreService: {
    getStatus: vi.fn(),
    getBooks: vi.fn(),
    getStatistics: vi.fn()
  }
}));

import { calibreService } from '../../src/services/api.js';
import CalibreLibrary from '../../src/views/CalibreLibrary.vue';

describe('CalibreLibrary', () => {
  let wrapper;
  let router;

  beforeEach(async () => {
    vi.clearAllMocks();

    // Default mock for getStatistics to avoid undefined errors
    calibreService.getStatistics.mockResolvedValue({
      books_read: 299
    });

    router = createRouter({
      history: createWebHistory(),
      routes: [
        { path: '/', component: { template: '<div />' } },
        { path: '/calibre', component: CalibreLibrary },
        { path: '/livre/:id', component: { template: '<div />' } }
      ]
    });
    await router.push('/calibre');
  });

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount();
    }
  });

  describe('Service Detection', () => {
    it('should display unavailable message when Calibre is not configured', async () => {
      // Arrange
      calibreService.getStatus.mockResolvedValue({
        available: false,
        error: 'CALIBRE_LIBRARY_PATH not configured'
      });

      // Act
      wrapper = mount(CalibreLibrary, {
        global: {
          plugins: [router]
        }
      });

      await flushPromises();

      // Assert
      expect(wrapper.text()).toContain('Calibre non disponible');
      expect(wrapper.text()).toContain('CALIBRE_LIBRARY_PATH not configured');
      expect(wrapper.find('[data-testid="books-list"]').exists()).toBe(false);
    });

    it('should load and display books when Calibre is available', async () => {
      // Arrange
      calibreService.getStatus.mockResolvedValue({
        available: true,
        library_path: '/calibre',
        total_books: 516,
        virtual_library_tag: 'guillaume'
      });

      calibreService.getBooks.mockResolvedValue({
        total: 516,
        offset: 0,
        limit: 50,
        books: [
          {
            id: 3,
            title: 'Le Silence de la mer',
            authors: ['Vercors'],
            isbn: '978-2-7011-1234-5',
            rating: 8,
            read: true
          }
        ]
      });

      // Act
      wrapper = mount(CalibreLibrary, {
        global: {
          plugins: [router]
        }
      });

      await flushPromises();

      // Assert
      expect(wrapper.find('[data-testid="books-list"]').exists()).toBe(true);
      expect(wrapper.text()).toContain('Le Silence de la mer');
      expect(wrapper.text()).toContain('Vercors');
      expect(calibreService.getBooks).toHaveBeenCalled();
    });

    it('should display book counts in filter buttons', async () => {
      // Arrange
      calibreService.getStatus.mockResolvedValue({
        available: true,
        library_path: '/calibre',
        total_books: 516,
        virtual_library_tag: 'guillaume'
      });

      calibreService.getBooks.mockResolvedValue({
        total: 516,
        offset: 0,
        limit: 50,
        books: []
      });

      calibreService.getStatistics.mockResolvedValue({
        books_read: 299
      });

      // Act
      wrapper = mount(CalibreLibrary, {
        global: {
          plugins: [router]
        }
      });

      await flushPromises();

      // Assert - should show total, read, and computed unread counts
      expect(wrapper.text()).toContain('Tous (516)');
      expect(wrapper.text()).toContain('Lus (299)');
      expect(wrapper.text()).toContain('Non lus (217)'); // 516 - 299 = 217
    });
  });

  describe('Books List', () => {
    beforeEach(() => {
      calibreService.getStatus.mockResolvedValue({
        available: true,
        library_path: '/calibre',
        total_books: 516
      });
    });

    it('should display book details correctly', async () => {
      // Arrange
      calibreService.getBooks.mockResolvedValue({
        total: 1,
        offset: 0,
        limit: 50,
        books: [
          {
            id: 3,
            title: 'Le Silence de la mer',
            authors: ['Vercors'],
            isbn: '978-2-7011-1234-5',
            rating: 8,
            tags: ['guillaume', 'roman'],
            read: true,
            publisher: 'Albin Michel'
          }
        ]
      });

      // Act
      wrapper = mount(CalibreLibrary, {
        global: {
          plugins: [router]
        }
      });

      await flushPromises();

      // Assert
      const booksList = wrapper.find('[data-testid="books-list"]');
      expect(booksList.text()).toContain('Le Silence de la mer');
      expect(booksList.text()).toContain('Vercors');
      expect(booksList.text()).toContain('978-2-7011-1234-5');
      expect(booksList.text()).toContain('Albin Michel');
    });

    it('should display read status badge', async () => {
      // Arrange
      calibreService.getBooks.mockResolvedValue({
        total: 2,
        offset: 0,
        limit: 50,
        books: [
          {
            id: 1,
            title: 'Livre lu',
            authors: ['Auteur 1'],
            read: true
          },
          {
            id: 2,
            title: 'Livre non lu',
            authors: ['Auteur 2'],
            read: false
          }
        ]
      });

      // Act
      wrapper = mount(CalibreLibrary, {
        global: {
          plugins: [router]
        }
      });

      await flushPromises();

      // Assert
      const booksList = wrapper.find('[data-testid="books-list"]');
      expect(booksList.html()).toContain('read-badge');
    });
  });

  describe('Filters', () => {
    beforeEach(() => {
      calibreService.getStatus.mockResolvedValue({
        available: true,
        library_path: '/calibre',
        total_books: 516
      });

      calibreService.getBooks.mockResolvedValue({
        total: 516,
        offset: 0,
        limit: 50,
        books: []
      });
    });

    it('should have filter buttons for read status', async () => {
      // Act
      wrapper = mount(CalibreLibrary, {
        global: {
          plugins: [router]
        }
      });

      await flushPromises();

      // Assert
      expect(wrapper.find('[data-testid="filter-all"]').exists()).toBe(true);
      expect(wrapper.find('[data-testid="filter-read"]').exists()).toBe(true);
      expect(wrapper.find('[data-testid="filter-unread"]').exists()).toBe(true);
    });

    it('should filter read books when clicking "Lus" button', async () => {
      // Arrange
      calibreService.getBooks.mockResolvedValue({
        total: 4,
        books: [
          { id: 1, title: 'Book 1', authors: ['A'], read: true },
          { id: 2, title: 'Book 2', authors: ['B'], read: false },
          { id: 3, title: 'Book 3', authors: ['C'], read: true },
          { id: 4, title: 'Book 4', authors: ['D'], read: null }
        ]
      });

      wrapper = mount(CalibreLibrary, {
        global: {
          plugins: [router]
        }
      });

      await flushPromises();

      // Act
      const readButton = wrapper.find('[data-testid="filter-read"]');
      await readButton.trigger('click');
      await wrapper.vm.$nextTick();

      // Assert - Should only show read books (client-side filtering)
      expect(wrapper.vm.readFilter).toBe(true);
      expect(wrapper.vm.filteredBooks).toHaveLength(2);
      expect(wrapper.vm.filteredBooks.every(b => b.read === true)).toBe(true);
    });

    it('should filter unread books when clicking "Non lus" button', async () => {
      // Arrange
      calibreService.getBooks.mockResolvedValue({
        total: 5,
        books: [
          { id: 1, title: 'Book 1', authors: ['A'], read: true },
          { id: 2, title: 'Book 2', authors: ['B'], read: false },
          { id: 3, title: 'Book 3', authors: ['C'], read: true },
          { id: 4, title: 'Book 4', authors: ['D'], read: false },
          { id: 5, title: 'Book 5', authors: ['E'], read: null }
        ]
      });

      wrapper = mount(CalibreLibrary, {
        global: {
          plugins: [router]
        }
      });

      await flushPromises();

      // Act
      const unreadButton = wrapper.find('[data-testid="filter-unread"]');
      await unreadButton.trigger('click');
      await wrapper.vm.$nextTick();

      // Assert - Should show unread books (false) AND books with unknown status (null)
      expect(wrapper.vm.readFilter).toBe(false);
      expect(wrapper.vm.filteredBooks).toHaveLength(3);
      expect(wrapper.vm.filteredBooks.every(b => b.read === false || b.read === null)).toBe(true);
      expect(wrapper.vm.filteredBooks.some(b => b.id === 5 && b.read === null)).toBe(true);
    });
  });

  describe('Sorting and Filtering', () => {
    beforeEach(() => {
      calibreService.getStatus.mockResolvedValue({
        available: true,
        library_path: '/calibre',
        total_books: 516
      });
    });

    it('should load all books at once on mount', async () => {
      // Arrange
      calibreService.getBooks.mockResolvedValue({
        total: 516,
        offset: 0,
        limit: 10000, // Large limit to get all books
        books: Array(516).fill({}).map((_, i) => ({
          id: i,
          title: `Book ${i}`,
          authors: ['Author'],
          timestamp: `2024-01-${String(i % 28 + 1).padStart(2, '0')}`
        }))
      });

      // Act
      wrapper = mount(CalibreLibrary, {
        global: {
          plugins: [router]
        }
      });

      await flushPromises();

      // Assert - Should load ALL books at once
      expect(wrapper.vm.allBooks).toHaveLength(516);
      expect(calibreService.getBooks).toHaveBeenCalledWith(
        expect.objectContaining({ limit: 10000 })
      );
    });

    it('should filter books by search text (title)', async () => {
      // Arrange
      calibreService.getBooks.mockResolvedValue({
        total: 3,
        books: [
          { id: 1, title: 'Le Silence de la mer', authors: ['Vercors'] },
          { id: 2, title: 'La Peste', authors: ['Camus'] },
          { id: 3, title: 'Le Petit Prince', authors: ['Saint-Exupéry'] }
        ]
      });

      wrapper = mount(CalibreLibrary, {
        global: {
          plugins: [router]
        }
      });

      await flushPromises();

      // Act - Search for "silence"
      const searchInput = wrapper.find('[data-testid="search-input"]');
      await searchInput.setValue('silence');
      await wrapper.vm.$nextTick();

      // Assert
      expect(wrapper.vm.filteredBooks).toHaveLength(1);
      expect(wrapper.vm.filteredBooks[0].title).toBe('Le Silence de la mer');
      expect(wrapper.text()).toContain('1 livre affiché sur 3');
    });

    it('should filter books by search text (author)', async () => {
      // Arrange
      calibreService.getBooks.mockResolvedValue({
        total: 3,
        books: [
          { id: 1, title: 'Le Silence de la mer', authors: ['Vercors'] },
          { id: 2, title: 'La Peste', authors: ['Albert Camus'] },
          { id: 3, title: 'L\'Étranger', authors: ['Albert Camus'] }
        ]
      });

      wrapper = mount(CalibreLibrary, {
        global: {
          plugins: [router]
        }
      });

      await flushPromises();

      // Act - Search for "camus"
      const searchInput = wrapper.find('[data-testid="search-input"]');
      await searchInput.setValue('camus');
      await wrapper.vm.$nextTick();

      // Assert
      expect(wrapper.vm.filteredBooks).toHaveLength(2);
      expect(wrapper.text()).toContain('2 livres affichés sur 3');
    });

    it('should sort books by title A-Z', async () => {
      // Arrange
      calibreService.getBooks.mockResolvedValue({
        total: 3,
        books: [
          { id: 1, title: 'Zebra', authors: ['A'] },
          { id: 2, title: 'Apple', authors: ['B'] },
          { id: 3, title: 'Mango', authors: ['C'] }
        ]
      });

      wrapper = mount(CalibreLibrary, {
        global: {
          plugins: [router]
        }
      });

      await flushPromises();

      // Act
      const sortButton = wrapper.find('[data-testid="sort-title-az"]');
      await sortButton.trigger('click');
      await wrapper.vm.$nextTick();

      // Assert
      expect(wrapper.vm.filteredBooks[0].title).toBe('Apple');
      expect(wrapper.vm.filteredBooks[1].title).toBe('Mango');
      expect(wrapper.vm.filteredBooks[2].title).toBe('Zebra');
    });

    it('should sort books by author A-Z', async () => {
      // Arrange
      calibreService.getBooks.mockResolvedValue({
        total: 3,
        books: [
          { id: 1, title: 'Book 1', authors: ['Zola'] },
          { id: 2, title: 'Book 2', authors: ['Balzac'] },
          { id: 3, title: 'Book 3', authors: ['Hugo'] }
        ]
      });

      wrapper = mount(CalibreLibrary, {
        global: {
          plugins: [router]
        }
      });

      await flushPromises();

      // Act
      const sortButton = wrapper.find('[data-testid="sort-author-az"]');
      await sortButton.trigger('click');
      await wrapper.vm.$nextTick();

      // Assert
      expect(wrapper.vm.filteredBooks[0].authors[0]).toBe('Balzac');
      expect(wrapper.vm.filteredBooks[1].authors[0]).toBe('Hugo');
      expect(wrapper.vm.filteredBooks[2].authors[0]).toBe('Zola');
    });

    it('should sort books by date added (most recent first)', async () => {
      // Arrange
      calibreService.getBooks.mockResolvedValue({
        total: 3,
        books: [
          { id: 1, title: 'Old Book', authors: ['A'], timestamp: '2024-01-01 10:00:00+00:00' },
          { id: 2, title: 'New Book', authors: ['B'], timestamp: '2024-12-01 10:00:00+00:00' },
          { id: 3, title: 'Middle Book', authors: ['C'], timestamp: '2024-06-01 10:00:00+00:00' }
        ]
      });

      wrapper = mount(CalibreLibrary, {
        global: {
          plugins: [router]
        }
      });

      await flushPromises();

      // Act
      const sortButton = wrapper.find('[data-testid="sort-date-added"]');
      await sortButton.trigger('click');
      await wrapper.vm.$nextTick();

      // Assert - Most recent first
      expect(wrapper.vm.filteredBooks[0].title).toBe('New Book');
      expect(wrapper.vm.filteredBooks[1].title).toBe('Middle Book');
      expect(wrapper.vm.filteredBooks[2].title).toBe('Old Book');
    });

    it('should render a "Dernières lectures" sort button, active by default (Issue #274)', async () => {
      calibreService.getBooks.mockResolvedValue({ total: 0, books: [] });

      wrapper = mount(CalibreLibrary, {
        global: { plugins: [router] }
      });

      await flushPromises();

      const button = wrapper.find('[data-testid="sort-recent-reads"]');
      expect(button.exists()).toBe(true);
      expect(button.text()).toBe('Dernières lectures');
      expect(button.classes()).toContain('active');
      expect(wrapper.vm.sortBy).toBe('recent-reads');
    });

    it('should place in-progress books first, sorted by most recent start date (Issue #274)', async () => {
      // In-progress = has ko_date_started but no ko_date_finished
      calibreService.getBooks.mockResolvedValue({
        total: 3,
        books: [
          {
            id: 1, title: 'Lecture ancienne', authors: ['A'], timestamp: '2024-01-01',
            ko_date_started: '2026-07-01T00:00:00Z', ko_date_finished: null
          },
          {
            id: 2, title: 'Lecture récente', authors: ['B'], timestamp: '2024-01-01',
            ko_date_started: '2026-08-20T00:00:00Z', ko_date_finished: null
          },
          { id: 3, title: 'Jamais lu', authors: ['C'], timestamp: '2024-06-01' }
        ]
      });

      wrapper = mount(CalibreLibrary, {
        global: { plugins: [router] }
      });

      await flushPromises();

      // "recent-reads" is the default sort — no click needed
      expect(wrapper.vm.filteredBooks[0].title).toBe('Lecture récente');
      expect(wrapper.vm.filteredBooks[1].title).toBe('Lecture ancienne');
      expect(wrapper.vm.filteredBooks[2].title).toBe('Jamais lu');
    });

    it('should place finished books after in-progress ones, sorted by most recent finish date (Issue #274)', async () => {
      calibreService.getBooks.mockResolvedValue({
        total: 3,
        books: [
          {
            id: 1, title: 'En cours', authors: ['A'], timestamp: '2020-01-01',
            ko_date_started: '2026-08-01T00:00:00Z', ko_date_finished: null
          },
          {
            id: 2, title: 'Terminé récemment', authors: ['B'], timestamp: '2020-01-01',
            ko_date_started: '2026-07-01T00:00:00Z', ko_date_finished: '2026-08-10T00:00:00Z'
          },
          {
            id: 3, title: 'Terminé il y a longtemps', authors: ['C'], timestamp: '2020-01-01',
            ko_date_started: '2026-01-01T00:00:00Z', ko_date_finished: '2026-02-01T00:00:00Z'
          }
        ]
      });

      wrapper = mount(CalibreLibrary, {
        global: { plugins: [router] }
      });

      await flushPromises();

      expect(wrapper.vm.filteredBooks[0].title).toBe('En cours');
      expect(wrapper.vm.filteredBooks[1].title).toBe('Terminé récemment');
      expect(wrapper.vm.filteredBooks[2].title).toBe('Terminé il y a longtemps');
    });

    it('should sort never-synced books last, by date added (Issue #274)', async () => {
      calibreService.getBooks.mockResolvedValue({
        total: 2,
        books: [
          { id: 1, title: 'Ajouté récemment', authors: ['A'], timestamp: '2026-06-01' },
          {
            id: 2, title: 'Terminé', authors: ['B'], timestamp: '2020-01-01',
            ko_date_started: '2026-07-01T00:00:00Z', ko_date_finished: '2026-08-10T00:00:00Z'
          }
        ]
      });

      wrapper = mount(CalibreLibrary, {
        global: { plugins: [router] }
      });

      await flushPromises();

      // "Terminé" has a ko_date_finished → comes before never-synced books,
      // regardless of timestamp
      expect(wrapper.vm.filteredBooks[0].title).toBe('Terminé');
      expect(wrapper.vm.filteredBooks[1].title).toBe('Ajouté récemment');
    });

    it('should combine search and read filter', async () => {
      // Arrange
      calibreService.getBooks.mockResolvedValue({
        total: 4,
        books: [
          { id: 1, title: 'Le Silence', authors: ['Vercors'], read: true },
          { id: 2, title: 'La Peste', authors: ['Camus'], read: false },
          { id: 3, title: 'Le Petit', authors: ['Saint-Exupéry'], read: true },
          { id: 4, title: 'Silence Total', authors: ['Autre'], read: false }
        ]
      });

      wrapper = mount(CalibreLibrary, {
        global: {
          plugins: [router]
        }
      });

      await flushPromises();

      // Act - Filter by "read" and search "silence"
      await wrapper.find('[data-testid="filter-read"]').trigger('click');
      await wrapper.find('[data-testid="search-input"]').setValue('silence');
      await wrapper.vm.$nextTick();

      // Assert - Only "Le Silence" should match (read=true AND title contains "silence")
      expect(wrapper.vm.filteredBooks).toHaveLength(1);
      expect(wrapper.vm.filteredBooks[0].title).toBe('Le Silence');
    });

    it('should highlight search matches in book titles and authors', async () => {
      // Arrange
      calibreService.getBooks.mockResolvedValue({
        total: 2,
        books: [
          { id: 1, title: 'Le Silence de la mer', authors: ['Vercors'] },
          { id: 2, title: 'La Peste', authors: ['Albert Camus'] }
        ]
      });

      wrapper = mount(CalibreLibrary, {
        global: {
          plugins: [router]
        }
      });

      await flushPromises();

      // Act - Search for "silen" (minimum 3 chars for highlighting)
      const searchInput = wrapper.find('[data-testid="search-input"]');
      await searchInput.setValue('silen');
      await wrapper.vm.$nextTick();

      // Assert - Should highlight matched text in book title
      const bookCards = wrapper.findAll('[data-testid="book-card"]');
      expect(bookCards).toHaveLength(1);

      // Check that highlightText method returns HTML with highlighting
      const highlightedTitle = wrapper.vm.highlightText('Le Silence de la mer', 'silen');
      expect(highlightedTitle).toContain('<strong');
      expect(highlightedTitle).toContain('background: #fff3cd');
      expect(highlightedTitle).toContain('Silen'); // Matched text should be wrapped

      // Test author highlighting
      await searchInput.setValue('camus');
      await wrapper.vm.$nextTick();

      const highlightedAuthor = wrapper.vm.highlightText('Albert Camus', 'camus');
      expect(highlightedAuthor).toContain('<strong');
      expect(highlightedAuthor).toContain('Camus'); // Matched text should be wrapped
    });

    it('should not highlight if search text is less than 3 characters', async () => {
      // Arrange
      calibreService.getBooks.mockResolvedValue({
        total: 1,
        books: [
          { id: 1, title: 'Le Silence de la mer', authors: ['Vercors'] }
        ]
      });

      wrapper = mount(CalibreLibrary, {
        global: {
          plugins: [router]
        }
      });

      await flushPromises();

      // Act - Search with only 2 characters
      const searchInput = wrapper.find('[data-testid="search-input"]');
      await searchInput.setValue('si');
      await wrapper.vm.$nextTick();

      // Assert - Should NOT highlight (text returned as-is)
      const result = wrapper.vm.highlightText('Le Silence de la mer', 'si');
      expect(result).toBe('Le Silence de la mer');
      expect(result).not.toContain('<strong');
    });
  });

  describe('Typographic Characters Search (Issue #173)', () => {
    it('should find book with ligature oe when searching for oeuvre', async () => {
      // Arrange
      calibreService.getStatus.mockResolvedValue({
        available: true,
        library_path: '/calibre',
        total_books: 1
      });

      calibreService.getBooks.mockResolvedValue({
        total: 1,
        books: [
          { id: 1, title: 'L\u2019\u0153uvre au noir', authors: ['Marguerite Yourcenar'], read: null }
        ]
      });

      wrapper = mount(CalibreLibrary, {
        global: {
          plugins: [router]
        }
      });

      await flushPromises();

      // Act - Search with "oeuvre" (without ligature)
      const searchInput = wrapper.find('[data-testid="search-input"]');
      await searchInput.setValue('oeuvre');
      await wrapper.vm.$nextTick();

      // Assert - Should find the book with "œuvre" (with ligature)
      const bookCards = wrapper.findAll('[data-testid="book-card"]');
      expect(bookCards.length).toBe(1);
      expect(bookCards[0].text()).toContain('œuvre');
    });

    it('should find book with em dash when searching with simple hyphen', async () => {
      // Arrange
      calibreService.getStatus.mockResolvedValue({
        available: true,
        library_path: '/calibre',
        total_books: 1
      });

      calibreService.getBooks.mockResolvedValue({
        total: 1,
        books: [
          { id: 1, title: 'Marie\u2013Claire Blais', authors: ['Author'], read: null }
        ]
      });

      wrapper = mount(CalibreLibrary, {
        global: {
          plugins: [router]
        }
      });

      await flushPromises();

      // Act - Search with simple hyphen
      const searchInput = wrapper.find('[data-testid="search-input"]');
      await searchInput.setValue('Marie-Claire');
      await wrapper.vm.$nextTick();

      // Assert - Should find the book with em dash
      const bookCards = wrapper.findAll('[data-testid="book-card"]');
      expect(bookCards.length).toBe(1);
    });

    it('should find author with typographic apostrophe when searching with simple apostrophe', async () => {
      // Arrange
      calibreService.getStatus.mockResolvedValue({
        available: true,
        library_path: '/calibre',
        total_books: 1
      });

      calibreService.getBooks.mockResolvedValue({
        total: 1,
        books: [
          { id: 1, title: 'Test Book', authors: ['L\u2019auteur inconnu'], read: null }
        ]
      });

      wrapper = mount(CalibreLibrary, {
        global: {
          plugins: [router]
        }
      });

      await flushPromises();

      // Act - Search with simple apostrophe
      const searchInput = wrapper.find('[data-testid="search-input"]');
      await searchInput.setValue("l'auteur");
      await wrapper.vm.$nextTick();

      // Assert - Should find the author with typographic apostrophe
      const bookCards = wrapper.findAll('[data-testid="book-card"]');
      expect(bookCards.length).toBe(1);
    });
  });

  describe('Clickable tiles (Issue #277)', () => {
    beforeEach(() => {
      calibreService.getStatus.mockResolvedValue({
        available: true,
        library_path: '/calibre',
        total_books: 516
      });
    });

    it('should render a matched book tile as a link to its LMELP book page', async () => {
      calibreService.getBooks.mockResolvedValue({
        total: 1,
        books: [
          {
            id: 3,
            title: 'Le Silence de la mer',
            authors: ['Vercors'],
            read: true,
            mongo_livre_id: 'abc123'
          }
        ]
      });

      wrapper = mount(CalibreLibrary, {
        global: { plugins: [router] }
      });

      await flushPromises();

      const bookCard = wrapper.find('[data-testid="book-card"]');
      expect(bookCard.element.tagName).toBe('A');
      expect(bookCard.attributes('href')).toBe('/livre/abc123');
      expect(bookCard.classes()).toContain('clickable');
    });

    it('should render an unmatched book tile as a plain non-clickable div', async () => {
      calibreService.getBooks.mockResolvedValue({
        total: 1,
        books: [
          {
            id: 42,
            title: 'Livre Sans Correspondance',
            authors: ['Auteur Inconnu'],
            read: false,
            mongo_livre_id: null
          }
        ]
      });

      wrapper = mount(CalibreLibrary, {
        global: { plugins: [router] }
      });

      await flushPromises();

      const bookCard = wrapper.find('[data-testid="book-card"]');
      expect(bookCard.element.tagName).toBe('DIV');
      expect(bookCard.classes()).not.toContain('clickable');
    });
  });

  describe('Emission date tag styling (Issue #288)', () => {
    beforeEach(async () => {
      calibreService.getStatus.mockResolvedValue({
        available: true,
        library_path: '/calibre',
        total_books: 1
      });
      calibreService.getBooks.mockResolvedValue({
        total: 1,
        books: [
          {
            id: 1,
            title: 'Livre test',
            authors: ['Auteur Test'],
            read: false,
            mongo_livre_id: null,
            tags: ['lmelp_260320', 'lmelp_nelly_kaprielian', 'Roman']
          }
        ]
      });

      wrapper = mount(CalibreLibrary, {
        global: { plugins: [router] }
      });

      await flushPromises();
    });

    it('should detect a tag matching the lmelp_YYMMDD emission date format', () => {
      expect(wrapper.vm.isLmelpDateTag('lmelp_260320')).toBe(true);
    });

    it('should not detect a lmelp_ critic name tag as an emission date tag', () => {
      expect(wrapper.vm.isLmelpDateTag('lmelp_nelly_kaprielian')).toBe(false);
    });

    it('should not detect a regular tag as an emission date tag', () => {
      expect(wrapper.vm.isLmelpDateTag('Roman')).toBe(false);
    });

    it('should apply the lmelp-date class only to the emission date tag', () => {
      const tags = wrapper.findAll('.tag');
      const dateTag = tags.find((t) => t.text() === 'lmelp_260320');
      const criticTag = tags.find((t) => t.text() === 'lmelp_nelly_kaprielian');
      const otherTag = tags.find((t) => t.text() === 'Roman');

      expect(dateTag.classes()).toContain('tag-lmelp-date');
      expect(criticTag.classes()).not.toContain('tag-lmelp-date');
      expect(otherTag.classes()).not.toContain('tag-lmelp-date');
    });
  });

  describe('URL state persistence (Issue #277)', () => {
    beforeEach(() => {
      calibreService.getStatus.mockResolvedValue({
        available: true,
        library_path: '/calibre',
        total_books: 516
      });
      calibreService.getBooks.mockResolvedValue({
        total: 0,
        books: []
      });
    });

    it('should restore readFilter and sortBy from query params on mount', async () => {
      await router.push('/calibre?read=true&sort=title-az');

      wrapper = mount(CalibreLibrary, {
        global: { plugins: [router] }
      });

      await flushPromises();

      expect(wrapper.vm.readFilter).toBe(true);
      expect(wrapper.vm.sortBy).toBe('title-az');
    });

    it('should restore readFilter=false from query params on mount', async () => {
      await router.push('/calibre?read=false');

      wrapper = mount(CalibreLibrary, {
        global: { plugins: [router] }
      });

      await flushPromises();

      expect(wrapper.vm.readFilter).toBe(false);
    });

    it('should write search, read and sort to the URL when changed', async () => {
      wrapper = mount(CalibreLibrary, {
        global: { plugins: [router] }
      });

      await flushPromises();

      await wrapper.find('[data-testid="filter-read"]').trigger('click');
      await flushPromises();
      await wrapper.find('[data-testid="sort-title-az"]').trigger('click');
      await flushPromises();
      await wrapper.find('[data-testid="search-input"]').setValue('camus');
      await flushPromises();

      expect(router.currentRoute.value.query.read).toBe('true');
      expect(router.currentRoute.value.query.sort).toBe('title-az');
      expect(router.currentRoute.value.query.search).toBe('camus');
    });

    it('should restore filters after navigating away and back (browser back)', async () => {
      await router.push('/calibre?search=camus&read=true&sort=title-az');

      wrapper = mount(CalibreLibrary, {
        global: { plugins: [router] }
      });

      await flushPromises();

      expect(wrapper.vm.searchText).toBe('camus');
      expect(wrapper.vm.readFilter).toBe(true);
      expect(wrapper.vm.sortBy).toBe('title-az');
    });
  });

  describe('Error Handling', () => {
    it('should display error message when API call fails', async () => {
      // Arrange
      calibreService.getStatus.mockRejectedValue(new Error('Network error'));

      // Act
      wrapper = mount(CalibreLibrary, {
        global: {
          plugins: [router]
        }
      });

      await flushPromises();

      // Assert
      expect(wrapper.text()).toContain('Erreur');
    });
  });
});
