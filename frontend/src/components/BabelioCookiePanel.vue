<template>
  <div class="babelio-cookie-panel" data-test="babelio-cookie-panel">
    <component
      :is="collapsible ? 'details' : 'div'"
      :open="collapsible ? open : undefined"
      class="babelio-cookie-box"
      data-test="babelio-cookie-details"
    >
      <component :is="collapsible ? 'summary' : 'div'" class="babelio-cookie-summary">
        🔑 Cookie Babelio
        <span
          :class="['cookie-status', badge.cssClass]"
          :data-cookie-state="cookieState"
          data-test="cookie-badge"
        >{{ badge.label }}</span>
        <!-- Actions de la page hôte sur la ligne du cookie (ex : relancer la validation).
             Dans un <summary>, le bouton doit appeler preventDefault pour ne pas plier le panneau. -->
        <span v-if="$slots.actions" class="babelio-cookie-actions">
          <slot name="actions" />
        </span>
      </component>
      <div class="babelio-cookie-form">
        <p class="cookie-help">
          Le cookie <code>jstsToken</code> (TTL ~5 min) est requis pour éviter les blocages 403.
          Il est stocké <strong>côté serveur</strong> et utilisé automatiquement par toutes les requêtes Babelio.
          Le navigateur n'en garde aucun : chaque cookie se colle frais.
          <slot />
        </p>

        <!-- Cookie actif : pas de champ, seulement de quoi le remplacer -->
        <div v-if="!formVisible" class="cookie-actions">
          <button class="btn-save-cookie" data-test="cookie-replace" @click="startReplacing">
            Entrer un cookie plus récent
          </button>
        </div>

        <template v-else>
          <details class="cookie-instructions">
            <summary>Comment obtenir le cookie ?</summary>
            <ol>
              <li>Connectez-vous à votre compte Babelio sur <a href="https://www.babelio.com" target="_blank" rel="noopener">babelio.com</a>, jusqu'à voir votre avatar : un bouton « Continuer en tant que… » affiché ne suffit pas. Un cookie copié sans être connecté déclenche une vérification humaine (403)</li>
              <li>Ouvre les DevTools (F12) → onglet <strong>Réseau</strong></li>
              <li>Recharge la page, clique sur la requête <code>/</code> de babelio.com</li>
              <li>Dans <strong>En-têtes de requête</strong>, clic droit sur <strong>Cookie</strong> → Copier la valeur</li>
              <li>Colle-la ci-dessous et clique Enregistrer</li>
            </ol>
          </details>
          <textarea
            v-model="cookieInput"
            class="cookie-input"
            placeholder="jstsToken=...; p=FR; disclaimer=1; ..."
            rows="2"
            autocomplete="off"
            :aria-invalid="formatError ? 'true' : 'false'"
          ></textarea>
          <p v-if="formatError" class="cookie-format-error" data-test="cookie-format-error">⚠ {{ formatError }}</p>
          <div class="cookie-actions">
            <button
              class="btn-save-cookie"
              data-test="cookie-save"
              :disabled="!cookieInput.trim() || !!formatError || saving"
              @click="saveCookie"
            >
              Enregistrer
            </button>
            <!-- Vide le champ seulement : le cookie du serveur n'est jamais effacé d'ici -->
            <button
              v-if="cookieInput"
              class="btn-clear-cookie"
              data-test="cookie-input-clear"
              @click="clearInput"
            >
              Vider
            </button>
            <button v-if="replacing" class="btn-clear-cookie" data-test="cookie-cancel" @click="cancelReplacing">
              Annuler
            </button>
          </div>
        </template>

        <p v-if="anonymousWarning" class="cookie-anonymous-warning" data-test="cookie-anonymous-warning">⚠ {{ anonymousWarning }}</p>

        <div v-if="justSaved || saveError" class="cookie-feedback">
          <span v-if="justSaved" class="cookie-saved-confirmation" data-test="cookie-saved-confirmation">✓ Cookie enregistré</span>
          <span v-if="saveError" class="cookie-save-error" data-test="cookie-save-error">{{ saveError }}</span>
        </div>
      </div>
    </component>
  </div>
</template>

<script>
import axios from 'axios';
import { checkBabelioCookie } from '../utils/babelioCookie.js';

// Clés où les anciennes versions gardaient le cookie dans le navigateur.
const LEGACY_STORAGE_KEYS = ['babelio_cookies', 'babelio_cookies_saved_at'];

const BADGES = {
  missing: { label: '⚠ non configuré (risque 403)', cssClass: 'cookie-missing' },
  expired: { label: '⏰ périmé — collez un cookie frais', cssClass: 'cookie-expired' },
  active: { label: '✓ Actif côté serveur', cssClass: 'cookie-ok' },
};

// Repli si le statut serveur signale un cookie anonyme sans réponse d'enregistrement
// sous la main (même texte que BABELIO_ANONYMOUS_COOKIE_WARNING côté serveur)
const ANONYMOUS_COOKIE_WARNING =
  'Cookie anonyme : Babelio risque de demander une vérification humaine. '
  + 'Connectez-vous à Babelio puis copiez un nouveau cookie.';

// Rafraîchissement du temps restant affiché (pas d'appel serveur)
const CLOCK_TICK_MS = 5000;

/**
 * Panneau « Cookie Babelio » partagé par les pages qui interrogent Babelio.
 *
 * Le serveur est la seule source du cookie : le badge ne lit que `status`
 * (réponse de GET /api/babelio/status, possédée par la page) et le champ
 * démarre toujours vide. Un cookie gardé dans le navigateur, renvoyé tel quel,
 * passerait pour frais côté serveur (il est daté à la réception) : Babelio
 * répondrait 403, et ses 403 deviennent un ban IP d'environ 24 h.
 */
export default {
  name: 'BabelioCookiePanel',

  props: {
    status: { type: Object, default: null },
    open: { type: Boolean, default: false },
    collapsible: { type: Boolean, default: true },
  },

  // cookie-state : 'missing' | 'expired' | 'active', émis à chaque changement
  // (compte à rebours compris) pour que la page grise ses actions Babelio
  emits: ['saved', 'cookie-state'],

  data() {
    return {
      cookieInput: '',
      saving: false,
      justSaved: false,
      saveError: null,
      // Avertissement renvoyé par POST /api/babelio/cookie (cookie anonyme)
      saveWarning: null,
      // Champ de saisie ouvert alors qu'un cookie actif est déjà sur le serveur
      replacing: false,
      // Horloge locale : fait vieillir le cookie entre deux statuts serveur
      statusReceivedAt: Date.now(),
      now: Date.now(),
      clockTimer: null,
      justSavedTimeout: null,
    };
  },

  computed: {
    // Secondes restantes avant que le serveur ne refuse le cookie (null si inconnu)
    remainingSec() {
      const st = this.status;
      if (!st || typeof st.cookie_age_sec !== 'number' || typeof st.cookie_max_age_sec !== 'number') {
        return null;
      }
      const elapsedSec = (this.now - this.statusReceivedAt) / 1000;
      return st.cookie_max_age_sec - st.cookie_age_sec - elapsedSec;
    },
    cookieState() {
      const st = this.status;
      if (!st || !st.cookie_active) return 'missing';
      if (st.cookie_expired || (this.remainingSec !== null && this.remainingSec <= 0)) return 'expired';
      return 'active';
    },
    savedAtLabel() {
      const age = this.status?.cookie_age_sec;
      if (typeof age !== 'number') return null;
      return new Date(this.statusReceivedAt - age * 1000).toLocaleTimeString('fr-FR', {
        hour: '2-digit',
        minute: '2-digit',
      });
    },
    remainingLabel() {
      if (this.remainingSec === null) return null;
      return this.remainingSec >= 60 ? `~${Math.round(this.remainingSec / 60)} min` : '< 1 min';
    },
    // Cookie copié sans être connecté au compte : Babelio exigera un captcha
    anonymousWarning() {
      if (this.saveWarning) return this.saveWarning;
      if (this.status?.cookie_active && this.status.cookie_anonymous === true) {
        return ANONYMOUS_COOKIE_WARNING;
      }
      return null;
    },
    badge() {
      const badge = BADGES[this.cookieState];
      if (this.cookieState !== 'active') return badge;
      const parts = [badge.label];
      if (this.anonymousWarning) parts.push('⚠ anonyme');
      if (this.savedAtLabel) parts.push(`enregistré à ${this.savedAtLabel}`);
      if (this.remainingLabel) parts.push(`expire dans ${this.remainingLabel}`);
      return { ...badge, label: parts.join(' · ') };
    },
    // Sans cookie utilisable, le champ s'affiche d'emblée ; sinon sur demande
    formVisible() {
      return this.cookieState !== 'active' || this.replacing;
    },
    // Forme du texte collé, vérifiée avant l'envoi (le serveur revérifie)
    cookieCheck() {
      return checkBabelioCookie(this.cookieInput);
    },
    formatError() {
      return this.cookieInput.trim() ? this.cookieCheck.error : null;
    },
  },

  watch: {
    cookieState: {
      immediate: true,
      handler(state) {
        this.$emit('cookie-state', state);
      },
    },
    status: {
      immediate: true,
      handler() {
        this.statusReceivedAt = Date.now();
        this.now = this.statusReceivedAt;
        this.updateClock();
      },
    },
  },

  mounted() {
    for (const key of LEGACY_STORAGE_KEYS) {
      try {
        localStorage.removeItem(key);
      } catch {
        // Stockage inaccessible (navigation privée…) : rien à purger
      }
    }
  },

  beforeUnmount() {
    this.clearTimers();
  },

  methods: {
    updateClock() {
      const running = this.status?.cookie_active && !this.status?.cookie_expired;
      if (running && !this.clockTimer) {
        this.clockTimer = setInterval(() => {
          this.now = Date.now();
        }, CLOCK_TICK_MS);
      } else if (!running && this.clockTimer) {
        clearInterval(this.clockTimer);
        this.clockTimer = null;
      }
    },

    clearTimers() {
      if (this.clockTimer) {
        clearInterval(this.clockTimer);
        this.clockTimer = null;
      }
      if (this.justSavedTimeout) {
        clearTimeout(this.justSavedTimeout);
        this.justSavedTimeout = null;
      }
    },

    startReplacing() {
      this.cookieInput = '';
      this.saveError = null;
      this.replacing = true;
    },

    clearInput() {
      this.cookieInput = '';
      this.saveError = null;
    },

    cancelReplacing() {
      this.cookieInput = '';
      this.saveError = null;
      this.replacing = false;
    },

    async saveCookie() {
      if (!this.cookieInput.trim() || this.formatError) return;
      const { value } = this.cookieCheck;
      this.saving = true;
      this.saveError = null;
      this.saveWarning = null;
      try {
        const response = await axios.post('/api/babelio/cookie', { cookie: value });
        this.saveWarning = response?.data?.warning || null;
      } catch (error) {
        this.saveError = error?.response?.data?.detail || "Échec de l'enregistrement du cookie";
        return;
      } finally {
        this.saving = false;
      }
      this.cookieInput = '';
      this.replacing = false;
      this.justSaved = true;
      if (this.justSavedTimeout) clearTimeout(this.justSavedTimeout);
      this.justSavedTimeout = setTimeout(() => {
        this.justSaved = false;
        this.justSavedTimeout = null;
      }, 3000);
      this.$emit('saved');
    },
  },
};
</script>

<style scoped>
.babelio-cookie-box {
  border: 1px solid #dee2e6;
  border-radius: 6px;
  overflow: hidden;
}

.babelio-cookie-summary {
  padding: 0.5rem 1rem;
  background: #f8f9fa;
  font-size: 0.85rem;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.babelio-cookie-actions {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

summary.babelio-cookie-summary {
  cursor: pointer;
  user-select: none;
}

.cookie-status {
  font-size: 0.75rem;
  padding: 1px 6px;
  border-radius: 10px;
}

.cookie-ok {
  background: #d4edda;
  color: #155724;
}

.cookie-missing {
  background: #fff3cd;
  color: #856404;
}

.cookie-expired {
  background: #ffe5b4;
  color: #8a5a00;
}

.babelio-cookie-form {
  padding: 0.75rem 1rem;
  background: white;
}

.cookie-help {
  font-size: 0.8rem;
  color: #6c757d;
  margin-bottom: 0.5rem;
}

.cookie-instructions { margin-bottom: 1rem; font-size: 0.9rem; }
.cookie-instructions ol { margin: 0.5rem 0 0 1.5rem; padding-left: 0; }
.cookie-instructions li { margin-bottom: 0.25rem; }

.cookie-input {
  width: 100%;
  font-family: monospace;
  font-size: 0.75rem;
  padding: 0.4rem;
  border: 1px solid #ced4da;
  border-radius: 4px;
  resize: vertical;
  box-sizing: border-box;
}

.cookie-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

.btn-save-cookie,
.btn-clear-cookie {
  padding: 4px 12px;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.8rem;
}

.btn-save-cookie { background: #0d6efd; }
.btn-clear-cookie { background: #6c757d; }

.btn-save-cookie:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.cookie-feedback {
  margin-top: 0.5rem;
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.cookie-anonymous-warning {
  font-size: 0.8rem;
  color: #856404;
  background: #fff3cd;
  border-radius: 4px;
  padding: 0.4rem 0.6rem;
  margin: 0.5rem 0 0;
}

.cookie-format-error {
  font-size: 0.8rem;
  color: #721c24;
  margin: 0.25rem 0 0;
}

.cookie-saved-confirmation {
  font-size: 0.8rem;
  color: #155724;
  align-self: center;
}

.cookie-save-error {
  font-size: 0.8rem;
  color: #721c24;
  align-self: center;
}
</style>
