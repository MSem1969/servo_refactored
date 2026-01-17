// =============================================================================
// SERV.O v10.1 - FILTER BAR COMPONENT
// =============================================================================
// Barra filtri riutilizzabile per liste e tabelle
// =============================================================================

import React from 'react';
import Button from './Button';

/**
 * FilterBar - Barra filtri configurabile
 *
 * Features:
 * - Filtri configurabili (text, select, date, dateRange)
 * - Reset filtri
 * - Layout responsive
 * - Contatore risultati
 *
 * @param {Array} filters - Configurazione filtri [{ key, type, label, placeholder, options, value }]
 * @param {object} values - Valori correnti filtri { key: value }
 * @param {function} onChange - Handler cambio filtro (key, value)
 * @param {function} onReset - Handler reset filtri
 * @param {number} resultCount - Numero risultati (opzionale)
 * @param {string} resultLabel - Label risultati (default: 'risultati')
 * @param {boolean} compact - Layout compatto
 * @param {string} className - Classi CSS aggiuntive
 */
const FilterBar = ({
  filters = [],
  values = {},
  onChange,
  onReset,
  resultCount,
  resultLabel = 'risultati',
  compact = false,
  className = '',
  children,
}) => {
  // Check if any filter has value
  const hasActiveFilters = Object.values(values).some(
    (v) => v !== '' && v !== null && v !== undefined
  );

  // Render single filter
  const renderFilter = (filter) => {
    const value = values[filter.key] ?? '';
    const baseInputClass = `
      w-full px-3 py-2 border border-slate-300 rounded-lg
      focus:ring-2 focus:ring-blue-500 focus:border-blue-500
      text-sm transition-colors
      ${compact ? 'py-1.5 text-xs' : ''}
    `;

    switch (filter.type) {
      case 'text':
      case 'search':
        return (
          <div key={filter.key} className={filter.width || 'min-w-[180px]'}>
            {filter.label && (
              <label className="block text-xs font-medium text-slate-600 mb-1">
                {filter.label}
              </label>
            )}
            <div className="relative">
              {filter.type === 'search' && (
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">
                  🔍
                </span>
              )}
              <input
                type="text"
                value={value}
                onChange={(e) => onChange(filter.key, e.target.value)}
                placeholder={filter.placeholder || `Cerca...`}
                className={`${baseInputClass} ${filter.type === 'search' ? 'pl-9' : ''}`}
              />
              {value && (
                <button
                  onClick={() => onChange(filter.key, '')}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                >
                  ✕
                </button>
              )}
            </div>
          </div>
        );

      case 'select':
        return (
          <div key={filter.key} className={filter.width || 'min-w-[150px]'}>
            {filter.label && (
              <label className="block text-xs font-medium text-slate-600 mb-1">
                {filter.label}
              </label>
            )}
            <select
              value={value}
              onChange={(e) => onChange(filter.key, e.target.value)}
              className={baseInputClass}
            >
              <option value="">{filter.placeholder || 'Tutti'}</option>
              {filter.options?.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        );

      case 'date':
        return (
          <div key={filter.key} className={filter.width || 'min-w-[150px]'}>
            {filter.label && (
              <label className="block text-xs font-medium text-slate-600 mb-1">
                {filter.label}
              </label>
            )}
            <input
              type="date"
              value={value}
              onChange={(e) => onChange(filter.key, e.target.value)}
              className={baseInputClass}
            />
          </div>
        );

      case 'dateRange':
        return (
          <div key={filter.key} className="flex items-end gap-2">
            <div className={filter.width || 'min-w-[130px]'}>
              {filter.label && (
                <label className="block text-xs font-medium text-slate-600 mb-1">
                  {filter.label} da
                </label>
              )}
              <input
                type="date"
                value={value?.from || ''}
                onChange={(e) => onChange(filter.key, { ...value, from: e.target.value })}
                className={baseInputClass}
              />
            </div>
            <div className={filter.width || 'min-w-[130px]'}>
              <label className="block text-xs font-medium text-slate-600 mb-1">a</label>
              <input
                type="date"
                value={value?.to || ''}
                onChange={(e) => onChange(filter.key, { ...value, to: e.target.value })}
                className={baseInputClass}
              />
            </div>
          </div>
        );

      case 'number':
        return (
          <div key={filter.key} className={filter.width || 'min-w-[120px]'}>
            {filter.label && (
              <label className="block text-xs font-medium text-slate-600 mb-1">
                {filter.label}
              </label>
            )}
            <input
              type="number"
              value={value}
              onChange={(e) => onChange(filter.key, e.target.value)}
              placeholder={filter.placeholder}
              min={filter.min}
              max={filter.max}
              step={filter.step}
              className={baseInputClass}
            />
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className={`bg-white rounded-lg border border-slate-200 p-4 ${className}`}>
      <div className="flex flex-wrap items-end gap-4">
        {/* Filters */}
        {filters.map(renderFilter)}

        {/* Custom children (additional filters/buttons) */}
        {children}

        {/* Reset button */}
        {hasActiveFilters && onReset && (
          <Button
            variant="ghost"
            size={compact ? 'sm' : 'md'}
            onClick={onReset}
            className="text-slate-500"
          >
            ✕ Reset
          </Button>
        )}

        {/* Result count */}
        {resultCount !== undefined && (
          <div className="ml-auto text-sm text-slate-500">
            <span className="font-semibold text-slate-700">{resultCount}</span> {resultLabel}
          </div>
        )}
      </div>
    </div>
  );
};

/**
 * QuickFilters - Filtri rapidi con chip/badge
 */
export const QuickFilters = ({
  options = [],
  value,
  onChange,
  label,
  multiple = false,
}) => {
  const isSelected = (optValue) => {
    if (multiple) {
      return Array.isArray(value) && value.includes(optValue);
    }
    return value === optValue;
  };

  const handleClick = (optValue) => {
    if (multiple) {
      const current = Array.isArray(value) ? value : [];
      const newValue = current.includes(optValue)
        ? current.filter((v) => v !== optValue)
        : [...current, optValue];
      onChange(newValue);
    } else {
      onChange(value === optValue ? null : optValue);
    }
  };

  return (
    <div className="flex items-center gap-2 flex-wrap">
      {label && <span className="text-sm text-slate-500">{label}:</span>}
      {options.map((opt) => (
        <button
          key={opt.value}
          onClick={() => handleClick(opt.value)}
          className={`
            px-3 py-1 rounded-full text-sm font-medium transition-colors
            ${isSelected(opt.value)
              ? 'bg-blue-600 text-white'
              : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }
          `}
        >
          {opt.icon && <span className="mr-1">{opt.icon}</span>}
          {opt.label}
          {opt.count !== undefined && (
            <span className={`ml-1.5 ${isSelected(opt.value) ? 'text-blue-200' : 'text-slate-400'}`}>
              ({opt.count})
            </span>
          )}
        </button>
      ))}
    </div>
  );
};

export { FilterBar };
export default FilterBar;
