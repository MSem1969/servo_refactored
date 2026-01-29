// =============================================================================
// SERV.O v11.4 - USE SUPERVISIONE HOOK
// =============================================================================
// Custom hook per gestione stato e logica pagina supervisione ML
// v11.4: Aggiunto supporto anagrafica modal e nuovo workflow bottoni
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
 * @param {Object} options.initialContext - v11.4: Contesto da ripristinare (tab, viewMode)
 */
export function useSupervisione({ currentUser, returnToOrdine, onReturnToOrdine, initialContext }) {
  // State principale
  const [supervisioni, setSupervisioni] = useState([]);
  const [groupedSupervisioni, setGroupedSupervisioni] = useState([]);
  const [criteri, setCriteri] = useState([]);
  // const [storico, setStorico] = useState([]); // v11.4: Rimosso - tab non utilizzato
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  // v11.4: Ripristina contesto se presente (ritorno da altra pagina)
  const [activeTab, setActiveTab] = useState(initialContext?.activeTab || 'pending');
  const [viewMode, setViewMode] = useState(initialContext?.viewMode || 'grouped');

  // State per processing
  const [processingAction, setProcessingAction] = useState(null);
  const [processingPattern, setProcessingPattern] = useState(null);

  // State per modali
  const [correzioneModal, setCorrezioneModal] = useState({ isOpen: false, supervisione: null });
  const [archiviazioneModal, setArchiviazioneModal] = useState({ isOpen: false, supervisione: null });
  const [aicModal, setAicModal] = useState({ isOpen: false, supervisione: null }); // v9.0
  // v11.4: anagraficaModal ora usa AnomaliaDetailModal (unificato operatore/supervisore)
  const [anagraficaModal, setAnagraficaModal] = useState({
    isOpen: false,
    supervisione: null,
    anomaliaDetail: null,
    loading: false
  });

  const operatore = currentUser?.username || 'admin';

  // Carica dati supervisione
  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      // v11.4: Rimosso getStorico - tab non utilizzato
      const [pendingRes, groupedRes, criteriRes, statsRes] = await Promise.all([
        supervisioneApi.getPending(),
        supervisioneApi.getPendingGrouped(),
        supervisioneApi.getCriteriTutti(),
        supervisioneApi.getCriteriStats(),
      ]);

      setSupervisioni(pendingRes?.supervisioni || []);
      setGroupedSupervisioni(groupedRes?.groups || []);
      setCriteri(criteriRes?.criteri || []);
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

  // v11.4: Cancella pattern completamente
  const handleDeletePattern = async (signature) => {
    if (!richiestaConferma(
      'Cancella pattern ML',
      'ATTENZIONE: Questa azione cancellerà definitivamente il pattern.\n\n' +
      'A differenza del RESET (che azzera il contatore), la cancellazione\n' +
      'rimuove completamente il pattern dal sistema.\n\n' +
      'Il pattern dovrà essere riappreso da zero. Continuare?'
    )) return;

    try {
      await supervisioneApi.deletePattern(signature, operatore);
      loadData();
    } catch (err) {
      alert('Errore cancellazione: ' + err.message);
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

  // v11.4: Handler modale Anagrafica (usa AnomaliaDetailModal unificato)
  // Carica dettaglio anomalia e apre il modal
  const handleOpenAnagrafica = async (supervisione) => {
    // Apre modal in loading
    setAnagraficaModal({
      isOpen: true,
      supervisione,
      anomaliaDetail: null,
      loading: true
    });

    try {
      // Carica dettaglio anomalia usando id_anomalia dalla supervisione
      const idAnomalia = supervisione?.id_anomalia;
      if (idAnomalia) {
        const { anomalieApi } = await import('../../../api/anomalie');
        const result = await anomalieApi.getDettaglio(idAnomalia);
        if (result.success) {
          // Assicurati che pdf_file sia presente
          let anomaliaDetail = result.data;
          if (!anomaliaDetail?.anomalia?.pdf_file && !anomaliaDetail?.ordine_data?.pdf_file) {
            // Carica pdf_file dalla testata
            try {
              const { ordiniApi } = await import('../../../api');
              const idTestata = anomaliaDetail?.anomalia?.id_testata || supervisione?.id_testata;
              if (idTestata) {
                const ordineRes = await ordiniApi.getOrdine(idTestata);
                if (ordineRes?.pdf_file) {
                  anomaliaDetail = {
                    ...anomaliaDetail,
                    anomalia: { ...anomaliaDetail.anomalia, pdf_file: ordineRes.pdf_file },
                    ordine_data: { ...anomaliaDetail.ordine_data, pdf_file: ordineRes.pdf_file }
                  };
                }
              }
            } catch (e) {
              console.warn('Impossibile caricare pdf_file:', e);
            }
          }
          setAnagraficaModal(prev => ({
            ...prev,
            anomaliaDetail,
            loading: false
          }));
        } else {
          console.error('Errore caricamento dettaglio anomalia:', result.error);
          setAnagraficaModal(prev => ({ ...prev, loading: false }));
        }
      } else {
        // Se non c'è id_anomalia, costruisci un anomaliaDetail minimo dai dati ordine
        // Carica anche il pdf_file dalla testata se disponibile
        let pdfFile = supervisione?.pdf_file;
        if (!pdfFile && supervisione?.id_testata) {
          try {
            const { ordiniApi } = await import('../../../api');
            const ordineRes = await ordiniApi.getOrdine(supervisione.id_testata);
            pdfFile = ordineRes?.pdf_file;
          } catch (e) {
            console.warn('Impossibile caricare pdf_file:', e);
          }
        }

        setAnagraficaModal(prev => ({
          ...prev,
          anomaliaDetail: {
            anomalia: {
              id_anomalia: null,
              id_testata: supervisione?.id_testata,
              tipo_anomalia: 'LOOKUP',
              codice_anomalia: supervisione?.codice_anomalia,
              stato: 'APERTA',
              numero_ordine: supervisione?.numero_ordine,
              vendor: supervisione?.vendor,
              pdf_file: pdfFile
            },
            ordine_data: {
              partita_iva: supervisione?.piva_estratta,
              ragione_sociale: supervisione?.ragione_sociale_estratta || supervisione?.ragione_sociale,
              indirizzo: supervisione?.indirizzo_estratto,
              cap: supervisione?.cap_estratto,
              citta: supervisione?.citta_estratta,
              provincia: supervisione?.provincia_estratta,
              pdf_file: pdfFile
            }
          },
          loading: false
        }));
      }
    } catch (err) {
      console.error('Errore caricamento dettaglio:', err);
      setAnagraficaModal(prev => ({ ...prev, loading: false }));
    }
  };

  const handleCloseAnagrafica = () => {
    setAnagraficaModal({ isOpen: false, supervisione: null, anomaliaDetail: null, loading: false });
  };

  const handleAnagraficaSuccess = (result) => {
    if (result?.message) {
      alert(result.message);
    }
    loadData();
    if (returnToOrdine && onReturnToOrdine) {
      onReturnToOrdine(returnToOrdine);
    }
  };

  // v11.4: Rifiuta Anagrafica
  const handleRifiutaAnagrafica = async (id) => {
    const note = richiestaInput(
      'Motivo del rifiuto (obbligatorio):',
      { required: true, minLength: 5 }
    );
    if (!note) {
      alert('Motivo non valido. Minimo 5 caratteri.');
      return;
    }

    setProcessingAction(id);
    try {
      await supervisioneApi.rifiutaAnagrafica(id, operatore, note);

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

  // v11.4: Rimossi tab Storico e Analytics (senza funzione)
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
    }
  ];

  return {
    // State
    supervisioni,
    groupedSupervisioni,
    criteri,
    // storico, // v11.4: Rimosso - tab non utilizzato
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
    anagraficaModal, // v11.4

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
    handleDeletePattern, // v11.4

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
    handleOpenAnagrafica,    // v11.4
    handleCloseAnagrafica,   // v11.4
    handleAnagraficaSuccess, // v11.4
    handleRifiutaAnagrafica, // v11.4

    // Bulk actions
    handleRiapplicaListino,
    handleRiapplicaListinoLst,  // v10.0

    // Utilities
    getMLProgress,
    getAnomaliaUrgency,
  };
}

export default useSupervisione;
