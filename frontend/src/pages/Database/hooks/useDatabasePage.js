// =============================================================================
// SERV.O v7.0 - USE DATABASE PAGE HOOK
// =============================================================================
// Custom hook per gestione stato e logica pagina database
// =============================================================================

import { useState, useEffect, useCallback } from 'react';
import { ordiniApi, anomalieApi, lookupApi } from '../../../api';
import { richiestaConferma } from '../../../utils/confirmazione';

export function useDatabasePage(currentUser, onOpenOrdine) {
  // Tab state
  const [activeTab, setActiveTab] = useState('ordini');

  // Ordini state
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
  const [downloadingPdf, setDownloadingPdf] = useState(false);

  // Stats
  const [stats, setStats] = useState({
    ordini: 0,
    confermati: 0,
    parzEvaso: 0,
    evaso: 0,
    archiviati: 0,
    anomalie_aperte: 0
  });

  // PDF Modal
  const [showPdfModal, setShowPdfModal] = useState(false);
  const [pdfToShow, setPdfToShow] = useState(null);

  // Anomalie state
  const [anomalieList, setAnomalieList] = useState([]);
  const [loadingAnomalies, setLoadingAnomalies] = useState(false);
  const [selectedAnomalies, setSelectedAnomalies] = useState([]);
  const [anomalieFilters, setAnomalieFilters] = useState({
    tipo: '',
    stato: '',
    vendor: ''
  });

  // Anomalia detail modal
  const [showAnomaliaDetailModal, setShowAnomaliaDetailModal] = useState(false);
  const [anomaliaDetail, setAnomaliaDetail] = useState(null);
  const [loadingAnomaliaDetail, setLoadingAnomaliaDetail] = useState(false);

  // =============================================================================
  // LOAD STATS (v11.3: da backend, non calcolato localmente)
  // =============================================================================

  const loadStats = useCallback(async () => {
    try {
      const res = await ordiniApi.getStats();
      if (res.success && res.data) {
        // Usa stats totali dal backend
        const totali = res.data.totali || {};
        setStats({
          ordini: totali.ordini || 0,
          confermati: totali.confermato || 0,
          parzEvaso: totali.parz_evaso || 0,
          evaso: totali.evaso || 0,
          archiviati: totali.archiviato || 0,
          anomalie_aperte: totali.anomalie_aperte || 0
        });
      }
    } catch (err) {
      console.error('Errore caricamento stats:', err);
    }
  }, []);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  // =============================================================================
  // LOAD ORDINI
  // =============================================================================

  const loadOrdini = useCallback(async () => {
    try {
      setLoading(true);
      const queryParams = { ...filters, limit: 100 };

      Object.keys(queryParams).forEach(key => {
        if (!queryParams[key]) delete queryParams[key];
      });

      const res = await ordiniApi.getList(queryParams);

      if (res.success) {
        const ordiniData = res.data || [];
        setOrdini(ordiniData);
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

  // =============================================================================
  // LOAD ANOMALIE COUNT (legacy - now included in loadStats)
  // =============================================================================

  const loadAnomalieCount = useCallback(async () => {
    // v11.3: Anomalie count is now loaded via loadStats
    // Keeping this for backward compatibility but it's a no-op
  }, []);

  // =============================================================================
  // LOAD ANOMALIE LIST
  // =============================================================================

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
        setAnomalieList([]);
      }
    } catch (err) {
      console.error('Errore caricamento anomalie:', err);
      setAnomalieList([]);
    } finally {
      setLoadingAnomalies(false);
    }
  }, [anomalieFilters]);

  useEffect(() => {
    if (activeTab === 'anomalie') {
      loadAnomalies();
    }
  }, [activeTab, loadAnomalies]);

  // =============================================================================
  // SELECTION HANDLERS
  // =============================================================================

  const toggleSelect = useCallback((id) => {
    setSelected(prev => {
      const isSelected = prev.includes(id);
      if (isSelected) {
        if (selectedOrdine?.id_testata === id) {
          setSelectedOrdine(null);
          setRighe([]);
        }
        return prev.filter(x => x !== id);
      } else {
        const ordine = ordini.find(o => o.id_testata === id);
        if (ordine) setSelectedOrdine(ordine);
        return [...prev, id];
      }
    });
  }, [ordini, selectedOrdine]);

  const selectAll = useCallback(() => {
    if (selected.length === ordini.length) {
      setSelected([]);
      setSelectedOrdine(null);
      setRighe([]);
    } else {
      setSelected(ordini.map(o => o.id_testata));
    }
  }, [ordini, selected]);

  const toggleAnomaliaSelect = useCallback((id) => {
    setSelectedAnomalies(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    );
  }, []);

  const selectAllAnomalies = useCallback((checked) => {
    setSelectedAnomalies(checked ? anomalieList.map(a => a.id_anomalia) : []);
  }, [anomalieList]);

  // =============================================================================
  // BATCH ACTIONS
  // =============================================================================

  const handleBatchArchivia = useCallback(async () => {
    if (selected.length === 0) return;

    if (!richiestaConferma(
      'Archiviazione massiva ordini',
      `Vuoi archiviare definitivamente ${selected.length} ordini?\n` +
      `Lo stato diventerà EVASO e non saranno più modificabili.`
    )) return;

    // Helper per ottenere numero_ordine dall'id_testata
    const getNumeroOrdine = (id_testata) => {
      const ordine = ordini.find(o => o.id_testata === id_testata);
      return ordine?.numero_ordine || ordine?.numero_ordine_vendor || `ID:${id_testata}`;
    };

    let successi = 0;
    let errori = [];

    try {
      for (const id_testata of selected) {
        const numeroOrdine = getNumeroOrdine(id_testata);
        try {
          await ordiniApi.archiviaOrdine(id_testata, currentUser?.username || 'admin');
          successi++;
        } catch (err) {
          const errorMsg = err.response?.data?.detail || err.message || 'Errore sconosciuto';
          errori.push({ numeroOrdine, error: errorMsg });
        }
      }

      let msg = `ARCHIVIAZIONE COMPLETATA\n\nOrdini archiviati: ${successi}/${selected.length}\n`;
      if (errori.length > 0) {
        msg += `\nErrori: ${errori.length}\n`;
        errori.slice(0, 10).forEach(e => {
          msg += `  - Ordine ${e.numeroOrdine}: ${e.error}\n`;
        });
        if (errori.length > 10) {
          msg += `  ... e altri ${errori.length - 10} errori\n`;
        }
      }

      alert(msg);
      setSelected([]);
      loadOrdini();
    } catch (err) {
      alert('Errore archiviazione: ' + (err.response?.data?.detail || err.message));
    }
  }, [selected, currentUser, loadOrdini, ordini]);

  const handleBatchValidate = useCallback(async () => {
    if (selected.length === 0) return;

    if (!richiestaConferma(
      'Convalida massiva ordini',
      `Saranno generati i tracciati TOTALI di tutti i ${selected.length} ordini selezionati.`
    )) return;

    setValidatingBatch(true);
    const operatore = currentUser?.username || 'BATCH_EXPORT';

    // Helper per ottenere numero_ordine dall'id_testata
    const getNumeroOrdine = (id_testata) => {
      const ordine = ordini.find(o => o.id_testata === id_testata);
      return ordine?.numero_ordine || ordine?.numero_ordine_vendor || `ID:${id_testata}`;
    };

    let successi = 0;
    let errori = [];
    let totaleRighe = 0;

    try {
      for (const id_testata of selected) {
        const numeroOrdine = getNumeroOrdine(id_testata);
        try {
          const res = await ordiniApi.validaEGeneraTracciato(id_testata, operatore, true);
          if (res.success) {
            successi++;
            totaleRighe += res.statistiche?.righe_esportate || 0;
          } else {
            errori.push({ numeroOrdine, error: res.error || 'Errore sconosciuto' });
          }
        } catch (err) {
          // Estrai messaggio errore user-friendly dal backend
          const errorMsg = err.response?.data?.detail || err.message || 'Errore sconosciuto';
          errori.push({ numeroOrdine, error: errorMsg });
        }
      }

      let msg = `VALIDAZIONE MASSIVA COMPLETATA\n\n`;
      msg += `Ordini processati: ${selected.length}\n`;
      msg += `Successi: ${successi}\n`;
      msg += `Righe esportate: ${totaleRighe}\n`;

      if (errori.length > 0) {
        msg += `\nErrori: ${errori.length}\n`;
        errori.slice(0, 10).forEach(e => {
          msg += `  - Ordine ${e.numeroOrdine}: ${e.error}\n`;
        });
        if (errori.length > 10) {
          msg += `  ... e altri ${errori.length - 10} errori\n`;
        }
      }

      alert(msg);
      setSelected([]);
      loadOrdini();
    } catch (err) {
      alert('Errore durante la validazione massiva: ' + (err.response?.data?.detail || err.message));
    } finally {
      setValidatingBatch(false);
    }
  }, [selected, currentUser, loadOrdini, ordini]);

  const handleResolveAnomalies = useCallback(async () => {
    if (selectedAnomalies.length === 0) return;

    const nota = prompt('Nota di risoluzione (opzionale):');
    if (nota === null) return;

    try {
      const res = await anomalieApi.batchRisolvi(selectedAnomalies, nota || 'Risolta manualmente');
      if (res.success) {
        alert(`Risolte ${res.resolved || selectedAnomalies.length} anomalie`);
        setSelectedAnomalies([]);
        loadAnomalies();
        loadAnomalieCount();
      }
    } catch (err) {
      alert('Errore: ' + err.message);
    }
  }, [selectedAnomalies, loadAnomalies, loadAnomalieCount]);

  const handleDownloadPdf = useCallback(async () => {
    if (selected.length === 0) return;

    setDownloadingPdf(true);
    try {
      const result = await ordiniApi.downloadPdfZip(selected);
      if (result.success) {
        let msg = `Download completato: ${result.filesAdded} PDF`;
        if (result.filesMissing > 0) {
          msg += ` (${result.filesMissing} file non trovati)`;
        }
        console.log(msg);
      }
    } catch (err) {
      const errorMsg = err.response?.data?.detail || err.message;
      alert('Errore download PDF: ' + errorMsg);
    } finally {
      setDownloadingPdf(false);
    }
  }, [selected]);

  // =============================================================================
  // ANOMALIA DETAIL HANDLERS
  // =============================================================================

  const loadAnomaliaDetail = useCallback(async (idAnomalia) => {
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
  }, []);

  const handleSaveRigaParent = useCallback(async (editingData) => {
    if (!anomaliaDetail?.anomalia?.id_anomalia) return false;

    try {
      const res = await anomalieApi.modificaRiga(anomaliaDetail.anomalia.id_anomalia, editingData);
      if (res.success) {
        alert('Riga aggiornata');
        await loadAnomaliaDetail(anomaliaDetail.anomalia.id_anomalia);
        return true;
      }
      return false;
    } catch (err) {
      alert('Errore: ' + err.message);
      return false;
    }
  }, [anomaliaDetail, loadAnomaliaDetail]);

  const handleRisolviAnomaliaDetail = useCallback(async () => {
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
        loadAnomalieCount();
      }
    } catch (err) {
      alert('Errore: ' + err.message);
    }
  }, [anomaliaDetail, loadAnomalies, loadAnomalieCount]);

  const handleAssignFarmacia = useCallback(async (idTestata, idFarmacia, idParafarmacia, minIdManuale = null) => {
    try {
      const res = await lookupApi.manuale(idTestata, idFarmacia, idParafarmacia, minIdManuale);
      if (res.success) {
        alert(minIdManuale ? `MIN_ID ${minIdManuale} assegnato` : 'Farmacia assegnata');
        setShowAnomaliaDetailModal(false);
        setAnomaliaDetail(null);
        loadAnomalies();
        loadAnomalieCount();
        if (activeTab === 'ordini') loadOrdini();
        return true;
      }
      return false;
    } catch (err) {
      alert('Errore: ' + err.message);
      return false;
    }
  }, [activeTab, loadAnomalies, loadAnomalieCount, loadOrdini]);

  const closeAnomaliaModal = useCallback(() => {
    setShowAnomaliaDetailModal(false);
    setAnomaliaDetail(null);
  }, []);

  // =============================================================================
  // PDF MODAL
  // =============================================================================

  const showPdf = useCallback((pdfFile) => {
    setPdfToShow(pdfFile);
    setShowPdfModal(true);
  }, []);

  const closePdfModal = useCallback(() => {
    setShowPdfModal(false);
    setPdfToShow(null);
  }, []);

  // =============================================================================
  // FILTER HANDLERS
  // =============================================================================

  const clearFilters = useCallback(() => {
    setFilters({ vendor: '', stato: '', q: '', data_da: '', data_a: '' });
  }, []);

  // =============================================================================
  // RETURN
  // =============================================================================

  return {
    // Tab
    activeTab,
    setActiveTab,

    // Ordini
    ordini,
    selectedOrdine,
    righe,
    loading,
    filters,
    setFilters,
    selected,
    validatingBatch,
    downloadingPdf,

    // Stats
    stats,

    // PDF Modal
    showPdfModal,
    pdfToShow,

    // Anomalie
    anomalieList,
    loadingAnomalies,
    selectedAnomalies,
    anomalieFilters,
    setAnomalieFilters,

    // Anomalia detail modal
    showAnomaliaDetailModal,
    anomaliaDetail,
    loadingAnomaliaDetail,

    // Actions
    loadOrdini,
    loadAnomalies,
    loadAnomalieCount,
    toggleSelect,
    selectAll,
    toggleAnomaliaSelect,
    selectAllAnomalies,
    handleBatchArchivia,
    handleBatchValidate,
    handleDownloadPdf,
    handleResolveAnomalies,
    loadAnomaliaDetail,
    handleSaveRigaParent,
    handleRisolviAnomaliaDetail,
    handleAssignFarmacia,
    closeAnomaliaModal,
    showPdf,
    closePdfModal,
    clearFilters
  };
}

export default useDatabasePage;
