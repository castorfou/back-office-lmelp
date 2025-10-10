/**
 * Tests unitaires pour formatEpisodeOption()
 * Vérifie l'affichage des indicateurs visuels pour les épisodes
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { shallowMount } from '@vue/test-utils'
import LivresAuteurs from '@/views/LivresAuteurs.vue'

describe('formatEpisodeOption', () => {
  let formatEpisodeOption

  beforeEach(() => {
    // Utiliser shallowMount pour éviter de rendre les composants enfants
    const wrapper = shallowMount(LivresAuteurs, {
      global: {
        stubs: {
          Navigation: true
        }
      }
    })
    formatEpisodeOption = wrapper.vm.formatEpisodeOption
  })

  it('should add ⚠️ prefix when episode has incomplete books', () => {
    const episode = {
      date: '2025-01-12',
      titre: 'Les nouvelles pages du polar',
      has_cached_books: true,
      has_incomplete_books: true
    }

    const result = formatEpisodeOption(episode)

    expect(result).toBe('⚠️ 12/01/2025 - Les nouvelles pages du polar')
  })

  it('should add * prefix when episode has cached books but all validated', () => {
    const episode = {
      date: '2025-01-12',
      titre: 'Les nouvelles pages du polar',
      has_cached_books: true,
      has_incomplete_books: false
    }

    const result = formatEpisodeOption(episode)

    expect(result).toBe('* 12/01/2025 - Les nouvelles pages du polar')
  })

  it('should not add prefix when has_cached_books is false', () => {
    const episode = {
      date: '2025-01-05',
      titre: 'Littérature contemporaine',
      has_cached_books: false,
      has_incomplete_books: false
    }

    const result = formatEpisodeOption(episode)

    expect(result).toBe('05/01/2025 - Littérature contemporaine')
  })

  it('should not add prefix when has_cached_books is undefined', () => {
    const episode = {
      date: '2025-01-05',
      titre: 'Littérature contemporaine'
      // has_cached_books absent
    }

    const result = formatEpisodeOption(episode)

    expect(result).toBe('05/01/2025 - Littérature contemporaine')
  })

  it('should use titre_corrige if present', () => {
    const episode = {
      date: '2025-01-12',
      titre: 'Titre original',
      titre_corrige: 'Titre corrigé',
      has_cached_books: true,
      has_incomplete_books: false
    }

    const result = formatEpisodeOption(episode)

    expect(result).toBe('* 12/01/2025 - Titre corrigé')
  })

  it('should prioritize ⚠️ over * when has_incomplete_books is true', () => {
    const episode = {
      date: '2025-01-12',
      titre: 'Titre original',
      titre_corrige: 'Titre corrigé',
      has_cached_books: true,
      has_incomplete_books: true
    }

    const result = formatEpisodeOption(episode)

    expect(result).toBe('⚠️ 12/01/2025 - Titre corrigé')
  })
})
