/**
 * Page « Configuration mobile » (Issue #427, prototype #418) : QR code de la
 * clé d'écoute, saisie manuelle, invalidation avec confirmation.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import ConfigurationMobile from '../ConfigurationMobile.vue';
import { cleEcouteService } from '@/services/api';

vi.mock('@/services/api', () => ({
  cleEcouteService: { lire: vi.fn(), invalider: vi.fn() },
}));

// forme de GET /api/cle-ecoute
const CLE = {
  cle: 'Qm3xYc9vT2pL8sWk4rN7aE1uZ6hJ0fDb', // pragma: allowlist secret
  creee_le: '2026-11-28T15:40:12.345000+00:00',
  changements: [],
};

const lienDe = (cle) =>
  `lmelp://ecoute?base=${encodeURIComponent('https://lmelp-streaming.ascot63.synology.me')}&cle=${encodeURIComponent(cle)}`;

function monter() {
  return mount(ConfigurationMobile, {
    global: {
      stubs: { Navigation: { template: '<div />' } },
      mocks: { $router: { back: vi.fn(), push: vi.fn() } },
    },
  });
}

describe('ConfigurationMobile', () => {
  const location = window.location;

  beforeEach(() => {
    vi.resetAllMocks();
    cleEcouteService.lire.mockResolvedValue(CLE);
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: { ...location, hostname: 'lmelp.ascot63.synology.me' },
    });
  });

  afterEach(() => {
    Object.defineProperty(window, 'location', { configurable: true, value: location });
    vi.restoreAllMocks();
  });

  it('affiche le QR code du lien lmelp://ecoute avec l\'adresse de lmelp-streaming', async () => {
    const page = monter();
    await flushPromises();

    expect(page.vm.lien).toBe(lienDe(CLE.cle));
    // la génération du QR code est asynchrone
    await vi.waitFor(() => expect(page.find('img.qr').exists()).toBe(true));
    expect(page.find('img.qr').attributes('src')).toMatch(/^data:image\/png;base64,/);
    expect(page.text()).toContain('https://lmelp-streaming.ascot63.synology.me');
  });

  it('masque la clé et la montre sur demande', async () => {
    const page = monter();
    await flushPromises();

    expect(page.text()).not.toContain(CLE.cle);
    await page.find('[data-test="voir-cle"]').trigger('click');
    expect(page.text()).toContain(CLE.cle);
  });

  it('copie le lien', async () => {
    const writeText = vi.fn().mockResolvedValue();
    Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText } });
    const page = monter();
    await flushPromises();

    await page.find('[data-test="copier-lien"]').trigger('click');
    await flushPromises();

    expect(writeText).toHaveBeenCalledWith(lienDe(CLE.cle));
  });

  it("dit depuis quand la clé est en service et combien de fois elle a changé", async () => {
    cleEcouteService.lire.mockResolvedValue({
      ...CLE,
      creee_le: '2026-11-20T10:00:00',
      changements: ['2026-11-12T09:00:00', '2026-11-20T10:00:00'],
    });
    const page = monter();
    await flushPromises();

    const note = page.find('[data-test="historique"]').text();
    expect(note).toContain('Clé en service depuis le 20 novembre 2026');
    expect(note).toContain('changée 2 fois, la dernière le 20 novembre 2026');
  });

  it("invalide la clé après confirmation et affiche le nouveau QR code", async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    const nouvelle = { cle: 'nouvelle-cle-0123456789abcdef', creee_le: '2026-11-28T16:00:00', changements: ['2026-11-28T16:00:00'] };
    cleEcouteService.invalider.mockResolvedValue(nouvelle);
    const page = monter();
    await flushPromises();

    await page.find('[data-test="invalider"]').trigger('click');
    await flushPromises();

    expect(cleEcouteService.invalider).toHaveBeenCalled();
    expect(page.vm.lien).toBe(lienDe(nouvelle.cle));
    expect(page.text()).toContain("L'ancienne est refusée");
  });

  it("n'invalide rien sans confirmation", async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(false);
    const page = monter();
    await flushPromises();

    await page.find('[data-test="invalider"]').trigger('click');

    expect(cleEcouteService.invalider).not.toHaveBeenCalled();
  });

  it("n'affiche pas de QR code quand l'adresse de lmelp-streaming ne se déduit pas", async () => {
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: { ...location, hostname: 'localhost' },
    });
    const page = monter();
    await flushPromises();

    expect(page.find('img.qr').exists()).toBe(false);
    expect(page.find('[data-test="sans-adresse"]').text()).toContain('lmelp.');
  });

  it('dit pourquoi la clé ne se charge pas', async () => {
    cleEcouteService.lire.mockRejectedValue(new Error('Erreur réseau'));
    const page = monter();
    await flushPromises();

    expect(page.text()).toContain('Erreur réseau');
  });
});
