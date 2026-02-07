// =============================================================================
// SERV.O v11.3 - USE ORDINE DETAIL HOOK
// =============================================================================
// Custom hook per gestione stato e logica dettaglio ordine
// v11.3: Sort state persistente (non si resetta durante reload)
// =============================================================================

import { useState, useEffect, useCallback } from 'react';
import { ordiniApi, anomalieApi, lookupApi, supervisioneApi } from '../../../api';

const INITIAL_FORM_MODIFICA = {
  codice_aic: '',
  descrizione: '',
  q_venduta: 0,
  q_sconto_merce: 0,
  q_omaggio: 0,
  q_da_evadere: 0,
  prezzo_netto: 0,
  prezzo_pubblico: 0,
  sconto_1: 0,
  sconto_2: 0,
  sconto_3: 0,
  sconto_4: 0,
  note_allestimento: ''
};

export function useOrdineDetail(ordineId, currentUser) {
  // Core state
  const [ordine, setOrdine] = useState(null);
  const [righe, setRighe] = useState([]);
  const [righeAll, setRigheAll] = useState([]);  // Include child rows for EspositoreTab
  const [anomalie, setAnomalieList] = useState([]);
  const [supervisioni, setSupervisioni] = useState([]);

  // UI state
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('righe');
  const [actionLoading, setActionLoading] = useState(null);

  // v11.3: Sort state - lifted here to persist across tab changes and data reloads
  const [sortField, setSortField] = useState('n_riga');
  const [sortDirection, setSortDirection] = useState('asc');

  // Edit state
  const [rigaInModifica, setRigaInModifica] = useState(null);
  const [formModifica, setFormModifica] = useState(INITIAL_FORM_MODIFICA);

  // Modal state
  const [showPdfModal, setShowPdfModal] = useState(false);
  const [showAnomaliaDetailModal, setShowAnomaliaDetailModal] = useState(false);
  const [anomaliaDetail, setAnomaliaDetail] = useState(null);
  const [loadingAnomaliaDetail, setLoadingAnomaliaDetail] = useState(false);

  // v11.5: Correzione listino modal state
  const [correzioneListinoModal, setCorrezioneListinoModal] = useState({ isOpen: false, supervisione: null });

  // =============================================================================
  // DATA LOADING
  // =============================================================================

  const loadOrdine = useCallback(async () => {
    if (!ordineId) return;

    setLoading(true);
    setError(null);

    try {
      const [ordineData, righeData, righeAllData, anomalieData] = await Promise.all([
        ordiniApi.getDetail(ordineId),
        ordiniApi.getRighe(ordineId),
        ordiniApi.getRigheAll(ordineId),  // Include children for EspositoreTab
        anomalieApi.getByOrdine(ordineId).catch(() => ({ items: [] }))
      ]);

      setOrdine(ordineData?.data || ordineData);

      const righeArray = Array.isArray(righeData)
        ? righeData
        : (righeData?.righe || righeData?.data || righeData?.items || []);
      setRighe(righeArray);

      const righeAllArray = Array.isArray(righeAllData)
        ? righeAllData
        : (righeAllData?.righe || righeAllData?.data || righeAllData?.items || []);
      setRigheAll(righeAllArray);

      const anomalieArray = Array.isArray(anomalieData)
        ? anomalieData
        : (anomalieData?.items || anomalieData?.data || anomalieData?.anomalie || []);
      setAnomalieList(anomalieArray);

      // Carica supervisioni espositore
      try {
        const supData = await fetch(`/api/v1/supervisione/ordine/${ordineId}`).then(r => r.json());
        setSupervisioni(supData?.supervisioni || []);
      } catch (e) {
        setSupervisioni([]);
      }
    } catch (err) {
      console.error('Errore caricamento ordine:', err);
      setError(err.response?.data?.detail || 'Errore nel caricamento dell\'ordine');
    } finally {
      setLoading(false);
    }
  }, [ordineId]);

  useEffect(() => {
    loadOrdine();
  }, [loadOrdine]);

  // =============================================================================
  // RIGA HANDLERS
  // =============================================================================

  const apriModificaRiga = useCallback((riga) => {
    setRigaInModifica(riga);
    const qVenduta = riga.q_venduta || riga.q_ordinata || riga.quantita || 0;
    const qScontoMerce = riga.q_sconto_merce || 0;
    const qOmaggio = riga.q_omaggio || 0;

    setFormModifica({
      codice_aic: riga.codice_aic || riga.codice_prodotto || '',
      descrizione: riga.descrizione || riga.descrizione_prodotto || '',
      q_venduta: qVenduta,
      q_sconto_merce: qScontoMerce,
      q_omaggio: qOmaggio,
      q_da_evadere: riga.q_da_evadere || 0,
      prezzo_netto: riga.prezzo_netto || 0,
      prezzo_pubblico: riga.prezzo_pubblico || 0,
      sconto_1: riga.sconto_1 || 0,
      sconto_2: riga.sconto_2 || 0,
      sconto_3: riga.sconto_3 || 0,
      sconto_4: riga.sconto_4 || 0,
      note_allestimento: riga.note_allestimento || ''
    });
  }, []);

  const chiudiModificaRiga = useCallback(() => {
    setRigaInModifica(null);
    setFormModifica(INITIAL_FORM_MODIFICA);
  }, []);

  const salvaModificaRiga = useCallback(async (riga) => {
    const idRiga = riga.id_dettaglio || riga.id;
    try {
      const modifiche = {
        codice_aic: formModifica.codice_aic,
        descrizione: formModifica.descrizione,
        q_venduta: parseInt(formModifica.q_venduta) || 0,
        q_sconto_merce: parseInt(formModifica.q_sconto_merce) || 0,
        q_omaggio: parseInt(formModifica.q_omaggio) || 0,
        prezzo_netto: parseFloat(formModifica.prezzo_netto) || 0,
        prezzo_pubblico: parseFloat(formModifica.prezzo_pubblico) || 0,
        sconto_1: parseFloat(formModifica.sconto_1) || 0,
        sconto_2: parseFloat(formModifica.sconto_2) || 0,
        sconto_3: parseFloat(formModifica.sconto_3) || 0,
        sconto_4: parseFloat(formModifica.sconto_4) || 0,
        note_allestimento: formModifica.note_allestimento || ''
      };

      await ordiniApi.modificaRiga(ordineId, idRiga, currentUser?.username || 'admin', modifiche);

      const qDaEvadere = parseInt(formModifica.q_da_evadere) || 0;
      if (qDaEvadere >= 0) {
        await ordiniApi.registraEvasione(ordineId, idRiga, qDaEvadere, currentUser?.username || 'admin');
      }

      chiudiModificaRiga();
      await loadOrdine();
    } catch (err) {
      setError(err.response?.data?.detail || 'Errore nel salvataggio');
    }
  }, [ordineId, currentUser, formModifica, loadOrdine, chiudiModificaRiga]);

  const confermaRigaCompleta = useCallback(async (riga) => {
    const idRiga = riga.id_dettaglio || riga.id;
    const qVenduta = riga.q_venduta || riga.q_ordinata || riga.quantita || 0;
    const qScontoMerce = riga.q_sconto_merce || 0;
    const qOmaggio = riga.q_omaggio || 0;
    const qTotale = qVenduta + qScontoMerce + qOmaggio;
    const qEvasa = riga.q_evasa || 0;
    const qResiduo = qTotale - qEvasa;

    if (qResiduo <= 0) {
      alert('Questa riga è già completamente evasa.');
      return;
    }

    if ((riga.q_da_evadere || 0) > 0 && riga.q_da_evadere !== qResiduo) {
      if (!window.confirm(`Questa riga ha già ${riga.q_da_evadere} unità da evadere.\nVuoi sovrascrivere con tutto il residuo (${qResiduo})?`)) {
        return;
      }
    }

    try {
      await ordiniApi.registraEvasione(ordineId, idRiga, qResiduo, currentUser?.username || 'admin');
      await loadOrdine();
    } catch (err) {
      setError(err.response?.data?.detail || 'Errore nella conferma');
    }
  }, [ordineId, currentUser, loadOrdine]);

  const ripristinaRiga = useCallback(async (riga) => {
    const idRiga = riga.id_dettaglio || riga.id;
    const qDaEvadere = riga.q_da_evadere || 0;
    const qEvasa = riga.q_evasa || 0;
    const statoRiga = riga.stato_riga;

    // v11.5: Per righe EVASO, mostra conferma HARD RESET
    if (statoRiga === 'EVASO') {
      if (!window.confirm(`HARD RESET - RIGA EVASA\n\n` +
          `Prodotto: ${riga.descrizione || riga.descrizione_prodotto || '-'}\n` +
          `Quantità evasa: ${qEvasa}\n\n` +
          `ATTENZIONE:\n` +
          `- La quantità evasa sarà AZZERATA\n` +
          `- La riga tornerà a stato ESTRATTO\n` +
          `- I tracciati già generati NON saranno annullati\n` +
          `- Potrai generare un nuovo tracciato per questa riga\n\n` +
          `Confermi il ripristino?`)) {
        return;
      }
    } else if (qDaEvadere === 0 && qEvasa === 0) {
      alert('Questa riga non ha quantità da ripristinare.');
      return;
    } else {
      if (!window.confirm(`Vuoi annullare la conferma di questa riga?\n\n` +
          `Prodotto: ${riga.descrizione || riga.descrizione_prodotto || '-'}\n` +
          `Da Evadere attuale: ${qDaEvadere}\n\n` +
          `La quantità "Da Evadere" sarà azzerata.`)) {
        return;
      }
    }

    try {
      await ordiniApi.ripristinaRiga(ordineId, idRiga, currentUser?.username || 'admin');
      await loadOrdine();
    } catch (err) {
      setError(err.response?.data?.detail || 'Errore nel ripristino');
    }
  }, [ordineId, currentUser, loadOrdine]);

  const archiviaRiga = useCallback(async (riga) => {
    const idRiga = riga.id_dettaglio || riga.id;
    const conferma = window.confirm(
      `ARCHIVIAZIONE RIGA\n\n` +
      `Vuoi archiviare la riga #${riga.n_riga}?\n` +
      `Prodotto: ${riga.descrizione || riga.descrizione_prodotto || '-'}\n` +
      `Codice AIC: ${riga.codice_aic || riga.codice_prodotto || '-'}\n\n` +
      `ATTENZIONE:\n` +
      `- Lo stato diventerà ARCHIVIATO (frozen)\n` +
      `- Le quantità saranno bloccate\n` +
      `- Sarà possibile ripristinarla in seguito`
    );
    if (!conferma) return;

    try {
      await ordiniApi.archiviaRiga(ordineId, idRiga, currentUser?.username || 'admin');
      alert(`Riga #${riga.n_riga} archiviata (frozen)`);
      await loadOrdine();
    } catch (err) {
      setError(err.response?.data?.detail || 'Errore nell\'archiviazione della riga');
    }
  }, [ordineId, currentUser, loadOrdine]);

  const ripristinaArchiviata = useCallback(async (riga) => {
    const idRiga = riga.id_dettaglio || riga.id;
    const conferma = window.confirm(
      `RIPRISTINO RIGA ARCHIVIATA\n\n` +
      `Vuoi ripristinare la riga #${riga.n_riga}?\n` +
      `Prodotto: ${riga.descrizione || riga.descrizione_prodotto || '-'}\n\n` +
      `La riga tornerà modificabile e potrà essere inclusa nei tracciati.`
    );
    if (!conferma) return;

    try {
      await ordiniApi.ripristinaRiga(ordineId, idRiga, currentUser?.username || 'admin');
      alert(`Riga #${riga.n_riga} ripristinata`);
      await loadOrdine();
    } catch (err) {
      setError(err.response?.data?.detail || 'Errore nel ripristino della riga');
    }
  }, [ordineId, currentUser, loadOrdine]);

  // =============================================================================
  // BULK HANDLERS
  // =============================================================================

  const confermaTutto = useCallback(async () => {
    // v11.3: Usa l'API conferma-tutto che gestisce anche il blocco per data consegna
    try {
      const result = await ordiniApi.confermaOrdineCompleto(
        ordineId,
        currentUser?.username || 'admin',
        false, // forza_conferma
        null   // note
      );

      if (result.success) {
        // Costruisci messaggio dettagliato
        let msg = result.message || `Confermate ${result.righe_confermate || 0} righe.`;

        // v11.3: Mostra alert per righe bloccate per data consegna
        const bloccateData = result.righe_bloccate_data_consegna || [];
        if (bloccateData.length > 0) {
          msg += `\n\n⚠️ ATTENZIONE: ${bloccateData.length} righe NON confermate perché hanno data di consegna oltre 30 giorni da oggi.`;
          msg += `\n\nModificare la data di consegna per poterle confermare.`;
        }

        // Mostra anche righe che richiedono supervisione
        const bloccateSupervisione = result.righe_bloccate_supervisione || [];
        if (bloccateSupervisione.length > 0) {
          msg += `\n\n${bloccateSupervisione.length} righe richiedono supervisione.`;
        }

        alert(msg);
        await loadOrdine();
      } else {
        setError(result.error || 'Errore nella conferma');
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Errore nella conferma');
    }
  }, [ordineId, currentUser, loadOrdine]);

  const ripristinaTutto = useCallback(async () => {
    const righeConfermate = righe.filter(r => r.stato_riga === 'CONFERMATO' || (r.q_da_evadere || 0) > 0);

    if (righeConfermate.length === 0) {
      alert('Nessuna riga confermata da ripristinare.');
      return;
    }

    if (!window.confirm(`Vuoi annullare la conferma di ${righeConfermate.length} righe?\n\n` +
        `Tutte le quantità "Da Evadere" saranno azzerate.`)) {
      return;
    }

    try {
      const res = await ordiniApi.ripristinaTutto(ordineId, currentUser?.username || 'admin');
      if (res.success) {
        alert(`Ripristinate ${res.righe_ripristinate} righe.`);
        await loadOrdine();
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Errore nel ripristino');
    }
  }, [ordineId, currentUser, righe, loadOrdine]);

  const validaOrdine = useCallback(async () => {
    const righeConDaEvadere = righe.filter(r => (r.q_da_evadere || 0) > 0);

    if (righeConDaEvadere.length === 0) {
      if (!window.confirm('Nessuna riga ha quantità "Da Evadere" impostata.\n\nVuoi impostare automaticamente tutto il residuo?')) {
        return;
      }
      await confermaTutto();
    }

    const totDaEvadere = righe.reduce((sum, r) => sum + (r.q_da_evadere || 0), 0);
    if (!window.confirm(`Procedere alla generazione del tracciato?\n\n` +
        `Righe da esportare: ${righeConDaEvadere.length}\n` +
        `Quantità totale da evadere: ${totDaEvadere} pezzi`)) {
      return;
    }

    try {
      const res = await ordiniApi.validaEGeneraTracciato(ordineId, currentUser?.username || 'admin');
      if (res.success) {
        alert(`Tracciato generato!\nRighe esportate: ${res.statistiche?.righe_esportate || 0}`);
        await loadOrdine();
      } else {
        throw new Error(res.error || 'Errore nella validazione');
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Errore nella validazione');
    }
  }, [ordineId, currentUser, righe, loadOrdine, confermaTutto]);

  // =============================================================================
  // ANOMALIE HANDLERS
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
      setError('Errore caricamento dettaglio: ' + err.message);
      setShowAnomaliaDetailModal(false);
    } finally {
      setLoadingAnomaliaDetail(false);
    }
  }, []);

  const risolviAnomalia = useCallback(async (anomaliaId) => {
    try {
      await anomalieApi.update(anomaliaId, 'risolta', 'Risolta da dettaglio ordine');
      await loadOrdine();
    } catch (err) {
      setError(err.response?.data?.detail || 'Errore nella risoluzione anomalia');
    }
  }, [loadOrdine]);

  const saveRigaParent = useCallback(async (editingData) => {
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
      setError('Errore: ' + err.message);
      return false;
    }
  }, [anomaliaDetail, loadAnomaliaDetail]);

  const risolviAnomaliaDetail = useCallback(async () => {
    if (!anomaliaDetail?.anomalia?.id_anomalia) return;

    const nota = prompt('Nota di risoluzione (opzionale):');
    if (nota === null) return;

    try {
      const res = await anomalieApi.risolviDettaglio(anomaliaDetail.anomalia.id_anomalia, nota || 'Risolta da dettaglio');
      if (res.success) {
        alert('Anomalia risolta');
        setShowAnomaliaDetailModal(false);
        setAnomaliaDetail(null);
        await loadOrdine();
      }
    } catch (err) {
      setError('Errore: ' + err.message);
    }
  }, [anomaliaDetail, loadOrdine]);

  const assignFarmacia = useCallback(async (idTestata, idFarmacia, idParafarmacia, minIdManuale = null) => {
    try {
      const res = await lookupApi.manuale(idTestata, idFarmacia, idParafarmacia, minIdManuale, currentUser?.username);
      if (res.success) {
        alert(minIdManuale ? `MIN_ID ${minIdManuale} assegnato` : 'Farmacia assegnata');
        setShowAnomaliaDetailModal(false);
        setAnomaliaDetail(null);
        await loadOrdine();
        return true;
      }
      return false;
    } catch (err) {
      setError('Errore: ' + err.message);
      return false;
    }
  }, [loadOrdine, currentUser]);

  const closeAnomaliaModal = useCallback(() => {
    setShowAnomaliaDetailModal(false);
    setAnomaliaDetail(null);
  }, []);

  // =============================================================================
  // CORREZIONE LISTINO HANDLERS (v11.5)
  // =============================================================================

  const handleOpenCorrezioneListino = useCallback(async (anomaliaDetailData) => {
    const idAnomalia = anomaliaDetailData?.anomalia?.id_anomalia;
    if (!idAnomalia) return;

    try {
      const supData = await supervisioneApi.getListinoByAnomalia(idAnomalia);
      // Chiudi modal anomalia e apri modal correzione
      setShowAnomaliaDetailModal(false);
      setAnomaliaDetail(null);
      setCorrezioneListinoModal({ isOpen: true, supervisione: supData });
    } catch (err) {
      const msg = err.response?.status === 404
        ? 'Supervisione listino non trovata per questa anomalia'
        : 'Errore nel caricamento della supervisione: ' + (err.response?.data?.detail || err.message);
      alert(msg);
    }
  }, []);

  const handleCloseCorrezioneListino = useCallback(() => {
    setCorrezioneListinoModal({ isOpen: false, supervisione: null });
  }, []);

  const handleCorrezioneListinoSuccess = useCallback(() => {
    setCorrezioneListinoModal({ isOpen: false, supervisione: null });
    loadOrdine();
  }, [loadOrdine]);

  // =============================================================================
  // SUPERVISIONE HANDLERS
  // =============================================================================

  const approvaSuper = useCallback(async (idSupervisione) => {
    try {
      await fetch(`/api/v1/supervisione/${idSupervisione}/approva`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ operatore: currentUser?.username || 'operatore', note: 'Confermato da dettaglio ordine' })
      });
      await loadOrdine();
    } catch (err) {
      setError(`Errore approvazione: ${err.message}`);
    }
  }, [currentUser, loadOrdine]);

  const rifiutaSuper = useCallback(async (idSupervisione) => {
    try {
      await fetch(`/api/v1/supervisione/${idSupervisione}/rifiuta`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ operatore: currentUser?.username || 'operatore', note: 'Rifiutato da dettaglio ordine' })
      });
      await loadOrdine();
    } catch (err) {
      setError(`Errore rifiuto: ${err.message}`);
    }
  }, [currentUser, loadOrdine]);

  // =============================================================================
  // ESPOSITORE HANDLERS
  // =============================================================================

  const fixEspositore = useCallback(async (righeToUpdate) => {
    try {
      const result = await ordiniApi.fixEspositore(
        ordineId,
        righeToUpdate,
        currentUser?.username || 'admin',
        'Fix espositore da dettaglio ordine'
      );
      if (result.success) {
        await loadOrdine();
      }
      return result;
    } catch (err) {
      const errorMsg = err.response?.data?.detail || err.message || 'Errore fix espositore';
      setError(errorMsg);
      return { success: false, error: errorMsg };
    }
  }, [ordineId, currentUser, loadOrdine]);

  // =============================================================================
  // SORT HANDLER (v11.3)
  // =============================================================================

  const handleSort = useCallback((field) => {
    if (sortField === field) {
      setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  }, [sortField]);

  // =============================================================================
  // COMPUTED VALUES
  // =============================================================================

  const stats = {
    totaleRighe: righe.length,
    totaleEvase: righe.reduce((sum, r) => sum + (r.q_evasa || 0), 0),
    totaleDaEvadere: righe.reduce((sum, r) => sum + (r.q_da_evadere || 0), 0),
    totaleResiduo: righe.reduce((sum, r) => {
      const qTot = (r.q_venduta || 0) + (r.q_sconto_merce || 0) + (r.q_omaggio || 0);
      return sum + Math.max(0, qTot - (r.q_evasa || 0));
    }, 0),
    tutteEvase: righe.every(r => {
      const qTot = (r.q_venduta || 0) + (r.q_sconto_merce || 0) + (r.q_omaggio || 0);
      return qTot - (r.q_evasa || 0) <= 0;
    }),
    haRigheConfermate: righe.some(r => r.stato_riga === 'CONFERMATO' || (r.q_da_evadere || 0) > 0)
  };

  return {
    // Data
    ordine,
    righe,
    righeAll,  // Include children for EspositoreTab
    anomalie,
    supervisioni,
    stats,

    // UI state
    loading,
    error,
    setError,
    activeTab,
    setActiveTab,
    actionLoading,

    // v11.3: Sort state (persists across reloads and tab changes)
    sortField,
    sortDirection,
    handleSort,

    // Edit state
    rigaInModifica,
    formModifica,
    setFormModifica,

    // Modal state
    showPdfModal,
    setShowPdfModal,
    showAnomaliaDetailModal,
    anomaliaDetail,
    loadingAnomaliaDetail,
    correzioneListinoModal,

    // Actions
    loadOrdine,
    apriModificaRiga,
    chiudiModificaRiga,
    salvaModificaRiga,
    confermaRigaCompleta,
    ripristinaRiga,
    archiviaRiga,
    ripristinaArchiviata,
    confermaTutto,
    ripristinaTutto,
    validaOrdine,
    loadAnomaliaDetail,
    risolviAnomalia,
    saveRigaParent,
    risolviAnomaliaDetail,
    assignFarmacia,
    closeAnomaliaModal,
    handleOpenCorrezioneListino,
    handleCloseCorrezioneListino,
    handleCorrezioneListinoSuccess,
    approvaSuper,
    rifiutaSuper,
    fixEspositore
  };
}

export default useOrdineDetail;
