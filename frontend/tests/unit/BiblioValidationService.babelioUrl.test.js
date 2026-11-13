/**
 * Une suggestion Babelio garde l'URL du livre suggéré (Issue #339).
 *
 * Bug : l'URL n'était conservée que si la confiance backend atteignait 0.90
 * (enrichissement à l'extraction). Une suggestion sous ce seuil (ex: co-auteurs
 * « Cyril Pedrosa & Taiyo Matsumoto » vs « Cyril Pedrosa ») perdait l'URL que
 * verifyBook avait pourtant renvoyée : la modale de validation ne pouvait pas
 * la pré-remplir, et le livre repartait dans la page Liaison Babelio.
 *
 * Mocks : sortie réelle de verifyBook capturée dans babelio-book-cases.yml.
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

describe('BiblioValidationService - URL Babelio des suggestions (Issue #339)', () => {
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

  it('une suggestion Babelio (confiance 0.58) garde l\'URL du livre suggéré', async () => {
    const bookFixture = findBook('Colcause', 'Emmanuel Carrère');
    mockBabelioService.verifyAuthor.mockResolvedValueOnce(findAuthor('Emmanuel Carrère').output);
    mockBabelioService.verifyBook.mockResolvedValueOnce(bookFixture.output);

    const result = await service.validateBiblio('Emmanuel Carrère', 'Colcause', '', null);

    expect(result.status).toBe('suggestion');
    expect(result.data.suggested.title).toBe("L'Adversaire");
    expect(result.data.babelio_url).toBe(
      'https://www.babelio.com/livres/Carrere-LAdversaire/234935'
    );
  });
});

describe('buildBookDataForBackend - URL Babelio de la suggestion (Issue #339)', () => {
  const book = {
    auteur: 'Cyril Pedrosa & Taiyo Matsumoto',
    titre: 'Nanbanjin',
    editeur: 'Dupuis (Air Libre)',
    programme: false,
  };

  it('transmet l\'URL du livre suggéré quand l\'extraction n\'en a pas', () => {
    const validationResult = {
      status: 'suggestion',
      data: {
        suggested: { author: 'Cyril Pedrosa', title: 'Nanbanjin' },
        babelio_url: 'https://www.babelio.com/livres/Pedrosa-Nanbanjin/1234567',
      },
    };

    const result = buildBookDataForBackend(book, validationResult, 'suggestion');

    expect(result.babelio_url).toBe('https://www.babelio.com/livres/Pedrosa-Nanbanjin/1234567');
  });

  it('l\'URL de l\'extraction (confiance >= 0.90) reste prioritaire', () => {
    const validationResult = {
      status: 'suggestion',
      data: { babelio_url: 'https://www.babelio.com/livres/Autre/1' },
    };

    const result = buildBookDataForBackend(
      { ...book, babelio_url: 'https://www.babelio.com/livres/Pedrosa-Nanbanjin/1234567' },
      validationResult,
      'suggestion'
    );

    expect(result.babelio_url).toBe('https://www.babelio.com/livres/Pedrosa-Nanbanjin/1234567');
  });
});
