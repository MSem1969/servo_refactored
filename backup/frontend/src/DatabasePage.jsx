// =============================================================================
// DATABASE PAGE - MODERNIZZATA v6.2
// =============================================================================
// Pagina database ordini con tabella, filtri, selezione multipla, azioni batch
// =============================================================================

import React, { useState, useEffect, useCallback } from 'react';
import { ordiniApi, anomalieApi, lookupApi } from './api';
import { Button, StatusBadge, VendorBadge, Loading, ErrorBox } from './common';
// v6.2: Componenti condivisi
import { AnomaliaDetailModal, StatCard, StatCardGrid, TipoAnomaliaBadge, StatoAnomaliaBadge } from './components';

/**
 * Componente DatabasePage modernizzato
 * 
 * LOGICA IMPLEMENTATIVA:
 * - Tabella ordini con filtri avanzati
 * - Selezione multipla per azioni batch
 * - Stati ordini con color coding
 * - Navigazione verso dettaglio ordine
 * - Gestione urgenza consegna con highlighting
 * 
 * INTERRELAZIONI:
 * - API: ordiniApi.getList(), ordiniApi.batchDelete()
 * - Componenti: Button, StatusBadge, VendorBadge, Loading, ErrorBox
 * - Navigazione: onOpenOrdine per dettaglio
 */
const DatabasePage = ({ currentUser, onOpenOrdine }) => {
  const [activeTab, setActiveTab] = useState('ordini');
  const [ordini, setOrdini] = useState([]);
  const [selectedOrdine, setSelectedOrdine] = useState(null);
  const [righe, setRighe] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    vendor: '',
    stato: '',
    q: '',
    data_da: '',
    data_a: ''
  });
  const [selected, setSelected] = useState([]);
  const [validatingBatch, setValidatingBatch] = useState(false);
  const [stats, setStats] = useState({
    ordini: 0,
    confermati: 0,
    parzEvaso: 0,
    evaso: 0,
    archiviati: 0,
    anomalie_aperte: 0
  });

  // State per modal PDF
  const [showPdfModal, setShowPdfModal] = useState(false);
  const [pdfToShow, setPdfToShow] = useState(null);

  // Stati per tab Anomalie
  const [anomalieList, setAnomalieList] = useState([]);
  const [loadingAnomalies, setLoadingAnomalies] = useState(false);
  const [selectedAnomalies, setSelectedAnomalies] = useState([]);
  const [anomalieFilters, setAnomalieFilters] = useState({
    tipo: '',
    stato: '',
    vendor: ''
  });

  // v6.2: Stati per modal dettaglio anomalia (refactored)
  const [showAnomaliaDetailModal, setShowAnomaliaDetailModal] = useState(false);
  const [anomaliaDetail, setAnomaliaDetail] = useState(null);
  const [loadingAnomaliaDetail, setLoadingAnomaliaDetail] = useState(false);

  // Helper per data consegna e urgenza
  const addBusinessDays = (date, days) => {
    const result = new Date(date);
    let addedDays = 0;
    
    while (addedDays < days) {
      result.setDate(result.getDate() + 1);
      const dayOfWeek = result.getDay();
      if (dayOfWeek !== 0 && dayOfWeek !== 6) {
        addedDays++;
      }
    }
    return result;
  };

  const parseDataConsegna = (dataStr, dataOrdineStr) => {
    if (!dataStr) {
      if (dataOrdineStr) {
        const dataOrdine = new Date(dataOrdineStr);
        return addBusinessDays(dataOrdine, 10);
      }
      return new Date();
    }

    if (typeof dataStr === 'string') {
      if (dataStr.includes('/')) {
        const [day, month, year] = dataStr.split('/');
        return new Date(year, month - 1, day);
      }
      if (dataStr.includes('-')) {
        return new Date(dataStr);
      }
    }
    
    return new Date(dataStr);
  };

  const getUrgenza = (dataConsegnaStr, dataOrdineStr) => {
    const dataConsegna = parseDataConsegna(dataConsegnaStr, dataOrdineStr);
    const oggi = new Date();
    oggi.setHours(0, 0, 0, 0);
    dataConsegna.setHours(0, 0, 0, 0);

    const diffDays = Math.ceil((dataConsegna - oggi) / (1000 * 60 * 60 * 24));
    
    if (diffDays < 0) return 'SCADUTO';
    if (diffDays <= 2) return 'URGENTE';
    return 'ORDINARIO';
  };

  // Formatta data per display DD/MM/YYYY
  const formatDataForDisplay = (dataStr) => {
    if (!dataStr) return '-';
    if (dataStr.includes('/')) return dataStr;
    if (dataStr.includes('-')) {
      const [anno, mese, giorno] = dataStr.split('-');
      return `${giorno}/${mese}/${anno}`;
    }
    return dataStr;
  };

  // Componente DeliveryBadge per stato urgenza consegna
  const DeliveryBadge = ({ dataConsegna, dataOrdine }) => {
    if (!dataConsegna && !dataOrdine) {
      return <span className="text-slate-400 text-xs">-</span>;
    }

    const urgenza = getUrgenza(dataConsegna, dataOrdine);
    const data = parseDataConsegna(dataConsegna, dataOrdine);
    const displayDate = data.toLocaleDateString('it-IT', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric'
    });

    // Stato ORDINARIO: rendering minimale
    if (urgenza === 'ORDINARIO') {
      return (
        <span className="text-emerald-600 font-mono text-xs flex items-center gap-1">
          <span>🟢</span>
          <span>{displayDate}</span>
        </span>
      );
    }

    // Stati SCADUTO o URGENTE: badge colorato con label
    const config = {
      SCADUTO: { label: 'SCADUTO', icon: '🔴', bgColor: 'bg-red-100', textColor: 'text-red-700' },
      URGENTE: { label: 'URGENTE', icon: '🟠', bgColor: 'bg-amber-100', textColor: 'text-amber-700' }
    };
    const { label, icon, bgColor, textColor } = config[urgenza];

    return (
      <div className="flex flex-col items-start gap-0.5">
        <span className={`px-1.5 py-0.5 text-xs font-semibold rounded-full ${bgColor} ${textColor} flex items-center gap-1`}>
          <span>{icon}</span>
          <span>{label}</span>
        </span>
        <span className={`text-xs font-mono ${textColor}`}>{displayDate}</span>
      </div>
    );
  };

  // Classe CSS per highlighting riga in base a urgenza
  const getRowHighlightClass = (dataConsegnaStr, dataOrdineStr) => {
    const urgenza = getUrgenza(dataConsegnaStr, dataOrdineStr);
    switch (urgenza) {
      case 'SCADUTO':
        return 'bg-red-50 border-l-4 border-l-red-500';
      case 'URGENTE':
        return 'bg-amber-50 border-l-4 border-l-amber-400';
      default:
        return '';
    }
  };

  // Carica ordini con filtri
  const loadOrdini = useCallback(async () => {
    try {
      setLoading(true);
      const queryParams = {
        ...filters,
        limit: 100
      };

      // Rimuovi filtri vuoti
      Object.keys(queryParams).forEach(key => {
        if (!queryParams[key]) delete queryParams[key];
      });

      // Carica ordini
      const res = await ordiniApi.getList(queryParams);

      if (res.success) {
        const ordiniData = res.data || [];
        setOrdini(ordiniData);

        // Calcola stats basati sugli stati degli ordini
        const newStats = {
          ordini: ordiniData.length,
          confermati: ordiniData.filter(o => o.stato === 'CONFERMATO').length,
          parzEvaso: ordiniData.filter(o => o.stato === 'PARZ_EVASO').length,
          evaso: ordiniData.filter(o => o.stato === 'EVASO').length,
          archiviati: ordiniData.filter(o => o.stato === 'ARCHIVIATO').length,
        };
        setStats(newStats);
      }
    } catch (err) {
      console.error('Errore caricamento ordini:', err);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    loadOrdini();
  }, [loadOrdini]);

  // Carica conteggio anomalie aperte all'avvio e quando si ricaricano gli ordini
  const loadAnomalieCount = useCallback(async () => {
    try {
      const res = await anomalieApi.getList({ stato: 'APERTA' });
      if (res.success) {
        setStats(prev => ({ ...prev, anomalie_aperte: (res.data || []).length }));
      }
    } catch (err) {
      console.error('Errore caricamento conteggio anomalie:', err);
    }
  }, []);

  useEffect(() => {
    loadAnomalieCount();
  }, [loadAnomalieCount]);

  // Carica righe ordine per dettaglio
  const loadRighe = async (ordine) => {
    setSelectedOrdine(ordine);
    try {
      const res = await ordiniApi.getRighe(ordine.id_testata);
      if (res.success) setRighe(res.data || []);
    } catch (err) {
      console.error('Errore caricamento righe:', err);
    }
  };

  // Carica lista anomalie dal backend
  const loadAnomalies = useCallback(async () => {
    setLoadingAnomalies(true);
    try {
      const params = {};
      if (anomalieFilters.tipo) params.tipo = anomalieFilters.tipo;
      if (anomalieFilters.stato) params.stato = anomalieFilters.stato;
      if (anomalieFilters.vendor) params.vendor = anomalieFilters.vendor;

      const res = await anomalieApi.getList(params);
      if (res.success) {
        setAnomalieList(res.data || []);
      } else {
        console.error('Errore caricamento anomalie:', res.error);
        setAnomalieList([]);
      }
    } catch (err) {
      console.error('Errore caricamento anomalie:', err);
      setAnomalieList([]);
    } finally {
      setLoadingAnomalies(false);
    }
  }, [anomalieFilters]);

  // Risolvi anomalie selezionate
  const handleResolveAnomalies = async () => {
    if (selectedAnomalies.length === 0) return;

    const nota = prompt('Nota di risoluzione (opzionale):');
    if (nota === null) return; // Annullato

    try {
      const res = await anomalieApi.batchRisolvi(selectedAnomalies, nota || 'Risolta manualmente');
      if (res.success) {
        alert(`Risolte ${res.resolved || selectedAnomalies.length} anomalie`);
        setSelectedAnomalies([]);
        loadAnomalies();
        loadAnomalieCount(); // Aggiorna conteggio
      }
    } catch (err) {
      alert('Errore: ' + err.message);
    }
  };

  // v6.2: Carica dettaglio anomalia con parent/child (refactored)
  const loadAnomaliaDetail = async (idAnomalia) => {
    setLoadingAnomaliaDetail(true);
    setShowAnomaliaDetailModal(true);
    try {
      const res = await anomalieApi.getDettaglio(idAnomalia);
      if (res.success) {
        setAnomaliaDetail(res.data);
      }
    } catch (err) {
      console.error('Errore caricamento dettaglio anomalia:', err);
      alert('Errore caricamento dettaglio: ' + err.message);
      setShowAnomaliaDetailModal(false);
    } finally {
      setLoadingAnomaliaDetail(false);
    }
  };

  // v6.2: Salva modifiche riga parent (adattato per nuovo componente)
  const handleSaveRigaParent = async (editingData) => {
    if (!anomaliaDetail?.anomalia?.id_anomalia) return false;

    try {
      const res = await anomalieApi.modificaRiga(anomaliaDetail.anomalia.id_anomalia, editingData);
      if (res.success) {
        alert('Riga aggiornata');
        // Ricarica dettaglio
        await loadAnomaliaDetail(anomaliaDetail.anomalia.id_anomalia);
        return true;
      }
      return false;
    } catch (err) {
      alert('Errore: ' + err.message);
      return false;
    }
  };

  // v6.2: Risolvi anomalia da dettaglio
  const handleRisolviAnomaliaDetail = async () => {
    if (!anomaliaDetail?.anomalia?.id_anomalia) return;

    const nota = prompt('Nota di risoluzione (opzionale):');
    if (nota === null) return;

    try {
      const res = await anomalieApi.risolviDettaglio(anomaliaDetail.anomalia.id_anomalia, nota || 'Risolta da dettaglio');
      if (res.success) {
        alert('Anomalia risolta');
        setShowAnomaliaDetailModal(false);
        setAnomaliaDetail(null);
        loadAnomalies();
        loadAnomalieCount(); // Aggiorna conteggio
      }
    } catch (err) {
      alert('Errore: ' + err.message);
    }
  };

  // v6.2: Assegna farmacia manualmente (da ricerca o MIN_ID manuale)
  const handleAssignFarmacia = async (idTestata, idFarmacia, idParafarmacia, minIdManuale = null) => {
    try {
      const res = await lookupApi.manuale(idTestata, idFarmacia, idParafarmacia, minIdManuale);
      if (res.success) {
        alert(minIdManuale ? `MIN_ID ${minIdManuale} assegnato` : 'Farmacia assegnata');
        // Ricarica dati e chiudi modale
        setShowAnomaliaDetailModal(false);
        setAnomaliaDetail(null);
        loadAnomalies();
        loadAnomalieCount(); // Aggiorna conteggio
        if (activeTab === 'ordini') {
          loadOrdini();
        }
        return true;
      }
      return false;
    } catch (err) {
      alert('Errore: ' + err.message);
      return false;
    }
  };

  // Carica anomalie quando si seleziona il tab
  useEffect(() => {
    if (activeTab === 'anomalie') {
      loadAnomalies();
    }
  }, [activeTab, loadAnomalies]);

  // Gestione selezione multipla
  const toggleSelect = (id) => {
    setSelected((prev) => {
      const isCurrentlySelected = prev.includes(id);
      if (isCurrentlySelected) {
        // Se deselezioniamo, pulisci anche selectedOrdine se era questo
        if (selectedOrdine?.id_testata === id) {
          setSelectedOrdine(null);
          setRighe([]);
        }
        return prev.filter((x) => x !== id);
      } else {
        // Seleziona e imposta come ordine corrente per il tab Dettaglio
        const ordine = ordini.find(o => o.id_testata === id);
        if (ordine) {
          setSelectedOrdine(ordine);
        }
        return [...prev, id];
      }
    });
  };

  const selectAll = () => {
    if (selected.length === ordini.length) {
      setSelected([]);
      setSelectedOrdine(null);
      setRighe([]);
    } else {
      setSelected(ordini.map((o) => o.id_testata));
    }
  };

  // Azioni batch - Archiviazione massiva
  const handleBatchArchivia = async () => {
    if (selected.length === 0) return;

    const conferma = window.confirm(
      `ARCHIVIAZIONE MASSIVA\n\n` +
      `Vuoi archiviare definitivamente ${selected.length} ordini?\n\n` +
      `Lo stato diventerà EVASO e non saranno più modificabili.\n\n` +
      `Premi OK per confermare, Annulla per tornare indietro.`
    );

    if (!conferma) return;

    let successi = 0;
    let errori = [];

    try {
      for (const id_testata of selected) {
        try {
          await ordiniApi.archiviaOrdine(id_testata, currentUser?.username || 'admin');
          successi++;
        } catch (err) {
          errori.push({ id: id_testata, error: err.message });
        }
      }

      let msg = `ARCHIVIAZIONE COMPLETATA\n\n`;
      msg += `Ordini archiviati: ${successi}/${selected.length}\n`;

      if (errori.length > 0) {
        msg += `\nErrori: ${errori.length}\n`;
        errori.slice(0, 5).forEach((e) => {
          msg += `  - Ordine #${e.id}: ${e.error}\n`;
        });
      }

      alert(msg);
      setSelected([]);
      loadOrdini();
    } catch (err) {
      alert('Errore archiviazione: ' + err.message);
    }
  };

  // v6.2: Validazione massiva con conferma righe e generazione tracciati
  const handleBatchValidate = async () => {
    if (selected.length === 0) return;

    // Prompt con conferma esplicita
    const conferma = prompt(
      `⚠️ SEI SICURO DI VOLER CONVALIDARE MASSIVAMENTE?\n\n` +
      `Saranno generati i tracciati TOTALI di tutti i ${selected.length} ordini flaggati.\n\n` +
      `ATTENZIONE: Verranno confermate ed esportate TUTTE le righe di ciascun ordine.\n\n` +
      `Se vuoi procedere digita S, altrimenti clicca Annulla:`
    );

    if (conferma?.toUpperCase() !== 'S') {
      return;
    }

    setValidatingBatch(true);
    const operatore = currentUser?.username || 'BATCH_EXPORT';

    let successi = 0;
    let errori = [];
    let totaleRighe = 0;

    try {
      for (const id_testata of selected) {
        try {
          // Validazione massiva: conferma TUTTE le righe e genera tracciato in un'unica chiamata
          const res = await ordiniApi.validaEGeneraTracciato(id_testata, operatore, true);
          if (res.success) {
            successi++;
            totaleRighe += res.statistiche?.righe_esportate || 0;
          } else {
            errori.push({
              id: id_testata,
              error: res.error || 'Errore sconosciuto'
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
      alert('Errore durante la validazione massiva: ' + err.message);
    } finally {
      setValidatingBatch(false);
    }
  };

  // Pulisci filtri
  const clearFilters = () => {
    setFilters({ vendor: '', stato: '', q: '', data_da: '', data_a: '' });
  };

  // Tabs dati
  const tabs = [
    { id: 'ordini', label: 'Ordini', count: stats.ordini },
    { id: 'dettaglio', label: 'Dettaglio', count: null, disabled: !selectedOrdine },
    { id: 'anomalie', label: 'Anomalie', count: stats.anomalie_aperte > 0 ? stats.anomalie_aperte : null }
  ];

  return (
    <div className="space-y-6">
      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
              📋
            </div>
            <div>
              <p className="text-xs text-slate-600 font-medium">Ordini</p>
              <p className="text-xl font-bold text-slate-800">{stats.ordini}</p>
            </div>
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-emerald-100 rounded-lg flex items-center justify-center">
              ✅
            </div>
            <div>
              <p className="text-xs text-slate-600 font-medium">Confermati</p>
              <p className="text-xl font-bold text-emerald-600">{stats.confermati}</p>
            </div>
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-yellow-100 rounded-lg flex items-center justify-center">
              🔄
            </div>
            <div>
              <p className="text-xs text-slate-600 font-medium">Parz. Evaso</p>
              <p className="text-xl font-bold text-yellow-600">{stats.parzEvaso}</p>
            </div>
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
              📦
            </div>
            <div>
              <p className="text-xs text-slate-600 font-medium">Evaso</p>
              <p className="text-xl font-bold text-green-600">{stats.evaso}</p>
            </div>
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-slate-100 rounded-lg flex items-center justify-center">
              🗄️
            </div>
            <div>
              <p className="text-xs text-slate-600 font-medium">Archiviati</p>
              <p className="text-xl font-bold text-slate-500">{stats.archiviati}</p>
            </div>
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-red-100 rounded-lg flex items-center justify-center">
              ⚠️
            </div>
            <div>
              <p className="text-xs text-slate-600 font-medium">Anomalie Aperte</p>
              <p className="text-xl font-bold text-red-600">{stats.anomalie_aperte}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="bg-white rounded-xl border border-slate-200">
        {/* Tabs */}
        <div className="border-b border-slate-200">
          <div className="flex">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => {
                  if (tab.disabled) return;
                  if (tab.id === 'dettaglio' && selectedOrdine) {
                    onOpenOrdine && onOpenOrdine(selectedOrdine.id_testata);
                  } else {
                    setActiveTab(tab.id);
                  }
                }}
                disabled={tab.disabled}
                className={`px-4 py-3 text-sm font-medium transition-colors ${
                  tab.disabled
                    ? 'text-slate-300 cursor-not-allowed'
                    : activeTab === tab.id
                    ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50'
                    : 'text-slate-500 hover:bg-slate-50'
                }`}
              >
                {tab.label}
                {tab.count !== null && (
                  <span className="ml-1 text-slate-400">({tab.count})</span>
                )}
              </button>
            ))}
          </div>
        </div>

        {/* Filtri */}
        <div className="p-4 border-b border-slate-100">
          <div className="grid grid-cols-1 md:grid-cols-6 gap-3">
            <input
              type="text"
              placeholder="🔍 Cerca numero ordine, farmacia..."
              value={filters.q}
              onChange={(e) => setFilters({ ...filters, q: e.target.value })}
              className="md:col-span-2 px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            
            <select
              value={filters.vendor}
              onChange={(e) => setFilters({ ...filters, vendor: e.target.value })}
              className="px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Tutti i Vendor</option>
              {['ANGELINI', 'BAYER', 'CODIFI', 'CHIESI', 'MENARINI', 'OPELLA'].map((v) => (
                <option key={v} value={v}>{v}</option>
              ))}
            </select>
            
            <select
              value={filters.stato}
              onChange={(e) => setFilters({ ...filters, stato: e.target.value })}
              className="px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Tutti gli Stati</option>
              {['ESTRATTO', 'CONFERMATO', 'ANOMALIA', 'PARZ_EVASO', 'EVASO', 'ARCHIVIATO'].map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
            
            <Button variant="secondary" size="sm" onClick={loadOrdini} disabled={loading}>
              🔄
            </Button>
            
            {/* Azioni batch */}
            {selected.length > 0 && (
              <div className="flex gap-2">
                <Button
                  variant="warning"
                  size="sm"
                  onClick={handleBatchArchivia}
                  disabled={validatingBatch}
                >
                  📦 Archivia ({selected.length})
                </Button>
                <Button 
                  variant="primary" 
                  size="sm" 
                  onClick={handleBatchValidate}
                  disabled={validatingBatch}
                >
                  {validatingBatch ? '⏳ Validazione...' : `✓ Valida Massivo (${selected.length})`}
                </Button>
              </div>
            )}
          </div>
        </div>

        {/* Tabella Ordini */}
        {activeTab === 'ordini' && (
          <div className="overflow-x-auto">
            {loading ? (
              <div className="p-8">
                <Loading text="Caricamento ordini..." />
              </div>
            ) : ordini.length === 0 ? (
              <div className="p-8 text-center text-slate-500">
                <div className="text-4xl mb-2">📭</div>
                <p>Nessun ordine trovato</p>
                <Button variant="secondary" size="sm" className="mt-3" onClick={clearFilters}>
                  Pulisci Filtri
                </Button>
              </div>
            ) : (
              <table className="w-full">
                <thead className="bg-slate-50 border-b border-slate-200">
                  <tr>
                    <th className="w-8 p-2">
                      <input
                        type="checkbox"
                        checked={selected.length === ordini.length && ordini.length > 0}
                        onChange={selectAll}
                        className="rounded border-slate-300"
                      />
                    </th>
                    <th className="text-left p-2 text-xs font-medium text-slate-600">Vendor</th>
                    <th className="text-left p-2 text-xs font-medium text-slate-600">N. Ordine</th>
                    <th className="text-left p-2 text-xs font-medium text-slate-600">Consegna</th>
                    <th className="text-left p-2 text-xs font-medium text-slate-600">Farmacia</th>
                    <th className="text-left p-2 text-xs font-medium text-slate-600">Citta</th>
                    <th className="text-center p-2 text-xs font-medium text-slate-600">Righe</th>
                    <th className="text-center p-2 text-xs font-medium text-slate-600">Confermate</th>
                    <th className="text-center p-2 text-xs font-medium text-slate-600">Stato</th>
                    <th className="text-center p-2 text-xs font-medium text-slate-600">Lookup</th>
                    <th className="text-center p-2 text-xs font-medium text-slate-600">Azioni</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {ordini.map((ordine) => {
                    const isSelected = selected.includes(ordine.id_testata);
                    const rowHighlight = getRowHighlightClass(ordine.data_consegna, ordine.data_ordine);

                    return (
                      <tr
                        key={ordine.id_testata}
                        className={`hover:bg-slate-50 cursor-pointer ${rowHighlight} ${
                          selectedOrdine?.id_testata === ordine.id_testata ? 'bg-blue-50' : ''
                        }`}
                        onClick={() => onOpenOrdine && onOpenOrdine(ordine.id_testata)}
                      >
                        <td className="p-2 text-center" onClick={(e) => e.stopPropagation()}>
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => toggleSelect(ordine.id_testata)}
                            className="rounded border-slate-300"
                          />
                        </td>
                        <td className="p-2">
                          <VendorBadge vendor={ordine.vendor} size="xs" />
                        </td>
                        <td className="p-2 font-mono text-xs font-medium">
                          {ordine.numero_ordine || ordine.numero_ordine_vendor || '-'}
                        </td>
                        <td className="p-2">
                          <DeliveryBadge dataConsegna={ordine.data_consegna} dataOrdine={ordine.data_ordine} />
                        </td>
                        <td className="p-2 truncate max-w-[200px] text-xs">
                          {ordine.ragione_sociale}
                        </td>
                        <td className="p-2 text-xs text-slate-500">
                          {ordine.citta}
                        </td>
                        <td className="p-2 text-center text-xs">
                          {ordine.righe_totali || ordine.num_righe || '-'}
                        </td>
                        <td className="p-2 text-center">
                          {ordine.righe_confermate !== undefined && (ordine.righe_totali || ordine.num_righe) > 0 ? (
                            <span className={`text-xs font-mono ${
                              ordine.righe_confermate === (ordine.righe_totali || ordine.num_righe)
                                ? 'text-emerald-600'
                                : ordine.righe_confermate > 0
                                ? 'text-amber-600'
                                : 'text-slate-400'
                            }`}>
                              {ordine.righe_confermate}/{ordine.righe_totali || ordine.num_righe}
                            </span>
                          ) : (
                            <span className="text-slate-400 text-xs">-</span>
                          )}
                        </td>
                        <td className="p-2 text-center">
                          <StatusBadge status={ordine.stato} size="xs" />
                        </td>
                        <td className="p-2 text-center">
                          <span className={`text-xs ${
                            ordine.lookup_score >= 90
                              ? 'text-emerald-600'
                              : ordine.lookup_score >= 60
                              ? 'text-amber-600'
                              : 'text-red-600'
                          }`}>
                            {ordine.lookup_method || '-'}
                            {ordine.lookup_score ? ` (${ordine.lookup_score}%)` : ''}
                          </span>
                        </td>
                        <td className="p-2 text-center" onClick={(e) => e.stopPropagation()}>
                          {/* Pulsante Visualizza PDF */}
                          {ordine.pdf_file && (
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                setPdfToShow(ordine.pdf_file);
                                setShowPdfModal(true);
                              }}
                              className="px-2 py-1 text-xs bg-slate-100 text-slate-700 rounded hover:bg-slate-200"
                              title="Visualizza PDF originale"
                            >
                              🔍
                            </button>
                          )}

                          <button
                            onClick={() => onOpenOrdine && onOpenOrdine(ordine.id_testata)}
                            className="ml-1 px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded hover:bg-blue-200"
                            title="Apri dettaglio ordine"
                          >
                            Dettaglio
                          </button>

                          <button
                            onClick={async (e) => {
                              e.stopPropagation();
                              const conferma = window.confirm(
                                `ARCHIVIAZIONE DEFINITIVA\n\n` +
                                `Vuoi archiviare definitivamente l'ordine?\n\n` +
                                `Ordine: ${ordine.numero_ordine_vendor || '-'}\n` +
                                `Cliente: ${ordine.ragione_sociale || ordine.ragione_sociale_1 || '-'}\n` +
                                `Vendor: ${ordine.vendor || '-'}\n` +
                                `Data: ${ordine.data_ordine || '-'}\n\n` +
                                `Lo stato diventerà EVASO e non sarà più modificabile.\n\n` +
                                `Premi OK per confermare (SI), Annulla per tornare indietro.`
                              );
                              if (conferma) {
                                try {
                                  await ordiniApi.archiviaOrdine(ordine.id_testata);
                                  alert(`Ordine ${ordine.numero_ordine_vendor} archiviato con successo!`);
                                  if (typeof loadOrdini === "function") loadOrdini();
                                } catch (err) {
                                  alert("Errore: " + (err.response?.data?.detail || err.message));
                                }
                              }
                            }}
                            className="ml-1 px-2 py-1 text-xs bg-orange-100 text-orange-700 rounded hover:bg-orange-200"
                            title="Archivia ordine (stato EVASO)"
                          >
                            📦 Archivia
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        )}

        {/* Tab Righe - v6.2: Aggiunta colonna Consegna, Sconto, Flags */}
        {activeTab === 'righe' && selectedOrdine && (
          <div className="overflow-x-auto">
            <div className="p-3 bg-slate-50 border-b border-slate-100">
              <span className="text-sm font-medium">
                Ordine: <span className="font-mono">{selectedOrdine.numero_ordine}</span>
              </span>
              <span className="text-slate-500 ml-4">{selectedOrdine.ragione_sociale}</span>
            </div>

            {righe.length === 0 ? (
              <p className="text-center text-slate-500 py-8">Nessuna riga trovata</p>
            ) : (
              <table className="w-full text-xs">
                <thead className="bg-slate-50 text-slate-600">
                  <tr>
                    <th className="p-2 text-left">#</th>
                    <th className="p-2 text-left">AIC</th>
                    <th className="p-2 text-left">Descrizione</th>
                    <th className="p-2 text-left">Consegna</th>
                    <th className="p-2 text-right">Q.ta</th>
                    <th className="p-2 text-right">Prezzo</th>
                    <th className="p-2 text-right">Sconto</th>
                    <th className="p-2 text-center">Flags</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {righe.map((riga) => {
                    const rowHighlight = getRowHighlightClass(riga.data_consegna, selectedOrdine.data_ordine);

                    return (
                      <tr
                        key={riga.id_dettaglio}
                        className={`hover:bg-slate-50 ${rowHighlight}`}
                      >
                        <td className="p-2">{riga.n_riga}</td>
                        <td className="p-2 font-mono">{riga.codice_aic || '-'}</td>
                        <td className="p-2 truncate max-w-[250px]">{riga.descrizione}</td>
                        <td className="p-2">
                          <DeliveryBadge dataConsegna={riga.data_consegna} dataOrdine={selectedOrdine.data_ordine} />
                        </td>
                        <td className="p-2 text-right">{riga.q_venduta}</td>
                        <td className="p-2 text-right">
                          {riga.prezzo_netto != null ? `€${riga.prezzo_netto.toFixed(2)}` : '-'}
                        </td>
                        <td className="p-2 text-right">
                          {riga.sconto_1 ? `${riga.sconto_1}%` : '-'}
                        </td>
                        <td className="p-2 text-center">
                          {riga.is_espositore && <span title="Espositore">🎁</span>}
                          {riga.is_no_aic && <span title="No AIC">⚠️</span>}
                          {!riga.is_espositore && !riga.is_no_aic && '-'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        )}

        {/* Tab Anomalie */}
        {activeTab === 'anomalie' && (
          <div className="p-4">
            {/* Filtri */}
            <div className="flex gap-4 mb-4 flex-wrap">
              <select
                value={anomalieFilters.tipo}
                onChange={(e) => setAnomalieFilters(f => ({ ...f, tipo: e.target.value }))}
                className="px-3 py-2 border border-slate-300 rounded-lg text-sm"
              >
                <option value="">Tutti i tipi</option>
                <option value="ESPOSITORE">Espositore</option>
                <option value="NO_AIC">No AIC</option>
                <option value="LOOKUP_FALLITO">Lookup Fallito</option>
                <option value="DUPLICATO">Duplicato</option>
                <option value="PREZZO_ZERO">Prezzo Zero</option>
                <option value="QTA_ANOMALA">Quantita Anomala</option>
                <option value="SCONTO_ANOMALO">Sconto Anomalo</option>
              </select>

              <select
                value={anomalieFilters.stato}
                onChange={(e) => setAnomalieFilters(f => ({ ...f, stato: e.target.value }))}
                className="px-3 py-2 border border-slate-300 rounded-lg text-sm"
              >
                <option value="">Tutti gli stati</option>
                <option value="APERTA">Aperta</option>
                <option value="IN_GESTIONE">In gestione</option>
                <option value="RISOLTA">Risolta</option>
                <option value="IGNORATA">Ignorata</option>
              </select>

              <button
                onClick={loadAnomalies}
                className="px-4 py-2 bg-slate-100 hover:bg-slate-200 rounded-lg text-sm"
              >
                🔄 Ricarica
              </button>

              {selectedAnomalies.length > 0 && (
                <button
                  onClick={handleResolveAnomalies}
                  className="px-4 py-2 bg-green-500 hover:bg-green-600 text-white rounded-lg text-sm"
                >
                  ✓ Risolvi ({selectedAnomalies.length})
                </button>
              )}
            </div>

            {/* Tabella Anomalie */}
            {loadingAnomalies ? (
              <div className="text-center py-8 text-slate-500">
                <div className="animate-spin text-2xl mb-2">⏳</div>
                <p>Caricamento anomalie...</p>
              </div>
            ) : anomalieList.length === 0 ? (
              <div className="text-center py-8 text-slate-500">
                <div className="text-4xl mb-2">✅</div>
                <p>Nessuna anomalia trovata</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-slate-50">
                    <tr>
                      <th className="p-3 text-left w-10">
                        <input
                          type="checkbox"
                          checked={selectedAnomalies.length === anomalieList.length && anomalieList.length > 0}
                          onChange={(e) => {
                            e.stopPropagation();
                            if (e.target.checked) {
                              setSelectedAnomalies(anomalieList.map(a => a.id_anomalia));
                            } else {
                              setSelectedAnomalies([]);
                            }
                          }}
                        />
                      </th>
                      <th className="p-3 text-left">ID</th>
                      <th className="p-3 text-left">Tipo</th>
                      <th className="p-3 text-left">Ordine</th>
                      <th className="p-3 text-left">Descrizione</th>
                      <th className="p-3 text-left">Severita</th>
                      <th className="p-3 text-left">Stato</th>
                      <th className="p-3 text-left">Data</th>
                      <th className="p-3 text-left">Azioni</th>
                    </tr>
                  </thead>
                  <tbody>
                    {anomalieList.map((anomalia) => (
                      <tr
                        key={anomalia.id_anomalia}
                        className={`border-b border-slate-100 hover:bg-slate-50 cursor-pointer ${
                          selectedAnomalies.includes(anomalia.id_anomalia) ? 'bg-blue-50' : ''
                        }`}
                        onClick={() => {
                          // Click sulla riga apre dettaglio anomalia
                          loadAnomaliaDetail(anomalia.id_anomalia);
                        }}
                      >
                        <td className="p-3" onClick={(e) => e.stopPropagation()}>
                          <input
                            type="checkbox"
                            checked={selectedAnomalies.includes(anomalia.id_anomalia)}
                            onChange={(e) => {
                              e.stopPropagation();
                              if (e.target.checked) {
                                setSelectedAnomalies([...selectedAnomalies, anomalia.id_anomalia]);
                              } else {
                                setSelectedAnomalies(selectedAnomalies.filter(id => id !== anomalia.id_anomalia));
                              }
                            }}
                          />
                        </td>
                        <td className="p-3 font-mono text-xs">{anomalia.id_anomalia}</td>
                        <td className="p-3">
                          <span className={`px-2 py-1 rounded text-xs font-medium ${
                            anomalia.tipo_anomalia === 'ESPOSITORE' ? 'bg-purple-100 text-purple-700' :
                            anomalia.tipo_anomalia === 'NO_AIC' ? 'bg-orange-100 text-orange-700' :
                            anomalia.tipo_anomalia === 'LOOKUP_FALLITO' ? 'bg-red-100 text-red-700' :
                            anomalia.tipo_anomalia === 'DUPLICATO' ? 'bg-yellow-100 text-yellow-700' :
                            anomalia.tipo_anomalia === 'PREZZO_ZERO' ? 'bg-amber-100 text-amber-700' :
                            'bg-slate-100 text-slate-700'
                          }`}>
                            {anomalia.tipo_anomalia}
                          </span>
                        </td>
                        <td className="p-3">
                          <div className="flex flex-col">
                            <span className="font-mono text-xs">{anomalia.numero_ordine || '-'}</span>
                            {anomalia.vendor && (
                              <span className="text-xs text-slate-500">{anomalia.vendor}</span>
                            )}
                          </div>
                        </td>
                        <td className="p-3 max-w-xs truncate" title={anomalia.descrizione}>
                          {anomalia.descrizione}
                        </td>
                        <td className="p-3">
                          <span className={`px-2 py-1 rounded text-xs font-medium ${
                            anomalia.severita === 'CRITICAL' ? 'bg-red-200 text-red-800' :
                            anomalia.severita === 'ERROR' ? 'bg-red-100 text-red-700' :
                            anomalia.severita === 'WARNING' ? 'bg-yellow-100 text-yellow-700' :
                            'bg-blue-100 text-blue-700'
                          }`}>
                            {anomalia.severita || 'INFO'}
                          </span>
                        </td>
                        <td className="p-3">
                          <span className={`px-2 py-1 rounded text-xs font-medium ${
                            anomalia.stato === 'APERTA' ? 'bg-red-100 text-red-700' :
                            anomalia.stato === 'IN_GESTIONE' ? 'bg-yellow-100 text-yellow-700' :
                            anomalia.stato === 'RISOLTA' ? 'bg-green-100 text-green-700' :
                            'bg-slate-100 text-slate-700'
                          }`}>
                            {anomalia.stato}
                          </span>
                        </td>
                        <td className="p-3 text-xs text-slate-500">
                          {anomalia.data_creazione ? new Date(anomalia.data_creazione).toLocaleDateString('it-IT') : '-'}
                        </td>
                        <td className="p-3" onClick={(e) => e.stopPropagation()}>
                          <div className="flex gap-1">
                            {anomalia.id_testata && (
                              <button
                                onClick={() => onOpenOrdine?.(anomalia.id_testata)}
                                className="px-2 py-1 text-xs bg-blue-100 hover:bg-blue-200 text-blue-700 rounded"
                                title="Apri ordine collegato"
                              >
                                📋
                              </button>
                            )}
                            <button
                              onClick={async () => {
                                try {
                                  await anomalieApi.update(anomalia.id_anomalia, { stato: 'RISOLTA', nota: 'Risolta manualmente' });
                                  loadAnomalies();
                                  loadAnomalieCount();
                                } catch (err) {
                                  alert('Errore: ' + err.message);
                                }
                              }}
                              className="px-2 py-1 text-xs bg-green-100 hover:bg-green-200 text-green-700 rounded"
                              disabled={anomalia.stato === 'RISOLTA'}
                              title="Risolvi anomalia"
                            >
                              ✓
                            </button>
                            <button
                              onClick={async () => {
                                try {
                                  await anomalieApi.update(anomalia.id_anomalia, { stato: 'IGNORATA', nota: 'Ignorata manualmente' });
                                  loadAnomalies();
                                  loadAnomalieCount();
                                } catch (err) {
                                  alert('Errore: ' + err.message);
                                }
                              }}
                              className="px-2 py-1 text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 rounded"
                              disabled={anomalia.stato === 'IGNORATA'}
                              title="Ignora anomalia"
                            >
                              ✗
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>

      {/* v6.2: Legenda Urgenze Consegna */}
      <div className="bg-white rounded-xl border border-slate-200 p-3">
        <h4 className="text-xs font-semibold text-slate-600 mb-2">
          Legenda Urgenze Consegna
        </h4>
        <div className="flex gap-6 text-xs">
          <div className="flex items-center gap-2">
            <span className="w-4 h-4 bg-red-50 border-l-4 border-red-500 rounded"></span>
            <span className="text-slate-600">🔴 Scaduto (data passata)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-4 h-4 bg-amber-50 border-l-4 border-amber-400 rounded"></span>
            <span className="text-slate-600">🟠 Urgente (≤2 gg lavorativi)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="flex items-center gap-1 text-emerald-600">🟢</span>
            <span className="text-slate-600">Ordinario (&gt;2 gg lavorativi)</span>
          </div>
        </div>
      </div>

      {/* Modal Visualizza PDF */}
      {showPdfModal && pdfToShow && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl w-[90vw] h-[90vh] flex flex-col">
            {/* Header Modal */}
            <div className="flex items-center justify-between p-4 border-b border-slate-200">
              <h3 className="text-lg font-semibold text-slate-800">
                📄 PDF Originale
              </h3>
              <button
                onClick={() => {
                  setShowPdfModal(false);
                  setPdfToShow(null);
                }}
                className="p-2 hover:bg-slate-100 rounded-lg text-slate-500"
              >
                ✕
              </button>
            </div>

            {/* Contenuto PDF */}
            <div className="flex-1 p-4">
              <iframe
                src={`/api/v1/upload/pdf/${encodeURIComponent(pdfToShow)}`}
                className="w-full h-full border border-slate-200 rounded-lg"
                title="PDF Viewer"
              />
            </div>
          </div>
        </div>
      )}

      {/* v6.2: Modal Dettaglio Anomalia (Componente condiviso) */}
      <AnomaliaDetailModal
        isOpen={showAnomaliaDetailModal}
        onClose={() => {
          setShowAnomaliaDetailModal(false);
          setAnomaliaDetail(null);
        }}
        anomaliaDetail={anomaliaDetail}
        loading={loadingAnomaliaDetail}
        onSaveParent={handleSaveRigaParent}
        onRisolvi={handleRisolviAnomaliaDetail}
        onOpenOrdine={onOpenOrdine}
        onAssignFarmacia={handleAssignFarmacia}
      />
    </div>
  );
};

export default DatabasePage;
