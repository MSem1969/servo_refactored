// =============================================================================
// SERV.O v11.0 - RIGA EDIT MODAL COMPONENT
// =============================================================================
// v11.0: Usa ModalBase per coerenza UI (TIER 2.2)
// =============================================================================

import React from 'react';
import { ModalBase } from '../../common';

export default function RigaEditModal({
  riga,
  formModifica,
  setFormModifica,
  onSave,
  onClose
}) {
  if (!riga) return null;

  const qTotale = (riga.q_venduta || 0) + (riga.q_sconto_merce || 0) + (riga.q_omaggio || 0);
  const qEvasa = riga.q_evasa || 0;
  const qResiduo = qTotale - qEvasa;

  return (
    <ModalBase
      isOpen={!!riga}
      onClose={onClose}
      title={`Modifica Riga #${riga.n_riga}`}
      size="md"
      variant="primary"
      actions={{
        confirm: () => onSave(riga),
        confirmText: 'Salva Modifiche',
        confirmVariant: 'primary',
      }}
    >
      <div className="space-y-4">
          {/* Codice AIC e Descrizione */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Codice AIC</label>
              <input
                type="text"
                value={formModifica.codice_aic}
                onChange={(e) => setFormModifica(f => ({ ...f, codice_aic: e.target.value }))}
                className="w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Descrizione</label>
              <input
                type="text"
                value={formModifica.descrizione}
                onChange={(e) => setFormModifica(f => ({ ...f, descrizione: e.target.value }))}
                className="w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>

          {/* Quantita */}
          <div className="grid grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Q.ta Ordinata</label>
              <input
                type="number"
                min="0"
                value={formModifica.q_venduta}
                onChange={(e) => setFormModifica(f => ({ ...f, q_venduta: parseInt(e.target.value) || 0 }))}
                className="w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Sc. Merce</label>
              <input
                type="number"
                min="0"
                value={formModifica.q_sconto_merce}
                onChange={(e) => setFormModifica(f => ({ ...f, q_sconto_merce: parseInt(e.target.value) || 0 }))}
                className="w-full px-3 py-2 border border-amber-300 rounded-md focus:ring-2 focus:ring-amber-500 focus:border-amber-500 bg-amber-50"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Omaggio</label>
              <input
                type="number"
                min="0"
                value={formModifica.q_omaggio}
                onChange={(e) => setFormModifica(f => ({ ...f, q_omaggio: parseInt(e.target.value) || 0 }))}
                className="w-full px-3 py-2 border border-green-300 rounded-md focus:ring-2 focus:ring-green-500 focus:border-green-500 bg-green-50"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-blue-700 mb-1">Da Evadere *</label>
              <input
                type="number"
                min="0"
                value={formModifica.q_da_evadere}
                onChange={(e) => setFormModifica(f => ({ ...f, q_da_evadere: parseInt(e.target.value) || 0 }))}
                onFocus={(e) => e.target.select()}
                className="w-full px-3 py-2 border border-blue-400 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-blue-50 font-medium"
              />
              <p className="text-xs text-blue-600 mt-1">Quantita per il prossimo tracciato</p>
            </div>
          </div>

          {/* Info Evaso e Residuo */}
          <div className="bg-slate-50 rounded-md p-3 border border-slate-200">
            <div className="grid grid-cols-3 gap-4 text-sm">
              <div>
                <span className="text-slate-500">Totale ordinato:</span>
                <span className="ml-2 font-medium">{qTotale}</span>
              </div>
              <div>
                <span className="text-slate-500">Gia evaso:</span>
                <span className="ml-2 font-medium text-green-600">{qEvasa}</span>
              </div>
              <div>
                <span className="text-slate-500">Residuo disponibile:</span>
                <span className="ml-2 font-medium text-orange-600">{qResiduo}</span>
              </div>
            </div>
          </div>

          {/* Prezzi */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Prezzo Netto (EUR)</label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={formModifica.prezzo_netto}
                onChange={(e) => setFormModifica(f => ({ ...f, prezzo_netto: parseFloat(e.target.value) || 0 }))}
                className="w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Prezzo Pubblico (EUR)</label>
              <input
                type="number"
                step="0.01"
                min="0"
                value={formModifica.prezzo_pubblico}
                onChange={(e) => setFormModifica(f => ({ ...f, prezzo_pubblico: parseFloat(e.target.value) || 0 }))}
                className="w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>

          {/* Sconti */}
          <div className="grid grid-cols-4 gap-4">
            {[1, 2, 3, 4].map(n => (
              <div key={n}>
                <label className="block text-sm font-medium text-slate-700 mb-1">Sconto {n} (%)</label>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  max="100"
                  value={formModifica[`sconto_${n}`]}
                  onChange={(e) => setFormModifica(f => ({ ...f, [`sconto_${n}`]: parseFloat(e.target.value) || 0 }))}
                  className="w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>
            ))}
          </div>

          {/* Note */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Note Allestimento</label>
            <textarea
              value={formModifica.note_allestimento}
              onChange={(e) => setFormModifica(f => ({ ...f, note_allestimento: e.target.value }))}
              rows={2}
              className="w-full px-3 py-2 border border-slate-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Note per allestimento..."
            />
          </div>
        </div>
    </ModalBase>
  );
}
