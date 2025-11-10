/**
 * Tests for accent-insensitive search highlighting functionality
 * Issue #92: Implement accent-insensitive search
 */

import { describe, it, expect } from 'vitest';
import {
  removeAccents,
  createAccentInsensitiveRegex,
  highlightSearchTermAccentInsensitive
} from '../../src/utils/textUtils.js';

describe('Accent Insensitive Highlighting', () => {
  describe('removeAccents', () => {
    it('should remove accents from French characters', () => {
      expect(removeAccents('Carrère')).toBe('Carrere');
      expect(removeAccents('Émonet')).toBe('Emonet');
      expect(removeAccents('François')).toBe('Francois');
    });

    it('should preserve non-accented characters', () => {
      expect(removeAccents('hello')).toBe('hello');
      expect(removeAccents('123')).toBe('123');
    });

    it('should handle mixed case', () => {
      expect(removeAccents('CARRÈRE')).toBe('CARRERE');
      expect(removeAccents('Étranger')).toBe('Etranger');
    });
  });

  describe('createAccentInsensitiveRegex', () => {
    it('should create regex pattern that matches accent variants', () => {
      const pattern = createAccentInsensitiveRegex('carre');
      expect(pattern).toContain('[cç]');
      expect(pattern).toContain('[aàâäáãåāăą]');
      expect(pattern).toContain('[eèéêëēĕėęě]');
    });

    it('should normalize accented search terms', () => {
      const pattern1 = createAccentInsensitiveRegex('café');
      const pattern2 = createAccentInsensitiveRegex('cafe');
      expect(pattern1).toBe(pattern2);
    });

    it('should handle special characters like apostrophes', () => {
      const pattern = createAccentInsensitiveRegex("l'ami");
      expect(pattern).toContain("'"); // Apostrophe should be preserved
      expect(pattern).toContain('[aàâäáãåāăą]'); // 'a' should have variants
    });
  });

  describe('highlightSearchTermAccentInsensitive', () => {
    it('should highlight "carre" in "Emmanuel Carrère"', () => {
      const result = highlightSearchTermAccentInsensitive('Emmanuel Carrère', 'carre');
      expect(result).toContain('<strong');
      expect(result).toContain('Carr');
      expect(result).toContain('</strong>');
    });

    it('should highlight "carrere" in "Emmanuel Carrère"', () => {
      const result = highlightSearchTermAccentInsensitive('Emmanuel Carrère', 'carrere');
      expect(result).toContain('<strong');
      expect(result).toContain('Carrère');
      expect(result).toContain('</strong>');
    });

    it('should highlight "emonet" in "Simone Émonet"', () => {
      const result = highlightSearchTermAccentInsensitive('Simone Émonet', 'emonet');
      expect(result).toContain('<strong');
      expect(result).toContain('Émonet');
      expect(result).toContain('</strong>');
    });

    it('should highlight "etranger" in "L\'Étranger"', () => {
      const result = highlightSearchTermAccentInsensitive("L'Étranger", 'etranger');
      expect(result).toContain('<strong');
      expect(result).toContain('Étranger');
      expect(result).toContain('</strong>');
    });

    it('should be case-insensitive', () => {
      const result = highlightSearchTermAccentInsensitive('Emmanuel CARRÈRE', 'carrere');
      expect(result).toContain('<strong');
      expect(result).toContain('CARRÈRE');
      expect(result).toContain('</strong>');
    });

    it('should not highlight if search term is less than 3 characters', () => {
      const result = highlightSearchTermAccentInsensitive('Emmanuel Carrère', 'ca');
      expect(result).toBe('Emmanuel Carrère');
      expect(result).not.toContain('<strong');
    });

    it('should return original text if no match', () => {
      const result = highlightSearchTermAccentInsensitive('Emmanuel Carrère', 'xyz');
      expect(result).toBe('Emmanuel Carrère');
      expect(result).not.toContain('<strong');
    });

    it('should handle empty inputs gracefully', () => {
      expect(highlightSearchTermAccentInsensitive('', 'test')).toBe('');
      expect(highlightSearchTermAccentInsensitive('text', '')).toBe('text');
      expect(highlightSearchTermAccentInsensitive(null, 'test')).toBe('');
    });

    it('should highlight multiple occurrences', () => {
      const result = highlightSearchTermAccentInsensitive('Carrère et Carrère', 'carrere');
      const matches = (result.match(/<strong/g) || []).length;
      expect(matches).toBe(2);
    });
  });
});
