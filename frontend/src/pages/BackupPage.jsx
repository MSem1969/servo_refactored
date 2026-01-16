// =============================================================================
// BACKUP PAGE - v9.0
// =============================================================================
// Gestione sistema backup modulare SERV.O
// Configurazione moduli, storage, monitoraggio, storico backup
// =============================================================================

import React, { useState, useEffect, useCallback } from "react";
import { backupApi } from "../api";
import { Button, StatusBadge, Loading, ErrorBox } from "../common";

/**
 * Componente BackupPage
 *
 * Gestisce il sistema di backup modulare:
 * - Dashboard con statistiche aggregate
 * - Configurazione moduli (WAL Archive, Full Backup, etc.)
 * - Gestione storage locations
 * - Storico backup eseguiti
 */
const BackupPage = ({ currentUser, embedded = false }) => {
  // State principale
  const [activeTab, setActiveTab] = useState("dashboard");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // State dati
  const [dashboard, setDashboard] = useState(null);
  const [modules, setModules] = useState([]);
  const [storage, setStorage] = useState([]);
  const [history, setHistory] = useState([]);

  // State operazioni
  const [executing, setExecuting] = useState(null);
  const [configuring, setConfiguring] = useState(null);

  // State modal configurazione
  const [configModal, setConfigModal] = useState({ open: false, module: null });

  // Carica dati iniziali
  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const [dashboardRes, modulesRes, storageRes, historyRes] = await Promise.all([
        backupApi.getDashboard(),
        backupApi.getModules(),
        backupApi.getStorageLocations(),
        backupApi.getHistory({ limit: 20 })
      ]);

      setDashboard(dashboardRes);
      setModules(modulesRes);
      setStorage(storageRes);
      setHistory(historyRes);
    } catch (err) {
      console.error("Errore caricamento dati backup:", err);
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Handler esecuzione backup
  const handleExecuteBackup = async (moduleName) => {
    if (executing) return;

    if (!window.confirm(`Eseguire backup modulo "${moduleName}"?`)) return;

    try {
      setExecuting(moduleName);
      const result = await backupApi.executeBackup(moduleName, "manual");

      if (result.success) {
        alert(`Backup completato!\nFile: ${result.file_path || 'N/A'}\nDimensione: ${result.size_mb?.toFixed(2) || (result.file_size_bytes ? (result.file_size_bytes / 1024 / 1024).toFixed(2) : 0)} MB`);
        loadData(); // Ricarica dati
      } else {
        throw new Error(result.error || result.message || "Backup fallito");
      }
    } catch (err) {
      const errorMsg = err.response?.data?.detail
        || err.response?.data?.message
        || (typeof err.message === 'object' ? JSON.stringify(err.message) : err.message)
        || "Errore sconosciuto";
      alert("Errore: " + errorMsg);
    } finally {
      setExecuting(null);
    }
  };

  // Handler test modulo
  const handleTestModule = async (moduleName) => {
    try {
      setExecuting(moduleName);
      const result = await backupApi.testModule(moduleName);

      if (result.success) {
        alert(`Test modulo "${moduleName}" completato con successo!`);
      } else {
        alert(`Test fallito: ${result.message}`);
      }
    } catch (err) {
      alert("Errore test: " + (err.response?.data?.detail || err.message));
    } finally {
      setExecuting(null);
    }
  };

  // Handler enable/disable modulo
  const handleToggleModule = async (moduleName, currentEnabled) => {
    const action = currentEnabled ? "disabilitare" : "abilitare";
    if (!window.confirm(`Vuoi ${action} il modulo "${moduleName}"?`)) return;

    try {
      setConfiguring(moduleName);

      if (currentEnabled) {
        await backupApi.disableModule(moduleName);
      } else {
        await backupApi.enableModule(moduleName);
      }

      loadData();
    } catch (err) {
      alert("Errore: " + (err.response?.data?.detail || err.message));
    } finally {
      setConfiguring(null);
    }
  };

  // Handler cleanup modulo
  const handleCleanup = async (moduleName) => {
    if (!window.confirm(`Eseguire cleanup backup obsoleti per "${moduleName}"?`)) return;

    try {
      setExecuting(moduleName);
      const result = await backupApi.cleanupModule(moduleName);
      alert(`Cleanup completato!\nFile eliminati: ${result.deleted_count || 0}\nSpazio liberato: ${result.freed_mb?.toFixed(2) || 0} MB`);
      loadData();
    } catch (err) {
      alert("Errore: " + (err.response?.data?.detail || err.message));
    } finally {
      setExecuting(null);
    }
  };

  // Handler apri configurazione modulo
  const handleOpenConfig = (module) => {
    setConfigModal({ open: true, module });
  };

  // Handler salva configurazione modulo
  const handleSaveConfig = async (moduleName, config) => {
    try {
      setConfiguring(moduleName);
      // Note: backupApi.configureModule already wraps in { config: ... }
      const result = await backupApi.configureModule(moduleName, config);

      if (result.success) {
        // Mostra eventuali istruzioni manuali
        if (result.manual_steps && result.manual_steps.length > 0) {
          alert(`Configurazione salvata!\n\nPassaggi manuali richiesti:\n${result.manual_steps.map((s, i) => `${i+1}. ${s}`).join('\n')}`);
        } else {
          alert('Configurazione salvata con successo!');
        }
        setConfigModal({ open: false, module: null });
        loadData();
      } else {
        throw new Error(result.message || 'Configurazione fallita');
      }
    } catch (err) {
      let errorMsg = "Errore sconosciuto";
      if (err.response?.data?.detail) {
        errorMsg = typeof err.response.data.detail === 'object'
          ? JSON.stringify(err.response.data.detail)
          : err.response.data.detail;
      } else if (err.response?.data?.message) {
        errorMsg = err.response.data.message;
      } else if (err.message) {
        errorMsg = typeof err.message === 'object' ? JSON.stringify(err.message) : err.message;
      }
      alert("Errore: " + errorMsg);
    } finally {
      setConfiguring(null);
    }
  };

  // Verifica ruolo admin
  const isAdmin = currentUser?.ruolo === 'admin';

  // Tabs disponibili
  const tabs = [
    { id: "dashboard", label: "Dashboard", icon: "📊" },
    { id: "modules", label: "Moduli", icon: "🧩" },
    { id: "storage", label: "Storage", icon: "💾" },
    { id: "history", label: "Storico", icon: "📜" },
  ];

  if (loading) {
    return (
      <div className="space-y-6">
        <Loading text="Caricamento sistema backup..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <ErrorBox.Error message={error} />
        <Button variant="primary" onClick={loadData}>
          Riprova
        </Button>
      </div>
    );
  }

  return (
    <div className={embedded ? "" : "space-y-6"}>
      {/* Header - nascosto in modalita' embedded */}
      {!embedded && (
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-slate-800">Sistema Backup</h1>
            <p className="text-sm text-slate-600">
              Gestione backup modulare SERV.O v9.0
            </p>
          </div>
          <Button variant="secondary" onClick={loadData}>
            Aggiorna
          </Button>
        </div>
      )}

      {/* Main Content */}
      <div className={embedded ? "" : "bg-white rounded-xl border border-slate-200"}>
        {/* Tabs */}
        <div className="border-b border-slate-200">
          <div className="flex">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-4 py-3 text-sm font-medium transition-colors flex items-center gap-2 ${
                  activeTab === tab.id
                    ? "text-blue-600 border-b-2 border-blue-600 bg-blue-50"
                    : "text-slate-500 hover:bg-slate-50"
                }`}
              >
                <span>{tab.icon}</span>
                <span>{tab.label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Tab Dashboard */}
        {activeTab === "dashboard" && (
          <DashboardTab dashboard={dashboard} modules={modules} />
        )}

        {/* Tab Moduli */}
        {activeTab === "modules" && (
          <ModulesTab
            modules={modules}
            isAdmin={isAdmin}
            executing={executing}
            configuring={configuring}
            onExecute={handleExecuteBackup}
            onTest={handleTestModule}
            onToggle={handleToggleModule}
            onCleanup={handleCleanup}
            onConfigure={handleOpenConfig}
          />
        )}

        {/* Modal Configurazione Modulo */}
        {configModal.open && configModal.module && (
          <ConfigureModuleModal
            module={configModal.module}
            onSave={(config) => handleSaveConfig(configModal.module.name, config)}
            onClose={() => setConfigModal({ open: false, module: null })}
            saving={configuring === configModal.module.name}
          />
        )}

        {/* Tab Storage */}
        {activeTab === "storage" && (
          <StorageTab storage={storage} isAdmin={isAdmin} onReload={loadData} />
        )}

        {/* Tab Storico */}
        {activeTab === "history" && (
          <HistoryTab history={history} />
        )}
      </div>
    </div>
  );
};

// =============================================================================
// SUB-COMPONENTS
// =============================================================================

/**
 * Tab Dashboard - Statistiche aggregate
 */
const DashboardTab = ({ dashboard, modules }) => {
  const enabledModules = modules?.filter(m => m.enabled)?.length || 0;
  const totalModules = modules?.length || 0;

  return (
    <div className="p-6 space-y-6">
      {/* Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard
          icon="🧩"
          label="Moduli Attivi"
          value={`${enabledModules}/${totalModules}`}
          color="blue"
        />
        <StatCard
          icon="💾"
          label="Backup Oggi"
          value={dashboard?.backups_today || 0}
          color="green"
        />
        <StatCard
          icon="📦"
          label="Spazio Totale"
          value={`${dashboard?.total_size_gb?.toFixed(2) || 0} GB`}
          color="purple"
        />
        <StatCard
          icon="✓"
          label="Ultimo Backup OK"
          value={dashboard?.last_success ? new Date(dashboard.last_success).toLocaleDateString('it-IT') : 'Mai'}
          color="emerald"
        />
      </div>

      {/* Status Moduli */}
      <div>
        <h3 className="font-medium text-slate-800 mb-4">Stato Moduli</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {modules?.map((module) => (
            <ModuleStatusCard key={module.name} module={module} />
          ))}
        </div>
      </div>

      {/* Ultimi Backup */}
      {dashboard?.recent_backups?.length > 0 && (
        <div>
          <h3 className="font-medium text-slate-800 mb-4">Ultimi Backup</h3>
          <div className="space-y-2">
            {dashboard.recent_backups.slice(0, 5).map((backup, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between p-3 bg-slate-50 rounded-lg"
              >
                <div className="flex items-center gap-3">
                  <StatusBadge
                    status={backup.status === 'success' ? 'completed' : 'error'}
                    label={backup.status}
                    size="xs"
                  />
                  <span className="text-sm font-medium text-slate-700">
                    {backup.module_name}
                  </span>
                </div>
                <div className="text-xs text-slate-500">
                  {new Date(backup.created_at).toLocaleString('it-IT')}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

/**
 * Tab Moduli - Configurazione e gestione
 */
const ModulesTab = ({
  modules,
  isAdmin,
  executing,
  configuring,
  onExecute,
  onTest,
  onToggle,
  onCleanup,
  onConfigure,
}) => {
  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-medium text-slate-800">Moduli Backup Disponibili</h3>
        {!isAdmin && (
          <span className="text-xs text-amber-600 bg-amber-50 px-2 py-1 rounded">
            Solo admin puo' modificare
          </span>
        )}
      </div>

      <div className="space-y-4">
        {modules?.map((module) => (
          <ModuleCard
            key={module.name}
            module={module}
            isAdmin={isAdmin}
            isExecuting={executing === module.name}
            isConfiguring={configuring === module.name}
            onExecute={() => onExecute(module.name)}
            onTest={() => onTest(module.name)}
            onToggle={() => onToggle(module.name, module.enabled)}
            onCleanup={() => onCleanup(module.name)}
            onConfigure={() => onConfigure(module)}
          />
        ))}
      </div>

      {/* Legenda Tier */}
      <div className="mt-6 p-4 bg-slate-50 rounded-lg">
        <h4 className="text-sm font-medium text-slate-700 mb-2">Priorita Moduli</h4>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-2 text-xs text-slate-600">
          <div><span className="font-mono bg-blue-100 px-1 rounded">TIER 1</span> WAL Archive - PITR base</div>
          <div><span className="font-mono bg-green-100 px-1 rounded">TIER 2</span> Full Backup - pg_dump</div>
          <div><span className="font-mono bg-purple-100 px-1 rounded">TIER 3</span> Incrementale</div>
          <div><span className="font-mono bg-amber-100 px-1 rounded">TIER 4</span> Offsite Sync</div>
          <div><span className="font-mono bg-cyan-100 px-1 rounded">TIER 5</span> Cloud Backup</div>
          <div><span className="font-mono bg-red-100 px-1 rounded">TIER 6</span> Replica Standby</div>
        </div>
      </div>
    </div>
  );
};

/**
 * Tab Storage - Gestione storage locations
 */
const StorageTab = ({ storage, isAdmin, onReload }) => {
  const [showAddForm, setShowAddForm] = useState(false);
  const [newStorage, setNewStorage] = useState({
    name: '',
    storage_type: 'local',
    path: '',
    capacity_gb: null
  });
  const [adding, setAdding] = useState(false);

  const handleAddStorage = async () => {
    if (!newStorage.name || !newStorage.path) {
      alert("Compila nome e percorso");
      return;
    }

    try {
      setAdding(true);
      await backupApi.addStorageLocation(newStorage);
      setShowAddForm(false);
      setNewStorage({ name: '', storage_type: 'local', path: '', capacity_gb: null });
      onReload();
    } catch (err) {
      alert("Errore: " + (err.response?.data?.detail || err.message));
    } finally {
      setAdding(false);
    }
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-medium text-slate-800">Storage Locations</h3>
        {isAdmin && (
          <Button
            variant="primary"
            size="sm"
            onClick={() => setShowAddForm(!showAddForm)}
          >
            + Aggiungi Storage
          </Button>
        )}
      </div>

      {/* Form Aggiunta */}
      {showAddForm && (
        <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg space-y-3">
          <h4 className="font-medium text-blue-800">Nuovo Storage Location</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-slate-600 mb-1">Nome</label>
              <input
                type="text"
                value={newStorage.name}
                onChange={(e) => setNewStorage({ ...newStorage, name: e.target.value })}
                className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm"
                placeholder="backup-nas-01"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-600 mb-1">Tipo</label>
              <select
                value={newStorage.storage_type}
                onChange={(e) => setNewStorage({ ...newStorage, storage_type: e.target.value })}
                className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm"
              >
                <option value="local">Local Disk</option>
                <option value="nas">NAS</option>
                <option value="s3">AWS S3</option>
                <option value="gcs">Google Cloud Storage</option>
                <option value="azure">Azure Blob</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-slate-600 mb-1">Percorso/Endpoint</label>
              <input
                type="text"
                value={newStorage.path}
                onChange={(e) => setNewStorage({ ...newStorage, path: e.target.value })}
                className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm"
                placeholder="/mnt/backup oppure s3://bucket-name"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-600 mb-1">Capacita (GB)</label>
              <input
                type="number"
                value={newStorage.capacity_gb || ''}
                onChange={(e) => setNewStorage({ ...newStorage, capacity_gb: parseInt(e.target.value) || null })}
                className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm"
                placeholder="500"
              />
            </div>
          </div>
          <div className="flex gap-2">
            <Button
              variant="primary"
              size="sm"
              onClick={handleAddStorage}
              loading={adding}
            >
              Salva
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setShowAddForm(false)}
            >
              Annulla
            </Button>
          </div>
        </div>
      )}

      {/* Lista Storage */}
      <div className="space-y-3">
        {storage?.length === 0 ? (
          <div className="text-center py-8 text-slate-500">
            Nessuno storage configurato
          </div>
        ) : (
          storage?.map((loc) => (
            <StorageCard key={loc.id || loc.name} storage={loc} />
          ))
        )}
      </div>
    </div>
  );
};

/**
 * Tab Storico - Lista backup eseguiti
 */
const HistoryTab = ({ history }) => {
  return (
    <div className="p-6">
      <h3 className="font-medium text-slate-800 mb-4">Storico Backup</h3>

      {history?.length === 0 ? (
        <div className="text-center py-8 text-slate-500">
          Nessun backup eseguito
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200">
                <th className="text-left py-2 px-3 font-medium text-slate-600">Data</th>
                <th className="text-left py-2 px-3 font-medium text-slate-600">Modulo</th>
                <th className="text-left py-2 px-3 font-medium text-slate-600">Stato</th>
                <th className="text-left py-2 px-3 font-medium text-slate-600">Dimensione</th>
                <th className="text-left py-2 px-3 font-medium text-slate-600">Durata</th>
                <th className="text-left py-2 px-3 font-medium text-slate-600">Trigger</th>
              </tr>
            </thead>
            <tbody>
              {history.map((entry, idx) => (
                <tr key={idx} className="border-b border-slate-100 hover:bg-slate-50">
                  <td className="py-2 px-3 font-mono text-xs">
                    {new Date(entry.started_at || entry.created_at).toLocaleString('it-IT')}
                  </td>
                  <td className="py-2 px-3 font-medium">{entry.module_name || entry.module_title}</td>
                  <td className="py-2 px-3">
                    <StatusBadge
                      status={entry.status === 'success' ? 'completed' : entry.status === 'running' ? 'pending' : 'error'}
                      label={entry.status}
                      size="xs"
                    />
                  </td>
                  <td className="py-2 px-3 font-mono text-xs">
                    {entry.file_size_bytes ? `${(entry.file_size_bytes / (1024*1024)).toFixed(2)} MB` : '-'}
                  </td>
                  <td className="py-2 px-3 font-mono text-xs">
                    {entry.duration_seconds ? `${entry.duration_seconds}s` : '-'}
                  </td>
                  <td className="py-2 px-3 text-xs text-slate-500">
                    {entry.triggered_by || 'manual'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

// =============================================================================
// HELPER COMPONENTS
// =============================================================================

/**
 * Card statistica semplice
 */
const StatCard = ({ icon, label, value, color = 'blue' }) => {
  const colorClasses = {
    blue: 'bg-blue-100 text-blue-600',
    green: 'bg-green-100 text-green-600',
    purple: 'bg-purple-100 text-purple-600',
    emerald: 'bg-emerald-100 text-emerald-600',
    amber: 'bg-amber-100 text-amber-600',
    red: 'bg-red-100 text-red-600',
  };

  return (
    <div className="bg-white p-4 rounded-xl border border-slate-200">
      <div className="flex items-center gap-3">
        <div className={`w-10 h-10 ${colorClasses[color]?.split(' ')[0]} rounded-lg flex items-center justify-center`}>
          <span className={colorClasses[color]?.split(' ')[1]}>{icon}</span>
        </div>
        <div>
          <p className="text-xs text-slate-600">{label}</p>
          <p className="text-xl font-bold text-slate-800">{value}</p>
        </div>
      </div>
    </div>
  );
};

/**
 * Card stato modulo compatto
 */
const ModuleStatusCard = ({ module }) => {
  const statusColor = module.enabled
    ? module.last_status === 'success' ? 'bg-emerald-50 border-emerald-200' : 'bg-amber-50 border-amber-200'
    : 'bg-slate-50 border-slate-200';

  return (
    <div className={`p-3 rounded-lg border ${statusColor}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-lg">{module.enabled ? (module.last_status === 'success' ? '✓' : '⚠') : '○'}</span>
          <span className="text-sm font-medium text-slate-700">{module.title || module.name}</span>
        </div>
        <span className={`text-xs px-1.5 py-0.5 rounded ${
          module.enabled ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-500'
        }`}>
          {module.enabled ? 'ON' : 'OFF'}
        </span>
      </div>
    </div>
  );
};

/**
 * Card modulo dettagliata
 */
const ModuleCard = ({
  module,
  isAdmin,
  isExecuting,
  isConfiguring,
  onExecute,
  onTest,
  onToggle,
  onCleanup,
  onConfigure,
}) => {
  const tierColors = {
    1: 'bg-blue-100 text-blue-700',
    2: 'bg-green-100 text-green-700',
    3: 'bg-purple-100 text-purple-700',
    4: 'bg-amber-100 text-amber-700',
    5: 'bg-cyan-100 text-cyan-700',
    6: 'bg-red-100 text-red-700',
  };

  const isConfigured = module.configured;
  const hasConfig = module.config && Object.keys(module.config).length > 0;

  return (
    <div className={`p-4 border rounded-lg ${module.enabled ? 'bg-white border-slate-200' : 'bg-slate-50 border-slate-200'}`}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className={`text-xs px-1.5 py-0.5 rounded font-mono ${tierColors[module.tier] || 'bg-slate-100'}`}>
              TIER {module.tier}
            </span>
            <h4 className="font-medium text-slate-800">{module.title || module.name}</h4>
            {module.enabled ? (
              <StatusBadge
                status={module.last_status === 'success' ? 'completed' : module.last_status === 'running' ? 'pending' : 'error'}
                label={module.last_status || 'pending'}
                size="xs"
              />
            ) : (
              <span className={`text-xs px-1.5 py-0.5 rounded ${isConfigured ? 'bg-blue-100 text-blue-700' : 'bg-slate-100 text-slate-500'}`}>
                {isConfigured ? 'Configurato' : 'Non configurato'}
              </span>
            )}
          </div>
          <p className="text-sm text-slate-600 mb-2">{module.description}</p>

          {/* Config info */}
          {hasConfig && (
            <div className="text-xs text-slate-500 flex flex-wrap gap-3">
              {(module.config.archive_dir || module.config.backup_dir) && (
                <span>Path: <code className="bg-slate-100 px-1 rounded">{module.config.archive_dir || module.config.backup_dir}</code></span>
              )}
              {module.config.retention_hours && (
                <span>Retention: {module.config.retention_hours}h</span>
              )}
              {module.config.retention_days && (
                <span>Retention: {module.config.retention_days}d</span>
              )}
              {module.config.format && (
                <span>Format: {module.config.format}</span>
              )}
              {module.config.compression !== undefined && (
                <span>Compressione: {module.config.compression ? 'Si' : 'No'}</span>
              )}
            </div>
          )}
        </div>

        {/* Azioni */}
        {isAdmin && (
          <div className="flex items-center gap-2 ml-4 flex-wrap justify-end">
            {/* Configura - sempre visibile */}
            <Button
              variant="secondary"
              size="sm"
              onClick={onConfigure}
              disabled={isExecuting || isConfiguring}
            >
              Configura
            </Button>

            {/* Test - solo se disponibile (tier 1-2) */}
            {module.available && (
              <Button
                variant="secondary"
                size="sm"
                onClick={onTest}
                disabled={isExecuting || isConfiguring || !isConfigured}
              >
                Test
              </Button>
            )}

            {/* Azioni per moduli abilitati */}
            {module.enabled && (
              <>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={onExecute}
                  loading={isExecuting}
                  disabled={isConfiguring}
                >
                  Esegui
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={onCleanup}
                  disabled={isExecuting || isConfiguring}
                >
                  Cleanup
                </Button>
              </>
            )}

            {/* Enable/Disable */}
            <Button
              variant={module.enabled ? 'danger' : 'primary'}
              size="sm"
              onClick={onToggle}
              loading={isConfiguring}
              disabled={isExecuting || (!isConfigured && !module.enabled)}
              title={!isConfigured && !module.enabled ? 'Configura prima il modulo' : ''}
            >
              {module.enabled ? 'Disabilita' : 'Abilita'}
            </Button>
          </div>
        )}
      </div>
    </div>
  );
};

/**
 * Card storage location
 */
const StorageCard = ({ storage }) => {
  const typeIcons = {
    local: '💾',
    nas: '🗄️',
    s3: '☁️',
    gcs: '☁️',
    azure: '☁️',
  };

  // Backend returns Italian field names: nome, tipo, stato
  const storageType = storage.tipo || storage.storage_type || 'local';
  const storageName = storage.nome || storage.name;
  const storageStatus = storage.stato || storage.status || 'unknown';

  const usagePercent = storage.capacity_gb && storage.used_gb
    ? Math.round((storage.used_gb / storage.capacity_gb) * 100)
    : null;

  return (
    <div className="p-4 bg-white border border-slate-200 rounded-lg">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-2xl">{typeIcons[storageType] || '💾'}</span>
          <div>
            <h4 className="font-medium text-slate-800">{storageName}</h4>
            <p className="text-xs text-slate-500">{storage.path}</p>
          </div>
        </div>
        <div className="text-right">
          <StatusBadge
            status={storageStatus === 'active' ? 'completed' : storageStatus === 'error' ? 'error' : 'pending'}
            label={storageStatus}
            size="xs"
          />
          {usagePercent !== null && (
            <p className="text-xs text-slate-500 mt-1">
              {usagePercent}% utilizzato
            </p>
          )}
        </div>
      </div>

      {/* Progress bar utilizzo */}
      {usagePercent !== null && (
        <div className="mt-3">
          <div className="w-full h-1.5 bg-slate-100 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full ${
                usagePercent > 90 ? 'bg-red-500' : usagePercent > 70 ? 'bg-amber-500' : 'bg-emerald-500'
              }`}
              style={{ width: `${Math.min(usagePercent, 100)}%` }}
            />
          </div>
          <p className="text-xs text-slate-500 mt-1">
            {storage.used_gb?.toFixed(1) || 0} GB / {storage.capacity_gb} GB
          </p>
        </div>
      )}
    </div>
  );
};

/**
 * Modal configurazione modulo
 */
const ConfigureModuleModal = ({ module, onSave, onClose, saving }) => {
  // Configurazione iniziale basata sul modulo
  const getDefaultConfig = () => {
    const existing = module.config || {};

    switch (module.name) {
      case 'wal_archive':
        return {
          archive_dir: existing.archive_dir || '/home/jobseminara/extractor_v2/backend/backups/wal',
          compression: existing.compression !== undefined ? existing.compression : true,
          retention_hours: existing.retention_hours || 168, // 7 giorni
        };
      case 'full_backup':
        return {
          backup_dir: existing.backup_dir || '/home/jobseminara/extractor_v2/backend/backups/full',
          format: existing.format || 'custom',
          compression: existing.compression !== undefined ? existing.compression : true,
          retention_days: existing.retention_days || 7,
        };
      case 'incremental':
        return {
          backup_path: existing.backup_path || '/var/backups/postgresql/incremental',
          base_backup_interval_hours: existing.base_backup_interval_hours || 24,
        };
      default:
        return existing;
    }
  };

  const [config, setConfig] = useState(getDefaultConfig);

  const handleSubmit = (e) => {
    e.preventDefault();
    onSave(config);
  };

  // Render form fields based on module type
  const renderFields = () => {
    switch (module.name) {
      case 'wal_archive':
        return (
          <>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Directory Archivio WAL
              </label>
              <input
                type="text"
                value={config.archive_dir}
                onChange={(e) => setConfig({ ...config, archive_dir: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="/home/jobseminara/extractor_v2/backend/backups/wal"
              />
              <p className="text-xs text-slate-500 mt-1">
                Directory dove salvare i WAL segments. Deve essere accessibile da PostgreSQL.
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Retention (ore)
              </label>
              <input
                type="number"
                value={config.retention_hours}
                onChange={(e) => setConfig({ ...config, retention_hours: parseInt(e.target.value) || 168 })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                min="1"
                max="720"
              />
              <p className="text-xs text-slate-500 mt-1">
                Per quanto tempo mantenere i WAL (default: 168h = 7 giorni)
              </p>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="compression"
                checked={config.compression}
                onChange={(e) => setConfig({ ...config, compression: e.target.checked })}
                className="w-4 h-4 text-blue-600 rounded"
              />
              <label htmlFor="compression" className="text-sm text-slate-700">
                Comprimi WAL con gzip
              </label>
            </div>
          </>
        );

      case 'full_backup':
        return (
          <>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Directory Backup
              </label>
              <input
                type="text"
                value={config.backup_dir}
                onChange={(e) => setConfig({ ...config, backup_dir: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="/home/jobseminara/extractor_v2/backend/backups/full"
              />
              <p className="text-xs text-slate-500 mt-1">
                Directory dove salvare i backup pg_dump.
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Formato
              </label>
              <select
                value={config.format}
                onChange={(e) => setConfig({ ...config, format: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="custom">Custom (-Fc) - Compresso, restore flessibile</option>
                <option value="plain">Plain SQL (-Fp) - Leggibile, piu' grande</option>
                <option value="directory">Directory (-Fd) - Parallelo, piu' veloce</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Retention (giorni)
              </label>
              <input
                type="number"
                value={config.retention_days}
                onChange={(e) => setConfig({ ...config, retention_days: parseInt(e.target.value) || 7 })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                min="1"
                max="365"
              />
              <p className="text-xs text-slate-500 mt-1">
                Per quanti giorni mantenere i backup (default: 7)
              </p>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="compression_full"
                checked={config.compression}
                onChange={(e) => setConfig({ ...config, compression: e.target.checked })}
                className="w-4 h-4 text-blue-600 rounded"
              />
              <label htmlFor="compression_full" className="text-sm text-slate-700">
                Comprimi backup con gzip
              </label>
            </div>
          </>
        );

      default:
        return (
          <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg">
            <p className="text-sm text-amber-800">
              Configurazione per questo modulo non ancora disponibile.
              Modulo: <strong>{module.name}</strong> (Tier {module.tier})
            </p>
          </div>
        );
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-slate-200">
          <div>
            <h3 className="font-bold text-slate-800">Configura {module.title || module.name}</h3>
            <p className="text-xs text-slate-500">TIER {module.tier}</p>
          </div>
          <button
            onClick={onClose}
            className="p-1 hover:bg-slate-100 rounded-lg transition-colors"
          >
            <svg className="w-5 h-5 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit}>
          <div className="p-4 space-y-4">
            {renderFields()}
          </div>

          {/* Note per WAL Archive */}
          {module.name === 'wal_archive' && (
            <div className="mx-4 mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
              <p className="text-xs text-blue-800 font-medium mb-1">Nota:</p>
              <p className="text-xs text-blue-700">
                Dopo la configurazione, dovrai modificare postgresql.conf per abilitare l'archivio WAL.
                Le istruzioni verranno mostrate dopo il salvataggio.
              </p>
            </div>
          )}

          {/* Footer */}
          <div className="flex items-center justify-end gap-3 p-4 border-t border-slate-200 bg-slate-50 rounded-b-xl">
            <Button
              type="button"
              variant="secondary"
              onClick={onClose}
              disabled={saving}
            >
              Annulla
            </Button>
            <Button
              type="submit"
              variant="primary"
              loading={saving}
              disabled={saving}
            >
              Salva Configurazione
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default BackupPage;
