/**
 * AnomaliaDetailModal Component - v11.4 Refactoring
 * Modale dettaglio anomalia con gestione:
 * - ESPOSITORE: parent/child editing
 * - LOOKUP/ANAGRAFICA: ricerca farmacia/parafarmacia + deposito
 * - AIC: correzione codice AIC con propagazione (v11.0 - usa AicAssignmentModal unificato)
 *
 * v11.4: Unificato per operatore E supervisore
 * - Operatore: corregge anomalie singole
 * - Supervisore: stesse azioni + opzione propagazione
 *
 * Usato da DatabasePage, OrdineDetailPage e SupervisionePage
 */
import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { TipoAnomaliaBadge, StatoAnomaliaBadge, SeveritaBadge } from '../common/StatusBadge';
import { lookupApi, getApiBaseUrl } from '../api';
// v8.2: Import diretto per evitare problemi con barrel export
import { anomalieApi } from '../api/anomalie';
// v11.0: Import AicAssignmentModal unificato (TIER 2.1)
import { AicAssignmentModal, AIC_MODAL_MODES } from './AicAssignmentModal';

export function AnomaliaDetailModal({
  isOpen,
  onClose,
  anomaliaDetail,
  loading = false,
  onSaveParent,
  onRisolvi,
  onOpenOrdine,
  onAssignFarmacia,
  // v11.4: Props per supporto Supervisione
  fromSupervisione = false,        // Se true, mostra opzioni supervisore
  supervisione = null,             // Dati supervisione (per propagazione)
  onSupervisioneSuccess = null,    // Callback dopo azione supervisore
}) {
  // v11.4: Determina se utente è supervisore
  const { operatore, isSupervisor } = useMemo(() => {
    try {
      const user = JSON.parse(localStorage.getItem('servo_user') || '{}');
      const ruolo = (user.ruolo || '').toLowerCase();
      const canGlobal = ['admin', 'supervisore', 'supervisor', 'superuser'].includes(ruolo);
      return {
        operatore: user.username || 'operatore',
        isSupervisor: canGlobal
      };
    } catch {
      return { operatore: 'operatore', isSupervisor: false };
    }
  }, []);
  // Stato editing parent (per ESPOSITORE)
  const [isEditingParent, setIsEditingParent] = useState(false);
  const [editingRigaParent, setEditingRigaParent] = useState(null);

  // Stato per LOOKUP
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [selectedResult, setSelectedResult] = useState(null);

  // v11.0: Stato per AIC modal unificato
  const [isAicModalOpen, setIsAicModalOpen] = useState(false);

  // Determina tipo di anomalia
  const isLookupAnomalia = anomaliaDetail?.anomalia?.tipo_anomalia === 'LOOKUP' ||
    anomaliaDetail?.anomalia?.codice_anomalia?.startsWith('LKP-');

  // v8.2: Anomalia AIC (codice mancante o non valido)
  const isAicAnomalia = anomaliaDetail?.anomalia?.codice_anomalia?.startsWith('AIC-') ||
    anomaliaDetail?.anomalia?.tipo_anomalia === 'NO_AIC';

  // v10.5: Anomalia LISTINO/PREZZO
  const isListinoAnomalia = anomaliaDetail?.anomalia?.tipo_anomalia === 'LISTINO' ||
    anomaliaDetail?.anomalia?.tipo_anomalia === 'PREZZO' ||
    anomaliaDetail?.anomalia?.codice_anomalia?.startsWith('LST-') ||
    anomaliaDetail?.anomalia?.codice_anomalia?.startsWith('PRICE-');

  // v10.5: Anomalia ESPOSITORE
  const isEspositoreAnomalia = anomaliaDetail?.anomalia?.tipo_anomalia === 'ESPOSITORE' ||
    anomaliaDetail?.anomalia?.codice_anomalia?.startsWith('ESP-');

  // v8.2: Anomalie ERRORE/CRITICO richiedono azione correttiva
  const isErroreAnomalia = ['ERRORE', 'CRITICO'].includes(
    anomaliaDetail?.anomalia?.livello?.toUpperCase() ||
    anomaliaDetail?.anomalia?.livello_anomalia?.toUpperCase() || ''
  );

  // Reset editing state when modal opens/closes or data changes
  useEffect(() => {
    if (anomaliaDetail?.riga_parent) {
      setEditingRigaParent({
        q_venduta: anomaliaDetail.riga_parent.q_venduta || 0,
        q_sconto_merce: anomaliaDetail.riga_parent.q_sconto_merce || 0,
        q_omaggio: anomaliaDetail.riga_parent.q_omaggio || 0,
        descrizione: anomaliaDetail.riga_parent.descrizione || '',
        codice_originale: anomaliaDetail.riga_parent.codice_originale || '',
        prezzo_netto: anomaliaDetail.riga_parent.prezzo_netto || anomaliaDetail.riga_parent.prezzo_pubblico || 0,
        note_allestimento: anomaliaDetail.riga_parent.note_allestimento || ''
      });
    }
    setIsEditingParent(false);
    // Reset lookup state
    setSearchQuery('');
    setSearchResults([]);
    setSelectedResult(null);
  }, [anomaliaDetail]);

  // Ricerca farmacia/parafarmacia per LOOKUP anomalies
  const handleSearch = useCallback(async () => {
    if (!searchQuery || searchQuery.length < 3) return;
    setSearchLoading(true);
    try {
      const [farmacie, parafarmacie] = await Promise.all([
        lookupApi.searchFarmacie(searchQuery),
        lookupApi.searchParafarmacie(searchQuery)
      ]);
      const results = [
        ...(farmacie.data || []).map(f => ({ ...f, tipo: 'FARMACIA' })),
        ...(parafarmacie.data || []).map(p => ({ ...p, tipo: 'PARAFARMACIA' }))
      ];
      setSearchResults(results);
    } catch (err) {
      console.error('Errore ricerca:', err);
      setSearchResults([]);
    } finally {
      setSearchLoading(false);
    }
  }, [searchQuery]);

  // Assegna farmacia/parafarmacia
  const handleAssign = async () => {
    if (!selectedResult || !anomaliaDetail?.anomalia?.id_testata) return;
    if (onAssignFarmacia) {
      const success = await onAssignFarmacia(
        anomaliaDetail.anomalia.id_testata,
        selectedResult.tipo === 'FARMACIA' ? selectedResult.id_farmacia : null,
        selectedResult.tipo === 'PARAFARMACIA' ? selectedResult.id_parafarmacia : null
      );
      if (success) {
        onClose();
      }
    }
  };

  // v11.0: ESC key handler e body scroll lock per coerenza con ModalBase (TIER 2.2)
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen) {
        handleCloseInternal();
      }
    };
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'hidden';
    }
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  if (!isOpen) return null;

  const handleCloseInternal = () => {
    setIsEditingParent(false);
    setEditingRigaParent(null);
    onClose();
  };

  // v11.0: Alias per compatibilità con codice esistente
  const handleClose = handleCloseInternal;

  // v11.0: Overlay click handler
  const handleOverlayClick = (e) => {
    if (e.target === e.currentTarget) {
      handleClose();
    }
  };

  const handleSaveParent = async () => {
    if (onSaveParent && editingRigaParent) {
      const success = await onSaveParent(editingRigaParent);
      if (success) {
        setIsEditingParent(false);
      }
    }
  };

  const handleCancelEdit = () => {
    setIsEditingParent(false);
    if (anomaliaDetail?.riga_parent) {
      setEditingRigaParent({
        q_venduta: anomaliaDetail.riga_parent.q_venduta || 0,
        q_sconto_merce: anomaliaDetail.riga_parent.q_sconto_merce || 0,
        q_omaggio: anomaliaDetail.riga_parent.q_omaggio || 0,
        descrizione: anomaliaDetail.riga_parent.descrizione || '',
        codice_originale: anomaliaDetail.riga_parent.codice_originale || '',
        prezzo_netto: anomaliaDetail.riga_parent.prezzo_netto || anomaliaDetail.riga_parent.prezzo_pubblico || 0,
        note_allestimento: anomaliaDetail.riga_parent.note_allestimento || ''
      });
    }
  };

  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
      onClick={handleOverlayClick}
    >
      <div
        className="bg-white rounded-xl w-[90vw] max-w-4xl max-h-[90vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-slate-200">
          <h3 className="text-lg font-semibold text-slate-800">
            Dettaglio Anomalia {anomaliaDetail?.anomalia?.id_anomalia && `#${anomaliaDetail.anomalia.id_anomalia}`}
          </h3>
          <div className="flex items-center gap-2">
            {/* Pulsante Visualizza PDF - controlla anomalia, ordine_data, testata */}
            {(() => {
              const pdfFile = anomaliaDetail?.anomalia?.pdf_file
                || anomaliaDetail?.ordine_data?.pdf_file
                || anomaliaDetail?.testata?.pdf_file;
              return pdfFile ? (
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
              ) : null;
            })()}
            <button
              onClick={handleClose}
              className="p-2 hover:bg-slate-100 rounded-lg text-slate-500"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Contenuto */}
        <div className="flex-1 overflow-y-auto p-4">
          {loading ? (
            <div className="text-center py-8">
              <div className="animate-spin text-2xl mb-2">Loading...</div>
              <p className="text-slate-500">Caricamento...</p>
            </div>
          ) : anomaliaDetail ? (
            <div className="space-y-6">
              {/* Info Anomalia */}
              <AnomaliaInfo
                anomalia={anomaliaDetail.anomalia}
                rigaParent={anomaliaDetail.riga_parent}
                onOpenOrdine={onOpenOrdine}
                onClose={handleClose}
              />

              {/* LOOKUP ANOMALIA - Mostra UI ricerca farmacia */}
              {isLookupAnomalia && (
                <LookupSection
                  idTestata={anomaliaDetail.anomalia.id_testata}
                  anomalia={anomaliaDetail.anomalia}
                  ordineData={anomaliaDetail.ordine_data}
                  searchQuery={searchQuery}
                  setSearchQuery={setSearchQuery}
                  searchResults={searchResults}
                  searchLoading={searchLoading}
                  selectedResult={selectedResult}
                  setSelectedResult={setSelectedResult}
                  onSearch={handleSearch}
                  onAssign={handleAssign}
                  onAssignManualMinId={async (minId) => {
                    if (onAssignFarmacia) {
                      // Passa MIN_ID manuale come terzo parametro
                      const success = await onAssignFarmacia(
                        anomaliaDetail.anomalia.id_testata,
                        null,  // id_farmacia
                        null,  // id_parafarmacia
                        minId  // manual MIN_ID
                      );
                      if (success) {
                        onClose();
                      }
                    }
                  }}
                  onClose={onClose}
                  // v11.4: Props per supporto Supervisione
                  fromSupervisione={fromSupervisione}
                  isSupervisor={isSupervisor}
                  supervisione={supervisione}
                  onSupervisioneSuccess={onSupervisioneSuccess}
                />
              )}

              {/* v11.0: AIC ANOMALIA - Usa AicAssignmentModal unificato (TIER 2.1) */}
              {isAicAnomalia && anomaliaDetail.anomalia?.stato !== 'RISOLTA' && (
                <div className="bg-purple-50 rounded-lg p-4">
                  <h4 className="font-semibold text-purple-800 mb-3 flex items-center gap-2">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
                    </svg>
                    Correzione Codice AIC
                  </h4>
                  <p className="text-sm text-purple-700 mb-3">
                    Questa anomalia richiede l'assegnazione di un codice AIC valido al prodotto.
                  </p>
                  <button
                    onClick={() => setIsAicModalOpen(true)}
                    className="w-full px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium flex items-center justify-center gap-2"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                    </svg>
                    Assegna Codice AIC
                  </button>
                </div>
              )}

              {/* v11.0: AIC Modal unificato */}
              <AicAssignmentModal
                isOpen={isAicModalOpen}
                onClose={() => setIsAicModalOpen(false)}
                mode={AIC_MODAL_MODES.ANOMALIA}
                anomalia={anomaliaDetail?.anomalia}
                rigaParent={anomaliaDetail?.riga_parent}
                onSuccess={() => {
                  setIsAicModalOpen(false);
                  onRisolvi?.();
                  onClose();
                }}
              />

              {/* ESPOSITORE ANOMALIA - Mostra UI parent/child */}
              {isEspositoreAnomalia && (
                <>
                  {/* Riga Parent */}
                  {anomaliaDetail.riga_parent && (
                    <RigaParentSection
                      rigaParent={anomaliaDetail.riga_parent}
                      isEditing={isEditingParent}
                      editingData={editingRigaParent}
                      onStartEdit={() => setIsEditingParent(true)}
                      onCancelEdit={handleCancelEdit}
                      onSave={handleSaveParent}
                      onEditChange={setEditingRigaParent}
                    />
                  )}

                  {/* Righe Child */}
                  {anomaliaDetail.righe_child && anomaliaDetail.righe_child.length > 0 && (
                    <RigheChildSection
                      righeChild={anomaliaDetail.righe_child}
                      totaleChild={anomaliaDetail.totale_child}
                    />
                  )}
                </>
              )}

              {/* v10.5: LISTINO ANOMALIA - Mostra info riga se presente */}
              {isListinoAnomalia && anomaliaDetail.riga_parent && (
                <RigaParentSection
                  rigaParent={anomaliaDetail.riga_parent}
                  isEditing={isEditingParent}
                  editingData={editingRigaParent}
                  onStartEdit={() => setIsEditingParent(true)}
                  onCancelEdit={handleCancelEdit}
                  onSave={handleSaveParent}
                  onEditChange={setEditingRigaParent}
                />
              )}

              {/* v10.6: Sezione Propagazione per anomalie che possono essere propagate */}
              {/* ESCLUSE: LOOKUP (richiede selezione), AIC (ha sua sezione), ESPOSITORE (uniche per ordine) */}
              {!isLookupAnomalia && !isAicAnomalia && !isEspositoreAnomalia && anomaliaDetail.anomalia?.stato !== 'RISOLTA' && (
                <PropagazioneSection
                  anomalia={anomaliaDetail.anomalia}
                  onSuccess={() => {
                    onRisolvi?.();
                    onClose();
                  }}
                  onClose={onClose}
                />
              )}

              {/* v10.6: Sezione risoluzione semplice per ESPOSITORE */}
              {isEspositoreAnomalia && anomaliaDetail.anomalia?.stato !== 'RISOLTA' && (
                <EspositoreRisolviSection
                  anomalia={anomaliaDetail.anomalia}
                  onSuccess={() => {
                    onRisolvi?.();
                    onClose();
                  }}
                />
              )}
            </div>
          ) : (
            <div className="text-center py-8 text-slate-500">
              Nessun dato disponibile
            </div>
          )}
        </div>

        {/* Footer - Solo per LOOKUP (che richiede selezione farmacia prima di risolvere) */}
        {/* Per AIC e ESPOSITORE la risoluzione avviene tramite le rispettive Section con propagazione */}
        {anomaliaDetail && anomaliaDetail.anomalia?.stato !== 'RISOLTA' && isLookupAnomalia && (
          <div className="p-4 border-t border-slate-200 flex justify-end gap-3">
            <button
              onClick={handleClose}
              className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded"
            >
              Annulla
            </button>
            {onRisolvi && (
              <button
                onClick={onRisolvi}
                disabled={isErroreAnomalia && !selectedResult}
                className={`px-4 py-2 rounded flex items-center gap-2 ${
                  isErroreAnomalia && !selectedResult
                    ? 'bg-slate-300 text-slate-500 cursor-not-allowed'
                    : 'bg-green-500 hover:bg-green-600 text-white'
                }`}
                title={isErroreAnomalia && !selectedResult
                  ? 'Seleziona prima una farmacia per risolvere questa anomalia'
                  : undefined}
              >
                Risolvi Anomalia
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// Sub-componente: Info Anomalia
function AnomaliaInfo({ anomalia, rigaParent, onOpenOrdine, onClose }) {
  if (!anomalia) return null;

  // v11.0: Usa livello corretto (livello > livello_anomalia > severita)
  const severita = anomalia.livello || anomalia.livello_anomalia || anomalia.severita || 'INFO';

  // v11.0: Descrizione prodotto da anomalia o da riga parent
  const descrizioneProdotto = anomalia.descrizione_prodotto || rigaParent?.descrizione;

  return (
    <div className="bg-slate-50 rounded-lg p-4">
      <h4 className="font-semibold text-slate-700 mb-3">Informazioni Anomalia</h4>
      <div className="grid grid-cols-2 gap-4 text-sm">
        <div>
          <span className="text-slate-500">Tipo:</span>{' '}
          <TipoAnomaliaBadge tipo={anomalia.tipo_anomalia} />
        </div>
        <div>
          <span className="text-slate-500">Stato:</span>{' '}
          <StatoAnomaliaBadge stato={anomalia.stato} />
        </div>
        <div>
          <span className="text-slate-500">Ordine:</span>{' '}
          <span className="font-mono">{anomalia.numero_ordine || '-'}</span>
          {anomalia.vendor && (
            <span className="ml-2 text-slate-400">({anomalia.vendor})</span>
          )}
        </div>
        <div>
          <span className="text-slate-500">Severita:</span>{' '}
          <SeveritaBadge severita={severita} />
        </div>
        {/* v11.0: Descrizione prodotto separata */}
        {descrizioneProdotto && (
          <div className="col-span-2">
            <span className="text-slate-500">Prodotto:</span>{' '}
            <span className="font-medium uppercase">{descrizioneProdotto}</span>
          </div>
        )}
        <div className="col-span-2">
          <span className="text-slate-500">Descrizione:</span>{' '}
          <span>{anomalia.descrizione}</span>
        </div>
      </div>

      {/* Link all'ordine */}
      {anomalia.id_testata && onOpenOrdine && (
        <div className="mt-3 pt-3 border-t border-slate-200">
          <button
            onClick={() => {
              onClose();
              onOpenOrdine(anomalia.id_testata);
            }}
            className="text-sm text-blue-600 hover:text-blue-800 flex items-center gap-1"
          >
            Vai all'ordine completo
          </button>
        </div>
      )}
    </div>
  );
}

// Sub-componente: Riga Parent
function RigaParentSection({
  rigaParent,
  isEditing,
  editingData,
  onStartEdit,
  onCancelEdit,
  onSave,
  onEditChange
}) {
  const prezzoUnitario = parseFloat(editingData?.prezzo_netto || rigaParent.prezzo_netto || rigaParent.prezzo_pubblico || 0) || 0;
  const quantita = parseInt(editingData?.q_venduta ?? rigaParent.q_venduta ?? 0) || 0;
  const prezzoTotale = prezzoUnitario * quantita;

  return (
    <div className="bg-blue-50 rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <h4 className="font-semibold text-blue-800">
          Riga Parent (Espositore)
          {rigaParent.is_espositore === 1 && ' (Espositore)'}
        </h4>
        {!isEditing && (
          <button
            onClick={onStartEdit}
            className="px-3 py-1 bg-blue-500 hover:bg-blue-600 text-white rounded text-sm"
          >
            Modifica
          </button>
        )}
      </div>

      <div className="space-y-3">
        {!isEditing ? (
          // Modalita visualizzazione
          <>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs text-slate-500 mb-1">Codice</label>
                <div className="px-3 py-2 bg-white border border-slate-200 rounded text-sm font-mono">
                  {rigaParent.codice_originale || '-'}
                </div>
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-1">Quantita Venduta</label>
                <div className="px-3 py-2 bg-white border border-slate-200 rounded text-sm">
                  {rigaParent.q_venduta || 0}
                </div>
              </div>
            </div>
            {/* Quantità aggiuntive */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs text-slate-500 mb-1">Q. Sconto Merce</label>
                <div className="px-3 py-2 bg-amber-50 border border-amber-200 rounded text-sm text-amber-700">
                  {rigaParent.q_sconto_merce || 0}
                </div>
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-1">Q. Omaggio</label>
                <div className="px-3 py-2 bg-green-50 border border-green-200 rounded text-sm text-green-700">
                  {rigaParent.q_omaggio || 0}
                </div>
              </div>
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-1">Descrizione</label>
              <div className="px-3 py-2 bg-white border border-slate-200 rounded text-sm uppercase">
                {rigaParent.descrizione || '-'}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4 pt-2 border-t border-blue-200">
              <div>
                <label className="block text-xs text-slate-500 mb-1">Prezzo Unitario</label>
                <div className="px-3 py-2 bg-white border border-slate-300 rounded text-sm font-medium text-slate-700">
                  {prezzoUnitario.toFixed(2)} EUR
                </div>
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-1">Prezzo Totale Vendita</label>
                <div className="px-3 py-2 bg-green-100 border border-green-300 rounded text-sm font-bold text-green-700">
                  {prezzoTotale.toFixed(2)} EUR
                </div>
              </div>
            </div>
            {rigaParent.note_allestimento && (
              <div>
                <label className="block text-xs text-slate-500 mb-1">Note Allestimento</label>
                <div className="px-3 py-2 bg-white border border-slate-200 rounded text-sm">
                  {rigaParent.note_allestimento}
                </div>
              </div>
            )}
          </>
        ) : (
          // Modalita modifica
          <>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs text-slate-500 mb-1">Codice</label>
                <input
                  type="text"
                  value={editingData?.codice_originale || ''}
                  onChange={(e) => onEditChange(prev => ({...prev, codice_originale: e.target.value}))}
                  className="w-full px-3 py-2 border border-blue-300 rounded text-sm font-mono bg-white focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-1">Quantita Venduta</label>
                <input
                  type="number"
                  value={editingData?.q_venduta || 0}
                  onChange={(e) => onEditChange(prev => ({...prev, q_venduta: parseInt(e.target.value) || 0}))}
                  className="w-full px-3 py-2 border border-blue-300 rounded text-sm bg-white focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
            {/* Quantità aggiuntive */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs text-slate-500 mb-1">Q. Sconto Merce</label>
                <input
                  type="number"
                  min="0"
                  value={editingData?.q_sconto_merce || 0}
                  onChange={(e) => onEditChange(prev => ({...prev, q_sconto_merce: parseInt(e.target.value) || 0}))}
                  className="w-full px-3 py-2 border border-amber-300 rounded text-sm bg-amber-50 focus:ring-2 focus:ring-amber-500"
                />
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-1">Q. Omaggio</label>
                <input
                  type="number"
                  min="0"
                  value={editingData?.q_omaggio || 0}
                  onChange={(e) => onEditChange(prev => ({...prev, q_omaggio: parseInt(e.target.value) || 0}))}
                  className="w-full px-3 py-2 border border-green-300 rounded text-sm bg-green-50 focus:ring-2 focus:ring-green-500"
                />
              </div>
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-1">Descrizione</label>
              <input
                type="text"
                value={editingData?.descrizione || ''}
                onChange={(e) => onEditChange(prev => ({...prev, descrizione: e.target.value}))}
                className="w-full px-3 py-2 border border-blue-300 rounded text-sm bg-white focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div className="grid grid-cols-2 gap-4 pt-2 border-t border-blue-200">
              <div>
                <label className="block text-xs text-slate-500 mb-1">Prezzo Unitario (EUR)</label>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  value={editingData?.prezzo_netto || 0}
                  onChange={(e) => onEditChange(prev => ({...prev, prezzo_netto: parseFloat(e.target.value) || 0}))}
                  className="w-full px-3 py-2 border border-blue-300 rounded text-sm bg-white focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-1">Prezzo Totale Vendita</label>
                <div className="px-3 py-2 bg-green-100 border border-green-300 rounded text-sm font-bold text-green-700">
                  {((editingData?.prezzo_netto || 0) * (editingData?.q_venduta || 0)).toFixed(2)} EUR
                </div>
              </div>
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-1">Note Allestimento</label>
              <textarea
                value={editingData?.note_allestimento || ''}
                onChange={(e) => onEditChange(prev => ({...prev, note_allestimento: e.target.value}))}
                className="w-full px-3 py-2 border border-blue-300 rounded text-sm bg-white focus:ring-2 focus:ring-blue-500"
                rows={2}
              />
            </div>
            <div className="flex justify-end gap-2">
              <button
                onClick={onCancelEdit}
                className="px-4 py-2 bg-slate-200 hover:bg-slate-300 text-slate-700 rounded text-sm"
              >
                Annulla
              </button>
              <button
                onClick={onSave}
                className="px-4 py-2 bg-green-500 hover:bg-green-600 text-white rounded text-sm"
              >
                Salva
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

// Sub-componente: Righe Child
function RigheChildSection({ righeChild, totaleChild }) {
  const totaleQta = righeChild.reduce((sum, c) => sum + (c.q_venduta || 0), 0);
  const totaleValore = righeChild.reduce((sum, c) => {
    const qta = c.q_venduta || 0;
    const prezzo = c.prezzo_netto || c.prezzo_pubblico || 0;
    return sum + (qta * prezzo);
  }, 0);

  return (
    <div className="bg-slate-50 rounded-lg p-4">
      <h4 className="font-semibold text-slate-700 mb-3">
        Righe Child ({totaleChild})
      </h4>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-slate-100">
            <tr>
              <th className="p-2 text-left">Riga</th>
              <th className="p-2 text-left">Codice</th>
              <th className="p-2 text-left">Descrizione</th>
              <th className="p-2 text-right">Qta</th>
              <th className="p-2 text-right">Prezzo Unit.</th>
              <th className="p-2 text-right">Totale</th>
            </tr>
          </thead>
          <tbody>
            {righeChild.map((child, idx) => {
              const qta = parseInt(child.q_venduta || 0) || 0;
              const prezzoUnit = parseFloat(child.prezzo_netto || child.prezzo_pubblico || 0) || 0;
              const totale = qta * prezzoUnit;
              return (
                <tr key={child.id_dettaglio || idx} className="border-b border-slate-200">
                  <td className="p-2 text-slate-500">{child.n_riga}</td>
                  <td className="p-2 font-mono text-xs">{child.codice_originale || child.codice_aic || '-'}</td>
                  <td className="p-2 truncate max-w-xs uppercase" title={child.descrizione}>{child.descrizione}</td>
                  <td className="p-2 text-right">{qta}</td>
                  <td className="p-2 text-right">{prezzoUnit.toFixed(2)} EUR</td>
                  <td className="p-2 text-right font-medium">{totale.toFixed(2)} EUR</td>
                </tr>
              );
            })}
          </tbody>
          <tfoot className="bg-slate-100 font-medium">
            <tr>
              <td className="p-2" colSpan={3}>Totale Child</td>
              <td className="p-2 text-right">{totaleQta}</td>
              <td className="p-2 text-right">-</td>
              <td className="p-2 text-right text-blue-700">{totaleValore.toFixed(2)} EUR</td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  );
}

// Sub-componente: Sezione LOOKUP
function LookupSection({
  idTestata,
  anomalia,  // v10.6: Aggiunto per check LKP-A05
  ordineData,
  searchQuery,
  setSearchQuery,
  searchResults,
  searchLoading,
  selectedResult,
  setSelectedResult,
  onSearch,
  onAssign,
  onAssignManualMinId,
  onClose,  // v10.6: Per chiudere modal dopo risoluzione deposito
  // v11.4: Props per supporto Supervisione
  fromSupervisione = false,
  isSupervisor = false,
  supervisione = null,
  onSupervisioneSuccess = null
}) {
  const [manualMinId, setManualMinId] = React.useState('');
  const [mode, setMode] = React.useState('alternative'); // 'alternative', 'search', 'manual', 'deposito'

  // v10.6: Stato per deposito manuale
  const [depositoRiferimento, setDepositoRiferimento] = React.useState('');
  const [depositoSubmitting, setDepositoSubmitting] = React.useState(false);
  const [depositoError, setDepositoError] = React.useState(null);

  // v11.4: Stato per propagazione (supervisore)
  const [livelloPropagazione, setLivelloPropagazione] = React.useState('ORDINE');

  // v11.4: Stato per flusso a due step (assegna → rivedi → risolvi)
  const [assignedData, setAssignedData] = React.useState(null); // Dati assegnati (farmacia/MIN_ID/deposito)
  const [isResolving, setIsResolving] = React.useState(false);

  // v10.6: Check se è LKP-A05 (Cliente non in anagrafica - deposito non determinabile)
  const isLkpA05 = anomalia?.codice_anomalia === 'LKP-A05';

  // v6.2.5: Alternative P.IVA-filtered
  const [alternatives, setAlternatives] = React.useState(null);
  const [alternativesLoading, setAlternativesLoading] = React.useState(false);
  const [alternativesError, setAlternativesError] = React.useState(null);

  // Carica alternative quando c'e una P.IVA estratta
  React.useEffect(() => {
    const loadAlternatives = async () => {
      if (!idTestata || !ordineData?.partita_iva) {
        setAlternatives(null);
        return;
      }

      setAlternativesLoading(true);
      setAlternativesError(null);
      try {
        const result = await lookupApi.getAlternative(idTestata);
        if (result.success && result.data) {
          setAlternatives(result.data);
        } else {
          setAlternativesError(result.error || 'Errore caricamento alternative');
        }
      } catch (err) {
        console.error('Errore caricamento alternative:', err);
        setAlternativesError(err.message || 'Errore caricamento alternative');
      } finally {
        setAlternativesLoading(false);
      }
    };

    loadAlternatives();
  }, [idTestata, ordineData?.partita_iva]);

  // v11.4: Assegna farmacia da ricerca/alternative (popola TUTTI i campi)
  const handleAssignFarmacia = (farmacia) => {
    setAssignedData({
      type: farmacia.tipo === 'FARMACIA' ? 'farmacia' : 'parafarmacia',
      id_farmacia: farmacia.tipo === 'FARMACIA' ? farmacia.id_farmacia : null,
      id_parafarmacia: farmacia.tipo === 'PARAFARMACIA' ? farmacia.id_parafarmacia : null,
      // Campi da anagrafica ministeriale/clienti
      min_id: farmacia.min_id || farmacia.codice_sito || '',
      partita_iva: farmacia.partita_iva || '',
      ragione_sociale: farmacia.ragione_sociale || farmacia.sito_logistico || '',
      indirizzo: farmacia.indirizzo || '',
      cap: farmacia.cap || '',
      citta: farmacia.citta || '',
      provincia: farmacia.provincia || '',
      // Deposito da anagrafica clienti (se disponibile)
      deposito: farmacia.deposito_riferimento || farmacia.deposito || ''
    });
    // Reset campi manuali quando si seleziona una farmacia
    setManualMinId('');
    setDepositoRiferimento('');
  };

  // v11.4: Aggiorna MIN_ID manuale (aggiorna campo specifico in assignedData)
  const handleAssignManualMinId = () => {
    if (manualMinId && manualMinId.length >= 6) {
      const paddedMinId = manualMinId.padStart(9, '0');
      if (assignedData) {
        // Aggiorna MIN_ID nei dati già assegnati
        setAssignedData(prev => ({ ...prev, min_id: paddedMinId }));
      } else {
        // Crea nuova assegnazione con solo MIN_ID (dati base da ordine)
        setAssignedData({
          type: 'manual',
          min_id: paddedMinId,
          partita_iva: ordineData?.partita_iva || '',
          ragione_sociale: ordineData?.ragione_sociale || '',
          indirizzo: ordineData?.indirizzo || '',
          cap: ordineData?.cap || '',
          citta: ordineData?.citta || '',
          provincia: ordineData?.provincia || '',
          deposito: ''
        });
      }
    }
  };

  // v11.4: Aggiorna Deposito manuale (aggiorna campo specifico in assignedData)
  const handleAssignDeposito = () => {
    if (depositoRiferimento && depositoRiferimento.trim()) {
      const dep = depositoRiferimento.trim();
      if (assignedData) {
        // Aggiorna deposito nei dati già assegnati
        setAssignedData(prev => ({ ...prev, deposito: dep }));
      } else {
        // Crea nuova assegnazione con solo deposito (dati base da ordine)
        setAssignedData({
          type: 'manual',
          min_id: '',
          partita_iva: ordineData?.partita_iva || '',
          ragione_sociale: ordineData?.ragione_sociale || '',
          indirizzo: ordineData?.indirizzo || '',
          cap: ordineData?.cap || '',
          citta: ordineData?.citta || '',
          provincia: ordineData?.provincia || '',
          deposito: dep
        });
      }
    }
  };

  // v11.4: Valida campi obbligatori (P.IVA, MIN_ID, Deposito)
  const missingFields = React.useMemo(() => {
    if (!assignedData) return [];
    const missing = [];
    if (!assignedData.partita_iva) missing.push('partita_iva');
    if (!assignedData.min_id) missing.push('min_id');
    if (!assignedData.deposito) missing.push('deposito');
    return missing;
  }, [assignedData]);

  const canResolve = assignedData && missingFields.length === 0;

  // v11.4: Risolvi anomalia (step 2 - conferma e salva)
  const handleRisolviAnomalia = async () => {
    if (!canResolve) return;

    setIsResolving(true);
    setDepositoError(null);

    try {
      const user = JSON.parse(localStorage.getItem('servo_user') || '{}');
      const operatore = user.username || 'admin';

      // Usa sempre onAssign con i dati completi (farmacia o manuale)
      if (assignedData.type === 'farmacia' || assignedData.type === 'parafarmacia') {
        // Assegna farmacia/parafarmacia + deposito se necessario
        if (onAssign) {
          // Prima assegna la farmacia
          onAssign();
          // Se c'è un deposito manuale aggiunto, aggiorna anche quello
          if (assignedData.deposito && !assignedData.id_farmacia?.deposito_riferimento) {
            // TODO: aggiorna deposito ordine se necessario
          }
        }
      } else {
        // Assegnazione manuale (MIN_ID e/o Deposito)
        if (assignedData.min_id && onAssignManualMinId) {
          onAssignManualMinId(assignedData.min_id);
        }
        if (assignedData.deposito) {
          const { anomalieApi } = await import('../api/anomalie');
          await anomalieApi.risolviDeposito(anomalia.id_anomalia, {
            deposito_riferimento: assignedData.deposito,
            operatore,
            note: `Deposito assegnato manualmente`
          });
        }
        if (onClose) onClose();
      }
    } catch (err) {
      console.error('Errore risoluzione:', err);
      setDepositoError(err.message || 'Errore durante risoluzione');
    } finally {
      setIsResolving(false);
    }
  };

  // v11.4: Reset assegnazione
  const handleResetAssignment = () => {
    setAssignedData(null);
    setManualMinId('');
    setDepositoRiferimento('');
  };

  // Conta alternative disponibili
  const totaleAlternative = alternatives?.totale_alternative || 0;
  const hasPivaBloccata = !!alternatives?.piva_bloccata;

  return (
    <div className="space-y-4">
      {/* Dati estratti dal documento */}
      <div className="bg-amber-50 rounded-lg p-4">
        <h4 className="font-semibold text-amber-800 mb-3">Dati Estratti dal Documento</h4>
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div>
            <span className="text-slate-500">P.IVA:</span>{' '}
            <span className={`font-mono ${ordineData?.partita_iva ? 'text-green-700 font-bold' : ''}`}>
              {ordineData?.partita_iva || '-'}
            </span>
            {ordineData?.partita_iva && (
              <span className="ml-2 text-xs bg-green-100 text-green-700 px-1.5 py-0.5 rounded">
                Rilevata
              </span>
            )}
          </div>
          <div>
            <span className="text-slate-500">Cod. Ministeriale:</span>{' '}
            <span className="font-mono">{ordineData?.codice_ministeriale || '-'}</span>
          </div>
          <div className="col-span-2">
            <span className="text-slate-500">Ragione Sociale:</span>{' '}
            <span>{ordineData?.ragione_sociale?.toUpperCase() || '-'}</span>
          </div>
          <div className="col-span-2">
            <span className="text-slate-500">Indirizzo:</span>{' '}
            <span>{ordineData?.indirizzo?.toUpperCase() || '-'}</span>
          </div>
          <div>
            <span className="text-slate-500">CAP:</span>{' '}
            <span>{ordineData?.cap || '-'}</span>
          </div>
          <div>
            <span className="text-slate-500">Citta:</span>{' '}
            <span>{ordineData?.citta?.toUpperCase() || '-'}</span>
          </div>
          <div>
            <span className="text-slate-500">Provincia:</span>{' '}
            <span>{ordineData?.provincia?.toUpperCase() || '-'}</span>
          </div>
        </div>
      </div>

      {/* v11.4: Preview Anagrafica Assegnata (dopo selezione, prima di risoluzione) */}
      {assignedData && (
        <div className={`border-2 rounded-lg p-4 ${canResolve ? 'bg-green-50 border-green-300' : 'bg-amber-50 border-amber-300'}`}>
          <div className="flex items-center justify-between mb-3">
            <h4 className={`font-semibold flex items-center gap-2 ${canResolve ? 'text-green-800' : 'text-amber-800'}`}>
              {canResolve ? (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              ) : (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              )}
              Anagrafica da Assegnare
            </h4>
            <button
              onClick={handleResetAssignment}
              className="text-sm text-red-600 hover:text-red-800 flex items-center gap-1"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
              Annulla
            </button>
          </div>

          {/* Alert campi mancanti */}
          {missingFields.length > 0 && (
            <div className="mb-4 p-3 bg-amber-100 border border-amber-300 rounded-lg">
              <p className="text-sm font-medium text-amber-800 mb-2">
                Campi obbligatori mancanti - inserisci manualmente:
              </p>
              <div className="flex flex-wrap gap-2">
                {missingFields.includes('partita_iva') && (
                  <span className="px-2 py-1 bg-red-100 text-red-700 rounded text-xs font-medium">P.IVA</span>
                )}
                {missingFields.includes('min_id') && (
                  <span className="px-2 py-1 bg-red-100 text-red-700 rounded text-xs font-medium">MIN_ID</span>
                )}
                {missingFields.includes('deposito') && (
                  <span className="px-2 py-1 bg-red-100 text-red-700 rounded text-xs font-medium">Deposito</span>
                )}
              </div>
            </div>
          )}

          {/* Griglia dati con evidenziazione campi mancanti */}
          <div className="grid grid-cols-2 gap-3 text-sm">
            {/* P.IVA */}
            <div className={missingFields.includes('partita_iva') ? 'p-2 bg-red-50 border border-red-200 rounded' : ''}>
              <span className="text-slate-500">P.IVA:</span>{' '}
              {assignedData.partita_iva ? (
                <span className="font-mono font-medium">{assignedData.partita_iva}</span>
              ) : (
                <span className="text-red-500 font-medium">MANCANTE</span>
              )}
            </div>

            {/* MIN_ID */}
            <div className={missingFields.includes('min_id') ? 'p-2 bg-red-50 border border-red-200 rounded' : ''}>
              <span className="text-slate-500">MIN_ID:</span>{' '}
              {assignedData.min_id ? (
                <span className="font-mono font-bold text-green-700">{assignedData.min_id}</span>
              ) : (
                <div className="inline-flex items-center gap-2">
                  <span className="text-red-500 font-medium">MANCANTE</span>
                  <input
                    type="text"
                    value={manualMinId}
                    onChange={(e) => setManualMinId(e.target.value.replace(/\D/g, '').slice(0, 9))}
                    placeholder="Inserisci"
                    className="w-24 px-2 py-1 border border-orange-300 rounded text-xs font-mono"
                    maxLength={9}
                  />
                  <button
                    onClick={handleAssignManualMinId}
                    disabled={!manualMinId || manualMinId.length < 6}
                    className="px-2 py-1 bg-orange-500 hover:bg-orange-600 disabled:bg-orange-300 text-white rounded text-xs"
                  >
                    OK
                  </button>
                </div>
              )}
            </div>

            {/* Ragione Sociale */}
            <div className="col-span-2">
              <span className="text-slate-500">Ragione Sociale:</span>{' '}
              <span className="font-medium">{assignedData.ragione_sociale?.toUpperCase() || '-'}</span>
            </div>

            {/* Indirizzo */}
            <div className="col-span-2">
              <span className="text-slate-500">Indirizzo:</span>{' '}
              <span>{assignedData.indirizzo?.toUpperCase() || '-'}</span>
            </div>

            {/* CAP, Città, Provincia */}
            <div>
              <span className="text-slate-500">CAP:</span>{' '}
              <span>{assignedData.cap || '-'}</span>
            </div>
            <div>
              <span className="text-slate-500">Città:</span>{' '}
              <span>{assignedData.citta?.toUpperCase() || '-'}</span>
            </div>
            <div>
              <span className="text-slate-500">Provincia:</span>{' '}
              <span>{assignedData.provincia?.toUpperCase() || '-'}</span>
            </div>

            {/* Deposito */}
            <div className={`${missingFields.includes('deposito') ? 'p-2 bg-red-50 border border-red-200 rounded' : ''}`}>
              <span className="text-slate-500">Deposito:</span>{' '}
              {assignedData.deposito ? (
                <span className="font-bold text-purple-700">{assignedData.deposito}</span>
              ) : (
                <div className="inline-flex items-center gap-2">
                  <span className="text-red-500 font-medium">MANCANTE</span>
                  <input
                    type="text"
                    value={depositoRiferimento}
                    onChange={(e) => setDepositoRiferimento(e.target.value.slice(0, 10))}
                    placeholder="Cod."
                    className="w-16 px-2 py-1 border border-purple-300 rounded text-xs font-mono"
                    maxLength={10}
                  />
                  <button
                    onClick={handleAssignDeposito}
                    disabled={!depositoRiferimento}
                    className="px-2 py-1 bg-purple-500 hover:bg-purple-600 disabled:bg-purple-300 text-white rounded text-xs"
                  >
                    OK
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Errore */}
          {depositoError && (
            <div className="mt-3 p-2 bg-red-100 border border-red-300 rounded text-red-700 text-sm">
              {depositoError}
            </div>
          )}

          {/* v11.4: Opzioni Propagazione per Supervisore */}
          {fromSupervisione && isSupervisor && (
            <div className="mt-4 pt-3 border-t border-green-200">
              <p className="text-sm font-medium text-green-800 mb-2">Propagazione:</p>
              <div className="flex gap-4">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="propagazione_lookup"
                    value="ORDINE"
                    checked={livelloPropagazione === 'ORDINE'}
                    onChange={() => setLivelloPropagazione('ORDINE')}
                    className="text-green-600"
                  />
                  <span className="text-sm">Solo questo ordine</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="propagazione_lookup"
                    value="GLOBALE"
                    checked={livelloPropagazione === 'GLOBALE'}
                    onChange={() => setLivelloPropagazione('GLOBALE')}
                    className="text-green-600"
                  />
                  <span className="text-sm">
                    Propaga globalmente
                    {supervisione?.total_count > 1 && (
                      <span className="ml-1 text-green-600 font-medium">
                        ({supervisione.total_count})
                      </span>
                    )}
                  </span>
                </label>
              </div>
            </div>
          )}

          {/* Bottone Risolvi Anomalia */}
          <div className="mt-4 flex justify-end">
            <button
              onClick={handleRisolviAnomalia}
              disabled={!canResolve || isResolving}
              className={`px-6 py-2 rounded-lg font-medium flex items-center gap-2 ${
                !canResolve || isResolving
                  ? 'bg-slate-300 text-slate-500 cursor-not-allowed'
                  : 'bg-green-600 hover:bg-green-700 text-white'
              }`}
              title={!canResolve ? 'Compila i campi obbligatori mancanti' : ''}
            >
              {isResolving ? (
                <>
                  <span className="animate-spin">⏳</span>
                  Risoluzione in corso...
                </>
              ) : !canResolve ? (
                <>
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                  Compila campi mancanti
                </>
              ) : (
                <>
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  Risolvi Anomalia
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* Toggle tra modalita (nascosto se già assegnato) */}
      {!assignedData && (
        <>
        <div className="flex gap-2">
        {hasPivaBloccata && (
          <button
            onClick={() => setMode('alternative')}
            className={`flex-1 px-4 py-2 rounded text-sm font-medium transition-colors ${
              mode === 'alternative'
                ? 'bg-green-500 text-white'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            Alternative P.IVA ({totaleAlternative})
          </button>
        )}
        <button
          onClick={() => setMode('search')}
          className={`flex-1 px-4 py-2 rounded text-sm font-medium transition-colors ${
            mode === 'search'
              ? 'bg-blue-500 text-white'
              : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
          }`}
        >
          Ricerca Libera
        </button>
        <button
          onClick={() => setMode('manual')}
          className={`flex-1 px-4 py-2 rounded text-sm font-medium transition-colors ${
            mode === 'manual'
              ? 'bg-orange-500 text-white'
              : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
          }`}
        >
          MIN_ID Manuale
        </button>
        {/* v11.4: Deposito manuale sempre visibile (non solo LKP-A05) */}
        <button
          onClick={() => setMode('deposito')}
          className={`flex-1 px-4 py-2 rounded text-sm font-medium transition-colors ${
            mode === 'deposito'
              ? 'bg-purple-500 text-white'
              : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
          }`}
        >
          Deposito
        </button>
      </div>

      {/* v6.2.5: Alternative P.IVA-filtered */}
      {mode === 'alternative' && hasPivaBloccata && (
        <div className="bg-green-50 rounded-lg p-4">
          <h4 className="font-semibold text-green-800 mb-2">
            Alternative con P.IVA {alternatives.piva_bloccata}
          </h4>
          <p className="text-sm text-green-700 mb-4">
            Farmacie/Parafarmacie con la stessa P.IVA estratta dal documento, ordinate per corrispondenza indirizzo.
          </p>

          {alternativesLoading ? (
            <div className="text-center py-4 text-green-600">Caricamento alternative...</div>
          ) : alternativesError ? (
            <div className="text-center py-4 text-red-500">{alternativesError}</div>
          ) : (
            <>
              {/* Lista farmacie */}
              {alternatives.farmacie && alternatives.farmacie.length > 0 && (
                <div className="mb-4">
                  <h5 className="text-sm font-medium text-green-700 mb-2">
                    Farmacie ({alternatives.farmacie.length})
                  </h5>
                  <div className="max-h-48 overflow-y-auto border border-green-200 rounded bg-white">
                    {alternatives.farmacie.map((farm) => {
                      const isSelected = selectedResult?.id_farmacia === farm.id_farmacia;
                      return (
                        <div
                          key={`farm-${farm.id_farmacia}`}
                          onClick={() => setSelectedResult({ ...farm, tipo: 'FARMACIA' })}
                          className={`p-3 border-b border-green-100 cursor-pointer hover:bg-green-100 ${
                            isSelected ? 'bg-green-200' : ''
                          } ${farm.is_selected ? 'ring-2 ring-blue-400' : ''}`}
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <span className="text-xs px-2 py-0.5 rounded bg-green-100 text-green-700">
                                FARMACIA
                              </span>
                              <span className="font-medium">{farm.ragione_sociale?.toUpperCase()}</span>
                              {farm.is_selected && (
                                <span className="text-xs bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded">
                                  Attuale
                                </span>
                              )}
                            </div>
                            <div className="flex items-center gap-2">
                              <span className={`text-xs font-bold px-2 py-1 rounded ${
                                farm.fuzzy_score >= 80 ? 'bg-green-200 text-green-800' :
                                farm.fuzzy_score >= 50 ? 'bg-yellow-200 text-yellow-800' :
                                'bg-red-200 text-red-800'
                              }`}>
                                {farm.fuzzy_score}%
                              </span>
                              <span className="text-xs font-mono text-slate-500">{farm.min_id}</span>
                            </div>
                          </div>
                          <div className="text-xs text-slate-500 mt-1">
                            {farm.indirizzo && `${farm.indirizzo}, `}
                            {farm.cap && `${farm.cap} `}
                            {farm.citta && `${farm.citta} `}
                            {farm.provincia && `(${farm.provincia})`}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Lista parafarmacie */}
              {alternatives.parafarmacie && alternatives.parafarmacie.length > 0 && (
                <div className="mb-4">
                  <h5 className="text-sm font-medium text-purple-700 mb-2">
                    Parafarmacie ({alternatives.parafarmacie.length})
                  </h5>
                  <div className="max-h-48 overflow-y-auto border border-purple-200 rounded bg-white">
                    {alternatives.parafarmacie.map((para) => {
                      const isSelected = selectedResult?.id_parafarmacia === para.id_parafarmacia;
                      return (
                        <div
                          key={`para-${para.id_parafarmacia}`}
                          onClick={() => setSelectedResult({ ...para, tipo: 'PARAFARMACIA' })}
                          className={`p-3 border-b border-purple-100 cursor-pointer hover:bg-purple-100 ${
                            isSelected ? 'bg-purple-200' : ''
                          } ${para.is_selected ? 'ring-2 ring-blue-400' : ''}`}
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <span className="text-xs px-2 py-0.5 rounded bg-purple-100 text-purple-700">
                                PARAFARMACIA
                              </span>
                              <span className="font-medium">{(para.ragione_sociale || para.sito_logistico)?.toUpperCase()}</span>
                              {para.is_selected && (
                                <span className="text-xs bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded">
                                  Attuale
                                </span>
                              )}
                            </div>
                            <div className="flex items-center gap-2">
                              <span className={`text-xs font-bold px-2 py-1 rounded ${
                                para.fuzzy_score >= 80 ? 'bg-green-200 text-green-800' :
                                para.fuzzy_score >= 50 ? 'bg-yellow-200 text-yellow-800' :
                                'bg-red-200 text-red-800'
                              }`}>
                                {para.fuzzy_score}%
                              </span>
                              <span className="text-xs font-mono text-slate-500">{para.codice_sito}</span>
                            </div>
                          </div>
                          <div className="text-xs text-slate-500 mt-1">
                            {para.indirizzo && `${para.indirizzo}, `}
                            {para.cap && `${para.cap} `}
                            {para.citta && `${para.citta} `}
                            {para.provincia && `(${para.provincia})`}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {totaleAlternative === 0 && (
                <div className="text-center py-4 text-slate-500 text-sm">
                  Nessuna alternativa trovata con questa P.IVA. Usa la ricerca libera.
                </div>
              )}
            </>
          )}

          {/* Selezione corrente e pulsante assegna */}
          {selectedResult && (
            <div className="mt-4 p-3 bg-green-100 border border-green-300 rounded">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-sm font-medium text-green-800">Selezionato:</span>
                  <span className="ml-2">{(selectedResult.ragione_sociale || selectedResult.sito_logistico)?.toUpperCase()}</span>
                  <span className="ml-2 text-xs text-slate-500">
                    ({selectedResult.tipo === 'FARMACIA' ? selectedResult.min_id : selectedResult.codice_sito})
                  </span>
                </div>
                <button
                  onClick={() => handleAssignFarmacia(selectedResult)}
                  className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded text-sm font-medium"
                >
                  Assegna
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Ricerca libera */}
      {mode === 'search' && (
        <div className="bg-blue-50 rounded-lg p-4">
          <h4 className="font-semibold text-blue-800 mb-3">Ricerca Libera Farmacia/Parafarmacia</h4>
          <div className="flex gap-2 mb-2">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Cerca per P.IVA, ragione sociale, citta..."
              className="flex-1 px-3 py-2 border border-blue-300 rounded text-sm focus:ring-2 focus:ring-blue-500"
              onKeyDown={(e) => e.key === 'Enter' && onSearch()}
            />
            <button
              onClick={onSearch}
              disabled={searchLoading || searchQuery.length < 3}
              className="px-4 py-2 bg-blue-500 hover:bg-blue-600 disabled:bg-blue-300 text-white rounded text-sm"
            >
              {searchLoading ? 'Cerco...' : 'Cerca'}
            </button>
          </div>
          <p className="text-xs text-blue-600 mb-4">
            <span className="font-medium">Operatori:</span>{' '}
            <code className="bg-blue-100 px-1 rounded">ROMA + MILANO</code> (OR){' '}
            <code className="bg-blue-100 px-1 rounded">SEMINARA * CATANIA</code> (AND)
          </p>

          {/* Risultati ricerca */}
          {searchResults.length > 0 ? (
            <div className="max-h-64 overflow-y-auto border border-blue-200 rounded">
              {searchResults.map((result, idx) => {
                const id = result.tipo === 'FARMACIA' ? result.id_farmacia : result.id_parafarmacia;
                const codice = result.tipo === 'FARMACIA' ? result.min_id : result.codice_sito;
                const isSelected = selectedResult &&
                  ((result.tipo === 'FARMACIA' && selectedResult.id_farmacia === result.id_farmacia) ||
                   (result.tipo === 'PARAFARMACIA' && selectedResult.id_parafarmacia === result.id_parafarmacia));

                return (
                  <div
                    key={`${result.tipo}-${id}`}
                    onClick={() => setSelectedResult(result)}
                    className={`p-3 border-b border-blue-100 cursor-pointer hover:bg-blue-100 ${
                      isSelected ? 'bg-blue-200' : ''
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <span className={`text-xs px-2 py-0.5 rounded ${
                          result.tipo === 'FARMACIA' ? 'bg-green-100 text-green-700' : 'bg-purple-100 text-purple-700'
                        }`}>
                          {result.tipo}
                        </span>
                        <span className="ml-2 font-medium">{result.ragione_sociale?.toUpperCase()}</span>
                      </div>
                      <span className="text-xs font-mono text-slate-500">{codice}</span>
                    </div>
                    <div className="text-xs text-slate-500 mt-1">
                      {result.indirizzo && `${result.indirizzo}, `}
                      {result.cap && `${result.cap} `}
                      {result.citta && `${result.citta} `}
                      {result.provincia && `(${result.provincia})`}
                    </div>
                    <div className="text-xs text-slate-400 mt-1">
                      P.IVA: {result.partita_iva || '-'}
                    </div>
                  </div>
                );
              })}
            </div>
          ) : searchQuery.length >= 3 && !searchLoading ? (
            <div className="text-center py-4 text-slate-500 text-sm">
              Nessun risultato trovato. Prova con l'inserimento manuale del MIN_ID.
            </div>
          ) : null}

          {/* Selezione corrente e pulsante assegna */}
          {selectedResult && (
            <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-sm font-medium text-green-800">Selezionato:</span>
                  <span className="ml-2">{selectedResult.ragione_sociale?.toUpperCase()}</span>
                  <span className="ml-2 text-xs text-slate-500">
                    ({selectedResult.tipo === 'FARMACIA' ? selectedResult.min_id : selectedResult.codice_sito})
                  </span>
                </div>
                <button
                  onClick={() => handleAssignFarmacia(selectedResult)}
                  className="px-4 py-2 bg-green-500 hover:bg-green-600 text-white rounded text-sm font-medium"
                >
                  Assegna
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Inserimento manuale MIN_ID */}
      {mode === 'manual' && (
        <div className="bg-orange-50 rounded-lg p-4">
          <h4 className="font-semibold text-orange-800 mb-3">Inserimento Manuale Codice Ministeriale</h4>
          <p className="text-sm text-orange-700 mb-4">
            Usa questa opzione quando la farmacia non e presente nel database.
            Inserisci il codice MIN_ID (9 cifre per farmacie) o codice sito (per parafarmacie).
          </p>

          <div className="flex gap-2 mb-4">
            <input
              type="text"
              value={manualMinId}
              onChange={(e) => setManualMinId(e.target.value.replace(/\D/g, '').slice(0, 9))}
              placeholder="Inserisci MIN_ID (es: 010123456)"
              className="flex-1 px-3 py-2 border border-orange-300 rounded text-sm font-mono focus:ring-2 focus:ring-orange-500"
              maxLength={9}
            />
            <button
              onClick={handleAssignManualMinId}
              disabled={!manualMinId || manualMinId.length < 6}
              className="px-4 py-2 bg-orange-500 hover:bg-orange-600 disabled:bg-orange-300 text-white rounded text-sm font-medium"
            >
              Assegna
            </button>
          </div>

          {manualMinId && manualMinId.length >= 6 && (
            <div className="p-3 bg-orange-100 border border-orange-200 rounded">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-sm font-medium text-orange-800">MIN_ID da assegnare:</span>
                  <span className="ml-2 font-mono text-lg">{manualMinId.padStart(9, '0')}</span>
                </div>
                <button
                  onClick={handleAssignManualMinId}
                  disabled={!manualMinId || manualMinId.length < 6}
                  className="px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded text-sm font-medium"
                >
                  Assegna
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* v11.4: Inserimento manuale Deposito (per tutti i LOOKUP/ANAGRAFICA) */}
      {mode === 'deposito' && (
        <div className="bg-purple-50 rounded-lg p-4">
          <h4 className="font-semibold text-purple-800 mb-3">Assegnazione Deposito</h4>
          <p className="text-sm text-purple-700 mb-4">
            Inserisci manualmente il codice deposito di riferimento per procedere con l'ordine.
          </p>

          {depositoError && (
            <div className="mb-4 p-3 bg-red-100 border border-red-300 rounded text-red-700 text-sm">
              {depositoError}
            </div>
          )}

          <div className="flex gap-2 mb-4">
            <input
              type="text"
              value={depositoRiferimento}
              onChange={(e) => setDepositoRiferimento(e.target.value.slice(0, 10))}
              placeholder="Codice deposito (es: 001)"
              className="flex-1 px-3 py-2 border border-purple-300 rounded text-sm font-mono focus:ring-2 focus:ring-purple-500"
              maxLength={10}
            />
            <button
              onClick={handleAssignDeposito}
              disabled={!depositoRiferimento}
              className="px-4 py-2 bg-purple-500 hover:bg-purple-600 disabled:bg-purple-300 text-white rounded text-sm font-medium"
            >
              Assegna
            </button>
          </div>

          {depositoRiferimento && (
            <div className="p-3 bg-purple-100 border border-purple-200 rounded">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-sm font-medium text-purple-800">Deposito da assegnare:</span>
                  <span className="ml-2 font-mono text-lg">{depositoRiferimento}</span>
                </div>
                <button
                  onClick={handleAssignDeposito}
                  disabled={!depositoRiferimento}
                  className="px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:bg-purple-300 text-white rounded text-sm font-medium"
                >
                  Assegna
                </button>
              </div>
            </div>
          )}
        </div>
      )}
      {/* Fine blocco !assignedData */}
      </>
      )}
    </div>
  );
}

// =============================================================================
// v10.5: Sub-componente Propagazione Generica
// =============================================================================

function PropagazioneSection({ anomalia, onSuccess, onClose }) {
  const [livelloPropagazione, setLivelloPropagazione] = useState('ORDINE');
  const [note, setNote] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [conteggi, setConteggi] = useState({ ordine: 1, globale: 0 });
  const [livelliPermessi, setLivelliPermessi] = useState(['ORDINE']);
  const [loadingConteggi, setLoadingConteggi] = useState(true);

  // Recupera operatore e ruolo dal localStorage
  const { operatore, ruolo, isSupervisor } = React.useMemo(() => {
    try {
      const user = JSON.parse(localStorage.getItem('servo_user') || '{}');
      const userRuolo = (user.ruolo || 'operatore').toLowerCase();
      const canGlobal = userRuolo === 'admin' || userRuolo === 'supervisore' || userRuolo === 'supervisor' || userRuolo === 'superuser';
      return {
        operatore: user.username || 'operatore',
        ruolo: userRuolo,
        isSupervisor: canGlobal
      };
    } catch {
      return { operatore: 'operatore', ruolo: 'operatore', isSupervisor: false };
    }
  }, []);

  // Carica conteggi anomalie identiche e livelli permessi
  useEffect(() => {
    const loadConteggi = async () => {
      if (!anomalia?.id_anomalia) return;
      setLoadingConteggi(true);
      try {
        const res = await anomalieApi.getLivelliPermessi(anomalia.id_anomalia, ruolo);
        if (res.success) {
          setConteggi(res.data.conteggi);
          setLivelliPermessi(res.data.livelli_permessi);
          // Default al livello più alto permesso se sono supervisore
          if (res.data.livelli_permessi.includes('ORDINE') && res.data.conteggi.ordine > 1) {
            setLivelloPropagazione('ORDINE');
          }
        }
      } catch (err) {
        console.error('Errore caricamento conteggi:', err);
      } finally {
        setLoadingConteggi(false);
      }
    };
    loadConteggi();
  }, [anomalia?.id_anomalia, ruolo]);

  const handleSubmit = async () => {
    setSubmitting(true);
    setError(null);

    try {
      const response = await anomalieApi.risolviConPropagazione(anomalia.id_anomalia, {
        livello_propagazione: livelloPropagazione,
        operatore,
        ruolo,
        note: note || undefined
      });

      if (response.success) {
        setResult(response.data);
        setTimeout(() => {
          onSuccess?.();
        }, 1500);
      } else {
        setError(response.error || 'Errore durante risoluzione');
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Errore durante risoluzione');
    } finally {
      setSubmitting(false);
    }
  };

  const livelloOptions = [
    {
      value: 'ORDINE',
      label: 'Stesso ordine',
      desc: 'Tutte le anomalie identiche in questo ordine',
      count: conteggi.ordine
    },
    {
      value: 'GLOBALE',
      label: 'Globale (Supervisore)',
      desc: 'Tutte le anomalie identiche stesso vendor in tutti gli ordini',
      count: conteggi.globale,
      supervisorOnly: true
    }
  ].filter(opt => livelliPermessi.includes(opt.value));

  return (
    <div className="bg-indigo-50 rounded-lg p-4">
      <h4 className="font-semibold text-indigo-800 mb-3 flex items-center gap-2">
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        Risolvi Anomalia
        {conteggi.globale > 1 && (
          <span className="ml-auto text-xs bg-indigo-200 text-indigo-700 px-2 py-1 rounded">
            {conteggi.globale} identiche nel sistema
          </span>
        )}
      </h4>

      {/* Risultato successo */}
      {result && (
        <div className="mb-4 p-4 bg-green-100 border border-green-300 rounded">
          <div className="flex items-center gap-2 text-green-800 font-medium mb-2">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            Anomalie Risolte con Successo
          </div>
          <div className="text-sm text-green-700 space-y-1">
            <p>Anomalie risolte: <span className="font-bold">{result.anomalie_risolte}</span></p>
            <p>Ordini coinvolti: <span className="font-bold">{result.ordini_coinvolti?.length || 0}</span></p>
            {result.supervisioni_approvate > 0 && (
              <p>Supervisioni approvate: <span className="font-bold">{result.supervisioni_approvate}</span></p>
            )}
            {result.ml_pattern_incrementato > 0 && (
              <p>Pattern ML incrementato: <span className="font-bold">+{result.ml_pattern_incrementato}</span></p>
            )}
          </div>
        </div>
      )}

      {/* Form risoluzione */}
      {!result && (
        <div className="space-y-4">
          {loadingConteggi ? (
            <div className="text-center py-4 text-indigo-600">Caricamento...</div>
          ) : (
            <>
              {/* Livello propagazione */}
              {livelloOptions.length > 1 && (
                <div>
                  <label className="block text-sm font-medium text-indigo-800 mb-2">
                    Livello Propagazione
                  </label>
                  <div className="space-y-2">
                    {livelloOptions.map((opt) => (
                      <label
                        key={opt.value}
                        className={`flex items-start gap-3 p-3 rounded border cursor-pointer transition-colors ${
                          livelloPropagazione === opt.value
                            ? 'border-indigo-500 bg-indigo-100'
                            : 'border-slate-200 bg-white hover:bg-slate-50'
                        }`}
                      >
                        <input
                          type="radio"
                          name="livello_propagazione"
                          value={opt.value}
                          checked={livelloPropagazione === opt.value}
                          onChange={(e) => setLivelloPropagazione(e.target.value)}
                          className="mt-1"
                        />
                        <div className="flex-1">
                          <div className="font-medium text-sm flex items-center justify-between">
                            <span>{opt.label}</span>
                            <span className={`text-xs px-2 py-0.5 rounded ${
                              opt.count > 1 ? 'bg-indigo-200 text-indigo-700' : 'bg-slate-200 text-slate-600'
                            }`}>
                              {opt.count} anomali{opt.count === 1 ? 'a' : 'e'}
                            </span>
                          </div>
                          <div className="text-xs text-slate-500">{opt.desc}</div>
                        </div>
                      </label>
                    ))}
                  </div>
                </div>
              )}

              {/* Messaggio per operatori */}
              {!isSupervisor && conteggi.globale > 1 && (
                <div className="p-3 bg-amber-50 border border-amber-200 rounded text-sm text-amber-700">
                  <strong>Nota:</strong> Come operatore, puoi risolvere solo questa anomalia.
                  Per propagare la risoluzione a tutte le {conteggi.globale} anomalie identiche,
                  contatta un supervisore.
                </div>
              )}

              {/* Note */}
              <div>
                <label className="block text-sm font-medium text-indigo-800 mb-1">
                  Note (opzionale)
                </label>
                <textarea
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  placeholder="Es: Verificato con vendor, dati corretti"
                  className="w-full px-3 py-2 border border-indigo-300 rounded text-sm focus:ring-2 focus:ring-indigo-500"
                  rows={2}
                />
              </div>

              {/* Errore */}
              {error && (
                <div className="p-3 bg-red-100 border border-red-300 rounded text-red-700 text-sm">
                  {error}
                </div>
              )}

              {/* Pulsanti */}
              <div className="flex justify-end gap-3 pt-2">
                <button
                  onClick={onClose}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded font-medium"
                  disabled={submitting}
                >
                  Annulla
                </button>
                <button
                  onClick={handleSubmit}
                  disabled={submitting}
                  className={`px-4 py-2 rounded font-medium flex items-center gap-2 ${
                    !submitting
                      ? 'bg-indigo-600 hover:bg-indigo-700 text-white'
                      : 'bg-slate-300 text-slate-500 cursor-not-allowed'
                  }`}
                >
                  {submitting ? (
                    <>
                      <span className="animate-spin">⏳</span>
                      Risoluzione in corso...
                    </>
                  ) : (
                    <>
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                      {livelloPropagazione === 'ORDINE'
                        ? `Risolvi ${conteggi.ordine} Anomalie`
                        : `Risolvi ${conteggi.globale} Anomalie`}
                    </>
                  )}
                </button>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}

// =============================================================================
// v10.6: Sub-componente Risoluzione ESPOSITORE (senza propagazione)
// =============================================================================

function EspositoreRisolviSection({ anomalia, onSuccess }) {
  const [note, setNote] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  // Recupera operatore dal localStorage
  const operatore = React.useMemo(() => {
    try {
      const user = JSON.parse(localStorage.getItem('servo_user') || '{}');
      return user.username || 'operatore';
    } catch {
      return 'operatore';
    }
  }, []);

  const handleRisolvi = async () => {
    setSubmitting(true);
    setError(null);

    try {
      // Usa l'endpoint semplice di risoluzione (senza propagazione)
      const response = await anomalieApi.risolviDettaglio(anomalia.id_anomalia, {
        note: note || `Anomalia espositore risolta da ${operatore}`
      });

      if (response.success) {
        setSuccess(true);
        setTimeout(() => {
          onSuccess?.();
        }, 1000);
      } else {
        setError(response.error || 'Errore durante risoluzione');
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Errore durante risoluzione');
    } finally {
      setSubmitting(false);
    }
  };

  if (success) {
    return (
      <div className="bg-green-50 rounded-lg p-4">
        <div className="flex items-center gap-2 text-green-700 font-medium">
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
          Anomalia Espositore Risolta
        </div>
      </div>
    );
  }

  return (
    <div className="bg-amber-50 rounded-lg p-4">
      <h4 className="font-semibold text-amber-800 mb-3 flex items-center gap-2">
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        Risolvi Anomalia Espositore
      </h4>

      <p className="text-sm text-amber-700 mb-3">
        Le anomalie espositore sono specifiche per questo ordine e non vengono propagate.
        Verifica i dati del parent/child prima di risolvere.
      </p>

      {error && (
        <div className="mb-3 p-3 bg-red-100 border border-red-300 rounded text-red-700 text-sm">
          {error}
        </div>
      )}

      <div className="mb-3">
        <label className="block text-sm font-medium text-amber-700 mb-1">
          Note (opzionale)
        </label>
        <input
          type="text"
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="Aggiungi una nota..."
          className="w-full px-3 py-2 border border-amber-300 rounded focus:ring-2 focus:ring-amber-500 focus:border-amber-500"
        />
      </div>

      <button
        onClick={handleRisolvi}
        disabled={submitting}
        className={`w-full py-2 rounded font-medium flex items-center justify-center gap-2 ${
          submitting
            ? 'bg-amber-300 text-amber-600 cursor-not-allowed'
            : 'bg-amber-600 hover:bg-amber-700 text-white'
        }`}
      >
        {submitting ? (
          <>
            <span className="animate-spin">⏳</span>
            Risoluzione in corso...
          </>
        ) : (
          <>
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            Risolvi Anomalia
          </>
        )}
      </button>
    </div>
  );
}

// v11.0: AicCorrectionSection rimosso - ora usa AicAssignmentModal unificato (TIER 2.1)

export default AnomaliaDetailModal;
