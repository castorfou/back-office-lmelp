<template>
  <!--
    PROTOTYPE JETABLE — « Interface de correction des Passages » (wayfinder #398).
    Trois variantes de la section Passages de la page Émission, ?variant=A|B|C.
    Données : épisode témoin du 15/11/2026 (repérage #391), QUELLE QUE SOIT
    l'émission choisie. Tout est en mémoire : aucune écriture serveur.
  -->
  <section class="proto card">
    <div class="bandeau">PROTOTYPE · données témoin du 15/11/2026, quelle que soit l'émission choisie · rien n'est enregistré</div>
    <div class="tete">
      <h3>🎧 Passages <small>{{ nb }} Passages · {{ sans }} livre(s) sans Passage</small></h3>
      <div class="actions">
        <button @click="relancer">🔄 Relancer le repérage</button>
        <button @click="reinitialiser" title="Revenir aux données de départ du prototype">♻ remettre à zéro</button>
      </div>
    </div>
    <div class="lecteur">
      <label class="fichier">📂 Audio de l'épisode
        <input type="file" accept="audio/*" @change="choisir" /></label>
      <span v-if="lecteur.nom" class="nom">{{ lecteur.nom }}</span>
      <span v-else class="nom attention">choisir le .m4a du 15/11 (nom : {{ episode.audio }})</span>
      <audio ref="audio" :src="lecteur.src" controls preload="metadata"></audio>
      <span class="pos">{{ fmt(lecteur.t) }}<span v-if="lecteur.arret != null"> → arrêt {{ fmt(lecteur.arret) }}</span></span>
    </div>

    <VariantTableau v-if="variant === 'A'" />
    <VariantFrise v-else-if="variant === 'B'" />
    <VariantTranscription v-else />

    <details class="etat" open>
      <summary>État (journal des actions et Passages en mémoire)</summary>
      <div class="cols">
        <ol class="journal"><li v-for="(l, i) in journal" :key="i">{{ l }}</li></ol>
        <pre>{{ etat }}</pre>
      </div>
    </details>
    <PrototypeSwitcher :variants="variants" />
  </section>
</template>

<script>
import PrototypeSwitcher from '../PrototypeSwitcher.vue';
import VariantTableau from './VariantTableau.vue';
import VariantFrise from './VariantFrise.vue';
import VariantTranscription from './VariantTranscription.vue';
import * as s from './store.js';

const VARIANTS = { A: 'Tableau', B: 'Frise', C: 'Transcription' };

export default {
  name: 'PassagesCorrectionPrototype',
  components: { PrototypeSwitcher, VariantTableau, VariantFrise, VariantTranscription },
  data: () => ({ variants: VARIANTS }),
  computed: {
    variant() { const v = this.$route.query.variant; return v in VARIANTS ? v : 'A'; },
    lecteur: () => s.lecteur,
    episode: () => s.episode,
    journal: () => s.journal.value,
    nb() { return s.visibles().length; },
    sans() { return s.livresSansPassage.length; },
    etat() {
      return s.passages
        .slice().sort((a, b) => a.debut - b.debut)
        .map((p) => `${p.supprime ? '🗑' : '  '} ${s.fmt(p.debut)}–${s.fmt(p.fin)} ${p.origine.padEnd(7)} ${p.titre}`)
        .join('\n');
    },
  },
  mounted() { s.brancherAudio(this.$refs.audio); },
  methods: {
    ...s,
    choisir(e) { const f = e.target.files[0]; if (f) s.choisirFichier(f); },
  },
};
</script>

<style scoped>
.proto { margin: 1rem auto; max-width: 1400px; padding: 1rem; background: #fff; border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,.08); }
.bandeau { background: repeating-linear-gradient(45deg, #ffeb3b 0 12px, #fff59d 12px 24px); color: #000;
  font: 600 12px monospace; padding: .25rem .6rem; border-radius: 4px; margin-bottom: .6rem; }
.tete { display: flex; justify-content: space-between; align-items: center; }
.tete h3 { margin: .2rem 0; } .tete small { color: #777; font-weight: normal; font-size: .8rem; margin-left: .5rem; }
.actions button { margin-left: .4rem; cursor: pointer; }
.lecteur { display: flex; align-items: center; gap: .7rem; position: sticky; top: 76px; z-index: 5; background: #fff;
  padding: .5rem 0; border-bottom: 1px solid #eee; margin-bottom: .6rem; flex-wrap: wrap; }
.lecteur audio { height: 32px; flex: 1; min-width: 280px; }
.fichier input { font-size: .75rem; } .nom { font-size: .75rem; color: #555; max-width: 260px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.attention { color: #b26a00; } .pos { font-family: monospace; }
.etat { margin-top: 1rem; font-size: .78rem; } .cols { display: flex; gap: 1rem; }
.journal { flex: 1; max-height: 220px; overflow-y: auto; margin: 0; }
.etat pre { flex: 1; margin: 0; background: #f7f7f7; padding: .4rem; }
</style>
