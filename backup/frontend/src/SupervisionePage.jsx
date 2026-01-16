// =============================================================================
// SUPERVISIONE PAGE - MODERNIZZATA v6.2
// =============================================================================
// Pagina supervisione ML con pattern recognition, workflow di approvazione
// Machine Learning per espositori ANGELINI v3.0
// =============================================================================

import React, { useState, useEffect, useCallback } from 'react';
import { supervisioneApi } from './api';
import { Button, StatusBadge, VendorBadge, Loading, ErrorBox } from './common';

/**
 * Componente SupervisionePage modernizzato
 * 
 * LOGICA IMPLEMENTATIVA:
 * - Sistema ML per pattern recognition su anomalie espositori
 * - Workflow APPROVE/REJECT/MODIFY con conteggio approvazioni
 * - Promozione automatica a "criterio ordinario" dopo 5 approvazioni
 * - Gestione pattern signature e fasci scostamento
 * - Dashboard ML con stats apprendimento
 * 
 * INTERRELAZIONI:
 * - API: supervisioneApi.getPending(), approva(), rifiuta()
 * - ML: pattern signature, soglia promozione, reset automatico
 * - Workflow: blocco ordini, sblocco automatico, audit trail
 * - Navigazione: supporto ritorno a ordine specifico
 */
const SupervisionePage = ({
  supervisioneId,
  returnToOrdine,
  currentUser,
  onReturnToOrdine
}) => {
  const [supervisioni, setSupervisioni] = useState([]);
  const [criteri, setCriteri] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('pending');
  const operatore = currentUser?.username || 'admin';
  const [processingAction, setProcessingAction] = useState(null);

  // Carica dati supervisione
  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [pendingRes, criteriRes, statsRes] = await Promise.all([
        supervisioneApi.getPending(),
        supervisioneApi.getCriteriOrdinari(), 
        supervisioneApi.getCriteriStats(),
      ]);
      
      setSupervisioni(pendingRes.data?.supervisioni || []);
      setCriteri(criteriRes.data?.criteri || []);
      setStats(statsRes.data || {
        totale_pattern: 0,
        pattern_ordinari: 0,
        approvazioni_totali: 0,
        pending: 0
      });
    } catch (err) {
      console.error('Errore caricamento supervisione:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Actions con ML pattern tracking
  const handleApprova = async (id, patternSignature) => {
    if (!window.confirm('Confermi approvazione? Questo contribuirà all\'apprendimento ML.')) return;
    
    setProcessingAction(id);
    try {
      if (returnToOrdine && onReturnToOrdine) {
        // Modalità ritorno a ordine specifico
        await supervisioneApi.approvaETorna(id, operatore);
        onReturnToOrdine(returnToOrdine);
      } else {
        // Modalità normale con ricarico dati
        await supervisioneApi.approva(id, operatore);
        loadData();
      }
    } catch (err) {
      alert('Errore: ' + (err.response?.data?.detail || err.message));
    } finally {
      setProcessingAction(null);
    }
  };

  const handleRifiuta = async (id, patternSignature) => {
    const note = window.prompt('Motivo del rifiuto (obbligatorio):\n\n⚠️ ATTENZIONE: Un rifiuto resetterà l\'apprendimento ML per questo pattern.');
    if (!note || note.trim().length < 5) {
      alert('Motivo troppo breve. Minimo 5 caratteri.');
      return;
    }
    
    setProcessingAction(id);
    try {
      await supervisioneApi.rifiuta(id, operatore, note);
      
      if (returnToOrdine && onReturnToOrdine) {
        onReturnToOrdine(returnToOrdine);
      } else {
        loadData();
      }
    } catch (err) {
      alert('Errore: ' + (err.response?.data?.detail || err.message));
    } finally {
      setProcessingAction(null);
    }
  };

  const handleModifica = async (id, modifiche) => {
    setProcessingAction(id);
    try {
      await supervisioneApi.modifica(id, operatore, modifiche);
      loadData();
    } catch (err) {
      alert('Errore: ' + (err.response?.data?.detail || err.message));
    } finally {
      setProcessingAction(null);
    }
  };

  const handleLasciaSospeso = async (id) => {
    if (returnToOrdine && onReturnToOrdine) {
      try {
        await supervisioneApi.lasciaSospeso(id, operatore);
        onReturnToOrdine(returnToOrdine);
      } catch (err) {
        alert('Errore: ' + (err.response?.data?.detail || err.message));
      }
    }
  };

  const handleResetPattern = async (signature) => {
    if (!window.confirm(
      '⚠️ RESET PATTERN ML\n\n' +
      'Vuoi azzerare il contatore approvazioni per questo pattern?\n\n' +
      'L\'apprendimento ripartirà da zero e il pattern non sarà più automatico.'
    )) return;
    
    try {
      await supervisioneApi.resetPattern(signature);
      loadData();
      alert('✅ Pattern resettato. Apprendimento ripartito da zero.');
    } catch (err) {
      alert('Errore reset: ' + err.message);
    }
  };

  // Utility per calcolare progress ML
  const getMLProgress = (approvazioni) => {
    const soglia = 5; // Soglia per promozione automatica
    return Math.min((approvazioni / soglia) * 100, 100);
  };

  // Utility per determinare urgenza anomalia
  const getAnomaliaUrgency = (anomalia) => {
    if (anomalia.livello === 'CRITICO') return 'high';
    if (anomalia.tipo_scostamento === 'ECCESSO' && anomalia.percentuale_scostamento > 50) return 'high';
    if (anomalia.tipo_scostamento === 'DIFETTO' && anomalia.percentuale_scostamento < -30) return 'medium';
    return 'low';
  };

  // Tabs per navigazione
  const tabs = [
    { 
      id: 'pending', 
      label: 'In Attesa', 
      count: supervisioni.filter(s => s.stato === 'PENDING_REVIEW').length,
      icon: '⏳'
    },
    { 
      id: 'patterns', 
      label: 'Pattern ML', 
      count: criteri.length,
      icon: '🧠'
    },
    { 
      id: 'approved', 
      label: 'Approvate', 
      count: supervisioni.filter(s => s.stato === 'APPROVED').length,
      icon: '✅'
    },
    { 
      id: 'stats', 
      label: 'Analytics', 
      count: stats?.approvazioni_totali || 0,
      icon: '📊'
    }
  ];

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
              <p className="text-xl font-bold text-slate-800">{supervisioni.filter(s => s.stato === 'PENDING_REVIEW').length}</p>
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

        {/* Tab In Attesa */}
        {activeTab === 'pending' && (
          <div className="divide-y divide-slate-100">
            {supervisioni.filter(s => s.stato === 'PENDING_REVIEW').length === 0 ? (
              <div className="p-8 text-center">
                <div className="text-4xl mb-3">🎉</div>
                <h3 className="text-lg font-medium text-slate-800 mb-2">Nessuna supervisione in attesa</h3>
                <p className="text-slate-600">Tutte le anomalie sono state gestite o risolte automaticamente dall'ML.</p>
              </div>
            ) : (
              supervisioni.filter(s => s.stato === 'PENDING_REVIEW').map((sup) => {
                const urgency = getAnomaliaUrgency(sup);
                const mlProgress = getMLProgress(sup.pattern_approvazioni || 0);
                const isProcessing = processingAction === sup.id_supervisione;
                
                return (
                  <div 
                    key={sup.id_supervisione}
                    className={`p-6 ${
                      urgency === 'high' ? 'bg-red-50 border-l-4 border-red-500' :
                      urgency === 'medium' ? 'bg-amber-50 border-l-4 border-amber-500' : ''
                    }`}
                  >
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <h4 className="font-medium text-slate-800">
                            Ordine #{sup.numero_ordine} - {sup.ragione_sociale}
                          </h4>
                          <VendorBadge vendor="ANGELINI" size="xs" />
                          <StatusBadge 
                            status={urgency === 'high' ? 'error' : urgency === 'medium' ? 'warning' : 'pending'} 
                            size="xs"
                          />
                        </div>
                        
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                          <div>
                            <p className="text-slate-600">
                              <strong>Anomalia:</strong> {sup.codice_anomalia}
                            </p>
                            <p className="text-slate-600">
                              <strong>Espositore:</strong> {sup.espositore_codice}
                            </p>
                            <p className="text-slate-600">
                              <strong>Scostamento:</strong> {sup.percentuale_scostamento}% 
                              ({sup.pezzi_trovati} vs {sup.pezzi_attesi} attesi)
                            </p>
                          </div>
                          <div>
                            <p className="text-slate-600">
                              <strong>Pattern:</strong> 
                              <span className="font-mono text-xs ml-1">{sup.pattern_signature?.substr(0, 8)}...</span>
                            </p>
                            <p className="text-slate-600">
                              <strong>Approvazioni ML:</strong> {sup.pattern_approvazioni || 0}/5
                            </p>
                            <div className="mt-2">
                              <div className="flex items-center gap-2">
                                <div className="flex-1 h-2 bg-slate-200 rounded-full overflow-hidden">
                                  <div 
                                    className="h-full bg-gradient-to-r from-orange-400 to-emerald-500 transition-all duration-300"
                                    style={{ width: `${mlProgress}%` }}
                                  />
                                </div>
                                <span className="text-xs text-slate-500">
                                  {Math.round(mlProgress)}%
                                </span>
                              </div>
                              <p className="text-xs text-slate-500 mt-1">
                                {sup.pattern_approvazioni >= 5 ? 
                                  '🎯 Pattern promosso - gestione automatica attiva' :
                                  `${5 - (sup.pattern_approvazioni || 0)} approvazioni rimanenti per automazione`
                                }
                              </p>
                            </div>
                          </div>
                        </div>
                        
                        {sup.descrizione_anomalia && (
                          <div className="mt-3 p-3 bg-slate-50 rounded-lg">
                            <p className="text-sm text-slate-700">{sup.descrizione_anomalia}</p>
                          </div>
                        )}
                      </div>
                    </div>
                    
                    {/* Actions */}
                    <div className="flex items-center gap-3">
                      <Button
                        variant="success"
                        size="sm"
                        loading={isProcessing}
                        onClick={() => handleApprova(sup.id_supervisione, sup.pattern_signature)}
                        disabled={isProcessing}
                      >
                        ✅ Approva (+1 ML)
                      </Button>
                      
                      <Button
                        variant="danger"
                        size="sm"
                        loading={isProcessing}
                        onClick={() => handleRifiuta(sup.id_supervisione, sup.pattern_signature)}
                        disabled={isProcessing}
                      >
                        ❌ Rifiuta (Reset ML)
                      </Button>
                      
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => handleModifica(sup.id_supervisione, {})}
                        disabled={isProcessing}
                      >
                        ✏️ Modifica
                      </Button>
                      
                      {returnToOrdine && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleLasciaSospeso(sup.id_supervisione)}
                          disabled={isProcessing}
                        >
                          ⏸️ Lascia Sospeso
                        </Button>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        )}

        {/* Tab Pattern ML */}
        {activeTab === 'patterns' && (
          <div className="p-6">
            <div className="mb-4">
              <h3 className="text-lg font-medium text-slate-800 mb-2">Pattern Machine Learning</h3>
              <p className="text-slate-600">Criteri appresi automaticamente dal sistema per gestione anomalie.</p>
            </div>
            
            {criteri.length === 0 ? (
              <div className="text-center py-8">
                <div className="text-4xl mb-3">🧠</div>
                <p className="text-slate-500">Nessun pattern ML ancora appreso</p>
                <p className="text-sm text-slate-400 mt-1">I pattern si creano approvando anomalie simili</p>
              </div>
            ) : (
              <div className="space-y-4">
                {criteri.map((criterio) => {
                  const progress = getMLProgress(criterio.count_approvazioni);
                  const isOrdinario = criterio.count_approvazioni >= 5;
                  
                  return (
                    <div 
                      key={criterio.pattern_signature}
                      className={`p-4 border rounded-lg ${
                        isOrdinario ? 'border-emerald-200 bg-emerald-50' : 'border-slate-200 bg-white'
                      }`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <h4 className="font-medium text-slate-800">
                              {criterio.pattern_descrizione}
                            </h4>
                            {isOrdinario && (
                              <StatusBadge status="completed" label="AUTOMATICO" size="xs" />
                            )}
                          </div>
                          
                          <div className="grid grid-cols-2 gap-4 text-sm text-slate-600">
                            <div>
                              <p><strong>Signature:</strong> <code className="text-xs">{criterio.pattern_signature}</code></p>
                              <p><strong>Espositore:</strong> {criterio.codice_espositore}</p>
                            </div>
                            <div>
                              <p><strong>Approvazioni:</strong> {criterio.count_approvazioni}/5</p>
                              <p><strong>Fascia:</strong> {criterio.fascia_scostamento}</p>
                            </div>
                          </div>
                          
                          <div className="mt-3">
                            <div className="flex items-center gap-2">
                              <div className="flex-1 h-2 bg-slate-200 rounded-full overflow-hidden">
                                <div 
                                  className={`h-full transition-all duration-300 ${
                                    isOrdinario ? 'bg-emerald-500' : 'bg-orange-400'
                                  }`}
                                  style={{ width: `${progress}%` }}
                                />
                              </div>
                              <span className="text-xs text-slate-500">{Math.round(progress)}%</span>
                            </div>
                          </div>
                        </div>
                        
                        <div className="ml-4">
                          <Button
                            variant="ghost"
                            size="xs"
                            onClick={() => handleResetPattern(criterio.pattern_signature)}
                          >
                            🔄 Reset
                          </Button>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
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
    </div>
  );
};

export default SupervisionePage;
