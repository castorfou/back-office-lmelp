import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount } from '@vue/test-utils';
import PgxTranscription from '../PgxTranscription.vue';
import axios from 'axios';

vi.mock('axios', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

function mockApi({ diagnostics = [], missingVars = [], episodes = [], progress = null } = {}) {
  axios.get.mockImplementation((url) => {
    if (url === '/api/pgx/diagnostics') {
      return Promise.resolve({
        data: { diagnostics, missing_vars: missingVars },
      });
    }
    if (url === '/api/pgx/episodes-without-transcription') {
      return Promise.resolve({ data: { episodes } });
    }
    if (url === '/api/pgx/transcription/progress') {
      return Promise.resolve({
        data:
          progress || {
            is_running: false,
            episode_ids: [],
            current_episode_id: null,
            current_episode_index: 0,
            processed: [],
            start_time: null,
            logs: [],
            last_update: null,
          },
      });
    }
    return Promise.reject(new Error(`Unexpected URL: ${url}`));
  });
}

function mountView() {
  return mount(PgxTranscription, {
    global: {
      stubs: {
        Navigation: { template: '<div />' },
      },
    },
  });
}

describe('PgxTranscription (Issue #302)', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('affiche la checklist de diagnostics PGX', async () => {
    mockApi({
      diagnostics: [
        { name: 'Machine joignable', status: 'ok', detail: '192.168.50.151 répond' },
        { name: 'Authentification SSH (clé dédiée)', status: 'fail', detail: 'Échec' },
      ],
    });

    const wrapper = mountView();
    await vi.runAllTimersAsync();
    await wrapper.vm.$nextTick();

    const text = wrapper.text();
    expect(text).toContain('Machine joignable');
    expect(text).toContain('Authentification SSH');
  });

  it("affiche un avertissement de configuration manquante sans appeler le diagnostic réseau", async () => {
    mockApi({ missingVars: ['PGX_HOST', 'PGX_SSH_KEY_PATH'] });

    const wrapper = mountView();
    await vi.runAllTimersAsync();
    await wrapper.vm.$nextTick();

    expect(wrapper.text()).toContain('PGX_HOST');
  });

  it('désactive le bouton de lancement si la checklist PGX n\'est pas entièrement au vert', async () => {
    mockApi({
      diagnostics: [{ name: 'Machine joignable', status: 'fail', detail: '...' }],
      episodes: [{ id: 'abc', titre: 'Episode Test', date: '2026-03-01' }],
    });

    const wrapper = mountView();
    await vi.runAllTimersAsync();
    await wrapper.vm.$nextTick();

    const startButton = wrapper.find('[data-testid="pgx-start-button"]');
    expect(startButton.attributes('disabled')).toBeDefined();
  });

  it("désactive le bouton de lancement si aucun épisode n'est en attente", async () => {
    mockApi({
      diagnostics: [
        { name: 'Machine joignable', status: 'ok', detail: '...' },
        { name: 'Authentification SSH (clé dédiée)', status: 'ok', detail: '...' },
        { name: 'Répertoire audio distant', status: 'ok', detail: '...' },
        { name: 'Répertoire transcriptions distant', status: 'ok', detail: '...' },
      ],
      episodes: [],
    });

    const wrapper = mountView();
    await vi.runAllTimersAsync();
    await wrapper.vm.$nextTick();

    const startButton = wrapper.find('[data-testid="pgx-start-button"]');
    expect(startButton.attributes('disabled')).toBeDefined();
  });

  it('active le bouton de lancement quand tout est prêt et affiche le nombre d\'épisodes', async () => {
    mockApi({
      diagnostics: [
        { name: 'Machine joignable', status: 'ok', detail: '...' },
        { name: 'Authentification SSH (clé dédiée)', status: 'ok', detail: '...' },
        { name: 'Répertoire audio distant', status: 'ok', detail: '...' },
        { name: 'Répertoire transcriptions distant', status: 'ok', detail: '...' },
      ],
      episodes: [
        { id: 'abc', titre: 'Episode Un', date: '2026-03-01' },
        { id: 'def', titre: 'Episode Deux', date: '2026-03-02' },
      ],
    });

    const wrapper = mountView();
    await vi.runAllTimersAsync();
    await wrapper.vm.$nextTick();

    const startButton = wrapper.find('[data-testid="pgx-start-button"]');
    expect(startButton.attributes('disabled')).toBeUndefined();
    expect(wrapper.text()).toContain('2');
  });

  it('affiche une ligne par épisode avec sa date de diffusion (dd/mm/yy) et son titre', async () => {
    mockApi({
      diagnostics: [
        { name: 'Machine joignable', status: 'ok', detail: '...' },
        { name: 'Authentification SSH (clé dédiée)', status: 'ok', detail: '...' },
        { name: 'Répertoire audio distant', status: 'ok', detail: '...' },
        { name: 'Répertoire transcriptions distant', status: 'ok', detail: '...' },
      ],
      episodes: [
        { id: 'abc', titre: 'Episode Un', date: '2026-03-01T10:10:50' },
        { id: 'def', titre: 'Episode Deux', date: '2026-03-08T10:10:50' },
      ],
    });

    const wrapper = mountView();
    await vi.runAllTimersAsync();
    await wrapper.vm.$nextTick();

    const items = wrapper.findAll('.pgx-episodes-list li');
    expect(items).toHaveLength(2);
    expect(items[0].text()).toContain('01/03/26');
    expect(items[0].text()).toContain('Episode Un');
    expect(items[1].text()).toContain('08/03/26');
    expect(items[1].text()).toContain('Episode Deux');
  });

  it('déclenche la transcription et démarre le polling de progression', async () => {
    mockApi({
      diagnostics: [
        { name: 'Machine joignable', status: 'ok', detail: '...' },
        { name: 'Authentification SSH (clé dédiée)', status: 'ok', detail: '...' },
        { name: 'Répertoire audio distant', status: 'ok', detail: '...' },
        { name: 'Répertoire transcriptions distant', status: 'ok', detail: '...' },
      ],
      episodes: [{ id: 'abc', titre: 'Episode Un', date: '2026-03-01' }],
    });
    axios.post.mockResolvedValueOnce({
      data: { status: 'started', episode_count: 1 },
    });

    const wrapper = mountView();
    await vi.runAllTimersAsync();
    await wrapper.vm.$nextTick();

    await wrapper.find('[data-testid="pgx-start-button"]').trigger('click');
    await wrapper.vm.$nextTick();

    expect(axios.post).toHaveBeenCalledWith('/api/pgx/transcription/start');
    expect(wrapper.vm.pgxPollInterval).not.toBeNull();
  });

  it('arrête le polling automatiquement quand is_running redevient false', async () => {
    mockApi({
      diagnostics: [
        { name: 'Machine joignable', status: 'ok', detail: '...' },
        { name: 'Authentification SSH (clé dédiée)', status: 'ok', detail: '...' },
        { name: 'Répertoire audio distant', status: 'ok', detail: '...' },
        { name: 'Répertoire transcriptions distant', status: 'ok', detail: '...' },
      ],
      episodes: [{ id: 'abc', titre: 'Episode Un', date: '2026-03-01' }],
    });
    axios.post.mockResolvedValueOnce({
      data: { status: 'started', episode_count: 1 },
    });

    const wrapper = mountView();
    await vi.runAllTimersAsync();
    await wrapper.vm.$nextTick();

    await wrapper.find('[data-testid="pgx-start-button"]').trigger('click');
    await wrapper.vm.$nextTick();
    expect(wrapper.vm.pgxPollInterval).not.toBeNull();

    // Le prochain poll retourne is_running: false => arrêt automatique attendu
    axios.get.mockImplementation((url) => {
      if (url === '/api/pgx/transcription/progress') {
        return Promise.resolve({
          data: {
            is_running: false,
            episode_ids: ['abc'],
            current_episode_id: null,
            current_episode_index: 0,
            processed: [{ episode_id: 'abc', success: true, error: null }],
            start_time: '2026-03-01T10:00:00+00:00',
            logs: ['Terminé'],
            last_update: '2026-03-01T10:05:00+00:00',
          },
        });
      }
      if (url === '/api/pgx/episodes-without-transcription') {
        return Promise.resolve({ data: { episodes: [] } });
      }
      if (url === '/api/pgx/diagnostics') {
        return Promise.resolve({ data: { diagnostics: [], missing_vars: [] } });
      }
      return Promise.reject(new Error(`Unexpected URL: ${url}`));
    });

    await vi.advanceTimersByTimeAsync(2000);
    await wrapper.vm.$nextTick();

    expect(wrapper.vm.pgxPollInterval).toBeNull();
  });

  it('nettoie le polling au démontage du composant', async () => {
    mockApi({
      diagnostics: [
        { name: 'Machine joignable', status: 'ok', detail: '...' },
        { name: 'Authentification SSH (clé dédiée)', status: 'ok', detail: '...' },
        { name: 'Répertoire audio distant', status: 'ok', detail: '...' },
        { name: 'Répertoire transcriptions distant', status: 'ok', detail: '...' },
      ],
      episodes: [{ id: 'abc', titre: 'Episode Un', date: '2026-03-01' }],
    });
    axios.post.mockResolvedValueOnce({
      data: { status: 'started', episode_count: 1 },
    });

    const wrapper = mountView();
    await vi.runAllTimersAsync();
    await wrapper.vm.$nextTick();

    await wrapper.find('[data-testid="pgx-start-button"]').trigger('click');
    await wrapper.vm.$nextTick();
    expect(wrapper.vm.pgxPollInterval).not.toBeNull();

    wrapper.unmount();

    expect(wrapper.vm.pgxPollInterval).toBeNull();
  });

  it('recharge diagnostics et épisodes au clic sur le bouton de rafraîchissement', async () => {
    mockApi({
      diagnostics: [{ name: 'Machine joignable', status: 'fail', detail: 'injoignable' }],
      episodes: [],
    });

    const wrapper = mountView();
    await vi.runAllTimersAsync();
    await wrapper.vm.$nextTick();

    expect(wrapper.text()).toContain('injoignable');

    mockApi({
      diagnostics: [
        { name: 'Machine joignable', status: 'ok', detail: 'répond' },
        { name: 'Authentification SSH (clé dédiée)', status: 'ok', detail: '...' },
        { name: 'Répertoire audio distant', status: 'ok', detail: '...' },
        { name: 'Répertoire transcriptions distant', status: 'ok', detail: '...' },
      ],
      episodes: [{ id: 'abc', titre: 'Episode Un', date: '2026-03-01' }],
    });

    await wrapper.find('[data-testid="pgx-refresh-button"]').trigger('click');
    await vi.runAllTimersAsync();
    await wrapper.vm.$nextTick();

    expect(wrapper.text()).toContain('répond');
    expect(wrapper.text()).toContain('Episode Un');
  });
});
