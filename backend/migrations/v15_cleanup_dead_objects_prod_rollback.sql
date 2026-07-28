-- =============================================================================
-- SERV.O v15 - ROLLBACK della pulizia oggetti DB morti (produzione)
-- =============================================================================
-- Ricrea gli 8 oggetti rimossi da v15_cleanup_dead_objects_prod.sql.
-- I dati non vengono ripristinati perche' non ce n'erano: tutte le tabelle
-- erano verificate vuote dal controllo di sicurezza della migration stessa.
--
-- ATTENZIONE - il DDL qui sotto e' stato estratto dal DB di SVILUPPO prima del
-- drop (pg_dump -s e pg_get_viewdef), non dalla produzione. Le due strutture
-- coincidono per quanto rilevato, ma per un ripristino fedele al byte usare il
-- dump dello schema fatto prima di applicare la migration:
--   pg_dump -s -U <ruolo_app> -h <host> -d servo > schema_pre_v15.sql
-- Questo file resta la via rapida quando quel dump non e' disponibile.
--
-- Le clausole OWNER sono omesse: gli oggetti apparterranno al ruolo che li crea,
-- che deve essere il ruolo applicativo.
-- =============================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS public.tracciati (
    id_tracciato integer NOT NULL,
    nome_file character varying(255) NOT NULL,
    tipo character varying(20) DEFAULT 'CSV'::character varying,
    num_righe integer DEFAULT 0,
    id_operatore integer,
    note text,
    data_generazione timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS public.tracciati_dettaglio (
    id integer NOT NULL,
    id_tracciato integer NOT NULL,
    id_testata integer,
    id_dettaglio integer
);

CREATE TABLE IF NOT EXISTS public.supervisione_unificata (
    id_supervisione integer NOT NULL,
    tipo_supervisione character varying(20) NOT NULL,
    id_testata integer NOT NULL,
    id_anomalia integer,
    id_dettaglio integer,
    codice_anomalia character varying(20),
    vendor character varying(50),
    pattern_signature text,
    stato character varying(20) DEFAULT 'PENDING'::character varying,
    operatore character varying(100),
    timestamp_creazione timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    timestamp_decisione timestamp without time zone,
    note text,
    payload jsonb DEFAULT '{}'::jsonb,
    CONSTRAINT supervisione_unificata_stato_check CHECK (((stato)::text = ANY (ARRAY[('PENDING'::character varying)::text, ('APPROVED'::character varying)::text, ('REJECTED'::character varying)::text, ('MODIFIED'::character varying)::text]))),
    CONSTRAINT supervisione_unificata_tipo_supervisione_check CHECK (((tipo_supervisione)::text = ANY (ARRAY[('AIC'::character varying)::text, ('LISTINO'::character varying)::text, ('PREZZO'::character varying)::text, ('LOOKUP'::character varying)::text, ('ESPOSITORE'::character varying)::text])))
);

CREATE TABLE IF NOT EXISTS public.backup_schedules (
    id_schedule integer NOT NULL,
    id_module integer NOT NULL,
    cron_expression character varying(50) NOT NULL,
    active boolean DEFAULT true,
    next_run timestamp without time zone,
    last_run timestamp without time zone,
    last_status character varying(20),
    options jsonb DEFAULT '{}'::jsonb,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone
);

CREATE TABLE IF NOT EXISTS public.alembic_version (
    version_num character varying(32) NOT NULL
);

CREATE OR REPLACE VIEW v_backup_dashboard AS
 SELECT m.id_module,
    m.nome,
    m.tier,
    m.titolo,
    m.enabled,
    m.configured,
    m.last_run,
    m.last_status,
    m.schedule_cron,
    s.nome AS storage_nome,
    s.tipo AS storage_tipo,
    s.stato AS storage_stato,
    ( SELECT count(*) AS count
           FROM backup_history h
          WHERE h.id_module = m.id_module AND h.started_at > (CURRENT_TIMESTAMP - '7 days'::interval)) AS backups_7d,
    ( SELECT count(*) AS count
           FROM backup_history h
          WHERE h.id_module = m.id_module AND h.status::text = 'failed'::text AND h.started_at > (CURRENT_TIMESTAMP - '7 days'::interval)) AS failures_7d,
    ( SELECT max(h.completed_at) AS max
           FROM backup_history h
          WHERE h.id_module = m.id_module AND h.status::text = 'success'::text) AS last_success,
    ( SELECT COALESCE(sum(h.file_size_bytes), 0::numeric) AS "coalesce"
           FROM backup_history h
          WHERE h.id_module = m.id_module AND h.status::text = 'success'::text) AS total_bytes
   FROM backup_modules m
     LEFT JOIN backup_storage s ON m.id_storage = s.id_storage
  ORDER BY m.tier;

CREATE OR REPLACE VIEW v_backup_history_detail AS
 SELECT h.id_backup,
    h.backup_type,
    h.file_name,
    h.file_size_bytes,
    pg_size_pretty(h.file_size_bytes) AS file_size_pretty,
    h.started_at,
    h.completed_at,
    h.duration_seconds,
    h.status,
    h.error_message,
    h.triggered_by,
    m.nome AS module_nome,
    m.titolo AS module_titolo,
    m.tier AS module_tier,
    s.nome AS storage_nome,
    s.tipo AS storage_tipo,
    o.username AS operator_username
   FROM backup_history h
     JOIN backup_modules m ON h.id_module = m.id_module
     LEFT JOIN backup_storage s ON h.id_storage = s.id_storage
     LEFT JOIN operatori o ON h.operator_id = o.id_operatore
  ORDER BY h.started_at DESC;

CREATE OR REPLACE VIEW v_sync_status AS
 SELECT sync_state.key,
    sync_state.last_sync,
    sync_state.last_url,
    sync_state.records_count,
    sync_state.etag,
        CASE
            WHEN sync_state.last_sync IS NULL THEN 'MAI_SINCRONIZZATO'::text
            WHEN sync_state.last_sync < (CURRENT_TIMESTAMP - '7 days'::interval) THEN 'OBSOLETO'::text
            WHEN sync_state.last_sync < (CURRENT_TIMESTAMP - '1 day'::interval) THEN 'DA_AGGIORNARE'::text
            ELSE 'AGGIORNATO'::text
        END AS stato,
    EXTRACT(epoch FROM CURRENT_TIMESTAMP - sync_state.last_sync::timestamp with time zone) / 3600::numeric AS ore_dalla_sync
   FROM sync_state
  ORDER BY sync_state.last_sync DESC;

COMMIT;
