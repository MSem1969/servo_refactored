-- v10.4: Update view to include descrizione_prodotto for LISTINO supervisions
DROP VIEW IF EXISTS v_supervisione_grouped_pending;

CREATE VIEW v_supervisione_grouped_pending AS
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
        coe.pattern_descrizione,
        se.descrizione_espositore AS descrizione_prodotto,
        se.codice_espositore AS codice_aic
    FROM supervisione_espositore se
    JOIN ordini_testata ot ON se.id_testata = ot.id_testata
    JOIN vendor v ON ot.id_vendor = v.id_vendor
    LEFT JOIN criteri_ordinari_espositore coe ON se.pattern_signature = coe.pattern_signature
    WHERE se.stato = 'PENDING'

    UNION ALL

    -- Listino supervisions (v10.4: include descrizione_prodotto)
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
        col.pattern_descrizione,
        sl.descrizione_prodotto,
        sl.codice_aic
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
        colk.pattern_descrizione,
        ot.ragione_sociale_1 AS descrizione_prodotto,
        slk.partita_iva_estratta AS codice_aic
    FROM supervisione_lookup slk
    JOIN ordini_testata ot ON slk.id_testata = ot.id_testata
    LEFT JOIN criteri_ordinari_lookup colk ON slk.pattern_signature = colk.pattern_signature
    WHERE slk.stato = 'PENDING'

    UNION ALL

    -- AIC supervisions (v9.1, v10.4: include descrizione_prodotto)
    SELECT
        saic.pattern_signature,
        'aic' AS tipo_supervisione,
        saic.codice_anomalia,
        COALESCE(saic.vendor, 'UNKNOWN') AS vendor,
        saic.id_supervisione,
        saic.id_testata,
        saic.stato,
        ot.numero_ordine_vendor,
        ot.ragione_sociale_1,
        saic.timestamp_creazione,
        COALESCE(coaic.count_approvazioni, 0) AS pattern_count,
        COALESCE(coaic.is_ordinario, FALSE) AS pattern_ordinario,
        coaic.pattern_descrizione,
        saic.descrizione_prodotto,
        saic.codice_originale AS codice_aic
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
    MIN(timestamp_creazione) AS first_occurrence,
    -- v10.4: Include descrizione prodotto e codice AIC
    (ARRAY_AGG(descrizione_prodotto ORDER BY timestamp_creazione))[1] AS descrizione_prodotto,
    (ARRAY_AGG(codice_aic ORDER BY timestamp_creazione))[1] AS codice_aic
FROM all_supervisions
GROUP BY pattern_signature, tipo_supervisione, codice_anomalia, vendor
ORDER BY first_occurrence DESC;

SELECT 'View updated with descrizione_prodotto!' AS status;
