<template>
  <!-- PROTOTYPE JETABLE (#418) : signalement (stub, journal seulement), cf. #422 -->
  <span ref="racine" class="sig">
    <button class="sig-btn" title="Signaler un Passage mal découpé" @click.stop="ouvert = !ouvert">⚠️</button>
    <span v-if="ouvert" class="sig-menu" @click.stop>
      <strong>Signaler à {{ fmt(etat.position) }}</strong>
      <button v-for="m in MOTIFS" :key="m" @click="envoyer(m)">{{ m }}</button>
    </span>
    <span v-if="merci" class="sig-merci">✓ Signalé : {{ merci }}</span>
  </span>
</template>

<script>
import { etat, MOTIFS, signaler, fmt } from './store.js';

export default {
  name: 'SignalerPassage',
  data() { return { etat, MOTIFS, ouvert: false, merci: false }; },
  watch: {
    ouvert(v) {
      if (v) setTimeout(() => document.addEventListener('click', this.dehors), 0);
      else document.removeEventListener('click', this.dehors);
    },
  },
  beforeUnmount() { document.removeEventListener('click', this.dehors); },
  methods: {
    fmt,
    dehors(e) {
      if (!this.$refs.racine?.contains(e.target)) this.ouvert = false;
    },
    envoyer(m) {
      signaler(m);
      this.ouvert = false;
      this.merci = `${m} à ${fmt(etat.position)}`;
      setTimeout(() => { this.merci = false; }, 2500);
    },
  },
};
</script>

<style scoped>
.sig { position: relative; display: inline-flex; align-items: center; }
.sig-btn { border: none; background: none; border-radius: 6px; font-size: .75rem; cursor: pointer; padding: 0 .3rem; }
.sig-menu { position: absolute; bottom: 120%; right: -2rem; z-index: 50; background: #fff; border: 1px solid #ccc;
  border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,.15); padding: .4rem; display: flex; flex-direction: column;
  gap: .2rem; min-width: 14rem; font-size: .8rem; }
.sig-menu button { text-align: left; border: none; background: #f6f6f6; border-radius: 4px; padding: .2rem .4rem; cursor: pointer; }
.sig-menu button:hover { background: #ffe8a1; }
.sig-merci { position: absolute; bottom: 130%; right: -2rem; z-index: 50; background: #198754; color: #fff;
  font-size: .75rem; padding: .25rem .5rem; border-radius: 6px; white-space: nowrap; box-shadow: 0 2px 8px rgba(0,0,0,.15); }
</style>
