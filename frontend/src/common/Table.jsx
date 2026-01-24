// =============================================================================
// SERV.O v10.1 - TABLE COMPONENT
// =============================================================================
// Componente tabella riutilizzabile con sorting, loading, empty states
// =============================================================================

import React from 'react';
import Loading from './Loading';

/**
 * Table - Componente tabella riutilizzabile
 *
 * Features:
 * - Colonne configurabili con render custom
 * - Sorting integrato
 * - Loading state
 * - Empty state personalizzabile
 * - Row click handler
 * - Sticky header opzionale
 * - Striped rows opzionale
 *
 * @param {Array} columns - Configurazione colonne [{ key, label, render, sortable, width, align }]
 * @param {Array} data - Array di oggetti da visualizzare
 * @param {boolean} loading - Stato di caricamento
 * @param {string} emptyMessage - Messaggio quando data è vuoto
 * @param {string} emptyIcon - Emoji/icona per empty state
 * @param {function} onRowClick - Handler click su riga (riceve item)
 * @param {string} rowKey - Chiave unica per ogni riga (default: 'id')
 * @param {object} sorting - { key, direction } per sorting attivo
 * @param {function} onSort - Handler per cambio sorting
 * @param {boolean} striped - Righe alternate
 * @param {boolean} hoverable - Highlight on hover
 * @param {boolean} compact - Padding ridotto
 * @param {boolean} stickyHeader - Header fisso
 * @param {string} className - Classi CSS aggiuntive
 */
const Table = ({
  columns = [],
  data = [],
  loading = false,
  emptyMessage = 'Nessun dato disponibile',
  emptyIcon = '📭',
  onRowClick,
  rowKey = 'id',
  sorting,
  onSort,
  striped = false,
  hoverable = true,
  compact = false,
  stickyHeader = false,
  className = '',
}) => {
  // Handle sort click
  const handleSort = (column) => {
    if (!column.sortable || !onSort) return;

    const newDirection =
      sorting?.key === column.key && sorting?.direction === 'asc'
        ? 'desc'
        : 'asc';

    onSort({ key: column.key, direction: newDirection });
  };

  // Get sort icon
  const getSortIcon = (column) => {
    if (!column.sortable) return null;

    if (sorting?.key === column.key) {
      return sorting.direction === 'asc' ? '↑' : '↓';
    }
    return '↕';
  };

  // Cell padding based on compact mode
  const cellPadding = compact ? 'px-3 py-2' : 'px-4 py-3';
  const headerPadding = compact ? 'px-3 py-2' : 'px-4 py-3';

  // Alignment classes
  const alignClasses = {
    left: 'text-left',
    center: 'text-center',
    right: 'text-right',
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg border border-slate-200 p-8">
        <Loading text="Caricamento dati..." />
      </div>
    );
  }

  return (
    <div className={`bg-white rounded-lg border border-slate-200 overflow-hidden ${className}`}>
      <div className="overflow-x-auto">
        <table className="w-full">
          {/* Header */}
          <thead className={`bg-slate-50 border-b border-slate-200 ${stickyHeader ? 'sticky top-0 z-10' : ''}`}>
            <tr>
              {columns.map((column) => (
                <th
                  key={column.key}
                  className={`
                    ${headerPadding}
                    ${alignClasses[column.align || 'left']}
                    text-xs font-semibold text-slate-600 uppercase tracking-wider
                    ${column.sortable ? 'cursor-pointer hover:bg-slate-100 select-none' : ''}
                  `}
                  style={column.width ? { width: column.width } : {}}
                  onClick={() => handleSort(column)}
                >
                  <span className="flex items-center gap-1">
                    {column.label}
                    {column.sortable && (
                      <span className={`text-xs ${sorting?.key === column.key ? 'text-blue-600' : 'text-slate-400'}`}>
                        {getSortIcon(column)}
                      </span>
                    )}
                  </span>
                </th>
              ))}
            </tr>
          </thead>

          {/* Body */}
          <tbody className="divide-y divide-slate-100">
            {data.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="px-4 py-12 text-center">
                  <div className="text-4xl mb-3">{emptyIcon}</div>
                  <p className="text-slate-500">{emptyMessage}</p>
                </td>
              </tr>
            ) : (
              data.map((item, index) => (
                <tr
                  key={item[rowKey] || index}
                  className={`
                    ${striped && index % 2 === 1 ? 'bg-slate-50' : 'bg-white'}
                    ${hoverable ? 'hover:bg-blue-50 transition-colors' : ''}
                    ${onRowClick ? 'cursor-pointer' : ''}
                  `}
                  onClick={() => onRowClick?.(item)}
                >
                  {columns.map((column) => (
                    <td
                      key={column.key}
                      className={`${cellPadding} ${alignClasses[column.align || 'left']} text-sm text-slate-700`}
                    >
                      {column.render
                        ? column.render(item[column.key], item, index)
                        : item[column.key] ?? '-'}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

/**
 * TableCell - Celle specializzate per casi comuni
 */
export const TableCell = {
  // Cella con badge
  Badge: ({ children, variant = 'default' }) => {
    const variants = {
      default: 'bg-slate-100 text-slate-700',
      primary: 'bg-blue-100 text-blue-700',
      success: 'bg-emerald-100 text-emerald-700',
      warning: 'bg-amber-100 text-amber-700',
      danger: 'bg-red-100 text-red-700',
    };
    return (
      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${variants[variant]}`}>
        {children}
      </span>
    );
  },

  // Cella con icona e testo
  WithIcon: ({ icon, children }) => (
    <span className="flex items-center gap-2">
      <span>{icon}</span>
      <span>{children}</span>
    </span>
  ),

  // Cella monospace (per codici)
  Code: ({ children }) => (
    <code className="bg-slate-100 px-1.5 py-0.5 rounded text-xs font-mono">
      {children}
    </code>
  ),

  // Cella con troncamento
  Truncate: ({ children, maxWidth = '200px' }) => (
    <span
      className="block truncate"
      style={{ maxWidth }}
      title={children}
    >
      {children}
    </span>
  ),

  // Cella numerica con formattazione
  Number: ({ value, decimals = 2, prefix = '', suffix = '' }) => (
    <span className="font-mono tabular-nums">
      {prefix}{typeof value === 'number' ? value.toFixed(decimals) : value}{suffix}
    </span>
  ),

  // Cella data
  Date: ({ value, format = 'short' }) => {
    if (!value) return '-';
    const date = new Date(value);
    const options = format === 'short'
      ? { day: '2-digit', month: '2-digit', year: 'numeric' }
      : { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' };
    return <span>{date.toLocaleDateString('it-IT', options)}</span>;
  },

  // Cella azioni
  Actions: ({ children }) => (
    <div className="flex items-center gap-1 justify-end" onClick={(e) => e.stopPropagation()}>
      {children}
    </div>
  ),
};

export { Table };
export default Table;
