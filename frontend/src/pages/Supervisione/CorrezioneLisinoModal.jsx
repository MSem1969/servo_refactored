// =============================================================================
// SERV.O v8.1 - MODALE CORREZIONE LISTINO
// =============================================================================
// Form per correzione prezzi listino con suggerimenti pattern ML
// =============================================================================

import React, { useState, useEffect } from 'react';
import { supervisioneApi } from '../../api';
import { Button, StatusBadge, Loading } from '../../common';

const CorrezioneLisinoModal = ({ isOpen, onClose, supervisione, operatore, onSuccess }) => {
  const [loading, setLoading] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [detail, setDetail] = useState(null);
  const [formData, setFormData] = useState({
    prezzo_netto: '',
    prezzo_pubblico: '',
    prezzo_scontare: '',
    sconto_1: '',
    sconto_2: '',
    sconto_3: '',
    sconto_4: '',
    aliquota_iva: '',
    scorporo_iva: 'S',
    data_decorrenza: '',
    applica_a_listino: false,
    note: '',
  });

  // Carica dettagli e suggerimenti quando si apre
  useEffect(() => {
    if (isOpen && supervisione?.id_supervisione) {
      setLoadingDetail(true);
      supervisioneApi.getListinoDetail(supervisione.id_supervisione)
        .then(res => {
          setDetail(res);
          // Pre-popola form con valori correnti o suggeriti
          const riga = res.riga_corrente || {};
          const suggerimenti = res.suggerimenti || {};
          const listino = res.suggerimento_listino || {};
          setFormData({
            prezzo_netto: suggerimenti.prezzo_netto || listino.prezzo_netto || riga.prezzo_netto || '',
            prezzo_pubblico: suggerimenti.prezzo_pubblico || listino.prezzo_pubblico || riga.prezzo_pubblico || '',
            prezzo_scontare: suggerimenti.prezzo_scontare || listino.prezzo_scontare || riga.prezzo_scontare || '',
            sconto_1: suggerimenti.sconto_1 || listino.sconto_1 || riga.sconto_1 || '',
            sconto_2: suggerimenti.sconto_2 || listino.sconto_2 || riga.sconto_2 || '',
            sconto_3: suggerimenti.sconto_3 || listino.sconto_3 || riga.sconto_3 || '',
            sconto_4: suggerimenti.sconto_4 || listino.sconto_4 || riga.sconto_4 || '',
            aliquota_iva: suggerimenti.aliquota_iva || listino.aliquota_iva || riga.aliquota_iva || '10',
            scorporo_iva: suggerimenti.scorporo_iva || listino.scorporo_iva || riga.scorporo_iva || 'S',
            data_decorrenza: suggerimenti.data_decorrenza || listino.data_decorrenza || '',
            applica_a_listino: false,
            note: '',
          });
        })
        .catch(err => console.error('Errore caricamento dettaglio listino:', err))
        .finally(() => setLoadingDetail(false));
    }
  }, [isOpen, supervisione]);

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async () => {
    setLoading(true);
    try {
      const payload = {
        operatore,
        prezzo_netto: formData.prezzo_netto ? parseFloat(formData.prezzo_netto) : null,
        prezzo_pubblico: formData.prezzo_pubblico ? parseFloat(formData.prezzo_pubblico) : null,
        prezzo_scontare: formData.prezzo_scontare ? parseFloat(formData.prezzo_scontare) : null,
        sconto_1: formData.sconto_1 ? parseFloat(formData.sconto_1) : null,
        sconto_2: formData.sconto_2 ? parseFloat(formData.sconto_2) : null,
        sconto_3: formData.sconto_3 ? parseFloat(formData.sconto_3) : null,
        sconto_4: formData.sconto_4 ? parseFloat(formData.sconto_4) : null,
        aliquota_iva: formData.aliquota_iva ? parseFloat(formData.aliquota_iva) : null,
        scorporo_iva: formData.scorporo_iva || 'S',
        data_decorrenza: formData.data_decorrenza || null,
        applica_a_listino: formData.applica_a_listino,
        note: formData.note || null,
      };

      await supervisioneApi.correggiListino(supervisione.id_supervisione, payload);
      onSuccess?.();
      onClose();
    } catch (err) {
      alert('Errore correzione: ' + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  const riga = detail?.riga_corrente || {};
  const suggerimenti = detail?.suggerimenti || {};
  const hasSuggerimenti = Object.keys(suggerimenti).length > 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-auto">
        <div className="p-6 border-b border-slate-200">
          <h3 className="text-lg font-semibold text-slate-800">Correzione Listino</h3>
          <p className="text-sm text-slate-600 mt-1">
            AIC: <code className="bg-slate-100 px-2 py-0.5 rounded">{supervisione?.codice_aic}</code>
            {' - '}
            <span className="font-medium uppercase">
              {supervisione?.descrizione_prodotto || detail?.riga_corrente?.descrizione_prodotto || 'Descrizione non disponibile'}
            </span>
          </p>
        </div>

        {loadingDetail ? (
          <div className="p-8 text-center">
            <Loading text="Caricamento dettagli..." />
          </div>
        ) : (
          <div className="p-6">
            {/* Suggerimenti pattern */}
            {hasSuggerimenti && (
              <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-blue-600">Suggerimento Pattern</span>
                  <StatusBadge status="info" size="xs" label={`${suggerimenti.count_utilizzi || 0} utilizzi`} />
                </div>
                <p className="text-sm text-blue-800">
                  Questo prodotto è stato corretto in precedenza. I valori suggeriti sono pre-compilati.
                </p>
              </div>
            )}

            {/* Valori correnti dalla riga */}
            {riga.id_dettaglio && (
              <div className="mb-6 p-4 bg-slate-50 border border-slate-200 rounded-lg">
                <h4 className="text-sm font-medium text-slate-700 mb-2">Valori Correnti Riga</h4>
                <div className="grid grid-cols-3 gap-2 text-sm">
                  <p><span className="text-slate-500">Prezzo Netto:</span> {riga.prezzo_netto || '-'}</p>
                  <p><span className="text-slate-500">Prezzo Pubblico:</span> {riga.prezzo_pubblico || '-'}</p>
                  <p><span className="text-slate-500">IVA:</span> {riga.aliquota_iva || '-'}%</p>
                  <p><span className="text-slate-500">Sconto 1:</span> {riga.sconto_1 || '0'}%</p>
                  <p><span className="text-slate-500">Sconto 2:</span> {riga.sconto_2 || '0'}%</p>
                  <p><span className="text-slate-500">Sconto 3:</span> {riga.sconto_3 || '0'}%</p>
                </div>
              </div>
            )}

            {/* Form correzione */}
            <div className="space-y-4">
              {/* Sezione Prezzi */}
              <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
                <h5 className="text-sm font-medium text-green-800 mb-3">Prezzi</h5>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <label className="block text-xs font-medium text-slate-600 mb-1">Prezzo Netto</label>
                    <input
                      type="number"
                      step="0.01"
                      value={formData.prezzo_netto}
                      onChange={(e) => handleChange('prezzo_netto', e.target.value)}
                      className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      placeholder="0.00"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-600 mb-1">Prezzo Pubblico</label>
                    <input
                      type="number"
                      step="0.01"
                      value={formData.prezzo_pubblico}
                      onChange={(e) => handleChange('prezzo_pubblico', e.target.value)}
                      className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      placeholder="0.00"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-600 mb-1">Prezzo da Scontare</label>
                    <input
                      type="number"
                      step="0.01"
                      value={formData.prezzo_scontare}
                      onChange={(e) => handleChange('prezzo_scontare', e.target.value)}
                      className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      placeholder="0.00"
                    />
                  </div>
                </div>
              </div>

              {/* Sezione Sconti */}
              <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <h5 className="text-sm font-medium text-blue-800 mb-3">Sconti %</h5>
                <div className="grid grid-cols-4 gap-4">
                  {['sconto_1', 'sconto_2', 'sconto_3', 'sconto_4'].map((field, idx) => (
                    <div key={field}>
                      <label className="block text-xs font-medium text-slate-600 mb-1">Sconto {idx + 1}</label>
                      <input
                        type="number"
                        step="0.01"
                        value={formData[field]}
                        onChange={(e) => handleChange(field, e.target.value)}
                        className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        placeholder="0"
                      />
                    </div>
                  ))}
                </div>
              </div>

              {/* Sezione IVA e Date */}
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Aliquota IVA %</label>
                  <input
                    type="number"
                    step="0.01"
                    value={formData.aliquota_iva}
                    onChange={(e) => handleChange('aliquota_iva', e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    placeholder="10"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Scorporo IVA</label>
                  <select
                    value={formData.scorporo_iva}
                    onChange={(e) => handleChange('scorporo_iva', e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="S">S - Netto</option>
                    <option value="N">N - IVA inclusa</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Data Decorrenza</label>
                  <input
                    type="date"
                    value={formData.data_decorrenza}
                    onChange={(e) => handleChange('data_decorrenza', e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
              </div>

              {/* Note */}
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Note</label>
                <textarea
                  value={formData.note}
                  onChange={(e) => handleChange('note', e.target.value)}
                  rows={2}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Note opzionali..."
                />
              </div>

              {/* Checkbox listino */}
              <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg">
                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={formData.applica_a_listino}
                    onChange={(e) => handleChange('applica_a_listino', e.target.checked)}
                    className="w-5 h-5 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                  />
                  <div>
                    <span className="text-sm font-medium text-amber-800">Aggiungi al listino vendor</span>
                    <p className="text-xs text-amber-600">Se attivo, il prodotto verra aggiunto al listino per utilizzo futuro</p>
                  </div>
                </label>
              </div>
            </div>
          </div>
        )}

        <div className="p-6 border-t border-slate-200 flex justify-end gap-3">
          <Button variant="ghost" onClick={onClose} disabled={loading}>
            Annulla
          </Button>
          <Button variant="primary" onClick={handleSubmit} loading={loading}>
            Salva Correzione
          </Button>
        </div>
      </div>
    </div>
  );
};

export default CorrezioneLisinoModal;
