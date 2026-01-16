-- =============================================================================
-- MIGRATION 002: Aggiunta colonna q_da_evadere per evasioni parziali
-- =============================================================================
-- Data: 2026-01-08
-- Descrizione: Separa la logica di evasione:
--   - q_evaso: totale cumulativo già esportato in tracciati
--   - q_da_evadere: quantità da esportare nel PROSSIMO tracciato (editabile)
--   - q_residuo: rimanente da evadere in futuro
--
-- Flusso:
--   1. Utente imposta q_da_evadere (es. 50 su 200 ordinati)
--   2. Genera tracciato -> usa q_da_evadere
--   3. Post-tracciato: q_evaso += q_da_evadere, q_da_evadere = 0
--   4. q_residuo = q_totale - q_evaso
-- =============================================================================

-- Aggiungi colonna q_da_evadere
ALTER TABLE ordini_dettaglio ADD COLUMN IF NOT EXISTS q_da_evadere INTEGER DEFAULT 0;

-- Commento descrittivo
COMMENT ON COLUMN ordini_dettaglio.q_da_evadere IS 'Quantita da evadere nel prossimo tracciato (editabile)';

-- =============================================================================
-- FINE MIGRATION
-- =============================================================================
