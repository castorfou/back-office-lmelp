/**
 * Tests unitaires pour les liens cliquables vers pages détail (Issue #96)
 * Vérifie que les auteurs et titres sont cliquables et pointent vers les pages de détail
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import LivresAuteurs from '@/views/LivresAuteurs.vue'

// Mock du service API
vi.mock('@/services/api.js', () => ({
  livresAuteursService: {
    getEpisodesWithReviews: vi.fn(),
    getLivresAuteurs: vi.fn(),
    autoProcessVerifiedBooks: vi.fn(),
    setValidationResults: vi.fn()
  },
  episodeService: {
    getEpisodeById: vi.fn()
  },
  babelioService: {},
  fuzzySearchService: {},
  searchService: {},
  statisticsService: {}
}))

describe('LivresAuteurs - Liens vers pages détail (Issue #96)', () => {
  let router
  let livresAuteursService

  beforeEach(async () => {
    vi.resetAllMocks()

    // Import le service mocké
    const api = await import('@/services/api.js')
    livresAuteursService = api.livresAuteursService

    // Create a real router for testing
    router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/livres-auteurs', component: LivresAuteurs },
        { path: '/livre/:id', component: { template: '<div>Livre Detail</div>' } },
        { path: '/auteur/:id', component: { template: '<div>Auteur Detail</div>' } }
      ]
    })
  })

  it('should have clickable author and title links for mongo books', async () => {
    // GIVEN: Des épisodes et livres mongo avec IDs
    const mockEpisodes = [
      { id: 'ep1', date: '2025-01-01', titre: 'Episode 1' }
    ]

    const mockBooks = [
      {
        book_id: 'livre1',
        author_id: 'auteur1',
        auteur: 'Auteur Test',
        titre: 'Livre Test',
        editeur: 'Editeur Test',
        status: 'mongo',
        episode_oid: 'ep1'
      }
    ]

    livresAuteursService.getEpisodesWithReviews.mockResolvedValue(mockEpisodes)
    livresAuteursService.getLivresAuteurs.mockResolvedValue(mockBooks)

    await router.push('/livres-auteurs?episode=ep1')
    const wrapper = mount(LivresAuteurs, {
      global: {
        plugins: [router]
      }
    })

    await flushPromises()

    // THEN: Les liens auteur et titre doivent exister
    const authorLinks = wrapper.findAll('[data-test="author-link"]')
    const titleLinks = wrapper.findAll('[data-test="title-link"]')

    expect(authorLinks).toHaveLength(1)
    expect(titleLinks).toHaveLength(1)

    // Vérifier que les liens pointent vers les bonnes routes
    expect(authorLinks[0].attributes('href')).toBe('/auteur/auteur1')
    expect(authorLinks[0].text()).toBe('Auteur Test')

    expect(titleLinks[0].attributes('href')).toBe('/livre/livre1')
    expect(titleLinks[0].text()).toBe('Livre Test')
  })

  it('should display plain text for books without IDs', async () => {
    // GIVEN: Des livres cache sans IDs (pas encore validés)
    const mockEpisodes = [
      { id: 'ep1', date: '2025-01-01', titre: 'Episode 1' }
    ]

    const mockBooks = [
      {
        auteur: 'Auteur Cache',
        titre: 'Livre Cache',
        editeur: 'Editeur',
        status: 'cache',
        episode_oid: 'ep1'
      }
    ]

    livresAuteursService.getEpisodesWithReviews.mockResolvedValue(mockEpisodes)
    livresAuteursService.getLivresAuteurs.mockResolvedValue(mockBooks)

    await router.push('/livres-auteurs?episode=ep1')
    const wrapper = mount(LivresAuteurs, {
      global: {
        plugins: [router]
      }
    })

    await flushPromises()

    // THEN: Pas de liens pour les livres cache sans IDs
    const authorLinks = wrapper.findAll('[data-test="author-link"]')
    const titleLinks = wrapper.findAll('[data-test="title-link"]')

    expect(authorLinks).toHaveLength(0)
    expect(titleLinks).toHaveLength(0)

    // Mais le texte doit être affiché
    expect(wrapper.text()).toContain('Auteur Cache')
    expect(wrapper.text()).toContain('Livre Cache')
  })
})
