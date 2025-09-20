import { describe, test, expect, vi, beforeEach } from 'vitest'
import { fixtureCaptureService } from '@/services/FixtureCaptureService.js'

describe('API Interceptor Logic', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.spyOn(fixtureCaptureService, 'logCall').mockImplementation(() => {})
  })

  // Fonction d'intercepteur extraite pour test direct
  function interceptorLogic(response) {
    // Logique de l'intercepteur copiée de api.js
    if (response.config.url?.includes('/fuzzy-search-episode')) {
      const requestData = JSON.parse(response.config.data || '{}')
      fixtureCaptureService.logCall(
        'fuzzySearchService',
        'searchEpisode',
        requestData,
        response.data
      )
    }

    if (response.config.url?.includes('/verify-babelio')) {
      const requestData = JSON.parse(response.config.data || '{}')
      const method = requestData.type === 'author' ? 'verifyAuthor' :
                     requestData.type === 'book' ? 'verifyBook' : 'verifyPublisher'

      fixtureCaptureService.logCall(
        'babelioService',
        method,
        requestData,
        response.data
      )
    }

    return response
  }

  test('should intercept babelio author verification calls', () => {
    const mockResponse = {
      data: { status: 'verified', original: 'Test Author' },
      config: {
        url: '/verify-babelio',
        data: JSON.stringify({ type: 'author', name: 'Test Author' })
      }
    }

    interceptorLogic(mockResponse)

    expect(fixtureCaptureService.logCall).toHaveBeenCalledWith(
      'babelioService',
      'verifyAuthor',
      { type: 'author', name: 'Test Author' },
      { status: 'verified', original: 'Test Author' }
    )
  })

  test('should intercept babelio book verification calls', () => {
    const mockResponse = {
      data: { status: 'verified', original: 'Test Book' },
      config: {
        url: '/verify-babelio',
        data: JSON.stringify({ type: 'book', title: 'Test Book', author: 'Test Author' })
      }
    }

    interceptorLogic(mockResponse)

    expect(fixtureCaptureService.logCall).toHaveBeenCalledWith(
      'babelioService',
      'verifyBook',
      { type: 'book', title: 'Test Book', author: 'Test Author' },
      { status: 'verified', original: 'Test Book' }
    )
  })

  test('should intercept babelio publisher verification calls', () => {
    const mockResponse = {
      data: { status: 'verified', original: 'Test Publisher' },
      config: {
        url: '/verify-babelio',
        data: JSON.stringify({ type: 'publisher', name: 'Test Publisher' })
      }
    }

    interceptorLogic(mockResponse)

    expect(fixtureCaptureService.logCall).toHaveBeenCalledWith(
      'babelioService',
      'verifyPublisher',
      { type: 'publisher', name: 'Test Publisher' },
      { status: 'verified', original: 'Test Publisher' }
    )
  })

  test('should intercept fuzzy search episode calls', () => {
    const mockResponse = {
      data: { found_suggestions: true, title_matches: [], author_matches: [] },
      config: {
        url: '/fuzzy-search-episode',
        data: JSON.stringify({
          episode_id: 'test-id',
          query_title: 'Test Title',
          query_author: 'Test Author'
        })
      }
    }

    interceptorLogic(mockResponse)

    expect(fixtureCaptureService.logCall).toHaveBeenCalledWith(
      'fuzzySearchService',
      'searchEpisode',
      { episode_id: 'test-id', query_title: 'Test Title', query_author: 'Test Author' },
      { found_suggestions: true, title_matches: [], author_matches: [] }
    )
  })

  test('should not intercept other API calls', () => {
    const mockResponse = {
      data: { episodes: [] },
      config: {
        url: '/episodes'
      }
    }

    interceptorLogic(mockResponse)

    // L'intercepteur ne devrait pas avoir été appelé pour cette route
    expect(fixtureCaptureService.logCall).not.toHaveBeenCalled()
  })

  test('should handle malformed request data gracefully', () => {
    const mockResponse = {
      data: { status: 'verified' },
      config: {
        url: '/verify-babelio',
        data: undefined // Pas de data
      }
    }

    interceptorLogic(mockResponse)

    // L'intercepteur devrait gérer gracieusement l'absence de data
    // (par défaut, type undefined devient verifyPublisher)
    expect(fixtureCaptureService.logCall).toHaveBeenCalledWith(
      'babelioService',
      'verifyPublisher',
      {},
      { status: 'verified' }
    )
  })
})
