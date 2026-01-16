/**
 * Card produttività singolo operatore
 * Mostra timer, contatori, indicatore online/offline e pulsante dettagli
 */
import { useState, useEffect } from 'react';

const CounterItem = ({ label, value, icon }) => (
  <div className="flex justify-between items-center py-1">
    <span className="text-slate-500 text-sm">{icon} {label}</span>
    <span className="font-semibold text-slate-700">{value}</span>
  </div>
);

// Indicatore stato online/offline
const OnlineIndicator = ({ isOnline }) => (
  <div className="flex items-center gap-1.5">
    <div
      className={`w-2.5 h-2.5 rounded-full ${
        isOnline
          ? 'bg-emerald-500 animate-pulse'
          : 'bg-slate-300'
      }`}
    />
    <span className={`text-xs ${isOnline ? 'text-emerald-600' : 'text-slate-400'}`}>
      {isOnline ? 'Online' : 'Offline'}
    </span>
  </div>
);

export function ProduttivitaCard({ operatore, onDettagli }) {
  const [displayTime, setDisplayTime] = useState(operatore.tempo_formattato || '00:00:00');
  const isOnline = operatore.is_online || false;

  // Timer che incrementa ogni secondo (SOLO per operatori online)
  useEffect(() => {
    // Non incrementare il timer se l'operatore è offline
    if (!isOnline) {
      setDisplayTime(operatore.tempo_formattato || '00:00:00');
      return;
    }

    let seconds = operatore.tempo_totale_secondi || 0;

    const interval = setInterval(() => {
      seconds += 1;
      const h = Math.floor(seconds / 3600);
      const m = Math.floor((seconds % 3600) / 60);
      const s = seconds % 60;
      setDisplayTime(`${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`);
    }, 1000);

    return () => clearInterval(interval);
  }, [operatore.tempo_totale_secondi, isOnline]);

  // Reset display time quando cambiano i dati
  useEffect(() => {
    setDisplayTime(operatore.tempo_formattato || '00:00:00');
  }, [operatore.tempo_formattato]);

  const nomeCompleto = [operatore.nome, operatore.cognome].filter(Boolean).join(' ') || operatore.username;
  const iniziale = (operatore.nome || operatore.username || '?')[0].toUpperCase();

  const ruoloBadgeColor = operatore.ruolo === 'supervisore'
    ? 'bg-purple-100 text-purple-700'
    : 'bg-blue-100 text-blue-700';

  // Bordo colorato in base allo stato online
  const cardBorderColor = isOnline
    ? 'border-emerald-300 ring-1 ring-emerald-100'
    : 'border-slate-200';

  return (
    <div className={`bg-white rounded-xl shadow-sm border ${cardBorderColor} p-4 hover:shadow-md transition-shadow`}>
      {/* Header con avatar, nome e indicatore online */}
      <div className="flex items-center gap-3 mb-4">
        <div className="relative">
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white font-semibold">
            {iniziale}
          </div>
          {/* Pallino online/offline sull'avatar */}
          <div
            className={`absolute -bottom-0.5 -right-0.5 w-3.5 h-3.5 rounded-full border-2 border-white ${
              isOnline ? 'bg-emerald-500' : 'bg-slate-300'
            }`}
          />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-slate-800 truncate">{nomeCompleto}</h3>
            <OnlineIndicator isOnline={isOnline} />
          </div>
          <span className={`text-xs px-2 py-0.5 rounded-full ${ruoloBadgeColor}`}>
            {operatore.ruolo}
          </span>
        </div>
      </div>

      {/* Timer */}
      <div className="bg-slate-50 rounded-lg p-3 mb-4 text-center">
        <div className="text-xs text-slate-500 mb-1">Tempo sessione</div>
        <div className="text-2xl font-mono font-bold text-slate-800">
          {displayTime}
        </div>
      </div>

      {/* Contatori */}
      <div className="space-y-1 mb-4">
        <CounterItem icon="📦" label="Ordini validati" value={operatore.ordini_validati || 0} />
        <CounterItem icon="✏️" label="Righe modificate" value={operatore.righe_modificate || 0} />
        <CounterItem icon="🔍" label="Anomalie verificate" value={operatore.anomalie_verificate || 0} />
        <CounterItem icon="✓" label="Righe confermate" value={operatore.righe_confermate || 0} />
        <CounterItem icon="📄" label="Tracciati esportati" value={operatore.tracciati_generati || 0} />
      </div>

      {/* Pulsante dettagli */}
      <button
        onClick={() => onDettagli(operatore)}
        className="w-full py-2 px-4 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-sm font-medium transition-colors"
      >
        Dettagli
      </button>
    </div>
  );
}

export default ProduttivitaCard;
