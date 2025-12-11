/**
 * Tests TDD pour la barre de progression de BabelioMigration.vue (Issue #124)
 *
 * Ce test vérifie qu'une barre de progression visuelle est affichée
 * pendant la liaison automatique, montrant le pourcentage de complétion
 * basé sur books_processed / totalItemsToProcess.
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

describe('BabelioMigration - Progress Bar', () => {
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

  it('should display progress bar when migration is running', async () => {
    // Arrange - Mock API responses
    const mockStatus = {
      total_books: 504,
      migrated_count: 481,
      not_found_count: 5,
      problematic_count: 2,
      pending_count: 0,  // Pas de livres en attente
      total_authors: 463,
      authors_with_url: 448,
      authors_without_url_babelio: 15  // 15 auteurs en attente
    }

    const mockProgress = {
      is_running: true,
      books_processed: 7,  // 7 auteurs traités sur 15
      start_time: '2025-12-09T03:59:38',
      last_update: '2025-12-09T04:00:05',
      book_logs: []
    }

    const mockProblematicCases = []

    axios.get.mockImplementation((url) => {
      if (url.includes('/api/babelio-migration/status')) {
        return Promise.resolve({ data: mockStatus })
      } else if (url.includes('/api/babelio-migration/progress')) {
        return Promise.resolve({ data: mockProgress })
      } else if (url.includes('/api/babelio-migration/problematic-cases')) {
        return Promise.resolve({ data: mockProblematicCases })
      }
      return Promise.reject(new Error('Unknown URL'))
    })

    // Act - Mount component
    const wrapper = mountWithRouter(BabelioMigration)

    // Wait for data to load
    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))

    // Assert - Progress bar should be visible
    const progressBar = wrapper.find('.progress-bar-container')
    expect(progressBar.exists()).toBe(true)

    // Assert - Progress bar fill width should be 46.7% (7/15)
    const progressFill = wrapper.find('.progress-bar-fill')
    expect(progressFill.exists()).toBe(true)
    const width = progressFill.element.style.width
    expect(width).toContain('46')  // ~46.7%

    // Assert - Progress label should show "7 / 15 traités (47%)"
    const progressLabel = wrapper.find('.progress-bar-label')
    expect(progressLabel.exists()).toBe(true)
    expect(progressLabel.text()).toContain('7 / 15')
    expect(progressLabel.text()).toContain('47%')  // Rounded
  })

  it('should calculate total items as pending_count + authors_without_url', async () => {
    // Arrange - 10 livres en attente + 5 auteurs en attente = 15 total
    const mockStatus = {
      total_books: 504,
      migrated_count: 481,
      pending_count: 10,  // 10 livres en attente
      total_authors: 463,
      authors_with_url: 458,
      authors_without_url_babelio: 5  // 5 auteurs en attente
    }

    const mockProgress = {
      is_running: true,
      books_processed: 3,  // 3 sur 15 traités
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

    // Assert - Total should be 15 (10 livres + 5 auteurs)
    const progressLabel = wrapper.find('.progress-bar-label')
    expect(progressLabel.text()).toContain('3 / 15')
    expect(progressLabel.text()).toContain('20%')  // 3/15 = 20%
  })

  it('should not display progress bar when no items to process', async () => {
    // Arrange - Tout est traité
    const mockStatus = {
      total_books: 504,
      migrated_count: 504,
      pending_count: 0,  // Pas de livres
      total_authors: 463,
      authors_with_url: 463,
      authors_without_url_babelio: 0  // Pas d'auteurs
    }

    const mockProgress = {
      is_running: false,
      books_processed: 0,
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

    // Assert - Progress bar should NOT exist
    const progressBar = wrapper.find('.progress-bar-container')
    expect(progressBar.exists()).toBe(false)
  })
})
