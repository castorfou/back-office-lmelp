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
        { path: '/calibre', component: CalibreLibrary }
      ]
    });
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
