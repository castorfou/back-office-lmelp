/**
 * Tests TDD pour l'identification visuelle des épisodes avec livres incomplets.
 *
 * Objectif: Les épisodes avec has_incomplete_books=true doivent avoir une couleur orange
 * pour signaler qu'il reste des livres à valider.
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { shallowMount } from '@vue/test-utils'
import LivresAuteurs from '../../src/views/LivresAuteurs.vue'

describe('Episode Incomplete Books Styling', () => {
  let wrapper
  let getEpisodeClass

  beforeEach(() => {
    wrapper = shallowMount(LivresAuteurs, {
      global: {
        stubs: {
          Navigation: true
        }
      }
    })
    getEpisodeClass = wrapper.vm.getEpisodeClass
  })

  it('should return orange class when episode has incomplete books', () => {
    const episode = {
      date: '2025-01-12',
      titre: 'Les nouvelles pages du polar',
      has_cached_books: true,
      has_incomplete_books: true
    }

    const cssClass = getEpisodeClass(episode)
    expect(cssClass).toBe('episode-incomplete')
  })

  it('should return empty class when episode has all books validated', () => {
    const episode = {
      date: '2025-01-12',
      titre: 'Les nouvelles pages du polar',
      has_cached_books: true,
      has_incomplete_books: false
    }

    const cssClass = getEpisodeClass(episode)
    expect(cssClass).toBe('')
  })

  it('should return empty class when episode has no cached books', () => {
    const episode = {
      date: '2025-01-12',
      titre: 'Les nouvelles pages du polar',
      has_cached_books: false,
      has_incomplete_books: false
    }

    const cssClass = getEpisodeClass(episode)
    expect(cssClass).toBe('')
  })

  it('should handle undefined has_incomplete_books as empty class', () => {
    const episode = {
      date: '2025-01-12',
      titre: 'Les nouvelles pages du polar',
      has_cached_books: true
      // has_incomplete_books est undefined
    }

    const cssClass = getEpisodeClass(episode)
    expect(cssClass).toBe('')
  })

  it('should prioritize incomplete over cached when both are true', () => {
    const episode = {
      date: '2025-01-12',
      titre: 'Les nouvelles pages du polar',
      has_cached_books: true,
      has_incomplete_books: true
    }

    const cssClass = getEpisodeClass(episode)
    // On veut la couleur orange (episode-incomplete) plutôt que le préfixe *
    expect(cssClass).toBe('episode-incomplete')
  })
})
