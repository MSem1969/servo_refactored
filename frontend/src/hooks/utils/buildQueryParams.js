// =============================================================================
// SERV.O v10.1 - QUERY PARAMS UTILITY
// =============================================================================
// Utility for building URL query parameters from filter objects
// =============================================================================

/**
 * Builds URLSearchParams from a filters object.
 * Filters out undefined, null, and empty string values.
 *
 * @param {Object} filters - Object with filter key-value pairs
 * @returns {URLSearchParams} - URLSearchParams instance
 *
 * @example
 * const params = buildQueryParams({ vendor: 'ANGELINI', stato: '', q: null });
 * // Returns URLSearchParams with only 'vendor=ANGELINI'
 */
export function buildQueryParams(filters = {}) {
  const params = new URLSearchParams();

  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      // Handle arrays (e.g., multiple stati)
      if (Array.isArray(value)) {
        value.forEach(v => params.append(key, String(v)));
      } else {
        params.append(key, String(value));
      }
    }
  });

  return params;
}

/**
 * Converts filters object to query string.
 *
 * @param {Object} filters - Object with filter key-value pairs
 * @returns {string} - Query string (without leading '?')
 */
export function filtersToQueryString(filters = {}) {
  const params = buildQueryParams(filters);
  return params.toString();
}

/**
 * Parses URL search params back to object.
 *
 * @param {string|URLSearchParams} searchParams - URL search params
 * @returns {Object} - Parsed filters object
 */
export function parseQueryParams(searchParams) {
  const params = typeof searchParams === 'string'
    ? new URLSearchParams(searchParams)
    : searchParams;

  const result = {};

  params.forEach((value, key) => {
    if (result[key]) {
      // Multiple values for same key → array
      if (Array.isArray(result[key])) {
        result[key].push(value);
      } else {
        result[key] = [result[key], value];
      }
    } else {
      result[key] = value;
    }
  });

  return result;
}

/**
 * Merges current filters with new values, removing empty values.
 *
 * @param {Object} currentFilters - Current filter state
 * @param {Object} newFilters - New filter values to merge
 * @returns {Object} - Merged filters
 */
export function mergeFilters(currentFilters, newFilters) {
  const merged = { ...currentFilters, ...newFilters };

  // Remove empty values
  return Object.fromEntries(
    Object.entries(merged).filter(([, value]) =>
      value !== undefined && value !== null && value !== ''
    )
  );
}

export default buildQueryParams;
