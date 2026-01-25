-- =============================================================================
-- SERV.O v11.3 - VIEW CON PRIORITÀ MODIFICA MANUALE
-- =============================================================================
-- Quando lookup_method = 'MANUALE', i valori della testata hanno priorità
-- su quelli dell'anagrafica farmacie
-- =============================================================================

CREATE OR REPLACE VIEW public.v_ordini_completi AS
SELECT
    ot.id_testata,
    ot.id_acquisizione,
    v.codice_vendor AS vendor,
    ot.numero_ordine_vendor,
    ot.data_ordine,
    ot.data_consegna,
    ot.stato,
    -- MIN_ID: priorità a testata se MANUALE, altrimenti anagrafica
    CASE
        WHEN ot.lookup_method = 'MANUALE' THEN COALESCE(ot.min_id, ot.codice_ministeriale_estratto, af.min_id)
        ELSE COALESCE(af.min_id, ot.min_id, ot.codice_ministeriale_estratto)
    END AS min_id,
    -- P.IVA: priorità a testata se MANUALE
    CASE
        WHEN ot.lookup_method = 'MANUALE' THEN COALESCE(ot.partita_iva_estratta, af.partita_iva)
        ELSE COALESCE(af.partita_iva, ot.partita_iva_estratta)
    END AS partita_iva,
    -- Ragione sociale: priorità a testata se MANUALE
    CASE
        WHEN ot.lookup_method = 'MANUALE' THEN COALESCE(ot.ragione_sociale_1, af.ragione_sociale)
        ELSE COALESCE(af.ragione_sociale, ot.ragione_sociale_1)
    END AS ragione_sociale,
    ot.ragione_sociale_1,
    ot.ragione_sociale_2,
    ot.indirizzo,
    ot.cap,
    -- Città: priorità a testata se MANUALE
    CASE
        WHEN ot.lookup_method = 'MANUALE' THEN COALESCE(ot.citta, af.comune)
        ELSE COALESCE(af.comune, ot.citta)
    END AS citta,
    -- Provincia: priorità a testata se MANUALE
    CASE
        WHEN ot.lookup_method = 'MANUALE' THEN COALESCE(ot.provincia, af.provincia)
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
    a.nome_file_originale AS pdf_file
FROM public.ordini_testata ot
LEFT JOIN public.vendor v ON ot.id_vendor = v.id_vendor
LEFT JOIN public.anagrafica_farmacie af ON ot.id_farmacia_lookup = af.id_farmacia
LEFT JOIN public.acquisizioni a ON ot.id_acquisizione = a.id_acquisizione;

-- Verifica
SELECT 'Vista v_ordini_completi aggiornata con priorità MANUALE' as status;
