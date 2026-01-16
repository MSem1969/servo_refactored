-- =============================================================================
-- TO_EXTRACTOR v6.2 - DATABASE SCHEMA BACKUP
-- Generated: $(date)
-- =============================================================================

-- Drop existing tables (in reverse dependency order)
DROP TABLE IF EXISTS tracciati_dettaglio CASCADE;
DROP TABLE IF EXISTS tracciati CASCADE;
DROP TABLE IF EXISTS esportazioni_dettaglio CASCADE;
DROP TABLE IF EXISTS esportazioni CASCADE;
DROP TABLE IF EXISTS log_criteri_applicati CASCADE;
DROP TABLE IF EXISTS supervisione_espositore CASCADE;
DROP TABLE IF EXISTS anomalie CASCADE;
DROP TABLE IF EXISTS ordini_dettaglio CASCADE;
DROP TABLE IF EXISTS ordini_testata CASCADE;
DROP TABLE IF EXISTS acquisizioni CASCADE;
DROP TABLE IF EXISTS email_acquisizioni CASCADE;
DROP TABLE IF EXISTS user_sessions CASCADE;
DROP TABLE IF EXISTS log_operazioni CASCADE;
DROP TABLE IF EXISTS sessione_attivita CASCADE;
DROP TABLE IF EXISTS operatori CASCADE;
DROP TABLE IF EXISTS criteri_ordinari_espositore CASCADE;
DROP TABLE IF EXISTS vendor CASCADE;
DROP TABLE IF EXISTS anagrafica_farmacie CASCADE;
DROP TABLE IF EXISTS anagrafica_parafarmacie CASCADE;

-- Table: vendor
CREATE TABLE IF NOT EXISTS vendor (
    id_vendor SERIAL NOT NULL,
    codice_vendor VARCHAR(50) NOT NULL,
    ragione_sociale VARCHAR(255),
    partita_iva_vendor VARCHAR(16),
    linea_offerta VARCHAR(100),
    note_estrazione TEXT,
    attivo BOOLEAN DEFAULT true,
    data_inserimento TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table: operatori
CREATE TABLE IF NOT EXISTS operatori (
    id_operatore SERIAL NOT NULL,
    username VARCHAR(50) NOT NULL,
    password_hash VARCHAR(255) DEFAULT ''::character varying,
    nome VARCHAR(100),
    cognome VARCHAR(100),
    email VARCHAR(255),
    ruolo VARCHAR(20) DEFAULT 'operatore'::character varying,
    attivo BOOLEAN DEFAULT true,
    data_creazione TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by_operatore INTEGER,
    updated_at TIMESTAMP WITHOUT TIME ZONE,
    last_login_at TIMESTAMP WITHOUT TIME ZONE,
    disabled_at TIMESTAMP WITHOUT TIME ZONE,
    disabled_by_operatore INTEGER,
    disable_reason TEXT,
    last_login_ip VARCHAR(50),
    data_nascita DATE,
    avatar_base64 TEXT,
    avatar_mime_type VARCHAR(50) DEFAULT 'image/jpeg'::character varying
);

-- Table: anagrafica_farmacie
CREATE TABLE IF NOT EXISTS anagrafica_farmacie (
    id_farmacia SERIAL NOT NULL,
    min_id VARCHAR(9) NOT NULL,
    codice_farmacia_asl VARCHAR(20),
    partita_iva VARCHAR(16),
    ragione_sociale VARCHAR(255),
    indirizzo VARCHAR(255),
    cap VARCHAR(10),
    citta VARCHAR(100),
    frazione VARCHAR(100),
    provincia VARCHAR(3),
    regione VARCHAR(50),
    data_inizio_validita DATE,
    data_fine_validita DATE,
    attiva BOOLEAN DEFAULT true,
    fonte_dati VARCHAR(50),
    data_import TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table: anagrafica_parafarmacie
CREATE TABLE IF NOT EXISTS anagrafica_parafarmacie (
    id_parafarmacia SERIAL NOT NULL,
    codice_sito VARCHAR(20) NOT NULL,
    sito_logistico VARCHAR(255),
    partita_iva VARCHAR(16),
    indirizzo VARCHAR(255),
    cap VARCHAR(10),
    codice_comune VARCHAR(10),
    citta VARCHAR(100),
    codice_provincia VARCHAR(3),
    provincia VARCHAR(50),
    codice_regione VARCHAR(3),
    regione VARCHAR(50),
    data_inizio_validita DATE,
    data_fine_validita DATE,
    latitudine NUMERIC,
    longitudine NUMERIC,
    attiva BOOLEAN DEFAULT true,
    fonte_dati VARCHAR(50),
    data_import TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table: acquisizioni
CREATE TABLE IF NOT EXISTS acquisizioni (
    id_acquisizione SERIAL NOT NULL,
    nome_file_originale VARCHAR(255) NOT NULL,
    nome_file_storage VARCHAR(255) NOT NULL,
    percorso_storage TEXT,
    hash_file VARCHAR(64),
    hash_contenuto_pdf VARCHAR(64),
    dimensione_bytes INTEGER,
    mime_type VARCHAR(100) DEFAULT 'application/pdf'::character varying,
    id_vendor INTEGER,
    vendor_rilevato_auto BOOLEAN DEFAULT true,
    stato VARCHAR(20) DEFAULT 'CARICATO'::character varying,
    num_ordini_estratti INTEGER DEFAULT 0,
    messaggio_errore TEXT,
    is_duplicato BOOLEAN DEFAULT false,
    id_acquisizione_originale INTEGER,
    id_operatore_upload INTEGER DEFAULT 1,
    data_upload TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    data_elaborazione TIMESTAMP WITHOUT TIME ZONE,
    origine VARCHAR(20) DEFAULT 'MANUALE'::character varying,
    id_email INTEGER
);

-- Table: ordini_testata
CREATE TABLE IF NOT EXISTS ordini_testata (
    id_testata SERIAL NOT NULL,
    id_acquisizione INTEGER NOT NULL,
    id_vendor INTEGER NOT NULL,
    numero_ordine_vendor VARCHAR(50) NOT NULL,
    data_ordine DATE,
    data_consegna DATE,
    partita_iva_estratta VARCHAR(16),
    codice_ministeriale_estratto VARCHAR(9),
    ragione_sociale_1 VARCHAR(100),
    ragione_sociale_2 VARCHAR(100),
    indirizzo VARCHAR(100),
    cap VARCHAR(10),
    citta VARCHAR(100),
    provincia VARCHAR(3),
    nome_agente VARCHAR(100),
    gg_dilazione_1 INTEGER DEFAULT 90,
    gg_dilazione_2 INTEGER,
    gg_dilazione_3 INTEGER,
    note_ordine TEXT,
    note_ddt TEXT,
    id_farmacia_lookup INTEGER,
    id_parafarmacia_lookup INTEGER,
    lookup_method VARCHAR(20),
    lookup_source VARCHAR(20) DEFAULT 'FARMACIA'::character varying,
    lookup_score INTEGER,
    chiave_univoca_ordine VARCHAR(64),
    is_ordine_duplicato BOOLEAN DEFAULT false,
    id_testata_originale INTEGER,
    stato VARCHAR(20) DEFAULT 'ESTRATTO'::character varying,
    data_estrazione TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    data_validazione TIMESTAMP WITHOUT TIME ZONE,
    validato_da VARCHAR(50),
    righe_totali INTEGER DEFAULT 0,
    righe_confermate INTEGER DEFAULT 0,
    righe_in_supervisione INTEGER DEFAULT 0,
    data_ultimo_aggiornamento TIMESTAMP WITHOUT TIME ZONE
);

-- Table: ordini_dettaglio
CREATE TABLE IF NOT EXISTS ordini_dettaglio (
    id_dettaglio SERIAL NOT NULL,
    id_testata INTEGER NOT NULL,
    n_riga INTEGER NOT NULL,
    codice_aic VARCHAR(10),
    codice_originale VARCHAR(20),
    codice_materiale VARCHAR(20),
    descrizione VARCHAR(100),
    tipo_posizione VARCHAR(20) DEFAULT ''::character varying,
    q_venduta INTEGER DEFAULT 0,
    q_sconto_merce INTEGER DEFAULT 0,
    q_omaggio INTEGER DEFAULT 0,
    data_consegna_riga DATE,
    sconto_1 NUMERIC DEFAULT 0,
    sconto_2 NUMERIC DEFAULT 0,
    sconto_3 NUMERIC DEFAULT 0,
    sconto_4 NUMERIC DEFAULT 0,
    prezzo_netto NUMERIC DEFAULT 0,
    prezzo_scontare NUMERIC DEFAULT 0,
    prezzo_pubblico NUMERIC DEFAULT 0,
    prezzo_listino NUMERIC DEFAULT 0,
    valore_netto NUMERIC DEFAULT 0,
    aliquota_iva NUMERIC DEFAULT 10,
    scorporo_iva VARCHAR(1) DEFAULT 'N'::bpchar,
    note_allestimento TEXT,
    is_espositore BOOLEAN DEFAULT false,
    is_child BOOLEAN DEFAULT false,
    is_no_aic BOOLEAN DEFAULT false,
    tipo_riga VARCHAR(20) DEFAULT ''::character varying,
    id_parent_espositore INTEGER,
    espositore_metadata JSONB,
    stato_riga VARCHAR(20) DEFAULT 'ESTRATTO'::character varying,
    richiede_supervisione BOOLEAN DEFAULT false,
    id_supervisione INTEGER,
    confermato_da VARCHAR(50),
    data_conferma TIMESTAMP WITHOUT TIME ZONE,
    note_supervisione TEXT,
    modificato_manualmente BOOLEAN DEFAULT false,
    valori_originali JSONB,
    q_originale INTEGER DEFAULT 0,
    q_esportata INTEGER DEFAULT 0,
    q_residua INTEGER DEFAULT 0,
    num_esportazioni INTEGER DEFAULT 0,
    ultima_esportazione TIMESTAMP WITHOUT TIME ZONE,
    id_ultima_esportazione INTEGER,
    q_evasa INTEGER DEFAULT 0,
    q_da_evadere INTEGER DEFAULT 0
);

-- Table: anomalie
CREATE TABLE IF NOT EXISTS anomalie (
    id_anomalia SERIAL NOT NULL,
    id_testata INTEGER,
    id_dettaglio INTEGER,
    id_acquisizione INTEGER,
    tipo_anomalia VARCHAR(50) NOT NULL,
    livello VARCHAR(20) DEFAULT 'ATTENZIONE'::character varying,
    codice_anomalia VARCHAR(20),
    descrizione TEXT,
    valore_anomalo TEXT,
    stato VARCHAR(20) DEFAULT 'APERTA'::character varying,
    id_operatore_gestione INTEGER,
    note_risoluzione TEXT,
    data_rilevazione TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    data_risoluzione TIMESTAMP WITHOUT TIME ZONE,
    richiede_supervisione BOOLEAN DEFAULT false,
    pattern_signature VARCHAR(100)
);

-- Table: supervisione_espositore
CREATE TABLE IF NOT EXISTS supervisione_espositore (
    id_supervisione SERIAL NOT NULL,
    id_testata INTEGER NOT NULL,
    id_anomalia INTEGER,
    codice_anomalia VARCHAR(20) NOT NULL,
    codice_espositore VARCHAR(20),
    descrizione_espositore VARCHAR(255),
    pezzi_attesi INTEGER DEFAULT 0,
    pezzi_trovati INTEGER DEFAULT 0,
    valore_calcolato NUMERIC DEFAULT 0,
    pattern_signature VARCHAR(100),
    stato VARCHAR(20) DEFAULT 'PENDING'::character varying,
    operatore VARCHAR(50),
    timestamp_creazione TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    timestamp_decisione TIMESTAMP WITHOUT TIME ZONE,
    note TEXT,
    modifiche_manuali_json JSONB
);

-- Table: criteri_ordinari_espositore
CREATE TABLE IF NOT EXISTS criteri_ordinari_espositore (
    pattern_signature VARCHAR(100) NOT NULL,
    pattern_descrizione TEXT,
    vendor VARCHAR(50) NOT NULL,
    codice_anomalia VARCHAR(20),
    codice_espositore VARCHAR(20),
    pezzi_per_unita INTEGER,
    tipo_scostamento VARCHAR(20),
    fascia_scostamento VARCHAR(20),
    count_approvazioni INTEGER DEFAULT 0,
    is_ordinario BOOLEAN DEFAULT false,
    data_prima_occorrenza TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    data_promozione TIMESTAMP WITHOUT TIME ZONE,
    operatori_approvatori TEXT,
    descrizione_normalizzata VARCHAR(255),
    child_sequence_json JSONB,
    num_child_attesi INTEGER DEFAULT 0,
    total_applications INTEGER DEFAULT 0,
    successful_applications INTEGER DEFAULT 0
);

-- Table: log_criteri_applicati
CREATE TABLE IF NOT EXISTS log_criteri_applicati (
    id_log SERIAL NOT NULL,
    id_testata INTEGER,
    id_supervisione INTEGER,
    pattern_signature VARCHAR(100) NOT NULL,
    azione VARCHAR(50),
    applicato_automaticamente BOOLEAN DEFAULT false,
    operatore VARCHAR(50),
    note TEXT,
    timestamp TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table: esportazioni
CREATE TABLE IF NOT EXISTS esportazioni (
    id_esportazione SERIAL NOT NULL,
    nome_tracciato_generato VARCHAR(255),
    data_tracciato DATE,
    nome_file_to_t VARCHAR(255),
    nome_file_to_d VARCHAR(255),
    num_testate INTEGER DEFAULT 0,
    num_dettagli INTEGER DEFAULT 0,
    stato VARCHAR(20) DEFAULT 'GENERATO'::character varying,
    note TEXT,
    data_generazione TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table: esportazioni_dettaglio
CREATE TABLE IF NOT EXISTS esportazioni_dettaglio (
    id SERIAL NOT NULL,
    id_esportazione INTEGER NOT NULL,
    id_testata INTEGER
);

-- Table: tracciati
CREATE TABLE IF NOT EXISTS tracciati (
    id_tracciato SERIAL NOT NULL,
    nome_file VARCHAR(255) NOT NULL,
    tipo VARCHAR(20) DEFAULT 'CSV'::character varying,
    num_righe INTEGER DEFAULT 0,
    id_operatore INTEGER,
    note TEXT,
    data_generazione TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table: tracciati_dettaglio
CREATE TABLE IF NOT EXISTS tracciati_dettaglio (
    id SERIAL NOT NULL,
    id_tracciato INTEGER NOT NULL,
    id_testata INTEGER,
    id_dettaglio INTEGER
);

-- Table: user_sessions
CREATE TABLE IF NOT EXISTS user_sessions (
    id_session SERIAL NOT NULL,
    id_operatore INTEGER NOT NULL,
    token_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    revoked_at TIMESTAMP WITHOUT TIME ZONE,
    revoked_by_operatore INTEGER,
    ip_address VARCHAR(45),
    user_agent TEXT
);

-- Table: log_operazioni
CREATE TABLE IF NOT EXISTS log_operazioni (
    id_log SERIAL NOT NULL,
    tipo_operazione VARCHAR(50) NOT NULL,
    entita VARCHAR(50),
    id_entita INTEGER,
    descrizione TEXT,
    dati_json JSONB,
    id_operatore INTEGER,
    timestamp TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    action_category VARCHAR(50)
);

-- Table: sessione_attivita
CREATE TABLE IF NOT EXISTS sessione_attivita (
    id SERIAL NOT NULL,
    id_operatore INTEGER NOT NULL,
    id_session INTEGER,
    sezione VARCHAR(50) NOT NULL,
    ultimo_heartbeat TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    durata_secondi INTEGER DEFAULT 0,
    data_riferimento DATE DEFAULT CURRENT_DATE NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table: email_acquisizioni
CREATE TABLE IF NOT EXISTS email_acquisizioni (
    id_email SERIAL NOT NULL,
    message_id VARCHAR(255) NOT NULL,
    gmail_id VARCHAR(100),
    subject VARCHAR(500),
    sender_email VARCHAR(255) NOT NULL,
    sender_name VARCHAR(255),
    received_date TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    attachment_filename VARCHAR(255) NOT NULL,
    attachment_size INTEGER,
    attachment_hash VARCHAR(64) NOT NULL,
    id_acquisizione INTEGER,
    stato VARCHAR(20) DEFAULT 'DA_PROCESSARE'::character varying,
    data_elaborazione TIMESTAMP WITHOUT TIME ZONE,
    errore_messaggio TEXT,
    num_retry INTEGER DEFAULT 0,
    label_applicata VARCHAR(100),
    marcata_come_letta BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
