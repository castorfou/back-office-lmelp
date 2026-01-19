import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import { createRouter, createMemoryHistory } from 'vue-router';
import AvisTable from '../AvisTable.vue';

describe('AvisTable.vue', () => {
  let router;

  const createWrapper = (props = {}) => {
    router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/', component: { template: '<div>Home</div>' } },
        { path: '/livre/:id', component: { template: '<div>Livre</div>' } },
        { path: '/critique/:id', component: { template: '<div>Critique</div>' } },
        { path: '/auteur/:id', component: { template: '<div>Auteur</div>' } },
      ],
    });

    return mount(AvisTable, {
      global: { plugins: [router] },
      props: {
        avis: [],
        ...props,
      },
    });
  };

  describe('Groupement des livres au programme', () => {
    it('should group avis by livre_oid when available (same book, different extracted titles)', async () => {
      /**
       * TDD RED: Ce test vérifie que les avis avec le même livre_oid sont groupés ensemble,
       * même si les titres extraits sont différents (ex: "4 jours" vs "Quatre jours").
       *
       * Scénario réel: L'épisode du 7 décembre 2025 contient le livre "4 jours sans ma mère"
       * mais le summary markdown utilise parfois "Quatre jours sans ma mère".
       * Les deux variantes ont été matchées en Phase 1 au même livre MongoDB.
       */
      const mockAvis = [
        {
          id: '1',
          section: 'programme',
          livre_oid: 'livre123',
          livre_titre_extrait: '4 jours sans ma mère',
          livre_titre: '4 jours sans ma mère',
          auteur_nom_extrait: 'Ramsès Kefi',
          auteur_oid: 'auteur123',
          editeur_extrait: 'Seuil',
          critique_nom_extrait: 'Bernard Poirette',
          critique_oid: 'critique1',
          commentaire: 'Enthousiasmé, bonheur indicible',
          note: 9,
        },
        {
          id: '2',
          section: 'programme',
          livre_oid: 'livre123', // Même livre_oid!
          livre_titre_extrait: 'Quatre jours sans ma mère', // Titre différent
          livre_titre: '4 jours sans ma mère',
          auteur_nom_extrait: 'Ramsès Kefi',
          auteur_oid: 'auteur123',
          editeur_extrait: 'Seuil',
          critique_nom_extrait: 'Patricia Martin',
          critique_oid: 'critique2',
          commentaire: 'Très beau roman',
          note: 8,
        },
        {
          id: '3',
          section: 'programme',
          livre_oid: 'livre456', // Autre livre
          livre_titre_extrait: 'Autre livre',
          livre_titre: 'Autre livre',
          auteur_nom_extrait: 'Autre Auteur',
          auteur_oid: 'auteur456',
          editeur_extrait: 'Gallimard',
          critique_nom_extrait: 'Bernard Poirette',
          critique_oid: 'critique1',
          commentaire: 'Très bien',
          note: 7,
        },
      ];

      const wrapper = createWrapper({ avis: mockAvis });
      await wrapper.vm.$nextTick();

      // Vérifier qu'on a bien 2 livres (pas 3!)
      const livresRows = wrapper.findAll('tbody tr');
      expect(livresRows.length).toBe(2);

      // Le premier livre devrait avoir 2 avis regroupés
      const firstLivreAvis = wrapper.findAll('tbody tr').at(0).findAll('.avis-item');
      expect(firstLivreAvis.length).toBe(2);
    });

    it('should use titre_extrait as key when livre_oid is null (unresolved)', async () => {
      /**
       * TDD: Les avis non résolus (livre_oid = null) doivent être groupés par titre.
       */
      const mockAvis = [
        {
          id: '1',
          section: 'programme',
          livre_oid: null, // Non résolu
          livre_titre_extrait: 'Livre Inconnu',
          auteur_nom_extrait: 'Auteur Inconnu',
          editeur_extrait: 'Éditeur',
          critique_nom_extrait: 'Critique 1',
          critique_oid: 'critique1',
          commentaire: 'Avis 1',
          note: 7,
        },
        {
          id: '2',
          section: 'programme',
          livre_oid: null, // Non résolu aussi
          livre_titre_extrait: 'Livre Inconnu', // Même titre
          auteur_nom_extrait: 'Auteur Inconnu',
          editeur_extrait: 'Éditeur',
          critique_nom_extrait: 'Critique 2',
          critique_oid: 'critique2',
          commentaire: 'Avis 2',
          note: 8,
        },
      ];

      const wrapper = createWrapper({ avis: mockAvis });
      await wrapper.vm.$nextTick();

      // Devrait y avoir 1 seul livre (groupé par titre)
      const livresRows = wrapper.findAll('tbody tr');
      expect(livresRows.length).toBe(1);

      // Avec 2 avis
      const avisItems = wrapper.findAll('.avis-item');
      expect(avisItems.length).toBe(2);
    });

    it('should display official title when available instead of extracted title', async () => {
      /**
       * TDD: Quand livre_titre est disponible, l'afficher à la place de livre_titre_extrait.
       */
      const mockAvis = [
        {
          id: '1',
          section: 'programme',
          livre_oid: 'livre123',
          livre_titre_extrait: 'Quatre jours sans ma mère', // Titre extrait
          livre_titre: '4 jours sans ma mère', // Titre officiel MongoDB
          auteur_nom_extrait: 'Ramsès Kefi',
          auteur_oid: 'auteur123',
          editeur_extrait: 'Seuil',
          critique_nom_extrait: 'Bernard Poirette',
          critique_oid: 'critique1',
          commentaire: 'Très bien',
          note: 9,
        },
      ];

      const wrapper = createWrapper({ avis: mockAvis });
      await wrapper.vm.$nextTick();

      // Vérifier que le titre officiel est affiché
      const titreCell = wrapper.find('.titre-cell');
      expect(titreCell.text()).toContain('4 jours sans ma mère');
      expect(titreCell.text()).not.toContain('Quatre jours');
    });
  });
});
