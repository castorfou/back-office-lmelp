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
      wrapper = mount(CalibreLibrary, {
        global: {
          plugins: [router]
        }
      });

      await flushPromises();
      vi.clearAllMocks();

      calibreService.getBooks.mockResolvedValue({
        total: 299,
        offset: 0,
        limit: 50,
        books: []
      });

      // Act
      const readButton = wrapper.find('[data-testid="filter-read"]');
      await readButton.trigger('click');
      await flushPromises();

      // Assert
      expect(calibreService.getBooks).toHaveBeenCalledWith(
        expect.objectContaining({ read_filter: true })
      );
    });

    it('should filter unread books when clicking "Non lus" button', async () => {
      // Arrange
      wrapper = mount(CalibreLibrary, {
        global: {
          plugins: [router]
        }
      });

      await flushPromises();
      vi.clearAllMocks();

      calibreService.getBooks.mockResolvedValue({
        total: 217,
        offset: 0,
        limit: 50,
        books: []
      });

      // Act
      const unreadButton = wrapper.find('[data-testid="filter-unread"]');
      await unreadButton.trigger('click');
      await flushPromises();

      // Assert
      expect(calibreService.getBooks).toHaveBeenCalledWith(
        expect.objectContaining({ read_filter: false })
      );
    });
  });

  describe('Infinite Scroll', () => {
    beforeEach(() => {
      calibreService.getStatus.mockResolvedValue({
        available: true,
        library_path: '/calibre',
        total_books: 516
      });
    });

    it('should load initial books on mount', async () => {
      // Arrange
      calibreService.getBooks.mockResolvedValue({
        total: 516,
        offset: 0,
        limit: 50,
        books: Array(50).fill({}).map((_, i) => ({
          id: i,
          title: `Book ${i}`,
          authors: ['Author']
        }))
      });

      // Act
      wrapper = mount(CalibreLibrary, {
        global: {
          plugins: [router]
        }
      });

      await flushPromises();

      // Assert
      expect(wrapper.findAll('[data-testid="book-card"]')).toHaveLength(50);
      expect(calibreService.getBooks).toHaveBeenCalledWith(
        expect.objectContaining({ offset: 0, limit: 50 })
      );
    });

    it('should load more books when scrolling near bottom', async () => {
      // Arrange
      calibreService.getBooks.mockResolvedValueOnce({
        total: 516,
        offset: 0,
        limit: 50,
        books: Array(50).fill({}).map((_, i) => ({
          id: i,
          title: `Book ${i}`,
          authors: ['Author']
        }))
      });

      wrapper = mount(CalibreLibrary, {
        global: {
          plugins: [router]
        }
      });

      await flushPromises();
      vi.clearAllMocks();

      calibreService.getBooks.mockResolvedValueOnce({
        total: 516,
        offset: 50,
        limit: 50,
        books: Array(50).fill({}).map((_, i) => ({
          id: i + 50,
          title: `Book ${i + 50}`,
          authors: ['Author']
        }))
      });

      // Act - Simulate scroll to bottom
      await wrapper.vm.loadMoreBooks();
      await flushPromises();

      // Assert
      expect(calibreService.getBooks).toHaveBeenCalledWith(
        expect.objectContaining({ offset: 50 })
      );
      expect(wrapper.vm.books).toHaveLength(100);
    });

    it('should not load more when all books are loaded', async () => {
      // Arrange
      calibreService.getBooks.mockResolvedValue({
        total: 50,
        offset: 0,
        limit: 50,
        books: Array(50).fill({}).map((_, i) => ({
          id: i,
          title: `Book ${i}`,
          authors: ['Author']
        }))
      });

      wrapper = mount(CalibreLibrary, {
        global: {
          plugins: [router]
        }
      });

      await flushPromises();
      vi.clearAllMocks();

      // Act - Try to load more
      await wrapper.vm.loadMoreBooks();
      await flushPromises();

      // Assert
      expect(calibreService.getBooks).not.toHaveBeenCalled();
    });

    it('should show loading indicator while loading more books', async () => {
      // Arrange
      calibreService.getBooks.mockResolvedValue({
        total: 516,
        offset: 0,
        limit: 50,
        books: Array(50).fill({}).map((_, i) => ({
          id: i,
          title: `Book ${i}`,
          authors: ['Author']
        }))
      });

      wrapper = mount(CalibreLibrary, {
        global: {
          plugins: [router]
        }
      });

      await flushPromises();

      // Act - Start loading more (don't await)
      const loadPromise = wrapper.vm.loadMoreBooks();
      await wrapper.vm.$nextTick();

      // Assert - Should show loading during load
      expect(wrapper.vm.loadingMore).toBe(true);

      // Cleanup
      await loadPromise;
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
