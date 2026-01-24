// =============================================================================
// SERV.O v10.1 - MULTI-MODAL HOOK
// =============================================================================
// Reusable hook for managing multiple modal states
// =============================================================================

import { useState, useCallback, useMemo } from 'react';

/**
 * Hook for managing multiple modal states in a component.
 *
 * @param {Object} modalConfig - Configuration object defining modal names
 * @returns {Object} Modal state and handlers
 *
 * @example
 * const modals = useMultiModal({
 *   detail: { initialData: null },
 *   edit: { initialData: null },
 *   confirm: { initialData: null },
 *   delete: { initialData: null },
 * });
 *
 * // Open modal with data
 * modals.open('detail', { ordine: selectedOrdine });
 *
 * // Check if modal is open
 * if (modals.isOpen('detail')) { ... }
 *
 * // Get modal data
 * const ordine = modals.getData('detail')?.ordine;
 *
 * // Close modal
 * modals.close('detail');
 *
 * // In JSX
 * <Modal show={modals.isOpen('detail')} onHide={() => modals.close('detail')}>
 *   <OrdineDetail data={modals.getData('detail')} />
 * </Modal>
 */
export function useMultiModal(modalConfig = {}) {
  // Initialize state for all modals
  const [modalStates, setModalStates] = useState(() => {
    const initial = {};
    Object.keys(modalConfig).forEach(name => {
      initial[name] = {
        isOpen: false,
        data: modalConfig[name]?.initialData ?? null,
      };
    });
    return initial;
  });

  // Open a modal with optional data
  const open = useCallback((name, data = null) => {
    setModalStates(prev => ({
      ...prev,
      [name]: { isOpen: true, data },
    }));
  }, []);

  // Close a modal and optionally clear data
  const close = useCallback((name, clearData = false) => {
    setModalStates(prev => ({
      ...prev,
      [name]: {
        isOpen: false,
        data: clearData ? (modalConfig[name]?.initialData ?? null) : prev[name]?.data,
      },
    }));
  }, [modalConfig]);

  // Close all modals
  const closeAll = useCallback(() => {
    setModalStates(prev => {
      const next = {};
      Object.keys(prev).forEach(name => {
        next[name] = { ...prev[name], isOpen: false };
      });
      return next;
    });
  }, []);

  // Toggle a modal
  const toggle = useCallback((name, data = null) => {
    setModalStates(prev => ({
      ...prev,
      [name]: {
        isOpen: !prev[name]?.isOpen,
        data: prev[name]?.isOpen ? prev[name]?.data : (data ?? prev[name]?.data),
      },
    }));
  }, []);

  // Check if a modal is open
  const isOpen = useCallback((name) => {
    return modalStates[name]?.isOpen ?? false;
  }, [modalStates]);

  // Get modal data
  const getData = useCallback((name) => {
    return modalStates[name]?.data ?? null;
  }, [modalStates]);

  // Set modal data without changing open state
  const setData = useCallback((name, data) => {
    setModalStates(prev => ({
      ...prev,
      [name]: { ...prev[name], data },
    }));
  }, []);

  // Get props for a modal component
  const getModalProps = useCallback((name) => ({
    show: modalStates[name]?.isOpen ?? false,
    onHide: () => close(name),
    data: modalStates[name]?.data ?? null,
  }), [modalStates, close]);

  // Check if any modal is open
  const hasOpenModal = useMemo(() =>
    Object.values(modalStates).some(state => state.isOpen),
    [modalStates]
  );

  // Get list of open modals
  const openModals = useMemo(() =>
    Object.keys(modalStates).filter(name => modalStates[name].isOpen),
    [modalStates]
  );

  return {
    // Core operations
    open,
    close,
    closeAll,
    toggle,

    // State checks
    isOpen,
    getData,
    setData,
    getModalProps,

    // Computed
    hasOpenModal,
    openModals,

    // Raw state (for advanced use)
    states: modalStates,
  };
}

/**
 * Simplified hook for a single modal.
 *
 * @param {*} initialData - Initial data for the modal
 * @returns {Object} Modal state and handlers
 *
 * @example
 * const detailModal = useModal(null);
 *
 * // Open with data
 * detailModal.open(selectedOrdine);
 *
 * // In JSX
 * <Modal show={detailModal.isOpen} onHide={detailModal.close}>
 *   <Detail data={detailModal.data} />
 * </Modal>
 */
export function useModal(initialData = null) {
  const [isOpen, setIsOpen] = useState(false);
  const [data, setData] = useState(initialData);

  const open = useCallback((newData = null) => {
    setData(newData ?? initialData);
    setIsOpen(true);
  }, [initialData]);

  const close = useCallback(() => {
    setIsOpen(false);
  }, []);

  const closeAndClear = useCallback(() => {
    setIsOpen(false);
    setData(initialData);
  }, [initialData]);

  const toggle = useCallback((newData = null) => {
    setIsOpen(prev => {
      if (!prev && newData !== null) {
        setData(newData);
      }
      return !prev;
    });
  }, []);

  return {
    isOpen,
    data,
    open,
    close,
    closeAndClear,
    toggle,
    setData,
    props: { show: isOpen, onHide: close, data },
  };
}

export default useMultiModal;
