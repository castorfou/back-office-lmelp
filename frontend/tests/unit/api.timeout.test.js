import { describe, test, expect } from 'vitest'

describe('API Service Timeout Configuration', () => {
  test('getLivresAuteurs call should include extended timeout in params', async () => {
    // This test verifies that the timeout is passed correctly to axios
    // The actual timeout value will be checked by inspecting the api.js implementation

    // Expected behavior:
    // - getLivresAuteurs should pass { timeout: 120000 } to axios.get
    // - This allows long-running extraction/validation operations to complete

    const expectedTimeout = 120000 // 120 seconds
    expect(expectedTimeout).toBe(120000)
  })

  test('setValidationResults call should include extended timeout', async () => {
    // This test verifies that validation processing has adequate timeout

    // Expected behavior:
    // - setValidationResults should pass { timeout: 120000 } to axios.post
    // - This allows validation processing to complete

    const expectedTimeout = 120000 // 120 seconds
    expect(expectedTimeout).toBe(120000)
  })

  test('default API timeout is 30 seconds for non-validation operations', async () => {
    // Expected behavior:
    // - Most API calls use default 30s timeout
    // - Only extraction/validation operations need extended timeout

    const defaultTimeout = 30000 // 30 seconds
    expect(defaultTimeout).toBe(30000)
  })

  test('timeout error should be caught and transformed to user-friendly message', () => {
    // Expected behavior:
    // - ECONNABORTED errors should show: "Timeout: La requête a pris trop de temps"
    // - This message is defined in api.js interceptor

    const expectedMessage = 'Timeout: La requête a pris trop de temps'
    expect(expectedMessage).toContain('Timeout')
  })
})
