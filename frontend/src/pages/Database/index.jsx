// =============================================================================
// SERV.O v7.0 - DATABASE PAGE (REFACTORED)
// =============================================================================
// Pagina database ordini - versione decomposta e modulare
// =============================================================================

import React from 'react';
import { ordiniApi, getApiBaseUrl } from '../../api';
import { Button } from '../../common';
import { AnomaliaDetailModal } from '../../components';

// Sub-components
import StatsCards from './StatsCards';
import OrdiniTab from './OrdiniTab';
import AnomalieTab from './AnomalieTab';

// Custom hook
import { useDatabasePage } from './hooks/useDatabasePage';

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export default function DatabasePage({ currentUser, onOpenOrdine }) {
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
    clearFilters
  } = useDatabasePage(currentUser, onOpenOrdine);

  // Tabs config
  const tabs = [
    { id: 'ordini', label: 'Ordini', count: stats.ordini },
    { id: 'dettaglio', label: 'Dettaglio', count: null, disabled: !selectedOrdine },
    { id: 'anomalie', label: 'Anomalie', count: stats.anomalie_aperte > 0 ? stats.anomalie_aperte : null }
  ];

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
      <StatsCards stats={stats} />

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
                    onOpenOrdine?.(selectedOrdine.id_testata);
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
              {['DOC_GENERICI', 'CODIFI', 'COOPER', 'MENARINI', 'OPELLA', 'CHIESI', 'ANGELINI', 'BAYER', 'RECKITT'].map((v) => (
                <option key={v} value={v}>{v}</option>
              ))}
            </select>

            <select
              value={filters.stato}
              onChange={(e) => setFilters({ ...filters, stato: e.target.value })}
              className="px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Tutti gli Stati</option>
              {['ESTRATTO', 'CONFERMATO', 'ANOMALIA', 'PARZ_EVASO', 'EVASO', 'ARCHIVIATO'].map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>

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
            onOpenOrdine={onOpenOrdine}
            onShowPdf={showPdf}
            onArchiviaOrdine={handleArchiviaOrdine}
            onClearFilters={clearFilters}
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

      {/* Legenda Urgenze */}
      <div className="bg-white rounded-xl border border-slate-200 p-3">
        <h4 className="text-xs font-semibold text-slate-600 mb-2">
          Legenda Urgenze Consegna
        </h4>
        <div className="flex gap-6 text-xs">
          <div className="flex items-center gap-2">
            <span className="w-4 h-4 bg-red-50 border-l-4 border-red-500 rounded"></span>
            <span className="text-slate-600">🔴 Scaduto (data passata)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-4 h-4 bg-amber-50 border-l-4 border-amber-400 rounded"></span>
            <span className="text-slate-600">🟠 Urgente (meno di 2 gg lavorativi)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="flex items-center gap-1 text-emerald-600">🟢</span>
            <span className="text-slate-600">Ordinario (piu di 2 gg lavorativi)</span>
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
