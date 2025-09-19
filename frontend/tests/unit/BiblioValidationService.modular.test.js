/**
 * Tests modulaires pour BiblioValidationService
 * Utilise des fixtures séparées par service pour plus de réalisme et maintenabilité
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import yaml from 'js-yaml';
import { BiblioValidationService } from '../../src/services/BiblioValidationService.js';

// Load modular fixtures
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const fixturesDir = join(__dirname, '..', 'fixtures');

const fuzzySearchCases = yaml.load(readFileSync(join(fixturesDir, 'fuzzy-search-cases.yml'), 'utf8'));
const babelioAuthorCases = yaml.load(readFileSync(join(fixturesDir, 'babelio-author-cases.yml'), 'utf8'));
const babelioBookCases = yaml.load(readFileSync(join(fixturesDir, 'babelio-book-cases.yml'), 'utf8'));
const validationScenarios = yaml.load(readFileSync(join(fixturesDir, 'biblio-validation-scenarios.yml'), 'utf8'));

// Mock services
const mockFuzzySearchService = {
  searchEpisode: vi.fn()
};

const mockBabelioService = {
  verifyAuthor: vi.fn(),
  verifyBook: vi.fn()
};

const mockLocalAuthorService = {
  findAuthor: vi.fn()
};

describe('BiblioValidationService - Modular Tests', () => {
  let biblioValidationService;

  beforeEach(() => {
    vi.clearAllMocks();

    biblioValidationService = new BiblioValidationService({
      fuzzySearchService: mockFuzzySearchService,
      babelioService: mockBabelioService,
      localAuthorService: mockLocalAuthorService
    });
  });

  /**
   * Helper function to find fixture by reference name
   */
  function findFixture(fixtures, refName) {
    const fixture = fixtures.cases.find(c => c.name === refName);
    if (!fixture) {
      throw new Error(`Fixture not found: ${refName}`);
    }
    return fixture;
  }

  /**
   * Helper function to setup mocks for a scenario
   */
  function setupScenarioMocks(scenario) {
    const calls = scenario.calls;

    // Setup fuzzy search mocks
    const fuzzySearchCalls = calls.filter(call => call.service === 'fuzzySearch');
    fuzzySearchCalls.forEach(call => {
      const fixture = findFixture(fuzzySearchCases, call.ref);
      mockFuzzySearchService.searchEpisode.mockResolvedValueOnce(fixture.output);
    });

    // Setup babelio author mocks
    const authorCalls = calls.filter(call => call.service === 'babelioAuthor');
    authorCalls.forEach(call => {
      const fixture = findFixture(babelioAuthorCases, call.ref);
      mockBabelioService.verifyAuthor.mockResolvedValueOnce(fixture.output);
    });

    // Setup babelio book mocks (can be multiple calls)
    const bookCalls = calls.filter(call => call.service === 'babelioBook');
    bookCalls.forEach(call => {
      const fixture = findFixture(babelioBookCases, call.ref);
      mockBabelioService.verifyBook.mockResolvedValueOnce(fixture.output);
    });
  }

  describe('🔍 Individual Service Tests', () => {
    describe('Fuzzy Search Cases', () => {
      fuzzySearchCases.cases.forEach((testCase) => {
        it(`should handle: ${testCase.name}`, async () => {
          // This tests just the fixture consistency
          expect(testCase.input).toHaveProperty('episode_id');
          expect(testCase.output).toHaveProperty('found_suggestions');
          expect(testCase.output).toHaveProperty('title_matches');
          expect(testCase.output).toHaveProperty('author_matches');
        });
      });
    });

    describe('Babelio Author Cases', () => {
      babelioAuthorCases.cases.forEach((testCase) => {
        it(`should handle: ${testCase.name}`, async () => {
          expect(testCase.input).toHaveProperty('name');
          expect(testCase.output).toHaveProperty('status');
          expect(['verified', 'corrected', 'not_found']).toContain(testCase.output.status);
        });
      });
    });

    describe('Babelio Book Cases', () => {
      babelioBookCases.cases.forEach((testCase) => {
        it(`should handle: ${testCase.name}`, async () => {
          expect(testCase.input).toHaveProperty('title');
          expect(testCase.input).toHaveProperty('author');
          expect(testCase.output).toHaveProperty('status');
          expect(['verified', 'corrected', 'not_found']).toContain(testCase.output.status);
        });
      });
    });
  });

  describe('🎯 End-to-End Validation Scenarios', () => {
    validationScenarios.scenarios.forEach((scenario) => {
      it(`should handle scenario: ${scenario.name}`, async () => {
        // Setup mocks based on scenario calls
        setupScenarioMocks(scenario);

        // Execute validation
        const result = await biblioValidationService.validateBiblio(
          scenario.input.author,
          scenario.input.title,
          scenario.input.publisher,
          scenario.input.episodeId
        );

        // Verify result
        expect(result.status).toBe(scenario.expected.status);

        if (scenario.expected.status === 'suggestion') {
          expect(result.data.suggested.author).toBe(scenario.expected.author);
          expect(result.data.suggested.title).toBe(scenario.expected.title);
          if (scenario.expected.corrections) {
            expect(result.data.corrections.author).toBe(scenario.expected.corrections.author);
            expect(result.data.corrections.title).toBe(scenario.expected.corrections.title);
          }
          if (scenario.expected.source) {
            expect(result.data.source).toBe(scenario.expected.source);
          }
        }

        if (scenario.expected.status === 'not_found') {
          if (scenario.expected.reason) {
            expect(result.data.reason).toBe(scenario.expected.reason);
          }
          if (scenario.expected.attempts) {
            expect(result.data.attempts).toEqual(scenario.expected.attempts);
          }
        }

        // Log for debugging
        console.log(`\n=== SCENARIO: ${scenario.name} ===`);
        console.log(`Expected: ${scenario.expected.status}`);
        console.log(`Actual: ${result.status}`);
        if (result.status === 'suggestion') {
          console.log(`Suggestion: ${result.data.suggested?.author} - ${result.data.suggested?.title}`);
        }
      });
    });
  });

  describe('🚨 Critical Bug Tests', () => {
    it('should call verifyBook with corrected author when status=verified with different suggestion', async () => {
      // Le bug critique : Alain Mabancou → Mabanckou mais book search avec original
      setupScenarioMocks(validationScenarios.scenarios.find(s => s.name.includes('Alain Mabancou')));

      await biblioValidationService.validateBiblio(
        'Alain Mabancou',
        'Ramsès de Paris',
        'Seuil',
        '68c707ad6e51b9428ab87e9e'  // pragma: allowlist secret
      );

      // Verify the critical calls were made in the right order
      expect(mockBabelioService.verifyAuthor).toHaveBeenCalledWith('Alain Mabancou');
      expect(mockBabelioService.verifyBook).toHaveBeenCalledTimes(2);

      // First call should be with original author (fails)
      expect(mockBabelioService.verifyBook).toHaveBeenNthCalledWith(1, 'Ramsès de Paris', 'Alain Mabancou');

      // Second call should be with corrected author (succeeds)
      expect(mockBabelioService.verifyBook).toHaveBeenNthCalledWith(2, 'Ramsès de Paris', 'Alain Mabanckou');
    });
  });

  describe('🔧 Author Reconstruction from Ground Truth', () => {
    it('should filter noise words when reconstructing author from ground truth fragments', () => {
      // Cas Maria Pourchet avec fragment parasite "pour"
      const groundTruthResult = {
        found_suggestions: true,
        titleMatches: [["📖 Tressaillir", 100]],
        authorMatches: [["pour", 90], ["Maria", 90], ["Pourchet", 90], ["Pour", 90]]
      };

      const suggestion = biblioValidationService._extractGroundTruthSuggestion(groundTruthResult);

      // Doit filtrer "pour" et "Pour" et reconstruire "Maria Pourchet"
      expect(suggestion.author).toBe("Maria Pourchet");
      expect(suggestion.title).toBe("Tressaillir");
    });

    it('should handle complex fragmented names correctly', () => {
      // Cas Yakuta Ali Kavazovic
      const groundTruthResult = {
        found_suggestions: true,
        titleMatches: [["📖 Au grand jamais", 100]],
        authorMatches: [["Alikavazovic", 82], ["Jakuta", 78]]
      };

      const suggestion = biblioValidationService._extractGroundTruthSuggestion(groundTruthResult);

      expect(suggestion.author).toBe("Jakuta Alikavazovic");
      expect(suggestion.title).toBe("Au grand jamais");
    });
  });
});
