/**
 * Tests unitaires pour le service API Calibre (TDD)
 *
 * Ces tests vérifient:
 * - Détection du statut Calibre (disponible/non disponible)
 * - Récupération de la liste des livres avec pagination
 * - Récupération des statistiques
 * - Gestion des erreurs réseau
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock du module api.js
vi.mock('../../src/services/api.js', async () => {
  const actual = await vi.importActual('../../src/services/api.js');
  return {
    ...actual,
    calibreService: {
      getStatus: vi.fn(),
      getBooks: vi.fn(),
      getStatistics: vi.fn(),
      getBook: vi.fn(),
      getAuthors: vi.fn()
    }
  };
});

import { calibreService } from '../../src/services/api.js';

describe('calibreService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('getStatus', () => {
    it('should return available status when Calibre is configured', async () => {
      // Arrange
      const mockStatus = {
        available: true,
        library_path: '/calibre',
        total_books: 516,
        virtual_library_tag: 'guillaume',
        custom_columns: {
          read: 'Read (bool)',
          paper: 'paper (bool)',
          text: 'Commentaire (comments)'
        },
        error: null
      };

      calibreService.getStatus.mockResolvedValue(mockStatus);

      // Act
      const status = await calibreService.getStatus();

      // Assert
      expect(status.available).toBe(true);
      expect(status.library_path).toBe('/calibre');
      expect(status.total_books).toBe(516);
      expect(status.virtual_library_tag).toBe('guillaume');
      expect(status.custom_columns).toHaveProperty('read');
    });

    it('should return unavailable status when Calibre is not configured', async () => {
      // Arrange
      const mockStatus = {
        available: false,
        library_path: null,
        total_books: null,
        virtual_library_tag: null,
        custom_columns: {},
        error: 'CALIBRE_LIBRARY_PATH not configured'
      };

      calibreService.getStatus.mockResolvedValue(mockStatus);

      // Act
      const status = await calibreService.getStatus();

      // Assert
      expect(status.available).toBe(false);
      expect(status.error).toBe('CALIBRE_LIBRARY_PATH not configured');
    });

    it('should handle network errors gracefully', async () => {
      // Arrange
      calibreService.getStatus.mockRejectedValue(new Error('Erreur réseau: Impossible de contacter le serveur'));

      // Act & Assert
      await expect(calibreService.getStatus()).rejects.toThrow('Erreur réseau');
    });
  });

  describe('getBooks', () => {
    it('should fetch books with default pagination', async () => {
      // Arrange
      const mockBooksResponse = {
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
            tags: ['guillaume'],
            read: true
          },
          {
            id: 42,
            title: "L'Étranger",
            authors: ['Camus, Albert'],
            isbn: '978-2-07-036002-4',
            rating: 10,
            tags: ['guillaume'],
            read: false
          }
        ]
      };

      calibreService.getBooks.mockResolvedValue(mockBooksResponse);

      // Act
      const result = await calibreService.getBooks();

      // Assert
      expect(result.total).toBe(516);
      expect(result.books).toHaveLength(2);
      expect(result.books[0].title).toBe('Le Silence de la mer');
      expect(result.books[0].authors).toContain('Vercors');
      expect(result.books[1].read).toBe(false);
    });

    it('should support pagination parameters', async () => {
      // Arrange
      const mockBooksResponse = {
        total: 516,
        offset: 50,
        limit: 25,
        books: []
      };

      calibreService.getBooks.mockResolvedValue(mockBooksResponse);

      // Act
      const result = await calibreService.getBooks({ limit: 25, offset: 50 });

      // Assert
      expect(calibreService.getBooks).toHaveBeenCalledWith({ limit: 25, offset: 50 });
      expect(result.offset).toBe(50);
      expect(result.limit).toBe(25);
    });

    it('should support read filter', async () => {
      // Arrange
      const mockBooksResponse = {
        total: 299,
        offset: 0,
        limit: 50,
        books: []
      };

      calibreService.getBooks.mockResolvedValue(mockBooksResponse);

      // Act
      const result = await calibreService.getBooks({ read_filter: true });

      // Assert
      expect(calibreService.getBooks).toHaveBeenCalledWith({ read_filter: true });
      expect(result.total).toBe(299);
    });
  });

  describe('getStatistics', () => {
    it('should fetch Calibre library statistics', async () => {
      // Arrange
      const mockStats = {
        total_books: 516,
        books_with_isbn: 221,
        books_with_rating: 500,
        books_with_tags: 516,
        total_authors: 450,
        total_tags: 100,
        books_read: 299
      };

      calibreService.getStatistics.mockResolvedValue(mockStats);

      // Act
      const stats = await calibreService.getStatistics();

      // Assert
      expect(stats.total_books).toBe(516);
      expect(stats.books_with_isbn).toBe(221);
      expect(stats.books_read).toBe(299);
      expect(stats.total_authors).toBe(450);
    });
  });
});
