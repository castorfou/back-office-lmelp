/**
 * Test TDD pour le cache de livres extraits (Issue #85 - Performance)
 *
 * PROBLÈME:
 * Quand l'utilisateur clique "Relancer validation Biblio" avec 10 livres:
 * - autoValidateAndSendResults() boucle sur 10 livres
 * - Chaque livre appelle validateBiblio()
 * - Chaque validateBiblio() appelle _getExtractedBooks(episodeId)
 * - _getExtractedBooks() appelle GET /api/livres-auteurs
 * - Backend enrichit les 10 livres à chaque appel
 * - Résultat: 10 appels × 10 livres = 100 enrichissements (au lieu de 10)
 *
 * SOLUTION:
 * Cacher les livres extraits par épisode dans BiblioValidationService
 * - 1er appel: fetch API et cache le résultat
 * - Appels suivants (même épisode): retourne le cache
 * - Méthode clearExtractedBooksCache() pour vider le cache si besoin
 *
 * CE TEST DOIT ÉCHOUER initialement car le cache n'existe pas encore.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { BiblioValidationService } from '../../src/services/BiblioValidationService.js';

describe('BiblioValidationService - Cache des livres extraits', () => {
  let service;
  let mockLivresAuteursService;

  beforeEach(() => {
    // Mock du service livres-auteurs
    mockLivresAuteursService = {
      getLivresAuteurs: vi.fn()
    };

    // Créer le service avec dépendances mockées
    service = new BiblioValidationService({
      livresAuteursService: mockLivresAuteursService,
      babelioService: {},
      fuzzySearchService: {},
      localAuthorService: null
    });
  });

  describe('_getExtractedBooks() avec cache', () => {
    it('devrait appeler API une seule fois pour le même épisode (cache hit)', async () => {
      // Arrange
      const episodeId = '68c707ad6e51b9428ab87e9e';
      const mockBooks = [
        { auteur: 'Carlos Gimenez', titre: 'Paracuellos, Intégrale', editeur: 'Audie-Fluide glacial' },
        { auteur: 'Alain Mabanckou', titre: 'Ramsès de Paris', editeur: 'Seuil' }
      ];

      mockLivresAuteursService.getLivresAuteurs.mockResolvedValue(mockBooks);

      // Act - Appeler 3 fois avec le même épisode (simule 3 validations de livres)
      const result1 = await service._getExtractedBooks(episodeId);
      const result2 = await service._getExtractedBooks(episodeId);
      const result3 = await service._getExtractedBooks(episodeId);

      // Assert
      // ❌ DOIT ÉCHOUER INITIALEMENT (RED phase)
      // Actuellement: getLivresAuteurs appelé 3 fois
      // Attendu: getLivresAuteurs appelé 1 seule fois (les appels 2 et 3 utilisent le cache)
      expect(mockLivresAuteursService.getLivresAuteurs).toHaveBeenCalledTimes(1);
      expect(mockLivresAuteursService.getLivresAuteurs).toHaveBeenCalledWith({ episode_oid: episodeId });

      // Vérifier que les 3 résultats sont identiques (format {author, title})
      expect(result1).toEqual([
        { author: 'Carlos Gimenez', title: 'Paracuellos, Intégrale' },
        { author: 'Alain Mabanckou', title: 'Ramsès de Paris' }
      ]);
      expect(result2).toEqual(result1);
      expect(result3).toEqual(result1);
    });

    it('devrait appeler API séparément pour des épisodes différents', async () => {
      // Arrange
      const episode1 = '68c707ad6e51b9428ab87e9e';
      const episode2 = '68c707ad6e51b9428ab87e9f';

      const books1 = [
        { auteur: 'Auteur 1', titre: 'Livre 1', editeur: 'Éditeur 1' }
      ];
      const books2 = [
        { auteur: 'Auteur 2', titre: 'Livre 2', editeur: 'Éditeur 2' }
      ];

      mockLivresAuteursService.getLivresAuteurs
        .mockResolvedValueOnce(books1)
        .mockResolvedValueOnce(books2);

      // Act
      const result1 = await service._getExtractedBooks(episode1);
      const result2 = await service._getExtractedBooks(episode2);

      // Assert - 2 appels API différents (épisodes différents)
      expect(mockLivresAuteursService.getLivresAuteurs).toHaveBeenCalledTimes(2);
      expect(mockLivresAuteursService.getLivresAuteurs).toHaveBeenNthCalledWith(1, { episode_oid: episode1 });
      expect(mockLivresAuteursService.getLivresAuteurs).toHaveBeenNthCalledWith(2, { episode_oid: episode2 });

      expect(result1).toEqual([{ author: 'Auteur 1', title: 'Livre 1' }]);
      expect(result2).toEqual([{ author: 'Auteur 2', title: 'Livre 2' }]);
    });

    it('devrait retourner [] si episodeId est null ou undefined', async () => {
      // Act
      const resultNull = await service._getExtractedBooks(null);
      const resultUndefined = await service._getExtractedBooks(undefined);

      // Assert - Pas d'appel API si episodeId invalide
      expect(mockLivresAuteursService.getLivresAuteurs).not.toHaveBeenCalled();
      expect(resultNull).toEqual([]);
      expect(resultUndefined).toEqual([]);
    });

    it('devrait gérer les erreurs API et retourner []', async () => {
      // Arrange
      const episodeId = '68c707ad6e51b9428ab87e9e';
      mockLivresAuteursService.getLivresAuteurs.mockRejectedValue(new Error('API Error'));

      // Act
      const result = await service._getExtractedBooks(episodeId);

      // Assert
      expect(result).toEqual([]);
      expect(mockLivresAuteursService.getLivresAuteurs).toHaveBeenCalledTimes(1);
    });
  });

  describe('clearExtractedBooksCache()', () => {
    it('devrait vider le cache pour un épisode spécifique', async () => {
      // Arrange
      const episodeId = '68c707ad6e51b9428ab87e9e';
      const mockBooks = [
        { auteur: 'Carlos Gimenez', titre: 'Paracuellos, Intégrale', editeur: 'Audie-Fluide glacial' }
      ];

      mockLivresAuteursService.getLivresAuteurs.mockResolvedValue(mockBooks);

      // Act
      await service._getExtractedBooks(episodeId); // 1er appel → cache
      service.clearExtractedBooksCache(episodeId); // Vider le cache
      await service._getExtractedBooks(episodeId); // 2e appel → doit re-fetch

      // Assert
      // ❌ DOIT ÉCHOUER INITIALEMENT (clearExtractedBooksCache n'existe pas)
      expect(mockLivresAuteursService.getLivresAuteurs).toHaveBeenCalledTimes(2);
    });

    it('devrait vider le cache pour TOUS les épisodes si aucun ID fourni', async () => {
      // Arrange
      const episode1 = '68c707ad6e51b9428ab87e9e';
      const episode2 = '68c707ad6e51b9428ab87e9f';

      const books1 = [{ auteur: 'Auteur 1', titre: 'Livre 1', editeur: 'Éditeur 1' }];
      const books2 = [{ auteur: 'Auteur 2', titre: 'Livre 2', editeur: 'Éditeur 2' }];

      mockLivresAuteursService.getLivresAuteurs
        .mockResolvedValueOnce(books1)
        .mockResolvedValueOnce(books2)
        .mockResolvedValueOnce(books1)
        .mockResolvedValueOnce(books2);

      // Act
      await service._getExtractedBooks(episode1); // 1er appel episode1 → cache
      await service._getExtractedBooks(episode2); // 1er appel episode2 → cache
      service.clearExtractedBooksCache(); // Vider TOUT le cache (sans ID)
      await service._getExtractedBooks(episode1); // 2e appel episode1 → doit re-fetch
      await service._getExtractedBooks(episode2); // 2e appel episode2 → doit re-fetch

      // Assert
      // ❌ DOIT ÉCHOUER INITIALEMENT
      expect(mockLivresAuteursService.getLivresAuteurs).toHaveBeenCalledTimes(4);
    });
  });

  describe('Scénario complet: Validation de 10 livres', () => {
    it('devrait appeler API 1 fois pour valider 10 livres du même épisode', async () => {
      // Arrange - Simuler 10 livres extraits
      const episodeId = '68c707ad6e51b9428ab87e9e';
      const mockExtractedBooks = Array.from({ length: 10 }, (_, i) => ({
        auteur: `Auteur ${i + 1}`,
        titre: `Livre ${i + 1}`,
        editeur: `Éditeur ${i + 1}`
      }));

      mockLivresAuteursService.getLivresAuteurs.mockResolvedValue(mockExtractedBooks);

      // Act - Simuler la boucle de autoValidateAndSendResults()
      // Appeler _getExtractedBooks() 10 fois (une fois par livre validé)
      const results = [];
      for (let i = 0; i < 10; i++) {
        const books = await service._getExtractedBooks(episodeId);
        results.push(books);
      }

      // Assert
      // ❌ DOIT ÉCHOUER INITIALEMENT (RED phase)
      // Actuellement: 10 appels API
      // Attendu: 1 seul appel API (les 9 autres utilisent le cache)
      expect(mockLivresAuteursService.getLivresAuteurs).toHaveBeenCalledTimes(1);

      // Vérifier que les 10 résultats sont identiques
      results.forEach(result => {
        expect(result).toHaveLength(10);
        expect(result[0]).toEqual({ author: 'Auteur 1', title: 'Livre 1' });
      });
    });
  });
});
