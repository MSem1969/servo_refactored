// =============================================================================
// SERV.O v8.1 - EXPORT PAGE
// =============================================================================
// Pagina esportazione dati con filtri e preview
// =============================================================================

import React, { useState, useEffect, useMemo } from 'react';
import { reportApi } from '../api';
import { Button, Loading, ErrorBox } from '../common';

// =============================================================================
// COMPONENTE ACCORDION TAB
// =============================================================================
const AccordionTab = ({ title, icon, isOpen, onClick, children, badge, onClear }) => (
  <div className="border border-slate-200 rounded-lg overflow-hidden">
    <button
      onClick={onClick}
      className={`w-full flex items-center justify-between px-4 py-3 text-left transition-colors ${
        isOpen ? 'bg-blue-50 border-b border-slate-200' : 'bg-white hover:bg-slate-50'
      }`}
    >
      <div className="flex items-center gap-2">
        <span>{icon}</span>
        <span className="font-medium text-slate-700">{title}</span>
        {badge && (
          <span className="px-2 py-0.5 text-xs font-medium bg-blue-100 text-blue-700 rounded-full">
            {badge}
          </span>
        )}
        {badge && onClear && (
          <span
            onClick={(e) => {
              e.stopPropagation();
              onClear();
            }}
            className="px-1.5 py-0.5 text-xs font-medium bg-red-100 text-red-600 rounded-full hover:bg-red-200 cursor-pointer"
            title="Azzera filtro"
          >
            ✕
          </span>
        )}
      </div>
      <svg
        className={`w-5 h-5 text-slate-400 transition-transform ${isOpen ? 'rotate-180' : ''}`}
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
      </svg>
    </button>
    {isOpen && <div className="p-4 bg-white">{children}</div>}
  </div>
);

// =============================================================================
// COMPONENTE CHECKBOX GROUP
// =============================================================================
const CheckboxGroup = ({ options, selected, onChange }) => {
  if (!options || options.length === 0) {
    return (
      <div className="text-sm text-slate-500 italic py-2">
        Nessuna opzione disponibile
      </div>
    );
  }

  return (
    <div className="space-y-1">
      {options.map((opt) => (
        <label
          key={opt.value}
          className={`flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer transition-colors ${
            selected.includes(opt.value)
              ? 'bg-blue-50 border border-blue-200'
              : 'bg-slate-50 border border-slate-200 hover:bg-slate-100'
          }`}
        >
          <input
            type="checkbox"
            checked={selected.includes(opt.value)}
            onChange={() => {
              if (selected.includes(opt.value)) {
                onChange(selected.filter((v) => v !== opt.value));
              } else {
                onChange([...selected, opt.value]);
              }
            }}
            className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
          />
          <span className="text-sm text-slate-700">{opt.label}</span>
        </label>
      ))}
    </div>
  );
};

// =============================================================================
// COMPONENTE SORTABLE HEADER
// =============================================================================
const SortableHeader = ({ label, field, sortConfig, onSort }) => {
  const isActive = sortConfig.field === field;
  return (
    <th
      className="px-4 py-3 text-left text-xs font-semibold text-slate-600 uppercase tracking-wider cursor-pointer hover:bg-slate-100 select-none"
      onClick={() => onSort(field)}
    >
      <div className="flex items-center gap-1">
        {label}
        <span className={`transition-opacity ${isActive ? 'opacity-100' : 'opacity-30'}`}>
          {isActive && sortConfig.direction === 'desc' ? '↓' : '↑'}
        </span>
      </div>
    </th>
  );
};

// =============================================================================
// PAGINA PRINCIPALE EXPORT
// =============================================================================
export default function ExportPage() {
  // State filtri
  const [openTab, setOpenTab] = useState(null);
  const [filters, setFilters] = useState({
    tipo_data: 'ordine', // 'ordine' o 'consegna'
    data_inizio: '',
    data_fine: '',
    vendors: [],
    depositi: [], // v10.0: Deposito di riferimento
    tipo_prodotto: [],
    stati: [],
    clienti: [],
    aic: [],
  });

  // State opzioni disponibili
  const [vendorOptions, setVendorOptions] = useState([]);
  const [depositiOptions, setDepositiOptions] = useState([]); // v10.0
  const [statiOptions, setStatiOptions] = useState([]);
  const [clientiOptions, setClientiOptions] = useState([]);
  const [prodottiOptions, setProdottiOptions] = useState([]);
  const [clientiSearch, setClientiSearch] = useState('');
  const [prodottiSearch, setProdottiSearch] = useState('');

  // State dati e UI
  const [reportData, setReportData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadingOptions, setLoadingOptions] = useState(true);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState(null);

  // State ordinamento
  const [sortConfig, setSortConfig] = useState({ field: 'vendor', direction: 'asc' });

  // Label leggibili per stati
  const STATO_LABELS = {
    'DA_EVADERE': 'Da Evadere',
  };

  // Opzioni tipo prodotto (statiche)
  const tipoProdottoOptions = [
    { value: 'VENDITA', label: 'Vendita' },
    { value: 'OMAGGI', label: 'Omaggi' },
    { value: 'SC_MERCE', label: 'Sconto Merce' },
    { value: 'ESPOSITORI', label: 'Espositori' },
  ];

  // Helper: costruisce oggetto filtri per cascata (esclude il filtro target)
  const buildCascadeFilters = (exclude = []) => {
    const cascade = {};
    if (filters.tipo_data) cascade.tipo_data = filters.tipo_data;
    if (!exclude.includes('data_inizio') && filters.data_inizio) cascade.data_inizio = filters.data_inizio;
    if (!exclude.includes('data_fine') && filters.data_fine) cascade.data_fine = filters.data_fine;
    if (!exclude.includes('vendors') && filters.vendors.length > 0) cascade.vendors = filters.vendors.join(',');
    if (!exclude.includes('depositi') && filters.depositi.length > 0) cascade.depositi = filters.depositi.join(',');
    if (!exclude.includes('stati') && filters.stati.length > 0) cascade.stati = filters.stati.join(',');
    if (!exclude.includes('clienti') && filters.clienti.length > 0) cascade.clienti = filters.clienti.join(',');
    if (!exclude.includes('aic') && filters.aic.length > 0) cascade.aic = filters.aic.join(',');
    return cascade;
  };

  // Carica opzioni filtri iniziale (solo al mount)
  useEffect(() => {
    const loadOptions = async () => {
      try {
        setLoadingOptions(true);
        const [vendorsRes, depositiRes, statiRes] = await Promise.all([
          reportApi.getVendors({}),
          reportApi.getDepositi({}),
          reportApi.getStati({}),
        ]);
        setVendorOptions(vendorsRes.vendors?.map((v) => ({ value: v, label: v })) || []);
        setDepositiOptions(depositiRes.depositi?.map((d) => ({ value: d, label: d })) || []);
        setStatiOptions(statiRes.stati?.map((s) => ({ value: s, label: STATO_LABELS[s] || s })) || []);
      } catch (err) {
        console.error('Errore caricamento opzioni:', err);
        setError('Errore caricamento filtri: ' + (err.response?.data?.detail || err.message));
      } finally {
        setLoadingOptions(false);
      }
    };
    loadOptions();
  }, []);

  // Reload vendors quando cambiano altri filtri (cascata)
  useEffect(() => {
    // Skip al mount - gestito da useEffect iniziale
    if (loadingOptions) return;

    const reloadVendors = async () => {
      try {
        const cascade = buildCascadeFilters(['vendors']);
        const res = await reportApi.getVendors(cascade);
        setVendorOptions(res.vendors?.map((v) => ({ value: v, label: v })) || []);
      } catch (err) {
        console.error('Errore reload vendors:', err);
      }
    };

    const debounce = setTimeout(reloadVendors, 150);
    return () => clearTimeout(debounce);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters.data_inizio, filters.data_fine, filters.depositi, filters.stati, filters.clienti, filters.aic]);

  // Reload depositi quando cambiano altri filtri (cascata)
  useEffect(() => {
    // Skip al mount - gestito da useEffect iniziale
    if (loadingOptions) return;

    const reloadDepositi = async () => {
      try {
        const cascade = buildCascadeFilters(['depositi']);
        const res = await reportApi.getDepositi(cascade);
        setDepositiOptions(res.depositi?.map((d) => ({ value: d, label: d })) || []);
      } catch (err) {
        console.error('Errore reload depositi:', err);
      }
    };

    const debounce = setTimeout(reloadDepositi, 150);
    return () => clearTimeout(debounce);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters.data_inizio, filters.data_fine, filters.vendors, filters.stati, filters.clienti, filters.aic]);

  // Reload stati quando cambiano altri filtri (cascata)
  useEffect(() => {
    // Skip al mount - gestito da useEffect iniziale
    if (loadingOptions) return;

    const reloadStati = async () => {
      try {
        const cascade = buildCascadeFilters(['stati']);
        const res = await reportApi.getStati(cascade);
        setStatiOptions(res.stati?.map((s) => ({ value: s, label: s })) || []);
      } catch (err) {
        console.error('Errore reload stati:', err);
      }
    };

    const debounce = setTimeout(reloadStati, 150);
    return () => clearTimeout(debounce);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters.data_inizio, filters.data_fine, filters.vendors, filters.depositi, filters.clienti, filters.aic]);

  // Cerca clienti (con cascata)
  useEffect(() => {
    const searchClienti = async () => {
      try {
        const cascade = buildCascadeFilters(['clienti']);
        const res = await reportApi.searchClienti(clientiSearch || null, 100, cascade);
        setClientiOptions(
          res.clienti?.map((c) => ({
            value: c.min_id,
            label: `${c.min_id} - ${c.ragione_sociale || 'N/D'}`,
          })) || []
        );
      } catch (err) {
        console.error('Errore ricerca clienti:', err);
      }
    };

    const debounce = setTimeout(searchClienti, 300);
    return () => clearTimeout(debounce);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clientiSearch, filters.data_inizio, filters.data_fine, filters.vendors, filters.depositi, filters.stati, filters.aic]);

  // Carica AIC disponibili (basato su filtri ESCLUSO aic)
  useEffect(() => {
    const loadAvailableAics = async () => {
      try {
        // Usa cascading senza il filtro AIC per ottenere tutti gli AIC disponibili
        const cascade = buildCascadeFilters(['aic']);
        const res = await reportApi.searchProdotti(prodottiSearch || null, 500, cascade);
        setProdottiOptions(
          res.prodotti?.map((p) => ({
            value: p.codice_aic,
            label: `${p.codice_aic} - ${(p.descrizione || 'N/D').toUpperCase()}`,
          })) || []
        );
      } catch (err) {
        console.error('Errore caricamento AIC:', err);
      }
    };

    const debounce = setTimeout(loadAvailableAics, 300);
    return () => clearTimeout(debounce);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [prodottiSearch, filters.data_inizio, filters.data_fine, filters.vendors, filters.depositi, filters.stati, filters.clienti]);

  // Costruisci filtri API
  const buildApiFilters = () => {
    const apiFilters = {};
    if (filters.tipo_data) apiFilters.tipo_data = filters.tipo_data;
    if (filters.data_inizio) apiFilters.data_inizio = filters.data_inizio;
    if (filters.data_fine) apiFilters.data_fine = filters.data_fine;
    if (filters.vendors.length > 0) apiFilters.vendors = filters.vendors.join(',');
    if (filters.depositi.length > 0) apiFilters.depositi = filters.depositi.join(',');
    if (filters.tipo_prodotto.length > 0) apiFilters.tipo_prodotto = filters.tipo_prodotto.join(',');
    if (filters.stati.length > 0) apiFilters.stati = filters.stati.join(',');
    if (filters.clienti.length > 0) apiFilters.clienti = filters.clienti.join(',');
    if (filters.aic.length > 0) apiFilters.aic = filters.aic.join(',');
    return apiFilters;
  };

  // Carica preview
  const loadPreview = async () => {
    try {
      setLoading(true);
      setError(null);
      const apiFilters = buildApiFilters();
      const res = await reportApi.getData(apiFilters);
      setReportData(res);
    } catch (err) {
      setError(err.response?.data?.detail || 'Errore caricamento dati');
    } finally {
      setLoading(false);
    }
  };

  // Download Excel
  const handleDownload = async () => {
    try {
      setDownloading(true);
      setError(null);
      const apiFilters = buildApiFilters();
      await reportApi.downloadExcel(apiFilters);
    } catch (err) {
      setError(err.response?.data?.detail || 'Errore download Excel');
    } finally {
      setDownloading(false);
    }
  };

  // Reset filtri
  const resetFilters = () => {
    setFilters({
      tipo_data: 'ordine',
      data_inizio: '',
      data_fine: '',
      vendors: [],
      depositi: [],
      tipo_prodotto: [],
      stati: [],
      clienti: [],
      aic: [],
    });
    setClientiSearch('');
    setProdottiSearch('');
    setReportData(null);
  };

  // Auto-refresh preview quando cambiano i filtri (interattivo)
  useEffect(() => {
    // Debounce per evitare troppe chiamate
    const debounce = setTimeout(() => {
      loadPreview();
    }, 500);
    return () => clearTimeout(debounce);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    filters.tipo_data,
    filters.data_inizio,
    filters.data_fine,
    filters.vendors,
    filters.depositi,
    filters.tipo_prodotto,
    filters.stati,
    filters.clienti,
    filters.aic,
  ]);

  // Gestione ordinamento
  const handleSort = (field) => {
    setSortConfig((prev) => ({
      field,
      direction: prev.field === field && prev.direction === 'asc' ? 'desc' : 'asc',
    }));
  };

  // Dati ordinati
  const sortedData = useMemo(() => {
    if (!reportData?.data) return [];
    const data = [...reportData.data];
    data.sort((a, b) => {
      let aVal = a[sortConfig.field];
      let bVal = b[sortConfig.field];

      // Gestione numeri
      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return sortConfig.direction === 'asc' ? aVal - bVal : bVal - aVal;
      }

      // Gestione stringhe
      aVal = String(aVal || '').toLowerCase();
      bVal = String(bVal || '').toLowerCase();
      if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1;
      return 0;
    });
    return data;
  }, [reportData?.data, sortConfig]);

  // Conteggio filtri attivi
  const getFilterCount = (filterKey) => {
    if (filterKey === 'periodo') {
      return (filters.data_inizio ? 1 : 0) + (filters.data_fine ? 1 : 0);
    }
    return filters[filterKey]?.length || 0;
  };

  const totalFilters =
    getFilterCount('periodo') +
    filters.vendors.length +
    filters.depositi.length +
    filters.tipo_prodotto.length +
    filters.stati.length +
    filters.clienti.length +
    filters.aic.length;

  if (loadingOptions) {
    return <Loading text="Caricamento filtri..." />;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Report</h1>
          <p className="text-slate-600">Seleziona i filtri - la preview si aggiorna automaticamente</p>
        </div>
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            onClick={resetFilters}
            disabled={totalFilters === 0}
            className={totalFilters === 0 ? 'opacity-50' : ''}
          >
            Azzera filtri {totalFilters > 0 && `(${totalFilters})`}
          </Button>
          {loading && (
            <span className="text-sm text-slate-500 animate-pulse">Caricamento...</span>
          )}
        </div>
      </div>

      {/* Accordion Filtri - 7 tabs */}
      <div className="grid grid-cols-1 md:grid-cols-7 gap-3">
        {/* Periodo */}
        <AccordionTab
          title="Periodo"
          icon="📅"
          isOpen={openTab === 'periodo'}
          onClick={() => setOpenTab(openTab === 'periodo' ? null : 'periodo')}
          badge={getFilterCount('periodo') > 0 ? getFilterCount('periodo') : null}
          onClear={() => setFilters({ ...filters, data_inizio: '', data_fine: '' })}
        >
          <div className="space-y-3">
            {/* Tipo data: Ordine o Consegna */}
            <div>
              <label className="block text-sm font-medium text-slate-600 mb-2">Tipo Data</label>
              {/* v11.0: Layout verticale - Data Consegna sotto Data Ordine */}
              <div className="flex flex-col gap-2">
                <label className={`flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer transition-colors ${
                  filters.tipo_data === 'ordine'
                    ? 'bg-blue-50 border border-blue-200'
                    : 'bg-slate-50 border border-slate-200 hover:bg-slate-100'
                }`}>
                  <input
                    type="radio"
                    name="tipo_data"
                    value="ordine"
                    checked={filters.tipo_data === 'ordine'}
                    onChange={(e) => setFilters({ ...filters, tipo_data: e.target.value })}
                    className="w-4 h-4 text-blue-600"
                  />
                  <span className="text-sm text-slate-700">Data Ordine</span>
                </label>
                <label className={`flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer transition-colors ${
                  filters.tipo_data === 'consegna'
                    ? 'bg-blue-50 border border-blue-200'
                    : 'bg-slate-50 border border-slate-200 hover:bg-slate-100'
                }`}>
                  <input
                    type="radio"
                    name="tipo_data"
                    value="consegna"
                    checked={filters.tipo_data === 'consegna'}
                    onChange={(e) => setFilters({ ...filters, tipo_data: e.target.value })}
                    className="w-4 h-4 text-blue-600"
                  />
                  <span className="text-sm text-slate-700">Data Consegna</span>
                </label>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-600 mb-1">Data Inizio</label>
              <input
                type="date"
                value={filters.data_inizio}
                onChange={(e) => setFilters({ ...filters, data_inizio: e.target.value })}
                className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-600 mb-1">Data Fine</label>
              <input
                type="date"
                value={filters.data_fine}
                onChange={(e) => setFilters({ ...filters, data_fine: e.target.value })}
                className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>
          </div>
        </AccordionTab>

        {/* Vendor */}
        <AccordionTab
          title="Vendor"
          icon="🏭"
          isOpen={openTab === 'vendor'}
          onClick={() => setOpenTab(openTab === 'vendor' ? null : 'vendor')}
          badge={filters.vendors.length > 0 ? filters.vendors.length : null}
          onClear={() => setFilters({ ...filters, vendors: [] })}
        >
          <CheckboxGroup
            options={vendorOptions}
            selected={filters.vendors}
            onChange={(v) => setFilters({ ...filters, vendors: v })}
          />
        </AccordionTab>

        {/* Deposito di Riferimento */}
        <AccordionTab
          title="Deposito"
          icon="🏢"
          isOpen={openTab === 'depositi'}
          onClick={() => setOpenTab(openTab === 'depositi' ? null : 'depositi')}
          badge={filters.depositi.length > 0 ? filters.depositi.length : null}
          onClear={() => setFilters({ ...filters, depositi: [] })}
        >
          <CheckboxGroup
            options={depositiOptions}
            selected={filters.depositi}
            onChange={(v) => setFilters({ ...filters, depositi: v })}
          />
        </AccordionTab>

        {/* Stato Ordine */}
        <AccordionTab
          title="Stato"
          icon="📊"
          isOpen={openTab === 'stati'}
          onClick={() => setOpenTab(openTab === 'stati' ? null : 'stati')}
          badge={filters.stati.length > 0 ? filters.stati.length : null}
          onClear={() => setFilters({ ...filters, stati: [] })}
        >
          <CheckboxGroup
            options={statiOptions}
            selected={filters.stati}
            onChange={(v) => setFilters({ ...filters, stati: v })}
          />
        </AccordionTab>

        {/* Tipo Prodotto */}
        <AccordionTab
          title="Tipo"
          icon="📦"
          isOpen={openTab === 'tipo_prodotto'}
          onClick={() => setOpenTab(openTab === 'tipo_prodotto' ? null : 'tipo_prodotto')}
          badge={filters.tipo_prodotto.length > 0 ? filters.tipo_prodotto.length : null}
          onClear={() => setFilters({ ...filters, tipo_prodotto: [] })}
        >
          <CheckboxGroup
            options={tipoProdottoOptions}
            selected={filters.tipo_prodotto}
            onChange={(v) => setFilters({ ...filters, tipo_prodotto: v })}
          />
        </AccordionTab>

        {/* AIC (nuovo) */}
        <AccordionTab
          title="AIC"
          icon="💊"
          isOpen={openTab === 'aic'}
          onClick={() => setOpenTab(openTab === 'aic' ? null : 'aic')}
          badge={filters.aic.length > 0 ? filters.aic.length : null}
          onClear={() => { setFilters({ ...filters, aic: [] }); setProdottiSearch(''); }}
        >
          <div className="space-y-3">
            <input
              type="text"
              placeholder="Cerca per AIC o descrizione..."
              value={prodottiSearch}
              onChange={(e) => setProdottiSearch(e.target.value)}
              className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
            <div className="max-h-48 overflow-y-auto">
              <CheckboxGroup
                options={prodottiOptions}
                selected={filters.aic}
                onChange={(v) => setFilters({ ...filters, aic: v })}
              />
            </div>
          </div>
        </AccordionTab>

        {/* Clienti */}
        <AccordionTab
          title="Clienti"
          icon="👥"
          isOpen={openTab === 'clienti'}
          onClick={() => setOpenTab(openTab === 'clienti' ? null : 'clienti')}
          badge={filters.clienti.length > 0 ? filters.clienti.length : null}
          onClear={() => { setFilters({ ...filters, clienti: [] }); setClientiSearch(''); }}
        >
          <div className="space-y-3">
            <input
              type="text"
              placeholder="Cerca per MIN_ID o ragione sociale..."
              value={clientiSearch}
              onChange={(e) => setClientiSearch(e.target.value)}
              className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
            <div className="max-h-48 overflow-y-auto">
              <CheckboxGroup
                options={clientiOptions}
                selected={filters.clienti}
                onChange={(v) => setFilters({ ...filters, clienti: v })}
              />
            </div>
          </div>
        </AccordionTab>
      </div>

      {/* Errore */}
      {error && <ErrorBox.Error message={error} onDismiss={() => setError(null)} />}

      {/* Tabella Preview */}
      {reportData && (
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div>
                <h2 className="text-lg font-semibold text-slate-800">
                  Preview Report
                </h2>
                <p className="text-sm text-slate-500">
                  Visualizzati {reportData.count} di {reportData.total_count} record
                  {reportData.include_cliente && ' - Raggruppamento per cliente attivo'}
                </p>
              </div>
              {loading && (
                <span className="text-sm text-blue-600 animate-pulse">Aggiornamento...</span>
              )}
            </div>
            <Button
              variant="success"
              onClick={handleDownload}
              loading={downloading}
              disabled={reportData.total_count === 0 || loading}
            >
              Scarica Excel ({reportData.total_count})
            </Button>
          </div>

          {reportData.total_count === 0 ? (
            <div className="px-6 py-12 text-center text-slate-500">
              Nessun dato trovato con i filtri selezionati
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-slate-50">
                  <tr>
                    <SortableHeader
                      label="Vendor"
                      field="vendor"
                      sortConfig={sortConfig}
                      onSort={handleSort}
                    />
                    <SortableHeader
                      label="AIC"
                      field="codice_aic"
                      sortConfig={sortConfig}
                      onSort={handleSort}
                    />
                    <SortableHeader
                      label="Descrizione"
                      field="descrizione"
                      sortConfig={sortConfig}
                      onSort={handleSort}
                    />
                    {reportData.include_cliente && (
                      <>
                        <SortableHeader
                          label="MIN_ID"
                          field="min_id"
                          sortConfig={sortConfig}
                          onSort={handleSort}
                        />
                        <SortableHeader
                          label="Cliente"
                          field="cliente"
                          sortConfig={sortConfig}
                          onSort={handleSort}
                        />
                      </>
                    )}
                    <SortableHeader
                      label="N. Ordini"
                      field="n_ordini"
                      sortConfig={sortConfig}
                      onSort={handleSort}
                    />
                    <SortableHeader
                      label="Pezzi"
                      field="pezzi"
                      sortConfig={sortConfig}
                      onSort={handleSort}
                    />
                    <SortableHeader
                      label="Valore"
                      field="valore"
                      sortConfig={sortConfig}
                      onSort={handleSort}
                    />
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {sortedData.map((row, idx) => (
                    <tr key={idx} className="hover:bg-slate-50">
                      <td className="px-4 py-3 text-sm font-medium text-slate-700">{row.vendor}</td>
                      <td className="px-4 py-3 text-sm text-slate-600 font-mono">{row.codice_aic}</td>
                      <td className="px-4 py-3 text-sm text-slate-600 uppercase">{row.descrizione}</td>
                      {reportData.include_cliente && (
                        <>
                          <td className="px-4 py-3 text-sm text-slate-600 font-mono">{row.min_id}</td>
                          <td className="px-4 py-3 text-sm text-slate-600">{row.cliente}</td>
                        </>
                      )}
                      <td className="px-4 py-3 text-sm text-slate-700 text-right">{row.n_ordini}</td>
                      <td className="px-4 py-3 text-sm text-slate-700 text-right font-medium">
                        {row.pezzi.toLocaleString('it-IT')}
                      </td>
                      <td className="px-4 py-3 text-sm text-slate-700 text-right font-medium">
                        {row.valore.toLocaleString('it-IT', {
                          style: 'currency',
                          currency: 'EUR',
                        })}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Loading stato */}
      {loading && !reportData && (
        <div className="bg-white rounded-xl border border-slate-200 p-12 text-center">
          <div className="text-4xl mb-4 animate-spin">⏳</div>
          <h3 className="text-lg font-semibold text-slate-700">
            Caricamento dati...
          </h3>
        </div>
      )}
    </div>
  );
}
