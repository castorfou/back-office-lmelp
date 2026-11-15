/**
 * Ordre des blocs de la page Livres et Auteurs (Issue #358).
 *
 * La légende décrit les pastilles du sélecteur d'épisode : elle suit le
 * sélecteur. Le bloc Babelio (barre « Valider avec Babelio », panneau cookie)
 * ne sert qu'à valider les livres : il précède directement la liste, après les
 * détails de l'épisode.
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'
import LivresAuteurs from '@/views/LivresAuteurs.vue'

// GET /api/babelio/status (panneau cookie) : pas de serveur dans les tests
vi.mock('axios', () => ({
  default: { get: vi.fn().mockResolvedValue({ data: null }), post: vi.fn() }
}))

vi.mock('../../src/services/api.js', () => ({
  livresAuteursService: {
    getEpisodesWithReviews: vi.fn(),
    getLivresAuteurs: vi.fn(),
    setValidationResults: vi.fn(),
    autoProcessVerifiedBooks: vi.fn(),
  },
  episodeService: {
    getEpisodeById: vi.fn(),
  },
  statisticsService: {
    getStatistics: vi.fn(),
  },
  babelioService: {
    verifyAuthor: vi.fn(),
    verifyBook: vi.fn(),
  },
  fuzzySearchService: {
    searchEpisode: vi.fn(),
  }
}))

const mockEpisode = {
  id: '6af98629a3c9beafb9dcb702', // pragma: allowlist secret
  titre: 'CRITIQUE : Elise Lespade, Pierric Bailly…',
  date: '2026-11-15',
  avis_critique_id: '6af98629a3c9beafb9dcb703' // pragma: allowlist secret
}

// Livre extrait pas encore validé (sans statut) : la barre « Valider avec Babelio » s'affiche
const bookToValidate = {
  cache_id: '6af98629a3c9beafb9dcb704', // pragma: allowlist secret
  episode_oid: mockEpisode.id,
  auteur: 'Pierric Bailly',
  titre: 'Rouge Truite',
  editeur: 'P.O.L.',
  programme: true,
  coup_de_coeur: false
}

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/livres-auteurs', component: LivresAuteurs },
    { path: '/', component: { template: '<div>Home</div>' } }
  ]
})

// Réponse réelle de GET /api/babelio/status, cookie actif (âge 115 s sur 300)
const activeCookieStatus = {
  overall: 'ok', cookie_active: true, cookie_age_sec: 115.1, cookie_max_age_sec: 300,
  cookie_expired: false, circuit_open: false, circuit_reason: null
}

// a précède b dans le document
const precedes = (a, b) =>
  Boolean(a.element.compareDocumentPosition(b.element) & Node.DOCUMENT_POSITION_FOLLOWING)

describe('LivresAuteurs - ordre des blocs (Issue #358)', () => {
  let wrapper

  beforeEach(async () => {
    vi.resetAllMocks()
    const { livresAuteursService, episodeService, statisticsService } =
      vi.mocked(await import('../../src/services/api.js'))
    episodeService.getEpisodeById.mockResolvedValue(mockEpisode)
    livresAuteursService.getEpisodesWithReviews.mockResolvedValue([mockEpisode])
    livresAuteursService.getLivresAuteurs.mockResolvedValue([bookToValidate])
    statisticsService.getStatistics.mockResolvedValue({})

    wrapper = mount(LivresAuteurs, { global: { plugins: [router] } })
    await wrapper.vm.loadEpisodesWithReviews?.()
    wrapper.vm.selectedEpisodeId = mockEpisode.id
    await wrapper.vm.loadBooksForEpisode()
    await wrapper.vm.$nextTick()
  })

  // L'état du cookie vient du panneau cookie, seule source de vérité de la page
  const setCookieState = async (state) => {
    wrapper.findComponent({ name: 'BabelioCookiePanel' }).vm.$emit('cookie-state', state)
    await wrapper.vm.$nextTick()
  }

  it('place la légende sous le sélecteur, puis les détails, puis le bloc Babelio, puis les livres', () => {
    const selector = wrapper.find('.episode-selector')
    const legend = wrapper.find('.legend-section')
    const details = wrapper.find('.episode-details-accordion')
    const validateBar = wrapper.find('[data-test="validate-babelio-button"]')
    const cookie = wrapper.find('.babelio-cookie-section')
    const stats = wrapper.find('.stats-section')

    for (const block of [selector, legend, details, validateBar, cookie, stats]) {
      expect(block.exists()).toBe(true)
    }
    expect(precedes(selector, legend)).toBe(true)
    expect(precedes(legend, details)).toBe(true)
    expect(precedes(details, validateBar)).toBe(true)
    expect(precedes(validateBar, cookie)).toBe(true)
    expect(precedes(cookie, stats)).toBe(true)
  })

  it('intitule la légende « Statuts des épisodes » : elle décrit les pastilles du sélecteur', () => {
    expect(wrapper.find('.legend-section h6').text()).toBe('Statuts des épisodes :')
  })

  describe('bouton 🔄 « Relancer la validation »', () => {
    const refreshButton = () => wrapper.find('[data-testid="refresh-cache-button"]')

    it('est dans la ligne du cookie Babelio, plus à côté du sélecteur', () => {
      expect(refreshButton().exists()).toBe(true)
      expect(wrapper.find('.episode-selector [data-testid="refresh-cache-button"]').exists()).toBe(false)
      expect(wrapper.find('.babelio-cookie-summary [data-testid="refresh-cache-button"]').exists()).toBe(true)
      expect(refreshButton().text()).toContain('Relancer la validation')
    })

    it('relance la validation sans plier ni déplier le panneau cookie', async () => {
      await setCookieState('active')
      const spy = vi.spyOn(wrapper.vm, 'refreshEpisodeCache').mockResolvedValue()
      const click = new MouseEvent('click', { bubbles: true, cancelable: true })

      refreshButton().element.dispatchEvent(click)
      await wrapper.vm.$nextTick()

      expect(spy).toHaveBeenCalled()
      // Clic dans un <summary> : sans preventDefault, le <details> basculerait
      expect(click.defaultPrevented).toBe(true)
    })
  })
})

describe('LivresAuteurs - boutons Babelio et état du cookie (Issue #358)', () => {
  let wrapper
  const validateButton = () => wrapper.find('[data-test="validate-babelio-button"]')
  const refreshButton = () => wrapper.find('[data-testid="refresh-cache-button"]')
  const setCookieState = async (state) => {
    wrapper.findComponent({ name: 'BabelioCookiePanel' }).vm.$emit('cookie-state', state)
    await wrapper.vm.$nextTick()
  }

  beforeEach(async () => {
    vi.resetAllMocks()
    const { livresAuteursService, episodeService, statisticsService } =
      vi.mocked(await import('../../src/services/api.js'))
    episodeService.getEpisodeById.mockResolvedValue(mockEpisode)
    livresAuteursService.getEpisodesWithReviews.mockResolvedValue([mockEpisode])
    livresAuteursService.getLivresAuteurs.mockResolvedValue([bookToValidate])
    livresAuteursService.deleteCacheByEpisode = vi.fn().mockResolvedValue({ deleted_count: 1 })
    statisticsService.getStatistics.mockResolvedValue({})

    wrapper = mount(LivresAuteurs, { global: { plugins: [router] } })
    wrapper.vm.selectedEpisodeId = mockEpisode.id
    await wrapper.vm.loadBooksForEpisode()
    await wrapper.vm.$nextTick()
  })

  for (const state of ['missing', 'expired']) {
    it(`grise « Valider avec Babelio » et « Relancer la validation » quand le cookie est ${state}`, async () => {
      await setCookieState(state)

      expect(validateButton().attributes('disabled')).toBeDefined()
      expect(refreshButton().attributes('disabled')).toBeDefined()
      expect(refreshButton().attributes('title')).toContain('cookie Babelio frais')
    })
  }

  it('active les deux boutons quand le cookie est actif', async () => {
    await setCookieState('active')

    expect(validateButton().attributes('disabled')).toBeUndefined()
    expect(refreshButton().attributes('disabled')).toBeUndefined()
  })

  it('ne vide pas le cache de l\'épisode sans cookie utilisable, même appelé directement', async () => {
    const { livresAuteursService } = vi.mocked(await import('../../src/services/api.js'))
    await setCookieState('expired')

    await wrapper.vm.refreshEpisodeCache()
    await wrapper.vm.validateWithBabelio()

    expect(livresAuteursService.deleteCacheByEpisode).not.toHaveBeenCalled()
    expect(livresAuteursService.getLivresAuteurs).not.toHaveBeenCalledWith(
      expect.objectContaining({ enrich_babelio: true })
    )
  })
})

describe('BabelioCookiePanel - état du cookie transmis à la page (Issue #358)', () => {
  const mountPanel = async (status) => {
    const { default: BabelioCookiePanel } = await import('@/components/BabelioCookiePanel.vue')
    return mount(BabelioCookiePanel, { props: { status } })
  }

  it('émet « active » pour un cookie actif', async () => {
    const panel = await mountPanel(activeCookieStatus)
    expect(panel.emitted('cookie-state').at(-1)).toEqual(['active'])
  })

  it('émet « expired » pour un cookie périmé', async () => {
    const panel = await mountPanel({ ...activeCookieStatus, cookie_age_sec: 400, cookie_expired: true })
    expect(panel.emitted('cookie-state').at(-1)).toEqual(['expired'])
  })

  it('émet « missing » sans cookie, puis « active » quand un cookie frais arrive', async () => {
    const panel = await mountPanel(null)
    expect(panel.emitted('cookie-state').at(-1)).toEqual(['missing'])

    await panel.setProps({ status: activeCookieStatus })
    expect(panel.emitted('cookie-state').at(-1)).toEqual(['active'])
  })
})

describe('BabelioCookiePanel - emplacement « actions » (Issue #358)', () => {
  it('n\'affiche aucune zone d\'actions quand la page hôte n\'en fournit pas', async () => {
    const { default: BabelioCookiePanel } = await import('@/components/BabelioCookiePanel.vue')
    const panel = mount(BabelioCookiePanel, { props: { status: null } })

    expect(panel.find('.babelio-cookie-actions').exists()).toBe(false)
  })
})
