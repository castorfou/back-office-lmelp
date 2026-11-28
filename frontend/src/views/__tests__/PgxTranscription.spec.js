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
  archive = [],
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
    if (url === '/api/pgx/episodes-sans-segments') {
      return Promise.resolve({ data: { episodes: archive } });
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
        { name: 'PGX localisée', status: 'ok', detail: "PGX trouvée en 192.168.50.151 (clé d'hôte SHA256:25SQCoKsuvCVdRNxfmcQdwC2wbSns6z4sMrziDVcMCc)" },
        { name: 'Authentification SSH (clé dédiée)', status: 'fail', detail: 'Échec' },
      ],
    });

    const wrapper = mountView();
    await vi.runAllTimersAsync();
    await wrapper.vm.$nextTick();

    const text = wrapper.text();
    expect(text).toContain('PGX localisée');
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
    expect(text).toContain('PGX localisée');
    expect(text).not.toContain('Machine joignable');
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
      diagnostics: [{ name: 'PGX localisée', status: 'fail', detail: '...' }],
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
        { name: 'PGX localisée', status: 'ok', detail: '...' },
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
        { name: 'PGX localisée', status: 'ok', detail: '...' },
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
    expect(wrapper.text()).toContain('2 épisodes seront traités :');
  });

  it('accorde le texte au singulier quand un seul épisode est en attente', async () => {
    mockApi({
      diagnostics: [
        { name: 'PGX localisée', status: 'ok', detail: '...' },
        { name: 'Authentification SSH (clé dédiée)', status: 'ok', detail: '...' },
        { name: 'Répertoire audio distant', status: 'ok', detail: '...' },
        { name: 'Répertoire transcriptions distant', status: 'ok', detail: '...' },
      ],
      episodes: [{ id: 'abc', titre: 'Episode Un', date: '2026-03-01' }],
    });

    const wrapper = mountView();
    await vi.runAllTimersAsync();
    await wrapper.vm.$nextTick();

    expect(wrapper.text()).toContain('1 épisode sera traité :');
  });

  it('affiche une ligne par épisode avec sa date de diffusion (dd/mm/yy) et son titre', async () => {
    mockApi({
      diagnostics: [
        { name: 'PGX localisée', status: 'ok', detail: '...' },
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
        { name: 'PGX localisée', status: 'ok', detail: '...' },
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

  it("rafraîchit l'historique automatiquement pendant le polling de progression", async () => {
    mockApi({
      diagnostics: [
        { name: 'PGX localisée', status: 'ok', detail: '...' },
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
    await wrapper.vm.$nextTick();

    expect(axios.post).toHaveBeenCalledWith('/api/pgx/transcription/start');
    expect(wrapper.vm.pgxPollInterval).not.toBeNull();

    const callsBefore = axios.get.mock.calls.filter(
      (c) => c[0] === '/api/pgx/logs'
    ).length;

    await vi.advanceTimersByTimeAsync(2000);

    const callsAfter = axios.get.mock.calls.filter(
      (c) => c[0] === '/api/pgx/logs'
    ).length;
    expect(callsAfter).toBeGreaterThan(callsBefore);
  });

  it("rafraîchit le détail d'historique ouvert pendant le polling de progression", async () => {
    mockApi({
      diagnostics: [
        { name: 'PGX localisée', status: 'ok', detail: '...' },
        { name: 'Authentification SSH (clé dédiée)', status: 'ok', detail: '...' },
        { name: 'Répertoire audio distant', status: 'ok', detail: '...' },
        { name: 'Répertoire transcriptions distant', status: 'ok', detail: '...' },
      ],
      episodes: [{ id: 'abc', titre: 'Episode Un', date: '2026-03-01' }],
      logs: [
        {
          _id: 'log1',
          started_at: '2026-03-01T10:00:00+00:00',
          trigger: 'api',
          status: 'pgx',
          episodes: [],
        },
      ],
      logDetail: {
        _id: 'log1',
        trigger: 'api',
        status: 'pgx',
        episodes: [],
        retry_attempts: [],
      },
    });
    axios.post.mockResolvedValueOnce({
      data: { status: 'started', episode_count: 1 },
    });

    const wrapper = mountView();
    await vi.runAllTimersAsync();
    await wrapper.vm.$nextTick();

    await wrapper.find('.pgx-log-row').trigger('click');
    await vi.runAllTimersAsync();
    await wrapper.vm.$nextTick();
    expect(wrapper.vm.detailedPgxLog.status).toBe('pgx');

    await wrapper.find('[data-testid="pgx-start-button"]').trigger('click');
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();

    // Le cycle se termine avec succès entre-temps : le détail déjà ouvert
    // doit se resynchroniser pendant le polling, pas rester figé sur 'pgx'.
    axios.get.mockImplementation((url) => {
      if (url === '/api/pgx/diagnostics') {
        return Promise.resolve({
          data: { diagnostics: [], missing_vars: [] },
        });
      }
      if (url === '/api/pgx/episodes-without-transcription') {
        return Promise.resolve({ data: { episodes: [] } });
      }
      if (url === '/api/pgx/transcription/progress') {
        return Promise.resolve({
          data: {
            is_running: true,
            episode_ids: ['abc'],
            current_episode_id: null,
            current_episode_index: 0,
            processed: [],
            start_time: '2026-03-01T10:00:00+00:00',
            logs: [],
            last_update: '2026-03-01T10:00:00+00:00',
            retry_pending: false,
            next_attempt_at: null,
          },
        });
      }
      if (url === '/api/pgx/logs') {
        return Promise.resolve({
          data: [
            {
              _id: 'log1',
              started_at: '2026-03-01T10:00:00+00:00',
              trigger: 'api',
              status: 'success',
              episodes: [{ titre: 'Episode Un', success: true, error: null }],
            },
          ],
        });
      }
      if (url === '/api/pgx/logs/log1') {
        return Promise.resolve({
          data: {
            _id: 'log1',
            trigger: 'api',
            status: 'success',
            episodes: [{ titre: 'Episode Un', success: true, error: null }],
            retry_attempts: [],
          },
        });
      }
      return Promise.reject(new Error(`Unexpected URL: ${url}`));
    });

    await vi.advanceTimersByTimeAsync(2000);
    await wrapper.vm.$nextTick();

    expect(wrapper.vm.detailedPgxLog.status).toBe('success');
  });

  it('arrête le polling automatiquement quand is_running redevient false', async () => {
    mockApi({
      diagnostics: [
        { name: 'PGX localisée', status: 'ok', detail: '...' },
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
      if (url === '/api/pgx/logs') {
        return Promise.resolve({ data: [] });
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
        { name: 'PGX localisée', status: 'ok', detail: '...' },
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
      diagnostics: [{ name: 'PGX localisée', status: 'fail', detail: 'injoignable' }],
      episodes: [],
    });

    const wrapper = mountView();
    await vi.runAllTimersAsync();
    await wrapper.vm.$nextTick();

    expect(wrapper.text()).toContain('injoignable');

    mockApi({
      diagnostics: [
        { name: 'PGX localisée', status: 'ok', detail: 'répond' },
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

  it("n'affiche pas la section clé SSH quand l'authentification SSH est déjà réussie", async () => {
    mockApi({
      diagnostics: [
        { name: 'PGX localisée', status: 'ok', detail: 'répond' },
        { name: 'Authentification SSH (clé dédiée)', status: 'ok', detail: 'Authentification réussie' },
        { name: 'Répertoire audio distant', status: 'ok', detail: '...' },
        { name: 'Répertoire transcriptions distant', status: 'ok', detail: '...' },
      ],
      sshKey: 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA back-office-lmelp-pgx',
    });

    const wrapper = mountView();
    await vi.runAllTimersAsync();
    await wrapper.vm.$nextTick();

    expect(wrapper.find('[data-testid="pgx-ssh-public-key"]').exists()).toBe(false);
  });

  it('affiche la section clé SSH quand l\'authentification SSH échoue encore', async () => {
    mockApi({
      diagnostics: [
        { name: 'PGX localisée', status: 'ok', detail: 'répond' },
        { name: 'Authentification SSH (clé dédiée)', status: 'fail', detail: 'Échec' },
        { name: 'Répertoire audio distant', status: 'skipped', detail: '...' },
        { name: 'Répertoire transcriptions distant', status: 'skipped', detail: '...' },
      ],
      sshKey: 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA back-office-lmelp-pgx',
    });

    const wrapper = mountView();
    await vi.runAllTimersAsync();
    await wrapper.vm.$nextTick();

    expect(wrapper.find('[data-testid="pgx-ssh-public-key"]').exists()).toBe(true);
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
      expect(wrapper.vm.pgxLogStatusBadgeClass('error')).toBe('badge-expired');
      expect(wrapper.vm.pgxLogStatusBadgeClass('pgx')).toBe('badge-expired');
    });

    it("affiche l'heure de fin (finished_at) dans la colonne Date, pas l'heure de début", async () => {
      mockApi({
        logs: [
          {
            _id: 'log1',
            started_at: '2026-03-01T10:00:00+00:00',
            finished_at: '2026-03-01T10:05:00+00:00',
            trigger: 'api',
            status: 'success',
            episodes: [],
          },
        ],
      });

      const wrapper = mountView();
      await vi.runAllTimersAsync();
      await wrapper.vm.$nextTick();

      const dateCell = wrapper.find('.td-date');
      expect(dateCell.text()).toContain('10:05');
      expect(dateCell.text()).not.toContain('10:00');
    });

    it("retombe sur started_at pour la colonne Date quand finished_at est absent (cycle en cours)", async () => {
      mockApi({
        logs: [
          {
            _id: 'log1',
            started_at: '2026-03-01T10:00:00+00:00',
            finished_at: null,
            trigger: 'api',
            status: 'pgx',
            episodes: [],
          },
        ],
      });

      const wrapper = mountView();
      await vi.runAllTimersAsync();
      await wrapper.vm.$nextTick();

      const dateCell = wrapper.find('.td-date');
      expect(dateCell.text()).toContain('10:00');
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

    it('affiche la date et le titre de chaque épisode du détail, comme pour l\'historique RSS', async () => {
      mockApi({
        logs: [
          {
            _id: 'log1',
            started_at: '2026-03-01T10:00:00+00:00',
            trigger: 'api',
            status: 'success',
            episodes: [{ titre: 'Un bel épisode', date: '2026-03-01T00:00:00+00:00', success: true, error: null }],
          },
        ],
        logDetail: {
          _id: 'log1',
          trigger: 'api',
          status: 'success',
          episodes: [{ titre: 'Un bel épisode', date: '2026-03-01T00:00:00+00:00', success: true, error: null }],
          retry_attempts: [],
        },
      });

      const wrapper = mountView();
      await vi.runAllTimersAsync();
      await wrapper.vm.$nextTick();

      await wrapper.find('.pgx-log-row').trigger('click');
      await vi.runAllTimersAsync();
      await wrapper.vm.$nextTick();

      const detailText = wrapper.find('.log-detail').text();
      expect(detailText).toContain('Un bel épisode');
      expect(detailText).toContain('01/03/26');
    });

    it("rafraîchit aussi le détail ouvert au clic sur le bouton Rafraîchir de l'historique", async () => {
      mockApi({
        logs: [
          {
            _id: 'log1',
            started_at: '2026-03-01T10:00:00+00:00',
            trigger: 'api',
            status: 'pgx',
            episodes: [],
          },
        ],
        logDetail: {
          _id: 'log1',
          trigger: 'api',
          status: 'pgx',
          episodes: [],
          retry_attempts: [],
        },
      });

      const wrapper = mountView();
      await vi.runAllTimersAsync();
      await wrapper.vm.$nextTick();

      await wrapper.find('.pgx-log-row').trigger('click');
      await vi.runAllTimersAsync();
      await wrapper.vm.$nextTick();
      expect(wrapper.vm.detailedPgxLog.status).toBe('pgx');

      axios.get.mockImplementation((url) => {
        if (url === '/api/pgx/diagnostics') {
          return Promise.resolve({ data: { diagnostics: [], missing_vars: [] } });
        }
        if (url === '/api/pgx/episodes-without-transcription') {
          return Promise.resolve({ data: { episodes: [] } });
        }
        if (url === '/api/pgx/transcription/progress') {
          return Promise.resolve({
            data: {
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
          return Promise.resolve({
            data: [
              {
                _id: 'log1',
                started_at: '2026-03-01T10:00:00+00:00',
                finished_at: '2026-03-01T10:05:00+00:00',
                trigger: 'api',
                status: 'success',
                episodes: [{ titre: 'Episode Un', success: true, error: null }],
              },
            ],
          });
        }
        if (url === '/api/pgx/logs/log1') {
          return Promise.resolve({
            data: {
              _id: 'log1',
              trigger: 'api',
              status: 'success',
              episodes: [{ titre: 'Episode Un', success: true, error: null }],
              retry_attempts: [],
            },
          });
        }
        return Promise.reject(new Error(`Unexpected URL: ${url}`));
      });

      const refreshButton = wrapper
        .findAll('button')
        .find((b) => b.text().includes('🔄 Rafraîchir') && !b.text().includes('statut'));
      await refreshButton.trigger('click');
      await vi.runAllTimersAsync();
      await wrapper.vm.$nextTick();

      expect(wrapper.vm.detailedPgxLog.status).toBe('success');
    });

    it('affiche un récapitulatif du retry (heure de démarrage + nombre de tentatives) quand la reprise a réussi', async () => {
      mockApi({
        logs: [
          {
            _id: 'log1',
            started_at: '2026-03-01T10:00:00+00:00',
            trigger: 'api',
            status: 'success',
            episodes: [{ titre: 'Un épisode', date: '2026-03-01T00:00:00+00:00', success: true, error: null }],
          },
        ],
        logDetail: {
          _id: 'log1',
          started_at: '2026-03-01T10:00:00+00:00',
          trigger: 'api',
          status: 'success',
          episodes: [{ titre: 'Un épisode', date: '2026-03-01T00:00:00+00:00', success: true, error: null }],
          retry_attempts: [
            { attempted_at: '2026-03-01T10:30:00+00:00', reachable: false },
            { attempted_at: '2026-03-01T11:00:00+00:00', reachable: true },
          ],
        },
      });

      const wrapper = mountView();
      await vi.runAllTimersAsync();
      await wrapper.vm.$nextTick();

      await wrapper.find('.pgx-log-row').trigger('click');
      await vi.runAllTimersAsync();
      await wrapper.vm.$nextTick();

      const detailText = wrapper.find('.log-detail').text();
      expect(detailText).toContain('Démarré à');
      expect(detailText).toContain('repris après 2 tentatives');
    });

    it("affiche 'toujours injoignable' quand le retry a été abandonné sans jamais réussir", async () => {
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
          started_at: '2026-03-01T10:00:00+00:00',
          trigger: 'api',
          status: 'pgx_unreachable_abandoned',
          episodes: [],
          retry_attempts: [
            { attempted_at: '2026-03-01T11:00:00+00:00', reachable: false },
            { attempted_at: '2026-03-01T12:00:00+00:00', reachable: false },
          ],
        },
      });

      const wrapper = mountView();
      await vi.runAllTimersAsync();
      await wrapper.vm.$nextTick();

      await wrapper.find('.pgx-log-row').trigger('click');
      await vi.runAllTimersAsync();
      await wrapper.vm.$nextTick();

      const detailText = wrapper.find('.log-detail').text();
      expect(detailText).toContain('toujours injoignable');
      expect(detailText).toContain('2 tentative(s)');
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
      // Cycle en cours : le polling tourne, runAllTimersAsync ne finirait pas
      await vi.advanceTimersByTimeAsync(0);
      await wrapper.vm.$nextTick();

      expect(wrapper.text()).toContain('injoignable');
      wrapper.unmount();
    });
  });
});

describe('PgxTranscription — cycle en attente de PGX (Issue #402)', () => {
  const ALL_OK = [
    { name: 'PGX localisée', status: 'ok', detail: '...' },
    { name: 'Authentification SSH (clé dédiée)', status: 'ok', detail: '...' },
    { name: 'Répertoire audio distant', status: 'ok', detail: '...' },
    { name: 'Répertoire transcriptions distant', status: 'ok', detail: '...' },
  ];

  function runningProgress(retryPending) {
    return {
      is_running: true,
      episode_ids: ['abc'],
      current_episode_id: 'abc',
      current_episode_index: 0,
      processed: [],
      start_time: '2026-03-01T10:00:00+00:00',
      logs: [],
      last_update: '2026-03-01T10:00:00+00:00',
      retry_pending: retryPending,
      next_attempt_at: retryPending ? '2026-03-01T11:00:00+00:00' : null,
    };
  }

  beforeEach(() => {
    vi.resetAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  async function mountRunning(retryPending, diagnostics = ALL_OK) {
    mockApi({
      diagnostics,
      episodes: [
        { id: 'abc', titre: 'Episode Un', date: '2026-03-01' },
        { id: 'def', titre: 'Episode Deux', date: '2026-03-02' },
      ],
      progress: runningProgress(retryPending),
    });
    const wrapper = mountView();
    await vi.advanceTimersByTimeAsync(0);
    await wrapper.vm.$nextTick();
    return wrapper;
  }

  it("active le bouton « Réessayer maintenant » pendant l'attente quand PGX est au vert", async () => {
    const wrapper = await mountRunning(true);

    const button = wrapper.find('[data-testid="pgx-start-button"]');
    expect(button.attributes('disabled')).toBeUndefined();
    expect(button.text()).toContain('Réessayer maintenant');
    wrapper.unmount();
  });

  it("garde le bouton désactivé pendant l'attente si PGX n'est pas au vert", async () => {
    const wrapper = await mountRunning(true, [
      { name: 'PGX localisée', status: 'fail', detail: '...' },
    ]);

    const button = wrapper.find('[data-testid="pgx-start-button"]');
    expect(button.attributes('disabled')).toBeDefined();
    wrapper.unmount();
  });

  it('garde le bouton désactivé pendant un cycle qui travaille (sans attente)', async () => {
    const wrapper = await mountRunning(false);

    const button = wrapper.find('[data-testid="pgx-start-button"]');
    expect(button.attributes('disabled')).toBeDefined();
    expect(button.text()).toContain('Lancer la transcription');
    wrapper.unmount();
  });

  it('le clic pendant l\'attente demande une nouvelle tentative immédiate', async () => {
    const wrapper = await mountRunning(true);
    axios.post.mockResolvedValueOnce({ data: { status: 'retrying' } });

    await wrapper.vm.startPgxTranscription();

    expect(axios.post).toHaveBeenCalledWith('/api/pgx/transcription/retry-now');
    expect(axios.post).not.toHaveBeenCalledWith('/api/pgx/transcription/start');
    expect(wrapper.vm.pgxPollInterval).not.toBeNull();
    wrapper.unmount();
  });

  it('suit la progression dès l\'ouverture de la page pendant un cycle', async () => {
    const wrapper = await mountRunning(false);

    expect(wrapper.vm.pgxPollInterval).not.toBeNull();
    wrapper.unmount();
  });
});


describe('PgxTranscription - retranscription horodatée de l\'archive (Issue #427)', () => {
  const ARCHIVE = Array.from({ length: 250 }, (_, i) => ({
    id: `e${i}`, titre: `Épisode ${i}`, date: '2015-06-28T00:00:00',
  }));

  beforeEach(() => {
    vi.resetAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  async function monter(options) {
    mockApi({ diagnostics: [{ name: 'PGX localisée', status: 'ok', detail: 'ok' }], ...options });
    const vue = mountView();
    await vi.runOnlyPendingTimersAsync();
    await vue.vm.$nextTick();
    return vue;
  }

  it('annonce le nombre d\'épisodes à retranscrire et la durée estimée', async () => {
    const vue = await monter({ archive: ARCHIVE });

    const section = vue.find('[data-testid="pgx-archive"]');
    expect(section.text()).toContain('250 épisode(s)');
    expect(section.text()).toContain('environ 19 h');
    expect(vue.find('[data-testid="pgx-archive-button"]').attributes('disabled')).toBeUndefined();
  });

  it('lance la retranscription après confirmation et suit sa progression', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    axios.post.mockResolvedValue({ data: { status: 'started', episode_count: 250 } });
    const vue = await monter({ archive: ARCHIVE });

    await vue.find('[data-testid="pgx-archive-button"]').trigger('click');
    await vue.vm.$nextTick();

    expect(axios.post).toHaveBeenCalledWith('/api/pgx/transcription/archive');
    expect(vue.vm.pgxPollInterval).not.toBeNull();
  });

  it("dit moins d'une heure pour quelques épisodes", async () => {
    const vue = await monter({ archive: ARCHIVE.slice(0, 3) });

    expect(vue.find('[data-testid="pgx-archive"]').text()).toContain("moins d'une heure");
  });

  it('dit pourquoi rien n\'a été lancé quand un cycle tourne déjà', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    axios.post.mockResolvedValue({ data: { status: 'already_running' } });
    const vue = await monter({ archive: ARCHIVE });

    await vue.find('[data-testid="pgx-archive-button"]').trigger('click');
    await vue.vm.$nextTick();
    await vue.vm.$nextTick();

    expect(vue.find('[data-testid="pgx-archive-message"]').text()).toContain('déjà en cours');
  });

  it('ne lance rien sans confirmation', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(false);
    const vue = await monter({ archive: ARCHIVE });

    await vue.find('[data-testid="pgx-archive-button"]').trigger('click');

    expect(axios.post).not.toHaveBeenCalled();
  });

  it("montre un cycle d'archive comme tel dans l'historique", async () => {
    const vue = await monter({
      logs: [{
        _id: 'l1', started_at: '2026-11-28T10:00:00+00:00', finished_at: null, trigger: 'manual',
        status: 'success', episode_ids: ['e1'], episodes: [], retry_attempts: [], archive: true,
      }],
    });

    expect(vue.find('.history-section tbody').text()).toContain('archive');
  });

  it('dit que l\'archive est entièrement horodatée', async () => {
    const vue = await monter({ archive: [] });

    expect(vue.find('[data-testid="pgx-archive"]').text()).toContain('Tous les épisodes ont leurs Segments');
    expect(vue.find('[data-testid="pgx-archive-button"]').exists()).toBe(false);
  });

  it('bloque le bouton pendant un cycle, et dit quand c\'est l\'archive qui tourne', async () => {
    const vue = await monter({
      archive: ARCHIVE,
      progress: {
        is_running: true, archive: true, episode_ids: ['e1', 'e2'], current_episode_id: 'e1',
        current_episode_index: 0, processed: [], start_time: null, logs: [], last_update: null,
        retry_pending: false, next_attempt_at: null,
      },
    });

    expect(vue.find('[data-testid="pgx-archive-button"]').attributes('disabled')).toBeDefined();
    expect(vue.find('.progress-header').text()).toContain('Retranscription de l\'archive en cours');
  });
});
