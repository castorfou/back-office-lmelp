/**
 * Tests unitaires pour la fonctionnalité de lien direct vers un épisode (Issue #96)
 * Vérifie que l'URL ?episode=<id> sélectionne automatiquement l'épisode au montage
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import LivresAuteurs from '@/views/LivresAuteurs.vue'

// Mock du service API
vi.mock('@/services/api.js', () => ({
  livresAuteursService: {
    getEpisodesWithReviews: vi.fn(),
    getLivresAuteurs: vi.fn(),
    autoProcessVerifiedBooks: vi.fn()
  },
  episodeService: {
    getEpisodeById: vi.fn()
  },
  babelioService: {},
  fuzzySearchService: {},
  searchService: {},
  statisticsService: {}
}))

describe('Episode direct link (Issue #96)', () => {
  let livresAuteursService

  beforeEach(async () => {
    vi.resetAllMocks()
    // Import le service mocké
    const api = await import('@/services/api.js')
    livresAuteursService = api.livresAuteursService
  })

  it('should auto-select episode when ?episode=<id> is in URL', async () => {
    // GIVEN: Episodes disponibles
    const mockEpisodes = [
      { id: 'ep1', date: '2025-01-01', titre: 'Episode 1' },
      { id: 'ep2', date: '2025-01-02', titre: 'Episode 2' },
      { id: 'ep3', date: '2025-01-03', titre: 'Episode 3' }
    ]

    livresAuteursService.getEpisodesWithReviews.mockResolvedValue(mockEpisodes)
    livresAuteursService.getLivresAuteurs.mockResolvedValue([])

    // GIVEN: URL avec ?episode=ep2
    const wrapper = mount(LivresAuteurs, {
      global: {
        mocks: {
          $route: {
            query: { episode: 'ep2' }
          }
        },
        stubs: {
          Navigation: true
        }
      }
    })

    // WHEN: Le composant est monté
    await flushPromises() // Attendre que toutes les promesses (y compris mounted()) se résolvent

    // THEN: L'épisode ep2 doit être auto-sélectionné
    expect(wrapper.vm.selectedEpisodeId).toBe('ep2')
  })

  it('should not select episode when episode ID does not exist', async () => {
    // GIVEN: Episodes disponibles
    const mockEpisodes = [
      { id: 'ep1', date: '2025-01-01', titre: 'Episode 1' },
      { id: 'ep2', date: '2025-01-02', titre: 'Episode 2' }
    ]

    livresAuteursService.getEpisodesWithReviews.mockResolvedValue(mockEpisodes)

    // GIVEN: URL avec un ID inexistant
    const wrapper = mount(LivresAuteurs, {
      global: {
        mocks: {
          $route: {
            query: { episode: 'ep999' }
          }
        },
        stubs: {
          Navigation: true
        }
      }
    })

    // WHEN: Le composant est monté
    await flushPromises()

    // THEN: Aucun épisode ne doit être sélectionné
    expect(wrapper.vm.selectedEpisodeId).toBe('')
  })

  it('should work normally when no episode parameter in URL', async () => {
    // GIVEN: Episodes disponibles
    const mockEpisodes = [
      { id: 'ep1', date: '2025-01-01', titre: 'Episode 1' }
    ]

    livresAuteursService.getEpisodesWithReviews.mockResolvedValue(mockEpisodes)

    // GIVEN: URL sans paramètre episode
    const wrapper = mount(LivresAuteurs, {
      global: {
        mocks: {
          $route: {
            query: {}
          }
        },
        stubs: {
          Navigation: true
        }
      }
    })

    // WHEN: Le composant est monté
    await flushPromises()

    // THEN: Aucun épisode ne doit être auto-sélectionné
    expect(wrapper.vm.selectedEpisodeId).toBe('')
  })
})
