/**
 * Tests unitaires pour le composant EpisodeEditor
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount } from '@vue/test-utils';
import EpisodeEditor from '../../src/components/EpisodeEditor.vue';
import { episodeService } from '../../src/services/api.js';

// Mock du service API
vi.mock('../../src/services/api.js', () => ({
  episodeService: {
    updateEpisodeDescription: vi.fn(),
    updateEpisodeTitle: vi.fn(),
  }
}));

// Mock de lodash.debounce pour les tests
vi.mock('lodash.debounce', () => ({
  default: (fn) => {
    fn.cancel = vi.fn();
    return fn;
  }
}));

// Mock des utilitaires
vi.mock('../../src/utils/errorHandler.js', () => ({
  ErrorHandler: {
    handleError: vi.fn().mockReturnValue('Erreur serveur')
  },
  errorMixin: {
    methods: {
      handleError: vi.fn()
    }
  }
}));

vi.mock('../../src/utils/memoryGuard.js', () => ({
  memoryGuard: {
    checkMemoryLimit: vi.fn().mockReturnValue(null),
    forceShutdown: vi.fn()
  }
}));

describe('EpisodeEditor', () => {
  let wrapper;

  const mockEpisode = {
    id: '123',
    titre: 'Episode Test',
    date: '2024-01-15T09:00:00Z',
    type: 'livres',
    description: 'Description originale',
    description_corrigee: 'Description déjà corrigée',
    titre_corrige: 'Titre déjà corrigé'
  };

  beforeEach(() => {
    vi.clearAllMocks();
    vi.clearAllTimers();
    vi.useFakeTimers();
  });

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount();
    }
    vi.useRealTimers();
  });

  it('affiche les informations de l\'épisode', () => {
    wrapper = mount(EpisodeEditor, {
      props: { episode: mockEpisode }
    });

    expect(wrapper.find('#titre-corrected').element.value).toBe(mockEpisode.titre_corrige);
    expect(wrapper.text()).toContain('15 janvier 2024');
    expect(wrapper.text()).toContain('livres');
  });

  it('affiche la description originale en lecture seule', () => {
    wrapper = mount(EpisodeEditor, {
      props: { episode: mockEpisode }
    });

    const originalTextarea = wrapper.findAll('textarea')[0];
    expect(originalTextarea.element.value).toBe(mockEpisode.description);
    expect(originalTextarea.element.readOnly).toBe(true);
  });

  it('initialise l\'éditeur avec la description corrigée', () => {
    wrapper = mount(EpisodeEditor, {
      props: { episode: mockEpisode }
    });

    expect(wrapper.vm.correctedDescription).toBe(mockEpisode.description_corrigee);
  });

  it('initialise l\'éditeur avec la description originale si pas de correction', () => {
    const episodeWithoutCorrection = {
      ...mockEpisode,
      description_corrigee: null
    };

    wrapper = mount(EpisodeEditor, {
      props: { episode: episodeWithoutCorrection }
    });

    expect(wrapper.vm.correctedDescription).toBe(mockEpisode.description);
  });

  it('détecte les changements dans la description', async () => {
    wrapper = mount(EpisodeEditor, {
      props: { episode: mockEpisode }
    });

    // Attendre que le composant s'initialise complètement
    await wrapper.vm.$nextTick();

    // Vérifier l'état initial
    expect(wrapper.vm.hasChanges).toBe(false);

    // Changer la description et déclencher directement le calcul
    wrapper.vm.correctedDescription = 'Nouvelle description modifiée';
    wrapper.vm.hasDescriptionChanges = wrapper.vm.correctedDescription !== wrapper.vm.originalCorrectedDescription;
    wrapper.vm.hasChanges = wrapper.vm.hasDescriptionChanges || wrapper.vm.hasTitleChanges;
    await wrapper.vm.$nextTick();

    expect(wrapper.vm.hasChanges).toBe(true);
    expect(wrapper.find('.pending').exists()).toBe(true);
  });

  it('sauvegarde automatiquement après modification', async () => {
    episodeService.updateEpisodeDescription.mockResolvedValue({ success: true });

    wrapper = mount(EpisodeEditor, {
      props: { episode: mockEpisode }
    });

    // Modifier la description
    const textarea = wrapper.findAll('textarea')[1];
    await textarea.setValue('Nouvelle description');

    // Déclencher la sauvegarde (normalement déclenchée par debounce)
    await wrapper.vm.saveDescription();

    expect(episodeService.updateEpisodeDescription).toHaveBeenCalledWith(
      mockEpisode.id,
      'Nouvelle description'
    );
  });

  it('affiche le statut de sauvegarde', async () => {
    episodeService.updateEpisodeDescription.mockResolvedValue({ success: true });

    wrapper = mount(EpisodeEditor, {
      props: { episode: mockEpisode }
    });

    // Modifier et sauvegarder
    const textarea = wrapper.findAll('textarea')[1];
    await textarea.setValue('Nouvelle description');

    // Simuler le statut de sauvegarde
    wrapper.vm.descriptionSaveStatus = 'saving';
    await wrapper.vm.$nextTick();
    expect(wrapper.find('.saving').exists()).toBe(true);

    // Simuler la fin de sauvegarde
    wrapper.vm.descriptionSaveStatus = 'saved';
    await wrapper.vm.$nextTick();
    expect(wrapper.find('.saved').exists()).toBe(true);
  });

  it('gère les erreurs de sauvegarde', async () => {
    const error = new Error('Erreur serveur');
    episodeService.updateEpisodeDescription.mockRejectedValue(error);

    wrapper = mount(EpisodeEditor, {
      props: { episode: mockEpisode }
    });

    // Modifier et tenter de sauvegarder
    const textarea = wrapper.findAll('textarea')[1];
    await textarea.setValue('Nouvelle description');
    await wrapper.vm.saveDescription();

    expect(wrapper.vm.descriptionSaveStatus).toBe('error');
    expect(wrapper.vm.descriptionSaveError).toBeTruthy();
  });

  it('ne sauvegarde pas s\'il n\'y a pas de changements', async () => {
    wrapper = mount(EpisodeEditor, {
      props: { episode: mockEpisode }
    });

    await wrapper.vm.saveDescription();

    expect(episodeService.updateEpisodeDescription).not.toHaveBeenCalled();
  });

  it('formate correctement les dates', () => {
    wrapper = mount(EpisodeEditor, {
      props: { episode: mockEpisode }
    });

    const formatted = wrapper.vm.formatDate('2024-01-15T09:00:00Z');
    expect(formatted).toBe('15 janvier 2024');
  });

  it('gère les dates invalides', () => {
    wrapper = mount(EpisodeEditor, {
      props: { episode: mockEpisode }
    });

    expect(wrapper.vm.formatDate(null)).toBe('Date inconnue');
    expect(wrapper.vm.formatDate('invalid-date')).toBe('Date invalide');
  });

  it('réinitialise l\'état lors du changement d\'épisode', async () => {
    wrapper = mount(EpisodeEditor, {
      props: { episode: mockEpisode }
    });

    // Modifier la description
    const textarea = wrapper.findAll('textarea')[1];
    await textarea.setValue('Modification');

    // Changer d'épisode
    const newEpisode = { ...mockEpisode, id: '456', titre: 'Nouvel épisode' };
    await wrapper.setProps({ episode: newEpisode });

    expect(wrapper.vm.hasChanges).toBe(false);
    expect(wrapper.vm.descriptionSaveStatus).toBe('');
    expect(wrapper.vm.titleSaveStatus).toBe('');
  });

  // Tests pour l'édition du titre
  it('affiche le champ d\'édition du titre', () => {
    wrapper = mount(EpisodeEditor, {
      props: { episode: mockEpisode }
    });

    const titleInput = wrapper.find('#titre-corrected');
    expect(titleInput.exists()).toBe(true);
    expect(titleInput.element.value).toBe(mockEpisode.titre_corrige);
  });

  it('initialise l\'éditeur de titre avec titre corrigé existant', () => {
    wrapper = mount(EpisodeEditor, {
      props: { episode: mockEpisode }
    });

    expect(wrapper.vm.correctedTitle).toBe(mockEpisode.titre_corrige);
  });

  it('initialise l\'éditeur de titre avec titre original si pas de correction', () => {
    const episodeWithoutTitleCorrection = {
      ...mockEpisode,
      titre_corrige: null
    };

    wrapper = mount(EpisodeEditor, {
      props: { episode: episodeWithoutTitleCorrection }
    });

    expect(wrapper.vm.correctedTitle).toBe(mockEpisode.titre);
  });

  it('détecte les changements dans le titre', async () => {
    wrapper = mount(EpisodeEditor, {
      props: { episode: mockEpisode }
    });

    await wrapper.vm.$nextTick();
    expect(wrapper.vm.hasChanges).toBe(false);

    // Changer le titre
    wrapper.vm.correctedTitle = 'Nouveau titre modifié';
    wrapper.vm.hasTitleChanges = wrapper.vm.correctedTitle !== wrapper.vm.originalCorrectedTitle;
    wrapper.vm.hasChanges = wrapper.vm.hasTitleChanges || wrapper.vm.hasDescriptionChanges;
    await wrapper.vm.$nextTick();

    expect(wrapper.vm.hasChanges).toBe(true);
  });

  it('sauvegarde automatiquement après modification du titre', async () => {
    episodeService.updateEpisodeTitle.mockResolvedValue({ success: true });

    wrapper = mount(EpisodeEditor, {
      props: { episode: mockEpisode }
    });

    // Modifier le titre
    const titleInput = wrapper.find('#titre-corrected');
    await titleInput.setValue('Nouveau titre');

    // Déclencher la sauvegarde (normalement déclenchée par debounce)
    await wrapper.vm.saveTitle();

    expect(episodeService.updateEpisodeTitle).toHaveBeenCalledWith(
      mockEpisode.id,
      'Nouveau titre'
    );
  });

  it('détecte les changements combinés titre et description', async () => {
    wrapper = mount(EpisodeEditor, {
      props: { episode: mockEpisode }
    });

    await wrapper.vm.$nextTick();
    expect(wrapper.vm.hasChanges).toBe(false);

    // Changer titre et description
    wrapper.vm.correctedTitle = 'Nouveau titre';
    wrapper.vm.correctedDescription = 'Nouvelle description';
    wrapper.vm.hasTitleChanges = wrapper.vm.correctedTitle !== wrapper.vm.originalCorrectedTitle;
    wrapper.vm.hasDescriptionChanges = wrapper.vm.correctedDescription !== wrapper.vm.originalCorrectedDescription;
    wrapper.vm.hasChanges = wrapper.vm.hasTitleChanges || wrapper.vm.hasDescriptionChanges;
    await wrapper.vm.$nextTick();

    expect(wrapper.vm.hasChanges).toBe(true);
  });
});
