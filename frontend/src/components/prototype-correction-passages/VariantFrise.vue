<template>
  <!-- Variante B : frise de l'épisode entier, poignées à glisser, panneau du Passage choisi -->
  <div class="vf">
    <div class="graduations">
      <span v-for="m in minutes" :key="m" :style="{ left: pct(m * 60) }">{{ m }}′</span>
    </div>
    <div class="piste" ref="piste" @click="cliquerPiste">
      <div class="tete" :style="{ left: pct(lecteur.t) }"></div>
      <div v-for="(p, i) in liste" :key="p.id"
        :class="['bloc', p.origine, { choisi: choisi === p.id }]"
        :style="{ left: pct(val(p, 'debut')), width: pct(val(p, 'fin') - val(p, 'debut')), top: (i % 2) * 34 + 'px' }"
        @click.stop="choisi = p.id" :title="`${p.titre} ${fmt(p.debut)}–${fmt(p.fin)}`">
        <span class="poignee g" @mousedown.stop.prevent="saisir(p, 'debut', $event)"></span>
        <span class="nom">{{ p.titre }}</span>
        <span class="poignee d" @mousedown.stop.prevent="saisir(p, 'fin', $event)"></span>
      </div>
    </div>
    <p class="aide">Glisser une poignée pour déplacer une borne · cliquer la piste pour écouter à partir de là ·
      un bloc jaune est corrigé.</p>

    <div class="panneaux">
      <div class="panneau" v-if="sel">
        <h4>{{ sel.titre }} <small>— {{ sel.auteur }}</small> <span :class="['badge', sel.origine]">{{ sel.origine }}</span></h4>
        <div class="ligne">Début <strong>{{ fmt(sel.debut) }}</strong>
          <button v-for="d in [-5, -1, 1, 5]" :key="'d' + d" @click="setDebut(sel.id, sel.debut + d)">{{ d > 0 ? '+' : '' }}{{ d }}</button>
          <button @click="jouer(sel.debut, sel.debut + 15)">▶</button>
          <button @click="setDebut(sel.id, position())">⤓ position du lecteur ({{ fmt(lecteur.t) }})</button>
        </div>
        <div class="ligne">Fin <strong>{{ fmt(sel.fin) }}</strong>
          <button v-for="d in [-5, -1, 1, 5]" :key="'f' + d" @click="setFin(sel.id, sel.fin + d)">{{ d > 0 ? '+' : '' }}{{ d }}</button>
          <button @click="jouer(sel.fin - 15, sel.fin)">▶</button>
          <button @click="setFin(sel.id, position())">⤓ position du lecteur ({{ fmt(lecteur.t) }})</button>
        </div>
        <div class="ligne">Durée {{ fmt(sel.fin - sel.debut) }}
          <span v-if="sel.ecoute" class="indice">· à l'écoute (#391) : {{ fmt(sel.ecoute[0]) }}–{{ fmt(sel.ecoute[1]) }}</span>
        </div>
        <button @click="jouer(sel.debut, sel.fin)">▶ écouter le Passage</button>
        <button class="danger" @click="supprimer(sel.id); choisi = null">🗑 Ce n'est pas un Passage</button>
      </div>
      <div class="panneau" v-else><em>Choisir un Passage sur la frise.</em></div>

      <div class="panneau hors">
        <h4>Hors frise</h4>
        <div v-for="l in livresSansPassage" :key="l.livre_oid" class="puce manquant">
          ⚠️ {{ l.titre }}
          <button @click="placer(l.livre_oid, position(), position() + 60)">➕ placer à {{ fmt(lecteur.t) }}</button>
        </div>
        <div v-for="p in supprimes" :key="p.id" class="puce supp">
          🗑 {{ p.titre }} <button @click="restaurer(p.id)">↩</button>
        </div>
        <p v-if="!livresSansPassage.length && !supprimes.length"><em>rien</em></p>
      </div>
    </div>
  </div>
</template>

<script>
import * as s from './store.js';

export default {
  name: 'VariantFrise',
  data: () => ({ choisi: null, drag: null }),
  computed: {
    lecteur: () => s.lecteur,
    liste() { return s.visibles(); },
    supprimes() { return s.passages.filter((p) => p.supprime); },
    livresSansPassage() { return s.livresSansPassage; },
    sel() { return s.passages.find((p) => p.id === this.choisi && !p.supprime) || null; },
    minutes() { return Array.from({ length: Math.ceil(s.episode.duree / 300) }, (_, i) => i * 5); },
  },
  methods: {
    ...s,
    pct(sec) { return `${(sec / s.episode.duree) * 100}%`; },
    val(p, borne) { return this.drag && this.drag.id === p.id && this.drag.borne === borne ? this.drag.v : p[borne]; },
    secondes(ev) {
      const r = this.$refs.piste.getBoundingClientRect();
      return Math.round(Math.min(1, Math.max(0, (ev.clientX - r.left) / r.width)) * s.episode.duree);
    },
    cliquerPiste(ev) { s.jouer(this.secondes(ev)); },
    saisir(p, borne, ev) {
      this.choisi = p.id;
      this.drag = { id: p.id, borne, v: p[borne] };
      const move = (e) => { this.drag.v = this.secondes(e); };
      const up = () => {
        window.removeEventListener('mousemove', move);
        window.removeEventListener('mouseup', up);
        const { v } = this.drag;
        this.drag = null;
        if (v !== p[borne]) (borne === 'debut' ? s.setDebut : s.setFin)(p.id, v);
      };
      window.addEventListener('mousemove', move);
      window.addEventListener('mouseup', up);
    },
  },
};
</script>

<style scoped>
.graduations { position: relative; height: 1.1rem; font-size: .7rem; color: #888; }
.graduations span { position: absolute; transform: translateX(-50%); }
.piste { position: relative; height: 72px; background: repeating-linear-gradient(90deg, #fafafa 0 2px, #f0f0f0 2px 4px);
  border: 1px solid #ddd; border-radius: 4px; cursor: crosshair; user-select: none; }
.tete { position: absolute; top: 0; bottom: 0; width: 2px; background: #d32f2f; z-index: 3; pointer-events: none; }
.bloc { position: absolute; height: 30px; margin-top: 4px; background: #90caf9; border: 1px solid #1e88e5;
  border-radius: 3px; overflow: hidden; display: flex; align-items: center; font-size: .7rem; cursor: pointer; opacity: .9; }
.bloc.corrige { background: #ffe082; border-color: #f9a825; }
.bloc.choisi { outline: 2px solid #000; z-index: 2; }
.bloc .nom { flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; padding: 0 2px; }
.poignee { width: 6px; align-self: stretch; background: rgba(0,0,0,.35); cursor: ew-resize; flex: none; }
.aide { font-size: .75rem; color: #777; }
.panneaux { display: flex; gap: 1rem; }
.panneau { flex: 2; border: 1px solid #e0e0e0; border-radius: 6px; padding: .6rem; }
.panneau.hors { flex: 1; }
.ligne { margin: .3rem 0; } .ligne button, .panneau button { font-size: .75rem; margin-left: .2rem; cursor: pointer; }
.badge { padding: .1rem .4rem; border-radius: 4px; font-size: .7rem; }
.badge.auto { background: #e3f2fd; } .badge.corrige { background: #ffe082; }
.puce { margin: .3rem 0; font-size: .85rem; } .danger { color: #b00020; } .indice { color: #888; font-size: .8rem; }
</style>
