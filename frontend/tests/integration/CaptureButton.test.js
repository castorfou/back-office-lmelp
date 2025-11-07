import { describe, test, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'
import LivresAuteurs from '@/views/LivresAuteurs.vue'
import { fixtureCaptureService } from '@/services/FixtureCaptureService.js'
import BiblioValidationService from '@/services/BiblioValidationService.js'

// Mock du module API
vi.mock('@/services/api.js', () => ({
  livresAuteursService: {
    getEpisodesWithReviews: vi.fn(),
    getLivresAuteurs: vi.fn(),
    setValidationResults: vi.fn(),
    autoProcessVerifiedBooks: vi.fn()
  }
}))

// Mock du service de validation Biblio
vi.mock('@/services/BiblioValidationService.js', () => ({
  default: {
    validateBiblio: vi.fn()
  }
}))

// Mock du service de capture de fixtures
vi.mock('@/services/FixtureCaptureService.js', () => ({
  fixtureCaptureService: {
    startCapture: vi.fn(),
    stopCaptureAndSend: vi.fn(),
    logCall: vi.fn()
  }
}))

// Mock du composant BiblioValidationCell
vi.mock('@/components/BiblioValidationCell.vue', () => ({
  default: {
    name: 'BiblioValidationCell',
    props: ['author', 'title', 'publisher', 'episodeId'],
    template: '<div data-testid="biblio-validation-cell">Mocked BiblioValidationCell</div>'
  }
}))

// Mock du composant Navigation
vi.mock('@/components/Navigation.vue', () => ({
  default: {
    name: 'Navigation',
    props: ['pageTitle'],
    template: '<div data-testid="navigation">Mocked Navigation</div>'
  }
}))

describe.skip('Capture Button Integration', () => {
  let wrapper

  // Configuration du routeur pour les tests
  const router = createRouter({
    history: createWebHistory(),
    routes: [
      { path: '/livres-auteurs', component: LivresAuteurs },
      { path: '/', component: { template: '<div>Home</div>' } }
    ]
  })
  const mockEpisodes = [
    {
      id: 'episode-1',
      titre: 'Episode Test',
      date: '2023-01-01'
    }
  ]

  const mockBooks = [
    {
      episode_oid: 'episode-1',
      auteur: 'Emmanuel Carrère',
      titre: 'Colcause',
      editeur: 'POL',
      status: 'verified',
      programme: true,
      coup_de_coeur: false
    },
    {
      episode_oid: 'episode-1',
      auteur: 'Fatima Das',
      titre: 'Jouer le jeu',
      editeur: 'Flammarion',
      status: 'suggested',
      programme: false,
      coup_de_coeur: true
    }
  ]

  beforeEach(async () => {
    vi.clearAllMocks()

    // Mock des réponses API
    const { livresAuteursService } = vi.mocked(await import('@/services/api.js'))
    livresAuteursService.getEpisodesWithReviews.mockResolvedValue(mockEpisodes)
    livresAuteursService.getLivresAuteurs.mockResolvedValue(mockBooks)
    livresAuteursService.setValidationResults.mockResolvedValue({ success: true })
    livresAuteursService.autoProcessVerifiedBooks.mockResolvedValue({ success: true, processed_count: 0 })

    // Mock du service de validation
    vi.mocked(BiblioValidationService.validateBiblio).mockResolvedValue({
      status: 'verified'
    })

    // Mock du service de capture
    vi.mocked(fixtureCaptureService.stopCaptureAndSend).mockResolvedValue()
  })

  test('should display capture button on each row', async () => {
    wrapper = mount(LivresAuteurs, {
      global: {
        plugins: [router]
      }
    })

    // Attendre que les épisodes soient chargés
    await wrapper.vm.$nextTick()
    await new Promise(resolve => setTimeout(resolve, 10))

    // Sélectionner un épisode
    wrapper.vm.selectedEpisodeId = 'episode-1'
    await wrapper.vm.loadBooksForEpisode()
    await wrapper.vm.$nextTick()

    // Activer la colonne YAML pour afficher les boutons de capture
    wrapper.vm.showYamlColumn = true
    await wrapper.vm.$nextTick()

    // Vérifier que le tableau s'affiche maintenant
    const table = wrapper.find('.books-table')
    expect(table.exists()).toBe(true)

    // Vérifier que les boutons de capture sont présents
    const captureButtons = wrapper.findAll('.btn-capture-fixtures')
    expect(captureButtons).toHaveLength(mockBooks.length)

    // Vérifier le contenu des boutons
    captureButtons.forEach(button => {
      expect(button.text()).toBe('🔄 YAML')
      expect(button.attributes('title')).toBe('Capturer les appels API pour les fixtures')
    })
  })

  test('should trigger capture when button clicked', async () => {
    wrapper = mount(LivresAuteurs, {
      global: {
        plugins: [router]
      }
    })

    await wrapper.vm.$nextTick()
    wrapper.vm.selectedEpisodeId = 'episode-1'
    await wrapper.vm.loadBooksForEpisode()
    await wrapper.vm.$nextTick()

    // Activer la colonne YAML pour afficher les boutons de capture
    wrapper.vm.showYamlColumn = true
    await wrapper.vm.$nextTick()

    // Cliquer sur le premier bouton de capture
    const firstCaptureButton = wrapper.find('.btn-capture-fixtures')
    await firstCaptureButton.trigger('click')

    // Vérifier que la capture a été démarrée
    expect(fixtureCaptureService.startCapture).toHaveBeenCalled()

    // Vérifier que BiblioValidationService a été appelé
    expect(BiblioValidationService.validateBiblio).toHaveBeenCalledWith(
      'Emmanuel Carrère',
      'Colcause',
      'POL',
      'episode-1'
    )

    // Vérifier que la capture a été arrêtée et envoyée
    expect(fixtureCaptureService.stopCaptureAndSend).toHaveBeenCalled()
  })

  test('should handle validation errors gracefully', async () => {
    // Mock une erreur de validation
    vi.mocked(BiblioValidationService.validateBiblio).mockRejectedValue(
      new Error('Network error')
    )

    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})

    wrapper = mount(LivresAuteurs, {
      global: {
        plugins: [router]
      }
    })

    await wrapper.vm.$nextTick()
    wrapper.vm.selectedEpisodeId = 'episode-1'
    await wrapper.vm.loadBooksForEpisode()
    await wrapper.vm.$nextTick()

    // Activer la colonne YAML pour afficher les boutons de capture
    wrapper.vm.showYamlColumn = true
    await wrapper.vm.$nextTick()

    // Cliquer sur le bouton de capture
    const captureButton = wrapper.find('.btn-capture-fixtures')
    await captureButton.trigger('click')

    // Attendre que l'erreur soit traitée
    await wrapper.vm.$nextTick()

    // Vérifier que l'erreur a été loggée
    expect(consoleError).toHaveBeenCalledWith(
      '❌ Error during BiblioValidation:',
      expect.any(Error)
    )

    // Vérifier que stopCaptureAndSend est toujours appelé (finally block)
    expect(fixtureCaptureService.stopCaptureAndSend).toHaveBeenCalled()

    consoleError.mockRestore()
  })

  test('should call captureFixtures with correct book data', async () => {
    wrapper = mount(LivresAuteurs, {
      global: {
        plugins: [router]
      }
    })

    await wrapper.vm.$nextTick()
    wrapper.vm.selectedEpisodeId = 'episode-1'
    await wrapper.vm.loadBooksForEpisode()
    await wrapper.vm.$nextTick()

    // Activer la colonne YAML pour afficher les boutons de capture
    wrapper.vm.showYamlColumn = true
    await wrapper.vm.$nextTick()

    // Spy sur la méthode captureFixtures
    const captureFixturesSpy = vi.spyOn(wrapper.vm, 'captureFixtures')

    // Cliquer sur le premier bouton
    const firstCaptureButton = wrapper.find('.btn-capture-fixtures')
    await firstCaptureButton.trigger('click')

    // Vérifier que captureFixtures a été appelé avec les bonnes données
    expect(captureFixturesSpy).toHaveBeenCalledWith(mockBooks[0])
  })

  test('should have proper test ids for capture buttons', async () => {
    wrapper = mount(LivresAuteurs, {
      global: {
        plugins: [router]
      }
    })

    await wrapper.vm.$nextTick()
    wrapper.vm.selectedEpisodeId = 'episode-1'
    await wrapper.vm.loadBooksForEpisode()
    await wrapper.vm.$nextTick()

    // Activer la colonne YAML pour afficher les boutons de capture
    wrapper.vm.showYamlColumn = true
    await wrapper.vm.$nextTick()

    // Vérifier les test ids
    const firstButton = wrapper.find('[data-testid="capture-button-episode-1-Emmanuel Carrère-Colcause"]')
    expect(firstButton.exists()).toBe(true)

    const secondButton = wrapper.find('[data-testid="capture-button-episode-1-Fatima Das-Jouer le jeu"]')
    expect(secondButton.exists()).toBe(true)
  })
})
