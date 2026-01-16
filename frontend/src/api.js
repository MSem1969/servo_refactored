// =============================================================================
// SERV.O v6.2 - API CLIENT
// Con autenticazione JWT
// =============================================================================

import axios from 'axios'

// Configurazione
const isDev = import.meta.env.DEV
const isCodespaces = window.location.hostname.includes('github.dev')
const isCloudflare = window.location.hostname.includes('trycloudflare.com')

// URL Backend Cloudflare Tunnel (aggiornare se cambia)
const CLOUDFLARE_BACKEND_URL = 'https://journalism-pleasant-jumping-difficulties.trycloudflare.com'

export function getApiBaseUrl() {
  if (isDev && !isCodespaces) return ''  // Vite proxy
  if (isCloudflare) {
    return CLOUDFLARE_BACKEND_URL  // Tunnel esterno
  }
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
const TOKEN_KEY = 'servo_token'
const USER_KEY = 'servo_user'

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

  importClienti: (file, onProgress) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/anagrafica/clienti/import', formData, {
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
  clearClienti: () => api.delete('/anagrafica/clienti?confirm=true').then(r => r.data),
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
  getCriteriTutti: () => api.get('/supervisione/criteri/tutti').then(r => r.data),
  getCriteriStats: () => api.get('/supervisione/criteri/stats').then(r => r.data),
  getPattern: (signature) => api.get(`/supervisione/criteri/${signature}`).then(r => r.data),
  resetPattern: (signature, operatore) =>
    api.post(`/supervisione/criteri/${signature}/reset?operatore=${encodeURIComponent(operatore)}`).then(r => r.data),
  promuoviPattern: (signature, operatore) =>
    api.post(`/supervisione/criteri/${signature}/promuovi?operatore=${encodeURIComponent(operatore)}`).then(r => r.data),
  
  // Storico
  getStorico: (limit = 50) => api.get(`/supervisione/criteri/storico/applicazioni?limit=${limit}`).then(r => r.data),

  // === SUPERVISIONE LISTINO (v7.0) ===

  // Dettaglio supervisione listino con suggerimenti
  getListinoDetail: (id) => api.get(`/supervisione/listino/${id}`).then(r => r.data),

  // Correzione prezzi/sconti listino
  correggiListino: (id, data) => api.post(`/supervisione/listino/${id}/correggi`, data).then(r => r.data),

  // Archiviazione riga listino
  archiviaListino: (id, data) => api.post(`/supervisione/listino/${id}/archivia`, data).then(r => r.data),

  // Pattern per AIC (suggerimenti precedenti)
  getListinoPattern: (codiceAic) => api.get(`/supervisione/listino/pattern/${codiceAic}`).then(r => r.data),

  // === SUPERVISIONE RAGGRUPPATA PER PATTERN (v8.0) ===

  // Supervisioni raggruppate per pattern
  getPendingGrouped: () => api.get('/supervisione/pending/grouped').then(r => r.data),

  // Approvazione bulk per pattern
  approvaBulk: (patternSignature, operatore, note = null) =>
    api.post(`/supervisione/pattern/${encodeURIComponent(patternSignature)}/approva-bulk`, { operatore, note }).then(r => r.data),

  // Rifiuto bulk per pattern
  rifiutaBulk: (patternSignature, operatore, note) =>
    api.post(`/supervisione/pattern/${encodeURIComponent(patternSignature)}/rifiuta-bulk`, { operatore, note }).then(r => r.data),

  // === SUPERVISIONE LOOKUP (v8.0) ===

  // Dettaglio supervisione lookup con suggerimenti farmacie
  getLookupDetail: (id) => api.get(`/supervisione/lookup/${id}`).then(r => r.data),

  // Risolvi supervisione lookup (assegna farmacia)
  risolviLookup: (id, data) => api.post(`/supervisione/lookup/${id}/risolvi`, data).then(r => r.data),

  // Rifiuta supervisione lookup
  rifiutaLookup: (id, operatore, note) =>
    api.post(`/supervisione/lookup/${id}/rifiuta`, { operatore, note }).then(r => r.data),

  // === SUPERVISIONE PREZZO (v8.1) ===

  // Riapplica listino a tutte le supervisioni prezzo pending (PRICE-A01)
  riapplicaListinoBulk: (operatore) =>
    api.post(`/supervisione/prezzo/riapplica-listino?operatore=${encodeURIComponent(operatore)}`).then(r => r.data),

  // v10.0: Riapplica listino a tutte le supervisioni listino pending (LST-A01)
  riapplicaListinoLstBulk: (operatore) =>
    api.post(`/supervisione/listino/riapplica-listino?operatore=${encodeURIComponent(operatore)}`).then(r => r.data),

  // === SUPERVISIONE AIC (v9.0) ===

  // Lista supervisioni AIC pending
  getAicPending: () => api.get('/supervisione/aic/pending').then(r => r.data),

  // Dettaglio supervisione AIC con suggerimenti
  getAicDetail: (id) => api.get(`/supervisione/aic/${id}`).then(r => r.data),

  // Risolvi supervisione AIC (assegna codice AIC)
  risolviAic: (id, operatore, codiceAic, note = null) =>
    api.post(`/supervisione/aic/${id}/risolvi`, { operatore, codice_aic: codiceAic, note }).then(r => r.data),

  // Rifiuta supervisione AIC
  rifiutaAic: (id, operatore, note) =>
    api.post(`/supervisione/aic/${id}/rifiuta`, { operatore, note }).then(r => r.data),

  // Cerca suggerimenti AIC per descrizione
  searchAic: (descrizione, vendor = null) => {
    const params = new URLSearchParams({ descrizione })
    if (vendor) params.append('vendor', vendor)
    return api.get(`/supervisione/aic/search-aic?${params}`).then(r => r.data)
  },

  // Statistiche AIC
  getAicStats: () => api.get('/supervisione/aic/stats').then(r => r.data),

  // Approvazione bulk pattern AIC con codice AIC
  approvaBulkAic: (patternSignature, operatore, codiceAic, note = null) =>
    api.post(`/supervisione/aic/pattern/${encodeURIComponent(patternSignature)}/approva-bulk`, {
      operatore,
      codice_aic: codiceAic,
      note
    }).then(r => r.data),
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
// LISTINI API (v6.2 - Prezzi vendor)
// =============================================================================
export const listiniApi = {
  // Statistiche listini caricati
  getStats: () => api.get('/listini/stats').then(r => r.data),

  // Import listino CSV per vendor
  importListino: (file, vendor, onProgress) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post(`/listini/import?vendor=${encodeURIComponent(vendor)}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: e => onProgress?.(Math.round((e.loaded * 100) / e.total))
    }).then(r => r.data)
  },

  // Elimina listino di un vendor
  deleteListino: (vendor) => api.delete(`/listini/${encodeURIComponent(vendor)}`).then(r => r.data),
}

// =============================================================================
// MAIL MONITOR API (v6.2)
// =============================================================================
export const mailApi = {
  // Stato e configurazione Mail Monitor
  getStatus: () => api.get('/mail/status').then(r => r.data),

  // Avvia sincronizzazione manuale
  sync: () => api.post('/mail/sync').then(r => r.data),

  // Lista email scaricate (con paginazione e filtri)
  getEmails: (params = {}) => {
    const searchParams = new URLSearchParams()
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') searchParams.append(k, String(v))
    })
    return api.get(`/mail/emails?${searchParams}`).then(r => r.data)
  },

  // Dettaglio singola email
  getEmail: (id) => api.get(`/mail/emails/${id}`).then(r => r.data),

  // Ritenta elaborazione email in errore
  retryEmail: (id) => api.post(`/mail/emails/${id}/retry`).then(r => r.data),

  // Statistiche dettagliate
  getStats: () => api.get('/mail/stats').then(r => r.data),
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

// =============================================================================
// BACKUP API (v9.0 - Sistema backup modulare)
// =============================================================================
export const backupApi = {
  // === MODULI ===

  // Lista moduli backup disponibili
  getModules: () => api.get('/backup/modules').then(r => r.data),

  // Dettaglio singolo modulo
  getModule: (name) => api.get(`/backup/modules/${name}`).then(r => r.data),

  // Stato corrente modulo (health check)
  getModuleStatus: (name) => api.get(`/backup/modules/${name}/status`).then(r => r.data),

  // Configura modulo (richiede admin)
  configureModule: (name, config) =>
    api.post(`/backup/modules/${name}/configure`, { config }).then(r => r.data),

  // Abilita modulo (richiede admin)
  enableModule: (name) => api.post(`/backup/modules/${name}/enable`).then(r => r.data),

  // Disabilita modulo (richiede admin)
  disableModule: (name) => api.post(`/backup/modules/${name}/disable`).then(r => r.data),

  // Testa modulo (richiede admin)
  testModule: (name) => api.post(`/backup/modules/${name}/test`).then(r => r.data),

  // === ESECUZIONE ===

  // Esegue backup per modulo (richiede admin)
  executeBackup: (name, triggeredBy = 'manual') =>
    api.post(`/backup/modules/${name}/execute`, { triggered_by: triggeredBy }).then(r => r.data),

  // Cleanup backup vecchi per modulo (richiede admin)
  cleanupModule: (name, retentionDays = null) =>
    api.post(`/backup/modules/${name}/cleanup`, { retention_days: retentionDays }).then(r => r.data),

  // === DASHBOARD E STORICO ===

  // Dashboard statistiche backup
  getDashboard: () => api.get('/backup/dashboard').then(r => r.data),

  // Storico backup eseguiti
  getHistory: (params = {}) => {
    const searchParams = new URLSearchParams()
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') searchParams.append(k, String(v))
    })
    return api.get(`/backup/history?${searchParams}`).then(r => r.data)
  },

  // === STORAGE ===

  // Lista storage locations
  getStorageLocations: () => api.get('/backup/storage').then(r => r.data),

  // Aggiungi storage location (richiede admin)
  addStorageLocation: (data) => api.post('/backup/storage', data).then(r => r.data),
}

// =============================================================================
// EMAIL CONFIG API (v8.1 - Configurazione email unificata)
// =============================================================================
export const emailApi = {
  // Configurazione completa (senza password, solo flag se configurate)
  getConfig: () => api.get('/email/config').then(r => r.data),

  // Salva configurazione (no password - quelle vanno in .env)
  saveConfig: (data) => api.put('/email/config', data).then(r => r.data),

  // Configurazione solo IMAP
  getImapConfig: () => api.get('/email/config/imap').then(r => r.data),

  // Configurazione solo SMTP
  getSmtpConfig: () => api.get('/email/config/smtp').then(r => r.data),

  // Test connessione IMAP
  testImap: () => api.post('/email/test/imap').then(r => r.data),

  // Test connessione SMTP (opzionalmente invia email test)
  testSmtp: (destinatario = null) =>
    api.post('/email/test/smtp', destinatario ? { destinatario } : {}).then(r => r.data),

  // Log email inviate
  getLog: (params = {}) => {
    const searchParams = new URLSearchParams()
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') searchParams.append(k, String(v))
    })
    return api.get(`/email/log?${searchParams}`).then(r => r.data)
  },

  // Ritenta invio email fallita
  retryEmail: (logId) => api.post(`/email/log/${logId}/retry`).then(r => r.data),
}

// =============================================================================
// CRM API (v8.1 - Sistema Ticketing)
// =============================================================================
export const crmApi = {
  // === TICKETS ===

  // Lista ticket (admin vede tutti, user solo propri)
  getTickets: (filters = {}) => {
    const params = new URLSearchParams()
    Object.entries(filters).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') params.append(k, String(v))
    })
    return api.get(`/crm/tickets?${params}`).then(r => r.data)
  },

  // Crea nuovo ticket
  createTicket: (data) => api.post('/crm/tickets', data).then(r => r.data),

  // Dettaglio ticket con messaggi
  getTicket: (id) => api.get(`/crm/tickets/${id}`).then(r => r.data),

  // Aggiorna stato ticket (solo admin)
  updateStatus: (id, stato) =>
    api.patch(`/crm/tickets/${id}/stato`, { stato }).then(r => r.data),

  // Aggiorna altri campi ticket
  updateTicket: (id, data) =>
    api.patch(`/crm/tickets/${id}`, data).then(r => r.data),

  // === MESSAGGI ===

  // Lista messaggi di un ticket
  getMessages: (ticketId) =>
    api.get(`/crm/tickets/${ticketId}/messaggi`).then(r => r.data),

  // Aggiungi messaggio a ticket
  addMessage: (ticketId, contenuto) =>
    api.post(`/crm/tickets/${ticketId}/messaggi`, { contenuto }).then(r => r.data),

  // === STATISTICHE ===

  // Statistiche ticket (admin globali, user propri)
  getStats: () => api.get('/crm/stats').then(r => r.data),

  // Costanti per UI (stati, categorie, priorita)
  getConstants: () => api.get('/crm/constants').then(r => r.data),

  // === ALLEGATI ===

  // Upload allegato
  uploadAttachment: (ticketId, file) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post(`/crm/tickets/${ticketId}/allegati`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    }).then(r => r.data)
  },

  // Lista allegati ticket
  getAttachments: (ticketId) =>
    api.get(`/crm/tickets/${ticketId}/allegati`).then(r => r.data),

  // Download allegato (ritorna URL)
  getAttachmentUrl: (allegatoId) =>
    `${api.defaults.baseURL}/crm/allegati/${allegatoId}/download`,

  // Elimina allegato
  deleteAttachment: (allegatoId) =>
    api.delete(`/crm/allegati/${allegatoId}`).then(r => r.data),
}

// =============================================================================
// REPORT API (v8.1 - Esportazione dati con filtri a cascata)
// =============================================================================
export const reportApi = {
  // Helper per costruire params con filtri
  _buildParams: (filters = {}) => {
    const params = new URLSearchParams()
    Object.entries(filters).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') params.append(k, String(v))
    })
    return params
  },

  // Dati report consolidato con filtri
  getData: (filters = {}) => {
    const params = reportApi._buildParams(filters)
    return api.get(`/report/export/data?${params}`).then(r => r.data)
  },

  // URL download Excel (blob response)
  downloadExcel: (filters = {}) => {
    const params = reportApi._buildParams(filters)
    return api.get(`/report/export/excel?${params}`, {
      responseType: 'blob'
    }).then(r => {
      // Crea URL blob e triggera download
      const url = window.URL.createObjectURL(new Blob([r.data]))
      const link = document.createElement('a')
      link.href = url
      // Estrai nome file dall'header o usa default
      const contentDisposition = r.headers['content-disposition']
      let filename = 'report_ordini.xlsx'
      if (contentDisposition) {
        const match = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/)
        if (match && match[1]) filename = match[1].replace(/['"]/g, '')
      }
      link.setAttribute('download', filename)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
      return { success: true, filename }
    })
  },

  // Lista vendor disponibili (con filtri a cascata)
  getVendors: (cascadeFilters = {}) => {
    const params = reportApi._buildParams(cascadeFilters)
    return api.get(`/report/filters/vendors?${params}`).then(r => r.data)
  },

  // Lista depositi disponibili (con filtri a cascata)
  getDepositi: (cascadeFilters = {}) => {
    const params = reportApi._buildParams(cascadeFilters)
    return api.get(`/report/filters/depositi?${params}`).then(r => r.data)
  },

  // Lista stati ordine disponibili (con filtri a cascata)
  getStati: (cascadeFilters = {}) => {
    const params = reportApi._buildParams(cascadeFilters)
    return api.get(`/report/filters/stati?${params}`).then(r => r.data)
  },

  // Ricerca clienti (con filtri a cascata)
  searchClienti: (q = null, limit = 50, cascadeFilters = {}) => {
    const params = reportApi._buildParams(cascadeFilters)
    if (q) params.append('q', q)
    params.append('limit', String(limit))
    return api.get(`/report/filters/clienti?${params}`).then(r => r.data)
  },

  // Ricerca prodotti per AIC o descrizione (con filtri a cascata)
  searchProdotti: (q = null, limit = 100, cascadeFilters = {}) => {
    const params = reportApi._buildParams(cascadeFilters)
    if (q) params.append('q', q)
    params.append('limit', String(limit))
    return api.get(`/report/filters/prodotti?${params}`).then(r => r.data)
  },
}

// =============================================================================
// PERMESSI API (v10.0 - Gestione matrice permessi)
// =============================================================================
export const permessiApi = {
  // Lista sezioni applicazione
  getSezioni: () => api.get('/permessi/sezioni').then(r => r.data),

  // Lista ruoli disponibili
  getRuoli: () => api.get('/permessi/ruoli').then(r => r.data),

  // Matrice completa permessi (solo admin)
  getMatrice: () => api.get('/permessi/matrice').then(r => r.data),

  // Permessi per ruolo specifico
  getPermessiRuolo: (ruolo) => api.get(`/permessi/ruolo/${ruolo}`).then(r => r.data),

  // Aggiorna singolo permesso
  updatePermesso: (ruolo, sezione, canView, canEdit) =>
    api.put(`/permessi/ruolo/${ruolo}/sezione/${sezione}`, {
      can_view: canView,
      can_edit: canEdit
    }).then(r => r.data),

  // Aggiorna tutti i permessi di un ruolo
  updatePermessiRuoloBulk: (ruolo, permessi) =>
    api.put(`/permessi/ruolo/${ruolo}/bulk`, permessi).then(r => r.data),

  // I miei permessi (utente corrente)
  getMyPermissions: () => api.get('/permessi/me').then(r => r.data),

  // Sezioni visibili per utente corrente
  getSezioniVisibili: () => api.get('/permessi/sezioni-visibili').then(r => r.data),
}

export default api