// =============================================================================
// BUTTON COMPONENT
// =============================================================================
// Componente pulsante riutilizzabile con varianti predefinite
// Sostituisce tutti i button sparsi in App.jsx
// =============================================================================

import React from 'react';

/**
 * Componente Button versatile per SERV.O
 *
 * LOGICA IMPLEMENTATIVA:
 * - Varianti predefinite con stili coerenti
 * - Sizing responsive (sm, md, lg)
 * - Stati disabled e loading gestiti automaticamente
 * - Classi CSS modulari e componibili
 * - Support per icone e contenuto custom
 * - Supporto `as` prop per rendering come altri elementi (es: span per label)
 *
 * @param {string} variant - Stile del button (primary, secondary, success, danger, ghost)
 * @param {string} size - Dimensione (sm, md, lg)
 * @param {boolean} disabled - Stato disabilitato
 * @param {boolean} loading - Stato di caricamento (mostra spinner)
 * @param {string} className - Classi CSS aggiuntive
 * @param {function} onClick - Handler click
 * @param {string} as - Elemento da renderizzare (default: 'button', può essere 'span', 'div', ecc.)
 * @param {React.Node} children - Contenuto del button
 * @param {object} ...props - Altri props HTML del button
 */
const Button = ({
  children,
  variant = 'primary',
  size = 'md',
  onClick,
  disabled = false,
  loading = false,
  className = '',
  type = 'button',
  as: Component = 'button',
  ...props
}) => {
  
  // Mappa varianti → classi CSS
  const variantClasses = {
    primary: 'bg-blue-600 text-white hover:bg-blue-700 focus:ring-blue-500 disabled:bg-blue-300',
    secondary: 'bg-slate-100 text-slate-700 hover:bg-slate-200 focus:ring-slate-500 disabled:bg-slate-50 disabled:text-slate-400',
    success: 'bg-emerald-600 text-white hover:bg-emerald-700 focus:ring-emerald-500 disabled:bg-emerald-300',
    danger: 'bg-red-600 text-white hover:bg-red-700 focus:ring-red-500 disabled:bg-red-300',
    ghost: 'text-slate-600 hover:bg-slate-100 focus:ring-slate-500 disabled:text-slate-300',
    warning: 'bg-amber-600 text-white hover:bg-amber-700 focus:ring-amber-500 disabled:bg-amber-300',
  };
  
  // Mappa dimensioni → classi CSS
  const sizeClasses = {
    xs: 'px-2 py-1 text-xs',
    sm: 'px-3 py-1.5 text-xs',
    md: 'px-4 py-2 text-sm',
    lg: 'px-6 py-3 text-base',
  };
  
  // Classi base comuni a tutti i button
  const baseClasses = [
    'font-medium',
    'rounded-lg',
    'transition-all',
    'duration-200',
    'focus:outline-none',
    'focus:ring-2',
    'focus:ring-offset-1',
    'disabled:cursor-not-allowed',
    'disabled:opacity-50',
    'inline-flex',
    'items-center',
    'justify-center',
    'gap-2',
  ].join(' ');
  
  // Combina tutte le classi
  const finalClasses = [
    baseClasses,
    variantClasses[variant] || variantClasses.primary,
    sizeClasses[size] || sizeClasses.md,
    className
  ].join(' ');
  
  // Stato finale disabled (loading o disabled esplicito)
  const isDisabled = disabled || loading;
  
  // Props condizionali (type solo per button)
  const elementProps = {
    className: finalClasses,
    ...props
  };

  // Aggiungi props specifici solo per button
  if (Component === 'button') {
    elementProps.type = type;
    elementProps.onClick = onClick;
    elementProps.disabled = isDisabled;
  }

  return (
    <Component {...elementProps}>
      {/* Spinner di loading */}
      {loading && (
        <div className="animate-spin w-4 h-4 border-2 border-current border-t-transparent rounded-full" />
      )}

      {/* Contenuto del button */}
      {children}
    </Component>
  );
};

// Export named e default per flessibilità
export { Button };
export default Button;
