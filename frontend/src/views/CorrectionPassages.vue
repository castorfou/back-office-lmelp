<template>
  <!--
    Page « Correction des passages » (Issue #427) : reproduit le prototype validé
    (branche prototype/correction-passages, #398, #400, #401). Chaque correction est
    enregistrée par le serveur, qui renvoie l'état de l'émission.
  -->
  <div class="correction-passages">
    <Navigation pageTitle="Correction des passages" />
    <main>
      <section class="selecteur card">
        <div v-if="chargement">Chargement des émissions…</div>
        <div v-else-if="erreur" class="erreur">✖ {{ erreur }}</div>
        <div v-else-if="!emissions.length" class="vide">Aucune émission.</div>
        <div v-else class="form-group">
          <label class="form-label">
            Choisir une émission ({{ emissions.length }} :
            🟢 {{ compte.passages_valides }} validées / 🟠 {{ compte.segments_dispo }} à corriger /
            🔴 {{ compte.segments_absents }} sans Segments)
          </label>
          <div class="ligne-selecteur">
            <button class="nav-episode-btn" :disabled="index <= 0" @click="decaler(-1)">◀️ Précédent</button>
            <EpisodeDropdown v-model="emissionId" :episodes="options" @update:modelValue="choisir" />
            <button class="nav-episode-btn" :disabled="index >= emissions.length - 1" @click="decaler(1)">Suivant ▶️</button>
          </div>
        </div>
      </section>

      <section v-if="emission" class="card corps">
        <div v-if="statut(emission) === 'segments_absents'" class="vide">
          🔴 Pas de Segments horodatés pour cette émission : rien à corriger tant qu'elle n'est pas retranscrite.
        </div>
        <div v-else-if="erreurEmission" class="vide erreur">✖ {{ erreurEmission }}</div>
        <div v-else-if="!etat.ep" class="vide">Chargement des Segments…</div>
        <template v-else>
          <div class="barre">
            <div class="lecture">
              <button class="btn btn-primary btn-sm lire" @click="basculerLecture">{{ lecteur.enLecture ? '⏸ Pause' : '▶ Lire' }}</button>
              <button v-for="d in [-60, -30, -10]" :key="d" :class="['btn', 'btn-sm', 'saut', 'recul', `i${Math.abs(d)}`]" @click="avancer(d)">{{ d }} s</button>
              <button v-for="d in [10, 30, 60]" :key="d" :class="['btn', 'btn-sm', 'saut', 'avance', `i${d}`]" @click="avancer(d)">+{{ d }} s</button>
              <span class="pos">{{ fmt(lecteur.t) }} / {{ fmt(lecteur.duree) }}
                <span v-if="lecteur.arret != null"> · arrêt à {{ fmt(lecteur.arret) }}</span></span>
            </div>
            <div class="actions">
              <span class="resume">{{ nbPassages }} Passages · {{ etat.ep.livresSansPassage.length }} livre(s) sans Passage</span>
              <button data-test="valider" :class="['btn', 'btn-sm', valide ? 'btn-secondary' : 'btn-primary']" @click="basculerValidation">
                {{ valide ? '🟢 Passages validés (annuler)' : '✅ Valider les Passages' }}</button>
            </div>
          </div>
          <audio ref="audio" :src="audioUrl" preload="metadata"></audio>

          <TranscriptionPassages ref="tp" />

          <details class="journal">
            <summary>Journal des actions ({{ etat.ep.journal.length }})</summary>
            <ol><li v-for="(l, i) in etat.ep.journal" :key="i">{{ l }}</li></ol>
          </details>
        </template>
      </section>
    </main>
  </div>
</template>

<script>
import Navigation from '../components/Navigation.vue';
import EpisodeDropdown from '../components/EpisodeDropdown.vue';
import TranscriptionPassages from '../components/correction-passages/TranscriptionPassages.vue';
import { emissionsService, passagesService } from '../services/api';
import * as s from '../services/correctionPassages.js';
import { arreter as arreterLecteurGlobal } from '../services/lecteurPassages.js';

const PASTILLE = { valide: 'passages_valides', a_verifier: 'segments_dispo' };

export default {
  name: 'CorrectionPassages',
  components: { Navigation, EpisodeDropdown, TranscriptionPassages },
  data: () => ({ emissions: [], emissionId: null, chargement: true, erreur: null, erreurEmission: null }),
  computed: {
    etat: () => s.etat,
    lecteur: () => s.lecteur,
    options() {
      return this.emissions.map((e) => ({
        id: e.id, _id: e.id, date: e.date, titre: e.episode?.titre || 'Sans titre',
        badge_status: this.statut(e), has_cached_books: null, has_incomplete_books: null,
      }));
    },
    compte() {
      const c = { passages_valides: 0, segments_dispo: 0, segments_absents: 0 };
      for (const e of this.emissions) c[this.statut(e)] += 1;
      return c;
    },
    emission() { return this.emissions.find((e) => e.id === this.emissionId) || null; },
    index() { return this.emissions.findIndex((e) => e.id === this.emissionId); },
    audioUrl() { return this.emission ? `/api/episodes/${this.emission.episode_id}/audio` : null; },
    valide() { return !!s.etat.ep?.valide; },
    nbPassages() { return s.visibles().length; },
  },
  async mounted() {
    // un seul audio à la fois : le lecteur de l'application s'arrête
    arreterLecteurGlobal();
    try {
      const [emissions, statuts] = await Promise.all([
        emissionsService.getAllEmissions(),
        passagesService.getStatuts(),
      ]);
      this.emissions = emissions;
      s.etat.statuts = statuts;
    } catch (e) {
      this.erreur = `Émissions non chargées : ${e.message}`;
      return;
    } finally {
      this.chargement = false;
    }
    // un lien (signalement) peut désigner l'émission et le Passage à ouvrir
    const { episode, passage } = this.$route?.query || {};
    const premier = (episode && this.emissions.find((e) => e.episode_id === episode))
      || this.emissions.find((e) => s.etat.statuts[e.episode_id]) || this.emissions[0];
    if (premier) await this.choisir(premier.id, passage);
  },
  beforeUnmount() {
    s.debrancherAudio();
    s.fermer();
  },
  methods: {
    fmt: s.fmt,
    avancer: s.avancer,
    basculerLecture: s.basculerLecture,
    basculerValidation: s.basculerValidation,
    statut(e) {
      return PASTILLE[s.etat.statuts[e.episode_id]] || 'segments_absents';
    },
    decaler(d) { const e = this.emissions[this.index + d]; if (e) this.choisir(e.id); },
    /** Ouvre une émission, et met en avant un de ses Passages s'il est donné. */
    async choisir(id, passageId = null) {
      this.emissionId = id;
      this.erreurEmission = null;
      s.fermer();
      const e = this.emission;
      if (!e || this.statut(e) === 'segments_absents') return;
      let data;
      try {
        data = await passagesService.getCorrectionEpisode(e.episode_id);
      } catch (err) {
        if (this.emissionId === id) this.erreurEmission = `Passages non chargés : ${err.message}`;
        return;
      }
      if (this.emissionId !== id) return;
      s.charger(e.episode_id, data);
      await this.$nextTick();
      if (this.$refs.audio) s.brancherAudio(this.$refs.audio);
      const cible = passageId && s.etat.ep.passages.find((p) => p.id === passageId);
      if (cible) this.$refs.tp?.cibler(cible);
    },
  },
};
</script>

<style scoped>
.correction-passages :deep(.navigation) { margin-bottom: 0; }
.correction-passages { position: fixed; inset: 0; z-index: 10; background: #f5f6fa; display: flex; flex-direction: column; overflow: hidden; }
main { flex: 1; min-height: 0; width: 100%; max-width: 1400px; margin: 0 auto; padding: .6rem 1rem;
  display: flex; flex-direction: column; box-sizing: border-box; }
.selecteur { flex: none; padding: .6rem 1rem; }
.corps { flex: 1; min-height: 0; display: flex; flex-direction: column; margin-bottom: 0; }
.corps > :deep(.edition) { flex: 1; min-height: 0; }
.card { background: #fff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,.08); padding: 1rem; margin-bottom: .6rem; }
.ligne-selecteur { display: flex; gap: .5rem; align-items: center; }
.ligne-selecteur :deep(select) { flex: 1; }
.form-label { display: block; margin-bottom: .4rem; font-weight: 600; }
/* repris de Emissions.vue */
.nav-episode-btn { padding: .5rem 1rem; background: #0066cc; color: white; border: none; border-radius: 4px;
  cursor: pointer; font-size: .9rem; white-space: nowrap; transition: background-color .2s; }
.nav-episode-btn:hover:not(:disabled) { background: #0052a3; }
.nav-episode-btn:disabled { background: #ccc; cursor: not-allowed; opacity: .6; }
/* Boutons : .btn/.btn-primary globaux (style.css), variantes reprises de BabelioControl.vue */
.btn-secondary { background: #6c757d; color: white; }
.btn-secondary:hover:not(:disabled) { background: #545b62; }
.btn-danger { background: #dc3545; color: white; }
.btn-danger:hover:not(:disabled) { background: #a71d2a; }
.btn-sm { padding: .3rem .6rem; font-size: .8rem; font-weight: 500; }

.barre { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: .5rem;
  padding-bottom: .6rem; margin-bottom: .6rem; border-bottom: 1px solid #eee; flex: none; }
.lecture .btn, .actions .btn { margin-right: .3rem; }
.lecture .lire { min-width: 5.5rem; }
/* sauts : fond blanc, rouge pour reculer, vert pour avancer, plus marqué quand le saut est grand */
.saut { background: #fff; border: 1px solid; min-width: 3.6rem; }
.recul.i10 { color: #e57373; border-color: #f1b0b7; } .recul.i30 { color: #d32f2f; border-color: #e57373; }
.recul.i60 { color: #a71d2a; border-color: #a71d2a; border-width: 2px; }
.avance.i10 { color: #66bb6a; border-color: #a5d6a7; } .avance.i30 { color: #2e7d32; border-color: #66bb6a; }
.avance.i60 { color: #1b5e20; border-color: #1b5e20; border-width: 2px; }
.recul:hover { background: #fdecea; } .avance:hover { background: #e8f5e9; }
.pos { font-family: monospace; margin-left: .4rem; }
.resume { color: #666; font-size: .85rem; margin-right: .6rem; }
.vide { padding: 2rem; text-align: center; color: #555; }
.erreur { color: #b02a37; }
.journal { flex: none; margin-top: .5rem; font-size: .8rem; max-height: 25vh; overflow-y: auto; }
</style>
