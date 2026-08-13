-- =============================================================================
-- v17 - BONIFICA: supervisioni e anomalie su ordini gia' ARCHIVIATI
-- =============================================================================
-- Un ordine archiviato riga per riga diventava ARCHIVIATO tramite il ricalcolo
-- di _calcola_stato_ordine, che non toccava anomalie ne' supervisioni: restavano
-- APERTA/PENDING su ordini che non saranno mai esportati, occupando per sempre
-- la coda di supervisione.
--
-- Il fix del codice (archivia_anomalie_e_supervisioni chiamata da archivia_riga
-- e da _aggiorna_contatori_ordine) impedisce nuovi casi. Questa migration
-- bonifica lo storico, applicando gli stessi valori di archivia_ordine:
--   anomalie APERTA/IN_GESTIONE -> ARCHIVIATA
--   supervisioni PENDING        -> ARCHIVED
--
-- Riguarda SOLO ordini con stato = 'ARCHIVIATO'. Nessun altro stato e' toccato.
--
-- Applicare con:  psql -U servo -d servo -f v17_bonifica_supervisioni_ordini_archiviati.sql
-- =============================================================================

BEGIN;

-- 0. PREREQUISITO: supervisione_aic e' l'unica tabella supervisione con un CHECK
-- sullo stato, e non ammetteva 'ARCHIVED'. Per questo archivia_ordine falliva su
-- AIC fin da gennaio 2026 (l'errore era nascosto da un except: pass) e le sue
-- supervisioni restavano PENDING sugli ordini archiviati.
ALTER TABLE supervisione_aic DROP CONSTRAINT IF EXISTS supervisione_aic_stato_check;
ALTER TABLE supervisione_aic ADD CONSTRAINT supervisione_aic_stato_check
    CHECK (stato IN ('PENDING', 'APPROVED', 'REJECTED', 'ARCHIVED'));

-- Prima/dopo: conteggio di controllo
\echo '--- PRIMA ---'
SELECT count(*) AS supervisioni_pending_su_ordini_archiviati
FROM (
    SELECT s.id_supervisione FROM supervisione_lookup s
      JOIN ordini_testata o ON o.id_testata = s.id_testata
     WHERE s.stato = 'PENDING' AND o.stato = 'ARCHIVIATO'
    UNION ALL
    SELECT s.id_supervisione FROM supervisione_espositore s
      JOIN ordini_testata o ON o.id_testata = s.id_testata
     WHERE s.stato = 'PENDING' AND o.stato = 'ARCHIVIATO'
    UNION ALL
    SELECT s.id_supervisione FROM supervisione_listino s
      JOIN ordini_testata o ON o.id_testata = s.id_testata
     WHERE s.stato = 'PENDING' AND o.stato = 'ARCHIVIATO'
    UNION ALL
    SELECT s.id_supervisione FROM supervisione_aic s
      JOIN ordini_testata o ON o.id_testata = s.id_testata
     WHERE s.stato = 'PENDING' AND o.stato = 'ARCHIVIATO'
    UNION ALL
    SELECT s.id_supervisione FROM supervisione_prezzo s
      JOIN ordini_testata o ON o.id_testata = s.id_testata
     WHERE s.stato = 'PENDING' AND o.stato = 'ARCHIVIATO'
    UNION ALL
    SELECT s.id_supervisione FROM supervisione_erp s
      JOIN ordini_testata o ON o.id_testata = s.id_testata
     WHERE s.stato = 'PENDING' AND o.stato = 'ARCHIVIATO'
) x;

-- 1. Anomalie ancora aperte su ordini archiviati
UPDATE anomalie a
SET stato = 'ARCHIVIATA',
    data_risoluzione = CURRENT_TIMESTAMP,
    note_risoluzione = COALESCE(a.note_risoluzione || ' | ', '')
                       || '[BONIFICA v17] Archiviata: ordine senza righe attive'
FROM ordini_testata o
WHERE o.id_testata = a.id_testata
  AND o.stato = 'ARCHIVIATO'
  AND a.stato IN ('APERTA', 'IN_GESTIONE');

-- 2. Supervisioni pending su ordini archiviati
UPDATE supervisione_lookup s
SET stato = 'ARCHIVED', operatore = 'SISTEMA', timestamp_decisione = CURRENT_TIMESTAMP,
    note = COALESCE(s.note || ' | ', '') || '[BONIFICA v17] Archiviata: ordine senza righe attive'
FROM ordini_testata o
WHERE o.id_testata = s.id_testata AND o.stato = 'ARCHIVIATO' AND s.stato = 'PENDING';

UPDATE supervisione_espositore s
SET stato = 'ARCHIVED', operatore = 'SISTEMA', timestamp_decisione = CURRENT_TIMESTAMP,
    note = COALESCE(s.note || ' | ', '') || '[BONIFICA v17] Archiviata: ordine senza righe attive'
FROM ordini_testata o
WHERE o.id_testata = s.id_testata AND o.stato = 'ARCHIVIATO' AND s.stato = 'PENDING';

UPDATE supervisione_listino s
SET stato = 'ARCHIVED', operatore = 'SISTEMA', timestamp_decisione = CURRENT_TIMESTAMP,
    note = COALESCE(s.note || ' | ', '') || '[BONIFICA v17] Archiviata: ordine senza righe attive'
FROM ordini_testata o
WHERE o.id_testata = s.id_testata AND o.stato = 'ARCHIVIATO' AND s.stato = 'PENDING';

UPDATE supervisione_aic s
SET stato = 'ARCHIVED', operatore = 'SISTEMA', timestamp_decisione = CURRENT_TIMESTAMP,
    note = COALESCE(s.note || ' | ', '') || '[BONIFICA v17] Archiviata: ordine senza righe attive'
FROM ordini_testata o
WHERE o.id_testata = s.id_testata AND o.stato = 'ARCHIVIATO' AND s.stato = 'PENDING';

UPDATE supervisione_prezzo s
SET stato = 'ARCHIVED', operatore = 'SISTEMA', timestamp_decisione = CURRENT_TIMESTAMP,
    note = COALESCE(s.note || ' | ', '') || '[BONIFICA v17] Archiviata: ordine senza righe attive'
FROM ordini_testata o
WHERE o.id_testata = s.id_testata AND o.stato = 'ARCHIVIATO' AND s.stato = 'PENDING';

UPDATE supervisione_erp s
SET stato = 'ARCHIVED', operatore = 'SISTEMA', timestamp_decisione = CURRENT_TIMESTAMP,
    note = COALESCE(s.note || ' | ', '') || '[BONIFICA v17] Archiviata: ordine senza righe attive'
FROM ordini_testata o
WHERE o.id_testata = s.id_testata AND o.stato = 'ARCHIVIATO' AND s.stato = 'PENDING';

\echo '--- DOPO (atteso: 0) ---'
SELECT count(*) AS supervisioni_pending_su_ordini_archiviati
FROM supervisione_lookup s
JOIN ordini_testata o ON o.id_testata = s.id_testata
WHERE s.stato = 'PENDING' AND o.stato = 'ARCHIVIATO';

-- Sostituire con ROLLBACK per una prova a vuoto.
COMMIT;
