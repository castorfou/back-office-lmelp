/**
 * Tests TDD pour la fonction markNotFound - Issue #153.
 *
 * Objectif: Vérifier que markNotFound() envoie le bon item_type au backend
 * selon le type de cas (livre, auteur, livre_auteur_groupe).
 *
 * Problème business:
 * - Pour un cas de type 'livre_auteur_groupe', markNotFound() envoyait
 *   item_type='livre_auteur_groupe' au lieu de 'livre'
 * - Le backend ne reconnaît que 'livre' et 'auteur'
 * - Résultat: Erreur 500/404
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import BabelioMigration from '../../src/views/BabelioMigration.vue'
import axios from 'axios'

// Mock axios
vi.mock('axios')

describe('Babelio Migration - markNotFound', () => {
  let wrapper

  beforeEach(() => {
    vi.clearAllMocks()

    // Mock axios.get pour loadData initial
    axios.get.mockResolvedValue({
      data: {
        total_books: 100,
        migrated_count: 50,
        not_found_count: 10,
        problematic_count: 5,
        pending_count: 35,
        total_authors: 50,
        authors_with_url: 30,
        authors_not_found_count: 2,
        problematic_authors_count: 3,
        authors_without_url_babelio: 15,
        problematic_cases: []
      }
    })

    wrapper = mount(BabelioMigration, {
      global: {
        stubs: {
          Navigation: true
        }
      }
    })
  })

  it('should send item_type="livre" for livre_auteur_groupe type', async () => {
    // Arrange - Cas de type 'livre_auteur_groupe'
    const cas = {
      type: 'livre_auteur_groupe',
      livre_id: '507f1f77bcf86cd799439011',
      auteur_id: '507f1f77bcf86cd799439012',
      titre_attendu: 'Le Petit Prince',
      nom_auteur: 'Antoine de Saint-Exupéry'
    }

    // Mock axios.post pour mark-not-found
    axios.post.mockResolvedValueOnce({
      data: {
        status: 'success',
        message: 'Livre marqué not found'
      }
    })

    // Act - Appeler markNotFound
    await wrapper.vm.markNotFound(cas)

    // Assert - Vérifier que axios.post a été appelé avec item_type='livre'
    expect(axios.post).toHaveBeenCalledWith(
      '/api/babelio-migration/mark-not-found',
      expect.objectContaining({
        item_id: '507f1f77bcf86cd799439011',
        item_type: 'livre',  // Doit être 'livre', PAS 'livre_auteur_groupe'
        reason: 'Livre non disponible sur Babelio'
      })
    )
  })

  it('should send item_type="livre" for livre type', async () => {
    // Arrange - Cas de type 'livre'
    const cas = {
      type: 'livre',
      livre_id: '507f1f77bcf86cd799439011',
      titre_attendu: 'L\'Étranger'
    }

    axios.post.mockResolvedValueOnce({
      data: { status: 'success' }
    })

    // Act
    await wrapper.vm.markNotFound(cas)

    // Assert
    expect(axios.post).toHaveBeenCalledWith(
      '/api/babelio-migration/mark-not-found',
      expect.objectContaining({
        item_id: '507f1f77bcf86cd799439011',
        item_type: 'livre',
        reason: 'Livre non disponible sur Babelio'
      })
    )
  })

  it('should send item_type="auteur" for auteur type', async () => {
    // Arrange - Cas de type 'auteur'
    const cas = {
      type: 'auteur',
      auteur_id: '507f1f77bcf86cd799439012',
      nom_auteur: 'Victor Hugo'
    }

    axios.post.mockResolvedValueOnce({
      data: { status: 'success' }
    })

    // Act
    await wrapper.vm.markNotFound(cas)

    // Assert
    expect(axios.post).toHaveBeenCalledWith(
      '/api/babelio-migration/mark-not-found',
      expect.objectContaining({
        item_id: '507f1f77bcf86cd799439012',
        item_type: 'auteur',
        reason: 'Auteur non disponible sur Babelio'
      })
    )
  })

  it('should handle errors gracefully', async () => {
    // Arrange
    const cas = {
      type: 'livre',
      livre_id: '507f1f77bcf86cd799439011',
      titre_attendu: 'Test'
    }

    // Mock erreur backend
    axios.post.mockRejectedValueOnce({
      response: {
        data: {
          message: 'Type invalide: livre_auteur_groupe'
        }
      }
    })

    // Spy sur showToast
    const showToastSpy = vi.spyOn(wrapper.vm, 'showToast')

    // Act
    await wrapper.vm.markNotFound(cas)

    // Assert - Une erreur doit être affichée
    expect(showToastSpy).toHaveBeenCalledWith(
      expect.stringContaining('Erreur'),
      'error'
    )
  })
})
