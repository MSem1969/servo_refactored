/**
 * Modal Component - v6.2 Refactoring
 * Componente modale riutilizzabile
 */
import React from 'react';

export function Modal({
  isOpen,
  onClose,
  title,
  children,
  footer,
  size = 'lg', // sm, md, lg, xl, full
  showCloseButton = true
}) {
  if (!isOpen) return null;

  const sizeClasses = {
    sm: 'max-w-md',
    md: 'max-w-2xl',
    lg: 'max-w-4xl',
    xl: 'max-w-6xl',
    full: 'max-w-[95vw]'
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className={`bg-white rounded-xl w-[90vw] ${sizeClasses[size]} max-h-[90vh] flex flex-col`}>
        {/* Header */}
        {title && (
          <div className="p-4 border-b border-slate-200 flex justify-between items-center shrink-0">
            <h3 className="font-semibold text-slate-800">{title}</h3>
            {showCloseButton && (
              <button
                onClick={onClose}
                className="p-1 hover:bg-slate-100 rounded-lg transition-colors"
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
        {footer && (
          <div className="p-4 border-t border-slate-200 shrink-0 flex justify-end gap-2">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}

export default Modal;
