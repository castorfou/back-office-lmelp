/**
 * Tests TDD pour Issue #89 - Lien vers la page RadioFrance de l'épisode
 *
 * Fonctionnalités testées:
 * 1. Auto-fetch de l'URL RadioFrance quand épisode sélectionné
 * 2. Affichage du logo cliquable dans les détails de l'épisode
 * 3. Gestion des cas d'erreur (pas d'URL trouvée, erreur réseau)
 */

import { mount, flushPromises } from '@vue/test-utils';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { createRouter, createWebHistory } from 'vue-router';
import LivresAuteurs from '../../src/views/LivresAuteurs.vue';
import * as api from '../../src/services/api.js';

describe('LivresAuteurs - Episode RadioFrance Page URL (Issue #89)', () => {
  let wrapper;
  let router;

  beforeEach(() => {
    // Reset all mocks before each test
    vi.resetAllMocks();

    // Créer un router de test
    router = createRouter({
      history: createWebHistory(),
      routes: [
        { path: '/', component: { template: '<div>Home</div>' } },
        { path: '/livres-auteurs', component: LivresAuteurs }
      ]
    });

    // Mock minimal pour éviter les appels réseau
    vi.spyOn(api.livresAuteursService, 'getEpisodesWithReviews').mockResolvedValue([
      {
        id: 'episode-1',
        titre: 'Test Episode 1',
        date: '2025-10-01T00:00:00Z',
        avis_critiques_count: 5
      },
      {
        id: 'episode-2',
        titre: 'Test Episode 2',
        date: '2025-10-02T00:00:00Z',
        avis_critiques_count: 3
      }
    ]);

    vi.spyOn(api.livresAuteursService, 'getLivresAuteurs').mockResolvedValue([]);
  });

  describe('Auto-fetch de l\'URL RadioFrance', () => {
    it('RED: devrait appeler fetchEpisodePageUrl quand épisode sélectionné sans URL', async () => {
      // Arrange: Episode sans episode_page_url
      const episodeWithoutUrl = {
        id: 'episode-1',
        titre: 'Test Episode',
        description: 'Test description'
        // Pas de episode_page_url
      };

      vi.spyOn(api.episodeService, 'getEpisodeById').mockResolvedValue(episodeWithoutUrl);
      const fetchSpy = vi.spyOn(api.episodeService, 'fetchEpisodePageUrl').mockResolvedValue({
        success: true,
        episode_page_url: 'https://www.radiofrance.fr/franceinter/podcasts/le-masque-et-la-plume/episode-test'
      });

      wrapper = mount(LivresAuteurs, {
        global: {
          plugins: [router],
          stubs: ['router-link']
        }
      });

      await flushPromises();

      // Act: Sélectionner un épisode
      wrapper.vm.selectedEpisodeId = 'episode-1';
      await wrapper.vm.onEpisodeChange();
      await flushPromises();

      // Assert: fetchEpisodePageUrl devrait être appelé
      expect(fetchSpy).toHaveBeenCalledWith('episode-1');
    });

    it('GREEN: devrait mettre à jour selectedEpisodeFull avec l\'URL récupérée', async () => {
      // Arrange
      const episodeWithoutUrl = {
        id: 'episode-1',
        titre: 'Test Episode',
        description: 'Test description'
      };

      const fetchedUrl = 'https://www.radiofrance.fr/franceinter/podcasts/le-masque-et-la-plume/episode-test';

      vi.spyOn(api.episodeService, 'getEpisodeById').mockResolvedValue(episodeWithoutUrl);
      vi.spyOn(api.episodeService, 'fetchEpisodePageUrl').mockResolvedValue({
        success: true,
        episode_page_url: fetchedUrl
      });

      wrapper = mount(LivresAuteurs, {
        global: {
          plugins: [router],
          stubs: ['router-link']
        }
      });

      await flushPromises();

      // Act
      wrapper.vm.selectedEpisodeId = 'episode-1';
      await wrapper.vm.onEpisodeChange();
      await flushPromises();

      // Assert: selectedEpisodeFull devrait contenir l'URL
      expect(wrapper.vm.selectedEpisodeFull.episode_page_url).toBe(fetchedUrl);
    });

    it('devrait NE PAS appeler fetchEpisodePageUrl si l\'URL existe déjà', async () => {
      // Arrange: Episode avec URL déjà présente
      const episodeWithUrl = {
        id: 'episode-1',
        titre: 'Test Episode',
        description: 'Test description',
        episode_page_url: 'https://www.radiofrance.fr/franceinter/podcasts/le-masque-et-la-plume/existing'
      };

      vi.spyOn(api.episodeService, 'getEpisodeById').mockResolvedValue(episodeWithUrl);
      const fetchSpy = vi.spyOn(api.episodeService, 'fetchEpisodePageUrl');

      wrapper = mount(LivresAuteurs, {
        global: {
          plugins: [router],
          stubs: ['router-link']
        }
      });

      await flushPromises();

      // Act
      wrapper.vm.selectedEpisodeId = 'episode-1';
      await wrapper.vm.onEpisodeChange();
      await flushPromises();

      // Assert: fetchEpisodePageUrl NE devrait PAS être appelé
      expect(fetchSpy).not.toHaveBeenCalled();
    });

    it('devrait gérer les erreurs de fetch sans bloquer l\'UI', async () => {
      // Arrange: Fetch échoue (épisode non trouvé sur RadioFrance)
      const episodeWithoutUrl = {
        id: 'episode-1',
        titre: 'Episode inexistant',
        description: 'Test description'
      };

      vi.spyOn(api.episodeService, 'getEpisodeById').mockResolvedValue(episodeWithoutUrl);
      vi.spyOn(api.episodeService, 'fetchEpisodePageUrl').mockRejectedValue(new Error('404 Not Found'));

      const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

      wrapper = mount(LivresAuteurs, {
        global: {
          plugins: [router],
          stubs: ['router-link']
        }
      });

      await flushPromises();

      // Act
      wrapper.vm.selectedEpisodeId = 'episode-1';
      await wrapper.vm.onEpisodeChange();
      await flushPromises();

      // Assert: L'erreur devrait être loggée mais ne pas crasher
      expect(consoleWarnSpy).toHaveBeenCalledWith(
        expect.stringContaining('Impossible de récupérer l\'URL de la page RadioFrance'),
        expect.any(String)
      );

      // L'UI devrait rester fonctionnelle (selectedEpisodeFull existe)
      expect(wrapper.vm.selectedEpisodeFull).toBeTruthy();
      expect(wrapper.vm.selectedEpisodeFull.episode_page_url).toBeUndefined();

      consoleWarnSpy.mockRestore();
    });
  });

  describe('Affichage du logo RadioFrance', () => {
    it('RED: devrait afficher le logo quand episode_page_url est présent', async () => {
      // Arrange
      const episodeWithUrl = {
        id: 'episode-1',
        titre: 'Test Episode',
        description: 'Test description',
        episode_page_url: 'https://www.radiofrance.fr/franceinter/podcasts/le-masque-et-la-plume/test'
      };

      vi.spyOn(api.episodeService, 'getEpisodeById').mockResolvedValue(episodeWithUrl);

      wrapper = mount(LivresAuteurs, {
        global: {
          plugins: [router],
          stubs: ['router-link']
        }
      });

      await flushPromises();

      wrapper.vm.selectedEpisodeId = 'episode-1';
      await wrapper.vm.onEpisodeChange();
      await flushPromises();

      // Ouvrir l'accordéon des détails
      wrapper.vm.showEpisodeDetails = true;
      await wrapper.vm.$nextTick();

      // Assert: Le logo devrait être présent
      const logoLink = wrapper.find('.episode-logo-link');
      expect(logoLink.exists()).toBe(true);
      expect(logoLink.attributes('href')).toBe(episodeWithUrl.episode_page_url);
      expect(logoLink.attributes('target')).toBe('_blank');
      expect(logoLink.attributes('rel')).toBe('noopener noreferrer');

      const logoImg = logoLink.find('.episode-logo');
      expect(logoImg.exists()).toBe(true);
      expect(logoImg.attributes('alt')).toBe('Logo Le Masque et la Plume');
    });

    it('devrait NE PAS afficher le logo quand episode_page_url est absent', async () => {
      // Arrange
      const episodeWithoutUrl = {
        id: 'episode-1',
        titre: 'Test Episode',
        description: 'Test description'
        // Pas de episode_page_url
      };

      vi.spyOn(api.episodeService, 'getEpisodeById').mockResolvedValue(episodeWithoutUrl);
      vi.spyOn(api.episodeService, 'fetchEpisodePageUrl').mockResolvedValue({
        success: false  // Fetch échoué
      });

      wrapper = mount(LivresAuteurs, {
        global: {
          plugins: [router],
          stubs: ['router-link']
        }
      });

      await flushPromises();

      wrapper.vm.selectedEpisodeId = 'episode-1';
      await wrapper.vm.onEpisodeChange();
      await flushPromises();

      wrapper.vm.showEpisodeDetails = true;
      await wrapper.vm.$nextTick();

      // Assert: Le logo NE devrait PAS être présent
      const logoLink = wrapper.find('.episode-logo-link');
      expect(logoLink.exists()).toBe(false);
    });

    it('GREEN: devrait afficher le logo après auto-fetch réussi', async () => {
      // Arrange: Episode sans URL, puis fetch réussi
      const episodeWithoutUrl = {
        id: 'episode-1',
        titre: 'Test Episode',
        description: 'Test description'
      };

      const fetchedUrl = 'https://www.radiofrance.fr/franceinter/podcasts/le-masque-et-la-plume/test-auto';

      vi.spyOn(api.episodeService, 'getEpisodeById').mockResolvedValue(episodeWithoutUrl);
      vi.spyOn(api.episodeService, 'fetchEpisodePageUrl').mockResolvedValue({
        success: true,
        episode_page_url: fetchedUrl
      });

      wrapper = mount(LivresAuteurs, {
        global: {
          plugins: [router],
          stubs: ['router-link']
        }
      });

      await flushPromises();

      // Act: Sélectionner épisode
      wrapper.vm.selectedEpisodeId = 'episode-1';
      await wrapper.vm.onEpisodeChange();
      await flushPromises();

      // Ouvrir l'accordéon
      wrapper.vm.showEpisodeDetails = true;
      await wrapper.vm.$nextTick();

      // Assert: Le logo devrait apparaître avec l'URL auto-fetchée
      const logoLink = wrapper.find('.episode-logo-link');
      expect(logoLink.exists()).toBe(true);
      expect(logoLink.attributes('href')).toBe(fetchedUrl);
    });
  });
});
