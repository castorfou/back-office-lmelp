/**
 * Tests TDD pour la fonctionnalité de migration des couvertures - Issue #238.
 *
 * Objectif: Section "Couvertures" dans BabelioMigration.vue qui:
 * - Affiche les statistiques de couvertures (total, liés, en attente)
 * - Lance un batch de liaison des couvertures
 * - Peut être arrêté en cours de traitement
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import BabelioMigration from '../../src/views/BabelioMigration.vue'
import axios from 'axios'

// Mock axios
vi.mock('axios')

const defaultStatusResponse = {
  data: {
    total_books: 100,
    migrated_count: 80,
    not_found_count: 10,
    problematic_count: 5,
    pending_count: 5,
    total_authors: 50,
    authors_with_url: 30,
    authors_not_found_count: 2,
    problematic_authors_count: 3,
    authors_without_url_babelio: 15,
    // Statistiques couvertures
    covers_total: 100,
    covers_with_url: 30,
    covers_not_applicable: 10,
    covers_pending: 40,
  }
}

const defaultProblematicResponse = { data: [] }

describe('Babelio Cover Migration', () => {
  let wrapper

  beforeEach(() => {
    vi.clearAllMocks()

    // Mock axios.get: status + problematic-cases
    axios.get.mockImplementation((url) => {
      if (url.includes('status')) {
        return Promise.resolve(defaultStatusResponse)
      }
      if (url.includes('problematic-cases')) {
        return Promise.resolve(defaultProblematicResponse)
      }
      if (url.includes('progress')) {
        return Promise.resolve({ data: { is_running: false, books_processed: 0, book_logs: [] } })
      }
      return Promise.resolve({ data: {} })
    })
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
    }
  })

  it('should display cover stats when status is loaded', async () => {
    // Arrange & Act
    wrapper = mount(BabelioMigration, {
      global: { stubs: { Navigation: true } }
    })
    // Wait for all pending promises (loadData + checkMigrationProgress)
    await Promise.resolve()
    await Promise.resolve()
    await Promise.resolve()
    await wrapper.vm.$nextTick()

    // Assert: les statistiques couvertures doivent être affichées
    const html = wrapper.html()
    expect(html).toContain('Couvertures')
    expect(html).toContain('30') // covers_with_url
    expect(html).toContain('40') // covers_pending
  })

  it('should display cover migration launch button', async () => {
    // Arrange & Act
    wrapper = mount(BabelioMigration, {
      global: { stubs: { Navigation: true } }
    })
    // Wait for all pending promises (loadData + checkMigrationProgress)
    await Promise.resolve()
    await Promise.resolve()
    await Promise.resolve()
    await wrapper.vm.$nextTick()

    // Assert: un bouton pour lancer la liaison des couvertures doit exister
    const buttons = wrapper.findAll('button')
    const coverButton = buttons.find(b => b.text().includes('couverture') || b.text().includes('Couverture'))
    expect(coverButton).toBeDefined()
  })

  it('should call pending covers endpoint when starting cover migration', async () => {
    // Arrange
    wrapper = mount(BabelioMigration, {
      global: { stubs: { Navigation: true } }
    })
    await wrapper.vm.$nextTick()

    // Mock des livres vide pour éviter le délai de 10s dans la boucle
    axios.get.mockResolvedValueOnce({ data: [] })

    // Act: déclencher la méthode (aucun livre → pas de boucle → pas de délai)
    await wrapper.vm.startCoverMigration()

    // Assert: GET covers/pending doit avoir été appelé
    const getCalls = axios.get.mock.calls.map(c => c[0])
    expect(getCalls.some(url => url.includes('covers/pending'))).toBe(true)
  })

  it('should stop cover migration when stopCoverMigration is called', async () => {
    // Arrange
    wrapper = mount(BabelioMigration, {
      global: { stubs: { Navigation: true } }
    })
    await wrapper.vm.$nextTick()

    // Verify stop method sets the flag
    wrapper.vm.coverProgress = { is_running: true, processed: 0, total: 5, logs: [] }

    // Act
    wrapper.vm.stopCoverMigration()

    // Assert: le flag d'arrêt doit être positionné
    expect(wrapper.vm.stopCoverMigration_flag).toBe(true)
  })
})
