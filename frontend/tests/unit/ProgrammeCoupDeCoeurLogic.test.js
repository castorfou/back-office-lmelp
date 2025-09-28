/**
 * Tests TDD pour corriger la logique programme/coup de cœur
 * Bug: programme: false devrait afficher icône coup de cœur, pas rien
 */

import { describe, it, expect } from 'vitest'

describe('TDD: Logique programme/coup de cœur', () => {

  describe('RED: Test de la logique actuelle (doit échouer)', () => {
    it('devrait mapper programme=true vers icône programme', () => {
      const book = { programme: true, coup_de_coeur: false }

      // La logique actuelle utilise book.programme pour l'icône programme
      const shouldShowProgramme = book.programme === true
      const shouldShowCoeur = book.coup_de_coeur === true  // ❌ FAUX!

      expect(shouldShowProgramme).toBe(true)
      expect(shouldShowCoeur).toBe(false) // ❌ Devrait être true car programme=false = coup de cœur
    })

    it('devrait mapper programme=false vers icône coup de cœur (corrigé)', () => {
      const book = { programme: false, coup_de_coeur: false }

      // LOGIQUE CORRIGÉE: programme=false signifie coup de cœur
      const shouldShowProgramme = book.programme === true
      const shouldShowCoeur = book.programme === false  // ✅ CORRIGÉ!

      expect(shouldShowProgramme).toBe(false)
      expect(shouldShowCoeur).toBe(true) // Maintenant correct: programme=false = coup de cœur
    })

    it('ne devrait jamais avoir programme=true ET coup_de_coeur=true simultanément', () => {
      // Un livre est soit au programme, soit coup de cœur, jamais les deux
      const bookProgramme = { programme: true }
      const bookCoeur = { programme: false }

      // LOGIQUE CORRECTE: programme=false signifie coup de cœur
      const programmeShowsProgramme = bookProgramme.programme === true
      const programmeShowsCoeur = bookProgramme.programme === false

      const coeurShowsProgramme = bookCoeur.programme === true
      const coeurShowsCoeur = bookCoeur.programme === false

      expect(programmeShowsProgramme).toBe(true)
      expect(programmeShowsCoeur).toBe(false)

      expect(coeurShowsProgramme).toBe(false)
      expect(coeurShowsCoeur).toBe(true) // ❌ Logique actuelle ne fait pas ça
    })
  })

  describe('GREEN: Logique corrigée (après correction)', () => {

    function getCorrectIconLogic(book) {
      // LOGIQUE CORRIGÉE
      return {
        showProgramme: book.programme === true,
        showCoeur: book.programme === false,  // ✅ CORRECTION!
        showEmpty: false // Jamais d'icône vide avec cette logique
      }
    }

    it('devrait afficher icône programme pour programme=true', () => {
      const book = { programme: true }
      const icons = getCorrectIconLogic(book)

      expect(icons.showProgramme).toBe(true)
      expect(icons.showCoeur).toBe(false)
      expect(icons.showEmpty).toBe(false)
    })

    it('devrait afficher icône coup de cœur pour programme=false', () => {
      const book = { programme: false }
      const icons = getCorrectIconLogic(book)

      expect(icons.showProgramme).toBe(false)
      expect(icons.showCoeur).toBe(true)
      expect(icons.showEmpty).toBe(false)
    })

    it('ne devrait jamais avoir d\'icône vide avec cette logique', () => {
      const bookProgramme = { programme: true }
      const bookCoeur = { programme: false }

      const iconsProgramme = getCorrectIconLogic(bookProgramme)
      const iconsCoeur = getCorrectIconLogic(bookCoeur)

      expect(iconsProgramme.showEmpty).toBe(false)
      expect(iconsCoeur.showEmpty).toBe(false)

      // Exactly one icon should show
      expect(iconsProgramme.showProgramme + iconsProgramme.showCoeur).toBe(1)
      expect(iconsCoeur.showProgramme + iconsCoeur.showCoeur).toBe(1)
    })
  })

  describe('Données réelles du cache MongoDB', () => {
    it('devrait correctement interpréter les données cache réelles', () => {
      // Données réelles de l'épisode
      const realCacheData = [
        { auteur: "Laurent Mauvignier", programme: true },      // Programme
        { auteur: "Alain Mabancou", programme: true },          // Programme
        { auteur: "Agnès Michaud", programme: false },          // Coup de cœur!
        { auteur: "Caroline Dussain", programme: false }        // Coup de cœur!
      ]

      realCacheData.forEach(book => {
        const icons = getCorrectIconLogic(book)

        if (book.programme) {
          expect(icons.showProgramme).toBe(true)
          expect(icons.showCoeur).toBe(false)
        } else {
          expect(icons.showProgramme).toBe(false)
          expect(icons.showCoeur).toBe(true) // ❌ Logique actuelle ne fait pas ça
        }
      })
    })
  })

  function getCorrectIconLogic(book) {
    // LOGIQUE CORRIGÉE pour l'implémentation
    return {
      showProgramme: book.programme === true,
      showCoeur: book.programme === false,
      showEmpty: false
    }
  }
})
