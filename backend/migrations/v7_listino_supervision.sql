-- =============================================================================
-- SERV.O v7.0 - MIGRAZIONE SUPERVISIONE LISTINO
-- =============================================================================
-- Eseguire su PostgreSQL per aggiungere supporto supervisione listino
-- =============================================================================

-- Tabella supervisione listino - per anomalie LST-A01, LST-A02
CREATE TABLE IF NOT EXISTS supervisione_listino (
    id_supervisione SERIAL PRIMARY KEY,
    id_testata INTEGER NOT NULL REFERENCES ordini_testata(id_testata) ON DELETE CASCADE,
    id_anomalia INTEGER REFERENCES anomalie(id_anomalia) ON DELETE SET NULL,
    codice_anomalia TEXT NOT NULL,
    -- Dati listino
    vendor TEXT NOT NULL,
    codice_aic TEXT,
    n_riga INTEGER,
    descrizione_prodotto TEXT,
    -- Pattern ML
    pattern_signature TEXT,
    stato TEXT DEFAULT 'PENDING',
    operatore TEXT,
    timestamp_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    timestamp_decisione TIMESTAMP,
    note TEXT,
    -- Dati proposti per validazione
    prezzo_proposto NUMERIC(10,2),
    sconto_1_proposto NUMERIC(5,2),
    sconto_2_proposto NUMERIC(5,2)
);

CREATE INDEX IF NOT EXISTS idx_sup_listino_testata ON supervisione_listino(id_testata);
CREATE INDEX IF NOT EXISTS idx_sup_listino_stato ON supervisione_listino(stato);
CREATE INDEX IF NOT EXISTS idx_sup_listino_vendor ON supervisione_listino(vendor);

-- Tabella criteri ordinari listino - per ML pattern learning
CREATE TABLE IF NOT EXISTS criteri_ordinari_listino (
    pattern_signature TEXT PRIMARY KEY,
    pattern_descrizione TEXT,
    vendor TEXT NOT NULL,
    codice_anomalia TEXT NOT NULL,
    codice_aic TEXT,
    count_approvazioni INTEGER DEFAULT 0,
    is_ordinario BOOLEAN DEFAULT FALSE,
    data_prima_occorrenza TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_promozione TIMESTAMP,
    operatori_approvatori TEXT
);

-- Vista supervisione listino pending
CREATE OR REPLACE VIEW v_supervisione_listino_pending AS
SELECT
    sl.id_supervisione,
    sl.id_testata,
    sl.codice_anomalia,
    sl.vendor,
    sl.codice_aic,
    sl.n_riga,
    sl.descrizione_prodotto,
    sl.pattern_signature,
    sl.stato,
    sl.timestamp_creazione,
    sl.prezzo_proposto,
    ot.numero_ordine_vendor AS numero_ordine,
    ot.ragione_sociale_1 AS ragione_sociale,
    ot.citta,
    a.nome_file_originale AS pdf_file,
    COALESCE(col.count_approvazioni, 0) AS count_pattern,
    COALESCE(col.is_ordinario, FALSE) AS pattern_ordinario
FROM supervisione_listino sl
JOIN ordini_testata ot ON sl.id_testata = ot.id_testata
JOIN acquisizioni a ON ot.id_acquisizione = a.id_acquisizione
LEFT JOIN criteri_ordinari_listino col ON sl.pattern_signature = col.pattern_signature
WHERE sl.stato = 'PENDING'
ORDER BY sl.timestamp_creazione DESC;

-- Tabella LISTINI_VENDOR per prezzi CODIFI
CREATE TABLE IF NOT EXISTS listini_vendor (
    id_listino SERIAL PRIMARY KEY,
    vendor TEXT NOT NULL,
    codice_aic TEXT NOT NULL,
    descrizione TEXT,
    -- Sconti TO_D (Discount1-4)
    sconto_1 NUMERIC(5,2),
    sconto_2 NUMERIC(5,2),
    sconto_3 NUMERIC(5,2),
    sconto_4 NUMERIC(5,2),
    -- Prezzi TO_D
    prezzo_netto NUMERIC(10,2),
    prezzo_scontare NUMERIC(10,2),
    prezzo_pubblico NUMERIC(10,2),
    -- IVA TO_D
    aliquota_iva NUMERIC(5,2),
    scorporo_iva TEXT DEFAULT 'S',
    -- Campi import CSV
    prezzo_csv_originale NUMERIC(10,2),
    prezzo_pubblico_csv NUMERIC(10,2),
    data_decorrenza DATE,
    -- Metadata
    attivo BOOLEAN DEFAULT TRUE,
    data_import TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fonte_file TEXT,
    UNIQUE(vendor, codice_aic)
);

CREATE INDEX IF NOT EXISTS idx_listini_vendor ON listini_vendor(vendor);
CREATE INDEX IF NOT EXISTS idx_listini_aic ON listini_vendor(codice_aic);
CREATE INDEX IF NOT EXISTS idx_listini_vendor_aic ON listini_vendor(vendor, codice_aic);

-- Verifica creazione
SELECT 'Tabelle create:' AS info;
SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename IN ('supervisione_listino', 'criteri_ordinari_listino', 'listini_vendor');
