// =============================================================================
// SERV.O v9.0 - ASSEGNA AIC MODAL
// =============================================================================
// Modale per assegnazione codice AIC a prodotti con anomalia AIC-A01
// =============================================================================

import React, { useState, useEffect, useCallback } from 'react';
import { Button, Loading } from '../../common';
import { supervisioneApi } from '../../api';

/**
 * Modale per assegnare codice AIC a supervisione
 *
 * @param {Object} props
 * @param {boolean} props.isOpen - Se la modale è aperta
 * @param {Function} props.onClose - Callback chiusura
 * @param {Object} props.supervisione - Dati supervisione AIC
 * @param {string} props.operatore - Username operatore
 * @param {Function} props.onSuccess - Callback successo
 */
const AssegnaAicModal = ({
  isOpen,
  onClose,
  supervisione,
  operatore,
  onSuccess
}) => {
  // State
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [detail, setDetail] = useState(null);
  const [codiceAic, setCodiceAic] = useState('');
  const [note, setNote] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [suggerimenti, setSuggerimenti] = useState([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [error, setError] = useState(null);

  // Flag per modalità bulk
  const isBulk = supervisione?.is_bulk || false;

  // Carica dettaglio supervisione
  useEffect(() => {
    if (!isOpen) {
      setDetail(null);
      setCodiceAic('');
      setNote('');
      setSearchQuery('');
      setSuggerimenti([]);
      setError(null);
      return;
    }

    // Per modalità bulk, usa i dati già presenti nella supervisione
    if (isBulk) {
      setLoading(false);
      setDetail({
        ...supervisione,
        descrizione_prodotto: supervisione.descrizione_prodotto || supervisione.descrizione_normalizzata || ''
      });
      setSearchQuery(supervisione.descrizione_prodotto || supervisione.descrizione_normalizzata || '');
      return;
    }

    // Per singola supervisione, carica dettaglio
    if (!supervisione?.id_supervisione) {
      setDetail(null);
      return;
    }

    const loadDetail = async () => {
      setLoading(true);
      try {
        const data = await supervisioneApi.getAicDetail(supervisione.id_supervisione);
        setDetail(data);

        // Pre-popola ricerca con descrizione prodotto
        const desc = data.descrizione_prodotto || data.descrizione_normalizzata || '';
        setSearchQuery(desc);

        // Carica suggerimenti iniziali
        if (data.suggerimenti_aic?.length > 0) {
          setSuggerimenti(data.suggerimenti_aic);
        }
      } catch (err) {
        console.error('Errore caricamento dettaglio AIC:', err);
        setError('Impossibile caricare i dettagli della supervisione');
      } finally {
        setLoading(false);
      }
    };

    loadDetail();
  }, [isOpen, supervisione?.id_supervisione, isBulk]);

  // Cerca suggerimenti AIC
  const handleSearch = useCallback(async () => {
    if (!searchQuery || searchQuery.length < 3) {
      setSuggerimenti([]);
      return;
    }

    setSearchLoading(true);
    try {
      const result = await supervisioneApi.searchAic(
        searchQuery,
        detail?.vendor || supervisione?.vendor
      );
      setSuggerimenti(result.suggerimenti || []);
    } catch (err) {
      console.error('Errore ricerca AIC:', err);
    } finally {
      setSearchLoading(false);
    }
  }, [searchQuery, detail?.vendor, supervisione?.vendor]);

  // Seleziona suggerimento
  const handleSelectSuggerimento = (sug) => {
    setCodiceAic(sug.codice_aic);
  };

  // Valida codice AIC
  const isValidAic = (code) => {
    return code && code.length === 9 && /^\d{9}$/.test(code);
  };

  // Submit
  const handleSubmit = async () => {
    if (!isValidAic(codiceAic)) {
      setError('Il codice AIC deve essere composto da 9 cifre');
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      let result;

      if (isBulk) {
        // Approvazione bulk per pattern
        result = await supervisioneApi.approvaBulkAic(
          supervisione.pattern_signature,
          operatore,
          codiceAic,
          note || undefined
        );

        if (result.success) {
          onSuccess?.({
            ...result,
            message: `AIC ${codiceAic} assegnato a ${result.supervisioni_approvate} supervisioni. ` +
                     `Righe aggiornate: ${result.righe_aggiornate}, Ordini: ${result.ordini_coinvolti?.length || 0}`
          });
          onClose();
        } else {
          setError(result.error || 'Errore durante assegnazione bulk');
        }
      } else {
        // Approvazione singola
        result = await supervisioneApi.risolviAic(
          supervisione.id_supervisione,
          operatore,
          codiceAic,
          note || undefined
        );

        if (result.success) {
          onSuccess?.({
            ...result,
            message: `AIC ${codiceAic} assegnato. Righe propagate: ${result.righe_propagate || 0}`
          });
          onClose();
        } else {
          setError(result.error || 'Errore durante assegnazione');
        }
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Errore durante assegnazione');
    } finally {
      setSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Overlay */}
      <div
        className="fixed inset-0 bg-black/50 transition-opacity"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div
          className="relative w-full max-w-2xl bg-white rounded-2xl shadow-2xl transform transition-all"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className={`px-6 py-4 border-b border-slate-200 rounded-t-2xl ${
            isBulk ? 'bg-gradient-to-r from-indigo-50 to-purple-50' : 'bg-gradient-to-r from-teal-50 to-cyan-50'
          }`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className={`w-10 h-10 rounded-xl flex items-center justify-center text-white text-lg ${
                  isBulk ? 'bg-indigo-600' : 'bg-teal-600'
                }`}>
                  {isBulk ? '🎯' : '🔬'}
                </div>
                <div>
                  <h2 className="text-lg font-semibold text-slate-800">
                    {isBulk ? 'Assegna AIC - Pattern Bulk' : 'Assegna Codice AIC'}
                  </h2>
                  <p className="text-sm text-slate-600">
                    {isBulk
                      ? `${supervisione?.total_count || 0} supervisioni con stesso pattern`
                      : 'Anomalia AIC-A01 - Codice mancante'}
                  </p>
                </div>
              </div>
              <button
                onClick={onClose}
                className="p-2 hover:bg-slate-200 rounded-lg transition-colors"
              >
                <span className="text-xl text-slate-500">&times;</span>
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="p-6">
            {loading ? (
              <Loading text="Caricamento dettagli..." />
            ) : error && !detail ? (
              <div className="text-center py-8">
                <div className="text-4xl mb-3">⚠️</div>
                <p className="text-red-600">{error}</p>
              </div>
            ) : (
              <div className="space-y-6">
                {/* Info ordine/pattern */}
                <div className={`rounded-xl p-4 ${isBulk ? 'bg-indigo-50' : 'bg-slate-50'}`}>
                  <h3 className="text-sm font-medium text-slate-700 mb-3">
                    {isBulk ? 'Dettagli Pattern' : 'Dettagli Ordine'}
                  </h3>
                  {isBulk ? (
                    <div className="space-y-3">
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <span className="text-slate-500">Supervisioni:</span>
                          <span className="ml-2 font-bold text-indigo-700">
                            {supervisione?.total_count || 0}
                          </span>
                        </div>
                        <div>
                          <span className="text-slate-500">Ordini coinvolti:</span>
                          <span className="ml-2 font-bold text-indigo-700">
                            {supervisione?.affected_order_ids?.length || 0}
                          </span>
                        </div>
                        <div>
                          <span className="text-slate-500">Vendor:</span>
                          <span className="ml-2 font-medium">
                            {supervisione?.vendor || 'N/A'}
                          </span>
                        </div>
                        <div>
                          <span className="text-slate-500">Pattern:</span>
                          <code className="ml-2 text-xs bg-slate-200 px-1 rounded">
                            {supervisione?.pattern_signature?.substring(0, 12)}...
                          </code>
                        </div>
                      </div>
                      <div className="text-xs text-slate-600 bg-white/50 p-2 rounded">
                        <strong>Ordini:</strong> {supervisione?.affected_order_ids?.join(', ') || 'N/A'}
                      </div>
                    </div>
                  ) : (
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-slate-500">Ordine:</span>
                        <span className="ml-2 font-medium">
                          #{detail?.numero_ordine_vendor || supervisione?.numero_ordine}
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-500">Vendor:</span>
                        <span className="ml-2 font-medium">
                          {detail?.vendor || supervisione?.vendor || 'N/A'}
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-500">Cliente:</span>
                        <span className="ml-2 font-medium">
                          {(detail?.ragione_sociale_1 || supervisione?.ragione_sociale)?.toUpperCase() || 'N/A'}
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-500">Riga:</span>
                        <span className="ml-2 font-medium">
                          {detail?.n_riga || supervisione?.n_riga || 'N/A'}
                        </span>
                      </div>
                    </div>
                  )}
                </div>

                {/* Prodotto senza AIC */}
                <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
                  <h3 className="text-sm font-medium text-amber-800 mb-2">
                    Prodotto senza AIC
                  </h3>
                  <p className="text-lg font-medium text-slate-800 uppercase">
                    {detail?.descrizione_prodotto || detail?.descrizione_normalizzata || supervisione?.descrizione_prodotto || 'N/A'}
                  </p>
                  {detail?.codice_originale && (
                    <p className="text-sm text-slate-600 mt-1">
                      Codice originale: <code className="bg-slate-200 px-1 rounded">{detail.codice_originale}</code>
                    </p>
                  )}
                  {detail?.q_venduta && (
                    <p className="text-sm text-slate-600 mt-1">
                      Quantita: {detail.q_venduta} pz
                      {detail?.prezzo_netto && ` - Netto: €${detail.prezzo_netto}`}
                    </p>
                  )}
                </div>

                {/* Pattern info */}
                {detail?.pattern_info && (
                  <div className="bg-purple-50 border border-purple-200 rounded-xl p-4">
                    <h3 className="text-sm font-medium text-purple-800 mb-2">
                      Pattern ML
                    </h3>
                    <div className="flex items-center gap-4">
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-purple-700">Approvazioni:</span>
                        <span className="font-bold">{detail.pattern_info.count_approvazioni || 0}/5</span>
                      </div>
                      {detail.pattern_info.is_ordinario && (
                        <span className="px-2 py-1 text-xs bg-emerald-100 text-emerald-700 rounded-full">
                          AUTOMATICO
                        </span>
                      )}
                      {detail.pattern_info.codice_aic_default && (
                        <div className="text-sm">
                          <span className="text-purple-700">AIC default:</span>
                          <code className="ml-1 bg-purple-100 px-2 py-0.5 rounded font-mono">
                            {detail.pattern_info.codice_aic_default}
                          </code>
                          <button
                            onClick={() => setCodiceAic(detail.pattern_info.codice_aic_default)}
                            className="ml-2 text-xs text-purple-600 hover:text-purple-800 underline"
                          >
                            Usa questo
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Ricerca AIC */}
                <div>
                  <h3 className="text-sm font-medium text-slate-700 mb-2">
                    Cerca Codice AIC
                  </h3>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                      placeholder="Cerca per descrizione prodotto..."
                      className="flex-1 px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
                    />
                    <Button
                      variant="secondary"
                      onClick={handleSearch}
                      loading={searchLoading}
                      disabled={searchQuery.length < 3}
                    >
                      Cerca
                    </Button>
                  </div>
                </div>

                {/* Suggerimenti */}
                {suggerimenti.length > 0 && (
                  <div className="border border-slate-200 rounded-xl overflow-hidden">
                    <div className="px-4 py-2 bg-slate-50 border-b border-slate-200">
                      <span className="text-sm font-medium text-slate-700">
                        Suggerimenti ({suggerimenti.length})
                      </span>
                    </div>
                    <div className="max-h-48 overflow-y-auto divide-y divide-slate-100">
                      {suggerimenti.map((sug, idx) => (
                        <button
                          key={idx}
                          onClick={() => handleSelectSuggerimento(sug)}
                          className={`w-full px-4 py-3 text-left hover:bg-teal-50 transition-colors ${
                            codiceAic === sug.codice_aic ? 'bg-teal-100' : ''
                          }`}
                        >
                          <div className="flex items-center justify-between">
                            <div>
                              <code className="text-sm font-mono font-bold text-teal-700">
                                {sug.codice_aic}
                              </code>
                              <span className="mx-2 text-slate-400">-</span>
                              <span className="text-sm text-slate-700 uppercase">
                                {sug.descrizione}
                              </span>
                            </div>
                            {sug.fonte && (
                              <span className="text-xs text-slate-500 bg-slate-100 px-2 py-0.5 rounded">
                                {sug.fonte}
                              </span>
                            )}
                          </div>
                          {sug.similarity && (
                            <div className="mt-1 text-xs text-slate-500">
                              Match: {Math.round(sug.similarity * 100)}%
                            </div>
                          )}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Input manuale AIC */}
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    Codice AIC (9 cifre)
                  </label>
                  <input
                    type="text"
                    value={codiceAic}
                    onChange={(e) => {
                      const val = e.target.value.replace(/\D/g, '').slice(0, 9);
                      setCodiceAic(val);
                    }}
                    placeholder="Es: 012345678"
                    maxLength={9}
                    className={`w-full px-4 py-3 border rounded-lg font-mono text-lg tracking-wider ${
                      codiceAic.length === 9
                        ? 'border-emerald-500 bg-emerald-50'
                        : 'border-slate-300'
                    } focus:ring-2 focus:ring-teal-500 focus:border-teal-500`}
                  />
                  <div className="mt-1 flex items-center justify-between text-xs">
                    <span className={codiceAic.length === 9 ? 'text-emerald-600' : 'text-slate-500'}>
                      {codiceAic.length}/9 cifre
                    </span>
                    {isValidAic(codiceAic) && (
                      <span className="text-emerald-600 flex items-center gap-1">
                        <span>✓</span> Formato valido
                      </span>
                    )}
                  </div>
                </div>

                {/* Note opzionali */}
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-2">
                    Note (opzionale)
                  </label>
                  <textarea
                    value={note}
                    onChange={(e) => setNote(e.target.value)}
                    placeholder="Eventuali note sull'assegnazione..."
                    rows={2}
                    className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
                  />
                </div>

                {/* Errore */}
                {error && (
                  <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                    <p className="text-sm text-red-700">{error}</p>
                  </div>
                )}

                {/* Info propagazione */}
                <div className={`border rounded-lg p-3 ${isBulk ? 'bg-indigo-50 border-indigo-200' : 'bg-blue-50 border-blue-200'}`}>
                  <p className={`text-sm ${isBulk ? 'text-indigo-700' : 'text-blue-700'}`}>
                    {isBulk ? (
                      <>
                        <strong>Approvazione Bulk:</strong> Il codice AIC verra assegnato a tutte le{' '}
                        <strong>{supervisione?.total_count || 0}</strong> supervisioni del pattern.
                        Tutte le righe ordine correlate saranno aggiornate e gli ordini sbloccati.
                      </>
                    ) : (
                      <>
                        <strong>Nota:</strong> Il codice AIC verra propagato automaticamente a tutte le righe
                        con la stessa descrizione prodotto e vendor. Questo contribuira all'apprendimento ML.
                      </>
                    )}
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="px-6 py-4 border-t border-slate-200 bg-slate-50 rounded-b-2xl flex items-center justify-end gap-3">
            <Button variant="secondary" onClick={onClose} disabled={submitting}>
              Annulla
            </Button>
            <Button
              variant={isBulk ? 'success' : 'primary'}
              onClick={handleSubmit}
              loading={submitting}
              disabled={!isValidAic(codiceAic) || loading}
            >
              {isBulk ? `Assegna AIC a ${supervisione?.total_count || 0} supervisioni` : 'Assegna AIC'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AssegnaAicModal;
