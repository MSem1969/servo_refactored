// =============================================================================
// SERV.O v11.4 - SUPERVISIONE PAGE
// =============================================================================
// Pagina supervisione ML con pattern recognition e workflow approvazione
// v9.0: Aggiunto supporto supervisione AIC (AIC-A01)
// v11.4: Refactoring workflow con nuovi bottoni:
//        - Verifica Ordine: naviga all'ordine
//        - Azione Correttiva: apre modal per correzione (stessa del operatore)
//        - Supervisione: apre modal per review correzione operatore
//        Aggiunto supporto ANAGRAFICA (unifica lookup + deposito)
// =============================================================================

import React, { useEffect } from 'react';
import { Button, StatusBadge, VendorBadge, Loading } from '../../common';
import { useSupervisione } from './hooks/useSupervisione';
import CorrezioneLisinoModal from './CorrezioneLisinoModal';
import ArchiviazioneListinoModal from './ArchiviazioneListinoModal';
// v11.0: Usa AicAssignmentModal unificato (TIER 2.1)
import { AicAssignmentModal, AIC_MODAL_MODES } from '../../components/AicAssignmentModal';
// v11.4: AnomaliaDetailModal unificato per LOOKUP/ANAGRAFICA (stessa UI operatore e supervisore)
import { AnomaliaDetailModal } from '../../components/AnomaliaDetailModal';

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
  // v11.4: Navigazione con ritorno
  onNavigateWithReturn,
  initialContext
}) => {
  const {
    // State
    supervisioni,
    groupedSupervisioni,
    criteri,
    // storico, // v11.4: Rimosso - tab non utilizzato
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
    anagraficaModal, // v11.4

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
    handleDeletePattern, // v11.4

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
    handleOpenAnagrafica,    // v11.4
    handleCloseAnagrafica,   // v11.4
    handleAnagraficaSuccess, // v11.4
    handleRifiutaAnagrafica, // v11.4

    // Bulk actions
    handleRiapplicaListinoLst,  // v10.0 - Riapplica listino unificato

    // Utilities
    getMLProgress,
    getAnomaliaUrgency,
  } = useSupervisione({ currentUser, returnToOrdine, onReturnToOrdine, initialContext });

  useEffect(() => {
    loadData();
  }, [loadData]);

  // v11.4: Funzione generica per navigare con salvataggio contesto
  // Usata da tutti i bottoni che devono tornare a Supervisione (Verifica Ordine, etc.)
  const handleNavigateWithReturn = (idTestata) => {
    if (onNavigateWithReturn) {
      // Salva contesto corrente per ripristinarlo al ritorno
      const context = {
        activeTab,
        viewMode,
        // Potremmo aggiungere: scrollPosition, selectedPattern, etc.
      };
      onNavigateWithReturn('ordine-detail', { ordineId: idTestata }, context);
    }
  };

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
            onNavigateToOrdine={handleNavigateWithReturn}
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
            handleOpenAnagrafica={handleOpenAnagrafica}  // v11.4
            handleRifiutaAnagrafica={handleRifiutaAnagrafica}  // v11.4
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
            handleDeletePattern={handleDeletePattern}
          />
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

      {/* v11.4: AnomaliaDetailModal unificato per LOOKUP/ANAGRAFICA */}
      <AnomaliaDetailModal
        isOpen={anagraficaModal.isOpen}
        onClose={handleCloseAnagrafica}
        anomaliaDetail={anagraficaModal.anomaliaDetail}
        loading={anagraficaModal.loading}
        // v11.4: Props per supporto Supervisione
        fromSupervisione={true}
        supervisione={anagraficaModal.supervisione}
        onSupervisioneSuccess={handleAnagraficaSuccess}
        // Callback per assegnazione farmacia (usa lookupApi.manuale)
        onAssignFarmacia={async (idTestata, idFarmacia, idParafarmacia, manualMinId) => {
          try {
            const { lookupApi } = await import('../../api');
            const result = await lookupApi.manuale(idTestata, idFarmacia, idParafarmacia, manualMinId);
            if (result.success) {
              handleAnagraficaSuccess(result);
              return true;
            }
            return false;
          } catch (err) {
            console.error('Errore assegnazione:', err);
            return false;
          }
        }}
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
  handleOpenAnagrafica,    // v11.4
  handleRifiutaAnagrafica, // v11.4
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
          handleOpenAnagrafica={handleOpenAnagrafica}
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
          handleOpenAnagrafica={handleOpenAnagrafica}      // v11.4
          handleRifiutaAnagrafica={handleRifiutaAnagrafica}// v11.4
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
  'aic': 1,        // AIC mancante - più critico
  'prezzo': 2,     // Prezzi mancanti
  'listino': 3,    // Problemi listino
  'anagrafica': 4, // Problemi header/lookup - v11.4
  'lookup': 5,     // Farmacia non trovata (legacy)
  'espositore': 6, // Problemi espositori
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
  handleOpenAnagrafica,
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
    'anagrafica': { bg: 'bg-orange-100', text: 'text-orange-700', label: 'ANAGRAFICA' },  // v11.4
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
                  {/* v11.0: Per LOOKUP mostra ragione_sociale cliente per distinguere i pattern */}
                  {group.tipo_supervisione === 'lookup'
                    ? `Cliente: ${(group.descrizione_prodotto || 'N/A').toUpperCase()}`
                    : group.descrizione_prodotto
                      ? `${group.codice_aic || ''} - ${group.descrizione_prodotto}`.trim()
                      : (group.pattern_descrizione || `Pattern: ${group.pattern_signature?.substring(0, 12)}...`)}
                </p>
                <div className="flex flex-wrap gap-4 text-sm text-slate-500">
                  <span><strong>{group.total_count}</strong> supervisioni</span>
                  <span><strong>{group.affected_order_ids?.length || 0}</strong> ordini</span>
                  <span className="truncate max-w-md" title={Array.isArray(group.affected_orders_preview) ? group.affected_orders_preview.join(' | ') : group.affected_orders_preview}>
                    {/* v11.0: Separatore "|" tra ordini */}
                    Ordini: {Array.isArray(group.affected_orders_preview)
                      ? group.affected_orders_preview.join(' | ')
                      : (group.affected_orders_preview || 'N/A').toString().replace(/,\s*/g, ' | ')}
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

            {/* Actions - v11.4: Workflow UNIFICATO per TUTTI i pattern */}
            {/* 1. Verifica Ordine  2. Azione Correttiva  3. Supervisione */}
            <div className="mt-4 flex items-center gap-3 flex-wrap">
              {/* 1. VERIFICA ORDINE - sempre presente per tutti */}
              {group.affected_order_ids?.length > 0 && onNavigateToOrdine && (
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => onNavigateToOrdine(group.affected_order_ids[0])}
                >
                  Verifica Ordine
                </Button>
              )}

              {/* 2. AZIONE CORRETTIVA - apre modal/azione specifica per tipo */}
              {(() => {
                const firstSup = supervisioni.find(s => s.pattern_signature === group.pattern_signature);
                if (!firstSup) return null;

                // Azione correttiva specifica per tipo
                if (group.tipo_supervisione === 'anagrafica' || group.tipo_supervisione === 'lookup') {
                  return (
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => handleOpenAnagrafica?.(firstSup)}
                      disabled={isProcessing}
                    >
                      Azione Correttiva
                    </Button>
                  );
                }
                if (group.tipo_supervisione === 'aic') {
                  return (
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => handleOpenAic?.({
                        ...firstSup,
                        is_bulk: true,
                        pattern_signature: group.pattern_signature,
                        total_count: group.total_count,
                        affected_order_ids: group.affected_order_ids
                      })}
                      disabled={isProcessing}
                    >
                      Azione Correttiva
                    </Button>
                  );
                }
                if (group.tipo_supervisione === 'listino' || group.tipo_supervisione === 'prezzo') {
                  // PREZZO e LISTINO usano stesso modal CorrezioneLisinoModal
                  return (
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => handleOpenCorrezione?.(firstSup)}
                      disabled={isProcessing}
                    >
                      Azione Correttiva
                    </Button>
                  );
                }
                // ESPOSITORE - va alla tab Espositore dell'ordine
                return (
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => onNavigateToOrdine?.(group.affected_order_ids?.[0])}
                    disabled={isProcessing}
                  >
                    Azione Correttiva
                  </Button>
                );
              })()}

              {/* 3. SUPERVISIONE - approva pattern (sempre presente) */}
              <Button
                variant="success"
                size="sm"
                loading={isProcessing}
                onClick={() => handleApprovaBulk(group.pattern_signature, group.total_count)}
                disabled={isProcessing}
              >
                Supervisione ({group.total_count})
              </Button>
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
  handleOpenAnagrafica,    // v11.4
  handleRifiutaAnagrafica, // v11.4
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
        const isAnagrafica = sup.tipo_supervisione === 'anagrafica' || sup.codice_anomalia?.startsWith('DEP-');  // v11.4
        const vendorDisplay = isListino ? (sup.vendor || 'CODIFI') : (sup.vendor || 'ANGELINI');

        return (
          <SupervisioneCard
            key={`${isPrezzo ? 'prz' : isAic ? 'aic' : isListino ? 'lst' : isAnagrafica ? 'ana' : isLookup ? 'lkp' : 'esp'}-${sup.id_supervisione}`}
            sup={sup}
            urgency={urgency}
            mlProgress={mlProgress}
            isProcessing={isProcessing}
            isListino={isListino}
            isLookup={isLookup}
            isPrezzo={isPrezzo}
            isAic={isAic}
            isAnagrafica={isAnagrafica}
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
            handleOpenAnagrafica={handleOpenAnagrafica}      // v11.4
            handleRifiutaAnagrafica={handleRifiutaAnagrafica}// v11.4
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
  isAnagrafica, // v11.4
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
  handleOpenAnagrafica,    // v11.4
  handleRifiutaAnagrafica, // v11.4
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
          ) : isAnagrafica ? (
            <span className="px-2 py-0.5 text-xs bg-orange-100 text-orange-700 rounded-full">ANAGRAFICA</span>
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
          <SupervisioneDetails sup={sup} isPrezzo={isPrezzo} isListino={isListino} isLookup={isLookup} isAic={isAic} isAnagrafica={isAnagrafica} />

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
      isAnagrafica={isAnagrafica}
      onNavigateToOrdine={onNavigateToOrdine}
      handleApprova={handleApprova}
      handleRifiuta={handleRifiuta}
      handleModifica={handleModifica}
      handleLasciaSospeso={handleLasciaSospeso}
      handleOpenCorrezione={handleOpenCorrezione}
      handleOpenArchiviazione={handleOpenArchiviazione}
      handleOpenAic={handleOpenAic}           // v9.0
      handleRifiutaAic={handleRifiutaAic}     // v9.0
      handleOpenAnagrafica={handleOpenAnagrafica}      // v11.4
      handleRifiutaAnagrafica={handleRifiutaAnagrafica}// v11.4
      returnToOrdine={returnToOrdine}
    />
  </div>
);

// =============================================================================
// SUPERVISIONE DETAILS - Dettagli specifici per tipo
// =============================================================================
const SupervisioneDetails = ({ sup, isPrezzo, isListino, isLookup, isAic, isAnagrafica }) => {
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

  // v11.4: Anagrafica (unifica lookup + deposito + header)
  if (isAnagrafica || isLookup) {
    return (
      <div className="space-y-1">
        <p className="text-slate-600"><strong>Anomalia:</strong> {sup.codice_anomalia}</p>
        <p className="text-slate-600"><strong>Ragione sociale:</strong> {(sup.ragione_sociale_estratta || sup.ragione_sociale)?.toUpperCase() || 'N/A'}</p>
        {(sup.piva_estratta || sup.piva) && <p className="text-slate-600"><strong>P.IVA:</strong> {sup.piva_estratta || sup.piva}</p>}
        {sup.deposito_estratto && <p className="text-slate-600"><strong>Deposito:</strong> {sup.deposito_estratto}</p>}
        {sup.lookup_score !== undefined && <p className="text-slate-600"><strong>Score:</strong> {sup.lookup_score}%</p>}
        {sup.operatore_correzione && (
          <p className="text-emerald-600"><strong>Corretto da:</strong> {sup.operatore_correzione}</p>
        )}
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
  isAnagrafica,
  onNavigateToOrdine,
  handleApprova,
  handleRifiuta,
  handleModifica,
  handleLasciaSospeso,
  handleOpenCorrezione,
  handleOpenArchiviazione,
  handleOpenAic,       // v9.0
  handleRifiutaAic,    // v9.0
  handleOpenAnagrafica,    // v11.4
  handleRifiutaAnagrafica, // v11.4
  returnToOrdine,
}) => {
  // v11.4: Workflow UNIFICATO - tutti i pattern hanno: Verifica Ordine + Azione Correttiva + Supervisione

  return (
    <div className="flex items-center gap-3 flex-wrap">
      {/* 1. VERIFICA ORDINE - sempre presente per tutti */}
      {sup.id_testata && onNavigateToOrdine && (
        <Button variant="secondary" size="sm" onClick={() => onNavigateToOrdine(sup.id_testata)}>
          Verifica Ordine
        </Button>
      )}

      {/* 2. AZIONE CORRETTIVA - specifica per tipo pattern */}
      {(isAnagrafica || isLookup) ? (
        <Button
          variant="primary"
          size="sm"
          loading={isProcessing}
          onClick={() => handleOpenAnagrafica?.(sup)}
          disabled={isProcessing}
        >
          Azione Correttiva
        </Button>
      ) : isAic ? (
        <Button variant="primary" size="sm" loading={isProcessing} onClick={() => handleOpenAic?.(sup)} disabled={isProcessing}>
          Azione Correttiva
        </Button>
      ) : (isPrezzo || isListino) ? (
        // PREZZO e LISTINO usano stesso modal CorrezioneLisinoModal
        <Button variant="primary" size="sm" loading={isProcessing} onClick={() => handleOpenCorrezione?.(sup)} disabled={isProcessing}>
          Azione Correttiva
        </Button>
      ) : (
        // ESPOSITORE - va alla tab Espositore dell'ordine
        <Button variant="primary" size="sm" loading={isProcessing} onClick={() => onNavigateToOrdine?.(sup.id_testata)} disabled={isProcessing}>
          Azione Correttiva
        </Button>
      )}

      {/* 3. SUPERVISIONE - sempre presente per tutti */}
      <Button
        variant="success"
        size="sm"
        loading={isProcessing}
        onClick={() => handleApprova(sup.id_supervisione, sup.pattern_signature)}
        disabled={isProcessing}
      >
        Supervisione
      </Button>

      {returnToOrdine && (
        <Button variant="ghost" size="sm" onClick={() => handleLasciaSospeso(sup.id_supervisione)} disabled={isProcessing}>
          Lascia Sospeso
        </Button>
      )}
    </div>
  );
};

// =============================================================================
// TAB PATTERNS - Pattern ML appresi
// =============================================================================
const TabPatterns = ({ criteri, getMLProgress, handlePromuoviPattern, handleResetPattern, handleDeletePattern }) => (
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
            handleDeletePattern={handleDeletePattern}
          />
        ))}
      </div>
    )}
  </div>
);

// =============================================================================
// PATTERN CARD - v11.4: Descrizioni migliorate, 3 azioni per tutti i pattern
// =============================================================================
const PatternCard = ({ criterio, getMLProgress, handlePromuoviPattern, handleResetPattern, handleDeletePattern }) => {
  const approvazioni = criterio.count_approvazioni || 0;
  const progress = getMLProgress(approvazioni);
  const isOrdinario = criterio.is_ordinario || approvazioni >= 5;
  const isListino = criterio.tipo === 'listino';
  const isLookup = criterio.tipo === 'lookup';
  const isPrezzo = criterio.tipo === 'prezzo';
  const isAic = criterio.tipo === 'aic';
  const mancanti = Math.max(0, 5 - approvazioni);

  // v11.4: Costruisci descrizione per LISTINO: codice_anomalia - VENDOR - AIC xxx - descrizione_prodotto
  const buildListinoDescription = () => {
    const codiceAnom = criterio.codice_anomalia || 'LST-A01';
    const vendor = criterio.vendor || '';
    const aic = criterio.codice_aic || '';
    const descProdotto = criterio.descrizione_prodotto || '';
    const parts = [];
    parts.push(codiceAnom);
    if (vendor) parts.push(vendor);
    if (aic) parts.push(`AIC ${aic}`);
    if (descProdotto) parts.push(descProdotto);
    return parts.join(' - ');
  };

  // v11.4: Costruisci descrizione per LOOKUP: codice_anomalia - VENDOR - ragione_sociale_farmacia
  const buildLookupDescription = () => {
    const codiceAnom = criterio.codice_anomalia || 'LKP-A01';
    const vendor = criterio.vendor || '';
    let farmacia = criterio.ragione_sociale_farmacia || '';

    // v11.4: Fallback - estrai farmacia da pattern_descrizione se non disponibile dal JOIN
    // Formato: "Lookup VENDOR - LKP-A0x - MIN_ID RAGIONE_SOCIALE - CITTA"
    if (!farmacia && criterio.pattern_descrizione) {
      const desc = criterio.pattern_descrizione;
      // Trova tutto dopo "LKP-A0x - " (terzo segmento)
      const match = desc.match(/LKP-A\d+\s*-\s*(.+)/);
      if (match && match[1]) {
        farmacia = match[1].trim();
      }
    }

    const parts = [];
    parts.push(codiceAnom);
    if (vendor) parts.push(vendor);
    if (farmacia) parts.push(farmacia);
    return parts.join(' - ');
  };

  // v11.4: Costruisci descrizione per ESPOSITORE: codice - descrizione normalizzata
  const buildEspositoreDescription = () => {
    const codiceEsp = criterio.codice_espositore || '';
    const desc = criterio.descrizione_normalizzata || criterio.pattern_descrizione || '';
    const fascia = criterio.fascia_scostamento || '';
    const parts = [];
    if (codiceEsp) parts.push(codiceEsp);
    if (desc) parts.push(desc);
    if (fascia) parts.push(`±${fascia}%`);
    return parts.join(' - ') || 'Pattern espositore';
  };

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
              isAic ? 'bg-teal-100 text-teal-800' :
              isListino ? 'bg-blue-100 text-blue-800' :
              isLookup ? 'bg-amber-100 text-amber-800' :
              'bg-purple-100 text-purple-800'
            }`}>
              {isPrezzo ? 'PREZZO' : isAic ? 'AIC' : isListino ? 'LISTINO' : isLookup ? 'LOOKUP' : 'ESPOSITORE'}
            </span>
            {/* v11.4: Descrizione inline migliorata per tutti i tipi */}
            <span className="font-semibold text-slate-800">
              {(isListino || isPrezzo)
                ? buildListinoDescription()
                : isLookup
                ? buildLookupDescription()
                : isAic
                ? (criterio.codice_aic_default ? `${criterio.codice_aic_default} - ${criterio.descrizione_normalizzata || criterio.pattern_descrizione || ''}` : criterio.pattern_descrizione || 'Pattern AIC')
                : buildEspositoreDescription()}
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

        {/* v11.4: 3 azioni sempre presenti per tutti i pattern */}
        <div className="ml-6 flex flex-col gap-2">
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
            className="text-amber-600 hover:bg-amber-50"
          >
            🔄 Reset Apprendimento
          </Button>
          <Button
            variant="danger"
            size="sm"
            onClick={() => handleDeletePattern(criterio.pattern_signature)}
            className="bg-red-600 hover:bg-red-700 text-white"
          >
            🗑️ CANCELLA
          </Button>
        </div>
      </div>
    </div>
  );
};

export default SupervisionePage;
