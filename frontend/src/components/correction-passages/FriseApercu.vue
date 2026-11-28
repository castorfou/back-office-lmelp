<template>
  <!--
    Frise de l'émission : vue d'ensemble des Passages, sert de menu pour cibler un Passage.
    Trous : hachurés, écoutables ; on y dépose un livre « À placer » (il prend tout le trou).
    Un trou de plus de 2 min est mis en évidence : un livre manque probablement.
    Livre placé à la main : un clic ouvre son menu (tout / première partie / dernière partie /
    remettre à placer) ; on peut aussi le glisser vers « À placer ».
  -->
  <div class="frise" ref="frise">
    <div class="graduations">
      <span v-for="m in minutes" :key="m" :style="{ left: pct(m * 60) }">{{ m }}′</span>
    </div>
    <div class="piste" ref="piste">
      <div class="tete" :style="{ left: pct(lecteur.t) }"></div>
      <div v-for="t in trous" :key="t.id" :class="['trou', { long: t.long, depot: !!glisse, survol: survol === t.id }]"
        :style="{ left: pct(t.debut), width: pct(t.fin - t.debut) }"
        :title="`Trou ${fmt(t.debut)}–${fmt(t.fin)} : aucun livre${t.long ? ' (plus de 2 min : un livre manque ?)' : ''}. Écouter, puis y glisser un livre « À placer »`"
        @dragover.prevent="survol = t.id" @dragleave="survol = null" @drop.prevent="deposer(t)">
        <button class="ecouter" title="Écouter le trou" @click.stop="$emit('ecouter-trou', t)">▶</button>
        <span>?</span>
      </div>
      <div v-for="(p, i) in liste" :key="p.id" :data-bloc="p.id"
        :class="['bloc', p.origine, { main: p.place_main, choisi: choisi === p.id, autre: choisi && choisi !== p.id }]"
        :style="{ left: pct(p.debut), width: pct(p.fin - p.debut), top: (i % 2) * 50 + '%', background: couleur(p) }"
        :title="p.place_main
          ? `${p.titre} · ${fmt(p.debut)}–${fmt(p.fin)} · placé à la main : cliquer pour choisir sa place, ou le glisser vers « À placer »`
          : `${p.titre} · ${fmt(p.debut)}–${fmt(p.fin)} · ${p.origine === 'auto' ? 'repéré auto' : 'corrigé'}`"
        :draggable="!!p.place_main" @dragstart="reprendre(p, $event)" @dragend="finReprendre"
        @click="cliquer(p, $event)">
        <span>{{ p.place_main ? '✋ ' : '' }}{{ p.titre }}</span>
      </div>
    </div>

    <!-- menu d'un livre placé à la main (deuxième clic) -->
    <div v-if="menuPassage" class="menu" :style="{ left: menuX + 'px' }" @click.stop>
      <div class="menu-titre">{{ menuPassage.titre }} <button class="fermer" title="Fermer" @click="menu = null">✕</button></div>
      <button @click="choisir('tout')" title="Le livre occupe tout l'espace libre autour de lui">■ Tout le trou</button>
      <button @click="choisir('tete')" title="Coupé en deux : le livre prend la première partie, un autre livre viendra après">◧ Première partie</button>
      <button @click="choisir('fin')" title="Coupé en deux : le livre prend la dernière partie, un autre livre viendra avant">◨ Dernière partie</button>
      <button class="retour" @click="remettre" title="Retirer ce livre de la frise et le remettre dans « À placer »">↩ Remettre à placer</button>
    </div>
  </div>
</template>

<script>
import * as s from '../../services/correctionPassages.js';

export default {
  name: 'FriseApercu',
  emits: ['cibler', 'ecouter-trou'],
  data: () => ({ survol: null, menu: null, menuX: 0 }),
  computed: {
    lecteur: () => s.lecteur,
    choisi: () => s.etat.choisi,
    glisse: () => s.etat.glisse,
    episode: () => s.etat.ep,
    trous: () => s.trous(),
    liste() { return s.visibles(); },
    menuPassage() { return this.menu && s.etat.ep ? s.etat.ep.passages.find((p) => p.id === this.menu) || null : null; },
    duree() {
      const sg = s.etat.ep?.segments || [];
      return Math.max(s.lecteur.duree || 0, sg.length ? sg[sg.length - 1][1] : 1);
    },
    minutes() { return Array.from({ length: Math.ceil(this.duree / 300) }, (_, i) => i * 5); },
  },
  watch: {
    episode() { this.menu = null; }, // menu fermé quand on change d'émission
  },
  methods: {
    fmt: s.fmt,
    couleur: s.couleur,
    pct(sec) { return `${(sec / this.duree) * 100}%`; },
    // dépôt sur un trou : le livre prend tout le trou ; son menu s'ouvre pour préciser sa place
    async deposer(trou) {
      this.survol = null;
      const livre = s.etat.glisse;
      s.etat.glisse = null;
      if (!livre) return;
      const p = await s.deposer(livre, trou);
      if (p) this.$nextTick(() => this.ouvrirMenu(p));
    },
    cliquer(p, ev) {
      this.$emit('cibler', p);
      if (p.place_main) this.ouvrirMenu(p, ev.currentTarget);
      else this.menu = null;
    },
    ouvrirMenu(p, el = null) {
      const bloc = el || this.$refs.piste?.querySelector(`[data-bloc="${p.id}"]`);
      if (!this.$refs.frise) return;
      const f = this.$refs.frise.getBoundingClientRect();
      const r = bloc ? bloc.getBoundingClientRect() : f;
      this.menuX = Math.min(Math.max(r.left - f.left, 0), f.width - 220);
      this.menu = p.id;
    },
    choisir(mode) {
      const p = this.menuPassage;
      if (p) s.occuper(p, mode);
      this.menu = null;
    },
    remettre() {
      const p = this.menuPassage;
      if (p) s.remettre(p);
      this.menu = null;
    },
    reprendre(p, ev) {
      if (!p.place_main) return;
      s.etat.retour = p;
      this.menu = null;
      ev.dataTransfer.effectAllowed = 'move';
      ev.dataTransfer.setData('text/plain', p.titre);
    },
    finReprendre() { s.etat.retour = null; },
  },
};
</script>

<style scoped>
.frise { display: flex; flex-direction: column; position: relative; }
.graduations { position: relative; height: 1rem; font-size: .68rem; color: #888; flex: none; }
.graduations span { position: absolute; transform: translateX(-50%); }
.piste { position: relative; flex: 1; min-height: 50px; background: #fafafa; border: 1px solid #e0e0e0; border-radius: 4px; overflow: hidden; }
.tete { position: absolute; top: 0; bottom: 0; width: 2px; background: #d32f2f; z-index: 3; pointer-events: none; }
.bloc { position: absolute; height: 48%; margin-top: 1px; border-radius: 3px; overflow: hidden; display: flex; align-items: center;
  color: #fff; font-size: .7rem; cursor: pointer; opacity: .85; box-sizing: border-box; }
.bloc.corrige { border: 2px solid #212121; opacity: 1; }
.bloc.main { border: 2px dashed #212121; cursor: grab; }
.bloc span { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; padding: 0 4px; }
.bloc:hover { opacity: 1; }
.bloc.autre { opacity: .45; }
.bloc.choisi { opacity: 1; outline: 3px solid #212121; outline-offset: -1px; z-index: 2; font-weight: 600; }
.trou { position: absolute; top: 0; bottom: 0; border: 1px dashed #999; border-radius: 3px; box-sizing: border-box;
  background: repeating-linear-gradient(45deg, #e6e6e6 0 6px, #f7f7f7 6px 12px); display: flex; align-items: center;
  justify-content: center; gap: .3rem; color: #777; font-weight: 700; z-index: 1; }
.trou.long { border: 2px dashed #e65100; color: #e65100; }
.trou.depot { border: 2px dashed #f0ad4e; background: repeating-linear-gradient(45deg, #ffe8bf 0 6px, #fff6e3 6px 12px); }
.trou.survol { background: #ffd48a; }
.trou .ecouter { background: #fff; border: 1px solid #aaa; border-radius: 4px; font-size: .7rem; padding: 0 .3rem; cursor: pointer; }
.menu { position: absolute; top: 100%; margin-top: 4px; z-index: 20; width: 220px; background: #fff; border: 1px solid #ced4da;
  border-radius: 6px; box-shadow: 0 4px 14px rgba(0,0,0,.18); padding: .3rem; display: flex; flex-direction: column; gap: .2rem; }
.menu-titre { font-size: .75rem; font-weight: 600; display: flex; justify-content: space-between; align-items: center; padding: 0 .2rem; }
.menu button { text-align: left; background: #fff; border: 1px solid #e0e0e0; border-radius: 4px; padding: .25rem .5rem;
  font-size: .8rem; cursor: pointer; }
.menu button:hover { background: #e9ecef; }
.menu .retour { color: #8a5a00; border-color: #f0ad4e; }
.menu .fermer { border: none; padding: 0 .2rem; color: #777; }
</style>
