<template>
  <!-- Configuration de lmelp-mobile : QR code de la clé d'écoute (Issue #427, prototype #418) -->
  <div>
    <Navigation pageTitle="Configuration mobile" />
    <main class="cm">
      <button class="cm-retour" @click="retour">← Retour</button>
      <div v-if="erreur" class="cm-erreur">✖ Clé d'écoute non chargée : {{ erreur }}</div>
      <div v-else-if="!cle" class="loading">Chargement…</div>
      <template v-else>
        <!-- Remise de la clé -->
        <section class="card cm-carte">
          <div class="cm-qr">
            <img v-if="qr" :src="qr" class="qr" alt="QR code de la clé d'écoute" />
            <div v-else-if="!base" class="cm-sans-adresse" data-test="sans-adresse">
              Pas de QR code : l'adresse de lmelp-streaming se déduit de celle de lmelp
              (<code>lmelp.&lt;domaine&gt;</code> → <code>lmelp-streaming.&lt;domaine&gt;</code>).
              Ouvrez cette page par son adresse <code>lmelp.…</code>.
            </div>
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
                <dd><code>{{ base || '—' }}</code></dd>
                <dt>Clé d'écoute</dt>
                <dd>
                  <code>{{ voir ? cle.cle : '•'.repeat(12) }}</code>
                  <button class="cm-petit" data-test="voir-cle" @click="voir = !voir">{{ voir ? 'Masquer' : 'Afficher' }}</button>
                  <button v-if="base" class="cm-petit" data-test="copier-lien" @click="copier">{{ copie ? 'Copié ✓' : 'Copier le lien' }}</button>
                </dd>
              </dl>
            </details>
            <p class="cm-note" data-test="historique">
              Clé en service depuis le {{ dateHeure(cle.creee_le) }}<template v-if="cle.changements.length">
                · changée {{ cle.changements.length }} fois, la dernière le
                {{ dateHeure(cle.changements[cle.changements.length - 1]) }}</template>.
              Elle est partagée par tout le cercle des auditeurs : ne la diffusez pas.
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
          <button class="cm-invalider" data-test="invalider" :disabled="enCours" @click="invalider">
            {{ enCours ? 'Invalidation…' : '🔄 Invalider et générer un nouveau QR code' }}
          </button>
          <p v-if="fait" class="cm-fait">✓ Nouvelle clé créée le {{ dateHeure(cle.creee_le) }}. L'ancienne est refusée.</p>
          <p v-if="erreurInvalidation" class="cm-erreur">✖ {{ erreurInvalidation }}</p>
        </section>
      </template>
    </main>
  </div>
</template>

<script>
import QRCode from 'qrcode';
import Navigation from '../components/Navigation.vue';
import { cleEcouteService } from '../services/api';
import { adresseStreaming } from '../utils/adresseStreaming';

export default {
  name: 'ConfigurationMobile',
  components: { Navigation },
  data() {
    return {
      cle: null, qr: null, erreur: null, erreurInvalidation: null,
      voir: false, copie: false, enCours: false, fait: false,
      base: adresseStreaming(window.location),
    };
  },
  computed: {
    lien() {
      if (!this.cle || !this.base) return null;
      return `lmelp://ecoute?base=${encodeURIComponent(this.base)}&cle=${encodeURIComponent(this.cle.cle)}`;
    },
  },
  watch: {
    lien: {
      async handler(lien) {
        this.qr = lien ? await QRCode.toDataURL(lien, { width: 240, margin: 1 }) : null;
      },
    },
  },
  async mounted() {
    try {
      this.cle = await cleEcouteService.lire();
    } catch (e) {
      this.erreur = e.message;
    }
  },
  beforeUnmount() {
    clearTimeout(this.minuterieCopie);
  },
  methods: {
    retour() {
      if (window.history.state?.back) this.$router.back();
      else this.$router.push('/');
    },
    async copier() {
      await navigator.clipboard?.writeText(this.lien);
      this.copie = true;
      clearTimeout(this.minuterieCopie);
      this.minuterieCopie = setTimeout(() => { this.copie = false; }, 2000);
    },
    async invalider() {
      if (!confirm("Invalider le QR code actuel ?\n\nL'ancienne clé sera refusée aussitôt : chaque auditeur devra scanner le nouveau code dans lmelp-mobile.")) return;
      this.enCours = true;
      this.erreurInvalidation = null;
      try {
        this.cle = await cleEcouteService.invalider();
        this.voir = false;
        this.fait = true;
      } catch (e) {
        this.erreurInvalidation = `Clé non invalidée : ${e.message}`;
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
.cm-qr { display: flex; flex-direction: column; align-items: center; gap: .4rem; flex: none; }
.qr { width: 240px; height: 240px; border: 8px solid #fff; box-shadow: 0 0 0 1px #ddd; }
.cm-sans-adresse { width: 240px; padding: 1rem; border: 1px dashed #f0ad4e; background: #fff8e6;
  border-radius: 6px; color: #8a5a00; font-size: .85rem; }
.cm-texte h2 { margin-top: 0; }
.cm-texte dl { display: grid; grid-template-columns: auto 1fr; gap: .4rem 1rem; align-items: center; }
.cm-texte dd { margin: 0; display: flex; gap: .5rem; align-items: center; flex-wrap: wrap; }
.cm-petit { padding: .15rem .5rem; font-size: .8rem; background: #e0e0e0; border: none; border-radius: 4px; cursor: pointer; }
.cm-note { color: #666; font-size: .9rem; margin-top: 1.2rem; }
.cm-danger { padding: 1.5rem 2rem; border: 1px solid #f1aeb5; background: #fff8f8; }
.cm-danger h3 { margin-top: 0; color: #b02a37; }
.cm-invalider { background: #fff; color: #dc3545; border: 1px solid #dc3545; border-radius: 6px;
  padding: .5rem 1rem; font-size: .95rem; cursor: pointer; }
.cm-invalider:hover:not(:disabled) { background: #dc3545; color: #fff; }
.cm-fait { color: #198754; margin-top: .8rem; }
.cm-erreur { color: #b02a37; margin-top: .8rem; }
</style>
