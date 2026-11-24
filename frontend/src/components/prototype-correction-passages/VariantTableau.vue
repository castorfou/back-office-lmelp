<template>
  <!-- Variante A : tableau, une ligne par livre, saisie mm:ss et réglage ±10 s -->
  <div class="vt">
    <table>
      <thead>
        <tr><th>Livre</th><th>Début</th><th>Fin</th><th>Durée</th><th>Origine</th><th></th></tr>
      </thead>
      <tbody>
        <tr v-for="p in liste" :key="p.id" :class="{ corrige: p.origine === 'corrige' }">
          <td><strong>{{ p.titre }}</strong><br /><small>{{ p.auteur }}</small>
            <small v-if="p.ecoute" class="indice" title="Bornes corrigées à l'écoute lors du ticket #391">
              <br />à l'écoute : {{ fmt(p.ecoute[0]) }}–{{ fmt(p.ecoute[1]) }}</small>
          </td>
          <td class="borne">
            <button @click="setDebut(p.id, p.debut - 10)">−10</button>
            <input :value="fmt(p.debut)" @change="setDebut(p.id, parse($event.target.value))" />
            <button @click="setDebut(p.id, p.debut + 10)">+10</button>
            <div class="sous">
              <button @click="jouer(p.debut, p.debut + 15)" title="Écouter les 15 s après le début">▶ début</button>
              <button @click="setDebut(p.id, position())" title="Prendre la position du lecteur">⤓ ici</button>
            </div>
          </td>
          <td class="borne">
            <button @click="setFin(p.id, p.fin - 10)">−10</button>
            <input :value="fmt(p.fin)" @change="setFin(p.id, parse($event.target.value))" />
            <button @click="setFin(p.id, p.fin + 10)">+10</button>
            <div class="sous">
              <button @click="jouer(p.fin - 15, p.fin)" title="Écouter les 15 s avant la fin">▶ fin</button>
              <button @click="setFin(p.id, position())" title="Prendre la position du lecteur">⤓ ici</button>
            </div>
          </td>
          <td>{{ fmt(p.fin - p.debut) }}</td>
          <td><span :class="['badge', p.origine]">{{ p.origine }}</span></td>
          <td>
            <button @click="jouer(p.debut, p.fin)">▶ tout</button>
            <button class="danger" @click="supprimer(p.id)">🗑 Supprimer</button>
          </td>
        </tr>
      </tbody>
    </table>

    <div class="bas">
      <div class="bloc">
        <h4>⚠️ Livres sans Passage ({{ livresSansPassage.length }})</h4>
        <p v-if="!livresSansPassage.length"><em>aucun</em></p>
        <ul>
          <li v-for="l in livresSansPassage" :key="l.livre_oid">
            {{ l.titre }} — <small>{{ l.auteur }}</small>
            <button @click="placer(l.livre_oid, position(), position() + 60)"
              title="Question ouverte : autoriser un Passage manuel ?">➕ placer à la position du lecteur</button>
          </li>
        </ul>
      </div>
      <div class="bloc" v-if="supprimes.length">
        <h4>🗑 Supprimés ({{ supprimes.length }})</h4>
        <ul>
          <li v-for="p in supprimes" :key="p.id">{{ p.titre }}
            <button @click="restaurer(p.id)">↩ restaurer</button></li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script>
import * as s from './store.js';

export default {
  name: 'VariantTableau',
  computed: {
    liste() { return s.visibles(); },
    supprimes() { return s.passages.filter((p) => p.supprime); },
    livresSansPassage() { return s.livresSansPassage; },
  },
  methods: { ...s },
};
</script>

<style scoped>
table { width: 100%; border-collapse: collapse; font-size: .9rem; }
th, td { border-bottom: 1px solid #e5e5e5; padding: .4rem; text-align: left; vertical-align: top; }
tr.corrige { background: #fff8e1; }
.borne input { width: 4.2rem; text-align: center; font-family: monospace; }
.borne .sous { margin-top: .25rem; }
.borne button, td button { font-size: .75rem; margin: 0 .1rem; cursor: pointer; }
.badge { padding: .1rem .4rem; border-radius: 4px; font-size: .75rem; }
.badge.auto { background: #e3f2fd; } .badge.corrige { background: #ffe082; }
.danger { color: #b00020; }
.indice { color: #888; }
.bas { display: flex; gap: 2rem; margin-top: 1rem; }
.bloc h4 { margin: .3rem 0; }
</style>
