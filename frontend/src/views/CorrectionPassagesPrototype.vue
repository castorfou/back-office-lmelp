<template>
  <!--
    PROTOTYPE JETABLE — page « Correction des passages » (wayfinder #398), jamais fusionné.
    Segments : seulement les 2 épisodes témoins (15/11 et 04/10/2026).
    Corrections et validation en mémoire du navigateur, perdues au rechargement.
  -->
  <div class="correction-passages">
    <Navigation pageTitle="Correction des passages" />
    <main>
      <section class="selecteur card">
        <div v-if="chargement">Chargement des émissions…</div>
        <div v-else class="form-group">
          <label class="form-label">
            Choisir une émission ({{ emissions.length }} :
            🟢 {{ compte.passages_valides }} validées / 🟠 {{ compte.segments_dispo }} à corriger /
            🔴 {{ compte.segments_absents }} sans Segments)
            <span class="bandeau">PROTOTYPE · rien n'est enregistré (rechargement = remise à zéro)</span>
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
        <div v-else-if="!etat.ep" class="vide">Chargement des Segments…</div>
        <template v-else>
          <div class="barre">
            <div class="lecture">
              <button @click="basculerLecture">{{ lecteur.enLecture ? '⏸' : '▶' }}</button>
              <button v-for="d in [-60, -30, -10]" :key="d" @click="avancer(d)">{{ d }} s</button>
              <button v-for="d in [10, 30, 60]" :key="d" @click="avancer(d)">+{{ d }} s</button>
              <span class="pos">{{ fmt(lecteur.t) }} / {{ fmt(lecteur.duree) }}
                <span v-if="lecteur.arret != null"> · arrêt à {{ fmt(lecteur.arret) }}</span></span>
            </div>
            <div class="actions">
              <span class="resume">{{ nbPassages }} Passages · {{ etat.ep.livresSansPassage.length }} livre(s) sans Passage</span>
              <button @click="relancer">🔄 Relancer le repérage</button>
              <button :class="['valider', { fait: valide }]" @click="basculerValidation">
                {{ valide ? '🟢 Passages validés (annuler)' : '✅ Valider les Passages' }}</button>
            </div>
          </div>
          <audio ref="audio" :src="audioUrl" preload="metadata"></audio>

          <TranscriptionPassages />

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
import axios from 'axios';
import Navigation from '../components/Navigation.vue';
import EpisodeDropdown from '../components/EpisodeDropdown.vue';
import TranscriptionPassages from '../components/prototype-correction-passages/TranscriptionPassages.vue';
import { emissionsService } from '../services/api';
import * as s from '../components/prototype-correction-passages/store.js';

export default {
  name: 'CorrectionPassagesPrototype',
  components: { Navigation, EpisodeDropdown, TranscriptionPassages },
  data: () => ({ emissions: [], avecSegments: new Set(), emissionId: null, chargement: true }),
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
    audioUrl() { return this.emission ? `/api/prototype-passages/episodes/${this.emission.episode_id}/audio?date=${this.emission.date.slice(0, 10)}` : null; },
    valide() { return s.etat.valides.has(this.emission?.episode_id); },
    nbPassages() { return s.visibles().length; },
  },
  async mounted() {
    const [emissions, segs] = await Promise.all([
      emissionsService.getAllEmissions(),
      axios.get('/api/prototype-passages/segments-disponibles'),
    ]);
    this.emissions = emissions;
    this.avecSegments = new Set(segs.data);
    this.chargement = false;
    const premier = emissions.find((e) => this.avecSegments.has(e.episode_id)) || emissions[0];
    if (premier) this.choisir(premier.id);
  },
  methods: {
    ...s,
    statut(e) {
      if (s.etat.valides.has(e.episode_id)) return 'passages_valides';
      return this.avecSegments.has(e.episode_id) ? 'segments_dispo' : 'segments_absents';
    },
    decaler(d) { const e = this.emissions[this.index + d]; if (e) this.choisir(e.id); },
    async choisir(id) {
      this.emissionId = id;
      s.etat.ep = null;
      const e = this.emission;
      if (!e || !this.avecSegments.has(e.episode_id)) return;
      const { data } = await axios.get(`/api/prototype-passages/episodes/${e.episode_id}`, { params: { date: e.date.slice(0, 10) } });
      if (this.emissionId !== id) return;
      s.charger(data);
      await this.$nextTick();
      s.brancherAudio(this.$refs.audio);
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
.corps > :deep(.vc) { flex: 1; min-height: 0; height: auto; }
.card { background: #fff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,.08); padding: 1rem; margin-bottom: .6rem; }
.bandeau { background: repeating-linear-gradient(45deg, #ffeb3b 0 12px, #fff59d 12px 24px);
  font: 600 11px monospace; padding: .1rem .5rem; border-radius: 4px; margin-left: 1rem; }
.ligne-selecteur { display: flex; gap: .5rem; align-items: center; }
.ligne-selecteur :deep(select) { flex: 1; }
.form-label { display: block; margin-bottom: .4rem; font-weight: 600; }
.nav-episode-btn { white-space: nowrap; cursor: pointer; }
.barre { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: .5rem;
  padding-bottom: .6rem; margin-bottom: .6rem; border-bottom: 1px solid #eee; flex: none; }
.lecture button, .actions button { cursor: pointer; margin-right: .3rem; }
.lecture button:first-child { font-size: 1.1rem; width: 2.4rem; }
.pos { font-family: monospace; margin-left: .4rem; }
.resume { color: #666; font-size: .85rem; margin-right: .6rem; }
.valider { font-weight: 600; } .valider.fait { background: #e8f5e9; }
.vide { padding: 2rem; text-align: center; color: #555; }
.journal { flex: none; margin-top: .5rem; font-size: .8rem; max-height: 25vh; overflow-y: auto; }
</style>
