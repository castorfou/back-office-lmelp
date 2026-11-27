<template>
  <!-- PROTOTYPE JETABLE (#418) : configuration de lmelp-mobile (QR de la clé d'écoute), jamais fusionnée -->
  <div>
    <Navigation pageTitle="Configuration mobile" />
    <main class="cm">
      <button class="cm-retour" @click="retour">← Retour</button>
      <div v-if="!cle" class="loading">Chargement…</div>
      <template v-else>
        <!-- Remise de la clé -->
        <section class="card cm-carte">
          <div class="cm-qr">
            <svg :viewBox="`0 0 ${N} ${N}`" class="qr" shape-rendering="crispEdges">
              <rect :width="N" :height="N" fill="#fff" />
              <rect v-for="(c, i) in modules" :key="i" :x="c[0]" :y="c[1]" width="1" height="1" fill="#111" />
            </svg>
            <small class="cm-faux">faux QR (prototype : bibliothèque qrcode non installée)</small>
          </div>
          <div class="cm-texte">
            <h2>Écouter les Passages sur lmelp-mobile</h2>
            <ol>
              <li>Dans lmelp-mobile, ouvrir <strong>Réglages › Écoute des passages</strong>.</li>
              <li>Toucher <strong>Scanner le QR code</strong> et viser ce code.</li>
              <li>Les Passages s'écoutent alors depuis la fiche livre et la fiche émission, en ligne.</li>
            </ol>
            <details>
              <summary>Saisie manuelle</summary>
              <dl>
                <dt>Adresse</dt>
                <dd><code>{{ cle.base_publique }}</code></dd>
                <dt>Clé d'écoute</dt>
                <dd>
                  <code>{{ voir ? cle.cle : '•'.repeat(12) }}</code>
                  <button class="cm-petit" @click="voir = !voir">{{ voir ? 'Masquer' : 'Afficher' }}</button>
                  <button class="cm-petit" @click="copier">{{ copie ? 'Copié ✓' : 'Copier le lien' }}</button>
                </dd>
              </dl>
            </details>
            <p class="cm-note">
              Clé en service depuis le {{ dateHeure(cle.creee_le) }}. Elle est partagée par tout le
              cercle des auditeurs : ne la diffusez pas.
            </p>
          </div>
        </section>

        <!-- Invalidation -->
        <section class="card cm-danger">
          <h3>Invalider le QR code</h3>
          <p>
            À faire si le QR code ou la clé a circulé hors du cercle des auditeurs. Une nouvelle clé
            remplace l'actuelle : <strong>l'ancienne est refusée aussitôt</strong>, et chaque auditeur
            doit scanner le nouveau code dans lmelp-mobile pour continuer à écouter.
            L'écoute dans lmelp n'est pas concernée.
          </p>
          <button class="cm-invalider" :disabled="enCours" @click="invalider">
            {{ enCours ? 'Invalidation…' : '🔄 Invalider et générer un nouveau QR code' }}
          </button>
          <p v-if="fait" class="cm-fait">✓ Nouvelle clé créée le {{ dateHeure(cle.creee_le) }}. L'ancienne est refusée.</p>
        </section>
      </template>
    </main>
  </div>
</template>

<script>
import axios from 'axios';
import Navigation from '../components/Navigation.vue';

export default {
  name: 'ConfigurationMobilePrototype',
  components: { Navigation },
  data() { return { cle: null, voir: false, copie: false, enCours: false, fait: false, N: 29 }; },
  computed: {
    lien() {
      return `lmelp://ecoute?base=${encodeURIComponent(this.cle.base_publique)}&cle=${encodeURIComponent(this.cle.cle)}`;
    },
    modules() {
      // Motif pseudo-aléatoire dérivé du lien (change avec la clé), avec les 3 repères d'un vrai QR
      const N = this.N;
      let h = 0;
      for (const ch of this.lien) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
      const out = [];
      const repere = (x, y) => {
        const dx = x - (x < 8 ? 0 : N - 7);
        const dy = y - (y < 8 ? 0 : N - 7);
        if (dx < 0 || dy < 0 || dx > 6 || dy > 6) return false;
        return dx === 0 || dx === 6 || dy === 0 || dy === 6 || (dx > 1 && dx < 5 && dy > 1 && dy < 5);
      };
      for (let y = 0; y < N; y++) {
        for (let x = 0; x < N; x++) {
          const dansRepere = (x < 8 && y < 8) || (x > N - 9 && y < 8) || (x < 8 && y > N - 9);
          let noir;
          if (dansRepere) noir = repere(x, y);
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
  async mounted() {
    this.cle = (await axios.get('/api/prototype-lecteurs/cle')).data;
  },
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
    async invalider() {
      if (!confirm("Invalider le QR code actuel ?\n\nL'ancienne clé sera refusée aussitôt : chaque auditeur devra scanner le nouveau code dans lmelp-mobile.")) return;
      this.enCours = true;
      try {
        this.cle = (await axios.post('/api/prototype-lecteurs/cle/invalider')).data;
        this.voir = false;
        this.fait = true;
      } finally {
        this.enCours = false;
      }
    },
    dateHeure(iso) {
      return new Date(iso).toLocaleString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit' });
    },
  },
};
</script>

<style scoped>
.cm { max-width: 900px; margin: 2rem auto; padding: 0 1rem; }
.cm-retour { margin-bottom: 1rem; padding: .5rem 1.2rem; background: #e0e0e0; border: none;
  border-radius: 6px; color: #2c3e50; font-size: 1rem; cursor: pointer; }
.cm-retour:hover { background: #bdbdbd; }
.cm-carte { display: flex; gap: 2rem; padding: 2rem; align-items: flex-start; margin-bottom: 1.5rem; }
.cm-qr { display: flex; flex-direction: column; align-items: center; gap: .4rem; }
.qr { width: 240px; height: 240px; border: 8px solid #fff; box-shadow: 0 0 0 1px #ddd; }
.cm-faux { color: #c60; font-size: .75rem; max-width: 240px; text-align: center; }
.cm-texte h2 { margin-top: 0; }
.cm-texte dl { display: grid; grid-template-columns: auto 1fr; gap: .4rem 1rem; align-items: center; }
.cm-texte dd { margin: 0; display: flex; gap: .5rem; align-items: center; }
.cm-petit { padding: .15rem .5rem; font-size: .8rem; background: #e0e0e0; border: none; border-radius: 4px; cursor: pointer; }
.cm-note { color: #666; font-size: .9rem; margin-top: 1.2rem; }
.cm-danger { padding: 1.5rem 2rem; border: 1px solid #f1aeb5; background: #fff8f8; }
.cm-danger h3 { margin-top: 0; color: #b02a37; }
.cm-invalider { background: #fff; color: #dc3545; border: 1px solid #dc3545; border-radius: 6px;
  padding: .5rem 1rem; font-size: .95rem; cursor: pointer; }
.cm-invalider:hover:not(:disabled) { background: #dc3545; color: #fff; }
.cm-fait { color: #198754; margin-top: .8rem; }
</style>
