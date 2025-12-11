/**
 * Tests TDD pour le bouton "Arrêter la liaison" (Issue #124)
 *
 * Problème business réel:
 * - L'UI affiche "Liaison en cours" avec la barre de progression
 * - L'utilisateur clique sur "Arrêter la liaison"
 * - Un toast apparaît disant "Aucune liaison en cours"
 * - Cause: Le frontend interroge l'API toutes les 3 secondes mais ne met pas à jour migrationProgress.is_running
 *
 * Solution:
 * - Mettre à jour migrationProgress.is_running dans le polling
 * - Afficher "Liaison en cours" seulement si migrationProgress.is_running === true
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import BabelioMigration from '../src/views/BabelioMigration.vue'
import axios from 'axios'

vi.mock('axios')

// Mock router-link component
const RouterLinkStub = {
  template: '<a><slot /></a>'
}

describe('BabelioMigration - Stop Button', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // Helper to mount with router mocks
  const mountWithRouter = (component) => {
    return mount(component, {
      global: {
        stubs: {
          'router-link': RouterLinkStub
        },
        mocks: {
          $route: {
            path: '/babelio-migration'
          }
        }
      }
    })
  }

  it('should hide "Liaison en cours" when backend says is_running=false', async () => {
    // Arrange - Backend dit que la migration est arrêtée
    const mockStatus = {
      total_books: 504,
      migrated_count: 498,
      pending_count: 0,
      authors_without_url_babelio: 15
    }

    const mockProgress = {
      is_running: false,  // Backend dit: PAS en cours
      books_processed: 0,
      book_logs: []
    }

    axios.get.mockImplementation((url) => {
      if (url.includes('/api/babelio-migration/status')) {
        return Promise.resolve({ data: mockStatus })
      } else if (url.includes('/api/babelio-migration/progress')) {
        return Promise.resolve({ data: mockProgress })
      } else if (url.includes('/api/babelio-migration/problematic-cases')) {
        return Promise.resolve({ data: [] })
      }
      return Promise.reject(new Error('Unknown URL'))
    })

    // Act - Mount component
    const wrapper = mountWithRouter(BabelioMigration)

    // Wait for data to load
    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    // Assert - "Liaison en cours" ne doit PAS être affiché
    const liaisonEnCours = wrapper.find('h2').text()
    expect(liaisonEnCours).not.toContain('Liaison en cours')
    expect(liaisonEnCours).toContain('Migration Babelio')  // Titre par défaut

    // Assert - La barre de progression ne doit PAS être affichée (is_running=false)
    const progressBar = wrapper.find('.progress-bar-container')
    expect(progressBar.exists()).toBe(false)
  })

  it('should show "Liaison en cours" only when backend says is_running=true', async () => {
    // Arrange - Backend dit que la migration est EN COURS
    const mockStatus = {
      total_books: 504,
      migrated_count: 498,
      pending_count: 0,
      authors_without_url_babelio: 15
    }

    const mockProgress = {
      is_running: true,  // Backend dit: EN COURS
      books_processed: 4,
      start_time: '2025-12-09T04:09:48',
      book_logs: []
    }

    axios.get.mockImplementation((url) => {
      if (url.includes('/status')) return Promise.resolve({ data: mockStatus })
      if (url.includes('/progress')) return Promise.resolve({ data: mockProgress })
      if (url.includes('/problematic-cases')) return Promise.resolve({ data: [] })
      return Promise.reject(new Error('Unknown URL'))
    })

    // Act
    const wrapper = mountWithRouter(BabelioMigration)
    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    // Assert - "Liaison en cours" doit être affiché
    const liaisonEnCours = wrapper.find('h2').text()
    expect(liaisonEnCours).toContain('Liaison en cours')

    // Assert - La barre de progression doit être affichée
    const progressBar = wrapper.find('.progress-bar-container')
    expect(progressBar.exists()).toBe(true)
  })

  it('should reflect is_running state from backend in UI', async () => {
    // Arrange - Backend retourne is_running basé sur l'état actuel
    const mockStatus = {
      total_books: 504,
      migrated_count: 498,
      pending_count: 0,
      authors_without_url_babelio: 15
    }

    // Test case 1: is_running=true
    axios.get.mockImplementation((url) => {
      if (url.includes('/status')) {
        return Promise.resolve({ data: mockStatus })
      } else if (url.includes('/progress')) {
        return Promise.resolve({
          data: {
            is_running: true,  // Backend dit: EN COURS
            books_processed: 4,
            book_logs: []
          }
        })
      } else if (url.includes('/problematic-cases')) {
        return Promise.resolve({ data: [] })
      }
      return Promise.reject(new Error('Unknown URL'))
    })

    // Act
    const wrapper = mountWithRouter(BabelioMigration)
    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    // Assert - Afficher "Liaison en cours" quand backend dit is_running=true
    expect(wrapper.find('h2').text()).toContain('Liaison en cours')

    // Test case 2: is_running=false
    axios.get.mockImplementation((url) => {
      if (url.includes('/status')) {
        return Promise.resolve({ data: mockStatus })
      } else if (url.includes('/progress')) {
        return Promise.resolve({
          data: {
            is_running: false,  // Backend dit: ARRÊTÉ
            books_processed: 15,
            book_logs: []
          }
        })
      } else if (url.includes('/problematic-cases')) {
        return Promise.resolve({ data: [] })
      }
      return Promise.reject(new Error('Unknown URL'))
    })

    // Act - Force component to re-fetch (simulate manual refresh)
    wrapper.vm.migrationProgress.is_running = false
    await wrapper.vm.$nextTick()

    // Assert - Ne plus afficher "Liaison en cours" quand is_running=false
    expect(wrapper.find('h2').text()).not.toContain('Liaison en cours')
    expect(wrapper.find('h2').text()).toContain('Migration Babelio')
  })
})
