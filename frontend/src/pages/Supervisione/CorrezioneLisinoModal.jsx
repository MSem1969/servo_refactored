// =============================================================================
// SERV.O v11.3 - MODALE CORREZIONE LISTINO
// =============================================================================
// Form per correzione prezzi listino con suggerimenti pattern ML
// v11.3: Calcolo prezzo netto da prezzo pubblico + sconti con gestione IVA
// =============================================================================

import React, { useState, useEffect, useMemo } from 'react';
import { supervisioneApi, ordiniApi } from '../../api';
import { ModalBase, StatusBadge, Loading, PdfViewerButton } from '../../common';

// Aliquote IVA disponibili
const ALIQUOTE_IVA = [
  { value: '10', label: '10%' },
  { value: '22', label: '22%' },
  { value: '4', label: '4%' },
  { value: '0', label: '0% (esente)' },
];

const CorrezioneLisinoModal = ({ isOpen, onClose, supervisione, operatore, onSuccess, scope = 'supervisore' }) => {
  const [loading, setLoading] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [detail, setDetail] = useState(null);
  const [pdfFile, setPdfFile] = useState(null); // v11.4: PDF file per visualizzazione

  // v11.3: Modalità inserimento - 'diretto' o 'calcolato'
  const [modalitaInserimento, setModalitaInserimento] = useState('calcolato');

  const [formData, setFormData] = useState({
    prezzo_netto: '',
    prezzo_pubblico: '',
    prezzo_scontare: '',
    sconto_1: '',
    sconto_2: '',
    sconto_3: '',
    sconto_4: '',
    aliquota_iva: '10',
    scorporo_iva: 'S',
    // v11.3: Nuovo campo per indicare se il prezzo pubblico è ivato
    prezzo_pubblico_ivato: true,
    data_decorrenza: '',
    applica_a_listino: false,
    note: '',
  });

  // Carica dettagli e suggerimenti quando si apre
  useEffect(() => {
    if (isOpen && supervisione?.id_supervisione) {
      setLoadingDetail(true);
      setPdfFile(null);

      // Carica dettaglio listino
      supervisioneApi.getListinoDetail(supervisione.id_supervisione)
        .then(async (res) => {
          setDetail(res);

          // v11.4: Carica pdf_file dalla testata se non presente
          let pdf = res?.pdf_file || res?.riga_corrente?.pdf_file;
          if (!pdf && supervisione?.id_testata) {
            try {
              const ordineRes = await ordiniApi.getOrdine(supervisione.id_testata);
              // v11.4 fix: ordineRes è { success, data: {...ordine} }
              pdf = ordineRes?.data?.pdf_file;
            } catch (e) {
              console.warn('Impossibile caricare pdf_file:', e);
            }
          }
          setPdfFile(pdf);

          // Pre-popola form con valori correnti o suggeriti
          const riga = res.riga_corrente || {};
          const suggerimenti = res.suggerimenti || {};
          const listino = res.suggerimento_listino || {};

          const prezzoNetto = suggerimenti.prezzo_netto || listino.prezzo_netto || riga.prezzo_netto || '';

          setFormData({
            prezzo_netto: prezzoNetto,
            prezzo_pubblico: suggerimenti.prezzo_pubblico || listino.prezzo_pubblico || riga.prezzo_pubblico || '',
            prezzo_scontare: suggerimenti.prezzo_scontare || listino.prezzo_scontare || riga.prezzo_scontare || '',
            sconto_1: suggerimenti.sconto_1 || listino.sconto_1 || riga.sconto_1 || '',
            sconto_2: suggerimenti.sconto_2 || listino.sconto_2 || riga.sconto_2 || '',
            sconto_3: suggerimenti.sconto_3 || listino.sconto_3 || riga.sconto_3 || '',
            sconto_4: suggerimenti.sconto_4 || listino.sconto_4 || riga.sconto_4 || '',
            aliquota_iva: suggerimenti.aliquota_iva || listino.aliquota_iva || riga.aliquota_iva || '10',
            scorporo_iva: suggerimenti.scorporo_iva || listino.scorporo_iva || riga.scorporo_iva || 'S',
            prezzo_pubblico_ivato: true,
            data_decorrenza: suggerimenti.data_decorrenza || listino.data_decorrenza || '',
            applica_a_listino: false,
            note: '',
          });

          // Default: modalità calcolata (prezzo pubblico + sconti)
          setModalitaInserimento('calcolato');
        })
        .catch(err => console.error('Errore caricamento dettaglio listino:', err))
        .finally(() => setLoadingDetail(false));
    }
  }, [isOpen, supervisione]);

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  // v11.3: Calcolo prezzo netto da prezzo pubblico + sconti
  const calcoloPrezzoNetto = useMemo(() => {
    if (modalitaInserimento !== 'calcolato') return null;

    const prezzoBase = parseFloat(formData.prezzo_pubblico) || 0;
    if (prezzoBase <= 0) return null;

    const aliquotaIva = parseFloat(formData.aliquota_iva) || 0;
    const sconto1 = parseFloat(formData.sconto_1) || 0;
    const sconto2 = parseFloat(formData.sconto_2) || 0;

    // Step 1: Scorporo IVA se il prezzo è ivato
    let prezzoSenzaIva = prezzoBase;
    if (formData.prezzo_pubblico_ivato && aliquotaIva > 0) {
      prezzoSenzaIva = prezzoBase / (1 + aliquotaIva / 100);
    }

    // Step 2: Applica sconti in cascata
    let prezzoScontato = prezzoSenzaIva;
    if (sconto1 > 0) {
      prezzoScontato = prezzoScontato * (1 - sconto1 / 100);
    }
    if (sconto2 > 0) {
      prezzoScontato = prezzoScontato * (1 - sconto2 / 100);
    }

    return {
      prezzoBase,
      prezzoSenzaIva: Math.round(prezzoSenzaIva * 100) / 100,
      prezzoNetto: Math.round(prezzoScontato * 100) / 100,
      ivaScorporata: formData.prezzo_pubblico_ivato ? Math.round((prezzoBase - prezzoSenzaIva) * 100) / 100 : 0,
      scontoTotale: Math.round((prezzoSenzaIva - prezzoScontato) * 100) / 100,
    };
  }, [modalitaInserimento, formData.prezzo_pubblico, formData.aliquota_iva, formData.sconto_1, formData.sconto_2, formData.prezzo_pubblico_ivato]);

  // v11.3: Applica il prezzo calcolato al form
  const applicaPrezzoCalcolato = () => {
    if (calcoloPrezzoNetto?.prezzoNetto > 0) {
      setFormData(prev => ({
        ...prev,
        prezzo_netto: calcoloPrezzoNetto.prezzoNetto.toFixed(2),
        prezzo_scontare: calcoloPrezzoNetto.prezzoSenzaIva.toFixed(2),
      }));
    }
  };

  const handleSubmit = async () => {
    // v11.3: Se in modalità calcolata, applica prima il prezzo
    let prezzoNettoFinale = formData.prezzo_netto;
    if (modalitaInserimento === 'calcolato' && calcoloPrezzoNetto?.prezzoNetto > 0) {
      prezzoNettoFinale = calcoloPrezzoNetto.prezzoNetto.toFixed(2);
    }

    if (!prezzoNettoFinale || parseFloat(prezzoNettoFinale) <= 0) {
      alert('Inserire un prezzo netto valido');
      return;
    }

    setLoading(true);
    try {
      const payload = {
        operatore,
        prezzo_netto: parseFloat(prezzoNettoFinale),
        prezzo_pubblico: formData.prezzo_pubblico ? parseFloat(formData.prezzo_pubblico) : null,
        prezzo_scontare: modalitaInserimento === 'calcolato' && calcoloPrezzoNetto
          ? calcoloPrezzoNetto.prezzoSenzaIva
          : (formData.prezzo_scontare ? parseFloat(formData.prezzo_scontare) : null),
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

  const riga = detail?.riga_corrente || {};
  const suggerimenti = detail?.suggerimenti || {};
  const hasSuggerimenti = Object.keys(suggerimenti).length > 0;

  // v11.4: Usa descrizione_riga (da ordini_dettaglio) invece di descrizione_prodotto (che contiene messaggio anomalia)
  const descrizioneProdotto = detail?.descrizione_riga || riga?.descrizione || supervisione?.descrizione_normalizzata || 'N/A';
  const subtitleText = `AIC: ${supervisione?.codice_aic || detail?.codice_aic || ''} - ${descrizioneProdotto.toUpperCase()}`;

  return (
    <ModalBase
      isOpen={isOpen}
      onClose={onClose}
      title="Correzione Listino"
      subtitle={subtitleText}
      size="lg"
      variant="primary"
      headerActions={<PdfViewerButton pdfFile={pdfFile} variant="compact" />}
      actions={{
        confirm: handleSubmit,
        confirmText: 'Salva Correzione',
        loading,
        disabled: loadingDetail,
      }}
    >
      {loadingDetail ? (
        <div className="py-8 text-center">
          <Loading text="Caricamento dettagli..." />
        </div>
      ) : (
        <div className="space-y-4">
          {/* Suggerimenti pattern */}
          {hasSuggerimenti && (
            <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
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
            <div className="p-4 bg-slate-50 border border-slate-200 rounded-lg">
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

          {/* v11.3: Selettore modalità inserimento */}
          <div className="p-4 bg-indigo-50 border border-indigo-200 rounded-lg">
            <h5 className="text-sm font-medium text-indigo-800 mb-3">Modalità Inserimento Prezzo</h5>
            <div className="flex gap-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="modalita"
                  value="diretto"
                  checked={modalitaInserimento === 'diretto'}
                  onChange={() => setModalitaInserimento('diretto')}
                  className="w-4 h-4 text-indigo-600"
                />
                <span className="text-sm text-indigo-700">Inserisci Prezzo Netto direttamente</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="modalita"
                  value="calcolato"
                  checked={modalitaInserimento === 'calcolato'}
                  onChange={() => setModalitaInserimento('calcolato')}
                  className="w-4 h-4 text-indigo-600"
                />
                <span className="text-sm text-indigo-700">Calcola da Prezzo Pubblico + Sconti</span>
              </label>
            </div>
          </div>

          {/* Modalità DIRETTA: Inserimento prezzo netto */}
          {modalitaInserimento === 'diretto' && (
            <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
              <h5 className="text-sm font-medium text-green-800 mb-3">Prezzo Netto</h5>
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">Prezzo Netto *</label>
                  <input
                    type="number"
                    step="0.01"
                    value={formData.prezzo_netto}
                    onChange={(e) => handleChange('prezzo_netto', e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
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
          )}

          {/* Modalità CALCOLATA: Prezzo pubblico + sconti */}
          {modalitaInserimento === 'calcolato' && (
            <>
              <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg">
                <h5 className="text-sm font-medium text-amber-800 mb-3">Prezzo Pubblico e IVA</h5>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <label className="block text-xs font-medium text-slate-600 mb-1">Prezzo Pubblico *</label>
                    <input
                      type="number"
                      step="0.01"
                      value={formData.prezzo_pubblico}
                      onChange={(e) => handleChange('prezzo_pubblico', e.target.value)}
                      className="w-full px-3 py-2 border border-amber-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-amber-500"
                      placeholder="0.00"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-600 mb-1">Aliquota IVA</label>
                    <select
                      value={formData.aliquota_iva}
                      onChange={(e) => handleChange('aliquota_iva', e.target.value)}
                      className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-amber-500"
                    >
                      {ALIQUOTE_IVA.map(opt => (
                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                      ))}
                    </select>
                  </div>
                  <div className="flex items-end pb-2">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={formData.prezzo_pubblico_ivato}
                        onChange={(e) => handleChange('prezzo_pubblico_ivato', e.target.checked)}
                        className="w-4 h-4 rounded border-slate-300 text-amber-600 focus:ring-amber-500"
                      />
                      <span className="text-sm text-slate-700">Prezzo IVA inclusa</span>
                    </label>
                  </div>
                </div>
              </div>

              <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <h5 className="text-sm font-medium text-blue-800 mb-3">Sconti % (applicati in cascata)</h5>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-medium text-slate-600 mb-1">Sconto 1 %</label>
                    <input
                      type="number"
                      step="0.01"
                      value={formData.sconto_1}
                      onChange={(e) => handleChange('sconto_1', e.target.value)}
                      className="w-full px-3 py-2 border border-blue-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      placeholder="0"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-600 mb-1">Sconto 2 %</label>
                    <input
                      type="number"
                      step="0.01"
                      value={formData.sconto_2}
                      onChange={(e) => handleChange('sconto_2', e.target.value)}
                      className="w-full px-3 py-2 border border-blue-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      placeholder="0"
                    />
                  </div>
                </div>
              </div>

              {/* Preview calcolo */}
              {calcoloPrezzoNetto && (
                <div className="p-4 bg-green-100 border border-green-300 rounded-lg">
                  <h5 className="text-sm font-bold text-green-800 mb-3">Anteprima Calcolo</h5>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-slate-600">Prezzo Pubblico:</span>
                      <span className="font-medium">€ {calcoloPrezzoNetto.prezzoBase.toFixed(2)}</span>
                    </div>
                    {formData.prezzo_pubblico_ivato && calcoloPrezzoNetto.ivaScorporata > 0 && (
                      <div className="flex justify-between text-amber-700">
                        <span>- IVA scorporata ({formData.aliquota_iva}%):</span>
                        <span>€ {calcoloPrezzoNetto.ivaScorporata.toFixed(2)}</span>
                      </div>
                    )}
                    <div className="flex justify-between">
                      <span className="text-slate-600">= Prezzo senza IVA:</span>
                      <span className="font-medium">€ {calcoloPrezzoNetto.prezzoSenzaIva.toFixed(2)}</span>
                    </div>
                    {calcoloPrezzoNetto.scontoTotale > 0 && (
                      <div className="flex justify-between text-blue-700">
                        <span>- Sconti applicati:</span>
                        <span>€ {calcoloPrezzoNetto.scontoTotale.toFixed(2)}</span>
                      </div>
                    )}
                    <div className="flex justify-between pt-2 border-t border-green-400">
                      <span className="font-bold text-green-800">= PREZZO NETTO:</span>
                      <span className="font-bold text-green-800 text-lg">€ {calcoloPrezzoNetto.prezzoNetto.toFixed(2)}</span>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={applicaPrezzoCalcolato}
                    className="mt-3 w-full px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm font-medium"
                  >
                    Applica questo prezzo
                  </button>
                </div>
              )}
            </>
          )}

          {/* Sezione Sconti (solo in modalità diretta) */}
          {modalitaInserimento === 'diretto' && (
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
          )}

          {/* Sezione IVA e Date (solo in modalità diretta) */}
          {modalitaInserimento === 'diretto' && (
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Aliquota IVA %</label>
                <select
                  value={formData.aliquota_iva}
                  onChange={(e) => handleChange('aliquota_iva', e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  {ALIQUOTE_IVA.map(opt => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Scorporo IVA</label>
                <select
                  value={formData.scorporo_iva}
                  onChange={(e) => handleChange('scorporo_iva', e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="S">S - Netto (no scorporo)</option>
                  <option value="N">N - IVA inclusa (scorporare)</option>
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
          )}

          {/* Data decorrenza in modalità calcolata */}
          {modalitaInserimento === 'calcolato' && (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Scorporo IVA (tracciato)</label>
                <select
                  value={formData.scorporo_iva}
                  onChange={(e) => handleChange('scorporo_iva', e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                >
                  <option value="S">S - Netto (no scorporo)</option>
                  <option value="N">N - IVA inclusa (scorporare)</option>
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
          )}

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

          {/* Checkbox listino - disabilitato per operatore */}
          <div className={`p-4 rounded-lg border ${scope === 'operatore' ? 'bg-slate-50 border-slate-200 opacity-60' : 'bg-amber-50 border-amber-200'}`}>
            <label className={`flex items-center gap-3 ${scope === 'operatore' ? 'cursor-not-allowed' : 'cursor-pointer'}`}>
              <input
                type="checkbox"
                checked={formData.applica_a_listino}
                onChange={(e) => handleChange('applica_a_listino', e.target.checked)}
                disabled={scope === 'operatore'}
                className="w-5 h-5 rounded border-slate-300 text-blue-600 focus:ring-blue-500 disabled:opacity-50"
              />
              <div>
                <span className="text-sm font-medium text-amber-800">Aggiungi al listino vendor</span>
                <p className="text-xs text-amber-600">Se attivo, il prodotto verra aggiunto al listino per utilizzo futuro</p>
              </div>
            </label>
          </div>
        </div>
      )}
    </ModalBase>
  );
};

export default CorrezioneLisinoModal;
