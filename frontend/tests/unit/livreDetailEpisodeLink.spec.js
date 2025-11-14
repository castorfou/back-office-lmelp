/**
 * Tests unitaires pour le lien vers la page livres-auteurs depuis LivreDetail (Issue #96)
 * Vérifie que chaque épisode a un lien vers /livres-auteurs?episode=<id>
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import LivreDetail from '@/views/LivreDetail.vue'
import axios from 'axios'

// Mock axios
vi.mock('axios')

describe('LivreDetail - Lien vers page livres-auteurs (Issue #96)', () => {
  let router

  beforeEach(() => {
    vi.resetAllMocks()

    // Create a real router for testing
    router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/livre/:id', component: LivreDetail },
        { path: '/livres-auteurs', component: { template: '<div>Livres Auteurs</div>' } }
      ]
    })
  })

  it('should display a link to livres-auteurs page for each episode', async () => {
    // GIVEN: Un livre avec 2 épisodes
    const mockLivre = {
      _id: 'livre1',
      titre: 'Test Livre',
      auteur_nom: 'Test Auteur',
      auteur_id: 'auteur1',
      editeur: 'Test Editeur',
      nombre_episodes: 2,
      episodes: [
        {
          episode_id: 'ep1',
          titre: 'Episode 1',
          date: '2025-01-01',
          programme: true
        },
        {
          episode_id: 'ep2',
          titre: 'Episode 2',
          date: '2025-01-02',
          programme: false
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

    // THEN: Chaque épisode doit avoir un lien vers /livres-auteurs?episode=<episode_id>
    const episodeLinks = wrapper.findAll('[data-test="episode-link"]')
    expect(episodeLinks).toHaveLength(2)

    // Vérifier que les liens pointent vers /livres-auteurs avec le bon episode_id
    expect(episodeLinks[0].attributes('href')).toBe('/livres-auteurs?episode=ep1')
    expect(episodeLinks[0].text()).toContain('Episode 1')

    expect(episodeLinks[1].attributes('href')).toBe('/livres-auteurs?episode=ep2')
    expect(episodeLinks[1].text()).toContain('Episode 2')
  })
})
