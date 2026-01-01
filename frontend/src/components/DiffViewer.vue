<template>
  <div class="diff-viewer">
    <div class="diff-column">
      <h4>Phase 1 (Original)</h4>
      <pre>{{ original }}</pre>
    </div>
    <div class="diff-column">
      <h4>Phase 2 (Corrigé)</h4>
      <pre>{{ modified }}</pre>
    </div>
  </div>
</template>

<script>
export default {
  name: 'DiffViewer',
  props: {
    original: {
      type: String,
      required: true
    },
    modified: {
      type: String,
      required: true
    }
  }
};
</script>

<style scoped>
.diff-viewer {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
  margin-top: 1rem;
}

.diff-column {
  background: #f9f9f9;
  padding: 1rem;
  border-radius: 6px;
  border: 1px solid #ddd;
  overflow-x: auto;
}

.diff-column h4 {
  margin-top: 0;
  margin-bottom: 1rem;
  color: #333;
  font-size: 1rem;
  font-weight: 600;
}

.diff-column pre {
  overflow-x: auto;
  font-size: 0.85rem;
  white-space: pre-wrap;
  word-wrap: break-word;
  margin: 0;
  font-family: 'Courier New', Courier, monospace;
  line-height: 1.5;
}
</style>
