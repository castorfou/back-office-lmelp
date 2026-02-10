/**
 * Tests pour le composant AvisTable - enrichissement éditeur.
 *
 * Vérifie que l'éditeur officiel MongoDB est utilisé en priorité
 * sur l'éditeur extrait par le LLM (Issue #208).
 */
import { describe, it, expect } from 'vitest';
import { mount } from '@vue/test-utils';
import AvisTable from '@/components/AvisTable.vue';

describe('AvisTable - editeur enrichment', () => {
  it('should use editeur officiel over editeur_extrait when available', () => {
    const wrapper = mount(AvisTable, {
      props: {
        avis: [
          {
            id: '1',
            section: 'programme',
            livre_oid: 'livre123',
            livre_titre: 'Kolkhoze',
            livre_titre_extrait: 'Kolkhoze',
            auteur_nom: 'Emmanuel Carrère',
            auteur_nom_extrait: 'Emmanuel Carrère',
            editeur: 'P.O.L.',
            editeur_extrait: 'POL',
            critique_nom_extrait: 'Laurent Chalumeau',
            commentaire: 'Virtuose',
            note: 9,
          },
        ],
      },
      global: {
        stubs: {
          'router-link': {
            template: '<a><slot /></a>',
          },
        },
      },
    });

    // Vérifier que l'éditeur officiel est affiché, pas l'extrait LLM
    const editeurCell = wrapper.find('.editeur-cell');
    expect(editeurCell.text()).toBe('P.O.L.');
  });

  it('should fallback to editeur_extrait when editeur officiel is not available', () => {
    const wrapper = mount(AvisTable, {
      props: {
        avis: [
          {
            id: '2',
            section: 'programme',
            livre_oid: null,
            livre_titre_extrait: 'Un Livre',
            auteur_nom_extrait: 'Un Auteur',
            editeur_extrait: 'Gallimard',
            critique_nom_extrait: 'Un Critique',
            commentaire: 'Bien',
            note: 7,
          },
        ],
      },
      global: {
        stubs: {
          'router-link': {
            template: '<a><slot /></a>',
          },
        },
      },
    });

    // Pas d'éditeur officiel -> fallback sur editeur_extrait
    const editeurCell = wrapper.find('.editeur-cell');
    expect(editeurCell.text()).toBe('Gallimard');
  });
});
