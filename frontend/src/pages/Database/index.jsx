// =============================================================================
// SERV.O v7.0 - DATABASE PAGE (REFACTORED)
// =============================================================================
// Pagina database ordini - versione decomposta e modulare
// =============================================================================

import React, { useState, useRef, useEffect } from 'react';
import { ordiniApi, getApiBaseUrl } from '../../api';
import { Button } from '../../common';
import { AnomaliaDetailModal } from '../../components';

// Sub-components
import StatsCards from './StatsCards';
import OrdiniTab from './OrdiniTab';
import AnomalieTab from './AnomalieTab';
import EvasioneModal from './EvasioneModal';

// Custom hook
import { useDatabasePage } from './hooks/useDatabasePage';

// =============================================================================
// STATO MULTI-SELECT DROPDOWN
// =============================================================================

const STATI_OPTIONS = ['ESTRATTO', 'CONFERMATO', 'VALIDATO', 'ESPORTATO', 'PARZ_ESPORTATO', 'ANOMALIA', 'PARZ_EVASO', 'EVASO', 'ARCHIVIATO'];

function StatoMultiSelect({ selected = [], onChange }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    const handler = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const toggle = (stato) => {
    const next = selected.includes(stato)
      ? selected.filter(s => s !== stato)
      : [...selected, stato];
    onChange(next);
  };

  const allSelected = selected.length === STATI_OPTIONS.length;
  const toggleAll = () => onChange(allSelected ? [] : [...STATI_OPTIONS]);

  const label = selected.length === 0
    ? 'Tutti gli Stati'
    : selected.length <= 2
      ? selected.join(', ')
      : `${selected.length} stati`;

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className={`w-full px-3 py-2 border rounded-lg text-sm text-left focus:outline-none focus:ring-2 focus:ring-blue-500 flex items-center justify-between ${
          selected.length > 0 ? 'border-blue-400 bg-blue-50' : 'border-slate-200'
        }`}
      >
        <span className="truncate">{label}</span>
        <svg className={`w-4 h-4 ml-1 transition-transform ${open ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {open && (
        <div className="absolute z-50 mt-1 w-full bg-white border border-slate-200 rounded-lg shadow-lg py-1 max-h-64 overflow-auto">
          <label className="flex items-center gap-2 px-3 py-1.5 hover:bg-slate-50 cursor-pointer text-sm font-medium border-b border-slate-100">
            <input
              type="checkbox"
              checked={allSelected}
              onChange={toggleAll}
              className="rounded border-slate-300"
            />
            Tutti
          </label>
          {STATI_OPTIONS.map(s => (
            <label key={s} className="flex items-center gap-2 px-3 py-1.5 hover:bg-slate-50 cursor-pointer text-sm">
              <input
                type="checkbox"
                checked={selected.includes(s)}
                onChange={() => toggle(s)}
                className="rounded border-slate-300"
              />
              {s}
            </label>
          ))}
        </div>
      )}
    </div>
  );
}

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export default function DatabasePage({ currentUser, onOpenOrdine, restoreScrollY = 0, savedFilters = null, onSaveFilters }) {
  const {
    // Tab
    activeTab,
    setActiveTab,

    // Ordini
    ordini,
    selectedOrdine,
    loading,
    filters,
    setFilters,
    selected,
    validatingBatch,
    downloadingPdf,

    // Stats
    stats,

    // v11.3: View tracking
    viewedOrders,
    trackOrderView,

    // Evasione Modal
    evasioneModal,
    handleRegistraEvasione,
    handleSalvaEvasione,
    closeEvasioneModal,

    // PDF Modal
    showPdfModal,
    pdfToShow,

    // Anomalie
    anomalieList,
    loadingAnomalies,
    selectedAnomalies,
    anomalieFilters,
    setAnomalieFilters,

    // Anomalia detail modal
    showAnomaliaDetailModal,
    anomaliaDetail,
    loadingAnomaliaDetail,

    // Actions
    loadOrdini,
    loadAnomalies,
    loadAnomalieCount,
    toggleSelect,
    selectAll,
    toggleAnomaliaSelect,
    selectAllAnomalies,
    handleBatchArchivia,
    handleBatchValidate,
    handleDownloadPdf,
    handleResolveAnomalies,
    loadAnomaliaDetail,
    handleSaveRigaParent,
    handleRisolviAnomaliaDetail,
    handleAssignFarmacia,
    closeAnomaliaModal,
    showPdf,
    closePdfModal,
    clearFilters,
    handleToggleDifarm
  } = useDatabasePage(currentUser, onOpenOrdine, { savedFilters, onSaveFilters });

  // Ripristina scroll position dopo caricamento ordini (ritorno da dettaglio)
  const scrollRestored = useRef(false);
  useEffect(() => {
    if (restoreScrollY > 0 && !loading && ordini.length > 0 && !scrollRestored.current) {
      scrollRestored.current = true;
      requestAnimationFrame(() => window.scrollTo(0, restoreScrollY));
    }
  }, [restoreScrollY, loading, ordini]);

  // Tabs config
  const tabs = [
    { id: 'ordini', label: 'Ordini', count: stats.ordini },
    { id: 'dettaglio', label: 'Dettaglio', count: null, disabled: !selectedOrdine },
    { id: 'anomalie', label: 'Anomalie', count: stats.anomalie_aperte > 0 ? stats.anomalie_aperte : null }
  ];

  // v11.3: Wrapper per onOpenOrdine che traccia la visualizzazione
  // v12.1: Salva filtri correnti prima di navigare al dettaglio
  const handleOpenOrdine = (idTestata) => {
    trackOrderView(idTestata);
    onSaveFilters?.(filters);
    onOpenOrdine?.(idTestata);
  };

  // Handle archivia ordine singolo
  const handleArchiviaOrdine = async (ordine) => {
    const conferma = window.confirm(
      `ARCHIVIAZIONE DEFINITIVA\n\n` +
      `Vuoi archiviare definitivamente l'ordine?\n\n` +
      `Ordine: ${ordine.numero_ordine_vendor || '-'}\n` +
      `Cliente: ${ordine.ragione_sociale?.toUpperCase() || '-'}\n` +
      `Vendor: ${ordine.vendor || '-'}\n\n` +
      `Lo stato diventera EVASO e non sara piu modificabile.`
    );
    if (!conferma) return;

    try {
      await ordiniApi.archiviaOrdine(ordine.id_testata);
      alert(`Ordine ${ordine.numero_ordine_vendor} archiviato con successo!`);
      loadOrdini();
    } catch (err) {
      alert('Errore: ' + (err.response?.data?.detail || err.message));
    }
  };

  return (
    <div className="space-y-6">
      {/* Stats Cards */}
      <StatsCards
        stats={stats}
        activeFilter={filters.stato}
        onStatClick={(stato) => {
          if (stato === '') {
            // "Ordini" card: toggle between all (empty) and default
            setFilters(prev => ({
              ...prev,
              stato: prev.stato.length === 0 ? ['ESTRATTO', 'PARZ_ESPORTATO', 'ANOMALIA'] : []
            }));
          } else {
            setFilters(prev => {
              const arr = Array.isArray(prev.stato) ? prev.stato : [];
              const next = arr.includes(stato)
                ? arr.filter(s => s !== stato)
                : [...arr, stato];
              return { ...prev, stato: next };
            });
          }
          setActiveTab('ordini');
        }}
      />

      {/* Main Content */}
      <div className="bg-white rounded-xl border border-slate-200">
        {/* Tabs */}
        <div className="border-b border-slate-200">
          <div className="flex">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => {
                  if (tab.disabled) return;
                  if (tab.id === 'dettaglio' && selectedOrdine) {
                    handleOpenOrdine(selectedOrdine.id_testata);
                  } else {
                    setActiveTab(tab.id);
                  }
                }}
                disabled={tab.disabled}
                className={`px-4 py-3 text-sm font-medium transition-colors ${
                  tab.disabled
                    ? 'text-slate-300 cursor-not-allowed'
                    : activeTab === tab.id
                    ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50'
                    : 'text-slate-500 hover:bg-slate-50'
                }`}
              >
                {tab.label}
                {tab.count !== null && (
                  <span className="ml-1 text-slate-400">({tab.count})</span>
                )}
              </button>
            ))}
          </div>
        </div>

        {/* Filtri */}
        <div className="p-4 border-b border-slate-100">
          <div className="grid grid-cols-1 md:grid-cols-6 gap-3">
            <input
              type="text"
              placeholder="🔍 Cerca numero ordine, farmacia..."
              value={filters.q}
              onChange={(e) => setFilters({ ...filters, q: e.target.value })}
              className="md:col-span-2 px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />

            <select
              value={filters.vendor}
              onChange={(e) => setFilters({ ...filters, vendor: e.target.value })}
              className="px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Tutti i Vendor</option>
              {/* v11.2: Lista vendor aggiornata + COOPER + RECKITT */}
              {['DOC_GENERICI', 'CODIFI', 'COOPER', 'MENARINI', 'OPELLA', 'CHIESI', 'ANGELINI', 'BAYER', 'RECKITT', 'VIATRIS', 'PERRIGO'].map((v) => (
                <option key={v} value={v}>{v}</option>
              ))}
            </select>

            <StatoMultiSelect
              selected={filters.stato}
              onChange={(stato) => setFilters(prev => ({ ...prev, stato }))}
            />

            <Button variant="secondary" size="sm" onClick={loadOrdini} disabled={loading}>
              🔄
            </Button>

            {/* Azioni batch */}
            {selected.length > 0 && (
              <div className="flex gap-2">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={handleDownloadPdf}
                  disabled={downloadingPdf}
                >
                  {downloadingPdf ? '⏳ Download...' : `📥 PDF (${selected.length})`}
                </Button>
                <Button
                  variant="warning"
                  size="sm"
                  onClick={handleBatchArchivia}
                  disabled={validatingBatch}
                >
                  🔒 Archivia ({selected.length})
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={handleBatchValidate}
                  disabled={validatingBatch}
                >
                  {validatingBatch ? '⏳ Validazione...' : `✓ Valida (${selected.length})`}
                </Button>
              </div>
            )}
          </div>
        </div>

        {/* Tab Content */}
        {activeTab === 'ordini' && (
          <OrdiniTab
            ordini={ordini}
            loading={loading}
            selected={selected}
            selectedOrdine={selectedOrdine}
            onToggleSelect={toggleSelect}
            onSelectAll={selectAll}
            onOpenOrdine={handleOpenOrdine}
            onShowPdf={showPdf}
            onArchiviaOrdine={handleArchiviaOrdine}
            onRegistraEvasione={handleRegistraEvasione}
            onClearFilters={clearFilters}
            viewedOrders={viewedOrders}
            onToggleDifarm={handleToggleDifarm}
          />
        )}

        {activeTab === 'anomalie' && (
          <AnomalieTab
            anomalieList={anomalieList}
            loading={loadingAnomalies}
            filters={anomalieFilters}
            setFilters={setAnomalieFilters}
            selectedAnomalies={selectedAnomalies}
            onToggleSelect={toggleAnomaliaSelect}
            onSelectAll={selectAllAnomalies}
            onReload={loadAnomalies}
            onResolveSelected={handleResolveAnomalies}
            onLoadDetail={loadAnomaliaDetail}
            onOpenOrdine={onOpenOrdine}
            onReloadCount={loadAnomalieCount}
          />
        )}
      </div>

      {/* Legenda */}
      <div className="bg-white rounded-xl border border-slate-200 p-3">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Legenda Urgenze */}
          <div>
            <h4 className="text-xs font-semibold text-slate-600 mb-2">
              Urgenze Consegna
            </h4>
            <div className="flex gap-6 text-xs">
              <div className="flex items-center gap-2">
                <span className="w-4 h-4 bg-red-50 border-l-4 border-red-500 rounded"></span>
                <span className="text-slate-600">Scaduto</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-4 h-4 bg-amber-50 border-l-4 border-amber-400 rounded"></span>
                <span className="text-slate-600">Urgente (&lt;2gg)</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="flex items-center gap-1 text-emerald-600">●</span>
                <span className="text-slate-600">Ordinario</span>
              </div>
            </div>
          </div>
          {/* Legenda Visualizzazione */}
          <div>
            <h4 className="text-xs font-semibold text-slate-600 mb-2">
              Stato Visualizzazione
            </h4>
            <div className="flex gap-6 text-xs">
              <div className="flex items-center gap-2">
                <span className="w-4 h-4 bg-blue-50/50 border-l-4 border-blue-500 rounded"></span>
                <span className="text-slate-600">Da visualizzare</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-4 h-4 bg-white border border-slate-200 rounded"></span>
                <span className="text-slate-600">Gia visualizzato</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Modal PDF */}
      {showPdfModal && pdfToShow && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl w-[90vw] h-[90vh] flex flex-col">
            <div className="flex items-center justify-between p-4 border-b border-slate-200">
              <h3 className="text-lg font-semibold text-slate-800">
                PDF Originale
              </h3>
              <button
                onClick={closePdfModal}
                className="p-2 hover:bg-slate-100 rounded-lg text-slate-500"
              >
                X
              </button>
            </div>
            <div className="flex-1 p-4">
              <iframe
                src={`${getApiBaseUrl()}/api/v1/upload/pdf/${encodeURIComponent(pdfToShow)}`}
                className="w-full h-full border border-slate-200 rounded-lg"
                title="PDF Viewer"
              />
            </div>
          </div>
        </div>
      )}

      {/* Modal Evasione */}
      <EvasioneModal
        isOpen={evasioneModal.open}
        onClose={closeEvasioneModal}
        onSave={handleSalvaEvasione}
        ordine={evasioneModal.ordine}
      />

      {/* Modal Dettaglio Anomalia */}
      <AnomaliaDetailModal
        isOpen={showAnomaliaDetailModal}
        onClose={closeAnomaliaModal}
        anomaliaDetail={anomaliaDetail}
        loading={loadingAnomaliaDetail}
        onSaveParent={handleSaveRigaParent}
        onRisolvi={handleRisolviAnomaliaDetail}
        onOpenOrdine={onOpenOrdine}
        onAssignFarmacia={handleAssignFarmacia}
      />
    </div>
  );
}
