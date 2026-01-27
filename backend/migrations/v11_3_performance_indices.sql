-- =============================================================================
-- SERV.O v11.3 - Performance Indices
-- =============================================================================
-- Indici per migliorare le performance delle query più frequenti
-- =============================================================================

-- Indici su ordini_dettaglio
CREATE INDEX IF NOT EXISTS idx_ordini_dettaglio_id_testata
    ON ordini_dettaglio(id_testata);

CREATE INDEX IF NOT EXISTS idx_ordini_dettaglio_stato_riga
    ON ordini_dettaglio(stato_riga);

CREATE INDEX IF NOT EXISTS idx_ordini_dettaglio_testata_stato
    ON ordini_dettaglio(id_testata, stato_riga);

-- Indici su anomalie
CREATE INDEX IF NOT EXISTS idx_anomalie_id_testata
    ON anomalie(id_testata);

CREATE INDEX IF NOT EXISTS idx_anomalie_stato
    ON anomalie(stato);

CREATE INDEX IF NOT EXISTS idx_anomalie_testata_stato
    ON anomalie(id_testata, stato);

-- Indici su ordini_testata
CREATE INDEX IF NOT EXISTS idx_ordini_testata_stato
    ON ordini_testata(stato);

CREATE INDEX IF NOT EXISTS idx_ordini_testata_id_vendor
    ON ordini_testata(id_vendor);

CREATE INDEX IF NOT EXISTS idx_ordini_testata_data_ordine
    ON ordini_testata(data_ordine);

-- Indici su anagrafica_farmacie per lookup
CREATE INDEX IF NOT EXISTS idx_anagrafica_farmacie_partita_iva
    ON anagrafica_farmacie(partita_iva);

CREATE INDEX IF NOT EXISTS idx_anagrafica_farmacie_attiva
    ON anagrafica_farmacie(attiva) WHERE attiva = TRUE;

-- Indici su anagrafica_parafarmacie
CREATE INDEX IF NOT EXISTS idx_anagrafica_parafarmacie_partita_iva
    ON anagrafica_parafarmacie(partita_iva);

CREATE INDEX IF NOT EXISTS idx_anagrafica_parafarmacie_attiva
    ON anagrafica_parafarmacie(attiva) WHERE attiva = TRUE;

-- Analyze delle tabelle per aggiornare le statistiche
ANALYZE ordini_dettaglio;
ANALYZE ordini_testata;
ANALYZE anomalie;
ANALYZE anagrafica_farmacie;
ANALYZE anagrafica_parafarmacie;
