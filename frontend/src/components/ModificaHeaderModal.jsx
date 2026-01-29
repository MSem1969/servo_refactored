/**
 * ModificaHeaderModal - v11.3
 * Modal per modifica manuale header ordine
 *
 * PRIORITÀ MASSIMA: la modifica manuale sovrascrive:
 * - Dati estratti dal PDF
 * - Lookup automatico
 * - Anagrafica ministeriale
 */
import React, { useState, useEffect } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { ordiniApi, getApiBaseUrl } from '../api';
import Modal from './Modal';

// Opzioni deposito disponibili
const DEPOSITI_OPTIONS = [
  { value: '', label: '-- Seleziona deposito --' },
  { value: 'CT', label: 'CT - Catania (SOFAD)' },
  { value: 'CL', label: 'CL - Caltanissetta (SOFAD)' },
  { value: 'PE', label: 'PE - Pescara (SAFAR)' },
  { value: 'CB', label: 'CB - Campobasso (SAFAR)' },
  { value: '001', label: '001 - Deposito Default (FARVI)' },
];

export default function ModificaHeaderModal({ ordine, isOpen, onClose, onSuccess, currentUser }) {
  const queryClient = useQueryClient();

  const [formData, setFormData] = useState({
    partita_iva: '',
    min_id: '',
    ragione_sociale: '',
    deposito_riferimento: '',
    indirizzo: '',
    cap: '',
    localita: '',
    provincia: '',
    note: ''
  });

  const [errors, setErrors] = useState({});

  // Popola form con dati ordine
  useEffect(() => {
    if (ordine && isOpen) {
      setFormData({
        partita_iva: ordine.partita_iva || ordine.partita_iva_estratta || '',
        min_id: ordine.min_id || '',
        ragione_sociale: ordine.ragione_sociale || ordine.ragione_sociale_1 || '',
        deposito_riferimento: ordine.deposito || ordine.deposito_riferimento || '',
        indirizzo: ordine.indirizzo || '',
        cap: ordine.cap || '',
        localita: ordine.localita || ordine.citta || '',
        provincia: ordine.provincia || '',
        note: ''
      });
      setErrors({});
    }
  }, [ordine, isOpen]);

  // Mutation per salvare
  const mutation = useMutation({
    mutationFn: (data) => ordiniApi.modificaHeader(ordine.id_testata, data),
    onSuccess: (response) => {
      // Invalida cache ordini
      queryClient.invalidateQueries(['ordine', ordine.id_testata]);
      queryClient.invalidateQueries(['ordini']);
      queryClient.invalidateQueries(['anomalie']);

      if (onSuccess) onSuccess(response);
      onClose();
    },
    onError: (error) => {
      setErrors({
        submit: error.response?.data?.detail || error.message || 'Errore nel salvataggio'
      });
    }
  });

  // Validazione
  const validate = () => {
    const newErrors = {};

    // P.IVA: 11 o 16 caratteri (se fornita)
    if (formData.partita_iva) {
      const piva = formData.partita_iva.replace(/\s/g, '');
      if (piva.length !== 11 && piva.length !== 16) {
        newErrors.partita_iva = 'P.IVA deve essere 11 cifre (o 16 per codice fiscale)';
      }
    }

    // CAP: 5 cifre (se fornito)
    if (formData.cap && !/^\d{5}$/.test(formData.cap)) {
      newErrors.cap = 'CAP deve essere 5 cifre';
    }

    // Provincia: 2 lettere (se fornita)
    if (formData.provincia && !/^[A-Za-z]{2}$/.test(formData.provincia)) {
      newErrors.provincia = 'Provincia deve essere 2 lettere';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e) => {
    e.preventDefault();

    if (!validate()) return;

    // Prepara payload: invia solo campi modificati rispetto a originale
    const payload = {
      operatore: currentUser?.username || currentUser || 'admin'
    };

    // Confronta con valori originali e includi solo modifiche
    const originalValues = {
      partita_iva: ordine.partita_iva || ordine.partita_iva_estratta || '',
      min_id: ordine.min_id || '',
      ragione_sociale: ordine.ragione_sociale || ordine.ragione_sociale_1 || '',
      deposito_riferimento: ordine.deposito || ordine.deposito_riferimento || '',
      indirizzo: ordine.indirizzo || '',
      cap: ordine.cap || '',
      localita: ordine.localita || ordine.citta || '',
      provincia: ordine.provincia || '',
    };

    let hasChanges = false;

    Object.entries(formData).forEach(([key, value]) => {
      if (key === 'note') return; // Note sempre incluse se presenti

      const trimmedValue = typeof value === 'string' ? value.trim() : value;
      const originalValue = originalValues[key] || '';

      if (trimmedValue && trimmedValue !== originalValue) {
        payload[key] = trimmedValue;
        hasChanges = true;
      }
    });

    // Aggiungi note se presenti
    if (formData.note?.trim()) {
      payload.note = formData.note.trim();
    }

    if (!hasChanges) {
      setErrors({ submit: 'Nessuna modifica rilevata' });
      return;
    }

    mutation.mutate(payload);
  };

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    // Rimuovi errore quando l'utente modifica
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: null }));
    }
  };

  if (!isOpen) return null;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Modifica Header - Ordine #${ordine?.id_testata}`}
      size="lg"
      footer={
        <>
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors"
            disabled={mutation.isPending}
          >
            Annulla
          </button>
          <button
            onClick={handleSubmit}
            disabled={mutation.isPending}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
          >
            {mutation.isPending ? 'Salvataggio...' : 'Salva Modifiche'}
          </button>
        </>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* v11.4: Bottone Visualizza PDF */}
        {ordine?.pdf_file && (
          <div className="flex justify-end">
            <a
              href={`${getApiBaseUrl()}/api/v1/upload/pdf/${encodeURIComponent(ordine.pdf_file)}`}
              target="_blank"
              rel="noopener noreferrer"
              className="px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm flex items-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
              </svg>
              Visualizza PDF
            </a>
          </div>
        )}

        {/* Avviso priorità */}
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
          <div className="flex gap-2">
            <svg className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <div className="text-sm text-amber-800">
              <strong>Priorità massima:</strong> La modifica manuale sovrascrive i dati estratti dal PDF
              e il lookup automatico. Verifica accuratamente i dati prima di salvare.
            </div>
          </div>
        </div>

        {/* Errore submit */}
        {errors.submit && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-red-700 text-sm">
            {errors.submit}
          </div>
        )}

        {/* Sezione Farmacia */}
        <fieldset className="border border-slate-200 rounded-lg p-4">
          <legend className="text-sm font-semibold text-slate-700 px-2">Dati Farmacia</legend>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Partita IVA
              </label>
              <input
                type="text"
                value={formData.partita_iva}
                onChange={(e) => handleChange('partita_iva', e.target.value)}
                className={`w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
                  errors.partita_iva ? 'border-red-300' : 'border-slate-300'
                }`}
                maxLength={16}
                placeholder="11 o 16 cifre"
              />
              {errors.partita_iva && (
                <p className="text-red-500 text-xs mt-1">{errors.partita_iva}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                MIN_ID (Cod. Ministeriale)
              </label>
              <input
                type="text"
                value={formData.min_id}
                onChange={(e) => handleChange('min_id', e.target.value)}
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="Codice ministeriale farmacia"
              />
            </div>
          </div>

          <div className="mt-4">
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Ragione Sociale
            </label>
            <input
              type="text"
              value={formData.ragione_sociale}
              onChange={(e) => handleChange('ragione_sociale', e.target.value)}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Nome farmacia"
            />
          </div>

          <div className="mt-4">
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Deposito di Riferimento
            </label>
            <select
              value={formData.deposito_riferimento}
              onChange={(e) => handleChange('deposito_riferimento', e.target.value)}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              {DEPOSITI_OPTIONS.map(opt => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>
        </fieldset>

        {/* Sezione Indirizzo */}
        <fieldset className="border border-slate-200 rounded-lg p-4">
          <legend className="text-sm font-semibold text-slate-700 px-2">Indirizzo (opzionale)</legend>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Indirizzo
              </label>
              <input
                type="text"
                value={formData.indirizzo}
                onChange={(e) => handleChange('indirizzo', e.target.value)}
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="Via/Piazza..."
              />
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  CAP
                </label>
                <input
                  type="text"
                  value={formData.cap}
                  onChange={(e) => handleChange('cap', e.target.value)}
                  className={`w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
                    errors.cap ? 'border-red-300' : 'border-slate-300'
                  }`}
                  maxLength={5}
                  placeholder="00000"
                />
                {errors.cap && (
                  <p className="text-red-500 text-xs mt-1">{errors.cap}</p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Località
                </label>
                <input
                  type="text"
                  value={formData.localita}
                  onChange={(e) => handleChange('localita', e.target.value)}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Città"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Provincia
                </label>
                <input
                  type="text"
                  value={formData.provincia}
                  onChange={(e) => handleChange('provincia', e.target.value.toUpperCase())}
                  className={`w-full border rounded-lg px-3 py-2 text-sm uppercase focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
                    errors.provincia ? 'border-red-300' : 'border-slate-300'
                  }`}
                  maxLength={2}
                  placeholder="XX"
                />
                {errors.provincia && (
                  <p className="text-red-500 text-xs mt-1">{errors.provincia}</p>
                )}
              </div>
            </div>
          </div>
        </fieldset>

        {/* Note */}
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            Note sulla modifica
          </label>
          <textarea
            value={formData.note}
            onChange={(e) => handleChange('note', e.target.value)}
            className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            rows={2}
            placeholder="Motivazione della modifica manuale (opzionale)..."
          />
        </div>

        {/* Info lookup attuale */}
        {ordine && (
          <div className="bg-slate-50 rounded-lg p-3 text-sm text-slate-600">
            <div className="grid grid-cols-2 gap-2">
              <div>
                <span className="font-medium">Lookup attuale:</span>{' '}
                {ordine.lookup_method || 'N/D'}
              </div>
              <div>
                <span className="font-medium">Score:</span>{' '}
                {ordine.lookup_score ?? 'N/D'}%
              </div>
            </div>
            <p className="mt-2 text-xs text-slate-500">
              Dopo il salvataggio: lookup_method = MANUALE, lookup_score = 100
            </p>
          </div>
        )}
      </form>
    </Modal>
  );
}
