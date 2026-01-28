// =============================================================================
// HEADER COMPONENT
// =============================================================================
// Componente header modulare per barra superiore
// Gestisce titolo pagina, user actions
// v11.4: Rimosso sistema notifiche mockup (notifiche via ticket CRM)
// =============================================================================

import React, { useState } from 'react';
import { utentiApi } from '../api';

/**
 * Componente Header per barra superiore
 *
 * LOGICA IMPLEMENTATIVA:
 * - Titolo dinamico basato su pagina corrente
 * - Data formattata localizzata italiana
 * - User avatar e info rapide
 *
 * INTERRELAZIONI:
 * - Usato in: Layout principale
 * - Sostituisce: Header hardcoded in App.jsx
 *
 * @param {string} title - Titolo pagina corrente
 * @param {string} subtitle - Sottotitolo opzionale
 * @param {Object} currentUser - Dati utente corrente
 * @param {function} onLogout - Handler logout
 * @param {React.Node} actions - Azioni personalizzate header (opzionale)
 * @param {boolean} showDate - Mostra data corrente (default: true)
 */
const Header = ({
  title = 'Dashboard',
  subtitle,
  currentUser,
  onLogout,
  actions,
  showDate = true
}) => {

  const [showUserMenu, setShowUserMenu] = useState(false);
  const [showPasswordModal, setShowPasswordModal] = useState(false);

  // Formatta data corrente in italiano
  const getCurrentDate = () => {
    return new Date().toLocaleDateString('it-IT', {
      weekday: 'long',
      day: 'numeric',
      month: 'long',
      year: 'numeric',
    });
  };

  // Genera iniziali utente
  const getUserInitials = (user) => {
    if (!user) return 'U';
    const firstName = user.nome?.charAt(0) || '';
    const lastName = user.cognome?.charAt(0) || '';
    return (firstName + lastName) || user.username?.charAt(0) || 'U';
  };

  return (
    <>
      <header className="sticky top-0 bg-white border-b border-slate-200 z-40 backdrop-blur-sm bg-white/95">
        <div className="flex items-center justify-between px-6 py-3">
          {/* Left: Title Section */}
          <div className="flex-1">
            <div className="flex items-center gap-3">
              <h1 className="text-xl font-bold text-slate-800 tracking-tight">
                {title}
              </h1>
              {subtitle && (
                <>
                  <span className="text-slate-400">•</span>
                  <span className="text-sm text-slate-500">{subtitle}</span>
                </>
              )}
            </div>
            
            {showDate && (
              <p className="text-xs text-slate-500 mt-0.5">
                {getCurrentDate()}
              </p>
            )}
          </div>

          {/* Center: Custom Actions */}
          {actions && (
            <div className="flex items-center gap-2">
              {actions}
            </div>
          )}

          {/* Right: User Menu */}
          <div className="flex items-center gap-3">
            {/* User Info - Clickable for menu */}
            <div className="relative">
              <button
                onClick={() => setShowUserMenu(!showUserMenu)}
                className="flex items-center gap-3 pl-3 border-l border-slate-200 hover:bg-slate-50 rounded-lg py-1 px-2 transition-colors"
              >
                {/* User Avatar */}
                <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-blue-700 rounded-full flex items-center justify-center text-white text-xs font-bold shadow-md">
                  {getUserInitials(currentUser)}
                </div>

                {/* User Details */}
                <div className="text-right">
                  <p className="text-sm font-medium text-slate-700">
                    {currentUser?.username}
                  </p>
                  <p className="text-xs text-slate-500 capitalize">
                    {currentUser?.ruolo}
                  </p>
                </div>

                {/* Dropdown arrow */}
                <span className="text-slate-400 text-xs ml-1">
                  {showUserMenu ? '▲' : '▼'}
                </span>
              </button>

              {/* User Menu Dropdown */}
              {showUserMenu && (
                <UserMenuDropdown
                  currentUser={currentUser}
                  onClose={() => setShowUserMenu(false)}
                  onChangePassword={() => {
                    setShowUserMenu(false);
                    setShowPasswordModal(true);
                  }}
                  onLogout={() => {
                    setShowUserMenu(false);
                    onLogout?.();
                  }}
                />
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Overlay per chiudere user menu */}
      {showUserMenu && (
        <div
          className="fixed inset-0 z-30"
          onClick={() => setShowUserMenu(false)}
        />
      )}

      {/* Modal Cambio Password */}
      {showPasswordModal && (
        <PasswordChangeModal
          currentUser={currentUser}
          onClose={() => setShowPasswordModal(false)}
        />
      )}
    </>
  );
};

/**
 * Componente UserMenuDropdown
 * Menu dropdown per azioni utente (cambio password, logout)
 */
const UserMenuDropdown = ({ currentUser, onClose, onChangePassword, onLogout }) => {
  return (
    <div className="absolute top-12 right-0 w-56 bg-white rounded-xl shadow-2xl border border-slate-200 z-50 overflow-hidden">
      {/* Header con info utente */}
      <div className="p-3 border-b border-slate-100 bg-slate-50">
        <p className="font-semibold text-sm text-slate-800">
          {currentUser?.nome || ''} {currentUser?.cognome || ''}
        </p>
        <p className="text-xs text-slate-500">{currentUser?.email || currentUser?.username}</p>
      </div>

      {/* Menu Items */}
      <div className="py-1">
        <button
          onClick={onChangePassword}
          className="w-full px-4 py-2.5 text-left text-sm text-slate-700 hover:bg-slate-50 flex items-center gap-3 transition-colors"
        >
          <span>🔑</span>
          <span>Cambia Password</span>
        </button>

        <div className="border-t border-slate-100 my-1" />

        <button
          onClick={onLogout}
          className="w-full px-4 py-2.5 text-left text-sm text-red-600 hover:bg-red-50 flex items-center gap-3 transition-colors"
        >
          <span>🚪</span>
          <span>Esci</span>
        </button>
      </div>
    </div>
  );
};

/**
 * Componente PasswordChangeModal
 * Modal per cambio password accessibile da qualsiasi pagina
 */
const PasswordChangeModal = ({ currentUser, onClose }) => {
  const [formData, setFormData] = useState({
    vecchia_password: '',
    nuova_password: '',
    conferma_password: ''
  });
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  const validate = () => {
    const newErrors = {};

    if (!formData.vecchia_password) {
      newErrors.vecchia_password = 'Inserisci la password attuale';
    }
    if (!formData.nuova_password) {
      newErrors.nuova_password = 'Inserisci la nuova password';
    } else if (formData.nuova_password.length < 6) {
      newErrors.nuova_password = 'Minimo 6 caratteri';
    }
    if (formData.nuova_password !== formData.conferma_password) {
      newErrors.conferma_password = 'Le password non coincidono';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) return;

    setLoading(true);
    try {
      const userId = currentUser?.id_operatore || currentUser?.id;
      if (!userId) {
        throw new Error('ID utente non trovato. Riprova dopo aver fatto logout e login.');
      }

      await utentiApi.changePassword(userId, {
        vecchia_password: formData.vecchia_password,
        nuova_password: formData.nuova_password
      });

      setSuccess(true);
      setTimeout(() => {
        onClose();
      }, 2000);
    } catch (err) {
      const errorMsg = err.response?.data?.detail || err.message || 'Errore durante il cambio password';
      setErrors({ general: errorMsg });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-md mx-4">
        {/* Header */}
        <div className="p-4 border-b border-slate-200 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-slate-800">
            🔑 Cambia Password
          </h3>
          <button
            onClick={onClose}
            className="p-1 hover:bg-slate-100 rounded-lg text-slate-500"
          >
            ✕
          </button>
        </div>

        {/* Content */}
        {success ? (
          <div className="p-8 text-center">
            <div className="text-4xl mb-4">✅</div>
            <p className="text-lg font-medium text-emerald-600">
              Password cambiata con successo!
            </p>
            <p className="text-sm text-slate-500 mt-2">
              La finestra si chiuderà automaticamente...
            </p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="p-4 space-y-4">
            {/* Error generale */}
            {errors.general && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
                {errors.general}
              </div>
            )}

            {/* Password attuale */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Password attuale *
              </label>
              <input
                type="password"
                value={formData.vecchia_password}
                onChange={(e) => setFormData(f => ({ ...f, vecchia_password: e.target.value }))}
                className={`w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                  errors.vecchia_password ? 'border-red-500' : 'border-slate-300'
                }`}
                placeholder="Inserisci la password attuale"
              />
              {errors.vecchia_password && (
                <p className="text-xs text-red-500 mt-1">{errors.vecchia_password}</p>
              )}
            </div>

            {/* Nuova password */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Nuova password *
              </label>
              <input
                type="password"
                value={formData.nuova_password}
                onChange={(e) => setFormData(f => ({ ...f, nuova_password: e.target.value }))}
                className={`w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                  errors.nuova_password ? 'border-red-500' : 'border-slate-300'
                }`}
                placeholder="Minimo 6 caratteri"
              />
              {errors.nuova_password && (
                <p className="text-xs text-red-500 mt-1">{errors.nuova_password}</p>
              )}
            </div>

            {/* Conferma password */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Conferma nuova password *
              </label>
              <input
                type="password"
                value={formData.conferma_password}
                onChange={(e) => setFormData(f => ({ ...f, conferma_password: e.target.value }))}
                className={`w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                  errors.conferma_password ? 'border-red-500' : 'border-slate-300'
                }`}
                placeholder="Ripeti la nuova password"
              />
              {errors.conferma_password && (
                <p className="text-xs text-red-500 mt-1">{errors.conferma_password}</p>
              )}
            </div>

            {/* Actions */}
            <div className="flex gap-3 pt-2">
              <button
                type="button"
                onClick={onClose}
                className="flex-1 px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-sm font-medium transition-colors"
              >
                Annulla
              </button>
              <button
                type="submit"
                disabled={loading}
                className="flex-1 px-4 py-2 bg-blue-500 hover:bg-blue-600 disabled:bg-slate-300 text-white rounded-lg text-sm font-medium transition-colors"
              >
                {loading ? 'Salvataggio...' : 'Cambia Password'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};

export { Header, UserMenuDropdown, PasswordChangeModal };
export default Header;
