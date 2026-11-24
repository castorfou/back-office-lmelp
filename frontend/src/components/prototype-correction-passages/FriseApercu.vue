<template>
  <!-- PROTOTYPE JETABLE (#398) : vue d'ensemble des Passages, sert de menu pour cibler un Passage (rien n'y est modifiable) -->
  <div class="frise">
    <div class="graduations">
      <span v-for="m in minutes" :key="m" :style="{ left: pct(m * 60) }">{{ m }}′</span>
    </div>
    <div class="piste" ref="piste">
      <div class="tete" :style="{ left: pct(lecteur.t) }"></div>
      <div v-for="t in trous" :key="t.id" :class="['trou', { depot: !!glisse, survol: survol === t.id }]"
        :style="styleTrou(t)"
        :title="`Trou ${fmt(t.debut)}–${fmt(t.fin)} : aucun livre. Écouter, puis y glisser un livre « À placer »`"
        @dragover.prevent="survol = t.id" @dragleave="survol = null" @drop.prevent="deposer(t, 'tout')">
        <template v-if="!glisse">
          <button class="ecouter" title="Écouter le trou" @click.stop="$emit('ecouter-trou', t)">▶</button>
          <span>?</span>
        </template>
        <!-- pendant le glisser : trois zones de dépôt -->
        <template v-else>
          <div v-for="z in ZONES" :key="z.cle" :class="['zone', { survolee: survolZone === t.id + z.cle }]" :title="z.aide"
            @dragover.prevent.stop="survol = t.id; survolZone = t.id + z.cle" @dragleave="survolZone = null"
            @drop.prevent.stop="deposer(t, z.cle)">{{ z.libelle }}</div>
        </template>
      </div>
      <div v-for="(p, i) in liste" :key="p.id" :class="['bloc', p.origine, { choisi: choisi === p.id, autre: choisi && choisi !== p.id }]"
        :style="{ left: pct(p.debut), width: pct(p.fin - p.debut), top: (i % 2) * 50 + '%', background: couleur(p) }"
        :title="`${p.titre} · ${fmt(p.debut)}–${fmt(p.fin)} · ${p.origine === 'auto' ? 'repéré auto' : 'corrigé'}`"
        @click="$emit('cibler', p)">
        <span>{{ p.titre }}</span>
      </div>
    </div>
  </div>
</template>

<script>
import * as s from './store.js';

export default {
  name: 'FriseApercu',
  emits: ['cibler', 'ecouter-trou'],
  data: () => ({
    survol: null,
    survolZone: null,
    ZONES: [
      { cle: 'tete', libelle: '◧ en tête', aide: 'Le livre prend la première moitié ; un autre livre reste à placer après' },
      { cle: 'tout', libelle: '■ tout', aide: 'Le livre prend tout le trou' },
      { cle: 'fin', libelle: '◨ en fin', aide: 'Le livre prend la seconde moitié ; un autre livre reste à placer avant' },
    ],
  }),
  computed: {
    lecteur: () => s.lecteur,
    choisi: () => s.etat.choisi,
    glisse: () => s.etat.glisse,
    trous: () => s.trous(),
    liste() { return s.visibles(); },
    duree() {
      const sg = s.etat.ep?.segments || [];
      return Math.max(s.lecteur.duree || 0, sg.length ? sg[sg.length - 1][1] : 1);
    },
    minutes() { return Array.from({ length: Math.ceil(this.duree / 300) }, (_, i) => i * 5); },
  },
  methods: {
    fmt: s.fmt,
    couleur: s.couleur,
    pct(sec) { return `${(sec / this.duree) * 100}%`; },
    // pendant le glisser, un trou étroit s'élargit à 180 px, centré et gardé dans la frise
    styleTrou(t) {
      const W = this.$refs.piste?.clientWidth;
      if (!this.glisse || !W) return { left: this.pct(t.debut), width: this.pct(t.fin - t.debut) };
      const g = (t.debut / this.duree) * W;
      const l = ((t.fin - t.debut) / this.duree) * W;
      const w = Math.max(l, 180);
      const x = Math.min(Math.max(g + l / 2 - w / 2, 0), W - w);
      return { left: `${x}px`, width: `${w}px` };
    },
    // dépôt sur la frise : en tête, tout le trou ou en fin (le point de lâcher exact est imprécis)
    deposer(trou, zone) {
      this.survol = null;
      this.survolZone = null;
      if (s.etat.glisse) s.deposerSurFrise(s.etat.glisse, trou, zone);
      s.etat.glisse = null;
    },
  },
};
</script>

<style scoped>
.frise { display: flex; flex-direction: column; }
.graduations { position: relative; height: 1rem; font-size: .68rem; color: #888; flex: none; }
.graduations span { position: absolute; transform: translateX(-50%); }
.piste { position: relative; flex: 1; min-height: 50px; background: #fafafa; border: 1px solid #e0e0e0; border-radius: 4px; overflow: hidden; }
.tete { position: absolute; top: 0; bottom: 0; width: 2px; background: #d32f2f; z-index: 3; pointer-events: none; }
.bloc { position: absolute; height: 48%; margin-top: 1px; border-radius: 3px; overflow: hidden; display: flex; align-items: center;
  color: #fff; font-size: .7rem; cursor: pointer; opacity: .85; box-sizing: border-box; }
.bloc.corrige { border: 2px solid #212121; opacity: 1; }
.bloc span { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; padding: 0 4px; }
.bloc:hover { opacity: 1; }
.bloc.autre { opacity: .45; }
.trou { position: absolute; top: 0; bottom: 0; border: 1px dashed #999; border-radius: 3px; box-sizing: border-box;
  background: repeating-linear-gradient(45deg, #e6e6e6 0 6px, #f7f7f7 6px 12px); display: flex; align-items: center;
  justify-content: center; gap: .3rem; color: #777; font-weight: 700; z-index: 1; }
.trou.depot { border: 2px dashed #f0ad4e; background: repeating-linear-gradient(45deg, #ffe8bf 0 6px, #fff6e3 6px 12px); }
.trou.survol { background: #ffd48a; }
.trou .zone { flex: 1; align-self: stretch; display: flex; align-items: center; justify-content: center;
  font-size: .65rem; font-weight: 600; color: #8a5a00; border-right: 1px dashed #f0ad4e; overflow: hidden; white-space: nowrap; }
.trou .zone:last-child { border-right: none; }
.trou .zone.survolee { background: #ffc766; color: #000; }
.trou.depot { gap: 0; z-index: 5; box-shadow: 0 2px 8px rgba(0,0,0,.25); }
.trou .ecouter { background: #fff; border: 1px solid #aaa; border-radius: 4px; font-size: .7rem; padding: 0 .3rem; cursor: pointer; }
.bloc.choisi { opacity: 1; outline: 3px solid #212121; outline-offset: -1px; z-index: 2; font-weight: 600; }
</style>
