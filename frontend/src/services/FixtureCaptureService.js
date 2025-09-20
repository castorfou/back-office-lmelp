/**
 * Service de capture des appels API pour génération automatique de fixtures
 */

import api from './api.js'

export class FixtureCaptureService {
  constructor() {
    this.capturedCalls = []
    this.isCapturing = false
  }

  startCapture() {
    this.capturedCalls = []
    this.isCapturing = true
    console.log('🎯 Fixture capture started')
  }

  logCall(service, method, input, output) {
    if (!this.isCapturing) return

    this.capturedCalls.push({
      service,
      method,
      input: JSON.parse(JSON.stringify(input)),
      output: JSON.parse(JSON.stringify(output)),
      timestamp: Date.now()
    })

    console.log(`📹 Captured: ${service}.${method}`, { input, output })
  }

  async stopCaptureAndSend() {
    this.isCapturing = false

    if (this.capturedCalls.length === 0) {
      console.log('⚠️ No API calls captured')
      return
    }

    console.log(`📦 Sending ${this.capturedCalls.length} captured calls`)

    try {
      const response = await api.post('/update-fixtures', {
        calls: this.capturedCalls
      })

      console.log('✅ Fixtures updated:', response.data)
    } catch (error) {
      console.error('❌ Failed to update fixtures:', error)
    }
  }
}

// Instance singleton
export const fixtureCaptureService = new FixtureCaptureService()
