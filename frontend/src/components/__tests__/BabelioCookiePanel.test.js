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
    await wrapper.find('textarea').setValue('  PHPSESSID=fresh; p=FR  ');
    await wrapper.find('[data-test="cookie-save"]').trigger('click');
    await flushPromises();

    expect(axios.post).toHaveBeenCalledWith('/api/babelio/cookie', { cookie: 'PHPSESSID=fresh; p=FR' });
    expect(wrapper.find('textarea').element.value).toBe('');
    expect(wrapper.emitted('saved')).toHaveLength(1);
    expect(wrapper.find('[data-test="cookie-saved-confirmation"]').exists()).toBe(true);
  });

  it('un échec d\'enregistrement garde le champ et n\'émet rien', async () => {
    axios.post.mockRejectedValueOnce(new Error('network'));
    wrapper = mount(BabelioCookiePanel, { props: { status: { cookie_active: false } } });
    await wrapper.find('textarea').setValue('PHPSESSID=fresh');
    await wrapper.find('[data-test="cookie-save"]').trigger('click');
    await flushPromises();

    expect(wrapper.find('textarea').element.value).toBe('PHPSESSID=fresh');
    expect(wrapper.emitted('saved')).toBeUndefined();
    expect(wrapper.find('[data-test="cookie-save-error"]').exists()).toBe(true);
  });

  it('ne propose pas d\'effacer le cookie serveur', async () => {
    // Sans cookie, le serveur interroge Babelio avec des cookies génériques :
    // effacer ne protège de rien, et le cookie se périme seul en 4 min.
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
    await wrapper.find('textarea').setValue('Cookie: PHPSESSID=fresh; p=FR');
    expect(wrapper.find('[data-test="cookie-format-error"]').exists()).toBe(false);

    await wrapper.find('[data-test="cookie-save"]').trigger('click');
    await flushPromises();

    expect(axios.post).toHaveBeenCalledWith('/api/babelio/cookie', { cookie: 'PHPSESSID=fresh; p=FR' });
  });

  it('affiche le motif d\'un refus du serveur (400)', async () => {
    axios.post.mockRejectedValueOnce({ response: { status: 400, data: { detail: 'PHPSESSID absent : ...' } } });
    wrapper = mount(BabelioCookiePanel, { props: { status: { cookie_active: false } } });
    await wrapper.find('textarea').setValue('PHPSESSID=fresh');
    await wrapper.find('[data-test="cookie-save"]').trigger('click');
    await flushPromises();

    expect(wrapper.find('[data-test="cookie-save-error"]').text()).toContain('PHPSESSID absent');
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

      await wrapper.find('textarea').setValue('PHPSESSID=draft');
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
      await wrapper.find('textarea').setValue('PHPSESSID=fresher');
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
    localStorage.setItem('babelio_cookies', 'PHPSESSID=old');
    wrapper = mount(BabelioCookiePanel, { props: { status: { cookie_active: false } } });
    await flushPromises();

    expect(axios.post).not.toHaveBeenCalled();
    expect(localStorage.getItem('babelio_cookies')).toBeNull();
  });

  // Issue #357 : un cookie copié sans être connecté au compte Babelio reçoit
  // une page de vérification humaine (403)
  describe('cookie anonyme', () => {
    const WARNING = 'Cookie anonyme : Babelio risque de demander une vérification humaine. Connectez-vous à Babelio puis copiez un nouveau cookie.';

    it('l\'aide commence par la connexion au compte Babelio', () => {
      wrapper = mount(BabelioCookiePanel, { props: { status: { cookie_active: false } } });
      const steps = wrapper.findAll('.cookie-instructions li');
      expect(steps[0].text()).toContain('Connectez-vous à votre compte Babelio');
      // id_user et bbac survivent à la déconnexion : seule la page fait foi
      expect(steps[0].text()).toContain('Continuer en tant que');
      // Les étapes de copie viennent après
      expect(steps[1].text()).not.toContain('Connectez-vous');
    });

    it('affiche l\'avertissement renvoyé par le serveur à l\'enregistrement', async () => {
      axios.post.mockResolvedValueOnce({ data: { ok: true, warning: WARNING } });
      wrapper = mount(BabelioCookiePanel, { props: { status: { cookie_active: false } } });
      await wrapper.find('textarea').setValue('PHPSESSID=fresh; p=FR');
      await wrapper.find('[data-test="cookie-save"]').trigger('click');
      await flushPromises();

      expect(wrapper.find('[data-test="cookie-anonymous-warning"]').text()).toContain('Cookie anonyme');
    });

    it('garde l\'avertissement tant que le cookie actif est anonyme (statut serveur)', () => {
      wrapper = mount(BabelioCookiePanel, {
        props: { status: { cookie_active: true, cookie_anonymous: true, cookie_age_sec: 10, cookie_max_age_sec: 300, cookie_expired: false } },
      });
      expect(wrapper.find('[data-test="cookie-anonymous-warning"]').text()).toContain('Connectez-vous à Babelio');
      // Visible aussi panneau replié
      expect(badgeText(wrapper)).toContain('anonyme');
    });

    it('pas d\'avertissement pour un cookie de session connectée', async () => {
      axios.post.mockResolvedValueOnce({ data: { ok: true, warning: null } });
      wrapper = mount(BabelioCookiePanel, { props: { status: { cookie_active: false } } });
      await wrapper.find('textarea').setValue('PHPSESSID=fresh; id_user=1');
      await wrapper.find('[data-test="cookie-save"]').trigger('click');
      await flushPromises();
      await wrapper.setProps({ status: { cookie_active: true, cookie_anonymous: false, cookie_age_sec: 0, cookie_max_age_sec: 300, cookie_expired: false } });

      expect(wrapper.find('[data-test="cookie-anonymous-warning"]').exists()).toBe(false);
    });
  });

  // Issue #368 : lmelp imite l'empreinte réseau de Firefox ; un User-Agent
  // d'un autre navigateur la contredit (403, puis ban IP)
  describe('navigateur qui n\'est pas Firefox', () => {
    const BROWSER_WARNING = "Cookie enregistré depuis un navigateur qui n'est pas Firefox : lmelp imite Firefox, Babelio risque de refuser les requêtes (403, puis ban IP). Enregistrez le cookie depuis le Firefox connecté à Babelio.";

    it('affiche l\'avertissement renvoyé par le serveur à l\'enregistrement', async () => {
      axios.post.mockResolvedValueOnce({ data: { ok: true, warning: null, browser_warning: BROWSER_WARNING } });
      wrapper = mount(BabelioCookiePanel, { props: { status: { cookie_active: false } } });
      await wrapper.find('textarea').setValue('PHPSESSID=fresh; id_user=1');
      await wrapper.find('[data-test="cookie-save"]').trigger('click');
      await flushPromises();

      expect(wrapper.find('[data-test="cookie-browser-warning"]').text()).toContain("n'est pas Firefox");
    });

    it('garde l\'avertissement tant que le cookie actif vient d\'un autre navigateur (statut serveur)', () => {
      wrapper = mount(BabelioCookiePanel, {
        props: { status: { cookie_active: true, cookie_anonymous: false, cookie_browser_not_firefox: true, cookie_age_sec: 10, cookie_max_age_sec: 300, cookie_expired: false } },
      });
      expect(wrapper.find('[data-test="cookie-browser-warning"]').text()).toContain('depuis le Firefox connecté');
      // Visible aussi panneau replié
      expect(badgeText(wrapper)).toContain('pas Firefox');
      expect(wrapper.find('[data-test="cookie-anonymous-warning"]').exists()).toBe(false);
    });

    it('pas d\'avertissement pour un cookie enregistré depuis Firefox', () => {
      wrapper = mount(BabelioCookiePanel, {
        props: { status: { cookie_active: true, cookie_anonymous: false, cookie_browser_not_firefox: false, cookie_age_sec: 10, cookie_max_age_sec: 300, cookie_expired: false } },
      });
      expect(wrapper.find('[data-test="cookie-browser-warning"]').exists()).toBe(false);
      expect(badgeText(wrapper)).not.toContain('Firefox');
    });
  });

  // Un collage refusé (PHPSESSID absent…) se vide d'un clic
  it('« Vider » efface le texte collé et son erreur, sans toucher au cookie serveur', async () => {
    wrapper = mount(BabelioCookiePanel, { props: { status: { cookie_active: false } } });
    expect(wrapper.find('[data-test="cookie-input-clear"]').exists()).toBe(false);

    await wrapper.find('textarea').setValue('p=FR; disclaimer=1');
    expect(wrapper.find('[data-test="cookie-format-error"]').exists()).toBe(true);

    await wrapper.find('[data-test="cookie-input-clear"]').trigger('click');

    expect(wrapper.find('textarea').element.value).toBe('');
    expect(wrapper.find('[data-test="cookie-format-error"]').exists()).toBe(false);
    expect(axios.post).not.toHaveBeenCalled();
    expect(axios.delete).not.toHaveBeenCalled();
  });
});
