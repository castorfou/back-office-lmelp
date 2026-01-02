import { describe, it, expect } from 'vitest';
import { removeAccents, createAccentInsensitiveRegex, highlightSearchTermAccentInsensitive } from '../textUtils.js';

describe('textUtils.js - Typographic Characters Support (Issue #173)', () => {
  describe('removeAccents', () => {
    it('should normalize ligature oe to oe', () => {
      // U+0153 = œ (ligature oe)
      expect(removeAccents('\u0153uvre')).toBe('oeuvre');
      expect(removeAccents('\u0152uvre')).toBe('Oeuvre');
    });

    it('should normalize ligature ae to ae', () => {
      // U+00E6 = æ (ligature ae)
      expect(removeAccents('\u00E6quo')).toBe('aequo');
      expect(removeAccents('\u00C6gis')).toBe('Aegis');
    });

    it('should normalize em dash to hyphen', () => {
      // U+2013 = – (en dash / em dash)
      expect(removeAccents('Marie\u2013Claire')).toBe('Marie-Claire');
    });

    it('should normalize typographic apostrophe to simple apostrophe', () => {
      // U+2019 = ' (right single quotation mark)
      expect(removeAccents('l\u2019ami')).toBe("l'ami");
    });

    it('should handle multiple typographic characters', () => {
      expect(removeAccents('L\u2019\u0153uvre\u2013test')).toBe("L'oeuvre-test");
    });

    it('should still remove accents as before (Issue #92)', () => {
      expect(removeAccents('café')).toBe('cafe');
      expect(removeAccents('château')).toBe('chateau');
    });
  });

  describe('createAccentInsensitiveRegex', () => {
    it('should create pattern that matches both oe and ligature oe', () => {
      const pattern = createAccentInsensitiveRegex('oeuvre');
      const regex = new RegExp(pattern, 'i');

      expect(regex.test('oeuvre')).toBe(true);
      expect(regex.test('\u0153uvre')).toBe(true);
      expect(regex.test('\u0152UVRE')).toBe(true);
    });

    it('should create pattern that matches both ae and ligature ae', () => {
      const pattern = createAccentInsensitiveRegex('aegis');
      const regex = new RegExp(pattern, 'i');

      expect(regex.test('aegis')).toBe(true);
      expect(regex.test('\u00E6gis')).toBe(true);
    });

    it('should create pattern that matches both hyphen and em dash', () => {
      const pattern = createAccentInsensitiveRegex('Marie-Claire');
      const regex = new RegExp(pattern, 'i');

      expect(regex.test('Marie-Claire')).toBe(true);
      expect(regex.test('Marie\u2013Claire')).toBe(true);
    });

    it('should create pattern that matches both apostrophes', () => {
      const pattern = createAccentInsensitiveRegex("l'ami");
      const regex = new RegExp(pattern, 'i');

      expect(regex.test("l'ami")).toBe(true);
      expect(regex.test('l\u2019ami')).toBe(true);
    });

    it('should handle term with ligature input (ligature oe matches both)', () => {
      const pattern = createAccentInsensitiveRegex('\u0153uvre');
      const regex = new RegExp(pattern, 'i');

      expect(regex.test('oeuvre')).toBe(true);
      expect(regex.test('\u0153uvre')).toBe(true);
    });
  });

  describe('highlightSearchTermAccentInsensitive', () => {
    it('should highlight matches with ligature normalization', () => {
      const result = highlightSearchTermAccentInsensitive('L\u2019\u0153uvre au noir', 'oeuvre');
      expect(result).toContain('<strong');
      expect(result).toContain('\u0153uvre');
    });

    it('should highlight matches with em dash normalization', () => {
      const result = highlightSearchTermAccentInsensitive('Marie\u2013Claire Blais', 'Marie-Claire');
      expect(result).toContain('<strong');
      expect(result).toContain('Marie\u2013Claire');
    });
  });
});
