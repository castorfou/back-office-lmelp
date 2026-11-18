/**
 * L'éditeur Babelio accompagne l'URL Babelio du résultat de validation (Issue #352).
 *
 * L'enrichissement à l'extraction (seule source de babelio_publisher) disparaît :
 * verifyBook renvoie déjà babelio_publisher (babelio_service.verify_book), la
 * validation le conserve pour la page dont elle retient l'URL.
 *
 * Mocks : sortie réelle de verifyBook capturée dans babelio-book-cases.yml,
 * complétée du champ babelio_publisher que le serveur renvoie désormais.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import yaml from 'js-yaml';
import { BiblioValidationService } from '../../src/services/BiblioValidationService.js';
import { buildBookDataForBackend } from '../../src/utils/buildBookDataForBackend.js';

const fixturesDir = join(dirname(fileURLToPath(import.meta.url)), '..', 'fixtures');
const bookCases = yaml.load(readFileSync(join(fixturesDir, 'babelio-book-cases.yml'), 'utf8'));
const authorCases = yaml.load(readFileSync(join(fixturesDir, 'babelio-author-cases.yml'), 'utf8'));

const findBook = (title, author) =>
  bookCases.cases.find((c) => c.input.title === title && c.input.author === author);
const findAuthor = (name) => authorCases.cases.find((c) => c.input.name === name);

const mockBabelioService = { verifyAuthor: vi.fn(), verifyBook: vi.fn() };

describe('BiblioValidationService - éditeur Babelio (Issue #352)', () => {
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

  it('une suggestion garde l\'éditeur de la page Babelio dont elle garde l\'URL', async () => {
    const bookOutput = { ...findBook('Colcause', 'Emmanuel Carrère').output, babelio_publisher: 'P.O.L' };
    mockBabelioService.verifyAuthor.mockResolvedValueOnce(findAuthor('Emmanuel Carrère').output);
    mockBabelioService.verifyBook.mockResolvedValueOnce(bookOutput);

    const result = await service.validateBiblio('Emmanuel Carrère', 'Colcause', '', null);

    expect(result.data.babelio_url).toBe('https://www.babelio.com/livres/Carrere-LAdversaire/234935');
    expect(result.data.babelio_publisher).toBe('P.O.L');
  });

  it('pas d\'éditeur sans URL Babelio', async () => {
    mockBabelioService.verifyAuthor.mockResolvedValueOnce({ status: 'not_found' });
    mockBabelioService.verifyBook.mockResolvedValue({ status: 'not_found', babelio_publisher: 'X' });

    const result = await service.validateBiblio('Inconnu', 'Introuvable', '', null);

    expect(result.data?.babelio_publisher).toBeUndefined();
  });
});

describe('buildBookDataForBackend - éditeur Babelio de la validation (Issue #352)', () => {
  const book = { auteur: 'Emmanuel Carrère', titre: 'Colcause', editeur: 'POL', programme: true };

  it('transmet l\'éditeur Babelio du résultat de validation', () => {
    const validationResult = {
      status: 'suggestion',
      data: { babelio_url: 'https://www.babelio.com/livres/x/1', babelio_publisher: 'P.O.L' },
    };

    const result = buildBookDataForBackend(book, validationResult, 'suggestion');

    expect(result.babelio_publisher).toBe('P.O.L');
  });
});
