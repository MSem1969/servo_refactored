-- =============================================================================
-- v18 - Ripristina lo stato ANOMALIA sugli ordini che l'hanno perso
-- =============================================================================
-- _calcola_stato_ordine non conosceva lo stato ANOMALIA: ogni ricalcolo dei
-- contatori (conferma riga, q_da_evadere, ripristino, fix-stati, bolla) lo
-- sovrascriveva con ESTRATTO/CONFERMATO. Risultato: ordini con anomalie
-- bloccanti aperte o supervisioni pending che sembrano a posto nella lista
-- ordini e poi non generano il tracciato.
--
-- Il fix del codice (parametro ha_blocchi_aperti in _calcola_stato_ordine)
-- impedisce nuovi casi. Questa migration allinea lo storico.
--
-- Riguarda SOLO gli stati pre-tracciato ESTRATTO/CONFERMATO: VALIDATO,
-- ESPORTATO, EVASO e ARCHIVIATO non vengono toccati.
--
-- Applicare con:  psql -U servo -d servo -f v18_ripristina_stato_anomalia.sql
-- =============================================================================

BEGIN;

\echo '--- PRIMA (ordini da riportare in ANOMALIA) ---'
SELECT o.stato, count(*) AS ordini
FROM ordini_testata o
WHERE o.stato IN ('ESTRATTO', 'CONFERMATO')
  AND (
    EXISTS (SELECT 1 FROM anomalie a WHERE a.id_testata = o.id_testata
              AND a.stato IN ('APERTA','IN_GESTIONE') AND a.livello IN ('ERRORE','CRITICO'))
    OR EXISTS (SELECT 1 FROM supervisione_lookup     s WHERE s.id_testata = o.id_testata AND s.stato = 'PENDING')
    OR EXISTS (SELECT 1 FROM supervisione_espositore s WHERE s.id_testata = o.id_testata AND s.stato = 'PENDING')
    OR EXISTS (SELECT 1 FROM supervisione_listino    s WHERE s.id_testata = o.id_testata AND s.stato = 'PENDING')
    OR EXISTS (SELECT 1 FROM supervisione_aic        s WHERE s.id_testata = o.id_testata AND s.stato = 'PENDING')
    OR EXISTS (SELECT 1 FROM supervisione_prezzo     s WHERE s.id_testata = o.id_testata AND s.stato = 'PENDING')
    OR EXISTS (SELECT 1 FROM supervisione_erp        s WHERE s.id_testata = o.id_testata AND s.stato = 'PENDING')
  )
GROUP BY o.stato;

UPDATE ordini_testata o
SET stato = 'ANOMALIA',
    data_ultimo_aggiornamento = CURRENT_TIMESTAMP
WHERE o.stato IN ('ESTRATTO', 'CONFERMATO')
  AND (
    EXISTS (SELECT 1 FROM anomalie a WHERE a.id_testata = o.id_testata
              AND a.stato IN ('APERTA','IN_GESTIONE') AND a.livello IN ('ERRORE','CRITICO'))
    OR EXISTS (SELECT 1 FROM supervisione_lookup     s WHERE s.id_testata = o.id_testata AND s.stato = 'PENDING')
    OR EXISTS (SELECT 1 FROM supervisione_espositore s WHERE s.id_testata = o.id_testata AND s.stato = 'PENDING')
    OR EXISTS (SELECT 1 FROM supervisione_listino    s WHERE s.id_testata = o.id_testata AND s.stato = 'PENDING')
    OR EXISTS (SELECT 1 FROM supervisione_aic        s WHERE s.id_testata = o.id_testata AND s.stato = 'PENDING')
    OR EXISTS (SELECT 1 FROM supervisione_prezzo     s WHERE s.id_testata = o.id_testata AND s.stato = 'PENDING')
    OR EXISTS (SELECT 1 FROM supervisione_erp        s WHERE s.id_testata = o.id_testata AND s.stato = 'PENDING')
  );

\echo '--- DOPO (atteso: 0 righe) ---'
SELECT o.stato, count(*) AS ordini
FROM ordini_testata o
WHERE o.stato IN ('ESTRATTO', 'CONFERMATO')
  AND EXISTS (SELECT 1 FROM anomalie a WHERE a.id_testata = o.id_testata
                AND a.stato IN ('APERTA','IN_GESTIONE') AND a.livello IN ('ERRORE','CRITICO'))
GROUP BY o.stato;

-- Sostituire con ROLLBACK per una prova a vuoto.
COMMIT;
