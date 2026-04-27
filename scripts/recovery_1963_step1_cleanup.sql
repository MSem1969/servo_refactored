-- =============================================================================
-- RECOVERY ACQUISIZIONE 1963 - STEP 1: BACKUP + CLEANUP
-- =============================================================================
-- - Salva in tabelle temporanee persistenti gli stati delle 12 testate
--   esistenti e il path del PDF (servono nello Step 2 e Step 3).
-- - Cancella ogni traccia DB di id_acquisizione=1963 (incluse le 12 testate
--   e tutte le tabelle figlie senza FK CASCADE).
-- - Cancella anche il record acquisizioni stesso, cosi' il successivo
--   process_pdf NON triggera il dedup hash.
--
-- TUTTO IN UNA TRANSAZIONE: in caso di errore, rollback automatico.
--
-- IMPORTANTE: i tracciati FISICI inviati all'ERP (file TO_T/TO_D) NON
-- vengono toccati. Anche i record `esportazioni` (lotti) restano. Solo i
-- legami `esportazioni_dettaglio` -> testate vengono persi (audit DB).
-- =============================================================================

\set ON_ERROR_STOP on

BEGIN;

-- ---- 1. Backup stati testate (per restore in Step 3) -----------------------

DROP TABLE IF EXISTS _recovery_1963_stati;
CREATE TABLE _recovery_1963_stati AS
SELECT numero_ordine_vendor, stato
FROM ordini_testata
WHERE id_acquisizione = 1963
  AND stato IN ('ESPORTATO', 'ARCHIVIATO');

-- ---- 2. Backup info PDF (per riprocessarlo in Step 2) ----------------------

DROP TABLE IF EXISTS _recovery_1963_pdf;
CREATE TABLE _recovery_1963_pdf AS
SELECT id_acquisizione, nome_file_originale, nome_file_storage,
       percorso_storage, hash_file, dimensione_bytes, id_vendor
FROM acquisizioni
WHERE id_acquisizione = 1963;

-- Verifica backup non vuoto
DO $$
BEGIN
    IF (SELECT COUNT(*) FROM _recovery_1963_pdf) = 0 THEN
        RAISE EXCEPTION 'Acquisizione 1963 non trovata - abort cleanup';
    END IF;
END $$;

-- ---- 3. Cancellazione in ordine corretto -----------------------------------

-- esportazioni_dettaglio (no CASCADE, NO FK formale)
DELETE FROM esportazioni_dettaglio
WHERE id_testata IN (SELECT id_testata FROM ordini_testata WHERE id_acquisizione = 1963);

-- supervisioni a livello riga (no CASCADE)
DELETE FROM supervisione_aic         WHERE id_testata IN (SELECT id_testata FROM ordini_testata WHERE id_acquisizione = 1963);
DELETE FROM supervisione_listino     WHERE id_testata IN (SELECT id_testata FROM ordini_testata WHERE id_acquisizione = 1963);

-- supervisioni testata-level (alcune con FK NO ACTION - se non cancelliamo, DELETE testata fallisce)
DELETE FROM supervisione_anagrafica  WHERE id_testata IN (SELECT id_testata FROM ordini_testata WHERE id_acquisizione = 1963);
DELETE FROM supervisione_erp         WHERE id_testata IN (SELECT id_testata FROM ordini_testata WHERE id_acquisizione = 1963);
DELETE FROM supervisione_lookup      WHERE id_testata IN (SELECT id_testata FROM ordini_testata WHERE id_acquisizione = 1963);
DELETE FROM supervisione_prezzo      WHERE id_testata IN (SELECT id_testata FROM ordini_testata WHERE id_acquisizione = 1963);
DELETE FROM supervisione_espositore  WHERE id_testata IN (SELECT id_testata FROM ordini_testata WHERE id_acquisizione = 1963);
-- supervisione_unificata ha FK CASCADE, si pulisce da sola con DELETE testata

-- anomalie (no FK CASCADE)
DELETE FROM anomalie WHERE id_testata IN (SELECT id_testata FROM ordini_testata WHERE id_acquisizione = 1963);

-- dettagli (no FK CASCADE)
DELETE FROM ordini_dettaglio WHERE id_testata IN (SELECT id_testata FROM ordini_testata WHERE id_acquisizione = 1963);

-- testate
DELETE FROM ordini_testata WHERE id_acquisizione = 1963;

-- acquisizione (libera l'hash dal dedup, abilita process_pdf in Step 2)
DELETE FROM acquisizioni WHERE id_acquisizione = 1963;

-- ---- 4. Verifiche --------------------------------------------------------

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM ordini_testata WHERE id_acquisizione = 1963) THEN
        RAISE EXCEPTION 'Cleanup incompleto: testate residue su id_acquisizione=1963';
    END IF;
    IF EXISTS (SELECT 1 FROM acquisizioni WHERE id_acquisizione = 1963) THEN
        RAISE EXCEPTION 'Cleanup incompleto: acquisizione 1963 ancora presente';
    END IF;
END $$;

COMMIT;

-- ---- 5. Conferma a video --------------------------------------------------

SELECT 'STATI BACKUPPATI' AS check_label, COUNT(*) AS n_records FROM _recovery_1963_stati
UNION ALL
SELECT 'PDF BACKUPPATO',                COUNT(*)               FROM _recovery_1963_pdf;

\echo ''
\echo '== Step 1 completato =='
\echo 'Prossimo: Step 2 (Python) per ri-elaborare il PDF tramite process_pdf.'
\echo ''
