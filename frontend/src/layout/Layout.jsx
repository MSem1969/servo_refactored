// =============================================================================
// LAYOUT COMPONENT
// =============================================================================
// Componente layout principale che combina Sidebar + Header + Content
// Gestisce responsive, stati loading, errori globali
// =============================================================================

import React, { useState } from 'react';
import Sidebar from './Sidebar';
import Header from './Header';
import { Loading, ErrorBox } from '../common';
import { useSessionTracking } from '../hooks/useSessionTracking';
import FloatingWidget from '../components/CrmChatbot/FloatingWidget';

/**
 * Componente Layout principale
 * 
 * LOGICA IMPLEMENTATIVA:
 * - Combina Sidebar + Header + Content area
 * - Gestisce layout responsive
 * - Wrapper per stati globali (loading, errori)
 * - Context per comunicazione tra componenti layout
 * 
 * INTERRELAZIONI:
 * - Usato in: App.jsx come wrapper principale
 * - Dipende da: Sidebar, Header, Loading, ErrorBox
 * - Sostituisce: Layout hardcoded sparso in App.jsx
 * 
 * @param {React.Node} children - Contenuto pagina da renderizzare
 * @param {Object} currentUser - Dati utente corrente
 * @param {function} onLogout - Handler logout
 * @param {Array} menu - Array voci menu
 * @param {string} activePage - Pagina attiva corrente
 * @param {function} onPageChange - Handler cambio pagina
 * @param {string} pageTitle - Titolo pagina corrente
 * @param {string} pageSubtitle - Sottotitolo opzionale
 * @param {Array} notifications - Array notifiche
 * @param {function} onNotificationClick - Handler click notifica
 * @param {boolean} loading - Stato loading globale
 * @param {Error} error - Errore globale
 * @param {React.Node} headerActions - Azioni custom header
 */
const Layout = ({
  children,
  currentUser,
  onLogout,
  menu = [],
  activePage,
  onPageChange,
  pageTitle,
  pageSubtitle,
  notifications = [],
  onNotificationClick,
  loading = false,
  error = null,
  headerActions,
}) => {

  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  // Tracking tempo sessione per sezione (heartbeat ogni 60s)
  useSessionTracking(activePage);

  // Handler errori con retry
  const handleErrorRetry = () => {
    window.location.reload();
  };

  // Se c'è un errore globale, mostra error boundary
  if (error) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
        <div className="max-w-md w-full">
          <ErrorBox
            type="error"
            title="Errore Sistema"
            message={error.message || 'Si è verificato un errore imprevisto'}
            onRetry={handleErrorRetry}
            actions={
              <div className="flex gap-2">
                <button
                  onClick={() => window.location.href = '/'}
                  className="px-3 py-1.5 text-xs text-slate-600 hover:text-slate-800 transition-colors"
                >
                  🏠 Torna alla Home
                </button>
              </div>
            }
          />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 flex">
      {/* Sidebar */}
      <Sidebar
        menu={menu}
        activePage={activePage}
        onPageChange={onPageChange}
        currentUser={currentUser}
        onLogout={onLogout}
        collapsed={sidebarCollapsed}
      />

      {/* Main Content Area */}
      <main className="flex-1 ml-48 flex flex-col">
        {/* Header */}
        <Header
          title={pageTitle}
          subtitle={pageSubtitle}
          currentUser={currentUser}
          notifications={notifications}
          onNotificationClick={onNotificationClick}
          onLogout={onLogout}
          actions={headerActions}
        />

        {/* Content */}
        <div className="flex-1 relative">
          {loading ? (
            <div className="absolute inset-0 bg-white bg-opacity-75 backdrop-blur-sm flex items-center justify-center z-40">
              <Loading text="Caricamento..." size="lg" />
            </div>
          ) : (
            <div className="p-6 max-w-7xl mx-auto w-full">
              {children}
            </div>
          )}
        </div>
      </main>

      {/* Mobile Sidebar Overlay */}
      {sidebarCollapsed && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
          onClick={() => setSidebarCollapsed(false)}
        />
      )}

      {/* Widget Assistenza Flottante (non mostrare nella pagina Assistenza) */}
      {activePage !== 'crm' && (
        <FloatingWidget currentUser={currentUser} />
      )}
    </div>
  );
};

/**
 * Layout semplificato per pagine speciali (login, errori)
 */
const SimpleLayout = ({ children, title, subtitle }) => (
  <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50 flex flex-col items-center justify-center p-4">
    <div className="w-full max-w-md">
      {title && (
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-slate-800 mb-2">{title}</h1>
          {subtitle && (
            <p className="text-slate-600">{subtitle}</p>
          )}
        </div>
      )}
      {children}
    </div>

    {/* Footer Copyright */}
    <footer className="absolute bottom-4 left-0 right-0 text-center">
      <p className="text-[10px] text-slate-300 font-light tracking-wide">
        &copy; INTESA scs a r.l. ONLUS - P.IVA e CF 05022270879 - 2025 - empowered by Claude Code
      </p>
    </footer>
  </div>
);

/**
 * Layout fullscreen per modalità focus (es. supervisione)
 */
const FullscreenLayout = ({ children, onExit, title }) => (
  <div className="fixed inset-0 bg-white z-50 flex flex-col">
    {/* Minimal Header */}
    <header className="border-b border-slate-200 px-6 py-3 flex items-center justify-between bg-white">
      <h1 className="text-lg font-bold text-slate-800">{title}</h1>
      <button
        onClick={onExit}
        className="px-3 py-1.5 text-sm text-slate-600 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition-colors"
      >
        ✕ Esci
      </button>
    </header>
    
    {/* Content */}
    <main className="flex-1 overflow-auto">
      {children}
    </main>
  </div>
);

/**
 * Layout con pannelli divisi (per confronti, dual-view)
 */
const SplitLayout = ({ 
  children, 
  leftPanel, 
  rightPanel, 
  splitRatio = 50,
  currentUser,
  onLogout 
}) => (
  <div className="min-h-screen bg-slate-50 flex">
    <Sidebar
      menu={[]}
      currentUser={currentUser}
      onLogout={onLogout}
    />
    
    <div className="flex-1 ml-48 flex">
      {/* Left Panel */}
      <div 
        className="border-r border-slate-200 overflow-auto"
        style={{ width: `${splitRatio}%` }}
      >
        {leftPanel || children}
      </div>
      
      {/* Right Panel */}
      <div 
        className="overflow-auto"
        style={{ width: `${100 - splitRatio}%` }}
      >
        {rightPanel}
      </div>
    </div>
  </div>
);

// Export tutti i layout variants
export { 
  Layout, 
  SimpleLayout, 
  FullscreenLayout, 
  SplitLayout 
};
export default Layout;
