// =============================================================================
// SERV.O v11.0 - MODALE ARCHIVIAZIONE LISTINO
// =============================================================================
// Form per archiviazione riga listino (esclusione da tracciato EDI)
// v11.0: Usa ModalBase per coerenza UI (TIER 2.2)
// =============================================================================

import React, { useState, useEffect } from 'react';
import { supervisioneApi, getApiBaseUrl, ordiniApi } from '../../api';
import { ModalBase } from '../../common';

const ArchiviazioneListinoModal = ({ isOpen, onClose, supervisione, operatore, onSuccess }) => {
  const [loading, setLoading] = useState(false);
  const [motivo, setMotivo] = useState('');
  const [note, setNote] = useState('');
  const [pdfFile, setPdfFile] = useState(null); // v11.4: PDF file

  // v11.4: Carica pdf_file quando si apre
  useEffect(() => {
    if (isOpen && supervisione?.id_testata) {
      ordiniApi.getOrdine(supervisione.id_testata)
        .then(res => setPdfFile(res?.pdf_file || null))
        .catch(() => setPdfFile(null));
    } else if (!isOpen) {
      setPdfFile(null);
    }
  }, [isOpen, supervisione?.id_testata]);

  const motiviPredefiniti = [
    'Prodotto non in listino vendor',
    'AIC errato o non valido',
    'Prodotto fuori produzione',
    'Prodotto di altro vendor',
    'Errore estrazione PDF',
    'Altro (specificare nelle note)',
  ];

  const handleSubmit = async () => {
    if (!motivo || motivo.trim().length < 5) {
      alert('Inserire un motivo valido (minimo 5 caratteri)');
      return;
    }

    setLoading(true);
    try {
      await supervisioneApi.archiviaListino(supervisione.id_supervisione, {
        operatore,
        motivo,
        note: note || null,
      });
      onSuccess?.();
      onClose();
    } catch (err) {
      alert('Errore archiviazione: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  return (
    <ModalBase
      isOpen={isOpen}
      onClose={onClose}
      title="Archivia Riga"
      subtitle="La riga verrà esclusa dal tracciato EDI."
      size="sm"
      variant="warning"
      actions={{
        confirm: handleSubmit,
        confirmText: 'Archivia Riga',
        confirmVariant: 'danger',
        loading,
      }}
    >
      {/* v11.4: Bottone Visualizza PDF */}
      {pdfFile && (
        <div className="flex justify-end mb-4">
          <a
            href={`${getApiBaseUrl()}/api/v1/upload/pdf/${encodeURIComponent(pdfFile)}`}
            target="_blank"
            rel="noopener noreferrer"
            className="px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm flex items-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
            </svg>
            Visualizza PDF
          </a>
        </div>
      )}

      <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded-lg">
        <p className="text-sm text-amber-800">
          <strong>AIC:</strong> {supervisione?.codice_aic}<br />
          <strong>Prodotto:</strong> <span className="uppercase">{supervisione?.descrizione_prodotto || 'N/A'}</span>
        </p>
      </div>

      <div className="mb-4">
        <label className="block text-sm font-medium text-slate-700 mb-2">Motivo Archiviazione</label>
        <div className="space-y-2">
          {motiviPredefiniti.map((m) => (
            <label key={m} className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                name="motivo"
                checked={motivo === m}
                onChange={() => setMotivo(m)}
                className="w-4 h-4 border-slate-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-sm text-slate-700">{m}</span>
            </label>
          ))}
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">Note Aggiuntive</label>
        <textarea
          value={note}
          onChange={(e) => setNote(e.target.value)}
          rows={2}
          className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          placeholder="Dettagli aggiuntivi..."
        />
      </div>
    </ModalBase>
  );
};

export default ArchiviazioneListinoModal;
