<template>
  <span class="possession-cell">
    <template v-if="item.calibre_in_library">
      <router-link
        :to="calibreSearchUrl"
        class="calibre-badge"
        title="Dans la bibliothèque Calibre — voir dans Calibre"
        data-test="calibre-link"
      >{{ item.calibre_read ? '✓ Lu' : '◯' }}</router-link>
      <span
        v-if="item.calibre_rating != null"
        class="calibre-note"
        :title="`Note Calibre: ${item.calibre_rating}/10`"
        data-test="calibre-rating"
      >{{ item.calibre_rating }}/10</span>
    </template>
    <a
      v-else
      :href="annasArchiveUrl"
      target="_blank"
      rel="noopener noreferrer"
      class="external-link"
      title="Rechercher sur Anna's Archive"
      data-test="annas-archive-link"
    >
      <img
        src="@/assets/annas-archive-icon.svg"
        alt="Anna's Archive"
        class="link-icon"
      />
    </a>
  </span>
</template>

<script>
/**
 * Statut de possession d'un livre (Issue #325), partagé Palmarès / Recommandations.
 * - Dans Calibre : ◯ (non lu) ou ✓ Lu (+ note), lien vers la recherche Calibre
 * - Absent de Calibre : lien de recherche Anna's Archive
 */
export default {
  name: 'CalibrePossessionCell',
  props: {
    item: { type: Object, required: true },
    annasArchiveBaseUrl: { type: String, required: true },
  },
  computed: {
    calibreSearchUrl() {
      return `/calibre?search=${encodeURIComponent(this.item.titre || '')}`;
    },
    annasArchiveUrl() {
      const searchQuery = `${this.item.titre || ''} - ${this.item.auteur_nom || ''}`;
      const encodedQuery = encodeURIComponent(searchQuery)
        .replace(/%20/g, '+')
        .replace(/'/g, '%27')
        .replace(/!/g, '%21');
      return `${this.annasArchiveBaseUrl}/search?index=&page=1&sort=&display=&q=${encodedQuery}`;
    },
  },
};
</script>

<style scoped>
.possession-cell {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  gap: 0.2rem;
}

.calibre-badge {
  font-size: 0.8rem;
  font-weight: 500;
  color: #00c851;
  text-decoration: none;
  white-space: nowrap;
}

.calibre-note {
  font-size: 0.75rem;
  color: #888;
}

.external-link {
  display: inline-flex;
  align-items: center;
  opacity: 0.7;
  transition: opacity 0.2s;
}

.external-link:hover {
  opacity: 1;
}

.link-icon {
  width: 20px;
  height: 20px;
  object-fit: contain;
}
</style>
