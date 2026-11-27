<template>
  <!-- PROTOTYPE JETABLE (#418) : variante C, section « Écouter les Passages » de la fiche émission -->
  <section v-if="etat.charge" class="spe card">
    <div class="spe-entete">
      <h3>🎧 Écouter les Passages <small v-if="e">({{ e.passages.length }})</small></h3>
      <label v-if="e"><input type="checkbox" v-model="enchainer"> enchaîner les passages</label>
    </div>

    <p v-if="!e" class="spe-vide">
      Pas encore de Passages : cette émission n'a pas de transcription horodatée.
      (Prototype : seules les émissions du 15/11 et du 04/10/2026 en ont.)
    </p>

    <template v-else>
      <!-- Lecteur -->
      <div class="spe-lecteur" :class="{ inactif: !actuel }">
        <template v-if="actuel">
          <button class="btn btn-primary spe-play" @click="etat.statut === 'lecture' ? pause() : reprendre()">
            {{ etat.statut === 'lecture' ? '⏸' : etat.statut === 'fini' ? '↻' : '▶' }}
          </button>
          <button class="saut" @click="sauter(-10)">−10</button>
          <button class="saut avance" @click="sauter(10)">+10</button>
          <div class="spe-info">
            <div><strong>{{ actuel.titre }}</strong> · {{ actuel.auteur }}
              <span v-if="actuel.simule" class="simule">(simulé)</span></div>
            <div class="spe-temps">
              {{ fmt(etat.position) }} dans l'émission · passage {{ fmt(etat.position - actuel.debut) }} / {{ duree(actuel) }}
              <span v-if="etat.statut === 'fini'" class="spe-fin">· ✓ fin {{ e.passages.at(-1) === actuel ? 'du dernier passage' : 'du passage' }}</span>
            </div>
            <div v-if="etat.statut === 'erreur'" class="spe-erreur">✖ {{ etat.erreur }}</div>
            <div v-else class="spe-soustitre">« {{ sousTitre }} »</div>
          </div>
          <SignalerPassage />
        </template>
        <span v-else class="spe-invite">Cliquer un livre sur la frise ou dans la liste pour écouter les critiques en parler.</span>
      </div>

      <!-- Frise -->
      <div class="spe-frise">
        <div
          v-for="(b, i) in blocs"
          :key="i"
          class="spe-bloc"
          :class="{ trou: b.trou, actif: b.p && b.p === actuel }"
          :style="{ left: pc(b.debut) + '%', width: pc(b.fin - b.debut) + '%', background: b.trou ? null : couleur(b.i) }"
          :title="b.trou ? `Trou ${fmt(b.debut)}–${fmt(b.fin)} : aucun Passage` : `${b.p.titre} ${fmt(b.debut)}–${fmt(b.fin)}`"
          @click="b.p && jouerP(b.p)"
        >{{ b.trou ? '' : b.p.titre }}</div>
        <div v-if="actuel" class="spe-curseur" :style="{ left: pc(etat.position) + '%' }"></div>
      </div>

      <!-- Liste -->
      <ol class="spe-liste">
        <li v-for="(p, i) in e.passages" :key="p.id" :class="{ actif: p === actuel }" @click="jouerP(p)">
          <span class="pastille" :style="{ background: couleur(i) }"></span>
          <span class="spe-titre">{{ p.titre }}</span>
          <span class="spe-auteur">{{ p.auteur }}</span>
          <span class="spe-bornes">{{ fmt(p.debut) }}–{{ fmt(p.fin) }}</span>
          <span class="spe-duree">{{ duree(p) }}</span>
          <span class="spe-ic">{{ p === actuel && etat.statut === 'lecture' ? '❚❚' : '▶' }}</span>
        </li>
      </ol>
      <ul v-if="e.sans_passage.length" class="spe-sans">
        <li v-for="s in e.sans_passage" :key="s.titre">
          <span class="spe-titre">{{ s.titre }}</span> · {{ s.auteur }} —
          <em>{{ s.raison === 'supprime' ? 'passage retiré à la correction' : 'pas de passage repéré' }}</em>
          <span v-if="s.simule" class="simule">(simulé)</span>
        </li>
      </ul>
    </template>
  </section>
</template>

<script>
import {
  etat, emissionParDate, jouer, pause, reprendre, sauter, fmt, duree, segmentEnCours, COULEURS,
} from './store.js';
import SignalerPassage from './SignalerPassage.vue';

export default {
  name: 'SectionPassagesEmission',
  components: { SignalerPassage },
  props: { date: { type: String, default: '' } },
  data() { return { etat, enchainer: true }; },
  computed: {
    e() { return emissionParDate(this.date); },
    actuel() { return etat.passage && etat.passage.emission === this.e ? etat.passage : null; },
    total() { return this.e.duree || this.e.passages.at(-1).fin; },
    blocs() {
      const out = [];
      this.e.passages.forEach((p, i) => {
        const prec = this.e.passages[i - 1];
        if (prec && p.debut > prec.fin + 1) out.push({ trou: true, debut: prec.fin, fin: p.debut });
        out.push({ p, i, debut: p.debut, fin: p.fin });
      });
      return out;
    },
    sousTitre() { return segmentEnCours(this.actuel, etat.position)?.[2] || '…'; },
  },
  watch: {
    enchainer(v) { if (this.actuel) etat.modeFin = v ? 'enchainer' : 'stop'; },
  },
  methods: {
    pause, reprendre, sauter, fmt, duree,
    pc(s) { return (100 * s) / this.total; },
    couleur(i) { return COULEURS[i % COULEURS.length]; },
    jouerP(p) {
      if (p === this.actuel && etat.statut === 'lecture') return pause();
      if (p === this.actuel && etat.statut === 'pause') return reprendre();
      jouer(p, { liste: this.e.passages, modeFin: this.enchainer ? 'enchainer' : 'stop' });
    },
  },
};
</script>

<style scoped>
.spe { margin-bottom: 1.5rem; padding: 1rem 1.25rem; }
.spe-entete { display: flex; align-items: center; gap: 1.5rem; }
.spe-entete h3 { margin: 0; }
.spe-mobile { margin-left: auto; font-size: .85rem; }
.spe-vide { color: #777; font-style: italic; }
.spe-lecteur { display: flex; gap: .6rem; align-items: center; margin: .8rem 0; padding: .6rem .8rem;
  background: #f4f7fb; border-radius: 10px; min-height: 4.5rem; }
.spe-lecteur.inactif { color: #777; }
.spe-play { border-radius: 50%; width: 2.6rem; height: 2.6rem; padding: 0; font-size: 1.1rem; flex: none; }
.saut { background: #fff; border: 1px solid #dc3545; color: #dc3545; border-radius: 6px; padding: .1rem .4rem; cursor: pointer; }
.saut.avance { border-color: #198754; color: #198754; }
.spe-info { flex: 1; min-width: 0; }
.spe-temps { font: .8rem monospace; color: #555; }
.spe-fin { color: #198754; }
.spe-soustitre { font-style: italic; color: #333; margin-top: .2rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.spe-erreur { color: #b02a37; }
.spe-frise { position: relative; height: 2.2rem; background: #f0f0f0; border-radius: 6px; overflow: hidden; }
.spe-bloc { position: absolute; top: 0; bottom: 0; color: #fff; font-size: .7rem; padding: .2rem .3rem;
  overflow: hidden; white-space: nowrap; text-overflow: ellipsis; cursor: pointer; border-right: 1px solid #fff; opacity: .85; }
.spe-bloc:hover, .spe-bloc.actif { opacity: 1; box-shadow: inset 0 0 0 2px #111; }
.spe-bloc.trou { background: repeating-linear-gradient(45deg, #ddd, #ddd 4px, #f6f6f6 4px, #f6f6f6 8px); cursor: default; }
.spe-curseur { position: absolute; top: 0; bottom: 0; width: 2px; background: red; pointer-events: none; }
.spe-liste { list-style: none; padding: 0; margin: .8rem 0 0; }
.spe-liste li { display: grid; grid-template-columns: 1rem 2fr 2fr 7rem 3.5rem 1.5rem; gap: .5rem; align-items: center;
  padding: .3rem .4rem; border-radius: 6px; cursor: pointer; font-size: .9rem; }
.spe-liste li:hover { background: #f4f7fb; }
.spe-liste li.actif { background: #e3edff; font-weight: 600; }
.pastille { width: .8rem; height: .8rem; border-radius: 50%; }
.spe-auteur { color: #555; }
.spe-bornes, .spe-duree { font: .8rem monospace; color: #555; }
.spe-ic { color: #0d6efd; }
.spe-sans { list-style: none; padding: 0 0 0 1.9rem; margin: .4rem 0 0; color: #999; font-size: .85rem; }
.spe-titre { font-weight: 600; }
.simule { color: #c60; font-size: .75rem; }
</style>
