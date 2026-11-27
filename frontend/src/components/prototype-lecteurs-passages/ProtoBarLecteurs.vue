<template>
  <!-- PROTOTYPE JETABLE (#418) : choix de variante + état du lecteur, jamais en production -->
  <div v-if="actif" class="proto-bar" :class="{ haut: dockVisible }">
    <div class="ligne">
      <button @click="decaler(-1)" aria-label="Variante précédente">◀</button>
      <span>{{ courante }} ({{ VARIANTES[courante] }})</span>
      <button @click="decaler(1)" aria-label="Variante suivante">▶</button>
      <label title="Simule un fichier audio manquant sur le NAS : lmelp répond 404">
        <input type="checkbox" v-model="etat.panne" @change="arreter()"> fichier absent
      </label>
      <button class="journal-btn" @click="ouvert = !ouvert">{{ ouvert ? '▾' : '▸' }} état</button>
    </div>
    <div class="etat">
      {{ etat.statut }}
      <template v-if="etat.passage">
        · « {{ etat.passage.titre }} » {{ etat.passage.emission.date }}
        · {{ fmt(etat.position) }} (borne {{ fmt(etat.passage.debut) }}→{{ fmt(etat.passage.fin) }})
        · fin = {{ etat.modeFin }}
      </template>
    </div>
    <ul v-if="ouvert" class="journal">
      <li v-for="(l, i) in etat.journal" :key="i">{{ l }}</li>
    </ul>
  </div>
</template>

<script>
import { etat, VARIANTES, fmt, arreter } from './store.js';

export default {
  name: 'ProtoBarLecteurs',
  data() { return { etat, VARIANTES, ouvert: false }; },
  computed: {
    actif() { return !import.meta.env.PROD; },
    cles() { return Object.keys(VARIANTES); },
    courante() {
      const v = this.$route.query.variant;
      return this.cles.includes(v) ? v : 'A';
    },
    dockVisible() { return this.courante === 'B' && etat.passage; },
  },
  mounted() { window.addEventListener('keydown', this.clavier); },
  beforeUnmount() { window.removeEventListener('keydown', this.clavier); },
  methods: {
    fmt,
    arreter,
    decaler(d) {
      const i = (this.cles.indexOf(this.courante) + d + this.cles.length) % this.cles.length;
      sessionStorage.setItem('protoVariant', this.cles[i]);
      arreter();
      this.$router.replace({ query: { ...this.$route.query, variant: this.cles[i] } });
    },
    clavier(e) {
      const t = e.target;
      if (t.closest && t.closest('input, textarea, select, [contenteditable]')) return;
      if (e.key === 'ArrowLeft') this.decaler(-1);
      if (e.key === 'ArrowRight') this.decaler(1);
    },
  },
};
</script>

<style scoped>
.proto-bar {
  position: fixed; bottom: 1rem; left: 50%; transform: translateX(-50%);
  z-index: 9999; background: #111; color: #ff0; padding: .4rem .9rem; border-radius: 14px;
  box-shadow: 0 4px 14px rgba(0,0,0,.4); font: 600 13px monospace; max-width: 90vw;
}
.proto-bar.haut { bottom: 6.5rem; }
.ligne { display: flex; gap: .75rem; align-items: center; justify-content: center; }
.ligne button { background: none; border: 1px solid #ff0; color: #ff0;
  border-radius: 50%; width: 1.8rem; height: 1.8rem; cursor: pointer; }
.ligne .journal-btn { border-radius: 6px; width: auto; padding: 0 .4rem; }
.etat { font-weight: 400; font-size: 11px; color: #ddd; text-align: center; margin-top: .2rem; }
.journal { list-style: none; margin: .3rem 0 0; padding: 0; max-height: 9rem; overflow: auto;
  font-weight: 400; font-size: 11px; color: #ccc; }
</style>
