/**
 * Tests unitaires pour le lien vers la page émissions depuis LivreDetail (Issue #96, updated Issue #190)
 * Vérifie que chaque émission a un lien vers /emissions/<YYYYMMDD>
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import LivreDetail from '@/views/LivreDetail.vue'
import axios from 'axios'

// Mock axios
vi.mock('axios')

describe('LivreDetail - Lien vers page émissions (Issue #190)', () => {
  let router

  beforeEach(() => {
    vi.resetAllMocks()

    // Create a real router for testing
    router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/livre/:id', component: LivreDetail },
        { path: '/emissions/:date', component: { template: '<div>Emission Detail</div>' } }
      ]
    })
  })

  it('should display a link to emissions page for each emission', async () => {
    // GIVEN: Un livre avec 2 émissions
    const mockLivre = {
      _id: 'livre1',
      titre: 'Test Livre',
      auteur_nom: 'Test Auteur',
      auteur_id: 'auteur1',
      editeur: 'Test Editeur',
      note_moyenne: 7.5,
      nombre_emissions: 2,
      emissions: [
        {
          emission_id: 'em1',
          date: '2025-01-15',
          note_moyenne: 8.0,
          nombre_avis: 3
        },
        {
          emission_id: 'em2',
          date: '2025-01-02',
          note_moyenne: 7.0,
          nombre_avis: 2
        }
      ]
    }

    axios.get.mockResolvedValue({ data: mockLivre })

    // WHEN: On monte le composant
    await router.push('/livre/livre1')
    const wrapper = mount(LivreDetail, {
      global: {
        plugins: [router]
      }
    })

    await flushPromises()

    // THEN: Chaque émission doit avoir un lien vers /emissions/YYYYMMDD
    const emissionLinks = wrapper.findAll('[data-test="emission-link"]')
    expect(emissionLinks).toHaveLength(2)

    // Vérifier que les liens pointent vers /emissions/ avec le bon format de date
    expect(emissionLinks[0].attributes('href')).toBe('/emissions/20250115')
    expect(emissionLinks[1].attributes('href')).toBe('/emissions/20250102')
  })
})
