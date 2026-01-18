<template>
  <div class="avis-table-container">
    <!-- Stats de matching (affiché si n != m ou debug) -->
    <div v-if="matchingStats && showMatchingStats" class="matching-stats">
      <div class="stats-header">
        <span class="stats-warning" v-if="matchingStats.livres_summary !== matchingStats.livres_mongo">
          ⚠️ Livres summary ({{ matchingStats.livres_summary }}) ≠ Livres Mongo ({{ matchingStats.livres_mongo }})
        </span>
      </div>
      <div class="stats-details">
        <span class="stat-item stat-phase1">Phase 1 (exact): {{ matchingStats.match_phase1 }}</span>
        <span class="stat-item stat-phase2">Phase 2 (partiel): {{ matchingStats.match_phase2 }}</span>
        <span class="stat-item stat-phase3">Phase 3 (similarité): {{ matchingStats.match_phase3 }}</span>
        <span class="stat-item stat-unmatched" v-if="matchingStats.unmatched > 0">
          ⚠ Sans match: {{ matchingStats.unmatched }}
        </span>
      </div>
    </div>

    <!-- Section 1: Livres au programme -->
    <div v-if="sortedLivresAuProgramme.length > 0" class="avis-section">
      <h4>1. LIVRES DISCUTÉS AU PROGRAMME{{ formattedDate ? ` du ${formattedDate}` : '' }}</h4>
      <table class="avis-table">
        <thead>
          <tr>
            <th class="sortable-header" @click="setSortOrder('auteur')">
              Auteur
              <span class="sort-indicator" :class="getSortClass('auteur')">↕</span>
            </th>
            <th class="sortable-header" @click="setSortOrder('titre')">
              Titre
              <span class="sort-indicator" :class="getSortClass('titre')">↕</span>
            </th>
            <th>Éditeur</th>
            <th>Avis des critiques</th>
            <th class="sortable-header" @click="setSortOrder('noteMoyenne')">
              Note moy.
              <span class="sort-indicator" :class="getSortClass('noteMoyenne')">↕</span>
            </th>
            <th>Coup de cœur</th>
            <th class="chef-oeuvre-header">Chef d'œuvre</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="livre in sortedLivresAuProgramme" :key="livre.titre">
            <td class="auteur-cell">
              <router-link
                v-if="livre.auteur_oid"
                :to="`/auteur/${livre.auteur_oid}`"
                class="auteur-link"
              >
                {{ livre.auteur }}
              </router-link>
              <span v-else>{{ livre.auteur }}</span>
            </td>
            <td class="titre-cell">
              <router-link
                v-if="livre.livre_oid"
                :to="`/livre/${livre.livre_oid}`"
                class="livre-link"
              >
                {{ livre.titre }}
              </router-link>
              <span v-else class="unresolved">
                {{ livre.titre }}
                <span class="warning-icon" title="Livre non résolu">⚠️</span>
              </span>
            </td>
            <td class="editeur-cell">{{ livre.editeur }}</td>
            <td class="avis-cell">
              <div v-for="avis in livre.avis" :key="avis.id" class="avis-item">
                <span class="critique-nom">
                  <router-link
                    v-if="avis.critique_oid"
                    :to="`/critique/${avis.critique_oid}`"
                    class="critique-link"
                  >
                    {{ avis.critique_nom_extrait }}
                  </router-link>
                  <span v-else class="unresolved">
                    {{ avis.critique_nom_extrait }}
                    <span class="warning-icon" title="Critique non résolu">⚠️</span>
                  </span>
                </span>
                <span class="avis-commentaire">: {{ avis.commentaire }}</span>
                <span v-if="avis.note" class="avis-note" :class="noteClass(avis.note)">
                  {{ avis.note }}
                </span>
              </div>
            </td>
            <td class="note-moyenne-cell">
              <span class="note-moyenne" :class="noteClass(livre.noteMoyenne)">
                {{ livre.noteMoyenne ? livre.noteMoyenne.toFixed(1) : '-' }}
              </span>
            </td>
            <td class="coup-de-coeur-cell">
              <span v-if="livre.coupDeCoeur.length > 0" class="coup-de-coeur-list">
                {{ livre.coupDeCoeur.join(', ') }}
              </span>
              <span v-else class="empty-cell">-</span>
            </td>
            <td class="chef-oeuvre-cell">
              <span v-if="livre.isChefOeuvre" class="chef-oeuvre-badge">✓</span>
              <span v-else class="empty-cell">-</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Section 2: Coups de coeur -->
    <div v-if="sortedCoupsDeCoeursAvis.length > 0" class="avis-section">
      <h4>2. COUPS DE CŒUR DES CRITIQUES{{ formattedDate ? ` du ${formattedDate}` : '' }}</h4>
      <table class="avis-table coups-de-coeur">
        <thead>
          <tr>
            <th class="sortable-header" @click="setSortOrderSection2('critique')">
              Critique
              <span class="sort-indicator" :class="getSortClassSection2('critique')">↕</span>
            </th>
            <th class="sortable-header" @click="setSortOrderSection2('auteur')">
              Auteur
              <span class="sort-indicator" :class="getSortClassSection2('auteur')">↕</span>
            </th>
            <th class="sortable-header" @click="setSortOrderSection2('titre')">
              Titre
              <span class="sort-indicator" :class="getSortClassSection2('titre')">↕</span>
            </th>
            <th>Éditeur</th>
            <th class="sortable-header" @click="setSortOrderSection2('note')">
              Note
              <span class="sort-indicator" :class="getSortClassSection2('note')">↕</span>
            </th>
            <th>Commentaire</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="avis in sortedCoupsDeCoeursAvis" :key="avis.id">
            <td class="critique-cell">
              <router-link
                v-if="avis.critique_oid"
                :to="`/critique/${avis.critique_oid}`"
                class="critique-link"
              >
                {{ avis.critique_nom_extrait }}
              </router-link>
              <span v-else class="unresolved">
                {{ avis.critique_nom_extrait }}
                <span class="warning-icon" title="Critique non résolu">⚠️</span>
              </span>
            </td>
            <td class="auteur-cell">{{ avis.auteur_nom_extrait }}</td>
            <td class="titre-cell">
              <router-link
                v-if="avis.livre_oid"
                :to="`/livre/${avis.livre_oid}`"
                class="livre-link"
              >
                {{ avis.livre_titre_officiel || avis.livre_titre_extrait }}
              </router-link>
              <span v-else class="unresolved">
                {{ avis.livre_titre_extrait }}
                <span class="warning-icon" title="Livre non résolu">⚠️</span>
              </span>
            </td>
            <td class="editeur-cell">{{ avis.editeur_extrait }}</td>
            <td class="note-cell">
              <span v-if="avis.note" class="note" :class="noteClass(avis.note)">
                {{ avis.note }}
              </span>
              <span v-else class="note-missing">-</span>
            </td>
            <td class="commentaire-cell">{{ avis.commentaire }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Message si aucun avis -->
    <div v-if="avis.length === 0" class="no-avis">
      <p>Aucun avis structuré disponible pour cette émission.</p>
    </div>
  </div>
</template>

<script>
import { computed, ref } from 'vue';

export default {
  name: 'AvisTable',

  props: {
    avis: {
      type: Array,
      required: true,
      default: () => [],
    },
    emissionDate: {
      type: String,
      default: null,
    },
    matchingStats: {
      type: Object,
      default: null,
    },
  },

  setup(props) {
    /**
     * Formate la date de l'émission en format français (ex: "21 décembre 2025")
     */
    const formattedDate = computed(() => {
      if (!props.emissionDate) return null;
      const date = new Date(props.emissionDate);
      return date.toLocaleDateString('fr-FR', {
        day: 'numeric',
        month: 'long',
        year: 'numeric',
      });
    });

    /**
     * Affiche les stats si n != m ou s'il y a des non matchés
     */
    const showMatchingStats = computed(() => {
      if (!props.matchingStats) return false;
      const stats = props.matchingStats;
      return stats.livres_summary !== stats.livres_mongo || stats.unmatched > 0;
    });

    // État du tri Section 1 (livres au programme)
    const sortField = ref('noteMoyenne');
    const sortAscending = ref(false); // Descendant par défaut pour les notes

    // État du tri Section 2 (coups de coeur)
    const sortFieldSection2 = ref('note');
    const sortAscendingSection2 = ref(false); // Descendant par défaut pour les notes

    /**
     * Groupe les avis de la Section 1 (programme) par livre
     */
    const livresAuProgramme = computed(() => {
      const programmeAvis = props.avis.filter(a => a.section === 'programme');

      // Grouper par livre (titre + auteur)
      const livresMap = new Map();

      for (const avis of programmeAvis) {
        const key = `${avis.livre_titre_extrait}|${avis.auteur_nom_extrait}`;

        if (!livresMap.has(key)) {
          livresMap.set(key, {
            titre: avis.livre_titre_extrait,
            auteur: avis.auteur_nom_extrait,
            editeur: avis.editeur_extrait,
            livre_oid: avis.livre_oid,
            auteur_oid: avis.auteur_oid,
            avis: [],
          });
        }

        livresMap.get(key).avis.push(avis);
      }

      // Calculer la note moyenne, coups de coeur et chef d'oeuvre pour chaque livre
      return Array.from(livresMap.values()).map(livre => {
        const notesValides = livre.avis.filter(a => a.note != null).map(a => a.note);
        const noteMoyenne = notesValides.length > 0
          ? notesValides.reduce((sum, n) => sum + n, 0) / notesValides.length
          : null;

        // Coups de coeur : critiques ayant mis une note >= 9
        const coupDeCoeur = livre.avis
          .filter(a => a.note != null && a.note >= 9)
          .map(a => a.critique_nom_extrait);

        // Chef d'oeuvre : au moins un critique a mis 10
        const isChefOeuvre = livre.avis.some(a => a.note === 10);

        return { ...livre, noteMoyenne, coupDeCoeur, isChefOeuvre };
      });
    });

    /**
     * Livres triés selon le champ et l'ordre sélectionnés
     */
    const sortedLivresAuProgramme = computed(() => {
      const livres = [...livresAuProgramme.value];

      livres.sort((a, b) => {
        let valA, valB;

        switch (sortField.value) {
          case 'auteur':
            valA = (a.auteur || '').toLowerCase();
            valB = (b.auteur || '').toLowerCase();
            break;
          case 'titre':
            valA = (a.titre || '').toLowerCase();
            valB = (b.titre || '').toLowerCase();
            break;
          case 'noteMoyenne':
          default:
            // Notes nulles vont à la fin
            valA = a.noteMoyenne ?? -Infinity;
            valB = b.noteMoyenne ?? -Infinity;
            break;
        }

        if (valA < valB) return sortAscending.value ? -1 : 1;
        if (valA > valB) return sortAscending.value ? 1 : -1;
        return 0;
      });

      return livres;
    });

    /**
     * Récupère les avis de la Section 2 (coups de coeur)
     */
    const coupsDeCoeursAvis = computed(() => {
      return props.avis.filter(a => a.section === 'coup_de_coeur');
    });

    /**
     * Coups de coeur triés
     */
    const sortedCoupsDeCoeursAvis = computed(() => {
      const avisArr = [...coupsDeCoeursAvis.value];

      avisArr.sort((a, b) => {
        let valA, valB;

        switch (sortFieldSection2.value) {
          case 'critique':
            valA = (a.critique_nom_extrait || '').toLowerCase();
            valB = (b.critique_nom_extrait || '').toLowerCase();
            break;
          case 'auteur':
            valA = (a.auteur_nom_extrait || '').toLowerCase();
            valB = (b.auteur_nom_extrait || '').toLowerCase();
            break;
          case 'titre':
            valA = (a.livre_titre_extrait || '').toLowerCase();
            valB = (b.livre_titre_extrait || '').toLowerCase();
            break;
          case 'note':
          default:
            valA = a.note ?? -Infinity;
            valB = b.note ?? -Infinity;
            break;
        }

        if (valA < valB) return sortAscendingSection2.value ? -1 : 1;
        if (valA > valB) return sortAscendingSection2.value ? 1 : -1;
        return 0;
      });

      return avisArr;
    });

    /**
     * Change l'ordre de tri Section 1
     */
    const setSortOrder = (field) => {
      if (sortField.value === field) {
        sortAscending.value = !sortAscending.value;
      } else {
        sortField.value = field;
        // Tri descendant par défaut pour les notes, ascendant pour le texte
        sortAscending.value = field !== 'noteMoyenne';
      }
    };

    /**
     * Retourne la classe CSS pour l'indicateur de tri Section 1
     */
    const getSortClass = (field) => {
      if (sortField.value !== field) return '';
      return sortAscending.value ? 'sort-asc' : 'sort-desc';
    };

    /**
     * Change l'ordre de tri Section 2
     */
    const setSortOrderSection2 = (field) => {
      if (sortFieldSection2.value === field) {
        sortAscendingSection2.value = !sortAscendingSection2.value;
      } else {
        sortFieldSection2.value = field;
        // Tri descendant par défaut pour les notes, ascendant pour le texte
        sortAscendingSection2.value = field !== 'note';
      }
    };

    /**
     * Retourne la classe CSS pour l'indicateur de tri Section 2
     */
    const getSortClassSection2 = (field) => {
      if (sortFieldSection2.value !== field) return '';
      return sortAscendingSection2.value ? 'sort-asc' : 'sort-desc';
    };

    /**
     * Retourne la classe CSS selon la note
     */
    const noteClass = (note) => {
      if (note == null) return '';
      if (note >= 9) return 'note-excellent';
      if (note >= 7) return 'note-good';
      if (note >= 5) return 'note-average';
      return 'note-poor';
    };

    return {
      formattedDate,
      showMatchingStats,
      sortedLivresAuProgramme,
      sortedCoupsDeCoeursAvis,
      noteClass,
      setSortOrder,
      getSortClass,
      setSortOrderSection2,
      getSortClassSection2,
    };
  },
};
</script>

<style scoped>
.avis-table-container {
  margin-top: 1.5rem;
}

.avis-section {
  margin-bottom: 2rem;
}

.avis-section h4 {
  margin: 0 0 1rem 0;
  color: #333;
  font-size: 1.1rem;
  border-bottom: 2px solid #e0e0e0;
  padding-bottom: 0.5rem;
}

.avis-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}

.avis-table th,
.avis-table td {
  padding: 0.75rem;
  text-align: left;
  border-bottom: 1px solid #e0e0e0;
  vertical-align: top;
}

.avis-table th {
  background: #f5f5f5;
  font-weight: 600;
  color: #333;
}

.avis-table tbody tr:hover {
  background: #fafafa;
}

/* En-têtes triables */
.sortable-header {
  cursor: pointer;
  user-select: none;
  position: relative;
  transition: background-color 0.2s ease;
}

.sortable-header:hover {
  background: #e9ecef;
}

.sort-indicator {
  opacity: 0.5;
  margin-left: 0.5rem;
  font-size: 0.8rem;
  transition: opacity 0.2s ease;
}

.sort-asc .sort-indicator {
  opacity: 1;
  color: #667eea;
}

.sort-asc .sort-indicator::before {
  content: '↑';
}

.sort-desc .sort-indicator {
  opacity: 1;
  color: #667eea;
}

.sort-desc .sort-indicator::before {
  content: '↓';
}

/* Cellules spécifiques */
.auteur-cell {
  font-weight: 500;
  white-space: nowrap;
}

.titre-cell {
  font-weight: 500;
}

.editeur-cell {
  color: #666;
  font-size: 0.85rem;
}

.avis-cell {
  min-width: 300px;
}

.avis-item {
  margin-bottom: 0.5rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px dashed #e0e0e0;
}

.avis-item:last-child {
  margin-bottom: 0;
  padding-bottom: 0;
  border-bottom: none;
}

.critique-nom {
  font-weight: 600;
  color: #333;
}

.avis-commentaire {
  color: #555;
}

.avis-note {
  display: inline-block;
  margin-left: 0.5rem;
  padding: 0.15rem 0.4rem;
  border-radius: 3px;
  font-weight: 600;
  font-size: 0.85rem;
}

/* Notes avec couleurs */
.note-excellent {
  background: #00C851;
  color: white;
}

.note-good {
  background: #8BC34A;
  color: white;
}

.note-average {
  background: #CDDC39;
  color: #333;
}

.note-poor {
  background: #F44336;
  color: white;
}

.note-moyenne-cell {
  text-align: center;
}

.note-moyenne {
  display: inline-block;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-weight: 700;
  font-size: 1rem;
}

/* Liens */
.livre-link,
.critique-link {
  color: #0066cc;
  text-decoration: none;
}

.livre-link:hover,
.critique-link:hover {
  text-decoration: underline;
}

/* Entités non résolues */
.unresolved {
  color: #856404;
}

.warning-icon {
  font-size: 0.8rem;
  margin-left: 0.25rem;
  cursor: help;
}

/* Coups de coeur */
.coups-de-coeur .critique-cell {
  font-weight: 600;
}

.coups-de-coeur .note-cell {
  text-align: center;
}

.coups-de-coeur .note {
  display: inline-block;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  font-weight: 700;
}

.note-missing {
  color: #999;
}

.commentaire-cell {
  font-style: italic;
  color: #555;
}

/* Matching stats */
.matching-stats {
  background: #fff3cd;
  border: 1px solid #ffc107;
  border-radius: 4px;
  padding: 0.75rem 1rem;
  margin-bottom: 1rem;
}

.stats-header {
  margin-bottom: 0.5rem;
}

.stats-warning {
  font-weight: 600;
  color: #856404;
}

.stats-details {
  display: flex;
  gap: 1.5rem;
  font-size: 0.9rem;
}

.stat-item {
  padding: 0.25rem 0.5rem;
  border-radius: 3px;
}

.stat-phase1 {
  background: #d4edda;
  color: #155724;
}

.stat-phase2 {
  background: #cce5ff;
  color: #004085;
}

.stat-phase3 {
  background: #fff3cd;
  color: #856404;
}

.stat-unmatched {
  background: #f8d7da;
  color: #721c24;
}

/* Colonnes Coup de coeur et Chef d'oeuvre */
.coup-de-coeur-cell {
  font-size: 0.85rem;
  color: #666;
  max-width: 150px;
}

.coup-de-coeur-list {
  color: #e91e63;
}

.chef-oeuvre-header {
  text-align: center;
  white-space: nowrap;
}

.chef-oeuvre-cell {
  text-align: center;
}

.chef-oeuvre-badge {
  display: inline-block;
  background: #ffd700;
  color: #333;
  font-weight: bold;
  padding: 0.2rem 0.4rem;
  border-radius: 3px;
}

.empty-cell {
  color: #ccc;
}

/* Lien auteur */
.auteur-link {
  color: #0066cc;
  text-decoration: none;
}

.auteur-link:hover {
  text-decoration: underline;
}

/* Message vide */
.no-avis {
  padding: 2rem;
  text-align: center;
  color: #666;
  background: #f9f9f9;
  border-radius: 4px;
}

/* Responsive */
@media (max-width: 768px) {
  .avis-table {
    font-size: 0.8rem;
  }

  .avis-table th,
  .avis-table td {
    padding: 0.5rem;
  }

  .avis-cell {
    min-width: auto;
  }
}
</style>
