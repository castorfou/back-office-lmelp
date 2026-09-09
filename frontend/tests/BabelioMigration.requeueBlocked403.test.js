/**
 * Tests TDD pour l'action groupée "Relancer tous les 403" (Issue #304)
 *
 * Problème business réel :
 * - Un run de migration avec cookie Babelio expiré pollue
 *   babelio_problematic_cases avec des livres marqués "blocked_403"
 * - Ces livres sont exclus définitivement des runs futurs
 * - L'utilisateur doit pouvoir les libérer en masse depuis la page
 *   Migration Babelio, sans traiter chaque cas manuellement
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import BabelioMigration from '../src/views/BabelioMigration.vue'
import axios from 'axios'

vi.mock('axios')

const RouterLinkStub = {
  template: '<a><slot /></a>'
}

describe('BabelioMigration - Relancer tous les 403 (Issue #304)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

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

  const mockDefaultEndpoints = (problematicCases) => {
    axios.get.mockImplementation((url) => {
      if (url.includes('/status')) {
        return Promise.resolve({ data: { total_books: 10, migrated_count: 5, pending_count: 5, authors_without_url_babelio: 0 } })
      }
      if (url.includes('/progress')) {
        return Promise.resolve({ data: { is_running: false, books_processed: 0, book_logs: [] } })
      }
      if (url.includes('/problematic-cases')) {
        return Promise.resolve({ data: problematicCases })
      }
      if (url.includes('/covers/mismatch')) {
        return Promise.resolve({ data: [] })
      }
      return Promise.reject(new Error('Unknown URL'))
    })
  }

  it('n\'affiche pas le bouton "Relancer tous les 403" quand aucun cas n\'est bloqué', async () => {
    mockDefaultEndpoints([
      {
        type: 'livre',
        livre_id: '1',
        titre_attendu: 'Titre A',
        auteur: 'Auteur A',
        raison: 'Titre ne correspond pas',
        url_babelio: 'N/A',
        timestamp: '2026-01-01T00:00:00Z'
      }
    ])

    const wrapper = mountWithRouter(BabelioMigration)
    await wrapper.vm.$nextTick()
    await new Promise((resolve) => setTimeout(resolve, 50))

    expect(wrapper.find('[data-test="requeue-blocked-403-btn"]').exists()).toBe(false)
  })

  it('affiche le bouton "Relancer tous les 403" avec le bon compte quand des cas sont bloqués', async () => {
    mockDefaultEndpoints([
      {
        type: 'livre',
        livre_id: '1',
        titre_attendu: 'Titre A',
        auteur: 'Auteur A',
        raison: 'Livre non traité - status: blocked_403',
        url_babelio: 'N/A',
        timestamp: '2026-01-01T00:00:00Z'
      },
      {
        type: 'livre',
        livre_id: '2',
        titre_attendu: 'Titre B',
        auteur: 'Auteur B',
        raison: 'Livre non traité - status: blocked_403',
        url_babelio: 'N/A',
        timestamp: '2026-01-01T00:00:00Z'
      },
      {
        type: 'livre',
        livre_id: '3',
        titre_attendu: 'Titre C',
        auteur: 'Auteur C',
        raison: 'Titre ne correspond pas',
        url_babelio: 'N/A',
        timestamp: '2026-01-01T00:00:00Z'
      }
    ])

    const wrapper = mountWithRouter(BabelioMigration)
    await wrapper.vm.$nextTick()
    await new Promise((resolve) => setTimeout(resolve, 50))

    const button = wrapper.find('[data-test="requeue-blocked-403-btn"]')
    expect(button.exists()).toBe(true)
    expect(button.text()).toContain('2')
  })

  it('appelle l\'endpoint requeue-blocked-403 puis recharge les données au clic', async () => {
    mockDefaultEndpoints([
      {
        type: 'livre',
        livre_id: '1',
        titre_attendu: 'Titre A',
        auteur: 'Auteur A',
        raison: 'Livre non traité - status: blocked_403',
        url_babelio: 'N/A',
        timestamp: '2026-01-01T00:00:00Z'
      }
    ])

    axios.post.mockResolvedValue({
      data: { status: 'success', requeued_count: 1, message: '1 cas libérés pour retraitement au prochain run' }
    })

    const wrapper = mountWithRouter(BabelioMigration)
    await wrapper.vm.$nextTick()
    await new Promise((resolve) => setTimeout(resolve, 50))

    const getCallsBefore = axios.get.mock.calls.length

    const button = wrapper.find('[data-test="requeue-blocked-403-btn"]')
    await button.trigger('click')
    await wrapper.vm.$nextTick()
    await new Promise((resolve) => setTimeout(resolve, 50))

    expect(axios.post).toHaveBeenCalledWith('/api/babelio-migration/requeue-blocked-403')
    expect(axios.get.mock.calls.length).toBeGreaterThan(getCallsBefore)
  })
})
