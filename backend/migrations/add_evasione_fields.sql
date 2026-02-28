-- =============================================================================
-- MIGRAZIONE: Aggiunta campi evasione a esportazioni_dettaglio
-- =============================================================================
-- Data evasione (bolla) e numero bolla per ogni esportazione
-- =============================================================================

ALTER TABLE esportazioni_dettaglio
  ADD COLUMN IF NOT EXISTS data_evasione DATE,
  ADD COLUMN IF NOT EXISTS numero_bolla VARCHAR(50),
  ADD COLUMN IF NOT EXISTS operatore_evasione VARCHAR(100),
  ADD COLUMN IF NOT EXISTS data_registrazione_evasione TIMESTAMP;
