<template>
  <a
    v-if="hasValidUrl"
    :href="url"
    target="_blank"
    rel="noopener noreferrer"
    class="babelio-link"
  >
    🔗 {{ displayLabel }}
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
      default: 'Voir sur Babelio'
    }
  },

  computed: {
    hasValidUrl() {
      return this.url && this.url.trim().length > 0;
    },

    displayLabel() {
      return this.label || 'Voir sur Babelio';
    }
  }
};
</script>

<style scoped>
.babelio-link {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  color: #1976d2;
  text-decoration: none;
  font-size: 0.9rem;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  transition: background-color 0.2s ease;
}

.babelio-link:hover {
  background-color: #e3f2fd;
  text-decoration: underline;
}

.babelio-link:active {
  background-color: #bbdefb;
}
</style>
