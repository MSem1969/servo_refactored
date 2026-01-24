// =============================================================================
// SERV.O v10.0 - AUTH CONTEXT
// =============================================================================
// Gestione centralizzata autenticazione utente con permessi dinamici da DB
// =============================================================================

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { authApi, permessiApi } from '../api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [permissions, setPermissions] = useState({}); // v10.0: Permessi da DB
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Carica permessi utente dal database
  const loadPermissions = useCallback(async () => {
    try {
      const perms = await permessiApi.getMyPermissions();
      setPermissions(perms);
    } catch (err) {
      console.error('Failed to load permissions:', err);
      setPermissions({});
    }
  }, []);

  // Verifica autenticazione all'avvio
  useEffect(() => {
    const checkAuth = async () => {
      if (authApi.isAuthenticated()) {
        try {
          const userData = await authApi.getMe();
          setUser(userData);
          // v10.0: Carica permessi dopo autenticazione
          await loadPermissions();
        } catch (err) {
          console.error('Auth check failed:', err);
          await authApi.logout();
        }
      }
      setLoading(false);
    };

    checkAuth();
  }, [loadPermissions]);

  // Login
  const login = useCallback(async (username, password) => {
    setError(null);
    try {
      const result = await authApi.login(username, password);
      setUser(result.user);
      // v10.0: Carica permessi dopo login
      await loadPermissions();
      return result.user;
    } catch (err) {
      const msg = err.response?.data?.detail || 'Credenziali non valide';
      setError(msg);
      throw err;
    }
  }, [loadPermissions]);

  // Logout
  const logout = useCallback(async () => {
    await authApi.logout();
    setUser(null);
    setPermissions({}); // v10.0: Reset permessi
  }, []);

  // v10.0: Verifica permesso visualizzazione per sezione
  const canView = useCallback((sezione) => {
    if (!user) return false;
    // Admin ha sempre accesso completo
    if (user.ruolo?.toLowerCase() === 'admin') return true;
    // Verifica permesso da database
    return permissions[sezione]?.can_view ?? false;
  }, [user, permissions]);

  // v10.0: Verifica permesso modifica per sezione
  const canEdit = useCallback((sezione) => {
    if (!user) return false;
    // Admin ha sempre accesso completo
    if (user.ruolo?.toLowerCase() === 'admin') return true;
    // Verifica permesso da database
    return permissions[sezione]?.can_edit ?? false;
  }, [user, permissions]);

  // Verifica permessi per ruolo (retrocompatibilità)
  const hasPermission = useCallback((permission) => {
    return canView(permission);
  }, [canView]);

  // Verifica se utente e admin
  const isAdmin = useCallback(() => {
    return user?.ruolo?.toLowerCase() === 'admin';
  }, [user]);

  // v10.0: Ricarica permessi (utile dopo modifica admin)
  const refreshPermissions = useCallback(async () => {
    await loadPermissions();
  }, [loadPermissions]);

  const value = {
    user,
    permissions, // v10.0: Esponi permessi
    loading,
    error,
    isAuthenticated: !!user,
    login,
    logout,
    hasPermission,
    canView,      // v10.0: Nuovo helper
    canEdit,      // v10.0: Nuovo helper
    isAdmin,
    refreshPermissions, // v10.0: Per refresh dopo modifica
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}

export default AuthContext;
