-- =============================================================================
-- SERV.O v9.0 - SUPERVISION AIC MIGRATION
-- =============================================================================
-- Sistema supervisione per prodotti senza codice AIC valido
-- Anomalia AIC-A01: Codice AIC mancante o non valido
-- =============================================================================

-- 1. Aggiungere colonna per AIC inserito manualmente in ordini_dettaglio
ALTER TABLE ordini_dettaglio
ADD COLUMN IF NOT EXISTS codice_aic_inserito TEXT;

-- 2. Tabella supervisione AIC
CREATE TABLE IF NOT EXISTS supervisione_aic (
    id_supervisione SERIAL PRIMARY KEY,
    id_testata INTEGER NOT NULL REFERENCES ordini_testata(id_testata) ON DELETE CASCADE,
    id_anomalia INTEGER REFERENCES anomalie(id_anomalia) ON DELETE SET NULL,
    id_dettaglio INTEGER REFERENCES ordini_dettaglio(id_dettaglio) ON DELETE SET NULL,
    codice_anomalia TEXT NOT NULL DEFAULT 'AIC-A01',

    -- Context data
    vendor TEXT NOT NULL,
    n_riga INTEGER,
    descrizione_prodotto TEXT,
    descrizione_normalizzata TEXT,
    codice_originale TEXT,

    -- Pattern ML
    pattern_signature TEXT,
    stato TEXT DEFAULT 'PENDING' CHECK (stato IN ('PENDING', 'APPROVED', 'REJECTED')),
    operatore TEXT,
    timestamp_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    timestamp_decisione TIMESTAMP,
    note TEXT,

    -- Resolution
    codice_aic_assegnato TEXT
);

-- Indexes per supervisione_aic
CREATE INDEX IF NOT EXISTS idx_sup_aic_testata ON supervisione_aic(id_testata);
CREATE INDEX IF NOT EXISTS idx_sup_aic_stato ON supervisione_aic(stato);
CREATE INDEX IF NOT EXISTS idx_sup_aic_pattern ON supervisione_aic(pattern_signature);
CREATE INDEX IF NOT EXISTS idx_sup_aic_vendor_desc ON supervisione_aic(vendor, descrizione_normalizzata);

-- 3. Tabella criteri ML per AIC
CREATE TABLE IF NOT EXISTS criteri_ordinari_aic (
    pattern_signature TEXT PRIMARY KEY,
    pattern_descrizione TEXT,
    vendor TEXT NOT NULL,
    descrizione_normalizzata TEXT NOT NULL,
    count_approvazioni INTEGER DEFAULT 0,
    is_ordinario BOOLEAN DEFAULT FALSE,
    data_prima_occorrenza TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_promozione TIMESTAMP,
    operatori_approvatori TEXT,
    codice_aic_default TEXT
);

-- Index per ricerca pattern
CREATE INDEX IF NOT EXISTS idx_crit_aic_vendor_desc ON criteri_ordinari_aic(vendor, descrizione_normalizzata);
CREATE INDEX IF NOT EXISTS idx_crit_aic_ordinario ON criteri_ordinari_aic(is_ordinario) WHERE is_ordinario = TRUE;

-- 4. Aggiornare view v_supervisione_grouped_pending per includere AIC
DROP VIEW IF EXISTS v_supervisione_grouped_pending;

CREATE VIEW v_supervisione_grouped_pending AS
WITH all_supervisions AS (
    -- Espositore supervisions
    SELECT
        se.pattern_signature,
        'espositore' AS tipo_supervisione,
        se.codice_anomalia,
        'ANGELINI' AS vendor,
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

    UNION ALL

    -- Prezzo supervisions (v8.1)
    SELECT
        sp.pattern_signature,
        'prezzo' AS tipo_supervisione,
        sp.codice_anomalia,
        sp.vendor,
        sp.id_supervisione,
        sp.id_testata,
        sp.stato,
        ot.numero_ordine_vendor,
        ot.ragione_sociale_1,
        sp.timestamp_creazione,
        0 AS pattern_count,
        FALSE AS pattern_ordinario,
        NULL AS pattern_descrizione
    FROM supervisione_prezzo sp
    JOIN ordini_testata ot ON sp.id_testata = ot.id_testata
    WHERE sp.stato = 'PENDING'

    UNION ALL

    -- AIC supervisions (v9.0)
    SELECT
        saic.pattern_signature,
        'aic' AS tipo_supervisione,
        saic.codice_anomalia,
        saic.vendor,
        saic.id_supervisione,
        saic.id_testata,
        saic.stato,
        ot.numero_ordine_vendor,
        ot.ragione_sociale_1,
        saic.timestamp_creazione,
        COALESCE(coaic.count_approvazioni, 0) AS pattern_count,
        COALESCE(coaic.is_ordinario, FALSE) AS pattern_ordinario,
        coaic.pattern_descrizione
    FROM supervisione_aic saic
    JOIN ordini_testata ot ON saic.id_testata = ot.id_testata
    LEFT JOIN criteri_ordinari_aic coaic ON saic.pattern_signature = coaic.pattern_signature
    WHERE saic.stato = 'PENDING'
)
SELECT
    pattern_signature,
    tipo_supervisione,
    codice_anomalia,
    vendor,
    COUNT(*) AS total_count,
    ARRAY_AGG(DISTINCT id_testata) AS affected_order_ids,
    ARRAY_AGG(id_supervisione) AS supervision_ids,
    MAX(pattern_count) AS pattern_count,
    BOOL_OR(pattern_ordinario) AS pattern_ordinario,
    MAX(pattern_descrizione) AS pattern_descrizione,
    ARRAY_AGG(DISTINCT numero_ordine_vendor) AS affected_orders_preview,
    ARRAY_AGG(DISTINCT ragione_sociale_1) AS affected_clients_preview,
    MIN(timestamp_creazione) AS first_occurrence
FROM all_supervisions
GROUP BY pattern_signature, tipo_supervisione, codice_anomalia, vendor
ORDER BY first_occurrence DESC;

-- Log migration
DO $$
BEGIN
    RAISE NOTICE 'Migration v10_supervision_aic completed successfully';
END $$;
