<template>
  <!-- PROTOTYPE JETABLE (#398) : lire la transcription horodatée et poser les bornes sur un Segment -->
  <div class="edition">
  <FriseApercu class="apercu" @cibler="cibler" />
  <div class="vc">
    <aside ref="cartes">
      <div v-for="p in liste" :key="p.id" :data-carte="p.id"
        :class="['carte', p.origine, { arme: arme && arme.id === p.id, choisi: choisi === p.id, autre: choisi && choisi !== p.id }]"
        :style="{ borderLeftColor: couleur(p), '--c': couleur(p) }" @click="selectionner(p)">
        <div class="t" @click.stop="cibler(p)">{{ p.titre }}</div>
        <div class="b">{{ fmt(p.debut) }}–{{ fmt(p.fin) }} · {{ fmt(p.fin - p.debut) }}
          <span :class="['badge', p.origine]">{{ p.origine === 'auto' ? 'repéré auto' : 'corrigé' }}</span></div>
        <div class="act">
          <button :class="['btn', 'btn-sm', estArme(p, 'debut') ? 'btn-primary' : 'btn-secondary']" @click="armer(p, 'debut')">⇤ Début</button>
          <button :class="['btn', 'btn-sm', estArme(p, 'fin') ? 'btn-primary' : 'btn-secondary']" @click="armer(p, 'fin')">⇥ Fin</button>
          <button class="btn btn-danger btn-sm" title="Ce n'est pas un Passage" @click="confirmerSuppression(p)">Supprimer</button>
        </div>
        <div class="act">
          <button class="btn btn-secondary btn-sm" :title="`Écouter de ${fmt(p.debut)} à ${fmt(p.debut + ECOUTE_S)}`"
            @click="ecouter(p, p.debut, p.debut + ECOUTE_S)">▶ début</button>
          <button class="btn btn-secondary btn-sm" :title="`Écouter de ${fmt(p.fin - ECOUTE_S)} à ${fmt(p.fin)}`"
            @click="ecouter(p, p.fin - ECOUTE_S, p.fin)">▶ fin</button>
          <button class="btn btn-secondary btn-sm" title="Écouter tout le Passage" @click="ecouter(p, p.debut, p.fin)">▶ tout</button>
        </div>
      </div>
      <div class="manque" v-for="l in livresSansPassage" :key="l.livre_oid">
        ⚠️ sans Passage : {{ l.titre }}
        <button class="btn btn-secondary btn-sm" @click="placerArme(l)">⇤ Poser son début</button>
      </div>
      <div class="manque" v-for="p in supprimes" :key="p.id">🗑 {{ p.titre }} <button class="btn btn-secondary btn-sm" @click="restaurer(p.id)">Restaurer</button></div>
    </aside>

    <div class="texte" ref="texte">
      <p v-if="arme" class="consigne">Cliquer le Segment où {{ arme.borne === 'debut' ? 'commence' : 'finit' }}
        « {{ arme.titre }} » · <a href="#" @click.prevent="arme = null">annuler</a></p>
      <template v-for="(sg, i) in segments" :key="i">
        <div v-for="p in debutsA(i)" :key="'h' + p.id" class="entete" :data-borne="`debut-${p.id}`" :style="{ background: couleur(p) }">
          ⇤ {{ p.titre }} <small>{{ fmt(p.debut) }}</small></div>
        <div :ref="'s' + i" :class="['seg', { courant: courant === i, cible: !!arme, transition: estTransition(sg[2]), 'dans-choisi': dansChoisi(i) }]"
          :style="{ boxShadow: bandes(sg, i) }" @click="cliquer(sg)">
          <span class="h" @click.stop="jouer(sg[0])">{{ fmt(sg[0]) }}</span> {{ sg[2] }}
        </div>
        <div v-for="p in finsA(i)" :key="'f' + p.id" class="pied" :data-borne="`fin-${p.id}`" :style="{ color: couleur(p) }">
          ⇥ fin de {{ p.titre }} <small>{{ fmt(p.fin) }}</small></div>
      </template>
    </div>
  </div>
  </div>
</template>

<script>
import * as s from './store.js';
import FriseApercu from './FriseApercu.vue';

const TRANSITION = /\bon (commence|encha[iî]ne|continue|termine|poursuit|passe|finit)\b|\bapr[eè]s (ce|cette)\b|\b[A-Z][a-zé]+ \?$/i;

export default {
  name: 'TranscriptionPassages',
  components: { FriseApercu },
  data: () => ({ arme: null, ECOUTE_S: 15 }),
  computed: {
    segments: () => s.etat.ep.segments,
    choisi: () => s.etat.choisi,
    liste() { return s.visibles(); },
    supprimes() { return s.etat.ep.passages.filter((p) => p.supprime); },
    livresSansPassage() { return s.etat.ep.livresSansPassage; },
    courant() {
      const t = s.lecteur.t;
      return this.segments.findIndex((sg) => t >= sg[0] && t < sg[1]);
    },
    // index du segment qui contient chaque borne
    idx() {
      const sg = this.segments;
      // Bornes en secondes entières, Segments tronqués à la seconde :
      // début -> 1er Segment qui commence à partir du début ; fin -> dernier Segment fini à la fin.
      const d = (t) => { const i = sg.findIndex((x) => Math.floor(x[0]) >= t); return i < 0 ? sg.length - 1 : i; };
      const f = (t) => { let i = -1; sg.forEach((x, k) => { if (Math.floor(x[1]) <= t) i = k; }); return Math.max(i, 0); };
      return Object.fromEntries(this.liste.map((p) => [p.id, { d: d(p.debut), f: f(p.fin) }]));
    },
  },
  watch: {
    // Suivi de lecture : ne bouge le texte que si la ligne en cours sort de la zone visible,
    // et la remet alors en haut (pas de recentrage permanent).
    courant(i) {
      const el = this.$refs['s' + i]?.[0];
      const cont = this.$refs.texte;
      if (!el || !cont || !s.lecteur.enLecture) return;
      const r = el.getBoundingClientRect();
      const c = cont.getBoundingClientRect();
      if (r.top < c.top || r.bottom > c.bottom) this.defiler(cont, el, 8);
    },
  },
  methods: {
    ...s,
    debutsA(i) { return this.liste.filter((p) => this.idx[p.id]?.d === i); },
    finsA(i) { return this.liste.filter((p) => this.idx[p.id]?.f === i); },
    bandes(sg, i) {
      const ps = this.liste.filter((p) => this.idx[p.id] && this.idx[p.id].d <= i && i <= this.idx[p.id].f);
      return ps.map((p, k) => `inset ${4 + k * 4}px 0 0 ${this.couleur(p)}`).join(', ') || 'none';
    },
    estTransition(txt) { return TRANSITION.test(txt); },
    estArme(p, b) { return this.arme && this.arme.id === p.id && this.arme.borne === b; },
    armer(p, borne) { this.arme = this.estArme(p, borne) ? null : { id: p.id, titre: p.titre, borne }; },
    placerArme(l) { this.arme = { livre: l, titre: l.titre, borne: 'debut' }; },
    cliquer(sg) {
      if (!this.arme) return s.jouer(sg[0]);
      const a = this.arme;
      this.arme = null;
      if (a.livre) return s.placer(a.livre, Math.floor(sg[0]), Math.floor(sg[0]) + 60);
      if (a.borne === 'debut') s.setDebut(a.id, Math.floor(sg[0]));
      else s.setFin(a.id, Math.floor(sg[1])); // = début du Segment suivant, tronqué
      // garder la borne déplacée sous les yeux
      this.$nextTick(() => {
        const el = this.$refs.texte?.querySelector(`[data-borne="${a.borne}-${a.id}"]`);
        el?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
      });
    },
    confirmerSuppression(p) {
      if (!confirm(`Supprimer le Passage « ${p.titre} » (${s.fmt(p.debut)}–${s.fmt(p.fin)}) ?\nUne relance du repérage ne le recréera pas.`)) return;
      s.supprimer(p.id);
    },
    dansChoisi(i) {
      const r = this.choisi && this.idx[this.choisi];
      return !!r && r.d <= i && i <= r.f;
    },
    // Tout clic dans une carte (lecture, Début, Fin…) met son livre en avant à gauche et
    // dans la frise, sans déplacer le texte (pendant la lecture, il suit déjà l'audio).
    selectionner(p) {
      if (s.etat.choisi === p.id) return;
      s.etat.choisi = p.id;
    },
    // Cibler un Passage (frise ou titre de carte) : carte mise en avant à gauche,
    // texte amené à son début et ses Segments surlignés.
    cibler(p) {
      s.etat.choisi = p.id;
      this.$nextTick(() => {
        this.defiler(this.$refs.cartes, this.$refs.cartes?.querySelector(`[data-carte="${p.id}"]`), 8);
        this.defiler(this.$refs.texte, this.$refs.texte?.querySelector(`[data-borne="debut-${p.id}"]`), 8);
      });
    },
    // deux scrollIntoView doux simultanés s'interrompent : on fait défiler chaque conteneur
    defiler(cont, el, marge) {
      if (!cont || !el) return;
      const top = cont.scrollTop + el.getBoundingClientRect().top - cont.getBoundingClientRect().top - marge;
      cont.scrollTo({ top, behavior: 'smooth' });
    },
    // Boutons de lecture d'une carte : le texte part du haut, au bandeau du livre si la
    // lecture commence à son début, sinon au Segment où elle commence.
    ecouter(p, de, jusqua) {
      s.jouer(de, jusqua);
      this.$nextTick(() => {
        const t = this.$refs.texte;
        let el = de === p.debut ? t?.querySelector(`[data-borne="debut-${p.id}"]`) : null;
        if (!el) {
          const i = this.segments.findIndex((sg) => sg[1] > de);
          el = this.$refs['s' + i]?.[0];
        }
        this.defiler(t, el, 8);
      });
    },
    aller(t) {
      const i = this.segments.findIndex((sg) => sg[1] > t);
      this.$refs['s' + i]?.[0]?.scrollIntoView({ block: 'start', behavior: 'smooth' });
    },
  },
};
</script>

<style scoped>
/* 4/5 édition, 1/5 aperçu */
.edition { display: flex; flex-direction: column; gap: .6rem; min-height: 0; }
.vc { flex: 4; display: flex; gap: 1rem; min-height: 0; }
.apercu { flex: 1; min-height: 70px; }
aside { width: 300px; flex: none; overflow-y: auto; }
.carte { border-left: 5px solid; padding: .25rem .5rem; margin-bottom: .3rem; background: #fafafa; border-radius: 3px; font-size: .82rem; }
.carte.corrige { background: #fff8e1; } .carte.arme { outline: 2px dashed #000; }
.carte { transition: opacity .2s, box-shadow .2s; }
.carte.choisi { box-shadow: 0 0 0 2px var(--c), 0 3px 10px rgba(0,0,0,.15); background: #fff; }
.carte.autre { opacity: .55; } .carte.autre:hover { opacity: 1; }
.carte .t { font-weight: 600; cursor: pointer; } .carte .b { color: #555; font-family: monospace; font-size: .75rem; }
.act { display: flex; gap: .25rem; margin-top: .25rem; } .manque .btn { margin-left: .3rem; }
/* Boutons : .btn/.btn-primary globaux (style.css), variantes reprises de BabelioControl.vue */
.btn-secondary { background: #6c757d; color: white; }
.btn-secondary:hover:not(:disabled) { background: #545b62; }
.btn-danger { background: #dc3545; color: white; }
.btn-danger:hover:not(:disabled) { background: #a71d2a; }
.btn-sm { padding: .3rem .6rem; font-size: .8rem; font-weight: 500; }

.manque { font-size: .8rem; margin: .4rem 0; }
.texte { flex: 1; overflow-y: auto; border: 1px solid #e0e0e0; border-radius: 4px; padding: .5rem 1rem; font-size: .88rem; line-height: 1.45; }
.seg { padding: 1px 0 1px 18px; cursor: pointer; }
.seg:hover { background: #f5f5f5; } .seg.cible:hover { background: #fff59d; }
.seg.dans-choisi { background: #f1f6fd; } .seg.courant { background: #ffebee; } .seg.transition { font-weight: 600; }
.seg .h { color: #999; font-family: monospace; font-size: .72rem; margin-right: .3rem; }
.seg .h:hover { color: #d32f2f; }
.entete { color: #fff; padding: .15rem .5rem; margin: .6rem 0 .1rem; border-radius: 3px; font-weight: 600; font-size: .8rem; }
.pied { font-size: .75rem; font-style: italic; margin: .1rem 0 .4rem 18px; }
.consigne { position: sticky; top: 0; background: #000; color: #ff0; padding: .3rem .6rem; border-radius: 4px; z-index: 1; }
.consigne a { color: #fff; }
.badge { padding: 0 .3rem; border-radius: 3px; font-size: .68rem; } .badge.auto { background: #e3f2fd; } .badge.corrige { background: #ffe082; }
.danger { color: #b00020; }
</style>
