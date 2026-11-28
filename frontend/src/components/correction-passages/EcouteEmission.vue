<template>
  <div class="ee">
    <!-- La transcription de « Correction des passages » sous le tableau de livres-auteurs -->
    <div class="ee-barre">
      <div class="lecture">
        <button class="btn btn-primary btn-sm lire" @click="basculerLecture">{{ lecteur.enLecture ? '⏸ Pause' : '▶ Lire' }}</button>
        <button v-for="d in [-30, -10]" :key="d" :class="['btn', 'btn-sm', 'saut', 'recul', `i${Math.abs(d)}`]" @click="avancer(d)">{{ d }} s</button>
        <button v-for="d in [10, 30]" :key="d" :class="['btn', 'btn-sm', 'saut', 'avance', `i${d}`]" @click="avancer(d)">+{{ d }} s</button>
        <span class="pos">{{ fmt(lecteur.t) }} / {{ fmt(lecteur.duree) }}
          <span v-if="lecteur.arret != null"> · arrêt à {{ fmt(lecteur.arret) }}</span></span>
      </div>
      <span v-if="enCours" class="ee-encours">🎧 {{ enCours.titre }}</span>
    </div>
    <audio ref="audio" :src="audioUrl" preload="metadata"></audio>
    <TranscriptionPassages v-if="pret" ref="tp" />
  </div>
</template>

<script>
import TranscriptionPassages from './TranscriptionPassages.vue';
import * as cp from '../../services/correctionPassages.js';
import { ecoute, passageDe } from '../../services/ecouteEmission.js';

export default {
  name: 'EcouteEmission',
  components: { TranscriptionPassages },
  computed: {
    lecteur: () => cp.lecteur,
    audioUrl() { return `/api/episodes/${ecoute.episodeId}/audio`; },
    cible: () => ecoute.cible,
    pret: () => !!cp.etat.ep,
    enCours() {
      const t = cp.lecteur.t;
      return cp.visibles().find((p) => t >= p.debut && t < p.fin) || null;
    },
  },
  watch: {
    cible() { this.appliquer(); },
  },
  mounted() {
    cp.brancherAudio(this.$refs.audio);
    if (ecoute.cible) this.$nextTick(() => this.appliquer());
  },
  beforeUnmount() {
    cp.debrancherAudio();
  },
  methods: {
    basculerLecture: cp.basculerLecture,
    avancer: cp.avancer,
    fmt: cp.fmt,
    appliquer() {
      const c = ecoute.cible;
      const tp = this.$refs.tp;
      if (!c || !tp) return;
      const p = passageDe(c.book);
      if (p) {
        tp.cibler(p);
        tp.ecouter(p, p.debut, p.fin);
        return;
      }
      // Livre sans Passage : mettre « À placer » en évidence
      const zone = this.$el.querySelector('.a-placer');
      if (zone) {
        zone.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
        zone.classList.remove('ee-flash');
        void zone.offsetWidth;
        zone.classList.add('ee-flash');
      }
    },
  },
};
</script>

<style scoped>
.ee { display: flex; flex-direction: column; height: 100%; min-height: 0; background: #fff; }
.ee > :deep(.edition) { flex: 1; min-height: 0; }
.ee-barre { display: flex; align-items: center; gap: .6rem; flex-wrap: wrap; flex: none;
  padding-bottom: .5rem; margin-bottom: .5rem; border-bottom: 1px solid #eee; }
.lecture .btn { margin-right: .3rem; }
.lecture .lire { min-width: 5.5rem; }
.saut { background: #fff; border: 1px solid; min-width: 3.2rem; }
.recul.i10 { color: #e57373; border-color: #f1b0b7; } .recul.i30 { color: #d32f2f; border-color: #e57373; }
.avance.i10 { color: #66bb6a; border-color: #a5d6a7; } .avance.i30 { color: #2e7d32; border-color: #66bb6a; }
.btn-sm { padding: .3rem .6rem; font-size: .8rem; font-weight: 500; }
.pos { font-family: monospace; margin-left: .3rem; }
.ee-encours { flex: 1; min-width: 0; font-weight: 600; color: #0d47a1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.ee :deep(.ee-flash) { animation: flash 1.6s ease 2; }
@keyframes flash { 50% { box-shadow: 0 0 0 4px #ff9800; } }
</style>
