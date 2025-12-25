/**
 * Tests unitaires pour le lien Anna's Archive depuis LivreDetail (Issue #165)
 * Vérifie l'affichage de l'icône et la génération de l'URL de recherche
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import LivreDetail from '@/views/LivreDetail.vue'
import axios from 'axios'

// Mock axios
vi.mock('axios')

describe('LivreDetail - Lien Anna\'s Archive (Issue #165)', () => {
  let router

  beforeEach(() => {
    vi.resetAllMocks()

    router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/livre/:id', component: LivreDetail }
      ]
    })
  })

  it('should display Anna\'s Archive icon next to Babelio icon', async () => {
    // GIVEN: Un livre avec titre et auteur
    const mockLivre = {
      _id: 'livre1',
      titre: 'Marx en Amérique',
      auteur_nom: 'Christian Laval',
      auteur_id: 'auteur1',
      editeur: 'Test Editeur',
      url_babelio: 'https://www.babelio.com/livres/test',
      nombre_episodes: 1,
      episodes: []
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

    // THEN: L'icône Anna's Archive doit être affichée
    const annasLink = wrapper.find('[data-test="annas-archive-link"]')
    expect(annasLink.exists()).toBe(true)

    // L'icône doit être présente
    const annasIcon = wrapper.find('[data-test="annas-archive-icon"]')
    expect(annasIcon.exists()).toBe(true)
  })

  it('should generate correct Anna\'s Archive search URL with encoded title and author', async () => {
    // GIVEN: Un livre avec titre et auteur contenant des caractères spéciaux
    const mockLivre = {
      _id: 'livre1',
      titre: 'Marx en Amérique',
      auteur_nom: 'Christian Laval',
      auteur_id: 'auteur1',
      editeur: 'Test Editeur',
      nombre_episodes: 1,
      episodes: []
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

    // THEN: Le lien doit pointer vers Anna's Archive avec titre et auteur encodés
    const annasLink = wrapper.find('[data-test="annas-archive-link"]')
    const expectedUrl = 'https://fr.annas-archive.org/search?index=&page=1&sort=&display=&q=Marx+en+Am%C3%A9rique+-+Christian+Laval'
    expect(annasLink.attributes('href')).toBe(expectedUrl)
  })

  it('should open Anna\'s Archive in a new tab', async () => {
    // GIVEN: Un livre
    const mockLivre = {
      _id: 'livre1',
      titre: 'Test Livre',
      auteur_nom: 'Test Auteur',
      auteur_id: 'auteur1',
      editeur: 'Test Editeur',
      nombre_episodes: 1,
      episodes: []
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

    // THEN: Le lien doit s'ouvrir dans un nouvel onglet
    const annasLink = wrapper.find('[data-test="annas-archive-link"]')
    expect(annasLink.attributes('target')).toBe('_blank')
    expect(annasLink.attributes('rel')).toBe('noopener noreferrer')
  })

  it('should handle special characters in title and author correctly', async () => {
    // GIVEN: Un livre avec caractères spéciaux variés
    const mockLivre = {
      _id: 'livre1',
      titre: 'L\'Art & la Vie: éléments',
      auteur_nom: 'Jean-Paul Évrard',
      auteur_id: 'auteur1',
      editeur: 'Test Editeur',
      nombre_episodes: 1,
      episodes: []
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

    // THEN: Les caractères spéciaux doivent être correctement encodés
    const annasLink = wrapper.find('[data-test="annas-archive-link"]')
    const href = annasLink.attributes('href')

    // Vérifier que l'URL contient le titre et l'auteur encodés selon le format Anna's Archive
    expect(href).toContain('L%27Art')    // apostrophe encodée → %27
    expect(href).toContain('%26')        // & → %26
    expect(href).toContain('%C3%A9')     // é → %C3%A9
    expect(href).toContain('Jean-Paul')  // tiret préservé
  })
})
