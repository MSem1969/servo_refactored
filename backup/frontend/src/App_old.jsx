import React, { useState, useEffect, useCallback } from "react";
import {
  dashboardApi,
  uploadApi,
  ordiniApi,
  anagraficaApi,
  tracciatiApi,
  anomalieApi,
  lookupApi,
  supervisioneApi,
  authApi,
  utentiApi,
  getApiBaseUrl,
} from "./api";

// ============================================
// HELPER FUNCTIONS - DATA CONSEGNA E URGENZA
// v6.2: Nuove funzioni per gestione urgenza consegna
// ============================================

/**
 * addBusinessDays - Aggiunge N giorni lavorativi a una data
 *
 * LOGICA IMPLEMENTATIVA:
 * 1. Parte dalla data fornita
 * 2. Itera giorno per giorno
 * 3. Conta solo i giorni feriali (lun-ven, esclude sab=6 e dom=0)
 * 4. Si ferma quando ha aggiunto il numero richiesto di giorni lavorativi
 *
 * @param {Date} date - Data di partenza
 * @param {number} days - Numero di giorni lavorativi da aggiungere
 * @returns {Date} - Nuova data con i giorni lavorativi aggiunti
 */
const addBusinessDays = (date, days) => {
  const result = new Date(date);
  let addedDays = 0;

  while (addedDays < days) {
    result.setDate(result.getDate() + 1);
    const dayOfWeek = result.getDay();
    // Sabato = 6, Domenica = 0 → SKIP
    if (dayOfWeek !== 0 && dayOfWeek !== 6) {
      addedDays++;
    }
  }
  return result;
};

/**
 * parseDataConsegna - Converte stringa data in oggetto Date
 *
 * FORMATI SUPPORTATI:
 * - "DD/MM/YYYY" (italiano)
 * - "YYYY-MM-DD" (ISO)
 * - null/undefined → null
 *
 * @param {string} dataStr - Data in formato stringa
 * @returns {Date|null} - Oggetto Date o null se non valido
 */
const parseDataConsegna = (dataStr) => {
  if (!dataStr) return null;

  // Formato italiano DD/MM/YYYY
  if (dataStr.includes("/")) {
    const [giorno, mese, anno] = dataStr.split("/").map(Number);
    return new Date(anno, mese - 1, giorno);
  }

  // Formato ISO YYYY-MM-DD
  if (dataStr.includes("-")) {
    return new Date(dataStr);
  }

  return null;
};

/**
 * getDeliveryStatus - Determina lo stato di urgenza di una consegna
 *
 * REGOLE (come da specifiche):
 * - dataConsegna <= oggi → SCADUTO (rosso)
 * - oggi < dataConsegna <= oggi + 3 gg lavorativi → URGENTE (arancione)
 * - dataConsegna > oggi + 3 gg lavorativi → ORDINARIO (verde/neutro)
 *
 * @param {string} dataConsegnaStr - Data consegna in formato stringa
 * @returns {Object} - { status, label, bgColor, textColor, icon }
 */
const getDeliveryStatus = (dataConsegnaStr) => {
  const dataConsegna = parseDataConsegna(dataConsegnaStr);

  // Se data non valida, ritorna stato neutro
  if (!dataConsegna) {
    return {
      status: "nd",
      label: "N/D",
      bgColor: "bg-slate-100",
      textColor: "text-slate-500",
      icon: "⚪",
    };
  }

  // Normalizza oggi a mezzanotte per confronto corretto
  const oggi = new Date();
  oggi.setHours(0, 0, 0, 0);

  // Calcola data limite: oggi + 3 giorni lavorativi
  const dataLimite = addBusinessDays(oggi, 3);
  dataLimite.setHours(23, 59, 59, 999);

  // REGOLA 1: dataConsegna <= oggi → SCADUTO
  if (dataConsegna <= oggi) {
    return {
      status: "scaduto",
      label: "SCADUTO",
      bgColor: "bg-red-100",
      textColor: "text-red-700",
      icon: "🔴",
    };
  }

  // REGOLA 2: oggi < dataConsegna <= oggi + 3 gg lav → URGENTE
  if (dataConsegna <= dataLimite) {
    return {
      status: "urgente",
      label: "URGENTE",
      bgColor: "bg-amber-100",
      textColor: "text-amber-700",
      icon: "🟠",
    };
  }

  // REGOLA 3: dataConsegna > oggi + 3 gg lav → ORDINARIO
  return {
    status: "ordinario",
    label: "ORDINARIO",
    bgColor: "bg-emerald-100",
    textColor: "text-emerald-700",
    icon: "🟢",
  };
};

/**
 * getRowHighlightClass - Restituisce classe CSS per highlighting riga
 *
 * @param {string} dataConsegnaStr - Data consegna
 * @returns {string} - Classi CSS per highlighting
 */
const getRowHighlightClass = (dataConsegnaStr) => {
  const status = getDeliveryStatus(dataConsegnaStr);
  switch (status.status) {
    case "scaduto":
      return "bg-red-50 border-l-4 border-l-red-500";
    case "urgente":
      return "bg-amber-50 border-l-4 border-l-amber-400";
    default:
      return "";
  }
};

/**
 * formatDataForDisplay - Formatta data per visualizzazione DD/MM/YYYY
 *
 * @param {string} dataStr - Data in qualsiasi formato
 * @returns {string} - Data formattata o "-"
 */
const formatDataForDisplay = (dataStr) => {
  if (!dataStr) return "-";

  // Se già in formato italiano, ritorna così
  if (dataStr.includes("/")) return dataStr;

  // Se formato ISO, converti
  if (dataStr.includes("-")) {
    const [anno, mese, giorno] = dataStr.split("-");
    return `${giorno}/${mese}/${anno}`;
  }

  return dataStr;
};

// ============================================
// COMPONENTS
// ============================================
const StatusBadge = ({ status }) => {
  const styles = {
    completed: "bg-emerald-100 text-emerald-700",
    processing: "bg-amber-100 text-amber-700",
    pending: "bg-slate-100 text-slate-600",
    error: "bg-red-100 text-red-700",
    duplicato: "bg-yellow-100 text-yellow-700",
    ESTRATTO: "bg-blue-100 text-blue-700",
    VALIDATO: "bg-emerald-100 text-emerald-700",
    ANOMALIA: "bg-red-100 text-red-700",
    INTEGRATO: "bg-purple-100 text-purple-700",
    ESPORTATO: "bg-slate-100 text-slate-600",
    PENDING_REVIEW: "bg-orange-100 text-orange-700",
    APERTA: "bg-red-100 text-red-700",
    RISOLTA: "bg-emerald-100 text-emerald-700",
    IGNORATA: "bg-slate-100 text-slate-500",
    PENDING: "bg-orange-100 text-orange-700",
    APPROVED: "bg-emerald-100 text-emerald-700",
    REJECTED: "bg-red-100 text-red-700",
    MODIFIED: "bg-purple-100 text-purple-700",
  };
  const labels = {
    completed: "✓ OK",
    processing: "● ...",
    pending: "○",
    error: "✕",
    duplicato: "⚠️ Duplicato",
    ESTRATTO: "Estratto",
    VALIDATO: "Validato",
    ANOMALIA: "Anomalia",
    INTEGRATO: "Integrato",
    ESPORTATO: "Esportato",
    PENDING_REVIEW: "⏳ In Revisione",
    APERTA: "Aperta",
    RISOLTA: "Risolta",
    IGNORATA: "Ignorata",
    PENDING: "⏳ Pending",
    APPROVED: "✓ Approvato",
    REJECTED: "✕ Rifiutato",
    MODIFIED: "✎ Modificato",
  };
  return (
    <span
      className={`px-2 py-0.5 text-xs font-medium rounded-full ${
        styles[status] || styles.pending
      }`}
    >
      {labels[status] || status}
    </span>
  );
};

/**
 * DeliveryBadge - Badge visuale per stato urgenza consegna
 * v6.2: Nuovo componente
 *
 * RENDERING CONDIZIONALE:
 * - SCADUTO: Badge rosso con icona 🔴 + label + data sotto
 * - URGENTE: Badge arancione con icona 🟠 + label + data sotto
 * - ORDINARIO: Icona verde 🟢 + data
 * - N/D: Trattino grigio
 *
 * @param {string} dataConsegna - Data in formato "DD/MM/YYYY" o "YYYY-MM-DD"
 */
const DeliveryBadge = ({ dataConsegna }) => {
  // Se data non presente, mostra placeholder
  if (!dataConsegna) {
    return <span className="text-slate-400 text-xs">-</span>;
  }

  const status = getDeliveryStatus(dataConsegna);
  const displayDate = formatDataForDisplay(dataConsegna);

  // CASO: Stato ORDINARIO → rendering minimale (icona verde + data)
  if (status.status === "ordinario") {
    return (
      <span className="text-emerald-600 font-mono text-xs flex items-center gap-1">
        <span>🟢</span>
        <span>{displayDate}</span>
      </span>
    );
  }

  // CASO: Stato N/D → trattino
  if (status.status === "nd") {
    return <span className="text-slate-400 text-xs">-</span>;
  }

  // CASO: Stato SCADUTO o URGENTE → badge colorato con label
  return (
    <div className="flex flex-col items-start gap-0.5">
      <span
        className={`px-1.5 py-0.5 text-xs font-semibold rounded-full ${status.bgColor} ${status.textColor} flex items-center gap-1`}
      >
        <span>{status.icon}</span>
        <span>{status.label}</span>
      </span>
      <span className={`text-xs font-mono ${status.textColor}`}>
        {displayDate}
      </span>
    </div>
  );
};

const VendorBadge = ({ vendor }) => {
  const colors = {
    ANGELINI: "bg-blue-100 text-blue-700",
    BAYER: "bg-amber-100 text-amber-700",
    CODIFI: "bg-emerald-100 text-emerald-700",
    CHIESI: "bg-purple-100 text-purple-700",
    MENARINI: "bg-pink-100 text-pink-700",
    OPELLA: "bg-indigo-100 text-indigo-700",
  };
  return (
    <span
      className={`px-1.5 py-0.5 text-xs rounded ${
        colors[vendor] || "bg-slate-100 text-slate-700"
      }`}
    >
      {vendor}
    </span>
  );
};

const StatCard = ({ title, value, icon, trend, color, onClick, loading }) => (
  <div
    onClick={onClick}
    className={`bg-white rounded-xl p-4 border border-slate-200 hover:shadow-lg transition-all ${
      onClick ? "cursor-pointer" : ""
    } group`}
  >
    <div className="flex items-start justify-between">
      <div>
        <p className="text-xs font-medium text-slate-500 uppercase">{title}</p>
        {loading ? (
          <div className="h-8 w-16 bg-slate-200 animate-pulse rounded mt-1"></div>
        ) : (
          <p className="text-2xl font-bold text-slate-800 mt-1 font-mono">
            {value?.toLocaleString() ?? "-"}
          </p>
        )}
        {trend !== undefined && (
          <p
            className={`text-xs mt-1 ${
              trend > 0
                ? "text-emerald-600"
                : trend < 0
                ? "text-red-600"
                : "text-slate-400"
            }`}
          >
            {trend > 0 ? "↑" : trend < 0 ? "↓" : "→"} {Math.abs(trend)}%
          </p>
        )}
      </div>
      <div
        className={`w-10 h-10 rounded-xl flex items-center justify-center text-xl ${color} group-hover:scale-110 transition-transform`}
      >
        {icon}
      </div>
    </div>
  </div>
);

const WorkflowProgress = ({ steps }) => (
  <div className="flex items-center justify-between">
    {steps.map((step, i) => (
      <React.Fragment key={step.id}>
        <div className="flex flex-col items-center">
          <div
            className={`w-10 h-10 rounded-xl flex items-center justify-center text-lg transition-all
            ${
              step.status === "completed"
                ? "bg-emerald-100 text-emerald-600"
                : ""
            }
            ${
              step.status === "active"
                ? "bg-blue-100 text-blue-600 ring-2 ring-blue-300"
                : ""
            }
            ${step.status === "pending" ? "bg-slate-100 text-slate-400" : ""}`}
          >
            {step.icon}
          </div>
          <p className="text-xs font-medium text-slate-600 mt-1">{step.name}</p>
          <p
            className={`text-xs font-mono ${
              step.status === "active"
                ? "text-blue-600 font-bold"
                : "text-slate-400"
            }`}
          >
            {step.count ?? "-"}
          </p>
        </div>
        {i < steps.length - 1 && (
          <div
            className={`flex-1 h-0.5 mx-2 ${
              step.status === "completed" ? "bg-emerald-400" : "bg-slate-200"
            }`}
          />
        )}
      </React.Fragment>
    ))}
  </div>
);

const Button = ({
  children,
  variant = "primary",
  size = "md",
  onClick,
  disabled,
  className = "",
}) => {
  const variants = {
    primary: "bg-blue-600 text-white hover:bg-blue-700 disabled:bg-blue-300",
    secondary: "bg-slate-100 text-slate-700 hover:bg-slate-200",
    success: "bg-emerald-600 text-white hover:bg-emerald-700",
    danger: "bg-red-600 text-white hover:bg-red-700",
    ghost: "text-slate-600 hover:bg-slate-100",
  };
  const sizes = {
    sm: "px-3 py-1.5 text-xs",
    md: "px-4 py-2 text-sm",
  };
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`${variants[variant]} ${sizes[size]} font-medium rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed ${className}`}
    >
      {children}
    </button>
  );
};

const Loading = ({ text = "Caricamento..." }) => (
  <div className="flex items-center justify-center p-8">
    <div className="animate-spin w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full mr-3"></div>
    <span className="text-slate-600">{text}</span>
  </div>
);

const ErrorBox = ({ message, onRetry }) => (
  <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-center">
    <p className="text-red-700 mb-2">❌ {message}</p>
    {onRetry && (
      <Button variant="secondary" size="sm" onClick={onRetry}>
        🔄 Riprova
      </Button>
    )}
  </div>
);

// ============================================
// LOGIN PAGE v6.2
// ============================================
const LoginPage = ({ onLogin }) => {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
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
    <div className="min-h-screen bg-white flex items-center justify-center p-4">
      <form onSubmit={handleSubmit} className="w-full max-w-sm space-y-4">
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
            className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
            tabIndex={-1}
          >
            {showPassword ? "👁️" : "👁️‍🗨️"}
          </button>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:bg-blue-300 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? "ACCESSO..." : "ACCEDI"}
        </button>

        {error && <p className="text-red-600 text-sm text-center">{error}</p>}
      </form>
    </div>
  );
};

// ============================================
// DASHBOARD PAGE
// ============================================
const DashboardPage = ({ onNavigate }) => {
  const [stats, setStats] = useState(null);
  const [recentOrders, setRecentOrders] = useState([]);
  const [vendorStats, setVendorStats] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [statsRes, recentRes, vendorRes] = await Promise.all([
        dashboardApi.getStats(),
        dashboardApi.getOrdiniRecenti(8),
        dashboardApi.getVendorStats(),
      ]);
      if (statsRes.success) setStats(statsRes.data);
      if (recentRes.success) setRecentOrders(recentRes.data || []);
      if (vendorRes.success) setVendorStats(vendorRes.data || []);
    } catch (err) {
      setError(err.message || "Errore caricamento dati");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const workflowSteps = [
    {
      id: 1,
      name: "Upload",
      icon: "📁",
      status: "completed",
      count: stats?.acquisizioni_oggi || 0,
    },
    {
      id: 2,
      name: "Estrazione",
      icon: "⚙️",
      status: "completed",
      count: stats?.ordini_totali || 0,
    },
    {
      id: 3,
      name: "Lookup",
      icon: "🔍",
      status: stats?.lookup_pending > 0 ? "active" : "completed",
      count: stats?.lookup_pending || 0,
    },
    {
      id: 4,
      name: "Tracciati",
      icon: "📋",
      status: stats?.pronti_export > 0 ? "active" : "pending",
      count: stats?.pronti_export || 0,
    },
  ];

  if (error) return <ErrorBox message={error} onRetry={loadData} />;

  return (
    <div className="space-y-4">
      {/* Stats Cards */}
      <div className="grid grid-cols-4 gap-3">
        <StatCard
          title="PDF Oggi"
          value={stats?.acquisizioni_oggi}
          icon="📄"
          color="bg-blue-100"
          onClick={() => onNavigate("upload")}
          loading={loading}
        />
        <StatCard
          title="In Attesa Lookup"
          value={stats?.lookup_pending}
          icon="⏳"
          color="bg-amber-100"
          onClick={() => onNavigate("lookup")}
          loading={loading}
        />
        <StatCard
          title="Pronti Export"
          value={stats?.pronti_export}
          icon="📋"
          color="bg-emerald-100"
          onClick={() => onNavigate("tracciati")}
          loading={loading}
        />
        <StatCard
          title="Anomalie"
          value={stats?.anomalie_aperte}
          icon="⚠️"
          color="bg-red-100"
          loading={loading}
        />
      </div>

      {/* Workflow */}
      <div className="bg-white rounded-xl p-4 border border-slate-200">
        <h3 className="text-sm font-bold text-slate-800 mb-3">Workflow</h3>
        <WorkflowProgress steps={workflowSteps} />
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-3 gap-3">
        {/* Recent Activity */}
        <div className="col-span-2 bg-white rounded-xl border border-slate-200">
          <div className="p-3 border-b border-slate-100">
            <h3 className="text-sm font-bold text-slate-800">
              Attività Recente
            </h3>
          </div>
          {loading ? (
            <Loading />
          ) : recentOrders.length === 0 ? (
            <p className="p-4 text-center text-slate-500 text-sm">
              Nessun ordine recente
            </p>
          ) : (
            <div className="divide-y divide-slate-100">
              {recentOrders.map((item) => (
                <div
                  key={item.id_testata}
                  className="p-2.5 hover:bg-slate-50 flex items-center gap-2"
                >
                  <div className="w-7 h-7 bg-slate-100 rounded-lg flex items-center justify-center text-sm">
                    📄
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-slate-800 truncate text-xs font-mono">
                      {item.numero_ordine}
                    </p>
                    <p className="text-xs text-slate-400 truncate">
                      {item.ragione_sociale}
                    </p>
                  </div>
                  <VendorBadge vendor={item.vendor} />
                  <StatusBadge status={item.stato} />
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Vendor Stats */}
        <div className="bg-white rounded-xl border border-slate-200">
          <div className="p-3 border-b border-slate-100">
            <h3 className="text-sm font-bold text-slate-800">Vendor</h3>
          </div>
          {loading ? (
            <Loading />
          ) : (
            <div className="p-3 space-y-2">
              {vendorStats.map((v) => (
                <div key={v.vendor} className="flex items-center gap-2">
                  <span className="text-xs text-slate-600 w-20">
                    {v.vendor}
                  </span>
                  <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full bg-blue-500"
                      style={{
                        width: `${Math.min(
                          (v.count / (stats?.ordini_totali || 1)) * 100,
                          100
                        )}%`,
                      }}
                    />
                  </div>
                  <span className="text-xs font-mono text-slate-500 w-8 text-right">
                    {v.count}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Quick Actions */}
      <div className="bg-gradient-to-r from-blue-600 to-blue-700 rounded-xl p-4 text-white flex items-center justify-between">
        <div>
          <h3 className="font-bold">Pronto per elaborare?</h3>
          <p className="text-blue-100 text-sm">
            {stats?.lookup_pending || 0} ordini in attesa di lookup
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => onNavigate("upload")}
            className="px-4 py-2 bg-white text-blue-600 font-medium rounded-lg text-sm hover:bg-blue-50"
          >
            📁 Upload
          </button>
          <button
            onClick={() => onNavigate("lookup")}
            className="px-4 py-2 bg-blue-500 text-white font-medium rounded-lg text-sm hover:bg-blue-400"
          >
            🔍 Lookup
          </button>
        </div>
      </div>
    </div>
  );
};

// ============================================
// UPLOAD PAGE
// ============================================
const UploadPage = () => {
  const [files, setFiles] = useState([]);
  const [isDragging, setIsDragging] = useState(false);
  const [stats, setStats] = useState(null);
  const [logs, setLogs] = useState([{ type: "info", text: "Sistema pronto" }]);

  const addLog = (type, text) => {
    setLogs((prev) => [
      ...prev,
      { type, text, time: new Date().toLocaleTimeString() },
    ]);
  };

  useEffect(() => {
    uploadApi.getStats().then((res) => {
      if (res.success) setStats(res.data);
    });
  }, []);

  const handleFiles = async (fileList) => {
    const pdfFiles = Array.from(fileList).filter(
      (f) => f.type === "application/pdf"
    );
    if (pdfFiles.length === 0) {
      addLog("error", "Seleziona file PDF validi");
      return;
    }

    for (const file of pdfFiles) {
      const fileId = Date.now() + Math.random();
      const newFile = {
        id: fileId,
        name: file.name,
        size: file.size,
        status: "uploading",
        progress: 0,
        vendor: null,
        righe: 0,
        error: null,
      };
      setFiles((prev) => [...prev, newFile]);
      addLog("upload", `Upload: ${file.name}`);

      try {
        const result = await uploadApi.uploadPdf(file, (progress) => {
          setFiles((prev) =>
            prev.map((f) =>
              f.id === fileId ? { ...f, progress, status: "uploading" } : f
            )
          );
        });

        if (result.success) {
          // Controlla se è un duplicato
          const isDuplicato = result.data?.status === "DUPLICATO";

          setFiles((prev) =>
            prev.map((f) =>
              f.id === fileId
                ? {
                    ...f,
                    status: isDuplicato ? "duplicato" : "completed",
                    progress: 100,
                    vendor: result.data?.vendor,
                    righe: result.data?.totale_righe || 0,
                    message: result.message,
                  }
                : f
            )
          );

          if (isDuplicato) {
            addLog("warn", `⚠️ ${file.name}: ${result.message}`);
          } else {
            addLog(
              "ok",
              `✓ ${file.name}: ${result.data?.vendor || "OK"} - ${
                result.data?.totale_righe || 0
              } righe`
            );
          }
        } else {
          throw new Error(result.error || "Upload fallito");
        }
      } catch (err) {
        setFiles((prev) =>
          prev.map((f) =>
            f.id === fileId ? { ...f, status: "error", error: err.message } : f
          )
        );
        addLog("error", `✕ ${file.name}: ${err.message}`);
      }
    }

    // Refresh stats
    uploadApi.getStats().then((res) => {
      if (res.success) setStats(res.data);
    });
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    handleFiles(e.dataTransfer.files);
  };

  const handleFileInput = (e) => {
    handleFiles(e.target.files);
    e.target.value = "";
  };

  const clearFiles = () => {
    setFiles([]);
    setLogs([{ type: "info", text: "Lista pulita" }]);
  };

  const formatSize = (bytes) => {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  };

  return (
    <div className="space-y-4">
      {/* Stats */}
      <div className="grid grid-cols-4 gap-3">
        <StatCard
          title="Totale Upload"
          value={stats?.totale}
          icon="📁"
          color="bg-blue-100"
        />
        <StatCard
          title="Oggi"
          value={stats?.oggi}
          icon="📅"
          color="bg-emerald-100"
        />
        <StatCard
          title="Elaborati"
          value={stats?.elaborati}
          icon="✓"
          color="bg-green-100"
        />
        <StatCard
          title="Errori"
          value={stats?.errori}
          icon="✕"
          color="bg-red-100"
        />
      </div>

      {/* Drop Zone */}
      <div
        className={`bg-white rounded-xl border-2 border-dashed p-8 text-center transition-all cursor-pointer
          ${
            isDragging
              ? "border-blue-500 bg-blue-50"
              : "border-slate-300 hover:border-blue-400"
          }`}
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        onClick={() => document.getElementById("fileInput").click()}
      >
        <input
          id="fileInput"
          type="file"
          accept=".pdf"
          multiple
          className="hidden"
          onChange={handleFileInput}
        />
        <div className="w-14 h-14 bg-blue-100 rounded-2xl flex items-center justify-center mx-auto mb-3 text-2xl">
          📁
        </div>
        <p className="text-base font-medium text-slate-700">
          Trascina qui i file PDF
        </p>
        <p className="text-sm text-slate-500 mt-1">
          oppure clicca per selezionare
        </p>
        <div className="flex flex-wrap justify-center gap-1.5 mt-3">
          {["ANGELINI", "BAYER", "CODIFI", "CHIESI", "MENARINI", "OPELLA"].map(
            (v) => (
              <VendorBadge key={v} vendor={v} />
            )
          )}
        </div>
      </div>

      {/* File List */}
      {files.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200">
          <div className="p-3 border-b border-slate-100 flex justify-between items-center">
            <h3 className="font-bold text-slate-800 text-sm">
              File Caricati ({files.length})
            </h3>
            <Button variant="secondary" size="sm" onClick={clearFiles}>
              🗑️ Pulisci
            </Button>
          </div>
          <div className="divide-y divide-slate-100 max-h-64 overflow-y-auto">
            {files.map((file) => (
              <div
                key={file.id}
                className={`p-3 flex items-center gap-3 ${
                  file.status === "duplicato" ? "bg-yellow-50" : ""
                }`}
              >
                <div
                  className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                    file.status === "duplicato" ? "bg-yellow-100" : "bg-red-100"
                  }`}
                >
                  {file.status === "duplicato" ? "⚠️" : "📄"}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-slate-800 text-sm font-mono truncate">
                    {file.name}
                  </p>
                  <div className="flex items-center gap-2 text-xs text-slate-400">
                    <span>{formatSize(file.size)}</span>
                    {file.status === "uploading" && (
                      <span>• {file.progress}%</span>
                    )}
                    {file.righe > 0 && <span>• {file.righe} righe</span>}
                    {file.error && (
                      <span className="text-red-500">• {file.error}</span>
                    )}
                  </div>
                  {/* Messaggio duplicato */}
                  {file.status === "duplicato" && file.message && (
                    <p
                      className="text-xs text-yellow-700 mt-1 truncate"
                      title={file.message}
                    >
                      {file.message}
                    </p>
                  )}
                  {file.status === "uploading" && (
                    <div className="w-full h-1 bg-slate-200 rounded-full mt-1">
                      <div
                        className="h-full bg-blue-500 rounded-full transition-all"
                        style={{ width: `${file.progress}%` }}
                      />
                    </div>
                  )}
                </div>
                {file.vendor && <VendorBadge vendor={file.vendor} />}
                <StatusBadge status={file.status} />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Console Log */}
      <div className="bg-slate-900 rounded-xl p-3 text-xs h-32 overflow-y-auto font-mono">
        {logs.map((log, i) => (
          <p
            key={i}
            className={`
              ${log.type === "info" ? "text-slate-400" : ""}
              ${log.type === "upload" ? "text-blue-400" : ""}
              ${log.type === "ok" ? "text-emerald-400" : ""}
              ${log.type === "warn" ? "text-yellow-400" : ""}
              ${log.type === "error" ? "text-red-400" : ""}
            `}
          >
            [{log.time || "INIT"}] {log.text}
          </p>
        ))}
      </div>
    </div>
  );
};

// ============================================
// DATABASE PAGE v6.2
// Aggiunta colonna dataConsegna + highlighting urgenza
// ============================================
const DatabasePage = ({ onOpenOrdine }) => {
  const [activeTab, setActiveTab] = useState("ordini");
  const [ordini, setOrdini] = useState([]);
  const [selectedOrdine, setSelectedOrdine] = useState(null);
  const [righe, setRighe] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({ vendor: "", stato: "", q: "" });
  const [selected, setSelected] = useState([]);

  const loadOrdini = useCallback(async () => {
    try {
      setLoading(true);
      const res = await ordiniApi.getList({ ...filters, limit: 50 });
      if (res.success) setOrdini(res.data || []);
    } catch (err) {
      console.error("Errore caricamento ordini:", err);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    loadOrdini();
  }, [loadOrdini]);

  const loadRighe = async (ordine) => {
    setSelectedOrdine(ordine);
    try {
      const res = await ordiniApi.getRighe(ordine.id_testata);
      if (res.success) setRighe(res.data || []);
    } catch (err) {
      console.error("Errore caricamento righe:", err);
    }
  };

  const toggleSelect = (id) => {
    setSelected((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  const selectAll = () => {
    if (selected.length === ordini.length) {
      setSelected([]);
    } else {
      setSelected(ordini.map((o) => o.id_testata));
    }
  };

  const handleBatchDelete = async () => {
    if (
      selected.length === 0 ||
      !confirm(`Eliminare ${selected.length} ordini?`)
    )
      return;
    try {
      await ordiniApi.batchDelete(selected);
      setSelected([]);
      loadOrdini();
    } catch (err) {
      alert("Errore eliminazione");
    }
  };

  // v6.1.2: Validazione massiva con conferma
  const [validatingBatch, setValidatingBatch] = useState(false);

  const handleBatchValidate = async () => {
    if (selected.length === 0) return;

    // Prompt con conferma esplicita
    const conferma = prompt(
      `⚠️ SEI SICURO DI VOLER CONVALIDARE MASSIVAMENTE?\n\n` +
        `Saranno generati i tracciati TOTALI di tutti i ${selected.length} ordini flaggati.\n\n` +
        `ATTENZIONE: Verranno confermate ed esportate TUTTE le righe di ciascun ordine.\n\n` +
        `Se vuoi procedere digita S, altrimenti clicca Annulla:`
    );

    if (conferma?.toUpperCase() !== "S") {
      return;
    }

    setValidatingBatch(true);
    const operatore = "BATCH_EXPORT";

    let successi = 0;
    let errori = [];
    let totaleRighe = 0;

    try {
      for (const id_testata of selected) {
        try {
          // Prima conferma tutte le righe dell'ordine
          await ordiniApi.confermaOrdineCompleto(id_testata, operatore);

          // Poi genera il tracciato
          const res = await ordiniApi.validaEGeneraTracciato(
            id_testata,
            operatore
          );
          if (res.success) {
            successi++;
            totaleRighe += res.statistiche?.righe_esportate || 0;
          } else {
            errori.push({
              id: id_testata,
              error: res.error || "Errore sconosciuto",
            });
          }
        } catch (err) {
          errori.push({ id: id_testata, error: err.message });
        }
      }

      // Messaggio riepilogo
      let msg = `✅ VALIDAZIONE MASSIVA COMPLETATA\n\n`;
      msg += `📊 Ordini processati: ${selected.length}\n`;
      msg += `✓ Successi: ${successi}\n`;
      msg += `📄 Righe esportate: ${totaleRighe}\n`;

      if (errori.length > 0) {
        msg += `\n⚠️ Errori: ${errori.length}\n`;
        errori.slice(0, 5).forEach((e) => {
          msg += `  - Ordine #${e.id}: ${e.error}\n`;
        });
        if (errori.length > 5) {
          msg += `  ... e altri ${errori.length - 5} errori\n`;
        }
      }

      alert(msg);
      setSelected([]);
      loadOrdini();
    } catch (err) {
      alert("Errore durante la validazione massiva: " + err.message);
    } finally {
      setValidatingBatch(false);
    }
  };

  const tabs = [
    { id: "ordini", label: "ORDINI_TESTATA", count: ordini.length },
    { id: "righe", label: "ORDINI_DETTAGLIO", count: righe.length },
  ];

  return (
    <div className="space-y-3">
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        {/* Tabs */}
        <div className="flex border-b border-slate-200">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-3 py-2 text-xs font-medium ${
                activeTab === tab.id
                  ? "text-blue-600 border-b-2 border-blue-600 bg-blue-50"
                  : "text-slate-500 hover:bg-slate-50"
              }`}
            >
              {tab.label}{" "}
              <span className="ml-1 text-slate-400">({tab.count})</span>
            </button>
          ))}
        </div>

        {/* Filters */}
        <div className="p-3 border-b border-slate-100 flex gap-3">
          <input
            type="text"
            placeholder="🔍 Cerca..."
            value={filters.q}
            onChange={(e) => setFilters({ ...filters, q: e.target.value })}
            className="flex-1 px-3 py-1.5 border border-slate-200 rounded-lg text-sm"
          />
          <select
            value={filters.vendor}
            onChange={(e) => setFilters({ ...filters, vendor: e.target.value })}
            className="px-3 py-1.5 border border-slate-200 rounded-lg text-sm"
          >
            <option value="">Tutti i Vendor</option>
            {[
              "ANGELINI",
              "BAYER",
              "CODIFI",
              "CHIESI",
              "MENARINI",
              "OPELLA",
            ].map((v) => (
              <option key={v} value={v}>
                {v}
              </option>
            ))}
          </select>
          <select
            value={filters.stato}
            onChange={(e) => setFilters({ ...filters, stato: e.target.value })}
            className="px-3 py-1.5 border border-slate-200 rounded-lg text-sm"
          >
            <option value="">Tutti gli Stati</option>
            {["ESTRATTO", "VALIDATO", "ANOMALIA", "INTEGRATO", "ESPORTATO"].map(
              (s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              )
            )}
          </select>
          <Button variant="secondary" size="sm" onClick={loadOrdini}>
            🔄
          </Button>
          {/* Bottoni azione batch */}
          {selected.length > 0 && (
            <>
              <Button
                variant="danger"
                size="sm"
                onClick={handleBatchDelete}
                disabled={validatingBatch}
                title={`Elimina ${selected.length} ordini`}
              >
                🗑️ Elimina ({selected.length})
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={handleBatchValidate}
                disabled={validatingBatch}
                title={`Valida e genera tracciati per ${selected.length} ordini`}
              >
                {validatingBatch
                  ? "⏳ Validazione..."
                  : `✓ Valida (${selected.length})`}
              </Button>
            </>
          )}
        </div>

        {/* Ordini Table - v6.2: Aggiunta colonna Consegna */}
        {activeTab === "ordini" && (
          <div className="overflow-x-auto">
            {loading ? (
              <Loading />
            ) : ordini.length === 0 ? (
              <p className="p-6 text-center text-slate-500">
                Nessun ordine trovato
              </p>
            ) : (
              <table className="w-full text-xs">
                <thead className="bg-slate-50 text-slate-600">
                  <tr>
                    <th className="w-8 p-2">
                      <input
                        type="checkbox"
                        checked={
                          selected.length === ordini.length && ordini.length > 0
                        }
                        onChange={selectAll}
                      />
                    </th>
                    <th className="p-2 text-left">Vendor</th>
                    <th className="p-2 text-left">N. Ordine</th>
                    {/* v6.2: NUOVA COLONNA CONSEGNA */}
                    <th className="p-2 text-left">📅 Consegna</th>
                    <th className="p-2 text-left">Farmacia</th>
                    <th className="p-2 text-left">Città</th>
                    <th className="p-2 text-center">Righe</th>
                    <th className="p-2 text-center">Confermate</th>
                    <th className="p-2 text-center">Stato</th>
                    <th className="p-2 text-center">Lookup</th>
                    <th className="p-2 text-center">Azioni</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {ordini.map((row) => (
                    <tr
                      key={row.id_testata}
                      className={`hover:bg-slate-50 cursor-pointer ${
                        selectedOrdine?.id_testata === row.id_testata
                          ? "bg-blue-50"
                          : ""
                      } ${getRowHighlightClass(row.data_consegna)}`}
                      onClick={() => loadRighe(row)}
                    >
                      <td
                        className="p-2 text-center"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <input
                          type="checkbox"
                          checked={selected.includes(row.id_testata)}
                          onChange={() => toggleSelect(row.id_testata)}
                        />
                      </td>
                      <td className="p-2">
                        <VendorBadge vendor={row.vendor} />
                      </td>
                      <td className="p-2 font-mono font-medium">
                        {row.numero_ordine}
                      </td>
                      {/* v6.2: NUOVA CELLA CONSEGNA con DeliveryBadge */}
                      <td className="p-2">
                        <DeliveryBadge dataConsegna={row.data_consegna} />
                      </td>
                      <td className="p-2 truncate max-w-[200px]">
                        {row.ragione_sociale}
                      </td>
                      <td className="p-2 text-slate-500">{row.citta}</td>
                      <td className="p-2 text-center">
                        {row.righe_totali || row.num_righe || "-"}
                      </td>
                      <td className="p-2 text-center">
                        {row.righe_confermate !== undefined &&
                        row.righe_totali > 0 ? (
                          <span
                            className={`text-xs font-mono ${
                              row.righe_confermate === row.righe_totali
                                ? "text-emerald-600"
                                : row.righe_confermate > 0
                                ? "text-amber-600"
                                : "text-slate-400"
                            }`}
                          >
                            {row.righe_confermate}/{row.righe_totali}
                          </span>
                        ) : (
                          "-"
                        )}
                      </td>
                      <td className="p-2 text-center">
                        <StatusBadge status={row.stato} />
                      </td>
                      <td className="p-2 text-center">
                        <span
                          className={`text-xs ${
                            row.lookup_score >= 90
                              ? "text-emerald-600"
                              : row.lookup_score >= 60
                              ? "text-amber-600"
                              : "text-red-600"
                          }`}
                        >
                          {row.lookup_method || "-"}
                          {row.lookup_score ? ` (${row.lookup_score}%)` : ""}
                        </span>
                      </td>
                      <td
                        className="p-2 text-center"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <button
                          onClick={() =>
                            onOpenOrdine && onOpenOrdine(row.id_testata)
                          }
                          className="px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded hover:bg-blue-200"
                          title="Apri dettaglio ordine con conferma righe"
                        >
                          📋 Dettaglio
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}

        {/* Righe Table - v6.2: Aggiunta colonna Consegna */}
        {activeTab === "righe" && (
          <div className="overflow-x-auto">
            {!selectedOrdine ? (
              <p className="p-6 text-center text-slate-500">
                Seleziona un ordine per vedere le righe
              </p>
            ) : righe.length === 0 ? (
              <p className="p-6 text-center text-slate-500">Nessuna riga</p>
            ) : (
              <>
                <div className="p-3 bg-slate-50 border-b border-slate-100">
                  <span className="text-sm font-medium">
                    Ordine:{" "}
                    <span className="font-mono">
                      {selectedOrdine.numero_ordine}
                    </span>
                  </span>
                </div>
                <table className="w-full text-xs">
                  <thead className="bg-slate-50 text-slate-600">
                    <tr>
                      <th className="p-2 text-left">#</th>
                      <th className="p-2 text-left">AIC</th>
                      <th className="p-2 text-left">Descrizione</th>
                      {/* v6.2: NUOVA COLONNA CONSEGNA */}
                      <th className="p-2 text-left">📅 Consegna</th>
                      <th className="p-2 text-right">Q.tà</th>
                      <th className="p-2 text-right">Prezzo</th>
                      <th className="p-2 text-right">Sconto</th>
                      <th className="p-2 text-center">Flags</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {righe.map((row) => (
                      <tr
                        key={row.id_dettaglio}
                        className={`hover:bg-slate-50 ${getRowHighlightClass(
                          row.data_consegna
                        )}`}
                      >
                        <td className="p-2">{row.n_riga}</td>
                        <td className="p-2 font-mono">
                          {row.codice_aic || "-"}
                        </td>
                        <td className="p-2 truncate max-w-[250px]">
                          {row.descrizione}
                        </td>
                        {/* v6.2: NUOVA CELLA CONSEGNA */}
                        <td className="p-2">
                          <DeliveryBadge dataConsegna={row.data_consegna} />
                        </td>
                        <td className="p-2 text-right">{row.q_venduta}</td>
                        <td className="p-2 text-right">
                          €{row.prezzo_netto?.toFixed(2) || "-"}
                        </td>
                        <td className="p-2 text-right">
                          {row.sconto_1 ? `${row.sconto_1}%` : "-"}
                        </td>
                        <td className="p-2 text-center">
                          {row.is_espositore && (
                            <span title="Espositore">🎁</span>
                          )}
                          {row.is_no_aic && <span title="No AIC">⚠️</span>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </>
            )}
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="flex gap-2">
        <Button
          variant="secondary"
          size="sm"
          disabled={selected.length === 0}
          onClick={handleBatchDelete}
        >
          🗑️ Elimina ({selected.length})
        </Button>
        <Button variant="success" size="sm" disabled={selected.length === 0}>
          ✅ Valida ({selected.length})
        </Button>
      </div>

      {/* v6.2: Legenda Urgenze */}
      <div className="bg-white rounded-xl border border-slate-200 p-3">
        <h4 className="text-xs font-semibold text-slate-600 mb-2">
          📌 Legenda Urgenze Consegna
        </h4>
        <div className="flex gap-4 text-xs">
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 bg-red-100 border-l-4 border-red-500 rounded"></span>
            <span className="text-slate-600">🔴 Scaduto (data passata)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 bg-amber-100 border-l-4 border-amber-400 rounded"></span>
            <span className="text-slate-600">
              🟠 Urgente (≤3 gg lavorativi)
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="flex items-center gap-1 text-emerald-600">🟢</span>
            <span className="text-slate-600">
              Ordinario (&gt;3 gg lavorativi)
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

// ============================================
// LOOKUP PAGE
// ============================================
const LookupPage = () => {
  const [stats, setStats] = useState(null);
  const [pending, setPending] = useState([]);
  const [loading, setLoading] = useState(true);
  const [lookupRunning, setLookupRunning] = useState(false);
  const [importProgress, setImportProgress] = useState(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [statsRes, pendingRes] = await Promise.all([
        anagraficaApi.getStats(),
        lookupApi.getPending(20),
      ]);
      if (statsRes.success) setStats(statsRes.data);
      if (pendingRes.success) setPending(pendingRes.data || []);
    } catch (err) {
      console.error("Errore:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const runBatchLookup = async () => {
    setLookupRunning(true);
    try {
      const res = await lookupApi.batch(100);
      if (res.success) {
        alert(`Lookup completato: ${res.data?.matched || 0} match trovati`);
        loadData();
      }
    } catch (err) {
      alert("Errore lookup: " + err.message);
    } finally {
      setLookupRunning(false);
    }
  };

  const handleImportFarmacie = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = "";

    setImportProgress({ type: "farmacie", progress: 0 });
    try {
      const res = await anagraficaApi.importFarmacie(file, (p) => {
        setImportProgress({ type: "farmacie", progress: p });
      });
      if (res.success) {
        alert(`Importate ${res.data?.importate || 0} farmacie`);
        loadData();
      }
    } catch (err) {
      alert("Errore import: " + err.message);
    } finally {
      setImportProgress(null);
    }
  };

  const handleImportParafarmacie = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = "";

    setImportProgress({ type: "parafarmacie", progress: 0 });
    try {
      const res = await anagraficaApi.importParafarmacie(file, (p) => {
        setImportProgress({ type: "parafarmacie", progress: p });
      });
      if (res.success) {
        alert(`Importate ${res.data?.importate || 0} parafarmacie`);
        loadData();
      }
    } catch (err) {
      alert("Errore import: " + err.message);
    } finally {
      setImportProgress(null);
    }
  };

  return (
    <div className="space-y-4">
      {/* Stats */}
      <div className="grid grid-cols-4 gap-3">
        <StatCard
          title="Farmacie"
          value={stats?.farmacie}
          icon="🏥"
          color="bg-blue-100"
          loading={loading}
        />
        <StatCard
          title="Parafarmacie"
          value={stats?.parafarmacie}
          icon="💊"
          color="bg-purple-100"
          loading={loading}
        />
        <StatCard
          title="In Attesa"
          value={pending.length}
          icon="⏳"
          color="bg-amber-100"
          loading={loading}
        />
        <StatCard
          title="Completati"
          value={stats?.lookup_ok || 0}
          icon="✓"
          color="bg-emerald-100"
          loading={loading}
        />
      </div>

      {/* Actions */}
      <div className="flex gap-2 flex-wrap">
        <Button
          variant="primary"
          onClick={runBatchLookup}
          disabled={lookupRunning || pending.length === 0}
        >
          {lookupRunning ? "⏳ Elaborazione..." : "🔍 Avvia Lookup Batch"}
        </Button>
        <label className="cursor-pointer">
          <input
            type="file"
            accept=".csv"
            className="hidden"
            onChange={handleImportFarmacie}
          />
          <span className="px-4 py-2 bg-slate-100 text-slate-700 font-medium rounded-lg text-sm hover:bg-slate-200 inline-block">
            📤 Import Farmacie (CSV)
          </span>
        </label>
        <label className="cursor-pointer">
          <input
            type="file"
            accept=".csv"
            className="hidden"
            onChange={handleImportParafarmacie}
          />
          <span className="px-4 py-2 bg-slate-100 text-slate-700 font-medium rounded-lg text-sm hover:bg-slate-200 inline-block">
            📤 Import Parafarmacie (CSV)
          </span>
        </label>
      </div>

      {/* Import Progress */}
      {importProgress && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
          <p className="text-sm text-blue-700 mb-2">
            Importazione {importProgress.type}... {importProgress.progress}%
          </p>
          <div className="w-full h-2 bg-blue-200 rounded-full">
            <div
              className="h-full bg-blue-600 rounded-full transition-all"
              style={{ width: `${importProgress.progress}%` }}
            />
          </div>
        </div>
      )}

      {/* Pending List */}
      <div className="bg-white rounded-xl border border-slate-200">
        <div className="p-3 border-b border-slate-100">
          <h3 className="font-bold text-slate-800 text-sm">
            Ordini in Attesa di Lookup ({pending.length})
          </h3>
        </div>
        {loading ? (
          <Loading />
        ) : pending.length === 0 ? (
          <p className="p-6 text-center text-slate-500">
            ✓ Tutti gli ordini hanno lookup completato
          </p>
        ) : (
          <div className="divide-y divide-slate-100 max-h-96 overflow-y-auto">
            {pending.map((item) => (
              <div key={item.id_testata} className="p-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <VendorBadge vendor={item.vendor} />
                    <span className="font-mono text-sm font-medium">
                      {item.numero_ordine}
                    </span>
                    <span className="text-slate-400">|</span>
                    <span className="text-sm truncate max-w-[200px]">
                      {item.ragione_sociale}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-slate-500">{item.citta}</span>
                    <span className="text-xs text-slate-400">
                      P.IVA: {item.partita_iva || "N/D"}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

// ============================================
// TRACCIATI PAGE
// ============================================
const TracciatiPage = () => {
  const [pronti, setPronti] = useState([]);
  const [storico, setStorico] = useState([]);
  const [selected, setSelected] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [preview, setPreview] = useState(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [prontiRes, storicoRes] = await Promise.all([
        tracciatiApi.getPronti(),
        tracciatiApi.getStorico(10),
      ]);
      if (prontiRes.success) setPronti(prontiRes.data || []);
      if (storicoRes.success) setStorico(storicoRes.data || []);
    } catch (err) {
      console.error("Errore:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const toggleSelect = (id) => {
    setSelected((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    );
  };

  const selectAll = () => {
    if (selected.length === pronti.length) {
      setSelected([]);
    } else {
      setSelected(pronti.map((o) => o.id_testata));
    }
  };

  const handleGenera = async () => {
    if (selected.length === 0) return;
    setGenerating(true);
    try {
      const res = await tracciatiApi.genera(selected);
      if (res.success) {
        alert(`Generati ${res.data?.files?.length || 0} tracciati`);
        setSelected([]);
        loadData();
      }
    } catch (err) {
      alert("Errore generazione: " + err.message);
    } finally {
      setGenerating(false);
    }
  };

  const showPreview = async (id) => {
    try {
      const res = await tracciatiApi.getPreview(id);
      if (res.success) {
        setPreview(res.data);
      }
    } catch (err) {
      alert("Errore preview");
    }
  };

  return (
    <div className="space-y-4">
      {/* Stats */}
      <div className="grid grid-cols-4 gap-3">
        <StatCard
          title="Pronti"
          value={pronti.length}
          icon="📋"
          color="bg-emerald-100"
          loading={loading}
        />
        <StatCard
          title="Selezionati"
          value={selected.length}
          icon="✓"
          color="bg-blue-100"
        />
        <StatCard
          title="Generati (storico)"
          value={storico.length}
          icon="📁"
          color="bg-slate-100"
          loading={loading}
        />
        <StatCard
          title="Oggi"
          value={storico.filter((s) => s.oggi).length}
          icon="📅"
          color="bg-amber-100"
        />
      </div>

      {/* Ordini Pronti */}
      <div className="bg-white rounded-xl border border-slate-200">
        <div className="p-3 border-b border-slate-100 flex justify-between items-center">
          <h3 className="font-bold text-slate-800 text-sm">
            Ordini Pronti per Export
          </h3>
          <Button
            variant="primary"
            size="sm"
            onClick={handleGenera}
            disabled={selected.length === 0 || generating}
          >
            {generating ? "⏳..." : `📋 Genera (${selected.length})`}
          </Button>
        </div>
        {loading ? (
          <Loading />
        ) : pronti.length === 0 ? (
          <p className="p-6 text-center text-slate-500">
            Nessun ordine pronto per export
          </p>
        ) : (
          <table className="w-full text-xs">
            <thead className="bg-slate-50 text-slate-600">
              <tr>
                <th className="w-8 p-2">
                  <input
                    type="checkbox"
                    checked={
                      selected.length === pronti.length && pronti.length > 0
                    }
                    onChange={selectAll}
                  />
                </th>
                <th className="p-2 text-left">Ordine</th>
                <th className="p-2 text-left">Vendor</th>
                <th className="p-2 text-left">Farmacia</th>
                <th className="p-2 text-center">Stato</th>
                <th className="p-2 text-center">Righe</th>
                <th className="p-2 text-center">Azioni</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {pronti.map((row) => (
                <tr
                  key={row.id_testata}
                  className={`hover:bg-slate-50 ${
                    selected.includes(row.id_testata) ? "bg-blue-50" : ""
                  }`}
                >
                  <td className="p-2 text-center">
                    <input
                      type="checkbox"
                      checked={selected.includes(row.id_testata)}
                      onChange={() => toggleSelect(row.id_testata)}
                    />
                  </td>
                  <td className="p-2 font-mono font-medium">
                    {row.numero_ordine}
                  </td>
                  <td className="p-2">
                    <VendorBadge vendor={row.vendor} />
                  </td>
                  <td className="p-2 truncate max-w-[200px]">
                    {row.ragione_sociale}
                  </td>
                  <td className="p-2 text-center">
                    <StatusBadge status={row.stato} />
                  </td>
                  <td className="p-2 text-center">{row.num_righe || "-"}</td>
                  <td className="p-2 text-center">
                    <button
                      className="text-blue-600 hover:underline text-xs"
                      onClick={() => showPreview(row.id_testata)}
                    >
                      👁️ Preview
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Preview Modal */}
      {preview && (
        <div className="bg-white rounded-xl border border-slate-200 p-4">
          <div className="flex justify-between items-center mb-3">
            <h3 className="font-bold text-slate-800 text-sm">
              📄 Preview Tracciato
            </h3>
            <button
              onClick={() => setPreview(null)}
              className="text-slate-400 hover:text-slate-600"
            >
              ✕
            </button>
          </div>
          <div className="bg-slate-900 rounded-lg p-3 text-xs font-mono overflow-x-auto">
            <p className="text-emerald-400 mb-1">TO_T:</p>
            <p className="text-slate-300 whitespace-pre">
              {preview.to_t?.substring(0, 200)}...
            </p>
            <p className="text-blue-400 mt-2 mb-1">TO_D:</p>
            {preview.to_d?.slice(0, 3).map((line, i) => (
              <p key={i} className="text-slate-300 whitespace-pre">
                {line.substring(0, 100)}...
              </p>
            ))}
          </div>
        </div>
      )}

      {/* Storico */}
      <div className="bg-white rounded-xl border border-slate-200">
        <div className="p-3 border-b border-slate-100">
          <h3 className="font-bold text-slate-800 text-sm">
            📁 Storico Esportazioni
          </h3>
        </div>
        {storico.length === 0 ? (
          <p className="p-4 text-center text-slate-500 text-sm">
            Nessuna esportazione effettuata
          </p>
        ) : (
          <div className="divide-y divide-slate-100">
            {storico.slice(0, 10).map((exp) => (
              <div
                key={exp.id_esportazione}
                className="p-3 flex items-center justify-between"
              >
                <div>
                  <p className="font-mono text-sm font-medium text-slate-800">
                    {exp.nome_tracciato_generato ||
                      exp.nome_tracciato ||
                      "Tracciato"}
                    {exp.oggi ? (
                      <span className="ml-2 text-xs bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded">
                        OGGI
                      </span>
                    ) : null}
                  </p>
                  <p className="text-xs text-slate-400">
                    {exp.data_generazione}
                  </p>
                </div>
                <div className="flex items-center gap-4">
                  <div className="text-right">
                    <p className="text-sm">{exp.num_testate} ordini</p>
                    <p className="text-xs text-slate-400">
                      {exp.num_dettagli} righe
                    </p>
                  </div>
                  <div className="flex gap-2">
                    {exp.nome_file_to_t && (
                      <button
                        onClick={() => {
                          fetch(
                            `${getApiBaseUrl()}/api/v1/tracciati/download/${
                              exp.nome_file_to_t
                            }`
                          )
                            .then((res) => res.blob())
                            .then((blob) => {
                              const url = window.URL.createObjectURL(blob);
                              const a = document.createElement("a");
                              a.href = url;
                              a.download = exp.nome_file_to_t;
                              a.click();
                              window.URL.revokeObjectURL(url);
                            });
                        }}
                        className="px-2 py-1 text-xs bg-slate-100 hover:bg-slate-200 rounded text-slate-700"
                        title="Scarica Testata"
                      >
                        📄 T
                      </button>
                    )}
                    {exp.nome_file_to_d && (
                      <button
                        onClick={() => {
                          fetch(
                            `${getApiBaseUrl()}/api/v1/tracciati/download/${
                              exp.nome_file_to_d
                            }`
                          )
                            .then((res) => res.blob())
                            .then((blob) => {
                              const url = window.URL.createObjectURL(blob);
                              const a = document.createElement("a");
                              a.href = url;
                              a.download = exp.nome_file_to_d;
                              a.click();
                              window.URL.revokeObjectURL(url);
                            });
                        }}
                        className="px-2 py-1 text-xs bg-blue-100 hover:bg-blue-200 rounded text-blue-700"
                        title="Scarica Dettaglio"
                      >
                        📄 D
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

// ============================================
// SETTINGS PAGE
// ============================================
const SettingsPage = () => {
  const [settings, setSettings] = useState({
    codProduttore: "HAL_FARVI",
    ggDilazione: 90,
    autoValidate: true,
  });

  return (
    <div className="space-y-4 max-w-2xl">
      {/* Tracciati Settings */}
      <div className="bg-white rounded-xl border border-slate-200">
        <div className="p-3 border-b border-slate-100">
          <h3 className="font-bold text-slate-800 text-sm">
            📋 Configurazione Tracciati
          </h3>
        </div>
        <div className="p-4 grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs text-slate-600 mb-1">
              Codice Produttore
            </label>
            <input
              type="text"
              value={settings.codProduttore}
              onChange={(e) =>
                setSettings({ ...settings, codProduttore: e.target.value })
              }
              className="w-full px-3 py-1.5 border border-slate-200 rounded-lg text-sm font-mono"
            />
          </div>
          <div>
            <label className="block text-xs text-slate-600 mb-1">
              GG Dilazione Default
            </label>
            <input
              type="number"
              value={settings.ggDilazione}
              onChange={(e) =>
                setSettings({
                  ...settings,
                  ggDilazione: parseInt(e.target.value),
                })
              }
              className="w-full px-3 py-1.5 border border-slate-200 rounded-lg text-sm"
            />
          </div>
        </div>
      </div>

      {/* Automation */}
      <div className="bg-white rounded-xl border border-slate-200">
        <div className="p-3 border-b border-slate-100">
          <h3 className="font-bold text-slate-800 text-sm">⚙️ Automazione</h3>
        </div>
        <div className="p-4 space-y-3">
          <label className="flex items-center justify-between p-3 bg-slate-50 rounded-lg cursor-pointer">
            <div>
              <p className="font-medium text-slate-800 text-sm">
                Auto-Validazione
              </p>
              <p className="text-xs text-slate-500">
                Valida automaticamente ordini con lookup OK
              </p>
            </div>
            <input
              type="checkbox"
              checked={settings.autoValidate}
              onChange={(e) =>
                setSettings({ ...settings, autoValidate: e.target.checked })
              }
              className="w-4 h-4"
            />
          </label>
        </div>
      </div>

      {/* Database Actions */}
      <div className="bg-white rounded-xl border border-slate-200">
        <div className="p-3 border-b border-slate-100">
          <h3 className="font-bold text-slate-800 text-sm">🗄️ Database</h3>
        </div>
        <div className="p-4 space-y-2">
          <Button
            variant="danger"
            size="sm"
            onClick={() => {
              if (confirm("Eliminare TUTTE le farmacie?")) {
                anagraficaApi
                  .clearFarmacie()
                  .then(() => alert("Farmacie eliminate"));
              }
            }}
          >
            🗑️ Svuota Farmacie
          </Button>
          <Button
            variant="danger"
            size="sm"
            className="ml-2"
            onClick={() => {
              if (confirm("Eliminare TUTTE le parafarmacie?")) {
                anagraficaApi
                  .clearParafarmacie()
                  .then(() => alert("Parafarmacie eliminate"));
              }
            }}
          >
            🗑️ Svuota Parafarmacie
          </Button>
        </div>
      </div>

      {/* Info */}
      <div className="bg-slate-100 rounded-xl p-4">
        <h3 className="font-bold text-slate-700 text-sm mb-2">
          ℹ️ Informazioni Sistema
        </h3>
        <div className="grid grid-cols-2 gap-2 text-xs text-slate-600">
          <div>
            Versione: <span className="font-mono">6.2.0</span>
          </div>
          <div>
            Backend: <span className="font-mono">FastAPI</span>
          </div>
          <div>
            Database: <span className="font-mono">SQLite</span>
          </div>
          <div>
            Frontend: <span className="font-mono">React + Vite</span>
          </div>
        </div>
      </div>
    </div>
  );
};

// ============================================
// ORDER DETAIL PAGE v6.1
// Dettaglio ordine con conferma righe
// ============================================
const OrderDetailPage = ({ ordineId, onBack, onNavigateToSupervisione }) => {
  const [ordine, setOrdine] = useState(null);
  const [righe, setRighe] = useState([]);
  const [statoRighe, setStatoRighe] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(null);
  const [error, setError] = useState(null);
  const [operatore] = useState("OPERATORE");

  // v6.1.1: Stato per modifica riga
  const [rigaInModifica, setRigaInModifica] = useState(null);
  const [formModifica, setFormModifica] = useState({});
  const [savingModifica, setSavingModifica] = useState(false);

  // v6.1.1: Stato per tracciato generato
  const [tracciatoGenerato, setTracciatoGenerato] = useState(null);
  const [validando, setValidando] = useState(false);

  // Caricamento dati
  const loadData = useCallback(async () => {
    if (!ordineId) return;
    try {
      setLoading(true);
      setError(null);

      const [ordineRes, righeRes, statoRes] = await Promise.all([
        ordiniApi.getDetail(ordineId),
        ordiniApi.getRighe(ordineId),
        ordiniApi.getStatoRighe(ordineId),
      ]);

      if (ordineRes.success) setOrdine(ordineRes.data);
      if (righeRes.success) setRighe(righeRes.data || []);
      if (statoRes.success) setStatoRighe(statoRes);
    } catch (err) {
      setError(err.message || "Errore caricamento");
    } finally {
      setLoading(false);
    }
  }, [ordineId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Conferma singola riga
  const handleConfermaRiga = async (idDettaglio) => {
    setActionLoading(idDettaglio);
    try {
      const res = await ordiniApi.confermaRiga(
        ordineId,
        idDettaglio,
        operatore
      );

      if (res.success) {
        setRighe((prev) =>
          prev.map((r) =>
            r.id_dettaglio === idDettaglio
              ? { ...r, stato_riga: "CONFERMATO", confermato_da: operatore }
              : r
          )
        );
        loadData();
      } else if (res.richiede_supervisione) {
        if (res.id_supervisione) {
          onNavigateToSupervisione(res.id_supervisione, ordineId);
        } else {
          const supRes = await ordiniApi.inviaASupervisione(
            ordineId,
            idDettaglio,
            operatore
          );
          if (supRes.success) {
            onNavigateToSupervisione(supRes.id_supervisione, ordineId);
          }
        }
      }
    } catch (err) {
      alert("Errore: " + (err.response?.data?.detail || err.message));
    } finally {
      setActionLoading(null);
    }
  };

  // Conferma tutte le righe
  const handleConfermaTutto = async () => {
    if (!confirm("Confermare tutte le righe confermabili?")) return;

    setActionLoading("all");
    try {
      const res = await ordiniApi.confermaOrdineCompleto(ordineId, operatore);

      if (res.success) {
        alert(
          `✅ ${res.righe_confermate} righe confermate` +
            (res.righe_bloccate?.length > 0
              ? `\n⚠️ ${res.righe_bloccate.length} righe richiedono supervisione`
              : "")
        );
        loadData();
      }
    } catch (err) {
      alert("Errore: " + (err.response?.data?.detail || err.message));
    } finally {
      setActionLoading(null);
    }
  };

  // Click su riga espositore/anomala → supervisione
  const handleRigaClick = async (riga) => {
    if (riga.richiede_supervisione && riga.stato_riga !== "CONFERMATO") {
      if (riga.id_supervisione) {
        onNavigateToSupervisione(riga.id_supervisione, ordineId);
      } else {
        try {
          const res = await ordiniApi.inviaASupervisione(
            ordineId,
            riga.id_dettaglio,
            operatore
          );
          if (res.success) {
            onNavigateToSupervisione(res.id_supervisione, ordineId);
          }
        } catch (err) {
          alert("Errore: " + err.message);
        }
      }
    }
  };

  // v6.1.1: Apri modale modifica riga
  const handleApriModifica = (riga) => {
    setRigaInModifica(riga);
    setFormModifica({
      codice_aic: riga.codice_aic || "",
      descrizione: riga.descrizione || "",
      q_venduta: riga.q_venduta || 0,
      q_sconto_merce: riga.q_sconto_merce || 0,
      q_omaggio: riga.q_omaggio || 0,
      prezzo_netto: riga.prezzo_netto || 0,
    });
  };

  // v6.1.1: Salva modifiche riga
  const handleSalvaModifica = async () => {
    if (!rigaInModifica) return;
    setSavingModifica(true);
    try {
      const res = await ordiniApi.modificaRiga(
        ordineId,
        rigaInModifica.id_dettaglio,
        operatore,
        formModifica
      );
      if (res.success) {
        // Aggiorna riga localmente
        setRighe((prev) =>
          prev.map((r) =>
            r.id_dettaglio === rigaInModifica.id_dettaglio
              ? { ...r, ...formModifica }
              : r
          )
        );
        setRigaInModifica(null);
        loadData(); // Ricarica per dati aggiornati
      }
    } catch (err) {
      alert(
        "Errore salvataggio: " + (err.response?.data?.detail || err.message)
      );
    } finally {
      setSavingModifica(false);
    }
  };

  // v6.1.1: Valida ordine e genera tracciato
  // v6.1.2: Genera tracciato solo per righe confermate
  const [statisticheExport, setStatisticheExport] = useState(null);

  const handleValidaEGenera = async () => {
    // Conta righe confermate
    const righeConfermate = righe.filter(
      (r) =>
        r.stato_riga === "CONFERMATO" || r.stato_riga === "PARZIALMENTE_ESP"
    ).length;
    if (righeConfermate === 0) {
      alert(
        "⚠️ Nessuna riga confermata!\n\nConferma prima le righe che vuoi includere nel tracciato."
      );
      return;
    }

    if (
      !confirm(
        `Generare tracciato per ${righeConfermate} righe confermate?\n\nLe righe non confermate rimarranno disponibili per esportazioni successive.`
      )
    )
      return;

    setValidando(true);
    try {
      const res = await ordiniApi.validaEGeneraTracciato(ordineId, operatore);
      if (res.success) {
        setTracciatoGenerato(res.tracciato);
        setStatisticheExport(res.statistiche);
        setOrdine((prev) => ({ ...prev, stato: res.stato }));

        // Messaggio dettagliato
        const stats = res.statistiche || {};
        let msg = `✅ Tracciato generato!\n\n`;
        msg += `📊 Righe esportate: ${stats.righe_esportate || 0}\n`;
        msg += `   ├ Complete: ${stats.righe_complete || 0}\n`;
        msg += `   └ Parziali: ${stats.righe_parziali || 0}\n\n`;
        if (stats.righe_non_esportate > 0) {
          msg += `⏳ Righe ancora da esportare: ${stats.righe_non_esportate}`;
        } else {
          msg += `✓ Ordine completamente esportato!`;
        }
        alert(msg);
        loadData();
      }
    } catch (err) {
      const errMsg = err.response?.data?.detail || err.message;
      if (errMsg.includes("Nessuna riga confermata")) {
        alert(
          "⚠️ Nessuna riga confermata da esportare.\n\nConferma prima le righe desiderate usando il bottone ✓ Conferma."
        );
      } else {
        alert("Errore generazione: " + errMsg);
      }
    } finally {
      setValidando(false);
    }
  };

  // Helper: stato riga badge
  const getStatoRigaBadge = (riga) => {
    const stati = {
      ESTRATTO: {
        bg: "bg-slate-100",
        text: "text-slate-600",
        label: "○ Da confermare",
      },
      IN_SUPERVISIONE: {
        bg: "bg-orange-100",
        text: "text-orange-700",
        label: "⏳ In Supervisione",
      },
      SUPERVISIONATO: {
        bg: "bg-blue-100",
        text: "text-blue-700",
        label: "✓ Supervisionato",
      },
      CONFERMATO: {
        bg: "bg-emerald-100",
        text: "text-emerald-700",
        label: "✓ Pronto Export",
      },
      IN_TRACCIATO: {
        bg: "bg-purple-100",
        text: "text-purple-700",
        label: "📋 In Tracciato",
      },
      ESPORTATO: {
        bg: "bg-green-200",
        text: "text-green-800",
        label: "✓✓ Esportato",
      },
      PARZIALMENTE_ESP: {
        bg: "bg-amber-100",
        text: "text-amber-700",
        label: "⚡ Parziale",
      },
    };
    const s = stati[riga.stato_riga] || stati["ESTRATTO"];
    return (
      <span
        className={`px-2 py-0.5 text-xs font-medium rounded-full ${s.bg} ${s.text}`}
      >
        {s.label}
      </span>
    );
  };

  // Helper: tipo riga icon
  const getTipoRigaIcon = (riga) => {
    if (riga.tipo_riga === "PARENT_ESPOSITORE" || riga.is_espositore)
      return "🎁";
    if (riga.tipo_riga === "SCONTO_MERCE") return "🏷️";
    if (riga.tipo_riga === "MATERIALE_POP") return "🎀";
    if (riga.is_no_aic) return "⚠️";
    return "📦";
  };

  // Helper: può confermare riga?
  const canConfermaRiga = (riga) => {
    // Già esportata completamente → NO
    if (riga.stato_riga === "ESPORTATO") return false;
    // Già confermata → NO
    if (riga.stato_riga === "CONFERMATO" || riga.stato_riga === "IN_TRACCIATO")
      return false;
    // Richiede supervisione non completata → NO
    if (riga.richiede_supervisione && riga.stato_riga !== "SUPERVISIONATO")
      return false;
    // PARZIALMENTE_ESP → SÌ (può ri-confermare per esportare residuo)
    if (riga.stato_riga === "PARZIALMENTE_ESP") return true;
    return true;
  };

  // Helper: può modificare riga?
  const canModificaRiga = (riga) => {
    // Già esportata completamente → NO
    if (riga.stato_riga === "ESPORTATO") return false;
    return true;
  };

  // Helper: richiede supervisione?
  const needsSupervisione = (riga) => {
    return (
      riga.richiede_supervisione === 1 &&
      riga.stato_riga !== "SUPERVISIONATO" &&
      riga.stato_riga !== "CONFERMATO"
    );
  };

  // Parse espositore metadata
  const parseEspositoreMetadata = (metadata) => {
    if (!metadata) return null;
    try {
      return typeof metadata === "string" ? JSON.parse(metadata) : metadata;
    } catch {
      return null;
    }
  };

  if (loading) return <Loading />;
  if (error)
    return (
      <div className="p-6 text-center">
        <p className="text-red-600 mb-4">{error}</p>
        <Button onClick={loadData}>Riprova</Button>
      </div>
    );
  if (!ordine)
    return (
      <div className="p-6 text-center">
        <p className="text-slate-500 mb-4">Ordine non trovato</p>
        <Button onClick={onBack}>← Torna alla lista</Button>
      </div>
    );

  const righeConfermabili = righe.filter((r) => canConfermaRiga(r)).length;
  const righeBloccate = righe.filter((r) => needsSupervisione(r)).length;

  return (
    <div className="space-y-4">
      {/* Header con back button */}
      <div className="flex items-center gap-4 bg-white rounded-xl p-4 border border-slate-200">
        <button
          onClick={onBack}
          className="p-2 hover:bg-slate-100 rounded-lg text-slate-600"
        >
          ← Indietro
        </button>
        <div className="flex-1">
          <h2 className="text-xl font-bold text-slate-800">
            Ordine {ordine.numero_ordine}
          </h2>
          <p className="text-sm text-slate-500">
            <VendorBadge vendor={ordine.vendor} /> • {ordine.ragione_sociale} •{" "}
            {ordine.citta}
          </p>
        </div>
        <StatusBadge status={ordine.stato} />

        {/* v6.2: Badge data consegna nell'header */}
        {ordine.data_consegna && (
          <div className="ml-2">
            <DeliveryBadge dataConsegna={ordine.data_consegna} />
          </div>
        )}

        {/* Bottone Genera Tracciato v6.1.2 - Disponibile finché ci sono righe da esportare */}
        {ordine.stato !== "ESPORTATO" &&
          (() => {
            const righePronte = righe.filter(
              (r) => r.stato_riga === "CONFERMATO"
            ).length;
            const righeParziali = righe.filter(
              (r) => r.stato_riga === "PARZIALMENTE_ESP"
            ).length;
            const righeEsportabili = righePronte + righeParziali;

            return (
              <button
                onClick={handleValidaEGenera}
                disabled={validando || righeEsportabili === 0}
                className={`px-4 py-2 text-white rounded-lg disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 ${
                  righeEsportabili > 0
                    ? "bg-emerald-600 hover:bg-emerald-700"
                    : "bg-slate-400"
                }`}
                title={
                  righeEsportabili === 0
                    ? "Conferma prima le righe da includere nel tracciato"
                    : `Genera tracciato per ${righeEsportabili} righe`
                }
              >
                {validando ? (
                  "⏳ Generazione..."
                ) : (
                  <>
                    📋 Genera Tracciato
                    {righeEsportabili > 0 && (
                      <span className="px-2 py-0.5 bg-white/20 rounded text-xs">
                        {righeEsportabili} righe
                      </span>
                    )}
                  </>
                )}
              </button>
            );
          })()}
      </div>

      {/* Box Tracciato Generato v6.1.2 */}
      {(tracciatoGenerato ||
        ordine.stato === "VALIDATO" ||
        ordine.stato === "ESPORTATO") && (
        <div
          className={`border rounded-xl p-4 ${
            ordine.stato === "ESPORTATO"
              ? "bg-green-50 border-green-200"
              : "bg-emerald-50 border-emerald-200"
          }`}
        >
          <h3
            className={`font-bold mb-3 flex items-center gap-2 ${
              ordine.stato === "ESPORTATO"
                ? "text-green-800"
                : "text-emerald-800"
            }`}
          >
            {ordine.stato === "ESPORTATO"
              ? "✓✓ Ordine Completamente Esportato"
              : "📋 Tracciato Generato"}
          </h3>

          {/* Statistiche esportazione */}
          {statisticheExport && (
            <div className="mb-3 text-sm grid grid-cols-4 gap-2">
              <div className="bg-white rounded p-2 text-center">
                <div className="text-lg font-bold text-emerald-600">
                  {statisticheExport.righe_esportate}
                </div>
                <div className="text-xs text-slate-500">Esportate</div>
              </div>
              <div className="bg-white rounded p-2 text-center">
                <div className="text-lg font-bold text-green-600">
                  {statisticheExport.righe_complete}
                </div>
                <div className="text-xs text-slate-500">Complete</div>
              </div>
              <div className="bg-white rounded p-2 text-center">
                <div className="text-lg font-bold text-amber-600">
                  {statisticheExport.righe_parziali}
                </div>
                <div className="text-xs text-slate-500">Parziali</div>
              </div>
              <div className="bg-white rounded p-2 text-center">
                <div className="text-lg font-bold text-slate-600">
                  {statisticheExport.righe_non_esportate}
                </div>
                <div className="text-xs text-slate-500">Da esportare</div>
              </div>
            </div>
          )}

          {tracciatoGenerato ? (
            <div className="flex flex-wrap gap-3">
              <button
                onClick={() => {
                  fetch(
                    `${getApiBaseUrl()}${tracciatoGenerato.to_t.download_url}`
                  )
                    .then((res) => res.blob())
                    .then((blob) => {
                      const url = window.URL.createObjectURL(blob);
                      const a = document.createElement("a");
                      a.href = url;
                      a.download = tracciatoGenerato.to_t.filename;
                      a.click();
                      window.URL.revokeObjectURL(url);
                    })
                    .catch((err) => alert("Errore download: " + err.message));
                }}
                className="px-4 py-2 bg-white border border-emerald-300 rounded-lg text-emerald-700 hover:bg-emerald-100 flex items-center gap-2 cursor-pointer"
              >
                📄 Scarica TO_T (Testata)
              </button>
              <button
                onClick={() => {
                  fetch(
                    `${getApiBaseUrl()}${tracciatoGenerato.to_d.download_url}`
                  )
                    .then((res) => res.blob())
                    .then((blob) => {
                      const url = window.URL.createObjectURL(blob);
                      const a = document.createElement("a");
                      a.href = url;
                      a.download = tracciatoGenerato.to_d.filename;
                      a.click();
                      window.URL.revokeObjectURL(url);
                    })
                    .catch((err) => alert("Errore download: " + err.message));
                }}
                className="px-4 py-2 bg-white border border-emerald-300 rounded-lg text-emerald-700 hover:bg-emerald-100 flex items-center gap-2 cursor-pointer"
              >
                📄 Scarica TO_D ({tracciatoGenerato.to_d.num_righe} righe)
              </button>
            </div>
          ) : (
            <p className="text-emerald-600 text-sm">
              {ordine.stato === "ESPORTATO"
                ? "Tutte le righe sono state esportate. Vai alla sezione Tracciati per lo storico."
                : "Ordine validato. Usa la sezione Tracciati per scaricare i file precedenti."}
            </p>
          )}
        </div>
      )}

      {/* Progress Bar Conferma v6.1.2 */}
      {statoRighe && (
        <div className="bg-white rounded-xl p-4 border border-slate-200">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-slate-700">
              Stato Righe Ordine
            </span>
            <span className="text-sm text-slate-500">
              {(statoRighe.per_stato?.esportato || 0) +
                (statoRighe.per_stato?.parzialmente_esp || 0)}{" "}
              esportate, {statoRighe.per_stato?.confermato || 0} pronte /{" "}
              {statoRighe.totale || 0} totali
            </span>
          </div>
          <div className="h-3 bg-slate-100 rounded-full overflow-hidden flex">
            {/* Esportate completamente */}
            <div
              className="bg-green-500 transition-all"
              style={{
                width: `${
                  ((statoRighe.per_stato?.esportato || 0) /
                    (statoRighe.totale || 1)) *
                  100
                }%`,
              }}
              title={`Esportate: ${statoRighe.per_stato?.esportato || 0}`}
            />
            {/* Parzialmente esportate */}
            <div
              className="bg-amber-400 transition-all"
              style={{
                width: `${
                  ((statoRighe.per_stato?.parzialmente_esp || 0) /
                    (statoRighe.totale || 1)) *
                  100
                }%`,
              }}
              title={`Parziali: ${statoRighe.per_stato?.parzialmente_esp || 0}`}
            />
            {/* Confermate pronte */}
            <div
              className="bg-emerald-500 transition-all"
              style={{
                width: `${
                  ((statoRighe.per_stato?.confermato || 0) /
                    (statoRighe.totale || 1)) *
                  100
                }%`,
              }}
              title={`Pronte export: ${statoRighe.per_stato?.confermato || 0}`}
            />
            {/* Supervisionate */}
            <div
              className="bg-blue-500 transition-all"
              style={{
                width: `${
                  ((statoRighe.per_stato?.supervisionato || 0) /
                    (statoRighe.totale || 1)) *
                  100
                }%`,
              }}
              title={`Supervisionate: ${
                statoRighe.per_stato?.supervisionato || 0
              }`}
            />
            {/* In supervisione */}
            <div
              className="bg-orange-400 transition-all"
              style={{
                width: `${
                  ((statoRighe.per_stato?.in_supervisione || 0) /
                    (statoRighe.totale || 1)) *
                  100
                }%`,
              }}
              title={`In supervisione: ${
                statoRighe.per_stato?.in_supervisione || 0
              }`}
            />
          </div>
          <div className="flex flex-wrap gap-3 mt-2 text-xs text-slate-500">
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-green-500"></span>{" "}
              Esportate ({statoRighe.per_stato?.esportato || 0})
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-amber-400"></span>{" "}
              Parziali ({statoRighe.per_stato?.parzialmente_esp || 0})
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-emerald-500"></span>{" "}
              Pronte ({statoRighe.per_stato?.confermato || 0})
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-blue-500"></span>{" "}
              Supervisionate ({statoRighe.per_stato?.supervisionato || 0})
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-orange-400"></span> In
              Supervisione ({statoRighe.per_stato?.in_supervisione || 0})
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-slate-300"></span> Da
              confermare ({statoRighe.per_stato?.estratto || 0})
            </span>
          </div>
        </div>
      )}

      {/* Alert righe bloccate */}
      {righeBloccate > 0 && (
        <div className="bg-orange-50 border border-orange-200 rounded-xl p-4 flex items-center gap-3">
          <span className="text-2xl">⚠️</span>
          <div>
            <p className="font-medium text-orange-800">
              {righeBloccate}{" "}
              {righeBloccate === 1 ? "riga richiede" : "righe richiedono"}{" "}
              supervisione
            </p>
            <p className="text-sm text-orange-600">
              Clicca sulla riga per aprire la supervisione
            </p>
          </div>
        </div>
      )}

      {/* Tabella Righe */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <div className="p-3 bg-slate-50 border-b flex items-center justify-between">
          <span className="font-medium text-slate-700">
            {righe.length} righe
          </span>
          <div className="flex gap-2">
            <Button
              variant="success"
              size="sm"
              onClick={handleConfermaTutto}
              disabled={righeConfermabili === 0 || actionLoading === "all"}
            >
              {actionLoading === "all" ? "⏳" : "✅"} Conferma Tutto (
              {righeConfermabili})
            </Button>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-slate-600 text-xs">
              <tr>
                <th className="p-2 text-center w-10">#</th>
                <th className="p-2 text-center w-10">Tipo</th>
                <th className="p-2 text-left">AIC</th>
                <th className="p-2 text-left">Descrizione</th>
                {/* v6.2: NUOVA COLONNA CONSEGNA */}
                <th className="p-2 text-left">📅 Consegna</th>
                <th className="p-2 text-right">Q.Ord</th>
                <th className="p-2 text-right">Q.Exp</th>
                <th className="p-2 text-right">Q.Res</th>
                <th className="p-2 text-right">Prezzo</th>
                <th className="p-2 text-center">Stato</th>
                <th className="p-2 text-center w-32">Azioni</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {righe.map((riga) => {
                const isEspositore =
                  riga.is_espositore || riga.tipo_riga === "PARENT_ESPOSITORE";
                const needsSuper = needsSupervisione(riga);
                const canConferma = canConfermaRiga(riga);
                const canModifica = canModificaRiga(riga);
                const isLoading = actionLoading === riga.id_dettaglio;
                const metadata = parseEspositoreMetadata(
                  riga.espositore_metadata
                );

                // v6.1.2: Calcola quantità per display
                const qOriginale = riga.q_originale || riga.q_venduta || 0;
                const qEsportata = riga.q_esportata || 0;
                const qResidua = riga.q_residua || qOriginale - qEsportata;
                const isParziale = riga.stato_riga === "PARZIALMENTE_ESP";
                const isEsportato = riga.stato_riga === "ESPORTATO";

                // v6.2: Highlighting per urgenza consegna
                const deliveryHighlight = getRowHighlightClass(
                  riga.data_consegna
                );

                return (
                  <tr
                    key={riga.id_dettaglio}
                    className={`
                      hover:bg-slate-50 transition-colors
                      ${needsSuper ? "bg-orange-50 cursor-pointer" : ""}
                      ${
                        riga.stato_riga === "CONFERMATO"
                          ? "bg-emerald-50/50"
                          : ""
                      }
                      ${isEsportato ? "bg-green-50/30 opacity-75" : ""}
                      ${isParziale ? "bg-amber-50/50" : ""}
                      ${deliveryHighlight}
                    `}
                    onClick={() => needsSuper && handleRigaClick(riga)}
                  >
                    <td className="p-2 text-center text-slate-400">
                      {riga.n_riga}
                    </td>
                    <td
                      className="p-2 text-center text-lg"
                      title={riga.tipo_riga}
                    >
                      {getTipoRigaIcon(riga)}
                    </td>
                    <td className="p-2 font-mono text-xs">
                      {riga.codice_aic || "-"}
                      {riga.codice_originale &&
                        riga.codice_originale !== riga.codice_aic && (
                          <span className="text-slate-400 ml-1">
                            ({riga.codice_originale})
                          </span>
                        )}
                    </td>
                    <td className="p-2 max-w-[250px]">
                      <div className="truncate">{riga.descrizione}</div>
                      {isEspositore && metadata && (
                        <div className="mt-1 text-xs">
                          <span
                            className={`px-1.5 py-0.5 rounded ${
                              metadata.pezzi_trovati ===
                              metadata.pezzi_attesi_totali
                                ? "bg-emerald-100 text-emerald-700"
                                : "bg-orange-100 text-orange-700"
                            }`}
                          >
                            📊 {metadata.pezzi_trovati}/
                            {metadata.pezzi_attesi_totali} pz
                          </span>
                          <span className="ml-2 text-slate-400">
                            {metadata.num_child} child • €
                            {metadata.valore_netto_child?.toFixed(2)}
                          </span>
                        </div>
                      )}
                      {/* Indicatore esportazioni */}
                      {riga.num_esportazioni > 0 && (
                        <div className="mt-1 text-xs text-slate-400">
                          📤 {riga.num_esportazioni}x esportato
                        </div>
                      )}
                    </td>
                    {/* v6.2: NUOVA CELLA CONSEGNA */}
                    <td className="p-2">
                      <DeliveryBadge dataConsegna={riga.data_consegna} />
                    </td>
                    {/* v6.1.2: Colonne quantità esportazione */}
                    <td className="p-2 text-right font-mono">
                      <span
                        className={
                          isParziale || isEsportato ? "text-slate-400" : ""
                        }
                      >
                        {qOriginale}
                      </span>
                      {riga.q_sconto_merce > 0 && (
                        <span className="text-amber-600 ml-1 text-xs">
                          +{riga.q_sconto_merce}🎁
                        </span>
                      )}
                    </td>
                    <td className="p-2 text-right font-mono">
                      {qEsportata > 0 ? (
                        <span className="text-green-600">{qEsportata}</span>
                      ) : (
                        <span className="text-slate-300">-</span>
                      )}
                    </td>
                    <td className="p-2 text-right font-mono">
                      {isEsportato ? (
                        <span className="text-green-600">✓</span>
                      ) : qResidua > 0 ? (
                        <span
                          className={
                            isParziale
                              ? "text-amber-600 font-bold"
                              : "text-slate-600"
                          }
                        >
                          {qResidua}
                        </span>
                      ) : (
                        <span className="text-slate-300">-</span>
                      )}
                    </td>
                    <td className="p-2 text-right font-mono">
                      {riga.prezzo_netto > 0
                        ? `€${riga.prezzo_netto.toFixed(2)}`
                        : "-"}
                    </td>
                    <td className="p-2 text-center">
                      {getStatoRigaBadge(riga)}
                    </td>
                    <td
                      className="p-2 text-center space-x-1"
                      onClick={(e) => e.stopPropagation()}
                    >
                      {/* Bottone Modifica - disabilitato se esportato */}
                      {canModifica && (
                        <button
                          onClick={() => handleApriModifica(riga)}
                          className="px-2 py-1 text-xs bg-slate-100 text-slate-700 rounded hover:bg-slate-200"
                          title="Modifica riga"
                        >
                          ✏️
                        </button>
                      )}

                      {needsSuper ? (
                        <button
                          onClick={() => handleRigaClick(riga)}
                          className="px-2 py-1 text-xs bg-orange-100 text-orange-700 rounded hover:bg-orange-200"
                        >
                          👁️ Supervisiona
                        </button>
                      ) : canConferma ? (
                        <button
                          onClick={() => handleConfermaRiga(riga.id_dettaglio)}
                          disabled={isLoading}
                          className={`px-2 py-1 text-xs rounded disabled:opacity-50 ${
                            isParziale
                              ? "bg-amber-100 text-amber-700 hover:bg-amber-200"
                              : "bg-emerald-100 text-emerald-700 hover:bg-emerald-200"
                          }`}
                        >
                          {isLoading ? "⏳" : "✓"}{" "}
                          {isParziale ? "Conf.Residuo" : "Conferma"}
                        </button>
                      ) : isEsportato ? (
                        <span className="text-green-600 text-xs font-medium">
                          ✓✓ Completato
                        </span>
                      ) : (
                        <span className="text-slate-400 text-xs">
                          {riga.stato_riga === "CONFERMATO" ? "✓ Pronto" : "-"}
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Info Box v6.1.2 */}
      <div className="bg-blue-50 rounded-xl p-4 text-sm text-blue-800">
        <h4 className="font-bold mb-2">ℹ️ Gestione Esportazioni Parziali</h4>
        <ul className="list-disc list-inside space-y-1 text-xs">
          <li>
            <strong>Q.Ord</strong>: Quantità originale dall'ordine PDF
          </li>
          <li>
            <strong>Q.Exp</strong>: Quantità già inclusa in tracciati precedenti
          </li>
          <li>
            <strong>Q.Res</strong>: Quantità residua ancora da esportare
          </li>
          <li>
            <strong>✓ Conferma</strong>: Rende la riga pronta per l'export
          </li>
          <li>
            <strong>⚡ Parziale</strong>: Riga esportata parzialmente - conferma
            il residuo per esportare
          </li>
          <li>
            <strong>✓✓ Esportato</strong>: Riga completamente esportata (non
            modificabile)
          </li>
          <li>
            <strong>Genera Tracciato</strong>: Esporta SOLO le righe confermate
            con le quantità correnti
          </li>
        </ul>
      </div>

      {/* v6.2: Legenda Urgenze */}
      <div className="bg-white rounded-xl border border-slate-200 p-3">
        <h4 className="text-xs font-semibold text-slate-600 mb-2">
          📌 Legenda Urgenze Consegna
        </h4>
        <div className="flex gap-4 text-xs">
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 bg-red-100 border-l-4 border-red-500 rounded"></span>
            <span className="text-slate-600">🔴 Scaduto</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 bg-amber-100 border-l-4 border-amber-400 rounded"></span>
            <span className="text-slate-600">🟠 Urgente (≤3 gg lav)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="flex items-center gap-1 text-emerald-600">🟢</span>
            <span className="text-slate-600">Ordinario</span>
          </div>
        </div>
      </div>

      {/* Modale Modifica Riga v6.1.1 */}
      {rigaInModifica && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg mx-4">
            <div className="p-4 border-b border-slate-200 flex justify-between items-center">
              <h3 className="font-bold text-lg">
                ✏️ Modifica Riga #{rigaInModifica.n_riga}
              </h3>
              <button
                onClick={() => setRigaInModifica(null)}
                className="text-slate-400 hover:text-slate-600 text-xl"
              >
                ✕
              </button>
            </div>

            <div className="p-4 space-y-4">
              {/* Codice AIC */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Codice AIC
                </label>
                <input
                  type="text"
                  value={formModifica.codice_aic}
                  onChange={(e) =>
                    setFormModifica({
                      ...formModifica,
                      codice_aic: e.target.value,
                    })
                  }
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-mono"
                  placeholder="Es: 500419116"
                />
              </div>

              {/* Descrizione */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Descrizione
                </label>
                <input
                  type="text"
                  value={formModifica.descrizione}
                  onChange={(e) =>
                    setFormModifica({
                      ...formModifica,
                      descrizione: e.target.value,
                    })
                  }
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Descrizione prodotto"
                />
              </div>

              {/* Quantità */}
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    Q.tà Venduta
                  </label>
                  <input
                    type="number"
                    value={formModifica.q_venduta}
                    onChange={(e) =>
                      setFormModifica({
                        ...formModifica,
                        q_venduta: parseInt(e.target.value) || 0,
                      })
                    }
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-right"
                    min="0"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    Q.tà SC.Merce
                  </label>
                  <input
                    type="number"
                    value={formModifica.q_sconto_merce}
                    onChange={(e) =>
                      setFormModifica({
                        ...formModifica,
                        q_sconto_merce: parseInt(e.target.value) || 0,
                      })
                    }
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-right"
                    min="0"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    Q.tà Omaggio
                  </label>
                  <input
                    type="number"
                    value={formModifica.q_omaggio}
                    onChange={(e) =>
                      setFormModifica({
                        ...formModifica,
                        q_omaggio: parseInt(e.target.value) || 0,
                      })
                    }
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-right"
                    min="0"
                  />
                </div>
              </div>

              {/* Prezzo */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Prezzo Netto €
                </label>
                <input
                  type="number"
                  step="0.01"
                  value={formModifica.prezzo_netto}
                  onChange={(e) =>
                    setFormModifica({
                      ...formModifica,
                      prezzo_netto: parseFloat(e.target.value) || 0,
                    })
                  }
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-right font-mono"
                  min="0"
                />
              </div>
            </div>

            <div className="p-4 border-t border-slate-200 flex justify-end gap-2">
              <button
                onClick={() => setRigaInModifica(null)}
                className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-lg"
              >
                Annulla
              </button>
              <button
                onClick={handleSalvaModifica}
                disabled={savingModifica}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {savingModifica ? "⏳ Salvataggio..." : "💾 Salva Modifiche"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// ============================================
// SUPERVISIONE PAGE v6.1
// Gestione supervisione espositori e criteri ML
// Con supporto ritorno a ordine
// ============================================
const SupervisionePage = ({
  supervisioneId,
  returnToOrdine,
  onReturnToOrdine,
}) => {
  const [supervisioni, setSupervisioni] = useState([]);
  const [criteri, setCriteri] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("pending");
  const [operatore, setOperatore] = useState("admin");

  // Carica dati
  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [pendingRes, criteriRes, statsRes] = await Promise.all([
        supervisioneApi.getPending(),
        supervisioneApi.getCriteriOrdinari(),
        supervisioneApi.getCriteriStats(),
      ]);
      setSupervisioni(pendingRes.supervisioni || []);
      setCriteri(criteriRes.criteri || []);
      setStats(statsRes);
    } catch (err) {
      console.error("Errore caricamento supervisione:", err);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // v6.1: Azioni con supporto ritorno a ordine
  const handleApprova = async (id) => {
    if (!confirm("Confermi approvazione?")) return;
    try {
      // Se siamo in modalità ritorno a ordine, usa endpoint specifico
      if (returnToOrdine && onReturnToOrdine) {
        await supervisioneApi.approvaETorna(id, operatore);
        onReturnToOrdine(returnToOrdine);
      } else {
        await supervisioneApi.approva(id, operatore);
        loadData();
      }
    } catch (err) {
      alert("Errore: " + (err.response?.data?.detail || err.message));
    }
  };

  const handleRifiuta = async (id) => {
    const note = prompt("Motivo del rifiuto (obbligatorio):");
    if (!note) return;
    try {
      await supervisioneApi.rifiuta(id, operatore, note);
      if (returnToOrdine && onReturnToOrdine) {
        onReturnToOrdine(returnToOrdine);
      } else {
        loadData();
      }
    } catch (err) {
      alert("Errore: " + (err.response?.data?.detail || err.message));
    }
  };

  // v6.1: Lascia sospeso e torna
  const handleLasciaSospeso = async (id) => {
    if (returnToOrdine && onReturnToOrdine) {
      try {
        await supervisioneApi.lasciaSospeso(id, operatore);
        onReturnToOrdine(returnToOrdine);
      } catch (err) {
        alert("Errore: " + (err.response?.data?.detail || err.message));
      }
    }
  };

  const handleResetPattern = async (signature) => {
    if (!confirm("Reset contatore pattern? L'apprendimento ripartirà da zero."))
      return;
    try {
      await supervisioneApi.resetPattern(signature, operatore);
      loadData();
    } catch (err) {
      alert("Errore: " + (err.response?.data?.detail || err.message));
    }
  };

  return (
    <div className="p-4 space-y-4">
      {/* v6.1: Header con back se in modalità embedded */}
      {returnToOrdine && (
        <div className="flex items-center gap-2 p-3 bg-blue-50 rounded-xl border border-blue-200">
          <button
            onClick={() => onReturnToOrdine(returnToOrdine)}
            className="flex items-center gap-2 text-blue-700 hover:text-blue-900 font-medium"
          >
            ← Torna all'ordine
          </button>
          <span className="text-sm text-blue-600">
            Supervisione riga da ordine #{returnToOrdine}
          </span>
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-800">
            👁️ Supervisione Espositori
          </h1>
          <p className="text-sm text-slate-500">
            Gestione anomalie e criteri ML
          </p>
        </div>
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={operatore}
            onChange={(e) => setOperatore(e.target.value)}
            placeholder="Operatore"
            className="px-2 py-1 text-sm border rounded"
          />
          <Button onClick={loadData} size="sm">
            🔄 Aggiorna
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-4 gap-3">
          <StatCard
            title="In Attesa"
            value={supervisioni.length}
            icon="⏳"
            color="bg-orange-100"
          />
          <StatCard
            title="Pattern Ordinari"
            value={stats.pattern_ordinari}
            icon="🧠"
            color="bg-emerald-100"
          />
          <StatCard
            title="In Apprendimento"
            value={stats.pattern_in_apprendimento}
            icon="📈"
            color="bg-blue-100"
          />
          <StatCard
            title="Auto Oggi"
            value={stats.applicazioni_automatiche_oggi}
            icon="⚡"
            color="bg-purple-100"
          />
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-2 border-b border-slate-200">
        {[
          { id: "pending", label: "⏳ In Attesa", count: supervisioni.length },
          {
            id: "criteri",
            label: "🧠 Criteri Ordinari",
            count: criteri.length,
          },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-3 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === tab.id
                ? "border-blue-500 text-blue-600"
                : "border-transparent text-slate-500 hover:text-slate-700"
            }`}
          >
            {tab.label}
            {tab.count > 0 && (
              <span className="ml-1 px-1.5 py-0.5 text-xs bg-slate-100 rounded-full">
                {tab.count}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Content */}
      {loading ? (
        <div className="flex justify-center py-8">
          <div className="animate-spin w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full"></div>
        </div>
      ) : (
        <>
          {/* Tab: Supervisioni Pending */}
          {activeTab === "pending" && (
            <div className="bg-white rounded-xl border">
              {supervisioni.length === 0 ? (
                <div className="p-8 text-center text-slate-500">
                  ✅ Nessuna supervisione in attesa
                </div>
              ) : (
                <table className="w-full text-sm">
                  <thead className="bg-slate-50">
                    <tr>
                      <th className="px-3 py-2 text-left">Ordine</th>
                      <th className="px-3 py-2 text-left">Vendor</th>
                      <th className="px-3 py-2 text-left">Anomalia</th>
                      <th className="px-3 py-2 text-left">Espositore</th>
                      <th className="px-3 py-2 text-center">Pezzi</th>
                      <th className="px-3 py-2 text-center">Pattern</th>
                      <th className="px-3 py-2 text-right">Azioni</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {supervisioni.map((sup) => (
                      <tr
                        key={sup.id_supervisione}
                        className="hover:bg-slate-50"
                      >
                        <td className="px-3 py-2">
                          <span className="font-mono text-xs">
                            {sup.numero_ordine}
                          </span>
                          <br />
                          <span className="text-xs text-slate-500">
                            {sup.ragione_sociale}
                          </span>
                        </td>
                        <td className="px-3 py-2">
                          <VendorBadge vendor={sup.vendor} />
                        </td>
                        <td className="px-3 py-2">
                          <span className="font-mono text-xs text-red-600">
                            {sup.codice_anomalia}
                          </span>
                        </td>
                        <td className="px-3 py-2">
                          <span className="text-xs">
                            {sup.descrizione_espositore}
                          </span>
                        </td>
                        <td className="px-3 py-2 text-center">
                          <span className="font-mono text-xs">
                            {sup.pezzi_trovati}/{sup.pezzi_attesi}
                          </span>
                        </td>
                        <td className="px-3 py-2 text-center">
                          <span className="font-mono text-xs text-slate-500">
                            {sup.count_pattern || 0}/5
                          </span>
                          {sup.pattern_ordinario ? (
                            <span className="ml-1 text-emerald-500">🧠</span>
                          ) : null}
                        </td>
                        <td className="px-3 py-2 text-right space-x-1">
                          <Button
                            size="xs"
                            variant="primary"
                            onClick={() => handleApprova(sup.id_supervisione)}
                          >
                            ✓ {returnToOrdine ? "Approva e Torna" : "Approva"}
                          </Button>
                          <Button
                            size="xs"
                            variant="danger"
                            onClick={() => handleRifiuta(sup.id_supervisione)}
                          >
                            ✕
                          </Button>
                          {returnToOrdine && (
                            <Button
                              size="xs"
                              variant="secondary"
                              onClick={() =>
                                handleLasciaSospeso(sup.id_supervisione)
                              }
                            >
                              ⏸️ Sospendi
                            </Button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}

          {/* Tab: Criteri Ordinari */}
          {activeTab === "criteri" && (
            <div className="bg-white rounded-xl border">
              {criteri.length === 0 ? (
                <div className="p-8 text-center text-slate-500">
                  📊 Nessun criterio ordinario ancora. Approva 5 volte lo stesso
                  pattern per promuoverlo.
                </div>
              ) : (
                <table className="w-full text-sm">
                  <thead className="bg-slate-50">
                    <tr>
                      <th className="px-3 py-2 text-left">Pattern</th>
                      <th className="px-3 py-2 text-left">Vendor</th>
                      <th className="px-3 py-2 text-left">Anomalia</th>
                      <th className="px-3 py-2 text-left">Descrizione</th>
                      <th className="px-3 py-2 text-center">Count</th>
                      <th className="px-3 py-2 text-center">Promosso</th>
                      <th className="px-3 py-2 text-right">Azioni</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {criteri.map((crit) => (
                      <tr
                        key={crit.pattern_signature}
                        className="hover:bg-slate-50"
                      >
                        <td className="px-3 py-2">
                          <span className="font-mono text-xs">
                            {crit.pattern_signature}
                          </span>
                        </td>
                        <td className="px-3 py-2">
                          <VendorBadge vendor={crit.vendor} />
                        </td>
                        <td className="px-3 py-2">
                          <span className="font-mono text-xs">
                            {crit.codice_anomalia}
                          </span>
                        </td>
                        <td className="px-3 py-2">
                          <span className="text-xs text-slate-600">
                            {crit.pattern_descrizione}
                          </span>
                        </td>
                        <td className="px-3 py-2 text-center">
                          <span className="font-mono font-bold text-emerald-600">
                            {crit.count_approvazioni}
                          </span>
                        </td>
                        <td className="px-3 py-2 text-center text-xs text-slate-500">
                          {crit.data_promozione?.split("T")[0] || "-"}
                        </td>
                        <td className="px-3 py-2 text-right">
                          <Button
                            size="xs"
                            variant="danger"
                            onClick={() =>
                              handleResetPattern(crit.pattern_signature)
                            }
                          >
                            Reset
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}
        </>
      )}

      {/* Info Box */}
      <div className="bg-blue-50 rounded-xl p-4 text-sm text-blue-800">
        <h4 className="font-bold mb-2">ℹ️ Come funziona il Machine Learning</h4>
        <ul className="list-disc list-inside space-y-1 text-xs">
          <li>Ogni anomalia espositore genera un "pattern signature" unico</li>
          <li>Quando approvi un'anomalia, il contatore del pattern aumenta</li>
          <li>
            Dopo <strong>5 approvazioni</strong> dello stesso pattern, diventa
            "ordinario"
          </li>
          <li>
            I pattern ordinari vengono applicati{" "}
            <strong>automaticamente</strong>
          </li>
          <li>Se rifiuti un'anomalia, il contatore si resetta a zero</li>
        </ul>
      </div>
    </div>
  );
};

// ============================================
// MAIN APP v6.2
// ============================================

export default function App() {
  console.log("🚀 App rendering...");
  const [page, setPage] = useState("dashboard");
  const [pageParams, setPageParams] = useState({});
  const [notif, setNotif] = useState(false);

  // v6.2: Stato autenticazione
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [currentUser, setCurrentUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);

  // v6.2: Verifica token all'avvio
  useEffect(() => {
    const checkAuth = async () => {
      if (authApi.isAuthenticated()) {
        try {
          const user = await authApi.getMe();
          setCurrentUser(user);
          setIsAuthenticated(true);
        } catch (err) {
          // Token invalido
          await authApi.logout();
        }
      }
      setAuthLoading(false);
    };
    checkAuth();
  }, []);

  // v6.2: Verifica token all'avvio
  useEffect(() => {
    const checkAuth = async () => {
      console.log("🔍 Checking auth..."); // AGGIUNGI
      if (authApi.isAuthenticated()) {
        console.log("📌 Token found, verifying..."); // AGGIUNGI
        try {
          const user = await authApi.getMe();
          console.log("✅ User:", user); // AGGIUNGI
          setCurrentUser(user);
          setIsAuthenticated(true);
        } catch (err) {
          console.log("❌ Token invalid:", err); // AGGIUNGI
          await authApi.logout();
        }
      } else {
        console.log("📌 No token"); // AGGIUNGI
      }
      setAuthLoading(false);
    };
    checkAuth();
  }, []);

  // v6.2: Handler login
  const handleLogin = (user) => {
    setCurrentUser(user);
    setIsAuthenticated(true);
    setPage("dashboard");
  };

  // v6.2: Handler logout
  const handleLogout = async () => {
    await authApi.logout();
    setCurrentUser(null);
    setIsAuthenticated(false);
    setPage("dashboard");
  };

  // v6.1: Navigazione con parametri
  const navigateTo = (pageName, params = {}) => {
    setPage(pageName);
    setPageParams(params);
  };

  const renderPage = () => {
    switch (page) {
      case "upload":
        return <UploadPage />;
      case "database":
        return (
          <DatabasePage
            onOpenOrdine={(id) => navigateTo("ordine-detail", { ordineId: id })}
          />
        );
      case "ordine-detail":
        return (
          <OrderDetailPage
            ordineId={pageParams.ordineId}
            onBack={() => navigateTo("database")}
            onNavigateToSupervisione={(idSup, idOrdine) =>
              navigateTo("supervisione", {
                supervisioneId: idSup,
                returnToOrdine: idOrdine,
              })
            }
          />
        );
      case "lookup":
        return <LookupPage />;
      case "supervisione":
        return (
          <SupervisionePage
            supervisioneId={pageParams.supervisioneId}
            returnToOrdine={pageParams.returnToOrdine}
            onReturnToOrdine={(idOrdine) =>
              navigateTo("ordine-detail", { ordineId: idOrdine })
            }
          />
        );
      case "tracciati":
        return <TracciatiPage />;
      case "settings":
        return <SettingsPage />;
      case "utenti":
        return <UtentiPage currentUser={currentUser} />;
      default:
        return <DashboardPage onNavigate={navigateTo} />;
    }
  };

  // Titolo pagina dinamico
  const getPageTitle = () => {
    if (page === "ordine-detail") return "Dettaglio Ordine";
    return menu.find((m) => m.id === page)?.label || "Dashboard";
  };

  // v6.2: Loading iniziale verifica auth
  if (authLoading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="animate-spin w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full"></div>
      </div>
    );
  }

  // v6.2: Pagina login se non autenticato
  if (!isAuthenticated) {
    console.log("🔐 Showing LoginPage");
    return <LoginPage onLogin={handleLogin} />;
  }

  // v6.2: Menu dinamico basato su ruolo
  const getMenu = () => {
    const baseMenu = [
      { id: "dashboard", label: "Dashboard", icon: "📊" },
      { id: "upload", label: "Upload PDF", icon: "📁" },
      { id: "database", label: "Database", icon: "🗄️" },
      { id: "lookup", label: "Lookup", icon: "🔍" },
      { id: "supervisione", label: "Supervisione", icon: "👁️" },
      { id: "tracciati", label: "Tracciati", icon: "📋" },
      { id: "settings", label: "Impostazioni", icon: "⚙️" },
    ];

    if (
      currentUser?.ruolo === "admin" ||
      currentUser?.ruolo === "supervisore"
    ) {
      baseMenu.push({ id: "utenti", label: "Utenti", icon: "👥" });
    }

    return baseMenu;
  };

  const menu = getMenu();

  return (
    <div className="min-h-screen bg-slate-50 flex">
      {/* Sidebar */}
      <aside className="fixed left-0 top-0 h-full w-48 bg-slate-900 text-white flex flex-col z-50">
        <div className="p-3 border-b border-slate-700">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center text-xs font-bold">
              TO
            </div>
            <div>
              <h1 className="font-bold text-sm">EXTRACTOR_TO</h1>
              <p className="text-xs text-slate-400">v6.2</p>
            </div>
          </div>
        </div>
        <nav className="flex-1 p-2 space-y-0.5">
          {menu.map((item) => (
            <button
              key={item.id}
              onClick={() => setPage(item.id)}
              className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${
                page === item.id
                  ? "bg-blue-600"
                  : "text-slate-400 hover:bg-slate-800 hover:text-white"
              }`}
            >
              <span>{item.icon}</span>
              <span>{item.label}</span>
            </button>
          ))}
        </nav>

        {/* v6.2: User info e logout */}
        <div className="p-2 border-t border-slate-700">
          <div className="bg-slate-800 rounded-lg p-2">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-7 h-7 bg-blue-600 rounded-full flex items-center justify-center text-white text-xs font-bold">
                {currentUser?.nome?.charAt(0) || "U"}
                {currentUser?.cognome?.charAt(0) || ""}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium truncate">
                  {currentUser?.nome} {currentUser?.cognome}
                </p>
                <p className="text-xs text-slate-400 capitalize">
                  {currentUser?.ruolo}
                </p>
              </div>
            </div>
            <button
              onClick={handleLogout}
              className="w-full px-2 py-1.5 text-xs text-slate-400 hover:text-white hover:bg-slate-700 rounded transition-colors flex items-center justify-center gap-1"
            >
              🚪 Logout
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 ml-48">
        {/* Header */}
        <header className="sticky top-0 bg-white border-b border-slate-200 z-40">
          <div className="flex items-center justify-between px-4 py-2">
            <div>
              <h2 className="text-lg font-bold text-slate-800">
                {getPageTitle()}
              </h2>
              <p className="text-xs text-slate-500">
                {new Date().toLocaleDateString("it-IT", {
                  weekday: "long",
                  day: "numeric",
                  month: "long",
                  year: "numeric",
                })}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setNotif(!notif)}
                className="relative p-1.5 rounded-lg hover:bg-slate-100"
              >
                🔔
                <span className="absolute top-0 right-0 w-2 h-2 bg-red-500 rounded-full"></span>
              </button>
              <div className="flex items-center gap-2 pl-2 border-l border-slate-200">
                <div className="w-7 h-7 bg-blue-600 rounded-full flex items-center justify-center text-white text-xs font-bold">
                  {currentUser?.nome?.charAt(0) || "U"}
                  {currentUser?.cognome?.charAt(0) || ""}
                </div>
                <span className="text-sm text-slate-600">
                  {currentUser?.username}
                </span>
              </div>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <div className="p-4">{renderPage()}</div>
      </main>

      {/* Notifications Panel */}
      {notif && (
        <div className="fixed top-12 right-4 w-64 bg-white rounded-xl shadow-xl border border-slate-200 z-50">
          <div className="p-2 border-b border-slate-100 flex justify-between items-center">
            <span className="font-bold text-sm">Notifiche</span>
            <button
              onClick={() => setNotif(false)}
              className="text-slate-400 hover:text-slate-600"
            >
              ✕
            </button>
          </div>
          <div className="p-2 space-y-1 text-sm">
            <div className="p-2 hover:bg-slate-50 rounded-lg cursor-pointer">
              ⚠️ Anomalie da gestire
            </div>
            <div className="p-2 hover:bg-slate-50 rounded-lg cursor-pointer">
              ✅ Upload completati
            </div>
            <div className="p-2 hover:bg-slate-50 rounded-lg cursor-pointer">
              📋 Tracciati generati
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
