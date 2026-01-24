// =============================================================================
// LOADING COMPONENT
// =============================================================================
// Componente per stati di caricamento uniformi
// Varie modalità: spinner, skeleton, inline, fullscreen
// =============================================================================

import React from 'react';

/**
 * Componente Loading per stati di caricamento
 * 
 * LOGICA IMPLEMENTATIVA:
 * - Diverse modalità: spinner, skeleton, dots, pulse
 * - Sizing automatico o personalizzabile
 * - Testi personalizzabili
 * - Centered layout automatico
 * 
 * INTERRELAZIONI:
 * - Usato in: tutte le pagine durante fetch API
 * - Sostituisce: tutti i div con animate-spin sparsi
 * 
 * @param {string} variant - Tipo loading (spinner, skeleton, dots, pulse)
 * @param {string} size - Dimensione (xs, sm, md, lg, xl)
 * @param {string} text - Testo opzionale
 * @param {boolean} center - Centra il loading (default: true)
 * @param {string} color - Colore spinner (blue, slate, etc.)
 * @param {string} className - Classi aggiuntive
 */
const Loading = ({ 
  variant = 'spinner',
  size = 'md',
  text = 'Caricamento...',
  center = true,
  color = 'blue',
  className = ''
}) => {
  
  // Dimensioni per diversi elementi
  const sizeClasses = {
    xs: { spinner: 'w-4 h-4', text: 'text-xs' },
    sm: { spinner: 'w-5 h-5', text: 'text-sm' },
    md: { spinner: 'w-6 h-6', text: 'text-sm' },
    lg: { spinner: 'w-8 h-8', text: 'text-base' },
    xl: { spinner: 'w-12 h-12', text: 'text-lg' },
  };
  
  // Colori spinner
  const colorClasses = {
    blue: 'border-blue-600 border-t-transparent',
    slate: 'border-slate-600 border-t-transparent', 
    emerald: 'border-emerald-600 border-t-transparent',
    red: 'border-red-600 border-t-transparent',
    amber: 'border-amber-600 border-t-transparent',
  };
  
  const currentSize = sizeClasses[size] || sizeClasses.md;
  const currentColor = colorClasses[color] || colorClasses.blue;
  
  // Wrapper container con centering opzionale
  const containerClasses = [
    center ? 'flex items-center justify-center p-8' : 'flex items-center gap-3',
    className
  ].join(' ');
  
  // Renderizza diversi tipi di loading
  const renderLoadingVariant = () => {
    switch (variant) {
      case 'spinner':
        return (
          <div className={containerClasses}>
            <div 
              className={`animate-spin border-2 rounded-full ${currentSize.spinner} ${currentColor}`}
            />
            {text && (
              <span className={`text-slate-600 ml-3 ${currentSize.text}`}>{text}</span>
            )}
          </div>
        );
        
      case 'dots':
        return (
          <div className={containerClasses}>
            <div className="flex space-x-1">
              {[0, 1, 2].map((i) => (
                <div 
                  key={i}
                  className={`bg-blue-600 rounded-full animate-pulse ${
                    size === 'xs' ? 'w-1 h-1' : 
                    size === 'sm' ? 'w-1.5 h-1.5' :
                    size === 'md' ? 'w-2 h-2' :
                    size === 'lg' ? 'w-2.5 h-2.5' : 'w-3 h-3'
                  }`}
                  style={{ animationDelay: `${i * 0.15}s` }}
                />
              ))}
            </div>
            {text && (
              <span className={`text-slate-600 ml-3 ${currentSize.text}`}>{text}</span>
            )}
          </div>
        );
        
      case 'skeleton':
        return (
          <div className={`space-y-3 ${className}`}>
            {/* Skeleton lines */}
            <div className="animate-pulse space-y-2">
              <div className="h-4 bg-slate-200 rounded w-3/4"></div>
              <div className="h-4 bg-slate-200 rounded w-1/2"></div>
              <div className="h-4 bg-slate-200 rounded w-5/6"></div>
            </div>
          </div>
        );
        
      case 'pulse':
        return (
          <div className={containerClasses}>
            <div 
              className={`bg-blue-600 rounded-full animate-pulse ${currentSize.spinner}`}
            />
            {text && (
              <span className={`text-slate-600 ml-3 animate-pulse ${currentSize.text}`}>{text}</span>
            )}
          </div>
        );
        
      default:
        return (
          <div className={containerClasses}>
            <div 
              className={`animate-spin border-2 rounded-full ${currentSize.spinner} ${currentColor}`}
            />
            {text && (
              <span className={`text-slate-600 ml-3 ${currentSize.text}`}>{text}</span>
            )}
          </div>
        );
    }
  };
  
  return renderLoadingVariant();
};

// Componenti predefiniti per casi comuni
Loading.Spinner = (props) => <Loading variant="spinner" {...props} />;
Loading.Dots = (props) => <Loading variant="dots" {...props} />;
Loading.Skeleton = (props) => <Loading variant="skeleton" center={false} {...props} />;
Loading.Pulse = (props) => <Loading variant="pulse" {...props} />;

// Loading inline senza centering
Loading.Inline = (props) => <Loading center={false} size="sm" {...props} />;

// Loading fullscreen
Loading.Fullscreen = ({ text = 'Caricamento...', ...props }) => (
  <div className="fixed inset-0 bg-white bg-opacity-75 backdrop-blur-sm flex items-center justify-center z-50">
    <Loading text={text} size="lg" {...props} />
  </div>
);

export { Loading };
export default Loading;
