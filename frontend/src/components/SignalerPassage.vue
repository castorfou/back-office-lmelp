<template>
  <!-- Signaler un Passage mal découpé, depuis le lecteur (prototype #418) -->
  <span v-if="passage && passage.livre_id" ref="racine" class="sig">
    <button type="button" class="sig-btn" title="Signaler un Passage mal découpé" @click.stop="ouvert = !ouvert">⚠️</button>
    <span v-if="ouvert" class="sig-menu" @click.stop>
      <strong>Signaler à {{ formaterDuree(instant) }}</strong>
      <textarea v-model="commentaire" maxlength="500" rows="2" placeholder="Commentaire (facultatif)"></textarea>
      <button v-for="m in MOTIFS" :key="m.valeur" type="button" class="motif" :disabled="envoi" @click="envoyer(m)">
        {{ m.libelle }}
      </button>
    </span>
    <span v-if="merci" class="sig-merci">✓ Signalé : {{ merci }}</span>
    <span v-if="erreur" class="sig-erreur">✖ Non signalé : {{ erreur }}</span>
  </span>
</template>

<script>
import { lecteur, formaterDuree } from '../services/lecteurPassages.js';
import { signalementsService } from '@/services/api';
import { MOTIFS } from '../utils/motifsSignalement.js';

const DUREE_BULLE_MS = 2500;

export default {
  name: 'SignalerPassage',
  data() {
    return { MOTIFS, ouvert: false, instant: 0, commentaire: '', merci: null, erreur: null, envoi: false };
  },
  computed: {
    passage: () => lecteur.passage,
  },
  watch: {
    ouvert(v) {
      clearTimeout(this.minuterieOuverture);
      if (v) {
        // l'instant signalé est celui où l'on ouvre le menu : l'audio continue
        // pendant qu'on écrit le commentaire
        this.instant = lecteur.position;
        this.minuterieOuverture = setTimeout(() => document.addEventListener('click', this.dehors), 0);
      } else {
        document.removeEventListener('click', this.dehors);
      }
    },
    // un autre Passage : le commentaire en cours ne le concerne pas
    passage() {
      this.ouvert = false;
      this.commentaire = '';
    },
  },
  beforeUnmount() {
    document.removeEventListener('click', this.dehors);
    clearTimeout(this.minuterieOuverture);
    clearTimeout(this.minuterieBulle);
  },
  methods: {
    formaterDuree,
    dehors(e) {
      if (!this.$refs.racine?.contains(e.target)) this.ouvert = false;
    },
    async envoyer(motif) {
      const p = this.passage;
      const { instant } = this;
      const signalement = {
        episode_id: p.episode_id, livre_id: p.livre_id, debut_ms: p.debut_ms, fin_ms: p.fin_ms,
        motif: motif.valeur, instant_ms: Math.round(instant * 1000),
      };
      const commentaire = this.commentaire.trim();
      if (commentaire) signalement.commentaire = commentaire;
      this.envoi = true;
      this.erreur = null;
      try {
        await signalementsService.creer(signalement);
        this.ouvert = false;
        this.commentaire = '';
        this.bulle('merci', `${motif.libelle} à ${formaterDuree(instant)}`);
      } catch (e) {
        this.bulle('erreur', e.message);
      } finally {
        this.envoi = false;
      }
    },
    bulle(champ, texte) {
      this.merci = null;
      this.erreur = null;
      this[champ] = texte;
      clearTimeout(this.minuterieBulle);
      this.minuterieBulle = setTimeout(() => { this[champ] = null; }, DUREE_BULLE_MS);
    },
  },
};
</script>

<style scoped>
.sig { position: relative; display: inline-flex; align-items: center; }
.sig-btn { border: none; background: none; border-radius: 6px; font-size: 1rem; cursor: pointer; padding: 0 .3rem; }
.sig-menu { position: absolute; bottom: 120%; right: -2rem; z-index: 950; background: #fff; border: 1px solid #ccc;
  border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,.15); padding: .4rem; display: flex; flex-direction: column;
  gap: .2rem; min-width: 15rem; font-size: .8rem; }
.sig-menu textarea { font: inherit; resize: vertical; border: 1px solid #ccc; border-radius: 4px; padding: .2rem .3rem; }
.sig-menu button { text-align: left; border: none; background: #f6f6f6; border-radius: 4px; padding: .2rem .4rem; cursor: pointer; }
.sig-menu button:hover:not(:disabled) { background: #ffe8a1; }
.sig-merci, .sig-erreur { position: absolute; bottom: 130%; right: -2rem; z-index: 950; color: #fff;
  font-size: .75rem; padding: .25rem .5rem; border-radius: 6px; white-space: nowrap; box-shadow: 0 2px 8px rgba(0,0,0,.15); }
.sig-merci { background: #198754; }
.sig-erreur { background: #b02a37; }
</style>
