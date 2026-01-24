// =============================================================================
// SERV.O v11.0 - RIGA EDIT FORM COMPONENT
// =============================================================================
// Componente riutilizzabile per editing campi riga ordine
// v11.0: TIER 3.1 - Estratto da RigaEditModal e AnomaliaDetailModal
// =============================================================================

import React from 'react';

/**
 * Campo input standardizzato per form riga
 */
function FormInput({
  label,
  value,
  onChange,
  type = 'text',
  disabled = false,
  className = '',
  labelClassName = '',
  inputClassName = '',
  hint,
  ...props
}) {
  const baseInputClass = 'w-full px-3 py-2 border rounded-md focus:ring-2 focus:outline-none';
  const defaultInputClass = 'border-slate-300 focus:ring-blue-500 focus:border-blue-500';

  return (
    <div className={className}>
      <label className={`block text-sm font-medium text-slate-700 mb-1 ${labelClassName}`}>
        {label}
      </label>
      <input
        type={type}
        value={value}
        onChange={(e) => {
          const val = type === 'number'
            ? (props.step ? parseFloat(e.target.value) : parseInt(e.target.value)) || 0
            : e.target.value;
          onChange(val);
        }}
        disabled={disabled}
        className={`${baseInputClass} ${inputClassName || defaultInputClass} ${disabled ? 'bg-slate-100 cursor-not-allowed' : ''}`}
        {...props}
      />
      {hint && <p className="text-xs text-slate-500 mt-1">{hint}</p>}
    </div>
  );
}

/**
 * Campo textarea standardizzato
 */
function FormTextarea({
  label,
  value,
  onChange,
  disabled = false,
  className = '',
  rows = 2,
  placeholder = '',
  ...props
}) {
  return (
    <div className={className}>
      <label className="block text-sm font-medium text-slate-700 mb-1">{label}</label>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        rows={rows}
        placeholder={placeholder}
        className={`w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${disabled ? 'bg-slate-100 cursor-not-allowed' : ''}`}
        {...props}
      />
    </div>
  );
}

/**
 * Campo display read-only
 */
function FormDisplay({ label, value, className = '', variant = 'default' }) {
  const variants = {
    default: 'bg-white border-slate-200',
    success: 'bg-green-50 border-green-200 text-green-700',
    warning: 'bg-amber-50 border-amber-200 text-amber-700',
    info: 'bg-blue-50 border-blue-200 text-blue-700',
  };

  return (
    <div className={className}>
      <label className="block text-xs text-slate-500 mb-1">{label}</label>
      <div className={`px-3 py-2 border rounded text-sm ${variants[variant] || variants.default}`}>
        {value}
      </div>
    </div>
  );
}

/**
 * Sezione quantità con campi specializzati
 */
export function QuantitaSection({
  formData,
  onChange,
  showDaEvadere = false,
  showTotals = false,
  riga = null,
  compact = false,
}) {
  // Calcola totali se richiesto
  const qTotale = (formData.q_venduta || 0) + (formData.q_sconto_merce || 0) + (formData.q_omaggio || 0);
  const qEvasa = riga?.q_evasa || 0;
  const qResiduo = qTotale - qEvasa;

  const gridCols = showDaEvadere ? 'grid-cols-4' : (compact ? 'grid-cols-2' : 'grid-cols-3');

  return (
    <>
      <div className={`grid ${gridCols} gap-4`}>
        <FormInput
          label={compact ? 'Q.ta Venduta' : 'Q.ta Ordinata'}
          type="number"
          min="0"
          value={formData.q_venduta || 0}
          onChange={(val) => onChange({ ...formData, q_venduta: val })}
        />
        <FormInput
          label={compact ? 'Q. Sconto Merce' : 'Sc. Merce'}
          type="number"
          min="0"
          value={formData.q_sconto_merce || 0}
          onChange={(val) => onChange({ ...formData, q_sconto_merce: val })}
          inputClassName="border-amber-300 focus:ring-amber-500 focus:border-amber-500 bg-amber-50"
        />
        <FormInput
          label={compact ? 'Q. Omaggio' : 'Omaggio'}
          type="number"
          min="0"
          value={formData.q_omaggio || 0}
          onChange={(val) => onChange({ ...formData, q_omaggio: val })}
          inputClassName="border-green-300 focus:ring-green-500 focus:border-green-500 bg-green-50"
        />
        {showDaEvadere && (
          <FormInput
            label="Da Evadere *"
            labelClassName="text-blue-700"
            type="number"
            min="0"
            value={formData.q_da_evadere || 0}
            onChange={(val) => onChange({ ...formData, q_da_evadere: val })}
            inputClassName="border-blue-400 focus:ring-blue-500 focus:border-blue-500 bg-blue-50 font-medium"
            hint="Quantita per il prossimo tracciato"
          />
        )}
      </div>

      {showTotals && riga && (
        <div className="bg-slate-50 rounded-md p-3 border border-slate-200">
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div>
              <span className="text-slate-500">Totale ordinato:</span>
              <span className="ml-2 font-medium">{qTotale}</span>
            </div>
            <div>
              <span className="text-slate-500">Gia evaso:</span>
              <span className="ml-2 font-medium text-green-600">{qEvasa}</span>
            </div>
            <div>
              <span className="text-slate-500">Residuo disponibile:</span>
              <span className="ml-2 font-medium text-orange-600">{qResiduo}</span>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

/**
 * Sezione prezzi con sconti opzionali
 */
export function PrezziSection({
  formData,
  onChange,
  showPrezzoScontare = false,
  showSconti = false,
  showPrezzoPubblico = true,
  compact = false,
}) {
  return (
    <>
      <div className={`grid ${compact ? 'grid-cols-2' : 'grid-cols-2'} gap-4`}>
        <FormInput
          label={compact ? 'Prezzo Unitario (EUR)' : 'Prezzo Netto (EUR)'}
          type="number"
          step="0.01"
          min="0"
          value={formData.prezzo_netto || 0}
          onChange={(val) => onChange({ ...formData, prezzo_netto: val })}
        />
        {showPrezzoPubblico && !compact && (
          <FormInput
            label="Prezzo Pubblico (EUR)"
            type="number"
            step="0.01"
            min="0"
            value={formData.prezzo_pubblico || 0}
            onChange={(val) => onChange({ ...formData, prezzo_pubblico: val })}
          />
        )}
        {compact && (
          <FormDisplay
            label="Prezzo Totale Vendita"
            value={`${((formData.prezzo_netto || 0) * (formData.q_venduta || 0)).toFixed(2)} EUR`}
            variant="success"
          />
        )}
      </div>

      {showSconti && (
        <div className="grid grid-cols-4 gap-4">
          {[1, 2, 3, 4].map(n => (
            <FormInput
              key={n}
              label={`Sconto ${n} (%)`}
              type="number"
              step="0.1"
              min="0"
              max="100"
              value={formData[`sconto_${n}`] || 0}
              onChange={(val) => onChange({ ...formData, [`sconto_${n}`]: val })}
            />
          ))}
        </div>
      )}
    </>
  );
}

/**
 * Sezione codice e descrizione
 */
export function IdentificazioneSection({
  formData,
  onChange,
  codiceField = 'codice_aic',
  codiceLabel = 'Codice AIC',
  compact = false,
}) {
  return (
    <div className={`grid ${compact ? 'grid-cols-2' : 'grid-cols-2'} gap-4`}>
      <FormInput
        label={codiceLabel}
        value={formData[codiceField] || ''}
        onChange={(val) => onChange({ ...formData, [codiceField]: val })}
        className={compact ? 'font-mono' : ''}
      />
      <FormInput
        label="Descrizione"
        value={formData.descrizione || ''}
        onChange={(val) => onChange({ ...formData, descrizione: val })}
      />
    </div>
  );
}

/**
 * Sezione note
 */
export function NoteSection({ formData, onChange, rows = 2, placeholder = 'Note per allestimento...' }) {
  return (
    <FormTextarea
      label="Note Allestimento"
      value={formData.note_allestimento || ''}
      onChange={(val) => onChange({ ...formData, note_allestimento: val })}
      rows={rows}
      placeholder={placeholder}
    />
  );
}

/**
 * Form completo per editing riga ordine
 * Usa tutte le sezioni con configurazione completa
 */
export default function RigaEditForm({
  formData,
  onChange,
  riga = null,
  variant = 'full', // 'full' | 'compact' | 'anomalia'
  showSconti = true,
  showDaEvadere = true,
  showTotals = true,
  className = '',
}) {
  const isCompact = variant === 'compact' || variant === 'anomalia';
  const codiceField = variant === 'anomalia' ? 'codice_originale' : 'codice_aic';
  const codiceLabel = variant === 'anomalia' ? 'Codice' : 'Codice AIC';

  return (
    <div className={`space-y-4 ${className}`}>
      <IdentificazioneSection
        formData={formData}
        onChange={onChange}
        codiceField={codiceField}
        codiceLabel={codiceLabel}
        compact={isCompact}
      />

      <QuantitaSection
        formData={formData}
        onChange={onChange}
        showDaEvadere={showDaEvadere && variant === 'full'}
        showTotals={showTotals && variant === 'full'}
        riga={riga}
        compact={isCompact}
      />

      <PrezziSection
        formData={formData}
        onChange={onChange}
        showSconti={showSconti && variant === 'full'}
        showPrezzoPubblico={variant === 'full'}
        compact={isCompact}
      />

      <NoteSection
        formData={formData}
        onChange={onChange}
        rows={isCompact ? 2 : 2}
      />
    </div>
  );
}

// Exports for individual use
export { FormInput, FormTextarea, FormDisplay };
