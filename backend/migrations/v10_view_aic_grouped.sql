-- =============================================================================
-- MIGRAZIONE v10: Aggiunge AIC alla view supervisione raggruppata
-- =============================================================================
-- La view v_supervisione_grouped_pending non includeva le supervisioni AIC
-- Questa migrazione aggiorna la view per includere il tipo 'aic'
-- =============================================================================

CREATE OR REPLACE VIEW v_supervisione_grouped_pending AS
WITH all_supervisions AS (
    -- ESPOSITORE
    SELECT se.pattern_signature, 'espositore' AS tipo_supervisione, se.codice_anomalia,
           v.codice_vendor AS vendor, se.id_supervisione, se.id_testata, se.stato,
           ot.numero_ordine_vendor, ot.ragione_sociale_1, se.timestamp_creazione,
           COALESCE(coe.count_approvazioni, 0) AS pattern_count,
           COALESCE(coe.is_ordinario, FALSE) AS pattern_ordinario, coe.pattern_descrizione
    FROM supervisione_espositore se
    JOIN ordini_testata ot ON se.id_testata = ot.id_testata
    JOIN vendor v ON ot.id_vendor = v.id_vendor
    LEFT JOIN criteri_ordinari_espositore coe ON se.pattern_signature = coe.pattern_signature
    WHERE se.stato = 'PENDING'

    UNION ALL

    -- LISTINO
    SELECT sl.pattern_signature, 'listino', sl.codice_anomalia, sl.vendor, sl.id_supervisione,
           sl.id_testata, sl.stato, ot.numero_ordine_vendor, ot.ragione_sociale_1, sl.timestamp_creazione,
           COALESCE(col.count_approvazioni, 0), COALESCE(col.is_ordinario, FALSE), col.pattern_descrizione
    FROM supervisione_listino sl
    JOIN ordini_testata ot ON sl.id_testata = ot.id_testata
    LEFT JOIN criteri_ordinari_listino col ON sl.pattern_signature = col.pattern_signature
    WHERE sl.stato = 'PENDING'

    UNION ALL

    -- LOOKUP
    SELECT slk.pattern_signature, 'lookup', slk.codice_anomalia, slk.vendor, slk.id_supervisione,
           slk.id_testata, slk.stato, ot.numero_ordine_vendor, ot.ragione_sociale_1, slk.timestamp_creazione,
           COALESCE(colk.count_approvazioni, 0), COALESCE(colk.is_ordinario, FALSE), colk.pattern_descrizione
    FROM supervisione_lookup slk
    JOIN ordini_testata ot ON slk.id_testata = ot.id_testata
    LEFT JOIN criteri_ordinari_lookup colk ON slk.pattern_signature = colk.pattern_signature
    WHERE slk.stato = 'PENDING'

    UNION ALL

    -- AIC (v9.0)
    SELECT saic.pattern_signature, 'aic', saic.codice_anomalia, saic.vendor, saic.id_supervisione,
           saic.id_testata, saic.stato, ot.numero_ordine_vendor, ot.ragione_sociale_1, saic.timestamp_creazione,
           COALESCE(coaic.count_approvazioni, 0), COALESCE(coaic.is_ordinario, FALSE), coaic.pattern_descrizione
    FROM supervisione_aic saic
    JOIN ordini_testata ot ON saic.id_testata = ot.id_testata
    LEFT JOIN criteri_ordinari_aic coaic ON saic.pattern_signature = coaic.pattern_signature
    WHERE saic.stato = 'PENDING'
)
SELECT pattern_signature, tipo_supervisione, codice_anomalia, vendor,
       COUNT(*) AS total_count, ARRAY_AGG(DISTINCT id_testata) AS affected_order_ids,
       ARRAY_AGG(id_supervisione ORDER BY timestamp_creazione) AS supervision_ids,
       MAX(pattern_count) AS pattern_count, BOOL_OR(pattern_ordinario) AS pattern_ordinario,
       MAX(pattern_descrizione) AS pattern_descrizione,
       STRING_AGG(DISTINCT numero_ordine_vendor::TEXT, ', ' ORDER BY numero_ordine_vendor::TEXT) AS affected_orders_preview,
       STRING_AGG(DISTINCT ragione_sociale_1::TEXT, ', ' ORDER BY ragione_sociale_1::TEXT) AS affected_clients_preview,
       MIN(timestamp_creazione) AS first_occurrence
FROM all_supervisions WHERE pattern_signature IS NOT NULL
GROUP BY pattern_signature, tipo_supervisione, codice_anomalia, vendor
ORDER BY COUNT(*) DESC, MIN(timestamp_creazione);

-- Grant accesso
GRANT SELECT ON v_supervisione_grouped_pending TO to_extractor_user;
