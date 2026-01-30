/**
 * Tests TDD pour la sélection automatique d'épisode par priorité de pastille
 * Issue #185: Sélection auto basée sur rouge > gris > vert
 *
 * Priorité pour /livres-auteurs:
 * - 🔴 has_incomplete_books === true (analyse incomplète)
 * - ⚪ has_cached_books === false (non traité)
 * - 🟢 has_cached_books === true (traité)
 *
 * Priorité pour /generation-avis-critiques:
 * - ⚪ has_summary === false (sans summary)
 * - 🟢 has_summary === true (avec summary)
 */

import { describe, it, expect } from 'vitest';
import { selectEpisodeByBadgePriority, selectEpisodeBySummaryPriority } from '../../src/utils/episodeSelection.js';

describe('Auto-sélection par priorité de pastille', () => {

  describe('selectEpisodeByBadgePriority (page /livres-auteurs)', () => {

    it('should return null for empty array', () => {
      expect(selectEpisodeByBadgePriority([])).toBeNull();
    });

    it('should return null for null/undefined', () => {
      expect(selectEpisodeByBadgePriority(null)).toBeNull();
      expect(selectEpisodeByBadgePriority(undefined)).toBeNull();
    });

    it('should select episode with incomplete books (🔴) first', () => {
      const episodes = [
        { id: '1', date: '2025-01-01', has_cached_books: true, has_incomplete_books: false },
        { id: '2', date: '2025-01-08', has_cached_books: true, has_incomplete_books: true }, // 🔴
        { id: '3', date: '2025-01-15', has_cached_books: false, has_incomplete_books: false },
      ];

      const selected = selectEpisodeByBadgePriority(episodes);
      expect(selected.id).toBe('2');
    });

    it('should select untreated episode (⚪) if no incomplete', () => {
      const episodes = [
        { id: '1', date: '2025-01-01', has_cached_books: true, has_incomplete_books: false }, // 🟢
        { id: '2', date: '2025-01-08', has_cached_books: true, has_incomplete_books: false }, // 🟢
        { id: '3', date: '2025-01-15', has_cached_books: false, has_incomplete_books: false }, // ⚪
      ];

      const selected = selectEpisodeByBadgePriority(episodes);
      expect(selected.id).toBe('3');
    });

    it('should select first episode if all are treated (🟢)', () => {
      const episodes = [
        { id: '1', date: '2025-01-01', has_cached_books: true, has_incomplete_books: false },
        { id: '2', date: '2025-01-08', has_cached_books: true, has_incomplete_books: false },
        { id: '3', date: '2025-01-15', has_cached_books: true, has_incomplete_books: false },
      ];

      const selected = selectEpisodeByBadgePriority(episodes);
      expect(selected.id).toBe('1'); // Premier de la liste (plus récent)
    });

    it('should prioritize 🔴 over ⚪', () => {
      const episodes = [
        { id: '1', date: '2025-01-01', has_cached_books: false, has_incomplete_books: false }, // ⚪
        { id: '2', date: '2025-01-08', has_cached_books: true, has_incomplete_books: true }, // 🔴
      ];

      const selected = selectEpisodeByBadgePriority(episodes);
      expect(selected.id).toBe('2'); // 🔴 a priorité sur ⚪
    });

    it('should handle episodes with null/undefined badge fields', () => {
      const episodes = [
        { id: '1', date: '2025-01-01' }, // Pas de champs badge
        { id: '2', date: '2025-01-08', has_cached_books: null, has_incomplete_books: null },
        { id: '3', date: '2025-01-15', has_cached_books: true, has_incomplete_books: true }, // 🔴
      ];

      const selected = selectEpisodeByBadgePriority(episodes);
      expect(selected.id).toBe('3'); // 🔴 trouvé
    });

  });

  describe('selectEpisodeBySummaryPriority (page /generation-avis-critiques)', () => {

    it('should return null for empty array', () => {
      expect(selectEpisodeBySummaryPriority([])).toBeNull();
    });

    it('should return null for null/undefined', () => {
      expect(selectEpisodeBySummaryPriority(null)).toBeNull();
      expect(selectEpisodeBySummaryPriority(undefined)).toBeNull();
    });

    it('should select episode without summary (⚪) first', () => {
      const episodes = [
        { id: '1', date: '2025-01-01', has_summary: true },  // 🟢
        { id: '2', date: '2025-01-08', has_summary: false }, // ⚪
        { id: '3', date: '2025-01-15', has_summary: true },  // 🟢
      ];

      const selected = selectEpisodeBySummaryPriority(episodes);
      expect(selected.id).toBe('2');
    });

    it('should select first episode if all have summary (🟢)', () => {
      const episodes = [
        { id: '1', date: '2025-01-01', has_summary: true },
        { id: '2', date: '2025-01-08', has_summary: true },
      ];

      const selected = selectEpisodeBySummaryPriority(episodes);
      expect(selected.id).toBe('1'); // Premier (plus récent)
    });

    it('should select first without summary among multiple', () => {
      const episodes = [
        { id: '1', date: '2025-01-01', has_summary: true },  // 🟢
        { id: '2', date: '2025-01-08', has_summary: false }, // ⚪ ← celui-ci
        { id: '3', date: '2025-01-15', has_summary: false }, // ⚪
      ];

      const selected = selectEpisodeBySummaryPriority(episodes);
      expect(selected.id).toBe('2'); // Premier ⚪ trouvé
    });

  });

});
