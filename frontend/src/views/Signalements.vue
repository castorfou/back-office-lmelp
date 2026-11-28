<template>
  <!-- Signalements ouverts de Passages mal découpés (Issue #427, US 19 à 21) -->
  <div>
    <Navigation pageTitle="Passages signalés" />
    <main class="sg">
      <div v-if="chargement" class="loading">Chargement des signalements…</div>
      <div v-else-if="erreur" class="sg-erreur">✖ Signalements non chargés : {{ erreur }}</div>
      <div v-else-if="!signalements.length" class="sg-vide">✓ Aucun signalement ouvert.</div>
      <template v-else>
        <p class="sg-aide">
          Un signalement se clôt quand le Passage est corrigé dans « Correction des passages », ou
          quand on le rejette.
        </p>
        <table class="sg-table">
          <thead>
            <tr>
              <th>Émission</th><th>Livre</th><th>Motif</th><th>Instant</th><th>Commentaire</th>
              <th>Signalé le</th><th>Source</th><th>Bornes</th><th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="s in signalements" :key="s.id" data-test="signalement">
              <td>{{ dateLongue(s.date) }}</td>
              <td>{{ s.titre || '—' }}</td>
              <td>{{ libelleMotif(s.motif) }}</td>
              <td class="sg-temps">{{ formaterDuree(s.instant_ms / 1000) }}</td>
              <td class="sg-commentaire">{{ s.commentaire || '' }}</td>
              <td>{{ dateHeure(s.cree_le) }}</td>
              <td>{{ s.source }}</td>
              <td data-test="bornes" :class="['sg-temps', { changees: bornesChangees(s) }]">
                écoutées {{ bornes(s.bornes_ecoutees) }}
                <template v-if="!s.bornes_actuelles"><br />plus de Passage</template>
                <template v-else-if="bornesChangees(s)"><br />maintenant {{ bornes(s.bornes_actuelles) }}</template>
              </td>
              <td class="sg-actions">
                <router-link
                  v-if="s.passage_id"
                  data-test="corriger"
                  class="btn btn-primary btn-sm"
                  :to="{ path: '/correction-passages', query: { episode: s.episode_id, passage: s.passage_id } }"
                >Corriger</router-link>
                <button type="button" data-test="rejeter" class="btn btn-outline btn-sm" @click="rejeter(s)">Rejeter</button>
              </td>
            </tr>
          </tbody>
        </table>
        <p v-if="erreurRejet" class="sg-erreur">✖ {{ erreurRejet }}</p>
      </template>
    </main>
  </div>
</template>

<script>
import Navigation from '../components/Navigation.vue';
import { signalementsService } from '@/services/api';
import { formaterDuree } from '../services/lecteurPassages.js';
import { libelleMotif } from '../utils/motifsSignalement.js';

export default {
  name: 'Signalements',
  components: { Navigation },
  data() {
    return { signalements: [], chargement: true, erreur: null, erreurRejet: null };
  },
  async mounted() {
    try {
      this.signalements = await signalementsService.lister();
    } catch (e) {
      this.erreur = e.message;
    } finally {
      this.chargement = false;
    }
  },
  methods: {
    formaterDuree,
    libelleMotif,
    bornes(b) {
      return `${formaterDuree(b.debut_ms / 1000)} → ${formaterDuree(b.fin_ms / 1000)}`;
    },
    bornesChangees(s) {
      const a = s.bornes_actuelles;
      const e = s.bornes_ecoutees;
      return !a || a.debut_ms !== e.debut_ms || a.fin_ms !== e.fin_ms;
    },
    async rejeter(s) {
      if (!confirm(`Rejeter le signalement sur « ${s.titre || 'ce Passage'} » ? Le Passage reste tel quel.`)) return;
      this.erreurRejet = null;
      try {
        await signalementsService.rejeter(s.id);
        this.signalements = this.signalements.filter((x) => x.id !== s.id);
      } catch (e) {
        this.erreurRejet = `Signalement non rejeté : ${e.message}`;
      }
    },
    dateLongue(date) {
      if (!date) return '—';
      return new Date(`${date}T12:00:00`).toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' });
    },
    dateHeure(iso) {
      return new Date(iso).toLocaleString('fr-FR', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
    },
  },
};
</script>

<style scoped>
.sg { max-width: 1300px; margin: 2rem auto; padding: 0 1rem; }
.sg-aide { color: #666; font-size: .9rem; }
.sg-vide { padding: 2rem; text-align: center; color: #198754; background: #fff; border-radius: 8px; }
.sg-erreur { color: #b02a37; margin-top: .8rem; }
.sg-table { width: 100%; border-collapse: collapse; background: #fff; border-radius: 8px; overflow: hidden;
  box-shadow: 0 2px 8px rgba(0,0,0,.08); font-size: .9rem; }
.sg-table th { background: #f8f9fa; text-align: left; padding: .6rem; font-weight: 600; }
.sg-table td { padding: .6rem; border-top: 1px solid #eee; vertical-align: top; }
.sg-temps { font-family: monospace; white-space: nowrap; }
.sg-temps.changees { color: #8a5a00; }
.sg-commentaire { max-width: 18rem; }
.sg-actions { white-space: nowrap; }
.sg-actions .btn { margin-right: .3rem; text-decoration: none; }
.btn-sm { padding: .3rem .6rem; font-size: .8rem; font-weight: 500; }
.btn-outline { background: #fff; color: #b02a37; border: 1px solid #b02a37; border-radius: 4px; cursor: pointer; }
.btn-outline:hover { background: #fdecea; }
</style>
