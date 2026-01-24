-- =============================================================================
-- SERV.O v9.1 - SUPERVISIONE AIC MIGRATION (Quick)
-- =============================================================================
-- Esegui con: psql -h 127.0.0.1 -U servo_user -d servo -f run_aic_migration.sql
-- Oppure copia/incolla nel client PostgreSQL
-- =============================================================================

-- 1. Crea tabella supervisione_aic (senza FK su anomalie per evitare blocchi)
CREATE TABLE IF NOT EXISTS supervisione_aic (
    id_supervisione SERIAL PRIMARY KEY,
    id_testata INTEGER NOT NULL REFERENCES ordini_testata(id_testata) ON DELETE CASCADE,
    id_anomalia INTEGER,
    id_dettaglio INTEGER,
    codice_anomalia TEXT NOT NULL DEFAULT 'AIC-A01',
    vendor TEXT NOT NULL,
    n_riga INTEGER,
    descrizione_prodotto TEXT,
    descrizione_normalizzata TEXT,
    codice_originale TEXT,
    pattern_signature TEXT,
    stato TEXT DEFAULT 'PENDING' CHECK (stato IN ('PENDING', 'APPROVED', 'REJECTED')),
    operatore TEXT,
    timestamp_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    timestamp_decisione TIMESTAMP,
    note TEXT,
    codice_aic_assegnato TEXT
);

-- 2. Indexes
CREATE INDEX IF NOT EXISTS idx_sup_aic_testata ON supervisione_aic(id_testata);
CREATE INDEX IF NOT EXISTS idx_sup_aic_stato ON supervisione_aic(stato);
CREATE INDEX IF NOT EXISTS idx_sup_aic_pattern ON supervisione_aic(pattern_signature);
CREATE INDEX IF NOT EXISTS idx_sup_aic_vendor_desc ON supervisione_aic(vendor, descrizione_normalizzata);

-- 3. Colonna per AIC manuale su dettaglio
ALTER TABLE ordini_dettaglio ADD COLUMN IF NOT EXISTS codice_aic_inserito TEXT;

-- Done
SELECT 'Migration supervisione_aic completata!' AS status;
