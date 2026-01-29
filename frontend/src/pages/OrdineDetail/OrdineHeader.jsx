// =============================================================================
// SERV.O v7.0 - ORDINE HEADER COMPONENT
// =============================================================================

import React from 'react';
import { Button } from '../../common';
import { getStatoColor } from './utils';

// Formatta data in formato italiano DD/MM/YYYY
function formatDataItaliana(dataStr) {
  if (!dataStr) return '-';

  // Se già in formato italiano (DD/MM/YYYY o DD-MM-YYYY), restituisci così com'è
  if (/^\d{2}[\/\-]\d{2}[\/\-]\d{4}$/.test(dataStr)) {
    return dataStr.replace(/-/g, '/');
  }

  // Prova a parsare come data
  try {
    const date = new Date(dataStr);
    if (!isNaN(date.getTime())) {
      const day = String(date.getDate()).padStart(2, '0');
      const month = String(date.getMonth() + 1).padStart(2, '0');
      const year = date.getFullYear();
      return `${day}/${month}/${year}`;
    }
  } catch {
    // Fallback
  }

  return dataStr;
}

export default function OrdineHeader({ ordine, onBack, onShowPdf, onEditHeader, returnToSupervisione }) {
  if (!ordine) return null;

  // Verifica se l'ordine è modificabile
  const isEditable = !['EVASO', 'ARCHIVIATO'].includes(ordine.stato);

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-4">
          <h2 className="text-xl font-bold text-slate-800">
            Ordine #{ordine?.numero_ordine_vendor || ordine?.numero_ordine || ordine?.id_testata || '-'}
          </h2>
          <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatoColor(ordine.stato)}`}>
            {ordine.stato?.toUpperCase()}
          </span>
          {ordine.lookup_method === 'MANUALE' && (
            <span className="px-2 py-0.5 bg-purple-100 text-purple-700 text-xs rounded-full font-medium">
              Modificato manualmente
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {isEditable && onEditHeader && (
            <button
              onClick={onEditHeader}
              className="px-3 py-2 border border-slate-300 text-slate-700 rounded-lg hover:bg-slate-50 flex items-center gap-2 text-sm"
              title="Modifica dati farmacia"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
              </svg>
              Modifica Header
            </button>
          )}
          <Button variant="secondary" onClick={onBack}>
            {returnToSupervisione ? 'Torna a Supervisione ML' : 'Torna al Database'}
          </Button>
          {ordine?.pdf_file && (
            <button
              onClick={onShowPdf}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
            >
              📄 Visualizza PDF
            </button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm mb-3">
        <div>
          <span className="text-slate-500">Vendor:</span>
          <span className="ml-2 font-medium">{ordine?.vendor || '-'}</span>
        </div>
        <div>
          <span className="text-slate-500">Data:</span>
          <span className="ml-2 font-medium">{formatDataItaliana(ordine?.data_ordine)}</span>
        </div>
        <div>
          <span className="text-slate-500">Cliente:</span>
          <span className="ml-2 font-medium">{ordine?.ragione_sociale?.toUpperCase() || '-'}</span>
        </div>
        <div>
          <span className="text-slate-500">Deposito:</span>
          <span className={`ml-2 font-medium ${ordine?.deposito ? 'text-purple-700' : 'text-slate-400'}`}>
            {ordine?.deposito || '-'}
          </span>
        </div>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
        <div>
          <span className="text-slate-500">Citta:</span>
          <span className="ml-2 font-medium">
            {ordine?.citta && ordine?.provincia ? `${ordine.citta.toUpperCase()} (${ordine.provincia.toUpperCase()})` : '-'}
          </span>
        </div>
        <div>
          <span className="text-slate-500">MIN_ID:</span>
          <span className="ml-2 font-medium font-mono">{ordine?.min_id || '-'}</span>
        </div>
        <div>
          <span className="text-slate-500">P.IVA:</span>
          <span className="ml-2 font-medium font-mono">{ordine?.partita_iva || '-'}</span>
        </div>
        <div>
          <span className="text-slate-500">Totale Netto:</span>
          <span className="ml-2 font-bold text-green-700">
            {ordine?.valore_totale_netto != null
              ? `€ ${Number(ordine.valore_totale_netto).toLocaleString('it-IT', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
              : '-'}
          </span>
        </div>
      </div>
    </div>
  );
}
