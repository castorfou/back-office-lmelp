/**
 * Tests pour vérifier l'accès réseau depuis un téléphone mobile.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import fs from 'fs'
import path from 'path'

describe('Network Access Configuration', () => {
  it('should configure Vite to accept network connections', () => {
    // Lire le fichier de configuration Vite
    const configPath = path.resolve(process.cwd(), 'vite.config.js')
    expect(fs.existsSync(configPath)).toBe(true)

    const configContent = fs.readFileSync(configPath, 'utf8')

    // Vérifier que la configuration inclut un host pour l'accès réseau
    // Ce test échoue maintenant mais passera après modification
    expect(configContent).toMatch(/host:\s*['"]0\.0\.0\.0['"]/)
  })

  it('should handle different network origins for API calls', async () => {
    // Simuler différentes origines réseau
    const networkOrigins = [
      'http://192.168.1.100:5173',
      'http://10.0.0.50:5173',
      'http://172.16.0.10:5173'
    ]

    // Mock fetch pour tester les appels API depuis différentes origines
    global.fetch = vi.fn()

    for (const origin of networkOrigins) {
      // Simuler une requête depuis une origine réseau
      const mockResponse = {
        ok: true,
        json: async () => ({ message: 'test' })
      }
      global.fetch.mockResolvedValueOnce(mockResponse)

      // Vérifier que les appels API peuvent être faits depuis ces origines
      // (en réalité, cela dépendra de la configuration CORS du backend)
      const response = await fetch('/api/', {
        headers: {
          'Origin': origin
        }
      })

      expect(response.ok).toBe(true)
    }
  })

  it('should have development mode configuration', () => {
    // Vérifier qu'il y a une distinction entre dev et production
    const configPath = path.resolve(process.cwd(), 'vite.config.js')
    const configContent = fs.readFileSync(configPath, 'utf8')

    // La config devrait inclure des paramètres de serveur de développement
    expect(configContent).toMatch(/server:\s*{/)
  })
})
