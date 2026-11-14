/**
 * La page Contrôle Babelio affiche l'identité du navigateur retenue avec le
 * cookie : c'est sous ce User-Agent que partent les requêtes vers Babelio.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import axios from 'axios';
import BabelioControl from '../src/views/BabelioControl.vue';

vi.mock('axios');

const BROWSER_UA =
  'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:159.0) Gecko/20100101 Firefox/159.0';

function mountWithStatus(status) {
  axios.get.mockImplementation((url) =>
    Promise.resolve({ data: url.startsWith('/api/babelio/status') ? status : [] })
  );
  return mount(BabelioControl, {
    global: { stubs: { 'router-link': { template: '<a><slot /></a>' }, Navigation: true } },
  });
}

describe('BabelioControl - identité du navigateur', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('affiche le User-Agent retenu avec le cookie', async () => {
    const wrapper = mountWithStatus({
      cookie_active: true,
      browser_user_agent: BROWSER_UA,
      browser_accept_language: 'fr,en-US;q=0.9,en;q=0.8',
    });
    await flushPromises();

    expect(wrapper.find('[data-test="browser-identity"]').text()).toContain('Firefox/159.0');
  });

  it('signale l\'identité par défaut quand aucun navigateur n\'a fourni de cookie', async () => {
    const wrapper = mountWithStatus({ cookie_active: false, browser_user_agent: null });
    await flushPromises();

    expect(wrapper.find('[data-test="browser-identity"]').text()).toContain('par défaut');
  });
});
