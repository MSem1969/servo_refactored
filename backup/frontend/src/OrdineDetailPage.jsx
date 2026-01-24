// =============================================================================
// TO_EXTRACTOR v6.2 - ORDINE DETAIL PAGE
// =============================================================================
// Pagina dettaglio ordine con gestione righe e anomalie
// =============================================================================

import React, { useState, useEffect, useCallback } from 'react';
import { ordiniApi, anomalieApi, lookupApi } from './api';
import { Button, StatusBadge, Loading, ErrorBox } from './common';
// v6.2: Componenti condivisi
import { AnomaliaDetailModal } from './components';

// =============================================================================
// ORDINE DETAIL PAGE COMPONENT
// =============================================================================

export default function OrdineDetailPage({ ordineId, currentUser, onBack, onNavigateToSupervisione }) {
  // State
  const [ordine, setOrdine] = useState(null);
  const [righe, setRighe] = useState([]);
  const [anomalie, setAnomalieList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('righe');
  const [editMode, setEditMode] = useState(false);
  const [editData, setEditData] = useState({});
  const [saving, setSaving] = useState(false);
  const [actionLoading, setActionLoading] = useState(null);
  const [rigaInModifica, setRigaInModifica] = useState(null);
  const [formModifica, setFormModifica] = useState({
    codice_aic: '',
    descrizione: '',
    q_venduta: 0,
    q_sconto_merce: 0,
    q_omaggio: 0,
    q_da_evadere: 0,  // v6.2.1: Quantità da evadere nel prossimo tracciato
    prezzo_netto: 0,
    prezzo_pubblico: 0,
    sconto_1: 0,
    sconto_2: 0,
    sconto_3: 0,
    sconto_4: 0,
    note_allestimento: ''
  });
  const [showPdfModal, setShowPdfModal] = useState(false);
  const [supervisioni, setSupervisioni] = useState([]);

  // v6.2: State per modal dettaglio anomalia (refactored)
  const [showAnomaliaDetailModal, setShowAnomaliaDetailModal] = useState(false);
  const [anomaliaDetail, setAnomaliaDetail] = useState(null);
  const [loadingAnomaliaDetail, setLoadingAnomaliaDetail] = useState(false);

  // =============================================================================
  // LOAD DATA
  // =============================================================================

  const loadOrdine = useCallback(async () => {
    if (!ordineId) return;

    setLoading(true);
    setError(null);

    try {
      const [ordineData, righeData, anomalieData] = await Promise.all([
        ordiniApi.getDetail(ordineId),
        ordiniApi.getRighe(ordineId),
        anomalieApi.getByOrdine(ordineId).catch(() => ({ items: [] }))
      ]);

      setOrdine(ordineData?.data || ordineData);

      // Gestisce diversi formati di risposta API
      const righeArray = Array.isArray(righeData)
        ? righeData
        : (righeData?.righe || righeData?.data || righeData?.items || []);
      setRighe(righeArray);

      const anomalieArray = Array.isArray(anomalieData)
        ? anomalieData
        : (anomalieData?.items || anomalieData?.data || anomalieData?.anomalie || []);
      setAnomalieList(anomalieArray);

      // Carica supervisioni espositore
      try {
        const supData = await fetch(`/api/v1/supervisione/ordine/${ordineId}`).then(r => r.json());
        setSupervisioni(supData?.supervisioni || []);
      } catch (e) {
        console.log('Nessuna supervisione');
        setSupervisioni([]);
      }

      setEditData(ordineData?.data || ordineData);
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
  // HANDLERS
  // =============================================================================

  const handleEdit = () => {
    setEditMode(true);
    setEditData({ ...ordine });
  };

  const handleCancelEdit = () => {
    setEditMode(false);
    setEditData({ ...ordine });
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      // Per ora salviamo solo lo stato
      await ordiniApi.updateStato(ordineId, editData.stato);
      await loadOrdine();
      setEditMode(false);
    } catch (err) {
      setError(err.response?.data?.detail || 'Errore nel salvataggio');
    } finally {
      setSaving(false);
    }
  };

  const handleUpdateStato = async (nuovoStato) => {
    setActionLoading(nuovoStato);
    try {
      await ordiniApi.updateStato(ordineId, nuovoStato);
      await loadOrdine();
    } catch (err) {
      setError(err.response?.data?.detail || 'Errore nell\'aggiornamento stato');
    } finally {
      setActionLoading(null);
    }
  };

  const handleValidaEGenera = async () => {
    setActionLoading('valida');
    try {
      const result = await ordiniApi.validaEGeneraTracciato(ordineId, currentUser?.username || 'operatore');
      alert(`Ordine validato! Tracciato: ${result.tracciato || 'generato'}`);
      await loadOrdine();
    } catch (err) {
      setError(err.response?.data?.detail || 'Errore nella validazione');
    } finally {
      setActionLoading(null);
    }
  };

  const handleConfermaRiga = async (idDettaglio) => {
    try {
      await ordiniApi.confermaRiga(ordineId, idDettaglio, currentUser?.username || 'operatore');
      await loadOrdine();
    } catch (err) {
      setError(err.response?.data?.detail || 'Errore nella conferma riga');
    }
  };

  // v6.2.1: Conferma tutte le righe NON modificate manualmente
  // REGOLA: Se q_da_evadere è già impostato (modifica manuale), NON sovrascrivere
  const handleConfermaTutto = async () => {
    // Conta righe per categoria
    let righeGiaImpostate = 0;
    let righeDaImpostare = [];

    righe.forEach(r => {
      const qVenduta = r.q_venduta || r.q_ordinata || r.quantita || 0;
      const qScontoMerce = r.q_sconto_merce || 0;
      const qOmaggio = r.q_omaggio || 0;
      const qTotale = qVenduta + qScontoMerce + qOmaggio;
      const qEvasa = r.q_evasa || 0;
      const qResiduo = qTotale - qEvasa;
      const qDaEvadere = r.q_da_evadere || 0;

      if (qResiduo <= 0) {
        // Riga già completamente evasa - skip
        return;
      }

      if (qDaEvadere > 0) {
        // Riga già impostata manualmente - NON toccare
        righeGiaImpostate++;
      } else {
        // Riga da impostare automaticamente
        righeDaImpostare.push({ riga: r, qResiduo });
      }
    });

    if (righeDaImpostare.length === 0 && righeGiaImpostate === 0) {
      alert('Tutte le righe sono già completamente evase.');
      return;
    }

    if (righeDaImpostare.length === 0) {
      alert(`Tutte le righe con residuo hanno già "Da Evadere" impostato (${righeGiaImpostate} righe).\nLe modifiche manuali vengono preservate.`);
      return;
    }

    // Mostra info se ci sono righe manuali che verranno preservate
    if (righeGiaImpostate > 0) {
      const conferma = window.confirm(
        `Verranno impostate ${righeDaImpostare.length} righe con tutto il residuo.\n\n` +
        `${righeGiaImpostate} righe con "Da Evadere" già impostato manualmente verranno PRESERVATE.\n\n` +
        `Continuare?`
      );
      if (!conferma) return;
    }

    try {
      for (const { riga, qResiduo } of righeDaImpostare) {
        const idRiga = riga.id_dettaglio || riga.id;
        await ordiniApi.registraEvasione(ordineId, idRiga, qResiduo, currentUser?.username || 'admin');
      }
      await loadOrdine();
    } catch (err) {
      setError(err.response?.data?.detail || 'Errore nella conferma');
    }
  };

  const handleApriModificaRiga = (riga) => {
    setRigaInModifica(riga);
    // v6.2.1: Usa q_da_evadere invece di q_evasa
    const qVenduta = riga.q_venduta || riga.q_ordinata || riga.quantita || 0;
    const qScontoMerce = riga.q_sconto_merce || 0;
    const qOmaggio = riga.q_omaggio || 0;

    setFormModifica({
      codice_aic: riga.codice_aic || riga.codice_prodotto || '',
      descrizione: riga.descrizione || riga.descrizione_prodotto || '',
      q_venduta: qVenduta,
      q_sconto_merce: qScontoMerce,
      q_omaggio: qOmaggio,
      q_da_evadere: riga.q_da_evadere || 0,  // Default: 0 (utente deve inserire)
      prezzo_netto: riga.prezzo_netto || 0,
      prezzo_pubblico: riga.prezzo_pubblico || 0,
      sconto_1: riga.sconto_1 || 0,
      sconto_2: riga.sconto_2 || 0,
      sconto_3: riga.sconto_3 || 0,
      sconto_4: riga.sconto_4 || 0,
      note_allestimento: riga.note_allestimento || ''
    });
  };








  // v6.2.1: Salva la modifica della riga (quantità da evadere)
  const handleSalvaModificaRiga = async (riga) => {
    const idRiga = riga.id_dettaglio || riga.id;
    try {
      // Prepara le modifiche dei campi base
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

      // Salva le modifiche dei campi
      await ordiniApi.modificaRiga(ordineId, idRiga, currentUser?.username || 'admin', modifiche);

      // v6.2.1: Registra q_da_evadere (quantità da esportare nel prossimo tracciato)
      const qDaEvadere = parseInt(formModifica.q_da_evadere) || 0;
      if (qDaEvadere >= 0) {
        await ordiniApi.registraEvasione(ordineId, idRiga, qDaEvadere, currentUser?.username || 'admin');
      }

      setRigaInModifica(null);
      setFormModifica({
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
      });
      await loadOrdine();
    } catch (err) {
      setError(err.response?.data?.detail || 'Errore nel salvataggio');
    }
  };
  // v6.2.1: Conferma completamente una riga (imposta q_da_evadere = residuo)
  const handleConfermaRigaCompleta = async (riga) => {
    const idRiga = riga.id_dettaglio || riga.id;
    // Quantità totale = venduta + sconto merce + omaggio
    const qVenduta = riga.q_venduta || riga.q_ordinata || riga.quantita || 0;
    const qScontoMerce = riga.q_sconto_merce || 0;
    const qOmaggio = riga.q_omaggio || 0;
    const qTotale = qVenduta + qScontoMerce + qOmaggio;
    const qEvasa = riga.q_evasa || 0;
    const qResiduo = qTotale - qEvasa;

    // Se non c'è residuo, non c'è nulla da evadere
    if (qResiduo <= 0) {
      alert('Questa riga è già completamente evasa.');
      return;
    }

    // Se ha già una quantità da evadere impostata, chiedi conferma
    if ((riga.q_da_evadere || 0) > 0 && riga.q_da_evadere !== qResiduo) {
      if (!window.confirm(`Questa riga ha già ${riga.q_da_evadere} unità da evadere.\nVuoi sovrascrivere con tutto il residuo (${qResiduo})?`)) {
        return;
      }
    }

    // Imposta q_da_evadere = residuo (tutto il rimanente)
    try {
      await ordiniApi.registraEvasione(ordineId, idRiga, qResiduo, currentUser?.username || 'admin');
      await loadOrdine();
    } catch (err) {
      setError(err.response?.data?.detail || 'Errore nella conferma');
    }
  };

  // v6.2.1: Ripristina singola riga (annulla conferma)
  const handleRipristinaRiga = async (riga) => {
    const idRiga = riga.id_dettaglio || riga.id;
    const qDaEvadere = riga.q_da_evadere || 0;

    if (qDaEvadere === 0) {
      alert('Questa riga non ha quantità "Da Evadere" impostata.');
      return;
    }

    if (!window.confirm(`Vuoi annullare la conferma di questa riga?\n\n` +
        `Prodotto: ${riga.descrizione || riga.descrizione_prodotto || '-'}\n` +
        `Da Evadere attuale: ${qDaEvadere}\n\n` +
        `La quantità "Da Evadere" sarà azzerata.`)) {
      return;
    }

    try {
      await ordiniApi.ripristinaRiga(ordineId, idRiga, currentUser?.username || 'admin');
      await loadOrdine();
    } catch (err) {
      setError(err.response?.data?.detail || 'Errore nel ripristino');
    }
  };

  // v6.2.1: Ripristina tutte le righe confermate
  const handleRipristinaTutto = async () => {
    const righeConfermate = righe.filter(r => r.stato_riga === 'CONFERMATO' || (r.q_da_evadere || 0) > 0);

    if (righeConfermate.length === 0) {
      alert('Nessuna riga confermata da ripristinare.');
      return;
    }

    if (!window.confirm(`Vuoi annullare la conferma di ${righeConfermate.length} righe?\n\n` +
        `Tutte le quantità "Da Evadere" saranno azzerate.\n` +
        `Le righe torneranno allo stato precedente.`)) {
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
  };

  // v6.2.1: Valida ordine e genera tracciato
  const handleValidaOrdine = async () => {
    // Verifica se ci sono righe con q_da_evadere > 0 (quantità da esportare in questo tracciato)
    const righeConDaEvadere = righe.filter(r => (r.q_da_evadere || 0) > 0);

    if (righeConDaEvadere.length === 0) {
      if (!window.confirm('Nessuna riga ha quantità "Da Evadere" impostata.\n\nVuoi impostare automaticamente tutto il residuo per ogni riga e generare il tracciato?')) {
        return;
      }
      // Conferma tutte le righe prima di validare
      await handleConfermaTutto();
    }

    // Mostra riepilogo quantità da esportare
    const totDaEvadere = righe.reduce((sum, r) => sum + (r.q_da_evadere || 0), 0);
    if (!window.confirm(`Procedere alla generazione del tracciato?\n\n` +
        `Righe da esportare: ${righeConDaEvadere.length}\n` +
        `Quantità totale da evadere: ${totDaEvadere} pezzi\n\n` +
        `Questa operazione:\n` +
        `- Genererà i file TO_T e TO_D\n` +
        `- Aggiornerà q_evaso (cumulativo)\n` +
        `- Resetterà q_da_evadere a 0`)) {
      return;
    }

    try {
      const res = await ordiniApi.validaEGeneraTracciato(ordineId, currentUser?.username || 'admin');
      if (res.success) {
        alert(`Tracciato generato con successo!\n\n` +
              `Righe esportate: ${res.statistiche?.righe_esportate || 0}\n` +
              `Stato ordine: ${res.stato}`);
        await loadOrdine();
      } else {
        throw new Error(res.error || 'Errore nella validazione');
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Errore nella validazione');
    }
  };

  const handleInviaASupervisione = async (idDettaglio) => {
    try {
      const result = await ordiniApi.inviaASupervisione(ordineId, idDettaglio, currentUser?.username || 'operatore');
      await loadOrdine();
      if (onNavigateToSupervisione && result?.id_supervisione) {
        onNavigateToSupervisione(result.id_supervisione, ordineId);
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Errore nell\'invio a supervisione');
    }
  };

  const handleRisolviAnomalia = async (anomaliaId) => {
    try {
      await anomalieApi.update(anomaliaId, 'risolta', 'Risolta da dettaglio ordine');
      await loadOrdine();
    } catch (err) {
      setError(err.response?.data?.detail || 'Errore nella risoluzione anomalia');
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
      setError('Errore caricamento dettaglio: ' + err.message);
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
        await loadAnomaliaDetail(anomaliaDetail.anomalia.id_anomalia);
        return true;
      }
      return false;
    } catch (err) {
      setError('Errore: ' + err.message);
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
        await loadOrdine();
      }
    } catch (err) {
      setError('Errore: ' + err.message);
    }
  };

  // v6.2: Assegna farmacia manualmente (da ricerca o MIN_ID manuale)
  const handleAssignFarmacia = async (idTestata, idFarmacia, idParafarmacia, minIdManuale = null) => {
    try {
      const res = await lookupApi.manuale(idTestata, idFarmacia, idParafarmacia, minIdManuale);
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
  };

  const handleArchiviaRiga = async (riga) => {
    const idRiga = riga.id_dettaglio || riga.id;
    const conferma = window.confirm(
      `ARCHIVIAZIONE RIGA\n\n` +
      `Vuoi archiviare la riga #${riga.n_riga}?\n` +
      `Prodotto: ${riga.descrizione || riga.descrizione_prodotto || '-'}\n` +
      `Codice AIC: ${riga.codice_aic || riga.codice_prodotto || '-'}\n\n` +
      `ATTENZIONE:\n` +
      `- Lo stato diventerà ARCHIVIATO (frozen)\n` +
      `- Le quantità saranno bloccate\n` +
      `- Sarà possibile ripristinarla in seguito\n\n` +
      `Premi OK per confermare, Annulla per tornare indietro.`
    );
    if (!conferma) {
      return;
    }
    try {
      await ordiniApi.archiviaRiga(ordineId, idRiga, currentUser?.username || 'admin');
      alert(`Riga #${riga.n_riga} archiviata (frozen)`);
      await loadOrdine();
    } catch (err) {
      setError(err.response?.data?.detail || 'Errore nell\'archiviazione della riga');
    }
  };

  // Ripristina riga da stato ARCHIVIATO
  const handleRipristinaArchiviata = async (riga) => {
    const idRiga = riga.id_dettaglio || riga.id;
    const conferma = window.confirm(
      `RIPRISTINO RIGA ARCHIVIATA\n\n` +
      `Vuoi ripristinare la riga #${riga.n_riga}?\n` +
      `Prodotto: ${riga.descrizione || riga.descrizione_prodotto || '-'}\n\n` +
      `La riga tornerà modificabile e potrà essere inclusa nei tracciati.`
    );
    if (!conferma) {
      return;
    }
    try {
      await ordiniApi.ripristinaRiga(ordineId, idRiga, currentUser?.username || 'admin');
      alert(`Riga #${riga.n_riga} ripristinata`);
      await loadOrdine();
    } catch (err) {
      setError(err.response?.data?.detail || 'Errore nel ripristino della riga');
    }
  };

  const handleApprovaSuper = async (idSupervisione) => {
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
  };

  const handleRifiutaSuper = async (idSupervisione) => {
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
  };

  // =============================================================================
  // RENDER HELPERS
  // =============================================================================

  const getStatoColor = (stato) => {
    const colors = {
      'nuovo': 'bg-blue-100 text-blue-800',
      'in_lavorazione': 'bg-yellow-100 text-yellow-800',
      'validato': 'bg-green-100 text-green-800',
      'esportato': 'bg-purple-100 text-purple-800',
      'errore': 'bg-red-100 text-red-800',
      'supervisione': 'bg-orange-100 text-orange-800',
      // Stati ordine v6.2
      'ESTRATTO': 'bg-blue-100 text-blue-800',
      'CONFERMATO': 'bg-cyan-100 text-cyan-800',
      'ANOMALIA': 'bg-red-100 text-red-800',
      'PARZ_EVASO': 'bg-orange-100 text-orange-800',
      'EVASO': 'bg-green-100 text-green-800',
      'ARCHIVIATO': 'bg-slate-100 text-slate-600'
    };
    return colors[stato] || 'bg-slate-100 text-slate-800';
  };

  const getLivelloColor = (livello) => {
    const colors = {
      'critico': 'bg-red-100 text-red-800 border-red-300',
      'alto': 'bg-orange-100 text-orange-800 border-orange-300',
      'medio': 'bg-yellow-100 text-yellow-800 border-yellow-300',
      'basso': 'bg-blue-100 text-blue-800 border-blue-300'
    };
    return colors[livello] || 'bg-slate-100 text-slate-800 border-slate-300';
  };

  // =============================================================================
  // RENDER
  // =============================================================================

  if (loading) {
    return <Loading text="Caricamento ordine..." />;
  }

  if (error && !ordine) {
    return (
      <div className="space-y-4">
        <ErrorBox.Error message={error} />
        <Button variant="secondary" onClick={onBack}>
          Torna al Database
        </Button>
      </div>
    );
  }

  if (!ordine) {
    return (
      <div className="text-center py-8">
        <p className="text-slate-500">Ordine non trovato</p>
        <Button variant="secondary" onClick={onBack} className="mt-4">
          Torna al Database
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-xl border border-slate-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-4">
            <h2 className="text-xl font-bold text-slate-800">
              Ordine #{ordine?.numero_ordine_vendor || ordine?.numero_ordine || ordine?.id_testata || '-'}
            </h2>
            <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatoColor(ordine.stato)}`}>
              {ordine.stato?.toUpperCase()}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="secondary" onClick={onBack}>
              ← Torna al Database
            </Button>
            {ordine?.pdf_file && (
              <button
                onClick={() => setShowPdfModal(true)}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
              >
                📄 Visualizza PDF
              </button>
            )}
          </div>
        </div>

        {/* Info rapide */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-sm">
          <div>
            <span className="text-slate-500">Vendor:</span>
            <span className="ml-2 font-medium">{ordine?.vendor || '-'}</span>
          </div>
          <div>
            <span className="text-slate-500">Data:</span>
            <span className="ml-2 font-medium">{ordine?.data_ordine || '-'}</span>
          </div>
          <div>
            <span className="text-slate-500">Cliente:</span>
            <span className="ml-2 font-medium">{ordine?.ragione_sociale || '-'}</span>
          </div>
          <div>
            <span className="text-slate-500">Città:</span>
            <span className="ml-2 font-medium">{ordine?.citta && ordine?.provincia ? `${ordine.citta} (${ordine.provincia})` : '-'}</span>
          </div>
          <div>
            <span className="text-slate-500">Righe:</span>
            <span className="ml-2 font-medium">{righe.length}</span>
          </div>
        </div>
      </div>

      {/* Error message */}
      {error && <ErrorBox.Error message={error} onDismiss={() => setError(null)} />}

      {/* Tabs: Righe e Anomalie */}
      <div className="bg-white rounded-xl border border-slate-200">
        <div className="border-b border-slate-200">
          <nav className="flex gap-1 p-1">
            {[
              { id: 'righe', label: `Righe (${righe.length})`, icon: '📦' },
              { id: 'anomalie', label: `Anomalie (${anomalie.length + supervisioni.length})`, icon: '⚠️' }
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  activeTab === tab.id
                    ? 'bg-blue-100 text-blue-800'
                    : 'text-slate-600 hover:bg-slate-100'
                }`}
              >
                <span>{tab.icon}</span>
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        <div className="p-6">
          {/* Tab: Righe */}
          {activeTab === 'righe' && (
            <div className="p-4">
              {/* v6.2.1: Riepilogo quantità e azioni in blocco */}
              <div className="flex justify-between items-center mb-4">
                <div className="text-sm text-slate-500 flex flex-wrap gap-x-3">
                  <span>{righe.length} righe totali</span>
                  <span className="text-green-600">
                    {righe.reduce((sum, r) => sum + (r.q_evasa || 0), 0)} evase
                  </span>
                  <span className="text-blue-600 font-medium">
                    {righe.reduce((sum, r) => sum + (r.q_da_evadere || 0), 0)} da evadere
                  </span>
                  <span className="text-orange-600">
                    {righe.reduce((sum, r) => {
                      const qTot = (r.q_venduta || 0) + (r.q_sconto_merce || 0) + (r.q_omaggio || 0);
                      return sum + Math.max(0, qTot - (r.q_evasa || 0));
                    }, 0)} residuo
                  </span>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={handleConfermaTutto}
                    disabled={righe.length === 0 || righe.every(r => {
                      const qTot = (r.q_venduta || 0) + (r.q_sconto_merce || 0) + (r.q_omaggio || 0);
                      return qTot - (r.q_evasa || 0) <= 0;
                    })}
                    className="px-4 py-2 bg-green-500 hover:bg-green-600 disabled:bg-slate-300 disabled:cursor-not-allowed text-white rounded-lg text-sm font-medium"
                    title="Imposta Da Evadere = Residuo per tutte le righe"
                  >
                    ✓ Conferma Tutto
                  </button>
                  <button
                    onClick={handleRipristinaTutto}
                    disabled={righe.length === 0 || !righe.some(r => r.stato_riga === 'CONFERMATO' || (r.q_da_evadere || 0) > 0)}
                    className="px-4 py-2 bg-orange-500 hover:bg-orange-600 disabled:bg-slate-300 disabled:cursor-not-allowed text-white rounded-lg text-sm font-medium"
                    title="Annulla conferma per tutte le righe"
                  >
                    ↩ Ripristina Tutto
                  </button>
                </div>
              </div>

              {/* Tabella Righe */}
              {righe.length === 0 ? (
                <div className="text-center py-8 text-slate-500">
                  <div className="text-4xl mb-2">📦</div>
                  <p>Nessuna riga per questo ordine</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-slate-50 text-left text-xs font-medium text-slate-500 uppercase">
                      <tr>
                        <th className="px-3 py-3">N.</th>
                        <th className="px-3 py-3">Codice AIC</th>
                        <th className="px-3 py-3">Descrizione</th>
                        <th className="px-3 py-3 text-center">Ordinato</th>
                        <th className="px-3 py-3 text-center">Sc. Merce</th>
                        <th className="px-3 py-3 text-center">Omaggio</th>
                        <th className="px-3 py-3 text-center bg-green-50" title="Quantità già esportata in tracciati precedenti">Evaso</th>
                        <th className="px-3 py-3 text-center bg-blue-50" title="Quantità da esportare nel prossimo tracciato (editabile)">Da Evadere</th>
                        <th className="px-3 py-3 text-center bg-orange-50" title="Rimanente da evadere in futuro">Residuo</th>
                        <th className="px-3 py-3">Prezzo</th>
                        <th className="px-3 py-3">Stato</th>
                        <th className="px-3 py-3 text-center">Azioni</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200">
                      {righe.map((riga, index) => {
                        const qOrdinata = riga.q_ordinata || riga.q_venduta || riga.quantita || 0;
                        const qTotale = qOrdinata + (riga.q_sconto_merce || 0) + (riga.q_omaggio || 0);
                        const qEvasa = riga.q_evasa || 0;  // Cumulativo già esportato
                        const qDaEvadere = riga.q_da_evadere || 0;  // Da esportare nel prossimo tracciato
                        const qResidua = qTotale - qEvasa;  // Rimanente totale (senza considerare q_da_evadere)
                        const isEditing = rigaInModifica && (rigaInModifica.id_dettaglio || rigaInModifica.id) === (riga.id_dettaglio || riga.id);

                        return (
                          <tr key={riga.id_dettaglio || riga.id || index} className={`hover:bg-slate-50 ${riga.is_espositore ? 'bg-purple-50' : ''}`}>
                            <td className="px-3 py-3 text-slate-500">{riga.n_riga || index + 1}</td>
                            <td className="px-3 py-3">
                              <div className="font-mono text-xs">{riga.codice_aic || riga.codice_prodotto || '-'}</div>
                              {riga.codice_originale && riga.codice_originale !== riga.codice_aic && (
                                <div className="text-xs text-slate-400">
                                  {riga.codice_originale}
                                </div>
                              )}
                            </td>
                            <td className="px-3 py-3">
                              {!!(riga.is_espositore || (riga.codice_originale && riga.codice_originale !== riga.codice_aic)) && (
                                <span className="mr-1" title="Espositore">🎁</span>
                              )}
                              {riga.descrizione_prodotto || riga.descrizione || '-'}
                            </td>

                            {/* Quantità Ordinata */}
                            <td className="px-3 py-3 text-center font-medium">{qOrdinata}</td>

                            {/* Sconto Merce */}
                            <td className="px-3 py-3 text-center">
                              {riga.q_sconto_merce > 0 ? (
                                <span className="px-2 py-0.5 bg-amber-100 text-amber-700 rounded text-xs">{riga.q_sconto_merce}</span>
                              ) : '-'}
                            </td>

                            {/* Omaggio */}
                            <td className="px-3 py-3 text-center">
                              {riga.q_omaggio > 0 ? (
                                <span className="px-2 py-0.5 bg-green-100 text-green-700 rounded text-xs">{riga.q_omaggio}</span>
                              ) : '-'}
                            </td>

                            {/* Quantità Evasa - READ-ONLY (cumulativo già esportato) */}
                            <td className="px-3 py-3 text-center bg-green-50/50">
                              <span className={qEvasa > 0 ? 'text-green-600 font-medium' : 'text-slate-400'}>
                                {qEvasa}
                              </span>
                            </td>

                            {/* Quantità Da Evadere - EDITABILE (per prossimo tracciato) */}
                            <td className="px-3 py-3 text-center bg-blue-50/50">
                              {isEditing ? (
                                <input
                                  type="number"
                                  min="0"
                                  max={qResidua}
                                  value={formModifica.q_da_evadere}
                                  onChange={(e) => setFormModifica(f => ({ ...f, q_da_evadere: parseInt(e.target.value) || 0 }))}
                                  onFocus={(e) => e.target.select()}
                                  className="w-16 px-2 py-1 border border-blue-400 rounded text-center text-sm bg-white"
                                  autoFocus
                                />
                              ) : (
                                <span className={qDaEvadere > 0 ? 'text-blue-600 font-bold' : 'text-slate-400'}>
                                  {qDaEvadere > 0 ? qDaEvadere : '-'}
                                </span>
                              )}
                            </td>

                            {/* Quantità Residua - READ-ONLY (rimanente totale) */}
                            <td className="px-3 py-3 text-center bg-orange-50/50">
                              {qResidua > 0 ? (
                                <span className="text-orange-600 font-medium">{qResidua}</span>
                              ) : (
                                <span className="text-green-600">-</span>
                              )}
                            </td>

                            {/* Prezzo */}
                            <td className="px-3 py-3 text-right">
                              {riga.prezzo_netto ? `€ ${parseFloat(riga.prezzo_netto).toFixed(2)}` : '-'}
                            </td>

                            {/* Stato */}
                            <td className="px-3 py-3">
                              <span className={`px-2 py-1 rounded text-xs font-medium ${
                                riga.stato_riga === 'ARCHIVIATO' ? 'bg-slate-200 text-slate-700' :
                                riga.stato_riga === 'EVASO' ? 'bg-green-100 text-green-700' :
                                riga.stato_riga === 'CONFERMATO' ? 'bg-cyan-100 text-cyan-700' :
                                riga.stato_riga === 'PARZIALE' ? 'bg-yellow-100 text-yellow-700' :
                                riga.stato_riga === 'IN_SUPERVISIONE' ? 'bg-purple-100 text-purple-700' :
                                'bg-slate-100 text-slate-600'
                              }`}>
                                {riga.stato_riga === 'ARCHIVIATO' ? '🔒 ARCH' :
                                 riga.stato_riga === 'EVASO' ? '✓ EVASO' :
                                 riga.stato_riga === 'CONFERMATO' ? 'CONF' :
                                 riga.stato_riga === 'PARZIALE' ? 'PARZ' :
                                 riga.stato_riga === 'IN_SUPERVISIONE' ? 'SUP' :
                                 'PND'}
                              </span>
                            </td>

                            {/* Azioni */}
                            <td className="px-3 py-3">
                              <div className="flex gap-1 justify-center">
                                {/* Pulsante Visualizza PDF */}
                                {ordine?.pdf_file && (
                                  <button
                                    onClick={() => setShowPdfModal(true)}
                                    className="px-2 py-1 text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 rounded"
                                    title="Visualizza PDF originale"
                                  >
                                    🔍
                                  </button>
                                )}
                                {isEditing ? (
                                  <>
                                    <button
                                      onClick={() => handleSalvaModificaRiga(riga)}
                                      className="px-2 py-1 text-xs bg-green-500 hover:bg-green-600 text-white rounded"
                                      title="Salva"
                                    >
                                      💾
                                    </button>
                                    <button
                                      onClick={() => setRigaInModifica(null)}
                                      className="px-2 py-1 text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 rounded"
                                      title="Annulla"
                                    >
                                      ✕
                                    </button>
                                  </>
                                ) : (
                                  <>
                                    {/* Riga ARCHIVIATA: solo ripristino */}
                                    {riga.stato_riga === 'ARCHIVIATO' && (
                                      <button
                                        onClick={() => handleRipristinaArchiviata(riga)}
                                        className="px-2 py-1 text-xs bg-blue-100 hover:bg-blue-200 text-blue-700 rounded"
                                        title="Ripristina riga archiviata"
                                      >
                                        🔓 Ripristina
                                      </button>
                                    )}

                                    {/* Riga completamente evasa: nessuna azione possibile */}
                                    {riga.stato_riga === 'EVASO' && (
                                      <span className="text-xs text-green-600 font-medium">Completato</span>
                                    )}

                                    {/* Righe attive (non EVASO, non ARCHIVIATO): mostra azioni */}
                                    {riga.stato_riga !== 'ARCHIVIATO' && riga.stato_riga !== 'EVASO' && (
                                      <>
                                        {/* Riga con residuo > 0: modifica e conferma */}
                                        {qResidua > 0 && (
                                          <>
                                            <button
                                              onClick={() => handleApriModificaRiga(riga)}
                                              className="px-2 py-1 text-xs bg-blue-100 hover:bg-blue-200 text-blue-700 rounded"
                                              title="Modifica quantità da evadere"
                                            >
                                              ✏️
                                            </button>
                                            {riga.stato_riga !== 'CONFERMATO' && (
                                              <button
                                                onClick={() => handleConfermaRigaCompleta(riga)}
                                                className="px-2 py-1 text-xs bg-green-100 hover:bg-green-200 text-green-700 rounded"
                                                title="Conferma tutto il residuo"
                                              >
                                                ✓
                                              </button>
                                            )}
                                            {riga.stato_riga === 'CONFERMATO' && (
                                              <button
                                                onClick={() => handleRipristinaRiga(riga)}
                                                className="px-2 py-1 text-xs bg-amber-100 hover:bg-amber-200 text-amber-700 rounded"
                                                title="Annulla conferma (ripristina)"
                                              >
                                                ↩
                                              </button>
                                            )}
                                          </>
                                        )}
                                        {/* Riga senza residuo ma non evasa: stato PARZIALE con residuo 0 */}
                                        {qResidua <= 0 && (
                                          <span className="text-xs text-slate-500">Residuo esaurito</span>
                                        )}
                                        {/* Archivia sempre disponibile per righe non EVASO/ARCHIVIATO */}
                                        <button
                                          onClick={() => handleArchiviaRiga(riga)}
                                          className="px-2 py-1 text-xs bg-slate-200 hover:bg-slate-300 text-slate-700 rounded"
                                          title="Archivia riga (freeze)"
                                        >
                                          🔒
                                        </button>
                                      </>
                                    )}
                                  </>
                                )}
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>

                  {/* Leggenda simboli */}
                  <div className="mt-4 p-3 bg-slate-50 rounded-lg border border-slate-200">
                    <h4 className="text-sm font-semibold text-slate-700 mb-2">Legenda simboli</h4>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs text-slate-600">
                      <div className="flex items-center gap-1">
                        <span>🔍</span> <span>Visualizza PDF</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <span>🎁</span> <span>Espositore</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <span>✏️</span> <span>Modifica quantità</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <span>✓</span> <span>Conferma riga</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <span>↩</span> <span>Annulla conferma</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <span>🔒</span> <span>Archivia (freeze)</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <span>🔓</span> <span>Ripristina archiviata</span>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* v6.2.1: Pulsanti Valida, Conferma e Ripristina in fondo */}
              {righe.length > 0 && (
                <div className="mt-4 flex justify-between border-t border-slate-200 pt-4">
                  <button
                    onClick={handleValidaOrdine}
                    disabled={righe.length === 0}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-300 disabled:cursor-not-allowed text-white rounded-lg text-sm font-medium"
                    title="Genera tracciato con le quantità 'Da Evadere' impostate"
                  >
                    📤 Genera Tracciato
                  </button>
                  <div className="flex gap-2">
                    <button
                      onClick={handleConfermaTutto}
                      disabled={righe.length === 0 || righe.every(r => {
                        const qTot = (r.q_venduta || 0) + (r.q_sconto_merce || 0) + (r.q_omaggio || 0);
                        return qTot - (r.q_evasa || 0) <= 0;
                      })}
                      className="px-4 py-2 bg-green-500 hover:bg-green-600 disabled:bg-slate-300 disabled:cursor-not-allowed text-white rounded-lg text-sm font-medium"
                      title="Imposta 'Da Evadere' = Residuo per tutte le righe"
                    >
                      ✓ Conferma Tutto
                    </button>
                    <button
                      onClick={handleRipristinaTutto}
                      disabled={righe.length === 0 || !righe.some(r => r.stato_riga === 'CONFERMATO' || (r.q_da_evadere || 0) > 0)}
                      className="px-4 py-2 bg-orange-500 hover:bg-orange-600 disabled:bg-slate-300 disabled:cursor-not-allowed text-white rounded-lg text-sm font-medium"
                      title="Annulla conferma per tutte le righe"
                    >
                      ↩ Ripristina Tutto
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Tab: Anomalie */}
          {activeTab === 'anomalie' && (
            <div className="space-y-4">
              {/* Supervisioni Espositore */}
              {supervisioni.length > 0 && (
                <div className="mb-6">
                  <h3 className="text-sm font-semibold text-purple-700 mb-3 flex items-center gap-2">
                    📦 Supervisione Espositori ({supervisioni.filter(s => s.stato === 'PENDING').length} pending)
                  </h3>
                  <div className="space-y-3">
                    {supervisioni.map((sup) => (
                      <div key={sup.id_supervisione} className={`p-4 rounded-lg border ${sup.stato === 'PENDING' ? 'bg-purple-50 border-purple-200' : 'bg-slate-50 border-slate-200'}`}>
                        <div className="flex items-start justify-between gap-4">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-2">
                              <span className="text-lg">🎁</span>
                              <span className="font-semibold text-slate-800">{sup.descrizione_espositore}</span>
                              <span className="text-xs font-mono text-slate-500">({sup.codice_espositore})</span>
                            </div>

                            <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm mb-2">
                              <div className="text-slate-600">
                                Pezzi attesi: <span className="font-bold">{sup.pezzi_attesi}</span>
                              </div>
                              <div className="text-slate-600">
                                Pezzi trovati: <span className={`font-bold ${sup.pezzi_trovati === sup.pezzi_attesi ? 'text-green-600' : 'text-orange-600'}`}>{sup.pezzi_trovati}</span>
                              </div>
                              <div className="text-slate-600">
                                Valore: <span className="font-bold">€ {sup.valore_calcolato?.toFixed(2) || '0.00'}</span>
                              </div>
                              <div className="text-slate-600">
                                Tipo: <span className="font-bold">{sup.codice_anomalia}</span>
                              </div>
                            </div>

                            <div className="text-xs text-slate-500">
                              Pattern: <span className="font-mono">{sup.pattern_signature}</span>
                              {sup.count_approvazioni !== null && (
                                <span className="ml-2">({sup.count_approvazioni}/5 conferme)</span>
                              )}
                            </div>
                          </div>

                          <div className="flex flex-col gap-1">
                            <span className={`px-2 py-1 rounded text-xs font-medium ${
                              sup.stato === 'PENDING' ? 'bg-yellow-100 text-yellow-800' :
                              sup.stato === 'APPROVATO' ? 'bg-green-100 text-green-800' :
                              sup.stato === 'RIFIUTATO' ? 'bg-red-100 text-red-800' :
                              'bg-slate-100 text-slate-600'
                            }`}>
                              {sup.stato}
                            </span>

                            {sup.stato === 'PENDING' && (
                              <div className="flex flex-col gap-1 mt-2">
                                <button
                                  onClick={() => handleApprovaSuper(sup.id_supervisione)}
                                  className="px-3 py-1 text-xs bg-green-100 text-green-700 rounded hover:bg-green-200"
                                >
                                  ✓ Conferma
                                </button>
                                <button
                                  onClick={() => handleRifiutaSuper(sup.id_supervisione)}
                                  className="px-3 py-1 text-xs bg-red-100 text-red-700 rounded hover:bg-red-200"
                                >
                                  ✕ Rifiuta
                                </button>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {anomalie.length === 0 ? (
                <div className="text-center py-8 text-green-600">
                  <span className="text-4xl">OK</span>
                  <p className="mt-2">Nessuna anomalia rilevata</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {anomalie.map((anomalia) => (
                    <div
                      key={anomalia.id_anomalia || anomalia.id}
                      className={`p-4 rounded-lg border cursor-pointer hover:shadow-md transition-shadow ${getLivelloColor(anomalia.livello)}`}
                      onClick={() => loadAnomaliaDetail(anomalia.id_anomalia || anomalia.id)}
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                              anomalia.livello === 'critico' ? 'bg-red-200' :
                              anomalia.livello === 'alto' ? 'bg-orange-200' :
                              anomalia.livello === 'medio' ? 'bg-yellow-200' : 'bg-blue-200'
                            }`}>
                              {anomalia.livello?.toUpperCase()}
                            </span>
                            <span className="text-sm font-medium text-slate-700">
                              {anomalia.tipo || anomalia.tipo_anomalia}
                            </span>
                          </div>
                          <p className="text-sm text-slate-600">{anomalia.messaggio || anomalia.descrizione}</p>
                          {anomalia.campo && (
                            <p className="text-xs text-slate-500 mt-1">
                              Campo: <span className="font-mono">{anomalia.campo}</span>
                            </p>
                          )}
                        </div>
                        <div className="flex items-center gap-2">
                          <span className={`px-2 py-1 rounded text-xs font-medium ${
                            anomalia.stato === 'risolta' || anomalia.stato === 'RISOLTA' ? 'bg-green-100 text-green-800' :
                            anomalia.stato === 'ignorata' ? 'bg-slate-100 text-slate-600' :
                            'bg-red-100 text-red-800'
                          }`}>
                            {anomalia.stato}
                          </span>
                          {(anomalia.stato === 'aperta' || anomalia.stato === 'APERTA') && (
                            <Button
                              size="sm"
                              variant="secondary"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleRisolviAnomalia(anomalia.id_anomalia || anomalia.id);
                              }}
                            >
                              Risolvi
                            </Button>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Riepilogo azioni */}
      <div className="bg-slate-50 rounded-xl border border-slate-200 p-4">
        <div className="flex items-center justify-between">
          <div className="text-sm text-slate-600">
            <span className="font-medium">Ultimo aggiornamento:</span> {ordine.data_modifica || ordine.data_creazione || '-'}
          </div>
          <div className="flex gap-2">
            <Button variant="secondary" onClick={loadOrdine}>
              Ricarica
            </Button>
          </div>
        </div>
      </div>


      {/* Modal Modifica Riga */}
      {rigaInModifica && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between p-4 border-b bg-blue-50">
              <h3 className="text-lg font-semibold">✏️ Modifica Riga #{rigaInModifica.n_riga}</h3>
              <button
                onClick={() => setRigaInModifica(null)}
                className="px-3 py-1 bg-slate-100 text-slate-700 rounded hover:bg-slate-200 text-sm"
              >
                ✕
              </button>
            </div>
            <div className="p-4 space-y-4">
              {/* Codice AIC e Descrizione */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Codice AIC</label>
                  <input
                    type="text"
                    value={formModifica.codice_aic}
                    onChange={(e) => setFormModifica(f => ({ ...f, codice_aic: e.target.value }))}
                    className="w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Descrizione</label>
                  <input
                    type="text"
                    value={formModifica.descrizione}
                    onChange={(e) => setFormModifica(f => ({ ...f, descrizione: e.target.value }))}
                    className="w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
              </div>
              
              {/* Quantità - v6.2.1: Separazione Evaso (cumulativo) e Da Evadere (editabile) */}
              <div className="grid grid-cols-4 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Q.tà Ordinata</label>
                  <input
                    type="number"
                    min="0"
                    value={formModifica.q_venduta}
                    onChange={(e) => setFormModifica(f => ({ ...f, q_venduta: parseInt(e.target.value) || 0 }))}
                    className="w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Sc. Merce</label>
                  <input
                    type="number"
                    min="0"
                    value={formModifica.q_sconto_merce}
                    onChange={(e) => setFormModifica(f => ({ ...f, q_sconto_merce: parseInt(e.target.value) || 0 }))}
                    className="w-full px-3 py-2 border border-amber-300 rounded-md focus:ring-2 focus:ring-amber-500 focus:border-amber-500 bg-amber-50"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Omaggio</label>
                  <input
                    type="number"
                    min="0"
                    value={formModifica.q_omaggio}
                    onChange={(e) => setFormModifica(f => ({ ...f, q_omaggio: parseInt(e.target.value) || 0 }))}
                    className="w-full px-3 py-2 border border-green-300 rounded-md focus:ring-2 focus:ring-green-500 focus:border-green-500 bg-green-50"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-blue-700 mb-1">Da Evadere *</label>
                  <input
                    type="number"
                    min="0"
                    value={formModifica.q_da_evadere}
                    onChange={(e) => setFormModifica(f => ({ ...f, q_da_evadere: parseInt(e.target.value) || 0 }))}
                    onFocus={(e) => e.target.select()}
                    className="w-full px-3 py-2 border border-blue-400 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-blue-50 font-medium"
                  />
                  <p className="text-xs text-blue-600 mt-1">Quantità per il prossimo tracciato</p>
                </div>
              </div>

              {/* Info Evaso e Residuo (read-only) */}
              {rigaInModifica && (
                <div className="bg-slate-50 rounded-md p-3 border border-slate-200">
                  <div className="grid grid-cols-3 gap-4 text-sm">
                    <div>
                      <span className="text-slate-500">Totale ordinato:</span>
                      <span className="ml-2 font-medium">
                        {(rigaInModifica.q_venduta || 0) + (rigaInModifica.q_sconto_merce || 0) + (rigaInModifica.q_omaggio || 0)}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-500">Già evaso:</span>
                      <span className="ml-2 font-medium text-green-600">{rigaInModifica.q_evasa || 0}</span>
                    </div>
                    <div>
                      <span className="text-slate-500">Residuo disponibile:</span>
                      <span className="ml-2 font-medium text-orange-600">
                        {((rigaInModifica.q_venduta || 0) + (rigaInModifica.q_sconto_merce || 0) + (rigaInModifica.q_omaggio || 0)) - (rigaInModifica.q_evasa || 0)}
                      </span>
                    </div>
                  </div>
                </div>
              )}
              
              {/* Prezzi */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Prezzo Netto (€)</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={formModifica.prezzo_netto}
                    onChange={(e) => setFormModifica(f => ({ ...f, prezzo_netto: parseFloat(e.target.value) || 0 }))}
                    className="w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Prezzo Pubblico (€)</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={formModifica.prezzo_pubblico}
                    onChange={(e) => setFormModifica(f => ({ ...f, prezzo_pubblico: parseFloat(e.target.value) || 0 }))}
                    className="w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
              </div>
              
              {/* Sconti */}
              <div className="grid grid-cols-4 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Sconto 1 (%)</label>
                  <input
                    type="number"
                    step="0.1"
                    min="0"
                    max="100"
                    value={formModifica.sconto_1}
                    onChange={(e) => setFormModifica(f => ({ ...f, sconto_1: parseFloat(e.target.value) || 0 }))}
                    className="w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Sconto 2 (%)</label>
                  <input
                    type="number"
                    step="0.1"
                    min="0"
                    max="100"
                    value={formModifica.sconto_2}
                    onChange={(e) => setFormModifica(f => ({ ...f, sconto_2: parseFloat(e.target.value) || 0 }))}
                    className="w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Sconto 3 (%)</label>
                  <input
                    type="number"
                    step="0.1"
                    min="0"
                    max="100"
                    value={formModifica.sconto_3}
                    onChange={(e) => setFormModifica(f => ({ ...f, sconto_3: parseFloat(e.target.value) || 0 }))}
                    className="w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Sconto 4 (%)</label>
                  <input
                    type="number"
                    step="0.1"
                    min="0"
                    max="100"
                    value={formModifica.sconto_4}
                    onChange={(e) => setFormModifica(f => ({ ...f, sconto_4: parseFloat(e.target.value) || 0 }))}
                    className="w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
              </div>
              
              {/* Note */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Note Allestimento</label>
                <textarea
                  value={formModifica.note_allestimento}
                  onChange={(e) => setFormModifica(f => ({ ...f, note_allestimento: e.target.value }))}
                  rows={2}
                  className="w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Note per allestimento..."
                />
              </div>
            </div>
            
            {/* Footer con pulsanti */}
            <div className="flex justify-end gap-3 p-4 border-t bg-slate-50">
              <button
                onClick={() => setRigaInModifica(null)}
                className="px-4 py-2 bg-slate-100 text-slate-700 rounded-md hover:bg-slate-200 font-medium"
              >
                ❌ Annulla
              </button>
              <button
                onClick={() => handleSalvaModificaRiga(rigaInModifica)}
                className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 font-medium"
              >
                💾 Salva Modifiche
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal PDF */}
      {showPdfModal && ordine?.pdf_file && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg w-full max-w-5xl h-[90vh] flex flex-col">
            <div className="flex items-center justify-between p-4 border-b">
              <h3 className="text-lg font-semibold">📄 {ordine.pdf_file}</h3>
              <div className="flex gap-2">
                <a
                  href={`/api/v1/upload/pdf/${encodeURIComponent(ordine.pdf_file)}`}
                  download
                  className="px-3 py-1 bg-blue-100 text-blue-700 rounded hover:bg-blue-200 text-sm"
                >
                  ⬇️ Scarica
                </a>
                <button
                  onClick={() => setShowPdfModal(false)}
                  className="px-3 py-1 bg-slate-100 text-slate-700 rounded hover:bg-slate-200 text-sm"
                >
                  ✕ Chiudi
                </button>
              </div>
            </div>
            <div className="flex-1 p-2">
              <iframe
                src={`/api/v1/upload/pdf/${encodeURIComponent(ordine.pdf_file)}`}
                className="w-full h-full rounded border"
                title="PDF Ordine"
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
        onAssignFarmacia={handleAssignFarmacia}
      />
    </div>
  );
}
