// =============================================================================
// TO_EXTRACTOR v6.2 - API CLIENT
// Con autenticazione JWT
// =============================================================================

import axios from 'axios'

// Configurazione
const isDev = import.meta.env.DEV
const isCodespaces = window.location.hostname.includes('github.dev')

export function getApiBaseUrl() {
  if (isDev && !isCodespaces) return ''  // Vite proxy
  if (isCodespaces) {
    const baseHost = window.location.hostname.replace(/-\d+\./, '-8000.')
    return `https://${baseHost}`
  }
  return import.meta.env.VITE_API_URL || 'http://localhost:8000'
}

const API_URL = `${getApiBaseUrl()}/api/v1`

// =============================================================================
// STORAGE KEYS per autenticazione
// =============================================================================
const TOKEN_KEY = 'to_extractor_token'
const USER_KEY = 'to_extractor_user'

// =============================================================================
// CLIENT AXIOS
// =============================================================================
const api = axios.create({
  baseURL: API_URL,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' }
})

// =============================================================================
// REQUEST INTERCEPTOR - Aggiunge token JWT
// =============================================================================
api.interceptors.request.use(config => {
  // Recupera token da localStorage
  const token = localStorage.getItem(TOKEN_KEY)
  
  // Se token presente, aggiunge header Authorization
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  
  if (isDev) console.log(`📤 ${config.method?.toUpperCase()} ${config.url}`)
  return config
})

// =============================================================================
// RESPONSE INTERCEPTOR - Gestisce errori auth
// =============================================================================
api.interceptors.response.use(
  response => {
    if (isDev) console.log(`📥 ${response.status} ${response.config.url}`)
    return response
  },
  error => {
    console.error('❌ API Error:', error.response?.data || error.message)
    
    // 401 Unauthorized - Token invalido o scaduto
    if (error.response?.status === 401) {
      // Pulisce storage
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem(USER_KEY)
      
      // Redirect a login (se non già su login)
      if (!window.location.pathname.includes('/login')) {
        window.location.href = '/login'
      }
    }
    
    throw error
  }
)

// =============================================================================
// AUTH API (NUOVO v6.2)
// =============================================================================
export const authApi = {
  // Login
  login: (username, password) => 
    api.post('/auth/login', { username, password }).then(r => {
      const { access_token, user } = r.data
      localStorage.setItem(TOKEN_KEY, access_token)
      localStorage.setItem(USER_KEY, JSON.stringify(user))
      return r.data
    }),
  
  // Logout
  logout: () => 
    api.post('/auth/logout')
      .catch(() => {}) // Ignora errori
      .finally(() => {
        localStorage.removeItem(TOKEN_KEY)
        localStorage.removeItem(USER_KEY)
      }),
  
  // Info utente corrente
  getMe: () => api.get('/auth/me').then(r => r.data),
  
  // Permessi utente
  getMyPermissions: () => api.get('/auth/me/permissions').then(r => r.data),
  
  // Sessioni attive
  getMySessions: () => api.get('/auth/me/sessions').then(r => r.data),
  
  // Revoca sessione
  revokeSession: (id) => api.delete(`/auth/me/sessions/${id}`),
  
  // Revoca altre sessioni
  revokeOtherSessions: () => api.post('/auth/me/sessions/revoke-others'),
  
  // Helper: verifica se autenticato
  isAuthenticated: () => !!localStorage.getItem(TOKEN_KEY),
  
  // Helper: recupera utente da localStorage
  getStoredUser: () => {
    const userJson = localStorage.getItem(USER_KEY)
    return userJson ? JSON.parse(userJson) : null
  },
  
  // Helper: recupera token
  getToken: () => localStorage.getItem(TOKEN_KEY),
}

// =============================================================================
// UTENTI API (NUOVO v6.2)
// =============================================================================
export const utentiApi = {
  // Lista utenti
  getList: (params = {}) => {
    const searchParams = new URLSearchParams()
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') searchParams.append(k, String(v))
    })
    return api.get(`/utenti?${searchParams}`).then(r => r.data)
  },
  
  // Dettaglio utente
  getDetail: (id) => api.get(`/utenti/${id}`).then(r => r.data),
  
  // Crea utente
  create: (data) => api.post('/utenti', data).then(r => r.data),
  
  // Modifica utente
  update: (id, data) => api.patch(`/utenti/${id}`, data).then(r => r.data),
  
  // Cambio password
  changePassword: (id, data) => api.post(`/utenti/${id}/cambio-password`, data),
  
  // Disabilita utente
  disable: (id, motivo = null) => api.post(`/utenti/${id}/disabilita`, { motivo }).then(r => r.data),
  
  // Riabilita utente
  enable: (id) => api.post(`/utenti/${id}/riabilita`).then(r => r.data),
  
  // Log attività
  getLogs: (id, params = {}) => {
    const searchParams = new URLSearchParams()
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') searchParams.append(k, String(v))
    })
    return api.get(`/utenti/${id}/logs?${searchParams}`).then(r => r.data)
  },

  // Aggiorna profilo personale (v6.2.1)
  updateProfilo: (data) => api.patch('/utenti/me/profilo', data).then(r => r.data),
}

// =============================================================================
// DASHBOARD
// =============================================================================
export const dashboardApi = {
  getStats: () => api.get('/dashboard').then(r => r.data),
  getSummary: () => api.get('/dashboard/summary').then(r => r.data),
  getOrdiniRecenti: (limit = 10) => api.get(`/dashboard/ordini-recenti?limit=${limit}`).then(r => r.data),
  getAnomalieCritiche: (limit = 10) => api.get(`/dashboard/anomalie-critiche?limit=${limit}`).then(r => r.data),
  getVendorStats: () => api.get('/dashboard/vendor-stats').then(r => r.data),
  getAnagraficaStats: () => api.get('/dashboard/anagrafica-stats').then(r => r.data),
}

// =============================================================================
// UPLOAD
// =============================================================================
export const uploadApi = {
  uploadPdf: (file, onProgress) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: e => onProgress?.(Math.round((e.loaded * 100) / e.total))
    }).then(r => r.data)
  },
  
  uploadMultiple: (files, onProgress) => {
    const formData = new FormData()
    files.forEach(f => formData.append('files', f))
    return api.post('/upload/multiple', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: e => onProgress?.(Math.round((e.loaded * 100) / e.total))
    }).then(r => r.data)
  },
  
  getRecent: (limit = 20) => api.get(`/upload/recent?limit=${limit}`).then(r => r.data),
  getStats: () => api.get('/upload/stats').then(r => r.data),
  getVendors: () => api.get('/upload/vendors').then(r => r.data),
}

// =============================================================================
// ORDINI (v6.1 - con conferma righe)
// =============================================================================
export const ordiniApi = {
  // Query base
  getList: (filters = {}) => {
    const params = new URLSearchParams()
    Object.entries(filters).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') params.append(k, String(v))
    })
    return api.get(`/ordini?${params}`).then(r => r.data)
  },
  
  getDetail: (id) => api.get(`/ordini/${id}`).then(r => r.data),
  getRighe: (id) => api.get(`/ordini/${id}/righe`).then(r => r.data),
  updateStato: (id, stato) => api.put(`/ordini/${id}/stato?nuovo_stato=${stato}`).then(r => r.data),
  delete: (id) => api.delete(`/ordini/${id}`).then(r => r.data),
  batchUpdateStato: (ids, stato) => api.post('/ordini/batch/stato', { ids, nuovo_stato: stato }).then(r => r.data),
  batchDelete: (ids) => api.delete('/ordini/batch', { data: { ids } }).then(r => r.data),
  getStati: () => api.get('/ordini/stati').then(r => r.data),
  getLookupMethods: () => api.get('/ordini/lookup-methods').then(r => r.data),
  
  // v6.1: Conferma righe
  confermaRiga: (idTestata, idDettaglio, operatore, note = null) =>
    api.post(`/ordini/${idTestata}/righe/${idDettaglio}/conferma`, { operatore, note }).then(r => r.data),
  
  confermaOrdineCompleto: (idTestata, operatore, forzaConferma = false, note = null) =>
    api.post(`/ordini/${idTestata}/conferma-tutto`, { 
      operatore, 
      forza_conferma: forzaConferma, 
      note 
    }).then(r => r.data),
  
  getStatoRighe: (idTestata) => 
    api.get(`/ordini/${idTestata}/stato-righe`).then(r => r.data),
  
  getRigaDettaglio: (idTestata, idDettaglio) => 
    api.get(`/ordini/${idTestata}/righe/${idDettaglio}`).then(r => r.data),
  
  modificaRiga: (idTestata, idDettaglio, operatore, modifiche, note = null) =>
    api.put(`/ordini/${idTestata}/righe/${idDettaglio}`, { operatore, modifiche, note }).then(r => r.data),
  
  inviaASupervisione: (idTestata, idDettaglio, operatore) =>
    api.post(`/ordini/${idTestata}/righe/${idDettaglio}/supervisione?operatore=${encodeURIComponent(operatore)}`).then(r => r.data),

  // v6.1.1: Valida e genera tracciato
  // validazioneMassiva: true = Dashboard (conferma tutto), false = Dettaglio (solo confermate)
  validaEGeneraTracciato: (idTestata, operatore, validazioneMassiva = false) =>
    api.post(`/ordini/${idTestata}/valida`, { operatore, validazione_massiva: validazioneMassiva }).then(r => r.data),

  // v6.2.1: Evasioni parziali - imposta q_da_evadere (quantità per prossimo tracciato)
  registraEvasione: (idTestata, idDettaglio, qDaEvadere, operatore) =>
    api.post(`/ordini/${idTestata}/righe/${idDettaglio}/evasione`, {
      q_da_evadere: qDaEvadere,
      operatore
    }).then(r => r.data),
  // v6.2: Archiviazione (stato EVASO forzato)
  archiviaOrdine: (idTestata, operatore = "admin") =>
    api.post(`/ordini/${idTestata}/archivia?operatore=${encodeURIComponent(operatore)}`).then(r => r.data),
  
  archiviaRiga: (idTestata, idDettaglio, operatore = "admin") =>
    api.post(`/ordini/${idTestata}/righe/${idDettaglio}/archivia?operatore=${encodeURIComponent(operatore)}`).then(r => r.data),

  // v6.2.1: Ripristino conferme - annulla q_da_evadere e riporta stato a ESTRATTO/PARZIALE
  ripristinaRiga: (idTestata, idDettaglio, operatore) =>
    api.post(`/ordini/${idTestata}/righe/${idDettaglio}/ripristina`, { operatore }).then(r => r.data),

  ripristinaTutto: (idTestata, operatore) =>
    api.post(`/ordini/${idTestata}/ripristina-tutto`, { operatore }).then(r => r.data),
}

// =============================================================================
// ANAGRAFICA
// =============================================================================
export const anagraficaApi = {
  importFarmacie: (file, onProgress) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/anagrafica/farmacie/import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: e => onProgress?.(Math.round((e.loaded * 100) / e.total))
    }).then(r => r.data)
  },
  
  importParafarmacie: (file, onProgress) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/anagrafica/parafarmacie/import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: e => onProgress?.(Math.round((e.loaded * 100) / e.total))
    }).then(r => r.data)
  },
  
  getStats: () => api.get('/anagrafica/stats').then(r => r.data),
  search: (q, tipo = 'all', limit = 20) => 
    api.get(`/anagrafica/search?q=${encodeURIComponent(q)}&tipo=${tipo}&limit=${limit}`).then(r => r.data),
  getFarmacia: (id) => api.get(`/anagrafica/farmacie/${id}`).then(r => r.data),
  getFarmacieByPiva: (piva) => api.get(`/anagrafica/farmacie/piva/${piva}`).then(r => r.data),
  clearFarmacie: () => api.delete('/anagrafica/farmacie?confirm=true').then(r => r.data),
  clearParafarmacie: () => api.delete('/anagrafica/parafarmacie?confirm=true').then(r => r.data),
}

// =============================================================================
// TRACCIATI
// =============================================================================
export const tracciatiApi = {
  genera: (ordiniIds) => api.post('/tracciati/genera', ordiniIds ? { ordini_ids: ordiniIds } : {}).then(r => r.data),
  generaSingolo: (id) => api.post(`/tracciati/genera/${id}`).then(r => r.data),
  getPreview: (id) => api.get(`/tracciati/preview/${id}`).then(r => r.data),
  getPronti: () => api.get('/tracciati/pronti').then(r => r.data),
  getStorico: (limit = 20) => api.get(`/tracciati/storico?limit=${limit}`).then(r => r.data),
  getFiles: () => api.get('/tracciati/files').then(r => r.data),
  deleteFiles: () => api.delete('/tracciati/files?confirm=true').then(r => r.data),
  getDownloadUrl: (filename) => `${API_URL}/tracciati/download/${filename}`,
}

// =============================================================================
// ANOMALIE
// =============================================================================
export const anomalieApi = {
  getList: (filters = {}) => {
    const params = new URLSearchParams()
    Object.entries(filters).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') params.append(k, String(v))
    })
    return api.get(`/anomalie?${params}`).then(r => r.data)
  },

  getByOrdine: (id) => api.get(`/anomalie/ordine/${id}`).then(r => r.data),
  update: (id, data) => api.put(`/anomalie/${id}`, data).then(r => r.data),
  batchRisolvi: (ids, note) => api.post('/anomalie/batch/risolvi', { ids, note }).then(r => r.data),
  batchIgnora: (ids, note) => api.post('/anomalie/batch/ignora', { ids, note }).then(r => r.data),
  getTipi: () => api.get('/anomalie/tipi').then(r => r.data),
  getLivelli: () => api.get('/anomalie/livelli').then(r => r.data),
  getStati: () => api.get('/anomalie/stati').then(r => r.data),
  // v6.2: Dettaglio anomalia con parent/child
  getDettaglio: (id) => api.get(`/anomalie/dettaglio/${id}`).then(r => r.data),
  modificaRiga: (id, data) => api.put(`/anomalie/dettaglio/${id}/riga`, data).then(r => r.data),
  risolviDettaglio: (id, note) => api.post(`/anomalie/dettaglio/${id}/risolvi`, { note }).then(r => r.data),
}

// =============================================================================
// LOOKUP
// =============================================================================
export const lookupApi = {
  test: (data) => api.post('/lookup/test', data).then(r => r.data),
  batch: (limit = 100) => api.post(`/lookup/batch?limit=${limit}`).then(r => r.data),
  manuale: (id, idFarmacia, idParafarmacia, minIdManuale = null) =>
    api.put(`/lookup/manuale/${id}`, {
      id_farmacia: idFarmacia,
      id_parafarmacia: idParafarmacia,
      min_id_manuale: minIdManuale
    }).then(r => r.data),
  getPending: (limit = 50) => api.get(`/lookup/pending?limit=${limit}`).then(r => r.data),
  searchFarmacie: (q, limit = 20) =>
    api.get(`/lookup/search/farmacie?q=${encodeURIComponent(q)}&limit=${limit}`).then(r => r.data),
  searchParafarmacie: (q, limit = 20) =>
    api.get(`/lookup/search/parafarmacie?q=${encodeURIComponent(q)}&limit=${limit}`).then(r => r.data),
  getStats: () => api.get('/lookup/stats').then(r => r.data),
  // v6.2.5: Alternative lookup per P.IVA multipunto
  getAlternative: (idTestata) =>
    api.get(`/lookup/alternative/${idTestata}`).then(r => r.data),
}

// =============================================================================
// SUPERVISIONE (v6.1 - con ritorno a ordine)
// =============================================================================
export const supervisioneApi = {
  // Supervisioni pending
  getPending: () => api.get('/supervisione/pending').then(r => r.data),
  getPendingCount: () => api.get('/supervisione/pending/count').then(r => r.data),
  
  // Dettaglio supervisione
  getDetail: (id) => api.get(`/supervisione/${id}`).then(r => r.data),
  getByOrdine: (idTestata) => api.get(`/supervisione/ordine/${idTestata}`).then(r => r.data),
  
  // Decisioni base
  approva: (id, operatore, note = null) => 
    api.post(`/supervisione/${id}/approva`, { operatore, note }).then(r => r.data),
  rifiuta: (id, operatore, note) => 
    api.post(`/supervisione/${id}/rifiuta`, { operatore, note }).then(r => r.data),
  modifica: (id, operatore, modifiche, note = null) => 
    api.post(`/supervisione/${id}/modifica`, { operatore, modifiche, note }).then(r => r.data),
  
  // v6.1: Azioni con ritorno a ordine
  approvaETorna: (id, operatore, note = null) =>
    api.post(`/supervisione/${id}/completa-e-torna`, { operatore, note }).then(r => r.data),
  
  modificaETorna: (id, operatore, modifiche, note = null) =>
    api.post(`/supervisione/${id}/modifica-e-torna`, { operatore, modifiche, note }).then(r => r.data),
  
  lasciaSospeso: (id, operatore) =>
    api.post(`/supervisione/${id}/lascia-sospeso?operatore=${encodeURIComponent(operatore)}`).then(r => r.data),
  
  // Criteri ML
  getCriteriOrdinari: () => api.get('/supervisione/criteri/ordinari').then(r => r.data),
  getCriteriStats: () => api.get('/supervisione/criteri/stats').then(r => r.data),
  getPattern: (signature) => api.get(`/supervisione/criteri/${signature}`).then(r => r.data),
  resetPattern: (signature, operatore) => 
    api.post(`/supervisione/criteri/${signature}/reset?operatore=${encodeURIComponent(operatore)}`).then(r => r.data),
  
  // Storico
  getStorico: (limit = 50) => api.get(`/supervisione/storico/applicazioni?limit=${limit}`).then(r => r.data),
}

// =============================================================================
// ADMIN API - Operazioni amministrative sistema
// =============================================================================
export const adminApi = {
  // Crea backup database
  backup: () => api.post('/admin/backup').then(r => r.data),
  // Elimina tutti gli ordini (richiede conferma)
  clearOrdini: () => api.delete('/admin/ordini/all?confirm=CONFERMA').then(r => r.data),
  // Reset completo sistema (richiede conferma)
  resetSistema: () => api.post('/admin/reset?confirm=RESET_COMPLETO').then(r => r.data),
  // Recupera impostazioni
  getSettings: () => api.get('/admin/settings').then(r => r.data),
  // Salva impostazioni
  saveSettings: (settings) => api.put('/admin/settings', settings).then(r => r.data),
}

// =============================================================================
// GMAIL MONITOR API (v6.2)
// =============================================================================
export const gmailApi = {
  // Stato e configurazione Gmail Monitor
  getStatus: () => api.get('/gmail/status').then(r => r.data),

  // Avvia sincronizzazione manuale
  sync: () => api.post('/gmail/sync').then(r => r.data),

  // Lista email scaricate (con paginazione e filtri)
  getEmails: (params = {}) => {
    const searchParams = new URLSearchParams()
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') searchParams.append(k, String(v))
    })
    return api.get(`/gmail/emails?${searchParams}`).then(r => r.data)
  },

  // Dettaglio singola email
  getEmail: (id) => api.get(`/gmail/emails/${id}`).then(r => r.data),

  // Ritenta elaborazione email in errore
  retryEmail: (id) => api.post(`/gmail/emails/${id}/retry`).then(r => r.data),

  // Statistiche dettagliate
  getStats: () => api.get('/gmail/stats').then(r => r.data),
}

// =============================================================================
// API PRODUTTIVITÀ (v6.2)
// =============================================================================
export const produttivitaApi = {
  // Heartbeat per tracking tempo sezione
  heartbeat: (sezione) => api.post('/produttivita/heartbeat', { sezione }).then(r => r.data),

  // Produttività sessione corrente
  getSessione: () => api.get('/produttivita/sessione').then(r => r.data),

  // Produttività giornaliera
  getGiorno: (data) => api.get(`/produttivita/giorno/${data}`).then(r => r.data),

  // Ultime task di un operatore
  getUltimeTask: (idOperatore = null, limit = 10) => {
    const params = { limit };
    if (idOperatore) params.id_operatore = idOperatore;
    return api.get('/produttivita/ultime-task', { params }).then(r => r.data);
  },
}

export default api