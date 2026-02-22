-- =============================================================================
-- SERV.O v11.3 - VIEW CON PRIORITÀ DATI ESTRATTI DAL PDF
-- =============================================================================
-- I dati estratti dal PDF hanno SEMPRE priorità su quelli dell'anagrafica
-- ministeriale. L'anagrafica serve solo come fallback per campi vuoti.
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
    COALESCE(ot.codice_ministeriale_estratto, af.min_id) AS min_id,
    COALESCE(ot.partita_iva_estratta, af.partita_iva) AS partita_iva,
    COALESCE(ot.ragione_sociale_1, af.ragione_sociale) AS ragione_sociale,
    ot.ragione_sociale_1,
    ot.ragione_sociale_2,
    ot.indirizzo,
    ot.cap,
    COALESCE(ot.citta, af.citta) AS citta,
    COALESCE(ot.provincia, af.provincia) AS provincia,
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
SELECT 'Vista v_ordini_completi aggiornata: dati estratti hanno sempre priorità' as status;
