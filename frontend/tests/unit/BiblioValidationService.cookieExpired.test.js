/**
 * La validation dit quand un blocage vient d'un cookie Babelio expiré (Issue #352).
 *
 * Le serveur refuse sans rien envoyer et renvoie
 * { status: 'blocked_403', reason: 'cookie_expired' } (babelio_service.verify_book).
 * validateBiblio doit le remonter tel quel, même si le refus touche un appel
 * de confirmation et non le premier : un livre ne doit jamais finir « introuvable »
 * parce que le cookie a expiré au milieu de sa validation.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { BiblioValidationService } from '../../src/services/BiblioValidationService.js';

const cookieExpired = {
  status: 'blocked_403',
  reason: 'cookie_expired',
  original_title: 'Le Sillon',
  babelio_suggestion_title: null,
  original_author: 'Valérie Manteau',
  babelio_suggestion_author: null,
  confidence_score: 0.0,
  babelio_data: null,
  babelio_url: null,
  babelio_author_url: null,
  error_message: 'Babelio a bloqué la requête (403).',
};
const babelio403 = { ...cookieExpired, reason: null };

const mockBabelioService = { verifyAuthor: vi.fn(), verifyBook: vi.fn() };

describe('BiblioValidationService - cookie expiré (Issue #352)', () => {
  let service;

  beforeEach(() => {
    vi.resetAllMocks();
    service = new BiblioValidationService({
      fuzzySearchService: { searchEpisode: vi.fn() },
      babelioService: mockBabelioService,
      livresAuteursService: { getLivresAuteurs: vi.fn().mockResolvedValue([]) },
      localAuthorService: null,
    });
  });

  it('remonte reason cookie_expired', async () => {
    mockBabelioService.verifyAuthor.mockResolvedValue({ ...cookieExpired });
    mockBabelioService.verifyBook.mockResolvedValue({ ...cookieExpired });

    const result = await service.validateBiblio('Valérie Manteau', 'Le Sillon', '', null);

    expect(result.status).toBe('blocked_403');
    expect(result.data.reason).toBe('cookie_expired');
  });

  it('un vrai 403 de Babelio garde sa raison habituelle', async () => {
    mockBabelioService.verifyAuthor.mockResolvedValue({ ...babelio403 });
    mockBabelioService.verifyBook.mockResolvedValue({ ...babelio403 });

    const result = await service.validateBiblio('Valérie Manteau', 'Le Sillon', '', null);

    expect(result.status).toBe('blocked_403');
    expect(result.data.reason).toBe('babelio_blocked_403');
  });

  it('un cookie expiré sur un appel de confirmation bloque tout le livre', async () => {
    mockBabelioService.verifyAuthor.mockResolvedValue({
      status: 'not_found', original: 'Valérie Manteau', babelio_suggestion: null,
      confidence_score: 0, babelio_data: null, babelio_url: null, error_message: null,
    });
    // 1er verifyBook : introuvable ; suivants (recherche titre seul) : cookie expiré
    mockBabelioService.verifyBook
      .mockResolvedValueOnce({ ...cookieExpired, status: 'not_found', reason: undefined })
      .mockResolvedValue({ ...cookieExpired });

    const result = await service.validateBiblio('Valérie Manteau', 'Le Sillon', '', null);

    expect(mockBabelioService.verifyBook.mock.calls.length).toBeGreaterThan(1);
    expect(result.status).toBe('blocked_403');
    expect(result.data.reason).toBe('cookie_expired');
  });
});
