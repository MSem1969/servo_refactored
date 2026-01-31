// =============================================================================
// SERV.O v11.6 - FTP ENDPOINTS TAB
// =============================================================================
// Gestione configurazione endpoint FTP con 2FA
// Requisito NIS-2 compliance
// =============================================================================

import React, { useState, useEffect, useCallback } from 'react';
import { ftpApi } from '../../../api';
import { Button, Loading } from '../../../common';
import OtpModal from './OtpModal';
import EndpointForm from './EndpointForm';
import FtpLogConsole from './FtpLogConsole';

const DEPOSITI_DISPLAY = {
  CT: { label: 'Catania', color: 'bg-blue-100 text-blue-800' },
  CL: { label: 'Caltanissetta', color: 'bg-purple-100 text-purple-800' },
  null: { label: 'Tutti', color: 'bg-slate-100 text-slate-600' },
};

export default function FtpTab() {
  // State
  const [endpoints, setEndpoints] = useState([]);
  const [vendors, setVendors] = useState([]);
  const [depositi, setDepositi] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Modals
  const [showForm, setShowForm] = useState(false);
  const [editingEndpoint, setEditingEndpoint] = useState(null);
  const [showOtpModal, setShowOtpModal] = useState(false);
  const [otpOperation, setOtpOperation] = useState(null); // { type, endpointId, endpointName, callback }

  // Password view state
  const [visiblePasswords, setVisiblePasswords] = useState({}); // { endpointId: password }

  // Testing
  const [testingId, setTestingId] = useState(null);

  // Logs
  const [logs, setLogs] = useState([
    { type: 'info', text: 'Console FTP pronta', time: new Date().toLocaleTimeString('it-IT') }
  ]);

  // Helper per aggiungere log
  const addLog = useCallback((type, text) => {
    setLogs(prev => [...prev, {
      type,
      text,
      time: new Date().toLocaleTimeString('it-IT')
    }]);
  }, []);

  // Carica dati
  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [endpointsRes, vendorsRes, statsRes] = await Promise.all([
        ftpApi.getEndpoints(),
        ftpApi.getVendors(),
        ftpApi.getStats()
      ]);

      if (endpointsRes.success) setEndpoints(endpointsRes.data);
      if (vendorsRes.success) {
        setVendors(vendorsRes.data.vendors);
        setDepositi(vendorsRes.data.depositi);
      }
      if (statsRes.success) setStats(statsRes.data);

      addLog('ok', `Caricati ${endpointsRes.data?.length || 0} endpoint FTP`);
    } catch (err) {
      setError(err.response?.data?.detail || 'Errore caricamento dati');
      addLog('error', 'Errore caricamento endpoint');
    } finally {
      setLoading(false);
    }
  }, [addLog]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Toggle endpoint attivo
  const handleToggle = async (endpoint) => {
    try {
      const res = await ftpApi.toggleEndpoint(endpoint.id);
      if (res.success) {
        addLog(res.attivo ? 'ok' : 'warn', `Endpoint ${endpoint.nome} ${res.attivo ? 'attivato' : 'disattivato'}`);
        loadData();
      }
    } catch (err) {
      addLog('error', `Errore toggle: ${err.response?.data?.detail || err.message}`);
    }
  };

  // Test connessione
  const handleTest = async (endpoint) => {
    setTestingId(endpoint.id);
    addLog('info', `Test connessione ${endpoint.nome}...`);
    try {
      const res = await ftpApi.testConnection(endpoint.id);
      if (res.success) {
        addLog('ok', `Test OK: ${endpoint.nome} (${res.elapsed_seconds?.toFixed(2)}s)`);
        res.steps?.forEach(step => {
          addLog(step.success ? 'ok' : 'error', `  ${step.step}: ${step.message}`);
        });
      }
    } catch (err) {
      addLog('error', `Test FALLITO: ${err.response?.data?.detail || err.message}`);
    } finally {
      setTestingId(null);
    }
  };

  // Richiedi OTP per operazione
  const requestOtp = async (operation, endpointId, endpointName, callback) => {
    try {
      const res = await ftpApi.requestOtp(endpointId, operation);
      if (res.success) {
        addLog('info', `OTP inviato a ${res.email_masked} per ${endpointName}`);
        setOtpOperation({ type: operation, endpointId, endpointName, callback, scadenza: res.scadenza_secondi });
        setShowOtpModal(true);
      }
    } catch (err) {
      addLog('error', `Errore richiesta OTP: ${err.response?.data?.detail || err.message}`);
      alert('Errore: ' + (err.response?.data?.detail || err.message));
    }
  };

  // View password (richiede 2FA)
  const handleViewPassword = (endpoint) => {
    requestOtp('FTP_VIEW_PASSWORD', endpoint.id, endpoint.nome, async (otpCode) => {
      try {
        const res = await ftpApi.viewPassword(endpoint.id, otpCode);
        if (res.success) {
          setVisiblePasswords(prev => ({ ...prev, [endpoint.id]: res.password }));
          addLog('ok', `Password visualizzata per ${endpoint.nome}`);
          // Auto-nascondi dopo 30 secondi
          setTimeout(() => {
            setVisiblePasswords(prev => {
              const copy = { ...prev };
              delete copy[endpoint.id];
              return copy;
            });
          }, 30000);
        }
      } catch (err) {
        addLog('error', `Errore visualizzazione password: ${err.response?.data?.detail || err.message}`);
        throw err;
      }
    });
  };

  // Edit endpoint (richiede 2FA)
  const handleEdit = (endpoint) => {
    setEditingEndpoint(endpoint);
    requestOtp('FTP_EDIT', endpoint.id, endpoint.nome, async (otpCode) => {
      // OTP validato, mostra form di modifica
      setShowOtpModal(false);
      setShowForm(true);
      setEditingEndpoint({ ...endpoint, otpCode });
    });
  };

  // Delete endpoint (richiede 2FA)
  const handleDelete = (endpoint) => {
    if (!confirm(`Eliminare l'endpoint "${endpoint.nome}"?\nQuesta azione e irreversibile.`)) return;

    requestOtp('FTP_EDIT', endpoint.id, endpoint.nome, async (otpCode) => {
      try {
        const res = await ftpApi.deleteEndpoint(endpoint.id, otpCode);
        if (res.success) {
          addLog('warn', `Endpoint eliminato: ${endpoint.nome}`);
          loadData();
        }
      } catch (err) {
        addLog('error', `Errore eliminazione: ${err.response?.data?.detail || err.message}`);
        throw err;
      }
    });
  };

  // Salva endpoint (nuovo o modifica)
  const handleSaveEndpoint = async (data, otpCode = null) => {
    try {
      if (editingEndpoint?.id) {
        // Modifica
        const res = await ftpApi.updateEndpoint(editingEndpoint.id, data, otpCode || editingEndpoint.otpCode);
        if (res.success) {
          addLog('ok', `Endpoint aggiornato: ${data.nome}`);
        }
      } else {
        // Nuovo
        const res = await ftpApi.createEndpoint(data);
        if (res.success) {
          addLog('ok', `Nuovo endpoint creato: ${data.nome}`);
        }
      }
      setShowForm(false);
      setEditingEndpoint(null);
      loadData();
    } catch (err) {
      addLog('error', `Errore salvataggio: ${err.response?.data?.detail || err.message}`);
      alert('Errore: ' + (err.response?.data?.detail || err.message));
    }
  };

  // Verifica OTP
  const handleOtpVerify = async (code) => {
    if (!otpOperation?.callback) return;
    try {
      await otpOperation.callback(code);
      setShowOtpModal(false);
      setOtpOperation(null);
    } catch (err) {
      // Errore gia loggato nel callback
      throw err;
    }
  };

  if (loading) {
    return <Loading text="Caricamento configurazione FTP..." />;
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-800">Gestione Endpoint FTP</h2>
          <p className="text-sm text-slate-500">
            Configura gli endpoint FTP per l'invio automatico dei tracciati. Le password sono protette con 2FA.
          </p>
        </div>
        <Button variant="primary" onClick={() => { setEditingEndpoint(null); setShowForm(true); }}>
          + Nuovo Endpoint
        </Button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-red-700 text-sm">
          {error}
        </div>
      )}

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-white border border-slate-200 rounded-lg p-4">
            <div className="text-2xl font-bold text-slate-800">{stats.endpoints?.totale || 0}</div>
            <div className="text-sm text-slate-500">Endpoint totali</div>
          </div>
          <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-4">
            <div className="text-2xl font-bold text-emerald-600">{stats.endpoints?.attivi || 0}</div>
            <div className="text-sm text-emerald-700">Attivi</div>
          </div>
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
            <div className="text-2xl font-bold text-amber-600">{stats.endpoints?.disattivi || 0}</div>
            <div className="text-sm text-amber-700">Disattivi</div>
          </div>
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="text-2xl font-bold text-blue-600">{stats.log_24h?.successo || 0}</div>
            <div className="text-sm text-blue-700">Invii OK (24h)</div>
          </div>
        </div>
      )}

      {/* Endpoint Matrix */}
      <div className="overflow-x-auto border border-slate-200 rounded-lg">
        <table className="w-full text-sm">
          <thead className="bg-slate-100">
            <tr>
              <th className="p-3 text-left font-semibold text-slate-700 border-b border-slate-200 min-w-[200px]">
                Endpoint
              </th>
              <th className="p-3 text-center font-semibold text-slate-700 border-b border-slate-200">
                Vendor
              </th>
              <th className="p-3 text-center font-semibold text-slate-700 border-b border-slate-200">
                Deposito
              </th>
              <th className="p-3 text-center font-semibold text-slate-700 border-b border-slate-200">
                Host
              </th>
              <th className="p-3 text-center font-semibold text-slate-700 border-b border-slate-200">
                Path
              </th>
              <th className="p-3 text-center font-semibold text-slate-700 border-b border-slate-200">
                Stato
              </th>
              <th className="p-3 text-center font-semibold text-slate-700 border-b border-slate-200 min-w-[250px]">
                Azioni
              </th>
            </tr>
          </thead>
          <tbody>
            {endpoints.length === 0 ? (
              <tr>
                <td colSpan={7} className="p-8 text-center text-slate-500">
                  Nessun endpoint configurato. Clicca "Nuovo Endpoint" per iniziare.
                </td>
              </tr>
            ) : (
              endpoints.map((endpoint, idx) => {
                const depositoInfo = DEPOSITI_DISPLAY[endpoint.deposito] || DEPOSITI_DISPLAY[null];
                const isPasswordVisible = visiblePasswords[endpoint.id];

                return (
                  <tr key={endpoint.id} className={idx % 2 === 0 ? 'bg-white' : 'bg-slate-50'}>
                    {/* Nome */}
                    <td className="p-3 border-b border-slate-100">
                      <div className="font-medium text-slate-800">{endpoint.nome}</div>
                      {endpoint.descrizione && (
                        <div className="text-xs text-slate-500 truncate max-w-[200px]">{endpoint.descrizione}</div>
                      )}
                    </td>

                    {/* Vendor */}
                    <td className="p-3 border-b border-slate-100 text-center">
                      <span className="px-2 py-1 bg-indigo-100 text-indigo-800 text-xs font-medium rounded">
                        {endpoint.vendor_code}
                      </span>
                    </td>

                    {/* Deposito */}
                    <td className="p-3 border-b border-slate-100 text-center">
                      <span className={`px-2 py-1 text-xs font-medium rounded ${depositoInfo.color}`}>
                        {depositoInfo.label}
                      </span>
                    </td>

                    {/* Host */}
                    <td className="p-3 border-b border-slate-100 text-center">
                      <div className="font-mono text-xs text-slate-600">
                        {endpoint.ftp_host}:{endpoint.ftp_port}
                      </div>
                      <div className="text-xs text-slate-400">
                        {endpoint.ftp_username}
                      </div>
                    </td>

                    {/* Path */}
                    <td className="p-3 border-b border-slate-100 text-center">
                      <div className="font-mono text-xs text-slate-600">
                        {endpoint.ftp_path}
                      </div>
                    </td>

                    {/* Stato */}
                    <td className="p-3 border-b border-slate-100 text-center">
                      <button
                        onClick={() => handleToggle(endpoint)}
                        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                          endpoint.attivo ? 'bg-emerald-500' : 'bg-slate-300'
                        }`}
                      >
                        <span
                          className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                            endpoint.attivo ? 'translate-x-6' : 'translate-x-1'
                          }`}
                        />
                      </button>
                    </td>

                    {/* Azioni */}
                    <td className="p-3 border-b border-slate-100">
                      <div className="flex items-center justify-center gap-1">
                        {/* Test */}
                        <Button
                          variant="secondary"
                          size="xs"
                          onClick={() => handleTest(endpoint)}
                          disabled={testingId === endpoint.id}
                        >
                          {testingId === endpoint.id ? '...' : 'Test'}
                        </Button>

                        {/* View Password */}
                        <Button
                          variant="secondary"
                          size="xs"
                          onClick={() => isPasswordVisible ? null : handleViewPassword(endpoint)}
                          className={isPasswordVisible ? 'bg-amber-100' : ''}
                        >
                          {isPasswordVisible ? (
                            <span className="font-mono text-amber-700">{isPasswordVisible}</span>
                          ) : (
                            'Password'
                          )}
                        </Button>

                        {/* Edit */}
                        <Button
                          variant="secondary"
                          size="xs"
                          onClick={() => handleEdit(endpoint)}
                        >
                          Modifica
                        </Button>

                        {/* Delete */}
                        <Button
                          variant="danger"
                          size="xs"
                          onClick={() => handleDelete(endpoint)}
                        >
                          Elimina
                        </Button>
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Security Note */}
      <div className="p-4 bg-blue-50 rounded-lg text-sm text-blue-700">
        <strong>Sicurezza 2FA (NIS-2):</strong>
        <ul className="list-disc ml-5 mt-1 space-y-1">
          <li><strong>Visualizzazione password</strong>: Richiede verifica OTP via email</li>
          <li><strong>Modifica configurazione</strong>: Richiede verifica OTP via email</li>
          <li><strong>Eliminazione</strong>: Richiede verifica OTP via email</li>
          <li><strong>Creazione e Toggle</strong>: Non richiedono 2FA (operazioni reversibili)</li>
          <li>Le password sono criptate con AES-256 e mai trasmesse in chiaro</li>
        </ul>
      </div>

      {/* Log Console */}
      <FtpLogConsole logs={logs} onClear={() => setLogs([{
        type: 'info',
        text: 'Console pulita',
        time: new Date().toLocaleTimeString('it-IT')
      }])} />

      {/* OTP Modal */}
      {showOtpModal && otpOperation && (
        <OtpModal
          operation={otpOperation}
          onVerify={handleOtpVerify}
          onCancel={() => { setShowOtpModal(false); setOtpOperation(null); }}
        />
      )}

      {/* Endpoint Form Modal */}
      {showForm && (
        <EndpointForm
          endpoint={editingEndpoint}
          vendors={vendors}
          depositi={depositi}
          onSave={handleSaveEndpoint}
          onCancel={() => { setShowForm(false); setEditingEndpoint(null); }}
        />
      )}
    </div>
  );
}
