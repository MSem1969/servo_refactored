// =============================================================================
// SERV.O v9.0 - SUPERVISIONE PAGE
// =============================================================================
// Pagina supervisione ML con pattern recognition e workflow approvazione
// v9.0: Aggiunto supporto supervisione AIC (AIC-A01)
// =============================================================================

import React, { useEffect } from 'react';
import { Button, StatusBadge, VendorBadge, Loading } from '../../common';
import { useSupervisione } from './hooks/useSupervisione';
import CorrezioneLisinoModal from './CorrezioneLisinoModal';
import ArchiviazioneListinoModal from './ArchiviazioneListinoModal';
// v11.0: Usa AicAssignmentModal unificato (TIER 2.1)
import { AicAssignmentModal, AIC_MODAL_MODES } from '../../components/AicAssignmentModal';

/**
 * Componente SupervisionePage
 *
 * Sistema ML per pattern recognition su anomalie espositori e listino.
 * Workflow: APPROVE/REJECT/MODIFY con apprendimento automatico.
 */
const SupervisionePage = ({
  supervisioneId,
  returnToOrdine,
  currentUser,
  onReturnToOrdine,
  onNavigateToOrdine
}) => {
  const {
    // State
    supervisioni,
    groupedSupervisioni,
    criteri,
    storico,
    stats,
    loading,
    activeTab,
    setActiveTab,
    viewMode,
    setViewMode,
    processingAction,
    processingPattern,
    operatore,
    tabs,
    pendingCount,

    // Modal state
    correzioneModal,
    archiviazioneModal,
    aicModal, // v9.0

    // Actions
    loadData,
    handleApprova,
    handleRifiuta,
    handleModifica,
    handleApprovaBulk,
    handleRifiutaBulk,
    handleLasciaSospeso,
    handleResetPattern,
    handlePromuoviPattern,

    // Modal actions
    handleOpenCorrezione,
    handleCloseCorrezione,
    handleOpenArchiviazione,
    handleCloseArchiviazione,
    handleOpenAic,       // v9.0
    handleCloseAic,      // v9.0
    handleAicSuccess,    // v9.0
    handleRifiutaAic,    // v9.0
    handleListinoSuccess,

    // Bulk actions
    handleRiapplicaListinoLst,  // v10.0 - Riapplica listino unificato

    // Utilities
    getMLProgress,
    getAnomaliaUrgency,
  } = useSupervisione({ currentUser, returnToOrdine, onReturnToOrdine });

  useEffect(() => {
    loadData();
  }, [loadData]);

  if (loading) {
    return (
      <div className="space-y-6">
        <Loading text="Caricamento sistema supervisione ML..." />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header con ritorno ordine */}
      {returnToOrdine && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center text-white text-sm font-bold">
                🔗
              </div>
              <div>
                <p className="font-medium text-blue-900">Supervisione da Ordine #{returnToOrdine}</p>
                <p className="text-sm text-blue-700">Dopo l'azione tornerai automaticamente al dettaglio ordine</p>
              </div>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onReturnToOrdine?.(returnToOrdine)}
            >
              ← Torna all'Ordine
            </Button>
          </div>
        </div>
      )}

      {/* Stats ML Dashboard */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-orange-100 rounded-lg flex items-center justify-center">
              ⏳
            </div>
            <div>
              <p className="text-xs text-slate-600 font-medium">In Attesa</p>
              <p className="text-xl font-bold text-slate-800">{pendingCount}</p>
            </div>
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
              🧠
            </div>
            <div>
              <p className="text-xs text-slate-600 font-medium">Pattern ML</p>
              <p className="text-xl font-bold text-slate-800">{stats?.totale_pattern || 0}</p>
              <p className="text-xs text-slate-500">{stats?.pattern_ordinari || 0} automatici</p>
            </div>
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-emerald-100 rounded-lg flex items-center justify-center">
              ✅
            </div>
            <div>
              <p className="text-xs text-slate-600 font-medium">Approvazioni</p>
              <p className="text-xl font-bold text-slate-800">{stats?.approvazioni_totali || 0}</p>
            </div>
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
              🎯
            </div>
            <div>
              <p className="text-xs text-slate-600 font-medium">Efficienza ML</p>
              <p className="text-xl font-bold text-slate-800">
                {stats?.totale_pattern ? Math.round((stats.pattern_ordinari / stats.totale_pattern) * 100) : 0}%
              </p>
              <p className="text-xs text-slate-500">pattern automatici</p>
            </div>
          </div>
        </div>
      </div>

      {/* Azioni rapide */}
      <div className="flex flex-wrap items-center gap-3">
        <Button
          variant="secondary"
          size="sm"
          onClick={handleRiapplicaListinoLst}
          title="Applica prezzi dal listino a tutte le supervisioni LST-A01 pending"
        >
          📋 Riapplica Listino
        </Button>
        <span className="text-xs text-slate-500">
          Applica prezzi dal listino a tutte le supervisioni pending
        </span>
      </div>

      {/* Main Content */}
      <div className="bg-white rounded-xl border border-slate-200">
        {/* Tabs */}
        <div className="border-b border-slate-200">
          <div className="flex">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-4 py-3 text-sm font-medium transition-colors flex items-center gap-2 ${
                  activeTab === tab.id
                    ? 'text-blue-600 border-b-2 border-blue-600 bg-blue-50'
                    : 'text-slate-500 hover:bg-slate-50'
                }`}
              >
                <span>{tab.icon}</span>
                <span>{tab.label}</span>
                <span className="bg-slate-200 text-slate-600 px-1.5 py-0.5 rounded-full text-xs">
                  {tab.count}
                </span>
              </button>
            ))}
          </div>
        </div>

        {/* Tab Da Supervisionare */}
        {activeTab === 'pending' && (
          <TabPending
            supervisioni={supervisioni}
            groupedSupervisioni={groupedSupervisioni}
            viewMode={viewMode}
            setViewMode={setViewMode}
            processingAction={processingAction}
            processingPattern={processingPattern}
            onNavigateToOrdine={onNavigateToOrdine}
            handleApprova={handleApprova}
            handleRifiuta={handleRifiuta}
            handleModifica={handleModifica}
            handleApprovaBulk={handleApprovaBulk}
            handleRifiutaBulk={handleRifiutaBulk}
            handleLasciaSospeso={handleLasciaSospeso}
            handleOpenCorrezione={handleOpenCorrezione}
            handleOpenArchiviazione={handleOpenArchiviazione}
            handleOpenAic={handleOpenAic}           // v9.0
            handleRifiutaAic={handleRifiutaAic}     // v9.0
            returnToOrdine={returnToOrdine}
            getMLProgress={getMLProgress}
            getAnomaliaUrgency={getAnomaliaUrgency}
          />
        )}

        {/* Tab Pattern ML */}
        {activeTab === 'patterns' && (
          <TabPatterns
            criteri={criteri}
            getMLProgress={getMLProgress}
            handlePromuoviPattern={handlePromuoviPattern}
            handleResetPattern={handleResetPattern}
          />
        )}

        {/* Tab Storico */}
        {activeTab === 'storico' && (
          <TabStorico storico={storico} />
        )}

        {/* Tab Analytics */}
        {activeTab === 'stats' && (
          <div className="p-6">
            <div className="text-center py-8 text-slate-500">
              <div className="text-4xl mb-2">📊</div>
              <p>Analytics avanzate in sviluppo...</p>
              <p className="text-sm mt-1">Grafici performance ML, trend approvazioni, efficienza pattern</p>
            </div>
          </div>
        )}
      </div>

      {/* Modali Listino */}
      <CorrezioneLisinoModal
        isOpen={correzioneModal.isOpen}
        onClose={handleCloseCorrezione}
        supervisione={correzioneModal.supervisione}
        operatore={operatore}
        onSuccess={handleListinoSuccess}
      />

      <ArchiviazioneListinoModal
        isOpen={archiviazioneModal.isOpen}
        onClose={handleCloseArchiviazione}
        supervisione={archiviazioneModal.supervisione}
        operatore={operatore}
        onSuccess={handleListinoSuccess}
      />

      {/* v11.0: AicAssignmentModal unificato (TIER 2.1) */}
      <AicAssignmentModal
        isOpen={aicModal.isOpen}
        onClose={handleCloseAic}
        mode={aicModal.supervisione?.is_bulk ? AIC_MODAL_MODES.SUPERVISIONE_BULK : AIC_MODAL_MODES.SUPERVISIONE_SINGOLA}
        supervisione={aicModal.supervisione}
        operatore={operatore}
        onSuccess={handleAicSuccess}
      />
    </div>
  );
};

// =============================================================================
// TAB PENDING - Vista supervisioni da gestire
// =============================================================================
const TabPending = ({
  supervisioni,
  groupedSupervisioni,
  viewMode,
  setViewMode,
  processingAction,
  processingPattern,
  onNavigateToOrdine,
  handleApprova,
  handleRifiuta,
  handleModifica,
  handleApprovaBulk,
  handleRifiutaBulk,
  handleLasciaSospeso,
  handleOpenCorrezione,
  handleOpenArchiviazione,
  handleOpenAic,       // v9.0
  handleRifiutaAic,    // v9.0
  returnToOrdine,
  getMLProgress,
  getAnomaliaUrgency,
}) => {
  // Nota: supervisioni sono già filtrate per PENDING dal backend
  const pendingItems = supervisioni;

  return (
    <div>
      {/* Intestazione */}
      <div className="px-6 py-4 bg-blue-50 border-b border-blue-200">
        <h3 className="text-sm font-medium text-blue-900 mb-1">Anomalie da Supervisionare</h3>
        <p className="text-xs text-blue-700">
          Queste anomalie richiedono una decisione manuale. Puoi approvare (il pattern viene appreso dal ML),
          rifiutare (reset apprendimento), o navigare all'ordine per verificare i dettagli.
        </p>
      </div>

      {/* Toggle vista */}
      <div className="px-6 py-3 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm text-slate-600">Vista:</span>
          <button
            onClick={() => setViewMode('grouped')}
            className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
              viewMode === 'grouped'
                ? 'bg-indigo-600 text-white'
                : 'bg-white text-slate-700 border border-slate-300 hover:bg-slate-50'
            }`}
          >
            Per Pattern ({groupedSupervisioni.length})
          </button>
          <button
            onClick={() => setViewMode('individual')}
            className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
              viewMode === 'individual'
                ? 'bg-indigo-600 text-white'
                : 'bg-white text-slate-700 border border-slate-300 hover:bg-slate-50'
            }`}
          >
            Singole ({pendingItems.length})
          </button>
        </div>
        {viewMode === 'grouped' && (
          <p className="text-xs text-slate-500">
            Approvando un pattern, risolvi tutte le supervisioni con quel pattern
          </p>
        )}
      </div>

      {/* Vista raggruppata */}
      {viewMode === 'grouped' && (
        <GroupedView
          groups={groupedSupervisioni}
          supervisioni={supervisioni}
          processingPattern={processingPattern}
          onNavigateToOrdine={onNavigateToOrdine}
          handleApprovaBulk={handleApprovaBulk}
          handleRifiutaBulk={handleRifiutaBulk}
          handleOpenCorrezione={handleOpenCorrezione}
          handleOpenAic={handleOpenAic}
        />
      )}

      {/* Vista individuale */}
      {viewMode === 'individual' && (
        <IndividualView
          items={pendingItems}
          processingAction={processingAction}
          onNavigateToOrdine={onNavigateToOrdine}
          handleApprova={handleApprova}
          handleRifiuta={handleRifiuta}
          handleModifica={handleModifica}
          handleLasciaSospeso={handleLasciaSospeso}
          handleOpenCorrezione={handleOpenCorrezione}
          handleOpenArchiviazione={handleOpenArchiviazione}
          handleOpenAic={handleOpenAic}           // v9.0
          handleRifiutaAic={handleRifiutaAic}     // v9.0
          returnToOrdine={returnToOrdine}
          getMLProgress={getMLProgress}
          getAnomaliaUrgency={getAnomaliaUrgency}
        />
      )}
    </div>
  );
};

// =============================================================================
// HELPER: Ordinamento per tipo anomalia
// =============================================================================
const TIPO_PRIORITY = {
  'aic': 1,      // AIC mancante - più critico
  'prezzo': 2,   // Prezzi mancanti
  'listino': 3,  // Problemi listino
  'lookup': 4,   // Farmacia non trovata
  'espositore': 5, // Problemi espositori
};

const sortByTipoAnomalia = (items, tipoField = 'tipo_supervisione') => {
  return [...items].sort((a, b) => {
    const tipoA = (a[tipoField] || '').toLowerCase();
    const tipoB = (b[tipoField] || '').toLowerCase();
    const priorityA = TIPO_PRIORITY[tipoA] || 99;
    const priorityB = TIPO_PRIORITY[tipoB] || 99;
    return priorityA - priorityB;
  });
};

// =============================================================================
// GROUPED VIEW - Vista raggruppata per pattern
// =============================================================================
const GroupedView = ({
  groups,
  supervisioni,
  processingPattern,
  onNavigateToOrdine,
  handleApprovaBulk,
  handleRifiutaBulk,
  handleOpenCorrezione,
  handleOpenAic,
}) => {
  // Ordina i gruppi per tipo anomalia
  const sortedGroups = sortByTipoAnomalia(groups);

  if (sortedGroups.length === 0) {
    return (
      <div className="p-8 text-center">
        <div className="text-4xl mb-3">🎉</div>
        <h3 className="text-lg font-medium text-slate-800 mb-2">Nessuna supervisione in attesa</h3>
        <p className="text-slate-600">Tutte le anomalie sono state gestite o risolte automaticamente dall'ML.</p>
      </div>
    );
  }

  const tipoLabels = {
    'espositore': { bg: 'bg-purple-100', text: 'text-purple-700', label: 'ESPOSITORE' },
    'listino': { bg: 'bg-blue-100', text: 'text-blue-700', label: 'LISTINO' },
    'lookup': { bg: 'bg-amber-100', text: 'text-amber-700', label: 'LOOKUP' },
    'prezzo': { bg: 'bg-red-100', text: 'text-red-700', label: 'PREZZO' },
    'aic': { bg: 'bg-teal-100', text: 'text-teal-700', label: 'AIC' },  // v9.0
  };

  return (
    <div className="divide-y divide-slate-100">
      {sortedGroups.map((group) => {
        const isProcessing = processingPattern === group.pattern_signature;
        const tipoLabel = tipoLabels[group.tipo_supervisione] || { bg: 'bg-slate-100', text: 'text-slate-700', label: group.tipo_supervisione };
        const mlProgress = (group.pattern_count || 0) * 20;

        return (
          <div key={group.pattern_signature} className={`p-6 ${isProcessing ? 'opacity-50' : ''}`}>
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <span className={`px-2 py-0.5 text-xs rounded-full ${tipoLabel.bg} ${tipoLabel.text}`}>
                    {tipoLabel.label}
                  </span>
                  <span className="font-medium text-slate-800">{group.codice_anomalia}</span>
                  <VendorBadge vendor={group.vendor} size="xs" />
                  {group.pattern_ordinario && (
                    <span className="px-2 py-0.5 text-xs bg-emerald-100 text-emerald-700 rounded-full">
                      AUTOMATICO
                    </span>
                  )}
                </div>
                <p className="text-sm text-slate-600 mb-2">
                  {/* v10.4: Mostra descrizione prodotto per LISTINO/AIC, altrimenti pattern */}
                  {group.descrizione_prodotto
                    ? `${group.codice_aic || ''} - ${group.descrizione_prodotto}`.trim()
                    : (group.pattern_descrizione || `Pattern: ${group.pattern_signature?.substring(0, 12)}...`)}
                </p>
                <div className="flex flex-wrap gap-4 text-sm text-slate-500">
                  <span><strong>{group.total_count}</strong> supervisioni</span>
                  <span><strong>{group.affected_order_ids?.length || 0}</strong> ordini</span>
                  <span className="truncate max-w-md" title={group.affected_orders_preview}>
                    Ordini: {group.affected_orders_preview || 'N/A'}
                  </span>
                </div>
              </div>
              <div className="text-right">
                <div className="text-3xl font-bold text-slate-800">{group.total_count}</div>
                <div className="text-xs text-slate-500">supervisioni</div>
              </div>
            </div>

            {/* ML Progress */}
            <div className="mt-4 flex items-center gap-3">
              <span className="text-xs text-slate-500">ML:</span>
              <div className="flex-1 h-2 bg-slate-200 rounded-full max-w-xs">
                <div
                  className={`h-full rounded-full transition-all ${
                    group.pattern_count >= 5 ? 'bg-emerald-500' : 'bg-orange-400'
                  }`}
                  style={{ width: `${Math.min(mlProgress, 100)}%` }}
                />
              </div>
              <span className="text-xs text-slate-600">{group.pattern_count || 0}/5</span>
            </div>

            {/* Actions */}
            <div className="mt-4 flex items-center gap-3 flex-wrap">
              {group.affected_order_ids?.length > 0 && onNavigateToOrdine && (
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => onNavigateToOrdine(group.affected_order_ids[0])}
                >
                  Verifica Ordine
                </Button>
              )}
              {group.tipo_supervisione === 'listino' && (() => {
                const firstSup = supervisioni.find(s => s.pattern_signature === group.pattern_signature);
                return firstSup ? (
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => handleOpenCorrezione(firstSup)}
                    disabled={isProcessing}
                  >
                    Correggi Prezzi
                  </Button>
                ) : null;
              })()}
              {group.tipo_supervisione === 'aic' ? (
                // Per AIC: apri modal per assegnare codice
                <>
                  {(() => {
                    const firstSup = supervisioni.find(s =>
                      s.pattern_signature === group.pattern_signature && s.tipo_supervisione === 'aic'
                    );
                    return (
                      <Button
                        variant="primary"
                        size="sm"
                        onClick={() => handleOpenAic?.({
                          ...firstSup,
                          // Aggiungi info pattern per bulk
                          is_bulk: true,
                          pattern_signature: group.pattern_signature,
                          total_count: group.total_count,
                          affected_order_ids: group.affected_order_ids
                        })}
                        disabled={isProcessing}
                      >
                        Assegna AIC ({group.total_count})
                      </Button>
                    );
                  })()}
                  <Button
                    variant="danger"
                    size="sm"
                    loading={isProcessing}
                    onClick={() => handleRifiutaBulk(group.pattern_signature, group.total_count)}
                    disabled={isProcessing}
                  >
                    Rifiuta Tutti
                  </Button>
                </>
              ) : (
                <>
                  <Button
                    variant="success"
                    size="sm"
                    loading={isProcessing}
                    onClick={() => handleApprovaBulk(group.pattern_signature, group.total_count)}
                    disabled={isProcessing}
                  >
                    Approva Tutti ({group.total_count})
                  </Button>
                  <Button
                    variant="danger"
                    size="sm"
                    loading={isProcessing}
                    onClick={() => handleRifiutaBulk(group.pattern_signature, group.total_count)}
                    disabled={isProcessing}
                  >
                    Rifiuta Tutti
                  </Button>
                </>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
};

// =============================================================================
// INDIVIDUAL VIEW - Vista singole supervisioni
// =============================================================================
const IndividualView = ({
  items,
  processingAction,
  onNavigateToOrdine,
  handleApprova,
  handleRifiuta,
  handleModifica,
  handleLasciaSospeso,
  handleOpenCorrezione,
  handleOpenArchiviazione,
  handleOpenAic,       // v9.0
  handleRifiutaAic,    // v9.0
  returnToOrdine,
  getMLProgress,
  getAnomaliaUrgency,
}) => {
  // Ordina le supervisioni per tipo anomalia
  const sortedItems = sortByTipoAnomalia(items);

  if (sortedItems.length === 0) {
    return (
      <div className="p-8 text-center">
        <div className="text-4xl mb-3">🎉</div>
        <h3 className="text-lg font-medium text-slate-800 mb-2">Nessuna supervisione in attesa</h3>
        <p className="text-slate-600">Tutte le anomalie sono state gestite o risolte automaticamente dall'ML.</p>
      </div>
    );
  }

  return (
    <div className="divide-y divide-slate-100">
      {sortedItems.map((sup) => {
        const urgency = getAnomaliaUrgency(sup);
        const mlProgress = getMLProgress(sup.pattern_approvazioni || sup.count_pattern || 0);
        const isProcessing = processingAction === sup.id_supervisione;
        const isListino = sup.tipo_supervisione === 'listino' || sup.codice_anomalia?.startsWith('LST-');
        const isLookup = sup.tipo_supervisione === 'lookup' || sup.codice_anomalia?.startsWith('LKP-');
        const isPrezzo = sup.tipo_supervisione === 'prezzo' || sup.codice_anomalia?.startsWith('PRICE-');
        const isAic = sup.tipo_supervisione === 'aic' || sup.codice_anomalia?.startsWith('AIC-');  // v9.0
        const vendorDisplay = isListino ? (sup.vendor || 'CODIFI') : (sup.vendor || 'ANGELINI');

        return (
          <SupervisioneCard
            key={`${isPrezzo ? 'prz' : isAic ? 'aic' : isListino ? 'lst' : isLookup ? 'lkp' : 'esp'}-${sup.id_supervisione}`}
            sup={sup}
            urgency={urgency}
            mlProgress={mlProgress}
            isProcessing={isProcessing}
            isListino={isListino}
            isLookup={isLookup}
            isPrezzo={isPrezzo}
            isAic={isAic}
            vendorDisplay={vendorDisplay}
            onNavigateToOrdine={onNavigateToOrdine}
            handleApprova={handleApprova}
            handleRifiuta={handleRifiuta}
            handleModifica={handleModifica}
            handleLasciaSospeso={handleLasciaSospeso}
            handleOpenCorrezione={handleOpenCorrezione}
            handleOpenArchiviazione={handleOpenArchiviazione}
            handleOpenAic={handleOpenAic}           // v9.0
            handleRifiutaAic={handleRifiutaAic}     // v9.0
            returnToOrdine={returnToOrdine}
          />
        );
      })}
    </div>
  );
};

// =============================================================================
// SUPERVISIONE CARD - Card singola supervisione
// =============================================================================
const SupervisioneCard = ({
  sup,
  urgency,
  mlProgress,
  isProcessing,
  isListino,
  isLookup,
  isPrezzo,
  isAic,  // v9.0
  vendorDisplay,
  onNavigateToOrdine,
  handleApprova,
  handleRifiuta,
  handleModifica,
  handleLasciaSospeso,
  handleOpenCorrezione,
  handleOpenArchiviazione,
  handleOpenAic,       // v9.0
  handleRifiutaAic,    // v9.0
  returnToOrdine,
}) => (
  <div
    className={`p-6 ${
      urgency === 'high' ? 'bg-red-50 border-l-4 border-red-500' :
      urgency === 'medium' ? 'bg-amber-50 border-l-4 border-amber-500' : ''
    }`}
  >
    <div className="flex items-start justify-between mb-4">
      <div className="flex-1">
        {/* Header */}
        <div className="flex items-center gap-3 mb-2">
          <h4 className="font-medium text-slate-800">
            Ordine #{sup.numero_ordine} - {sup.ragione_sociale?.toUpperCase()}
          </h4>
          <VendorBadge vendor={vendorDisplay} size="xs" />
          {isPrezzo ? (
            <span className="px-2 py-0.5 text-xs bg-red-100 text-red-700 rounded-full">PREZZO</span>
          ) : isAic ? (
            <span className="px-2 py-0.5 text-xs bg-teal-100 text-teal-700 rounded-full">AIC</span>
          ) : isListino ? (
            <span className="px-2 py-0.5 text-xs bg-blue-100 text-blue-700 rounded-full">LISTINO</span>
          ) : isLookup ? (
            <span className="px-2 py-0.5 text-xs bg-amber-100 text-amber-700 rounded-full">LOOKUP</span>
          ) : (
            <span className="px-2 py-0.5 text-xs bg-purple-100 text-purple-700 rounded-full">ESPOSITORE</span>
          )}
          <StatusBadge
            status={urgency === 'high' ? 'error' : urgency === 'medium' ? 'warning' : 'pending'}
            size="xs"
          />
        </div>

        {/* Info */}
        <div className="flex flex-wrap gap-4 text-xs text-slate-500 mb-3">
          <span>ID: {sup.id_testata}</span>
          {sup.data_ordine && <span>Data: {new Date(sup.data_ordine).toLocaleDateString('it-IT')}</span>}
          {sup.min_id && <span>MIN: {sup.min_id}</span>}
        </div>

        {/* Details grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <SupervisioneDetails sup={sup} isPrezzo={isPrezzo} isListino={isListino} isLookup={isLookup} isAic={isAic} />

          {/* ML Progress */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500">ML:</span>
            <div className="flex-1 h-2 bg-slate-200 rounded-full max-w-[120px]">
              <div
                className={`h-full rounded-full ${mlProgress >= 100 ? 'bg-emerald-500' : 'bg-orange-400'}`}
                style={{ width: `${Math.min(mlProgress, 100)}%` }}
              />
            </div>
            <span className="text-xs text-slate-600">
              {sup.pattern_approvazioni || sup.count_pattern || 0}/5
            </span>
          </div>
        </div>

        {(sup.descrizione_anomalia || sup.descrizione_espositore) && (
          <div className="mt-3 p-3 bg-slate-100 rounded-lg border-l-2 border-slate-400">
            <p className="text-sm text-slate-700 font-medium mb-1">Descrizione:</p>
            <p className="text-sm text-slate-600 uppercase">{sup.descrizione_anomalia || sup.descrizione_espositore}</p>
          </div>
        )}
      </div>
    </div>

    {/* Actions */}
    <SupervisioneActions
      sup={sup}
      isProcessing={isProcessing}
      isPrezzo={isPrezzo}
      isListino={isListino}
      isLookup={isLookup}
      isAic={isAic}
      onNavigateToOrdine={onNavigateToOrdine}
      handleApprova={handleApprova}
      handleRifiuta={handleRifiuta}
      handleModifica={handleModifica}
      handleLasciaSospeso={handleLasciaSospeso}
      handleOpenCorrezione={handleOpenCorrezione}
      handleOpenArchiviazione={handleOpenArchiviazione}
      handleOpenAic={handleOpenAic}           // v9.0
      handleRifiutaAic={handleRifiutaAic}     // v9.0
      returnToOrdine={returnToOrdine}
    />
  </div>
);

// =============================================================================
// SUPERVISIONE DETAILS - Dettagli specifici per tipo
// =============================================================================
const SupervisioneDetails = ({ sup, isPrezzo, isListino, isLookup, isAic }) => {
  if (isAic) {
    return (
      <div className="space-y-1">
        <p className="text-slate-600"><strong>Anomalia:</strong> {sup.codice_anomalia}</p>
        <p className="text-slate-600"><strong>Descrizione:</strong> {sup.descrizione_prodotto || sup.descrizione_normalizzata || 'N/A'}</p>
        <p className="text-slate-600"><strong>Codice originale:</strong> {sup.codice_originale || 'N/A'}</p>
        <p className="text-slate-600"><strong>Vendor:</strong> {sup.vendor || 'N/A'}</p>
      </div>
    );
  }

  if (isPrezzo) {
    return (
      <div className="space-y-1">
        <p className="text-slate-600"><strong>Anomalia:</strong> {sup.codice_anomalia}</p>
        <p className="text-slate-600"><strong>Righe senza prezzo:</strong> {sup.numero_righe_coinvolte || 'N/A'}</p>
        <p className="text-slate-600"><strong>Vendor:</strong> {sup.vendor || 'N/A'}</p>
      </div>
    );
  }

  if (isListino) {
    return (
      <div className="space-y-1">
        <p className="text-slate-600"><strong>Anomalia:</strong> {sup.codice_anomalia}</p>
        <p className="text-slate-600"><strong>Codice AIC:</strong> {sup.codice_aic || 'N/A'}</p>
        <p className="text-slate-600"><strong>Prodotto:</strong> <span className="uppercase">{sup.descrizione_prodotto || 'N/D'}</span></p>
        {sup.n_riga && <p className="text-slate-600"><strong>Riga:</strong> {sup.n_riga}</p>}
      </div>
    );
  }

  if (isLookup) {
    return (
      <div className="space-y-1">
        <p className="text-slate-600"><strong>Anomalia:</strong> {sup.codice_anomalia}</p>
        <p className="text-slate-600"><strong>Farmacia estratta:</strong> {sup.ragione_sociale?.toUpperCase() || 'N/A'}</p>
        {sup.piva && <p className="text-slate-600"><strong>P.IVA:</strong> {sup.piva}</p>}
        {sup.lookup_score !== undefined && <p className="text-slate-600"><strong>Score:</strong> {sup.lookup_score}%</p>}
      </div>
    );
  }

  // Espositore
  return (
    <div className="space-y-1">
      <p className="text-slate-600"><strong>Anomalia:</strong> {sup.codice_anomalia}</p>
      <p className="text-slate-600"><strong>Espositore:</strong> {sup.codice_espositore || sup.espositore_codice}</p>
      <p className="text-slate-600">
        <strong>Scostamento:</strong> {sup.percentuale_scostamento}%
        ({sup.pezzi_trovati} vs {sup.pezzi_attesi} attesi)
      </p>
    </div>
  );
};

// =============================================================================
// SUPERVISIONE ACTIONS - Pulsanti azione
// =============================================================================
const SupervisioneActions = ({
  sup,
  isProcessing,
  isPrezzo,
  isListino,
  isLookup,
  isAic,
  onNavigateToOrdine,
  handleApprova,
  handleRifiuta,
  handleModifica,
  handleLasciaSospeso,
  handleOpenCorrezione,
  handleOpenArchiviazione,
  handleOpenAic,       // v9.0
  handleRifiutaAic,    // v9.0
  returnToOrdine,
}) => (
  <div className="flex items-center gap-3 flex-wrap">
    {sup.id_testata && onNavigateToOrdine && (
      <Button variant="secondary" size="sm" onClick={() => onNavigateToOrdine(sup.id_testata)}>
        Vai all'Ordine
      </Button>
    )}

    {isAic ? (
      <>
        <Button variant="primary" size="sm" loading={isProcessing} onClick={() => handleOpenAic?.(sup)} disabled={isProcessing}>
          Assegna AIC
        </Button>
        <Button variant="secondary" size="sm" onClick={() => onNavigateToOrdine?.(sup.id_testata)} disabled={isProcessing}>
          Vai all'Ordine
        </Button>
        <Button variant="danger" size="sm" loading={isProcessing} onClick={() => handleRifiutaAic?.(sup.id_supervisione)} disabled={isProcessing}>
          Rifiuta
        </Button>
      </>
    ) : isPrezzo ? (
      <>
        <Button variant="primary" size="sm" loading={isProcessing} onClick={() => onNavigateToOrdine?.(sup.id_testata)} disabled={isProcessing}>
          Gestisci Prezzi
        </Button>
        <Button variant="success" size="sm" loading={isProcessing} onClick={() => handleApprova(sup.id_supervisione, sup.pattern_signature)} disabled={isProcessing}>
          Approva
        </Button>
        <Button variant="danger" size="sm" loading={isProcessing} onClick={() => handleRifiuta(sup.id_supervisione, sup.pattern_signature)} disabled={isProcessing}>
          Rifiuta
        </Button>
      </>
    ) : isListino ? (
      <>
        <Button variant="primary" size="sm" loading={isProcessing} onClick={() => handleOpenCorrezione(sup)} disabled={isProcessing}>
          Correggi Prezzi
        </Button>
        <Button variant="warning" size="sm" loading={isProcessing} onClick={() => handleOpenArchiviazione(sup)} disabled={isProcessing}>
          Archivia Riga
        </Button>
        <Button variant="success" size="sm" loading={isProcessing} onClick={() => handleApprova(sup.id_supervisione, sup.pattern_signature)} disabled={isProcessing}>
          Approva
        </Button>
      </>
    ) : isLookup ? (
      <>
        <Button variant="success" size="sm" loading={isProcessing} onClick={() => handleApprova(sup.id_supervisione, sup.pattern_signature)} disabled={isProcessing}>
          Approva Farmacia
        </Button>
        <Button variant="danger" size="sm" loading={isProcessing} onClick={() => handleRifiuta(sup.id_supervisione, sup.pattern_signature)} disabled={isProcessing}>
          Rifiuta
        </Button>
      </>
    ) : (
      <>
        <Button variant="success" size="sm" loading={isProcessing} onClick={() => handleApprova(sup.id_supervisione, sup.pattern_signature)} disabled={isProcessing}>
          Approva (+1 ML)
        </Button>
        <Button variant="danger" size="sm" loading={isProcessing} onClick={() => handleRifiuta(sup.id_supervisione, sup.pattern_signature)} disabled={isProcessing}>
          Rifiuta (Reset ML)
        </Button>
        <Button variant="secondary" size="sm" onClick={() => handleModifica(sup.id_supervisione, {})} disabled={isProcessing}>
          Modifica
        </Button>
      </>
    )}

    {returnToOrdine && (
      <Button variant="ghost" size="sm" onClick={() => handleLasciaSospeso(sup.id_supervisione)} disabled={isProcessing}>
        Lascia Sospeso
      </Button>
    )}
  </div>
);

// =============================================================================
// TAB PATTERNS - Pattern ML appresi
// =============================================================================
const TabPatterns = ({ criteri, getMLProgress, handlePromuoviPattern, handleResetPattern }) => (
  <div className="p-6">
    <div className="mb-6 p-4 bg-indigo-50 border border-indigo-200 rounded-lg">
      <h3 className="text-lg font-semibold text-indigo-900 mb-2">Pattern Machine Learning</h3>
      <p className="text-sm text-indigo-700 mb-3">
        Il sistema apprende dai tuoi feedback. Ogni approvazione accumula +1 al pattern.
      </p>
      <div className="flex gap-6 text-xs">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-emerald-500 rounded-full"></div>
          <span className="text-indigo-800"><strong>AUTOMATICO</strong> (5+ approvazioni)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-orange-400 rounded-full"></div>
          <span className="text-indigo-800"><strong>IN APPRENDIMENTO</strong> (&lt;5)</span>
        </div>
      </div>
    </div>

    {criteri.length === 0 ? (
      <div className="text-center py-12 bg-slate-50 rounded-lg">
        <div className="text-5xl mb-4">🧠</div>
        <h4 className="text-lg font-medium text-slate-700 mb-2">Nessun pattern ancora appreso</h4>
        <p className="text-sm text-slate-500">I pattern vengono creati quando approvi anomalie.</p>
      </div>
    ) : (
      <div className="space-y-4">
        {criteri.map((criterio) => (
          <PatternCard
            key={criterio.pattern_signature}
            criterio={criterio}
            getMLProgress={getMLProgress}
            handlePromuoviPattern={handlePromuoviPattern}
            handleResetPattern={handleResetPattern}
          />
        ))}
      </div>
    )}
  </div>
);

// =============================================================================
// PATTERN CARD
// =============================================================================
const PatternCard = ({ criterio, getMLProgress, handlePromuoviPattern, handleResetPattern }) => {
  const approvazioni = criterio.count_approvazioni || 0;
  const progress = getMLProgress(approvazioni);
  const isOrdinario = criterio.is_ordinario || approvazioni >= 5;
  const isListino = criterio.tipo === 'listino';
  const isLookup = criterio.tipo === 'lookup';
  const isPrezzo = criterio.tipo === 'prezzo';
  const mancanti = Math.max(0, 5 - approvazioni);

  return (
    <div
      className={`p-5 border-2 rounded-xl ${
        isOrdinario
          ? 'border-emerald-300 bg-gradient-to-r from-emerald-50 to-green-50'
          : 'border-orange-300 bg-gradient-to-r from-orange-50 to-amber-50'
      }`}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-3">
            <span className={`px-3 py-1 text-sm font-bold rounded-lg ${
              isPrezzo ? 'bg-red-100 text-red-800' :
              isListino ? 'bg-blue-100 text-blue-800' :
              isLookup ? 'bg-amber-100 text-amber-800' :
              'bg-purple-100 text-purple-800'
            }`}>
              {isPrezzo ? 'PREZZO' : isListino ? 'LISTINO' : isLookup ? 'LOOKUP' : 'ESPOSITORE'}
            </span>
            <span className="font-semibold text-slate-800">
              {criterio.codice_anomalia || criterio.pattern_descrizione || 'Pattern'}
            </span>
            {isOrdinario ? (
              <span className="px-3 py-1 text-sm font-bold bg-emerald-200 text-emerald-800 rounded-lg">
                ✓ AUTOMATICO
              </span>
            ) : (
              <span className="px-3 py-1 text-sm font-medium bg-orange-200 text-orange-800 rounded-lg">
                IN APPRENDIMENTO
              </span>
            )}
          </div>

          <div className="bg-white/80 p-3 rounded-lg">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-slate-700">Approvazioni</span>
              <span className={`text-lg font-bold ${isOrdinario ? 'text-emerald-600' : 'text-orange-600'}`}>
                {approvazioni}/5
              </span>
            </div>
            <div className="h-4 bg-slate-200 rounded-full overflow-hidden">
              <div
                className={`h-full transition-all duration-500 ${isOrdinario ? 'bg-emerald-500' : 'bg-orange-400'}`}
                style={{ width: `${progress}%` }}
              />
            </div>
            {!isOrdinario && (
              <p className="text-xs text-slate-500 mt-2">
                Mancano <strong>{mancanti}</strong> approvazioni per diventare automatico
              </p>
            )}
          </div>
        </div>

        <div className="ml-6 flex flex-col gap-3">
          {!isOrdinario && (
            <Button
              variant="primary"
              size="sm"
              onClick={() => handlePromuoviPattern(criterio.pattern_signature)}
            >
              ⚡ Forza Automazione
            </Button>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => handleResetPattern(criterio.pattern_signature)}
            className="text-red-600 hover:bg-red-50"
          >
            Reset Apprendimento
          </Button>
        </div>
      </div>
    </div>
  );
};

// =============================================================================
// TAB STORICO
// =============================================================================
const TabStorico = ({ storico }) => (
  <div className="p-6">
    <div className="mb-4">
      <h3 className="text-lg font-medium text-slate-800 mb-2">Storico Decisioni</h3>
      <p className="text-slate-600 text-sm">Ultime decisioni per audit e verifica.</p>
    </div>

    {storico.length === 0 ? (
      <div className="text-center py-8 text-slate-500">
        <div className="text-4xl mb-3">📜</div>
        <p>Nessuna decisione nello storico</p>
      </div>
    ) : (
      <div className="space-y-3">
        {storico.map((item, idx) => (
          <div
            key={idx}
            className={`p-4 border rounded-lg ${
              item.azione === 'APPROVED' ? 'border-emerald-200 bg-emerald-50' :
              item.azione === 'REJECTED' ? 'border-red-200 bg-red-50' :
              'border-slate-200 bg-slate-50'
            }`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className={`px-2 py-1 text-xs rounded-full ${
                  item.azione === 'APPROVED' ? 'bg-emerald-100 text-emerald-700' :
                  item.azione === 'REJECTED' ? 'bg-red-100 text-red-700' :
                  'bg-slate-100 text-slate-700'
                }`}>
                  {item.azione === 'APPROVED' ? '✓ Approvato' :
                   item.azione === 'REJECTED' ? '✗ Rifiutato' : item.azione}
                </span>
                <span className="text-sm font-medium text-slate-800">
                  Ordine #{item.numero_ordine || item.id_testata}
                </span>
                <VendorBadge vendor={item.vendor} size="xs" />
              </div>
              <div className="text-right text-xs text-slate-500">
                <p>{item.operatore}</p>
                <p>{item.timestamp ? new Date(item.timestamp).toLocaleString('it-IT') : '-'}</p>
              </div>
            </div>
            {item.note && (
              <p className="mt-2 text-sm text-slate-600 italic">"{item.note}"</p>
            )}
          </div>
        ))}
      </div>
    )}
  </div>
);

export default SupervisionePage;
