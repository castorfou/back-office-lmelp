/**
 * Tests TDD pour l'affichage différencié selon le statut des livres
 * Focus: livres avec statut "mongo" = affichage simplifié
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'
import LivresAuteurs from '@/views/LivresAuteurs.vue'

// Mock des services
vi.mock('../../src/services/api.js', () => ({
  livresAuteursService: {
    getEpisodesWithReviews: vi.fn(),
    getLivresAuteurs: vi.fn(),
    validateSuggestion: vi.fn(),
    addManualBook: vi.fn(),
    getAllAuthors: vi.fn(),
    getAllBooks: vi.fn(),
    getCollectionsStatistics: vi.fn(),
    autoProcessVerifiedBooks: vi.fn(),
    autoProcessVerified: vi.fn(),
    getBooksByValidationStatus: vi.fn(),
    setValidationResults: vi.fn(),
  },
  episodeService: {
    getAllEpisodes: vi.fn(),
    getEpisodeById: vi.fn(),
    updateEpisodeDescription: vi.fn(),
    updateEpisodeTitle: vi.fn(),
  },
  statisticsService: {
    getStatistics: vi.fn(),
  },
  babelioService: {
    verifyAuthor: vi.fn(),
    verifyBook: vi.fn(),
    verifyPublisher: vi.fn(),
  },
  fuzzySearchService: {
    searchEpisode: vi.fn(),
  }
}))

describe('LivresAuteurs - Affichage différencié par statut', () => {
  let wrapper

  // Données de test basées sur les vraies données MongoDB
  const mockEpisode = {
    id: '68c707ad6e51b9428ab87e9e', // pragma: allowlist secret
    titre: 'Test Episode',
    date: '2024-01-01',
    avis_critique_id: '68c718a16e51b9428ab88066' // pragma: allowlist secret
  }

  const mongoBook = {
    cache_id: '68d5babe9265d804e509dbd4', // pragma: allowlist secret
    episode_oid: '68c707ad6e51b9428ab87e9e', // pragma: allowlist secret
    auteur: 'Alain Mabancou',        // Données originales
    titre: 'Ramsès de Paris',
    editeur: 'Seuil',
    programme: true,
    coup_de_coeur: false,
    status: 'mongo',                  // STATUT MONGO = AFFICHAGE SIMPLIFIÉ
    suggested_author: 'Alain Mabanckou', // Données corrigées à afficher
    suggested_title: 'Ramsès de Paris'
  }

  const suggestedBook = {
    cache_id: '68d5babe9265d804e509dbd5',
    episode_oid: '68c707ad6e51b9428ab87e9e', // pragma: allowlist secret
    auteur: 'Laurent Mauvignier',
    titre: 'La Maison Vide',
    editeur: 'Éditions de Minuit',
    programme: false,
    coup_de_coeur: true,
    status: 'suggested',              // STATUT SUGGESTED = AFFICHAGE COMPLET
    suggested_author: 'Laurent Mauvignier',
    suggested_title: 'La Maison Vide'
  }

  // Configuration du routeur pour les tests
  const router = createRouter({
    history: createWebHistory(),
    routes: [
      { path: '/livres-auteurs', component: LivresAuteurs },
      { path: '/', component: { template: '<div>Home</div>' } }
    ]
  })

  beforeEach(async () => {
    const { livresAuteursService, episodeService, statisticsService } = vi.mocked(await import('../../src/services/api.js'))

    episodeService.getEpisodeById.mockResolvedValue(mockEpisode)
    livresAuteursService.getEpisodesWithReviews.mockResolvedValue([mockEpisode])
    livresAuteursService.getLivresAuteurs.mockResolvedValue([mongoBook, suggestedBook])
    livresAuteursService.setValidationResults.mockResolvedValue({ success: true })
    statisticsService.getStatistics.mockResolvedValue({})
  })

  describe('TDD RED: Affichage livre avec statut "mongo"', () => {
    it('devrait afficher les données suggested_author/suggested_title au lieu de auteur/titre', async () => {
      wrapper = mount(LivresAuteurs, {
        global: {
          plugins: [router]
        }
      })
      await wrapper.vm.$nextTick()

      wrapper.vm.selectedEpisodeId = mockEpisode.id
      await wrapper.vm.loadBooksForEpisode()
      await wrapper.vm.$nextTick()

      // CRITICAL: Pour statut "mongo", afficher suggested_author/suggested_title
      const mongoBookRow = wrapper.findAll('tr').find(row =>
        row.text().includes('mongo') || row.text().includes('Alain Mabanckou')
      )

      expect(mongoBookRow).toBeTruthy()

      // RED: Ce test doit ÉCHOUER initialement
      // L'auteur affiché doit être "Alain Mabanckou" (suggested_author) pas "Alain Mabancou" (auteur)
      expect(mongoBookRow.text()).toContain('Alain Mabanckou') // suggested_author
      expect(mongoBookRow.text()).not.toContain('Alain Mabancou') // pas l'auteur original
    })

    it('devrait afficher l\'icône programme pour livre mongo avec programme=true', async () => {
      wrapper = mount(LivresAuteurs, {
        global: {
          plugins: [router]
        }
      })
      await wrapper.vm.$nextTick()

      wrapper.vm.selectedEpisodeId = mockEpisode.id
      await wrapper.vm.loadBooksForEpisode()
      await wrapper.vm.$nextTick()

      // RED: Vérifier que l'icône programme s'affiche correctement
      const programmeIcon = wrapper.find('[title="Au programme"]')
      expect(programmeIcon.exists()).toBe(true)
    })

    it('devrait afficher l\'icône coup de coeur pour livre avec coup_de_coeur=true', async () => {
      // Modifier temporairement mongoBook pour tester coup de coeur
      const { livresAuteursService } = vi.mocked(await import('../../src/services/api.js'))
      const bookWithCoeur = { ...mongoBook, coup_de_coeur: true, programme: false }
      livresAuteursService.getLivresAuteurs.mockResolvedValue([bookWithCoeur, suggestedBook])

      wrapper = mount(LivresAuteurs, {
        global: {
          plugins: [router]
        }
      })
      await wrapper.vm.$nextTick()

      wrapper.vm.selectedEpisodeId = mockEpisode.id
      await wrapper.vm.loadBooksForEpisode()
      await wrapper.vm.$nextTick()

      // RED: Ce test doit ÉCHOUER si l'icône coup de coeur a disparu
      const coeurIcon = wrapper.find('[title="Coup de coeur"]')
      expect(coeurIcon.exists()).toBe(true)
    })

    it('NE devrait PAS afficher les boutons Validation Babelio, YAML, Actions pour statut mongo', async () => {
      wrapper = mount(LivresAuteurs, {
        global: {
          plugins: [router]
        }
      })
      await wrapper.vm.$nextTick()

      wrapper.vm.selectedEpisodeId = mockEpisode.id
      await wrapper.vm.loadBooksForEpisode()
      await wrapper.vm.$nextTick()

      // RED: Ces éléments ne doivent PAS être présents pour statut mongo
      const biblioValidation = wrapper.find('[data-testid*="validation-babelio"]')
      const yamlButton = wrapper.find('[data-testid*="capture-button"]')
      const actionButtons = wrapper.find('[data-testid*="auto-process"]')

      // Pour livre mongo, ces éléments doivent être absents ou cachés
      // Le test échoue si ils sont visibles
      expect(biblioValidation.exists() && biblioValidation.isVisible()).toBe(false)
      expect(yamlButton.exists() && yamlButton.isVisible()).toBe(false)
      expect(actionButtons.exists() && actionButtons.isVisible()).toBe(false)
    })

    it('devrait avoir un style visuel différent (gris foncé) pour les livres mongo', async () => {
      wrapper = mount(LivresAuteurs, {
        global: {
          plugins: [router]
        }
      })
      await wrapper.vm.$nextTick()

      wrapper.vm.selectedEpisodeId = mockEpisode.id
      await wrapper.vm.loadBooksForEpisode()
      await wrapper.vm.$nextTick()

      // RED: Vérifier qu'il y a une classe CSS ou un style pour différencier les livres mongo
      const mongoBookRow = wrapper.findAll('tr').find(row =>
        row.text().includes('Alain Mabanckou')
      )

      expect(mongoBookRow).toBeTruthy()

      // Le livre mongo devrait avoir une classe spéciale ou un style gris foncé
      expect(
        mongoBookRow.classes().includes('mongo-book') ||
        mongoBookRow.classes().includes('processed-book') ||
        mongoBookRow.element.style.opacity !== ''
      ).toBe(true)
    })
  })

  describe('TDD: Affichage normal pour autres statuts', () => {
    it('devrait conserver l\'affichage complet pour statut "suggested"', async () => {
      wrapper = mount(LivresAuteurs, {
        global: {
          plugins: [router]
        }
      })
      await wrapper.vm.$nextTick()

      wrapper.vm.selectedEpisodeId = mockEpisode.id
      await wrapper.vm.loadBooksForEpisode()
      await wrapper.vm.$nextTick()

      // Définir le statut de validation pour que le bouton soit visible
      const bookKey = wrapper.vm.getBookKey(suggestedBook)
      wrapper.vm.validationStatuses.set(bookKey, 'corrected')
      await wrapper.vm.$nextTick()

      // Pour statut suggested, garder l'affichage actuel avec tous les boutons
      const suggestedBookRow = wrapper.findAll('tr').find(row =>
        row.text().includes('Laurent Mauvignier')
      )

      expect(suggestedBookRow).toBeTruthy()

      // Vérifier que les boutons d'action sont présents pour statut suggested
      const actionButton = wrapper.find('[data-testid="validate-suggestion-btn"]')
      expect(actionButton.exists()).toBe(true)
    })
  })
})
