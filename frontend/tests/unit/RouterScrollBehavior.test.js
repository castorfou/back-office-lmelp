/**
 * Tests pour le comportement de scroll du routeur
 */

import { describe, it, expect } from 'vitest'
import router from '../../src/router/index.js'

describe('Router Scroll Behavior', () => {
  it('should scroll to top on navigation', () => {
    const scrollBehavior = router.options.scrollBehavior

    // Simuler une navigation normale (pas de position sauvegardée)
    const to = { path: '/episodes' }
    const from = { path: '/' }
    const savedPosition = null

    const result = scrollBehavior(to, from, savedPosition)

    expect(result).toEqual({ top: 0, behavior: 'smooth' })
  })

  it('should restore saved position when using browser back/forward', () => {
    const scrollBehavior = router.options.scrollBehavior

    // Simuler l'utilisation des boutons précédent/suivant du navigateur
    const to = { path: '/' }
    const from = { path: '/episodes' }
    const savedPosition = { top: 250, left: 0 }

    const result = scrollBehavior(to, from, savedPosition)

    expect(result).toEqual(savedPosition)
  })

  it('should have smooth scroll behavior configured', () => {
    const scrollBehavior = router.options.scrollBehavior

    const to = { path: '/episodes' }
    const from = { path: '/' }
    const savedPosition = null

    const result = scrollBehavior(to, from, savedPosition)

    expect(result.behavior).toBe('smooth')
  })

  it('should always scroll to top position 0', () => {
    const scrollBehavior = router.options.scrollBehavior

    const to = { path: '/episodes' }
    const from = { path: '/' }
    const savedPosition = null

    const result = scrollBehavior(to, from, savedPosition)

    expect(result.top).toBe(0)
  })
})
