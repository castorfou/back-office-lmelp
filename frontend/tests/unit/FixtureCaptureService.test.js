import { describe, test, expect, vi, beforeEach } from 'vitest'
import { FixtureCaptureService } from '@/services/FixtureCaptureService.js'

// Mock du module api
vi.mock('@/services/api.js', () => ({
  default: {
    post: vi.fn()
  }
}))

describe('FixtureCaptureService', () => {
  let service

  beforeEach(() => {
    service = new FixtureCaptureService()
    vi.clearAllMocks()
  })

  test('should capture API calls when active', () => {
    service.startCapture()
    service.logCall('babelioService', 'verifyAuthor',
      { name: 'Test' },
      { status: 'verified' }
    )

    expect(service.capturedCalls).toHaveLength(1)
    expect(service.capturedCalls[0].service).toBe('babelioService')
    expect(service.capturedCalls[0].method).toBe('verifyAuthor')
    expect(service.capturedCalls[0].input).toEqual({ name: 'Test' })
    expect(service.capturedCalls[0].output).toEqual({ status: 'verified' })
    expect(service.capturedCalls[0].timestamp).toBeTypeOf('number')
  })

  test('should not capture when inactive', () => {
    // Pas de startCapture()
    service.logCall('babelioService', 'verifyAuthor', {}, {})

    expect(service.capturedCalls).toHaveLength(0)
  })

  test('should reset captured calls when starting new capture', () => {
    service.startCapture()
    service.logCall('babelioService', 'verifyAuthor', { name: 'Test1' }, { status: 'verified' })

    // Nouvelle capture
    service.startCapture()
    service.logCall('babelioService', 'verifyAuthor', { name: 'Test2' }, { status: 'verified' })

    expect(service.capturedCalls).toHaveLength(1)
    expect(service.capturedCalls[0].input.name).toBe('Test2')
  })

  test('should deep clone input and output to avoid reference issues', () => {
    const input = { name: 'Test' }
    const output = { status: 'verified' }

    service.startCapture()
    service.logCall('babelioService', 'verifyAuthor', input, output)

    // Modifier les objets originaux
    input.name = 'Modified'
    output.status = 'modified'

    // Les objets capturés ne doivent pas être affectés
    expect(service.capturedCalls[0].input.name).toBe('Test')
    expect(service.capturedCalls[0].output.status).toBe('verified')
  })

  test('should send captured calls to backend', async () => {
    const { default: api } = await import('@/services/api.js')
    const mockResponse = { data: { success: true, updated_files: ['test.yml'] } }
    api.post.mockResolvedValue(mockResponse)

    service.startCapture()
    service.logCall('babelioService', 'verifyAuthor', { name: 'Test' }, { status: 'verified' })

    await service.stopCaptureAndSend()

    expect(api.post).toHaveBeenCalledWith('/update-fixtures', {
      calls: service.capturedCalls
    })
  })

  test('should handle send error gracefully', async () => {
    const { default: api } = await import('@/services/api.js')
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
    api.post.mockRejectedValue(new Error('Network error'))

    service.startCapture()
    service.logCall('babelioService', 'verifyAuthor', { name: 'Test' }, { status: 'verified' })

    await service.stopCaptureAndSend()

    expect(consoleError).toHaveBeenCalledWith('❌ Failed to update fixtures:', expect.any(Error))
    consoleError.mockRestore()
  })

  test('should not send if no calls captured', async () => {
    const { default: api } = await import('@/services/api.js')
    const consoleLog = vi.spyOn(console, 'log').mockImplementation(() => {})

    service.startCapture()
    await service.stopCaptureAndSend()

    expect(api.post).not.toHaveBeenCalled()
    expect(consoleLog).toHaveBeenCalledWith('⚠️ No API calls captured')
    consoleLog.mockRestore()
  })
})
