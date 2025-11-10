/**
 * Text utilities for accent-insensitive search and highlighting
 * Issue #92: Implement accent-insensitive search
 */

/**
 * Normalizes a string by removing accents (NFD decomposition + removing diacritics)
 * @param {string} str - The string to normalize
 * @returns {string} - The string without accents
 */
export function removeAccents(str) {
  return str
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '');
}

/**
 * Creates an accent-insensitive regex pattern for highlighting
 * @param {string} term - The search term (e.g., "carrere")
 * @returns {string} - A regex pattern that matches accented variants
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
  };

  // Normalize the term first (remove accents)
  const normalized = removeAccents(term.toLowerCase());

  // Build regex pattern with accent variants
  const pattern = normalized
    .split('')
    .map(char => {
      // Escape special regex characters
      if (/[.*+?^${}()|[\]\\]/.test(char)) {
        return '\\' + char;
      }
      return accentMap[char] || char;
    })
    .join('');

  return pattern;
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
