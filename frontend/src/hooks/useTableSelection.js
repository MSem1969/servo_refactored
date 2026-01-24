// =============================================================================
// SERV.O v10.1 - TABLE SELECTION HOOK
// =============================================================================
// Reusable hook for table checkbox/bulk selection
// =============================================================================

import { useState, useCallback, useMemo } from 'react';

/**
 * Hook for managing table row selection with bulk operations.
 *
 * @param {Array} items - Array of items (must have unique `id` or custom key)
 * @param {Object} options - Configuration options
 * @param {string} [options.idKey='id'] - Key to use as unique identifier
 * @param {Function} [options.isSelectable] - Function to determine if item is selectable
 * @returns {Object} Selection state and handlers
 *
 * @example
 * const {
 *   selectedIds,
 *   selectedItems,
 *   isSelected,
 *   toggle,
 *   select,
 *   deselect,
 *   selectAll,
 *   deselectAll,
 *   toggleAll,
 *   isAllSelected,
 *   isSomeSelected,
 *   selectedCount,
 *   clear,
 * } = useTableSelection(ordini, { idKey: 'id_testata' });
 */
export function useTableSelection(items = [], options = {}) {
  const { idKey = 'id', isSelectable = () => true } = options;

  const [selectedIds, setSelectedIds] = useState(new Set());

  // Get selectable items
  const selectableItems = useMemo(() =>
    items.filter(item => isSelectable(item)),
    [items, isSelectable]
  );

  // Get selected items objects
  const selectedItems = useMemo(() =>
    items.filter(item => selectedIds.has(item[idKey])),
    [items, selectedIds, idKey]
  );

  // Check if specific item is selected
  const isSelected = useCallback((item) => {
    const id = typeof item === 'object' ? item[idKey] : item;
    return selectedIds.has(id);
  }, [selectedIds, idKey]);

  // Toggle single item selection
  const toggle = useCallback((item) => {
    const id = typeof item === 'object' ? item[idKey] : item;
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, [idKey]);

  // Select single item
  const select = useCallback((item) => {
    const id = typeof item === 'object' ? item[idKey] : item;
    setSelectedIds(prev => new Set(prev).add(id));
  }, [idKey]);

  // Deselect single item
  const deselect = useCallback((item) => {
    const id = typeof item === 'object' ? item[idKey] : item;
    setSelectedIds(prev => {
      const next = new Set(prev);
      next.delete(id);
      return next;
    });
  }, [idKey]);

  // Select all selectable items
  const selectAll = useCallback(() => {
    setSelectedIds(new Set(selectableItems.map(item => item[idKey])));
  }, [selectableItems, idKey]);

  // Deselect all items
  const deselectAll = useCallback(() => {
    setSelectedIds(new Set());
  }, []);

  // Clear selection (alias for deselectAll)
  const clear = deselectAll;

  // Toggle all (if all selected → deselect all, else select all)
  const toggleAll = useCallback(() => {
    if (selectedIds.size === selectableItems.length && selectableItems.length > 0) {
      deselectAll();
    } else {
      selectAll();
    }
  }, [selectedIds.size, selectableItems.length, selectAll, deselectAll]);

  // Select multiple items
  const selectMultiple = useCallback((itemsToSelect) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      itemsToSelect.forEach(item => {
        const id = typeof item === 'object' ? item[idKey] : item;
        next.add(id);
      });
      return next;
    });
  }, [idKey]);

  // Deselect multiple items
  const deselectMultiple = useCallback((itemsToDeselect) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      itemsToDeselect.forEach(item => {
        const id = typeof item === 'object' ? item[idKey] : item;
        next.delete(id);
      });
      return next;
    });
  }, [idKey]);

  // Computed values
  const isAllSelected = selectableItems.length > 0 &&
    selectedIds.size === selectableItems.length;

  const isSomeSelected = selectedIds.size > 0 &&
    selectedIds.size < selectableItems.length;

  const selectedCount = selectedIds.size;

  const hasSelection = selectedIds.size > 0;

  return {
    // State
    selectedIds: Array.from(selectedIds),
    selectedIdsSet: selectedIds,
    selectedItems,
    selectedCount,

    // Checks
    isSelected,
    isAllSelected,
    isSomeSelected,
    hasSelection,

    // Single item operations
    toggle,
    select,
    deselect,

    // Bulk operations
    selectAll,
    deselectAll,
    toggleAll,
    selectMultiple,
    deselectMultiple,
    clear,
  };
}

export default useTableSelection;
