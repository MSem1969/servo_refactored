// =============================================================================
// SERV.O v11.4 - MODAL BASE COMPONENT
// =============================================================================
// Componente modale riutilizzabile con varianti e features avanzate
// v11.4: Aggiunto supporto drag per spostare modal nello schermo
// =============================================================================

import React, { useEffect, useCallback, useState, useRef } from 'react';
import Button from './Button';

/**
 * ModalBase - Componente modale base per SERV.O
 *
 * Features:
 * - Chiusura con ESC
 * - Chiusura cliccando overlay (opzionale)
 * - Animazioni CSS
 * - Varianti colore per header
 * - Footer con azioni predefinite
 * - Supporto loading state
 * - v11.4: Trascinabile (drag header per spostare)
 *
 * @param {boolean} isOpen - Stato apertura modale
 * @param {function} onClose - Handler chiusura
 * @param {string} title - Titolo modale
 * @param {string} subtitle - Sottotitolo opzionale
 * @param {React.Node} children - Contenuto
 * @param {React.Node} footer - Footer custom (sovrascrive actions)
 * @param {string} size - Dimensione (sm, md, lg, xl, full)
 * @param {string} variant - Variante colore header (default, primary, success, warning, danger)
 * @param {boolean} showCloseButton - Mostra pulsante X
 * @param {boolean} closeOnOverlay - Chiudi cliccando overlay
 * @param {boolean} closeOnEsc - Chiudi con ESC
 * @param {boolean} draggable - Abilita trascinamento modal (default: true)
 * @param {object} actions - Azioni footer { confirm, cancel, confirmText, cancelText, confirmVariant, loading }
 * @param {React.Node} headerActions - v11.4: Azioni aggiuntive nel header (es. PdfViewerButton)
 */
const ModalBase = ({
  isOpen,
  onClose,
  title,
  subtitle,
  children,
  footer,
  size = 'lg',
  variant = 'default',
  showCloseButton = true,
  closeOnOverlay = true,
  closeOnEsc = true,
  draggable = true,
  actions,
  headerActions,
  className = '',
}) => {
  // v11.4: Stato per drag
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const dragRef = useRef({ startX: 0, startY: 0, initialX: 0, initialY: 0 });

  // Reset posizione quando si apre
  useEffect(() => {
    if (isOpen) {
      setPosition({ x: 0, y: 0 });
    }
  }, [isOpen]);

  // v11.4: Handler drag
  const handleMouseDown = useCallback((e) => {
    if (!draggable) return;
    // Evita drag se si clicca su bottoni o input
    if (e.target.closest('button') || e.target.closest('input')) return;

    setIsDragging(true);
    dragRef.current = {
      startX: e.clientX,
      startY: e.clientY,
      initialX: position.x,
      initialY: position.y,
    };
    e.preventDefault();
  }, [draggable, position]);

  const handleMouseMove = useCallback((e) => {
    if (!isDragging) return;

    const deltaX = e.clientX - dragRef.current.startX;
    const deltaY = e.clientY - dragRef.current.startY;

    setPosition({
      x: dragRef.current.initialX + deltaX,
      y: dragRef.current.initialY + deltaY,
    });
  }, [isDragging]);

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  // v11.4: Aggiungi listener globali per drag
  useEffect(() => {
    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    }
    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging, handleMouseMove, handleMouseUp]);

  // Chiusura con ESC
  const handleKeyDown = useCallback((e) => {
    if (closeOnEsc && e.key === 'Escape') {
      onClose?.();
    }
  }, [closeOnEsc, onClose]);

  useEffect(() => {
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'hidden';
    }
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
    };
  }, [isOpen, handleKeyDown]);

  if (!isOpen) return null;

  // Size classes
  const sizeClasses = {
    sm: 'max-w-md',
    md: 'max-w-2xl',
    lg: 'max-w-4xl',
    xl: 'max-w-6xl',
    full: 'max-w-[95vw]',
  };

  // Header variant classes
  const variantClasses = {
    default: 'bg-white border-b border-slate-200',
    primary: 'bg-blue-50 border-b border-blue-200',
    success: 'bg-emerald-50 border-b border-emerald-200',
    warning: 'bg-amber-50 border-b border-amber-200',
    danger: 'bg-red-50 border-b border-red-200',
  };

  const titleColorClasses = {
    default: 'text-slate-800',
    primary: 'text-blue-900',
    success: 'text-emerald-900',
    warning: 'text-amber-900',
    danger: 'text-red-900',
  };

  // Handle overlay click
  const handleOverlayClick = (e) => {
    if (closeOnOverlay && e.target === e.currentTarget) {
      onClose?.();
    }
  };

  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4 animate-fadeIn"
      onClick={handleOverlayClick}
    >
      <div
        className={`
          bg-white rounded-xl w-full ${sizeClasses[size]} max-h-[90vh] flex flex-col
          shadow-2xl animate-slideUp ${className}
          ${isDragging ? 'select-none' : ''}
        `}
        style={{
          transform: `translate(${position.x}px, ${position.y}px)`,
          transition: isDragging ? 'none' : 'transform 0.1s ease-out',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header - v11.4: Draggable handle */}
        {title && (
          <div
            className={`p-4 flex justify-between items-start shrink-0 rounded-t-xl ${variantClasses[variant]} ${
              draggable ? 'cursor-move' : ''
            }`}
            onMouseDown={handleMouseDown}
          >
            <div className="flex-1">
              <h3 className={`font-semibold text-lg ${titleColorClasses[variant]}`}>
                {title}
                {draggable && (
                  <span className="ml-2 text-xs text-slate-400 font-normal" title="Trascina per spostare">
                    ⋮⋮
                  </span>
                )}
              </h3>
              {subtitle && (
                <p className="text-sm text-slate-500 mt-0.5">{subtitle}</p>
              )}
            </div>
            {/* v11.4: Header actions (es. PDF viewer button) */}
            {headerActions && (
              <div className="flex items-center gap-2 mx-3">
                {headerActions}
              </div>
            )}
            {showCloseButton && (
              <button
                onClick={onClose}
                className="p-1.5 hover:bg-slate-100 rounded-lg transition-colors -mt-1 -mr-1"
                aria-label="Chiudi"
              >
                <svg className="w-5 h-5 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            )}
          </div>
        )}

        {/* Content */}
        <div className="p-4 overflow-y-auto flex-1">
          {children}
        </div>

        {/* Footer */}
        {(footer || actions) && (
          <div className="p-4 border-t border-slate-200 shrink-0 flex justify-end gap-3 bg-slate-50 rounded-b-xl">
            {footer || (
              <>
                {actions.cancel !== false && (
                  <Button
                    variant="secondary"
                    onClick={onClose}
                    disabled={actions.loading}
                  >
                    {actions.cancelText || 'Annulla'}
                  </Button>
                )}
                {actions.confirm && (
                  <Button
                    variant={actions.confirmVariant || 'primary'}
                    onClick={actions.confirm}
                    loading={actions.loading}
                    disabled={actions.disabled}
                  >
                    {actions.confirmText || 'Conferma'}
                  </Button>
                )}
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

// CSS animations (add to global CSS or use Tailwind config)
// @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
// @keyframes slideUp { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
// .animate-fadeIn { animation: fadeIn 0.15s ease-out; }
// .animate-slideUp { animation: slideUp 0.2s ease-out; }

export { ModalBase };
export default ModalBase;
