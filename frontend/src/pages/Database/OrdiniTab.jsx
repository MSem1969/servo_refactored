// =============================================================================
// SERV.O v7.0 - ORDINI TAB COMPONENT
// =============================================================================

import React, { useState, useMemo } from 'react';
import { Button, StatusBadge, VendorBadge, Loading } from '../../common';
import DeliveryBadge from './DeliveryBadge';
import { getRowHighlightClass } from './utils';

// Componente per intestazione colonna ordinabile
function SortableHeader({ label, field, sortField, sortDirection, onSort }) {
  const isActive = sortField === field;
  return (
    <th
      className="text-center align-middle p-2 text-xs font-medium text-slate-600 cursor-pointer hover:bg-slate-100 select-none"
      onClick={() => onSort(field)}
    >
      <div className="flex items-center justify-center gap-1">
        {label}
        <span className={`text-xs ${isActive ? 'text-blue-600' : 'text-slate-300'}`}>
          {isActive ? (sortDirection === 'asc' ? '▲' : '▼') : '⇅'}
        </span>
      </div>
    </th>
  );
}

export default function OrdiniTab({
  ordini,
  loading,
  selected,
  selectedOrdine,
  onToggleSelect,
  onSelectAll,
  onOpenOrdine,
  onShowPdf,
  onArchiviaOrdine,
  onClearFilters,
  onRegistraEvasione,
  viewedOrders = new Set()  // v11.3: Set di ID ordini già visualizzati
}) {
  // Stato ordinamento
  const [sortField, setSortField] = useState(null);
  const [sortDirection, setSortDirection] = useState('asc');

  // Gestione click su intestazione
  const handleSort = (field) => {
    if (sortField === field) {
      // Stesso campo: inverti direzione
      setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      // Nuovo campo: imposta ascendente
      setSortField(field);
      setSortDirection('asc');
    }
  };

  // Helper: converti data DD/MM/YYYY in timestamp per confronto
  const parseDate = (dateStr) => {
    if (!dateStr) return 0;
    // Formato: DD/MM/YYYY
    const parts = String(dateStr).split('/');
    if (parts.length !== 3) return 0;
    const [day, month, year] = parts.map(Number);
    return new Date(year, month - 1, day).getTime() || 0;
  };

  // Ordini ordinati
  const sortedOrdini = useMemo(() => {
    if (!sortField) return ordini;

    return [...ordini].sort((a, b) => {
      let valA = a[sortField];
      let valB = b[sortField];

      // Gestione null/undefined
      if (valA == null) valA = '';
      if (valB == null) valB = '';

      // Confronto numerico per campi numerici
      if (['righe_totali', 'num_righe', 'righe_confermate'].includes(sortField)) {
        valA = Number(valA) || 0;
        valB = Number(valB) || 0;
      }
      // Confronto date YYYY-MM-DD (data_evasione dal backend)
      else if (sortField === 'data_evasione') {
        valA = valA ? new Date(valA).getTime() : 0;
        valB = valB ? new Date(valB).getTime() : 0;
      }
      // Confronto date per campi data (formato DD/MM/YYYY)
      else if (['data_consegna', 'data_ordine', 'data_estrazione'].includes(sortField)) {
        valA = parseDate(valA);
        valB = parseDate(valB);
      }
      else {
        // Confronto stringa case-insensitive
        valA = String(valA).toLowerCase();
        valB = String(valB).toLowerCase();
      }

      if (valA < valB) return sortDirection === 'asc' ? -1 : 1;
      if (valA > valB) return sortDirection === 'asc' ? 1 : -1;
      return 0;
    });
  }, [ordini, sortField, sortDirection]);

  if (loading) {
    return (
      <div className="p-8">
        <Loading text="Caricamento ordini..." />
      </div>
    );
  }

  if (ordini.length === 0) {
    return (
      <div className="p-8 text-center text-slate-500">
        <div className="text-4xl mb-2">📦</div>
        <p>Nessun ordine trovato</p>
        <Button variant="secondary" size="sm" className="mt-3" onClick={onClearFilters}>
          Pulisci Filtri
        </Button>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead className="bg-slate-50 border-b border-slate-200">
          <tr>
            <th className="w-8 p-2 text-center align-middle">
              <input
                type="checkbox"
                checked={selected.length === ordini.length && ordini.length > 0}
                onChange={onSelectAll}
                className="rounded border-slate-300"
              />
            </th>
            <SortableHeader label="Vendor" field="vendor" sortField={sortField} sortDirection={sortDirection} onSort={handleSort} />
            <SortableHeader label="N. Ordine" field="numero_ordine" sortField={sortField} sortDirection={sortDirection} onSort={handleSort} />
            <SortableHeader label="Consegna" field="data_consegna" sortField={sortField} sortDirection={sortDirection} onSort={handleSort} />
            <SortableHeader label="Deposito" field="deposito" sortField={sortField} sortDirection={sortDirection} onSort={handleSort} />
            <SortableHeader label="Farmacia" field="ragione_sociale" sortField={sortField} sortDirection={sortDirection} onSort={handleSort} />
            <SortableHeader label="Citta" field="citta" sortField={sortField} sortDirection={sortDirection} onSort={handleSort} />
            <SortableHeader label="Righe" field="righe_totali" sortField={sortField} sortDirection={sortDirection} onSort={handleSort} />
            <SortableHeader label="Confermate" field="righe_confermate" sortField={sortField} sortDirection={sortDirection} onSort={handleSort} />
            <SortableHeader label="Stato" field="stato" sortField={sortField} sortDirection={sortDirection} onSort={handleSort} />
            <SortableHeader label="Evasione" field="data_evasione" sortField={sortField} sortDirection={sortDirection} onSort={handleSort} />
            <th className="text-center align-middle p-2 text-xs font-medium text-slate-600">Azioni</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {sortedOrdini.map((ordine) => {
            const isSelected = selected.includes(ordine.id_testata);
            const rowHighlight = getRowHighlightClass(ordine.data_consegna, ordine.data_ordine);
            const isViewed = viewedOrders.has(ordine.id_testata);

            return (
              <tr
                key={`${ordine.id_testata}_${ordine.numero_progressivo || 0}`}
                className={`hover:bg-slate-50 cursor-pointer ${rowHighlight} ${
                  selectedOrdine?.id_testata === ordine.id_testata ? 'bg-blue-50' : ''
                } ${!isViewed ? 'border-l-4 border-l-blue-500 bg-blue-50/30' : 'border-l-4 border-l-transparent'}`}
                onClick={() => onOpenOrdine(ordine.id_testata)}
              >
                <td className="p-2 text-center align-middle" onClick={(e) => e.stopPropagation()}>
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={() => onToggleSelect(ordine.id_testata)}
                    className="rounded border-slate-300"
                  />
                </td>
                <td className="p-2 text-center align-middle">
                  <VendorBadge vendor={ordine.vendor} size="xs" />
                </td>
                <td className="p-2 text-center align-middle font-mono text-xs font-medium">
                  {ordine.numero_ordine_display || ordine.numero_ordine || ordine.numero_ordine_vendor || '-'}
                </td>
                <td className="p-2 text-center align-middle">
                  <DeliveryBadge dataConsegna={ordine.data_consegna} dataOrdine={ordine.data_ordine} />
                </td>
                <td className="p-2 text-center align-middle text-xs font-medium text-purple-700">
                  {ordine.deposito || '-'}
                </td>
                <td className="p-2 text-center align-middle truncate max-w-[200px] text-xs">
                  {ordine.ragione_sociale?.toUpperCase() || '-'}
                </td>
                <td className="p-2 text-center align-middle text-xs text-slate-500">
                  {ordine.citta?.toUpperCase() || '-'}
                </td>
                <td className="p-2 text-center align-middle text-xs">
                  {ordine.righe_totali || ordine.num_righe || '-'}
                </td>
                <td className="p-2 text-center align-middle">
                  {ordine.righe_confermate !== undefined && (ordine.righe_totali || ordine.num_righe) > 0 ? (
                    <span className={`text-xs font-mono ${
                      ordine.righe_confermate === (ordine.righe_totali || ordine.num_righe)
                        ? 'text-emerald-600'
                        : ordine.righe_confermate > 0
                        ? 'text-amber-600'
                        : 'text-slate-400'
                    }`}>
                      {ordine.righe_confermate}/{ordine.righe_totali || ordine.num_righe}
                    </span>
                  ) : (
                    <span className="text-slate-400 text-xs">-</span>
                  )}
                </td>
                <td className="p-2 text-center align-middle">
                  <StatusBadge status={ordine.stato} size="xs" />
                </td>
                <td className="p-2 text-center align-middle" onClick={(e) => e.stopPropagation()}>
                  {ordine.data_evasione ? (
                    <button
                      onClick={() => onRegistraEvasione?.(ordine)}
                      className="text-xs text-emerald-600 font-medium hover:underline"
                      title={ordine.numero_bolla ? `Bolla: ${ordine.numero_bolla}` : 'Modifica evasione'}
                    >
                      {new Date(ordine.data_evasione).toLocaleDateString('it-IT')}
                      {ordine.numero_bolla && <span className="ml-1 text-slate-400">({ordine.numero_bolla})</span>}
                    </button>
                  ) : ordine.id_esportazione_dettaglio ? (
                    <button
                      onClick={() => onRegistraEvasione?.(ordine)}
                      className="px-2 py-0.5 text-xs bg-blue-50 text-blue-600 rounded hover:bg-blue-100 font-medium"
                    >
                      Registra
                    </button>
                  ) : (
                    <span className="text-slate-300 text-xs">-</span>
                  )}
                </td>
                <td className="p-2 text-center align-middle" onClick={(e) => e.stopPropagation()}>
                  {ordine.pdf_file && (
                    <button
                      onClick={() => onShowPdf(ordine.pdf_file)}
                      className="px-2 py-1 text-xs bg-slate-100 text-slate-700 rounded hover:bg-slate-200"
                      title="Visualizza PDF"
                    >
                      📄
                    </button>
                  )}

                  <button
                    onClick={() => onOpenOrdine(ordine.id_testata)}
                    className="ml-1 px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded hover:bg-blue-200"
                    title="Apri dettaglio"
                  >
                    🔍 Dettaglio
                  </button>

                  <button
                    onClick={() => onArchiviaOrdine(ordine)}
                    className="ml-1 px-2 py-1 text-xs bg-orange-100 text-orange-700 rounded hover:bg-orange-200"
                    title="Archivia ordine"
                  >
                    🔒 Archivia
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
