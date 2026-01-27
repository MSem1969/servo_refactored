import React, { useState, useEffect } from "react";

// 2. Import API
import { dashboardApi, authApi, utentiApi, permessiApi, getApiBaseUrl } from "./api";

// 3. Import componenti modulari
import { Button, StatusBadge, VendorBadge, Loading, ErrorBox } from "./common";

// 4. Import layout
import { Layout, SimpleLayout } from "./layout";

// 5. Import pagine (v7.0: da cartella pages/)
import UploadPage from "./pages/UploadPage";
import DatabasePage from "./pages/Database";
import SupervisionePage from "./pages/Supervisione";
import TracciatiPage from "./pages/TracciatiPage";
import SettingsPage from "./pages/Settings";
import OrdineDetailPage from "./pages/OrdineDetail";
import UtentiPage from "./pages/UtentiPage";
import CrmPage from "./pages/CrmPage";
import ExportPage from "./pages/ExportPage";
// BackupPage: spostato in tab Impostazioni (v9.0)

// 6. Import componenti produttività
import ProduttivitaDashboard from "./components/ProduttivitaDashboard";

// ============================================
// LOGIN PAGE COMPONENT
// ============================================
const LoginPage = ({ onLogin, initialResetToken }) => {
  // Mode: 'login' | 'forgot' | 'reset'
  const [mode, setMode] = useState(initialResetToken ? 'reset' : 'login');

  // Login state
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Forgot password state
  const [forgotEmail, setForgotEmail] = useState("");
  const [forgotSuccess, setForgotSuccess] = useState(false);

  // Reset password state
  const [resetToken] = useState(initialResetToken || "");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [resetSuccess, setResetSuccess] = useState(false);

  const handleLogin = async (e) => {
    e.preventDefault();
    if (!username.trim() || !password) {
      setError("Inserisci username e password");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const result = await authApi.login(username.trim(), password);
      onLogin(result.user);
    } catch (err) {
      const msg = err.response?.data?.detail || "Credenziali non valide";
      setError(msg);
      setPassword("");
    } finally {
      setLoading(false);
    }
  };

  const handleForgotPassword = async (e) => {
    e.preventDefault();
    if (!forgotEmail.trim()) {
      setError("Inserisci la tua email");
      return;
    }

    setLoading(true);
    setError("");

    try {
      await authApi.forgotPassword(forgotEmail.trim());
      setForgotSuccess(true);
    } catch (err) {
      // Per sicurezza, mostra sempre successo anche in caso di errore
      setForgotSuccess(true);
    } finally {
      setLoading(false);
    }
  };

  const handleResetPassword = async (e) => {
    e.preventDefault();
    if (!newPassword || newPassword.length < 6) {
      setError("La password deve avere almeno 6 caratteri");
      return;
    }
    if (newPassword !== confirmPassword) {
      setError("Le password non coincidono");
      return;
    }

    setLoading(true);
    setError("");

    try {
      await authApi.resetPassword(resetToken, newPassword);
      setResetSuccess(true);
      // Rimuovi token dall'URL
      window.history.replaceState({}, document.title, window.location.pathname);
    } catch (err) {
      const msg = err.response?.data?.detail || "Token non valido o scaduto";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  // Forgot Password Success
  if (mode === 'forgot' && forgotSuccess) {
    return (
      <SimpleLayout title="SERV.O" subtitle="Service Operations">
        <div className="bg-white rounded-xl shadow-lg p-8 border border-slate-200 text-center">
          <div className="text-4xl mb-4">📧</div>
          <h3 className="text-lg font-semibold text-slate-800 mb-2">
            Controlla la tua email
          </h3>
          <p className="text-slate-600 mb-6">
            Se l'indirizzo email esiste nel sistema, riceverai un link per reimpostare la password.
          </p>
          <button
            onClick={() => { setMode('login'); setForgotSuccess(false); setForgotEmail(''); }}
            className="text-blue-600 hover:text-blue-700 font-medium"
          >
            ← Torna al login
          </button>
        </div>
      </SimpleLayout>
    );
  }

  // Reset Password Success
  if (mode === 'reset' && resetSuccess) {
    return (
      <SimpleLayout title="SERV.O" subtitle="Service Operations">
        <div className="bg-white rounded-xl shadow-lg p-8 border border-slate-200 text-center">
          <div className="text-4xl mb-4">✅</div>
          <h3 className="text-lg font-semibold text-emerald-600 mb-2">
            Password reimpostata!
          </h3>
          <p className="text-slate-600 mb-6">
            La tua password è stata cambiata con successo. Puoi ora accedere con la nuova password.
          </p>
          <button
            onClick={() => { setMode('login'); setResetSuccess(false); }}
            className="px-6 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg font-medium"
          >
            Vai al login
          </button>
        </div>
      </SimpleLayout>
    );
  }

  // Forgot Password Form
  if (mode === 'forgot') {
    return (
      <SimpleLayout title="SERV.O" subtitle="Recupero Password">
        <div className="bg-white rounded-xl shadow-lg p-8 border border-slate-200">
          <div className="text-center mb-6">
            <div className="text-3xl mb-2">🔑</div>
            <p className="text-slate-600 text-sm">
              Inserisci l'email associata al tuo account per ricevere un link di recupero.
            </p>
          </div>

          <form onSubmit={handleForgotPassword} className="space-y-6">
            <input
              type="email"
              placeholder="Email"
              value={forgotEmail}
              onChange={(e) => setForgotEmail(e.target.value)}
              className={`w-full px-4 py-3 border rounded-lg text-base focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                error ? "border-red-400" : "border-slate-200"
              }`}
              disabled={loading}
              autoFocus
            />

            <Button
              type="submit"
              variant="primary"
              size="lg"
              loading={loading}
              className="w-full"
            >
              Invia link di recupero
            </Button>

            {error && <ErrorBox.Error message={error} dismissible={false} />}
          </form>

          <div className="text-center mt-6">
            <button
              onClick={() => { setMode('login'); setError(''); }}
              className="text-slate-500 hover:text-slate-700 text-sm"
            >
              ← Torna al login
            </button>
          </div>
        </div>
      </SimpleLayout>
    );
  }

  // Reset Password Form (with token)
  if (mode === 'reset') {
    return (
      <SimpleLayout title="SERV.O" subtitle="Nuova Password">
        <div className="bg-white rounded-xl shadow-lg p-8 border border-slate-200">
          <div className="text-center mb-6">
            <div className="text-3xl mb-2">🔐</div>
            <p className="text-slate-600 text-sm">
              Inserisci la tua nuova password.
            </p>
          </div>

          <form onSubmit={handleResetPassword} className="space-y-6">
            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                placeholder="Nuova password (min. 6 caratteri)"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className={`w-full px-4 py-3 pr-12 border rounded-lg text-base focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                  error ? "border-red-400" : "border-slate-200"
                }`}
                disabled={loading}
                autoFocus
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 focus:outline-none"
                tabIndex={-1}
              >
                {showPassword ? "🙈" : "👁️"}
              </button>
            </div>

            <input
              type="password"
              placeholder="Conferma nuova password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className={`w-full px-4 py-3 border rounded-lg text-base focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                error ? "border-red-400" : "border-slate-200"
              }`}
              disabled={loading}
            />

            <Button
              type="submit"
              variant="primary"
              size="lg"
              loading={loading}
              className="w-full"
            >
              Reimposta password
            </Button>

            {error && <ErrorBox.Error message={error} dismissible={false} />}
          </form>

          <div className="text-center mt-6">
            <button
              onClick={() => { setMode('login'); setError(''); window.history.replaceState({}, document.title, window.location.pathname); }}
              className="text-slate-500 hover:text-slate-700 text-sm"
            >
              ← Torna al login
            </button>
          </div>
        </div>
      </SimpleLayout>
    );
  }

  // Login Form (default)
  return (
    <SimpleLayout title="SERV.O" subtitle="Service Operations">
      <div className="bg-white rounded-xl shadow-lg p-8 border border-slate-200">
        <form onSubmit={handleLogin} className="space-y-6">
          <input
            type="text"
            placeholder="Nome Utente"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className={`w-full px-4 py-3 border rounded-lg text-base focus:outline-none focus:ring-2 focus:ring-blue-500 ${
              error ? "border-red-400" : "border-slate-200"
            }`}
            disabled={loading}
            autoFocus
          />

          <div className="relative">
            <input
              type={showPassword ? "text" : "password"}
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className={`w-full px-4 py-3 pr-12 border rounded-lg text-base focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                error ? "border-red-400" : "border-slate-200"
              }`}
              disabled={loading}
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 focus:outline-none"
              tabIndex={-1}
            >
              {showPassword ? (
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M3.707 2.293a1 1 0 00-1.414 1.414l14 14a1 1 0 001.414-1.414l-1.473-1.473A10.014 10.014 0 0019.542 10C18.268 5.943 14.478 3 10 3a9.958 9.958 0 00-4.512 1.074l-1.78-1.781zm4.261 4.26l1.514 1.515a2.003 2.003 0 012.45 2.45l1.514 1.514a4 4 0 00-5.478-5.478z" clipRule="evenodd" />
                  <path d="M12.454 16.697L9.75 13.992a4 4 0 01-3.742-3.741L2.335 6.578A9.98 9.98 0 00.458 10c1.274 4.057 5.065 7 9.542 7 .847 0 1.669-.105 2.454-.303z" />
                </svg>
              ) : (
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                  <path d="M10 12a2 2 0 100-4 2 2 0 000 4z" />
                  <path fillRule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z" clipRule="evenodd" />
                </svg>
              )}
            </button>
          </div>

          <Button
            type="submit"
            variant="primary"
            size="lg"
            loading={loading}
            className="w-full"
          >
            ACCEDI
          </Button>

          {error && <ErrorBox.Error message={error} dismissible={false} />}
        </form>

        {/* Link Password dimenticata */}
        <div className="text-center mt-6 pt-4 border-t border-slate-100">
          <button
            onClick={() => { setMode('forgot'); setError(''); }}
            className="text-blue-600 hover:text-blue-700 text-sm font-medium"
          >
            Password dimenticata?
          </button>
        </div>
      </div>
    </SimpleLayout>
  );
};

// ============================================
// DASHBOARD PAGE WITH TABS
// ============================================
const DashboardPage = ({ onNavigate }) => {
  const [activeTab, setActiveTab] = useState("statistiche");
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadStats = async () => {
      try {
        const response = await dashboardApi.getStats();
        setStats(response);
      } catch (err) {
        console.error("Error loading stats:", err);
      } finally {
        setLoading(false);
      }
    };

    loadStats();
  }, []);

  // Tab Statistiche content
  const StatisticheTab = () => {
    if (loading) {
      return <Loading text="Caricamento statistiche..." />;
    }

    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div className="bg-white p-6 rounded-xl border border-slate-200">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                📊
              </div>
              <div>
                <p className="text-sm text-slate-600">Ordini Totali</p>
                <p className="text-2xl font-bold text-slate-800">
                  {stats?.ordini_totali || 0}
                </p>
              </div>
            </div>
          </div>

          <div className="bg-white p-6 rounded-xl border border-slate-200">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-emerald-100 rounded-lg flex items-center justify-center">
                ✓
              </div>
              <div>
                <p className="text-sm text-slate-600">Validati</p>
                <p className="text-2xl font-bold text-slate-800">
                  {stats?.validati || 0}
                </p>
              </div>
            </div>
          </div>

          <div className="bg-white p-6 rounded-xl border border-slate-200">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-amber-100 rounded-lg flex items-center justify-center">
                !
              </div>
              <div>
                <p className="text-sm text-slate-600">Anomalie</p>
                <p className="text-2xl font-bold text-slate-800">
                  {stats?.anomalie || 0}
                </p>
              </div>
            </div>
          </div>

          <div className="bg-white p-6 rounded-xl border border-slate-200">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                📤
              </div>
              <div>
                <p className="text-sm text-slate-600">Esportati</p>
                <p className="text-2xl font-bold text-slate-800">
                  {stats?.esportati || 0}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <h3 className="text-lg font-bold text-slate-800 mb-4">Azioni Rapide</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Button
              variant="primary"
              className="h-20 flex-col gap-2"
              onClick={() => onNavigate("upload")}
            >
              <span className="text-xl">📁</span>
              Upload PDF
            </Button>
            <Button
              variant="secondary"
              className="h-20 flex-col gap-2"
              onClick={() => onNavigate("database")}
            >
              <span className="text-xl">🗄️</span>
              Database
            </Button>
            <Button
              variant="secondary"
              className="h-20 flex-col gap-2"
              onClick={() => onNavigate("tracciati")}
            >
              <span className="text-xl">📋</span>
              Tracciati
            </Button>
            <Button
              variant="secondary"
              className="h-20 flex-col gap-2"
              onClick={() => onNavigate("supervisione")}
            >
              <span className="text-xl">👁️</span>
              Supervisione
            </Button>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* Tab Navigation */}
      <div className="bg-white rounded-xl border border-slate-200 p-1 inline-flex">
        <button
          onClick={() => setActiveTab("statistiche")}
          className={`px-6 py-2.5 rounded-lg text-sm font-medium transition-all ${
            activeTab === "statistiche"
              ? "bg-blue-500 text-white shadow-sm"
              : "text-slate-600 hover:text-slate-800 hover:bg-slate-50"
          }`}
        >
          📊 Statistiche
        </button>
        <button
          onClick={() => setActiveTab("produttivita")}
          className={`px-6 py-2.5 rounded-lg text-sm font-medium transition-all ${
            activeTab === "produttivita"
              ? "bg-blue-500 text-white shadow-sm"
              : "text-slate-600 hover:text-slate-800 hover:bg-slate-50"
          }`}
        >
          👥 Produttività
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === "statistiche" ? (
        <StatisticheTab />
      ) : (
        <ProduttivitaDashboard />
      )}
    </div>
  );
};

// ============================================
// PLACEHOLDER PAGES
// ============================================
const PlaceholderPage = ({ title, icon }) => (
  <div className="space-y-6">
    <div className="bg-white rounded-xl border border-slate-200 p-8 text-center">
      <div className="text-4xl mb-4">{icon}</div>
      <h2 className="text-xl font-bold text-slate-800 mb-2">{title}</h2>
      <p className="text-slate-600">
        Questa sezione è in fase di migrazione ai nuovi componenti modulari.
      </p>
      <div className="mt-6">
        <Button variant="primary">🔧 Migra Componenti</Button>
      </div>
    </div>
  </div>
);

// ============================================
// MAIN APP COMPONENT v6.2
// ============================================
export default function App() {
  const [page, setPage] = useState("dashboard");
  const [pageParams, setPageParams] = useState({});
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [currentUser, setCurrentUser] = useState(null);
  const [userPermissions, setUserPermissions] = useState({}); // v10.0: Permessi da DB
  const [authLoading, setAuthLoading] = useState(true);
  const [globalLoading, setGlobalLoading] = useState(false);
  const [globalError, setGlobalError] = useState(null);

  // v10.0: Helper per verificare permesso visualizzazione
  const canViewSection = (sezione) => {
    // Admin ha sempre accesso completo
    if (currentUser?.ruolo?.toLowerCase() === 'admin') return true;
    // Verifica permesso da database
    return userPermissions[sezione]?.can_view ?? false;
  };

  const navigateTo = (pageName, params = {}) => {
    // v10.0: Verifica permessi prima di navigare
    // ordine-detail usa gli stessi permessi di database
    const sectionToCheck = pageName === 'ordine-detail' ? 'database' : pageName;
    if (!canViewSection(sectionToCheck)) {
      console.warn(`Access denied to section: ${pageName}`);
      return; // Non navigare se non autorizzato
    }
    setPage(pageName);
    setPageParams(params);
  };

  // v10.0: Carica permessi utente dal database
  // v10.1: Restituisce i permessi per uso immediato (landing page)
  const loadUserPermissions = async () => {
    try {
      const perms = await permessiApi.getMyPermissions();
      setUserPermissions(perms);
      return perms;
    } catch (err) {
      console.error('Failed to load permissions:', err);
      setUserPermissions({});
      return {};
    }
  };

  // v10.1: Determina landing page in base ai permessi
  const getLandingPage = (user, perms) => {
    // Admin ha sempre accesso a Dashboard
    if (user?.ruolo?.toLowerCase() === 'admin') return 'dashboard';
    // Se ha accesso (can_view) a Dashboard, vai a Dashboard
    if (perms.dashboard?.can_view) return 'dashboard';
    // Altrimenti vai a Upload PDF (default per operatore)
    return 'upload';
  };

  // v11.0: Sistema notifiche rimosso - non funzionante
  // TODO: Implementare sistema notifiche reale con backend API

  // Verifica autenticazione all'avvio
  useEffect(() => {
    const checkAuth = async () => {
      if (authApi.isAuthenticated()) {
        try {
          const user = await authApi.getMe();
          setCurrentUser(user);
          setIsAuthenticated(true);
          // v10.0: Carica permessi dopo autenticazione
          const perms = await loadUserPermissions();
          // v10.1: Landing page condizionale in base ai permessi
          setPage(getLandingPage(user, perms));
        } catch (err) {
          await authApi.logout();
        }
      }
      setAuthLoading(false);
    };

    checkAuth();
  }, []);

  // Handler login
  const handleLogin = async (user) => {
    setCurrentUser(user);
    setIsAuthenticated(true);
    // v10.0: Carica permessi dopo login
    const perms = await loadUserPermissions();
    // v10.1: Landing page condizionale in base ai permessi
    setPage(getLandingPage(user, perms));
  };

  // Handler logout
  const handleLogout = async () => {
    await authApi.logout();
    setCurrentUser(null);
    setUserPermissions({}); // v10.0: Reset permessi
    setIsAuthenticated(false);
    setPage("dashboard");
  };

  // Handler cambio pagina
  const handlePageChange = (newPage) => {
    setPage(newPage);
  };

  // Genera menu dinamico basato su permessi database (v10.0)
  const getMenu = () => {
    const allMenuItems = [
      { id: "dashboard", label: "Dashboard", icon: "📊" },
      { id: "upload", label: "Upload PDF", icon: "📁" },
      { id: "report", label: "Report", icon: "📈" },
      { id: "database", label: "Gestione Ordini", icon: "🗄️" },
      { id: "supervisione", label: "Supervisione", icon: "👁️" },
      { id: "tracciati", label: "Tracciati", icon: "📋" },
      { id: "crm", label: "Assistenza", icon: "🛠️" },
      { id: "settings", label: "Impostazioni", icon: "⚙️" },
    ];

    // v10.0: Filtra menu in base ai permessi dal database
    return allMenuItems.filter(item => canViewSection(item.id));
  };

  // Ottieni titolo pagina
  const getPageTitle = () => {
    const titles = {
      dashboard: "Dashboard",
      upload: "Upload PDF",
      database: "Gestione Ordini",
      "ordine-detail": "Dettaglio Ordine",
      supervisione: "Supervisione ML",
      export: "Report",
      tracciati: "Tracciati Export",
      crm: "Assistenza",
      settings: "Impostazioni",
    };

    return titles[page] || "Dashboard";
  };

  // Renderizza contenuto pagina
  const renderPage = () => {
    switch (page) {
      case "dashboard":
        return <DashboardPage onNavigate={navigateTo} />;
      // case "utenti":  // v6.2: Spostato in tab Impostazioni
      //   return <UtentiPage currentUser={currentUser} />;
      case "upload":
        return <UploadPage onNavigate={navigateTo} />;
      case "database":
        return (
          <DatabasePage
            currentUser={currentUser}
            onOpenOrdine={(id) => navigateTo("ordine-detail", { ordineId: id })}
          />
        );
      case "ordine-detail":
        return (
          <OrdineDetailPage
            ordineId={pageParams.ordineId}
            currentUser={currentUser}
            onBack={() => navigateTo("database")}
            onNavigateToSupervisione={(supervisioneId, ordineId) =>
              navigateTo("supervisione", {
                supervisioneId: supervisioneId,
                returnToOrdine: ordineId,
              })
            }
          />
        );
      // case "lookup":  // v6.2: Rimosso - lookup automatico integrato
      //   return <PlaceholderPage title="Lookup Farmacie" icon="🔍" />;
      case "supervisione":
        return (
          <SupervisionePage
            supervisioneId={pageParams.supervisioneId}
            returnToOrdine={pageParams.returnToOrdine}
            currentUser={currentUser}
            onReturnToOrdine={(idOrdine) =>
              navigateTo("ordine-detail", { ordineId: idOrdine })
            }
            onNavigateToOrdine={(idOrdine) =>
              navigateTo("ordine-detail", { ordineId: idOrdine })
            }
          />
        );
      case "tracciati":
        return <TracciatiPage />;
      case "report":
        return <ExportPage />;
      case "crm":
        return <CrmPage currentUser={currentUser} />;
      case "settings":
        return <SettingsPage currentUser={currentUser} />;
      default:
        return <DashboardPage />;
    }
  };

  // Loading iniziale
  if (authLoading) {
    return <Loading.Fullscreen text="Inizializzazione..." />;
  }

  // Login se non autenticato
  if (!isAuthenticated) {
    // Controlla se c'è un token di reset nell'URL
    const urlParams = new URLSearchParams(window.location.search);
    const resetToken = urlParams.get('reset_token');
    return <LoginPage onLogin={handleLogin} initialResetToken={resetToken} />;
  }

  // App principale con Layout modulare
  return (
    <Layout
      currentUser={currentUser}
      onLogout={handleLogout}
      menu={getMenu()}
      activePage={page}
      onPageChange={navigateTo}
      pageTitle={getPageTitle()}
      loading={globalLoading}
      error={globalError}
    >
      {renderPage()}
    </Layout>
  );
}
