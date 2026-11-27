<template>
  <!-- PROTOTYPE JETABLE (#418) : page qui remet la clé d'écoute à lmelp-mobile, jamais fusionnée -->
  <div>
    <Navigation pageTitle="Écouter depuis lmelp-mobile" />
    <main class="em">
      <button class="em-retour" @click="retour">← Retour</button>
      <div v-if="!etat.charge" class="loading">Chargement…</div>
      <div v-else class="card em-carte">
        <div class="em-qr">
          <svg :viewBox="`0 0 ${N} ${N}`" class="qr" shape-rendering="crispEdges">
            <rect :width="N" :height="N" fill="#fff" />
            <rect v-for="(c, i) in modules" :key="i" :x="c[0]" :y="c[1]" width="1" height="1" fill="#111" />
          </svg>
          <small class="em-faux">faux QR (prototype : bibliothèque qrcode non installée)</small>
        </div>
        <div class="em-texte">
          <h2>Scanner avec lmelp-mobile</h2>
          <ol>
            <li>Dans lmelp-mobile, ouvrir <strong>Réglages › Écoute des passages</strong>.</li>
            <li>Toucher <strong>Scanner le QR code</strong> et viser ce code.</li>
            <li>Les Passages s'écoutent alors depuis la fiche livre et la fiche émission, en ligne.</li>
          </ol>
          <details>
            <summary>Saisie manuelle</summary>
            <dl>
              <dt>Adresse</dt>
              <dd><code>{{ etat.donnees.base_publique }}</code></dd>
              <dt>Clé d'écoute</dt>
              <dd>
                <code>{{ voir ? etat.donnees.cle : '•'.repeat(etat.donnees.cle.length) }}</code>
                <button class="btn btn-secondary btn-sm" @click="voir = !voir">{{ voir ? 'Masquer' : 'Afficher' }}</button>
                <button class="btn btn-secondary btn-sm" @click="copier">{{ copie ? 'Copié ✓' : 'Copier le lien' }}</button>
              </dd>
            </dl>
          </details>
          <p class="em-note">
            Cette clé est partagée par tout le cercle des auditeurs : ne la diffusez pas.
            Quand elle change, chacun doit scanner le nouveau code.
          </p>
        </div>
      </div>
    </main>
  </div>
</template>

<script>
import Navigation from '../components/Navigation.vue';
import { etat, charger } from '../components/prototype-lecteurs-passages/store.js';

export default {
  name: 'EcouterMobilePrototype',
  components: { Navigation },
  data() { return { etat, voir: false, copie: false, N: 29 }; },
  computed: {
    lien() {
      const d = etat.donnees;
      return `lmelp://ecoute?base=${encodeURIComponent(d.base_publique)}&cle=${encodeURIComponent(d.cle)}`;
    },
    modules() {
      // Motif pseudo-aléatoire dérivé du lien, avec les 3 repères d'un vrai QR
      const N = this.N;
      let h = 0;
      for (const ch of this.lien) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
      const out = [];
      const repere = (x, y) => {
        const dx = x - (x < 8 ? 0 : N - 7);
        const dy = y - (y < 8 ? 0 : N - 7);
        if (dx < 0 || dy < 0 || dx > 6 || dy > 6) return null;
        return dx === 0 || dx === 6 || dy === 0 || dy === 6 || (dx > 1 && dx < 5 && dy > 1 && dy < 5);
      };
      for (let y = 0; y < N; y++) {
        for (let x = 0; x < N; x++) {
          const dansRepere = (x < 8 && y < 8) || (x > N - 9 && y < 8) || (x < 8 && y > N - 9);
          let noir;
          if (dansRepere) noir = repere(x, y) === true;
          else {
            h = (h * 1103515245 + 12345) >>> 0;
            noir = (h >>> 16) % 2 === 0;
          }
          if (noir) out.push([x, y]);
        }
      }
      return out;
    },
  },
  async mounted() { await charger(); },
  methods: {
    retour() {
      if (window.history.state?.back) this.$router.back();
      else this.$router.push('/');
    },
    async copier() {
      await navigator.clipboard?.writeText(this.lien);
      this.copie = true;
      setTimeout(() => { this.copie = false; }, 2000);
    },
  },
};
</script>

<style scoped>
.em { max-width: 900px; margin: 2rem auto; padding: 0 1rem; }
.em-retour { margin-bottom: 1rem; padding: .5rem 1.2rem; background: #e0e0e0; border: none;
  border-radius: 6px; color: #2c3e50; font-size: 1rem; cursor: pointer; }
.em-retour:hover { background: #bdbdbd; }
.em-carte { display: flex; gap: 2rem; padding: 2rem; align-items: flex-start; }
.em-qr { display: flex; flex-direction: column; align-items: center; gap: .4rem; }
.qr { width: 240px; height: 240px; border: 8px solid #fff; box-shadow: 0 0 0 1px #ddd; }
.em-faux { color: #c60; font-size: .75rem; max-width: 240px; text-align: center; }
.em-texte h2 { margin-top: 0; }
.em-texte dl { display: grid; grid-template-columns: auto 1fr; gap: .4rem 1rem; align-items: center; }
.em-texte dd { margin: 0; display: flex; gap: .5rem; align-items: center; }
.em-note { color: #666; font-size: .9rem; margin-top: 1.2rem; }
.btn-sm { padding: .15rem .5rem; font-size: .8rem; }
</style>
