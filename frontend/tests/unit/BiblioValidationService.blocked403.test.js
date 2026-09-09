/**
 * Tests TDD pour la propagation du statut blocked_403 (Issue #304).
 *
 * Bug racine : un blocage Babelio (403) sur l'auteur et/ou le livre n'était
 * reconnu par aucune branche de `_arbitrateResults`/`_tryPhase0DirectValidation`
 * (qui ne testent que 'verified'/'corrected'/'not_found') — le blocage était
 * donc silencieusement confondu avec un "livre introuvable".
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { BiblioValidationService } from '../../src/services/BiblioValidationService.js';

const mockFuzzySearchService = {
  searchEpisode: vi.fn()
};

const mockBabelioService = {
  verifyAuthor: vi.fn(),
  verifyBook: vi.fn()
};

const mockLivresAuteursService = {
  getLivresAuteurs: vi.fn()
};

describe('BiblioValidationService - blocked_403 (Issue #304)', () => {
  let biblioValidationService;

  beforeEach(() => {
    vi.clearAllMocks();
    mockLivresAuteursService.getLivresAuteurs.mockResolvedValue([]);

    biblioValidationService = new BiblioValidationService({
      fuzzySearchService: mockFuzzySearchService,
      babelioService: mockBabelioService,
      livresAuteursService: mockLivresAuteursService,
      localAuthorService: null
    });
  });

  it('retourne le statut blocked_403 quand auteur et livre sont bloqués par Babelio', async () => {
    mockBabelioService.verifyAuthor.mockResolvedValue({ status: 'blocked_403' });
    mockBabelioService.verifyBook.mockResolvedValue({ status: 'blocked_403' });

    const result = await biblioValidationService.validateBiblio('Auteur Test', 'Titre Test', '', null);

    expect(result.status).toBe('blocked_403');
  });

  it('retourne toujours not_found pour un livre légitimement introuvable (non-régression)', async () => {
    mockBabelioService.verifyAuthor.mockResolvedValue({ status: 'not_found' });
    mockBabelioService.verifyBook.mockResolvedValue({ status: 'not_found' });

    const result = await biblioValidationService.validateBiblio('Auteur Inconnu', 'Titre Inconnu', '', null);

    expect(result.status).toBe('not_found');
  });

  it('retourne toujours verified pour une validation directe réussie (non-régression)', async () => {
    mockBabelioService.verifyAuthor.mockResolvedValue({ status: 'verified', confidence_score: 1.0 });
    mockBabelioService.verifyBook.mockResolvedValue({ status: 'verified', confidence_score: 1.0 });

    const result = await biblioValidationService.validateBiblio('Auteur Connu', 'Titre Connu', '', null);

    expect(result.status).toBe('verified');
  });

  it('en Phase 0 (livre extrait correspondant), retourne blocked_403 sans retomber sur Phase 1', async () => {
    mockLivresAuteursService.getLivresAuteurs.mockResolvedValue([
      { auteur: 'Auteur Test', titre: 'Titre Test' }
    ]);
    mockBabelioService.verifyBook.mockResolvedValue({ status: 'blocked_403' });
    mockBabelioService.verifyAuthor.mockResolvedValue({ status: 'blocked_403' });

    const result = await biblioValidationService.validateBiblio('Auteur Test', 'Titre Test', '', 'ep1');

    expect(result.status).toBe('blocked_403');
    // Un seul appel réseau total : pas de fallback silencieux vers Phase 1
    expect(mockBabelioService.verifyBook).toHaveBeenCalledTimes(1);
    expect(mockBabelioService.verifyAuthor).not.toHaveBeenCalled();
  });
});
