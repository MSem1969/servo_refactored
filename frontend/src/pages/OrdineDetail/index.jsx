// =============================================================================
// SERV.O v11.4 - ORDINE DETAIL PAGE (REFACTORED)
// =============================================================================
// Pagina dettaglio ordine - versione decomposta e modulare
// v11.4: Aggiunto supporto ritorno a Supervisione ML con banner
// =============================================================================

import React, { useState } from 'react';
import { Loading, ErrorBox, Button } from '../../common';
import { AnomaliaDetailModal } from '../../components';
import ModificaHeaderModal from '../../components/ModificaHeaderModal';

// Sub-components
import OrdineHeader from './OrdineHeader';
import RigheTable from './RigheTable';
import RigaEditModal from './RigaEditModal';
import AnomalieTab from './AnomalieTab';
import EspositoreTab from './EspositoreTab';
import PdfModal from './PdfModal';

// Custom hook
import { useOrdineDetail } from './hooks/useOrdineDetail';

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export default function OrdineDetailPage({ ordineId, currentUser, onBack, onNavigateToSupervisione, returnToSupervisione }) {
  // State per modal modifica header
  const [showHeaderModal, setShowHeaderModal] = useState(false);

  const {
    // Data
    ordine,
    righe,
    righeAll,
    anomalie,
    supervisioni,
    stats,

    // UI state
    loading,
    error,
    setError,
    activeTab,
    setActiveTab,

    // v11.3: Sort state (persists across reloads)
    sortField,
    sortDirection,
    handleSort,

    // Edit state
    rigaInModifica,
    formModifica,
    setFormModifica,

    // Modal state
    showPdfModal,
    setShowPdfModal,
    showAnomaliaDetailModal,
    anomaliaDetail,
    loadingAnomaliaDetail,

    // Actions
    loadOrdine,
    apriModificaRiga,
    chiudiModificaRiga,
    salvaModificaRiga,
    confermaRigaCompleta,
    ripristinaRiga,
    archiviaRiga,
    ripristinaArchiviata,
    confermaTutto,
    ripristinaTutto,
    validaOrdine,
    loadAnomaliaDetail,
    risolviAnomalia,
    saveRigaParent,
    risolviAnomaliaDetail,
    assignFarmacia,
    closeAnomaliaModal,
    approvaSuper,
    rifiutaSuper,
    fixEspositore
  } = useOrdineDetail(ordineId, currentUser);

  // =============================================================================
  // LOADING & ERROR STATES
  // =============================================================================

  if (loading) {
    return <Loading text="Caricamento ordine..." />;
  }

  // v11.4: Testo dinamico per bottone indietro
  const backButtonText = returnToSupervisione ? 'Torna a Supervisione ML' : 'Torna al Database';

  if (error && !ordine) {
    return (
      <div className="space-y-4">
        <ErrorBox.Error message={error} />
        <Button variant="secondary" onClick={onBack}>
          {backButtonText}
        </Button>
      </div>
    );
  }

  if (!ordine) {
    return (
      <div className="text-center py-8">
        <p className="text-slate-500">Ordine non trovato</p>
        <Button variant="secondary" onClick={onBack} className="mt-4">
          {backButtonText}
        </Button>
      </div>
    );
  }

  // =============================================================================
  // RENDER
  // =============================================================================

  return (
    <div className="space-y-6">
      {/* v11.4: Banner ritorno a Supervisione ML */}
      {returnToSupervisione && (
        <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center text-white text-sm font-bold">
                ML
              </div>
              <div>
                <p className="font-medium text-indigo-900">Verifica da Supervisione ML</p>
                <p className="text-sm text-indigo-700">Clicca per tornare alla pagina Supervisione ML</p>
              </div>
            </div>
            <Button
              variant="primary"
              size="sm"
              onClick={onBack}
            >
              Torna a Supervisione ML
            </Button>
          </div>
        </div>
      )}

      {/* Header */}
      <OrdineHeader
        ordine={ordine}
        onBack={onBack}
        onShowPdf={() => setShowPdfModal(true)}
        onEditHeader={() => setShowHeaderModal(true)}
        returnToSupervisione={returnToSupervisione}
      />

      {/* Error message */}
      {error && <ErrorBox.Error message={error} onDismiss={() => setError(null)} />}

      {/* Tabs Container */}
      <div className="bg-white rounded-xl border border-slate-200">
        {/* Tab Navigation */}
        <div className="border-b border-slate-200">
          <nav className="flex gap-1 p-1">
            {[
              { id: 'righe', label: `Righe (${righe.length})`, icon: '[R]' },
              { id: 'espositore', label: 'Espositore', icon: '[E]' },
              { id: 'anomalie', label: `Anomalie (${anomalie.length + supervisioni.length})`, icon: '[!]' }
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  activeTab === tab.id
                    ? 'bg-blue-100 text-blue-800'
                    : 'text-slate-600 hover:bg-slate-100'
                }`}
              >
                <span>{tab.icon}</span>
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Tab Content */}
        <div className="p-6">
          {activeTab === 'righe' && (
            <RigheTable
              righe={righe}
              rigaInModifica={rigaInModifica}
              formModifica={formModifica}
              setFormModifica={setFormModifica}
              stats={stats}
              ordine={ordine}
              // v11.3: Sort state from parent (persists across reloads)
              sortField={sortField}
              sortDirection={sortDirection}
              onSort={handleSort}
              onShowPdf={() => setShowPdfModal(true)}
              onApriModifica={apriModificaRiga}
              onSalvaModifica={salvaModificaRiga}
              onChiudiModifica={chiudiModificaRiga}
              onConfermaRiga={confermaRigaCompleta}
              onRipristinaRiga={ripristinaRiga}
              onArchiviaRiga={archiviaRiga}
              onRipristinaArchiviata={ripristinaArchiviata}
              onConfermaTutto={confermaTutto}
              onRipristinaTutto={ripristinaTutto}
              onValidaOrdine={validaOrdine}
            />
          )}

          {activeTab === 'espositore' && (
            <EspositoreTab
              righe={righeAll}
              ordine={ordine}
              onFixEspositore={fixEspositore}
              loading={loading}
            />
          )}

          {activeTab === 'anomalie' && (
            <AnomalieTab
              anomalie={anomalie}
              supervisioni={supervisioni}
              onLoadDetail={loadAnomaliaDetail}
              onRisolvi={risolviAnomalia}
              onApprovaSuper={approvaSuper}
              onRifiutaSuper={rifiutaSuper}
            />
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="bg-slate-50 rounded-xl border border-slate-200 p-4">
        <div className="flex items-center justify-between">
          <div className="text-sm text-slate-600">
            <span className="font-medium">Ultimo aggiornamento:</span> {ordine.data_modifica || ordine.data_creazione || '-'}
          </div>
          <div className="flex gap-2">
            <Button variant="secondary" onClick={loadOrdine}>
              Ricarica
            </Button>
          </div>
        </div>
      </div>

      {/* Modals */}
      <RigaEditModal
        riga={rigaInModifica}
        formModifica={formModifica}
        setFormModifica={setFormModifica}
        onSave={salvaModificaRiga}
        onClose={chiudiModificaRiga}
      />

      {showPdfModal && ordine?.pdf_file && (
        <PdfModal
          pdfFile={ordine.pdf_file}
          onClose={() => setShowPdfModal(false)}
        />
      )}

      <AnomaliaDetailModal
        isOpen={showAnomaliaDetailModal}
        onClose={closeAnomaliaModal}
        anomaliaDetail={anomaliaDetail}
        loading={loadingAnomaliaDetail}
        onSaveParent={saveRigaParent}
        onRisolvi={risolviAnomaliaDetail}
        onAssignFarmacia={assignFarmacia}
      />

      {/* Modal Modifica Header (v11.3) */}
      <ModificaHeaderModal
        ordine={ordine}
        isOpen={showHeaderModal}
        onClose={() => setShowHeaderModal(false)}
        onSuccess={() => {
          // Ricarica ordine dopo modifica
          loadOrdine();
        }}
        currentUser={currentUser}
      />
    </div>
  );
}
