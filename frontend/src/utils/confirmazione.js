// =============================================================================
// SERV.O v8.1 - UTILITY CONFERMA OPERAZIONI
// =============================================================================
// Standardizzazione conferme per operazioni critiche
// =============================================================================

/**
 * Parola chiave di conferma standard (case-insensitive)
 */
export const PAROLA_CONFERMA = 'CONFERMA';

/**
 * Messaggio standard per richiesta conferma
 */
export const MESSAGGIO_CONFERMA = 'Valuta se vuoi procedere. Se si, scrivi CONFERMA';

/**
 * Richiede conferma per operazione critica con digitazione testo.
 *
 * @param {string} descrizioneOperazione - Descrizione dell'operazione (es. "Reset database")
 * @param {string} dettagli - Dettagli aggiuntivi opzionali
 * @returns {boolean} true se l'utente ha confermato correttamente
 *
 * @example
 * if (richiestaConferma('Reset completo database')) {
 *   // procedi con l'operazione
 * }
 */
export function richiestaConferma(descrizioneOperazione, dettagli = '') {
  const messaggioCompleto = dettagli
    ? `${descrizioneOperazione}\n\n${dettagli}\n\n${MESSAGGIO_CONFERMA}`
    : `${descrizioneOperazione}\n\n${MESSAGGIO_CONFERMA}`;

  const input = window.prompt(messaggioCompleto);

  if (input === null) {
    // Utente ha premuto Annulla
    return false;
  }

  return input.trim().toUpperCase() === PAROLA_CONFERMA.toUpperCase();
}

/**
 * Richiede conferma semplice (OK/Annulla) per operazioni meno critiche.
 *
 * @param {string} messaggio - Messaggio da mostrare
 * @returns {boolean} true se l'utente ha confermato
 */
export function richiestaConfermaSemplice(messaggio) {
  return window.confirm(messaggio);
}

/**
 * Richiede input testuale con validazione.
 *
 * @param {string} messaggio - Messaggio/domanda da mostrare
 * @param {Object} options - Opzioni di validazione
 * @param {boolean} options.required - Se true, non accetta stringa vuota
 * @param {number} options.minLength - Lunghezza minima
 * @returns {string|null} Testo inserito o null se annullato/invalido
 */
export function richiestaInput(messaggio, options = {}) {
  const { required = true, minLength = 1 } = options;

  const input = window.prompt(messaggio);

  if (input === null) {
    return null;
  }

  const trimmed = input.trim();

  if (required && trimmed.length < minLength) {
    return null;
  }

  return trimmed;
}

export default {
  PAROLA_CONFERMA,
  MESSAGGIO_CONFERMA,
  richiestaConferma,
  richiestaConfermaSemplice,
  richiestaInput,
};
