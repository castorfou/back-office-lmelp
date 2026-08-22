/**
 * Dérivation dynamique de l'URL du front-office lmelp à partir du hostname d'accès
 * Issue #265: l'URL était hardcodée sur localhost:8501, cassée en prod (NAS/reverse proxy)
 */

const DEFAULT_HOST = 'localhost';
const LMELP_PORT = '8501';
const IPV4_REGEX = /^\d{1,3}(\.\d{1,3}){3}$/;
const BO_SUFFIX_REGEX = /^([\w-]+)-bo\./;

/**
 * Calcule l'URL du front-office lmelp à partir du hostname d'accès au back-office.
 * @param {string} hostname - window.location.hostname du back-office
 * @param {string} [path] - chemin optionnel à ajouter après le domaine
 * @returns {string} URL complète du front-office lmelp
 */
export function getLmelpFrontOfficeUrl(hostname, path = '') {
  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    return `http://${hostname}:${LMELP_PORT}/${path}`;
  }

  if (IPV4_REGEX.test(hostname)) {
    return `http://${hostname}:${LMELP_PORT}/${path}`;
  }

  if (BO_SUFFIX_REGEX.test(hostname)) {
    const frontOfficeHost = hostname.replace(BO_SUFFIX_REGEX, '$1.');
    return `https://${frontOfficeHost}/${path}`;
  }

  return `http://${DEFAULT_HOST}:${LMELP_PORT}/${path}`;
}
