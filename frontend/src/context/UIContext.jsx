// =============================================================================
// SERV.O v11.4 - UI CONTEXT
// =============================================================================
// Gestione centralizzata stato UI (navigazione, modali, toast)
// v11.4: Rimosso sistema notifiche mockup (notifiche via ticket CRM)
// =============================================================================

import React, { createContext, useContext, useState, useCallback } from 'react';

const UIContext = createContext(null);

export function UIProvider({ children }) {
  // Navigazione
  const [currentPage, setCurrentPage] = useState('dashboard');
  const [pageParams, setPageParams] = useState({});

  // Modali
  const [activeModal, setActiveModal] = useState(null);
  const [modalData, setModalData] = useState(null);

  // Toast temporanei
  const [toasts, setToasts] = useState([]);

  // Loading globale
  const [globalLoading, setGlobalLoading] = useState(false);

  // Errore globale
  const [globalError, setGlobalError] = useState(null);

  // Navigazione
  const navigateTo = useCallback((page, params = {}) => {
    setCurrentPage(page);
    setPageParams(params);
  }, []);

  const goBack = useCallback(() => {
    // Logica per tornare indietro in base alla pagina corrente
    const backMapping = {
      'ordine-detail': 'database',
      'supervisione': 'database',
    };
    const backPage = backMapping[currentPage] || 'dashboard';
    navigateTo(backPage);
  }, [currentPage, navigateTo]);

  // Modali
  const openModal = useCallback((modalName, data = null) => {
    setActiveModal(modalName);
    setModalData(data);
  }, []);

  const closeModal = useCallback(() => {
    setActiveModal(null);
    setModalData(null);
  }, []);

  // Toast/Alert temporaneo (auto-rimozione)
  const showToast = useCallback((message, type = 'info', duration = 3000) => {
    const id = Date.now();
    const toast = {
      id,
      type,
      title: type === 'error' ? 'Errore' : type === 'success' ? 'Successo' : 'Info',
      message,
      timestamp: new Date().toISOString(),
    };

    setToasts(prev => [...prev, toast]);

    if (duration > 0) {
      setTimeout(() => {
        setToasts(prev => prev.filter(t => t.id !== id));
      }, duration);
    }

    return id;
  }, []);

  // Loading globale
  const setLoading = useCallback((loading, message = null) => {
    setGlobalLoading(loading ? (message || true) : false);
  }, []);

  // Errore globale
  const setError = useCallback((error) => {
    setGlobalError(error);
    if (error) {
      setTimeout(() => setGlobalError(null), 5000);
    }
  }, []);

  const value = {
    // Navigazione
    currentPage,
    pageParams,
    navigateTo,
    goBack,

    // Modali
    activeModal,
    modalData,
    openModal,
    closeModal,

    // Toast temporanei
    toasts,
    showToast,

    // Loading/Error
    globalLoading,
    globalError,
    setLoading,
    setError,
  };

  return (
    <UIContext.Provider value={value}>
      {children}
    </UIContext.Provider>
  );
}

export function useUI() {
  const context = useContext(UIContext);
  if (!context) {
    throw new Error('useUI must be used within UIProvider');
  }
  return context;
}

export default UIContext;
