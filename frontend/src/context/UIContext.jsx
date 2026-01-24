// =============================================================================
// SERV.O v7.0 - UI CONTEXT
// =============================================================================
// Gestione centralizzata stato UI (navigazione, modali, notifiche)
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

  // Notifiche
  const [notifications, setNotifications] = useState([]);

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

  // Notifiche
  const addNotification = useCallback((notification) => {
    const id = Date.now();
    setNotifications(prev => [...prev, { ...notification, id, read: false }]);
    return id;
  }, []);

  const markNotificationRead = useCallback((id) => {
    setNotifications(prev =>
      prev.map(n => n.id === id ? { ...n, read: true } : n)
    );
  }, []);

  const clearNotification = useCallback((id) => {
    setNotifications(prev => prev.filter(n => n.id !== id));
  }, []);

  const clearAllNotifications = useCallback(() => {
    setNotifications([]);
  }, []);

  // Toast/Alert temporaneo
  const showToast = useCallback((message, type = 'info', duration = 3000) => {
    const id = addNotification({
      type,
      title: type === 'error' ? 'Errore' : type === 'success' ? 'Successo' : 'Info',
      message,
      timestamp: new Date().toISOString(),
    });

    if (duration > 0) {
      setTimeout(() => clearNotification(id), duration);
    }

    return id;
  }, [addNotification, clearNotification]);

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

    // Notifiche
    notifications,
    unreadCount: notifications.filter(n => !n.read).length,
    addNotification,
    markNotificationRead,
    clearNotification,
    clearAllNotifications,
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
