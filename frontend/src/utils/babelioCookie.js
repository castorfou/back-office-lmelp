/**
 * Vérifie la valeur d'un en-tête Cookie Babelio collé à la main.
 *
 * Même règle que normalize_cookie_header() côté serveur
 * (src/back_office_lmelp/services/babelio_service.py), qui reste l'autorité :
 * ici, elle sert à prévenir avant l'envoi. Copier une autre entrée des outils
 * de développement (User-Agent, Set-Cookie, tous les en-têtes) enverrait à
 * Babelio un cookie inutilisable, d'où un 403, puis un ban IP.
 *
 * @param {string} raw - texte collé
 * @returns {{ value: string, error: string|null }} valeur nettoyée, ou message d'erreur
 */

// Nom de cookie : un « token » HTTP (RFC 6265 / RFC 7230).
const COOKIE_NAME_RE = /^[!#$%&'*+\-.^_`|~0-9A-Za-z]+$/;
// Attributs propres à un en-tête Set-Cookie (réponse), jamais à un en-tête Cookie.
const SET_COOKIE_ATTRIBUTES = new Set(['path', 'domain', 'expires', 'max-age', 'httponly', 'secure', 'samesite']);

export function checkBabelioCookie(raw) {
  let value = (raw || '').trim();
  if (/[\r\n]/.test(value)) {
    return { value, error: "Plusieurs lignes collées : copiez uniquement la valeur de l'en-tête Cookie de la requête." };
  }
  if (value.toLowerCase().startsWith('cookie:')) {
    value = value.slice('cookie:'.length).trim();
  }

  const pairs = {};
  for (const rawPart of value.split(';')) {
    const part = rawPart.trim();
    if (!part) continue;
    const sep = part.indexOf('=');
    const name = (sep === -1 ? part : part.slice(0, sep)).trim();
    if (SET_COOKIE_ATTRIBUTES.has(name.toLowerCase())) {
      return {
        value,
        error: "Ceci ressemble à un en-tête Set-Cookie (réponse) : copiez l'en-tête Cookie des en-têtes de requête.",
      };
    }
    if (sep === -1 || !COOKIE_NAME_RE.test(name)) {
      return {
        value,
        error: "Ce n'est pas un en-tête Cookie : attendu une suite « nom=valeur; nom=valeur » (En-têtes de requête → Cookie).",
      };
    }
    pairs[name] = part.slice(sep + 1).trim();
  }

  // Babelio ne pose plus de jstsToken (Issue #367) : s'il est là, il part avec
  // le reste ; le cookie de session, lui, est toujours requis.
  if (!pairs.PHPSESSID) {
    return {
      value,
      error: "PHPSESSID absent : connectez-vous à babelio.com, rechargez la page et copiez l'en-tête Cookie de la requête « / ».",
    };
  }
  return { value, error: null };
}
