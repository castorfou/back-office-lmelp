import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount } from '@vue/test-utils';
import { createRouter, createMemoryHistory } from 'vue-router';
import Critiques from '../Critiques.vue';
import axios from 'axios';

vi.mock('axios');

const mockCritiques = [
  { id: 'id1', nom: 'Arnaud Viviant', animateur: false, nombre_avis: 42, note_moyenne: 7.5 },
  { id: 'id2', nom: 'Éric Neuhoff', animateur: false, nombre_avis: 30, note_moyenne: 6.8 },
  { id: 'id3', nom: 'Nelly Kapriélian', animateur: false, nombre_avis: 55, note_moyenne: 8.1 },
  { id: 'id4', nom: 'Arnaud Laporte', animateur: true, nombre_avis: 0, note_moyenne: null },
];

describe('Critiques.vue', () => {
  let wrapper;
  let router;

  beforeEach(async () => {
    vi.clearAllMocks();
    vi.resetAllMocks();

    axios.get = vi.fn();
    axios.post = vi.fn();

    router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/critiques', component: Critiques },
        { path: '/critique/:id', component: { template: '<div>detail</div>' } },
      ]
    });

    await router.push('/critiques');
  });

  // ── 1. Rendu de la liste ─────────────────────────────────────────────────

  it('affiche la liste des critiques après chargement', async () => {
    axios.get.mockResolvedValueOnce({ data: mockCritiques });

    wrapper = mount(Critiques, { global: { plugins: [router] } });
    await new Promise(r => setTimeout(r, 50));
    await wrapper.vm.$nextTick();

    expect(wrapper.text()).toContain('Arnaud Viviant');
    expect(wrapper.text()).toContain('Éric Neuhoff');
    expect(wrapper.text()).toContain('Nelly Kapriélian');
  });

  it('affiche le nombre d\'avis et la note moyenne', async () => {
    axios.get.mockResolvedValueOnce({ data: mockCritiques });

    wrapper = mount(Critiques, { global: { plugins: [router] } });
    await new Promise(r => setTimeout(r, 50));
    await wrapper.vm.$nextTick();

    expect(wrapper.text()).toContain('42');
    expect(wrapper.text()).toContain('7.5');
  });

  it('affiche un état de chargement avant que les données arrivent', async () => {
    axios.get.mockReturnValue(new Promise(() => {})); // jamais résolu

    wrapper = mount(Critiques, { global: { plugins: [router] } });

    expect(wrapper.text()).toMatch(/chargement|loading/i);
  });

  it('affiche un message d\'erreur si l\'API échoue', async () => {
    axios.get.mockRejectedValueOnce(new Error('Network error'));

    wrapper = mount(Critiques, { global: { plugins: [router] } });
    await new Promise(r => setTimeout(r, 50));
    await wrapper.vm.$nextTick();

    expect(wrapper.text()).toMatch(/erreur|error/i);
  });

  it('affiche un message vide si aucun critique', async () => {
    axios.get.mockResolvedValueOnce({ data: [] });

    wrapper = mount(Critiques, { global: { plugins: [router] } });
    await new Promise(r => setTimeout(r, 50));
    await wrapper.vm.$nextTick();

    expect(wrapper.text()).toMatch(/aucun|vide|no critic/i);
  });

  // ── 2. Tri ───────────────────────────────────────────────────────────────

  it('trie par nom (A-Z) par défaut', async () => {
    const desordonnes = [
      { id: 'id2', nom: 'Éric Neuhoff', animateur: false, nombre_avis: 30, note_moyenne: 6.8 },
      { id: 'id1', nom: 'Arnaud Viviant', animateur: false, nombre_avis: 42, note_moyenne: 7.5 },
    ];
    axios.get.mockResolvedValueOnce({ data: desordonnes });

    wrapper = mount(Critiques, { global: { plugins: [router] } });
    await new Promise(r => setTimeout(r, 50));
    await wrapper.vm.$nextTick();

    const text = wrapper.text();
    const posArnaud = text.indexOf('Arnaud Viviant');
    const posEric = text.indexOf('Éric Neuhoff');
    expect(posArnaud).toBeLessThan(posEric);
  });

  it('inverse le tri au second clic sur la colonne Nom', async () => {
    axios.get.mockResolvedValueOnce({ data: mockCritiques });

    wrapper = mount(Critiques, { global: { plugins: [router] } });
    await new Promise(r => setTimeout(r, 50));
    await wrapper.vm.$nextTick();

    // Le tri par défaut est ASC — un seul clic passe en DESC
    const nomHeader = wrapper.find('[data-sort="nom"]');
    await nomHeader.trigger('click');
    await wrapper.vm.$nextTick();

    const text = wrapper.text();
    const posNelly = text.indexOf('Nelly Kapriélian');
    const posArnaud = text.indexOf('Arnaud Viviant');
    // En DESC, Nelly (N) avant Arnaud (A)
    expect(posNelly).toBeLessThan(posArnaud);
  });

  // ── 3. Navigation ────────────────────────────────────────────────────────

  it('navigue vers /critique/:id au clic sur une ligne', async () => {
    axios.get.mockResolvedValueOnce({ data: mockCritiques });

    wrapper = mount(Critiques, { global: { plugins: [router] } });
    await new Promise(r => setTimeout(r, 50));
    await wrapper.vm.$nextTick();

    const firstRow = wrapper.find('tr.critique-row');
    await firstRow.trigger('click');
    await new Promise(r => setTimeout(r, 50));

    expect(router.currentRoute.value.path).toMatch(/\/critique\//);
  });

  // ── 4. Merge ─────────────────────────────────────────────────────────────

  it('désactive le bouton merge sans sélection et sans confirmation', async () => {
    axios.get.mockResolvedValueOnce({ data: mockCritiques });

    wrapper = mount(Critiques, { global: { plugins: [router] } });
    await new Promise(r => setTimeout(r, 50));
    await wrapper.vm.$nextTick();

    const mergeBtn = wrapper.find('[data-testid="merge-btn"]');
    expect(mergeBtn.attributes('disabled')).toBeDefined();
  });

  it('active le bouton merge quand source, cible et confirmation sont remplis', async () => {
    axios.get.mockResolvedValueOnce({ data: mockCritiques });

    wrapper = mount(Critiques, { global: { plugins: [router] } });
    await new Promise(r => setTimeout(r, 50));
    await wrapper.vm.$nextTick();

    wrapper.vm.mergeSourceId = 'id1';
    wrapper.vm.mergeTargetId = 'id2';
    wrapper.vm.mergeConfirmation = 'Éric Neuhoff';
    await wrapper.vm.$nextTick();

    const mergeBtn = wrapper.find('[data-testid="merge-btn"]');
    expect(mergeBtn.attributes('disabled')).toBeUndefined();
  });

  it('appelle POST /api/critiques/merge avec les bons paramètres', async () => {
    axios.get.mockResolvedValueOnce({ data: mockCritiques });
    axios.post.mockResolvedValueOnce({ data: { merged_avis: 10, deleted_critique: 'id1' } });
    axios.get.mockResolvedValueOnce({ data: mockCritiques.filter(c => c.id !== 'id1') });

    wrapper = mount(Critiques, { global: { plugins: [router] } });
    await new Promise(r => setTimeout(r, 50));
    await wrapper.vm.$nextTick();

    wrapper.vm.mergeSourceId = 'id1';
    wrapper.vm.mergeTargetId = 'id2';
    wrapper.vm.mergeConfirmation = 'Éric Neuhoff';
    await wrapper.vm.$nextTick();

    await wrapper.vm.executeMerge();

    expect(axios.post).toHaveBeenCalledWith('/api/critiques/merge', {
      source_id: 'id1',
      target_id: 'id2',
      target_nom: 'Éric Neuhoff',
    });
  });
});
