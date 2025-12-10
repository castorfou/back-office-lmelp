/**
 * Tests TDD pour le polling de progression Babelio - Issue #124.
 *
 * Objectif: Remplacer EventSource par un polling simple qui:
 * - Ne tourne que quand is_running === true
 * - S'arrête quand is_running devient false
 * - Se nettoie proprement au démontage du composant
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import BabelioMigration from '../../src/views/BabelioMigration.vue'
import axios from 'axios'

// Mock axios
vi.mock('axios')

describe('Babelio Migration Polling', () => {
  let wrapper

  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()

    // Mock axios.get pour loadData
    axios.get.mockResolvedValue({
      data: {
        total_books: 100,
        migrated_count: 50,
        not_found_count: 10,
        problematic_count: 5,
        pending_count: 35,
        total_authors: 50,
        authors_with_url: 30,
        authors_not_found_count: 2,
        problematic_authors_count: 3,
        authors_without_url_babelio: 15,
        problematic_cases: []
      }
    })
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
    }
    vi.clearAllTimers()
    vi.useRealTimers()
  })

  it('should start polling when migration is started', async () => {
    // Arrange
    wrapper = mount(BabelioMigration, {
      global: {
        stubs: {
          Navigation: true
        }
      }
    })

    // Mock axios.post pour démarrer la migration
    axios.post.mockResolvedValueOnce({
      data: { status: 'started' }
    })

    // Mock axios.get pour le polling de progression
    axios.get.mockResolvedValueOnce({
      data: {
        is_running: true,
        books_processed: 10,
        book_logs: [],
        start_time: Date.now(),
        last_update: Date.now()
      }
    })

    // Act - Lancer la migration
    await wrapper.vm.toggleMigration()
    await wrapper.vm.$nextTick()

    // Assert - Vérifier que le polling est démarré
    expect(wrapper.vm.pollInterval).toBeDefined()
    expect(wrapper.vm.migrationProgress.is_running).toBe(true)
  })

  it('should stop polling when migration completes', async () => {
    // Arrange
    wrapper = mount(BabelioMigration, {
      global: {
        stubs: {
          Navigation: true
        }
      }
    })

    // Démarrer la migration
    axios.post.mockResolvedValueOnce({
      data: { status: 'started' }
    })

    // Premier appel au polling - migration en cours
    axios.get.mockResolvedValueOnce({
      data: {
        is_running: true,
        books_processed: 10,
        book_logs: []
      }
    })

    await wrapper.vm.toggleMigration()
    await wrapper.vm.$nextTick()

    expect(wrapper.vm.pollInterval).toBeDefined()
    const intervalId = wrapper.vm.pollInterval

    // Act - Simuler la fin de la migration
    axios.get.mockResolvedValueOnce({
      data: {
        is_running: false,
        books_processed: 100,
        book_logs: []
      }
    })

    // Avancer le timer pour déclencher le polling
    await vi.advanceTimersByTimeAsync(2000)
    await wrapper.vm.$nextTick()

    // Assert - Le polling doit s'être arrêté
    expect(wrapper.vm.pollInterval).toBeNull()
    expect(wrapper.vm.migrationProgress.is_running).toBe(false)
  })

  it('should clean up polling interval on component unmount', async () => {
    // Arrange
    wrapper = mount(BabelioMigration, {
      global: {
        stubs: {
          Navigation: true
        }
      }
    })

    // Démarrer la migration
    axios.post.mockResolvedValueOnce({
      data: { status: 'started' }
    })

    axios.get.mockResolvedValue({
      data: {
        is_running: true,
        books_processed: 10,
        book_logs: []
      }
    })

    await wrapper.vm.toggleMigration()
    await wrapper.vm.$nextTick()

    expect(wrapper.vm.pollInterval).toBeDefined()
    const intervalId = wrapper.vm.pollInterval

    // Act - Démonter le composant
    wrapper.unmount()

    // Assert - Vérifier qu'aucun polling ne continue après le démontage
    const callCountBefore = axios.get.mock.calls.length

    // Avancer le timer
    await vi.advanceTimersByTimeAsync(2000)

    const callCountAfter = axios.get.mock.calls.length

    // Le nombre d'appels ne doit pas avoir augmenté après démontage
    expect(callCountAfter).toBe(callCountBefore)
  })

  it('should not start polling if migration is not running', async () => {
    // Arrange
    wrapper = mount(BabelioMigration, {
      global: {
        stubs: {
          Navigation: true
        }
      }
    })

    await wrapper.vm.$nextTick()

    // S'assurer que is_running est false
    wrapper.vm.migrationProgress.is_running = false

    // Attendre que le montage soit complet
    await vi.runAllTimersAsync()
    vi.clearAllMocks() // Réinitialiser les compteurs d'appels

    const callCountBefore = axios.get.mock.calls.length

    // Act - Avancer le temps
    await vi.advanceTimersByTimeAsync(2000)

    const callCountAfter = axios.get.mock.calls.length

    // Assert - Aucun appel de polling ne doit être fait
    expect(callCountAfter).toBe(callCountBefore)
    expect(wrapper.vm.pollInterval).toBeNull()
  })

  it('should update progress data from polling response', async () => {
    // Arrange
    wrapper = mount(BabelioMigration, {
      global: {
        stubs: {
          Navigation: true
        }
      }
    })

    await wrapper.vm.$nextTick()

    // Démarrer la migration
    axios.post.mockResolvedValueOnce({
      data: { status: 'started' }
    })

    const mockProgressData = {
      is_running: true,
      books_processed: 42,
      book_logs: [
        { livre_id: '123', titre: 'Test', status: 'success' }
      ],
      start_time: 1234567890,
      last_update: 1234567900
    }

    // Mock pour le premier checkMigrationProgress immédiat
    axios.get.mockResolvedValueOnce({
      data: {
        is_running: true,
        books_processed: 0,
        book_logs: []
      }
    })

    // Mock pour le polling suivant avec les vraies données
    axios.get.mockResolvedValue({
      data: mockProgressData
    })

    await wrapper.vm.toggleMigration()
    await wrapper.vm.$nextTick()

    // Act - Appeler directement checkMigrationProgress pour simuler le polling
    await wrapper.vm.checkMigrationProgress()
    await wrapper.vm.$nextTick()

    // Assert - Les données de progression doivent être mises à jour
    expect(wrapper.vm.migrationProgress.books_processed).toBe(42)
    expect(wrapper.vm.migrationProgress.book_logs).toHaveLength(1)
    expect(wrapper.vm.migrationProgress.book_logs[0].titre).toBe('Test')
  })
})
