/**
 * Adresse publique de lmelp-streaming, déduite de celle par laquelle on lit
 * lmelp : `lmelp.<domaine>` → `https://lmelp-streaming.<domaine>`.
 * Renvoie null quand l'adresse de lmelp ne commence pas par « lmelp. »
 * (localhost, adresse IP…) : rien ne permet alors de la déduire.
 *
 * @param {{hostname: string}} location
 * @returns {string|null}
 */
export function adresseStreaming(location) {
  const [premier, ...reste] = (location?.hostname || '').split('.');
  if (premier !== 'lmelp' || reste.length < 2) return null;
  return `https://lmelp-streaming.${reste.join('.')}`;
}
