// =============================================================================
// SERV.O v10.0 - PERMESSI TAB
// =============================================================================
// Gestione matrice permessi per ruoli
// =============================================================================

import React, { useState, useEffect, useCallback } from 'react';
import { permessiApi } from '../../api';
import { Button, Loading } from '../../common';

const RUOLI_DISPLAY = {
  admin: { label: 'Admin', color: 'bg-red-100 text-red-800', description: 'Accesso completo' },
  superuser: { label: 'Superuser', color: 'bg-purple-100 text-purple-800', description: 'Gestione supervisori' },
  supervisore: { label: 'Supervisore', color: 'bg-blue-100 text-blue-800', description: 'Gestione operatori' },
  operatore: { label: 'Operatore', color: 'bg-green-100 text-green-800', description: 'Upload e database' },
  readonly: { label: 'Sola Lettura', color: 'bg-slate-100 text-slate-800', description: 'Solo visualizzazione' },
};

export default function PermessiTab() {
  const [matrice, setMatrice] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [changes, setChanges] = useState({});

  // Carica matrice permessi
  const loadMatrice = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await permessiApi.getMatrice();
      setMatrice(data);
      setChanges({});
    } catch (err) {
      setError(err.response?.data?.detail || 'Errore caricamento permessi');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadMatrice();
  }, [loadMatrice]);

  // Gestisce cambio checkbox
  const handleToggle = (ruolo, sezione, field) => {
    if (ruolo === 'admin') return; // Admin non modificabile

    const currentValue = getPermessoValue(ruolo, sezione, field);
    const newValue = !currentValue;

    // Se stiamo disabilitando can_view, disabilita anche can_edit
    let updatedPermesso = { ...getChangeOrCurrent(ruolo, sezione) };

    if (field === 'can_view' && !newValue) {
      updatedPermesso.can_view = false;
      updatedPermesso.can_edit = false;
    } else if (field === 'can_edit' && newValue) {
      // Se abiliti can_edit, abilita anche can_view
      updatedPermesso.can_view = true;
      updatedPermesso.can_edit = true;
    } else {
      updatedPermesso[field] = newValue;
    }

    setChanges(prev => ({
      ...prev,
      [`${ruolo}:${sezione}`]: updatedPermesso
    }));
  };

  // Ottiene valore permesso (da changes o da matrice originale)
  const getChangeOrCurrent = (ruolo, sezione) => {
    const key = `${ruolo}:${sezione}`;
    if (changes[key]) {
      return changes[key];
    }
    const permesso = matrice?.permessi?.[ruolo]?.[sezione];
    return {
      can_view: permesso?.can_view ?? false,
      can_edit: permesso?.can_edit ?? false
    };
  };

  const getPermessoValue = (ruolo, sezione, field) => {
    return getChangeOrCurrent(ruolo, sezione)[field];
  };

  // Verifica se ci sono modifiche non salvate
  const hasChanges = Object.keys(changes).length > 0;

  // Salva modifiche
  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      // Raggruppa modifiche per ruolo
      const changesByRuolo = {};
      for (const [key, value] of Object.entries(changes)) {
        const [ruolo, sezione] = key.split(':');
        if (!changesByRuolo[ruolo]) changesByRuolo[ruolo] = {};
        changesByRuolo[ruolo][sezione] = value;
      }

      // Salva per ogni ruolo
      for (const [ruolo, permessi] of Object.entries(changesByRuolo)) {
        await permessiApi.updatePermessiRuoloBulk(ruolo, permessi);
      }

      // Ricarica matrice
      await loadMatrice();
      alert('Permessi salvati con successo!');
    } catch (err) {
      setError(err.response?.data?.detail || 'Errore salvataggio permessi');
    } finally {
      setSaving(false);
    }
  };

  // Annulla modifiche
  const handleCancel = () => {
    setChanges({});
  };

  if (loading) {
    return <Loading text="Caricamento matrice permessi..." />;
  }

  if (error && !matrice) {
    return (
      <div className="p-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
          {error}
        </div>
      </div>
    );
  }

  const sezioni = matrice?.sezioni || [];
  const ruoli = matrice?.ruoli?.filter(r => r !== 'admin') || []; // Admin escluso dalla modifica

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-800">Matrice Permessi</h2>
          <p className="text-sm text-slate-500">
            Gestisci i permessi di accesso per ogni ruolo. I permessi Admin non sono modificabili.
          </p>
        </div>
        {hasChanges && (
          <div className="flex gap-2">
            <Button variant="secondary" onClick={handleCancel} disabled={saving}>
              Annulla
            </Button>
            <Button variant="primary" onClick={handleSave} disabled={saving}>
              {saving ? 'Salvataggio...' : 'Salva Modifiche'}
            </Button>
          </div>
        )}
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-red-700 text-sm">
          {error}
        </div>
      )}

      {/* Legenda */}
      <div className="flex flex-wrap gap-4 p-4 bg-slate-50 rounded-lg">
        <div className="text-sm text-slate-600 font-medium">Ruoli:</div>
        {Object.entries(RUOLI_DISPLAY).map(([ruolo, info]) => (
          <div key={ruolo} className="flex items-center gap-2">
            <span className={`px-2 py-0.5 rounded text-xs font-medium ${info.color}`}>
              {info.label}
            </span>
            <span className="text-xs text-slate-500">{info.description}</span>
          </div>
        ))}
      </div>

      {/* Tabella Matrice */}
      <div className="overflow-x-auto border border-slate-200 rounded-lg">
        <table className="w-full text-sm">
          <thead className="bg-slate-100">
            <tr>
              <th className="p-3 text-left font-semibold text-slate-700 border-b border-slate-200 min-w-[180px]">
                Sezione
              </th>
              {/* Admin colonna (readonly) */}
              <th className="p-3 text-center font-semibold text-slate-700 border-b border-slate-200 min-w-[100px]">
                <span className={`px-2 py-0.5 rounded text-xs font-medium ${RUOLI_DISPLAY.admin.color}`}>
                  Admin
                </span>
                <div className="text-xs font-normal text-slate-400 mt-1">Fisso</div>
              </th>
              {/* Altri ruoli (editabili) */}
              {ruoli.map(ruolo => (
                <th key={ruolo} className="p-3 text-center font-semibold text-slate-700 border-b border-slate-200 min-w-[100px]">
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${RUOLI_DISPLAY[ruolo]?.color || 'bg-slate-100'}`}>
                    {RUOLI_DISPLAY[ruolo]?.label || ruolo}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sezioni.map((sezione, idx) => (
              <tr key={sezione.codice_sezione} className={idx % 2 === 0 ? 'bg-white' : 'bg-slate-50'}>
                {/* Nome Sezione */}
                <td className="p-3 border-b border-slate-100">
                  <div className="font-medium text-slate-800">{sezione.nome_display}</div>
                  <div className="text-xs text-slate-500">{sezione.descrizione}</div>
                </td>

                {/* Admin (sempre OK, readonly) */}
                <td className="p-3 border-b border-slate-100 text-center">
                  <div className="flex flex-col items-center gap-1">
                    <span className="text-green-600 font-bold">OK</span>
                    <span className="text-xs text-slate-400">View + Edit</span>
                  </div>
                </td>

                {/* Altri ruoli (editabili) */}
                {ruoli.map(ruolo => {
                  const canView = getPermessoValue(ruolo, sezione.codice_sezione, 'can_view');
                  const canEdit = getPermessoValue(ruolo, sezione.codice_sezione, 'can_edit');
                  const isChanged = changes[`${ruolo}:${sezione.codice_sezione}`];

                  return (
                    <td
                      key={ruolo}
                      className={`p-3 border-b border-slate-100 text-center ${isChanged ? 'bg-yellow-50' : ''}`}
                    >
                      <div className="flex flex-col items-center gap-2">
                        {/* Checkbox View */}
                        <label className="flex items-center gap-1.5 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={canView}
                            onChange={() => handleToggle(ruolo, sezione.codice_sezione, 'can_view')}
                            className="w-4 h-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                          />
                          <span className={`text-xs ${canView ? 'text-green-600 font-medium' : 'text-slate-400'}`}>
                            View
                          </span>
                        </label>

                        {/* Checkbox Edit */}
                        <label className="flex items-center gap-1.5 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={canEdit}
                            onChange={() => handleToggle(ruolo, sezione.codice_sezione, 'can_edit')}
                            disabled={!canView}
                            className="w-4 h-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500 disabled:opacity-50"
                          />
                          <span className={`text-xs ${canEdit ? 'text-green-600 font-medium' : 'text-slate-400'}`}>
                            Edit
                          </span>
                        </label>

                        {/* Status badge */}
                        {!canView && (
                          <span className="text-xs text-red-500 font-medium">Nascosto</span>
                        )}
                      </div>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Note */}
      <div className="p-4 bg-blue-50 rounded-lg text-sm text-blue-700">
        <strong>Note:</strong>
        <ul className="list-disc ml-5 mt-1 space-y-1">
          <li><strong>View</strong>: L'utente può visualizzare la sezione nel menu e accedervi</li>
          <li><strong>Edit</strong>: L'utente può modificare i dati nella sezione (richiede View)</li>
          <li><strong>Nascosto</strong>: La sezione non appare nel menu per quel ruolo</li>
          <li>Le modifiche hanno effetto immediato dopo il salvataggio (richiede refresh/re-login)</li>
        </ul>
      </div>
    </div>
  );
}
