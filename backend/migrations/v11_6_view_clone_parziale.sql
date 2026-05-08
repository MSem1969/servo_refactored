-- =============================================================================
-- SERV.O v11.6 - V_ORDINI_COMPLETI con info clone parziale
-- =============================================================================
-- Aggiunge alla vista colonne:
--   is_clone_parziale       (dalla testata)
--   id_testata_originale    (dalla testata)
--   numero_ordine_root      (numero_ordine_vendor del root della catena)
--   n_cloni_catena          (totale cloni esistenti per il root, esclude il root)
-- =============================================================================

CREATE OR REPLACE VIEW V_ORDINI_COMPLETI AS
SELECT ot.id_testata,
    ot.id_acquisizione,
    v.codice_vendor AS vendor,
    ot.numero_ordine_vendor,
    ot.data_ordine,
    COALESCE(MIN(od.data_consegna_riga) FILTER (
        WHERE (od.stato_riga::text <> ALL (ARRAY['EVASO'::character varying,
                                                  'ARCHIVIATO'::character varying]::text[]))
          AND od.data_consegna_riga IS NOT NULL
    ), ot.data_consegna) AS data_consegna,
    ot.stato,
    CASE
        WHEN ot.lookup_method::text = 'MANUALE'::text THEN COALESCE(ot.codice_ministeriale_estratto, af.min_id)
        ELSE COALESCE(af.min_id, ot.codice_ministeriale_estratto)
    END AS min_id,
    CASE
        WHEN ot.lookup_method::text = 'MANUALE'::text THEN COALESCE(ot.partita_iva_estratta, af.partita_iva)
        ELSE COALESCE(af.partita_iva, ot.partita_iva_estratta)
    END AS partita_iva,
    CASE
        WHEN ot.lookup_method::text = 'MANUALE'::text THEN COALESCE(ot.ragione_sociale_1, af.ragione_sociale)
        ELSE COALESCE(af.ragione_sociale, ot.ragione_sociale_1)
    END AS ragione_sociale,
    ot.ragione_sociale_1,
    ot.ragione_sociale_2,
    ot.indirizzo,
    ot.cap,
    CASE
        WHEN ot.lookup_method::text = 'MANUALE'::text THEN COALESCE(ot.citta, af.citta)
        ELSE COALESCE(af.citta, ot.citta)
    END AS citta,
    CASE
        WHEN ot.lookup_method::text = 'MANUALE'::text THEN COALESCE(ot.provincia, af.provincia)
        ELSE COALESCE(af.provincia, ot.provincia)
    END AS provincia,
    ot.nome_agente,
    ot.note_ordine,
    ot.note_ddt,
    ot.lookup_score,
    ot.lookup_method,
    ot.righe_totali,
    ot.righe_confermate,
    ot.righe_in_supervisione,
    ot.data_estrazione,
    ot.data_validazione,
    ot.validato_da,
    ot.is_ordine_duplicato,
    ot.valore_totale_netto,
    ot.difarm,
    a.nome_file_originale AS pdf_file,
    -- v11.6: campi consegna ripartita
    ot.is_clone_parziale,
    ot.id_testata_originale,
    CASE
        WHEN ot.is_clone_parziale THEN ot_root.numero_ordine_vendor
        ELSE ot.numero_ordine_vendor
    END AS numero_ordine_root,
    COALESCE((
        SELECT COUNT(*)::int FROM ordini_testata ot2
        WHERE ot2.id_testata_originale = COALESCE(ot.id_testata_originale, ot.id_testata)
          AND ot2.is_clone_parziale = TRUE
    ), 0) AS n_cloni_catena
FROM ordini_testata ot
    LEFT JOIN vendor v ON ot.id_vendor = v.id_vendor
    LEFT JOIN anagrafica_farmacie af ON ot.id_farmacia_lookup = af.id_farmacia
    LEFT JOIN acquisizioni a ON ot.id_acquisizione = a.id_acquisizione
    LEFT JOIN ordini_dettaglio od ON ot.id_testata = od.id_testata
    LEFT JOIN ordini_testata ot_root
        ON ot_root.id_testata = ot.id_testata_originale
GROUP BY ot.id_testata, v.codice_vendor,
    af.min_id, af.partita_iva, af.ragione_sociale, af.citta, af.provincia,
    a.nome_file_originale,
    ot_root.numero_ordine_vendor;
