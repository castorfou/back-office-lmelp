/**
 * BiblioValidationCell piloté par la validation Babelio du tableau (Issue #352).
 */
import { describe, it, expect, vi, afterEach } from 'vitest';
import { mount } from '@vue/test-utils';
import BiblioValidationCell from '../../src/components/BiblioValidationCell.vue';

vi.mock('../../src/services/BiblioValidationService.js', () => ({
  BiblioValidationService: vi.fn().mockImplementation(() => ({ validateBiblio: vi.fn() })),
}));

const props = { author: 'Valérie Manteau', title: 'Le Sillon', publisher: 'Le Tripode' };

describe('BiblioValidationCell - statuts transmis par le tableau (Issue #352)', () => {
  let wrapper;
  afterEach(() => wrapper?.unmount());

  it('affiche « Bloqué (403) » pour un statut transitoire blocked_403', async () => {
    wrapper = mount(BiblioValidationCell, { props: { ...props, storedStatus: 'blocked_403' } });
    await wrapper.vm.$nextTick();
    expect(wrapper.find('[data-testid="validation-blocked-403"]').exists()).toBe(true);
  });

  it('affiche « Erreur » pour un statut transitoire error', async () => {
    wrapper = mount(BiblioValidationCell, { props: { ...props, storedStatus: 'error' } });
    await wrapper.vm.$nextTick();
    expect(wrapper.find('[data-testid="validation-error"]').exists()).toBe(true);
  });

  it('revient à « À valider » quand le statut est effacé', async () => {
    wrapper = mount(BiblioValidationCell, { props: { ...props, storedStatus: 'blocked_403' } });
    await wrapper.setProps({ storedStatus: null });
    expect(wrapper.find('[data-testid="validation-pending"]').exists()).toBe(true);
  });

  it('affiche « en cours » quand le tableau valide ce livre', () => {
    wrapper = mount(BiblioValidationCell, { props: { ...props, validating: true } });
    expect(wrapper.find('[data-testid="validation-loading"]').exists()).toBe(true);
  });
});
