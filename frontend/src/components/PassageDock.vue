<template>
  <!-- Lecteur fixé en bas de page : la lecture continue d'une page à l'autre -->
  <div v-if="p" class="passage-dock" role="region" aria-label="Lecteur de Passage">
    <div class="dock-quoi">
      <router-link v-if="p.livre_id" :to="`/livre/${p.livre_id}`" class="dock-titre">
        {{ p.titre }}
      </router-link>
      <span v-else class="dock-titre">{{ p.titre }}</span>
      <span class="dock-auteur">{{ p.auteur }}</span>
      <router-link v-if="p.date" :to="`/emissions/${p.date.replaceAll('-', '')}`" class="dock-emission">
        Émission du {{ dateLongue(p.date) }}
      </router-link>
    </div>

    <div class="dock-milieu">
      <div v-if="lecteur.statut === 'erreur'" class="dock-erreur">✖ {{ lecteur.erreur }}</div>
      <div v-else-if="lecteur.statut === 'fini'" class="dock-fin">
        <span>✓ Fin du passage</span>
        <button type="button" class="btn btn-secondary" @click="reprendre()">↻ Réécouter</button>
        <button
          v-if="lecteur.suivant"
          type="button"
          class="btn btn-primary"
          @click="jouer(lecteur.suivant, lecteur.liste)"
        >
          ▶ Suivant : {{ lecteur.suivant.titre }}
          <small v-if="lecteur.suivant.date !== p.date">({{ dateLongue(lecteur.suivant.date) }})</small>
        </button>
        <span v-else class="dock-dernier">dernier passage {{ contexte }}</span>
      </div>
      <template v-else>
        <div class="dock-controles">
          <button type="button" class="dock-saut" aria-label="Reculer de 10 secondes" @click="sauter(-10)">−10 s</button>
          <button
            type="button"
            class="btn btn-primary dock-lecture"
            :aria-label="lecteur.statut === 'lecture' ? 'Pause' : 'Lire'"
            @click="lecteur.statut === 'lecture' ? pause() : reprendre()"
          >
            {{ lecteur.statut === 'lecture' ? '⏸' : lecteur.statut === 'chargement' ? '…' : '▶' }}
          </button>
          <button type="button" class="dock-saut avance" aria-label="Avancer de 10 secondes" @click="sauter(10)">+10 s</button>
        </div>
        <div class="dock-progression">
          <span class="dock-temps">{{ formaterDuree(lecteur.position - debutSecondes(p)) }}</span>
          <span class="dock-barre" @click="seDeplacer">
            <span class="dock-rempli" :style="{ width: `${pourcentage}%` }"></span>
          </span>
          <span class="dock-temps">{{ formaterDuree(dureeSecondes(p)) }}</span>
        </div>
      </template>
    </div>

    <div class="dock-droite">
      <SignalerPassage />
      <button type="button" class="dock-fermer" aria-label="Fermer le lecteur" @click="arreter()">✕</button>
    </div>
  </div>
</template>

<script>
import {
  lecteur, jouer, pause, reprendre, sauter, aller, arreter, formaterDuree,
  debutSecondes, dureeSecondes,
} from '../services/lecteurPassages.js';
import SignalerPassage from './SignalerPassage.vue';

export default {
  name: 'PassageDock',
  components: { SignalerPassage },
  data() {
    return { lecteur };
  },
  computed: {
    p() {
      return lecteur.passage;
    },
    pourcentage() {
      const ecoule = lecteur.position - debutSecondes(this.p);
      return Math.min(100, Math.max(0, (100 * ecoule) / dureeSecondes(this.p)));
    },
    /** Le contexte de lecture : une émission, ou les émissions d'un livre. */
    contexte() {
      const episodes = new Set(lecteur.liste.map((x) => x.episode_id));
      return episodes.size > 1 ? 'de ce livre' : "de l'émission";
    },
  },
  watch: {
    // le lecteur ne masque pas le bas de la page
    p: {
      immediate: true,
      handler(passage) {
        document.body.style.paddingBottom = passage ? '6rem' : '';
      },
    },
  },
  beforeUnmount() {
    document.body.style.paddingBottom = '';
  },
  methods: {
    jouer, pause, reprendre, sauter, arreter, formaterDuree, debutSecondes, dureeSecondes,
    seDeplacer(evenement) {
      const zone = evenement.currentTarget.getBoundingClientRect();
      const fraction = (evenement.clientX - zone.left) / zone.width;
      aller(debutSecondes(this.p) + fraction * dureeSecondes(this.p));
    },
    dateLongue(date) {
      return new Date(`${date}T12:00:00`).toLocaleDateString('fr-FR', {
        day: 'numeric', month: 'long', year: 'numeric',
      });
    },
  },
};
</script>

<style scoped>
.passage-dock {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 900;
  height: 5.5rem;
  display: grid;
  grid-template-columns: 1fr 2fr auto;
  align-items: center;
  gap: 1rem;
  padding: 0 1.5rem;
  background: #fff;
  border-top: 1px solid #ddd;
  box-shadow: 0 -4px 14px rgba(0, 0, 0, 0.08);
}
.dock-quoi { display: flex; flex-direction: column; min-width: 0; }
.dock-titre {
  font-weight: 700; color: #222; text-decoration: none;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.dock-auteur { font-size: 0.85rem; color: #555; }
.dock-emission { font-size: 0.8rem; color: #0d6efd; text-decoration: none; }
.dock-milieu { display: flex; flex-direction: column; align-items: center; gap: 0.3rem; }
.dock-controles { display: flex; gap: 0.6rem; align-items: center; }
.dock-lecture { width: 2.6rem; height: 2.6rem; padding: 0; border-radius: 50%; font-size: 1.1rem; }
.dock-saut {
  padding: 0.1rem 0.5rem; border: 1px solid #dc3545; border-radius: 6px;
  background: #fff; color: #dc3545; cursor: pointer;
}
.dock-saut.avance { border-color: #198754; color: #198754; }
.dock-progression { display: flex; align-items: center; gap: 0.5rem; width: 100%; max-width: 36rem; }
.dock-temps { font: 0.8rem monospace; color: #555; }
.dock-barre {
  position: relative; flex: 1; height: 6px;
  background: #e3e6ea; border-radius: 3px; cursor: pointer;
}
.dock-rempli { position: absolute; left: 0; top: 0; bottom: 0; background: #0d6efd; border-radius: 3px; }
.dock-fin {
  display: flex; gap: 0.7rem; align-items: center; justify-content: center;
  color: #198754; white-space: nowrap;
}
.dock-fin .btn { padding: 0.3rem 0.8rem; font-size: 0.9rem; }
.dock-dernier { color: #777; font-size: 0.85rem; }
.dock-erreur { color: #b02a37; }
.dock-droite { display: flex; align-items: center; gap: .4rem; }
.dock-fermer { border: none; background: none; font-size: 1.1rem; color: #777; cursor: pointer; }
</style>
