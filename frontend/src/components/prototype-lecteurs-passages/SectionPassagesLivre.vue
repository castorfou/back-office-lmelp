<template>
  <!-- PROTOTYPE JETABLE (#418) : variante C, section « Écouter les critiques » de la fiche livre -->
  <section v-if="etat.charge" class="spl">
    <h2>🎧 Écouter les critiques en parler</h2>

    <p v-if="!passages.length && !sans.length" class="spl-vide">
      Pas encore de Passage pour ce livre : ses émissions n'ont pas de transcription horodatée.
    </p>

    <div v-for="p in passages" :key="p.id" class="spl-carte" :class="{ actif: p === etat.passage }">
      <div class="spl-haut">
        <button class="btn btn-primary spl-play" @click="clic(p)">
          {{ p === etat.passage && etat.statut === 'lecture' ? '⏸' : p === etat.passage && etat.statut === 'fini' ? '↻' : '▶' }}
        </button>
        <div class="spl-quoi">
          <router-link :to="`/emissions/${p.emission.date.replaceAll('-', '')}`">Émission du {{ dateLongue(p.emission.date) }}</router-link>
          <span class="spl-duree">{{ duree(p) }} · de {{ fmt(p.debut) }} à {{ fmt(p.fin) }}</span>
          <span v-if="p.simule" class="simule">(simulé)</span>
        </div>
        <SignalerPassage v-if="p === etat.passage" />
      </div>

      <!-- Mini-frise : où le livre se trouve dans l'émission -->
      <div class="spl-frise" :title="`Le Passage dans l'émission (${fmt(p.emission.duree)})`">
        <span class="spl-zone" :style="{ left: pc(p, p.debut) + '%', width: pc(p, p.fin - p.debut) + '%' }"></span>
        <span v-if="p === etat.passage" class="spl-curseur" :style="{ left: pc(p, etat.position) + '%' }"></span>
      </div>

      <blockquote v-if="p !== etat.passage" class="spl-citation">« {{ premieresPhrases(p) }} … »</blockquote>
      <div v-else class="spl-direct">
        <div v-if="etat.statut === 'erreur'" class="spl-erreur">✖ {{ etat.erreur }}</div>
        <template v-else>
          <span class="spl-temps">{{ fmt(etat.position - p.debut) }} / {{ duree(p) }}</span>
          <button class="saut" @click="sauter(-10)">−10</button>
          <button class="saut avance" @click="sauter(10)">+10</button>
          <em class="spl-soustitre">« {{ sousTitre }} »</em>
        </template>
        <div v-if="etat.statut === 'fini'" class="spl-fin">
          ✓ Fin du passage ·
          <router-link :to="`/emissions/${p.emission.date.replaceAll('-', '')}`">écouter les autres livres de l'émission →</router-link>
        </div>
      </div>
    </div>

    <p v-for="s in sans" :key="s.emission.date + s.titre" class="spl-sans">
      Émission du {{ dateLongue(s.emission.date) }} :
      {{ s.raison === 'supprime' ? 'passage retiré à la correction' : 'pas de passage repéré' }}
      <span v-if="s.simule" class="simule">(simulé)</span>
    </p>
  </section>
</template>

<script>
import {
  etat, passagesDuLivre, sansPassageDuLivre, basculer, sauter, fmt, duree, segmentEnCours, premieresPhrases,
} from './store.js';
import SignalerPassage from './SignalerPassage.vue';

export default {
  name: 'SectionPassagesLivre',
  components: { SignalerPassage },
  props: { livreId: { type: String, required: true } },
  data() { return { etat }; },
  computed: {
    passages() { return passagesDuLivre(this.livreId); },
    sans() { return sansPassageDuLivre(this.livreId); },
    sousTitre() { return segmentEnCours(etat.passage, etat.position)?.[2] || '…'; },
  },
  methods: {
    sauter, fmt, duree, premieresPhrases,
    clic(p) { basculer(p, { liste: this.passages, modeFin: 'stop' }); },
    pc(p, s) { return (100 * s) / (p.emission.duree || p.fin); },
    dateLongue(d) {
      return new Date(d + 'T12:00:00').toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' });
    },
  },
};
</script>

<style scoped>
.spl { margin: 1.5rem 0; }
.spl h2 { display: flex; align-items: baseline; gap: 1rem; }
.spl-mobile { font-size: .85rem; font-weight: 400; }
.spl-vide, .spl-sans { color: #888; font-style: italic; }
.spl-carte { background: #fff; border: 1px solid #e3e6ea; border-radius: 10px; padding: .8rem 1rem; margin-bottom: .8rem; }
.spl-carte.actif { border-color: #0d6efd; box-shadow: 0 0 0 2px #cfe0ff; }
.spl-haut { display: flex; gap: .8rem; align-items: center; }
.spl-play { border-radius: 50%; width: 2.4rem; height: 2.4rem; padding: 0; flex: none; }
.spl-quoi { display: flex; flex-direction: column; flex: 1; }
.spl-duree { font: .8rem monospace; color: #666; }
.spl-frise { position: relative; height: 8px; background: #eceff3; border-radius: 4px; margin: .6rem 0; }
.spl-zone { position: absolute; top: 0; bottom: 0; background: #0d6efd; border-radius: 4px; opacity: .7; }
.spl-curseur { position: absolute; top: -3px; bottom: -3px; width: 2px; background: red; }
.spl-citation { margin: 0; color: #555; font-style: italic; border-left: 3px solid #ddd; padding-left: .6rem; }
.spl-direct { display: flex; gap: .5rem; align-items: center; flex-wrap: wrap; }
.spl-temps { font: .8rem monospace; }
.saut { background: #fff; border: 1px solid #dc3545; color: #dc3545; border-radius: 6px; padding: 0 .4rem; cursor: pointer; }
.saut.avance { border-color: #198754; color: #198754; }
.spl-soustitre { flex: 1; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.spl-fin { width: 100%; color: #198754; }
.spl-erreur { color: #b02a37; }
.simule { color: #c60; font-size: .75rem; }
</style>
