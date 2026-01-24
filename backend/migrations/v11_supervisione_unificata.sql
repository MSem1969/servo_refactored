-- =============================================================================
-- SERV.O v11.0 - MIGRAZIONE SUPERVISIONE UNIFICATA
-- =============================================================================
-- Unifica le 5 tabelle supervisione_* in una sola tabella
-- con campo tipo_supervisione e payload JSONB per dati specifici
--
-- TABELLE DA MIGRARE:
-- - supervisione_aic
-- - supervisione_espositore
-- - supervisione_listino
-- - supervisione_lookup
-- - supervisione_prezzo
-- =============================================================================

-- ============================================================================
-- STEP 1: CREAZIONE NUOVA TABELLA UNIFICATA
-- ============================================================================

CREATE TABLE IF NOT EXISTS supervisione_unificata (
    id_supervisione SERIAL PRIMARY KEY,
    tipo_supervisione VARCHAR(20) NOT NULL
        CHECK (tipo_supervisione IN ('AIC', 'LISTINO', 'PREZZO', 'LOOKUP', 'ESPOSITORE')),

    -- Foreign Keys comuni
    id_testata INTEGER NOT NULL REFERENCES ordini_testata(id_testata) ON DELETE CASCADE,
    id_anomalia INTEGER REFERENCES anomalie(id_anomalia) ON DELETE SET NULL,
    id_dettaglio INTEGER REFERENCES ordini_dettaglio(id_dettaglio) ON DELETE SET NULL,

    -- Campi comuni
    codice_anomalia VARCHAR(20),
    vendor VARCHAR(50),
    pattern_signature TEXT,

    -- Stato e workflow
    stato VARCHAR(20) DEFAULT 'PENDING'
        CHECK (stato IN ('PENDING', 'APPROVED', 'REJECTED', 'MODIFIED')),
    operatore VARCHAR(100),
    timestamp_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    timestamp_decisione TIMESTAMP,
    note TEXT,

    -- Dati specifici per tipo (JSONB per flessibilità)
    -- AIC: {n_riga, descrizione_prodotto, descrizione_normalizzata, codice_originale, codice_aic_assegnato}
    -- ESPOSITORE: {codice_espositore, descrizione_espositore, pezzi_attesi, pezzi_trovati, valore_calcolato, modifiche_manuali_json}
    -- LISTINO: {codice_aic, n_riga, descrizione_prodotto, prezzo_estratto, prezzo_listino, prezzo_proposto, azione}
    -- LOOKUP: {partita_iva_estratta, lookup_method, lookup_score, min_id_assegnato, id_farmacia_assegnata, id_parafarmacia_assegnata}
    -- PREZZO: {numero_righe_coinvolte}
    payload JSONB DEFAULT '{}'
);

COMMENT ON TABLE supervisione_unificata IS 'Tabella unificata per tutte le supervisioni (v11.0)';
COMMENT ON COLUMN supervisione_unificata.tipo_supervisione IS 'Tipo: AIC, LISTINO, PREZZO, LOOKUP, ESPOSITORE';
COMMENT ON COLUMN supervisione_unificata.payload IS 'Dati specifici per tipo in formato JSONB';

-- ============================================================================
-- STEP 2: INDICI OTTIMIZZATI
-- ============================================================================

-- Indice composto per query comuni (tipo + stato)
CREATE INDEX IF NOT EXISTS idx_sup_unif_tipo_stato ON supervisione_unificata(tipo_supervisione, stato);

-- Indice per ricerca per ordine
CREATE INDEX IF NOT EXISTS idx_sup_unif_testata ON supervisione_unificata(id_testata);

-- Indice per ricerca per anomalia
CREATE INDEX IF NOT EXISTS idx_sup_unif_anomalia ON supervisione_unificata(id_anomalia) WHERE id_anomalia IS NOT NULL;

-- Indice per pattern ML
CREATE INDEX IF NOT EXISTS idx_sup_unif_pattern ON supervisione_unificata(pattern_signature) WHERE pattern_signature IS NOT NULL;

-- Indice GIN per ricerca nel payload JSONB
CREATE INDEX IF NOT EXISTS idx_sup_unif_payload ON supervisione_unificata USING GIN(payload);

-- ============================================================================
-- STEP 3: MIGRAZIONE DATI DA TABELLE ESISTENTI
-- ============================================================================

-- Migrazione supervisione_aic
INSERT INTO supervisione_unificata (
    tipo_supervisione, id_testata, id_anomalia, id_dettaglio,
    codice_anomalia, vendor, pattern_signature,
    stato, operatore, timestamp_creazione, timestamp_decisione, note,
    payload
)
SELECT
    'AIC',
    id_testata,
    id_anomalia,
    id_dettaglio,
    codice_anomalia,
    vendor,
    pattern_signature,
    stato,
    operatore,
    timestamp_creazione,
    timestamp_decisione,
    note,
    jsonb_build_object(
        'n_riga', n_riga,
        'descrizione_prodotto', descrizione_prodotto,
        'descrizione_normalizzata', descrizione_normalizzata,
        'codice_originale', codice_originale,
        'codice_aic_assegnato', codice_aic_assegnato
    )
FROM supervisione_aic
ON CONFLICT DO NOTHING;

-- Migrazione supervisione_espositore
INSERT INTO supervisione_unificata (
    tipo_supervisione, id_testata, id_anomalia, id_dettaglio,
    codice_anomalia, vendor, pattern_signature,
    stato, operatore, timestamp_creazione, timestamp_decisione, note,
    payload
)
SELECT
    'ESPOSITORE',
    id_testata,
    id_anomalia,
    NULL, -- espositore non ha id_dettaglio
    codice_anomalia,
    NULL, -- espositore non ha vendor
    pattern_signature,
    stato,
    operatore,
    timestamp_creazione,
    timestamp_decisione,
    note,
    jsonb_build_object(
        'codice_espositore', codice_espositore,
        'descrizione_espositore', descrizione_espositore,
        'pezzi_attesi', pezzi_attesi,
        'pezzi_trovati', pezzi_trovati,
        'valore_calcolato', valore_calcolato,
        'modifiche_manuali_json', modifiche_manuali_json
    )
FROM supervisione_espositore
ON CONFLICT DO NOTHING;

-- Migrazione supervisione_listino
INSERT INTO supervisione_unificata (
    tipo_supervisione, id_testata, id_anomalia, id_dettaglio,
    codice_anomalia, vendor, pattern_signature,
    stato, operatore, timestamp_creazione, timestamp_decisione, note,
    payload
)
SELECT
    'LISTINO',
    id_testata,
    id_anomalia,
    id_dettaglio,
    codice_anomalia,
    vendor,
    pattern_signature,
    stato,
    operatore,
    timestamp_creazione,
    timestamp_decisione,
    note,
    jsonb_build_object(
        'codice_aic', codice_aic,
        'n_riga', n_riga,
        'descrizione_prodotto', descrizione_prodotto,
        'prezzo_estratto', prezzo_estratto,
        'prezzo_listino', prezzo_listino,
        'prezzo_proposto', prezzo_proposto,
        'azione', azione
    )
FROM supervisione_listino
ON CONFLICT DO NOTHING;

-- Migrazione supervisione_lookup
INSERT INTO supervisione_unificata (
    tipo_supervisione, id_testata, id_anomalia, id_dettaglio,
    codice_anomalia, vendor, pattern_signature,
    stato, operatore, timestamp_creazione, timestamp_decisione, note,
    payload
)
SELECT
    'LOOKUP',
    id_testata,
    id_anomalia,
    NULL, -- lookup non ha id_dettaglio
    codice_anomalia,
    vendor,
    pattern_signature,
    stato,
    operatore,
    timestamp_creazione,
    timestamp_decisione,
    note,
    jsonb_build_object(
        'partita_iva_estratta', partita_iva_estratta,
        'lookup_method', lookup_method,
        'lookup_score', lookup_score,
        'min_id_assegnato', min_id_assegnato,
        'id_farmacia_assegnata', id_farmacia_assegnata,
        'id_parafarmacia_assegnata', id_parafarmacia_assegnata
    )
FROM supervisione_lookup
ON CONFLICT DO NOTHING;

-- Migrazione supervisione_prezzo
INSERT INTO supervisione_unificata (
    tipo_supervisione, id_testata, id_anomalia, id_dettaglio,
    codice_anomalia, vendor, pattern_signature,
    stato, operatore, timestamp_creazione, timestamp_decisione, note,
    payload
)
SELECT
    'PREZZO',
    id_testata,
    id_anomalia,
    NULL, -- prezzo non ha id_dettaglio
    codice_anomalia,
    vendor,
    pattern_signature,
    stato,
    operatore,
    timestamp_creazione,
    timestamp_decisione,
    note,
    jsonb_build_object(
        'numero_righe_coinvolte', numero_righe_coinvolte
    )
FROM supervisione_prezzo
ON CONFLICT DO NOTHING;

-- ============================================================================
-- STEP 4: VISTE PER RETROCOMPATIBILITÀ
-- ============================================================================

-- Vista compatibile con supervisione_aic
CREATE OR REPLACE VIEW v_supervisione_aic_compat AS
SELECT
    id_supervisione,
    id_testata,
    id_anomalia,
    id_dettaglio,
    codice_anomalia,
    vendor,
    (payload->>'n_riga')::INTEGER AS n_riga,
    payload->>'descrizione_prodotto' AS descrizione_prodotto,
    payload->>'descrizione_normalizzata' AS descrizione_normalizzata,
    payload->>'codice_originale' AS codice_originale,
    pattern_signature,
    stato,
    operatore,
    timestamp_creazione,
    timestamp_decisione,
    note,
    payload->>'codice_aic_assegnato' AS codice_aic_assegnato
FROM supervisione_unificata
WHERE tipo_supervisione = 'AIC';

-- Vista compatibile con supervisione_espositore
CREATE OR REPLACE VIEW v_supervisione_espositore_compat AS
SELECT
    id_supervisione,
    id_testata,
    id_anomalia,
    codice_anomalia,
    payload->>'codice_espositore' AS codice_espositore,
    payload->>'descrizione_espositore' AS descrizione_espositore,
    (payload->>'pezzi_attesi')::INTEGER AS pezzi_attesi,
    (payload->>'pezzi_trovati')::INTEGER AS pezzi_trovati,
    (payload->>'valore_calcolato')::NUMERIC AS valore_calcolato,
    pattern_signature,
    stato,
    operatore,
    timestamp_creazione,
    timestamp_decisione,
    note,
    payload->'modifiche_manuali_json' AS modifiche_manuali_json
FROM supervisione_unificata
WHERE tipo_supervisione = 'ESPOSITORE';

-- Vista compatibile con supervisione_listino
CREATE OR REPLACE VIEW v_supervisione_listino_compat AS
SELECT
    id_supervisione,
    id_testata,
    id_dettaglio,
    id_anomalia,
    codice_anomalia,
    vendor,
    payload->>'codice_aic' AS codice_aic,
    (payload->>'n_riga')::INTEGER AS n_riga,
    payload->>'descrizione_prodotto' AS descrizione_prodotto,
    (payload->>'prezzo_estratto')::NUMERIC(10,2) AS prezzo_estratto,
    (payload->>'prezzo_listino')::NUMERIC(10,2) AS prezzo_listino,
    (payload->>'prezzo_proposto')::NUMERIC(10,2) AS prezzo_proposto,
    pattern_signature,
    stato,
    operatore,
    timestamp_creazione,
    timestamp_decisione,
    note,
    payload->>'azione' AS azione
FROM supervisione_unificata
WHERE tipo_supervisione = 'LISTINO';

-- Vista compatibile con supervisione_lookup
CREATE OR REPLACE VIEW v_supervisione_lookup_compat AS
SELECT
    id_supervisione,
    id_testata,
    id_anomalia,
    codice_anomalia,
    vendor,
    payload->>'partita_iva_estratta' AS partita_iva_estratta,
    payload->>'lookup_method' AS lookup_method,
    (payload->>'lookup_score')::INTEGER AS lookup_score,
    payload->>'min_id_assegnato' AS min_id_assegnato,
    (payload->>'id_farmacia_assegnata')::INTEGER AS id_farmacia_assegnata,
    (payload->>'id_parafarmacia_assegnata')::INTEGER AS id_parafarmacia_assegnata,
    pattern_signature,
    stato,
    operatore,
    timestamp_creazione,
    timestamp_decisione,
    note
FROM supervisione_unificata
WHERE tipo_supervisione = 'LOOKUP';

-- Vista compatibile con supervisione_prezzo
CREATE OR REPLACE VIEW v_supervisione_prezzo_compat AS
SELECT
    id_supervisione,
    id_testata,
    id_anomalia,
    codice_anomalia,
    vendor,
    (payload->>'numero_righe_coinvolte')::INTEGER AS numero_righe_coinvolte,
    pattern_signature,
    stato,
    operatore,
    timestamp_creazione,
    timestamp_decisione,
    note
FROM supervisione_unificata
WHERE tipo_supervisione = 'PREZZO';

-- ============================================================================
-- STEP 5: REPORT MIGRAZIONE
-- ============================================================================

DO $$
DECLARE
    cnt_aic INTEGER;
    cnt_espositore INTEGER;
    cnt_listino INTEGER;
    cnt_lookup INTEGER;
    cnt_prezzo INTEGER;
    cnt_unificata INTEGER;
BEGIN
    SELECT COUNT(*) INTO cnt_aic FROM supervisione_aic;
    SELECT COUNT(*) INTO cnt_espositore FROM supervisione_espositore;
    SELECT COUNT(*) INTO cnt_listino FROM supervisione_listino;
    SELECT COUNT(*) INTO cnt_lookup FROM supervisione_lookup;
    SELECT COUNT(*) INTO cnt_prezzo FROM supervisione_prezzo;
    SELECT COUNT(*) INTO cnt_unificata FROM supervisione_unificata;

    RAISE NOTICE '========================================';
    RAISE NOTICE 'MIGRAZIONE SUPERVISIONE UNIFICATA v11.0';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Tabelle originali:';
    RAISE NOTICE '  - supervisione_aic: % record', cnt_aic;
    RAISE NOTICE '  - supervisione_espositore: % record', cnt_espositore;
    RAISE NOTICE '  - supervisione_listino: % record', cnt_listino;
    RAISE NOTICE '  - supervisione_lookup: % record', cnt_lookup;
    RAISE NOTICE '  - supervisione_prezzo: % record', cnt_prezzo;
    RAISE NOTICE 'Tabella unificata:';
    RAISE NOTICE '  - supervisione_unificata: % record', cnt_unificata;
    RAISE NOTICE '========================================';
END;
$$;

-- ============================================================================
-- NOTE:
-- Le tabelle originali NON vengono eliminate automaticamente.
-- Dopo aver verificato che la migrazione è corretta e che l'applicazione
-- funziona con le viste di compatibilità, eseguire:
--
-- DROP TABLE supervisione_aic CASCADE;
-- DROP TABLE supervisione_espositore CASCADE;
-- DROP TABLE supervisione_listino CASCADE;
-- DROP TABLE supervisione_lookup CASCADE;
-- DROP TABLE supervisione_prezzo CASCADE;
-- ============================================================================
