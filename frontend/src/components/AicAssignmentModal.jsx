// =============================================================================
// SERV.O v11.0 - UNIFIED AIC ASSIGNMENT MODAL
// =============================================================================
// Componente unificato per assegnazione codice AIC da:
// - AnomaliaDetailModal (mode: ANOMALIA)
// - SupervisionePage singola (mode: SUPERVISIONE_SINGOLA)
// - SupervisionePage bulk (mode: SUPERVISIONE_BULK)
//
// TIER 2.1: Unifica AicCorrectionSection e AssegnaAicModal
// =============================================================================

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { ModalBase } from '../common/ModalBase';
import { Button, Loading, PdfViewerButton } from '../common';
import { anomalieApi } from '../api/anomalie';
import { supervisioneApi, ordiniApi } from '../api';

/**
 * Modalità operative del componente
 */
export const AIC_MODAL_MODES = {
  ANOMALIA: 'ANOMALIA',                    // Correzione AIC da anomalia
  SUPERVISIONE_SINGOLA: 'SUPERVISIONE_SINGOLA', // Supervisione AIC singola
  SUPERVISIONE_BULK: 'SUPERVISIONE_BULK',  // Supervisione AIC bulk per pattern
};

/**
 * Livelli di propagazione
 */
export const PROPAGATION_LEVELS = {
  ORDINE: 'ORDINE',
  GLOBALE: 'GLOBALE',
};

/**
 * AicAssignmentModal - Componente unificato per assegnazione AIC
 *
 * @param {Object} props
 * @param {boolean} props.isOpen - Stato apertura modale
 * @param {Function} props.onClose - Handler chiusura
 * @param {string} props.mode - Modalità: ANOMALIA | SUPERVISIONE_SINGOLA | SUPERVISIONE_BULK
 * @param {Object} props.anomalia - Dati anomalia (per mode ANOMALIA)
 * @param {Object} props.rigaParent - Dati riga ordine (per mode ANOMALIA)
 * @param {Object} props.supervisione - Dati supervisione (per mode SUPERVISIONE_*)
 * @param {string} props.operatore - Username operatore (override)
 * @param {Function} props.onSuccess - Callback successo con risultato
 */
const AicAssignmentModal = ({
  isOpen,
  onClose,
  mode = AIC_MODAL_MODES.SUPERVISIONE_SINGOLA,
  anomalia = null,
  rigaParent = null,
  supervisione = null,
  operatore: operatoreOverride = null,
  onSuccess,
}) => {
  // ==========================================================================
  // STATE
  // ==========================================================================

  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  // Form state
  const [codiceAic, setCodiceAic] = useState('');
  const [livelloPropagazione, setLivelloPropagazione] = useState('ORDINE');
  const [note, setNote] = useState('');

  // Search state
  const [searchQuery, setSearchQuery] = useState('');
  const [suggerimenti, setSuggerimenti] = useState([]);
  const [searchLoading, setSearchLoading] = useState(false);

  // Dettaglio supervisione (caricato dinamicamente)
  const [detail, setDetail] = useState(null);

  // v11.4: PDF file per visualizzazione
  const [pdfFile, setPdfFile] = useState(null);

  // ==========================================================================
  // COMPUTED VALUES
  // ==========================================================================

  const isBulk = mode === AIC_MODAL_MODES.SUPERVISIONE_BULK;
  const isAnomalia = mode === AIC_MODAL_MODES.ANOMALIA;
  const isSupervisione = mode.startsWith('SUPERVISIONE');

  // Recupera operatore e ruolo dal localStorage
  const { operatore, isSupervisor } = useMemo(() => {
    if (operatoreOverride) {
      return { operatore: operatoreOverride, isSupervisor: true };
    }
    try {
      const user = JSON.parse(localStorage.getItem('servo_user') || '{}');
      const ruolo = (user.ruolo || '').toLowerCase();
      const canGlobal = ['admin', 'supervisore', 'supervisor', 'superuser'].includes(ruolo);
      return {
        operatore: user.username || 'operatore',
        isSupervisor: canGlobal,
      };
    } catch {
      return { operatore: 'operatore', isSupervisor: false };
    }
  }, [operatoreOverride]);

  // Dati prodotto (unificati da anomalia/supervisione)
  const prodottoData = useMemo(() => {
    if (isAnomalia && rigaParent) {
      return {
        descrizione: rigaParent.descrizione || '',
        codiceOriginale: rigaParent.codice_originale || rigaParent.codice_aic || '',
        vendor: anomalia?.vendor || '',
        nRiga: rigaParent.n_riga || '',
        qVenduta: rigaParent.q_venduta || 0,
        qOmaggio: rigaParent.q_omaggio || 0,
        qScontoMerce: rigaParent.q_sconto_merce || 0,
        prezzoNetto: rigaParent.prezzo_netto || 0,
      };
    }
    if (isSupervisione) {
      const source = detail || supervisione;
      return {
        descrizione: source?.descrizione_prodotto || source?.descrizione_normalizzata || '',
        codiceOriginale: source?.codice_originale || '',
        vendor: source?.vendor || '',
        nRiga: source?.n_riga || '',
        qVenduta: source?.q_venduta || 0,
        qOmaggio: source?.q_omaggio || 0,
        qScontoMerce: source?.q_sconto_merce || 0,
        prezzoNetto: source?.prezzo_netto || 0,
      };
    }
    return null;
  }, [isAnomalia, rigaParent, anomalia, isSupervisione, detail, supervisione]);

  // ==========================================================================
  // EFFECTS
  // ==========================================================================

  // Reset state quando il modal si apre/chiude
  useEffect(() => {
    if (!isOpen) {
      setDetail(null);
      setCodiceAic('');
      setLivelloPropagazione(isSupervisor ? 'GLOBALE' : 'ORDINE');
      setNote('');
      setSearchQuery('');
      setSuggerimenti([]);
      setError(null);
      setResult(null);
      setPdfFile(null);
      return;
    }

    // v11.4: Helper per caricare pdf_file dalla testata
    const loadPdfFile = async (idTestata) => {
      if (!idTestata) return;
      try {
        const ordineRes = await ordiniApi.getOrdine(idTestata);
        // v11.4 fix: ordineRes è { success, data: {...ordine} }
        setPdfFile(ordineRes?.data?.pdf_file || null);
      } catch (e) {
        console.warn('Impossibile caricare pdf_file:', e);
      }
    };

    // Per bulk, usa i dati già presenti
    if (isBulk && supervisione) {
      setLoading(false);
      setDetail({
        ...supervisione,
        descrizione_prodotto: supervisione.descrizione_prodotto || supervisione.descrizione_normalizzata || '',
      });
      setSearchQuery(supervisione.descrizione_prodotto || supervisione.descrizione_normalizzata || '');
      loadPdfFile(supervisione?.id_testata);
      return;
    }

    // Per supervisione singola, carica dettaglio
    if (isSupervisione && supervisione?.id_supervisione) {
      const loadDetail = async () => {
        setLoading(true);
        try {
          const data = await supervisioneApi.getAicDetail(supervisione.id_supervisione);
          setDetail(data);
          const desc = data.descrizione_prodotto || data.descrizione_normalizzata || '';
          setSearchQuery(desc);
          if (data.suggerimenti_aic?.length > 0) {
            setSuggerimenti(data.suggerimenti_aic);
          }
          // v11.4: Carica pdf_file
          await loadPdfFile(data?.id_testata || supervisione?.id_testata);
        } catch (err) {
          console.error('Errore caricamento dettaglio AIC:', err);
          setError('Impossibile caricare i dettagli della supervisione');
        } finally {
          setLoading(false);
        }
      };
      loadDetail();
      return;
    }

    // Per anomalia, pre-popola ricerca
    if (isAnomalia && rigaParent) {
      setSearchQuery(rigaParent.descrizione || '');
      loadPdfFile(anomalia?.id_testata);
    }
  }, [isOpen, isBulk, isSupervisione, isAnomalia, supervisione, rigaParent, anomalia, isSupervisor]);

  // ==========================================================================
  // HANDLERS
  // ==========================================================================

  // Validazione AIC
  const isValidAic = useCallback((code) => {
    return code && code.length === 9 && /^\d{9}$/.test(code);
  }, []);

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
        prodottoData?.vendor || ''
      );
      setSuggerimenti(result.suggerimenti || []);
    } catch (err) {
      console.error('Errore ricerca AIC:', err);
    } finally {
      setSearchLoading(false);
    }
  }, [searchQuery, prodottoData?.vendor]);

  // Seleziona suggerimento
  const handleSelectSuggerimento = useCallback((sug) => {
    setCodiceAic(sug.codice_aic);
  }, []);

  // Submit
  const handleSubmit = async () => {
    if (!isValidAic(codiceAic)) {
      setError('Il codice AIC deve essere composto da 9 cifre');
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      let response;

      if (isAnomalia) {
        // Correzione AIC da anomalia
        response = await anomalieApi.correggiAic(anomalia.id_anomalia, {
          codice_aic: codiceAic,
          livello_propagazione: livelloPropagazione,
          operatore,
          note: note || undefined,
        });
      } else if (isBulk) {
        // Approvazione bulk per pattern
        response = await supervisioneApi.approvaBulkAic(
          supervisione.pattern_signature,
          operatore,
          codiceAic,
          note || undefined
        );
      } else {
        // Supervisione singola
        response = await supervisioneApi.risolviAic(
          supervisione.id_supervisione,
          operatore,
          codiceAic,
          livelloPropagazione,
          note || undefined
        );
      }

      if (response.success || response.approvata) {
        setResult(response);

        // Costruisci messaggio di successo
        // v11.0: response è già il data object (API fa .then(r => r.data))
        const successMessage = isBulk
          ? `AIC ${codiceAic} assegnato a ${response.supervisioni_approvate || 0} supervisioni. Righe: ${response.righe_aggiornate || 0}`
          : `AIC ${codiceAic} assegnato. Righe aggiornate: ${response.righe_aggiornate || 0}`;

        // Attendi per mostrare il risultato
        setTimeout(() => {
          onSuccess?.({
            ...response,
            codice_aic: codiceAic,
            message: successMessage,
          });
          onClose?.();
        }, 1500);
      } else {
        setError(response.error || 'Errore durante assegnazione AIC');
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Errore durante assegnazione AIC');
    } finally {
      setSubmitting(false);
    }
  };

  // ==========================================================================
  // RENDER HELPERS
  // ==========================================================================

  // Titolo e sottotitolo basati su mode
  const { title, subtitle, variant } = useMemo(() => {
    if (isBulk) {
      return {
        title: 'Assegna AIC - Pattern Bulk',
        subtitle: `${supervisione?.total_count || 0} supervisioni con stesso pattern`,
        variant: 'primary',
      };
    }
    if (isAnomalia) {
      return {
        title: 'Correzione Codice AIC',
        subtitle: 'Anomalia AIC-A01 - Codice mancante o non valido',
        variant: 'warning',
      };
    }
    return {
      title: 'Assegna Codice AIC',
      subtitle: 'Anomalia AIC-A01 - Codice mancante',
      variant: 'default',
    };
  }, [isBulk, isAnomalia, supervisione]);

  // Opzioni livello propagazione
  const propagationOptions = useMemo(() => {
    const options = [
      {
        value: PROPAGATION_LEVELS.ORDINE,
        label: 'Intero ordine',
        desc: 'Tutte le righe con stessa descrizione in questo ordine',
      },
    ];

    // GLOBALE solo per supervisori
    if (isSupervisor) {
      options.push({
        value: PROPAGATION_LEVELS.GLOBALE,
        label: 'Globale (Supervisore)',
        desc: 'Tutte le righe nel database con stessa descrizione',
      });
    }

    return options;
  }, [isSupervisor]);

  // ==========================================================================
  // RENDER
  // ==========================================================================

  return (
    <ModalBase
      isOpen={isOpen}
      onClose={onClose}
      title={title}
      subtitle={subtitle}
      size="lg"
      variant={variant}
      headerActions={<PdfViewerButton pdfFile={pdfFile} variant="compact" />}
    >
      {loading ? (
        <Loading text="Caricamento dettagli..." />
      ) : error && !prodottoData ? (
        <div className="text-center py-8">
          <div className="text-4xl mb-3">⚠️</div>
          <p className="text-red-600">{error}</p>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Info ordine/pattern/anomalia */}
          <InfoSection
            mode={mode}
            isBulk={isBulk}
            isAnomalia={isAnomalia}
            anomalia={anomalia}
            supervisione={supervisione}
            detail={detail}
          />

          {/* Prodotto senza AIC */}
          {prodottoData && (
            <ProductSection prodotto={prodottoData} isAnomalia={isAnomalia} />
          )}

          {/* Pattern ML info (se disponibile) */}
          {detail?.pattern_info && (
            <PatternMLSection
              patternInfo={detail.pattern_info}
              onUseDefault={() => setCodiceAic(detail.pattern_info.codice_aic_default)}
            />
          )}

          {/* Risultato successo */}
          {result && (
            <SuccessResult
              result={result}
              codiceAic={codiceAic}
              isBulk={isBulk}
            />
          )}

          {/* Form (nascosto se c'è un risultato) */}
          {!result && (
            <>
              {/* Ricerca AIC */}
              <SearchAicSection
                searchQuery={searchQuery}
                setSearchQuery={setSearchQuery}
                searchLoading={searchLoading}
                onSearch={handleSearch}
                suggerimenti={suggerimenti}
                codiceAic={codiceAic}
                onSelectSuggerimento={handleSelectSuggerimento}
              />

              {/* Input AIC */}
              <AicInputSection
                codiceAic={codiceAic}
                setCodiceAic={setCodiceAic}
                isValidAic={isValidAic}
              />

              {/* Livello propagazione (non per bulk) */}
              {!isBulk && (
                <PropagationSection
                  livelloPropagazione={livelloPropagazione}
                  setLivelloPropagazione={setLivelloPropagazione}
                  options={propagationOptions}
                  isSupervisor={isSupervisor}
                />
              )}

              {/* Note */}
              <NoteSection note={note} setNote={setNote} />

              {/* Errore */}
              {error && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                  <p className="text-sm text-red-700">{error}</p>
                </div>
              )}

              {/* Info propagazione */}
              <PropagationInfo isBulk={isBulk} totalCount={supervisione?.total_count} />

              {/* Footer actions */}
              <div className="flex justify-end gap-3 pt-4 border-t border-slate-200">
                <Button variant="secondary" onClick={onClose} disabled={submitting}>
                  Annulla
                </Button>
                <Button
                  variant={isBulk ? 'success' : isAnomalia ? 'warning' : 'primary'}
                  onClick={handleSubmit}
                  loading={submitting}
                  disabled={!isValidAic(codiceAic) || loading}
                >
                  {isBulk
                    ? `Assegna a ${supervisione?.total_count || 0} supervisioni`
                    : isAnomalia
                    ? 'Correggi AIC'
                    : 'Assegna AIC'}
                </Button>
              </div>
            </>
          )}
        </div>
      )}
    </ModalBase>
  );
};

// =============================================================================
// SUB-COMPONENTS
// =============================================================================

/**
 * Sezione info ordine/pattern/anomalia
 */
function InfoSection({ mode, isBulk, isAnomalia, anomalia, supervisione, detail }) {
  const bgClass = isBulk ? 'bg-indigo-50' : isAnomalia ? 'bg-amber-50' : 'bg-slate-50';

  return (
    <div className={`rounded-xl p-4 ${bgClass}`}>
      <h3 className="text-sm font-medium text-slate-700 mb-3">
        {isBulk ? 'Dettagli Pattern' : isAnomalia ? 'Dettagli Anomalia' : 'Dettagli Ordine'}
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
              <span className="ml-2 font-medium">{supervisione?.vendor || 'N/A'}</span>
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
      ) : isAnomalia ? (
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-slate-500">Anomalia:</span>
            <span className="ml-2 font-mono font-medium text-amber-700">
              #{anomalia?.id_anomalia}
            </span>
          </div>
          <div>
            <span className="text-slate-500">Codice:</span>
            <span className="ml-2 font-mono">{anomalia?.codice_anomalia || 'AIC-A01'}</span>
          </div>
          <div>
            <span className="text-slate-500">Ordine:</span>
            <span className="ml-2 font-medium">#{anomalia?.numero_ordine || anomalia?.id_testata}</span>
          </div>
          <div>
            <span className="text-slate-500">Vendor:</span>
            <span className="ml-2 font-medium">{anomalia?.vendor || 'N/A'}</span>
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
  );
}

/**
 * Sezione prodotto senza AIC
 */
function ProductSection({ prodotto, isAnomalia }) {
  return (
    <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
      <h3 className="text-sm font-medium text-amber-800 mb-2">
        Prodotto senza AIC
      </h3>
      <p className="text-lg font-medium text-slate-800 uppercase">
        {prodotto.descrizione || 'N/A'}
      </p>
      {prodotto.codiceOriginale && (
        <p className="text-sm text-slate-600 mt-1">
          Codice originale:{' '}
          <code className={`bg-slate-200 px-1 rounded ${isAnomalia ? 'text-red-600' : ''}`}>
            {prodotto.codiceOriginale || 'MANCANTE'}
          </code>
        </p>
      )}
      {/* Griglia quantità e prezzo */}
      <div className="grid grid-cols-4 gap-3 mt-3 pt-3 border-t border-amber-200 text-sm">
        <div>
          <span className="text-slate-500">Q.Venduta:</span>
          <span className="ml-1 font-medium">{prodotto.qVenduta || 0}</span>
        </div>
        <div>
          <span className="text-slate-500">Q.Omaggio:</span>
          <span className="ml-1 font-medium text-green-600">{prodotto.qOmaggio || 0}</span>
        </div>
        <div>
          <span className="text-slate-500">Q.Sc.Merce:</span>
          <span className="ml-1 font-medium text-amber-600">{prodotto.qScontoMerce || 0}</span>
        </div>
        <div>
          <span className="text-slate-500">Prezzo:</span>
          <span className="ml-1 font-medium">
            {parseFloat(prodotto.prezzoNetto || 0).toFixed(2)}€
          </span>
        </div>
      </div>
    </div>
  );
}

/**
 * Sezione Pattern ML
 */
function PatternMLSection({ patternInfo, onUseDefault }) {
  return (
    <div className="bg-purple-50 border border-purple-200 rounded-xl p-4">
      <h3 className="text-sm font-medium text-purple-800 mb-2">Pattern ML</h3>
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <span className="text-sm text-purple-700">Approvazioni:</span>
          <span className="font-bold">{patternInfo.count_approvazioni || 0}/5</span>
        </div>
        {patternInfo.is_ordinario && (
          <span className="px-2 py-1 text-xs bg-emerald-100 text-emerald-700 rounded-full">
            AUTOMATICO
          </span>
        )}
        {patternInfo.codice_aic_default && (
          <div className="text-sm">
            <span className="text-purple-700">AIC default:</span>
            <code className="ml-1 bg-purple-100 px-2 py-0.5 rounded font-mono">
              {patternInfo.codice_aic_default}
            </code>
            <button
              onClick={onUseDefault}
              className="ml-2 text-xs text-purple-600 hover:text-purple-800 underline"
            >
              Usa questo
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Sezione ricerca AIC
 */
function SearchAicSection({
  searchQuery,
  setSearchQuery,
  searchLoading,
  onSearch,
  suggerimenti,
  codiceAic,
  onSelectSuggerimento,
}) {
  return (
    <div>
      <h3 className="text-sm font-medium text-slate-700 mb-2">Cerca Codice AIC</h3>
      <div className="flex gap-2">
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && onSearch()}
          placeholder="Cerca per descrizione prodotto..."
          className="flex-1 px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-teal-500 focus:border-teal-500"
        />
        <Button
          variant="secondary"
          onClick={onSearch}
          loading={searchLoading}
          disabled={searchQuery.length < 3}
        >
          Cerca
        </Button>
      </div>

      {/* Suggerimenti */}
      {suggerimenti.length > 0 && (
        <div className="mt-3 border border-slate-200 rounded-xl overflow-hidden">
          <div className="px-4 py-2 bg-slate-50 border-b border-slate-200">
            <span className="text-sm font-medium text-slate-700">
              Suggerimenti ({suggerimenti.length})
            </span>
          </div>
          <div className="max-h-48 overflow-y-auto divide-y divide-slate-100">
            {suggerimenti.map((sug, idx) => (
              <button
                key={idx}
                onClick={() => onSelectSuggerimento(sug)}
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
                    <span className="text-sm text-slate-700 uppercase">{sug.descrizione}</span>
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
    </div>
  );
}

/**
 * Sezione input AIC
 */
function AicInputSection({ codiceAic, setCodiceAic, isValidAic }) {
  return (
    <div>
      <label className="block text-sm font-medium text-slate-700 mb-2">
        Codice AIC (9 cifre) *
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
  );
}

/**
 * Sezione livello propagazione
 */
function PropagationSection({
  livelloPropagazione,
  setLivelloPropagazione,
  options,
  isSupervisor,
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-slate-700 mb-2">
        Livello Propagazione
      </label>
      <div className="space-y-2">
        {options.map((opt) => (
          <label
            key={opt.value}
            className={`flex items-start gap-3 p-3 rounded border cursor-pointer transition-colors ${
              livelloPropagazione === opt.value
                ? 'border-teal-500 bg-teal-100'
                : 'border-slate-200 bg-white hover:bg-slate-50'
            }`}
          >
            <input
              type="radio"
              name="livello"
              value={opt.value}
              checked={livelloPropagazione === opt.value}
              onChange={(e) => setLivelloPropagazione(e.target.value)}
              className="mt-1"
            />
            <div>
              <div className="font-medium text-sm">{opt.label}</div>
              <div className="text-xs text-slate-500">{opt.desc}</div>
            </div>
          </label>
        ))}
      </div>
      {!isSupervisor && (
        <p className="mt-2 text-xs text-amber-600">
          Nota: L'opzione "Globale" è disponibile solo per supervisori.
        </p>
      )}
    </div>
  );
}

/**
 * Sezione note
 */
function NoteSection({ note, setNote }) {
  return (
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
  );
}

/**
 * Info propagazione
 */
function PropagationInfo({ isBulk, totalCount }) {
  return (
    <div
      className={`border rounded-lg p-3 ${
        isBulk ? 'bg-indigo-50 border-indigo-200' : 'bg-blue-50 border-blue-200'
      }`}
    >
      <p className={`text-sm ${isBulk ? 'text-indigo-700' : 'text-blue-700'}`}>
        {isBulk ? (
          <>
            <strong>Approvazione Bulk:</strong> Il codice AIC verrà assegnato a tutte le{' '}
            <strong>{totalCount || 0}</strong> supervisioni del pattern. Tutte le righe ordine
            correlate saranno aggiornate e gli ordini sbloccati.
          </>
        ) : (
          <>
            <strong>Nota:</strong> Il codice AIC verrà propagato automaticamente a tutte le righe
            con la stessa descrizione prodotto e vendor. Questo contribuirà all'apprendimento ML.
          </>
        )}
      </p>
    </div>
  );
}

/**
 * Risultato successo
 */
function SuccessResult({ result, codiceAic, isBulk }) {
  return (
    <div className="bg-green-100 border border-green-300 rounded-xl p-4">
      <div className="flex items-center gap-2 text-green-800 font-medium mb-2">
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M5 13l4 4L19 7"
          />
        </svg>
        AIC Assegnato con Successo
      </div>
      <div className="text-sm text-green-700 space-y-1">
        <p>
          Codice AIC: <span className="font-mono font-bold">{codiceAic}</span>
        </p>
        <p>
          Righe aggiornate: <span className="font-bold">{result.righe_aggiornate || 0}</span>
        </p>
        {isBulk && (
          <p>
            Supervisioni approvate:{' '}
            <span className="font-bold">{result.supervisioni_approvate || 0}</span>
          </p>
        )}
        <p>
          Ordini coinvolti:{' '}
          <span className="font-bold">{result.ordini_coinvolti?.length || 0}</span>
        </p>
      </div>
    </div>
  );
}

export default AicAssignmentModal;
export { AicAssignmentModal };
