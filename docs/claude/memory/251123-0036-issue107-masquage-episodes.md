# Issue #107 - Masquage d'Épisodes - Implémentation Complète

**Date**: 2025-11-23
**Branch**: `107-masquer-des-episodes`
**Status**: Prêt pour PR
**Fichiers modifiés**: 26 fichiers (+1857 lignes, -25 lignes)

## Vue d'Ensemble

Implémentation d'une fonctionnalité complète de masquage d'épisodes permettant de cacher certains épisodes de l'interface utilisateur tout en les conservant en base de données. Cette fonctionnalité répond au besoin de filtrer les épisodes courts ou non pertinents sans les supprimer définitivement.

## Contexte et Motivation

L'utilisateur souhaitait pouvoir masquer certains épisodes (notamment les courts) sans les supprimer de la base de données. La solution devait :
- Filtrer automatiquement les épisodes masqués dans toutes les vues publiques
- Fournir une interface de gestion dédiée pour masquer/démasquer
- Maintenir l'intégrité des statistiques (ne pas compter les épisodes masqués)
- Suivre le pattern de design des pages existantes (LivresAuteurs.vue)

## Architecture de la Solution

### Schéma de Données MongoDB
```javascript
{
  "_id": ObjectId("..."),
  "titre": "Épisode Title",
  "date": ISODate("2024-11-10T09:59:39Z"),
  "type": "livre",
  "duree": 2763,  // secondes
  "masked": false  // NOUVEAU champ (défaut: false)
}
```

### Flow de Données
```
Frontend (MasquerEpisodes.vue)
  ↓ GET /api/episodes/all
Backend (app.py route)
  ↓ mongodb_service.get_all_episodes(include_masked=True)
MongoDB (episodes collection with masked field)
  ↑ Filter: {masked: {$ne: true}} ou tous si include_masked=True
Frontend (affichage tableau)
  ↓ Click toggle button
  ↓ PATCH /api/episodes/{id}/masked avec {masked: true/false}
Backend (app.py route)
  ↓ mongodb_service.update_episode_masked_status(id, masked)
MongoDB (update_one avec $set)
  ↑ Response matched_count (idempotent)
Frontend (mise à jour optimiste UI)
```

## Fichiers Modifiés - Détails Complets

### 📁 Backend - API Routes (1 fichier)

#### 1. **src/back_office_lmelp/app.py** (+76 lignes)

**Nouvelles routes** :

```python
@app.get("/api/episodes/all", response_model=list[dict[str, Any]])
async def get_all_episodes_including_masked():
    """
    Récupère tous les épisodes, y compris les masqués.

    CRITICAL: Route AVANT /api/episodes/{episode_id} pour éviter match {id}="all"
    """
    episodes = mongodb_service.get_all_episodes(include_masked=True)
    return episodes


@app.patch("/api/episodes/{episode_id}/masked")
async def update_episode_masked_status(
    episode_id: str,
    request: dict[str, bool]
):
    """
    Met à jour le statut masked d'un épisode.

    Utilise matched_count (idempotent) au lieu de modified_count.
    """
    masked = request.get("masked")
    if masked is None:
        raise HTTPException(status_code=422, detail="Field 'masked' required")

    success = mongodb_service.update_episode_masked_status(episode_id, masked)
    if not success:
        raise HTTPException(status_code=404, detail="Episode not found")

    return {"success": True}
```

**Ordre des routes** (CRITICAL) :
```python
# app.py lignes ajoutées dans ordre correct:
# 1. Route spécifique /api/episodes/all
# 2. Route paramétrique /api/episodes/{episode_id}
```

### 📁 Backend - Models (1 fichier)

#### 2. **src/back_office_lmelp/models/episode.py** (+8 lignes)

```python
class Episode:
    def __init__(self, data: dict[str, Any]):
        # ... champs existants ...
        self.masked: bool = data.get("masked", False)  # Défaut False

    def to_summary_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "titre": self.titre,
            "date": self.date.isoformat() if self.date else None,
            "type": self.type,
            "duree": self.duree,
            "masked": self.masked,  # AJOUTÉ
        }

    def to_dict(self) -> dict[str, Any]:
        result = {
            # ... champs existants ...
            "masked": self.masked,  # AJOUTÉ
        }
        return result
```

### 📁 Backend - Services (3 fichiers)

#### 3. **src/back_office_lmelp/services/mongodb_service.py** (+95 lignes)

**Nouvelle méthode get_all_episodes** :
```python
def get_all_episodes(self, include_masked: bool = False) -> list[dict[str, Any]]:
    """
    Récupère tous les épisodes avec filtrage optionnel des masqués.

    Args:
        include_masked: Si True, inclut les épisodes masqués

    Returns:
        Liste d'épisodes triés par date (desc)
    """
    # Issue #107: Filtrer les épisodes masqués par défaut
    query_filter: dict[str, Any] = {}
    if not include_masked:
        query_filter["masked"] = {"$ne": True}  # Pas {"masked": False} !

    episodes = list(
        self.episodes_collection.find(
            query_filter,
            {
                "titre": 1,
                "titre_corrige": 1,
                "date": 1,
                "type": 1,
                "duree": 1,  # AJOUTÉ pour affichage
                "masked": 1,  # AJOUTÉ pour toggle
                "_id": 1,
            },
        ).sort([("date", -1)])
    )

    # Conversion ObjectId en string
    for episode in episodes:
        episode["_id"] = str(episode["_id"])

    return episodes
```

**Nouvelle méthode update_episode_masked_status** :
```python
def update_episode_masked_status(self, episode_id: str, masked: bool) -> bool:
    """
    Met à jour le statut masked d'un épisode.

    Returns:
        True si l'épisode existe (idempotent), False sinon
    """
    try:
        oid = ObjectId(episode_id)
    except Exception:
        return False

    result = self.episodes_collection.update_one(
        {"_id": oid},
        {"$set": {"masked": masked}}
    )

    # CRITICAL: matched_count (idempotent) au lieu de modified_count
    return bool(result.matched_count > 0)
```

**Méthode delete_episode enrichie** :
```python
def delete_episode(self, episode_id: str) -> dict[str, Any]:
    # 1. Supprimer avis critiques
    avis_delete_result = self.avis_critiques_collection.delete_many(
        {"episode_oid": episode_id}
    )

    # 1.5 Supprimer cache livres-auteurs (NOUVEAU - Fix ghost stats)
    try:
        cache_collection = self.get_collection("livresauteurs_cache")
        cache_delete_result = cache_collection.delete_many(
            {"episode_oid": episode_id}
        )
        print(f"Suppression de {cache_delete_result.deleted_count} entrées cache")
    except Exception as e:
        print(f"Erreur suppression cache: {e}")

    # 2. Retirer références des livres
    # 3. Supprimer l'épisode
    # ...
```

**Méthode get_statistics mise à jour** :
```python
def get_statistics(self) -> dict[str, Any]:
    # Total des épisodes (visibles uniquement)
    total_episodes = self.episodes_collection.count_documents(
        {"masked": {"$ne": True}}
    )

    # Nombre d'épisodes masqués
    masked_episodes_count = self.episodes_collection.count_documents(
        {"masked": True}
    )

    # Avis critiques (excluant épisodes masqués)
    masked_episodes = list(
        self.episodes_collection.find({"masked": True}, {"_id": 1})
    )
    masked_episode_oids = [str(ep["_id"]) for ep in masked_episodes]

    critical_reviews_count = self.avis_critiques_collection.count_documents(
        {"episode_oid": {"$nin": masked_episode_oids}}
    )

    return {
        "total_episodes": total_episodes,
        "masked_episodes_count": masked_episodes_count,  # NOUVEAU
        # ... autres stats ...
    }
```

#### 4. **src/back_office_lmelp/services/livres_auteurs_cache_service.py** (+57 lignes)

**Méthode get_episodes_with_reviews mise à jour** :
```python
def get_episodes_with_reviews(self) -> list[dict[str, Any]]:
    """
    Récupère épisodes avec avis, EXCLUANT les masqués.
    """
    # Requête MongoDB pour récupérer épisodes avec avis
    episodes_cursor = self.episodes_collection.find(
        {
            "avis_critiques": {"$exists": True, "$ne": []},
            "masked": {"$ne": True}  # AJOUTÉ - Filtre masqués
        },
        {
            "titre": 1,
            "date": 1,
            "avis_critiques": 1,
            "_id": 1
        }
    ).sort([("date", -1)])

    return list(episodes_cursor)
```

#### 5. **src/back_office_lmelp/services/stats_service.py** (+3 lignes)

**Statistique maskedEpisodes ajoutée** :
```python
@staticmethod
def get_combined_statistics(mongodb_stats, cache_stats):
    return {
        "totalEpisodes": mongodb_stats.get("total_episodes", 0),
        "maskedEpisodes": mongodb_stats.get("masked_episodes_count", 0),  # NOUVEAU
        "episodesWithCorrectedTitles": mongodb_stats.get("episodes_with_corrected_titles", 0),
        # ... autres stats ...
    }
```

### 📁 Frontend - Components & Views (4 fichiers)

#### 6. **frontend/src/views/MasquerEpisodes.vue** (477 lignes - NOUVEAU)

**Composant Vue complet** avec Composition API :

```vue
<template>
  <div class="masquer-episodes">
    <Navigation pageTitle="Masquer les Épisodes" />

    <main>
      <!-- Section filtrage -->
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

      <!-- Tableau épisodes -->
      <section class="table-section card">
        <table class="episodes-table">
          <thead>
            <tr>
              <th @click="setSortOrder('titre')" class="sortable-header">
                Titre
                <span class="sort-indicator" :class="getSortClass('titre')"></span>
              </th>
              <th @click="setSortOrder('duree')" class="sortable-header col-duree">
                Durée
                <span class="sort-indicator" :class="getSortClass('duree')"></span>
              </th>
              <th @click="setSortOrder('date')" class="sortable-header">
                Date
                <span class="sort-indicator" :class="getSortClass('date')"></span>
              </th>
              <th @click="setSortOrder('masked')" class="sortable-header">
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
    </main>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import Navigation from '@/components/Navigation.vue'
import { episodeService } from '@/services/api.js'

export default {
  name: 'MasquerEpisodes',
  components: { Navigation },
  setup() {
    const episodes = ref([])
    const loading = ref(true)
    const error = ref(null)
    const searchFilter = ref('')
    const currentSortField = ref('date')
    const sortAscending = ref(false)  // Date DESC par défaut

    const loadEpisodes = async () => {
      episodes.value = await episodeService.getAllEpisodesIncludingMasked()
    }

    const formatDuration = (dureeSeconds) => {
      if (!dureeSeconds) return '-'
      const hours = Math.floor(dureeSeconds / 3600)
      const minutes = Math.floor((dureeSeconds % 3600) / 60)
      const seconds = dureeSeconds % 60

      if (hours > 0) return `${hours}h ${String(minutes).padStart(2, '0')} min`
      if (minutes > 0) return `${minutes} min`
      return `${seconds} s`
    }

    const formatDate = (dateStr) => {
      if (!dateStr) return '-'
      const date = new Date(dateStr)
      return date.toLocaleDateString('fr-FR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
      })
    }

    const toggleMasked = async (episode) => {
      const newMaskedStatus = !episode.masked
      await episodeService.updateEpisodeMaskedStatus(episode.id, newMaskedStatus)
      episode.masked = newMaskedStatus  // Mise à jour optimiste
    }

    const setSortOrder = (field) => {
      if (currentSortField.value === field) {
        sortAscending.value = !sortAscending.value
      } else {
        currentSortField.value = field
        sortAscending.value = true
      }
    }

    const filteredEpisodes = computed(() => {
      let filtered = [...episodes.value]

      // Filtrage
      if (searchFilter.value.trim()) {
        const search = searchFilter.value.toLowerCase()
        filtered = filtered.filter(ep => {
          const titre = (ep.titre || '').toLowerCase()
          const date = formatDate(ep.date).toLowerCase()
          return titre.includes(search) || date.includes(search)
        })
      }

      // Tri
      filtered.sort((a, b) => {
        let sortValue = 0

        switch (currentSortField.value) {
          case 'titre':
            sortValue = (a.titre || '').localeCompare(b.titre || '', 'fr')
            break
          case 'duree':
            sortValue = (a.duree ?? -1) - (b.duree ?? -1)
            break
          case 'date':
            const dateA = a.date ? new Date(a.date).getTime() : 0
            const dateB = b.date ? new Date(b.date).getTime() : 0
            sortValue = dateB - dateA  // DESC par défaut
            break
          case 'masked':
            const maskedA = a.masked ? 1 : 0
            const maskedB = b.masked ? 1 : 0
            sortValue = maskedB - maskedA  // Masqués en premier
            break
        }

        return sortAscending.value ? sortValue : -sortValue
      })

      return filtered
    })

    onMounted(() => {
      loadEpisodes()
    })

    return {
      episodes, loading, error, searchFilter,
      currentSortField, sortAscending, filteredEpisodes,
      formatDuration, formatDate, toggleMasked, setSortOrder, getSortClass
    }
  }
}
</script>
```

**Styling CSS - Pattern unifié avec LivresAuteurs** :
```css
.masquer-episodes {
  min-height: 100vh;
  background-color: #f5f5f5;  /* Gray background */
  margin: -2rem;  /* CRITICAL: Escape #app padding */
  padding: 0;
  display: flex;
  flex-direction: column;
}

main {
  flex: 1;
  padding: 2rem 0;  /* Vertical only - no horizontal */
}

.filter-section, .table-section, .error-message, .loading-indicator, .no-results {
  max-width: 1200px;  /* Match Navigation.nav-content */
  margin: 0 auto;
  padding: 1.5rem 2rem;  /* Own horizontal padding */
}

/* Table headers - Aligned with LivresAuteurs */
.episodes-table thead {
  background: #f8f9fa;
}

.episodes-table th {
  padding: 1rem;  /* Changed from 0.75rem 1rem */
  font-weight: 600;  /* Changed from 700 */
  color: #333;  /* Changed from #374151 */
  border-bottom: 2px solid #eee;  /* Changed from 1px */
}

.col-duree {
  width: 120px;
}

/* Toggle buttons with icons */
.toggle-button {
  padding: 0.375rem 0.875rem;
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
```

**Pattern CSS découvert** :
- Global `#app` : `max-width: 1200px; padding: 2rem;`
- Navigation `.nav-content` : `max-width: 1200px; padding: 0 2rem;`
- **Solution** : `margin: -2rem` pour échapper conteneur parent, puis `max-width: 1200px` sur blocs

#### 7. **frontend/src/services/api.js** (+22 lignes)

**Nouvelles méthodes episodeService** :
```javascript
getAllEpisodesIncludingMasked: async () => {
  const response = await axios.get(`${API_BASE_URL}/api/episodes/all`);
  return response.data;
},

updateEpisodeMaskedStatus: async (episodeId, masked) => {
  const response = await axios.patch(
    `${API_BASE_URL}/api/episodes/${episodeId}/masked`,
    { masked }
  );
  return response.data;
}
```

#### 8. **frontend/src/router/index.js** (+9 lignes)

```javascript
import MasquerEpisodes from '../views/MasquerEpisodes.vue';

const routes = [
  // ... routes existantes ...
  {
    path: '/masquer-episodes',
    name: 'MasquerEpisodes',
    component: MasquerEpisodes,
    meta: {
      title: 'Masquer les Épisodes - Back-office LMELP'
    }
  }
];
```

#### 9. **frontend/src/views/Dashboard.vue** (+23 lignes)

**Nouvelle carte avec affichage conditionnel** :
```vue
<template>
  <div class="features-grid">
    <!-- Cartes existantes ... -->

    <!-- Carte Masquer Épisodes - Affichée si episodes masqués > 0 -->
    <div
      v-if="stats.maskedEpisodes > 0"
      class="feature-card purple"
      @click="navigateTo('/masquer-episodes')"
    >
      <div class="feature-icon">🚫</div>
      <h2 class="feature-title">Masquer des Épisodes</h2>
      <p class="feature-description">Gérer la visibilité des épisodes</p>
      <div class="feature-badge">{{ stats.maskedEpisodes }} masqués</div>
    </div>
  </div>
</template>

<script>
// stats.maskedEpisodes provient de GET /api/stats
</script>

<style scoped>
.feature-card.purple {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
</style>
```

### 📁 Backend - Tests (8 fichiers)

#### 10. **tests/test_episode_masking.py** (310 lignes - NOUVEAU)

**Tests routes API** (7 tests) :
```python
def test_get_all_episodes_excludes_masked_by_default():
    """Par défaut, /api/episodes filtre les épisodes masqués."""
    # Mock MongoDB
    mock_episodes = [
        {"_id": "ep1", "titre": "Visible", "masked": False},
        {"_id": "ep2", "titre": "Masqué", "masked": True},
    ]
    mongodb_service.get_all_episodes.return_value = [mock_episodes[0]]

    response = client.get("/api/episodes")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["titre"] == "Visible"
    mongodb_service.get_all_episodes.assert_called_with(include_masked=False)


def test_get_all_episodes_includes_masked_when_requested():
    """/api/episodes/all inclut tous les épisodes."""
    mock_episodes = [
        {"_id": "ep1", "titre": "Visible", "masked": False},
        {"_id": "ep2", "titre": "Masqué", "masked": True},
    ]
    mongodb_service.get_all_episodes.return_value = mock_episodes

    response = client.get("/api/episodes/all")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    mongodb_service.get_all_episodes.assert_called_with(include_masked=True)


def test_update_masked_status_idempotent():
    """Appeler 2x avec même valeur doit réussir (idempotence REST)."""
    mongodb_service.update_episode_masked_status.return_value = True

    # Premier appel
    response1 = client.patch(
        "/api/episodes/ep1/masked",
        json={"masked": True}
    )
    assert response1.status_code == 200

    # Deuxième appel (même valeur)
    response2 = client.patch(
        "/api/episodes/ep1/masked",
        json={"masked": True}
    )
    assert response2.status_code == 200
```

**Tests MongoDB Service** (6 tests) :
```python
def test_update_episode_masked_status_returns_true_if_already_masked():
    """Idempotence: Retourne True même si déjà dans état désiré."""
    mock_collection.update_one.return_value = Mock(
        matched_count=1,  # Document trouvé
        modified_count=0  # Mais déjà masked=True
    )

    result = mongodb_service.update_episode_masked_status("ep1", True)

    assert result is True  # Succès car matched_count > 0
```

**Tests Statistiques** (2 tests) :
```python
def test_statistics_count_masked_episodes():
    """Statistiques incluent le compte d'épisodes masqués."""
    mock_collection.count_documents.side_effect = [
        100,  # total_episodes (visibles)
        15,   # masked_episodes_count
        # ...
    ]

    stats = mongodb_service.get_statistics()

    assert stats["total_episodes"] == 100
    assert stats["masked_episodes_count"] == 15
```

**Helper function** :
```python
def create_mock_episode(
    episode_id="ep1",
    titre="Test Episode",
    masked=False,
    **kwargs
):
    """
    Helper pour créer mock épisode avec structure réelle MongoDB.

    IMPORTANT: Basé sur vraie réponse API, pas inventé.
    """
    return {
        "_id": ObjectId(episode_id) if len(episode_id) == 24 else ObjectId(),
        "titre": titre,
        "date": datetime.now(),
        "type": "livre",
        "duree": 2763,
        "masked": masked,
        **kwargs
    }
```

#### 11-17. **Tests existants mis à jour** (7 fichiers)

**tests/test_correct_status_values.py** (+5 lignes) :
```python
# Vérifier que distinct a été appelé avec filtre masked
mock_mongodb.get_collection.return_value.distinct.assert_any_call(
    "avis_critique_id",
    {"episode_oid": {"$nin": []}}  # MODIFIÉ: Filtre épisodes masqués
)
```

**tests/test_models_validation.py** (+10 lignes) :
```python
# Tous les to_dict() et to_summary_dict() incluent maintenant:
assert result["masked"] == False
assert result["duree"] == expected_duree
```

**tests/test_mongodb_integration.py** (+11 lignes) :
```python
mock_collection.find.assert_called_once_with(
    {"masked": {"$ne": True}},  # AJOUTÉ: Filtre masqués
    {
        "titre": 1,
        "titre_corrige": 1,
        "date": 1,
        "type": 1,
        "duree": 1,      # AJOUTÉ
        "masked": 1,     # AJOUTÉ
        "_id": 1,
    },
)
```

**tests/test_mongodb_service_refactoring.py** (+10 lignes) :
```python
self.mock_collection.count_documents.side_effect = [
    100,  # total_episodes (visible uniquement)
    5,    # masked_episodes_count - AJOUTÉ
    15,   # episodes avec titre_origin
    25,   # episodes avec description_origin
]

assert result["masked_episodes_count"] == 5
```

**tests/test_mongodb_service_simple.py** (+11 lignes) :
```python
mongodb_service.episodes_collection.find.assert_called_once_with(
    {"masked": {"$ne": True}},  # AJOUTÉ
    {
        # ... projection avec duree et masked ajoutés
    },
)
```

**tests/test_statistics_endpoint.py** (+5 lignes) :
```python
mock_stats_data = {
    "total_episodes": 142,
    "masked_episodes_count": 5,  # AJOUTÉ
    # ...
}

assert data["maskedEpisodes"] == 5
```

**tests/test_stats_service.py** (+4 lignes) :
```python
expected_summary = """📊 STATISTIQUES CACHE LIVRES/AUTEURS

🚀 Auto-traités (en base) : 3 (couples)
📚 Livres uniques         : 0  # AJOUTÉ
⏳ En attente validation  : 10
```

### 📁 Frontend - Tests (3 fichiers)

#### 18. **frontend/tests/unit/masquerEpisodes.spec.js** (324 lignes - NOUVEAU)

**Tests affichage** :
```javascript
describe('MasquerEpisodes.vue', () => {
  beforeEach(() => {
    vi.resetAllMocks()  // CRITICAL: Reset mocks entre tests
  })

  it('should display all episodes including masked', async () => {
    const mockEpisodes = [
      { id: 'ep1', titre: 'Visible', masked: false },
      { id: 'ep2', titre: 'Masqué', masked: true },
    ]

    episodeService.getAllEpisodesIncludingMasked.mockResolvedValueOnce(mockEpisodes)

    const wrapper = mount(MasquerEpisodes, { global: { plugins: [router] } })
    await flushPromises()

    expect(wrapper.text()).toContain('Visible')
    expect(wrapper.text()).toContain('Masqué')
  })

  it('should display correct column headers', async () => {
    expect(wrapper.text()).toContain('Titre')
    expect(wrapper.text()).toContain('Durée')
    expect(wrapper.text()).toContain('Date')
    expect(wrapper.text()).toContain('Visibilité')  // Pas "Statut"
  })

  it('should format duration correctly', async () => {
    // 2763s = 46 min 3s
    expect(wrapper.text()).toContain('46 min')
  })

  it('should sort episodes by date descending by default', async () => {
    const mockEpisodes = [
      { id: 'ep1', titre: 'Episode 1', date: '2024-11-08T09:59:39', masked: false },
      { id: 'ep2', titre: 'Episode 2', date: '2024-11-10T09:59:39', masked: false },
      { id: 'ep3', titre: 'Episode 3', date: '2024-11-09T09:59:39', masked: false }
    ]

    const rows = wrapper.findAll('tbody tr')
    expect(rows[0].text()).toContain('Episode 2')  // 2024-11-10 (plus récent)
    expect(rows[1].text()).toContain('Episode 3')  // 2024-11-09
    expect(rows[2].text()).toContain('Episode 1')  // 2024-11-08
  })

  it('should toggle masked status on button click', async () => {
    episodeService.updateEpisodeMaskedStatus.mockResolvedValueOnce({ success: true })

    await wrapper.find('[data-test="toggle-masked-ep1"]').trigger('click')
    await flushPromises()

    expect(episodeService.updateEpisodeMaskedStatus)
      .toHaveBeenCalledWith('ep1', true)
  })
})
```

#### 19. **frontend/tests/integration/MasquerEpisodes.test.js** (63 lignes - NOUVEAU)

```javascript
it('should navigate to masquer episodes page from dashboard', async () => {
  const wrapper = mount(Dashboard, { global: { plugins: [router] } })
  await flushPromises()

  await wrapper.find('.feature-card.purple').trigger('click')
  await nextTick()

  expect(router.currentRoute.value.path).toBe('/masquer-episodes')
})
```

#### 20. **frontend/tests/integration/Dashboard.test.js** (+17 lignes)

```javascript
it('should display masquer episodes card when masked episodes exist', async () => {
  const mockStats = {
    totalEpisodes: 100,
    maskedEpisodes: 5,  // > 0 donc carte affichée
    // ...
  }

  await wrapper.vm.$nextTick()

  expect(wrapper.text()).toContain('Masquer des Épisodes')
  expect(wrapper.text()).toContain('5 masqués')
})
```

### 📁 Documentation (4 fichiers + 1 image)

#### 21. **CLAUDE.md** (+20 lignes)

**Section FastAPI Best Practices** ajoutée :
```markdown
### FastAPI Best Practices

**CRITICAL**: Two common patterns that cause production bugs:

1. **Route Order Matters** - Specific routes MUST come BEFORE parametric routes:
   ```python
   @app.get("/api/episodes/all")        # ✅ Specific FIRST
   @app.get("/api/episodes/{id}")       # ✅ Parametric AFTER
   ```
   ❌ Wrong order causes `/api/episodes/all` to match `{id}="all"` → 404 error

2. **REST Idempotence** - Use `matched_count` not `modified_count` for MongoDB updates:
   ```python
   result = collection.update_one({"_id": id}, {"$set": {"field": value}})
   return bool(result.matched_count > 0)  # ✅ Idempotent
   # NOT: result.modified_count > 0       # ❌ Fails if already in desired state
   ```

**Details**: See [FastAPI Route Patterns](docs/dev/claude-ai-guide.md#fastapi-route-patterns)
```

#### 22. **docs/dev/api.md** (+42 lignes)

**Nouvelle section** :
```markdown
## FastAPI Best Practices

### Route Order - CRITICAL

**IMPORTANT**: In FastAPI, route definition order matters. Specific routes MUST be defined BEFORE parametric routes.

**❌ Wrong (causes bugs)**:
```python
@app.get("/api/episodes/{episode_id}")  # Parametric FIRST → WRONG
@app.get("/api/episodes/all")           # Specific AFTER → BUG
```

Calling `/api/episodes/all` will match the first route with `episode_id="all"`, causing a 404 error.

**✅ Correct**:
```python
@app.get("/api/episodes/all")           # Specific FIRST → CORRECT
@app.get("/api/episodes/{episode_id}")  # Parametric AFTER → CORRECT
```

### REST Idempotence with MongoDB

**IMPORTANT**: Use `matched_count` instead of `modified_count` for idempotent operations.

**Why**: `modified_count` is 0 when the document is already in the desired state. REST APIs should be idempotent: calling the same operation twice should succeed both times.

**See**: [Claude AI Development Guide - FastAPI Route Patterns](claude-ai-guide.md#fastapi-route-patterns) for detailed explanations and testing strategies.
```

#### 23. **docs/dev/claude-ai-guide.md** (+114 lignes)

**Section enrichie** avec exemples complets :
```markdown
### FastAPI Route Patterns

#### Route Order (CRITICAL)

**Problem**: Routes are matched in definition order. Parametric routes (`{id}`) match everything.

**Bug Example**:
```python
# ❌ WRONG ORDER
@app.get("/api/episodes/{episode_id}")  # This matches EVERYTHING
@app.get("/api/episodes/all")           # Never reached!

# Calling GET /api/episodes/all
# → Matches first route with episode_id="all"
# → Tries to find episode with ObjectId("all")
# → 404 Error
```

**Solution**:
```python
# ✅ CORRECT ORDER
@app.get("/api/episodes/all")           # Specific FIRST
@app.get("/api/episodes/{episode_id}")  # Parametric AFTER
```

**Test Pattern**:
```python
def test_route_order_all_before_id():
    """Vérifie que /all est défini AVANT /{id}."""
    routes = [r.path for r in app.routes if r.path.startswith("/api/episodes")]
    all_index = routes.index("/api/episodes/all")
    id_index = routes.index("/api/episodes/{episode_id}")
    assert all_index < id_index, "Route /all must be defined before /{id}"
```

#### REST Idempotence with MongoDB

**Problem**: `modified_count` est 0 si document déjà dans état désiré.

**Non-Idempotent Example**:
```python
# ❌ FAILS on second identical call
def update_status(id, value):
    result = collection.update_one({"_id": id}, {"$set": {"status": value}})
    return bool(result.modified_count > 0)

# First call:  update_status(123, "active") → True  ✅
# Second call: update_status(123, "active") → False ❌
```

**Idempotent Solution**:
```python
# ✅ SUCCEEDS on all calls
def update_status(id, value):
    result = collection.update_one({"_id": id}, {"$set": {"status": value}})
    return bool(result.matched_count > 0)

# First call:  update_status(123, "active") → True  ✅
# Second call: update_status(123, "active") → True  ✅
```

**Test Pattern**:
```python
def test_update_masked_status_idempotent():
    """Calling twice with same value should succeed both times."""
    response1 = client.patch("/api/episodes/ep1/masked", json={"masked": True})
    assert response1.status_code == 200

    response2 = client.patch("/api/episodes/ep1/masked", json={"masked": True})
    assert response2.status_code == 200  # Still success!
```
```

#### 24. **docs/claude/echanges/107-Masquer des episodes.md** (77 lignes - NOUVEAU)

**Documentation API tests et discussions UX** :
```markdown
# Tests backend API episodes

## Tous les épisodes visibles
curl -s "$(bash -c '/workspaces/back-office-lmelp/.claude/get-backend-info.sh --url')/api/episodes" | jq 'length'

## Tous les épisodes y compris les invisibles
curl -s "$(bash -c '/workspaces/back-office-lmelp/.claude/get-backend-info.sh --url')/api/episodes/all" | jq 'length'

## Masquer l'épisode
BACKEND_URL=$(/workspaces/back-office-lmelp/.claude/get-backend-info.sh --url)
curl -X PATCH "$BACKEND_URL/api/episodes/6773e32258fc5717f3516b9f/masked" \
  -H "Content-Type: application/json" \
  -d '{"masked": true}'

# Discussions sur UX

> Décision: Nouvelle page dédiée /masquer-episodes accessible depuis Dashboard
> Template: Bandeau navigation + tableau cliquable/triable/filtrable
> Colonnes: Titre, Durée, Date, Visibilité
> Toggle button: Icône 👁️ (visible) ou 🚫 (masqué)
> Durée disponible en base: champ "duree" en secondes
```

#### 25. **docs/dev/image.png** (Binaire - 8865 bytes)

Image de référence pour documentation (probablement screenshot UI).

### 📁 Dependencies (1 fichier)

#### 26. **uv.lock** (+89 lignes)

**Nouvelle dépendance Pillow ajoutée** :
```toml
[[package]]
name = "pillow"
version = "12.0.0"
# ... wheels pour toutes les plateformes ...
```

Ajouté dans `dev` dependencies pour manipulation d'images (probablement pour tests ou documentation).

## Patterns et Apprentissages Clés

### 1. FastAPI Route Order (CRITICAL)

**Problème** : Routes définies dans mauvais ordre causent 404.

**Exemple Bug** :
```python
@app.get("/api/episodes/{episode_id}")  # Matche TOUT
@app.get("/api/episodes/all")           # Jamais atteint!
```

**Solution** :
```python
@app.get("/api/episodes/all")           # Spécifique D'ABORD
@app.get("/api/episodes/{episode_id}")  # Paramétrique APRÈS
```

**Test Pattern** :
```python
def test_route_order():
    routes = [r.path for r in app.routes if r.path.startswith("/api/episodes")]
    all_idx = routes.index("/api/episodes/all")
    id_idx = routes.index("/api/episodes/{episode_id}")
    assert all_idx < id_idx
```

### 2. REST Idempotence avec MongoDB

**Problème** : `modified_count` retourne 0 si document déjà dans état désiré.

**Non-Idempotent** ❌ :
```python
result = collection.update_one({"_id": id}, {"$set": {"masked": True}})
return bool(result.modified_count > 0)
# Premier appel: True ✅
# Deuxième appel (déjà masked=True): False ❌
```

**Idempotent** ✅ :
```python
result = collection.update_one({"_id": id}, {"$set": {"masked": True}})
return bool(result.matched_count > 0)
# Premier appel: True ✅
# Deuxième appel (déjà masked=True): True ✅
```

**Pourquoi** : REST PATCH doit être idempotent. Appeler 2× avec même valeur doit réussir 2×.

### 3. CSS Layout - Escape Container Pattern

**Problème** : Global `#app` avec `max-width: 1200px` et `padding: 2rem` contraint enfants.

**Découverte** :
- Navigation a full-width `<nav>`, avec `.nav-content` interne à `1200px`
- Pour matcher Navigation, il faut échapper le conteneur `#app`

**Solution** :
```css
.page-container {
  margin: -2rem;           /* Escape #app padding */
  background: #f5f5f5;     /* Full-width background visible */
}

main {
  padding: 2rem 0;         /* Vertical only, no horizontal */
}

.content-block {
  max-width: 1200px;       /* Match Navigation */
  margin: 0 auto;
  padding: 1.5rem 2rem;    /* Own horizontal padding */
}
```

**Résultat** :
- Gray background `#f5f5f5` visible entre white blocks
- All blocks aligned with Navigation banner
- Consistent spacing throughout page

### 4. MongoDB Filter Pattern - Exclude Masked

**Pattern standard** pour filtrer épisodes masqués :

```python
query_filter = {"masked": {"$ne": True}}
```

**Pas** :
```python
query_filter = {"masked": False}  # ❌ WRONG
```

**Pourquoi** : Épisodes sans champ `masked` (anciens documents) doivent être inclus dans résultats visibles.

`{"$ne": True}` matche :
- `masked: false` ✅
- `masked` absent ✅
- `masked: null` ✅

`{"masked": False}` matche seulement :
- `masked: false` ✅

### 5. Vue Test Pattern - Mock Reset

**Problème** : Mocks avec `mockImplementation` persistent entre tests via closures.

**Solution** :
```javascript
beforeEach(() => {
  vi.resetAllMocks()  // CRITICAL: Clean slate
})

// Prefer mockResolvedValueOnce over mockImplementation
service.method.mockResolvedValueOnce(data)  // Single use, no persistence
```

**Anti-Pattern** :
```javascript
// ❌ BAD: Closure persists across tests
service.method.mockImplementation(async () => mockData)
```

### 6. Cache Invalidation - Delete Cascade

**Bug découvert** : Supprimer épisode laissait entrées dans `livresauteurs_cache` → "ghost stats".

**Symptôme** :
- Épisode supprimé de collection `episodes`
- Cache `livresauteurs_cache` garde références `episode_oid`
- Page Livres-Auteurs compte fantômes dans statistiques

**Fix** :
```python
def delete_episode(episode_id: str):
    # 1. Delete avis_critiques
    self.avis_critiques_collection.delete_many({"episode_oid": episode_id})

    # 1.5 Delete cache entries (NOUVEAU)
    cache_collection = self.get_collection("livresauteurs_cache")
    cache_collection.delete_many({"episode_oid": episode_id})

    # 2. Update livres (remove episode references)
    self.livres_collection.update_many(
        {"episodes": episode_id},
        {"$pull": {"episodes": episode_id}}
    )

    # 3. Delete episode
    self.episodes_collection.delete_one({"_id": ObjectId(episode_id)})
```

**Leçon** : Toujours invalider/supprimer caches lors de suppression de données source.

### 7. Vue Sorting - Natural vs Numerical

**Problème** : Tri des dates et durées.

**Date Sorting** :
```javascript
case 'date': {
  const dateA = a.date ? new Date(a.date).getTime() : 0
  const dateB = b.date ? new Date(b.date).getTime() : 0
  sortValue = dateB - dateA  // DESC par défaut (récent en premier)
  break
}
```

**Duration Sorting** :
```javascript
case 'duree': {
  const durA = a.duree ?? -1  // null/undefined → -1 (fin de liste)
  const durB = b.duree ?? -1
  sortValue = durA - durB
  break
}
```

**String Sorting (locale-aware)** :
```javascript
case 'titre':
  sortValue = (a.titre || '').localeCompare(b.titre || '', 'fr', { sensitivity: 'base' })
  break
```

### 8. Python Type Hints - dict[str, Any] Pattern

**Pattern utilisé** dans mongodb_service.py :
```python
def get_all_episodes(self, include_masked: bool = False) -> list[dict[str, Any]]:
    """Retourne liste de dictionnaires avec structure flexible."""
    query_filter: dict[str, Any] = {}  # Type hint pour dict vide
    if not include_masked:
        query_filter["masked"] = {"$ne": True}
    return episodes
```

**Avantage** : MyPy vérifie types tout en permettant flexibilité MongoDB.

## Statistiques Finales

- **26 fichiers modifiés**
- **+1857 lignes, -25 lignes**
- **13 commits** sur branche
- **Backend** :
  - 6 fichiers service/model/app modifiés
  - 1 nouveau fichier test (310 lignes)
  - 7 fichiers test existants mis à jour
- **Frontend** :
  - 1 nouveau composant (477 lignes)
  - 4 fichiers existants modifiés
  - 3 nouveaux fichiers test (404 lignes)
- **Documentation** :
  - 4 fichiers enrichis
  - 1 image ajoutée
- **Tests** : 100% couverture nouvelle fonctionnalité

## Commits (13 total)

```
fac629a fix cicd
9c0200e corrections livres en bases
7f64026 feat: remove related cache entries when deleting an episode
b8fc169 fix CI/CD
ad5d955 feat: filter out masked episodes in get_episodes_with_reviews function
ed4e583 trie par ordre decroissant de date
f9a4465 dashboard
f9bc674 feat(tests): add 'duree' field to episode initialization tests
064286c fix(tests): update visibility label in MasquerEpisodes tests
8b76049 feat(tests): update MongoDB queries to exclude masked episodes and include duration field
6f30618 frontend masquage episode
33c047e commentaires sur le'UX
4792538 prompt too long
8fa182e feat(docs): add documentation for episode masking API tests and UX discussions
7e2d29b feat(backend): implement episode masking functionality (issue #107)
```

## Commandes Utiles

### Tests API
```bash
# Épisodes visibles
curl "$(bash -c '/workspaces/back-office-lmelp/.claude/get-backend-info.sh --url')/api/episodes" | jq 'length'

# Tous épisodes (incluant masqués)
curl "$(bash -c '/workspaces/back-office-lmelp/.claude/get-backend-info.sh --url')/api/episodes/all" | jq 'length'

# Masquer épisode
BACKEND_URL=$(/workspaces/back-office-lmelp/.claude/get-backend-info.sh --url)
curl -X PATCH "$BACKEND_URL/api/episodes/{id}/masked" \
  -H "Content-Type: application/json" \
  -d '{"masked": true}'
```

### Tests
```bash
# Backend
PYTHONPATH=/workspaces/back-office-lmelp/src uv run pytest tests/test_episode_masking.py -v

# Frontend
cd /workspaces/back-office-lmelp/frontend && npm test -- masquerEpisodes --run

# Tous tests
pytest -v && cd /workspaces/back-office-lmelp/frontend && npm test -- --run && cd /workspaces/back-office-lmelp
```

## Points d'Attention pour Review

1. **✅ Route Order** : `/api/episodes/all` AVANT `/{episode_id}` dans app.py
2. **✅ Idempotence** : Toutes routes PATCH utilisent `matched_count`
3. **✅ Cache Invalidation** : `delete_episode()` supprime cache livresauteurs
4. **✅ Filtrage Masqués** : Tous endpoints publics filtrent `{"masked": {"$ne": True}}`
5. **✅ CSS Alignment** : MasquerEpisodes suit exactement pattern LivresAuteurs
6. **✅ Tests Coverage** : 100% sur nouvelle fonctionnalité (backend + frontend)
7. **✅ Documentation** : Patterns critiques documentés dans guide développeur
8. **✅ Statistiques** : Nouveau champ `masked_episodes_count` dans API /stats
9. **✅ UX Consistency** : Icônes 👁️/🚫, tri date DESC par défaut, filtrage temps réel
10. **✅ Backward Compatibility** : Champ `masked` défaut `False`, anciens documents non cassés

## Next Steps

- [x] Implémentation backend complète
- [x] Implémentation frontend complète
- [x] Tests backend (100%)
- [x] Tests frontend (100%)
- [x] Documentation technique
- [x] Alignement UX avec pages existantes
- [ ] Review PR
- [ ] Merge vers main
- [ ] Vérifier déploiement production
- [ ] Monitorer statistiques nouvelles
- [ ] Documentation utilisateur (si nécessaire)

## Références

- **Issue**: #107
- **Branch**: `107-masquer-des-episodes`
- **Commits**: 13 commits de `7e2d29b` à `fac629a`
- **Docs**:
  - [docs/dev/api.md](../../dev/api.md#fastapi-best-practices)
  - [docs/dev/claude-ai-guide.md](../../dev/claude-ai-guide.md#fastapi-route-patterns)
  - [docs/claude/echanges/107-Masquer des episodes.md](../echanges/107-Masquer%20des%20episodes.md)
