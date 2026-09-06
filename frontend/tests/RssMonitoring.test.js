/**
 * Tests TDD pour la vue RssMonitoring (Issue #295).
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { mount } from '@vue/test-utils';
import RssMonitoring from '../src/views/RssMonitoring.vue';
import axios from 'axios';

vi.mock('axios');

const mountComponent = () => {
  return mount(RssMonitoring, {
    global: {
      stubs: { 'router-link': { template: '<a><slot /></a>' }, Navigation: true },
    },
  });
};

describe('RssMonitoring', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    axios.get.mockResolvedValue({ data: [] });
  });

  it('charge l\'historique des synchronisations au montage', async () => {
    axios.get.mockReset();
    axios.get.mockResolvedValue({
      data: [{ _id: '1', started_at: '2026-09-06T10:00:00Z', trigger: 'manual', status: 'success', episodes: [] }],
    });

    const wrapper = mountComponent();
    await wrapper.vm.loadLogs();

    expect(axios.get).toHaveBeenCalledWith('/api/rss/logs');
    expect(wrapper.vm.logs).toHaveLength(1);
  });

  it('déclenche une synchronisation manuelle au clic sur le bouton', async () => {
    axios.post.mockResolvedValueOnce({
      data: { status: 'success', episodes: [] },
    });

    const wrapper = mountComponent();
    await wrapper.vm.$nextTick();
    await Promise.resolve();

    await wrapper.vm.triggerSync();

    expect(axios.post).toHaveBeenCalledWith('/api/rss/sync', { trigger: 'manual' });
    expect(wrapper.vm.lastSyncResult.status).toBe('success');
  });

  it('affiche le détail d\'un run au clic (expansion inline)', async () => {
    axios.get.mockResolvedValueOnce({
      data: [{ _id: '1', started_at: '2026-09-06T10:00:00Z', trigger: 'manual', status: 'success', episodes: [] }],
    });
    axios.get.mockResolvedValueOnce({
      data: { _id: '1', episodes: [{ titre: 'Episode X', outcome: 'downloaded' }] },
    });

    const wrapper = mountComponent();
    await wrapper.vm.$nextTick();
    await Promise.resolve();

    await wrapper.vm.toggleDetail('1');

    expect(axios.get).toHaveBeenCalledWith('/api/rss/logs/1');
    expect(wrapper.vm.detailedLog.episodes[0].titre).toBe('Episode X');
  });

  it('préfixe le titre de chaque épisode par sa date de diffusion (dd/mm/yy)', () => {
    const wrapper = mountComponent();

    const formatted = wrapper.vm.formatEpisodeDate('2026-09-06T08:12:40.000Z');

    expect(formatted).toBe('06/09/26');
  });
});
