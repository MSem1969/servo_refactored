-- =============================================================================
-- SERV.O v8.0 - MIGRAZIONE SUPERVISIONE LOOKUP + RAGGRUPPAMENTO PATTERN
-- =============================================================================
-- Eseguire su PostgreSQL per aggiungere:
-- 1. Supervisione anomalie LKP-A01/A02
-- 2. Vista raggruppata per pattern
-- =============================================================================

-- =============================================================================
-- PARTE 1: TABELLE SUPERVISIONE LOOKUP
-- =============================================================================

-- Tabella supervisione lookup - per anomalie LKP-A01, LKP-A02
CREATE TABLE IF NOT EXISTS supervisione_lookup (
    id_supervisione SERIAL PRIMARY KEY,
    id_testata INTEGER NOT NULL REFERENCES ordini_testata(id_testata) ON DELETE CASCADE,
    id_anomalia INTEGER REFERENCES anomalie(id_anomalia) ON DELETE SET NULL,
    codice_anomalia TEXT NOT NULL,  -- LKP-A01 o LKP-A02
    -- Dati lookup
    vendor TEXT NOT NULL,
    partita_iva_estratta TEXT,
    lookup_method TEXT,
    lookup_score INTEGER,
    -- Pattern ML
    pattern_signature TEXT,
    stato TEXT DEFAULT 'PENDING',
    operatore TEXT,
    timestamp_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    timestamp_decisione TIMESTAMP,
    note TEXT,
    -- Risoluzione (compilato quando approvato)
    min_id_assegnato TEXT,
    id_farmacia_selezionata INTEGER REFERENCES anagrafica_farmacie(id_farmacia),
    id_parafarmacia_selezionata INTEGER REFERENCES anagrafica_parafarmacie(id_parafarmacia)
);

CREATE INDEX IF NOT EXISTS idx_sup_lookup_testata ON supervisione_lookup(id_testata);
CREATE INDEX IF NOT EXISTS idx_sup_lookup_stato ON supervisione_lookup(stato);
CREATE INDEX IF NOT EXISTS idx_sup_lookup_pattern ON supervisione_lookup(pattern_signature);

-- Tabella criteri ordinari lookup - per ML pattern learning
CREATE TABLE IF NOT EXISTS criteri_ordinari_lookup (
    pattern_signature TEXT PRIMARY KEY,
    pattern_descrizione TEXT,
    vendor TEXT NOT NULL,
    codice_anomalia TEXT NOT NULL,
    partita_iva_pattern TEXT,
    count_approvazioni INTEGER DEFAULT 0,
    is_ordinario BOOLEAN DEFAULT FALSE,
    data_prima_occorrenza TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_promozione TIMESTAMP,
    operatori_approvatori TEXT,
    -- Risoluzione default per applicazione automatica
    min_id_default TEXT,
    id_farmacia_default INTEGER REFERENCES anagrafica_farmacie(id_farmacia)
);

-- =============================================================================
-- PARTE 2: VISTA SUPERVISIONE LOOKUP PENDING
-- =============================================================================

CREATE OR REPLACE VIEW v_supervisione_lookup_pending AS
SELECT
    slk.id_supervisione,
    slk.id_testata,
    slk.codice_anomalia,
    slk.vendor,
    slk.partita_iva_estratta,
    slk.lookup_method,
    slk.lookup_score,
    slk.pattern_signature,
    slk.stato,
    slk.timestamp_creazione,
    slk.min_id_assegnato,
    ot.numero_ordine_vendor AS numero_ordine,
    ot.ragione_sociale_1 AS ragione_sociale,
    ot.citta,
    a.nome_file_originale AS pdf_file,
    COALESCE(colk.count_approvazioni, 0) AS count_pattern,
    COALESCE(colk.is_ordinario, FALSE) AS pattern_ordinario,
    colk.pattern_descrizione
FROM supervisione_lookup slk
JOIN ordini_testata ot ON slk.id_testata = ot.id_testata
JOIN acquisizioni a ON ot.id_acquisizione = a.id_acquisizione
LEFT JOIN criteri_ordinari_lookup colk ON slk.pattern_signature = colk.pattern_signature
WHERE slk.stato = 'PENDING'
ORDER BY slk.timestamp_creazione DESC;

-- =============================================================================
-- PARTE 3: VISTA RAGGRUPPATA PER PATTERN (TUTTE LE SUPERVISIONI)
-- =============================================================================

CREATE OR REPLACE VIEW v_supervisione_grouped_pending AS
WITH all_supervisions AS (
    -- Espositore supervisions
    SELECT
        se.pattern_signature,
        'espositore' AS tipo_supervisione,
        se.codice_anomalia,
        v.codice_vendor AS vendor,
        se.id_supervisione,
        se.id_testata,
        se.stato,
        ot.numero_ordine_vendor,
        ot.ragione_sociale_1,
        se.timestamp_creazione,
        COALESCE(coe.count_approvazioni, 0) AS pattern_count,
        COALESCE(coe.is_ordinario, FALSE) AS pattern_ordinario,
        coe.pattern_descrizione
    FROM supervisione_espositore se
    JOIN ordini_testata ot ON se.id_testata = ot.id_testata
    JOIN vendor v ON ot.id_vendor = v.id_vendor
    LEFT JOIN criteri_ordinari_espositore coe ON se.pattern_signature = coe.pattern_signature
    WHERE se.stato = 'PENDING'

    UNION ALL

    -- Listino supervisions
    SELECT
        sl.pattern_signature,
        'listino' AS tipo_supervisione,
        sl.codice_anomalia,
        sl.vendor,
        sl.id_supervisione,
        sl.id_testata,
        sl.stato,
        ot.numero_ordine_vendor,
        ot.ragione_sociale_1,
        sl.timestamp_creazione,
        COALESCE(col.count_approvazioni, 0) AS pattern_count,
        COALESCE(col.is_ordinario, FALSE) AS pattern_ordinario,
        col.pattern_descrizione
    FROM supervisione_listino sl
    JOIN ordini_testata ot ON sl.id_testata = ot.id_testata
    LEFT JOIN criteri_ordinari_listino col ON sl.pattern_signature = col.pattern_signature
    WHERE sl.stato = 'PENDING'

    UNION ALL

    -- Lookup supervisions
    SELECT
        slk.pattern_signature,
        'lookup' AS tipo_supervisione,
        slk.codice_anomalia,
        slk.vendor,
        slk.id_supervisione,
        slk.id_testata,
        slk.stato,
        ot.numero_ordine_vendor,
        ot.ragione_sociale_1,
        slk.timestamp_creazione,
        COALESCE(colk.count_approvazioni, 0) AS pattern_count,
        COALESCE(colk.is_ordinario, FALSE) AS pattern_ordinario,
        colk.pattern_descrizione
    FROM supervisione_lookup slk
    JOIN ordini_testata ot ON slk.id_testata = ot.id_testata
    LEFT JOIN criteri_ordinari_lookup colk ON slk.pattern_signature = colk.pattern_signature
    WHERE slk.stato = 'PENDING'
)
SELECT
    pattern_signature,
    tipo_supervisione,
    codice_anomalia,
    vendor,
    COUNT(*) AS total_count,
    array_agg(DISTINCT id_testata) AS affected_order_ids,
    array_agg(id_supervisione ORDER BY timestamp_creazione) AS supervision_ids,
    MAX(pattern_count) AS pattern_count,
    bool_or(pattern_ordinario) AS pattern_ordinario,
    MAX(pattern_descrizione) AS pattern_descrizione,
    string_agg(DISTINCT numero_ordine_vendor, ', ' ORDER BY numero_ordine_vendor) AS affected_orders_preview,
    string_agg(DISTINCT ragione_sociale_1, ', ' ORDER BY ragione_sociale_1) AS affected_clients_preview,
    MIN(timestamp_creazione) AS first_occurrence
FROM all_supervisions
WHERE pattern_signature IS NOT NULL
GROUP BY pattern_signature, tipo_supervisione, codice_anomalia, vendor
ORDER BY total_count DESC, first_occurrence ASC;

-- =============================================================================
-- PARTE 4: MIGRAZIONE ANOMALIE LKP ESISTENTI
-- =============================================================================
-- Migra le anomalie LKP-A01/A02 esistenti che hanno richiede_supervisione=TRUE
-- ma non hanno ancora una entry in supervisione_lookup

INSERT INTO supervisione_lookup (
    id_testata,
    id_anomalia,
    codice_anomalia,
    vendor,
    partita_iva_estratta,
    lookup_method,
    lookup_score,
    pattern_signature,
    stato,
    timestamp_creazione
)
SELECT
    a.id_testata,
    a.id_anomalia,
    a.codice_anomalia,
    COALESCE(v.codice_vendor, 'UNKNOWN'),
    ot.partita_iva_estratta,
    ot.lookup_method,
    ot.lookup_score,
    md5(COALESCE(v.codice_vendor, 'UNKNOWN') || '|' || a.codice_anomalia || '|' || COALESCE(ot.partita_iva_estratta, 'NO_PIVA'))::text,
    'PENDING',
    COALESCE(a.data_rilevazione, CURRENT_TIMESTAMP)
FROM anomalie a
JOIN ordini_testata ot ON a.id_testata = ot.id_testata
LEFT JOIN vendor v ON ot.id_vendor = v.id_vendor
WHERE a.codice_anomalia IN ('LKP-A01', 'LKP-A02')
  AND a.richiede_supervisione = TRUE
  AND a.stato = 'APERTA'
  AND NOT EXISTS (
      SELECT 1 FROM supervisione_lookup sl
      WHERE sl.id_anomalia = a.id_anomalia
  );

-- =============================================================================
-- VERIFICA
-- =============================================================================
SELECT 'Tabelle create:' AS info;
SELECT tablename FROM pg_tables
WHERE schemaname = 'public'
  AND tablename IN ('supervisione_lookup', 'criteri_ordinari_lookup');

SELECT 'Viste create:' AS info;
SELECT viewname FROM pg_views
WHERE schemaname = 'public'
  AND viewname IN ('v_supervisione_lookup_pending', 'v_supervisione_grouped_pending');

SELECT 'Anomalie LKP migrate:' AS info;
SELECT COUNT(*) AS count FROM supervisione_lookup;
