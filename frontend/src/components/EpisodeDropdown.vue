<template>
  <div class="episode-dropdown" ref="dropdown">
    <!-- Input avec valeur sélectionnée -->
    <div
      class="dropdown-input"
      @click="toggleDropdown"
      tabindex="0"
      @keydown.enter="toggleDropdown"
      @keydown.space.prevent="toggleDropdown"
      @keydown.escape="closeDropdown"
      @keydown.down.prevent="navigateDown"
      @keydown.up.prevent="navigateUp"
      role="combobox"
      :aria-expanded="isOpen"
      aria-haspopup="listbox"
    >
      <span v-if="selectedEpisode">{{ formatEpisode(selectedEpisode) }}</span>
      <span v-else class="placeholder">-- Sélectionner un épisode --</span>
      <span class="dropdown-arrow" :class="{ 'open': isOpen }">▼</span>
    </div>

    <!-- Liste déroulante -->
    <div
      v-show="isOpen"
      class="dropdown-list"
      role="listbox"
      ref="listbox"
    >
      <div
        v-for="(episode, index) in episodes"
        :key="episode.id"
        class="dropdown-option"
        :class="{
          'selected': episode.id === modelValue,
          'highlighted': index === highlightedIndex
        }"
        @click="selectEpisode(episode)"
        @mouseenter="highlightedIndex = index"
        role="option"
        :aria-selected="episode.id === modelValue"
        :ref="el => { if (episode.id === modelValue) selectedOptionRef = el }"
      >
        {{ formatEpisode(episode) }}
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'EpisodeDropdown',

  props: {
    modelValue: {
      type: String,
      default: ''
    },
    episodes: {
      type: Array,
      required: true
    }
  },

  emits: ['update:modelValue'],

  data() {
    return {
      isOpen: false,
      highlightedIndex: -1,
      selectedOptionRef: null
    };
  },

  computed: {
    selectedEpisode() {
      return this.episodes.find(ep => ep.id === this.modelValue);
    }
  },

  methods: {
    formatEpisode(episode) {
      const date = new Date(episode.date).toLocaleDateString('fr-FR');
      const title = episode.titre_corrige || episode.titre;

      // 🔴 Pastille rouge pour les épisodes avec livres incomplets
      if (episode.has_incomplete_books === true) {
        return `🔴 ${date} - ${title}`;
      }

      // 🟢 Pastille verte pour les épisodes traités / ⚪ Pastille grise pour non traités
      const prefix = episode.has_cached_books ? '🟢 ' : '⚪ ';
      return `${prefix}${date} - ${title}`;
    },

    toggleDropdown() {
      this.isOpen = !this.isOpen;
      if (this.isOpen) {
        this.$nextTick(() => {
          this.scrollToSelected();
        });
      }
    },

    closeDropdown() {
      this.isOpen = false;
      this.highlightedIndex = -1;
    },

    selectEpisode(episode) {
      this.$emit('update:modelValue', episode.id);
      this.closeDropdown();
    },

    scrollToSelected() {
      if (this.selectedOptionRef && this.$refs.listbox) {
        const listbox = this.$refs.listbox;
        const option = this.selectedOptionRef;

        // Centrer l'option sélectionnée dans la listbox
        const listboxHeight = listbox.clientHeight;
        const optionTop = option.offsetTop;
        const optionHeight = option.clientHeight;

        // Calculer la position de scroll pour centrer l'élément
        const scrollPosition = optionTop - (listboxHeight / 2) + (optionHeight / 2);
        listbox.scrollTop = Math.max(0, scrollPosition);
      }
    },

    navigateDown() {
      if (!this.isOpen) {
        this.isOpen = true;
        return;
      }

      if (this.highlightedIndex < this.episodes.length - 1) {
        this.highlightedIndex++;
      }
    },

    navigateUp() {
      if (!this.isOpen) {
        this.isOpen = true;
        return;
      }

      if (this.highlightedIndex > 0) {
        this.highlightedIndex--;
      }
    },

    handleClickOutside(event) {
      if (this.$refs.dropdown && !this.$refs.dropdown.contains(event.target)) {
        this.closeDropdown();
      }
    }
  },

  mounted() {
    document.addEventListener('click', this.handleClickOutside);
  },

  beforeUnmount() {
    document.removeEventListener('click', this.handleClickOutside);
  }
};
</script>

<style scoped>
.episode-dropdown {
  position: relative;
  width: 100%;
}

.dropdown-input {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  background: white;
  cursor: pointer;
  font-family: monospace;
  font-size: 0.9rem;
  transition: border-color 0.3s ease;
  min-height: 42px;
}

.dropdown-input:hover {
  border-color: #999;
}

.dropdown-input:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2);
}

.placeholder {
  color: #999;
}

.dropdown-arrow {
  margin-left: 0.5rem;
  transition: transform 0.2s ease;
  font-size: 0.7rem;
  color: #666;
}

.dropdown-arrow.open {
  transform: rotate(180deg);
}

.dropdown-list {
  position: absolute;
  top: 100%;
  left: 0;
  right: auto; /* Permettre à la liste de déborder */
  min-width: 100%;
  width: max-content; /* S'adapter au contenu le plus large */
  max-width: 90vw; /* Ne pas dépasser 90% de la largeur de l'écran */
  margin-top: 4px;
  max-height: 400px; /* Hauteur pour afficher 8 épisodes (50px par ligne) */
  overflow-y: auto;
  overflow-x: hidden;
  background: white;
  border: 1px solid #ddd;
  border-radius: 6px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  z-index: 1000;
}

.dropdown-option {
  padding: 0.75rem;
  cursor: pointer;
  font-family: monospace;
  font-size: 0.9rem;
  transition: background-color 0.15s ease;
  border-bottom: 1px solid #f0f0f0;
  white-space: nowrap; /* Empêcher le retour à la ligne */
}

.dropdown-option:last-child {
  border-bottom: none;
}

.dropdown-option:hover,
.dropdown-option.highlighted {
  background-color: #f5f5f5;
}

.dropdown-option.selected {
  background-color: #e8edff;
  font-weight: 500;
}

.dropdown-option.selected:hover {
  background-color: #d8e3ff;
}
</style>
