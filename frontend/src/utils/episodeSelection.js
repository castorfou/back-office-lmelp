/**
 * Sélection automatique d'épisode par priorité de pastille.
 *
 * Utilisé par les pages /livres-auteurs et /generation-avis-critiques
 * pour présélectionner l'épisode le plus pertinent à traiter.
 */

/**
 * Sélectionne l'épisode par priorité de pastille pour /livres-auteurs.
 *
 * Priorité: 🔴 incomplet > ⚪ non traité > 🟢 traité
 *
 * @param {Array} episodes - Liste d'épisodes avec has_incomplete_books et has_cached_books
 * @returns {Object|null} L'épisode sélectionné ou null
 */
export function selectEpisodeByBadgePriority(episodes) {
  if (!episodes || episodes.length === 0) return null;

  // 1. 🔴 Épisode avec livres incomplets (priorité max)
  const incomplete = episodes.find(ep => ep.has_incomplete_books === true);
  if (incomplete) return incomplete;

  // 2. ⚪ Épisode non traité (à traiter ensuite)
  const untreated = episodes.find(ep => ep.has_cached_books === false);
  if (untreated) return untreated;

  // 3. 🟢 Sinon le premier (déjà traité, plus récent)
  return episodes[0];
}

/**
 * Sélectionne l'épisode par priorité de pastille pour /generation-avis-critiques.
 *
 * Priorité: ⚪ sans summary > 🟢 avec summary
 *
 * @param {Array} episodes - Liste d'épisodes avec has_summary
 * @returns {Object|null} L'épisode sélectionné ou null
 */
export function selectEpisodeBySummaryPriority(episodes) {
  if (!episodes || episodes.length === 0) return null;

  // 1. ⚪ Épisode sans summary (à générer)
  const withoutSummary = episodes.find(ep => ep.has_summary === false);
  if (withoutSummary) return withoutSummary;

  // 2. 🟢 Sinon le premier (déjà traité)
  return episodes[0];
}
