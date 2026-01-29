// =============================================================================
// SERV.O v11.4 - PDF VIEWER BUTTON
// =============================================================================
// Componente riutilizzabile per visualizzare PDF ordine
// Usato in tutti i modal di risoluzione anomalie
// =============================================================================

import React, { useState, useEffect } from 'react';
import { getApiBaseUrl } from '../api';

/**
 * Bottone per visualizzare PDF ordine
 *
 * @param {Object} props
 * @param {string} props.pdfFile - Nome file PDF (se già disponibile)
 * @param {number} props.idTestata - ID testata per caricare pdf_file (alternativo a pdfFile)
 * @param {string} props.variant - Variante: 'default' | 'compact' | 'icon-only'
 * @param {string} props.className - Classi CSS aggiuntive
 */
const PdfViewerButton = ({
  pdfFile,
  idTestata,
  variant = 'default',
  className = ''
}) => {
  const [loadedPdfFile, setLoadedPdfFile] = useState(null);
  const [loading, setLoading] = useState(false);

  // Carica pdf_file da idTestata se non fornito direttamente
  useEffect(() => {
    if (pdfFile) {
      setLoadedPdfFile(pdfFile);
      return;
    }

    if (idTestata && !pdfFile) {
      setLoading(true);
      import('../api').then(({ ordiniApi }) => {
        ordiniApi.getOrdine(idTestata)
          .then(res => setLoadedPdfFile(res?.pdf_file || null))
          .catch(() => setLoadedPdfFile(null))
          .finally(() => setLoading(false));
      });
    }

    return () => {
      if (!pdfFile) setLoadedPdfFile(null);
    };
  }, [pdfFile, idTestata]);

  const actualPdfFile = pdfFile || loadedPdfFile;

  if (!actualPdfFile && !loading) return null;

  if (loading) {
    return (
      <span className="text-slate-400 text-sm">Caricamento PDF...</span>
    );
  }

  const pdfUrl = `${getApiBaseUrl()}/api/v1/upload/pdf/${encodeURIComponent(actualPdfFile)}`;

  // Icona PDF
  const PdfIcon = () => (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"
      />
    </svg>
  );

  // Varianti di stile
  const baseClasses = 'flex items-center gap-2 rounded-lg transition-colors';

  const variantClasses = {
    default: 'px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm',
    compact: 'px-2 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs',
    'icon-only': 'p-2 bg-blue-600 hover:bg-blue-700 text-white',
  };

  const variantLabels = {
    default: 'Visualizza PDF',
    compact: 'PDF',
    'icon-only': null,
  };

  return (
    <a
      href={pdfUrl}
      target="_blank"
      rel="noopener noreferrer"
      className={`${baseClasses} ${variantClasses[variant] || variantClasses.default} ${className}`}
      title="Apri PDF ordine"
    >
      <PdfIcon />
      {variantLabels[variant] !== null && variantLabels[variant]}
    </a>
  );
};

export default PdfViewerButton;
