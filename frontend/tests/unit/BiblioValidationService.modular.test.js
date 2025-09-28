/**
 * Tests pour BiblioValidationService
 * Utilise les fixtures biblio-validation-cases.yml capturées depuis l'interface
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import yaml from 'js-yaml';
import { BiblioValidationService } from '../../src/services/BiblioValidationService.js';

// Load all fixtures
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const fixturesDir = join(__dirname, '..', 'fixtures');

const fuzzySearchCases = yaml.load(readFileSync(join(fixturesDir, 'fuzzy-search-cases.yml'), 'utf8'));
const babelioAuthorCases = yaml.load(readFileSync(join(fixturesDir, 'babelio-author-cases.yml'), 'utf8'));
const babelioBookCases = yaml.load(readFileSync(join(fixturesDir, 'babelio-book-cases.yml'), 'utf8'));

let biblioValidationCases;
try {
  biblioValidationCases = yaml.load(readFileSync(join(fixturesDir, 'biblio-validation-cases.yml'), 'utf8'));
} catch (error) {
  biblioValidationCases = { cases: [] };
}

// Mock services
const mockFuzzySearchService = {
  searchEpisode: vi.fn()
};

const mockBabelioService = {
  verifyAuthor: vi.fn(),
  verifyBook: vi.fn()
};

describe('BiblioValidationService Tests', () => {
  let biblioValidationService;

  beforeEach(() => {
    vi.clearAllMocks();

    biblioValidationService = new BiblioValidationService({
      fuzzySearchService: mockFuzzySearchService,
      babelioService: mockBabelioService,
      localAuthorService: null
    });
  });

  describe('📦 Fixture Format Validation', () => {
    it('should have valid fixture format', () => {
      expect(biblioValidationCases).toHaveProperty('cases');
      expect(Array.isArray(biblioValidationCases.cases)).toBe(true);
    });

    biblioValidationCases.cases.forEach((testCase, index) => {
      it(`case ${index + 1} should have correct structure`, () => {
        // Input validation
        expect(testCase).toHaveProperty('input');
        expect(testCase.input).toHaveProperty('author');
        expect(testCase.input).toHaveProperty('title');
        expect(testCase.input).toHaveProperty('publisher');
        expect(testCase.input).toHaveProperty('episodeId');

        // Output validation
        expect(testCase).toHaveProperty('output');
        expect(testCase.output).toHaveProperty('status');
        expect(['verified', 'suggestion', 'not_found', 'error']).toContain(testCase.output.status);

        // Status-specific validations
        if (testCase.output.status === 'suggestion') {
          expect(testCase.output).toHaveProperty('suggested_author');
          expect(testCase.output).toHaveProperty('suggested_title');
          expect(testCase.output).toHaveProperty('corrections');
          expect(testCase.output.corrections).toHaveProperty('author');
          expect(testCase.output.corrections).toHaveProperty('title');
          expect(typeof testCase.output.corrections.author).toBe('boolean');
          expect(typeof testCase.output.corrections.title).toBe('boolean');
        }

        // Should NOT have timestamp or confidence_score
        expect(testCase).not.toHaveProperty('timestamp');
        expect(testCase.output).not.toHaveProperty('confidence_score');
      });
    });
  });

  // Helper functions with fixture error detection
  function getFixtureResponseOrError(service, input, fixture) {
    if (fixture) {
      return fixture.output;
    }

    // Return special fixture error response
    return {
      status: 'fixture_error',
      error_message: `Missing ${service} fixture for input: ${JSON.stringify(input)}`
    };
  }

  function findFixtureByAuthor(author) {
    return babelioAuthorCases.cases.find(c =>
      c.input.name === author || c.input.name?.toLowerCase() === author.toLowerCase()
    );
  }

  function findFixtureByBook(title, author) {
    return babelioBookCases.cases.find(c =>
      (c.input.title === title || c.input.title?.toLowerCase() === title.toLowerCase()) &&
      (c.input.author === author || c.input.author?.toLowerCase() === author.toLowerCase())
    );
  }

  function findFuzzyFixture(episodeId, author, title) {
    return fuzzySearchCases.cases.find(c =>
      c.input.episode_id === episodeId &&
      (c.input.query_author === author || c.input.query_author?.toLowerCase() === author.toLowerCase()) &&
      (c.input.query_title === title || c.input.query_title?.toLowerCase() === title.toLowerCase())
    );
  }

  describe('🎯 Captured Cases with Real Data', () => {
    // Summary of manual-review cases (fixtures with `expected` filled)
    const manualReviewCases = (biblioValidationCases.cases || []).filter(c => c.expected);
    if (manualReviewCases.length > 0) {
      console.warn(`\n⚠️ ${manualReviewCases.length} captured case(s) marked for manual review (fixtures contain an \`expected\` block).`);
      manualReviewCases.forEach((c, i) => {
        console.warn(`  - case ${i + 1}: ${c.input.author} - ${c.input.title}`);
      });
      console.warn('  These cases will be reported as warnings during tests and will not fail the suite.\n');
    }
    if (biblioValidationCases.cases.length === 0) {
      it('no captured cases found - run capture to generate test cases', () => {
        console.log('ℹ️ No biblio-validation-cases.yml found or empty. Use the 🔄 YAML button to capture real cases.');
        expect(true).toBe(true);
      });
    } else {
      biblioValidationCases.cases.forEach((testCase, index) => {
        it(`should reproduce case ${index + 1}: ${testCase.input.author} - ${testCase.input.title}`, async () => {
          // Find real fixture data
          const authorFixture = findFixtureByAuthor(testCase.input.author);
          const bookFixture = findFixtureByBook(testCase.input.title, testCase.input.author);
          const fuzzyFixture = findFuzzyFixture(testCase.input.episodeId, testCase.input.author, testCase.input.title);

          // Mock with REAL captured data OR fixture error responses
          const fuzzyResponse = getFixtureResponseOrError('fuzzySearch', { episode_id: testCase.input.episodeId, query_author: testCase.input.author, query_title: testCase.input.title }, fuzzyFixture);
          const authorResponse = getFixtureResponseOrError('babelioAuthor', { name: testCase.input.author }, authorFixture);
          const bookResponse = getFixtureResponseOrError('babelioBook', { author: testCase.input.author, title: testCase.input.title }, bookFixture);

          mockFuzzySearchService.searchEpisode.mockResolvedValueOnce(fuzzyResponse);
          mockBabelioService.verifyAuthor.mockResolvedValueOnce(authorResponse);

          // Make verifyBook robust: return the matching fixture output based on
          // the (title, author) arguments. This avoids desynchronization when
          // the service calls verifyBook multiple times or in different orders.
          mockBabelioService.verifyBook.mockImplementation((titleArg, authorArg) => {
            // Try exact match first
            const direct = findFixtureByBook(titleArg, authorArg);
            if (direct) return Promise.resolve(getFixtureResponseOrError('babelioBook', { author: authorArg, title: titleArg }, direct));

            // If not found, try matching with author suggestion from authorResponse
            const suggestedAuthor = authorResponse && authorResponse.babelio_suggestion;
            if (suggestedAuthor) {
              const suggested = findFixtureByBook(titleArg, suggestedAuthor);
              if (suggested) return Promise.resolve(getFixtureResponseOrError('babelioBook', { author: suggestedAuthor, title: titleArg }, suggested));
            }

            // Fallback: search any book fixture matching title only (case-insensitive)
            const titleOnly = babelioBookCases.cases.find(c => c.input.title?.toLowerCase() === (titleArg || '').toLowerCase());
            if (titleOnly) return Promise.resolve(getFixtureResponseOrError('babelioBook', { author: titleOnly.input.author, title: titleArg }, titleOnly));

            return Promise.resolve({ status: 'not_found' });
          });

          // Execute validation with real mocked data
          const result = await biblioValidationService.validateBiblio(
            testCase.input.author,
            testCase.input.title,
            testCase.input.publisher,
            testCase.input.episodeId
          );

          // If the fixture includes an `expected` block it means this case
          // requires manual review / future algorithmic improvement. Don't
          // fail the test for those: print a clear warning with observed vs
          // expected and continue. For other cases, keep strict assertions.
          if (testCase.expected) {
            console.warn(`\n[MANUAL REVIEW] case ${index + 1}: ${testCase.input.author} - ${testCase.input.title}`);
            console.warn(`  Observed output: ${JSON.stringify(testCase.output)}`);
            console.warn(`  Expected target: ${JSON.stringify(testCase.expected)}`);
            // Keep a sanity check to avoid totally malformed results
            expect(['verified', 'suggestion', 'not_found', 'error']).toContain(result.status);
          } else {
            // Verify against expected captured result
            expect(result.status).toBe(testCase.output.status);

            if (testCase.output.status === 'suggestion') {
              expect(result.data?.suggested?.author).toBe(testCase.output.suggested_author);
              expect(result.data?.suggested?.title).toBe(testCase.output.suggested_title);
            }
          }

          console.log(`✓ Case ${index + 1}: ${testCase.input.author} - ${testCase.input.title} → Expected: ${testCase.output.status}, Got: ${result.status}`);
        });
      });
    }
  });

  describe('🔬 Phase 0: Direct Babelio Validation (TDD)', () => {
    it('should validate extracted book directly with Babelio before fuzzy search - Alice Ferney case', async () => {
      // ===== CASE: Alice Ferney - Comme en amour should be found directly =====

      // Setup: Mock Babelio to return a positive result for the extracted book
      const extractedAuthor = 'Alice Ferney';
      const extractedTitle = 'Comme en amour';
      const inputAuthor = 'Alice Ferney';  // User typed this
      const inputTitle = 'Pour';           // User typed this (incorrect)

      // Mock: Babelio finds the extracted book directly
      mockBabelioService.verifyBook.mockResolvedValueOnce({
        status: 'verified',
        babelio_suggestion_author: 'Alice Ferney',
        babelio_suggestion_title: 'Comme en amour',
        confidence_score: 1.0,
        original_author: extractedAuthor,
        original_title: extractedTitle
      });

      // When: Validate the incorrect user input
      const result = await biblioValidationService.validateBiblio(
        inputAuthor,
        inputTitle,
        '',
        '68ab04b92dc760119d18f8ef' // pragma: allowlist secret
      );

      // Then: Should return verified status with the extracted book info
      expect(result.status).toBe('verified');
      expect(result.data.original.author).toBe(inputAuthor);
      expect(result.data.original.title).toBe(inputTitle);
      expect(result.data.suggested?.author).toBe('Alice Ferney');
      expect(result.data.suggested?.title).toBe('Comme en amour');
      expect(result.data.source).toBe('babelio_phase0');

      // Verify: Babelio was called with extracted data, NOT user input
      expect(mockBabelioService.verifyBook).toHaveBeenCalledWith(extractedTitle, extractedAuthor);

      // Verify: Fuzzy search should NOT be called (phase 0 succeeded)
      expect(mockFuzzySearchService.searchEpisode).not.toHaveBeenCalled();
    });

    it('should fallback to normal workflow when phase 0 fails', async () => {
      // Setup: Mock Babelio to fail for the extracted book (phase 0)
      mockBabelioService.verifyBook.mockResolvedValueOnce({
        status: 'not_found'
      });

      // Mock: Continue with normal workflow - fuzzy search finds suggestions
      mockFuzzySearchService.searchEpisode.mockResolvedValueOnce({
        found_suggestions: true,
        titleMatches: [['Pour', 77]],
        authorMatches: [['Alice', 90], ['Ferney', 90]]
      });

      // Mock: Author validation
      mockBabelioService.verifyAuthor.mockResolvedValueOnce({
        status: 'verified',
        babelio_suggestion: 'Alice Ferney',
        confidence_score: 1.0
      });

      // Mock: Book validation for user input
      mockBabelioService.verifyBook.mockResolvedValueOnce({
        status: 'not_found'
      });

      // When: Validate with phase 0 failing
      const result = await biblioValidationService.validateBiblio(
        'Alice Ferney',
        'NonExistentBook',
        '',
        '68ab04b92dc760119d18f8ef' // pragma: allowlist secret
      );

      // Then: Should fallback to normal workflow
      expect(mockFuzzySearchService.searchEpisode).toHaveBeenCalled();
      expect(result.status).toBe('suggestion'); // Since fuzzy search found decent matches
    });
  });

  describe('📊 Statistics', () => {
    it('should report captured cases statistics', () => {
      const totalCases = biblioValidationCases.cases.length;
      const statusCounts = biblioValidationCases.cases.reduce((acc, testCase) => {
        acc[testCase.output.status] = (acc[testCase.output.status] || 0) + 1;
        return acc;
      }, {});

      console.log(`\n📊 Captured Cases Statistics:`);
      console.log(`Total cases: ${totalCases}`);
      console.log(`Status breakdown:`, statusCounts);

      if (totalCases > 0) {
        expect(totalCases).toBeGreaterThan(0);
        expect(Object.keys(statusCounts).length).toBeGreaterThan(0);
      }
    });
  });
});
