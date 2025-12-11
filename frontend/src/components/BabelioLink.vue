<template>
  <a
    v-if="hasValidUrl"
    :href="url"
    target="_blank"
    rel="noopener noreferrer"
    class="babelio-link"
    :title="`Voir sur Babelio: ${displayLabel}`"
  >
    <img
      src="@/assets/babelio-symbol-liaison.svg"
      alt="Icône Babelio"
      class="babelio-icon"
    />
    <span class="babelio-label">{{ displayLabel }}</span>
  </a>
</template>

<script>
export default {
  name: 'BabelioLink',

  props: {
    url: {
      type: String,
      default: null
    },
    label: {
      type: String,
      default: 'Fiche Babelio'
    }
  },

  computed: {
    hasValidUrl() {
      return this.url && this.url.trim().length > 0;
    },

    displayLabel() {
      return this.label || 'Fiche Babelio';
    }
  }
};
</script>

<style scoped>
.babelio-link {
  display: inline-flex;
  align-items: center;
  gap: 1rem;
  text-decoration: none;
  color: #333;
  transition: transform 0.2s ease, opacity 0.2s ease;
}

.babelio-link:hover {
  transform: scale(1.05);
  opacity: 0.9;
}

.babelio-icon {
  width: 80px;
  height: 80px;
  flex-shrink: 0;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transition: box-shadow 0.2s ease;
}

.babelio-link:hover .babelio-icon {
  box-shadow: 0 4px 12px rgba(251, 185, 30, 0.3);
}

.babelio-label {
  font-size: 1rem;
  font-weight: 500;
  color: #333;
}
</style>
