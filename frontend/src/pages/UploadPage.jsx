// =============================================================================
// UPLOAD PAGE - MODERNIZZATA v6.2
// =============================================================================
// Pagina upload PDF con componenti modulari
// Drag & drop, progress, stati, vendor detection
// =============================================================================

import React, { useState, useEffect } from "react";
import { uploadApi, mailApi } from "../api";
import { Button, StatusBadge, VendorBadge, Loading, ErrorBox } from "../common";

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

  // Mail Monitor state
  const [mailStatus, setMailStatus] = useState(null);
  const [mailEmails, setMailEmails] = useState([]);
  const [mailLoading, setMailLoading] = useState(true);
  const [mailSyncing, setMailSyncing] = useState(false);
  const [showMailEmails, setShowMailEmails] = useState(false);

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

  // v11.0: Track ultimo messaggio di progresso visto
  const [lastProgressIndex, setLastProgressIndex] = useState(0);

  // Carica stato Mail Monitor
  // v11.0: Log risultati sync come upload manuale + progress real-time
  useEffect(() => {
    const loadMailStatus = async () => {
      try {
        const res = await mailApi.getStatus();
        if (res.success) {
          const wasSyncing = mailSyncing;
          const isNowSyncing = res.sync_status?.is_running;

          setMailStatus(res);

          // v11.0: Mostra messaggi di progresso durante sync
          if (isNowSyncing) {
            setMailSyncing(true);

            // Mostra nuovi messaggi di progresso
            const progressMsgs = res.sync_status?.progress_messages || [];
            if (progressMsgs.length > lastProgressIndex) {
              const newMsgs = progressMsgs.slice(lastProgressIndex);
              newMsgs.forEach(msg => {
                const msgText = msg.message || msg;
                if (msgText.includes('Errore')) {
                  addLog("error", `[${msg.time}] ${msgText}`);
                } else if (msgText.includes('elaborata') || msgText.includes('completata')) {
                  addLog("ok", `[${msg.time}] ${msgText}`);
                } else {
                  addLog("info", `[${msg.time}] ${msgText}`);
                }
              });
              setLastProgressIndex(progressMsgs.length);
            }

            // Mostra fase corrente se disponibile
            const phase = res.sync_status?.current_phase;
            if (phase && !progressMsgs.some(m => m.message?.includes(phase))) {
              // La fase viene mostrata solo se non è già nei messaggi
            }
          } else if (wasSyncing && !isNowSyncing) {
            // Sync appena completato - carica e logga risultati
            setMailSyncing(false);
            setLastProgressIndex(0); // Reset per prossima sync
            const syncResult = res.sync_status?.last_result;
            if (syncResult?.success) {
              const processed = syncResult.emails_processed || res.sync_status?.emails_processed || 0;
              const errors = syncResult.emails_errors || res.sync_status?.emails_errors || 0;
              addLog("ok", `✅ Sincronizzazione completata: ${processed} email elaborate, ${errors} errori`);

              // Carica email recenti processate e logga dettagli
              if (processed > 0) {
                const recentEmails = await mailApi.getEmails({ limit: 20 });
                if (recentEmails.success && recentEmails.emails) {
                  const processate = recentEmails.emails.filter(e => e.stato === 'PROCESSATA');
                  processate.slice(0, 10).forEach(email => {
                    const vendor = email.vendor || 'Sconosciuto';
                    const righe = email.num_righe || 0;
                    const righeMsg = righe > 0 ? ` - ${righe} righe estratte` : '';
                    addLog("ok", `   ${email.attachment_filename || 'Email'}: ${vendor}${righeMsg}`);
                  });
                  if (processate.length > 10) {
                    addLog("info", `   ... e altre ${processate.length - 10} email processate`);
                  }
                }
              }
              addLog("info", "Monitoraggio mail completato");
            } else if (syncResult) {
              addLog("error", `❌ Sync fallita: ${syncResult.error || 'Errore sconosciuto'}`);
              addLog("info", "Monitoraggio mail terminato con errori");
            }
          }
        }
      } catch (err) {
        console.error("Error loading Mail status:", err);
      } finally {
        setMailLoading(false);
      }
    };

    loadMailStatus();
    // v11.0: Polling ogni 3 secondi se sync in corso (era 10)
    const interval = setInterval(() => {
      if (mailSyncing) loadMailStatus();
    }, 3000);

    return () => clearInterval(interval);
  }, [mailSyncing, lastProgressIndex]);

  // Avvia sync Mail
  const handleMailSync = async () => {
    try {
      setMailSyncing(true);
      setLastProgressIndex(0); // v11.0: Reset progress tracking
      addLog("info", "Avvio sincronizzazione Mail...");
      const res = await mailApi.sync();
      if (res.success) {
        addLog("ok", "Connessione al server mail in corso...");
      }
    } catch (err) {
      const msg = err.response?.data?.detail || err.message;
      addLog("error", `Errore sync Mail: ${msg}`);
      setMailSyncing(false);
    }
  };

  // Carica email Mail (solo errori)
  // v11.0: Mostra stesse info di upload manuale
  const loadMailEmails = async () => {
    try {
      const res = await mailApi.getEmails({ limit: 50, stato: 'ERRORE' });
      if (res.success) {
        setMailEmails(res.emails || []);
        const emails = res.emails || [];
        addLog("info", `Caricate ${emails.length} email con errore`);
        // Log dettagli per ogni email come upload manuale
        emails.forEach(email => {
          const vendor = email.vendor || 'Sconosciuto';
          const righe = email.num_righe || 0;
          const righeMsg = righe > 0 ? ` - ${righe} righe` : '';
          const statoIcon = email.stato === 'ERRORE' ? '❌' : '📧';
          addLog(
            email.stato === 'ERRORE' ? 'error' : 'info',
            `${statoIcon} ${email.attachment_filename || email.subject}: ${vendor}${righeMsg}`
          );
        });
      }
    } catch (err) {
      addLog("error", "Errore caricamento email");
    }
  };

  // Riprova elaborazione email
  const handleRetryEmail = async (id) => {
    try {
      await mailApi.retryEmail(id);
      addLog("ok", `Email ${id} rimessa in coda`);
      loadMailEmails();
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
          // Aggiorna file con risultato OK
          setFiles((prev) =>
            prev.map((f) =>
              f.id === fileId
                ? {
                    ...f,
                    status: "completed",
                    progress: 100,
                    vendor: result.data?.vendor,
                    righe: result.data?.totale_righe || 0,
                    message: result.message,
                  }
                : f
            )
          );

          const vendor = result.data?.vendor || "Sconosciuto";
          const righe = result.data?.totale_righe || 0;
          const righeMsg = righe > 0 ? ` - ${righe} righe estratte` : "";
          addLog("ok", `✅ ${file.name}: ${vendor}${righeMsg}`);
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

      {/* Mail Monitor Section */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <div className="p-4 border-b border-slate-100 flex justify-between items-center bg-gradient-to-r from-blue-50 to-white">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
              <span className="text-xl">📧</span>
            </div>
            <div>
              <h3 className="font-medium text-slate-800">Mail Monitor</h3>
              <p className="text-xs text-slate-500">
                {mailLoading
                  ? "Caricamento..."
                  : mailStatus?.config?.configured
                  ? `Email: ${mailStatus.config.email}`
                  : "Non configurato"}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {!mailLoading && mailStatus?.config?.configured && (
              <>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={handleMailSync}
                  disabled={mailSyncing}
                >
                  {mailSyncing ? (
                    <>
                      <Loading.Spinner size="xs" /> Sincronizzando...
                    </>
                  ) : (
                    "🔄 Sincronizza"
                  )}
                </Button>
                <Button
                  variant={showMailEmails ? "primary" : "ghost"}
                  size="sm"
                  onClick={() => {
                    setShowMailEmails(!showMailEmails);
                    if (!showMailEmails && mailEmails.length === 0) {
                      loadMailEmails();
                    }
                  }}
                >
                  ⚠️ {showMailEmails ? "Nascondi" : "Mostra"} Errori
                </Button>
              </>
            )}
          </div>
        </div>

        {/* Stats Mail */}
        {!mailLoading && mailStatus?.statistics && (
          <div className="grid grid-cols-4 gap-px bg-slate-100">
            <div className="bg-white p-3 text-center">
              <p className="text-lg font-bold text-slate-800">
                {mailStatus.statistics.totale}
              </p>
              <p className="text-xs text-slate-500">Totale</p>
            </div>
            <div className="bg-white p-3 text-center">
              <p className="text-lg font-bold text-emerald-600">
                {mailStatus.statistics.processate}
              </p>
              <p className="text-xs text-slate-500">Processate</p>
            </div>
            <div className="bg-white p-3 text-center">
              <p className="text-lg font-bold text-yellow-600">
                {mailStatus.statistics.duplicati}
              </p>
              <p className="text-xs text-slate-500">Duplicati</p>
            </div>
            <div className="bg-white p-3 text-center">
              <p className="text-lg font-bold text-red-600">
                {mailStatus.statistics.errori}
              </p>
              <p className="text-xs text-slate-500">Errori</p>
            </div>
          </div>
        )}

        {/* Scheduler Status */}
        {!mailLoading && mailStatus?.scheduler?.enabled && (
          <div className="px-4 py-2 bg-blue-50 border-t border-blue-100 flex items-center gap-2 text-sm">
            <span className="text-blue-500">⏰</span>
            <span className="text-blue-700">
              Prossima verifica prevista alle ore{" "}
              <strong>
                {mailStatus.scheduler.next_run
                  ? new Date(mailStatus.scheduler.next_run).toLocaleString("it-IT", {
                      weekday: "short",
                      day: "2-digit",
                      month: "2-digit",
                      hour: "2-digit",
                      minute: "2-digit",
                    })
                  : "N/A"}
              </strong>
            </span>
            <span className="text-blue-400 text-xs ml-auto">
              {mailStatus.scheduler.schedule}
            </span>
          </div>
        )}

        {/* Lista Email */}
        {showMailEmails && (
          <div className="border-t border-slate-100">
            <div className="max-h-64 overflow-y-auto divide-y divide-slate-100">
              {mailEmails.length === 0 ? (
                <div className="p-4 text-center text-slate-500 text-sm">
                  Nessuna email scaricata
                </div>
              ) : (
                mailEmails.map((email) => (
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
                            {/* v11.0: Mostra righe estratte come upload manuale */}
                            {email.num_righe > 0 && (
                              <span className="text-emerald-600 ml-2">
                                • {email.num_righe} righe estratte
                              </span>
                            )}
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
        {!mailLoading && !mailStatus?.config?.configured && (
          <div className="p-4 bg-yellow-50 text-sm text-yellow-800">
            <p>
              <strong>Mail non configurato.</strong> Configura le credenziali
              nel file backend/.env.
            </p>
            {mailStatus?.config?.error && (
              <p className="text-xs mt-1 text-yellow-600">
                Errore: {mailStatus.config.error}
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
                  file.status === "error" ? "bg-red-50" : ""
                }`}
              >
                <div className="flex items-center gap-4">
                  {/* Icona stato */}
                  <div
                    className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                      file.status === "completed"
                        ? "bg-emerald-100"
                        : file.status === "error"
                        ? "bg-red-100"
                        : "bg-blue-100"
                    }`}
                  >
                    {file.status === "uploading" ? (
                      <Loading.Spinner size="xs" />
                    ) : file.status === "completed" ? (
                      "✅"
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

                    {/* Messaggio errore */}
                    {file.message && (
                      <p
                        className={`text-xs mt-1 ${
                          file.status === "error"
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
