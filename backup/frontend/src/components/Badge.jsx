/**
 * Badge Components - v6.2 Refactoring
 * Componenti badge riutilizzabili per stati, tipi, severità
 */
import React from 'react';

// Color mapping per stati ordine
const ORDINE_STATO_COLORS = {
  'ESTRATTO': 'bg-slate-100 text-slate-700',
  'CONFERMATO': 'bg-green-100 text-green-700',
  'ANOMALIA': 'bg-red-100 text-red-700',
  'PARZ_EVASO': 'bg-amber-100 text-amber-700',
  'EVASO': 'bg-emerald-100 text-emerald-700',
  'ARCHIVIATO': 'bg-purple-100 text-purple-700',
  'IN_TRACCIATO': 'bg-blue-100 text-blue-700',
  'SUPERVISIONATO': 'bg-cyan-100 text-cyan-700',
};

// Color mapping per stati anomalia
const ANOMALIA_STATO_COLORS = {
  'APERTA': 'bg-amber-100 text-amber-700',
  'IN_GESTIONE': 'bg-blue-100 text-blue-700',
  'RISOLTA': 'bg-green-100 text-green-700',
  'IGNORATA': 'bg-slate-100 text-slate-700',
};

// Color mapping per tipi anomalia
const ANOMALIA_TIPO_COLORS = {
  'ESPOSITORE': 'bg-purple-100 text-purple-700',
  'NO_AIC': 'bg-orange-100 text-orange-700',
  'LOOKUP': 'bg-cyan-100 text-cyan-700',
  'CHILD': 'bg-indigo-100 text-indigo-700',
  'PIVA_MULTIPUNTO': 'bg-pink-100 text-pink-700',
  'VALIDAZIONE': 'bg-amber-100 text-amber-700',
  'DUPLICATO_PDF': 'bg-red-100 text-red-700',
  'DUPLICATO_ORDINE': 'bg-red-100 text-red-700',
  'ALTRO': 'bg-slate-100 text-slate-700',
};

// Color mapping per severità/livello
const SEVERITA_COLORS = {
  'INFO': 'bg-blue-100 text-blue-700',
  'ATTENZIONE': 'bg-amber-100 text-amber-700',
  'ERRORE': 'bg-red-100 text-red-700',
  'CRITICO': 'bg-red-200 text-red-800',
  'WARNING': 'bg-amber-100 text-amber-700',
};

// Badge generico
export function Badge({ children, color = 'slate', className = '' }) {
  const colorClass = `bg-${color}-100 text-${color}-700`;
  return (
    <span className={`px-2 py-1 rounded text-xs font-medium ${colorClass} ${className}`}>
      {children}
    </span>
  );
}

// Badge per stato ordine
export function StatoOrdineBadge({ stato }) {
  const colorClass = ORDINE_STATO_COLORS[stato] || 'bg-slate-100 text-slate-700';
  return (
    <span className={`px-2 py-1 rounded text-xs font-medium ${colorClass}`}>
      {stato || 'N/D'}
    </span>
  );
}

// Badge per stato anomalia
export function StatoAnomaliaBadge({ stato }) {
  const colorClass = ANOMALIA_STATO_COLORS[stato] || 'bg-slate-100 text-slate-700';
  return (
    <span className={`px-2 py-1 rounded text-xs font-medium ${colorClass}`}>
      {stato || 'N/D'}
    </span>
  );
}

// Badge per tipo anomalia
export function TipoAnomaliaBadge({ tipo }) {
  const colorClass = ANOMALIA_TIPO_COLORS[tipo] || 'bg-slate-100 text-slate-700';
  return (
    <span className={`px-2 py-1 rounded text-xs font-medium ${colorClass}`}>
      {tipo || 'N/D'}
    </span>
  );
}

// Badge per severità
export function SeveritaBadge({ severita }) {
  const colorClass = SEVERITA_COLORS[severita] || 'bg-slate-100 text-slate-700';
  return (
    <span className={`px-2 py-1 rounded text-xs font-medium ${colorClass}`}>
      {severita || 'N/D'}
    </span>
  );
}

// Badge per booleano (Si/No)
export function BooleanBadge({ value, trueText = 'Si', falseText = 'No' }) {
  const colorClass = value ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-700';
  return (
    <span className={`px-2 py-1 rounded text-xs font-medium ${colorClass}`}>
      {value ? trueText : falseText}
    </span>
  );
}

// Export color mappings per uso esterno
export const colorMappings = {
  ordineStato: ORDINE_STATO_COLORS,
  anomaliaStato: ANOMALIA_STATO_COLORS,
  anomaliaTipo: ANOMALIA_TIPO_COLORS,
  severita: SEVERITA_COLORS,
};

export default Badge;
