/**
 * Test TDD pour optimiser les appels redondants de loadBooksForEpisode (Issue #85 - Performance)
 *
 * PROBLÈME:
 * Quand l'utilisateur clique "Relancer validation Biblio" (🔄):
 * 1. refreshEpisodeCache() ligne 932 → loadBooksForEpisode()
 * 2. loadBooksForEpisode() ligne 831 → GET /api/livres-auteurs → enrichit 10 livres (1er cycle)
 * 3. Si needsValidation (ligne 839), loadBooksForEpisode() appelle autoValidateAndSendResults()
 * 4. Puis loadBooksForEpisode() ligne 844 → GET /api/livres-auteurs à nouveau → enrichit 10 livres (2e cycle)
 *
 * Résultat: 2 cycles d'enrichissement au lieu de 1
 *
 * SOLUTION:
 * Éviter le 2e GET /api/livres-auteurs ligne 844 car les livres sont déjà dans le cache MongoDB
 * après autoValidateAndSendResults().
 *
 * CE TEST DOIT ÉCHOUER initialement car loadBooksForEpisode() appelle 2 fois getLivresAuteurs.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { mount } from '@vue/test-utils';
import LivresAuteurs from '../../src/views/LivresAuteurs.vue';
import { livresAuteursService } from '../../src/services/api.js';

// Mock de tous les services
vi.mock('../../src/services/api.js', () => ({
  livresAuteursService: {
    getEpisodesWithReviews: vi.fn(),
    getLivresAuteurs: vi.fn(),
    deleteCacheByEpisode: vi.fn(),
    setValidationResults: vi.fn(),
    autoProcessVerifiedBooks: vi.fn()
  },
  episodeService: {
    getEpisodeById: vi.fn()
  }
}));

// Mock BiblioValidationService
vi.mock('../../src/services/BiblioValidationService.js', () => ({
  default: {
    validateBiblio: vi.fn()
  }
}));

import BiblioValidationService from '../../src/services/BiblioValidationService.js';

describe('LivresAuteurs - Optimisation loadBooksForEpisode (Issue #85)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('devrait appeler getLivresAuteurs 1 SEULE FOIS après refreshEpisodeCache (RED phase)', async () => {
    // Arrange - Mock épisodes
    const mockEpisodes = [
      {
        id: '68c707ad6e51b9428ab87e9e',
        date: '2025-01-15',
        titre: 'Épisode Test',
        avis_critique_id: 'abc123',
        has_incomplete_books: true
      }
    ];

    livresAuteursService.getEpisodesWithReviews.mockResolvedValue(mockEpisodes);

    // Mock books SANS statuts (needsValidation = true)
    const mockBooksWithoutStatus = [
      {
        auteur: 'Carlos Gimenez',
        titre: 'Paracuellos, Intégrale',
        editeur: 'Audie-Fluide glacial',
        episode_oid: '68c707ad6e51b9428ab87e9e',
        cache_id: 'cache1',
        programme: true
        // PAS de status → needsValidation = true
      },
      {
        auteur: 'Alain Mabanckou',
        titre: 'Ramsès de Paris',
        editeur: 'Seuil',
        episode_oid: '68c707ad6e51b9428ab87e9e',
        cache_id: 'cache2',
        programme: true
      }
    ];

    // Mock books AVEC statuts (après validation)
    const mockBooksWithStatus = [
      {
        ...mockBooksWithoutStatus[0],
        status: 'verified',
        babelio_url: 'https://www.babelio.com/livres/Gimenez-Paracuellos-Integrale/112880',
        babelio_publisher: 'Audie-Fluide glacial'
      },
      {
        ...mockBooksWithoutStatus[1],
        status: 'suggestion',
        suggested_author: 'Alain Mabanckou'
      }
    ];

    // Mock BiblioValidationService
    BiblioValidationService.validateBiblio
      .mockResolvedValueOnce({ status: 'verified', data: {} })
      .mockResolvedValueOnce({ status: 'corrected', data: { suggested: { author: 'Alain Mabanckou' } } });

    // Mock setValidationResults (backend met à jour le cache)
    livresAuteursService.setValidationResults.mockResolvedValue({ success: true });

    // Mock deleteCacheByEpisode
    livresAuteursService.deleteCacheByEpisode.mockResolvedValue({ deleted_count: 2 });

    // Mock getLivresAuteurs:
    // - 1er appel (ligne 831): retourne books SANS statuts → déclenche validation
    // - 2e appel (ligne 844): retourne books AVEC statuts (cache mis à jour par backend)
    livresAuteursService.getLivresAuteurs
      .mockResolvedValueOnce(mockBooksWithoutStatus) // 1er appel
      .mockResolvedValueOnce(mockBooksWithStatus);   // 2e appel (REDONDANT - on veut éviter ça)

    // Mock autoProcessVerifiedBooks
    livresAuteursService.autoProcessVerifiedBooks.mockResolvedValue({ success: true });

    // Monter le composant
    const wrapper = mount(LivresAuteurs, {
      global: {
        stubs: {
          Navigation: true,
          BiblioValidationCell: true
        }
      }
    });

    // Attendre le chargement initial
    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 50));

    // Sélectionner un épisode
    wrapper.vm.selectedEpisodeId = '68c707ad6e51b9428ab87e9e';
    await wrapper.vm.onEpisodeChange();
    await new Promise(resolve => setTimeout(resolve, 100));

    // Reset le spy pour compter uniquement les appels de refreshEpisodeCache
    vi.clearAllMocks();

    // Reconfigurer les mocks pour refreshEpisodeCache
    livresAuteursService.deleteCacheByEpisode.mockResolvedValue({ deleted_count: 2 });
    livresAuteursService.getLivresAuteurs
      .mockResolvedValueOnce(mockBooksWithoutStatus) // 1er GET après cache delete
      .mockResolvedValueOnce(mockBooksWithStatus);   // 2e GET (ligne 844) - REDONDANT
    BiblioValidationService.validateBiblio
      .mockResolvedValueOnce({ status: 'verified', data: {} })
      .mockResolvedValueOnce({ status: 'corrected', data: { suggested: { author: 'Alain Mabanckou' } } });
    livresAuteursService.setValidationResults.mockResolvedValue({ success: true });
    livresAuteursService.autoProcessVerifiedBooks.mockResolvedValue({ success: true });

    // Act - Simuler click sur "Relancer validation Biblio" (🔄)
    await wrapper.vm.refreshEpisodeCache();
    await new Promise(resolve => setTimeout(resolve, 200));

    // Assert
    // ❌ DOIT ÉCHOUER INITIALEMENT (RED phase)
    // Actuellement: getLivresAuteurs appelé 2 fois (lignes 831 et 844)
    // Attendu: getLivresAuteurs appelé 1 SEULE fois (ligne 831)
    // Le 2e appel ligne 844 est REDONDANT car le backend a déjà mis à jour le cache
    expect(livresAuteursService.getLivresAuteurs).toHaveBeenCalledTimes(1);
    expect(livresAuteursService.getLivresAuteurs).toHaveBeenCalledWith({
      episode_oid: '68c707ad6e51b9428ab87e9e'
    });

    // Vérifier que la validation a bien eu lieu
    expect(BiblioValidationService.validateBiblio).toHaveBeenCalledTimes(2);
    expect(livresAuteursService.setValidationResults).toHaveBeenCalledTimes(1);
  });

  it('devrait charger les livres 1 fois même quand needsValidation est true', async () => {
    // Arrange
    const mockEpisodes = [
      {
        id: '68c707ad6e51b9428ab87e9e',
        date: '2025-01-15',
        titre: 'Épisode Test',
        avis_critique_id: 'abc123'
      }
    ];

    const mockBooksWithoutStatus = [
      {
        auteur: 'Test Author',
        titre: 'Test Book',
        editeur: 'Test Publisher',
        episode_oid: '68c707ad6e51b9428ab87e9e',
        cache_id: 'test1'
      }
    ];

    const mockBooksWithStatus = [
      {
        ...mockBooksWithoutStatus[0],
        status: 'verified'
      }
    ];

    livresAuteursService.getEpisodesWithReviews.mockResolvedValue(mockEpisodes);
    livresAuteursService.getLivresAuteurs
      .mockResolvedValueOnce(mockBooksWithoutStatus)
      .mockResolvedValueOnce(mockBooksWithStatus); // 2e appel REDONDANT

    BiblioValidationService.validateBiblio.mockResolvedValue({ status: 'verified', data: {} });
    livresAuteursService.setValidationResults.mockResolvedValue({ success: true });
    livresAuteursService.autoProcessVerifiedBooks.mockResolvedValue({ success: true });

    const wrapper = mount(LivresAuteurs, {
      global: {
        stubs: {
          Navigation: true,
          BiblioValidationCell: true
        }
      }
    });

    await wrapper.vm.$nextTick();
    await new Promise(resolve => setTimeout(resolve, 50));

    // Act - Sélectionner épisode (déclenche loadBooksForEpisode)
    wrapper.vm.selectedEpisodeId = '68c707ad6e51b9428ab87e9e';
    await wrapper.vm.onEpisodeChange();
    await new Promise(resolve => setTimeout(resolve, 100));

    // Assert
    // ❌ DOIT ÉCHOUER INITIALEMENT (RED phase)
    // Actuellement: 2 appels (ligne 831 + ligne 844)
    // Attendu: 1 seul appel (ligne 831)
    expect(livresAuteursService.getLivresAuteurs).toHaveBeenCalledTimes(1);
  });

  // Note: Test supprimé car les 2 tests ci-dessus couvrent déjà le cas principal
  // (éviter le 2e GET redondant après autoValidateAndSendResults)
});
