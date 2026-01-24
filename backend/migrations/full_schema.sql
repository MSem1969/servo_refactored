--
-- PostgreSQL database dump
--

\restrict Bngijxh1A5Am7u7C9Y8f6taW8R4nwt0LMetlAjt7IL25l3OIuWoQDnH8UAd9NES

-- Dumped from database version 15.14 (Debian 15.14-0+deb12u1)
-- Dumped by pg_dump version 15.14 (Debian 15.14-0+deb12u1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: backup_update_timestamp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.backup_update_timestamp() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: acquisizioni; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.acquisizioni (
    id_acquisizione integer NOT NULL,
    nome_file_originale character varying(255) NOT NULL,
    nome_file_storage character varying(255) NOT NULL,
    percorso_storage text,
    hash_file character varying(64),
    hash_contenuto_pdf character varying(64),
    dimensione_bytes integer,
    mime_type character varying(100) DEFAULT 'application/pdf'::character varying,
    id_vendor integer,
    vendor_rilevato_auto boolean DEFAULT true,
    stato character varying(20) DEFAULT 'CARICATO'::character varying,
    num_ordini_estratti integer DEFAULT 0,
    messaggio_errore text,
    is_duplicato boolean DEFAULT false,
    id_acquisizione_originale integer,
    id_operatore_upload integer DEFAULT 1,
    data_upload timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    data_elaborazione timestamp without time zone,
    origine character varying(20) DEFAULT 'MANUALE'::character varying,
    id_email integer
);


--
-- Name: acquisizioni_id_acquisizione_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.acquisizioni_id_acquisizione_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: acquisizioni_id_acquisizione_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.acquisizioni_id_acquisizione_seq OWNED BY public.acquisizioni.id_acquisizione;


--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


--
-- Name: anagrafica_clienti; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.anagrafica_clienti (
    id_cliente integer NOT NULL,
    codice_cliente character varying(20) NOT NULL,
    ragione_sociale_1 character varying(100),
    ragione_sociale_2 character varying(100),
    indirizzo character varying(200),
    cap character varying(10),
    localita character varying(100),
    provincia character varying(3),
    partita_iva character varying(16),
    email character varying(200),
    categoria character varying(10),
    codice_farmacia character varying(20),
    codice_stato character varying(10),
    codice_pagamento character varying(10),
    id_tipo character varying(20),
    riferimento character varying(10),
    data_import timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    data_aggiornamento timestamp without time zone
);


--
-- Name: TABLE anagrafica_clienti; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.anagrafica_clienti IS 'Anagrafica clienti esterna - NON azzerare durante RESET';


--
-- Name: anagrafica_clienti_id_cliente_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.anagrafica_clienti_id_cliente_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: anagrafica_clienti_id_cliente_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.anagrafica_clienti_id_cliente_seq OWNED BY public.anagrafica_clienti.id_cliente;


--
-- Name: anagrafica_farmacie; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.anagrafica_farmacie (
    id_farmacia integer NOT NULL,
    min_id character varying(9) NOT NULL,
    codice_farmacia_asl character varying(20),
    partita_iva character varying(16),
    ragione_sociale character varying(255),
    indirizzo character varying(255),
    cap character varying(10),
    citta character varying(100),
    frazione character varying(100),
    provincia character varying(3),
    regione character varying(50),
    data_inizio_validita date,
    data_fine_validita date,
    attiva boolean DEFAULT true,
    fonte_dati character varying(50),
    data_import timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: anagrafica_farmacie_id_farmacia_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.anagrafica_farmacie_id_farmacia_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: anagrafica_farmacie_id_farmacia_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.anagrafica_farmacie_id_farmacia_seq OWNED BY public.anagrafica_farmacie.id_farmacia;


--
-- Name: anagrafica_parafarmacie; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.anagrafica_parafarmacie (
    id_parafarmacia integer NOT NULL,
    codice_sito character varying(20) NOT NULL,
    sito_logistico character varying(255),
    partita_iva character varying(16),
    indirizzo character varying(255),
    cap character varying(10),
    codice_comune character varying(10),
    citta character varying(100),
    codice_provincia character varying(3),
    provincia character varying(50),
    codice_regione character varying(3),
    regione character varying(50),
    data_inizio_validita date,
    data_fine_validita date,
    latitudine numeric,
    longitudine numeric,
    attiva boolean DEFAULT true,
    fonte_dati character varying(50),
    data_import timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: anagrafica_parafarmacie_id_parafarmacia_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.anagrafica_parafarmacie_id_parafarmacia_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: anagrafica_parafarmacie_id_parafarmacia_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.anagrafica_parafarmacie_id_parafarmacia_seq OWNED BY public.anagrafica_parafarmacie.id_parafarmacia;


--
-- Name: anomalie; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.anomalie (
    id_anomalia integer NOT NULL,
    id_testata integer,
    id_dettaglio integer,
    id_acquisizione integer,
    tipo_anomalia character varying(50) NOT NULL,
    livello character varying(20) DEFAULT 'ATTENZIONE'::character varying,
    codice_anomalia character varying(20),
    descrizione text,
    valore_anomalo text,
    stato character varying(20) DEFAULT 'APERTA'::character varying,
    id_operatore_gestione integer,
    note_risoluzione text,
    data_rilevazione timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    data_risoluzione timestamp without time zone,
    richiede_supervisione boolean DEFAULT false,
    pattern_signature character varying(100)
);


--
-- Name: anomalie_id_anomalia_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.anomalie_id_anomalia_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: anomalie_id_anomalia_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.anomalie_id_anomalia_seq OWNED BY public.anomalie.id_anomalia;


--
-- Name: app_sezioni; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.app_sezioni (
    codice_sezione character varying(50) NOT NULL,
    nome_display character varying(100) NOT NULL,
    descrizione text,
    icona character varying(50),
    ordine_menu integer DEFAULT 0,
    is_active boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: audit_modifiche; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_modifiche (
    id_audit integer NOT NULL,
    entita character varying(50) NOT NULL,
    id_entita integer NOT NULL,
    id_testata integer,
    campo_modificato character varying(100) NOT NULL,
    valore_precedente text,
    valore_nuovo text,
    fonte_modifica character varying(50) NOT NULL,
    id_operatore integer,
    username_operatore character varying(100),
    motivazione text,
    id_sessione character varying(100),
    ip_address character varying(50),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: audit_modifiche_id_audit_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.audit_modifiche_id_audit_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: audit_modifiche_id_audit_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.audit_modifiche_id_audit_seq OWNED BY public.audit_modifiche.id_audit;


--
-- Name: backup_history; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.backup_history (
    id_backup integer NOT NULL,
    id_module integer NOT NULL,
    id_storage integer,
    backup_type character varying(20) NOT NULL,
    file_path text,
    file_name character varying(255),
    file_size_bytes bigint,
    file_checksum character varying(64),
    started_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    completed_at timestamp without time zone,
    duration_seconds integer,
    status character varying(20) DEFAULT 'running'::character varying NOT NULL,
    error_message text,
    metadata jsonb DEFAULT '{}'::jsonb,
    triggered_by character varying(50) DEFAULT 'scheduled'::character varying,
    operator_id integer,
    CONSTRAINT backup_history_backup_type_check CHECK (((backup_type)::text = ANY ((ARRAY['full'::character varying, 'incremental'::character varying, 'wal'::character varying, 'sync'::character varying, 'upload'::character varying])::text[]))),
    CONSTRAINT backup_history_status_check CHECK (((status)::text = ANY ((ARRAY['running'::character varying, 'success'::character varying, 'failed'::character varying, 'cancelled'::character varying])::text[])))
);


--
-- Name: backup_history_id_backup_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.backup_history_id_backup_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: backup_history_id_backup_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.backup_history_id_backup_seq OWNED BY public.backup_history.id_backup;


--
-- Name: backup_modules; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.backup_modules (
    id_module integer NOT NULL,
    nome character varying(50) NOT NULL,
    tier integer DEFAULT 1 NOT NULL,
    titolo character varying(100) NOT NULL,
    descrizione text,
    enabled boolean DEFAULT false,
    configured boolean DEFAULT false,
    config jsonb DEFAULT '{}'::jsonb,
    id_storage integer,
    schedule_cron character varying(50),
    retention_days integer DEFAULT 7,
    last_run timestamp without time zone,
    last_status character varying(20),
    last_error text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone,
    updated_by integer,
    CONSTRAINT backup_modules_last_status_check CHECK (((last_status)::text = ANY ((ARRAY['success'::character varying, 'failed'::character varying, 'running'::character varying, 'skipped'::character varying])::text[]))),
    CONSTRAINT backup_modules_tier_check CHECK (((tier >= 1) AND (tier <= 6)))
);


--
-- Name: backup_modules_id_module_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.backup_modules_id_module_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: backup_modules_id_module_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.backup_modules_id_module_seq OWNED BY public.backup_modules.id_module;


--
-- Name: backup_operations_log; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.backup_operations_log (
    id_log integer NOT NULL,
    operation character varying(50) NOT NULL,
    id_module integer,
    id_backup integer,
    details jsonb,
    status character varying(20) NOT NULL,
    message text,
    operator_id integer,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT backup_operations_log_status_check CHECK (((status)::text = ANY ((ARRAY['success'::character varying, 'failed'::character varying, 'info'::character varying, 'warning'::character varying])::text[])))
);


--
-- Name: backup_operations_log_id_log_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.backup_operations_log_id_log_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: backup_operations_log_id_log_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.backup_operations_log_id_log_seq OWNED BY public.backup_operations_log.id_log;


--
-- Name: backup_schedules; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.backup_schedules (
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


--
-- Name: backup_schedules_id_schedule_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.backup_schedules_id_schedule_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: backup_schedules_id_schedule_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.backup_schedules_id_schedule_seq OWNED BY public.backup_schedules.id_schedule;


--
-- Name: backup_storage; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.backup_storage (
    id_storage integer NOT NULL,
    nome character varying(100) NOT NULL,
    tipo character varying(20) NOT NULL,
    path text NOT NULL,
    config jsonb DEFAULT '{}'::jsonb,
    capacity_gb integer,
    used_gb integer,
    stato character varying(20) DEFAULT 'active'::character varying,
    ultimo_check timestamp without time zone,
    ultimo_errore text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    created_by integer,
    updated_at timestamp without time zone,
    CONSTRAINT backup_storage_stato_check CHECK (((stato)::text = ANY ((ARRAY['active'::character varying, 'inactive'::character varying, 'error'::character varying, 'full'::character varying])::text[]))),
    CONSTRAINT backup_storage_tipo_check CHECK (((tipo)::text = ANY ((ARRAY['local'::character varying, 'nas'::character varying, 's3'::character varying, 'gcs'::character varying, 'azure'::character varying])::text[])))
);


--
-- Name: backup_storage_id_storage_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.backup_storage_id_storage_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: backup_storage_id_storage_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.backup_storage_id_storage_seq OWNED BY public.backup_storage.id_storage;


--
-- Name: criteri_ordinari_aic; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.criteri_ordinari_aic (
    pattern_signature text NOT NULL,
    pattern_descrizione text,
    vendor text NOT NULL,
    descrizione_normalizzata text NOT NULL,
    count_approvazioni integer DEFAULT 0,
    is_ordinario boolean DEFAULT false,
    data_prima_occorrenza timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    data_promozione timestamp without time zone,
    operatori_approvatori text,
    codice_aic_default text
);


--
-- Name: criteri_ordinari_espositore; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.criteri_ordinari_espositore (
    pattern_signature character varying(100) NOT NULL,
    pattern_descrizione text,
    vendor character varying(50) NOT NULL,
    codice_anomalia character varying(20),
    codice_espositore character varying(20),
    pezzi_per_unita integer,
    tipo_scostamento character varying(20),
    fascia_scostamento character varying(20),
    count_approvazioni integer DEFAULT 0,
    is_ordinario boolean DEFAULT false,
    data_prima_occorrenza timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    data_promozione timestamp without time zone,
    operatori_approvatori text,
    descrizione_normalizzata character varying(255),
    child_sequence_json jsonb,
    num_child_attesi integer DEFAULT 0,
    total_applications integer DEFAULT 0,
    successful_applications integer DEFAULT 0
);


--
-- Name: criteri_ordinari_listino; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.criteri_ordinari_listino (
    pattern_signature text NOT NULL,
    pattern_descrizione text,
    vendor text NOT NULL,
    codice_anomalia text NOT NULL,
    codice_aic text,
    count_approvazioni integer DEFAULT 0,
    is_ordinario boolean DEFAULT false,
    data_prima_occorrenza timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    data_promozione timestamp without time zone,
    operatori_approvatori text,
    prezzo_netto_pattern numeric(10,2),
    prezzo_pubblico_pattern numeric(10,2),
    sconto_1_pattern numeric(5,2),
    sconto_2_pattern numeric(5,2),
    aliquota_iva_pattern numeric(5,2),
    azione_pattern text
);


--
-- Name: criteri_ordinari_lookup; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.criteri_ordinari_lookup (
    pattern_signature text NOT NULL,
    pattern_descrizione text,
    vendor text NOT NULL,
    codice_anomalia text NOT NULL,
    partita_iva_pattern text,
    count_approvazioni integer DEFAULT 0,
    is_ordinario boolean DEFAULT false,
    data_prima_occorrenza timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    data_promozione timestamp without time zone,
    operatori_approvatori text,
    min_id_default text,
    id_farmacia_default integer
);


--
-- Name: crm_allegati; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.crm_allegati (
    id_allegato integer NOT NULL,
    id_ticket integer NOT NULL,
    id_messaggio integer,
    nome_file character varying(255) NOT NULL,
    path_file character varying(500) NOT NULL,
    mime_type character varying(100),
    dimensione integer,
    id_operatore integer,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: crm_allegati_id_allegato_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.crm_allegati_id_allegato_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: crm_allegati_id_allegato_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.crm_allegati_id_allegato_seq OWNED BY public.crm_allegati.id_allegato;


--
-- Name: crm_messaggi; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.crm_messaggi (
    id_messaggio integer NOT NULL,
    id_ticket integer NOT NULL,
    contenuto text NOT NULL,
    tipo character varying(20) DEFAULT 'risposta'::character varying,
    id_operatore integer,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    is_admin_reply boolean DEFAULT false
);


--
-- Name: crm_messaggi_id_messaggio_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.crm_messaggi_id_messaggio_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: crm_messaggi_id_messaggio_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.crm_messaggi_id_messaggio_seq OWNED BY public.crm_messaggi.id_messaggio;


--
-- Name: crm_tickets; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.crm_tickets (
    id_ticket integer NOT NULL,
    oggetto character varying(255) NOT NULL,
    descrizione text,
    stato character varying(50) DEFAULT 'aperto'::character varying,
    priorita character varying(20) DEFAULT 'normale'::character varying,
    categoria character varying(50),
    email_notifica character varying(255),
    id_operatore integer,
    closed_by integer,
    closed_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    pagina_origine character varying(50),
    pagina_dettaglio character varying(200)
);


--
-- Name: crm_tickets_id_ticket_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.crm_tickets_id_ticket_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: crm_tickets_id_ticket_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.crm_tickets_id_ticket_seq OWNED BY public.crm_tickets.id_ticket;


--
-- Name: email_acquisizioni; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.email_acquisizioni (
    id_email integer NOT NULL,
    message_id character varying(255) NOT NULL,
    gmail_id character varying(100),
    subject character varying(500),
    sender_email character varying(255) NOT NULL,
    sender_name character varying(255),
    received_date timestamp without time zone NOT NULL,
    attachment_filename character varying(255) NOT NULL,
    attachment_size integer,
    attachment_hash character varying(64) NOT NULL,
    id_acquisizione integer,
    stato character varying(20) DEFAULT 'DA_PROCESSARE'::character varying,
    data_elaborazione timestamp without time zone,
    errore_messaggio text,
    num_retry integer DEFAULT 0,
    label_applicata character varying(100),
    marcata_come_letta boolean DEFAULT false,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: email_acquisizioni_id_email_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.email_acquisizioni_id_email_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: email_acquisizioni_id_email_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.email_acquisizioni_id_email_seq OWNED BY public.email_acquisizioni.id_email;


--
-- Name: esportazioni; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.esportazioni (
    id_esportazione integer NOT NULL,
    nome_tracciato_generato character varying(255),
    data_tracciato date,
    nome_file_to_t character varying(255),
    nome_file_to_d character varying(255),
    num_testate integer DEFAULT 0,
    num_dettagli integer DEFAULT 0,
    stato character varying(20) DEFAULT 'GENERATO'::character varying,
    note text,
    data_generazione timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: esportazioni_dettaglio; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.esportazioni_dettaglio (
    id integer NOT NULL,
    id_esportazione integer NOT NULL,
    id_testata integer
);


--
-- Name: esportazioni_dettaglio_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.esportazioni_dettaglio_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: esportazioni_dettaglio_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.esportazioni_dettaglio_id_seq OWNED BY public.esportazioni_dettaglio.id;


--
-- Name: esportazioni_id_esportazione_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.esportazioni_id_esportazione_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: esportazioni_id_esportazione_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.esportazioni_id_esportazione_seq OWNED BY public.esportazioni.id_esportazione;


--
-- Name: listini_vendor; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.listini_vendor (
    id_listino integer NOT NULL,
    vendor text NOT NULL,
    codice_aic text NOT NULL,
    descrizione text,
    sconto_1 numeric(5,2),
    sconto_2 numeric(5,2),
    sconto_3 numeric(5,2),
    sconto_4 numeric(5,2),
    prezzo_netto numeric(10,2),
    prezzo_scontare numeric(10,2),
    prezzo_pubblico numeric(10,2),
    aliquota_iva numeric(5,2),
    scorporo_iva text DEFAULT 'S'::text,
    prezzo_csv_originale numeric(10,2),
    prezzo_pubblico_csv numeric(10,2),
    data_decorrenza date,
    attivo boolean DEFAULT true,
    data_import timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    fonte_file text
);


--
-- Name: listini_vendor_id_listino_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.listini_vendor_id_listino_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: listini_vendor_id_listino_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.listini_vendor_id_listino_seq OWNED BY public.listini_vendor.id_listino;


--
-- Name: log_criteri_applicati; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.log_criteri_applicati (
    id_log integer NOT NULL,
    id_testata integer,
    id_supervisione integer,
    pattern_signature character varying(100) NOT NULL,
    azione character varying(50),
    applicato_automaticamente boolean DEFAULT false,
    operatore character varying(50),
    note text,
    "timestamp" timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: log_criteri_applicati_id_log_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.log_criteri_applicati_id_log_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: log_criteri_applicati_id_log_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.log_criteri_applicati_id_log_seq OWNED BY public.log_criteri_applicati.id_log;


--
-- Name: log_operazioni; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.log_operazioni (
    id_log integer NOT NULL,
    tipo_operazione character varying(50) NOT NULL,
    entita character varying(50),
    id_entita integer,
    descrizione text,
    dati_json jsonb,
    id_operatore integer,
    "timestamp" timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    action_category character varying(50),
    username_snapshot character varying(100)
);


--
-- Name: log_operazioni_id_log_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.log_operazioni_id_log_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: log_operazioni_id_log_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.log_operazioni_id_log_seq OWNED BY public.log_operazioni.id_log;


--
-- Name: operatori; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.operatori (
    id_operatore integer NOT NULL,
    username character varying(50) NOT NULL,
    password_hash character varying(255) DEFAULT ''::character varying,
    nome character varying(100),
    cognome character varying(100),
    email character varying(255),
    ruolo character varying(20) DEFAULT 'operatore'::character varying,
    attivo boolean DEFAULT true,
    data_creazione timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    created_by_operatore integer,
    updated_at timestamp without time zone,
    last_login_at timestamp without time zone,
    disabled_at timestamp without time zone,
    disabled_by_operatore integer,
    disable_reason text,
    last_login_ip character varying(50),
    data_nascita date,
    avatar_base64 text,
    avatar_mime_type character varying(50) DEFAULT 'image/jpeg'::character varying
);


--
-- Name: operatori_id_operatore_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.operatori_id_operatore_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: operatori_id_operatore_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.operatori_id_operatore_seq OWNED BY public.operatori.id_operatore;


--
-- Name: ordini_dettaglio; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ordini_dettaglio (
    id_dettaglio integer NOT NULL,
    id_testata integer NOT NULL,
    n_riga integer NOT NULL,
    codice_aic character varying(10),
    codice_originale character varying(20),
    codice_materiale character varying(20),
    descrizione character varying(100),
    tipo_posizione character varying(20) DEFAULT ''::character varying,
    q_venduta integer DEFAULT 0,
    q_sconto_merce integer DEFAULT 0,
    q_omaggio integer DEFAULT 0,
    data_consegna_riga date,
    sconto_1 numeric DEFAULT 0,
    sconto_2 numeric DEFAULT 0,
    sconto_3 numeric DEFAULT 0,
    sconto_4 numeric DEFAULT 0,
    prezzo_netto numeric DEFAULT 0,
    prezzo_scontare numeric DEFAULT 0,
    prezzo_pubblico numeric DEFAULT 0,
    prezzo_listino numeric DEFAULT 0,
    valore_netto numeric DEFAULT 0,
    aliquota_iva numeric DEFAULT 10,
    scorporo_iva character varying(1) DEFAULT 'N'::bpchar,
    note_allestimento text,
    is_espositore boolean DEFAULT false,
    is_child boolean DEFAULT false,
    is_no_aic boolean DEFAULT false,
    tipo_riga character varying(20) DEFAULT ''::character varying,
    id_parent_espositore integer,
    espositore_metadata jsonb,
    stato_riga character varying(20) DEFAULT 'ESTRATTO'::character varying,
    richiede_supervisione boolean DEFAULT false,
    id_supervisione integer,
    confermato_da character varying(50),
    data_conferma timestamp without time zone,
    note_supervisione text,
    modificato_manualmente boolean DEFAULT false,
    valori_originali jsonb,
    q_originale integer DEFAULT 0,
    q_esportata integer DEFAULT 0,
    q_residua integer DEFAULT 0,
    num_esportazioni integer DEFAULT 0,
    ultima_esportazione timestamp without time zone,
    id_ultima_esportazione integer,
    q_evasa integer DEFAULT 0,
    q_da_evadere integer DEFAULT 0,
    codice_aic_inserito text,
    descrizione_estratta character varying(200),
    fonte_codice_aic character varying(50),
    fonte_quantita character varying(50)
);


--
-- Name: ordini_dettaglio_id_dettaglio_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.ordini_dettaglio_id_dettaglio_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: ordini_dettaglio_id_dettaglio_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.ordini_dettaglio_id_dettaglio_seq OWNED BY public.ordini_dettaglio.id_dettaglio;


--
-- Name: ordini_testata; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ordini_testata (
    id_testata integer NOT NULL,
    id_acquisizione integer NOT NULL,
    id_vendor integer NOT NULL,
    numero_ordine_vendor character varying(50) NOT NULL,
    data_ordine date,
    data_consegna date,
    partita_iva_estratta character varying(16),
    codice_ministeriale_estratto character varying(9),
    ragione_sociale_1 character varying(100),
    ragione_sociale_2 character varying(100),
    indirizzo character varying(100),
    cap character varying(10),
    citta character varying(100),
    provincia character varying(3),
    nome_agente character varying(100),
    gg_dilazione_1 integer DEFAULT 90,
    gg_dilazione_2 integer,
    gg_dilazione_3 integer,
    note_ordine text,
    note_ddt text,
    id_farmacia_lookup integer,
    id_parafarmacia_lookup integer,
    lookup_method character varying(20),
    lookup_source character varying(20) DEFAULT 'FARMACIA'::character varying,
    lookup_score integer,
    chiave_univoca_ordine character varying(64),
    is_ordine_duplicato boolean DEFAULT false,
    id_testata_originale integer,
    stato character varying(20) DEFAULT 'ESTRATTO'::character varying,
    data_estrazione timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    data_validazione timestamp without time zone,
    validato_da character varying(50),
    righe_totali integer DEFAULT 0,
    righe_confermate integer DEFAULT 0,
    righe_in_supervisione integer DEFAULT 0,
    data_ultimo_aggiornamento timestamp without time zone,
    ragione_sociale_1_estratta character varying(100),
    indirizzo_estratto character varying(100),
    cap_estratto character varying(10),
    citta_estratta character varying(100),
    provincia_estratta character varying(3),
    data_ordine_estratta date,
    data_consegna_estratta date,
    fonte_anagrafica character varying(20),
    data_modifica_anagrafica timestamp without time zone,
    operatore_modifica_anagrafica character varying(100),
    valore_totale_netto numeric(12,2)
);


--
-- Name: ordini_testata_id_testata_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.ordini_testata_id_testata_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: ordini_testata_id_testata_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.ordini_testata_id_testata_seq OWNED BY public.ordini_testata.id_testata;


--
-- Name: permessi_ruolo; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.permessi_ruolo (
    id_permesso integer NOT NULL,
    ruolo character varying(20) NOT NULL,
    codice_sezione character varying(50) NOT NULL,
    can_view boolean DEFAULT false,
    can_edit boolean DEFAULT false,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_by character varying(100)
);


--
-- Name: permessi_ruolo_id_permesso_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.permessi_ruolo_id_permesso_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: permessi_ruolo_id_permesso_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.permessi_ruolo_id_permesso_seq OWNED BY public.permessi_ruolo.id_permesso;


--
-- Name: sessione_attivita; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sessione_attivita (
    id integer NOT NULL,
    id_operatore integer NOT NULL,
    id_session integer,
    sezione character varying(50) NOT NULL,
    ultimo_heartbeat timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    durata_secondi integer DEFAULT 0,
    data_riferimento date DEFAULT CURRENT_DATE NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: sessione_attivita_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.sessione_attivita_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: sessione_attivita_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.sessione_attivita_id_seq OWNED BY public.sessione_attivita.id;


--
-- Name: supervisione_aic; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.supervisione_aic (
    id_supervisione integer NOT NULL,
    id_testata integer NOT NULL,
    id_anomalia integer,
    id_dettaglio integer,
    codice_anomalia text DEFAULT 'AIC-A01'::text NOT NULL,
    vendor text NOT NULL,
    n_riga integer,
    descrizione_prodotto text,
    descrizione_normalizzata text,
    codice_originale text,
    pattern_signature text,
    stato text DEFAULT 'PENDING'::text,
    operatore text,
    timestamp_creazione timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    timestamp_decisione timestamp without time zone,
    note text,
    codice_aic_assegnato text,
    CONSTRAINT supervisione_aic_stato_check CHECK ((stato = ANY (ARRAY['PENDING'::text, 'APPROVED'::text, 'REJECTED'::text])))
);


--
-- Name: supervisione_aic_id_supervisione_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.supervisione_aic_id_supervisione_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: supervisione_aic_id_supervisione_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.supervisione_aic_id_supervisione_seq OWNED BY public.supervisione_aic.id_supervisione;


--
-- Name: supervisione_espositore; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.supervisione_espositore (
    id_supervisione integer NOT NULL,
    id_testata integer NOT NULL,
    id_anomalia integer,
    codice_anomalia character varying(20) NOT NULL,
    codice_espositore character varying(20),
    descrizione_espositore character varying(255),
    pezzi_attesi integer DEFAULT 0,
    pezzi_trovati integer DEFAULT 0,
    valore_calcolato numeric DEFAULT 0,
    pattern_signature character varying(100),
    stato character varying(20) DEFAULT 'PENDING'::character varying,
    operatore character varying(50),
    timestamp_creazione timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    timestamp_decisione timestamp without time zone,
    note text,
    modifiche_manuali_json jsonb
);


--
-- Name: supervisione_espositore_id_supervisione_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.supervisione_espositore_id_supervisione_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: supervisione_espositore_id_supervisione_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.supervisione_espositore_id_supervisione_seq OWNED BY public.supervisione_espositore.id_supervisione;


--
-- Name: supervisione_listino; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.supervisione_listino (
    id_supervisione integer NOT NULL,
    id_testata integer NOT NULL,
    id_dettaglio integer,
    id_anomalia integer,
    codice_anomalia character varying(20),
    vendor character varying(50),
    codice_aic character varying(20),
    n_riga integer,
    descrizione_prodotto character varying(200),
    prezzo_estratto numeric(10,2),
    prezzo_listino numeric(10,2),
    prezzo_proposto numeric(10,2),
    pattern_signature character varying(255),
    stato character varying(20) DEFAULT 'PENDING'::character varying,
    operatore character varying(100),
    timestamp_creazione timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    timestamp_decisione timestamp without time zone,
    note text,
    azione character varying(50)
);


--
-- Name: supervisione_listino_id_supervisione_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.supervisione_listino_id_supervisione_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: supervisione_listino_id_supervisione_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.supervisione_listino_id_supervisione_seq OWNED BY public.supervisione_listino.id_supervisione;


--
-- Name: supervisione_lookup; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.supervisione_lookup (
    id_supervisione integer NOT NULL,
    id_testata integer NOT NULL,
    id_anomalia integer,
    codice_anomalia character varying(20),
    vendor character varying(50),
    partita_iva_estratta character varying(20),
    lookup_method character varying(50),
    lookup_score integer,
    min_id_assegnato character varying(20),
    id_farmacia_assegnata integer,
    id_parafarmacia_assegnata integer,
    pattern_signature character varying(255),
    stato character varying(20) DEFAULT 'PENDING'::character varying,
    operatore character varying(100),
    timestamp_creazione timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    timestamp_decisione timestamp without time zone,
    note text
);


--
-- Name: supervisione_lookup_id_supervisione_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.supervisione_lookup_id_supervisione_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: supervisione_lookup_id_supervisione_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.supervisione_lookup_id_supervisione_seq OWNED BY public.supervisione_lookup.id_supervisione;


--
-- Name: supervisione_prezzo; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.supervisione_prezzo (
    id_supervisione integer NOT NULL,
    id_testata integer NOT NULL,
    id_anomalia integer,
    codice_anomalia text DEFAULT 'PRICE-A01'::text,
    vendor text,
    numero_righe_coinvolte integer,
    pattern_signature text,
    stato text DEFAULT 'PENDING'::text,
    operatore text,
    timestamp_creazione timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    timestamp_decisione timestamp without time zone,
    note text
);


--
-- Name: supervisione_prezzo_id_supervisione_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.supervisione_prezzo_id_supervisione_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: supervisione_prezzo_id_supervisione_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.supervisione_prezzo_id_supervisione_seq OWNED BY public.supervisione_prezzo.id_supervisione;


--
-- Name: sync_state; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sync_state (
    key character varying(50) NOT NULL,
    etag character varying(100),
    last_modified character varying(100),
    last_sync timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    last_url text,
    records_count integer DEFAULT 0,
    extra_data jsonb DEFAULT '{}'::jsonb
);


--
-- Name: tracciati; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tracciati (
    id_tracciato integer NOT NULL,
    nome_file character varying(255) NOT NULL,
    tipo character varying(20) DEFAULT 'CSV'::character varying,
    num_righe integer DEFAULT 0,
    id_operatore integer,
    note text,
    data_generazione timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: tracciati_dettaglio; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tracciati_dettaglio (
    id integer NOT NULL,
    id_tracciato integer NOT NULL,
    id_testata integer,
    id_dettaglio integer
);


--
-- Name: tracciati_dettaglio_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.tracciati_dettaglio_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: tracciati_dettaglio_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.tracciati_dettaglio_id_seq OWNED BY public.tracciati_dettaglio.id;


--
-- Name: tracciati_id_tracciato_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.tracciati_id_tracciato_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: tracciati_id_tracciato_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.tracciati_id_tracciato_seq OWNED BY public.tracciati.id_tracciato;


--
-- Name: user_sessions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_sessions (
    id_session integer NOT NULL,
    id_operatore integer NOT NULL,
    token_hash character varying(255) NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    expires_at timestamp without time zone NOT NULL,
    revoked_at timestamp without time zone,
    revoked_by_operatore integer,
    ip_address character varying(45),
    user_agent text
);


--
-- Name: user_sessions_id_session_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.user_sessions_id_session_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: user_sessions_id_session_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.user_sessions_id_session_seq OWNED BY public.user_sessions.id_session;


--
-- Name: v_backup_dashboard; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.v_backup_dashboard AS
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
           FROM public.backup_history h
          WHERE ((h.id_module = m.id_module) AND (h.started_at > (CURRENT_TIMESTAMP - '7 days'::interval)))) AS backups_7d,
    ( SELECT count(*) AS count
           FROM public.backup_history h
          WHERE ((h.id_module = m.id_module) AND ((h.status)::text = 'failed'::text) AND (h.started_at > (CURRENT_TIMESTAMP - '7 days'::interval)))) AS failures_7d,
    ( SELECT max(h.completed_at) AS max
           FROM public.backup_history h
          WHERE ((h.id_module = m.id_module) AND ((h.status)::text = 'success'::text))) AS last_success,
    ( SELECT COALESCE(sum(h.file_size_bytes), (0)::numeric) AS "coalesce"
           FROM public.backup_history h
          WHERE ((h.id_module = m.id_module) AND ((h.status)::text = 'success'::text))) AS total_bytes
   FROM (public.backup_modules m
     LEFT JOIN public.backup_storage s ON ((m.id_storage = s.id_storage)))
  ORDER BY m.tier;


--
-- Name: v_backup_history_detail; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.v_backup_history_detail AS
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
   FROM (((public.backup_history h
     JOIN public.backup_modules m ON ((h.id_module = m.id_module)))
     LEFT JOIN public.backup_storage s ON ((h.id_storage = s.id_storage)))
     LEFT JOIN public.operatori o ON ((h.operator_id = o.id_operatore)))
  ORDER BY h.started_at DESC;


--
-- Name: vendor; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.vendor (
    id_vendor integer NOT NULL,
    codice_vendor character varying(50) NOT NULL,
    ragione_sociale character varying(255),
    partita_iva_vendor character varying(16),
    linea_offerta character varying(100),
    note_estrazione text,
    attivo boolean DEFAULT true,
    data_inserimento timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: v_ordini_completi; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.v_ordini_completi AS
 SELECT ot.id_testata,
    ot.id_acquisizione,
    v.codice_vendor AS vendor,
    ot.numero_ordine_vendor,
    ot.data_ordine,
    ot.data_consegna,
    ot.stato,
    COALESCE(af.min_id, ot.codice_ministeriale_estratto) AS min_id,
    COALESCE(af.partita_iva, ot.partita_iva_estratta) AS partita_iva,
    COALESCE(af.ragione_sociale, ot.ragione_sociale_1) AS ragione_sociale,
    ot.ragione_sociale_1,
    ot.ragione_sociale_2,
    ot.indirizzo,
    ot.cap,
    ot.citta,
    ot.provincia,
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
   FROM (((public.ordini_testata ot
     LEFT JOIN public.vendor v ON ((ot.id_vendor = v.id_vendor)))
     LEFT JOIN public.anagrafica_farmacie af ON ((ot.id_farmacia_lookup = af.id_farmacia)))
     LEFT JOIN public.acquisizioni a ON ((ot.id_acquisizione = a.id_acquisizione)));


--
-- Name: v_supervisione_grouped_pending; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.v_supervisione_grouped_pending AS
 WITH all_supervisions AS (
         SELECT se.pattern_signature,
            'espositore'::text AS tipo_supervisione,
            se.codice_anomalia,
            v.codice_vendor AS vendor,
            se.id_supervisione,
            se.id_testata,
            se.stato,
            ot.numero_ordine_vendor,
            ot.ragione_sociale_1,
            se.timestamp_creazione,
            COALESCE(coe.count_approvazioni, 0) AS pattern_count,
            COALESCE(coe.is_ordinario, false) AS pattern_ordinario,
            coe.pattern_descrizione,
            se.descrizione_espositore AS descrizione_prodotto,
            se.codice_espositore AS codice_aic
           FROM (((public.supervisione_espositore se
             JOIN public.ordini_testata ot ON ((se.id_testata = ot.id_testata)))
             JOIN public.vendor v ON ((ot.id_vendor = v.id_vendor)))
             LEFT JOIN public.criteri_ordinari_espositore coe ON (((se.pattern_signature)::text = (coe.pattern_signature)::text)))
          WHERE ((se.stato)::text = 'PENDING'::text)
        UNION ALL
         SELECT sl.pattern_signature,
            'listino'::text AS tipo_supervisione,
            sl.codice_anomalia,
            sl.vendor,
            sl.id_supervisione,
            sl.id_testata,
            sl.stato,
            ot.numero_ordine_vendor,
            ot.ragione_sociale_1,
            sl.timestamp_creazione,
            COALESCE(col.count_approvazioni, 0) AS pattern_count,
            COALESCE(col.is_ordinario, false) AS pattern_ordinario,
            col.pattern_descrizione,
            sl.descrizione_prodotto,
            sl.codice_aic
           FROM ((public.supervisione_listino sl
             JOIN public.ordini_testata ot ON ((sl.id_testata = ot.id_testata)))
             LEFT JOIN public.criteri_ordinari_listino col ON (((sl.pattern_signature)::text = col.pattern_signature)))
          WHERE ((sl.stato)::text = 'PENDING'::text)
        UNION ALL
         SELECT slk.pattern_signature,
            'lookup'::text AS tipo_supervisione,
            slk.codice_anomalia,
            slk.vendor,
            slk.id_supervisione,
            slk.id_testata,
            slk.stato,
            ot.numero_ordine_vendor,
            ot.ragione_sociale_1,
            slk.timestamp_creazione,
            COALESCE(colk.count_approvazioni, 0) AS pattern_count,
            COALESCE(colk.is_ordinario, false) AS pattern_ordinario,
            colk.pattern_descrizione,
            ot.ragione_sociale_1 AS descrizione_prodotto,
            slk.partita_iva_estratta AS codice_aic
           FROM ((public.supervisione_lookup slk
             JOIN public.ordini_testata ot ON ((slk.id_testata = ot.id_testata)))
             LEFT JOIN public.criteri_ordinari_lookup colk ON (((slk.pattern_signature)::text = colk.pattern_signature)))
          WHERE ((slk.stato)::text = 'PENDING'::text)
        UNION ALL
         SELECT saic.pattern_signature,
            'aic'::text AS tipo_supervisione,
            saic.codice_anomalia,
            COALESCE(saic.vendor, 'UNKNOWN'::text) AS vendor,
            saic.id_supervisione,
            saic.id_testata,
            saic.stato,
            ot.numero_ordine_vendor,
            ot.ragione_sociale_1,
            saic.timestamp_creazione,
            COALESCE(coaic.count_approvazioni, 0) AS pattern_count,
            COALESCE(coaic.is_ordinario, false) AS pattern_ordinario,
            coaic.pattern_descrizione,
            saic.descrizione_prodotto,
            saic.codice_originale AS codice_aic
           FROM ((public.supervisione_aic saic
             JOIN public.ordini_testata ot ON ((saic.id_testata = ot.id_testata)))
             LEFT JOIN public.criteri_ordinari_aic coaic ON ((saic.pattern_signature = coaic.pattern_signature)))
          WHERE (saic.stato = 'PENDING'::text)
        )
 SELECT all_supervisions.pattern_signature,
    all_supervisions.tipo_supervisione,
    all_supervisions.codice_anomalia,
    all_supervisions.vendor,
    count(*) AS total_count,
    array_agg(DISTINCT all_supervisions.id_testata) AS affected_order_ids,
    array_agg(all_supervisions.id_supervisione) AS supervision_ids,
    max(all_supervisions.pattern_count) AS pattern_count,
    bool_or(all_supervisions.pattern_ordinario) AS pattern_ordinario,
    max(all_supervisions.pattern_descrizione) AS pattern_descrizione,
    array_agg(DISTINCT all_supervisions.numero_ordine_vendor) AS affected_orders_preview,
    array_agg(DISTINCT all_supervisions.ragione_sociale_1) AS affected_clients_preview,
    min(all_supervisions.timestamp_creazione) AS first_occurrence,
    (array_agg(all_supervisions.descrizione_prodotto ORDER BY all_supervisions.timestamp_creazione))[1] AS descrizione_prodotto,
    (array_agg(all_supervisions.codice_aic ORDER BY all_supervisions.timestamp_creazione))[1] AS codice_aic
   FROM all_supervisions
  GROUP BY all_supervisions.pattern_signature, all_supervisions.tipo_supervisione, all_supervisions.codice_anomalia, all_supervisions.vendor
  ORDER BY (min(all_supervisions.timestamp_creazione)) DESC;


--
-- Name: v_supervisione_listino_pending; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.v_supervisione_listino_pending AS
 SELECT sl.id_supervisione,
    sl.id_testata,
    sl.codice_anomalia,
    sl.vendor,
    sl.codice_aic,
    sl.n_riga,
    sl.descrizione_prodotto,
    sl.pattern_signature,
    sl.stato,
    sl.timestamp_creazione,
    sl.prezzo_proposto,
    ot.numero_ordine_vendor AS numero_ordine,
    ot.ragione_sociale_1 AS ragione_sociale,
    ot.citta,
    a.nome_file_originale AS pdf_file,
    COALESCE(col.count_approvazioni, 0) AS count_pattern,
    COALESCE(col.is_ordinario, false) AS pattern_ordinario
   FROM (((public.supervisione_listino sl
     JOIN public.ordini_testata ot ON ((sl.id_testata = ot.id_testata)))
     JOIN public.acquisizioni a ON ((ot.id_acquisizione = a.id_acquisizione)))
     LEFT JOIN public.criteri_ordinari_listino col ON (((sl.pattern_signature)::text = col.pattern_signature)))
  WHERE ((sl.stato)::text = 'PENDING'::text)
  ORDER BY sl.timestamp_creazione DESC;


--
-- Name: v_supervisione_lookup_pending; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.v_supervisione_lookup_pending AS
 SELECT slk.id_supervisione,
    slk.id_testata,
    slk.codice_anomalia,
    slk.vendor,
    slk.partita_iva_estratta,
    slk.lookup_method,
    slk.lookup_score,
    slk.pattern_signature,
    slk.stato,
    slk.timestamp_creazione,
    slk.min_id_assegnato,
    ot.numero_ordine_vendor AS numero_ordine,
    ot.ragione_sociale_1 AS ragione_sociale,
    ot.citta,
    a.nome_file_originale AS pdf_file,
    COALESCE(colk.count_approvazioni, 0) AS count_pattern,
    COALESCE(colk.is_ordinario, false) AS pattern_ordinario,
    colk.pattern_descrizione
   FROM (((public.supervisione_lookup slk
     JOIN public.ordini_testata ot ON ((slk.id_testata = ot.id_testata)))
     JOIN public.acquisizioni a ON ((ot.id_acquisizione = a.id_acquisizione)))
     LEFT JOIN public.criteri_ordinari_lookup colk ON (((slk.pattern_signature)::text = colk.pattern_signature)))
  WHERE ((slk.stato)::text = 'PENDING'::text)
  ORDER BY slk.timestamp_creazione DESC;


--
-- Name: v_supervisione_pending; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.v_supervisione_pending AS
 SELECT se.id_supervisione,
    se.id_testata,
    se.codice_anomalia,
    v.codice_vendor AS vendor,
    se.codice_espositore,
    se.descrizione_espositore,
    se.pezzi_attesi,
    se.pezzi_trovati,
    se.pattern_signature,
    se.stato,
    se.timestamp_creazione,
    ot.numero_ordine_vendor AS numero_ordine,
    ot.ragione_sociale_1 AS ragione_sociale,
    ot.citta,
    a.nome_file_originale AS pdf_file,
    COALESCE(coe.count_approvazioni, 0) AS count_pattern,
    COALESCE(coe.is_ordinario, false) AS pattern_ordinario,
    coe.pattern_descrizione
   FROM ((((public.supervisione_espositore se
     JOIN public.ordini_testata ot ON ((se.id_testata = ot.id_testata)))
     JOIN public.vendor v ON ((ot.id_vendor = v.id_vendor)))
     LEFT JOIN public.acquisizioni a ON ((ot.id_acquisizione = a.id_acquisizione)))
     LEFT JOIN public.criteri_ordinari_espositore coe ON (((se.pattern_signature)::text = (coe.pattern_signature)::text)))
  WHERE ((se.stato)::text = 'PENDING'::text)
  ORDER BY se.timestamp_creazione DESC;


--
-- Name: v_sync_status; Type: VIEW; Schema: public; Owner: -
--

CREATE VIEW public.v_sync_status AS
 SELECT sync_state.key,
    sync_state.last_sync,
    sync_state.last_url,
    sync_state.records_count,
    sync_state.etag,
        CASE
            WHEN (sync_state.last_sync IS NULL) THEN 'MAI_SINCRONIZZATO'::text
            WHEN (sync_state.last_sync < (CURRENT_TIMESTAMP - '7 days'::interval)) THEN 'OBSOLETO'::text
            WHEN (sync_state.last_sync < (CURRENT_TIMESTAMP - '1 day'::interval)) THEN 'DA_AGGIORNARE'::text
            ELSE 'AGGIORNATO'::text
        END AS stato,
    (EXTRACT(epoch FROM (CURRENT_TIMESTAMP - (sync_state.last_sync)::timestamp with time zone)) / (3600)::numeric) AS ore_dalla_sync
   FROM public.sync_state
  ORDER BY sync_state.last_sync DESC;


--
-- Name: vendor_id_vendor_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.vendor_id_vendor_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: vendor_id_vendor_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.vendor_id_vendor_seq OWNED BY public.vendor.id_vendor;


--
-- Name: acquisizioni id_acquisizione; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.acquisizioni ALTER COLUMN id_acquisizione SET DEFAULT nextval('public.acquisizioni_id_acquisizione_seq'::regclass);


--
-- Name: anagrafica_clienti id_cliente; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.anagrafica_clienti ALTER COLUMN id_cliente SET DEFAULT nextval('public.anagrafica_clienti_id_cliente_seq'::regclass);


--
-- Name: anagrafica_farmacie id_farmacia; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.anagrafica_farmacie ALTER COLUMN id_farmacia SET DEFAULT nextval('public.anagrafica_farmacie_id_farmacia_seq'::regclass);


--
-- Name: anagrafica_parafarmacie id_parafarmacia; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.anagrafica_parafarmacie ALTER COLUMN id_parafarmacia SET DEFAULT nextval('public.anagrafica_parafarmacie_id_parafarmacia_seq'::regclass);


--
-- Name: anomalie id_anomalia; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.anomalie ALTER COLUMN id_anomalia SET DEFAULT nextval('public.anomalie_id_anomalia_seq'::regclass);


--
-- Name: audit_modifiche id_audit; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_modifiche ALTER COLUMN id_audit SET DEFAULT nextval('public.audit_modifiche_id_audit_seq'::regclass);


--
-- Name: backup_history id_backup; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.backup_history ALTER COLUMN id_backup SET DEFAULT nextval('public.backup_history_id_backup_seq'::regclass);


--
-- Name: backup_modules id_module; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.backup_modules ALTER COLUMN id_module SET DEFAULT nextval('public.backup_modules_id_module_seq'::regclass);


--
-- Name: backup_operations_log id_log; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.backup_operations_log ALTER COLUMN id_log SET DEFAULT nextval('public.backup_operations_log_id_log_seq'::regclass);


--
-- Name: backup_schedules id_schedule; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.backup_schedules ALTER COLUMN id_schedule SET DEFAULT nextval('public.backup_schedules_id_schedule_seq'::regclass);


--
-- Name: backup_storage id_storage; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.backup_storage ALTER COLUMN id_storage SET DEFAULT nextval('public.backup_storage_id_storage_seq'::regclass);


--
-- Name: crm_allegati id_allegato; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.crm_allegati ALTER COLUMN id_allegato SET DEFAULT nextval('public.crm_allegati_id_allegato_seq'::regclass);


--
-- Name: crm_messaggi id_messaggio; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.crm_messaggi ALTER COLUMN id_messaggio SET DEFAULT nextval('public.crm_messaggi_id_messaggio_seq'::regclass);


--
-- Name: crm_tickets id_ticket; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.crm_tickets ALTER COLUMN id_ticket SET DEFAULT nextval('public.crm_tickets_id_ticket_seq'::regclass);


--
-- Name: email_acquisizioni id_email; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.email_acquisizioni ALTER COLUMN id_email SET DEFAULT nextval('public.email_acquisizioni_id_email_seq'::regclass);


--
-- Name: esportazioni id_esportazione; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.esportazioni ALTER COLUMN id_esportazione SET DEFAULT nextval('public.esportazioni_id_esportazione_seq'::regclass);


--
-- Name: esportazioni_dettaglio id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.esportazioni_dettaglio ALTER COLUMN id SET DEFAULT nextval('public.esportazioni_dettaglio_id_seq'::regclass);


--
-- Name: listini_vendor id_listino; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.listini_vendor ALTER COLUMN id_listino SET DEFAULT nextval('public.listini_vendor_id_listino_seq'::regclass);


--
-- Name: log_criteri_applicati id_log; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.log_criteri_applicati ALTER COLUMN id_log SET DEFAULT nextval('public.log_criteri_applicati_id_log_seq'::regclass);


--
-- Name: log_operazioni id_log; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.log_operazioni ALTER COLUMN id_log SET DEFAULT nextval('public.log_operazioni_id_log_seq'::regclass);


--
-- Name: operatori id_operatore; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.operatori ALTER COLUMN id_operatore SET DEFAULT nextval('public.operatori_id_operatore_seq'::regclass);


--
-- Name: ordini_dettaglio id_dettaglio; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ordini_dettaglio ALTER COLUMN id_dettaglio SET DEFAULT nextval('public.ordini_dettaglio_id_dettaglio_seq'::regclass);


--
-- Name: ordini_testata id_testata; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ordini_testata ALTER COLUMN id_testata SET DEFAULT nextval('public.ordini_testata_id_testata_seq'::regclass);


--
-- Name: permessi_ruolo id_permesso; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.permessi_ruolo ALTER COLUMN id_permesso SET DEFAULT nextval('public.permessi_ruolo_id_permesso_seq'::regclass);


--
-- Name: sessione_attivita id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sessione_attivita ALTER COLUMN id SET DEFAULT nextval('public.sessione_attivita_id_seq'::regclass);


--
-- Name: supervisione_aic id_supervisione; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supervisione_aic ALTER COLUMN id_supervisione SET DEFAULT nextval('public.supervisione_aic_id_supervisione_seq'::regclass);


--
-- Name: supervisione_espositore id_supervisione; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supervisione_espositore ALTER COLUMN id_supervisione SET DEFAULT nextval('public.supervisione_espositore_id_supervisione_seq'::regclass);


--
-- Name: supervisione_listino id_supervisione; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supervisione_listino ALTER COLUMN id_supervisione SET DEFAULT nextval('public.supervisione_listino_id_supervisione_seq'::regclass);


--
-- Name: supervisione_lookup id_supervisione; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supervisione_lookup ALTER COLUMN id_supervisione SET DEFAULT nextval('public.supervisione_lookup_id_supervisione_seq'::regclass);


--
-- Name: supervisione_prezzo id_supervisione; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supervisione_prezzo ALTER COLUMN id_supervisione SET DEFAULT nextval('public.supervisione_prezzo_id_supervisione_seq'::regclass);


--
-- Name: tracciati id_tracciato; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tracciati ALTER COLUMN id_tracciato SET DEFAULT nextval('public.tracciati_id_tracciato_seq'::regclass);


--
-- Name: tracciati_dettaglio id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tracciati_dettaglio ALTER COLUMN id SET DEFAULT nextval('public.tracciati_dettaglio_id_seq'::regclass);


--
-- Name: user_sessions id_session; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_sessions ALTER COLUMN id_session SET DEFAULT nextval('public.user_sessions_id_session_seq'::regclass);


--
-- Name: vendor id_vendor; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.vendor ALTER COLUMN id_vendor SET DEFAULT nextval('public.vendor_id_vendor_seq'::regclass);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: anagrafica_clienti anagrafica_clienti_codice_cliente_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.anagrafica_clienti
    ADD CONSTRAINT anagrafica_clienti_codice_cliente_key UNIQUE (codice_cliente);


--
-- Name: anagrafica_clienti anagrafica_clienti_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.anagrafica_clienti
    ADD CONSTRAINT anagrafica_clienti_pkey PRIMARY KEY (id_cliente);


--
-- Name: anagrafica_farmacie anagrafica_farmacie_min_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.anagrafica_farmacie
    ADD CONSTRAINT anagrafica_farmacie_min_id_key UNIQUE (min_id);


--
-- Name: anagrafica_farmacie anagrafica_farmacie_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.anagrafica_farmacie
    ADD CONSTRAINT anagrafica_farmacie_pkey PRIMARY KEY (id_farmacia);


--
-- Name: anagrafica_parafarmacie anagrafica_parafarmacie_codice_sito_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.anagrafica_parafarmacie
    ADD CONSTRAINT anagrafica_parafarmacie_codice_sito_key UNIQUE (codice_sito);


--
-- Name: anomalie anomalie_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.anomalie
    ADD CONSTRAINT anomalie_pkey PRIMARY KEY (id_anomalia);


--
-- Name: app_sezioni app_sezioni_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.app_sezioni
    ADD CONSTRAINT app_sezioni_pkey PRIMARY KEY (codice_sezione);


--
-- Name: audit_modifiche audit_modifiche_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_modifiche
    ADD CONSTRAINT audit_modifiche_pkey PRIMARY KEY (id_audit);


--
-- Name: backup_history backup_history_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.backup_history
    ADD CONSTRAINT backup_history_pkey PRIMARY KEY (id_backup);


--
-- Name: backup_modules backup_modules_nome_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.backup_modules
    ADD CONSTRAINT backup_modules_nome_key UNIQUE (nome);


--
-- Name: backup_modules backup_modules_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.backup_modules
    ADD CONSTRAINT backup_modules_pkey PRIMARY KEY (id_module);


--
-- Name: backup_operations_log backup_operations_log_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.backup_operations_log
    ADD CONSTRAINT backup_operations_log_pkey PRIMARY KEY (id_log);


--
-- Name: backup_schedules backup_schedules_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.backup_schedules
    ADD CONSTRAINT backup_schedules_pkey PRIMARY KEY (id_schedule);


--
-- Name: backup_storage backup_storage_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.backup_storage
    ADD CONSTRAINT backup_storage_pkey PRIMARY KEY (id_storage);


--
-- Name: criteri_ordinari_aic criteri_ordinari_aic_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.criteri_ordinari_aic
    ADD CONSTRAINT criteri_ordinari_aic_pkey PRIMARY KEY (pattern_signature);


--
-- Name: criteri_ordinari_aic criteri_ordinari_aic_unique_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.criteri_ordinari_aic
    ADD CONSTRAINT criteri_ordinari_aic_unique_key UNIQUE (pattern_signature);


--
-- Name: criteri_ordinari_listino criteri_ordinari_listino_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.criteri_ordinari_listino
    ADD CONSTRAINT criteri_ordinari_listino_pkey PRIMARY KEY (pattern_signature);


--
-- Name: criteri_ordinari_listino criteri_ordinari_listino_unique_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.criteri_ordinari_listino
    ADD CONSTRAINT criteri_ordinari_listino_unique_key UNIQUE (pattern_signature);


--
-- Name: criteri_ordinari_lookup criteri_ordinari_lookup_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.criteri_ordinari_lookup
    ADD CONSTRAINT criteri_ordinari_lookup_pkey PRIMARY KEY (pattern_signature);


--
-- Name: criteri_ordinari_lookup criteri_ordinari_lookup_unique_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.criteri_ordinari_lookup
    ADD CONSTRAINT criteri_ordinari_lookup_unique_key UNIQUE (pattern_signature);


--
-- Name: crm_allegati crm_allegati_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.crm_allegati
    ADD CONSTRAINT crm_allegati_pkey PRIMARY KEY (id_allegato);


--
-- Name: crm_messaggi crm_messaggi_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.crm_messaggi
    ADD CONSTRAINT crm_messaggi_pkey PRIMARY KEY (id_messaggio);


--
-- Name: crm_tickets crm_tickets_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.crm_tickets
    ADD CONSTRAINT crm_tickets_pkey PRIMARY KEY (id_ticket);


--
-- Name: listini_vendor listini_vendor_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.listini_vendor
    ADD CONSTRAINT listini_vendor_pkey PRIMARY KEY (id_listino);


--
-- Name: listini_vendor listini_vendor_vendor_codice_aic_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.listini_vendor
    ADD CONSTRAINT listini_vendor_vendor_codice_aic_key UNIQUE (vendor, codice_aic);


--
-- Name: operatori operatori_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.operatori
    ADD CONSTRAINT operatori_pkey PRIMARY KEY (id_operatore);


--
-- Name: ordini_dettaglio ordini_dettaglio_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ordini_dettaglio
    ADD CONSTRAINT ordini_dettaglio_pkey PRIMARY KEY (id_dettaglio);


--
-- Name: ordini_testata ordini_testata_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ordini_testata
    ADD CONSTRAINT ordini_testata_pkey PRIMARY KEY (id_testata);


--
-- Name: permessi_ruolo permessi_ruolo_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.permessi_ruolo
    ADD CONSTRAINT permessi_ruolo_pkey PRIMARY KEY (id_permesso);


--
-- Name: permessi_ruolo permessi_ruolo_ruolo_codice_sezione_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.permessi_ruolo
    ADD CONSTRAINT permessi_ruolo_ruolo_codice_sezione_key UNIQUE (ruolo, codice_sezione);


--
-- Name: supervisione_aic supervisione_aic_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supervisione_aic
    ADD CONSTRAINT supervisione_aic_pkey PRIMARY KEY (id_supervisione);


--
-- Name: supervisione_listino supervisione_listino_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supervisione_listino
    ADD CONSTRAINT supervisione_listino_pkey PRIMARY KEY (id_supervisione);


--
-- Name: supervisione_lookup supervisione_lookup_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supervisione_lookup
    ADD CONSTRAINT supervisione_lookup_pkey PRIMARY KEY (id_supervisione);


--
-- Name: supervisione_prezzo supervisione_prezzo_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supervisione_prezzo
    ADD CONSTRAINT supervisione_prezzo_pkey PRIMARY KEY (id_supervisione);


--
-- Name: sync_state sync_state_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sync_state
    ADD CONSTRAINT sync_state_pkey PRIMARY KEY (key);


--
-- Name: idx_audit_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_created ON public.audit_modifiche USING btree (created_at);


--
-- Name: idx_audit_entita; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_entita ON public.audit_modifiche USING btree (entita, id_entita);


--
-- Name: idx_audit_testata; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_testata ON public.audit_modifiche USING btree (id_testata);


--
-- Name: idx_backup_history_module; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_backup_history_module ON public.backup_history USING btree (id_module);


--
-- Name: idx_backup_history_started; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_backup_history_started ON public.backup_history USING btree (started_at DESC);


--
-- Name: idx_backup_history_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_backup_history_status ON public.backup_history USING btree (status);


--
-- Name: idx_backup_history_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_backup_history_type ON public.backup_history USING btree (backup_type);


--
-- Name: idx_backup_ops_log_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_backup_ops_log_created ON public.backup_operations_log USING btree (created_at DESC);


--
-- Name: idx_backup_ops_log_module; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_backup_ops_log_module ON public.backup_operations_log USING btree (id_module);


--
-- Name: idx_backup_ops_log_operation; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_backup_ops_log_operation ON public.backup_operations_log USING btree (operation);


--
-- Name: idx_backup_schedules_module; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_backup_schedules_module ON public.backup_schedules USING btree (id_module);


--
-- Name: idx_backup_schedules_next; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_backup_schedules_next ON public.backup_schedules USING btree (next_run) WHERE (active = true);


--
-- Name: idx_backup_storage_stato; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_backup_storage_stato ON public.backup_storage USING btree (stato);


--
-- Name: idx_backup_storage_tipo; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_backup_storage_tipo ON public.backup_storage USING btree (tipo);


--
-- Name: idx_clienti_codice; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_clienti_codice ON public.anagrafica_clienti USING btree (codice_cliente);


--
-- Name: idx_clienti_localita; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_clienti_localita ON public.anagrafica_clienti USING btree (localita);


--
-- Name: idx_clienti_piva; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_clienti_piva ON public.anagrafica_clienti USING btree (partita_iva);


--
-- Name: idx_clienti_provincia; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_clienti_provincia ON public.anagrafica_clienti USING btree (provincia);


--
-- Name: idx_crit_aic_ordinario; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_crit_aic_ordinario ON public.criteri_ordinari_aic USING btree (is_ordinario) WHERE (is_ordinario = true);


--
-- Name: idx_crit_aic_vendor_desc; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_crit_aic_vendor_desc ON public.criteri_ordinari_aic USING btree (vendor, descrizione_normalizzata);


--
-- Name: idx_crm_messaggi_ticket; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_crm_messaggi_ticket ON public.crm_messaggi USING btree (id_ticket);


--
-- Name: idx_crm_tickets_operatore; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_crm_tickets_operatore ON public.crm_tickets USING btree (id_operatore);


--
-- Name: idx_crm_tickets_stato; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_crm_tickets_stato ON public.crm_tickets USING btree (stato);


--
-- Name: idx_listini_aic; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_listini_aic ON public.listini_vendor USING btree (codice_aic);


--
-- Name: idx_listini_vendor; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_listini_vendor ON public.listini_vendor USING btree (vendor);


--
-- Name: idx_listini_vendor_aic; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_listini_vendor_aic ON public.listini_vendor USING btree (vendor, codice_aic);


--
-- Name: idx_permessi_ruolo_ruolo; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_permessi_ruolo_ruolo ON public.permessi_ruolo USING btree (ruolo);


--
-- Name: idx_permessi_ruolo_sezione; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_permessi_ruolo_sezione ON public.permessi_ruolo USING btree (codice_sezione);


--
-- Name: idx_sup_aic_pattern; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sup_aic_pattern ON public.supervisione_aic USING btree (pattern_signature);


--
-- Name: idx_sup_aic_stato; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sup_aic_stato ON public.supervisione_aic USING btree (stato);


--
-- Name: idx_sup_aic_testata; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sup_aic_testata ON public.supervisione_aic USING btree (id_testata);


--
-- Name: idx_sup_aic_vendor_desc; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sup_aic_vendor_desc ON public.supervisione_aic USING btree (vendor, descrizione_normalizzata);


--
-- Name: idx_sup_listino_stato; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sup_listino_stato ON public.supervisione_listino USING btree (stato);


--
-- Name: idx_sup_listino_testata; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sup_listino_testata ON public.supervisione_listino USING btree (id_testata);


--
-- Name: idx_sup_listino_vendor; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sup_listino_vendor ON public.supervisione_listino USING btree (vendor);


--
-- Name: idx_sup_lookup_pattern; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sup_lookup_pattern ON public.supervisione_lookup USING btree (pattern_signature);


--
-- Name: idx_sup_lookup_stato; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sup_lookup_stato ON public.supervisione_lookup USING btree (stato);


--
-- Name: idx_sup_lookup_testata; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sup_lookup_testata ON public.supervisione_lookup USING btree (id_testata);


--
-- Name: idx_sup_prezzo_stato; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sup_prezzo_stato ON public.supervisione_prezzo USING btree (stato);


--
-- Name: idx_sup_prezzo_testata; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sup_prezzo_testata ON public.supervisione_prezzo USING btree (id_testata);


--
-- Name: idx_supervisione_listino_stato; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_supervisione_listino_stato ON public.supervisione_listino USING btree (stato);


--
-- Name: idx_supervisione_listino_testata; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_supervisione_listino_testata ON public.supervisione_listino USING btree (id_testata);


--
-- Name: idx_supervisione_lookup_stato; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_supervisione_lookup_stato ON public.supervisione_lookup USING btree (stato);


--
-- Name: idx_supervisione_lookup_testata; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_supervisione_lookup_testata ON public.supervisione_lookup USING btree (id_testata);


--
-- Name: idx_sync_state_last_sync; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sync_state_last_sync ON public.sync_state USING btree (last_sync);


--
-- Name: backup_modules trg_backup_modules_updated; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_backup_modules_updated BEFORE UPDATE ON public.backup_modules FOR EACH ROW EXECUTE FUNCTION public.backup_update_timestamp();


--
-- Name: backup_storage trg_backup_storage_updated; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_backup_storage_updated BEFORE UPDATE ON public.backup_storage FOR EACH ROW EXECUTE FUNCTION public.backup_update_timestamp();


--
-- Name: backup_history backup_history_id_module_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.backup_history
    ADD CONSTRAINT backup_history_id_module_fkey FOREIGN KEY (id_module) REFERENCES public.backup_modules(id_module);


--
-- Name: backup_history backup_history_id_storage_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.backup_history
    ADD CONSTRAINT backup_history_id_storage_fkey FOREIGN KEY (id_storage) REFERENCES public.backup_storage(id_storage);


--
-- Name: backup_history backup_history_operator_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.backup_history
    ADD CONSTRAINT backup_history_operator_id_fkey FOREIGN KEY (operator_id) REFERENCES public.operatori(id_operatore);


--
-- Name: backup_modules backup_modules_id_storage_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.backup_modules
    ADD CONSTRAINT backup_modules_id_storage_fkey FOREIGN KEY (id_storage) REFERENCES public.backup_storage(id_storage);


--
-- Name: backup_modules backup_modules_updated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.backup_modules
    ADD CONSTRAINT backup_modules_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES public.operatori(id_operatore);


--
-- Name: backup_operations_log backup_operations_log_id_backup_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.backup_operations_log
    ADD CONSTRAINT backup_operations_log_id_backup_fkey FOREIGN KEY (id_backup) REFERENCES public.backup_history(id_backup);


--
-- Name: backup_operations_log backup_operations_log_id_module_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.backup_operations_log
    ADD CONSTRAINT backup_operations_log_id_module_fkey FOREIGN KEY (id_module) REFERENCES public.backup_modules(id_module);


--
-- Name: backup_operations_log backup_operations_log_operator_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.backup_operations_log
    ADD CONSTRAINT backup_operations_log_operator_id_fkey FOREIGN KEY (operator_id) REFERENCES public.operatori(id_operatore);


--
-- Name: backup_schedules backup_schedules_id_module_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.backup_schedules
    ADD CONSTRAINT backup_schedules_id_module_fkey FOREIGN KEY (id_module) REFERENCES public.backup_modules(id_module);


--
-- Name: backup_storage backup_storage_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.backup_storage
    ADD CONSTRAINT backup_storage_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.operatori(id_operatore);


--
-- Name: criteri_ordinari_lookup criteri_ordinari_lookup_id_farmacia_default_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.criteri_ordinari_lookup
    ADD CONSTRAINT criteri_ordinari_lookup_id_farmacia_default_fkey FOREIGN KEY (id_farmacia_default) REFERENCES public.anagrafica_farmacie(id_farmacia);


--
-- Name: crm_allegati crm_allegati_id_messaggio_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.crm_allegati
    ADD CONSTRAINT crm_allegati_id_messaggio_fkey FOREIGN KEY (id_messaggio) REFERENCES public.crm_messaggi(id_messaggio) ON DELETE CASCADE;


--
-- Name: crm_allegati crm_allegati_id_operatore_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.crm_allegati
    ADD CONSTRAINT crm_allegati_id_operatore_fkey FOREIGN KEY (id_operatore) REFERENCES public.operatori(id_operatore);


--
-- Name: crm_allegati crm_allegati_id_ticket_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.crm_allegati
    ADD CONSTRAINT crm_allegati_id_ticket_fkey FOREIGN KEY (id_ticket) REFERENCES public.crm_tickets(id_ticket) ON DELETE CASCADE;


--
-- Name: crm_messaggi crm_messaggi_id_operatore_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.crm_messaggi
    ADD CONSTRAINT crm_messaggi_id_operatore_fkey FOREIGN KEY (id_operatore) REFERENCES public.operatori(id_operatore);


--
-- Name: crm_messaggi crm_messaggi_id_ticket_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.crm_messaggi
    ADD CONSTRAINT crm_messaggi_id_ticket_fkey FOREIGN KEY (id_ticket) REFERENCES public.crm_tickets(id_ticket) ON DELETE CASCADE;


--
-- Name: crm_tickets crm_tickets_closed_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.crm_tickets
    ADD CONSTRAINT crm_tickets_closed_by_fkey FOREIGN KEY (closed_by) REFERENCES public.operatori(id_operatore);


--
-- Name: crm_tickets crm_tickets_id_operatore_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.crm_tickets
    ADD CONSTRAINT crm_tickets_id_operatore_fkey FOREIGN KEY (id_operatore) REFERENCES public.operatori(id_operatore);


--
-- Name: permessi_ruolo permessi_ruolo_codice_sezione_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.permessi_ruolo
    ADD CONSTRAINT permessi_ruolo_codice_sezione_fkey FOREIGN KEY (codice_sezione) REFERENCES public.app_sezioni(codice_sezione);


--
-- Name: supervisione_aic supervisione_aic_id_dettaglio_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supervisione_aic
    ADD CONSTRAINT supervisione_aic_id_dettaglio_fkey FOREIGN KEY (id_dettaglio) REFERENCES public.ordini_dettaglio(id_dettaglio) ON DELETE SET NULL;


--
-- Name: supervisione_aic supervisione_aic_id_testata_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supervisione_aic
    ADD CONSTRAINT supervisione_aic_id_testata_fkey FOREIGN KEY (id_testata) REFERENCES public.ordini_testata(id_testata) ON DELETE CASCADE;


--
-- Name: supervisione_listino supervisione_listino_id_testata_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supervisione_listino
    ADD CONSTRAINT supervisione_listino_id_testata_fkey FOREIGN KEY (id_testata) REFERENCES public.ordini_testata(id_testata) ON DELETE CASCADE;


--
-- Name: supervisione_lookup supervisione_lookup_id_testata_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.supervisione_lookup
    ADD CONSTRAINT supervisione_lookup_id_testata_fkey FOREIGN KEY (id_testata) REFERENCES public.ordini_testata(id_testata) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict Bngijxh1A5Am7u7C9Y8f6taW8R4nwt0LMetlAjt7IL25l3OIuWoQDnH8UAd9NES

