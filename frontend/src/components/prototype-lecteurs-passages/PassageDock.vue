<template>
  <!-- PROTOTYPE JETABLE (#418) : variante B, lecteur fixé en bas, garde la lecture d'une page à l'autre -->
  <div v-if="p" class="dock">
    <div class="dock-quoi">
      <router-link v-if="p.livre_id" :to="`/livre/${p.livre_id}`" class="dock-titre">{{ p.titre }}</router-link>
      <span v-else class="dock-titre">{{ p.titre }}</span>
      <span class="dock-auteur">{{ p.auteur }}</span>
      <router-link :to="`/emissions/${p.emission.date.replaceAll('-', '')}`" class="dock-emission">
        Émission du {{ dateLongue(p.emission.date) }}
      </router-link>
      <span v-if="p.simule" class="simule">Passage simulé</span>
    </div>

    <div class="dock-milieu">
      <div v-if="etat.statut === 'erreur'" class="dock-erreur">
        ✖ {{ etat.erreur }} · <router-link to="/ecouter-mobile">voir la clé d'écoute</router-link>
      </div>
      <div v-else-if="etat.statut === 'fini'" class="dock-fin">
        <span>✓ Fin du passage</span>
        <button class="btn btn-secondary" @click="reprendre()">↻ Réécouter</button>
        <button v-if="etat.suivant" class="btn btn-primary" @click="jouer(etat.suivant, { liste: etat.liste, modeFin: 'proposer' })">
          ▶ Suivant : {{ etat.suivant.titre }}
          <small v-if="etat.suivant.emission !== p.emission">({{ dateLongue(etat.suivant.emission.date) }})</small>
        </button>
        <span v-else class="dock-dernier">dernier passage {{ contexteListe }}</span>
      </div>
      <template v-else>
        <div class="dock-controles">
          <button class="saut" @click="sauter(-10)">−10 s</button>
          <button class="btn btn-primary dock-play" @click="etat.statut === 'lecture' ? pause() : reprendre()">
            {{ etat.statut === 'lecture' ? '⏸' : etat.statut === 'chargement' ? '…' : '▶' }}
          </button>
          <button class="saut avance" @click="sauter(10)">+10 s</button>
        </div>
        <div class="dock-barre-ligne">
          <span class="t">{{ fmt(etat.position - p.debut) }}</span>
          <span class="dock-barre" @click="seek($event)">
            <span class="dock-rempli" :style="{ width: pct + '%' }"></span>
          </span>
          <span class="t">{{ fmt(p.fin - p.debut) }}</span>
        </div>
      </template>
    </div>

    <div class="dock-droite">
      <SignalerPassage />
      <router-link to="/ecouter-mobile" class="dock-mobile" title="Écouter depuis lmelp-mobile">📱</router-link>
      <button class="dock-fermer" title="Fermer" @click="arreter()">✕</button>
    </div>
  </div>
</template>

<script>
import { etat, jouer, pause, reprendre, sauter, aller, arreter, fmt } from './store.js';
import SignalerPassage from './SignalerPassage.vue';

export default {
  name: 'PassageDock',
  components: { SignalerPassage },
  data() { return { etat }; },
  computed: {
    p() { return etat.passage; },
    pct() { return Math.min(100, (100 * (etat.position - this.p.debut)) / (this.p.fin - this.p.debut)); },
    contexteListe() {
      const l = etat.liste;
      if (!l.length) return '';
      return l.every((x) => x.emission === l[0].emission) ? "de l'émission" : 'de ce livre';
    },
  },
  watch: {
    p: { immediate: true, handler(v) { document.body.style.paddingBottom = v ? '6rem' : ''; } },
  },
  beforeUnmount() { document.body.style.paddingBottom = ''; },
  methods: {
    jouer, pause, reprendre, sauter, arreter, fmt,
    seek(e) {
      const r = e.currentTarget.getBoundingClientRect();
      aller(this.p.debut + ((e.clientX - r.left) / r.width) * (this.p.fin - this.p.debut));
    },
    dateLongue(d) {
      return new Date(d + 'T12:00:00').toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' });
    },
  },
};
</script>

<style scoped>
.dock { position: fixed; left: 0; right: 0; bottom: 0; z-index: 9000; height: 5.5rem;
  background: #fff; border-top: 1px solid #ddd; box-shadow: 0 -4px 14px rgba(0,0,0,.08);
  display: grid; grid-template-columns: 1fr 2fr 1fr; align-items: center; padding: 0 1.5rem; gap: 1rem; }
.dock-quoi { display: flex; flex-direction: column; min-width: 0; }
.dock-titre { font-weight: 700; color: #222; text-decoration: none; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.dock-auteur { font-size: .85rem; color: #555; }
.dock-emission { font-size: .8rem; color: #0d6efd; text-decoration: none; }
.dock-milieu { display: flex; flex-direction: column; align-items: center; gap: .3rem; }
.dock-controles { display: flex; gap: .6rem; align-items: center; }
.dock-play { border-radius: 50%; width: 2.6rem; height: 2.6rem; padding: 0; font-size: 1.1rem; }
.saut { background: #fff; border: 1px solid #dc3545; color: #dc3545; border-radius: 6px; padding: .1rem .5rem; cursor: pointer; }
.saut.avance { border-color: #198754; color: #198754; }
.dock-barre-ligne { display: flex; align-items: center; gap: .5rem; width: 100%; max-width: 36rem; }
.t { font: .8rem monospace; color: #555; }
.dock-barre { flex: 1; position: relative; height: 6px; background: #e3e6ea; border-radius: 3px; cursor: pointer; }
.dock-rempli { position: absolute; left: 0; top: 0; bottom: 0; background: #0d6efd; border-radius: 3px; }
.dock-fin { display: flex; gap: .7rem; align-items: center; color: #198754; justify-content: center; white-space: nowrap; }
.dock-fin .btn { padding: .3rem .8rem; font-size: .9rem; }
.dock-dernier { color: #777; font-size: .85rem; }
.dock-erreur { color: #b02a37; }
.dock-droite { display: flex; gap: .6rem; justify-content: flex-end; align-items: center; }
.dock-mobile { text-decoration: none; font-size: 1.1rem; }
.dock-fermer { border: none; background: none; font-size: 1.1rem; cursor: pointer; color: #777; }
.simule { color: #c60; font-size: .75rem; }
</style>
