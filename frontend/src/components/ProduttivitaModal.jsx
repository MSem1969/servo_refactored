/**
 * Modal dettagli produttività operatore
 * Mostra tempo per sezione + ultime 10 task
 */
import { useState, useEffect } from 'react';
import Modal from './Modal';
import { produttivitaApi } from '../api';

// Barra progresso per tempo sezione
const TempoSezioneBar = ({ sezione, durata_secondi, durata_formattata, maxSeconds }) => {
  const percentage = maxSeconds > 0 ? Math.min((durata_secondi / maxSeconds) * 100, 100) : 0;

  const sezioneLabels = {
    dashboard: 'Dashboard',
    ordini: 'Ordini',
    upload: 'Upload',
    supervisione: 'Supervisione',
    tracciati: 'Tracciati',
    database: 'Database',
    anomalie: 'Anomalie',
    utenti: 'Utenti',
  };

  return (
    <div className="flex items-center gap-3 py-2">
      <div className="w-28 text-sm text-slate-600 truncate">
        {sezioneLabels[sezione] || sezione}
      </div>
      <div className="flex-1 h-5 bg-slate-100 rounded-full overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-blue-500 to-indigo-500 rounded-full transition-all duration-300"
          style={{ width: `${percentage}%` }}
        />
      </div>
      <div className="w-20 text-sm text-slate-700 font-mono text-right">
        {durata_formattata}
      </div>
    </div>
  );
};

// Riga tabella task
const TaskRow = ({ task }) => {
  const tipoLabels = {
    'UPDATE_STATO': 'Aggiorna stato',
    'REGISTRA_EVASIONE': 'Conferma riga',
    'GENERA_TRACCIATI': 'Genera tracciato',
    'SUPERVISIONE_APPROVE': 'Approva supervisione',
    'SUPERVISIONE_REJECT': 'Rifiuta supervisione',
    'SUPERVISIONE_MODIFY': 'Modifica supervisione',
    'UPLOAD_PDF': 'Upload PDF',
    'LOGIN': 'Login',
    'LOGOUT': 'Logout',
    'VALIDA_TRACCIATO': 'Valida tracciato',
  };

  return (
    <tr className="border-b border-slate-100 hover:bg-slate-50">
      <td className="py-2 px-3 text-sm font-mono text-slate-500">{task.timestamp}</td>
      <td className="py-2 px-3">
        <span className="text-sm font-medium text-slate-700">
          {tipoLabels[task.tipo_operazione] || task.tipo_operazione}
        </span>
      </td>
      <td className="py-2 px-3 text-sm text-slate-600 truncate max-w-xs">
        {task.descrizione || '-'}
      </td>
    </tr>
  );
};

export function ProduttivitaModal({ isOpen, onClose, operatore, dataRiferimento }) {
  const [activeTab, setActiveTab] = useState('sessione');
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [datiIeri, setDatiIeri] = useState(null);

  const nomeCompleto = operatore
    ? [operatore.nome, operatore.cognome].filter(Boolean).join(' ') || operatore.username
    : '';

  // Carica ultime task
  useEffect(() => {
    if (isOpen && operatore) {
      setLoading(true);
      produttivitaApi.getUltimeTask(operatore.id_operatore, 10)
        .then(data => setTasks(data.tasks || []))
        .catch(err => console.error('Errore caricamento task:', err))
        .finally(() => setLoading(false));
    }
  }, [isOpen, operatore]);

  // Carica dati ieri quando si seleziona la tab
  useEffect(() => {
    if (activeTab === 'ieri' && !datiIeri && operatore) {
      const ieri = new Date();
      ieri.setDate(ieri.getDate() - 1);
      const ieriStr = ieri.toISOString().split('T')[0];

      produttivitaApi.getGiorno(ieriStr)
        .then(data => {
          const opIeri = data.operatori?.find(op => op.id_operatore === operatore.id_operatore);
          setDatiIeri(opIeri || null);
        })
        .catch(err => console.error('Errore caricamento dati ieri:', err));
    }
  }, [activeTab, datiIeri, operatore]);

  if (!operatore) return null;

  const datiCorrente = activeTab === 'sessione' ? operatore : (datiIeri || operatore);
  const tempoSezioni = datiCorrente.tempo_per_sezione || [];
  const maxSeconds = Math.max(...tempoSezioni.map(t => t.durata_secondi), 1);

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`${nomeCompleto} - Produttività`}
      size="lg"
      footer={
        <button
          onClick={onClose}
          className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-sm font-medium transition-colors"
        >
          Chiudi
        </button>
      }
    >
      {/* Tabs */}
      <div className="flex gap-2 mb-6">
        <button
          onClick={() => setActiveTab('sessione')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            activeTab === 'sessione'
              ? 'bg-blue-500 text-white'
              : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
          }`}
        >
          Sessione Corrente
        </button>
        <button
          onClick={() => setActiveTab('ieri')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            activeTab === 'ieri'
              ? 'bg-blue-500 text-white'
              : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
          }`}
        >
          Ieri
        </button>
      </div>

      {/* Contatori riepilogo */}
      <div className="grid grid-cols-5 gap-3 mb-6">
        {[
          { label: 'Ordini', value: datiCorrente.ordini_validati, icon: '📦' },
          { label: 'Righe mod.', value: datiCorrente.righe_modificate, icon: '✏️' },
          { label: 'Anomalie', value: datiCorrente.anomalie_verificate, icon: '🔍' },
          { label: 'Confermate', value: datiCorrente.righe_confermate, icon: '✓' },
          { label: 'Esportati', value: datiCorrente.tracciati_generati, icon: '📄' },
        ].map((item, i) => (
          <div key={i} className="bg-slate-50 rounded-lg p-3 text-center">
            <div className="text-2xl mb-1">{item.icon}</div>
            <div className="text-xl font-bold text-slate-800">{item.value || 0}</div>
            <div className="text-xs text-slate-500">{item.label}</div>
          </div>
        ))}
      </div>

      {/* Tempo per sezione */}
      <div className="mb-6">
        <h4 className="font-semibold text-slate-800 mb-3 flex items-center gap-2">
          <span>Tempo per sezione</span>
          <span className="text-sm font-normal text-slate-500">
            (Totale: {datiCorrente.tempo_formattato || '00:00:00'})
          </span>
        </h4>

        {tempoSezioni.length > 0 ? (
          <div className="bg-slate-50 rounded-lg p-4">
            {tempoSezioni.map((t, i) => (
              <TempoSezioneBar key={i} {...t} maxSeconds={maxSeconds} />
            ))}
          </div>
        ) : (
          <div className="bg-slate-50 rounded-lg p-4 text-center text-slate-500">
            Nessun dato disponibile
          </div>
        )}
      </div>

      {/* Ultime task */}
      <div>
        <h4 className="font-semibold text-slate-800 mb-3">
          Ultime 10 operazioni
        </h4>

        {loading ? (
          <div className="text-center py-8 text-slate-500">Caricamento...</div>
        ) : tasks.length > 0 ? (
          <div className="bg-slate-50 rounded-lg overflow-hidden">
            <table className="w-full">
              <thead className="bg-slate-100">
                <tr>
                  <th className="py-2 px-3 text-left text-xs font-semibold text-slate-600 uppercase">Ora</th>
                  <th className="py-2 px-3 text-left text-xs font-semibold text-slate-600 uppercase">Operazione</th>
                  <th className="py-2 px-3 text-left text-xs font-semibold text-slate-600 uppercase">Descrizione</th>
                </tr>
              </thead>
              <tbody>
                {tasks.map((task, i) => (
                  <TaskRow key={i} task={task} />
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="bg-slate-50 rounded-lg p-4 text-center text-slate-500">
            Nessuna operazione registrata
          </div>
        )}
      </div>
    </Modal>
  );
}

export default ProduttivitaModal;
