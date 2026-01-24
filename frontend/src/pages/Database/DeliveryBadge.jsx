// =============================================================================
// SERV.O v7.0 - DELIVERY BADGE COMPONENT
// =============================================================================

import React from 'react';
import { getUrgenza, parseDataConsegna } from './utils';

export default function DeliveryBadge({ dataConsegna, dataOrdine }) {
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
}
