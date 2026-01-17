// =============================================================================
// SERV.O v10.1 - FILTER STATE HOOK
// =============================================================================
// Reusable hook for managing filter state with URL sync option
// =============================================================================

import { useState, useCallback, useMemo } from 'react';
import { buildQueryParams, mergeFilters } from './utils/buildQueryParams';

/**
 * Hook for managing filter state with debouncing and URL sync options.
 *
 * @param {Object} initialFilters - Initial filter values
 * @param {Object} options - Configuration options
 * @param {boolean} [options.syncUrl=false] - Sync filters with URL search params
 * @param {Function} [options.onChange] - Callback when filters change
 * @returns {Object} Filter state and handlers
 *
 * @example
 * const {
 *   filters,
 *   setFilter,
 *   setFilters,
 *   clearFilters,
 *   clearFilter,
 *   hasActiveFilters,
 *   activeFilterCount,
 *   queryString,
 * } = useFilterState({
 *   vendor: '',
 *   stato: '',
 *   q: '',
 *   data_da: '',
 *   data_a: '',
 * });
 *
 * // Set single filter
 * setFilter('vendor', 'ANGELINI');
 *
 * // Set multiple filters
 * setFilters({ vendor: 'ANGELINI', stato: 'ESTRATTO' });
 *
 * // Clear single filter
 * clearFilter('vendor');
 *
 * // Clear all filters
 * clearFilters();
 */
export function useFilterState(initialFilters = {}, options = {}) {
  const { onChange } = options;

  const [filters, setFiltersState] = useState(initialFilters);

  // Set a single filter value
  const setFilter = useCallback((key, value) => {
    setFiltersState(prev => {
      const next = { ...prev, [key]: value };
      onChange?.(next);
      return next;
    });
  }, [onChange]);

  // Set multiple filter values
  const setFilters = useCallback((newFilters) => {
    setFiltersState(prev => {
      const next = mergeFilters(prev, newFilters);
      onChange?.(next);
      return next;
    });
  }, [onChange]);

  // Replace all filters
  const replaceFilters = useCallback((newFilters) => {
    setFiltersState(newFilters);
    onChange?.(newFilters);
  }, [onChange]);

  // Clear a single filter
  const clearFilter = useCallback((key) => {
    setFiltersState(prev => {
      const next = { ...prev, [key]: initialFilters[key] ?? '' };
      onChange?.(next);
      return next;
    });
  }, [initialFilters, onChange]);

  // Clear all filters (reset to initial)
  const clearFilters = useCallback(() => {
    setFiltersState(initialFilters);
    onChange?.(initialFilters);
  }, [initialFilters, onChange]);

  // Check if any filter has a non-empty value
  const hasActiveFilters = useMemo(() => {
    return Object.entries(filters).some(([key, value]) => {
      const initial = initialFilters[key];
      return value !== initial && value !== '' && value !== null && value !== undefined;
    });
  }, [filters, initialFilters]);

  // Count active filters
  const activeFilterCount = useMemo(() => {
    return Object.entries(filters).filter(([key, value]) => {
      const initial = initialFilters[key];
      return value !== initial && value !== '' && value !== null && value !== undefined;
    }).length;
  }, [filters, initialFilters]);

  // Get as URL query string
  const queryString = useMemo(() => {
    return buildQueryParams(filters).toString();
  }, [filters]);

  // Get as URLSearchParams
  const queryParams = useMemo(() => {
    return buildQueryParams(filters);
  }, [filters]);

  // Get non-empty filters only
  const activeFilters = useMemo(() => {
    return Object.fromEntries(
      Object.entries(filters).filter(([, value]) =>
        value !== '' && value !== null && value !== undefined
      )
    );
  }, [filters]);

  return {
    // State
    filters,
    activeFilters,

    // Setters
    setFilter,
    setFilters,
    replaceFilters,

    // Clearers
    clearFilter,
    clearFilters,

    // Computed
    hasActiveFilters,
    activeFilterCount,
    queryString,
    queryParams,
  };
}

/**
 * Creates a filter handler for input/select onChange events.
 *
 * @param {Function} setFilter - setFilter function from useFilterState
 * @param {string} key - Filter key
 * @returns {Function} Event handler
 *
 * @example
 * <input
 *   value={filters.q}
 *   onChange={createFilterHandler(setFilter, 'q')}
 * />
 */
export function createFilterHandler(setFilter, key) {
  return (event) => {
    const value = event?.target?.value ?? event;
    setFilter(key, value);
  };
}

export default useFilterState;
