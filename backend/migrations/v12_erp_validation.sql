-- =============================================================================
-- SERV.O v12.0 - VALIDAZIONE COERENZA ERP
-- =============================================================================
-- Tabelle per validazione MIN_ID + P.IVA contro anagrafica_clienti
-- e auto-rettifica dopo 5 correzioni concordanti
-- =============================================================================

-- Supervisione ERP: traccia le correzioni operatore per mismatch ERP
CREATE TABLE IF NOT EXISTS supervisione_erp (
    id_supervisione SERIAL PRIMARY KEY,
    id_testata INTEGER REFERENCES ordini_testata(id_testata),
    id_anomalia INTEGER REFERENCES anomalie(id_anomalia),
    pattern_signature VARCHAR(16),
    min_id VARCHAR(20),
    partita_iva_tracciato VARCHAR(16),    -- P.IVA che andrebbe nel tracciato (ministeriale/estratta)
    partita_iva_erp VARCHAR(16),          -- P.IVA da anagrafica_clienti
    partita_iva_corretta VARCHAR(16),     -- P.IVA scelta dall'operatore
    min_id_corretto VARCHAR(20),          -- MIN_ID corretto (se diverso)
    stato VARCHAR(20) DEFAULT 'PENDING',  -- PENDING/APPROVED/REJECTED
    operatore VARCHAR(100),
    note TEXT,
    timestamp_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    timestamp_decisione TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_supervisione_erp_testata ON supervisione_erp(id_testata);
CREATE INDEX IF NOT EXISTS idx_supervisione_erp_anomalia ON supervisione_erp(id_anomalia);
CREATE INDEX IF NOT EXISTS idx_supervisione_erp_pattern ON supervisione_erp(pattern_signature);
CREATE INDEX IF NOT EXISTS idx_supervisione_erp_stato ON supervisione_erp(stato);

-- Criteri ordinari ERP: pattern ML per auto-correzione dopo 5 approvazioni
CREATE TABLE IF NOT EXISTS criteri_ordinari_erp (
    id_criterio SERIAL PRIMARY KEY,
    pattern_signature VARCHAR(16) UNIQUE,
    pattern_descrizione VARCHAR(200),
    min_id VARCHAR(20),
    partita_iva_corretta VARCHAR(16),      -- P.IVA da usare nei tracciati
    count_approvazioni INTEGER DEFAULT 0,
    operatori_approvatori TEXT,             -- CSV operatori
    is_ordinario BOOLEAN DEFAULT FALSE,
    data_promozione TIMESTAMP,
    data_rettifica_anagrafica TIMESTAMP,    -- quando anagrafica_clienti è stata aggiornata
    data_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_criteri_erp_pattern ON criteri_ordinari_erp(pattern_signature);
CREATE INDEX IF NOT EXISTS idx_criteri_erp_min_id ON criteri_ordinari_erp(min_id);
