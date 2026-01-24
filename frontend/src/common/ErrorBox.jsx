// =============================================================================
// ERROR BOX COMPONENT
// =============================================================================
// Componente per visualizzazione errori uniforme
// Supporta diversi tipi: errore, warning, info, con azioni
// =============================================================================

import React from 'react';
import Button from './Button';

/**
 * Componente ErrorBox per gestione errori
 * 
 * LOGICA IMPLEMENTATIVA:
 * - Diversi tipi di alert: error, warning, info, success
 * - Azioni personalizzabili (retry, dismiss, custom)
 * - Icone automatiche per tipo
 * - Stili coerenti con design sistema
 * 
 * INTERRELAZIONI:
 * - Usato in: tutte le pagine per gestire errori API
 * - Sostituisce: tutti i div con bg-red-50 sparsi
 * 
 * @param {string} type - Tipo errore (error, warning, info, success)
 * @param {string} title - Titolo errore (opzionale)
 * @param {string} message - Messaggio errore
 * @param {function} onRetry - Handler per bottone retry (opzionale)
 * @param {function} onDismiss - Handler per chiudere (opzionale)
 * @param {React.Node} actions - Azioni custom (opzionale)
 * @param {boolean} dismissible - Mostra X per chiudere (default: true se onDismiss)
 * @param {string} className - Classi aggiuntive
 */
const ErrorBox = ({ 
  type = 'error',
  title,
  message,
  onRetry,
  onDismiss,
  actions,
  dismissible = !!onDismiss,
  className = ''
}) => {
  
  // Configurazione tipi di errore
  const typeConfig = {
    error: {
      bg: 'bg-red-50',
      border: 'border-red-200',
      titleColor: 'text-red-800',
      textColor: 'text-red-700',
      iconColor: 'text-red-500',
      icon: '❌',
      defaultTitle: 'Errore'
    },
    warning: {
      bg: 'bg-amber-50',
      border: 'border-amber-200', 
      titleColor: 'text-amber-800',
      textColor: 'text-amber-700',
      iconColor: 'text-amber-500',
      icon: '⚠️',
      defaultTitle: 'Attenzione'
    },
    info: {
      bg: 'bg-blue-50',
      border: 'border-blue-200',
      titleColor: 'text-blue-800', 
      textColor: 'text-blue-700',
      iconColor: 'text-blue-500',
      icon: 'ℹ️',
      defaultTitle: 'Informazione'
    },
    success: {
      bg: 'bg-emerald-50',
      border: 'border-emerald-200',
      titleColor: 'text-emerald-800',
      textColor: 'text-emerald-700', 
      iconColor: 'text-emerald-500',
      icon: '✅',
      defaultTitle: 'Successo'
    }
  };
  
  const config = typeConfig[type] || typeConfig.error;
  const finalTitle = title || config.defaultTitle;
  
  // Classi container
  const containerClasses = [
    'rounded-xl',
    'border',
    'p-4',
    'relative',
    config.bg,
    config.border,
    className
  ].join(' ');
  
  return (
    <div className={containerClasses} role="alert">
      {/* Header con icona, titolo e dismiss button */}
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          {/* Icona */}
          <span className={`text-lg ${config.iconColor}`}>
            {config.icon}
          </span>
          
          {/* Titolo */}
          {finalTitle && (
            <h4 className={`font-medium ${config.titleColor}`}>
              {finalTitle}
            </h4>
          )}
        </div>
        
        {/* Dismiss button */}
        {dismissible && onDismiss && (
          <button
            onClick={onDismiss}
            className={`${config.iconColor} hover:opacity-70 transition-opacity text-lg leading-none`}
            aria-label="Chiudi"
          >
            ✕
          </button>
        )}
      </div>
      
      {/* Messaggio */}
      {message && (
        <p className={`${config.textColor} text-sm mb-3 leading-relaxed`}>
          {message}
        </p>
      )}
      
      {/* Azioni */}
      {(onRetry || actions) && (
        <div className="flex items-center gap-2 mt-3">
          {/* Bottone retry automatico */}
          {onRetry && (
            <Button
              variant="secondary"
              size="sm"
              onClick={onRetry}
              className="text-xs"
            >
              🔄 Riprova
            </Button>
          )}
          
          {/* Azioni custom */}
          {actions}
        </div>
      )}
    </div>
  );
};

// Componenti predefiniti per tipi comuni
ErrorBox.Error = (props) => <ErrorBox type="error" {...props} />;
ErrorBox.Warning = (props) => <ErrorBox type="warning" {...props} />;
ErrorBox.Info = (props) => <ErrorBox type="info" {...props} />;
ErrorBox.Success = (props) => <ErrorBox type="success" {...props} />;

// ErrorBox per errori API con retry
ErrorBox.ApiError = ({ error, onRetry, ...props }) => {
  const message = error?.response?.data?.detail || 
                  error?.message || 
                  'Errore di comunicazione con il server';
  
  return (
    <ErrorBox 
      type="error"
      title="Errore API"
      message={message}
      onRetry={onRetry}
      {...props} 
    />
  );
};

// ErrorBox per network errors
ErrorBox.NetworkError = (props) => (
  <ErrorBox
    type="error"
    title="Errore di Rete"
    message="Impossibile connettersi al server. Verifica la connessione."
    {...props}
  />
);

export { ErrorBox };
export default ErrorBox;
