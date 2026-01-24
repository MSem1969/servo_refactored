// =============================================================================
// SERV.O v11.0 - ESPOSITORE TAB COMPONENT
// =============================================================================
// Tab per correzione relazioni parent/child (espositore) delle righe ordine
// =============================================================================

import React, { useState, useMemo, useCallback } from 'react';

// Tipi riga disponibili
const TIPO_RIGA_OPTIONS = [
  { value: 'NORMAL', label: 'Normale', color: 'bg-slate-100 text-slate-700' },
  { value: 'PARENT_ESPOSITORE', label: 'Parent (Espositore)', color: 'bg-purple-100 text-purple-700' },
  { value: 'CHILD_ESPOSITORE', label: 'Child', color: 'bg-blue-100 text-blue-700' }
];

// Helper per determinare tipo corrente
function getTipoRigaCorrente(riga) {
  if (riga.tipo_riga === 'PARENT_ESPOSITORE' || (riga.is_espositore && !riga.is_child && !riga.id_parent_espositore)) {
    // Se ha is_espositore=true senza parent, potrebbe essere un parent
    if (riga.is_espositore && !riga.is_child) {
      return 'PARENT_ESPOSITORE';
    }
  }
  if (riga.tipo_riga === 'CHILD_ESPOSITORE' || riga.is_child || riga.id_parent_espositore) {
    return 'CHILD_ESPOSITORE';
  }
  if (riga.tipo_riga === 'PARENT_ESPOSITORE') {
    return 'PARENT_ESPOSITORE';
  }
  return 'NORMAL';
}

export default function EspositoreTab({
  righe,
  ordine,
  onFixEspositore,
  loading = false
}) {
  // Stato locale per le modifiche
  const [modifiche, setModifiche] = useState({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  // Calcola righe con stato corrente (originale + modifiche)
  const righeConStato = useMemo(() => {
    return righe.map(riga => {
      // Use String key for consistent access
      const key = String(riga.id_dettaglio);
      const mod = modifiche[key];
      const tipoCorrente = mod?.tipo_riga ?? getTipoRigaCorrente(riga);
      const parentCorrente = mod?.id_parent_espositore ?? riga.id_parent_espositore;

      return {
        ...riga,
        tipo_riga_corrente: tipoCorrente,
        id_parent_corrente: parentCorrente,
        modificata: !!mod
      };
    });
  }, [righe, modifiche]);

  // Lista dei parent disponibili (per dropdown child)
  const parentDisponibili = useMemo(() => {
    return righeConStato.filter(r => r.tipo_riga_corrente === 'PARENT_ESPOSITORE');
  }, [righeConStato]);

  // Conta modifiche pendenti
  const numModifiche = Object.keys(modifiche).length;

  // Handler cambio tipo riga
  const handleTipoChange = useCallback((idDettaglio, nuovoTipo) => {
    const key = String(idDettaglio);
    setModifiche(prev => {
      const newMod = { ...prev };

      if (!newMod[key]) {
        newMod[key] = {};
      }

      newMod[key].tipo_riga = nuovoTipo;

      // Se diventa NORMAL o PARENT, rimuovi parent
      if (nuovoTipo !== 'CHILD_ESPOSITORE') {
        newMod[key].id_parent_espositore = null;
      }

      return newMod;
    });
    setSuccess(null);
    setError(null);
  }, []);

  // Handler cambio parent per child
  const handleParentChange = useCallback((idDettaglio, idParent) => {
    const key = String(idDettaglio);
    setModifiche(prev => ({
      ...prev,
      [key]: {
        ...prev[key],
        id_parent_espositore: idParent ? parseInt(idParent) : null
      }
    }));
    setSuccess(null);
    setError(null);
  }, []);

  // Reset modifiche
  const handleReset = useCallback(() => {
    setModifiche({});
    setError(null);
    setSuccess(null);
  }, []);

  // Salva modifiche
  const handleSave = useCallback(async () => {
    if (numModifiche === 0) return;

    // Prepara righe da inviare
    const righeToUpdate = Object.entries(modifiche).map(([idDettaglio, mod]) => {
      const riga = righe.find(r => r.id_dettaglio === parseInt(idDettaglio));
      const tipoRiga = mod.tipo_riga ?? getTipoRigaCorrente(riga);

      return {
        id_dettaglio: parseInt(idDettaglio),
        tipo_riga: tipoRiga,
        id_parent_espositore: tipoRiga === 'CHILD_ESPOSITORE' ? mod.id_parent_espositore : null
      };
    });

    // Valida che tutti i child abbiano un parent
    const childSenzaParent = righeToUpdate.filter(
      r => r.tipo_riga === 'CHILD_ESPOSITORE' && !r.id_parent_espositore
    );
    if (childSenzaParent.length > 0) {
      setError(`${childSenzaParent.length} righe CHILD non hanno un parent assegnato`);
      return;
    }

    setSaving(true);
    setError(null);

    try {
      const result = await onFixEspositore(righeToUpdate);
      if (result?.success) {
        setSuccess(`Aggiornate ${result.righe_aggiornate} righe`);
        setModifiche({});
      } else {
        setError(result?.error || 'Errore durante il salvataggio');
      }
    } catch (err) {
      setError(err.message || 'Errore durante il salvataggio');
    } finally {
      setSaving(false);
    }
  }, [modifiche, numModifiche, righe, onFixEspositore]);

  // Quick action: imposta prima riga come parent e altre come child
  const handleAutoSetup = useCallback(() => {
    if (righe.length < 2) return;

    const newMod = {};
    const parentId = righe[0].id_dettaglio;
    const parentKey = String(parentId);

    // Prima riga = PARENT
    newMod[parentKey] = { tipo_riga: 'PARENT_ESPOSITORE', id_parent_espositore: null };

    // Altre righe = CHILD
    righe.slice(1).forEach(riga => {
      const key = String(riga.id_dettaglio);
      newMod[key] = {
        tipo_riga: 'CHILD_ESPOSITORE',
        id_parent_espositore: parentId  // Keep as number for comparison
      };
    });

    setModifiche(newMod);
    setSuccess(null);
    setError(null);
  }, [righe]);

  if (loading) {
    return (
      <div className="text-center py-8">
        <div className="animate-spin text-2xl mb-2">...</div>
        <p className="text-slate-500">Caricamento...</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header con info */}
      <div className="bg-purple-50 rounded-lg p-4">
        <h4 className="font-semibold text-purple-800 mb-2 flex items-center gap-2">
          <span>Configurazione Espositore</span>
          {numModifiche > 0 && (
            <span className="text-xs bg-purple-200 text-purple-700 px-2 py-1 rounded">
              {numModifiche} modifiche pendenti
            </span>
          )}
        </h4>
        <p className="text-sm text-purple-700">
          Configura le relazioni parent/child per gli espositori.
          Il <strong>Parent</strong> rappresenta l'espositore completo,
          i <strong>Child</strong> sono i singoli prodotti contenuti.
        </p>
      </div>

      {/* Messaggi */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-red-700 text-sm">
          {error}
        </div>
      )}
      {success && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-3 text-green-700 text-sm">
          {success}
        </div>
      )}

      {/* Quick Actions */}
      <div className="flex gap-2 flex-wrap">
        <button
          onClick={handleAutoSetup}
          disabled={righe.length < 2}
          className="px-3 py-1.5 bg-purple-100 hover:bg-purple-200 text-purple-700 rounded text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
          title="Imposta riga 1 come Parent e le altre come Child"
        >
          Auto: Riga 1 = Parent, resto = Child
        </button>
        {numModifiche > 0 && (
          <button
            onClick={handleReset}
            className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded text-sm font-medium"
          >
            Annulla modifiche
          </button>
        )}
      </div>

      {/* Tabella righe */}
      <div className="overflow-x-auto border border-slate-200 rounded-lg">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left">
            <tr>
              <th className="px-3 py-2 font-medium text-slate-600">N.</th>
              <th className="px-3 py-2 font-medium text-slate-600">Codice AIC</th>
              <th className="px-3 py-2 font-medium text-slate-600">Descrizione</th>
              <th className="px-3 py-2 font-medium text-slate-600 text-right">Prezzo</th>
              <th className="px-3 py-2 font-medium text-slate-600 text-center">Qta</th>
              <th className="px-3 py-2 font-medium text-slate-600">Tipo Riga</th>
              <th className="px-3 py-2 font-medium text-slate-600">Parent</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200">
            {righeConStato.map((riga) => {
              const tipoOption = TIPO_RIGA_OPTIONS.find(o => o.value === riga.tipo_riga_corrente);
              const isChild = riga.tipo_riga_corrente === 'CHILD_ESPOSITORE';

              return (
                <tr
                  key={riga.id_dettaglio}
                  className={`${riga.modificata ? 'bg-yellow-50' : 'bg-white'} hover:bg-slate-50`}
                >
                  <td className="px-3 py-2 text-slate-500">
                    {riga.n_riga}
                    {riga.modificata && <span className="ml-1 text-yellow-600">*</span>}
                  </td>
                  <td className="px-3 py-2 font-mono text-xs">
                    {riga.codice_aic || riga.codice_originale || '-'}
                  </td>
                  <td className="px-3 py-2 uppercase max-w-xs truncate" title={riga.descrizione}>
                    {riga.descrizione || '-'}
                  </td>
                  <td className="px-3 py-2 text-right">
                    {riga.prezzo_netto ? `${parseFloat(riga.prezzo_netto).toFixed(2)}` : '-'}
                  </td>
                  <td className="px-3 py-2 text-center">
                    {riga.q_venduta || 0}
                  </td>
                  <td className="px-3 py-2">
                    <select
                      value={riga.tipo_riga_corrente}
                      onChange={(e) => handleTipoChange(riga.id_dettaglio, e.target.value)}
                      className={`px-2 py-1 rounded text-xs font-medium border-0 ${tipoOption?.color || 'bg-slate-100'}`}
                    >
                      {TIPO_RIGA_OPTIONS.map(opt => (
                        <option key={opt.value} value={opt.value}>
                          {opt.label}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="px-3 py-2">
                    {isChild ? (
                      <select
                        value={riga.id_parent_corrente || ''}
                        onChange={(e) => handleParentChange(riga.id_dettaglio, e.target.value)}
                        className={`px-2 py-1 rounded text-xs border ${
                          !riga.id_parent_corrente ? 'border-red-300 bg-red-50' : 'border-slate-200'
                        }`}
                      >
                        <option value="">-- Seleziona Parent --</option>
                        {parentDisponibili
                          .filter(p => p.id_dettaglio !== riga.id_dettaglio)
                          .map(parent => (
                            <option key={parent.id_dettaglio} value={parent.id_dettaglio}>
                              Riga {parent.n_riga}: {(parent.descrizione || '').substring(0, 30)}
                            </option>
                          ))
                        }
                      </select>
                    ) : (
                      <span className="text-slate-400 text-xs">-</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Anteprima struttura */}
      {parentDisponibili.length > 0 && (
        <div className="bg-slate-50 rounded-lg p-4">
          <h5 className="font-medium text-slate-700 mb-2">Anteprima Struttura</h5>
          <div className="space-y-2">
            {parentDisponibili.map(parent => {
              const children = righeConStato.filter(
                r => r.tipo_riga_corrente === 'CHILD_ESPOSITORE' &&
                     Number(r.id_parent_corrente) === Number(parent.id_dettaglio)
              );

              return (
                <div key={parent.id_dettaglio} className="border border-purple-200 rounded p-2 bg-white">
                  <div className="flex items-center gap-2 text-purple-700 font-medium">
                    <span className="text-purple-500">PARENT:</span>
                    <span className="uppercase">{parent.descrizione?.substring(0, 40) || '-'}</span>
                    <span className="text-xs text-slate-500">
                      ({parseFloat(parent.prezzo_netto || 0).toFixed(2)})
                    </span>
                  </div>
                  {children.length > 0 ? (
                    <div className="ml-4 mt-1 space-y-1">
                      {children.map(child => (
                        <div key={child.id_dettaglio} className="flex items-center gap-2 text-sm text-blue-700">
                          <span className="text-blue-400">CHILD:</span>
                          <span className="uppercase">{child.descrizione?.substring(0, 35) || '-'}</span>
                          <span className="text-xs text-slate-500">
                            (x{child.q_venduta || 0} @ {parseFloat(child.prezzo_netto || 0).toFixed(2)})
                          </span>
                        </div>
                      ))}
                      <div className="text-xs text-slate-500 border-t border-slate-200 pt-1 mt-1">
                        Totale child: {children.reduce((sum, c) => sum + parseFloat(c.prezzo_netto || 0) * (c.q_venduta || 0), 0).toFixed(2)}
                      </div>
                    </div>
                  ) : (
                    <div className="ml-4 mt-1 text-xs text-orange-600">
                      Nessun child assegnato
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Footer con pulsanti */}
      <div className="flex justify-end gap-3 pt-4 border-t border-slate-200">
        <button
          onClick={handleReset}
          disabled={numModifiche === 0 || saving}
          className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded font-medium disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Annulla
        </button>
        <button
          onClick={handleSave}
          disabled={numModifiche === 0 || saving}
          className={`px-4 py-2 rounded font-medium flex items-center gap-2 ${
            numModifiche > 0 && !saving
              ? 'bg-purple-600 hover:bg-purple-700 text-white'
              : 'bg-slate-300 text-slate-500 cursor-not-allowed'
          }`}
        >
          {saving ? (
            <>
              <span className="animate-spin">...</span>
              Salvataggio...
            </>
          ) : (
            <>
              Salva Modifiche ({numModifiche})
            </>
          )}
        </button>
      </div>
    </div>
  );
}
