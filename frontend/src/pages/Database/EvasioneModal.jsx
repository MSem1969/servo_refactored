// =============================================================================
// SERV.O - EVASIONE MODAL
// =============================================================================
// Modal per registrazione data evasione e numero bolla
// =============================================================================

import React, { useState, useEffect } from 'react';
import ModalBase from '../../common/ModalBase';

export default function EvasioneModal({ isOpen, onClose, onSave, ordine }) {
  const [dataEvasione, setDataEvasione] = useState('');
  const [numeroBolla, setNumeroBolla] = useState('');
  const [saving, setSaving] = useState(false);

  // Reset/popola campi quando si apre il modal
  useEffect(() => {
    if (isOpen && ordine) {
      setDataEvasione(ordine.data_evasione || new Date().toISOString().split('T')[0]);
      setNumeroBolla(ordine.numero_bolla || '');
    }
  }, [isOpen, ordine]);

  const handleSave = async () => {
    if (!dataEvasione) return;
    setSaving(true);
    try {
      await onSave(ordine.id_esportazione_dettaglio, dataEvasione, numeroBolla);
      onClose();
    } catch (err) {
      alert('Errore: ' + (err.message || 'Errore salvataggio'));
    } finally {
      setSaving(false);
    }
  };

  if (!ordine) return null;

  return (
    <ModalBase
      isOpen={isOpen}
      onClose={onClose}
      title="Registra Evasione"
      subtitle={`Ordine ${ordine.numero_ordine_display || ordine.numero_ordine || ordine.numero_ordine_vendor || ''}`}
      size="sm"
      actions={{
        confirm: handleSave,
        confirmText: 'Salva',
        cancelText: 'Annulla',
        loading: saving,
        disabled: !dataEvasione
      }}
    >
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            Data Evasione *
          </label>
          <input
            type="date"
            value={dataEvasione}
            onChange={(e) => setDataEvasione(e.target.value)}
            className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            required
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            Numero Bolla
          </label>
          <input
            type="text"
            value={numeroBolla}
            onChange={(e) => setNumeroBolla(e.target.value)}
            placeholder="Es. BL-12345"
            className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>
    </ModalBase>
  );
}
