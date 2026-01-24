// =============================================================================
// ORDINI API
// =============================================================================
// v11.0: TIER 3.2 - Usa buildQueryParams centralizzato
// =============================================================================

import api from './client';
import { buildQueryParams } from '../hooks/utils';

export const ordiniApi = {
  // Query base
  getList: (filters = {}) => {
    const params = buildQueryParams(filters);
    return api.get(`/ordini?${params}`).then(r => r.data);
  },

  getDetail: (id) => api.get(`/ordini/${id}`).then(r => r.data),
  getRighe: (id) => api.get(`/ordini/${id}/righe`).then(r => r.data),
  getRigheAll: (id) => api.get(`/ordini/${id}/righe?include_children=true`).then(r => r.data),
  updateStato: (id, stato) => api.put(`/ordini/${id}/stato?nuovo_stato=${stato}`).then(r => r.data),
  delete: (id) => api.delete(`/ordini/${id}`).then(r => r.data),
  batchUpdateStato: (ids, stato) => api.post('/ordini/batch/stato', { ids, nuovo_stato: stato }).then(r => r.data),
  batchDelete: (ids) => api.delete('/ordini/batch', { data: { ids } }).then(r => r.data),
  getStati: () => api.get('/ordini/stati').then(r => r.data),
  getLookupMethods: () => api.get('/ordini/lookup-methods').then(r => r.data),

  // Conferma righe
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

  // Valida e genera tracciato
  validaEGeneraTracciato: (idTestata, operatore, validazioneMassiva = false) =>
    api.post(`/ordini/${idTestata}/valida`, { operatore, validazione_massiva: validazioneMassiva }).then(r => r.data),

  // Evasioni parziali
  registraEvasione: (idTestata, idDettaglio, qDaEvadere, operatore) =>
    api.post(`/ordini/${idTestata}/righe/${idDettaglio}/evasione`, {
      q_da_evadere: qDaEvadere,
      operatore
    }).then(r => r.data),

  // Archiviazione
  archiviaOrdine: (idTestata, operatore = "admin") =>
    api.post(`/ordini/${idTestata}/archivia?operatore=${encodeURIComponent(operatore)}`).then(r => r.data),

  archiviaRiga: (idTestata, idDettaglio, operatore = "admin") =>
    api.post(`/ordini/${idTestata}/righe/${idDettaglio}/archivia?operatore=${encodeURIComponent(operatore)}`).then(r => r.data),

  // Ripristino
  ripristinaRiga: (idTestata, idDettaglio, operatore) =>
    api.post(`/ordini/${idTestata}/righe/${idDettaglio}/ripristina`, { operatore }).then(r => r.data),

  ripristinaTutto: (idTestata, operatore) =>
    api.post(`/ordini/${idTestata}/ripristina-tutto`, { operatore }).then(r => r.data),

  // Fix Espositore - Correzione relazioni parent/child
  fixEspositore: (idTestata, righe, operatore, note = null) =>
    api.put(`/ordini/${idTestata}/fix-espositore`, {
      righe,
      operatore,
      note
    }).then(r => r.data),

  // Download PDF come ZIP
  downloadPdfZip: async (ids) => {
    const response = await api.post('/ordini/batch/download-pdf', { ids }, {
      responseType: 'blob'
    });

    // Crea link per download
    const blob = new Blob([response.data], { type: 'application/zip' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;

    // Estrai filename dall'header o usa default
    const contentDisposition = response.headers['content-disposition'];
    let filename = 'ordini_pdf.zip';
    if (contentDisposition) {
      const match = contentDisposition.match(/filename=(.+)/);
      if (match) filename = match[1];
    }

    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);

    return {
      success: true,
      filesAdded: parseInt(response.headers['x-files-added'] || '0'),
      filesMissing: parseInt(response.headers['x-files-missing'] || '0')
    };
  },
};
