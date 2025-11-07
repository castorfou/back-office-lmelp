/**
 * Test unitaire pour buildBookDataForBackend() - Issue #85
 *
 * Ce test capture le bug identifié : la fonction autoValidateAndSendResults()
 * ne transmet PAS les champs babelio_url et babelio_publisher au backend.
 *
 * PROBLÈME ACTUEL (lignes 1192-1208 de LivresAuteurs.vue):
 * - Le code construit un objet bookForBackend mais oublie d'inclure:
 *   - babelio_url
 *   - babelio_publisher
 * - Ces champs existent dans l'objet `book` original mais sont perdus lors de la transmission
 *
 * POURQUOI CE TEST :
 * - Les tests backend passaient mais le bug persistait en production
 * - Le backend fonctionne correctement (enrichissement, formatage, API)
 * - Le problème est dans le FRONTEND : transmission incomplète des données
 * - Ce test aurait détecté le bug immédiatement avec TDD
 */

import { describe, it, expect } from 'vitest';
import { buildBookDataForBackend } from '../../src/utils/buildBookDataForBackend.js';

describe('buildBookDataForBackend() - Issue #85', () => {
  describe('Transmission des champs Babelio enrichis', () => {
    it('devrait transmettre babelio_url quand présent dans book original', () => {
      // Arrange - Simuler un livre enrichi automatiquement par le backend
      const book = {
        auteur: 'Carlos Gimenez',
        titre: 'Paracuellos, Intégrale',
        editeur: 'Audie-Fluide glacial',
        programme: true,
        coup_de_coeur: false,
        // Issue #85: Champs enrichis automatiquement (confidence >= 0.90)
        babelio_url: 'https://www.babelio.com/livres/Gimenez-Paracuellos-Integrale/112880',
        babelio_publisher: 'Audie-Fluide glacial'
      };

      const validationResult = {
        status: 'verified'
      };

      // Act - Construire l'objet pour le backend
      const bookForBackend = buildBookDataForBackend(book, validationResult, 'verified');

      // Assert - CRITIQUE Issue #85
      // Ces assertions DOIVENT ÉCHOUER actuellement car le bug n'est pas encore corrigé
      expect(bookForBackend).toHaveProperty('babelio_url');
      expect(bookForBackend.babelio_url).toBe('https://www.babelio.com/livres/Gimenez-Paracuellos-Integrale/112880');
    });

    it('devrait transmettre babelio_publisher quand présent dans book original', () => {
      // Arrange
      const book = {
        auteur: 'Carlos Gimenez',
        titre: 'Paracuellos, Intégrale',
        editeur: 'Audie-Fluide glacial',
        programme: false,
        babelio_url: 'https://www.babelio.com/livres/Gimenez-Paracuellos-Integrale/112880',
        babelio_publisher: 'Audie-Fluide glacial'
      };

      const validationResult = {
        status: 'verified'
      };

      // Act
      const bookForBackend = buildBookDataForBackend(book, validationResult, 'verified');

      // Assert - CRITIQUE Issue #85
      expect(bookForBackend).toHaveProperty('babelio_publisher');
      expect(bookForBackend.babelio_publisher).toBe('Audie-Fluide glacial');
    });

    it('NE devrait PAS transmettre babelio_url si absent du book original', () => {
      // Arrange - Livre sans enrichissement Babelio
      const book = {
        auteur: 'Auteur Test',
        titre: 'Livre Test',
        editeur: 'Éditeur Test',
        programme: false
        // Pas de babelio_url ni babelio_publisher
      };

      const validationResult = {
        status: 'verified'
      };

      // Act
      const bookForBackend = buildBookDataForBackend(book, validationResult, 'verified');

      // Assert - Ne doit pas inventer de champs
      expect(bookForBackend).not.toHaveProperty('babelio_url');
      expect(bookForBackend).not.toHaveProperty('babelio_publisher');
    });

    it('devrait préserver tous les champs existants en plus de babelio_*', () => {
      // Arrange - Livre avec suggestions ET enrichissement Babelio
      const book = {
        auteur: 'Alain Mabancou',
        titre: 'Ramsès de Paris',
        editeur: 'Seuil',
        programme: true,
        coup_de_coeur: false,
        babelio_url: 'https://www.babelio.com/livres/Mabanckou-Ramses-de-Paris/123456',
        babelio_publisher: 'Seuil'
      };

      const validationResult = {
        status: 'suggestion',
        data: {
          suggested: {
            author: 'Alain Mabanckou',
            title: 'Ramsès de Paris',
            publisher: 'Seuil'
          }
        }
      };

      // Act
      const bookForBackend = buildBookDataForBackend(book, validationResult, 'corrected');

      // Assert - Vérifier TOUS les champs
      expect(bookForBackend.auteur).toBe('Alain Mabancou');
      expect(bookForBackend.titre).toBe('Ramsès de Paris');
      expect(bookForBackend.editeur).toBe('Seuil');
      expect(bookForBackend.programme).toBe(true);
      expect(bookForBackend.validation_status).toBe('corrected');

      // Suggestions doivent être présentes
      expect(bookForBackend.suggested_author).toBe('Alain Mabanckou');
      expect(bookForBackend.suggested_title).toBe('Ramsès de Paris');

      // CRITIQUE Issue #85 : Enrichissements Babelio AUSSI présents
      expect(bookForBackend.babelio_url).toBe('https://www.babelio.com/livres/Mabanckou-Ramses-de-Paris/123456');
      expect(bookForBackend.babelio_publisher).toBe('Seuil');
    });
  });

  describe('Champs standards (regression tests)', () => {
    it('devrait toujours inclure auteur, titre, editeur, programme, validation_status', () => {
      // Arrange
      const book = {
        auteur: 'Test Author',
        titre: 'Test Title',
        editeur: 'Test Publisher',
        programme: true,
        coup_de_coeur: false
      };

      const validationResult = {
        status: 'verified'
      };

      // Act
      const bookForBackend = buildBookDataForBackend(book, validationResult, 'verified');

      // Assert - Champs obligatoires
      expect(bookForBackend).toHaveProperty('auteur');
      expect(bookForBackend).toHaveProperty('titre');
      expect(bookForBackend).toHaveProperty('editeur');
      expect(bookForBackend).toHaveProperty('programme');
      expect(bookForBackend).toHaveProperty('validation_status');

      expect(bookForBackend.auteur).toBe('Test Author');
      expect(bookForBackend.titre).toBe('Test Title');
      expect(bookForBackend.editeur).toBe('Test Publisher');
      expect(bookForBackend.programme).toBe(true);
      expect(bookForBackend.validation_status).toBe('verified');
    });

    it('devrait inclure suggestions si présentes dans validationResult', () => {
      // Arrange
      const book = {
        auteur: 'Original Author',
        titre: 'Original Title',
        editeur: 'Original Publisher',
        programme: false
      };

      const validationResult = {
        status: 'suggestion',
        data: {
          suggested: {
            author: 'Corrected Author',
            title: 'Corrected Title',
            publisher: 'Corrected Publisher'
          }
        }
      };

      // Act
      const bookForBackend = buildBookDataForBackend(book, validationResult, 'corrected');

      // Assert - Suggestions ajoutées
      expect(bookForBackend.suggested_author).toBe('Corrected Author');
      expect(bookForBackend.suggested_title).toBe('Corrected Title');
    });

    it('NE devrait PAS inclure suggestions si validationResult sans data.suggested', () => {
      // Arrange
      const book = {
        auteur: 'Test Author',
        titre: 'Test Title',
        editeur: 'Test Publisher',
        programme: false
      };

      const validationResult = {
        status: 'not_found'
      };

      // Act
      const bookForBackend = buildBookDataForBackend(book, validationResult, 'not_found');

      // Assert - Pas de suggestions
      expect(bookForBackend).not.toHaveProperty('suggested_author');
      expect(bookForBackend).not.toHaveProperty('suggested_title');
    });
  });
});
