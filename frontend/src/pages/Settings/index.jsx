// =============================================================================
// SETTINGS PAGE - MODERNIZZATA v6.2
// =============================================================================
// Pagina impostazioni complete del sistema SERV.O
// Configurazioni vendor, automazione, database, sistema
// =============================================================================

import React, { useState, useEffect, useCallback } from "react";
import { adminApi, anagraficaApi, utentiApi, listiniApi, getApiBaseUrl } from "../../api";
import { Button, StatusBadge, VendorBadge, Loading, ErrorBox } from "../../common";
import { richiestaConferma } from "../../utils/confirmazione";
import UtentiPage from "../UtentiPage";
import BackupPage from "../BackupPage";
import EmailTab from "./EmailTab";
import PermessiTab from "./PermessiTab";

/**
 * Componente SettingsPage modernizzato
 *
 * LOGICA IMPLEMENTATIVA:
 * - Configurazioni tracciati (codice produttore, dilazione)
 * - Impostazioni automazione (auto-validazione, ML)
 * - Gestione database (backup, pulizia, reset)
 * - Configurazioni vendor e sistema
 * - Info sistema e diagnostica
 *
 * INTERRELAZIONI:
 * - API: settingsApi per configurazioni, anagraficaApi per database
 * - Componenti: Button, StatusBadge per consistency UI
 * - Storage: localStorage per preferenze utente
 */
const SettingsPage = ({ currentUser }) => {
  const [settings, setSettings] = useState({
    // v6.2: codProduttore e ggDilazione rimossi
    // - codProduttore: generato dinamicamente (VENDOR_3lettere + GROSSISTA)
    // - ggDilazione: dipende da condizioni vendor e data consegna

    // Automazione
    autoValidate: true,
    mlAutoApprove: false,
    mlMinConfidence: 85,

    // Email
    emailNotifications: true,
    emailOnError: true,

    // Database
    autoBackup: true,
    backupRetention: 30,

    // Debug
    debugMode: false,
    logLevel: "INFO",
  });

  const [systemInfo, setSystemInfo] = useState({
    version: "v11.0",
    uptime: "0d 0h 0m",
    database_size: "0 MB",
    pdf_count: 0,
    orders_count: 0,
    last_backup: null,
  });

  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  // Default tab basato su ruolo: admin=general, altri=password
  const [activeTab, setActiveTab] = useState(() => {
    return currentUser?.ruolo === 'admin' ? "general" : "password";
  });
  const [importProgress, setImportProgress] = useState(null);

  // State per statistiche anagrafiche
  const [anagraficaStats, setAnagraficaStats] = useState({
    farmacie: { count: 0, last_import: null, filename: null },
    parafarmacie: { count: 0, last_import: null, filename: null },
    clienti: { totale: 0, last_import: null, filename: null }
  });

  // State per statistiche listini
  const [listiniStats, setListiniStats] = useState({
    CODIFI: { count: 0, last_import: null, filename: null }
  });

  // State per sincronizzazione Ministero (v8.2)
  const [syncStatus, setSyncStatus] = useState({
    farmacie: { last_sync: null, records_count: 0, needs_update: false },
    parafarmacie: { last_sync: null, records_count: 0, needs_update: false }
  });
  const [syncLoading, setSyncLoading] = useState(false);

  // State per cambio password
  const [passwordForm, setPasswordForm] = useState({
    vecchia_password: '',
    nuova_password: '',
    conferma_password: ''
  });
  const [changingPassword, setChangingPassword] = useState(false);

  // Carica impostazioni e info sistema
  const loadSettings = useCallback(async () => {
    try {
      setLoading(true);

      // Carica settings dal localStorage per ora (TODO: API backend)
      const savedSettings = localStorage.getItem("to_extractor_settings");
      if (savedSettings) {
        setSettings((prev) => ({ ...prev, ...JSON.parse(savedSettings) }));
      }

      // Carica statistiche anagrafiche
      try {
        const response = await anagraficaApi.getStats();
        if (response?.data) {
          setAnagraficaStats(response.data);
        }
      } catch (err) {
        console.warn("Errore caricamento stats anagrafiche:", err);
      }

      // Carica statistiche listini
      try {
        const response = await listiniApi.getStats();
        if (response?.data?.vendors) {
          // Trasforma la risposta per il frontend
          const transformedStats = {};
          Object.entries(response.data.vendors).forEach(([vendor, data]) => {
            transformedStats[vendor] = {
              count: data.prodotti || 0,
              last_import: data.ultimo_import,
              filename: data.ultimo_file
            };
          });
          setListiniStats(transformedStats);
        }
      } catch (err) {
        console.warn("Errore caricamento stats listini:", err);
      }

      // Carica stato sincronizzazione Ministero (v8.2)
      try {
        const response = await adminApi.getSyncStatus();
        if (response?.data) {
          setSyncStatus(response.data);
        }
      } catch (err) {
        console.warn("Errore caricamento stato sync:", err);
      }

      // Simula info sistema (TODO: API reale)
      setSystemInfo({
        version: "v11.0",
        uptime: "2d 14h 23m",
        database_size: "245 MB",
        pdf_count: 1247,
        orders_count: 892,
        last_backup: new Date(Date.now() - 24 * 60 * 60 * 1000).toLocaleString(
          "it-IT"
        ),
      });
    } catch (err) {
      console.error("Errore caricamento settings:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSettings();
  }, [loadSettings]);

  // Salva impostazioni
  const handleSave = async () => {
    setSaving(true);
    try {
      // Salva in localStorage per ora (TODO: API backend)
      localStorage.setItem("to_extractor_settings", JSON.stringify(settings));

      // Simula chiamata API
      await new Promise((resolve) => setTimeout(resolve, 1000));

      alert("✅ Impostazioni salvate con successo!");
    } catch (err) {
      alert("❌ Errore salvataggio: " + err.message);
    } finally {
      setSaving(false);
    }
  };

  // Reset impostazioni
  const handleReset = async () => {
    const confirm = window.confirm(
      "⚠️ RESET IMPOSTAZIONI\n\n" +
        "Vuoi ripristinare tutte le impostazioni ai valori predefiniti?\n\n" +
        "Questa operazione non è reversibile."
    );

    if (!confirm) return;

    const defaultSettings = {
      // v6.2: codProduttore e ggDilazione rimossi
      autoValidate: true,
      mlAutoApprove: false,
      mlMinConfidence: 85,
      emailNotifications: true,
      emailOnError: true,
      autoBackup: true,
      backupRetention: 30,
      debugMode: false,
      logLevel: "INFO",
    };

    setSettings(defaultSettings);
    localStorage.removeItem("to_extractor_settings");
    alert("✅ Impostazioni ripristinate ai valori predefiniti");
  };

  // Sincronizzazione Anagrafica Ministero (v8.2)
  const handleSync = async (tipo = 'all') => {
    setSyncLoading(true);
    try {
      let response;
      let tipoLabel;

      switch (tipo) {
        case 'farmacie':
          response = await adminApi.syncFarmacie();
          tipoLabel = 'Farmacie';
          break;
        case 'parafarmacie':
          response = await adminApi.syncParafarmacie();
          tipoLabel = 'Parafarmacie';
          break;
        default:
          response = await adminApi.syncAll();
          tipoLabel = 'Farmacie + Parafarmacie';
      }

      if (response.success) {
        const data = response.data;

        if (tipo === 'all') {
          // Risultato sync completa
          const f = data.farmacie || {};
          const p = data.parafarmacie || {};

          let msg = `✅ SINCRONIZZAZIONE COMPLETATA\n\n`;
          msg += `📥 Farmacie:\n`;
          msg += `   • Nuove: ${f.nuove || 0}\n`;
          msg += `   • Aggiornate: ${f.aggiornate || 0}\n`;
          msg += `   • Subentri (cambio P.IVA): ${f.subentri || 0}\n`;
          msg += `   • Chiuse: ${f.chiuse || 0}\n`;
          msg += `   • Totale DB: ${f.totale_db?.toLocaleString() || 0}\n\n`;
          msg += `📥 Parafarmacie:\n`;
          msg += `   • Nuove: ${p.nuove || 0}\n`;
          msg += `   • Aggiornate: ${p.aggiornate || 0}\n`;
          msg += `   • Subentri: ${p.subentri || 0}\n`;
          msg += `   • Chiuse: ${p.chiuse || 0}\n`;
          msg += `   • Totale DB: ${p.totale_db?.toLocaleString() || 0}\n\n`;
          msg += `⏱️ Durata: ${data.durata_totale_secondi?.toFixed(1) || 0}s`;

          alert(msg);
        } else {
          // Risultato sync singola
          let msg = `✅ SYNC ${tipoLabel.toUpperCase()}\n\n`;
          if (data.downloaded === false) {
            msg += `ℹ️ File non modificato (304 Not Modified)\n`;
            msg += `Nessun download necessario.`;
          } else {
            msg += `• Nuove: ${data.nuove || 0}\n`;
            msg += `• Aggiornate: ${data.aggiornate || 0}\n`;
            msg += `• Subentri: ${data.subentri || 0}\n`;
            msg += `• Chiuse: ${data.chiuse || 0}\n`;
            msg += `• Totale DB: ${data.totale_db?.toLocaleString() || 0}\n`;
            msg += `• Durata: ${data.durata_secondi?.toFixed(1) || 0}s`;
          }
          alert(msg);
        }

        // Ricarica stato sync
        const statusRes = await adminApi.getSyncStatus();
        if (statusRes?.data) {
          setSyncStatus(statusRes.data);
        }

        // Ricarica stats anagrafiche
        loadSettings();
      } else {
        alert(`❌ Errore: ${response.message}`);
      }
    } catch (err) {
      alert(`❌ Errore sincronizzazione: ${err.response?.data?.detail || err.message}`);
    } finally {
      setSyncLoading(false);
    }
  };

  // Azioni database
  const handleDatabaseAction = async (action) => {
    try {
      switch (action) {
        case 'backup':
          setLoading(true);
          const backupRes = await adminApi.backup();
          if (backupRes.success) {
            alert(`Backup creato: ${backupRes.filename} (${backupRes.size_mb} MB)`);
          }
          break;

        case 'clear_ordini':
          if (!richiestaConferma(
            'ATTENZIONE: Eliminare TUTTI gli ordini?',
            'Questa azione è irreversibile. Tutti gli ordini e le relative righe verranno eliminati.'
          )) return;
          setLoading(true);
          const clearRes = await adminApi.clearOrdini();
          if (clearRes.success) {
            alert(`Eliminati ${clearRes.deleted.ordini} ordini e ${clearRes.deleted.righe} righe.`);
          }
          break;

        case 'reset_complete':
          if (!richiestaConferma(
            'ATTENZIONE CRITICA: Reset completo del sistema',
            'Tutti i dati verranno eliminati.\nLe anagrafiche (farmacie/parafarmacie) verranno preservate.'
          )) return;
          setLoading(true);
          const resetRes = await adminApi.resetSistema();
          if (resetRes.success) {
            alert('Reset completato. Anagrafiche preservate.');
          }
          break;

        default:
          console.warn('Azione non riconosciuta:', action);
      }
    } catch (err) {
      alert('Errore: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  // Import Farmacie
  const handleImportFarmacie = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = "";

    if (!file.name.toLowerCase().endsWith(".csv")) {
      alert("⚠️ Seleziona un file CSV valido per le farmacie");
      return;
    }

    setImportProgress({ type: "farmacie", progress: 0 });

    try {
      const res = await anagraficaApi.importFarmacie(file, (progress) => {
        setImportProgress({ type: "farmacie", progress });
      });

      if (res.success) {
        const d = res.data || {};
        let msg = `✅ IMPORT FARMACIE COMPLETATO!\n\n` +
          `📄 Righe nel CSV: ${d.totale_righe_csv ?? 'N/A'}\n` +
          `🏥 Farmacie attive (data_fine='-'): ${d.righe_attive ?? 'N/A'}\n` +
          `📋 Farmacie importate: ${d.importate || 0}\n` +
          `📊 Duplicati/Aggiornati: ${d.duplicate || 0}`;

        // Debug info
        if (d.skip_empty_minid) msg += `\n⚠️ Skip (min_id vuoto): ${d.skip_empty_minid}`;
        if (d.skip_zero_minid) msg += `\n⚠️ Skip (min_id=0): ${d.skip_zero_minid}`;
        if (d.errori) msg += `\n❌ Errori: ${d.errori}`;
        if (d.ultimo_errore) msg += `\n🔴 Ultimo errore: ${d.ultimo_errore}`;

        alert(msg);
        loadSettings(); // Ricarica stats
      } else {
        throw new Error(res.error || "Import fallito");
      }
    } catch (err) {
      alert("❌ Errore import farmacie:\n" + err.message);
    } finally {
      setImportProgress(null);
    }
  };

  // Import Parafarmacie
  const handleImportParafarmacie = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = "";

    if (!file.name.toLowerCase().endsWith(".csv")) {
      alert("⚠️ Seleziona un file CSV valido per le parafarmacie");
      return;
    }

    setImportProgress({ type: "parafarmacie", progress: 0 });

    try {
      const res = await anagraficaApi.importParafarmacie(file, (progress) => {
        setImportProgress({ type: "parafarmacie", progress });
      });

      if (res.success) {
        const d = res.data || {};
        let msg = `✅ IMPORT PARAFARMACIE COMPLETATO!\n\n` +
          `📄 Righe nel CSV: ${d.totale_righe_csv ?? 'N/A'}\n` +
          `🏥 Parafarmacie attive (data_fine='-'): ${d.righe_attive ?? 'N/A'}\n` +
          `📋 Parafarmacie importate: ${d.importate || 0}\n` +
          `📊 Duplicati/Aggiornati: ${d.duplicate || 0}`;

        // Debug info
        if (d.colonne_csv) msg += `\n\n📋 Colonne CSV: ${d.colonne_csv.join(', ')}`;
        if (d.skip_empty_codice) msg += `\n⚠️ Skip (codice vuoto): ${d.skip_empty_codice}`;
        if (d.errori) msg += `\n❌ Errori: ${d.errori}`;
        if (d.ultimo_errore) msg += `\n🔴 Ultimo errore: ${d.ultimo_errore}`;
        if (d.error) msg += `\n🔴 Errore generale: ${d.error}`;

        alert(msg);
        loadSettings(); // Ricarica stats
      } else {
        throw new Error(res.error || "Import fallito");
      }
    } catch (err) {
      alert("❌ Errore import parafarmacie:\n" + err.message);
    } finally {
      setImportProgress(null);
    }
  };

  // Import Clienti
  const handleImportClienti = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = "";

    if (!file.name.toLowerCase().endsWith(".csv")) {
      alert("Seleziona un file CSV valido per i clienti");
      return;
    }

    setImportProgress({ type: "clienti", progress: 0 });

    try {
      const res = await anagraficaApi.importClienti(file, (progress) => {
        setImportProgress({ type: "clienti", progress });
      });

      if (res.success) {
        const d = res.data || {};
        let msg = `IMPORT CLIENTI COMPLETATO!\n\n` +
          `Righe nel CSV: ${d.totale_righe_csv ?? 'N/A'}\n` +
          `Clienti importati: ${d.importate || 0}\n` +
          `Clienti aggiornati: ${d.aggiornati || 0}\n` +
          `Totale in DB: ${d.totale_db || 0}`;

        // Debug info
        if (d.colonne_csv) msg += `\n\nColonne CSV: ${d.colonne_csv.join(', ')}`;
        if (d.skip_empty_codice) msg += `\nSkip (codice vuoto): ${d.skip_empty_codice}`;
        if (d.errori) msg += `\nErrori: ${d.errori}`;
        if (d.ultimo_errore) msg += `\nUltimo errore: ${d.ultimo_errore}`;

        alert(msg);
        loadSettings(); // Ricarica stats
      } else {
        throw new Error(res.error || "Import fallito");
      }
    } catch (err) {
      alert("Errore import clienti:\n" + err.message);
    } finally {
      setImportProgress(null);
    }
  };

  // Import Listino CODIFI
  const handleImportListino = async (e, vendor = 'CODIFI') => {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = "";

    if (!file.name.toLowerCase().endsWith(".csv")) {
      alert("⚠️ Seleziona un file CSV valido per il listino");
      return;
    }

    setImportProgress({ type: `listino_${vendor}`, progress: 0 });

    try {
      const res = await listiniApi.importListino(file, vendor, (progress) => {
        setImportProgress({ type: `listino_${vendor}`, progress });
      });

      if (res.success) {
        const d = res.data || {};
        let msg = `✅ IMPORT LISTINO ${vendor} COMPLETATO!\n\n` +
          `📋 Prodotti importati: ${(d.imported || 0).toLocaleString()}\n` +
          `📊 In database: ${(d.total_in_db || 0).toLocaleString()}`;

        if (d.skipped) msg += `\n⏭️ Saltati: ${d.skipped}`;
        if (d.errors && d.errors.length > 0) {
          msg += `\n\n❌ Errori (primi 5):`;
          d.errors.slice(0, 5).forEach(e => msg += `\n  • ${e}`);
        }
        if (d.prezzi_calcolati) {
          msg += `\n\n💰 Prezzi calcolati: ${d.prezzi_calcolati.updated || 0}`;
        }

        alert(msg);
        loadSettings(); // Ricarica stats
      } else {
        throw new Error(res.error || "Import fallito");
      }
    } catch (err) {
      alert("❌ Errore import listino:\n" + (err.response?.data?.detail || err.message));
    } finally {
      setImportProgress(null);
    }
  };

  // Download logs
  const handleDownloadLogs = () => {
    const logContent = `SERV.O v${systemInfo.version} - Log Export
Data: ${new Date().toLocaleString("it-IT")}
Uptime: ${systemInfo.uptime}

=== CONFIGURAZIONE ===
Auto Validazione: ${settings.autoValidate ? "ON" : "OFF"}
ML Auto Approve: ${settings.mlAutoApprove ? "ON" : "OFF"}
Debug Mode: ${settings.debugMode ? "ON" : "OFF"}

=== STATISTICHE ===
Database Size: ${systemInfo.database_size}
PDF Processati: ${systemInfo.pdf_count}
Ordini Totali: ${systemInfo.orders_count}
Ultimo Backup: ${systemInfo.last_backup || "Mai"}

=== FINE LOG ===`;

    const blob = new Blob([logContent], { type: "text/plain" });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `to_extractor_log_${new Date()
      .toISOString()
      .slice(0, 10)}.txt`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  };

  // Cambio password utente corrente
  const handleChangePassword = async () => {
    // Validazione
    if (!passwordForm.vecchia_password) {
      alert('Inserisci la password attuale');
      return;
    }
    if (!passwordForm.nuova_password) {
      alert('Inserisci la nuova password');
      return;
    }
    if (passwordForm.nuova_password.length < 6) {
      alert('La nuova password deve avere almeno 6 caratteri');
      return;
    }
    if (passwordForm.nuova_password !== passwordForm.conferma_password) {
      alert('Le password non coincidono');
      return;
    }

    setChangingPassword(true);
    try {
      const userId = currentUser?.id_operatore || currentUser?.id;
      if (!userId) {
        throw new Error('ID utente non trovato. Prova a fare logout e login.');
      }
      await utentiApi.changePassword(userId, {
        vecchia_password: passwordForm.vecchia_password,
        nuova_password: passwordForm.nuova_password
      });
      alert('Password cambiata con successo!');
      setPasswordForm({ vecchia_password: '', nuova_password: '', conferma_password: '' });
    } catch (err) {
      alert('Errore: ' + (err.response?.data?.detail || err.message));
    } finally {
      setChangingPassword(false);
    }
  };

  // Tabs configurazione basati su ruolo
  // ADMIN: tutti i tab
  // SUPERVISORE: Cambio Password + Utenti
  // OPERATORE: solo Cambio Password
  const isAdmin = currentUser?.ruolo === 'admin';
  const isSupervisor = currentUser?.ruolo === 'supervisore';
  const isAdminOrSupervisor = isAdmin || isSupervisor;

  const getTabs = () => {
    // Tab base per tutti: Cambio Password
    const baseTabs = [
      { id: "password", label: "Cambio Password", icon: "🔐" },
    ];

    // SUPERVISORE: aggiunge Utenti
    if (isSupervisor) {
      return [
        ...baseTabs,
        { id: "utenti", label: "Utenti", icon: "👥" },
      ];
    }

    // ADMIN: tutti i tab
    if (isAdmin) {
      return [
        { id: "general", label: "Generale", icon: "⚙️" },
        { id: "automation", label: "Automazione", icon: "🤖" },
        { id: "email", label: "Email", icon: "📧" },
        { id: "database", label: "Database", icon: "🗄️" },
        { id: "backup", label: "Backup", icon: "💾" },
        { id: "system", label: "Sistema", icon: "📊" },
        { id: "utenti", label: "Utenti", icon: "👥" },
        { id: "permessi", label: "Permessi", icon: "🔒" },
        { id: "password", label: "Cambio Password", icon: "🔐" },
      ];
    }

    // OPERATORE: solo Cambio Password
    return baseTabs;
  };

  const tabs = getTabs();

  if (loading) {
    return (
      <div className="space-y-6">
        <Loading text="Caricamento impostazioni..." />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header Actions */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-800">
            {isAdmin ? "Impostazioni Sistema" : "Impostazioni"}
          </h1>
          <p className="text-sm text-slate-600">
            {isAdmin
              ? `Configurazione SERV.O ${systemInfo.version}`
              : `Gestione account - ${currentUser?.username}`
            }
          </p>
        </div>
        {/* Pulsanti salvataggio solo per admin */}
        {isAdmin && (
          <div className="flex gap-3">
            <Button variant="secondary" onClick={handleReset}>
              🔄 Reset Default
            </Button>
            <Button
              variant="primary"
              onClick={handleSave}
              loading={saving}
              disabled={saving}
            >
              💾 Salva Tutto
            </Button>
          </div>
        )}
      </div>

      {/* Main Content */}
      <div className="bg-white rounded-xl border border-slate-200">
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

        {/* Tab Generale - Solo Admin */}
        {activeTab === "general" && isAdmin && (
          <div className="p-6 space-y-6">
            {/* Email Notifiche */}
            <div>
              <h3 className="font-medium text-slate-800 mb-4">
                📧 Notifiche Email
              </h3>
              <div className="space-y-3">
                <label className="flex items-center justify-between p-3 bg-slate-50 rounded-lg cursor-pointer">
                  <div>
                    <p className="font-medium text-slate-800 text-sm">
                      Notifiche Generali
                    </p>
                    <p className="text-xs text-slate-500">
                      Ricevi notifiche per eventi importanti del sistema
                    </p>
                  </div>
                  <input
                    type="checkbox"
                    checked={settings.emailNotifications}
                    onChange={(e) =>
                      setSettings({
                        ...settings,
                        emailNotifications: e.target.checked,
                      })
                    }
                    className="w-4 h-4 text-blue-600 rounded"
                  />
                </label>

                <label className="flex items-center justify-between p-3 bg-slate-50 rounded-lg cursor-pointer">
                  <div>
                    <p className="font-medium text-slate-800 text-sm">
                      Notifiche Errori
                    </p>
                    <p className="text-xs text-slate-500">
                      Ricevi email immediate per errori critici
                    </p>
                  </div>
                  <input
                    type="checkbox"
                    checked={settings.emailOnError}
                    onChange={(e) =>
                      setSettings({
                        ...settings,
                        emailOnError: e.target.checked,
                      })
                    }
                    className="w-4 h-4 text-blue-600 rounded"
                  />
                </label>
              </div>
            </div>
          </div>
        )}

        {/* Tab Email - Solo Admin */}
        {activeTab === "email" && isAdmin && (
          <EmailTab />
        )}

        {/* Tab Automazione - Solo Admin */}
        {activeTab === "automation" && isAdmin && (
          <div className="p-6 space-y-6">
            {/* Validazione Automatica */}
            <div>
              <h3 className="font-medium text-slate-800 mb-4">
                🤖 Automazione Ordini
              </h3>
              <div className="space-y-3">
                <label className="flex items-center justify-between p-3 bg-slate-50 rounded-lg cursor-pointer">
                  <div>
                    <p className="font-medium text-slate-800 text-sm">
                      Auto-Validazione
                    </p>
                    <p className="text-xs text-slate-500">
                      Valida automaticamente ordini con lookup PIVA perfetto
                    </p>
                  </div>
                  <input
                    type="checkbox"
                    checked={settings.autoValidate}
                    onChange={(e) =>
                      setSettings({
                        ...settings,
                        autoValidate: e.target.checked,
                      })
                    }
                    className="w-4 h-4 text-blue-600 rounded"
                  />
                </label>
              </div>
            </div>

            {/* Machine Learning */}
            <div>
              <h3 className="font-medium text-slate-800 mb-4">
                🧠 Machine Learning
              </h3>
              <div className="space-y-3">
                <label className="flex items-center justify-between p-3 bg-slate-50 rounded-lg cursor-pointer">
                  <div>
                    <p className="font-medium text-slate-800 text-sm">
                      Approvazione ML Automatica
                    </p>
                    <p className="text-xs text-slate-500">
                      Applica automaticamente pattern ML con alta confidenza
                    </p>
                  </div>
                  <input
                    type="checkbox"
                    checked={settings.mlAutoApprove}
                    onChange={(e) =>
                      setSettings({
                        ...settings,
                        mlAutoApprove: e.target.checked,
                      })
                    }
                    className="w-4 h-4 text-blue-600 rounded"
                  />
                </label>

                {settings.mlAutoApprove && (
                  <div className="ml-4 p-3 border-l-2 border-blue-200 bg-blue-50">
                    <label className="block text-sm text-slate-600 mb-2">
                      Soglia Confidenza ML (%)
                    </label>
                    <input
                      type="range"
                      min="50"
                      max="100"
                      value={settings.mlMinConfidence}
                      onChange={(e) =>
                        setSettings({
                          ...settings,
                          mlMinConfidence: parseInt(e.target.value),
                        })
                      }
                      className="w-full"
                    />
                    <div className="flex justify-between text-xs text-slate-500 mt-1">
                      <span>50%</span>
                      <span className="font-medium text-blue-600">
                        {settings.mlMinConfidence}%
                      </span>
                      <span>100%</span>
                    </div>
                    <p className="text-xs text-slate-600 mt-2">
                      Pattern con confidenza ≥ {settings.mlMinConfidence}%
                      verranno approvati automaticamente
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Tab Database - Solo Admin */}
        {activeTab === "database" && isAdmin && (
          <div className="p-6 space-y-6">
            {/* Backup */}
            <div>
              <h3 className="font-medium text-slate-800 mb-4">
                💾 Backup e Sicurezza
              </h3>
              <div className="space-y-3">
                <label className="flex items-center justify-between p-3 bg-slate-50 rounded-lg cursor-pointer">
                  <div>
                    <p className="font-medium text-slate-800 text-sm">
                      Backup Automatico
                    </p>
                    <p className="text-xs text-slate-500">
                      Esegui backup quotidiano automatico del database
                    </p>
                  </div>
                  <input
                    type="checkbox"
                    checked={settings.autoBackup}
                    onChange={(e) =>
                      setSettings({ ...settings, autoBackup: e.target.checked })
                    }
                    className="w-4 h-4 text-blue-600 rounded"
                  />
                </label>

                {settings.autoBackup && (
                  <div className="ml-4 p-3 border-l-2 border-green-200 bg-green-50">
                    <label className="block text-sm text-slate-600 mb-2">
                      Retention Backup (giorni)
                    </label>
                    <input
                      type="number"
                      value={settings.backupRetention}
                      onChange={(e) =>
                        setSettings({
                          ...settings,
                          backupRetention: parseInt(e.target.value),
                        })
                      }
                      className="w-24 px-2 py-1 border border-slate-200 rounded text-sm"
                      min="1"
                      max="365"
                    />
                    <p className="text-xs text-slate-600 mt-1">
                      Mantieni backup per {settings.backupRetention} giorni
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Azioni Database */}
            <div>
              <h3 className="font-medium text-slate-800 mb-4">
                📤 Import Anagrafiche
              </h3>
              <div className="space-y-4">
                {/* Import Farmacie */}
                <div className={`p-4 border rounded-lg ${anagraficaStats.farmacie?.totale > 0 ? 'border-green-300 bg-green-50/30' : 'border-slate-200'}`}>
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="text-sm font-medium text-slate-800">
                      Import Farmacie
                    </h4>
                    {anagraficaStats.farmacie?.totale > 0 ? (
                      <span className="px-2 py-1 bg-green-100 text-green-700 text-xs font-medium rounded-full flex items-center gap-1">
                        ✅ CSV Caricato
                      </span>
                    ) : (
                      <StatusBadge status="info" label="CSV" size="xs" />
                    )}
                  </div>
                  <div className="flex items-center gap-3">
                    <label className="cursor-pointer">
                      <input
                        type="file"
                        accept=".csv"
                        className="hidden"
                        onChange={handleImportFarmacie}
                        disabled={importProgress?.type === "farmacie"}
                      />
                      <Button
                        variant={anagraficaStats.farmacie?.totale > 0 ? "primary" : "secondary"}
                        size="sm"
                        as="span"
                        disabled={importProgress?.type === "farmacie"}
                        className={anagraficaStats.farmacie?.totale > 0 ? "bg-green-600 hover:bg-green-700" : ""}
                      >
                        📁 Seleziona CSV Farmacie
                      </Button>
                    </label>
                    <div className="flex-1">
                      <p className="text-xs text-slate-600 font-medium">
                        Registro Ministeriale Farmacie
                      </p>
                      <p className="text-xs text-slate-500">
                        Formato: MIN_ID, Ragione Sociale, P.IVA, Indirizzo, CAP,
                        Città...
                      </p>
                    </div>
                  </div>
                  {/* Legenda versione caricata */}
                  {anagraficaStats.farmacie?.totale > 0 && (
                    <div className="mt-3 pt-3 border-t border-green-200">
                      <div className="flex items-center gap-4 text-xs">
                        <div className="flex items-center gap-1.5">
                          <span className="text-green-600">🏥</span>
                          <span className="text-slate-600">Record:</span>
                          <span className="font-mono font-medium text-green-700">{anagraficaStats.farmacie.totale.toLocaleString()}</span>
                        </div>
                        {anagraficaStats.farmacie.last_import && (
                          <div className="flex items-center gap-1.5">
                            <span className="text-green-600">📅</span>
                            <span className="text-slate-600">Ultimo import:</span>
                            <span className="font-mono font-medium text-green-700">
                              {new Date(anagraficaStats.farmacie.last_import).toLocaleDateString('it-IT', {
                                day: '2-digit',
                                month: '2-digit',
                                year: 'numeric',
                                hour: '2-digit',
                                minute: '2-digit'
                              })}
                            </span>
                          </div>
                        )}
                        {anagraficaStats.farmacie.filename && (
                          <div className="flex items-center gap-1.5">
                            <span className="text-green-600">📄</span>
                            <span className="text-slate-600">File:</span>
                            <span className="font-mono font-medium text-green-700 truncate max-w-[200px]" title={anagraficaStats.farmacie.filename}>
                              {anagraficaStats.farmacie.filename}
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>

                {/* Import Parafarmacie */}
                <div className={`p-4 border rounded-lg ${anagraficaStats.parafarmacie?.totale > 0 ? 'border-green-300 bg-green-50/30' : 'border-slate-200'}`}>
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="text-sm font-medium text-slate-800">
                      Import Parafarmacie
                    </h4>
                    {anagraficaStats.parafarmacie?.totale > 0 ? (
                      <span className="px-2 py-1 bg-green-100 text-green-700 text-xs font-medium rounded-full flex items-center gap-1">
                        ✅ CSV Caricato
                      </span>
                    ) : (
                      <StatusBadge status="info" label="CSV" size="xs" />
                    )}
                  </div>
                  <div className="flex items-center gap-3">
                    <label className="cursor-pointer">
                      <input
                        type="file"
                        accept=".csv"
                        className="hidden"
                        onChange={handleImportParafarmacie}
                        disabled={importProgress?.type === "parafarmacie"}
                      />
                      <Button
                        variant={anagraficaStats.parafarmacie?.totale > 0 ? "primary" : "secondary"}
                        size="sm"
                        as="span"
                        disabled={importProgress?.type === "parafarmacie"}
                        className={anagraficaStats.parafarmacie?.totale > 0 ? "bg-green-600 hover:bg-green-700" : ""}
                      >
                        📁 Seleziona CSV Parafarmacie
                      </Button>
                    </label>
                    <div className="flex-1">
                      <p className="text-xs text-slate-600 font-medium">
                        Registro Ministeriale Parafarmacie
                      </p>
                      <p className="text-xs text-slate-500">
                        Formato: Codice Sito, Sito Logistico, P.IVA, Regione...
                      </p>
                    </div>
                  </div>
                  {/* Legenda versione caricata */}
                  {anagraficaStats.parafarmacie?.totale > 0 && (
                    <div className="mt-3 pt-3 border-t border-green-200">
                      <div className="flex items-center gap-4 text-xs">
                        <div className="flex items-center gap-1.5">
                          <span className="text-green-600">💊</span>
                          <span className="text-slate-600">Record:</span>
                          <span className="font-mono font-medium text-green-700">{anagraficaStats.parafarmacie.totale.toLocaleString()}</span>
                        </div>
                        {anagraficaStats.parafarmacie.last_import && (
                          <div className="flex items-center gap-1.5">
                            <span className="text-green-600">📅</span>
                            <span className="text-slate-600">Ultimo import:</span>
                            <span className="font-mono font-medium text-green-700">
                              {new Date(anagraficaStats.parafarmacie.last_import).toLocaleDateString('it-IT', {
                                day: '2-digit',
                                month: '2-digit',
                                year: 'numeric',
                                hour: '2-digit',
                                minute: '2-digit'
                              })}
                            </span>
                          </div>
                        )}
                        {anagraficaStats.parafarmacie.filename && (
                          <div className="flex items-center gap-1.5">
                            <span className="text-green-600">📄</span>
                            <span className="text-slate-600">File:</span>
                            <span className="font-mono font-medium text-green-700 truncate max-w-[200px]" title={anagraficaStats.parafarmacie.filename}>
                              {anagraficaStats.parafarmacie.filename}
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>

                {/* Import Clienti */}
                <div className={`p-4 border rounded-lg ${anagraficaStats.clienti?.totale > 0 ? 'border-purple-300 bg-purple-50/30' : 'border-slate-200'}`}>
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="text-sm font-medium text-slate-800">
                      Import Clienti
                    </h4>
                    {anagraficaStats.clienti?.totale > 0 ? (
                      <span className="px-2 py-1 bg-purple-100 text-purple-700 text-xs font-medium rounded-full flex items-center gap-1">
                        CSV Caricato
                      </span>
                    ) : (
                      <StatusBadge status="info" label="CSV" size="xs" />
                    )}
                  </div>
                  <div className="flex items-center gap-3">
                    <label className="cursor-pointer">
                      <input
                        type="file"
                        accept=".csv"
                        className="hidden"
                        onChange={handleImportClienti}
                        disabled={importProgress?.type === "clienti"}
                      />
                      <Button
                        variant={anagraficaStats.clienti?.totale > 0 ? "primary" : "secondary"}
                        size="sm"
                        as="span"
                        disabled={importProgress?.type === "clienti"}
                        className={anagraficaStats.clienti?.totale > 0 ? "bg-purple-600 hover:bg-purple-700" : ""}
                      >
                        Seleziona CSV Clienti
                      </Button>
                    </label>
                    <div className="flex-1">
                      <p className="text-xs text-slate-600 font-medium">
                        Anagrafica Clienti Esterna
                      </p>
                      <p className="text-xs text-slate-500">
                        Formato: AGCANA, AGRSO1, AGRSO2, AGINDI, AGCAP, AGLOCA...
                      </p>
                    </div>
                  </div>
                  {/* Legenda versione caricata */}
                  {anagraficaStats.clienti?.totale > 0 && (
                    <div className="mt-3 pt-3 border-t border-purple-200">
                      <div className="flex items-center gap-4 text-xs">
                        <div className="flex items-center gap-1.5">
                          <span className="text-purple-600">Clienti</span>
                          <span className="text-slate-600">Record:</span>
                          <span className="font-mono font-medium text-purple-700">{anagraficaStats.clienti.totale.toLocaleString()}</span>
                        </div>
                        {anagraficaStats.clienti.last_import && (
                          <div className="flex items-center gap-1.5">
                            <span className="text-purple-600">Ultimo import:</span>
                            <span className="font-mono font-medium text-purple-700">
                              {new Date(anagraficaStats.clienti.last_import).toLocaleDateString('it-IT', {
                                day: '2-digit',
                                month: '2-digit',
                                year: 'numeric',
                                hour: '2-digit',
                                minute: '2-digit'
                              })}
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>

                {/* Import Listino CODIFI */}
                <div className={`p-4 border rounded-lg ${listiniStats.CODIFI?.count > 0 ? 'border-blue-300 bg-blue-50/30' : 'border-slate-200'}`}>
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="text-sm font-medium text-slate-800">
                      Import Listino Prezzi CODIFI
                    </h4>
                    {listiniStats.CODIFI?.count > 0 ? (
                      <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs font-medium rounded-full flex items-center gap-1">
                        ✅ CSV Caricato
                      </span>
                    ) : (
                      <StatusBadge status="warning" label="CSV Mancante" size="xs" />
                    )}
                  </div>
                  <div className="flex items-center gap-3">
                    <label className="cursor-pointer">
                      <input
                        type="file"
                        accept=".csv"
                        className="hidden"
                        onChange={(e) => handleImportListino(e, 'CODIFI')}
                        disabled={importProgress?.type === "listino_CODIFI"}
                      />
                      <Button
                        variant={listiniStats.CODIFI?.count > 0 ? "primary" : "warning"}
                        size="sm"
                        as="span"
                        disabled={importProgress?.type === "listino_CODIFI"}
                        className={listiniStats.CODIFI?.count > 0 ? "bg-blue-600 hover:bg-blue-700" : "bg-amber-500 hover:bg-amber-600"}
                      >
                        📁 Seleziona CSV Listino CODIFI
                      </Button>
                    </label>
                    <div className="flex-1">
                      <p className="text-xs text-slate-600 font-medium">
                        Listino Prezzi Vendor CODIFI
                      </p>
                      <p className="text-xs text-slate-500">
                        Colonne: AFCODI (AIC), CVDPRO, CVPVEN, AFPEU1, CVSCO1, AFAIVA...
                      </p>
                    </div>
                  </div>
                  {/* Legenda versione caricata */}
                  {listiniStats.CODIFI?.count > 0 && (
                    <div className="mt-3 pt-3 border-t border-blue-200">
                      <div className="flex items-center gap-4 text-xs">
                        <div className="flex items-center gap-1.5">
                          <span className="text-blue-600">💊</span>
                          <span className="text-slate-600">Prodotti:</span>
                          <span className="font-mono font-medium text-blue-700">{listiniStats.CODIFI.count.toLocaleString()}</span>
                        </div>
                        {listiniStats.CODIFI.last_import && (
                          <div className="flex items-center gap-1.5">
                            <span className="text-blue-600">📅</span>
                            <span className="text-slate-600">Ultimo import:</span>
                            <span className="font-mono font-medium text-blue-700">
                              {new Date(listiniStats.CODIFI.last_import).toLocaleDateString('it-IT', {
                                day: '2-digit',
                                month: '2-digit',
                                year: 'numeric',
                                hour: '2-digit',
                                minute: '2-digit'
                              })}
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>

                {/* Progress Import */}
                {importProgress && (
                  <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <p className="text-sm font-medium text-blue-800">
                        Importazione {importProgress.type}...
                      </p>
                      <span className="text-sm font-mono font-medium text-blue-700">
                        {importProgress.progress}%
                      </span>
                    </div>
                    <div className="w-full h-2 bg-blue-200 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-blue-600 rounded-full transition-all duration-300"
                        style={{ width: `${importProgress.progress}%` }}
                      />
                    </div>
                    <p className="text-xs text-blue-600 mt-2">
                      Elaborazione file CSV in corso... Non chiudere la pagina.
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Sincronizzazione Anagrafica Ministero (v8.2) */}
            <div>
              <h3 className="font-medium text-slate-800 mb-4">
                🔄 Sincronizzazione Anagrafica Ministero
              </h3>
              <div className="p-4 border border-indigo-200 rounded-lg bg-indigo-50/30">
                <p className="text-xs text-slate-600 mb-4">
                  Sincronizza automaticamente farmacie e parafarmacie dal portale Open Data del Ministero della Salute.
                  Il sistema scarica solo se ci sono aggiornamenti (HTTP 304).
                </p>

                {/* Status Cards */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                  {/* Farmacie */}
                  <div className={`p-3 rounded-lg border ${syncStatus.farmacie?.needs_update ? 'border-amber-300 bg-amber-50' : 'border-green-200 bg-green-50/50'}`}>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-slate-700">🏥 Farmacie</span>
                      {syncStatus.farmacie?.needs_update ? (
                        <span className="px-2 py-0.5 bg-amber-100 text-amber-700 text-xs font-medium rounded-full">
                          Aggiornamento disponibile
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs font-medium rounded-full">
                          Aggiornato
                        </span>
                      )}
                    </div>
                    <div className="space-y-1 text-xs text-slate-600">
                      <div className="flex justify-between">
                        <span>Record:</span>
                        <span className="font-mono font-medium">{syncStatus.farmacie?.records_count?.toLocaleString() || 0}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Ultimo sync:</span>
                        <span className="font-mono">
                          {syncStatus.farmacie?.last_sync
                            ? new Date(syncStatus.farmacie.last_sync + (syncStatus.farmacie.last_sync.includes('Z') ? '' : 'Z')).toLocaleDateString('it-IT', {
                                day: '2-digit', month: '2-digit', year: 'numeric',
                                hour: '2-digit', minute: '2-digit'
                              })
                            : 'Mai'}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Parafarmacie */}
                  <div className={`p-3 rounded-lg border ${syncStatus.parafarmacie?.needs_update ? 'border-amber-300 bg-amber-50' : 'border-green-200 bg-green-50/50'}`}>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-slate-700">💊 Parafarmacie</span>
                      {syncStatus.parafarmacie?.needs_update ? (
                        <span className="px-2 py-0.5 bg-amber-100 text-amber-700 text-xs font-medium rounded-full">
                          Aggiornamento disponibile
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs font-medium rounded-full">
                          Aggiornato
                        </span>
                      )}
                    </div>
                    <div className="space-y-1 text-xs text-slate-600">
                      <div className="flex justify-between">
                        <span>Record:</span>
                        <span className="font-mono font-medium">{syncStatus.parafarmacie?.records_count?.toLocaleString() || 0}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Ultimo sync:</span>
                        <span className="font-mono">
                          {syncStatus.parafarmacie?.last_sync
                            ? new Date(syncStatus.parafarmacie.last_sync + (syncStatus.parafarmacie.last_sync.includes('Z') ? '' : 'Z')).toLocaleDateString('it-IT', {
                                day: '2-digit', month: '2-digit', year: 'numeric',
                                hour: '2-digit', minute: '2-digit'
                              })
                            : 'Mai'}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Sync Buttons */}
                <div className="flex flex-wrap gap-2">
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => handleSync('all')}
                    disabled={syncLoading}
                    className="bg-indigo-600 hover:bg-indigo-700"
                  >
                    {syncLoading ? '⏳ Sincronizzazione...' : '🔄 Sincronizza Tutto'}
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => handleSync('farmacie')}
                    disabled={syncLoading}
                  >
                    Solo Farmacie
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => handleSync('parafarmacie')}
                    disabled={syncLoading}
                  >
                    Solo Parafarmacie
                  </Button>
                </div>

                {syncLoading && (
                  <div className="mt-3 p-3 bg-indigo-100 rounded-lg">
                    <div className="flex items-center gap-2 text-sm text-indigo-700">
                      <div className="animate-spin h-4 w-4 border-2 border-indigo-600 border-t-transparent rounded-full"></div>
                      <span>Download e sincronizzazione in corso... (~60 secondi)</span>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Azioni Database */}
            <div>
              <h3 className="font-medium text-slate-800 mb-4">
                ⚠️ Azioni Database
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <Button
                  variant="primary"
                  onClick={() => handleDatabaseAction("backup")}
                >
                  💾 Backup Manuale
                </Button>

                <Button
                  variant="danger"
                  onClick={() => handleDatabaseAction("clear_farmacie")}
                >
                  🗑️ Pulisci Farmacie
                </Button>

                <Button
                  variant="danger"
                  onClick={() => handleDatabaseAction("clear_parafarmacie")}
                >
                  🗑️ Pulisci Parafarmacie
                </Button>

                <Button
                  variant="danger"
                  onClick={() => handleDatabaseAction("clear_ordini")}
                >
                  🗑️ Pulisci Ordini
                </Button>
              </div>

              {/* Reset Completo - Sezione separata per evidenziare pericolosità */}
              <div className="mt-6 p-4 bg-red-50 border-2 border-red-200 rounded-lg">
                <div className="flex items-start gap-3 mb-3">
                  <div className="w-6 h-6 bg-red-500 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="text-white text-xs font-bold">!</span>
                  </div>
                  <div>
                    <h4 className="font-medium text-red-800 text-sm mb-1">
                      Reset Completo Sistema
                    </h4>
                    <p className="text-xs text-red-700 mb-3">
                      Elimina tutti i dati tranne le anagrafiche farmacie e
                      parafarmacie. Include ordini, PDF, anomalie, tracciati,
                      cache e log.
                    </p>

                    <div className="bg-red-100 rounded p-2 mb-3">
                      <p className="text-xs text-red-800 font-medium mb-1">
                        PRESERVA:
                      </p>
                      <p className="text-xs text-red-700">
                        Anagrafica Farmacie - Anagrafica Parafarmacie - Anagrafica Clienti - Listini Prezzi
                      </p>
                    </div>

                    <div className="bg-white rounded p-2 border border-red-200">
                      <p className="text-xs text-red-800 font-medium mb-1">
                        🚨 ELIMINA:
                      </p>
                      <p className="text-xs text-red-700">
                        • Tutti gli ordini • PDF caricati • Anomalie •
                        Supervisioni • Tracciati • Cache applicativa • Log
                        sistema
                      </p>
                    </div>
                  </div>
                </div>

                <Button
                  variant="danger"
                  size="sm"
                  onClick={() => handleDatabaseAction("reset_complete")}
                  className="w-full font-bold"
                >
                  🚨 RESET COMPLETO SISTEMA
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Tab Backup - Solo Admin */}
        {activeTab === "backup" && isAdmin && (
          <div className="p-0">
            <BackupPage currentUser={currentUser} embedded={true} />
          </div>
        )}

        {/* Tab Sistema - Solo Admin */}
        {activeTab === "system" && isAdmin && (
          <div className="p-6 space-y-6">
            {/* Info Sistema */}
            <div>
              <h3 className="font-medium text-slate-800 mb-4">
                📊 Informazioni Sistema
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-3">
                  <div className="flex justify-between py-2 border-b border-slate-100">
                    <span className="text-sm text-slate-600">Versione</span>
                    <span className="text-sm font-mono font-medium">
                      {systemInfo.version}
                    </span>
                  </div>
                  <div className="flex justify-between py-2 border-b border-slate-100">
                    <span className="text-sm text-slate-600">Uptime</span>
                    <span className="text-sm font-mono font-medium">
                      {systemInfo.uptime}
                    </span>
                  </div>
                  <div className="flex justify-between py-2 border-b border-slate-100">
                    <span className="text-sm text-slate-600">
                      Database Size
                    </span>
                    <span className="text-sm font-mono font-medium">
                      {systemInfo.database_size}
                    </span>
                  </div>
                </div>

                <div className="space-y-3">
                  <div className="flex justify-between py-2 border-b border-slate-100">
                    <span className="text-sm text-slate-600">
                      PDF Processati
                    </span>
                    <span className="text-sm font-mono font-medium">
                      {systemInfo.pdf_count.toLocaleString()}
                    </span>
                  </div>
                  <div className="flex justify-between py-2 border-b border-slate-100">
                    <span className="text-sm text-slate-600">
                      Ordini Totali
                    </span>
                    <span className="text-sm font-mono font-medium">
                      {systemInfo.orders_count.toLocaleString()}
                    </span>
                  </div>
                  <div className="flex justify-between py-2 border-b border-slate-100">
                    <span className="text-sm text-slate-600">
                      Ultimo Backup
                    </span>
                    <span className="text-sm font-mono font-medium">
                      {systemInfo.last_backup || "Mai"}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Debug e Log */}
            <div>
              <h3 className="font-medium text-slate-800 mb-4">
                🔧 Debug e Logging
              </h3>
              <div className="space-y-3">
                <label className="flex items-center justify-between p-3 bg-slate-50 rounded-lg cursor-pointer">
                  <div>
                    <p className="font-medium text-slate-800 text-sm">
                      Modalità Debug
                    </p>
                    <p className="text-xs text-slate-500">
                      Abilita logging dettagliato per troubleshooting
                    </p>
                  </div>
                  <input
                    type="checkbox"
                    checked={settings.debugMode}
                    onChange={(e) =>
                      setSettings({ ...settings, debugMode: e.target.checked })
                    }
                    className="w-4 h-4 text-blue-600 rounded"
                  />
                </label>

                <div className="flex justify-between items-center">
                  <div>
                    <label className="block text-sm text-slate-600 mb-1">
                      Livello Log
                    </label>
                    <select
                      value={settings.logLevel}
                      onChange={(e) =>
                        setSettings({ ...settings, logLevel: e.target.value })
                      }
                      className="px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="DEBUG">DEBUG</option>
                      <option value="INFO">INFO</option>
                      <option value="WARNING">WARNING</option>
                      <option value="ERROR">ERROR</option>
                    </select>
                  </div>

                  <Button variant="secondary" onClick={handleDownloadLogs}>
                    📄 Download Log
                  </Button>
                </div>
              </div>
            </div>

            {/* Status Servizi */}
            <div>
              <h3 className="font-medium text-slate-800 mb-4">
                🟢 Status Servizi
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div className="flex items-center justify-between p-3 bg-emerald-50 rounded-lg">
                  <span className="text-sm font-medium">Database</span>
                  <StatusBadge status="completed" label="Online" size="xs" />
                </div>
                <div className="flex items-center justify-between p-3 bg-emerald-50 rounded-lg">
                  <span className="text-sm font-medium">API Server</span>
                  <StatusBadge status="completed" label="Running" size="xs" />
                </div>
                <div className="flex items-center justify-between p-3 bg-amber-50 rounded-lg">
                  <span className="text-sm font-medium">Email Service</span>
                  <StatusBadge status="pending" label="Idle" size="xs" />
                </div>
                <div className="flex items-center justify-between p-3 bg-emerald-50 rounded-lg">
                  <span className="text-sm font-medium">ML Engine</span>
                  <StatusBadge status="completed" label="Active" size="xs" />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tab Utenti - Solo per admin/supervisore */}
        {activeTab === "utenti" && isAdminOrSupervisor && (
          <div className="p-0">
            <UtentiPage currentUser={currentUser} />
          </div>
        )}

        {/* Tab Permessi - Solo Admin */}
        {activeTab === "permessi" && isAdmin && (
          <div className="p-0">
            <PermessiTab />
          </div>
        )}

        {/* Tab Cambio Password - Visibile a tutti */}
        {activeTab === "password" && (
          <div className="p-6 space-y-6">
            {/* Account - Cambio Password */}
            <div>
              <h3 className="font-medium text-slate-800 mb-4">
                🔐 Il Mio Account
              </h3>
              <div className="p-4 bg-slate-50 rounded-lg space-y-4">
                <div className="flex items-center gap-4 mb-4">
                  <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center text-xl">
                    👤
                  </div>
                  <div>
                    <p className="font-medium text-slate-800">{currentUser?.username}</p>
                    <p className="text-sm text-slate-500 capitalize">{currentUser?.ruolo}</p>
                    {currentUser?.email && (
                      <p className="text-xs text-slate-400">{currentUser?.email}</p>
                    )}
                  </div>
                </div>

                <div className="border-t border-slate-200 pt-4">
                  <p className="text-sm font-medium text-slate-700 mb-3">Cambia Password</p>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    <div>
                      <label className="block text-xs text-slate-600 mb-1">Password Attuale</label>
                      <input
                        type="password"
                        value={passwordForm.vecchia_password}
                        onChange={(e) => setPasswordForm({...passwordForm, vecchia_password: e.target.value})}
                        className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="••••••••"
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-slate-600 mb-1">Nuova Password</label>
                      <input
                        type="password"
                        value={passwordForm.nuova_password}
                        onChange={(e) => setPasswordForm({...passwordForm, nuova_password: e.target.value})}
                        className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="Min. 6 caratteri"
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-slate-600 mb-1">Conferma Password</label>
                      <input
                        type="password"
                        value={passwordForm.conferma_password}
                        onChange={(e) => setPasswordForm({...passwordForm, conferma_password: e.target.value})}
                        className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="Ripeti password"
                      />
                    </div>
                  </div>
                  <div className="mt-3">
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={handleChangePassword}
                      loading={changingPassword}
                      disabled={changingPassword}
                    >
                      🔑 Cambia Password
                    </Button>
                  </div>
                </div>
              </div>
            </div>

            {/* Info sessione corrente */}
            <div className="p-4 border border-slate-200 rounded-lg">
              <h4 className="text-sm font-medium text-slate-700 mb-2">Sessione Corrente</h4>
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse" />
                <span className="text-xs text-slate-600">Connesso</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default SettingsPage;
