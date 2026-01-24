// =============================================================================
// SERV.O v10.1 - FORM FIELD COMPONENT
// =============================================================================
// Componente input form riutilizzabile con label, errori, help text
// =============================================================================

import React from 'react';

/**
 * FormField - Input form con label e gestione errori
 *
 * Features:
 * - Label con required indicator
 * - Error e help text
 * - Vari tipi input (text, number, email, password, textarea, select)
 * - Prefix/suffix icons
 * - Disabled state styling
 *
 * @param {string} type - Tipo input (text, number, email, password, textarea, select)
 * @param {string} label - Label campo
 * @param {string} name - Nome campo (per form)
 * @param {string} value - Valore corrente
 * @param {function} onChange - Handler cambio valore
 * @param {string} placeholder - Placeholder
 * @param {string} error - Messaggio errore
 * @param {string} helpText - Testo aiuto
 * @param {boolean} required - Campo obbligatorio
 * @param {boolean} disabled - Campo disabilitato
 * @param {Array} options - Opzioni per select [{ value, label }]
 * @param {React.Node} prefix - Contenuto prefix (icona/testo)
 * @param {React.Node} suffix - Contenuto suffix (icona/testo)
 * @param {number} rows - Righe textarea
 * @param {string} className - Classi CSS container
 * @param {object} inputProps - Props aggiuntivi per input
 */
const FormField = ({
  type = 'text',
  label,
  name,
  value,
  onChange,
  placeholder,
  error,
  helpText,
  required = false,
  disabled = false,
  options = [],
  prefix,
  suffix,
  rows = 3,
  className = '',
  inputClassName = '',
  ...inputProps
}) => {
  // Base input classes
  const baseInputClass = `
    w-full px-3 py-2 border rounded-lg text-sm
    transition-colors duration-200
    focus:outline-none focus:ring-2 focus:ring-offset-0
    disabled:bg-slate-50 disabled:text-slate-500 disabled:cursor-not-allowed
    ${error
      ? 'border-red-300 focus:border-red-500 focus:ring-red-500/20'
      : 'border-slate-300 focus:border-blue-500 focus:ring-blue-500/20'
    }
    ${prefix ? 'pl-10' : ''}
    ${suffix ? 'pr-10' : ''}
    ${inputClassName}
  `;

  // Handle change for different input types
  const handleChange = (e) => {
    const val = e.target.value;
    if (type === 'number') {
      onChange(val === '' ? '' : Number(val));
    } else {
      onChange(val);
    }
  };

  // Render input based on type
  const renderInput = () => {
    const commonProps = {
      name,
      value: value ?? '',
      onChange: handleChange,
      placeholder,
      disabled,
      className: baseInputClass,
      ...inputProps,
    };

    switch (type) {
      case 'textarea':
        return <textarea {...commonProps} rows={rows} />;

      case 'select':
        return (
          <select {...commonProps}>
            {placeholder && <option value="">{placeholder}</option>}
            {options.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        );

      default:
        return <input type={type} {...commonProps} />;
    }
  };

  return (
    <div className={`space-y-1 ${className}`}>
      {/* Label */}
      {label && (
        <label
          htmlFor={name}
          className="block text-sm font-medium text-slate-700"
        >
          {label}
          {required && <span className="text-red-500 ml-0.5">*</span>}
        </label>
      )}

      {/* Input wrapper */}
      <div className="relative">
        {/* Prefix */}
        {prefix && (
          <div className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none">
            {prefix}
          </div>
        )}

        {/* Input */}
        {renderInput()}

        {/* Suffix */}
        {suffix && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400">
            {suffix}
          </div>
        )}
      </div>

      {/* Error message */}
      {error && (
        <p className="text-sm text-red-600 flex items-center gap-1">
          <span>⚠</span> {error}
        </p>
      )}

      {/* Help text */}
      {helpText && !error && (
        <p className="text-xs text-slate-500">{helpText}</p>
      )}
    </div>
  );
};

/**
 * FormRow - Layout helper per campi form in riga
 */
export const FormRow = ({ children, cols = 2, gap = 4, className = '' }) => (
  <div
    className={`grid gap-${gap} ${className}`}
    style={{ gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))` }}
  >
    {children}
  </div>
);

/**
 * FormSection - Sezione form con titolo
 */
export const FormSection = ({ title, description, children, className = '' }) => (
  <div className={`space-y-4 ${className}`}>
    {(title || description) && (
      <div className="border-b border-slate-200 pb-2">
        {title && <h4 className="text-sm font-semibold text-slate-800">{title}</h4>}
        {description && <p className="text-xs text-slate-500 mt-0.5">{description}</p>}
      </div>
    )}
    {children}
  </div>
);

/**
 * Checkbox - Checkbox con label
 */
export const Checkbox = ({
  label,
  checked,
  onChange,
  disabled = false,
  className = '',
}) => (
  <label className={`flex items-center gap-2 cursor-pointer ${disabled ? 'opacity-50 cursor-not-allowed' : ''} ${className}`}>
    <input
      type="checkbox"
      checked={checked}
      onChange={(e) => onChange(e.target.checked)}
      disabled={disabled}
      className="w-4 h-4 text-blue-600 border-slate-300 rounded focus:ring-blue-500"
    />
    <span className="text-sm text-slate-700">{label}</span>
  </label>
);

/**
 * RadioGroup - Gruppo radio buttons
 */
export const RadioGroup = ({
  name,
  options = [],
  value,
  onChange,
  disabled = false,
  inline = false,
  className = '',
}) => (
  <div className={`${inline ? 'flex items-center gap-4' : 'space-y-2'} ${className}`}>
    {options.map((opt) => (
      <label
        key={opt.value}
        className={`flex items-center gap-2 cursor-pointer ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
      >
        <input
          type="radio"
          name={name}
          value={opt.value}
          checked={value === opt.value}
          onChange={() => onChange(opt.value)}
          disabled={disabled}
          className="w-4 h-4 text-blue-600 border-slate-300 focus:ring-blue-500"
        />
        <span className="text-sm text-slate-700">{opt.label}</span>
      </label>
    ))}
  </div>
);

/**
 * Toggle - Switch toggle
 */
export const Toggle = ({
  label,
  checked,
  onChange,
  disabled = false,
  size = 'md',
  className = '',
}) => {
  const sizes = {
    sm: { track: 'w-8 h-4', thumb: 'w-3 h-3', translate: 'translate-x-4' },
    md: { track: 'w-10 h-5', thumb: 'w-4 h-4', translate: 'translate-x-5' },
    lg: { track: 'w-12 h-6', thumb: 'w-5 h-5', translate: 'translate-x-6' },
  };
  const s = sizes[size];

  return (
    <label className={`flex items-center gap-3 cursor-pointer ${disabled ? 'opacity-50 cursor-not-allowed' : ''} ${className}`}>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => !disabled && onChange(!checked)}
        className={`
          ${s.track} rounded-full relative transition-colors
          ${checked ? 'bg-blue-600' : 'bg-slate-300'}
          ${disabled ? 'cursor-not-allowed' : ''}
        `}
      >
        <span
          className={`
            ${s.thumb} bg-white rounded-full absolute top-0.5 left-0.5
            transition-transform shadow-sm
            ${checked ? s.translate : 'translate-x-0'}
          `}
        />
      </button>
      {label && <span className="text-sm text-slate-700">{label}</span>}
    </label>
  );
};

export { FormField };
export default FormField;
