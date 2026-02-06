/**
 * Tests unitaires pour l'affichage des tags Calibre sur LivreDetail (Issue #200)
 * Vérifie l'affichage des tags et la fonctionnalité de copie
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import LivreDetail from '@/views/LivreDetail.vue'
import axios from 'axios'

// Mock axios
vi.mock('axios')

describe('LivreDetail - Calibre Tags (Issue #200)', () => {
  let router

  beforeEach(() => {
    vi.resetAllMocks()

    router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/livre/:id', component: LivreDetail },
        { path: '/auteur/:id', component: { template: '<div>Auteur</div>' } },
        { path: '/emissions/:date', component: { template: '<div>Emission</div>' } }
      ]
    })
  })

  it('should display calibre tags as badges', async () => {
    // GIVEN: Un livre avec des tags Calibre
    const mockLivre = {
      titre: 'La Deuxième Vie',
      auteur_nom: 'Philippe Sollers',
      auteur_id: 'auteur1',
      editeur: 'Gallimard',
      note_moyenne: 9.0,
      nombre_emissions: 1,
      emissions: [
        { emission_id: 'em1', date: '2024-03-24', note_moyenne: 9.0, nombre_avis: 1 }
      ],
      calibre_tags: ['guillaume', 'lmelp_240324', 'lmelp_arnaud_viviant']
    }

    axios.get.mockResolvedValue({ data: mockLivre })

    // WHEN: On monte le composant
    await router.push('/livre/livre1')
    const wrapper = mount(LivreDetail, {
      global: { plugins: [router] }
    })
    await flushPromises()

    // THEN: Les tags sont affichés comme des badges
    const tagBadges = wrapper.findAll('[data-test="tag-badge"]')
    expect(tagBadges).toHaveLength(3)
    expect(tagBadges[0].text()).toBe('guillaume')
    expect(tagBadges[1].text()).toBe('lmelp_240324')
    expect(tagBadges[2].text()).toBe('lmelp_arnaud_viviant')
  })

  it('should not display tags section when calibre_tags is empty', async () => {
    // GIVEN: Un livre sans tags Calibre
    const mockLivre = {
      titre: 'Livre Sans Tags',
      auteur_nom: 'Auteur Test',
      auteur_id: 'auteur1',
      editeur: 'Editeur Test',
      note_moyenne: null,
      nombre_emissions: 0,
      emissions: [],
      calibre_tags: []
    }

    axios.get.mockResolvedValue({ data: mockLivre })

    // WHEN: On monte le composant
    await router.push('/livre/livre1')
    const wrapper = mount(LivreDetail, {
      global: { plugins: [router] }
    })
    await flushPromises()

    // THEN: Pas de section tags
    const tagsSection = wrapper.find('[data-test="tags-section"]')
    expect(tagsSection.exists()).toBe(false)
  })

  it('should not display tags section when calibre_tags is absent', async () => {
    // GIVEN: Un livre sans le champ calibre_tags (backward compatibility)
    const mockLivre = {
      titre: 'Ancien Livre',
      auteur_nom: 'Auteur Test',
      auteur_id: 'auteur1',
      editeur: 'Editeur Test',
      note_moyenne: null,
      nombre_emissions: 0,
      emissions: []
    }

    axios.get.mockResolvedValue({ data: mockLivre })

    // WHEN: On monte le composant
    await router.push('/livre/livre1')
    const wrapper = mount(LivreDetail, {
      global: { plugins: [router] }
    })
    await flushPromises()

    // THEN: Pas de section tags
    const tagsSection = wrapper.find('[data-test="tags-section"]')
    expect(tagsSection.exists()).toBe(false)
  })

  it('should copy tags to clipboard when copy button is clicked', async () => {
    // GIVEN: Un livre avec des tags Calibre
    const mockLivre = {
      titre: 'La Deuxième Vie',
      auteur_nom: 'Philippe Sollers',
      auteur_id: 'auteur1',
      editeur: 'Gallimard',
      note_moyenne: 9.0,
      nombre_emissions: 1,
      emissions: [
        { emission_id: 'em1', date: '2024-03-24', note_moyenne: 9.0, nombre_avis: 1 }
      ],
      calibre_tags: ['guillaume', 'lmelp_240324', 'lmelp_arnaud_viviant']
    }

    axios.get.mockResolvedValue({ data: mockLivre })

    // Mock clipboard API
    const writeTextMock = vi.fn().mockResolvedValue(undefined)
    Object.assign(navigator, {
      clipboard: { writeText: writeTextMock }
    })

    // WHEN: On monte et on clique sur copier
    await router.push('/livre/livre1')
    const wrapper = mount(LivreDetail, {
      global: { plugins: [router] }
    })
    await flushPromises()

    // Call method directly for reliable state access
    await wrapper.vm.copyTags()

    // THEN: Le presse-papier contient les tags séparés par des virgules
    expect(writeTextMock).toHaveBeenCalledWith('guillaume, lmelp_240324, lmelp_arnaud_viviant')
    expect(wrapper.vm.tagsCopied).toBe(true)
  })

  it('should show copy button only when tags exist', async () => {
    // GIVEN: Un livre avec des tags Calibre
    const mockLivre = {
      titre: 'Test Livre',
      auteur_nom: 'Test Auteur',
      auteur_id: 'auteur1',
      editeur: 'Test Editeur',
      note_moyenne: 7.5,
      nombre_emissions: 1,
      emissions: [
        { emission_id: 'em1', date: '2024-03-24', note_moyenne: 7.5, nombre_avis: 2 }
      ],
      calibre_tags: ['lmelp_240324']
    }

    axios.get.mockResolvedValue({ data: mockLivre })

    // WHEN: On monte le composant
    await router.push('/livre/livre1')
    const wrapper = mount(LivreDetail, {
      global: { plugins: [router] }
    })
    await flushPromises()

    // THEN: Le bouton copier est visible
    const copyBtn = wrapper.find('[data-test="copy-tags-btn"]')
    expect(copyBtn.exists()).toBe(true)
  })
})
