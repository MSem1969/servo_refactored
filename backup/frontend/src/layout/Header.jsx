// =============================================================================
// HEADER COMPONENT
// =============================================================================
// Componente header modulare per barra superiore
// Gestisce titolo pagina, notifiche, user actions
// =============================================================================

import React, { useState } from 'react';
import { Button } from '../common';

/**
 * Componente Header per barra superiore
 * 
 * LOGICA IMPLEMENTATIVA:
 * - Titolo dinamico basato su pagina corrente
 * - Data formattata localizzata italiana
 * - Sistema notifiche con dropdown
 * - User avatar e info rapide
 * 
 * INTERRELAZIONI:
 * - Usato in: Layout principale
 * - Dipende da: Button component
 * - Sostituisce: Header hardcoded in App.jsx
 * 
 * @param {string} title - Titolo pagina corrente
 * @param {string} subtitle - Sottotitolo opzionale
 * @param {Object} currentUser - Dati utente corrente
 * @param {Array} notifications - Array notifiche {id, type, message, timestamp}
 * @param {function} onNotificationClick - Handler click notifica
 * @param {React.Node} actions - Azioni personalizzate header (opzionale)
 * @param {boolean} showDate - Mostra data corrente (default: true)
 */
const Header = ({ 
  title = 'Dashboard',
  subtitle,
  currentUser,
  notifications = [],
  onNotificationClick,
  actions,
  showDate = true
}) => {
  
  const [showNotifications, setShowNotifications] = useState(false);
  
  // Formatta data corrente in italiano
  const getCurrentDate = () => {
    return new Date().toLocaleDateString('it-IT', {
      weekday: 'long',
      day: 'numeric',
      month: 'long',
      year: 'numeric',
    });
  };

  // Conta notifiche non lette
  const getUnreadCount = () => {
    return notifications.filter(n => !n.read).length;
  };

  // Genera iniziali utente
  const getUserInitials = (user) => {
    if (!user) return 'U';
    const firstName = user.nome?.charAt(0) || '';
    const lastName = user.cognome?.charAt(0) || '';
    return (firstName + lastName) || user.username?.charAt(0) || 'U';
  };

  // Handler click notifica
  const handleNotificationClick = (notification) => {
    onNotificationClick?.(notification);
    setShowNotifications(false);
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

          {/* Right: Notifications & User */}
          <div className="flex items-center gap-3">
            {/* Notifications */}
            <div className="relative">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowNotifications(!showNotifications)}
                className="relative"
              >
                🔔
                {getUnreadCount() > 0 && (
                  <span className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white text-xs rounded-full flex items-center justify-center font-bold">
                    {getUnreadCount() > 9 ? '9+' : getUnreadCount()}
                  </span>
                )}
              </Button>

              {/* Notifications Dropdown */}
              {showNotifications && (
                <NotificationDropdown
                  notifications={notifications}
                  onNotificationClick={handleNotificationClick}
                  onClose={() => setShowNotifications(false)}
                />
              )}
            </div>

            {/* User Info */}
            <div className="flex items-center gap-3 pl-3 border-l border-slate-200">
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
            </div>
          </div>
        </div>
      </header>

      {/* Overlay per chiudere notifiche */}
      {showNotifications && (
        <div 
          className="fixed inset-0 z-30" 
          onClick={() => setShowNotifications(false)}
        />
      )}
    </>
  );
};

/**
 * Componente NotificationDropdown
 * Dropdown per visualizzare notifiche
 */
const NotificationDropdown = ({ notifications, onNotificationClick, onClose }) => {
  
  // Icone per tipo notifica
  const getNotificationIcon = (type) => {
    const icons = {
      error: '❌',
      warning: '⚠️',
      info: 'ℹ️',
      success: '✅',
      upload: '📤',
      order: '📋',
      anomaly: '🚨',
    };
    return icons[type] || 'ℹ️';
  };

  // Colori per tipo notifica
  const getNotificationStyle = (type, read) => {
    const baseStyle = 'p-3 hover:bg-slate-50 cursor-pointer border-l-4 transition-colors';
    const opacity = read ? 'opacity-70' : '';
    
    const colors = {
      error: 'border-red-500 bg-red-50/50',
      warning: 'border-amber-500 bg-amber-50/50',
      info: 'border-blue-500 bg-blue-50/50',
      success: 'border-emerald-500 bg-emerald-50/50',
      upload: 'border-purple-500 bg-purple-50/50',
      order: 'border-indigo-500 bg-indigo-50/50',
      anomaly: 'border-orange-500 bg-orange-50/50',
    };
    
    return `${baseStyle} ${colors[type] || colors.info} ${opacity}`;
  };

  return (
    <div className="absolute top-12 right-0 w-80 bg-white rounded-xl shadow-2xl border border-slate-200 z-50 max-h-96 overflow-hidden">
      {/* Header */}
      <div className="p-3 border-b border-slate-100 flex justify-between items-center bg-slate-50">
        <span className="font-bold text-sm text-slate-800">Notifiche</span>
        <div className="flex items-center gap-2">
          {notifications.length > 0 && (
            <span className="text-xs text-slate-500">
              {notifications.filter(n => !n.read).length} non lette
            </span>
          )}
          <Button variant="ghost" size="xs" onClick={onClose}>
            ✕
          </Button>
        </div>
      </div>

      {/* Content */}
      <div className="max-h-80 overflow-y-auto">
        {notifications.length === 0 ? (
          <div className="p-6 text-center text-slate-500">
            <div className="text-2xl mb-2">🔕</div>
            <p className="text-sm">Nessuna notifica</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {notifications.map((notification) => (
              <div
                key={notification.id}
                className={getNotificationStyle(notification.type, notification.read)}
                onClick={() => onNotificationClick(notification)}
              >
                <div className="flex items-start gap-3">
                  {/* Icon */}
                  <span className="text-lg mt-0.5">
                    {getNotificationIcon(notification.type)}
                  </span>
                  
                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-800 mb-1">
                      {notification.title || 'Notifica'}
                    </p>
                    <p className="text-xs text-slate-600 leading-relaxed">
                      {notification.message}
                    </p>
                    {notification.timestamp && (
                      <p className="text-xs text-slate-400 mt-2">
                        {new Date(notification.timestamp).toLocaleString('it-IT')}
                      </p>
                    )}
                  </div>
                  
                  {/* Unread indicator */}
                  {!notification.read && (
                    <div className="w-2 h-2 bg-blue-500 rounded-full mt-2" />
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Footer Actions */}
      {notifications.length > 0 && (
        <div className="p-2 border-t border-slate-100 bg-slate-50">
          <Button
            variant="ghost"
            size="xs"
            className="w-full"
            onClick={() => {
              // Mark all as read logic here
              onClose();
            }}
          >
            Segna tutte come lette
          </Button>
        </div>
      )}
    </div>
  );
};

export { Header, NotificationDropdown };
export default Header;
