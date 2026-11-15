/**
 * Panneau cookie Babelio dans l'encadré « URL Babelio (optionnel) » des modales
 * (Issue #358).
 *
 * Coller une URL Babelio avec un cookie périmé faisait échouer l'extraction en
 * 403 ; le panneau cookie s'ouvrait derrière la modale. Le panneau vit
 * maintenant dans l'encadré URL : absent sans URL (Babelio n'intervient pas),
 * replié avec un cookie actif, ouvert sinon.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'
import axios from 'axios'
import LivresAuteurs from '@/views/LivresAuteurs.vue'

vi.mock('axios')

vi.mock('../../src/services/api.js', () => ({
  livresAuteursService: {
    getEpisodesWithReviews: vi.fn(),
    getLivresAuteurs: vi.fn(),
    setValidationResults: vi.fn(),
    autoProcessVerifiedBooks: vi.fn(),
  },
  episodeService: { getEpisodeById: vi.fn() },
  statisticsService: { getStatistics: vi.fn() },
  babelioService: { verifyAuthor: vi.fn(), verifyBook: vi.fn() },
  fuzzySearchService: { searchEpisode: vi.fn() }
}))

const EPISODE_ID = '6af98629a3c9beafb9dcb702' // pragma: allowlist secret
const BABELIO_URL = 'https://www.babelio.com/livres/Bailly-Rouges-Truites/2045671'

// Réponse réelle de GET /api/babelio/status
const activeCookie = {
  overall: 'ok', cookie_active: true, cookie_age_sec: 115.1, cookie_max_age_sec: 300,
  cookie_expired: false, circuit_open: false, circuit_reason: null
}
const expiredCookie = { ...activeCookie, cookie_age_sec: 400, cookie_expired: true }

const notFoundBook = {
  cache_id: '6af98629a3c9beafb9dcb704', // pragma: allowlist secret
  episode_oid: EPISODE_ID,
  auteur: 'Pierric Bailly',
  titre: 'Rouge Truite',
  editeur: 'P.O.L.',
  status: 'not_found'
}
const suggestedBook = {
  ...notFoundBook,
  cache_id: '6af98629a3c9beafb9dcb705', // pragma: allowlist secret
  status: 'suggested',
  suggested_title: 'Rouges Truites',
  babelio_url: BABELIO_URL
}

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/livres-auteurs', component: LivresAuteurs },
    { path: '/', component: { template: '<div>Home</div>' } }
  ]
})

describe('LivresAuteurs - cookie Babelio dans les modales (Issue #358)', () => {
  let wrapper

  const manualPanel = () => wrapper.find('[data-testid="manual-babelio-cookie-panel"]')
  const validationPanel = () => wrapper.find('[data-testid="validation-babelio-cookie-panel"]')
  const isOpen = (panel) => panel.find('details').element.open

  const setCookie = async (status) => {
    wrapper.vm.babelioStatus = status
    await flushPromises()
  }

  beforeEach(async () => {
    vi.resetAllMocks()
    axios.get.mockResolvedValue({ data: activeCookie })
    axios.post.mockResolvedValue({
      data: { status: 'success', data: { titre: 'Rouges Truites', auteur: 'Pierric Bailly', editeur: 'P.O.L.' } }
    })
    const { livresAuteursService, episodeService, statisticsService } =
      vi.mocked(await import('../../src/services/api.js'))
    episodeService.getEpisodeById.mockResolvedValue({ id: EPISODE_ID })
    livresAuteursService.getEpisodesWithReviews.mockResolvedValue([])
    livresAuteursService.getLivresAuteurs.mockResolvedValue([notFoundBook])
    statisticsService.getStatistics.mockResolvedValue({})

    wrapper = mount(LivresAuteurs, { global: { plugins: [router] }, attachTo: document.body })
    wrapper.vm.selectedEpisodeId = EPISODE_ID
    await flushPromises()
  })

  afterEach(() => wrapper.unmount())

  describe('« Ajouter manuellement un livre »', () => {
    it('n\'affiche pas le panneau cookie tant que l\'URL Babelio (optionnelle) est vide', async () => {
      wrapper.vm.addManualBook(notFoundBook)
      await flushPromises()

      expect(wrapper.find('[data-testid="manual-babelio-url-input"]').exists()).toBe(true)
      expect(manualPanel().exists()).toBe(false)
    })

    it('affiche le panneau replié dans l\'encadré URL avec un cookie actif', async () => {
      await setCookie(activeCookie)
      wrapper.vm.addManualBook(notFoundBook)
      wrapper.vm.manualBabelioUrl = BABELIO_URL
      await flushPromises()

      expect(wrapper.find('.babelio-url-group [data-testid="manual-babelio-cookie-panel"]').exists()).toBe(true)
      expect(isOpen(manualPanel())).toBe(false)
    })

    it('ouvre le panneau avec un cookie périmé, et laisse « Ajouter le livre » cliquable', async () => {
      await setCookie(expiredCookie)
      wrapper.vm.addManualBook(notFoundBook)
      wrapper.vm.manualBabelioUrl = BABELIO_URL
      await flushPromises()

      expect(isOpen(manualPanel())).toBe(true)
      const addButton = wrapper.findAll('button').find(b => b.text().includes('Ajouter le livre'))
      expect(addButton.attributes('disabled')).toBeUndefined()
    })

    it('ouvre le panneau quand l\'extraction est refusée en 403', async () => {
      await setCookie(activeCookie)
      wrapper.vm.addManualBook(notFoundBook)
      wrapper.vm.manualBabelioUrl = BABELIO_URL
      axios.post.mockRejectedValueOnce({
        response: { status: 403, data: { message: 'Babelio a bloqué la requête (403)' } }
      })

      await wrapper.vm.extractFromBabelioUrl('manual')
      await flushPromises()

      expect(isOpen(manualPanel())).toBe(true)
    })

    it('relance l\'extraction de l\'URL saisie après l\'enregistrement d\'un cookie frais', async () => {
      await setCookie(expiredCookie)
      wrapper.vm.addManualBook(notFoundBook)
      wrapper.vm.manualBabelioUrl = BABELIO_URL
      await flushPromises()
      axios.post.mockClear()

      wrapper.findComponent('[data-testid="manual-babelio-cookie-panel"]').vm.$emit('saved')
      await flushPromises()

      expect(axios.post).toHaveBeenCalledWith('/api/babelio/extract-from-url', { babelio_url: BABELIO_URL })
    })
  })

  describe('« Valider la suggestion »', () => {
    it('affiche le panneau dans l\'encadré URL, pré-rempli avec l\'URL de la suggestion', async () => {
      await setCookie(expiredCookie)
      wrapper.vm.validateSuggestion(suggestedBook)
      await flushPromises()

      expect(wrapper.find('.babelio-url-group [data-testid="validation-babelio-cookie-panel"]').exists()).toBe(true)
      expect(isOpen(validationPanel())).toBe(true)
    })
  })
})
