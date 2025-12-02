/**
 * Tests unitaires pour le composant BabelioLink
 *
 * Ce composant affiche un lien externe vers Babelio si l'URL est disponible
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { mount } from '@vue/test-utils';
import BabelioLink from '../../src/components/BabelioLink.vue';

describe('BabelioLink - Tests unitaires', () => {
  let wrapper;

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount();
    }
  });

  describe('Avec URL valide', () => {
    beforeEach(() => {
      wrapper = mount(BabelioLink, {
        props: {
          url: 'https://www.babelio.com/livres/Houellebecq-Les-particules-elementaires/1770',
          label: 'Voir sur Babelio'
        }
      });
    });

    it('affiche le lien externe', () => {
      const link = wrapper.find('a');
      expect(link.exists()).toBe(true);
    });

    it('utilise l\'URL fournie comme href', () => {
      const link = wrapper.find('a');
      expect(link.attributes('href')).toBe('https://www.babelio.com/livres/Houellebecq-Les-particules-elementaires/1770');
    });

    it('ouvre le lien dans un nouvel onglet', () => {
      const link = wrapper.find('a');
      expect(link.attributes('target')).toBe('_blank');
    });

    it('ajoute rel="noopener noreferrer" pour la sécurité', () => {
      const link = wrapper.find('a');
      expect(link.attributes('rel')).toBe('noopener noreferrer');
    });

    it('affiche le label fourni', () => {
      const link = wrapper.find('a');
      expect(link.text()).toContain('Voir sur Babelio');
    });

    it('affiche une icône de lien externe', () => {
      const link = wrapper.find('a');
      expect(link.html()).toContain('🔗');
    });
  });

  describe('Sans URL (null ou undefined)', () => {
    it('n\'affiche rien si url est null', () => {
      wrapper = mount(BabelioLink, {
        props: {
          url: null,
          label: 'Voir sur Babelio'
        }
      });

      const link = wrapper.find('a');
      expect(link.exists()).toBe(false);
    });

    it('n\'affiche rien si url est undefined', () => {
      wrapper = mount(BabelioLink, {
        props: {
          url: undefined,
          label: 'Voir sur Babelio'
        }
      });

      const link = wrapper.find('a');
      expect(link.exists()).toBe(false);
    });

    it('n\'affiche rien si url est une chaîne vide', () => {
      wrapper = mount(BabelioLink, {
        props: {
          url: '',
          label: 'Voir sur Babelio'
        }
      });

      const link = wrapper.find('a');
      expect(link.exists()).toBe(false);
    });
  });

  describe('Label par défaut', () => {
    it('utilise "Voir sur Babelio" si aucun label n\'est fourni', () => {
      wrapper = mount(BabelioLink, {
        props: {
          url: 'https://www.babelio.com/auteur/Michel-Houellebecq/2180'
        }
      });

      const link = wrapper.find('a');
      expect(link.text()).toContain('Voir sur Babelio');
    });
  });

  describe('Style et classes CSS', () => {
    beforeEach(() => {
      wrapper = mount(BabelioLink, {
        props: {
          url: 'https://www.babelio.com/livres/test/123'
        }
      });
    });

    it('applique la classe babelio-link au lien', () => {
      const link = wrapper.find('a');
      expect(link.classes()).toContain('babelio-link');
    });
  });
});
