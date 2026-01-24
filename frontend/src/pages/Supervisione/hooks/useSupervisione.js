// =============================================================================
// SERV.O v8.1 - USE SUPERVISIONE HOOK
// =============================================================================
// Custom hook per gestione stato e logica pagina supervisione ML
// =============================================================================

import { useState, useCallback } from 'react';
import { supervisioneApi } from '../../../api';
import { richiestaConfermaSemplice, richiestaInput, richiestaConferma } from '../../../utils/confirmazione';

/**
 * Custom hook per gestione supervisione ML
 *
 * @param {Object} options
 * @param {Object} options.currentUser - Utente corrente
 * @param {number} options.returnToOrdine - ID ordine per ritorno
 * @param {Function} options.onReturnToOrdine - Callback ritorno ordine
 */
export function useSupervisione({ currentUser, returnToOrdine, onReturnToOrdine }) {
  // State principale
  const [supervisioni, setSupervisioni] = useState([]);
  const [groupedSupervisioni, setGroupedSupervisioni] = useState([]);
  const [criteri, setCriteri] = useState([]);
  const [storico, setStorico] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('pending');
  const [viewMode, setViewMode] = useState('grouped');

  // State per processing
  const [processingAction, setProcessingAction] = useState(null);
  const [processingPattern, setProcessingPattern] = useState(null);

  // State per modali
  const [correzioneModal, setCorrezioneModal] = useState({ isOpen: false, supervisione: null });
  const [archiviazioneModal, setArchiviazioneModal] = useState({ isOpen: false, supervisione: null });
  const [aicModal, setAicModal] = useState({ isOpen: false, supervisione: null }); // v9.0

  const operatore = currentUser?.username || 'admin';

  // Carica dati supervisione
  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [pendingRes, groupedRes, criteriRes, statsRes, storicoRes] = await Promise.all([
        supervisioneApi.getPending(),
        supervisioneApi.getPendingGrouped(),
        supervisioneApi.getCriteriTutti(),
        supervisioneApi.getCriteriStats(),
        supervisioneApi.getStorico(50),
      ]);

      setSupervisioni(pendingRes?.supervisioni || []);
      setGroupedSupervisioni(groupedRes?.groups || []);
      setCriteri(criteriRes?.criteri || []);
      setStorico(storicoRes?.applicazioni || []);
      setStats(statsRes || {
        totale_pattern: 0,
        pattern_ordinari: 0,
        approvazioni_totali: 0,
        pending: 0
      });
    } catch (err) {
      console.error('Errore caricamento supervisione:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  // Action handlers
  const handleApprova = async (id, patternSignature) => {
    if (!richiestaConfermaSemplice('Confermi approvazione? Questo contribuirà all\'apprendimento ML.')) return;

    setProcessingAction(id);
    try {
      if (returnToOrdine && onReturnToOrdine) {
        await supervisioneApi.approvaETorna(id, operatore);
        onReturnToOrdine(returnToOrdine);
      } else {
        await supervisioneApi.approva(id, operatore);
        loadData();
      }
    } catch (err) {
      alert('Errore: ' + (err.response?.data?.detail || err.message));
    } finally {
      setProcessingAction(null);
    }
  };

  const handleRifiuta = async (id, patternSignature) => {
    const note = richiestaInput(
      'Motivo del rifiuto (obbligatorio):\n\n' +
      'ATTENZIONE: Un rifiuto resetterà l\'apprendimento ML per questo pattern.',
      { required: true, minLength: 5 }
    );
    if (!note) {
      alert('Motivo non valido. Minimo 5 caratteri.');
      return;
    }

    setProcessingAction(id);
    try {
      await supervisioneApi.rifiuta(id, operatore, note);

      if (returnToOrdine && onReturnToOrdine) {
        onReturnToOrdine(returnToOrdine);
      } else {
        loadData();
      }
    } catch (err) {
      alert('Errore: ' + (err.response?.data?.detail || err.message));
    } finally {
      setProcessingAction(null);
    }
  };

  const handleModifica = async (id, modifiche) => {
    setProcessingAction(id);
    try {
      await supervisioneApi.modifica(id, operatore, modifiche);
      loadData();
    } catch (err) {
      alert('Errore: ' + (err.response?.data?.detail || err.message));
    } finally {
      setProcessingAction(null);
    }
  };

  // Bulk operations
  const handleApprovaBulk = async (patternSignature, totalCount) => {
    if (!richiestaConfermaSemplice(
      `Confermi approvazione di ${totalCount} supervisioni con questo pattern?\n\n` +
      `Questo contribuirà all'apprendimento ML (+1 approvazione per il pattern).`
    )) return;

    setProcessingPattern(patternSignature);
    try {
      const result = await supervisioneApi.approvaBulk(patternSignature, operatore);
      alert(
        `Approvate ${result.approvate?.total || 0} supervisioni:\n` +
        `- Espositore: ${result.approvate?.espositore || 0}\n` +
        `- Listino: ${result.approvate?.listino || 0}\n` +
        `- Lookup: ${result.approvate?.lookup || 0}\n\n` +
        `Ordini sbloccati: ${result.approvate?.orders_affected?.length || 0}`
      );
      loadData();
    } catch (err) {
      alert('Errore: ' + (err.response?.data?.detail || err.message));
    } finally {
      setProcessingPattern(null);
    }
  };

  const handleRifiutaBulk = async (patternSignature, totalCount) => {
    const note = richiestaInput(
      `Stai per rifiutare ${totalCount} supervisioni.\n\n` +
      `ATTENZIONE: Questo resetterà l'apprendimento ML per questo pattern.\n\n` +
      `Inserisci il motivo del rifiuto (obbligatorio):`,
      { required: true, minLength: 5 }
    );
    if (!note) {
      alert('Motivo non valido. Minimo 5 caratteri.');
      return;
    }

    setProcessingPattern(patternSignature);
    try {
      const result = await supervisioneApi.rifiutaBulk(patternSignature, operatore, note);
      alert(
        `Rifiutate ${result.rifiutate?.total || 0} supervisioni:\n` +
        `- Espositore: ${result.rifiutate?.espositore || 0}\n` +
        `- Listino: ${result.rifiutate?.listino || 0}\n` +
        `- Lookup: ${result.rifiutate?.lookup || 0}`
      );
      loadData();
    } catch (err) {
      alert('Errore: ' + (err.response?.data?.detail || err.message));
    } finally {
      setProcessingPattern(null);
    }
  };

  // Sospendi operazione
  const handleLasciaSospeso = async (id) => {
    if (returnToOrdine && onReturnToOrdine) {
      try {
        await supervisioneApi.lasciaSospeso(id, operatore);
        onReturnToOrdine(returnToOrdine);
      } catch (err) {
        alert('Errore: ' + (err.response?.data?.detail || err.message));
      }
    }
  };

  // Pattern ML operations
  const handleResetPattern = async (signature) => {
    if (!richiestaConferma(
      'Reset pattern ML',
      'Vuoi azzerare il contatore approvazioni per questo pattern?\n' +
      'L\'apprendimento ripartirà da zero e il pattern non sarà più automatico.'
    )) return;

    try {
      await supervisioneApi.resetPattern(signature, operatore);
      loadData();
    } catch (err) {
      alert('Errore reset: ' + err.message);
    }
  };

  const handlePromuoviPattern = async (signature) => {
    if (!richiestaConfermaSemplice(
      'PROMUOVI PATTERN\n\n' +
      'Vuoi rendere questo pattern automatico?\n\n' +
      'Le future anomalie con questo pattern verranno gestite automaticamente.'
    )) return;

    try {
      await supervisioneApi.promuoviPattern(signature, operatore);
      loadData();
    } catch (err) {
      alert('Errore promozione: ' + err.message);
    }
  };

  // Modal handlers
  const handleOpenCorrezione = (supervisione) => {
    setCorrezioneModal({ isOpen: true, supervisione });
  };

  const handleCloseCorrezione = () => {
    setCorrezioneModal({ isOpen: false, supervisione: null });
  };

  const handleOpenArchiviazione = (supervisione) => {
    setArchiviazioneModal({ isOpen: true, supervisione });
  };

  const handleCloseArchiviazione = () => {
    setArchiviazioneModal({ isOpen: false, supervisione: null });
  };

  // v9.0: Handler modale AIC
  const handleOpenAic = (supervisione) => {
    setAicModal({ isOpen: true, supervisione });
  };

  const handleCloseAic = () => {
    setAicModal({ isOpen: false, supervisione: null });
  };

  const handleAicSuccess = (result) => {
    if (result?.message) {
      alert(result.message);
    }
    loadData();
    if (returnToOrdine && onReturnToOrdine) {
      onReturnToOrdine(returnToOrdine);
    }
  };

  // v9.0: Rifiuta AIC specifico
  const handleRifiutaAic = async (id) => {
    const note = richiestaInput(
      'Motivo del rifiuto (obbligatorio):\n\n' +
      'ATTENZIONE: Un rifiuto resetterà l\'apprendimento ML per questo pattern.',
      { required: true, minLength: 5 }
    );
    if (!note) {
      alert('Motivo non valido. Minimo 5 caratteri.');
      return;
    }

    setProcessingAction(id);
    try {
      await supervisioneApi.rifiutaAic(id, operatore, note);

      if (returnToOrdine && onReturnToOrdine) {
        onReturnToOrdine(returnToOrdine);
      } else {
        loadData();
      }
    } catch (err) {
      alert('Errore: ' + (err.response?.data?.detail || err.message));
    } finally {
      setProcessingAction(null);
    }
  };

  const handleListinoSuccess = () => {
    loadData();
    if (returnToOrdine && onReturnToOrdine) {
      onReturnToOrdine(returnToOrdine);
    }
  };

  // Riapplica listino a tutte le supervisioni prezzo pending (PRICE-A01)
  const handleRiapplicaListino = async () => {
    if (!richiestaConfermaSemplice(
      'RIAPPLICA LISTINO (PRICE-A01)\n\n' +
      'Vuoi applicare i prezzi dal listino a tutte le supervisioni PRICE-A01 pending?\n\n' +
      'Le supervisioni con tutte le righe risolte verranno auto-approvate.'
    )) return;

    try {
      const result = await supervisioneApi.riapplicaListinoBulk(operatore);
      alert(
        `Listino riapplicato!\n\n` +
        `Supervisioni processate: ${result.supervisioni_processate}\n` +
        `Auto-approvate: ${result.auto_approvate}\n` +
        `Ancora pending: ${result.ancora_pending}\n` +
        `Righe aggiornate: ${result.righe_aggiornate_totali}`
      );
      loadData();
    } catch (err) {
      alert('Errore: ' + (err.response?.data?.detail || err.message));
    }
  };

  // v10.0: Riapplica listino a tutte le supervisioni listino pending (LST-A01)
  const handleRiapplicaListinoLst = async () => {
    if (!richiestaConfermaSemplice(
      'RIAPPLICA LISTINO (LST-A01)\n\n' +
      'Vuoi applicare i prezzi dal listino a tutte le supervisioni LST-A01 pending?\n\n' +
      'Include DOC_GENERICI e altri vendor senza prezzi nel PDF.\n' +
      'Le supervisioni con AIC trovato nel listino verranno auto-approvate.'
    )) return;

    try {
      const result = await supervisioneApi.riapplicaListinoLstBulk(operatore);
      alert(
        `Listino riapplicato!\n\n` +
        `Supervisioni processate: ${result.supervisioni_processate}\n` +
        `Auto-approvate: ${result.auto_approvate}\n` +
        `Ancora pending: ${result.ancora_pending}`
      );
      loadData();
    } catch (err) {
      alert('Errore: ' + (err.response?.data?.detail || err.message));
    }
  };

  // Utility functions
  const getMLProgress = (approvazioni) => {
    const soglia = 5;
    return Math.min((approvazioni / soglia) * 100, 100);
  };

  const getAnomaliaUrgency = (anomalia) => {
    if (anomalia.livello === 'CRITICO') return 'high';
    if (anomalia.tipo_scostamento === 'ECCESSO' && anomalia.percentuale_scostamento > 50) return 'high';
    if (anomalia.tipo_scostamento === 'DIFETTO' && anomalia.percentuale_scostamento < -30) return 'medium';
    return 'low';
  };

  // Computed values
  // Nota: supervisioni sono già filtrate per PENDING dal backend,
  // non serve filtrare nuovamente (evita problemi se il campo stato non è sempre presente)
  const pendingCount = supervisioni.length;

  const tabs = [
    {
      id: 'pending',
      label: 'Da Supervisionare',
      count: pendingCount,
      icon: '⏳',
      description: 'Anomalie che richiedono decisione manuale'
    },
    {
      id: 'patterns',
      label: 'Pattern ML',
      count: criteri.length,
      icon: '🧠',
      description: 'Pattern appresi dal sistema'
    },
    {
      id: 'storico',
      label: 'Storico',
      count: storico.length,
      icon: '📜',
      description: 'Decisioni precedenti (audit trail)'
    },
    {
      id: 'stats',
      label: 'Analytics',
      count: stats?.approvazioni_totali || 0,
      icon: '📊',
      description: 'Statistiche e metriche ML'
    }
  ];

  return {
    // State
    supervisioni,
    groupedSupervisioni,
    criteri,
    storico,
    stats,
    loading,
    activeTab,
    setActiveTab,
    viewMode,
    setViewMode,
    processingAction,
    processingPattern,
    operatore,
    tabs,
    pendingCount,

    // Modal state
    correzioneModal,
    archiviazioneModal,
    aicModal, // v9.0

    // Actions
    loadData,
    handleApprova,
    handleRifiuta,
    handleModifica,
    handleApprovaBulk,
    handleRifiutaBulk,
    handleLasciaSospeso,
    handleResetPattern,
    handlePromuoviPattern,

    // Modal actions
    handleOpenCorrezione,
    handleCloseCorrezione,
    handleOpenArchiviazione,
    handleCloseArchiviazione,
    handleOpenAic,       // v9.0
    handleCloseAic,      // v9.0
    handleAicSuccess,    // v9.0
    handleRifiutaAic,    // v9.0
    handleListinoSuccess,

    // Bulk actions
    handleRiapplicaListino,
    handleRiapplicaListinoLst,  // v10.0

    // Utilities
    getMLProgress,
    getAnomaliaUrgency,
  };
}

export default useSupervisione;
