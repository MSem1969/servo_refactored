/**
 * UtentiPage.jsx
 * Gestione utenti del sistema con controllo accessi basato su ruoli.
 *
 * Funzionalità:
 * - Lista utenti con filtri
 * - Creazione nuovo utente (rispettando gerarchia ruoli)
 * - Modifica dati utente
 * - Cambio password
 * - Abilita/Disabilita utente
 * - Visualizzazione permessi per ruolo
 */

import { useState, useEffect, useCallback } from 'react';
import { utentiApi } from './api';
import Avatar from './components/Avatar';

// Configurazione ruoli e permessi (mirror del backend)
const RUOLI = {
  admin: { label: 'Amministratore', livello: 3, color: 'red' },
  supervisore: { label: 'Supervisore', livello: 2, color: 'purple' },
  operatore: { label: 'Operatore', livello: 1, color: 'blue' },
  readonly: { label: 'Sola Lettura', livello: 0, color: 'slate' }
};

const SEZIONI = [
  { id: 'dashboard', label: 'Dashboard', icon: '📊' },
  { id: 'upload', label: 'Upload PDF', icon: '📤' },
  { id: 'database', label: 'Database Ordini', icon: '🗄️' },
  { id: 'ordine_detail', label: 'Dettaglio Ordine', icon: '📋' },
  { id: 'anomalie', label: 'Anomalie', icon: '🚨' },
  { id: 'supervisione', label: 'Supervisione ML', icon: '🤖' },
  { id: 'tracciati', label: 'Tracciati', icon: '📁' },
  { id: 'settings', label: 'Impostazioni', icon: '⚙️' },
  { id: 'utenti', label: 'Gestione Utenti', icon: '👥' }
];

// Permessi default per ruolo (da sincronizzare con backend)
const PERMESSI_RUOLO = {
  admin: ['dashboard', 'upload', 'database', 'ordine_detail', 'anomalie', 'supervisione', 'tracciati', 'settings', 'utenti'],
  supervisore: ['dashboard', 'upload', 'database', 'ordine_detail', 'anomalie', 'supervisione', 'tracciati', 'utenti'],
  operatore: ['dashboard', 'upload', 'database', 'ordine_detail', 'tracciati'],
  readonly: ['dashboard', 'database']
};

export default function UtentiPage({ currentUser }) {
  // Stati principali
  const [loading, setLoading] = useState(true);
  const [utenti, setUtenti] = useState([]);
  const [selectedUtente, setSelectedUtente] = useState(null);
  const [activeTab, setActiveTab] = useState('lista');

  // Stati per creazione/modifica
  const [showModal, setShowModal] = useState(false);
  const [modalMode, setModalMode] = useState('create'); // 'create' | 'edit' | 'password'
  const [formData, setFormData] = useState({
    username: '',
    password: '',
    conferma_password: '',
    nome: '',
    cognome: '',
    email: '',
    ruolo: 'operatore'
  });
  const [formErrors, setFormErrors] = useState({});
  const [saving, setSaving] = useState(false);

  // Stati per filtri
  const [filters, setFilters] = useState({
    ruolo: '',
    attivo: '',
    q: ''
  });

  // Carica lista utenti
  const loadUtenti = useCallback(async () => {
    setLoading(true);
    try {
      const params = {};
      if (filters.ruolo) params.ruolo = filters.ruolo;
      if (filters.attivo !== '') params.attivo = filters.attivo === 'true';
      if (filters.q) params.search = filters.q;  // Backend usa 'search' non 'q'

      const res = await utentiApi.getList(params);
      // Backend restituisce { items: [...], total, page, ... }
      // Mappa i campi per compatibilità frontend
      const mappedUtenti = (res.items || []).map(u => ({
        ...u,
        id: u.id_operatore,
        ultimo_accesso: u.last_login_at
      }));
      setUtenti(mappedUtenti);
    } catch (err) {
      console.error('Errore caricamento utenti:', err);
      setUtenti([]);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  // Carica dati iniziali
  useEffect(() => {
    loadUtenti();
  }, [loadUtenti]);

  // Verifica se l'utente corrente può gestire un ruolo
  const canManageRole = (targetRole) => {
    if (!currentUser) return false;
    const currentLevel = RUOLI[currentUser.ruolo]?.livello || 0;
    const targetLevel = RUOLI[targetRole]?.livello || 0;
    return currentLevel > targetLevel;
  };

  // Verifica se l'utente corrente può modificare un utente
  const canManageUser = (utente) => {
    if (!currentUser) return false;
    if (currentUser.id === utente.id) return true; // Può modificare se stesso (solo alcuni campi)
    return canManageRole(utente.ruolo);
  };

  // Ruoli che l'utente corrente può creare
  const getCreatableRoles = () => {
    if (!currentUser) return [];
    return Object.entries(RUOLI)
      .filter(([key, value]) => canManageRole(key))
      .map(([key]) => key);
  };

  // v6.2.1: Ruoli visibili nella matrice permessi (proprio ruolo + inferiori)
  const getVisibleRoles = () => {
    if (!currentUser) return [];
    const currentLevel = RUOLI[currentUser.ruolo]?.livello || 0;
    return Object.entries(RUOLI)
      .filter(([key, value]) => value.livello <= currentLevel)
      .map(([key]) => key);
  };

  // v6.2.1: Sezioni visibili nella matrice (solo quelle a cui l'utente ha accesso)
  const getVisibleSections = () => {
    if (!currentUser) return [];
    const userPermissions = PERMESSI_RUOLO[currentUser.ruolo] || [];
    return SEZIONI.filter(sezione => userPermissions.includes(sezione.id));
  };

  // Apri modal creazione
  const openCreateModal = () => {
    const creatableRoles = getCreatableRoles();
    setFormData({
      username: '',
      password: '',
      conferma_password: '',
      nome: '',
      cognome: '',
      email: '',
      ruolo: creatableRoles[0] || 'operatore'
    });
    setFormErrors({});
    setModalMode('create');
    setShowModal(true);
  };

  // Apri modal modifica
  const openEditModal = (utente) => {
    setSelectedUtente(utente);
    setFormData({
      nome: utente.nome || '',
      cognome: utente.cognome || '',
      email: utente.email || '',
      ruolo: utente.ruolo
    });
    setFormErrors({});
    setModalMode('edit');
    setShowModal(true);
  };

  // Apri modal cambio password
  const openPasswordModal = (utente) => {
    setSelectedUtente(utente);
    setFormData({
      password: '',
      conferma_password: ''
    });
    setFormErrors({});
    setModalMode('password');
    setShowModal(true);
  };

  // Valida form
  const validateForm = () => {
    const errors = {};

    if (modalMode === 'create') {
      if (!formData.username?.trim()) errors.username = 'Username obbligatorio';
      if (formData.username && formData.username.length < 3) errors.username = 'Minimo 3 caratteri';
      if (!formData.password) errors.password = 'Password obbligatoria';
      if (formData.password && formData.password.length < 6) errors.password = 'Minimo 6 caratteri';
      if (formData.password !== formData.conferma_password) errors.conferma_password = 'Le password non coincidono';
      if (!formData.email?.trim()) errors.email = 'Email obbligatoria';
    }

    if (modalMode === 'edit') {
      if (!formData.email?.trim()) errors.email = 'Email obbligatoria';
    }

    if (modalMode === 'password') {
      if (!formData.password) errors.password = 'Password obbligatoria';
      if (formData.password && formData.password.length < 6) errors.password = 'Minimo 6 caratteri';
      if (formData.password !== formData.conferma_password) errors.conferma_password = 'Le password non coincidono';
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  // Salva (crea/modifica/password)
  const handleSave = async () => {
    if (!validateForm()) return;

    setSaving(true);
    try {
      if (modalMode === 'create') {
        await utentiApi.create({
          username: formData.username,
          password: formData.password,
          nome: formData.nome,
          cognome: formData.cognome,
          email: formData.email,
          ruolo: formData.ruolo
        });
        alert('Utente creato con successo!');
      } else if (modalMode === 'edit') {
        await utentiApi.update(selectedUtente.id, {
          nome: formData.nome,
          cognome: formData.cognome,
          email: formData.email
        });
        alert('Utente modificato con successo!');
      } else if (modalMode === 'password') {
        await utentiApi.changePassword(selectedUtente.id, {
          nuova_password: formData.password
        });
        alert('Password cambiata con successo!');
      }

      setShowModal(false);
      loadUtenti();
    } catch (err) {
      alert('Errore: ' + (err.response?.data?.detail || err.message));
    } finally {
      setSaving(false);
    }
  };

  // Disabilita utente
  const handleDisable = async (utente) => {
    if (!window.confirm(`Disabilitare l'utente ${utente.username}?`)) return;

    try {
      await utentiApi.disable(utente.id);
      alert('Utente disabilitato');
      loadUtenti();
    } catch (err) {
      alert('Errore: ' + (err.response?.data?.detail || err.message));
    }
  };

  // Riabilita utente
  const handleEnable = async (utente) => {
    if (!window.confirm(`Riabilitare l'utente ${utente.username}?`)) return;

    try {
      await utentiApi.enable(utente.id);
      alert('Utente riabilitato');
      loadUtenti();
    } catch (err) {
      alert('Errore: ' + (err.response?.data?.detail || err.message));
    }
  };

  // Render badge ruolo
  const RoleBadge = ({ ruolo }) => {
    const config = RUOLI[ruolo] || { label: ruolo, color: 'slate' };
    const colorClasses = {
      red: 'bg-red-100 text-red-700',
      purple: 'bg-purple-100 text-purple-700',
      blue: 'bg-blue-100 text-blue-700',
      slate: 'bg-slate-100 text-slate-700'
    };
    return (
      <span className={`px-2 py-1 rounded text-xs font-medium ${colorClasses[config.color]}`}>
        {config.label}
      </span>
    );
  };

  // Tabs
  const tabs = [
    { id: 'lista', label: 'Lista Utenti', count: utenti.length },
    { id: 'permessi', label: 'Matrice Permessi', count: null }
  ];

  return (
    <div className="p-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-800">Gestione Utenti</h1>
        <p className="text-slate-500 mt-1">
          Crea e gestisci gli utenti del sistema
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="bg-white rounded-xl p-4 shadow-sm border border-slate-200">
          <div className="text-3xl font-bold text-slate-800">{utenti.length}</div>
          <div className="text-sm text-slate-500">Totale Utenti</div>
        </div>
        <div className="bg-white rounded-xl p-4 shadow-sm border border-slate-200">
          <div className="text-3xl font-bold text-green-500">
            {utenti.filter(u => u.attivo !== false).length}
          </div>
          <div className="text-sm text-slate-500">Attivi</div>
        </div>
        <div className="bg-white rounded-xl p-4 shadow-sm border border-slate-200">
          <div className="text-3xl font-bold text-red-500">
            {utenti.filter(u => u.attivo === false).length}
          </div>
          <div className="text-sm text-slate-500">Disabilitati</div>
        </div>
        <div className="bg-white rounded-xl p-4 shadow-sm border border-slate-200">
          <div className="text-3xl font-bold text-purple-500">
            {utenti.filter(u => u.ruolo === 'supervisore').length}
          </div>
          <div className="text-sm text-slate-500">Supervisori</div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-4 border-b border-slate-200">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === tab.id
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
          >
            {tab.label}
            {tab.count !== null && (
              <span className={`ml-2 px-2 py-0.5 rounded-full text-xs ${
                activeTab === tab.id ? 'bg-blue-100 text-blue-600' : 'bg-slate-100'
              }`}>
                {tab.count}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200">

        {/* Tab Lista Utenti */}
        {activeTab === 'lista' && (
          <div className="p-4">
            {/* Filtri e azioni */}
            <div className="flex gap-4 mb-4 flex-wrap">
              <input
                type="text"
                placeholder="Cerca username, nome, email..."
                value={filters.q}
                onChange={(e) => setFilters(f => ({ ...f, q: e.target.value }))}
                className="px-3 py-2 border border-slate-300 rounded-lg text-sm flex-1 min-w-[200px]"
              />
              <select
                value={filters.ruolo}
                onChange={(e) => setFilters(f => ({ ...f, ruolo: e.target.value }))}
                className="px-3 py-2 border border-slate-300 rounded-lg text-sm"
              >
                <option value="">Tutti i ruoli</option>
                {Object.entries(RUOLI).map(([key, val]) => (
                  <option key={key} value={key}>{val.label}</option>
                ))}
              </select>
              <select
                value={filters.attivo}
                onChange={(e) => setFilters(f => ({ ...f, attivo: e.target.value }))}
                className="px-3 py-2 border border-slate-300 rounded-lg text-sm"
              >
                <option value="">Tutti gli stati</option>
                <option value="true">Attivi</option>
                <option value="false">Disabilitati</option>
              </select>
              <button
                onClick={loadUtenti}
                className="px-4 py-2 bg-slate-100 hover:bg-slate-200 rounded-lg text-sm"
              >
                Ricarica
              </button>
              {getCreatableRoles().length > 0 && (
                <button
                  onClick={openCreateModal}
                  className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg text-sm"
                >
                  + Nuovo Utente
                </button>
              )}
            </div>

            {/* Tabella */}
            {loading ? (
              <div className="text-center py-8 text-slate-500">
                <div className="animate-spin text-2xl mb-2">...</div>
                <p>Caricamento utenti...</p>
              </div>
            ) : utenti.length === 0 ? (
              <div className="text-center py-8 text-slate-500">
                <div className="text-4xl mb-2">--</div>
                <p>Nessun utente trovato</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-slate-50">
                    <tr>
                      <th className="p-3 text-left">Username</th>
                      <th className="p-3 text-left">Nome</th>
                      <th className="p-3 text-left">Email</th>
                      <th className="p-3 text-left">Ruolo</th>
                      <th className="p-3 text-left">Stato</th>
                      <th className="p-3 text-left">Ultimo Accesso</th>
                      <th className="p-3 text-left">Azioni</th>
                    </tr>
                  </thead>
                  <tbody>
                    {utenti.map((utente) => (
                      <tr key={utente.id} className="border-b border-slate-100 hover:bg-slate-50">
                        <td className="p-3">
                          <div className="flex items-center gap-2">
                            <Avatar user={utente} size="sm" />
                            <span className="font-medium">{utente.username}</span>
                          </div>
                        </td>
                        <td className="p-3">{utente.nome} {utente.cognome}</td>
                        <td className="p-3 text-slate-500">{utente.email || '-'}</td>
                        <td className="p-3"><RoleBadge ruolo={utente.ruolo} /></td>
                        <td className="p-3">
                          <span className={`px-2 py-1 rounded text-xs ${
                            utente.attivo !== false
                              ? 'bg-green-100 text-green-700'
                              : 'bg-red-100 text-red-700'
                          }`}>
                            {utente.attivo !== false ? 'Attivo' : 'Disabilitato'}
                          </span>
                        </td>
                        <td className="p-3 text-xs text-slate-500">
                          {utente.ultimo_accesso
                            ? new Date(utente.ultimo_accesso).toLocaleString('it-IT')
                            : 'Mai'
                          }
                        </td>
                        <td className="p-3">
                          <div className="flex gap-1">
                            {canManageUser(utente) && (
                              <>
                                <button
                                  onClick={() => openEditModal(utente)}
                                  className="px-2 py-1 text-xs bg-blue-100 hover:bg-blue-200 text-blue-700 rounded"
                                  title="Modifica"
                                >
                                  Edit
                                </button>
                                <button
                                  onClick={() => openPasswordModal(utente)}
                                  className="px-2 py-1 text-xs bg-yellow-100 hover:bg-yellow-200 text-yellow-700 rounded"
                                  title="Cambia Password"
                                >
                                  PWD
                                </button>
                              </>
                            )}
                            {canManageRole(utente.ruolo) && currentUser?.id !== utente.id && (
                              utente.attivo !== false ? (
                                <button
                                  onClick={() => handleDisable(utente)}
                                  className="px-2 py-1 text-xs bg-red-100 hover:bg-red-200 text-red-700 rounded"
                                  title="Disabilita"
                                >
                                  OFF
                                </button>
                              ) : (
                                <button
                                  onClick={() => handleEnable(utente)}
                                  className="px-2 py-1 text-xs bg-green-100 hover:bg-green-200 text-green-700 rounded"
                                  title="Riabilita"
                                >
                                  ON
                                </button>
                              )
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Tab Matrice Permessi */}
        {activeTab === 'permessi' && (
          <div className="p-4">
            <p className="text-sm text-slate-500 mb-4">
              Questa tabella mostra i permessi di accesso alle sezioni per ogni ruolo.
              I permessi sono definiti a livello di ruolo e non modificabili per singolo utente.
            </p>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="p-3 text-left">Sezione</th>
                    {/* v6.2.1: Mostra solo ruoli visibili (proprio + inferiori) */}
                    {getVisibleRoles().map((ruolo) => (
                      <th key={ruolo} className="p-3 text-center">
                        <RoleBadge ruolo={ruolo} />
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {/* v6.2.1: Mostra solo sezioni a cui l'utente ha accesso */}
                  {getVisibleSections().map((sezione) => (
                    <tr key={sezione.id} className="border-b border-slate-100">
                      <td className="p-3">
                        <span className="mr-2">{sezione.icon}</span>
                        {sezione.label}
                      </td>
                      {getVisibleRoles().map((ruolo) => (
                        <td key={ruolo} className="p-3 text-center">
                          {PERMESSI_RUOLO[ruolo]?.includes(sezione.id) ? (
                            <span className="text-green-500 text-lg">OK</span>
                          ) : (
                            <span className="text-red-300 text-lg">--</span>
                          )}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* Modal Creazione/Modifica/Password */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-md mx-4">
            <div className="p-4 border-b border-slate-200">
              <h3 className="text-lg font-semibold">
                {modalMode === 'create' && 'Nuovo Utente'}
                {modalMode === 'edit' && `Modifica: ${selectedUtente?.username}`}
                {modalMode === 'password' && `Cambia Password: ${selectedUtente?.username}`}
              </h3>
            </div>

            <div className="p-4 space-y-4">
              {/* Campi per creazione */}
              {modalMode === 'create' && (
                <>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">
                      Username *
                    </label>
                    <input
                      type="text"
                      value={formData.username}
                      onChange={(e) => setFormData(f => ({ ...f, username: e.target.value }))}
                      className={`w-full px-3 py-2 border rounded-lg text-sm ${
                        formErrors.username ? 'border-red-500' : 'border-slate-300'
                      }`}
                    />
                    {formErrors.username && (
                      <p className="text-xs text-red-500 mt-1">{formErrors.username}</p>
                    )}
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">
                      Ruolo *
                    </label>
                    <select
                      value={formData.ruolo}
                      onChange={(e) => setFormData(f => ({ ...f, ruolo: e.target.value }))}
                      className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                    >
                      {getCreatableRoles().map(ruolo => (
                        <option key={ruolo} value={ruolo}>
                          {RUOLI[ruolo].label}
                        </option>
                      ))}
                    </select>
                  </div>
                </>
              )}

              {/* Campi per modifica */}
              {(modalMode === 'create' || modalMode === 'edit') && (
                <>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-1">
                        Nome
                      </label>
                      <input
                        type="text"
                        value={formData.nome}
                        onChange={(e) => setFormData(f => ({ ...f, nome: e.target.value }))}
                        className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-slate-700 mb-1">
                        Cognome
                      </label>
                      <input
                        type="text"
                        value={formData.cognome}
                        onChange={(e) => setFormData(f => ({ ...f, cognome: e.target.value }))}
                        className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">
                      Email *
                    </label>
                    <input
                      type="email"
                      value={formData.email}
                      onChange={(e) => setFormData(f => ({ ...f, email: e.target.value }))}
                      className={`w-full px-3 py-2 border rounded-lg text-sm ${
                        formErrors.email ? 'border-red-500' : 'border-slate-300'
                      }`}
                    />
                    {formErrors.email && (
                      <p className="text-xs text-red-500 mt-1">{formErrors.email}</p>
                    )}
                  </div>
                </>
              )}

              {/* Campi password */}
              {(modalMode === 'create' || modalMode === 'password') && (
                <>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">
                      Password *
                    </label>
                    <input
                      type="password"
                      value={formData.password}
                      onChange={(e) => setFormData(f => ({ ...f, password: e.target.value }))}
                      className={`w-full px-3 py-2 border rounded-lg text-sm ${
                        formErrors.password ? 'border-red-500' : 'border-slate-300'
                      }`}
                    />
                    {formErrors.password && (
                      <p className="text-xs text-red-500 mt-1">{formErrors.password}</p>
                    )}
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">
                      Conferma Password *
                    </label>
                    <input
                      type="password"
                      value={formData.conferma_password}
                      onChange={(e) => setFormData(f => ({ ...f, conferma_password: e.target.value }))}
                      className={`w-full px-3 py-2 border rounded-lg text-sm ${
                        formErrors.conferma_password ? 'border-red-500' : 'border-slate-300'
                      }`}
                    />
                    {formErrors.conferma_password && (
                      <p className="text-xs text-red-500 mt-1">{formErrors.conferma_password}</p>
                    )}
                  </div>
                </>
              )}
            </div>

            <div className="p-4 border-t border-slate-200 flex justify-end gap-2">
              <button
                onClick={() => setShowModal(false)}
                className="px-4 py-2 bg-slate-100 hover:bg-slate-200 rounded-lg text-sm"
              >
                Annulla
              </button>
              <button
                onClick={handleSave}
                disabled={saving}
                className="px-4 py-2 bg-blue-500 hover:bg-blue-600 disabled:bg-slate-300 text-white rounded-lg text-sm"
              >
                {saving ? 'Salvataggio...' : 'Salva'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
