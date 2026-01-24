-- =============================================================================
-- SERV.O v8.2 - TABELLA SYNC_STATE
-- =============================================================================
-- Traccia stato sincronizzazioni con fonti esterne (Ministero, etc.)
-- =============================================================================

-- Tabella stato sincronizzazione
CREATE TABLE IF NOT EXISTS sync_state (
    key VARCHAR(50) PRIMARY KEY,
    etag VARCHAR(100),
    last_modified VARCHAR(100),
    last_sync TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_url TEXT,
    records_count INTEGER DEFAULT 0,
    extra_data JSONB DEFAULT '{}'::jsonb
);

-- Indice per query frequenti
CREATE INDEX IF NOT EXISTS idx_sync_state_last_sync ON sync_state(last_sync);

-- Commenti
COMMENT ON TABLE sync_state IS 'Stato sincronizzazioni con fonti esterne';
COMMENT ON COLUMN sync_state.key IS 'Identificativo univoco sync (es: farmacie_sync, parafarmacie_sync)';
COMMENT ON COLUMN sync_state.etag IS 'ETag HTTP per conditional requests';
COMMENT ON COLUMN sync_state.last_modified IS 'Header Last-Modified dalla risposta HTTP';
COMMENT ON COLUMN sync_state.last_sync IS 'Timestamp ultima sincronizzazione';
COMMENT ON COLUMN sync_state.last_url IS 'URL utilizzato per ultima sync';
COMMENT ON COLUMN sync_state.records_count IS 'Numero record processati';
COMMENT ON COLUMN sync_state.extra_data IS 'Dati aggiuntivi (statistiche, errori, etc.)';

-- =============================================================================
-- VISTA RIEPILOGO SINCRONIZZAZIONI
-- =============================================================================

CREATE OR REPLACE VIEW v_sync_status AS
SELECT
    key,
    last_sync,
    last_url,
    records_count,
    etag,
    CASE
        WHEN last_sync IS NULL THEN 'MAI_SINCRONIZZATO'
        WHEN last_sync < CURRENT_TIMESTAMP - INTERVAL '7 days' THEN 'OBSOLETO'
        WHEN last_sync < CURRENT_TIMESTAMP - INTERVAL '1 day' THEN 'DA_AGGIORNARE'
        ELSE 'AGGIORNATO'
    END AS stato,
    EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - last_sync)) / 3600 AS ore_dalla_sync
FROM sync_state
ORDER BY last_sync DESC;

COMMENT ON VIEW v_sync_status IS 'Riepilogo stato sincronizzazioni';
