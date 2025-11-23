/**
 * Tests unitaires pour la page Masquer les Épisodes (Issue #107)
 * Vérifie le chargement, l'affichage, le tri, le filtrage et le toggle du statut masked
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import MasquerEpisodes from '@/views/MasquerEpisodes.vue'

// Mock du service API
vi.mock('@/services/api.js', () => ({
  episodeService: {
    getAllEpisodesIncludingMasked: vi.fn(),
    updateEpisodeMaskedStatus: vi.fn()
  },
  livresAuteursService: {},
  babelioService: {},
  fuzzySearchService: {},
  searchService: {},
  statisticsService: {}
}))

describe('MasquerEpisodes - Affichage et fonctionnalités (Issue #107)', () => {
  let router
  let episodeService

  beforeEach(async () => {
    vi.resetAllMocks()

    // Import le service mocké
    const api = await import('@/services/api.js')
    episodeService = api.episodeService

    // Create a real router for testing
    router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/masquer-episodes', component: MasquerEpisodes },
        { path: '/', component: { template: '<div>Home</div>' } }
      ]
    })
  })

  it('should load and display episodes with all columns', async () => {
    // GIVEN: Des épisodes avec différents statuts
    const mockEpisodes = [
      {
        id: 'ep1',
        titre: 'Episode visible',
        date: '2024-11-10T09:59:39',
        duree: 2763,
        type: 'livre',
        masked: false
      },
      {
        id: 'ep2',
        titre: 'Episode masqué',
        date: '2024-11-09T09:59:39',
        duree: 1800,
        type: 'livre',
        masked: true
      },
      {
        id: 'ep3',
        titre: 'Episode sans durée',
        date: '2024-11-08T09:59:39',
        duree: null,
        type: 'livre',
        masked: false
      }
    ]

    episodeService.getAllEpisodesIncludingMasked.mockResolvedValue(mockEpisodes)

    await router.push('/masquer-episodes')
    const wrapper = mount(MasquerEpisodes, {
      global: {
        plugins: [router]
      }
    })

    await flushPromises()

    // THEN: Les colonnes doivent être présentes
    expect(wrapper.text()).toContain('Titre')
    expect(wrapper.text()).toContain('Durée')
    expect(wrapper.text()).toContain('Date')
    expect(wrapper.text()).toContain('Visibilité')

    // THEN: Les 3 épisodes doivent être affichés
    expect(wrapper.text()).toContain('Episode visible')
    expect(wrapper.text()).toContain('Episode masqué')
    expect(wrapper.text()).toContain('Episode sans durée')

    // THEN: Les durées formatées doivent être affichées
    expect(wrapper.text()).toContain('46 min') // 2763 secondes = 46 min 3s
    expect(wrapper.text()).toContain('30 min') // 1800 secondes = 30 min
  })

  it('should format duration correctly', async () => {
    // GIVEN: Épisodes avec différentes durées
    const mockEpisodes = [
      { id: 'ep1', titre: 'Court', date: '2024-11-10T09:59:39', duree: 59, type: 'livre', masked: false },
      { id: 'ep2', titre: 'Moyen', date: '2024-11-10T09:59:39', duree: 3661, type: 'livre', masked: false },
      { id: 'ep3', titre: 'Long', date: '2024-11-10T09:59:39', duree: 7325, type: 'livre', masked: false },
      { id: 'ep4', titre: 'Null', date: '2024-11-10T09:59:39', duree: null, type: 'livre', masked: false }
    ]

    episodeService.getAllEpisodesIncludingMasked.mockResolvedValue(mockEpisodes)

    await router.push('/masquer-episodes')
    const wrapper = mount(MasquerEpisodes, {
      global: {
        plugins: [router]
      }
    })

    await flushPromises()

    // THEN: Les durées doivent être formatées correctement
    expect(wrapper.text()).toContain('59 s')      // < 1 min
    expect(wrapper.text()).toContain('1h 01 min') // 3661s = 1h 1min 1s
    expect(wrapper.text()).toContain('2h 02 min') // 7325s = 2h 2min 5s
    expect(wrapper.text()).toContain('-')          // null
  })

  it('should toggle masked status when clicking toggle button', async () => {
    // GIVEN: Un épisode visible
    const mockEpisodes = [
      {
        id: 'ep1',
        titre: 'Episode à masquer',
        date: '2024-11-10T09:59:39',
        duree: 1200,
        type: 'livre',
        masked: false
      }
    ]

    episodeService.getAllEpisodesIncludingMasked.mockResolvedValue(mockEpisodes)
    episodeService.updateEpisodeMaskedStatus.mockResolvedValue({ message: 'Épisode masqué avec succès' })

    await router.push('/masquer-episodes')
    const wrapper = mount(MasquerEpisodes, {
      global: {
        plugins: [router]
      }
    })

    await flushPromises()

    // WHEN: On clique sur le toggle button
    const toggleButton = wrapper.find('[data-test="toggle-masked-ep1"]')
    expect(toggleButton.exists()).toBe(true)

    await toggleButton.trigger('click')
    await flushPromises()

    // THEN: L'API doit être appelée avec le nouveau statut
    expect(episodeService.updateEpisodeMaskedStatus).toHaveBeenCalledWith('ep1', true)
  })

  it('should filter episodes by title', async () => {
    // GIVEN: Des épisodes
    const mockEpisodes = [
      { id: 'ep1', titre: 'Daniel Pennac', date: '2024-11-10T09:59:39', duree: 2763, type: 'livre', masked: false },
      { id: 'ep2', titre: 'Victor Hugo', date: '2024-11-09T09:59:39', duree: 1800, type: 'livre', masked: false },
      { id: 'ep3', titre: 'Albert Camus', date: '2024-11-08T09:59:39', duree: null, type: 'livre', masked: false }
    ]

    episodeService.getAllEpisodesIncludingMasked.mockResolvedValue(mockEpisodes)

    await router.push('/masquer-episodes')
    const wrapper = mount(MasquerEpisodes, {
      global: {
        plugins: [router]
      }
    })

    await flushPromises()

    // WHEN: On filtre par "pennac"
    const searchInput = wrapper.find('input[type="text"]')
    await searchInput.setValue('pennac')
    await flushPromises()

    // THEN: Seul l'épisode correspondant doit être visible
    const tableText = wrapper.find('table').text()
    expect(tableText).toContain('Daniel Pennac')
    expect(tableText).not.toContain('Victor Hugo')
    expect(tableText).not.toContain('Albert Camus')
  })

  it('should sort episodes by title', async () => {
    // GIVEN: Des épisodes non triés
    const mockEpisodes = [
      { id: 'ep1', titre: 'Zola', date: '2024-11-10T09:59:39', duree: 2000, type: 'livre', masked: false },
      { id: 'ep2', titre: 'Baudelaire', date: '2024-11-09T09:59:39', duree: 1800, type: 'livre', masked: false },
      { id: 'ep3', titre: 'Molière', date: '2024-11-08T09:59:39', duree: 1900, type: 'livre', masked: false }
    ]

    episodeService.getAllEpisodesIncludingMasked.mockResolvedValue(mockEpisodes)

    await router.push('/masquer-episodes')
    const wrapper = mount(MasquerEpisodes, {
      global: {
        plugins: [router]
      }
    })

    await flushPromises()

    // WHEN: On clique sur l'en-tête "Titre" pour trier
    const titleHeader = wrapper.find('[data-test="sort-titre"]')
    await titleHeader.trigger('click')
    await flushPromises()

    // THEN: Les épisodes doivent être triés par ordre alphabétique
    const rows = wrapper.findAll('tbody tr')
    expect(rows[0].text()).toContain('Baudelaire')
    expect(rows[1].text()).toContain('Molière')
    expect(rows[2].text()).toContain('Zola')
  })

  it('should sort episodes by date', async () => {
    // GIVEN: Des épisodes avec différentes dates
    const mockEpisodes = [
      { id: 'ep1', titre: 'Episode 1', date: '2024-11-08T09:59:39', duree: 2000, type: 'livre', masked: false },
      { id: 'ep2', titre: 'Episode 2', date: '2024-11-10T09:59:39', duree: 1800, type: 'livre', masked: false },
      { id: 'ep3', titre: 'Episode 3', date: '2024-11-09T09:59:39', duree: 1900, type: 'livre', masked: false }
    ]

    episodeService.getAllEpisodesIncludingMasked.mockResolvedValue(mockEpisodes)

    await router.push('/masquer-episodes')
    const wrapper = mount(MasquerEpisodes, {
      global: {
        plugins: [router]
      }
    })

    await flushPromises()

    // WHEN: On clique sur l'en-tête "Date" pour trier
    // Note: Le tri par défaut est déjà sur la date (descendant).
    // Un clic va donc inverser l'ordre pour devenir ascendant (plus ancien en premier).
    const dateHeader = wrapper.find('[data-test="sort-date"]')
    await dateHeader.trigger('click')
    await flushPromises()

    // THEN: Les épisodes doivent être triés par date (plus ancien en premier)
    const rows = wrapper.findAll('tbody tr')
    expect(rows[0].text()).toContain('Episode 1') // 2024-11-08
    expect(rows[1].text()).toContain('Episode 3') // 2024-11-09
    expect(rows[2].text()).toContain('Episode 2') // 2024-11-10
  })

  it('should sort episodes by date descending by default', async () => {
    // GIVEN: Des épisodes avec différentes dates
    const mockEpisodes = [
      { id: 'ep1', titre: 'Episode 1', date: '2024-11-08T09:59:39', duree: 2000, type: 'livre', masked: false },
      { id: 'ep2', titre: 'Episode 2', date: '2024-11-10T09:59:39', duree: 1800, type: 'livre', masked: false },
      { id: 'ep3', titre: 'Episode 3', date: '2024-11-09T09:59:39', duree: 1900, type: 'livre', masked: false }
    ]

    episodeService.getAllEpisodesIncludingMasked.mockResolvedValue(mockEpisodes)

    await router.push('/masquer-episodes')
    const wrapper = mount(MasquerEpisodes, {
      global: {
        plugins: [router]
      }
    })

    await flushPromises()

    // THEN: Les épisodes doivent être triés par date (plus récent en premier) par défaut
    const rows = wrapper.findAll('tbody tr')
    expect(rows[0].text()).toContain('Episode 2') // 2024-11-10
    expect(rows[1].text()).toContain('Episode 3') // 2024-11-09
    expect(rows[2].text()).toContain('Episode 1') // 2024-11-08
  })

  it('should display error message when API call fails', async () => {
    // GIVEN: L'API retourne une erreur
    episodeService.getAllEpisodesIncludingMasked.mockRejectedValue(new Error('Erreur réseau'))

    await router.push('/masquer-episodes')
    const wrapper = mount(MasquerEpisodes, {
      global: {
        plugins: [router]
      }
    })

    await flushPromises()

    // THEN: Un message d'erreur doit être affiché
    expect(wrapper.text()).toContain('Erreur')
  })

  it('should show loading state while fetching episodes', async () => {
    // GIVEN: L'API est en cours de chargement
    let resolvePromise
    const promise = new Promise((resolve) => {
      resolvePromise = resolve
    })
    episodeService.getAllEpisodesIncludingMasked.mockReturnValue(promise)

    await router.push('/masquer-episodes')
    const wrapper = mount(MasquerEpisodes, {
      global: {
        plugins: [router]
      }
    })

    // THEN: Un indicateur de chargement doit être affiché
    expect(wrapper.text()).toContain('Chargement')

    // Clean up
    resolvePromise([])
    await flushPromises()
  })
})
