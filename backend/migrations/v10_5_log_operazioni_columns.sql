-- =============================================================================
-- SERV.O v10.5 - Log Operazioni Extended Columns
-- =============================================================================
-- Aggiunge colonne per tracking login/auth attempts
-- =============================================================================

ALTER TABLE log_operazioni ADD COLUMN IF NOT EXISTS success BOOLEAN DEFAULT TRUE;
ALTER TABLE log_operazioni ADD COLUMN IF NOT EXISTS error_message TEXT;
ALTER TABLE log_operazioni ADD COLUMN IF NOT EXISTS ip_address VARCHAR(45);
ALTER TABLE log_operazioni ADD COLUMN IF NOT EXISTS user_agent TEXT;

-- Indice per query su tentativi falliti
CREATE INDEX IF NOT EXISTS idx_log_operazioni_success ON log_operazioni(success) WHERE success = FALSE;
