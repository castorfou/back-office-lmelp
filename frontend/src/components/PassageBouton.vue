<template>
  <!-- Rond devant le titre d'un livre : lit son Passage dans le lecteur du bas -->
  <button
    v-if="passage"
    type="button"
    class="passage-rond"
    :class="{ actif: enLecture }"
    :aria-label="enLecture ? 'Pause' : 'Écouter le Passage'"
    :title="`Écouter les critiques en parler (${duree})`"
    @click.stop.prevent="basculer(passage, liste)"
  >
    <svg v-if="enLecture" viewBox="0 0 10 10" width="9" height="9" aria-hidden="true">
      <rect x="1.5" y="1" width="2.5" height="8" fill="currentColor" />
      <rect x="6" y="1" width="2.5" height="8" fill="currentColor" />
    </svg>
    <svg v-else viewBox="0 0 10 10" width="9" height="9" aria-hidden="true">
      <path d="M2.5 1 L9 5 L2.5 9 Z" fill="currentColor" />
    </svg>
  </button>
  <span v-else class="passage-rond passage-absent" :title="motif" aria-hidden="true">○</span>
</template>

<script>
import {
  lecteur, basculer, enCours, formaterDuree, dureeSecondes,
} from '../services/lecteurPassages.js';

const MOTIFS = {
  pas_de_segments: "Pas encore de Passage : l'émission n'a pas de transcription horodatée",
  supprime: 'Pas de Passage : il a été retiré à la correction',
  non_repere: "Pas de Passage : le repérage n'a pas trouvé ce livre dans l'émission",
};

export default {
  name: 'PassageBouton',
  props: {
    /** Le Passage du livre, ou null s'il n'en a pas. */
    passage: { type: Object, default: null },
    /** Les Passages du contexte, dans l'ordre : le suivant est proposé à la fin. */
    liste: { type: Array, default: () => [] },
    /** Pourquoi il n'y a pas de Passage : pas_de_segments, supprime, non_repere. */
    raison: { type: String, default: 'non_repere' },
  },
  computed: {
    enLecture() {
      return enCours(this.passage) && lecteur.statut === 'lecture';
    },
    duree() {
      return formaterDuree(dureeSecondes(this.passage));
    },
    motif() {
      return MOTIFS[this.raison] || MOTIFS.non_repere;
    },
  },
  methods: { basculer },
};
</script>

<style scoped>
.passage-rond {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.6rem;
  height: 1.6rem;
  margin-right: 0.35rem;
  padding: 0;
  flex: none;
  vertical-align: middle;
  border: 1.5px solid #0d6efd;
  border-radius: 50%;
  background: #fff;
  color: #0d6efd;
  cursor: pointer;
}
.passage-rond:hover,
.passage-rond.actif {
  background: #0d6efd;
  color: #fff;
}
.passage-absent {
  border-color: #ccc;
  color: #bbb;
  font-size: 0.8rem;
  cursor: help;
}
</style>
