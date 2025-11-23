<template>
  <div class="masquer-episodes">
    <Navigation pageTitle="Masquer les Épisodes" />

    <main>
      <!-- Filtrage -->
      <section class="filter-section card">
        <div class="filter-row">
          <input
            v-model="searchFilter"
            type="text"
            placeholder="Filtrer par titre ou date..."
            class="search-input"
          />
          <p class="filter-hint">✍️ Cliquez sur les en-têtes du tableau pour trier</p>
        </div>
      </section>

      <!-- Message d'erreur -->
      <div v-if="error" class="error-message">
        Erreur lors du chargement des épisodes : {{ error }}
      </div>

      <!-- Indicateur de chargement -->
      <div v-else-if="loading" class="loading-indicator">
        Chargement des épisodes...
      </div>

      <!-- Tableau des épisodes -->
      <section v-else class="table-section card">
        <table class="episodes-table">
        <thead>
          <tr>
            <th class="sortable-header" data-test="sort-titre" @click="setSortOrder('titre')">
              Titre
              <span class="sort-indicator" :class="getSortClass('titre')"></span>
            </th>
            <th class="sortable-header col-duree" data-test="sort-duree" @click="setSortOrder('duree')">
              Durée
              <span class="sort-indicator" :class="getSortClass('duree')"></span>
            </th>
            <th class="sortable-header" data-test="sort-date" @click="setSortOrder('date')">
              Date
              <span class="sort-indicator" :class="getSortClass('date')"></span>
            </th>
            <th class="sortable-header" data-test="sort-masked" @click="setSortOrder('masked')">
              Visibilité
              <span class="sort-indicator" :class="getSortClass('masked')"></span>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="episode in filteredEpisodes" :key="episode.id">
            <td class="episode-title">{{ episode.titre }}</td>
            <td class="episode-duree">{{ formatDuration(episode.duree) }}</td>
            <td class="episode-date">{{ formatDate(episode.date) }}</td>
            <td class="episode-status">
              <button
                :data-test="`toggle-masked-${episode.id}`"
                class="toggle-button"
                :class="{ masked: episode.masked }"
                @click="toggleMasked(episode)"
                :title="episode.masked ? 'Épisode masqué - Cliquer pour rendre visible' : 'Épisode visible - Cliquer pour masquer'"
              >
                <span v-if="episode.masked" class="status-icon">🚫</span>
                <span v-else class="status-icon">👁️</span>
                {{ episode.masked ? 'Masqué' : 'Visible' }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
      </section>

      <!-- Message si aucun épisode -->
      <div v-if="!loading && !error && filteredEpisodes.length === 0" class="no-results card">
        Aucun épisode trouvé.
      </div>
    </main>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import Navigation from '@/components/Navigation.vue'
import { episodeService } from '@/services/api.js'

export default {
  name: 'MasquerEpisodes',
  components: {
    Navigation
  },
  setup() {
    const episodes = ref([])
    const loading = ref(true)
    const error = ref(null)
    const searchFilter = ref('')
    const currentSortField = ref('date')
    const sortAscending = ref(true) // Date desc par défaut (plus récent en premier)

    /**
     * Charge tous les épisodes (masqués et visibles)
     */
    const loadEpisodes = async () => {
      try {
        loading.value = true
        error.value = null
        episodes.value = await episodeService.getAllEpisodesIncludingMasked()
      } catch (err) {
        console.error('Erreur lors du chargement des épisodes:', err)
        error.value = err.message || 'Erreur inconnue'
      } finally {
        loading.value = false
      }
    }

    /**
     * Formate la durée en heures, minutes et secondes
     * @param {number|null} dureeSeconds - Durée en secondes
     * @returns {string} Durée formatée
     */
    const formatDuration = (dureeSeconds) => {
      if (dureeSeconds === null || dureeSeconds === undefined) {
        return '-'
      }

      const hours = Math.floor(dureeSeconds / 3600)
      const minutes = Math.floor((dureeSeconds % 3600) / 60)
      const seconds = dureeSeconds % 60

      if (hours > 0) {
        return `${hours}h ${String(minutes).padStart(2, '0')} min`
      } else if (minutes > 0) {
        return `${minutes} min`
      } else {
        return `${seconds} s`
      }
    }

    /**
     * Formate la date au format français
     * @param {string|null} dateStr - Date ISO
     * @returns {string} Date formatée
     */
    const formatDate = (dateStr) => {
      if (!dateStr) return '-'
      const date = new Date(dateStr)
      return date.toLocaleDateString('fr-FR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
      })
    }

    /**
     * Change le statut masked d'un épisode
     * @param {Object} episode - Épisode à modifier
     */
    const toggleMasked = async (episode) => {
      const newMaskedStatus = !episode.masked

      try {
        await episodeService.updateEpisodeMaskedStatus(episode.id, newMaskedStatus)
        // Mise à jour optimiste dans l'UI
        episode.masked = newMaskedStatus
      } catch (err) {
        console.error('Erreur lors de la mise à jour du statut:', err)
        alert(`Erreur: ${err.message}`)
      }
    }

    /**
     * Définit l'ordre de tri
     * @param {string} field - Champ à trier
     */
    const setSortOrder = (field) => {
      if (currentSortField.value === field) {
        sortAscending.value = !sortAscending.value
      } else {
        currentSortField.value = field
        sortAscending.value = true
      }
    }

    /**
     * Retourne la classe CSS pour l'indicateur de tri
     * @param {string} field - Champ
     * @returns {string} Classe CSS
     */
    const getSortClass = (field) => {
      if (currentSortField.value !== field) return ''
      return sortAscending.value ? 'asc' : 'desc'
    }

    /**
     * Filtre et tri les épisodes
     */
    const filteredEpisodes = computed(() => {
      let filtered = [...episodes.value]

      // Filtrage
      if (searchFilter.value.trim()) {
        const search = searchFilter.value.toLowerCase()
        filtered = filtered.filter(episode => {
          const titre = (episode.titre || '').toLowerCase()
          const date = formatDate(episode.date).toLowerCase()
          return titre.includes(search) || date.includes(search)
        })
      }

      // Tri
      filtered.sort((a, b) => {
        let sortValue = 0

        switch (currentSortField.value) {
          case 'titre':
            sortValue = (a.titre || '').localeCompare(b.titre || '', 'fr', { sensitivity: 'base' })
            break
          case 'duree': {
            const durA = a.duree ?? -1
            const durB = b.duree ?? -1
            sortValue = durA - durB
            break
          }
          case 'date': {
            const dateA = a.date ? new Date(a.date).getTime() : 0
            const dateB = b.date ? new Date(b.date).getTime() : 0
            sortValue = dateB - dateA // Tri desc par défaut pour les dates
            break
          }
          case 'masked': {
            // Masqué (true) avant Visible (false) par défaut
            const maskedA = a.masked ? 1 : 0
            const maskedB = b.masked ? 1 : 0
            sortValue = maskedB - maskedA
            break
          }
          default:
            break
        }

        return sortAscending.value ? sortValue : -sortValue
      })

      return filtered
    })

    // Chargement au montage
    onMounted(() => {
      loadEpisodes()
    })

    return {
      episodes,
      loading,
      error,
      searchFilter,
      currentSortField,
      sortAscending,
      filteredEpisodes,
      formatDuration,
      formatDate,
      toggleMasked,
      setSortOrder,
      getSortClass
    }
  }
}
</script>

<style scoped>
.masquer-episodes {
  min-height: 100vh;
  background-color: #f5f5f5;
  display: flex;
  flex-direction: column;
  margin: -2rem;
  padding: 0;
}

main {
  flex: 1;
  padding: 2rem 0;
}

.filter-section {
  max-width: 1200px;
  margin: 0 auto 1.5rem auto;
  padding: 1.5rem 2rem;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.filter-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 2rem;
}

.search-input {
  flex: 0 0 500px;
  padding: 0.75rem 1rem;
  font-size: 1rem;
  border: 1px solid #ddd;
  border-radius: 8px;
  transition: border-color 0.3s;
}

.search-input:focus {
  outline: none;
  border-color: #667eea;
}

.filter-hint {
  margin: 0;
  font-size: 0.9rem;
  color: #6b7280;
  font-style: italic;
  flex-shrink: 0;
}

.card {
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.table-section {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0;
  overflow: hidden;
}

.error-message {
  max-width: 1200px;
  margin: 0 auto 1rem auto;
  background-color: #fee;
  color: #c33;
  padding: 1rem 2rem;
  border-radius: 4px;
}

.loading-indicator {
  max-width: 1200px;
  margin: 0 auto;
  text-align: center;
  padding: 2rem;
  font-size: 1.2rem;
  color: #333;
  background: white;
  border-radius: 8px;
}

.episodes-table {
  width: 100%;
  background: white;
  border-radius: 12px;
  overflow: hidden;
  border-collapse: collapse;
}

.episodes-table thead {
  background: #f8f9fa;
}

.episodes-table th {
  padding: 1rem;
  text-align: left;
  font-weight: 600;
  color: #333;
  border-bottom: 2px solid #eee;
}

.col-duree {
  width: 120px;
}

.sortable-header {
  cursor: pointer;
  user-select: none;
  transition: background-color 0.2s;
}

.sortable-header:hover {
  background-color: #e9ecef;
}

.sort-indicator {
  margin-left: 0.5rem;
  font-size: 0.75rem;
}

.sort-indicator.asc::after {
  content: '↑';
}

.sort-indicator.desc::after {
  content: '↓';
}

.episodes-table tbody tr {
  border-bottom: 1px solid #f3f4f6;
  transition: background-color 0.15s;
}

.episodes-table tbody tr:hover {
  background-color: #f9fafb;
}

.episodes-table tbody tr:last-child {
  border-bottom: none;
}

.episodes-table td {
  padding: 0.875rem 1rem;
  color: #6b7280;
  font-size: 0.875rem;
}

.episode-title {
  font-weight: 500;
  color: #111827;
}

.episode-duree,
.episode-date {
  color: #6b7280;
}

.toggle-button {
  padding: 0.375rem 0.875rem;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background-color: #ffffff;
  color: #374151;
  cursor: pointer;
  font-size: 0.8125rem;
  font-weight: 500;
  transition: all 0.2s;
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
}

.toggle-button .status-icon {
  font-size: 1rem;
}

.toggle-button.masked {
  background-color: #fef2f2;
  border-color: #fca5a5;
  color: #dc2626;
}

.toggle-button:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.toggle-button:active {
  transform: translateY(0);
}

.no-results {
  max-width: 1200px;
  margin: 0 auto;
  text-align: center;
  padding: 3rem 2rem;
  color: #6c757d;
  font-size: 1rem;
  background: white;
  border-radius: 8px;
}
</style>
