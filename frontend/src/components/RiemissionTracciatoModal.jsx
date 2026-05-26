/**
 * RiemissionTracciatoModal
 *
 * Edit raw TO_T/TO_D di un'esportazione tracciato (riemissione manuale
 * dopo scarto ERP). Solo admin.
 *
 * Flusso:
 *  1. Carica testo dei file via GET /tracciati/{id}/raw
 *  2. L'operatore modifica le textarea
 *  3. POST /tracciati/{id}/riemetti: crea nuova esportazione con numero
 *     ordine suffissato e marca l'originale SUPERSEDED
 *  4. Opzionalmente ritrasmette subito via FTP (POST /ritrasmetti)
 */

import React, { useEffect, useState, useCallback } from 'react';
import { Modal } from './Modal';
import { Button } from '../common';
import { tracciatiApi } from '../api';

const TO_T_EXPECTED_LEN = 869;

function lineLengths(text) {
  if (!text) return [];
  return text.replace(/\r\n/g, '\n').split('\n').map(l => l.length);
}

function RowMetrics({ label, text, expectedLen }) {
  const lens = lineLengths(text);
  const nonEmpty = lens.filter(l => l > 0);
  const ok = nonEmpty.length > 0 && nonEmpty.every(l => l === expectedLen);
  const min = nonEmpty.length ? Math.min(...nonEmpty) : 0;
  const max = nonEmpty.length ? Math.max(...nonEmpty) : 0;
  return (
    <div className="text-xs text-slate-600 flex items-center gap-3">
      <span className="font-medium">{label}:</span>
      <span>{nonEmpty.length} riga/he</span>
      <span>
        len {min}{min !== max ? `–${max}` : ''}
        {expectedLen && (
          <span className={ok ? 'text-emerald-600 ml-1' : 'text-amber-600 ml-1'}>
            (attesa {expectedLen})
          </span>
        )}
      </span>
    </div>
  );
}

export function RiemissionTracciatoModal({ isOpen, onClose, idEsportazione, onSuccess }) {
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [meta, setMeta] = useState(null);
  const [toT, setToT] = useState('');
  const [toD, setToD] = useState('');
  const [note, setNote] = useState('');
  const [error, setError] = useState(null);
  const [createdId, setCreatedId] = useState(null);

  const load = useCallback(async () => {
    if (!idEsportazione) return;
    setLoading(true);
    setError(null);
    setCreatedId(null);
    try {
      const res = await tracciatiApi.getRaw(idEsportazione);
      const d = res.data || {};
      setMeta(d);
      setToT(d.to_t || '');
      setToD(d.to_d || '');
      setNote('');
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Errore caricamento');
    } finally {
      setLoading(false);
    }
  }, [idEsportazione]);

  useEffect(() => {
    if (isOpen) load();
  }, [isOpen, load]);

  const handleRiemetti = async () => {
    if (!toT || !toD) {
      setError('TO_T e TO_D non possono essere vuoti');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const res = await tracciatiApi.riemetti(idEsportazione, {
        to_t_content: toT,
        to_d_content: toD,
        note: note || null,
      });
      const newId = res.data?.id_esportazione_riemessa;
      setCreatedId(newId);
      onSuccess?.(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Errore riemissione');
    } finally {
      setSaving(false);
    }
  };

  const handleRitrasmetti = async () => {
    const target = createdId || idEsportazione;
    setSaving(true);
    setError(null);
    try {
      const res = await tracciatiApi.ritrasmetti(target);
      const sent = res.data?.ftp_result?.success;
      if (sent) {
        alert('Tracciato ritrasmesso con successo via FTP.');
        onClose?.();
      } else {
        const msg = res.data?.ftp_result?.message || res.data?.ftp_result?.error || 'esito non determinato';
        setError(`Invio FTP non confermato: ${msg}`);
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Errore ritrasmissione');
    } finally {
      setSaving(false);
    }
  };

  const footer = createdId ? (
    <>
      <Button variant="secondary" onClick={onClose} disabled={saving}>Chiudi</Button>
      <Button variant="primary" onClick={handleRitrasmetti} disabled={saving}>
        {saving ? 'Invio in corso…' : '📤 Ritrasmetti via FTP'}
      </Button>
    </>
  ) : (
    <>
      <Button variant="secondary" onClick={onClose} disabled={saving}>Annulla</Button>
      <Button variant="primary" onClick={handleRiemetti} disabled={saving || loading}>
        {saving ? 'Creazione…' : '💾 Crea riemissione'}
      </Button>
    </>
  );

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Edit tracciato — esportazione #${idEsportazione}`}
      size="xl"
      footer={footer}
      closeOnOverlay={false}
    >
      {loading ? (
        <div className="p-4 text-slate-500">Caricamento…</div>
      ) : (
        <div className="space-y-4">
          {/* Metadati */}
          {meta && (
            <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 text-sm">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                <div>
                  <span className="text-slate-500">Numero ordine attuale:</span>{' '}
                  <span className="font-mono font-medium">{meta.numero_ordine_db || '-'}</span>
                </div>
                <div>
                  <span className="text-slate-500">Nuovo numero (riemissione):</span>{' '}
                  <span className="font-mono font-medium text-emerald-700">{meta.nuovo_numero_atteso || '-'}</span>
                </div>
                <div>
                  <span className="text-slate-500">Stato FTP attuale:</span>{' '}
                  <span className="font-medium">{meta.stato_ftp || '-'}</span>
                </div>
                {meta.is_riemissione && (
                  <div className="text-amber-700">⚠️ Questa è già una riemissione di #{meta.riemessa_da_id}</div>
                )}
              </div>
            </div>
          )}

          {/* Banner conferma post-creazione */}
          {createdId && (
            <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3 text-sm text-emerald-800">
              ✅ Riemissione creata (nuova esportazione #{createdId}). Originale marcata SUPERSEDED.
              Premi "Ritrasmetti via FTP" per inviarla.
            </div>
          )}

          {/* Errore */}
          {error && (
            <div className="bg-rose-50 border border-rose-200 rounded-lg p-3 text-sm text-rose-700">
              {error}
            </div>
          )}

          {/* TO_T */}
          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="text-sm font-medium text-slate-700">TO_T (testata)</label>
              <RowMetrics label="" text={toT} expectedLen={TO_T_EXPECTED_LEN} />
            </div>
            <textarea
              value={toT}
              onChange={(e) => setToT(e.target.value)}
              spellCheck={false}
              wrap="off"
              disabled={!!createdId || saving}
              className="w-full h-32 font-mono text-xs p-2 border border-slate-300 rounded-lg whitespace-pre overflow-auto"
              style={{ tabSize: 1 }}
            />
          </div>

          {/* TO_D */}
          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="text-sm font-medium text-slate-700">TO_D (dettaglio)</label>
              <RowMetrics label="" text={toD} />
            </div>
            <textarea
              value={toD}
              onChange={(e) => setToD(e.target.value)}
              spellCheck={false}
              wrap="off"
              disabled={!!createdId || saving}
              className="w-full h-56 font-mono text-xs p-2 border border-slate-300 rounded-lg whitespace-pre overflow-auto"
              style={{ tabSize: 1 }}
            />
          </div>

          {/* Note */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Motivo correzione (opzionale)
            </label>
            <input
              type="text"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              disabled={!!createdId || saving}
              placeholder="Es: corretto MIN_ID, fix prezzo riga 5…"
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
            />
          </div>

          <div className="text-xs text-slate-500">
            Il numero ordine viene sostituito automaticamente alla posizione 11-40 (TO_T)
            e 1-30 (TO_D, ogni riga). Non modificare manualmente quei caratteri.
          </div>
        </div>
      )}
    </Modal>
  );
}

export default RiemissionTracciatoModal;
