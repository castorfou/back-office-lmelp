/**
 * La vérité terrain ne doit pas suggérer le titre d'un autre livre de la même
 * émission (Issue #358).
 *
 * Émission du 15/11/2026 : le texte de l'émission ne contient pas « Rouges
 * Truites ». Les seuls candidats « titre » renvoyés par
 * POST /api/fuzzy-search-episode sont ceux des autres livres de l'émission
 * (« Saint Lucky Luke », « Le Fondateur ») et une URL. L'auteur, lui, est
 * trouvé à 100, ce qui rendait la mauvaise suggestion crédible.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { BiblioValidationService } from '../../src/services/BiblioValidationService.js';

const EPISODE_ID = '6af98629a3c9beafb9dcb702'; // pragma: allowlist secret

// Réponse réelle de POST /api/fuzzy-search-episode
// (query_title « Rouge Truite », query_author « Pierric Bailly »)
const rougeTruiteFuzzyResponse = () => ({
  found_suggestions: true,
  title_matches: [
    ['📖 Saint Lucky Luke', 35.71],
    ['📖 Le Fondateur', 33.33],
    [
      '📖 https://www.radiofrance.fr/franceinter/podcasts/le-masque-et-la-plume/le-masque-et-la-plume-du-dimanche-15-novembre-2026-1230115?at_campaign=desc_episode&amp;at_medium=lien_RSS',
      9.68
    ]
  ],
  author_matches: [
    ['Pierric Bailly', 100.0],
    ['Pierric Bailly', 100.0],
    ['Pierric Bailly ainsi', 82.35]
  ]
});

// Livres de l'émission, au format de l'API livres-auteurs ({auteur, titre})
const episodeBooks = [
  { auteur: 'Pierric Bailly', titre: 'Rouge Truite' },
  { auteur: 'Jul & Achdé', titre: 'Saint Lucky Luke' },
  { auteur: 'Auteur Fondateur', titre: 'Le Fondateur' }
];

const mockFuzzySearchService = { searchEpisode: vi.fn() };
const mockBabelioService = { verifyAuthor: vi.fn(), verifyBook: vi.fn() };
const mockLivresAuteursService = { getLivresAuteurs: vi.fn() };

describe('BiblioValidationService - titre d\'un autre livre de l\'émission (Issue #358)', () => {
  let service;

  beforeEach(() => {
    vi.resetAllMocks();
    mockLivresAuteursService.getLivresAuteurs.mockResolvedValue(episodeBooks);
    mockFuzzySearchService.searchEpisode.mockResolvedValue(rougeTruiteFuzzyResponse());
    mockBabelioService.verifyAuthor.mockResolvedValue({
      babelio_suggestion: 'Pierric Bailly',
      confidence_score: 1.0,
      original: 'Pierric Bailly',
      status: 'verified'
    });
    mockBabelioService.verifyBook.mockResolvedValue({
      babelio_data: null,
      babelio_suggestion_author: null,
      babelio_suggestion_title: null,
      babelio_url: null,
      confidence_score: 0,
      error_message: null,
      original_author: 'Pierric Bailly',
      original_title: 'Rouge Truite',
      status: 'not_found'
    });

    service = new BiblioValidationService({
      fuzzySearchService: mockFuzzySearchService,
      babelioService: mockBabelioService,
      livresAuteursService: mockLivresAuteursService,
      localAuthorService: null
    });
  });

  it('ne suggère pas « Saint Lucky Luke » pour « Rouge Truite » : le livre sort en non trouvé', async () => {
    const result = await service.validateBiblio('Pierric Bailly', 'Rouge Truite', 'P.O.L.', EPISODE_ID);

    expect(result.data.suggested?.title).not.toBe('Saint Lucky Luke');
    expect(result.status).toBe('not_found');
  });

  describe('_filterGroundTruthTitleCandidates', () => {
    const original = { author: 'Pierric Bailly', title: 'Rouge Truite' };
    const titles = (result) => result.title_matches.map(tm => tm[0]);

    it('retire le titre d\'un autre livre de l\'émission, même avec casse et accents différents', () => {
      const result = service._filterGroundTruthTitleCandidates(
        { found_suggestions: true, title_matches: [['📖 Rouge truite à la ligne', 90]] },
        original,
        ['Rouge Truite', 'ROUGE TRUITE A LA LIGNE']
      );

      expect(titles(result)).toEqual([]);
    });

    it('garde le titre du livre validé lui-même', () => {
      const result = service._filterGroundTruthTitleCandidates(
        { found_suggestions: true, title_matches: [['📖 Rouge Truite', 95]] },
        original,
        ['Rouge Truite', 'Saint Lucky Luke']
      );

      expect(titles(result)).toEqual(['📖 Rouge Truite']);
    });

    it('filtre aussi le format camelCase titleMatches', () => {
      const result = service._filterGroundTruthTitleCandidates(
        { found_suggestions: true, titleMatches: [['📖 Saint Lucky Luke', 90]] },
        original,
        ['Saint Lucky Luke']
      );

      expect(result.titleMatches).toEqual([]);
    });

    it('ne modifie pas la réponse reçue', () => {
      const response = rougeTruiteFuzzyResponse();
      service._filterGroundTruthTitleCandidates(response, original, ['Saint Lucky Luke']);

      expect(response.title_matches).toHaveLength(3);
    });
  });

  describe('_extractGroundTruthSuggestion : seuil minimal', () => {
    it('ne propose aucun titre faible et très éloigné du titre d\'origine, même hors liste de l\'émission', () => {
      const suggestion = service._extractGroundTruthSuggestion(
        rougeTruiteFuzzyResponse(),
        { author: 'Pierric Bailly', title: 'Rouge Truite' }
      );

      expect(suggestion.title).toBe('');
    });

    it('garde un candidat faible mais proche du titre d\'origine (Colcause → Kolkhoze)', () => {
      const suggestion = service._extractGroundTruthSuggestion(
        { found_suggestions: true, title_matches: [['📖 Kolkhoze', 38]], author_matches: [['Carrère', 90]] },
        { author: 'Emmanuel Carrère', title: 'Colcause' }
      );

      expect(suggestion.title).toBe('Kolkhoze');
    });
  });

  it('_isValidTitleSuggestion rejette un texte contenant une entité HTML', () => {
    expect(service._isValidTitleSuggestion('Tom &amp; Jerry contre tous', null)).toBe(false);
    expect(service._isValidTitleSuggestion('Tom &#38; Jerry contre tous', null)).toBe(false);
    expect(service._isValidTitleSuggestion('Tom & Jerry contre tous', null)).toBe(true);
  });
});
