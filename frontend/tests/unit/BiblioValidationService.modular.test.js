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
          mockBabelioService.verifyBook.mockResolvedValueOnce(bookResponse);

          // Execute validation with real mocked data
          const result = await biblioValidationService.validateBiblio(
            testCase.input.author,
            testCase.input.title,
            testCase.input.publisher,
            testCase.input.episodeId
          );

          // Verify against expected captured result
          expect(result.status).toBe(testCase.output.status);

          if (testCase.output.status === 'suggestion') {
            expect(result.data?.suggested?.author).toBe(testCase.output.suggested_author);
            expect(result.data?.suggested?.title).toBe(testCase.output.suggested_title);
          }

          console.log(`✓ Case ${index + 1}: ${testCase.input.author} - ${testCase.input.title} → Expected: ${testCase.output.status}, Got: ${result.status}`);
        });
      });
    }
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
