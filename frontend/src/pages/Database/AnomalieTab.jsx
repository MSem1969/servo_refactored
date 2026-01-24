// =============================================================================
// SERV.O v10.4 - ANOMALIE TAB COMPONENT (DATABASE PAGE)
// =============================================================================

import React from 'react';
import { anomalieApi } from '../../api';
import {
  getTipoAnomaliaColor,
  getLivelloBadgeClass,
  getStatoAnomaliaColor,
  getNormalizedLevel,
  sortAnomalieByTipo
} from '../../common';

export default function AnomalieTab({
  anomalieList,
  loading,
  filters,
  setFilters,
  selectedAnomalies,
  onToggleSelect,
  onSelectAll,
  onReload,
  onResolveSelected,
  onLoadDetail,
  onOpenOrdine,
  onReloadCount
}) {
  const handleQuickResolve = async (anomalia) => {
    try {
      await anomalieApi.update(anomalia.id_anomalia, { stato: 'RISOLTA', nota: 'Risolta manualmente' });
      onReload();
      onReloadCount();
    } catch (err) {
      alert('Errore: ' + err.message);
    }
  };

  const handleQuickIgnore = async (anomalia) => {
    try {
      await anomalieApi.update(anomalia.id_anomalia, { stato: 'IGNORATA', nota: 'Ignorata manualmente' });
      onReload();
      onReloadCount();
    } catch (err) {
      alert('Errore: ' + err.message);
    }
  };

  return (
    <div className="p-4">
      {/* Filtri */}
      <div className="flex gap-4 mb-4 flex-wrap">
        <select
          value={filters.tipo}
          onChange={(e) => setFilters(f => ({ ...f, tipo: e.target.value }))}
          className="px-3 py-2 border border-slate-300 rounded-lg text-sm"
        >
          <option value="">Tutti i tipi</option>
          <option value="ESPOSITORE">Espositore</option>
          <option value="NO_AIC">No AIC</option>
          <option value="LOOKUP_FALLITO">Lookup Fallito</option>
          <option value="DUPLICATO">Duplicato</option>
          <option value="PREZZO_ZERO">Prezzo Zero</option>
          <option value="QTA_ANOMALA">Quantita Anomala</option>
          <option value="SCONTO_ANOMALO">Sconto Anomalo</option>
        </select>

        <select
          value={filters.stato}
          onChange={(e) => setFilters(f => ({ ...f, stato: e.target.value }))}
          className="px-3 py-2 border border-slate-300 rounded-lg text-sm"
        >
          <option value="">Tutti gli stati</option>
          <option value="APERTA">Aperta</option>
          <option value="IN_GESTIONE">In gestione</option>
          <option value="RISOLTA">Risolta</option>
          <option value="IGNORATA">Ignorata</option>
        </select>

        <button
          onClick={onReload}
          className="px-4 py-2 bg-slate-100 hover:bg-slate-200 rounded-lg text-sm"
        >
          🔄 Ricarica
        </button>

        {selectedAnomalies.length > 0 && (
          <button
            onClick={onResolveSelected}
            className="px-4 py-2 bg-green-500 hover:bg-green-600 text-white rounded-lg text-sm"
          >
            ✓ Risolvi ({selectedAnomalies.length})
          </button>
        )}
      </div>

      {/* Tabella */}
      {loading ? (
        <div className="text-center py-8 text-slate-500">
          <div className="animate-spin text-2xl mb-2">⏳</div>
          <p>Caricamento anomalie...</p>
        </div>
      ) : anomalieList.length === 0 ? (
        <div className="text-center py-8 text-slate-500">
          <div className="text-4xl mb-2">✅</div>
          <p>Nessuna anomalia trovata</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50">
              <tr>
                <th className="p-3 text-left w-10">
                  <input
                    type="checkbox"
                    checked={selectedAnomalies.length === anomalieList.length && anomalieList.length > 0}
                    onChange={(e) => onSelectAll(e.target.checked)}
                  />
                </th>
                <th className="p-3 text-left">ID</th>
                <th className="p-3 text-left">Tipo</th>
                <th className="p-3 text-left">Ordine</th>
                <th className="p-3 text-left">Descrizione</th>
                <th className="p-3 text-left">Severita</th>
                <th className="p-3 text-left">Stato</th>
                <th className="p-3 text-left">Data</th>
                <th className="p-3 text-left">Azioni</th>
              </tr>
            </thead>
            <tbody>
              {anomalieList.map((anomalia) => (
                <tr
                  key={anomalia.id_anomalia}
                  className={`border-b border-slate-100 hover:bg-slate-50 cursor-pointer ${
                    selectedAnomalies.includes(anomalia.id_anomalia) ? 'bg-blue-50' : ''
                  }`}
                  onClick={() => onLoadDetail(anomalia.id_anomalia)}
                >
                  <td className="p-3" onClick={(e) => e.stopPropagation()}>
                    <input
                      type="checkbox"
                      checked={selectedAnomalies.includes(anomalia.id_anomalia)}
                      onChange={() => onToggleSelect(anomalia.id_anomalia)}
                    />
                  </td>
                  <td className="p-3 font-mono text-xs">{anomalia.id_anomalia}</td>
                  <td className="p-3">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${getTipoAnomaliaColor(anomalia.tipo_anomalia)}`}>
                      {anomalia.tipo_anomalia}
                    </span>
                  </td>
                  <td className="p-3">
                    <div className="flex flex-col">
                      <span className="font-mono text-xs">{anomalia.numero_ordine || '-'}</span>
                      {anomalia.vendor && (
                        <span className="text-xs text-slate-500">{anomalia.vendor}</span>
                      )}
                    </div>
                  </td>
                  <td className="p-3 max-w-xs truncate" title={anomalia.descrizione}>
                    {anomalia.descrizione}
                  </td>
                  <td className="p-3">
                    <span className={`px-2 py-1 rounded text-xs font-bold ${getLivelloBadgeClass(anomalia.livello || anomalia.severita)}`}>
                      {getNormalizedLevel(anomalia)}
                    </span>
                  </td>
                  <td className="p-3">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${getStatoAnomaliaColor(anomalia.stato)}`}>
                      {anomalia.stato}
                    </span>
                  </td>
                  <td className="p-3 text-xs text-slate-500">
                    {anomalia.data_creazione ? new Date(anomalia.data_creazione).toLocaleDateString('it-IT') : '-'}
                  </td>
                  <td className="p-3" onClick={(e) => e.stopPropagation()}>
                    <div className="flex gap-1">
                      {anomalia.id_testata && (
                        <button
                          onClick={() => onOpenOrdine?.(anomalia.id_testata)}
                          className="px-2 py-1 text-xs bg-blue-100 hover:bg-blue-200 text-blue-700 rounded"
                          title="Apri ordine"
                        >
                          📋
                        </button>
                      )}
                      <button
                        onClick={() => handleQuickResolve(anomalia)}
                        className="px-2 py-1 text-xs bg-green-100 hover:bg-green-200 text-green-700 rounded"
                        disabled={anomalia.stato === 'RISOLTA'}
                        title="Risolvi"
                      >
                        ✓
                      </button>
                      <button
                        onClick={() => handleQuickIgnore(anomalia)}
                        className="px-2 py-1 text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 rounded"
                        disabled={anomalia.stato === 'IGNORATA'}
                        title="Ignora"
                      >
                        ✗
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
