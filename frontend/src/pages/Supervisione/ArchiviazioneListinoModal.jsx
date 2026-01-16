// =============================================================================
// SERV.O v8.1 - MODALE ARCHIVIAZIONE LISTINO
// =============================================================================
// Form per archiviazione riga listino (esclusione da tracciato EDI)
// =============================================================================

import React, { useState } from 'react';
import { supervisioneApi } from '../../api';
import { Button } from '../../common';

const ArchiviazioneListinoModal = ({ isOpen, onClose, supervisione, operatore, onSuccess }) => {
  const [loading, setLoading] = useState(false);
  const [motivo, setMotivo] = useState('');
  const [note, setNote] = useState('');

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

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-xl shadow-xl max-w-md w-full mx-4">
        <div className="p-6 border-b border-slate-200">
          <h3 className="text-lg font-semibold text-slate-800">Archivia Riga</h3>
          <p className="text-sm text-slate-600 mt-1">
            La riga verrà esclusa dal tracciato EDI.
          </p>
        </div>

        <div className="p-6">
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
        </div>

        <div className="p-6 border-t border-slate-200 flex justify-end gap-3">
          <Button variant="ghost" onClick={onClose} disabled={loading}>
            Annulla
          </Button>
          <Button variant="danger" onClick={handleSubmit} loading={loading}>
            Archivia Riga
          </Button>
        </div>
      </div>
    </div>
  );
};

export default ArchiviazioneListinoModal;
