// =============================================================================
// TRACCIATI PAGE - RICERCA E ANALISI v6.2
// =============================================================================
// Pagina per ricerca e analisi tracciati esportati
// Filtri per ordini, clienti, vendor, date
// =============================================================================

import React, { useState, useEffect, useCallback } from 'react';
import { tracciatiApi, getApiBaseUrl } from '../api';
import { Button, StatusBadge, VendorBadge, Loading } from '../common';

/**
 * Componente TracciatiPage - Ricerca e Analisi
 *
 * FUNZIONALITA:
 * - Ricerca tracciati per numero ordine, cliente, vendor
 * - Filtro per date esportazione
 * - Visualizzazione storico esportazioni
 * - Download file TO_T e TO_D
 */
const TracciatiPage = () => {
  // State ricerca
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filters, setFilters] = useState({
    numero_ordine: '',
    ragione_sociale: '',
    vendor: '',
    data_da: '',
    data_a: '',
    stato: ''
  });

  // State statistiche
  const [stats, setStats] = useState({
    totale_esportati: 0,
    esportazioni_oggi: 0,
    vendors: []
  });

  // Lista vendor disponibili - v11.2 + COOPER
  const vendorOptions = ['DOC_GENERICI', 'CODIFI', 'COOPER', 'MENARINI', 'OPELLA', 'CHIESI', 'ANGELINI', 'BAYER', 'RECKITT'];

  // Carica dati iniziali
  const loadInitialData = useCallback(async () => {
    try {
      setLoading(true);
      // Carica ultimi 50 tracciati esportati
      const res = await fetch(`${getApiBaseUrl()}/api/v1/tracciati/ricerca?limit=50`);
      const data = await res.json();

      if (data.success) {
        setResults(data.data || []);

        // Calcola statistiche
        const oggi = new Date().toISOString().split('T')[0];
        const esportatiOggi = (data.data || []).filter(r =>
          r.esportazione?.data?.startsWith(oggi)
        ).length;

        setStats({
          totale_esportati: data.count || 0,
          esportazioni_oggi: esportatiOggi,
          vendors: [...new Set((data.data || []).map(r => r.vendor))]
        });
      }
    } catch (err) {
      console.error('Errore caricamento:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadInitialData();
  }, [loadInitialData]);

  // Esegui ricerca
  const handleSearch = async (e) => {
    e?.preventDefault();
    setLoading(true);

    try {
      const params = new URLSearchParams();
      if (filters.numero_ordine) params.append('numero_ordine', filters.numero_ordine);
      if (filters.ragione_sociale) params.append('ragione_sociale', filters.ragione_sociale);
      if (filters.vendor) params.append('vendor', filters.vendor);
      if (filters.data_da) params.append('data_da', filters.data_da);
      if (filters.data_a) params.append('data_a', filters.data_a);
      if (filters.stato) params.append('stato', filters.stato);
      params.append('limit', '100');

      const res = await fetch(`${getApiBaseUrl()}/api/v1/tracciati/ricerca?${params}`);
      const data = await res.json();

      if (data.success) {
        setResults(data.data || []);
      }
    } catch (err) {
      console.error('Errore ricerca:', err);
    } finally {
      setLoading(false);
    }
  };

  // Reset filtri
  const handleReset = () => {
    setFilters({
      numero_ordine: '',
      ragione_sociale: '',
      vendor: '',
      data_da: '',
      data_a: '',
      stato: ''
    });
    loadInitialData();
  };

  // Download file
  const handleDownload = async (filename) => {
    if (!filename) return;

    try {
      const response = await fetch(`${getApiBaseUrl()}/api/v1/tracciati/download/${filename}`);

      if (!response.ok) {
        throw new Error('File non trovato');
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

    } catch (err) {
      alert('Errore download: ' + err.message);
    }
  };

  // Format data
  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    try {
      return new Date(dateStr).toLocaleDateString('it-IT', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-emerald-100 rounded-lg flex items-center justify-center">
              📤
            </div>
            <div>
              <p className="text-xs text-slate-600 font-medium">Ordini Esportati</p>
              <p className="text-xl font-bold text-slate-800">{stats.totale_esportati}</p>
            </div>
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
              📅
            </div>
            <div>
              <p className="text-xs text-slate-600 font-medium">Esportati Oggi</p>
              <p className="text-xl font-bold text-slate-800">{stats.esportazioni_oggi}</p>
            </div>
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
              🏭
            </div>
            <div>
              <p className="text-xs text-slate-600 font-medium">Vendor Attivi</p>
              <p className="text-xl font-bold text-slate-800">{stats.vendors.length}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Filtri Ricerca */}
      <div className="bg-white rounded-xl border border-slate-200 p-4">
        <h3 className="font-medium text-slate-800 mb-4 flex items-center gap-2">
          🔍 Ricerca Tracciati
        </h3>

        <form onSubmit={handleSearch} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4">
            {/* Numero Ordine */}
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">
                Numero Ordine
              </label>
              <input
                type="text"
                value={filters.numero_ordine}
                onChange={(e) => setFilters({...filters, numero_ordine: e.target.value})}
                placeholder="Es: 271717338"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            {/* Cliente */}
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">
                Cliente / Farmacia
              </label>
              <input
                type="text"
                value={filters.ragione_sociale}
                onChange={(e) => setFilters({...filters, ragione_sociale: e.target.value})}
                placeholder="Ragione sociale..."
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            {/* Vendor */}
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">
                Vendor
              </label>
              <select
                value={filters.vendor}
                onChange={(e) => setFilters({...filters, vendor: e.target.value})}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="">Tutti</option>
                {vendorOptions.map(v => (
                  <option key={v} value={v}>{v}</option>
                ))}
              </select>
            </div>

            {/* Data Da */}
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">
                Data Da
              </label>
              <input
                type="date"
                value={filters.data_da}
                onChange={(e) => setFilters({...filters, data_da: e.target.value})}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            {/* Data A */}
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">
                Data A
              </label>
              <input
                type="date"
                value={filters.data_a}
                onChange={(e) => setFilters({...filters, data_a: e.target.value})}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            {/* Stato */}
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">
                Stato
              </label>
              <select
                value={filters.stato}
                onChange={(e) => setFilters({...filters, stato: e.target.value})}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="">Tutti</option>
                <option value="ESTRATTO">Estratto</option>
                <option value="CONFERMATO">Confermato</option>
                <option value="ANOMALIA">Anomalia</option>
                <option value="PARZ_EVASO">Parzialmente Evaso</option>
                <option value="EVASO">Evaso</option>
                <option value="ARCHIVIATO">Archiviato</option>
              </select>
            </div>
          </div>

          {/* Bottoni */}
          <div className="flex gap-3">
            <Button type="submit" variant="primary" disabled={loading}>
              🔍 Cerca
            </Button>
            <Button type="button" variant="secondary" onClick={handleReset}>
              🔄 Reset
            </Button>
            <Button type="button" variant="ghost" onClick={loadInitialData} disabled={loading}>
              ↻ Aggiorna
            </Button>
          </div>
        </form>
      </div>

      {/* Risultati */}
      <div className="bg-white rounded-xl border border-slate-200">
        <div className="p-4 border-b border-slate-200 flex justify-between items-center">
          <h3 className="font-medium text-slate-800">
            📋 Tracciati Esportati ({results.length})
          </h3>
        </div>

        {loading ? (
          <div className="p-8">
            <Loading text="Ricerca in corso..." />
          </div>
        ) : results.length === 0 ? (
          <div className="p-8 text-center">
            <div className="text-4xl mb-3">📭</div>
            <h3 className="text-lg font-medium text-slate-800 mb-2">Nessun risultato</h3>
            <p className="text-slate-600">Prova a modificare i filtri di ricerca</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-slate-50 border-b border-slate-200">
                <tr>
                  <th className="text-left p-3 text-xs font-medium text-slate-600 uppercase">Ordine</th>
                  <th className="text-left p-3 text-xs font-medium text-slate-600 uppercase">Vendor</th>
                  <th className="text-left p-3 text-xs font-medium text-slate-600 uppercase">Cliente</th>
                  <th className="text-left p-3 text-xs font-medium text-slate-600 uppercase">Righe</th>
                  <th className="text-left p-3 text-xs font-medium text-slate-600 uppercase">Stato</th>
                  <th className="text-left p-3 text-xs font-medium text-slate-600 uppercase">Data Export</th>
                  <th className="text-left p-3 text-xs font-medium text-slate-600 uppercase">Validato Da</th>
                  <th className="text-left p-3 text-xs font-medium text-slate-600 uppercase">Download</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {results.map((item) => (
                  <tr key={item.id_testata} className="hover:bg-slate-50">
                    <td className="p-3">
                      <div className="font-mono text-sm font-medium text-slate-800">
                        {item.numero_ordine}
                      </div>
                      <div className="text-xs text-slate-500">
                        ID: {item.id_testata}
                      </div>
                    </td>
                    <td className="p-3">
                      <VendorBadge vendor={item.vendor} size="xs" />
                    </td>
                    <td className="p-3">
                      <div className="max-w-48">
                        <div className="text-sm font-medium text-slate-800 truncate" title={item.cliente?.ragione_sociale?.toUpperCase()}>
                          {item.cliente?.ragione_sociale?.toUpperCase() || '-'}
                        </div>
                        <div className="text-xs text-slate-500">
                          {item.cliente?.citta?.toUpperCase()} {item.cliente?.provincia && `(${item.cliente.provincia.toUpperCase()})`}
                        </div>
                        {item.cliente?.min_id && (
                          <div className="text-xs text-slate-400 font-mono">
                            MIN: {item.cliente.min_id}
                          </div>
                        )}
                      </div>
                    </td>
                    <td className="p-3 text-sm text-slate-600">
                      {item.num_righe || 0}
                    </td>
                    <td className="p-3">
                      <StatusBadge
                        status={item.stato?.toLowerCase()}
                        label={item.stato}
                        size="xs"
                      />
                    </td>
                    <td className="p-3">
                      <div className="text-sm text-slate-800">
                        {formatDate(item.esportazione?.data)}
                      </div>
                    </td>
                    <td className="p-3">
                      <div className="text-sm text-slate-600">
                        {item.validato_da || '-'}
                      </div>
                    </td>
                    <td className="p-3">
                      <div className="flex gap-1">
                        {item.esportazione?.file_to_t && (
                          <Button
                            variant="ghost"
                            size="xs"
                            onClick={() => handleDownload(item.esportazione.file_to_t)}
                            title="Scarica TO_T (Testata)"
                          >
                            📄 T
                          </Button>
                        )}
                        {item.esportazione?.file_to_d && (
                          <Button
                            variant="ghost"
                            size="xs"
                            onClick={() => handleDownload(item.esportazione.file_to_d)}
                            title="Scarica TO_D (Dettaglio)"
                          >
                            📄 D
                          </Button>
                        )}
                        {!item.esportazione?.file_to_t && !item.esportazione?.file_to_d && (
                          <span className="text-xs text-slate-400">-</span>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default TracciatiPage;
