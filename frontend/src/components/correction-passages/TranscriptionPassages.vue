<template>
  <!-- Lire la transcription horodatée et poser les bornes d'un Passage sur un Segment -->
  <div class="edition">
  <div class="haut">
    <FriseApercu class="apercu" @cibler="cibler" @ecouter-trou="ecouterTrou" />
    <div v-if="avaitAPlacer || livresSansPassage.length" :class="['a-placer', { retour: !!retour, survol: survolRetour }]"
      @dragover="surRetour($event)" @dragleave="survolRetour = false" @drop="deposerRetour($event)">
      <div class="a-placer-titre" title="Glisser un livre sur un trou ▨ de la frise : il prend tout le trou ; cliquer ensuite sur le livre placé pour choisir tout le trou, la première ou la dernière partie">
        ⚠️ À placer ({{ livresSansPassage.length }}) · glisser sur un trou ▨</div>
      <div v-for="l in livresSansPassage" :key="l.titre" class="puce" draggable="true"
        :title="`Glisser « ${l.titre} » sur un trou de la frise`"
        @dragstart="glisser(l, $event)" @dragend="finGlisser">
        <span class="poignee">⠿</span> {{ l.titre }} <small>{{ l.auteur }}</small>
      </div>
      <div v-if="!livresSansPassage.length" class="tous-places">✓ Tous les livres sont placés</div>
      <div v-if="retour" class="retour-aide">↩ Déposer ici pour remettre « {{ retour.titre }} » à placer</div>
    </div>
  </div>
  <div class="vc">
    <aside ref="cartes">
      <div v-for="p in liste" :key="p.id" :data-carte="p.id"
        :class="['carte', p.origine, { arme: arme && arme.id === p.id, choisi: choisi === p.id, autre: choisi && choisi !== p.id }]"
        :style="{ borderLeftColor: couleur(p), '--c': couleur(p) }" @click="selectionner(p)">
        <!-- Variante B : icônes seules, infobulles -->
        <div class="entete-carte">
          <span :class="['t', { 'a-valider': !p.livre_id }]" @click.stop="cibler(p)"
            :title="p.livre_id ? 'Amener le texte au début de ce Passage' : 'Titre du résumé, livre à valider · amener le texte au début de ce Passage'">{{ p.titre }}</span>
          <small v-if="!p.livre_id" class="a-valider-tag">à valider</small>
          <router-link v-else :to="`/livre/${p.livre_id}`" class="lien-livre" title="Fiche du livre" @click.stop>↗</router-link>
          <span v-if="estCourt(p)" class="court" title="Passage de moins de 30 s : borne à vérifier">⚠️</span>
          <span class="duree">{{ fmt(p.fin - p.debut) }}</span>
          <span :class="['badge', p.origine]">{{ p.origine === 'auto' ? 'repéré auto' : 'corrigé' }}</span>
        </div>
        <div class="bornes">
          <span class="borne" title="Début du Passage">⇤ {{ fmt(p.debut) }}</span>
          <button class="ico" :title="`Écouter le début (${fmt(p.debut)} → ${fmt(p.debut + ECOUTE_S)})`"
            @click="ecouter(p, p.debut, p.debut + ECOUTE_S)">🎧</button>
          <button :class="['ico', { arme: estArme(p, 'debut') }]" title="Placer le début : puis cliquer le Segment dans le texte"
            @click="armer(p, 'debut')">📍</button>
          <span class="sep"></span>
          <span class="borne" title="Fin du Passage">⇥ {{ fmt(p.fin) }}</span>
          <button class="ico" :title="`Écouter la fin (${fmt(p.fin - ECOUTE_S)} → ${fmt(p.fin)})`"
            @click="ecouter(p, p.fin - ECOUTE_S, p.fin)">🎧</button>
          <button :class="['ico', { arme: estArme(p, 'fin') }]" title="Placer la fin : puis cliquer le Segment dans le texte"
            @click="armer(p, 'fin')">📍</button>
          <span class="sep"></span>
          <button class="ico" :title="`Écouter tout le Passage (${fmt(p.debut)} → ${fmt(p.fin)})`"
            @click="ecouter(p, p.debut, p.fin)">▶</button>
          <button class="ico danger" title="Supprimer ce Passage (ce n'est pas un Passage)"
            @click="confirmerSuppression(p)">🗑</button>
        </div>
      </div>
      <div class="manque" v-for="p in supprimes" :key="p.id" :data-supprime="p.id">🗑 {{ p.titre }} <button class="btn btn-secondary btn-sm" @click="restaurer(p.id)">Restaurer</button></div>
    </aside>

    <div class="texte" ref="texte">
      <p v-if="arme" class="consigne">Cliquer le Segment où {{ arme.borne === 'debut' ? 'commence' : 'finit' }}
        « {{ arme.titre }} » · <a href="#" @click.prevent="arme = null">annuler</a></p>
      <template v-for="(sg, i) in segments" :key="i">
        <div v-for="t in trousA(i)" :key="t.id" :data-trou="t.id" :class="['trou-entete', { long: t.long }]">
          ▨ Trou {{ fmt(t.debut) }}–{{ fmt(t.fin) }} · aucun livre<template v-if="t.long"> · plus de 2 min : un livre manque ?</template>
          <button class="ico" title="Écouter le trou" @click="ecouterTrou(t)">▶</button>
          <small v-if="glisse">déposer le livre sur la phrase où il commence</small>
        </div>
        <div v-for="p in debutsA(i)" :key="'h' + p.id" class="entete" :data-borne="`debut-${p.id}`" :style="{ background: couleur(p) }">
          ⇤ {{ p.titre }} <small>{{ fmt(p.debut) }}</small></div>
        <div :ref="'s' + i" :class="['seg', { courant: courant === i, cible: !!arme, transition: estTransition(sg[2]),
            'dans-choisi': dansChoisi(i), 'dans-trou': !!trouDe(i), depot: glisse && zoneDe(i), survol: survol === i }]"
          :style="{ boxShadow: bandes(sg, i) }" @click="cliquer(sg)"
          @dragover="surSurvol(i, $event)" @dragleave="survol = null" @drop="deposerSur(i, $event)">
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
import * as s from '../../services/correctionPassages.js';
import FriseApercu from './FriseApercu.vue';

const TRANSITION = /\bon (commence|encha[iî]ne|continue|termine|poursuit|passe|finit)\b|\bapr[eè]s (ce|cette)\b|\b[A-Z][a-zé]+ \?$/i;

export default {
  name: 'TranscriptionPassages',
  components: { FriseApercu },
  data: () => ({ arme: null, ECOUTE_S: 15, survol: null, survolRetour: false }),
  computed: {
    segments: () => s.etat.ep.segments,
    choisi: () => s.etat.choisi,
    glisse: () => s.etat.glisse,
    retour: () => s.etat.retour,
    avaitAPlacer: () => !!s.etat.ep?.avaitAPlacer,
    // trous de l'émission et Segments qu'ils couvrent
    idxTrous() {
      const sg = this.segments;
      const d = (t) => { const i = sg.findIndex((x) => x[0] >= t - 0.01); return i < 0 ? sg.length - 1 : i; };
      const f = (t) => { let i = -1; sg.forEach((x, k) => { if (x[1] <= t + 0.01) i = k; }); return Math.max(i, 0); };
      return s.trous().map((t) => ({ ...t, d: d(t.debut), f: f(t.fin) }));
    },
    liste() { return s.visibles(); },
    supprimes() { return s.etat.ep.supprimes; },
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
      // Bornes à l'heure exacte d'un Segment (centièmes) : comparaison avec une tolérance de 10 ms.
      const d = (t) => { const i = sg.findIndex((x) => x[0] >= t - 0.01); return i < 0 ? sg.length - 1 : i; };
      const f = (t) => { let i = -1; sg.forEach((x, k) => { if (x[1] <= t + 0.01) i = k; }); return Math.max(i, 0); };
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
    fmt: s.fmt,
    couleur: s.couleur,
    estCourt: s.estCourt,
    jouer: s.jouer,
    restaurer: s.restaurer,
    debutsA(i) { return this.liste.filter((p) => this.idx[p.id]?.d === i); },
    finsA(i) { return this.liste.filter((p) => this.idx[p.id]?.f === i); },
    bandes(sg, i) {
      const ps = this.liste.filter((p) => this.idx[p.id] && this.idx[p.id].d <= i && i <= this.idx[p.id].f);
      return ps.map((p, k) => `inset ${4 + k * 4}px 0 0 ${this.couleur(p)}`).join(', ') || null;
    },
    estTransition(txt) { return TRANSITION.test(txt); },
    estArme(p, b) { return this.arme && this.arme.id === p.id && this.arme.borne === b; },
    armer(p, borne) { this.arme = this.estArme(p, borne) ? null : { id: p.id, titre: p.titre, borne }; },
    async cliquer(sg) {
      if (!this.arme) return s.jouer(sg[0]);
      const a = this.arme;
      this.arme = null;
      // heure exacte du Segment : deux Segments de la même seconde restent distincts
      if (a.borne === 'debut') await s.setDebut(a.id, sg[0]);
      else await s.setFin(a.id, sg[1]); // = début du Segment suivant
      // garder la borne déplacée sous les yeux
      this.$nextTick(() => {
        const el = this.$refs.texte?.querySelector(`[data-borne="${a.borne}-${a.id}"]`);
        el?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
      });
    },
    confirmerSuppression(p) {
      if (!confirm(`Supprimer le Passage « ${p.titre} » (${s.fmt(p.debut)}–${s.fmt(p.fin)}) ?\nUne relance du repérage ne le recréera pas.`)) return;
      if (s.etat.choisi === p.id) s.etat.choisi = null;
      s.supprimer(p.id);
    },
    trousA(i) { return this.idxTrous.filter((t) => t.d === i); },
    trouDe(i) { return this.idxTrous.find((t) => t.d <= i && i <= t.f) || null; },
    glisser(l, ev) {
      s.etat.glisse = l;
      ev.dataTransfer.effectAllowed = 'move';
      ev.dataTransfer.setData('text/plain', l.titre);
    },
    finGlisser() { s.etat.glisse = null; this.survol = null; },
    // reprendre un livre placé : glissé depuis la frise vers « À placer »
    surRetour(ev) {
      if (!s.etat.retour) return;
      ev.preventDefault();
      this.survolRetour = true;
    },
    deposerRetour(ev) {
      ev.preventDefault?.();
      if (s.etat.retour) s.remettre(s.etat.retour);
      s.etat.retour = null;
      this.survolRetour = false;
    },
    // phrase où l'on peut déposer : dans un trou
    zoneDe(i) {
      const t = this.trouDe(i);
      return t ? { trou: t } : null;
    },
    surSurvol(i, ev) {
      if (!s.etat.glisse || !this.zoneDe(i)) return;
      ev.preventDefault(); // autorise le dépôt sur un Segment d'un trou
      this.survol = i;
    },
    // dépôt dans le texte : le livre commence à la phrase choisie
    deposerSur(i, ev) {
      ev.preventDefault?.();
      const z = this.zoneDe(i);
      const l = s.etat.glisse;
      if (l && z?.trou) s.deposer(l, z.trou, i === z.trou.d ? null : this.segments[i][0]);
      this.finGlisser();
    },
    ecouterTrou(t) {
      s.jouer(t.debut, t.fin);
      this.$nextTick(() => this.defiler(this.$refs.texte, this.$refs.texte?.querySelector(`[data-trou="${t.id}"]`), 8));
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
.haut { flex: 1; min-height: 70px; display: flex; gap: .6rem; }
.apercu { flex: 1; min-width: 0; }
.a-placer { width: 300px; flex: none; overflow-y: auto; }
aside { width: 345px; flex: none; overflow-y: auto; }
.carte { border-left: 5px solid; padding: .25rem .5rem; margin-bottom: .3rem; background: #fafafa; border-radius: 3px; font-size: .82rem; }
.carte.corrige { background: #fff8e1; } .carte.arme { outline: 2px dashed #000; }
.carte { transition: opacity .2s, box-shadow .2s; }
.carte.choisi { box-shadow: 0 0 0 2px var(--c), 0 3px 10px rgba(0,0,0,.15); background: #fff; }
.carte.autre { opacity: .55; } .carte.autre:hover { opacity: 1; }
.entete-carte { display: flex; align-items: baseline; gap: .4rem; }
.carte .t { font-weight: 600; cursor: pointer; flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.carte .t:hover { text-decoration: underline; }
.carte .t.a-valider { font-style: italic; font-weight: 500; }
.a-valider-tag { font-size: .68rem; color: #8a5a00; white-space: nowrap; }
.lien-livre { text-decoration: none; color: #0d6efd; font-size: .8rem; }
.court { font-size: .8rem; cursor: help; }
.duree { font-family: monospace; font-size: .75rem; color: #555; }
.bornes { display: flex; align-items: center; gap: .2rem; margin-top: .3rem; flex-wrap: wrap; }
.borne { font-family: monospace; font-size: .78rem; color: #333; margin-right: .1rem; }
.sep { width: .35rem; }
.ico { background: #fff; border: 1px solid #ced4da; border-radius: 4px; padding: .1rem .3rem; font-size: .85rem;
  line-height: 1.2; cursor: pointer; transition: background .15s, border-color .15s; }
.ico:hover { background: #e9ecef; border-color: #adb5bd; }
.ico.arme { background: #007bff; border-color: #007bff; }
.ico.danger { margin-left: auto; border-color: #f1b0b7; } .ico.danger:hover { background: #fdecea; border-color: #dc3545; }
.act { display: flex; gap: .25rem; margin-top: .25rem; } .manque .btn { margin-left: .3rem; }
/* Boutons : .btn/.btn-primary globaux (style.css), variantes reprises de BabelioControl.vue */
.btn-secondary { background: #6c757d; color: white; }
.btn-secondary:hover:not(:disabled) { background: #545b62; }
.btn-danger { background: #dc3545; color: white; }
.btn-danger:hover:not(:disabled) { background: #a71d2a; }
.btn-sm { padding: .3rem .6rem; font-size: .8rem; font-weight: 500; }

.manque { font-size: .8rem; margin: .4rem 0; }
.a-placer { border: 1px dashed #f0ad4e; background: #fff8e6; border-radius: 4px; padding: .3rem .4rem; box-sizing: border-box; }
.a-placer.retour { border: 2px dashed #8a5a00; } .a-placer.survol { background: #ffe0a3; }
.tous-places { font-size: .8rem; color: #2e7d32; padding: .2rem 0; }
.retour-aide { font-size: .75rem; color: #8a5a00; font-weight: 600; padding: .2rem 0; }
.a-placer-titre { font-size: .72rem; color: #8a5a00; margin-bottom: .1rem; cursor: help; }
.puce { background: #fff; border: 1px solid #f0ad4e; border-radius: 4px; padding: .1rem .4rem; margin: .15rem 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  font-size: .82rem; font-weight: 600; cursor: grab; }
.puce small { font-weight: normal; color: #777; } .puce .poignee { color: #bbb; margin-right: .2rem; }
.puce:active { cursor: grabbing; }
.trou-entete { margin: .6rem 0 .1rem; padding: .15rem .5rem; border-radius: 3px; font-size: .8rem; font-weight: 600; color: #555;
  background: repeating-linear-gradient(45deg, #eee 0 6px, #f8f8f8 6px 12px); border: 1px dashed #aaa; }
.trou-entete.long { border: 2px dashed #e65100; color: #e65100; }
.trou-entete small { font-weight: normal; color: #8a5a00; margin-left: .4rem; }
.seg.dans-trou { color: #666; box-shadow: inset 4px 0 0 #ccc; }
.seg.depot { outline: 1px dashed #f0ad4e; } .seg.survol { background: #ffe0a3 !important; }
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
