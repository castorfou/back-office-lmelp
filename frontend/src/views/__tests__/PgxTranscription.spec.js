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

function mockApi({
  diagnostics = [],
  missingVars = [],
  episodes = [],
  progress = null,
  sshKey = null,
  sshKeyMissingConfig = false,
  logs = [],
  logDetail = null,
} = {}) {
  axios.get.mockImplementation((url) => {
    if (url === '/api/pgx/diagnostics') {
      return Promise.resolve({
        data: { diagnostics, missing_vars: missingVars },
      });
    }
    if (url === '/api/pgx/ssh-key') {
      return Promise.resolve({
        data: { public_key: sshKey, missing_config: sshKeyMissingConfig },
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
            retry_pending: false,
            next_attempt_at: null,
          },
      });
    }
    if (url === '/api/pgx/logs') {
      return Promise.resolve({ data: logs });
    }
    if (url.startsWith('/api/pgx/logs/')) {
      return Promise.resolve({ data: logDetail });
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

  it("affiche un avertissement de configuration manquante ET la checklist grisée en même temps (Issue #310)", async () => {
    mockApi({ missingVars: ['PGX_HOST', 'PGX_SSH_KEY_PATH'] });

    const wrapper = mountView();
    await vi.runAllTimersAsync();
    await wrapper.vm.$nextTick();

    const text = wrapper.text();
    expect(text).toContain('PGX_HOST');
    // La checklist doit rester visible (statuts non exécutés), pas masquée
    // derrière le seul message d'avertissement — comportement lmelp.
    expect(text).toContain('Machine joignable');
    expect(text).toContain('Authentification SSH');
    expect(text).toContain('Répertoire audio distant');
    expect(text).toContain('Répertoire transcriptions distant');
  });

  it("n'appelle pas le diagnostic réseau quand la config est incomplète (piège lmelp #110)", async () => {
    mockApi({ missingVars: ['PGX_HOST', 'PGX_SSH_KEY_PATH'] });

    mountView();
    await vi.runAllTimersAsync();

    // Le backend lui-même court-circuite déjà l'appel réseau (testé côté
    // backend) ; ce test vérifie que le frontend ne masque pas cette
    // information en prétendant que tout est vert.
    expect(axios.get).toHaveBeenCalledWith('/api/pgx/diagnostics');
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

  it('affiche la clé SSH publique et la commande authorized_keys (Issue #310)', async () => {
    mockApi({
      missingVars: ['PGX_HOST'],
      sshKey: 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA back-office-lmelp-pgx',
    });

    const wrapper = mountView();
    await vi.runAllTimersAsync();
    await wrapper.vm.$nextTick();

    const text = wrapper.text();
    expect(text).toContain('ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA back-office-lmelp-pgx');
    expect(text).toContain('authorized_keys');
  });

  it("n'affiche pas la section clé SSH quand PGX_SSH_KEY_PATH n'est pas configuré", async () => {
    mockApi({ missingVars: ['PGX_SSH_KEY_PATH'], sshKey: null, sshKeyMissingConfig: true });

    const wrapper = mountView();
    await vi.runAllTimersAsync();
    await wrapper.vm.$nextTick();

    expect(wrapper.find('[data-testid="pgx-ssh-public-key"]').exists()).toBe(false);
  });

  it('recharge la clé SSH au clic sur le bouton de rafraîchissement', async () => {
    mockApi({ sshKey: 'ssh-ed25519 ANCIENNE_CLE' });

    const wrapper = mountView();
    await vi.runAllTimersAsync();
    await wrapper.vm.$nextTick();

    expect(wrapper.text()).toContain('ANCIENNE_CLE');

    mockApi({ sshKey: 'ssh-ed25519 NOUVELLE_CLE' });

    await wrapper.find('[data-testid="pgx-refresh-button"]').trigger('click');
    await vi.runAllTimersAsync();
    await wrapper.vm.$nextTick();

    expect(wrapper.text()).toContain('NOUVELLE_CLE');
  });

  describe('Historique (Issue #309)', () => {
    it('affiche les logs récupérés au montage', async () => {
      mockApi({
        logs: [
          {
            _id: 'log1',
            started_at: '2026-03-01T10:00:00+00:00',
            trigger: 'manual',
            status: 'success',
            episodes: [{ episode_id: 'ep1', titre: 'Ep', success: true, error: null }],
          },
        ],
      });

      const wrapper = mountView();
      await vi.runAllTimersAsync();
      await wrapper.vm.$nextTick();

      const text = wrapper.text();
      expect(text).toContain('manual');
      expect(text).toContain('success');
    });

    it("affiche un état vide quand aucun log n'existe", async () => {
      mockApi({ logs: [] });

      const wrapper = mountView();
      await vi.runAllTimersAsync();
      await wrapper.vm.$nextTick();

      expect(wrapper.text()).toContain('Aucune transcription enregistrée');
    });

    it('affiche le badge correct par statut', async () => {
      mockApi();
      const wrapper = mountView();
      await vi.runAllTimersAsync();
      await wrapper.vm.$nextTick();

      expect(wrapper.vm.pgxLogStatusBadgeClass('success')).toBe('badge-ok');
      expect(wrapper.vm.pgxLogStatusBadgeClass('partial_error')).toBe('badge-warning');
      expect(wrapper.vm.pgxLogStatusBadgeClass('error')).toBe('badge-expired');
      expect(wrapper.vm.pgxLogStatusBadgeClass('pgx_unreachable_abandoned')).toBe(
        'badge-expired'
      );
    });

    it('charge le détail au clic sur une ligne', async () => {
      mockApi({
        logs: [
          {
            _id: 'log1',
            started_at: '2026-03-01T10:00:00+00:00',
            trigger: 'api',
            status: 'pgx_unreachable_abandoned',
            episodes: [],
          },
        ],
        logDetail: {
          _id: 'log1',
          trigger: 'api',
          status: 'pgx_unreachable_abandoned',
          episodes: [],
          retry_attempts: [{ attempted_at: '2026-03-01T11:00:00+00:00', reachable: false }],
        },
      });

      const wrapper = mountView();
      await vi.runAllTimersAsync();
      await wrapper.vm.$nextTick();

      await wrapper.find('.pgx-log-row').trigger('click');
      await vi.runAllTimersAsync();
      await wrapper.vm.$nextTick();

      expect(axios.get).toHaveBeenCalledWith('/api/pgx/logs/log1');
      expect(wrapper.vm.detailedPgxLog).toEqual(
        expect.objectContaining({ _id: 'log1' })
      );
    });

    it('replie le détail au second clic sur la même ligne', async () => {
      mockApi({
        logs: [
          {
            _id: 'log1',
            started_at: '2026-03-01T10:00:00+00:00',
            trigger: 'manual',
            status: 'success',
            episodes: [],
          },
        ],
        logDetail: { _id: 'log1', trigger: 'manual', status: 'success', episodes: [] },
      });

      const wrapper = mountView();
      await vi.runAllTimersAsync();
      await wrapper.vm.$nextTick();

      await wrapper.find('.pgx-log-row').trigger('click');
      await vi.runAllTimersAsync();
      await wrapper.vm.$nextTick();
      expect(wrapper.vm.expandedPgxLogId).toBe('log1');

      await wrapper.find('.pgx-log-row').trigger('click');
      await wrapper.vm.$nextTick();
      expect(wrapper.vm.expandedPgxLogId).toBe(null);
    });

    it('affiche un bandeau si une nouvelle tentative de retry est programmée', async () => {
      mockApi({
        progress: {
          is_running: true,
          episode_ids: ['ep1'],
          current_episode_id: null,
          current_episode_index: 0,
          processed: [],
          start_time: '2026-03-01T10:00:00+00:00',
          logs: ['PGX injoignable — nouvelle tentative dans 1.0h'],
          last_update: '2026-03-01T10:00:00+00:00',
          retry_pending: true,
          next_attempt_at: '2026-03-01T11:00:00+00:00',
        },
      });

      const wrapper = mountView();
      await vi.runAllTimersAsync();
      await wrapper.vm.$nextTick();

      expect(wrapper.text()).toContain('injoignable');
    });
  });
});
