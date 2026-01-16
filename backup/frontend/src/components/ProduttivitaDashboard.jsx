/**
 * Dashboard Produttività Team
 * Visualizza le card produttività per tutti gli operatori visibili
 */
import { useState, useEffect, useCallback } from 'react';
import { produttivitaApi } from '../api';
import ProduttivitaCard from './ProduttivitaCard';
import ProduttivitaModal from './ProduttivitaModal';

const AUTO_REFRESH_INTERVAL = 30000; // 30 secondi

export function ProduttivitaDashboard() {
  const [vista, setVista] = useState('oggi'); // 'oggi' o 'ieri'
  const [operatori, setOperatori] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);

  // Modal state
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedOperatore, setSelectedOperatore] = useState(null);

  // Carica dati
  const loadData = useCallback(async () => {
    try {
      setError(null);
      let data;

      if (vista === 'oggi') {
        data = await produttivitaApi.getSessione();
      } else {
        const ieri = new Date();
        ieri.setDate(ieri.getDate() - 1);
        data = await produttivitaApi.getGiorno(ieri.toISOString().split('T')[0]);
      }

      setOperatori(data.operatori || []);
      setLastUpdate(new Date());
    } catch (err) {
      console.error('Errore caricamento produttività:', err);
      setError('Errore nel caricamento dei dati');
    } finally {
      setLoading(false);
    }
  }, [vista]);

  // Caricamento iniziale e su cambio vista
  useEffect(() => {
    setLoading(true);
    loadData();
  }, [loadData]);

  // Auto-refresh ogni 30 secondi (solo per vista 'oggi')
  useEffect(() => {
    if (vista !== 'oggi') return;

    const interval = setInterval(() => {
      loadData();
    }, AUTO_REFRESH_INTERVAL);

    return () => clearInterval(interval);
  }, [vista, loadData]);

  // Apri modal dettagli
  const handleDettagli = (operatore) => {
    setSelectedOperatore(operatore);
    setModalOpen(true);
  };

  // Chiudi modal
  const handleCloseModal = () => {
    setModalOpen(false);
    setSelectedOperatore(null);
  };

  // Formatta ultimo aggiornamento
  const formatLastUpdate = () => {
    if (!lastUpdate) return '';
    return lastUpdate.toLocaleTimeString('it-IT', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  return (
    <div>
      {/* Header con controlli */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
        <div className="flex items-center gap-3">
          <h2 className="text-xl font-semibold text-slate-800">
            Produttività Team
          </h2>
          {lastUpdate && (
            <span className="text-sm text-slate-500">
              Aggiornato alle {formatLastUpdate()}
            </span>
          )}
        </div>

        <div className="flex items-center gap-3">
          {/* Toggle vista */}
          <div className="flex bg-slate-100 rounded-lg p-1">
            <button
              onClick={() => setVista('oggi')}
              className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
                vista === 'oggi'
                  ? 'bg-white text-slate-800 shadow-sm'
                  : 'text-slate-600 hover:text-slate-800'
              }`}
            >
              Oggi
            </button>
            <button
              onClick={() => setVista('ieri')}
              className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
                vista === 'ieri'
                  ? 'bg-white text-slate-800 shadow-sm'
                  : 'text-slate-600 hover:text-slate-800'
              }`}
            >
              Ieri
            </button>
          </div>

          {/* Pulsante refresh manuale */}
          <button
            onClick={loadData}
            disabled={loading}
            className="p-2 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors disabled:opacity-50"
            title="Aggiorna"
          >
            <svg
              className={`w-5 h-5 text-slate-600 ${loading ? 'animate-spin' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
          </button>
        </div>
      </div>

      {/* Errore */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6">
          {error}
        </div>
      )}

      {/* Loading */}
      {loading && operatori.length === 0 ? (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
          <span className="ml-3 text-slate-600">Caricamento...</span>
        </div>
      ) : operatori.length === 0 ? (
        <div className="bg-slate-50 rounded-lg p-8 text-center text-slate-500">
          Nessun operatore trovato
        </div>
      ) : (
        /* Grid operatori */
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {operatori.map((op) => (
            <ProduttivitaCard
              key={op.id_operatore}
              operatore={op}
              onDettagli={handleDettagli}
            />
          ))}
        </div>
      )}

      {/* Modal dettagli */}
      <ProduttivitaModal
        isOpen={modalOpen}
        onClose={handleCloseModal}
        operatore={selectedOperatore}
        dataRiferimento={vista === 'oggi' ? new Date().toISOString().split('T')[0] : null}
      />
    </div>
  );
}

export default ProduttivitaDashboard;
