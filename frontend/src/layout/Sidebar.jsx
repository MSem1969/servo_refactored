// =============================================================================
// SIDEBAR COMPONENT
// =============================================================================
// Componente sidebar modulare per navigazione principale
// Gestisce menu dinamico, user info, logout
// =============================================================================

import React, { useState } from 'react';
import { Button } from '../common';
import Avatar from '../components/Avatar';
import ProfiloModal from '../components/ProfiloModal';
import { PasswordChangeModal } from './Header'; // v11.0: Cambio password dalla sidebar

/**
 * Componente Sidebar per navigazione principale
 * 
 * LOGICA IMPLEMENTATIVA:
 * - Menu dinamico basato su permessi utente
 * - Stati attivi gestiti automaticamente
 * - User info con avatar generato
 * - Logout con conferma opzionale
 * 
 * INTERRELAZIONI:
 * - Usato in: Layout principale
 * - Dipende da: Button component
 * - Sostituisce: Sidebar hardcoded in App.jsx
 * 
 * @param {Array} menu - Array voci menu {id, label, icon}
 * @param {string} activePage - Pagina attiva corrente
 * @param {function} onPageChange - Handler cambio pagina
 * @param {Object} currentUser - Dati utente corrente
 * @param {function} onLogout - Handler logout
 * @param {string} version - Versione app (default: v6.2)
 * @param {boolean} collapsed - Sidebar compatta (future use)
 * @param {function} onUserUpdate - Callback dopo aggiornamento profilo utente
 */
const Sidebar = ({
  menu = [],
  activePage,
  onPageChange,
  currentUser,
  onLogout,
  version = 'v11.0',
  collapsed = false,
  onUserUpdate
}) => {

  // State per modal profilo e password
  const [showProfiloModal, setShowProfiloModal] = useState(false);
  const [showPasswordModal, setShowPasswordModal] = useState(false); // v11.0

  // Handler logout con conferma opzionale
  const handleLogout = () => {
    if (window.confirm('Sei sicuro di voler uscire?')) {
      onLogout?.();
    }
  };

  // Handler aggiornamento profilo
  const handleProfiloUpdate = (updatedUser) => {
    // Aggiorna localStorage
    localStorage.setItem('servo_user', JSON.stringify(updatedUser));
    // Callback al parent per aggiornare lo state globale
    onUserUpdate?.(updatedUser);
  };

  return (
    <aside className="fixed left-0 top-0 h-full w-48 bg-slate-900 text-white flex flex-col z-50 shadow-xl">
      {/* Header App */}
      <div className="p-3 border-b border-slate-700">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-blue-700 rounded-lg flex items-center justify-center text-xs font-bold shadow-lg">
            S.O
          </div>
          <div>
            <h1 className="font-bold text-sm tracking-tight">SERV.O</h1>
            <p className="text-xs text-slate-400">{version}</p>
          </div>
        </div>
      </div>
      
      {/* Navigation Menu */}
      <nav className="flex-1 p-2 space-y-1 overflow-y-auto">
        {menu.map((item) => {
          const isActive = activePage === item.id;
          
          return (
            <button
              key={item.id}
              onClick={() => onPageChange?.(item.id)}
              className={`
                w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 group
                ${isActive 
                  ? 'bg-blue-600 text-white shadow-lg' 
                  : 'text-slate-300 hover:text-white hover:bg-slate-800 hover:translate-x-0.5'
                }
              `}
            >
              {/* Icon */}
              <span className={`text-base transition-transform duration-200 ${
                isActive ? 'scale-110' : 'group-hover:scale-105'
              }`}>
                {item.icon}
              </span>
              
              {/* Label */}
              <span className="flex-1 text-left truncate">
                {item.label}
              </span>
              
              {/* Active indicator */}
              {isActive && (
                <div className="w-1.5 h-1.5 bg-white rounded-full animate-pulse" />
              )}
            </button>
          );
        })}
      </nav>
      
      {/* User Section */}
      <div className="p-3 border-t border-slate-700 bg-slate-800/50">
        <div className="bg-slate-800 rounded-xl p-3 space-y-3">
          {/* User Info - Cliccabile per aprire profilo */}
          <div
            className="flex items-center gap-3 cursor-pointer hover:bg-slate-700/50 -mx-2 px-2 py-1 rounded-lg transition-colors"
            onClick={() => setShowProfiloModal(true)}
            title="Modifica profilo"
          >
            {/* Avatar con componente dedicato */}
            <Avatar user={currentUser} size="md" />

            {/* User Details */}
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-white truncate">
                {currentUser?.nome} {currentUser?.cognome}
              </p>
              <div className="flex items-center gap-2">
                <p className="text-xs text-slate-400 capitalize">
                  {currentUser?.ruolo}
                </p>
                {/* Online indicator */}
                <div className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse" />
              </div>
            </div>
          </div>

          {/* User Actions */}
          <div className="flex gap-2">
            {/* Profilo */}
            <button
              onClick={() => setShowProfiloModal(true)}
              className="flex-1 px-2 py-1.5 text-xs text-slate-300 hover:text-white hover:bg-slate-700 rounded-md transition-colors flex items-center justify-center gap-1"
              title="Il mio profilo"
            >
              👤
            </button>

            {/* v11.0: Cambio Password */}
            <button
              onClick={() => setShowPasswordModal(true)}
              className="flex-1 px-2 py-1.5 text-xs text-slate-300 hover:text-white hover:bg-slate-700 rounded-md transition-colors flex items-center justify-center gap-1"
              title="Cambia password"
            >
              🔑
            </button>

            {/* Settings - Navigazione a Impostazioni */}
            <button
              onClick={() => onPageChange?.('settings')}
              className="flex-1 px-2 py-1.5 text-xs text-slate-300 hover:text-white hover:bg-slate-700 rounded-md transition-colors flex items-center justify-center gap-1"
              title="Impostazioni"
            >
              ⚙️
            </button>

            {/* Logout */}
            <button
              onClick={handleLogout}
              className="flex-1 px-2 py-1.5 text-xs text-slate-300 hover:text-white hover:bg-red-600 rounded-md transition-colors flex items-center justify-center gap-1"
              title="Logout"
            >
              🚪
            </button>
          </div>
        </div>
      </div>

      {/* Modal Profilo */}
      <ProfiloModal
        isOpen={showProfiloModal}
        onClose={() => setShowProfiloModal(false)}
        user={currentUser}
        onUpdate={handleProfiloUpdate}
      />

      {/* v11.0: Modal Cambio Password */}
      {showPasswordModal && (
        <PasswordChangeModal
          currentUser={currentUser}
          onClose={() => setShowPasswordModal(false)}
        />
      )}
    </aside>
  );
};

// Utility per generare menu predefinito
Sidebar.getDefaultMenu = (userRole) => {
  // v6.2.1: Permessi per ruolo (sincronizzati con UtentiPage)
  const PERMESSI_RUOLO = {
    admin: ['dashboard', 'upload', 'database', 'supervisione', 'tracciati', 'settings', 'logs'],
    superuser: ['dashboard', 'upload', 'database', 'supervisione', 'tracciati', 'settings'],
    supervisore: ['dashboard', 'upload', 'database', 'supervisione', 'tracciati', 'settings'],
    operatore: ['dashboard', 'upload', 'database', 'tracciati', 'settings'],  // settings: solo cambio password
    readonly: ['dashboard', 'database']
  };

  const allMenuItems = [
    { id: 'dashboard', label: 'Dashboard', icon: '📊' },
    { id: 'upload', label: 'Upload PDF', icon: '📁' },
    { id: 'database', label: 'Gestione Ordini', icon: '🗄️' },
    { id: 'supervisione', label: 'Supervisione', icon: '👁️' },
    { id: 'tracciati', label: 'Tracciati', icon: '📋' },
    { id: 'settings', label: 'Impostazioni', icon: '⚙️' },
    { id: 'logs', label: 'Log Sistema', icon: '📝' },
  ];

  // Filtra menu in base ai permessi del ruolo
  const allowedIds = PERMESSI_RUOLO[userRole] || PERMESSI_RUOLO.readonly;
  return allMenuItems.filter(item => allowedIds.includes(item.id));
};

export { Sidebar };
export default Sidebar;
