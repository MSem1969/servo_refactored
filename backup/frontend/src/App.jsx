import React, { useState, useEffect } from "react";

// 2. Import API
import { dashboardApi, authApi, utentiApi, getApiBaseUrl } from "./api";

// 3. Import componenti modulari
import { Button, StatusBadge, VendorBadge, Loading, ErrorBox } from "./common";

// 4. Import layout
import { Layout, SimpleLayout } from "./layout";

// 5. Import pagine
import UploadPage from "./UploadPage";
import DatabasePage from "./DatabasePage";
import SupervisionePage from "./SupervisionePage";
import TracciatiPage from "./TracciatiPage";
import SettingsPage from "./SettingsPage";
import OrdineDetailPage from "./OrdineDetailPage";
import UtentiPage from "./UtentiPage";

// 6. Import componenti produttività
import ProduttivitaDashboard from "./components/ProduttivitaDashboard";

// ============================================
// LOGIN PAGE COMPONENT
// ============================================
const LoginPage = ({ onLogin }) => {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
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

  return (
    <SimpleLayout title="TO_EXTRACTOR" subtitle="Sistema Gestione Ordini v6.2">
      <div className="bg-white rounded-xl shadow-lg p-8 border border-slate-200">
        <form onSubmit={handleSubmit} className="space-y-6">
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

          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
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
            ACCEDI
          </Button>

          {error && <ErrorBox.Error message={error} dismissible={false} />}
        </form>
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
  const [authLoading, setAuthLoading] = useState(true);
  const [globalLoading, setGlobalLoading] = useState(false);
  const [globalError, setGlobalError] = useState(null);
  const navigateTo = (pageName, params = {}) => {
    setPage(pageName);
    setPageParams(params);
  };

  // Handler notifiche
  const handleNotificationClick = (notification) => {
    console.log("Notification clicked:", notification);

    // Logica per gestire diversi tipi di notifica
    switch (notification.type) {
      case "anomaly":
        navigateTo("supervisione");
        break;
      case "upload":
        navigateTo("upload");
        break;
      case "order":
        navigateTo("database");
        break;
      default:
        console.log("Notifica:", notification.message);
    }
  };

  // Mock notifications per demo
  const [notifications] = useState([
    {
      id: 1,
      type: "warning",
      title: "Anomalie Rilevate",
      message: "3 ordini richiedono supervisione",
      timestamp: new Date().toISOString(),
      read: false,
    },
    {
      id: 2,
      type: "success",
      title: "Upload Completato",
      message: "PDF ANGELINI processato con successo",
      timestamp: new Date(Date.now() - 3600000).toISOString(),
      read: true,
    },
  ]);

  // Verifica autenticazione all'avvio
  useEffect(() => {
    const checkAuth = async () => {
      if (authApi.isAuthenticated()) {
        try {
          const user = await authApi.getMe();
          setCurrentUser(user);
          setIsAuthenticated(true);
        } catch (err) {
          await authApi.logout();
        }
      }
      setAuthLoading(false);
    };

    checkAuth();
  }, []);

  // Handler login
  const handleLogin = (user) => {
    setCurrentUser(user);
    setIsAuthenticated(true);
    setPage("dashboard");
  };

  // Handler logout
  const handleLogout = async () => {
    await authApi.logout();
    setCurrentUser(null);
    setIsAuthenticated(false);
    setPage("dashboard");
  };

  // Handler cambio pagina
  const handlePageChange = (newPage) => {
    setPage(newPage);
  };

  // Genera menu dinamico basato su ruolo
  const getMenu = () => {
    // v6.2.1: Permessi menu per ruolo
    const PERMESSI_MENU = {
      admin: ['dashboard', 'upload', 'database', 'supervisione', 'tracciati', 'settings', 'logs'],
      supervisore: ['dashboard', 'upload', 'database', 'supervisione', 'tracciati', 'settings'],
      operatore: ['dashboard', 'upload', 'database', 'tracciati', 'settings'],
      readonly: ['dashboard', 'database']
    };

    const allMenuItems = [
      { id: "dashboard", label: "Dashboard", icon: "📊" },
      { id: "upload", label: "Upload PDF", icon: "📁" },
      { id: "database", label: "Gestione Ordini", icon: "🗄️" },
      { id: "supervisione", label: "Supervisione", icon: "👁️" },
      { id: "tracciati", label: "Tracciati", icon: "📋" },
      { id: "settings", label: "Impostazioni", icon: "⚙️" },
      { id: "logs", label: "Log Sistema", icon: "📝" },
    ];

    // Filtra menu in base al ruolo utente
    const userRole = currentUser?.ruolo?.toLowerCase() || 'readonly';
    const allowedIds = PERMESSI_MENU[userRole] || PERMESSI_MENU.readonly;
    return allMenuItems.filter(item => allowedIds.includes(item.id));
  };

  // Ottieni titolo pagina
  const getPageTitle = () => {
    const titles = {
      dashboard: "Dashboard",
      upload: "Upload PDF",
      database: "Gestione Ordini",
      "ordine-detail": "Dettaglio Ordine",
      // lookup: "Lookup Farmacie",  // v6.2: Rimosso
      supervisione: "Supervisione ML",
      tracciati: "Tracciati Export",
      settings: "Impostazioni",
      // utenti: "Gestione Utenti",  // v6.2: Spostato in tab Impostazioni
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
          />
        );
      case "tracciati":
        return <TracciatiPage />;
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
    return <LoginPage onLogin={handleLogin} />;
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
      notifications={notifications}
      onNotificationClick={handleNotificationClick}
      loading={globalLoading}
      error={globalError}
    >
      {renderPage()}
    </Layout>
  );
}
