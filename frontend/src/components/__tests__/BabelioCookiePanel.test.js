import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import axios from 'axios';
import BabelioCookiePanel from '../BabelioCookiePanel.vue';

vi.mock('axios');

const badgeText = (wrapper) => wrapper.find('[data-test="cookie-badge"]').text();

describe('BabelioCookiePanel', () => {
  let wrapper;

  beforeEach(() => {
    vi.resetAllMocks();
    axios.post.mockResolvedValue({ data: { ok: true } });
    axios.delete.mockResolvedValue({ data: { ok: true } });
  });

  afterEach(() => {
    if (wrapper) wrapper.unmount();
    wrapper = null;
    vi.useRealTimers();
  });

  it('affiche « non configuré » tant que le statut serveur est inconnu', () => {
    wrapper = mount(BabelioCookiePanel, { props: { status: null } });
    expect(badgeText(wrapper)).toContain('non configuré');
  });

  it('bascule en « périmé » à l\'échéance du cookie serveur, sans nouveau statut', async () => {
    vi.useFakeTimers();
    wrapper = mount(BabelioCookiePanel, {
      props: { status: { cookie_active: true, cookie_age_sec: 290, cookie_max_age_sec: 300, cookie_expired: false } },
    });
    expect(badgeText(wrapper)).toContain('Actif côté serveur');

    vi.advanceTimersByTime(10_000);
    await wrapper.vm.$nextTick();
    expect(badgeText(wrapper)).toContain('périmé');
  });

  it('un nouveau statut frais repart d\'un badge « Actif »', async () => {
    wrapper = mount(BabelioCookiePanel, {
      props: { status: { cookie_active: true, cookie_age_sec: 900, cookie_max_age_sec: 300, cookie_expired: true } },
    });
    expect(badgeText(wrapper)).toContain('périmé');

    await wrapper.setProps({ status: { cookie_active: true, cookie_age_sec: 0, cookie_max_age_sec: 300, cookie_expired: false } });
    expect(badgeText(wrapper)).toContain('Actif côté serveur');
  });

  it('Enregistrer envoie le cookie collé, vide le champ et émet « saved »', async () => {
    wrapper = mount(BabelioCookiePanel, { props: { status: { cookie_active: false } } });
    await wrapper.find('textarea').setValue('  jstsToken=fresh; p=FR  ');
    await wrapper.find('[data-test="cookie-save"]').trigger('click');
    await flushPromises();

    expect(axios.post).toHaveBeenCalledWith('/api/babelio/cookie', { cookie: 'jstsToken=fresh; p=FR' });
    expect(wrapper.find('textarea').element.value).toBe('');
    expect(wrapper.emitted('saved')).toHaveLength(1);
    expect(wrapper.find('[data-test="cookie-saved-confirmation"]').exists()).toBe(true);
  });

  it('un échec d\'enregistrement garde le champ et n\'émet rien', async () => {
    axios.post.mockRejectedValueOnce(new Error('network'));
    wrapper = mount(BabelioCookiePanel, { props: { status: { cookie_active: false } } });
    await wrapper.find('textarea').setValue('jstsToken=fresh');
    await wrapper.find('[data-test="cookie-save"]').trigger('click');
    await flushPromises();

    expect(wrapper.find('textarea').element.value).toBe('jstsToken=fresh');
    expect(wrapper.emitted('saved')).toBeUndefined();
    expect(wrapper.find('[data-test="cookie-save-error"]').exists()).toBe(true);
  });

  it('ne propose pas d\'effacer le cookie serveur', async () => {
    // Sans cookie, le serveur interroge Babelio avec des cookies génériques :
    // effacer ne protège de rien, et le cookie se périme seul en 5 min.
    wrapper = mount(BabelioCookiePanel, { props: { status: { cookie_active: false } } });
    expect(wrapper.find('[data-test="cookie-clear"]').exists()).toBe(false);

    await wrapper.setProps({ status: { cookie_active: true, cookie_age_sec: 5, cookie_max_age_sec: 300 } });
    expect(wrapper.find('[data-test="cookie-clear"]').exists()).toBe(false);
    expect(wrapper.text()).not.toContain('Effacer');
  });

  it('signale une saisie qui n\'est pas un en-tête Cookie et bloque l\'envoi', async () => {
    wrapper = mount(BabelioCookiePanel, { props: { status: { cookie_active: false } } });
    await wrapper.find('textarea').setValue('Mozilla/5.0 (X11; Linux x86_64; rv:150.0) Gecko/20100101 Firefox/150.0');

    expect(wrapper.find('[data-test="cookie-format-error"]').text()).toContain('en-tête Cookie');
    expect(wrapper.find('[data-test="cookie-save"]').attributes('disabled')).toBeDefined();

    await wrapper.vm.saveCookie();
    expect(axios.post).not.toHaveBeenCalled();
  });

  it('envoie la valeur nettoyée (préfixe « Cookie: » retiré)', async () => {
    wrapper = mount(BabelioCookiePanel, { props: { status: { cookie_active: false } } });
    await wrapper.find('textarea').setValue('Cookie: jstsToken=fresh; p=FR');
    expect(wrapper.find('[data-test="cookie-format-error"]').exists()).toBe(false);

    await wrapper.find('[data-test="cookie-save"]').trigger('click');
    await flushPromises();

    expect(axios.post).toHaveBeenCalledWith('/api/babelio/cookie', { cookie: 'jstsToken=fresh; p=FR' });
  });

  it('affiche le motif d\'un refus du serveur (400)', async () => {
    axios.post.mockRejectedValueOnce({ response: { status: 400, data: { detail: 'jstsToken absent : ...' } } });
    wrapper = mount(BabelioCookiePanel, { props: { status: { cookie_active: false } } });
    await wrapper.find('textarea').setValue('jstsToken=fresh');
    await wrapper.find('[data-test="cookie-save"]').trigger('click');
    await flushPromises();

    expect(wrapper.find('[data-test="cookie-save-error"]').text()).toContain('jstsToken absent');
  });

  describe('cookie actif côté serveur', () => {
    const ACTIVE = { cookie_active: true, cookie_age_sec: 60, cookie_max_age_sec: 300, cookie_expired: false };

    it('masque le champ et propose « Entrer un cookie plus récent »', () => {
      wrapper = mount(BabelioCookiePanel, { props: { status: ACTIVE } });
      expect(wrapper.find('textarea').exists()).toBe(false);
      expect(wrapper.find('[data-test="cookie-replace"]').text()).toContain('Entrer un cookie plus récent');
    });

    it('le bouton fait apparaître un champ vide, « Annuler » le referme', async () => {
      wrapper = mount(BabelioCookiePanel, { props: { status: ACTIVE } });
      await wrapper.find('[data-test="cookie-replace"]').trigger('click');
      expect(wrapper.find('textarea').element.value).toBe('');

      await wrapper.find('textarea').setValue('jstsToken=draft');
      await wrapper.find('[data-test="cookie-cancel"]').trigger('click');
      expect(wrapper.find('textarea').exists()).toBe(false);

      await wrapper.find('[data-test="cookie-replace"]').trigger('click');
      expect(wrapper.find('textarea').element.value).toBe('');
    });

    it('affiche l\'heure d\'enregistrement et le temps restant, qui diminue', async () => {
      vi.useFakeTimers();
      vi.setSystemTime(new Date(2026, 10, 15, 15, 56, 0));
      wrapper = mount(BabelioCookiePanel, { props: { status: ACTIVE } });
      // Âge 60 s à 15:56:00 → enregistré à 15:55, reste 4 min
      expect(badgeText(wrapper)).toContain('Actif côté serveur');
      expect(badgeText(wrapper)).toContain('enregistré à 15:55');
      expect(badgeText(wrapper)).toContain('expire dans ~4 min');

      vi.advanceTimersByTime(2 * 60 * 1000);
      await wrapper.vm.$nextTick();
      expect(badgeText(wrapper)).toContain('expire dans ~2 min');
    });

    it('après un enregistrement réussi, le champ se referme', async () => {
      wrapper = mount(BabelioCookiePanel, { props: { status: ACTIVE } });
      await wrapper.find('[data-test="cookie-replace"]').trigger('click');
      await wrapper.find('textarea').setValue('jstsToken=fresher');
      await wrapper.find('[data-test="cookie-save"]').trigger('click');
      await flushPromises();
      await wrapper.setProps({ status: { ...ACTIVE, cookie_age_sec: 0 } });

      expect(wrapper.find('textarea').exists()).toBe(false);
      expect(wrapper.find('[data-test="cookie-saved-confirmation"]').exists()).toBe(true);
    });

    it('un cookie périmé ré-affiche le champ directement', () => {
      wrapper = mount(BabelioCookiePanel, { props: { status: { ...ACTIVE, cookie_age_sec: 400, cookie_expired: true } } });
      expect(wrapper.find('textarea').exists()).toBe(true);
      expect(wrapper.find('[data-test="cookie-replace"]').exists()).toBe(false);
    });
  });

  it('n\'envoie jamais de cookie au montage', async () => {
    localStorage.setItem('babelio_cookies', 'jstsToken=old');
    wrapper = mount(BabelioCookiePanel, { props: { status: { cookie_active: false } } });
    await flushPromises();

    expect(axios.post).not.toHaveBeenCalled();
    expect(localStorage.getItem('babelio_cookies')).toBeNull();
  });
});
