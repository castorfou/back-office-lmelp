<template>
  <!-- PROTOTYPE JETABLE (#418) : bouton d'écoute d'un Passage, variantes A et B -->
  <span v-if="etat.charge && variante === seulement" class="pb" :class="`pb-${variante}`">
    <!-- Passage absent -->
    <template v-if="passage.absent">
      <span v-if="variante === 'A'" class="pb-absent" :title="raison">🎧 pas de passage</span>
      <span v-else class="pb-rond pb-rond-absent" :title="raison">○</span>
    </template>

    <!-- Variante A : tout se passe dans la ligne -->
    <template v-else-if="variante === 'A'">
      <button
        v-if="!enCours(passage)"
        class="pb-ecouter"
        :title="`Écouter le Passage ${fmt(passage.debut)}–${fmt(passage.fin)} de l'émission`"
        @click.stop.prevent="jouer(passage, { liste, modeFin: 'stop' })"
      >🎧 Écouter · {{ duree(passage) }}<span v-if="passage.simule" class="simule"> (simulé)</span></button>
      <span v-else class="pb-inline" @click.stop.prevent>
        <span v-if="etat.statut === 'erreur'" class="pb-erreur">✖ {{ etat.erreur }}
          <button class="pb-mini" @click="arreter()">✕</button>
        </span>
        <template v-else-if="etat.statut === 'fini'">
          <button class="pb-ecouter" @click="jouer(passage, { liste, modeFin: 'stop' })">↻ Réécouter · {{ duree(passage) }}</button>
          <span class="pb-fini">✓ fin du passage</span>
        </template>
        <template v-else>
          <span class="pb-l1">
            <button class="pb-play" :title="etat.statut === 'lecture' ? 'Pause' : 'Lire'" @click="basculer(passage, { liste, modeFin: 'stop' })">
              <svg v-if="etat.statut === 'lecture'" viewBox="0 0 10 10" width="10" height="10"><rect x="1.5" y="1" width="2.5" height="8" fill="currentColor"/><rect x="6" y="1" width="2.5" height="8" fill="currentColor"/></svg>
              <span v-else-if="etat.statut === 'chargement'">…</span>
              <svg v-else viewBox="0 0 10 10" width="10" height="10"><path d="M2.5 1 L9 5 L2.5 9 Z" fill="currentColor"/></svg>
            </button>
            <span class="pb-barre" @click="seek($event)">
              <span class="pb-rempli" :style="{ width: pct + '%' }"></span>
            </span>
            <span class="pb-temps">{{ fmt(etat.position - passage.debut) }} / {{ duree(passage) }}</span>
          </span>
          <span class="pb-l2">
            <button class="pb-lien" title="Reculer de 10 s" @click="sauter(-10)">↺ 10 s</button>
            <button class="pb-lien" title="Avancer de 10 s" @click="sauter(10)">10 s ↻</button>
            <span class="pb-sep"></span>
            <SignalerPassage />
            <button class="pb-lien" title="Arrêter" @click="arreter()">✕</button>
          </span>
        </template>
      </span>
    </template>

    <!-- Variante B : un rond, la lecture se passe dans le lecteur du bas -->
    <template v-else>
      <button
        class="pb-rond"
        :class="{ 'pb-rond-actif': enCours(passage) }"
        :title="`Écouter le Passage (${duree(passage)})`"
        @click.stop.prevent="basculer(passage, { liste, modeFin: 'proposer' })"
      >{{ enCours(passage) && etat.statut === 'lecture' ? '❚❚' : '▶' }}</button>
    </template>
  </span>
</template>

<script>
import {
  etat, passageDe, passagesDuLivre, emissionParDate, jouer, basculer, sauter, aller,
  arreter, enCours, fmt, duree,
} from './store.js';
import SignalerPassage from './SignalerPassage.vue';

const RAISONS = {
  non_repere: "Pas de Passage : le repérage n'a pas trouvé ce livre dans l'émission",
  supprime: 'Pas de Passage : il a été retiré à la correction',
  pas_de_segments: "Pas encore de Passages : l'émission n'a pas de transcription horodatée",
};

export default {
  name: 'PassageBouton',
  components: { SignalerPassage },
  props: {
    livreId: { type: String, default: null },
    date: { type: String, default: '' },
    contexte: { type: String, default: 'emission' }, // 'emission' | 'livre'
    seulement: { type: String, required: true }, // variante où ce bouton s'affiche
  },
  data() { return { etat }; },
  computed: {
    variante() {
      const v = this.$route.query.variant;
      return ['A', 'B', 'C'].includes(v) ? v : 'A';
    },
    passage() {
      if (!this.livreId) return { absent: 'non_repere' };
      return passageDe(this.livreId, this.date);
    },
    raison() { return RAISONS[this.passage.absent] || RAISONS.non_repere; },
    liste() {
      if (this.contexte === 'livre') return passagesDuLivre(this.livreId);
      return emissionParDate(this.date)?.passages || [];
    },
    pct() {
      const p = this.passage;
      return Math.min(100, (100 * (etat.position - p.debut)) / (p.fin - p.debut));
    },
  },
  methods: {
    jouer, basculer, sauter, arreter, enCours, fmt, duree,
    seek(e) {
      const r = e.currentTarget.getBoundingClientRect();
      const p = this.passage;
      aller(p.debut + ((e.clientX - r.left) / r.width) * (p.fin - p.debut));
    },
  },
};
</script>

<style scoped>
.pb { display: inline-flex; align-items: center; gap: .3rem; vertical-align: middle; }
.pb-A { display: flex; margin-top: .3rem; }
.pb-ecouter { border: 1px solid #0d6efd; background: #fff; color: #0d6efd; border-radius: 999px;
  padding: .1rem .6rem; font-size: .8rem; cursor: pointer; white-space: nowrap; }
.pb-ecouter:hover { background: #0d6efd; color: #fff; }
.pb-absent { color: #aaa; font-size: .8rem; font-style: italic; cursor: help; white-space: nowrap; }
.pb-inline { display: flex; flex-direction: column; gap: .25rem; background: #eef4ff;
  border-radius: 8px; padding: .35rem .5rem; width: 14rem; }
.pb-l1 { display: flex; align-items: center; gap: .45rem; }
.pb-l2 { display: flex; align-items: center; gap: .2rem; padding-left: 2.1rem; }
.pb-play { width: 1.65rem; height: 1.65rem; border-radius: 50%; border: none; background: #0d6efd;
  color: #fff; font-size: .7rem; cursor: pointer; flex: none; padding: 0;
  display: inline-flex; align-items: center; justify-content: center; }
.pb-barre { position: relative; flex: 1; height: 5px; background: #cfd8e6; border-radius: 3px; cursor: pointer; }
.pb-rempli { position: absolute; left: 0; top: 0; bottom: 0; background: #0d6efd; border-radius: 3px; }
.pb-temps { font: .72rem monospace; color: #555; white-space: nowrap; }
.pb-lien { border: none; background: none; color: #555; font-size: .72rem; cursor: pointer; padding: .05rem .25rem; border-radius: 4px; }
.pb-lien:hover { background: #dde7f7; color: #0d6efd; }
.pb-sep { flex: 1; }
.pb-mini { border: 1px solid #bbb; background: #fff; border-radius: 6px; font-size: .75rem; padding: 0 .35rem; cursor: pointer; }
.pb-fini { color: #198754; font-size: .8rem; }
.pb-erreur { color: #b02a37; font-size: .8rem; }
.pb-rond { width: 1.6rem; height: 1.6rem; border-radius: 50%; border: 1.5px solid #0d6efd;
  background: #fff; color: #0d6efd; font-size: .7rem; cursor: pointer; padding: 0; flex: none; }
.pb-rond:hover, .pb-rond-actif { background: #0d6efd; color: #fff; }
.pb-rond-absent { border-color: #ccc; color: #ccc; display: inline-flex; align-items: center;
  justify-content: center; cursor: help; }
.pb-B { margin-right: .35rem; }
.simule { color: #c60; }
</style>
