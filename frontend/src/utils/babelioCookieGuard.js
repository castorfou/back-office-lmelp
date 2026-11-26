/**
 * Garde Babelio commune aux pages qui déclenchent une lecture Babelio à la
 * demande (fusion de doublons, ré-extraction d'un livre, recherche).
 *
 * Sans cookie, Babelio répond 403, et un 403 peut tourner au ban IP (~24 h).
 * La page appelle `loadBabelioServiceStatus()` dans son `mounted`, après ses
 * propres chargements (le contenu de la page d'abord), affiche BabelioCookiePanel (`:status="babelioServiceStatus"`,
 * `@saved="loadBabelioServiceStatus"`, `@cookie-state="babelioCookieState = $event"`),
 * désactive ses actions tant que `babelioCookieActive` est faux, lance
 * `probeBabelio()` avant l'appel, et recharge le statut après un échec pour
 * que le panneau en affiche la cause (cookie, vérification humaine, ban).
 */
import axios from 'axios';

export const BABELIO_UNREACHABLE =
  'Babelio injoignable (IP probablement bannie, en général environ 24 h) : rien n\'a été envoyé.';

export const babelioCookieGuardMixin = {
  data() {
    return {
      // GET /api/babelio/status : seule source de l'état du cookie
      babelioServiceStatus: null,
      // 'missing' | 'expired' | 'active', émis par BabelioCookiePanel
      babelioCookieState: 'missing',
    };
  },

  computed: {
    babelioCookieActive() {
      return this.babelioCookieState === 'active';
    },
  },

  methods: {
    // Lire l'état du cookie côté serveur, sans jamais le réécrire.
    async loadBabelioServiceStatus() {
      try {
        const response = await axios.get('/api/babelio/status');
        this.babelioServiceStatus = response?.data || null;
      } catch {
        // Statut indisponible : pas de bandeau plutôt qu'un faux blocage
      }
    },

    // Essai TCP avant l'appel : une IP bannie ne répond pas, inutile
    // d'envoyer une requête à Babelio. Une sonde en erreur ne bloque pas.
    async probeBabelio() {
      try {
        const response = await axios.post('/api/babelio/probe');
        return response?.data?.reachable !== false;
      } catch {
        return true;
      }
    },
  },
};
