/**
 * Tests TDD pour confirmValidation() - Issue #85
 *
 * Objectif: S'assurer que babelio_url et babelio_publisher sont transmis
 * au backend quand l'utilisateur valide manuellement un livre enrichi.
 *
 * Scénario:
 * 1. Un livre a été enrichi automatiquement avec Babelio (babelio_url, babelio_publisher)
 * 2. L'utilisateur clique sur "Valider" dans le modal
 * 3. confirmValidation() doit transmettre ces champs au backend
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { mount } from '@vue/test-utils';
import LivresAuteurs from '../../src/views/LivresAuteurs.vue';

// Mock des services
vi.mock('../../src/services/api.js', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    livresAuteursService: {
      getLivresAuteurs: vi.fn(),
      validateSuggestion: vi.fn(),
      addManualBook: vi.fn(),
      deleteCacheByEpisode: vi.fn()
    },
    episodeService: {
      getEpisodesWithReviews: vi.fn()
    }
  };
});

// Import après le mock
import { livresAuteursService } from '../../src/services/api.js';

describe('LivresAuteurs - confirmValidation (Issue #85)', () => {
  let wrapper;

  beforeEach(() => {
    vi.clearAllMocks();

    // Mock getLivresAuteurs pour retourner une liste vide par défaut
    livresAuteursService.getLivresAuteurs.mockResolvedValue([]);

    // Mock validateSuggestion
    livresAuteursService.validateSuggestion.mockResolvedValue({ success: true });

    wrapper = mount(LivresAuteurs, {
      data() {
        return {
          selectedEpisodeId: '68bd9ed3582cf994fb66f1d6',
          episodesWithReviews: [
            {
              id: '68bd9ed3582cf994fb66f1d6',
              avis_critique_id: '68bddf38d79eae6a485abdaf'
            }
          ],
          showValidationModal: false,
          currentBookToValidate: null,
          validationForm: {
            author: '',
            title: '',
            publisher: ''
          }
        };
      }
    });
  });

  it('RED PHASE: devrait transmettre babelio_url et babelio_publisher depuis le livre enrichi', async () => {
    // Arrange: Livre enrichi avec données Babelio
    const enrichedBook = {
      cache_id: '68f52dd097c9ca8cb481ec35',
      auteur: 'Emmanuel Carrère',
      titre: 'Kolkhoze',
      editeur: 'POL',
      suggested_author: 'Emmanuel Carrère',
      suggested_title: 'Kolkhoze',
      babelio_url: 'https://www.babelio.com/livres/Carrere-Kolkhoze/1839593',
      babelio_publisher: 'P.O.L.'
    };

    // Simuler l'ouverture du modal de validation
    wrapper.vm.currentBookToValidate = enrichedBook;
    wrapper.vm.validationForm = {
      author: 'Emmanuel Carrère',
      title: 'Kolkhoze',
      publisher: 'P.O.L.'
    };
    wrapper.vm.showValidationModal = true;

    // Act: Confirmer la validation
    await wrapper.vm.confirmValidation();

    // Assert: Vérifier que validateSuggestion a été appelé avec babelio_publisher et babelio_url
    expect(livresAuteursService.validateSuggestion).toHaveBeenCalledTimes(1);

    const callArgs = livresAuteursService.validateSuggestion.mock.calls[0][0];

    // RED PHASE: Ces assertions vont échouer car confirmValidation ne transmet pas encore ces champs
    expect(callArgs).toHaveProperty('babelio_url');
    expect(callArgs.babelio_url).toBe('https://www.babelio.com/livres/Carrere-Kolkhoze/1839593');

    expect(callArgs).toHaveProperty('babelio_publisher');
    expect(callArgs.babelio_publisher).toBe('P.O.L.');
  });

  it('devrait transmettre babelio_publisher même si différent de editeur original', async () => {
    // Arrange: Livre où babelio_publisher corrige l'éditeur
    const enrichedBook = {
      cache_id: '68f52dd097c9ca8cb481ec35',
      auteur: 'Emmanuel Carrère',
      titre: 'Kolkhoze',
      editeur: 'POL',  // Transcription (potentiellement fausse)
      babelio_publisher: 'P.O.L.',  // Babelio (fiable)
      babelio_url: 'https://www.babelio.com/livres/Carrere-Kolkhoze/1839593'
    };

    wrapper.vm.currentBookToValidate = enrichedBook;
    wrapper.vm.validationForm = {
      author: 'Emmanuel Carrère',
      title: 'Kolkhoze',
      publisher: 'P.O.L.'  // Utilisateur garde la correction Babelio
    };

    // Act
    await wrapper.vm.confirmValidation();

    // Assert
    const callArgs = livresAuteursService.validateSuggestion.mock.calls[0][0];

    expect(callArgs.babelio_publisher).toBe('P.O.L.');
    expect(callArgs.editeur).toBe('POL');  // Éditeur original préservé
  });

  it('ne devrait PAS transmettre babelio_publisher si le livre n\'est pas enrichi', async () => {
    // Arrange: Livre sans enrichissement Babelio
    const nonEnrichedBook = {
      cache_id: '68f52dd097c9ca8cb481ec35',
      auteur: 'Natacha Appanah',
      titre: 'La Nuit au cœur',
      editeur: 'Gallimard'
      // Pas de babelio_url ni babelio_publisher
    };

    wrapper.vm.currentBookToValidate = nonEnrichedBook;
    wrapper.vm.validationForm = {
      author: 'Natacha Appanah',
      title: 'La Nuit au cœur',
      publisher: 'Gallimard'
    };

    // Act
    await wrapper.vm.confirmValidation();

    // Assert
    const callArgs = livresAuteursService.validateSuggestion.mock.calls[0][0];

    // Pas de babelio_publisher si le livre n'a pas été enrichi
    expect(callArgs.babelio_publisher).toBeUndefined();
    expect(callArgs.babelio_url).toBeUndefined();
  });

  it('devrait transmettre tous les champs requis en plus de babelio_publisher', async () => {
    // Arrange
    const enrichedBook = {
      cache_id: '68f52dd097c9ca8cb481ec35',
      auteur: 'Emmanuel Carrère',
      titre: 'Kolkhoze',
      editeur: 'POL',
      babelio_url: 'https://www.babelio.com/livres/Carrere-Kolkhoze/1839593',
      babelio_publisher: 'P.O.L.'
    };

    wrapper.vm.currentBookToValidate = enrichedBook;
    wrapper.vm.validationForm = {
      author: 'Emmanuel Carrère',
      title: 'Kolkhoze',
      publisher: 'P.O.L.'
    };

    // Act
    await wrapper.vm.confirmValidation();

    // Assert: Vérifier que tous les champs requis sont présents
    const callArgs = livresAuteursService.validateSuggestion.mock.calls[0][0];

    expect(callArgs).toMatchObject({
      cache_id: '68f52dd097c9ca8cb481ec35',
      episode_oid: '68bd9ed3582cf994fb66f1d6',
      avis_critique_id: '68bddf38d79eae6a485abdaf',
      auteur: 'Emmanuel Carrère',
      titre: 'Kolkhoze',
      editeur: 'POL',
      user_validated_author: 'Emmanuel Carrère',
      user_validated_title: 'Kolkhoze',
      user_validated_publisher: 'P.O.L.',
      babelio_url: 'https://www.babelio.com/livres/Carrere-Kolkhoze/1839593',
      babelio_publisher: 'P.O.L.'
    });
  });
});
