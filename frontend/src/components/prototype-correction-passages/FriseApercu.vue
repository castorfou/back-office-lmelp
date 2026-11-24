<template>
  <!-- PROTOTYPE JETABLE (#398) : vue d'ensemble des Passages, en lecture seule (frise de la variante B) -->
  <div class="frise">
    <div class="graduations">
      <span v-for="m in minutes" :key="m" :style="{ left: pct(m * 60) }">{{ m }}′</span>
    </div>
    <div class="piste">
      <div class="tete" :style="{ left: pct(lecteur.t) }"></div>
      <div v-for="(p, i) in liste" :key="p.id" :class="['bloc', p.origine]"
        :style="{ left: pct(p.debut), width: pct(p.fin - p.debut), top: (i % 2) * 50 + '%', background: couleur(p) }"
        :title="`${p.titre} · ${fmt(p.debut)}–${fmt(p.fin)} · ${p.origine === 'auto' ? 'repéré auto' : 'corrigé'}`"
        @click="$emit('aller', p.debut)">
        <span>{{ p.titre }}</span>
      </div>
    </div>
  </div>
</template>

<script>
import * as s from './store.js';

export default {
  name: 'FriseApercu',
  emits: ['aller'],
  computed: {
    lecteur: () => s.lecteur,
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
</style>
