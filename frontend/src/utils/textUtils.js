/**
 * Text utilities for accent-insensitive search and highlighting
 * Issue #92: Implement accent-insensitive search
 * Issue #173: Add support for typographic characters (ligatures, dashes, apostrophes)
 */

/**
 * Normalizes a string by removing accents and normalizing typographic characters
 * @param {string} str - The string to normalize
 * @returns {string} - The string without accents and with normalized typography
 */
export function removeAccents(str) {
  // Step 1: NFD decomposition + remove diacritics (Issue #92)
  let normalized = str
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '');

  // Step 2: Normalize ligatures (Issue #173)
  // œ (U+0153) → oe, Œ (U+0152) → oe
  normalized = normalized.replace(/œ/g, 'oe').replace(/Œ/g, 'Oe');
  // æ (U+00E6) → ae, Æ (U+00C6) → ae
  normalized = normalized.replace(/æ/g, 'ae').replace(/Æ/g, 'Ae');

  // Step 3: Normalize dashes and apostrophes (Issue #173)
  // – (U+2013 en dash) → - (hyphen)
  normalized = normalized.replace(/\u2013/g, '-');
  // ' (U+2019 right single quotation) → ' (simple apostrophe)
  normalized = normalized.replace(/\u2019/g, "'");

  return normalized;
}

/**
 * Creates an accent-insensitive regex pattern for highlighting
 * Supports ligatures, typographic characters, and accented variants
 * @param {string} term - The search term (e.g., "carrere", "oeuvre", "l'ami")
 * @returns {string} - A regex pattern that matches accented and typographic variants
 */
export function createAccentInsensitiveRegex(term) {
  const accentMap = {
    'a': '[aàâäáãåāăą]',
    'e': '[eèéêëēĕėęě]',
    'i': '[iìíîïĩīĭįı]',
    'o': '[oòóôöõøōŏő]',
    'u': '[uùúûüũūŭůűų]',
    'c': '[cç]',
    'n': '[nñń]',
    'y': '[yÿý]',
    '-': '[-\u2013]',   // Hyphen + en dash (Issue #173)
    "'": "['\u2019]",   // Simple + typographic apostrophe (Issue #173)
  };

  // Normalize the term first (remove accents, convert ligatures, normalize typography)
  const normalized = removeAccents(term.toLowerCase());

  // Build regex pattern with accent variants and ligature support
  const result = [];
  let i = 0;

  while (i < normalized.length) {
    const char = normalized[i];

    // Detect "oe" sequence → can match "oe" or "œ" (Issue #173)
    if (char === 'o' && i + 1 < normalized.length && normalized[i + 1] === 'e') {
      result.push('(?:[oòóôöõøōŏő][eèéêëēĕėęě]|œ)');
      i += 2;  // Skip both characters
    }
    // Detect "ae" sequence → can match "ae" or "æ" (Issue #173)
    else if (char === 'a' && i + 1 < normalized.length && normalized[i + 1] === 'e') {
      result.push('(?:[aàâäáãåāăą][eèéêëēĕėęě]|æ)');
      i += 2;  // Skip both characters
    }
    else {
      // Escape special regex characters
      if (/[.*+?^${}()|[\]\\]/.test(char)) {
        result.push('\\' + char);
      } else {
        result.push(accentMap[char] || char);
      }
      i += 1;
    }
  }

  return result.join('');
}

/**
 * Highlights search term in text with accent-insensitive matching
 * @param {string} text - The text to highlight in
 * @param {string} searchTerm - The search term
 * @returns {string} - HTML string with highlighted matches
 */
export function highlightSearchTermAccentInsensitive(text, searchTerm) {
  if (!text || !searchTerm) return text || '';

  const query = searchTerm.trim();
  if (query.length < 3) return text;

  const pattern = createAccentInsensitiveRegex(query);
  const regex = new RegExp(`(${pattern})`, 'gi');

  return text.replace(
    regex,
    '<strong style="background: #fff3cd; color: #856404; border-radius: 3px; font-weight: 700;">$1</strong>'
  );
}
