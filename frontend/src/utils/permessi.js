// =============================================================================
// PERMESSI DI SEZIONE - matrice Impostazioni → Permessi (tabella permessi_ruolo)
// =============================================================================
// Unica fonte per decidere cosa un utente vede o modifica. App.jsx la popola
// al login (GET /permessi/me); i componenti la interrogano senza ricevere i
// permessi via props. Mai controllare `ruolo === 'admin'` per abilitare
// un'azione di sezione: lo decide la matrice.
// =============================================================================

let ruoloCorrente = null;
let permessiCorrenti = {};

export const setPermessiUtente = (user, permessi) => {
  ruoloCorrente = (user?.ruolo || '').toLowerCase() || null;
  permessiCorrenti = permessi || {};
};

export const resetPermessiUtente = () => setPermessiUtente(null, {});

const isAdmin = () => ruoloCorrente === 'admin';

export const puoVedere = (sezione) =>
  isAdmin() || (permessiCorrenti[sezione]?.can_view ?? false);

export const puoModificare = (sezione) =>
  isAdmin() || (permessiCorrenti[sezione]?.can_edit ?? false);

// Propagazione GLOBALE di correzioni/anomalie: azione di supervisione
export const puoPropagareGlobale = () => puoModificare('supervisione');

// Gerarchia (non e' un permesso di sezione): ruoli che gestiscono utenti e
// permessi di ruoli inferiori. Specchio di auth/permissions.get_ruoli_creabili.
const RUOLI_CON_SUBORDINATI = ['admin', 'superuser', 'supervisore'];
export const gestisceRuoliInferiori = () => RUOLI_CON_SUBORDINATI.includes(ruoloCorrente);
