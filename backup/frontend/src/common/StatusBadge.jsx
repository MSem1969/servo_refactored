// =============================================================================
// STATUS BADGE COMPONENT
// =============================================================================
// Badge colorato per stati ordini, utenti, processi
// Centralizza tutta la logica di styling degli stati
// =============================================================================

import React from 'react';

/**
 * Componente StatusBadge per stati del sistema
 * 
 * LOGICA IMPLEMENTATIVA:
 * - Mapping stati → stili predefiniti
 * - Supporto per icone automatiche
 * - Labels personalizzabili o auto-generate
 * - Colori coerenti in tutto il sistema
 * 
 * INTERRELAZIONI:
 * - Usato in: DatabasePage, UploadPage, UtentiPage, OrderDetailPage
 * - Sostituisce: tutti gli span con classi bg-* text-* sparsi
 * 
 * @param {string} status - Stato da visualizzare
 * @param {string} label - Label custom (opzionale, auto-generata se mancante)
 * @param {boolean} showIcon - Mostra icona automatica (default: true)
 * @param {string} size - Dimensione (xs, sm, md)
 * @param {string} className - Classi aggiuntive
 */
const StatusBadge = ({ 
  status, 
  label, 
  showIcon = true, 
  size = 'sm',
  className = '' 
}) => {
  
  // Configurazione completa stati con: colori, label, icone
  const statusConfig = {
    // Stati generici
    completed: { 
      bg: 'bg-emerald-100', 
      text: 'text-emerald-700', 
      label: 'Completato', 
      icon: '✓' 
    },
    processing: { 
      bg: 'bg-amber-100', 
      text: 'text-amber-700', 
      label: 'In Elaborazione', 
      icon: '⏳' 
    },
    pending: { 
      bg: 'bg-slate-100', 
      text: 'text-slate-600', 
      label: 'In Attesa', 
      icon: '○' 
    },
    error: { 
      bg: 'bg-red-100', 
      text: 'text-red-700', 
      label: 'Errore', 
      icon: '✕' 
    },
    
    // Stati ordini specifici
    ESTRATTO: { 
      bg: 'bg-blue-100', 
      text: 'text-blue-700', 
      label: 'Estratto', 
      icon: '📄' 
    },
    ANOMALIA: { 
      bg: 'bg-red-100', 
      text: 'text-red-700', 
      label: 'Anomalia', 
      icon: '⚠️' 
    },
    PARZ_EVASO: {
      bg: 'bg-orange-100',
      text: 'text-orange-600',
      label: 'Parz. Evaso',
      icon: '📦'
    },
    EVASO: {
      bg: 'bg-emerald-100',
      text: 'text-emerald-700',
      label: 'Evaso',
      icon: '✅'
    },
    ARCHIVIATO: {
      bg: 'bg-slate-200',
      text: 'text-slate-500',
      label: 'Archiviato',
      icon: '📁'
    },
    
    // Stati righe ordine
    CONFERMATO: { 
      bg: 'bg-emerald-100', 
      text: 'text-emerald-700', 
      label: 'Pronto Export', 
      icon: '✓' 
    },
    IN_SUPERVISIONE: { 
      bg: 'bg-orange-100', 
      text: 'text-orange-700', 
      label: 'In Supervisione', 
      icon: '👁️' 
    },
    SUPERVISIONATO: { 
      bg: 'bg-blue-100', 
      text: 'text-blue-700', 
      label: 'Supervisionato', 
      icon: '✓' 
    },
    IN_TRACCIATO: { 
      bg: 'bg-purple-100', 
      text: 'text-purple-700', 
      label: 'In Tracciato', 
      icon: '📋' 
    },
    PARZIALMENTE_ESP: { 
      bg: 'bg-amber-100', 
      text: 'text-amber-700', 
      label: 'Parziale', 
      icon: '⚡' 
    },
    
    // Stati supervisione
    PENDING_REVIEW: { 
      bg: 'bg-orange-100', 
      text: 'text-orange-700', 
      label: 'In Revisione', 
      icon: '⏳' 
    },
    APPROVED: { 
      bg: 'bg-emerald-100', 
      text: 'text-emerald-700', 
      label: 'Approvato', 
      icon: '✓' 
    },
    REJECTED: { 
      bg: 'bg-red-100', 
      text: 'text-red-700', 
      label: 'Rifiutato', 
      icon: '✕' 
    },
    MODIFIED: { 
      bg: 'bg-purple-100', 
      text: 'text-purple-700', 
      label: 'Modificato', 
      icon: '✎' 
    },
    
    // Stati anomalie
    APERTA: { 
      bg: 'bg-red-100', 
      text: 'text-red-700', 
      label: 'Aperta', 
      icon: '🔴' 
    },
    RISOLTA: { 
      bg: 'bg-emerald-100', 
      text: 'text-emerald-700', 
      label: 'Risolta', 
      icon: '✅' 
    },
    IGNORATA: { 
      bg: 'bg-slate-100', 
      text: 'text-slate-500', 
      label: 'Ignorata', 
      icon: '⚪' 
    },
    
    // Stati upload
    duplicato: { 
      bg: 'bg-yellow-100', 
      text: 'text-yellow-700', 
      label: 'Duplicato', 
      icon: '⚠️' 
    },
    uploading: { 
      bg: 'bg-blue-100', 
      text: 'text-blue-700', 
      label: 'Caricamento...', 
      icon: '⬆️' 
    },
  };
  
  // Dimensioni badge
  const sizeClasses = {
    xs: 'px-1.5 py-0.5 text-xs',
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-1 text-sm',
  };
  
  // Recupera configurazione per lo stato corrente
  const config = statusConfig[status] || statusConfig.pending;
  
  // Label finale: custom o auto-generata
  const finalLabel = label || config.label;
  
  // Classi CSS finali
  const finalClasses = [
    'font-medium',
    'rounded-full',
    'inline-flex',
    'items-center',
    'gap-1',
    'whitespace-nowrap',
    config.bg,
    config.text,
    sizeClasses[size] || sizeClasses.sm,
    className
  ].join(' ');
  
  return (
    <span className={finalClasses}>
      {/* Icona (se abilitata) */}
      {showIcon && config.icon && (
        <span className="leading-none">{config.icon}</span>
      )}
      
      {/* Label */}
      <span>{finalLabel}</span>
    </span>
  );
};

// Utility per verificare se uno stato esiste
StatusBadge.hasStatus = (status) => {
  const statusConfig = {
    completed: true, processing: true, pending: true, error: true,
    ESTRATTO: true, ANOMALIA: true, PARZ_EVASO: true, EVASO: true, ARCHIVIATO: true,
    CONFERMATO: true, IN_SUPERVISIONE: true, SUPERVISIONATO: true, IN_TRACCIATO: true,
    PARZIALMENTE_ESP: true, PENDING_REVIEW: true, APPROVED: true, REJECTED: true,
    MODIFIED: true, APERTA: true, RISOLTA: true, IGNORATA: true,
    duplicato: true, uploading: true
  };
  return !!statusConfig[status];
};

export { StatusBadge };
export default StatusBadge;
