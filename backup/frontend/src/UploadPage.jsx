// =============================================================================
// UPLOAD PAGE - MODERNIZZATA v6.2
// =============================================================================
// Pagina upload PDF con componenti modulari
// Drag & drop, progress, stati, vendor detection
// =============================================================================

import React, { useState, useEffect } from "react";
import { uploadApi, gmailApi } from "./api";
import { Button, StatusBadge, VendorBadge, Loading, ErrorBox } from "./common";

/**
 * Componente UploadPage modernizzato
 *
 * LOGICA IMPLEMENTATIVA:
 * - Drag & drop con visual feedback
 * - Upload progressivo con status tracking
 * - Gestione duplicati e errori
 * - Stats real-time
 * - Console log attività
 *
 * INTERRELAZIONI:
 * - API: uploadApi.uploadPdf(), uploadApi.getStats()
 * - Componenti: Button, StatusBadge, VendorBadge, Loading, ErrorBox
 */
const UploadPage = () => {
  const [files, setFiles] = useState([]);
  const [isDragging, setIsDragging] = useState(false);
  const [stats, setStats] = useState(null);
  const [logs, setLogs] = useState([
    { type: "info", text: "Sistema pronto per upload" },
  ]);
  const [statsLoading, setStatsLoading] = useState(true);

  // Gmail Monitor state
  const [gmailStatus, setGmailStatus] = useState(null);
  const [gmailEmails, setGmailEmails] = useState([]);
  const [gmailLoading, setGmailLoading] = useState(true);
  const [gmailSyncing, setGmailSyncing] = useState(false);
  const [showGmailEmails, setShowGmailEmails] = useState(false);

  // Utility per aggiungere log con timestamp
  const addLog = (type, text) => {
    setLogs((prev) => [
      ...prev,
      {
        type,
        text,
        time: new Date().toLocaleTimeString("it-IT"),
      },
    ]);
  };

  // Carica statistiche all'avvio
  useEffect(() => {
    const loadStats = async () => {
      try {
        const res = await uploadApi.getStats();
        if (res.success) {
          setStats(res.data);
          addLog(
            "info",
            `Stats caricate: ${res.data?.totale || 0} upload totali`
          );
        }
      } catch (err) {
        console.error("Error loading stats:", err);
        addLog("error", "Errore caricamento statistiche");
      } finally {
        setStatsLoading(false);
      }
    };

    loadStats();
  }, []);

  // Carica stato Gmail Monitor
  useEffect(() => {
    const loadGmailStatus = async () => {
      try {
        const res = await gmailApi.getStatus();
        if (res.success) {
          setGmailStatus(res);
          // Aggiorna stato sync se in corso
          if (res.sync_status?.is_running) {
            setGmailSyncing(true);
          }
        }
      } catch (err) {
        console.error("Error loading Gmail status:", err);
      } finally {
        setGmailLoading(false);
      }
    };

    loadGmailStatus();
    // Polling ogni 10 secondi se sync in corso
    const interval = setInterval(() => {
      if (gmailSyncing) loadGmailStatus();
    }, 10000);

    return () => clearInterval(interval);
  }, [gmailSyncing]);

  // Avvia sync Gmail
  const handleGmailSync = async () => {
    try {
      setGmailSyncing(true);
      addLog("info", "Avvio sincronizzazione Gmail...");
      const res = await gmailApi.sync();
      if (res.success) {
        addLog("ok", "Sincronizzazione Gmail avviata in background");
      }
    } catch (err) {
      const msg = err.response?.data?.detail || err.message;
      addLog("error", `Errore sync Gmail: ${msg}`);
      setGmailSyncing(false);
    }
  };

  // Carica email Gmail (solo errori)
  const loadGmailEmails = async () => {
    try {
      const res = await gmailApi.getEmails({ limit: 50, stato: 'ERRORE' });
      if (res.success) {
        setGmailEmails(res.emails || []);
        addLog("info", `Caricate ${res.emails?.length || 0} email con errore`);
      }
    } catch (err) {
      addLog("error", "Errore caricamento email Gmail");
    }
  };

  // Riprova elaborazione email
  const handleRetryEmail = async (id) => {
    try {
      await gmailApi.retryEmail(id);
      addLog("ok", `Email ${id} rimessa in coda`);
      loadGmailEmails();
    } catch (err) {
      addLog("error", `Errore retry email: ${err.message}`);
    }
  };

  // Formatta dimensione file
  const formatSize = (bytes) => {
    if (!bytes) return "0 B";
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  };

  // Handler principale per elaborazione file
  const handleFiles = async (fileList) => {
    const pdfFiles = Array.from(fileList).filter(
      (f) => f.type === "application/pdf"
    );

    if (pdfFiles.length === 0) {
      addLog("error", "Seleziona file PDF validi");
      return;
    }

    addLog("info", `Elaborazione ${pdfFiles.length} file PDF...`);

    for (const file of pdfFiles) {
      const fileId = Date.now() + Math.random();

      // Crea oggetto file per tracking
      const newFile = {
        id: fileId,
        name: file.name,
        size: file.size,
        status: "uploading",
        progress: 0,
        vendor: null,
        righe: 0,
        error: null,
        message: null,
      };

      setFiles((prev) => [...prev, newFile]);
      addLog("upload", `Avvio upload: ${file.name} (${formatSize(file.size)})`);

      try {
        // Upload con progress callback
        const result = await uploadApi.uploadPdf(file, (progress) => {
          setFiles((prev) =>
            prev.map((f) =>
              f.id === fileId ? { ...f, progress, status: "uploading" } : f
            )
          );
        });

        if (result.success) {
          // Determina stato finale
          const isDuplicato = result.data?.status === "DUPLICATO";
          const finalStatus = isDuplicato ? "duplicato" : "completed";

          // Aggiorna file con risultato
          setFiles((prev) =>
            prev.map((f) =>
              f.id === fileId
                ? {
                    ...f,
                    status: finalStatus,
                    progress: 100,
                    vendor: result.data?.vendor,
                    righe: result.data?.totale_righe || 0,
                    message: result.message,
                  }
                : f
            )
          );

          // Log specifico per tipo risultato
          if (isDuplicato) {
            addLog("warn", `⚠️ ${file.name}: ${result.message}`);
          } else {
            const vendor = result.data?.vendor || "Sconosciuto";
            const righe = result.data?.totale_righe || 0;
            addLog(
              "ok",
              `✅ ${file.name}: ${vendor} - ${righe} righe estratte`
            );
          }
        } else {
          // Mostra errore dettagliato dal backend
          const errorMsg = result.message ||
                          (result.data?.anomalie && result.data.anomalie[0]) ||
                          result.error ||
                          "Upload fallito";
          throw new Error(errorMsg);
        }
      } catch (err) {
        // Errore upload
        setFiles((prev) =>
          prev.map((f) =>
            f.id === fileId ? { ...f, status: "error", error: err.message } : f
          )
        );
        addLog("error", `❌ ${file.name}: ${err.message}`);
      }
    }

    // Aggiorna stats dopo upload
    try {
      const res = await uploadApi.getStats();
      if (res.success) {
        setStats(res.data);
        addLog("info", "Statistiche aggiornate");
      }
    } catch (err) {
      console.error("Error updating stats:", err);
    }
  };

  // Handler drop area
  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    handleFiles(e.dataTransfer.files);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  // Handler input file
  const handleFileInput = (e) => {
    handleFiles(e.target.files);
    e.target.value = ""; // Reset input
  };

  // Pulisci lista file
  const clearFiles = () => {
    setFiles([]);
    setLogs([
      {
        type: "info",
        text: "Lista file pulita",
        time: new Date().toLocaleTimeString("it-IT"),
      },
    ]);
  };

  // Ricarica stats
  const refreshStats = async () => {
    setStatsLoading(true);
    try {
      const res = await uploadApi.getStats();
      if (res.success) {
        setStats(res.data);
        addLog("info", "Statistiche ricaricate");
      }
    } catch (err) {
      addLog("error", "Errore ricaricamento stats");
    } finally {
      setStatsLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Statistiche Upload */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
              📁
            </div>
            <div className="flex-1">
              <p className="text-xs text-slate-600 font-medium">
                Totale Upload
              </p>
              {statsLoading ? (
                <Loading.Inline size="xs" />
              ) : (
                <p className="text-xl font-bold text-slate-800">
                  {stats?.totale || 0}
                </p>
              )}
            </div>
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-emerald-100 rounded-lg flex items-center justify-center">
              📅
            </div>
            <div className="flex-1">
              <p className="text-xs text-slate-600 font-medium">Oggi</p>
              {statsLoading ? (
                <Loading.Inline size="xs" />
              ) : (
                <p className="text-xl font-bold text-slate-800">
                  {stats?.oggi || 0}
                </p>
              )}
            </div>
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
              ✅
            </div>
            <div className="flex-1">
              <p className="text-xs text-slate-600 font-medium">Elaborati</p>
              {statsLoading ? (
                <Loading.Inline size="xs" />
              ) : (
                <p className="text-xl font-bold text-slate-800">
                  {stats?.elaborati || 0}
                </p>
              )}
            </div>
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-red-100 rounded-lg flex items-center justify-center">
              ❌
            </div>
            <div className="flex-1">
              <p className="text-xs text-slate-600 font-medium">Errori</p>
              {statsLoading ? (
                <Loading.Inline size="xs" />
              ) : (
                <p className="text-xl font-bold text-slate-800">
                  {stats?.errori || 0}
                </p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Gmail Monitor Section */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <div className="p-4 border-b border-slate-100 flex justify-between items-center bg-gradient-to-r from-red-50 to-white">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-red-100 rounded-lg flex items-center justify-center">
              <span className="text-xl">📧</span>
            </div>
            <div>
              <h3 className="font-medium text-slate-800">Gmail Monitor</h3>
              <p className="text-xs text-slate-500">
                {gmailLoading
                  ? "Caricamento..."
                  : gmailStatus?.config?.configured
                  ? `Email: ${gmailStatus.config.email}`
                  : "Non configurato"}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {!gmailLoading && gmailStatus?.config?.configured && (
              <>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={handleGmailSync}
                  disabled={gmailSyncing}
                >
                  {gmailSyncing ? (
                    <>
                      <Loading.Spinner size="xs" /> Sincronizzando...
                    </>
                  ) : (
                    "🔄 Sincronizza"
                  )}
                </Button>
                <Button
                  variant={showGmailEmails ? "primary" : "ghost"}
                  size="sm"
                  onClick={() => {
                    setShowGmailEmails(!showGmailEmails);
                    if (!showGmailEmails && gmailEmails.length === 0) {
                      loadGmailEmails();
                    }
                  }}
                >
                  ⚠️ {showGmailEmails ? "Nascondi" : "Mostra"} Errori
                </Button>
              </>
            )}
          </div>
        </div>

        {/* Stats Gmail */}
        {!gmailLoading && gmailStatus?.statistics && (
          <div className="grid grid-cols-4 gap-px bg-slate-100">
            <div className="bg-white p-3 text-center">
              <p className="text-lg font-bold text-slate-800">
                {gmailStatus.statistics.totale}
              </p>
              <p className="text-xs text-slate-500">Totale</p>
            </div>
            <div className="bg-white p-3 text-center">
              <p className="text-lg font-bold text-emerald-600">
                {gmailStatus.statistics.processate}
              </p>
              <p className="text-xs text-slate-500">Processate</p>
            </div>
            <div className="bg-white p-3 text-center">
              <p className="text-lg font-bold text-yellow-600">
                {gmailStatus.statistics.duplicati}
              </p>
              <p className="text-xs text-slate-500">Duplicati</p>
            </div>
            <div className="bg-white p-3 text-center">
              <p className="text-lg font-bold text-red-600">
                {gmailStatus.statistics.errori}
              </p>
              <p className="text-xs text-slate-500">Errori</p>
            </div>
          </div>
        )}

        {/* Lista Email */}
        {showGmailEmails && (
          <div className="border-t border-slate-100">
            <div className="max-h-64 overflow-y-auto divide-y divide-slate-100">
              {gmailEmails.length === 0 ? (
                <div className="p-4 text-center text-slate-500 text-sm">
                  Nessuna email scaricata
                </div>
              ) : (
                gmailEmails.map((email) => (
                  <div
                    key={email.id_email}
                    className={`p-3 hover:bg-slate-50 ${
                      email.stato === "ERRORE" ? "bg-red-50" : ""
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      <div
                        className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
                          email.stato === "PROCESSATA"
                            ? "bg-emerald-100"
                            : email.stato === "ERRORE"
                            ? "bg-red-100"
                            : email.stato === "DUPLICATO"
                            ? "bg-yellow-100"
                            : "bg-blue-100"
                        }`}
                      >
                        {email.stato === "PROCESSATA"
                          ? "✅"
                          : email.stato === "ERRORE"
                          ? "❌"
                          : email.stato === "DUPLICATO"
                          ? "⚠️"
                          : "📄"}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-slate-800 truncate">
                          {email.subject || "(Nessun oggetto)"}
                        </p>
                        <p className="text-xs text-slate-500 truncate">
                          {email.sender_email} -{" "}
                          {new Date(email.received_date).toLocaleDateString(
                            "it-IT"
                          )}
                        </p>
                        {email.attachment_filename && (
                          <p className="text-xs text-blue-600 truncate">
                            📎 {email.attachment_filename}
                          </p>
                        )}
                        {email.errore_messaggio && (
                          <p className="text-xs text-red-600 mt-1">
                            {email.errore_messaggio}
                          </p>
                        )}
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        {email.vendor && (
                          <VendorBadge vendor={email.vendor} size="xs" />
                        )}
                        <span
                          className={`px-2 py-0.5 rounded text-xs font-medium ${
                            email.stato === "PROCESSATA"
                              ? "bg-emerald-100 text-emerald-700"
                              : email.stato === "ERRORE"
                              ? "bg-red-100 text-red-700"
                              : email.stato === "DUPLICATO"
                              ? "bg-yellow-100 text-yellow-700"
                              : "bg-blue-100 text-blue-700"
                          }`}
                        >
                          {email.stato}
                        </span>
                        {(email.stato === "ERRORE" ||
                          email.stato === "DA_PROCESSARE") && (
                          <Button
                            variant="ghost"
                            size="xs"
                            onClick={() => handleRetryEmail(email.id_email)}
                            title="Riprova elaborazione"
                          >
                            🔄
                          </Button>
                        )}
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* Messaggio non configurato */}
        {!gmailLoading && !gmailStatus?.config?.configured && (
          <div className="p-4 bg-yellow-50 text-sm text-yellow-800">
            <p>
              <strong>Gmail non configurato.</strong> Configura le credenziali
              nel file .env del modulo gmail_monitor.
            </p>
            {gmailStatus?.config?.error && (
              <p className="text-xs mt-1 text-yellow-600">
                Errore: {gmailStatus.config.error}
              </p>
            )}
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="flex items-center gap-3">
        <Button
          variant="secondary"
          size="sm"
          onClick={refreshStats}
          disabled={statsLoading}
        >
          🔄 Ricarica Stats
        </Button>
        {files.length > 0 && (
          <Button variant="ghost" size="sm" onClick={clearFiles}>
            🗑️ Pulisci Lista
          </Button>
        )}
      </div>

      {/* Drop Zone */}
      <div
        className={`bg-white rounded-xl border-2 border-dashed p-8 text-center transition-all duration-200 cursor-pointer group ${
          isDragging
            ? "border-blue-500 bg-blue-50 scale-105"
            : "border-slate-300 hover:border-blue-400 hover:bg-slate-50"
        }`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
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

        <div
          className={`w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-4 transition-all duration-200 ${
            isDragging
              ? "bg-blue-200 scale-110"
              : "bg-blue-100 group-hover:bg-blue-200"
          }`}
        >
          <span className="text-3xl">📁</span>
        </div>

        <h3 className="text-lg font-medium text-slate-700 mb-1">
          {isDragging ? "Rilascia qui i file PDF" : "Trascina qui i file PDF"}
        </h3>
        <p className="text-sm text-slate-500 mb-4">
          oppure clicca per selezionare
        </p>

        {/* Vendor badges supportati */}
        <div className="flex flex-wrap justify-center gap-2">
          {["ANGELINI", "BAYER", "CODIFI", "CHIESI", "MENARINI", "OPELLA"].map(
            (vendor) => (
              <VendorBadge key={vendor} vendor={vendor} size="xs" />
            )
          )}
        </div>
      </div>

      {/* Lista File */}
      {files.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200">
          <div className="p-4 border-b border-slate-100 flex justify-between items-center">
            <h3 className="font-medium text-slate-800">
              File Caricati ({files.length})
            </h3>
            <div className="flex items-center gap-2">
              <StatusBadge
                status="processing"
                label={`${
                  files.filter((f) => f.status === "uploading").length
                } in corso`}
                showIcon={false}
                size="xs"
              />
              <StatusBadge
                status="completed"
                label={`${
                  files.filter((f) => f.status === "completed").length
                } ok`}
                showIcon={false}
                size="xs"
              />
              <StatusBadge
                status="error"
                label={`${
                  files.filter((f) => f.status === "error").length
                } errori`}
                showIcon={false}
                size="xs"
              />
            </div>
          </div>

          <div className="divide-y divide-slate-100 max-h-80 overflow-y-auto">
            {files.map((file) => (
              <div
                key={file.id}
                className={`p-4 transition-colors ${
                  file.status === "duplicato" ? "bg-yellow-50" : ""
                }`}
              >
                <div className="flex items-center gap-4">
                  {/* Icona stato */}
                  <div
                    className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                      file.status === "completed"
                        ? "bg-emerald-100"
                        : file.status === "duplicato"
                        ? "bg-yellow-100"
                        : file.status === "error"
                        ? "bg-red-100"
                        : "bg-blue-100"
                    }`}
                  >
                    {file.status === "uploading" ? (
                      <Loading.Spinner size="xs" />
                    ) : file.status === "completed" ? (
                      "✅"
                    ) : file.status === "duplicato" ? (
                      "⚠️"
                    ) : file.status === "error" ? (
                      "❌"
                    ) : (
                      "📄"
                    )}
                  </div>

                  {/* Info file */}
                  <div className="flex-1 min-w-0">
                    <p className="font-mono text-sm font-medium text-slate-800 truncate">
                      {file.name}
                    </p>
                    <div className="flex items-center gap-3 text-xs text-slate-500">
                      <span>{formatSize(file.size)}</span>
                      {file.status === "uploading" && (
                        <span>• {file.progress}% caricato</span>
                      )}
                      {file.righe > 0 && <span>• {file.righe} righe</span>}
                      {file.error && (
                        <span className="text-red-500">• {file.error}</span>
                      )}
                    </div>

                    {/* Messaggio duplicato/errore */}
                    {file.message && (
                      <p
                        className={`text-xs mt-1 ${
                          file.status === "duplicato"
                            ? "text-yellow-700"
                            : file.status === "error"
                            ? "text-red-600"
                            : "text-slate-600"
                        }`}
                      >
                        {file.message}
                      </p>
                    )}

                    {/* Progress bar per upload */}
                    {file.status === "uploading" && (
                      <div className="w-full h-1 bg-slate-200 rounded-full mt-2">
                        <div
                          className="h-full bg-blue-500 rounded-full transition-all duration-300"
                          style={{ width: `${file.progress}%` }}
                        />
                      </div>
                    )}
                  </div>

                  {/* Badge vendor e stato */}
                  <div className="flex items-center gap-2">
                    {file.vendor && (
                      <VendorBadge vendor={file.vendor} size="xs" />
                    )}
                    <StatusBadge status={file.status} size="xs" />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Console Log */}
      <div className="bg-slate-900 rounded-xl">
        <div className="p-3 border-b border-slate-700 flex justify-between items-center">
          <h3 className="font-medium text-white text-sm">Console Upload</h3>
          <Button
            variant="ghost"
            size="xs"
            onClick={() =>
              setLogs([
                {
                  type: "info",
                  text: "Console pulita",
                  time: new Date().toLocaleTimeString("it-IT"),
                },
              ])
            }
            className="text-slate-400 hover:text-white"
          >
            🗑️ Pulisci
          </Button>
        </div>
        <div className="p-3 font-mono text-xs h-40 overflow-y-auto">
          {logs.map((log, i) => (
            <p
              key={i}
              className={`leading-relaxed ${
                log.type === "info"
                  ? "text-slate-400"
                  : log.type === "upload"
                  ? "text-blue-400"
                  : log.type === "ok"
                  ? "text-emerald-400"
                  : log.type === "warn"
                  ? "text-yellow-400"
                  : log.type === "error"
                  ? "text-red-400"
                  : "text-slate-300"
              }`}
            >
              <span className="text-slate-500">[{log.time}]</span> {log.text}
            </p>
          ))}
        </div>
      </div>
    </div>
  );
};

export default UploadPage;
