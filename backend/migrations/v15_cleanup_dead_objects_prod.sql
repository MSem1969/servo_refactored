-- =============================================================================
-- SERV.O v15 - PULIZIA OGGETTI DB MORTI (allineamento PRODUZIONE)
-- =============================================================================
-- Scopo: riallineare lo schema di produzione a quello di sviluppo, dove la
-- stessa pulizia e' gia' stata fatta. Dopo il rilascio del 2026-07-28 i due
-- ambienti divergono (dev 50 tabelle / 5 viste, prod 55 / 8) e gli scostamenti
-- di schema producono diagnosi sbagliate: il 28/07 la vista v_dettagli_completi
-- presente in dev e assente in prod ha generato un falso allarme su un presunto
-- blocco della generazione tracciati.
--
-- NON e' la v12 di sviluppo: quella e' tarata sullo schema dev e proverebbe a
-- droppare 11 viste che in produzione non sono mai esistite. Qui si rimuove
-- SOLO cio' che in produzione esiste davvero, rilevato il 2026-07-28:
--   5 tabelle, tutte a 0 righe
--   3 viste, mai referenziate dal backend
--
-- Verifiche svolte sul codice in produzione (commit 73c7988), con grep separati
-- per singolo nome: ZERO riferimenti per tutti e 8 gli oggetti, eccetto le liste
-- di reset in routers/admin.py, ripulite nello stesso commit di questa migration.
-- Nessuna FK entrante, nessuna vista dipendente.
--
-- SICUREZZA: il blocco di controllo qui sotto ABORTISCE l'intera transazione se
-- una qualsiasi delle tabelle candidate contiene anche una sola riga. Non serve
-- fidarsi di un conteggio fatto ieri: la verifica avviene adesso, atomicamente.
--
-- PRIMA DI ESEGUIRE, dump dello schema (rete di sicurezza vera):
--   pg_dump -s -U <ruolo_app> -h <host> -d servo > schema_pre_v15.sql
--
-- Applicare con il ruolo applicativo (servo_user), non come superuser.
-- Rollback: v15_cleanup_dead_objects_prod_rollback.sql
-- =============================================================================

BEGIN;

-- -----------------------------------------------------------------------------
-- 0. CONTROLLO DI SICUREZZA - abortisce se qualcosa non e' vuoto
-- -----------------------------------------------------------------------------
DO $$
DECLARE
    t          text;
    n          bigint;
    presente   boolean;
    dipendenti text;
BEGIN
    FOREACH t IN ARRAY ARRAY['tracciati', 'tracciati_dettaglio',
                             'supervisione_unificata', 'backup_schedules',
                             'alembic_version']
    LOOP
        SELECT EXISTS (
            SELECT 1 FROM pg_class c
            JOIN pg_namespace ns ON ns.oid = c.relnamespace
            WHERE c.relname = t AND c.relkind = 'r'
              AND ns.nspname NOT IN ('pg_catalog', 'information_schema')
        ) INTO presente;

        IF NOT presente THEN
            RAISE NOTICE 'Tabella % gia'' assente, nulla da fare', t;
            CONTINUE;
        END IF;

        EXECUTE format('SELECT count(*) FROM %I', t) INTO n;
        IF n > 0 THEN
            RAISE EXCEPTION
                'ABORT: la tabella % contiene % righe. Non e'' codice morto: '
                'nessun DROP verra'' eseguito.', t, n;
        END IF;

        -- Qualche vista dipende da questa tabella? In produzione non risultava,
        -- ma se l'ambiente e' diverso da quello analizzato meglio fermarsi con
        -- un messaggio chiaro che schiantarsi a meta' con l'errore di Postgres.
        SELECT string_agg(DISTINCT v.relname, ', ') INTO dipendenti
        FROM pg_depend d
        JOIN pg_rewrite r ON r.oid = d.objid
        JOIN pg_class   v ON v.oid = r.ev_class
        JOIN pg_class   c ON c.oid = d.refobjid
        WHERE v.relkind = 'v' AND c.relname = t AND v.relname <> t;

        IF dipendenti IS NOT NULL THEN
            RAISE EXCEPTION
                'ABORT: la tabella % ha viste dipendenti (%). Valutarle una per '
                'una prima di procedere: nessun DROP verra'' eseguito.',
                t, dipendenti;
        END IF;

        RAISE NOTICE 'Tabella % verificata: vuota e senza dipendenze', t;
    END LOOP;
END $$;

-- -----------------------------------------------------------------------------
-- 1. VISTE (solo quelle realmente presenti in produzione)
-- -----------------------------------------------------------------------------
-- Reporting mai interrogato dal backend.
DROP VIEW IF EXISTS v_backup_dashboard;
DROP VIEW IF EXISTS v_backup_history_detail;
DROP VIEW IF EXISTS v_sync_status;

-- -----------------------------------------------------------------------------
-- 2. TABELLE
-- -----------------------------------------------------------------------------
-- I tracciati EDI sono tracciati da esportazioni/esportazioni_dettaglio:
-- queste due tabelle non sono mai state ne' scritte ne' lette.
DROP TABLE IF EXISTS tracciati_dettaglio;
DROP TABLE IF EXISTS tracciati;

-- Tabella pivot del refactoring "supervisione unificata", mai completato.
DROP TABLE IF EXISTS supervisione_unificata;

-- Schedulazione backup: lo scheduler reale sta in app/services/scheduler/.
DROP TABLE IF EXISTS backup_schedules;

-- Alembic non e' mai stato applicato: il meccanismo in uso e' migrations/*.sql.
DROP TABLE IF EXISTS alembic_version;

COMMIT;

-- =============================================================================
-- VERIFICA (attesa: 50 tabelle base, 5 viste - come in sviluppo)
-- =============================================================================
-- SELECT
--   (SELECT count(*) FROM information_schema.tables
--     WHERE table_type='BASE TABLE'
--       AND table_schema NOT IN ('pg_catalog','information_schema')) AS tabelle,
--   (SELECT count(*) FROM pg_views
--     WHERE schemaname NOT IN ('pg_catalog','information_schema'))   AS viste;
--
-- Le 5 viste superstiti devono essere: v_ordini_completi,
-- v_supervisione_pending, v_supervisione_grouped_pending,
-- v_supervisione_listino_pending, v_supervisione_lookup_pending.
