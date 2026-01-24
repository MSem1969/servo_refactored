/**
 * AnomaliaDetailModal Component - v6.2 Refactoring
 * Modale dettaglio anomalia con gestione:
 * - ESPOSITORE: parent/child editing
 * - LOOKUP: ricerca farmacia/parafarmacia
 * Usato da DatabasePage e OrdineDetailPage
 */
import React, { useState, useEffect, useCallback } from 'react';
import { TipoAnomaliaBadge, StatoAnomaliaBadge, SeveritaBadge } from './Badge';
import { lookupApi } from '../api';

export function AnomaliaDetailModal({
  isOpen,
  onClose,
  anomaliaDetail,
  loading = false,
  onSaveParent,
  onRisolvi,
  onOpenOrdine,
  onAssignFarmacia,
}) {
  // Stato editing parent (per ESPOSITORE)
  const [isEditingParent, setIsEditingParent] = useState(false);
  const [editingRigaParent, setEditingRigaParent] = useState(null);

  // Stato per LOOKUP
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [selectedResult, setSelectedResult] = useState(null);

  // Determina tipo di anomalia
  const isLookupAnomalia = anomaliaDetail?.anomalia?.tipo_anomalia === 'LOOKUP' ||
    anomaliaDetail?.anomalia?.codice_anomalia?.startsWith('LKP-');

  // Reset editing state when modal opens/closes or data changes
  useEffect(() => {
    if (anomaliaDetail?.riga_parent) {
      setEditingRigaParent({
        q_venduta: anomaliaDetail.riga_parent.q_venduta || 0,
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

  if (!isOpen) return null;

  const handleClose = () => {
    setIsEditingParent(false);
    setEditingRigaParent(null);
    onClose();
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
        descrizione: anomaliaDetail.riga_parent.descrizione || '',
        codice_originale: anomaliaDetail.riga_parent.codice_originale || '',
        prezzo_netto: anomaliaDetail.riga_parent.prezzo_netto || anomaliaDetail.riga_parent.prezzo_pubblico || 0,
        note_allestimento: anomaliaDetail.riga_parent.note_allestimento || ''
      });
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl w-[90vw] max-w-4xl max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-slate-200">
          <h3 className="text-lg font-semibold text-slate-800">
            Dettaglio Anomalia {anomaliaDetail?.anomalia?.id_anomalia && `#${anomaliaDetail.anomalia.id_anomalia}`}
          </h3>
          <div className="flex items-center gap-2">
            {/* Pulsante Visualizza PDF */}
            {anomaliaDetail?.anomalia?.pdf_file && (
              <a
                href={`/api/v1/upload/pdf/${encodeURIComponent(anomaliaDetail.anomalia.pdf_file)}`}
                target="_blank"
                rel="noopener noreferrer"
                className="px-3 py-2 bg-blue-100 hover:bg-blue-200 text-blue-700 rounded-lg text-sm flex items-center gap-1"
              >
                Visualizza PDF
              </a>
            )}
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
                onOpenOrdine={onOpenOrdine}
                onClose={handleClose}
              />

              {/* LOOKUP ANOMALIA - Mostra UI ricerca farmacia */}
              {isLookupAnomalia && (
                <LookupSection
                  idTestata={anomaliaDetail.anomalia.id_testata}
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
                />
              )}

              {/* ESPOSITORE ANOMALIA - Mostra UI parent/child */}
              {!isLookupAnomalia && (
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
            </div>
          ) : (
            <div className="text-center py-8 text-slate-500">
              Nessun dato disponibile
            </div>
          )}
        </div>

        {/* Footer */}
        {anomaliaDetail && anomaliaDetail.anomalia?.stato !== 'RISOLTA' && (
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
                className="px-4 py-2 bg-green-500 hover:bg-green-600 text-white rounded flex items-center gap-2"
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
function AnomaliaInfo({ anomalia, onOpenOrdine, onClose }) {
  if (!anomalia) return null;

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
          <SeveritaBadge severita={anomalia.severita || 'INFO'} />
        </div>
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
                <label className="block text-xs text-slate-500 mb-1">Quantita</label>
                <div className="px-3 py-2 bg-white border border-slate-200 rounded text-sm">
                  {rigaParent.q_venduta || 0}
                </div>
              </div>
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-1">Descrizione</label>
              <div className="px-3 py-2 bg-white border border-slate-200 rounded text-sm">
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
                <label className="block text-xs text-slate-500 mb-1">Quantita</label>
                <input
                  type="number"
                  value={editingData?.q_venduta || 0}
                  onChange={(e) => onEditChange(prev => ({...prev, q_venduta: parseInt(e.target.value) || 0}))}
                  className="w-full px-3 py-2 border border-blue-300 rounded text-sm bg-white focus:ring-2 focus:ring-blue-500"
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
                  <td className="p-2 truncate max-w-xs" title={child.descrizione}>{child.descrizione}</td>
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
  ordineData,
  searchQuery,
  setSearchQuery,
  searchResults,
  searchLoading,
  selectedResult,
  setSelectedResult,
  onSearch,
  onAssign,
  onAssignManualMinId
}) {
  const [manualMinId, setManualMinId] = React.useState('');
  const [mode, setMode] = React.useState('alternative'); // 'alternative', 'search', 'manual'

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

  const handleManualAssign = () => {
    if (manualMinId && manualMinId.length >= 6 && onAssignManualMinId) {
      onAssignManualMinId(manualMinId);
    }
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
            <span>{ordineData?.ragione_sociale || '-'}</span>
          </div>
          <div className="col-span-2">
            <span className="text-slate-500">Indirizzo:</span>{' '}
            <span>{ordineData?.indirizzo || '-'}</span>
          </div>
          <div>
            <span className="text-slate-500">CAP:</span>{' '}
            <span>{ordineData?.cap || '-'}</span>
          </div>
          <div>
            <span className="text-slate-500">Citta:</span>{' '}
            <span>{ordineData?.citta || '-'}</span>
          </div>
          <div>
            <span className="text-slate-500">Provincia:</span>{' '}
            <span>{ordineData?.provincia || '-'}</span>
          </div>
        </div>
      </div>

      {/* Toggle tra modalita */}
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
                              <span className="font-medium">{farm.ragione_sociale}</span>
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
                              <span className="font-medium">{para.ragione_sociale || para.sito_logistico}</span>
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
                  <span className="ml-2">{selectedResult.ragione_sociale || selectedResult.sito_logistico}</span>
                  <span className="ml-2 text-xs text-slate-500">
                    ({selectedResult.tipo === 'FARMACIA' ? selectedResult.min_id : selectedResult.codice_sito})
                  </span>
                </div>
                <button
                  onClick={onAssign}
                  className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded text-sm font-medium"
                >
                  Assegna e Risolvi
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
          <div className="flex gap-2 mb-4">
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
                        <span className="ml-2 font-medium">{result.ragione_sociale}</span>
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
                  <span className="ml-2">{selectedResult.ragione_sociale}</span>
                  <span className="ml-2 text-xs text-slate-500">
                    ({selectedResult.tipo === 'FARMACIA' ? selectedResult.min_id : selectedResult.codice_sito})
                  </span>
                </div>
                <button
                  onClick={onAssign}
                  className="px-4 py-2 bg-green-500 hover:bg-green-600 text-white rounded text-sm font-medium"
                >
                  Assegna e Risolvi
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
              onClick={handleManualAssign}
              disabled={!manualMinId || manualMinId.length < 6}
              className="px-4 py-2 bg-orange-500 hover:bg-orange-600 disabled:bg-orange-300 text-white rounded text-sm font-medium"
            >
              Assegna MIN_ID
            </button>
          </div>

          {manualMinId && manualMinId.length >= 6 && (
            <div className="p-3 bg-orange-100 border border-orange-200 rounded">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-sm font-medium text-orange-800">MIN_ID da assegnare:</span>
                  <span className="ml-2 font-mono text-lg">{manualMinId.padStart(9, '0')}</span>
                </div>
              </div>
              <p className="text-xs text-orange-600 mt-2">
                L'ordine verra aggiornato con questo codice ministeriale e l'anomalia sara risolta.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default AnomaliaDetailModal;
