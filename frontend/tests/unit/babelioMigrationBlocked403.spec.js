/**
 * La page Liaison Babelio doit dire quand Babelio bloque les requêtes (Issue #339).
 *
 * Bug : cookie Babelio expiré → 403 → disjoncteur ouvert. La page affichait
 * « ✅ Dernière liaison » et ❌❌ sur le livre, sans rien qui indique la cause :
 * l'état du cookie et du disjoncteur n'était visible que dans Contrôle Babelio.
 *
 * Mocks : réponses réelles de /api/babelio/status, /api/babelio-migration/status
 * et /api/babelio-migration/progress capturées le 13/11/2026.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import axios from 'axios';
import BabelioMigration from '../../src/views/BabelioMigration.vue';

vi.mock('axios');

const BLOCKED_STATUS = {
  overall: 'blocked_403',
  cookie_active: false,
  circuit_open: true,
  cache_entries: 135,
  recent_requests_count: 50,
  min_interval_sec: 10,
  cache_ttl_hours: 24,
};

const OK_STATUS = { ...BLOCKED_STATUS, overall: 'ok', cookie_active: true, circuit_open: false };

const MIGRATION_STATUS = {
  total_books: 1735,
  migrated_count: 1714,
  not_found_count: 18,
  problematic_count: 0,
  pending_count: 3,
  last_migration: '2026-11-12T21:05:11+00:00',
  total_authors: 1183,
  authors_with_url: 1179,
  authors_not_found_count: 4,
  problematic_authors_count: 0,
  authors_without_url_babelio: 0,
  covers_total: 1714,
  covers_with_url: 1714,
  covers_not_applicable: 18,
  covers_mismatch_count: 0,
  covers_pending: 0,
};

const BLOCKED_PROGRESS = {
  is_running: false,
  start_time: '2026-11-13T13:08:43.123368+00:00',
  books_processed: 1,
  last_update: '2026-11-13T13:08:43.126198+00:00',
  logs: [
    'Migration #1: L’Héritage - 📚 blocked_403 - 👤 none',
    '✅ Migration completed successfully - 1 books processed',
  ],
  total_logs: 2,
  book_logs: [
    {
      titre: 'L’Héritage',
      auteur: 'Jonathan Littell',
      livre_status: 'blocked_403',
      auteur_status: 'none',
      details: [
        '📚 Livre: L’Héritage (Jonathan Littell)',
        '📊 Status: blocked_403',
        '❌ Livre non mis à jour',
        '❌ Auteur non migré',
      ],
    },
  ],
};

function mockApi({ babelioStatus, progress }) {
  axios.get.mockImplementation((url) => {
    if (url.startsWith('/api/babelio/status')) return Promise.resolve({ data: babelioStatus });
    if (url === '/api/babelio-migration/status') return Promise.resolve({ data: MIGRATION_STATUS });
    if (url === '/api/babelio-migration/progress') return Promise.resolve({ data: progress });
    return Promise.resolve({ data: [] });
  });
}

describe('BabelioMigration - blocage Babelio visible (Issue #339)', () => {
  let wrapper;

  const mountPage = async () => {
    wrapper = mount(BabelioMigration, {
      global: { stubs: { Navigation: true, 'router-link': true } },
    });
    await flushPromises();
  };

  beforeEach(() => {
    vi.resetAllMocks();
    axios.post.mockResolvedValue({ data: {} });
  });

  afterEach(() => {
    wrapper?.unmount();
  });

  it('affiche un bandeau quand Babelio est bloqué (cookie expiré, disjoncteur ouvert)', async () => {
    mockApi({ babelioStatus: BLOCKED_STATUS, progress: BLOCKED_PROGRESS });
    await mountPage();

    const banner = wrapper.find('[data-test="babelio-blocked-banner"]');
    expect(banner.exists()).toBe(true);
    expect(banner.text()).toContain('403');
    expect(banner.text()).toContain('cookie');
  });

  it('pas de bandeau quand Babelio répond normalement', async () => {
    mockApi({ babelioStatus: OK_STATUS, progress: { ...BLOCKED_PROGRESS, book_logs: [] } });
    await mountPage();

    expect(wrapper.find('[data-test="babelio-blocked-banner"]').exists()).toBe(false);
  });

  it('plus de bandeau dès qu\'un cookie frais a refermé le disjoncteur', async () => {
    // Réponse réelle juste après l'enregistrement du cookie : `overall` décrit
    // la dernière requête (le 403), il ne change qu'à la prochaine requête.
    mockApi({
      babelioStatus: {
        overall: 'blocked_403',
        cookie_active: true,
        circuit_open: false,
        cache_entries: 135,
        recent_requests_count: 1,
        min_interval_sec: 10.0,
        cache_ttl_hours: 24.0,
      },
      progress: BLOCKED_PROGRESS,
    });
    await mountPage();

    expect(wrapper.find('[data-test="babelio-blocked-banner"]').exists()).toBe(false);
  });

  it('la dernière liaison arrêtée par un 403 ne s\'affiche pas comme réussie', async () => {
    mockApi({ babelioStatus: BLOCKED_STATUS, progress: BLOCKED_PROGRESS });
    await mountPage();

    const title = wrapper.find('.migration-progress-panel h3').text();
    expect(title).not.toContain('✅');
    expect(title).toContain('403');
  });

  it('le livre bloqué est marqué « bloqué (403) », pas ❌❌', async () => {
    mockApi({ babelioStatus: BLOCKED_STATUS, progress: BLOCKED_PROGRESS });
    await mountPage();

    const status = wrapper.find('.book-log-status').text();
    expect(status).not.toContain('❌');
    expect(status).toContain('403');
  });
});
