-- =============================================================================
-- RECOVERY ACQUISIZIONE 1963 - STEP 3: RESTORE STATI
-- =============================================================================
-- - Riapplica gli stati 'ESPORTATO' (10 ordini) e 'ARCHIVIATO' (1 ordine)
--   sulle nuove testate create da Step 2, in base al backup salvato dallo
--   Step 1 in tabella _recovery_1963_stati.
-- - Allinea anche stato_riga e q_evasa nei dettagli per coerenza con stato.
-- - Drop delle tabelle di backup a operazione conclusa.
--
-- PRECONDIZIONE: completati Step 1 e Step 2.
-- IMPOSTA SOTTO L'id_acquisizione NUOVO ricevuto dallo Step 2.
-- =============================================================================

\set ON_ERROR_STOP on

-- *** MODIFICA QUI: sostituisci con l'id_acquisizione NUOVO dello Step 2 ***
\set id_acq_new 1964

BEGIN;

-- ---- 1. Verifica precondizioni ---------------------------------------------

DO $$
DECLARE
    v_count_new INT;
    v_count_backup INT;
BEGIN
    SELECT COUNT(*) INTO v_count_new
    FROM ordini_testata WHERE id_acquisizione = :id_acq_new;

    IF v_count_new != 34 THEN
        RAISE EXCEPTION 'Atteso 34 testate su id_acquisizione=:id_acq_new, trovate %.', v_count_new;
    END IF;

    SELECT COUNT(*) INTO v_count_backup FROM _recovery_1963_stati;
    IF v_count_backup = 0 THEN
        RAISE EXCEPTION 'Tabella _recovery_1963_stati vuota - hai gia eseguito Step 3?';
    END IF;

    RAISE NOTICE 'Precondizioni OK: % testate nuove, % stati da ripristinare',
                 v_count_new, v_count_backup;
END $$;

-- ---- 2. Restore stato testata ESPORTATO ------------------------------------

UPDATE ordini_testata
SET stato = 'ESPORTATO'
WHERE id_acquisizione = :id_acq_new
  AND numero_ordine_vendor IN (
    SELECT numero_ordine_vendor FROM _recovery_1963_stati WHERE stato = 'ESPORTATO'
);

-- ---- 3. Restore stato testata ARCHIVIATO -----------------------------------

UPDATE ordini_testata
SET stato = 'ARCHIVIATO'
WHERE id_acquisizione = :id_acq_new
  AND numero_ordine_vendor IN (
    SELECT numero_ordine_vendor FROM _recovery_1963_stati WHERE stato = 'ARCHIVIATO'
);

-- ---- 4. Allinea righe degli ESPORTATO: q_evasa = q_totale, stato='ESPORTATO'

UPDATE ordini_dettaglio od
SET stato_riga = 'ESPORTATO',
    q_evasa = COALESCE(od.q_venduta, 0) + COALESCE(od.q_sconto_merce, 0) + COALESCE(od.q_omaggio, 0),
    q_da_evadere = 0
FROM ordini_testata ot
WHERE od.id_testata = ot.id_testata
  AND ot.id_acquisizione = :id_acq_new
  AND ot.stato = 'ESPORTATO';

-- ---- 5. Allinea righe degli ARCHIVIATO -------------------------------------

UPDATE ordini_dettaglio od
SET stato_riga = 'ARCHIVIATO'
FROM ordini_testata ot
WHERE od.id_testata = ot.id_testata
  AND ot.id_acquisizione = :id_acq_new
  AND ot.stato = 'ARCHIVIATO';

-- ---- 6. Verifica risultato finale ------------------------------------------

DO $$
DECLARE
    v_esportati INT;
    v_archiviati INT;
BEGIN
    SELECT COUNT(*) INTO v_esportati FROM ordini_testata
    WHERE id_acquisizione = :id_acq_new AND stato = 'ESPORTATO';
    SELECT COUNT(*) INTO v_archiviati FROM ordini_testata
    WHERE id_acquisizione = :id_acq_new AND stato = 'ARCHIVIATO';

    RAISE NOTICE 'Stati finali su id_acquisizione=:id_acq_new: % ESPORTATO, % ARCHIVIATO',
                 v_esportati, v_archiviati;
END $$;

-- ---- 7. Cleanup tabelle di backup ------------------------------------------

DROP TABLE IF EXISTS _recovery_1963_stati;
DROP TABLE IF EXISTS _recovery_1963_pdf;

COMMIT;

-- ---- 8. Report finale ------------------------------------------------------

SELECT
    'TOTALE ORDINI' AS check_label, COUNT(*)::TEXT AS valore
FROM ordini_testata WHERE id_acquisizione = :id_acq_new
UNION ALL
SELECT
    'STATI ORDINE',
    STRING_AGG(stato || ':' || cnt, ', ' ORDER BY stato)
FROM (
    SELECT stato, COUNT(*) AS cnt
    FROM ordini_testata
    WHERE id_acquisizione = :id_acq_new
    GROUP BY stato
) s
UNION ALL
SELECT
    'TRACCIATI ESPORTAZIONI (file fisici inviati ERP)',
    COUNT(DISTINCT id_esportazione)::TEXT
FROM esportazioni
WHERE EXISTS (
    SELECT 1 FROM esportazioni e2
    WHERE e2.id_esportazione = esportazioni.id_esportazione
);

\echo ''
\echo '== Step 3 completato =='
\echo 'Le testate sono ripristinate. Verifica via UI che gli ordini ESPORTATO'
\echo 'e ARCHIVIATO appaiano nello stato corretto.'
\echo ''
