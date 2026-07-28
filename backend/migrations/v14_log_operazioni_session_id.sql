-- =============================================================================
-- SERV.O v14 - log_operazioni.session_id
-- =============================================================================
-- BUG: app/auth/router.py inserisce in log_operazioni anche la colonna
-- session_id, che su PostgreSQL non e' mai stata creata. La ALTER esisteva
-- solo in app/scripts/migrate_db.py, script legacy SQLite che su PG non gira.
--
-- Effetto: OGNI log di autenticazione fallisce in silenzio. L'INSERT viene
-- catturato e si limita a stampare
--   "Warning: impossibile loggare azione auth: column session_id ... does not exist"
-- quindi l'audit dei login resta vuoto. Nessun impatto sul login in se'.
--
-- Verificato sul DB di produzione il 2026-07-28: la colonna e' ASSENTE.
--
-- Migration ADDITIVA: non tocca dati esistenti, non riscrive la tabella
-- (ADD COLUMN senza DEFAULT non comporta rewrite su PostgreSQL >= 11) e non
-- richiede fermo applicativo. Idempotente: IF NOT EXISTS.
--
-- Applicare con il ruolo applicativo, non come superuser:
--   psql -U <ruolo_app> -h <host> -d <db> -f v14_log_operazioni_session_id.sql
-- =============================================================================

BEGIN;

ALTER TABLE log_operazioni ADD COLUMN IF NOT EXISTS session_id INTEGER;

COMMIT;

-- =============================================================================
-- VERIFICA
-- =============================================================================
-- SELECT column_name FROM information_schema.columns
--  WHERE table_name='log_operazioni' AND column_name='session_id';   -- 1 riga
--
-- Dopo il primo login successivo, l'audit deve iniziare a popolarsi:
-- SELECT count(*), max(timestamp) FROM log_operazioni
--  WHERE tipo_operazione ILIKE '%LOGIN%';
