<template>
  <!-- PROTOTYPE JETABLE : barre de choix de variante, jamais en production -->
  <div v-if="actif" class="proto-switcher">
    <button @click="decaler(-1)" aria-label="Variante précédente">◀</button>
    <span>{{ courante }} ({{ variants[courante] }})</span>
    <button @click="decaler(1)" aria-label="Variante suivante">▶</button>
  </div>
</template>

<script>
export default {
  name: 'PrototypeSwitcher',
  props: { variants: { type: Object, required: true } },
  computed: {
    actif() { return !import.meta.env.PROD; },
    cles() { return Object.keys(this.variants); },
    courante() {
      const v = this.$route.query.variant;
      return this.cles.includes(v) ? v : this.cles[0];
    },
  },
  mounted() { window.addEventListener('keydown', this.clavier); },
  beforeUnmount() { window.removeEventListener('keydown', this.clavier); },
  methods: {
    decaler(d) {
      const i = (this.cles.indexOf(this.courante) + d + this.cles.length) % this.cles.length;
      this.$router.replace({ query: { ...this.$route.query, variant: this.cles[i] } });
    },
    clavier(e) {
      const t = e.target;
      if (t.closest && t.closest('input, textarea, select, [contenteditable]')) return;
      if (e.key === 'ArrowLeft') this.decaler(-1);
      if (e.key === 'ArrowRight') this.decaler(1);
    },
  },
};
</script>

<style scoped>
.proto-switcher {
  position: fixed; bottom: 1rem; left: 50%; transform: translateX(-50%);
  z-index: 9999; display: flex; gap: .75rem; align-items: center;
  background: #111; color: #ff0; padding: .4rem .9rem; border-radius: 999px;
  box-shadow: 0 4px 14px rgba(0,0,0,.4); font: 600 14px monospace;
}
.proto-switcher button { background: none; border: 1px solid #ff0; color: #ff0;
  border-radius: 50%; width: 1.8rem; height: 1.8rem; cursor: pointer; }
</style>
