-- =============================================================================
-- SERV.O v8.1 - SUPERVISION PREZZO
-- =============================================================================
-- Migration per tabella supervisione_prezzo
-- Gestisce anomalie PRICE-A01: prodotti in vendita senza prezzo
-- =============================================================================

-- Tabella supervisione prezzo
CREATE TABLE IF NOT EXISTS supervisione_prezzo (
    id_supervisione SERIAL PRIMARY KEY,
    id_testata INTEGER REFERENCES ordini_testata(id_testata) ON DELETE CASCADE,
    id_anomalia INTEGER REFERENCES anomalie(id_anomalia) ON DELETE SET NULL,
    codice_anomalia VARCHAR(20) DEFAULT 'PRICE-A01',
    vendor VARCHAR(50),
    numero_ordine VARCHAR(50),
    numero_righe_coinvolte INTEGER DEFAULT 0,
    righe_dettaglio_json JSONB,  -- Lista righe senza prezzo con dettagli
    stato VARCHAR(20) DEFAULT 'PENDING' CHECK (stato IN ('PENDING', 'APPROVED', 'REJECTED', 'MODIFIED')),
    operatore VARCHAR(100),
    timestamp_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    timestamp_decisione TIMESTAMP,
    note TEXT,
    azione_correttiva VARCHAR(50) CHECK (azione_correttiva IN ('PREZZO_INSERITO', 'LISTINO_APPLICATO', 'ACCETTATO_SENZA_PREZZO', 'RIGHE_RIMOSSE'))
);

-- Indici per performance
CREATE INDEX IF NOT EXISTS idx_sup_prezzo_testata ON supervisione_prezzo(id_testata);
CREATE INDEX IF NOT EXISTS idx_sup_prezzo_stato ON supervisione_prezzo(stato);
CREATE INDEX IF NOT EXISTS idx_sup_prezzo_vendor ON supervisione_prezzo(vendor);

-- Commenti
COMMENT ON TABLE supervisione_prezzo IS 'Supervisione per anomalie PRICE-A01: prodotti in vendita senza prezzo';
COMMENT ON COLUMN supervisione_prezzo.righe_dettaglio_json IS 'JSON array con: id_dettaglio, n_riga, codice_aic, descrizione, q_venduta';
COMMENT ON COLUMN supervisione_prezzo.azione_correttiva IS 'Azione presa: PREZZO_INSERITO, LISTINO_APPLICATO, ACCETTATO_SENZA_PREZZO, RIGHE_RIMOSSE';
