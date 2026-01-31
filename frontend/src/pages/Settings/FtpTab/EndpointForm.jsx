// =============================================================================
// FTP ENDPOINT FORM MODAL
// =============================================================================

import React, { useState } from 'react';
import { Button } from '../../../common';

export default function EndpointForm({ endpoint, vendors, depositi, onSave, onCancel }) {
  const isEdit = !!endpoint?.id;

  const [form, setForm] = useState({
    nome: endpoint?.nome || '',
    descrizione: endpoint?.descrizione || '',
    vendor_code: endpoint?.vendor_code || '',
    deposito: endpoint?.deposito || '',
    ftp_host: endpoint?.ftp_host || '',
    ftp_port: endpoint?.ftp_port || 21,
    ftp_path: endpoint?.ftp_path || './',
    ftp_username: endpoint?.ftp_username || '',
    ftp_password: '',  // Mai precompilato per sicurezza
    ftp_passive_mode: endpoint?.ftp_passive_mode || false,
    ftp_timeout: endpoint?.ftp_timeout || 30,
    max_tentativi: endpoint?.max_tentativi || 3,
    intervallo_retry_sec: endpoint?.intervallo_retry_sec || 60,
    attivo: endpoint?.attivo ?? true,
    ordine: endpoint?.ordine || 0
  });

  const [errors, setErrors] = useState({});
  const [saving, setSaving] = useState(false);

  // Validazione
  const validate = () => {
    const errs = {};

    if (!form.nome.trim()) errs.nome = 'Nome obbligatorio';
    if (!form.vendor_code) errs.vendor_code = 'Seleziona un vendor';
    if (!form.ftp_host.trim()) errs.ftp_host = 'Host obbligatorio';
    if (!form.ftp_path.trim()) errs.ftp_path = 'Path obbligatorio';
    if (!form.ftp_username.trim()) errs.ftp_username = 'Username obbligatorio';
    if (!isEdit && !form.ftp_password.trim()) errs.ftp_password = 'Password obbligatoria';
    if (form.ftp_port < 1 || form.ftp_port > 65535) errs.ftp_port = 'Porta non valida';
    if (form.ftp_timeout < 5 || form.ftp_timeout > 300) errs.ftp_timeout = 'Timeout: 5-300 secondi';
    if (form.max_tentativi < 1 || form.max_tentativi > 10) errs.max_tentativi = 'Tentativi: 1-10';

    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  // Submit
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) return;

    setSaving(true);
    try {
      // Prepara dati - rimuovi password vuota in modifica
      const data = { ...form };
      if (!data.deposito) data.deposito = null;
      if (isEdit && !data.ftp_password) delete data.ftp_password;

      await onSave(data);
    } catch (err) {
      // Errore gestito dal parent
    } finally {
      setSaving(false);
    }
  };

  const handleChange = (field, value) => {
    setForm(prev => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: null }));
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 overflow-y-auto">
      <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full mx-4 my-8">
        {/* Header */}
        <div className="p-6 border-b border-slate-200">
          <h3 className="font-semibold text-slate-800 text-lg">
            {isEdit ? 'Modifica Endpoint FTP' : 'Nuovo Endpoint FTP'}
          </h3>
          <p className="text-sm text-slate-500">
            {isEdit ? `Modifica configurazione per ${endpoint.nome}` : 'Configura un nuovo endpoint per l\'invio tracciati'}
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit}>
          <div className="p-6 space-y-6 max-h-[60vh] overflow-y-auto">
            {/* Identificazione */}
            <div>
              <h4 className="text-sm font-medium text-slate-700 mb-3">Identificazione</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-slate-600 mb-1">Nome *</label>
                  <input
                    type="text"
                    value={form.nome}
                    onChange={(e) => handleChange('nome', e.target.value)}
                    className={`w-full px-3 py-2 border rounded-lg text-sm ${errors.nome ? 'border-red-300 bg-red-50' : 'border-slate-300'}`}
                    placeholder="Es: SOFAD Catania - Angelini"
                  />
                  {errors.nome && <p className="text-xs text-red-600 mt-1">{errors.nome}</p>}
                </div>
                <div>
                  <label className="block text-sm text-slate-600 mb-1">Descrizione</label>
                  <input
                    type="text"
                    value={form.descrizione}
                    onChange={(e) => handleChange('descrizione', e.target.value)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                    placeholder="Descrizione opzionale"
                  />
                </div>
              </div>
            </div>

            {/* Mapping */}
            <div>
              <h4 className="text-sm font-medium text-slate-700 mb-3">Mapping Vendor/Deposito</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-slate-600 mb-1">Vendor *</label>
                  <select
                    value={form.vendor_code}
                    onChange={(e) => handleChange('vendor_code', e.target.value)}
                    disabled={isEdit}
                    className={`w-full px-3 py-2 border rounded-lg text-sm ${errors.vendor_code ? 'border-red-300 bg-red-50' : 'border-slate-300'} ${isEdit ? 'bg-slate-100' : ''}`}
                  >
                    <option value="">Seleziona vendor...</option>
                    {vendors.map(v => (
                      <option key={v} value={v}>{v}</option>
                    ))}
                  </select>
                  {errors.vendor_code && <p className="text-xs text-red-600 mt-1">{errors.vendor_code}</p>}
                  {isEdit && <p className="text-xs text-slate-500 mt-1">Non modificabile</p>}
                </div>
                <div>
                  <label className="block text-sm text-slate-600 mb-1">Deposito</label>
                  <select
                    value={form.deposito}
                    onChange={(e) => handleChange('deposito', e.target.value)}
                    disabled={isEdit}
                    className={`w-full px-3 py-2 border border-slate-300 rounded-lg text-sm ${isEdit ? 'bg-slate-100' : ''}`}
                  >
                    <option value="">Tutti i depositi</option>
                    {depositi.map(d => (
                      <option key={d} value={d}>{d}</option>
                    ))}
                  </select>
                  {isEdit && <p className="text-xs text-slate-500 mt-1">Non modificabile</p>}
                </div>
              </div>
            </div>

            {/* Connessione FTP */}
            <div>
              <h4 className="text-sm font-medium text-slate-700 mb-3">Connessione FTP</h4>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="md:col-span-2">
                  <label className="block text-sm text-slate-600 mb-1">Host *</label>
                  <input
                    type="text"
                    value={form.ftp_host}
                    onChange={(e) => handleChange('ftp_host', e.target.value)}
                    className={`w-full px-3 py-2 border rounded-lg text-sm font-mono ${errors.ftp_host ? 'border-red-300 bg-red-50' : 'border-slate-300'}`}
                    placeholder="Es: 85.39.189.15"
                  />
                  {errors.ftp_host && <p className="text-xs text-red-600 mt-1">{errors.ftp_host}</p>}
                </div>
                <div>
                  <label className="block text-sm text-slate-600 mb-1">Porta</label>
                  <input
                    type="number"
                    value={form.ftp_port}
                    onChange={(e) => handleChange('ftp_port', parseInt(e.target.value) || 21)}
                    className={`w-full px-3 py-2 border rounded-lg text-sm font-mono ${errors.ftp_port ? 'border-red-300 bg-red-50' : 'border-slate-300'}`}
                  />
                  {errors.ftp_port && <p className="text-xs text-red-600 mt-1">{errors.ftp_port}</p>}
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
                <div>
                  <label className="block text-sm text-slate-600 mb-1">Username *</label>
                  <input
                    type="text"
                    value={form.ftp_username}
                    onChange={(e) => handleChange('ftp_username', e.target.value)}
                    className={`w-full px-3 py-2 border rounded-lg text-sm font-mono ${errors.ftp_username ? 'border-red-300 bg-red-50' : 'border-slate-300'}`}
                    placeholder="Es: sofadto"
                  />
                  {errors.ftp_username && <p className="text-xs text-red-600 mt-1">{errors.ftp_username}</p>}
                </div>
                <div>
                  <label className="block text-sm text-slate-600 mb-1">
                    Password {isEdit ? '(lascia vuoto per mantenere)' : '*'}
                  </label>
                  <input
                    type="password"
                    value={form.ftp_password}
                    onChange={(e) => handleChange('ftp_password', e.target.value)}
                    className={`w-full px-3 py-2 border rounded-lg text-sm ${errors.ftp_password ? 'border-red-300 bg-red-50' : 'border-slate-300'}`}
                    placeholder={isEdit ? 'Lascia vuoto per mantenere' : 'Password FTP'}
                  />
                  {errors.ftp_password && <p className="text-xs text-red-600 mt-1">{errors.ftp_password}</p>}
                </div>
              </div>

              <div className="mt-4">
                <label className="block text-sm text-slate-600 mb-1">Path remoto *</label>
                <input
                  type="text"
                  value={form.ftp_path}
                  onChange={(e) => handleChange('ftp_path', e.target.value)}
                  className={`w-full px-3 py-2 border rounded-lg text-sm font-mono ${errors.ftp_path ? 'border-red-300 bg-red-50' : 'border-slate-300'}`}
                  placeholder="Es: ./ANGELINI"
                />
                {errors.ftp_path && <p className="text-xs text-red-600 mt-1">{errors.ftp_path}</p>}
              </div>
            </div>

            {/* Opzioni avanzate */}
            <div>
              <h4 className="text-sm font-medium text-slate-700 mb-3">Opzioni Avanzate</h4>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm text-slate-600 mb-1">Timeout (sec)</label>
                  <input
                    type="number"
                    value={form.ftp_timeout}
                    onChange={(e) => handleChange('ftp_timeout', parseInt(e.target.value) || 30)}
                    className={`w-full px-3 py-2 border rounded-lg text-sm ${errors.ftp_timeout ? 'border-red-300 bg-red-50' : 'border-slate-300'}`}
                    min={5}
                    max={300}
                  />
                </div>
                <div>
                  <label className="block text-sm text-slate-600 mb-1">Max tentativi</label>
                  <input
                    type="number"
                    value={form.max_tentativi}
                    onChange={(e) => handleChange('max_tentativi', parseInt(e.target.value) || 3)}
                    className={`w-full px-3 py-2 border rounded-lg text-sm ${errors.max_tentativi ? 'border-red-300 bg-red-50' : 'border-slate-300'}`}
                    min={1}
                    max={10}
                  />
                </div>
                <div>
                  <label className="block text-sm text-slate-600 mb-1">Retry (sec)</label>
                  <input
                    type="number"
                    value={form.intervallo_retry_sec}
                    onChange={(e) => handleChange('intervallo_retry_sec', parseInt(e.target.value) || 60)}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                    min={10}
                    max={600}
                  />
                </div>
              </div>

              <div className="flex items-center gap-4 mt-4">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={form.ftp_passive_mode}
                    onChange={(e) => handleChange('ftp_passive_mode', e.target.checked)}
                    className="w-4 h-4 rounded border-slate-300 text-blue-600"
                  />
                  <span className="text-sm text-slate-700">Modalita passiva (PASV)</span>
                </label>

                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={form.attivo}
                    onChange={(e) => handleChange('attivo', e.target.checked)}
                    className="w-4 h-4 rounded border-slate-300 text-blue-600"
                  />
                  <span className="text-sm text-slate-700">Endpoint attivo</span>
                </label>
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="p-4 bg-slate-50 border-t border-slate-200 flex justify-end gap-3">
            <Button variant="secondary" type="button" onClick={onCancel} disabled={saving}>
              Annulla
            </Button>
            <Button variant="primary" type="submit" disabled={saving} loading={saving}>
              {isEdit ? 'Salva Modifiche' : 'Crea Endpoint'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
