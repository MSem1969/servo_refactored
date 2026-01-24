-- =============================================================================
-- TO_EXTRACTOR v6.2 - PostgreSQL Schema DDL
-- =============================================================================
-- Migrazione da SQLite - Schema completo per PostgreSQL
-- =============================================================================

-- Estensioni utili
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- Per ricerche fuzzy

-- =============================================================================
-- TABELLE PRINCIPALI
-- =============================================================================

-- OPERATORI (utenti sistema)
CREATE TABLE IF NOT EXISTS operatori (
    id_operatore SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) DEFAULT '',
    nome VARCHAR(100),
    cognome VARCHAR(100),
    email VARCHAR(255) UNIQUE,
    ruolo VARCHAR(20) DEFAULT 'operatore'
        CHECK (ruolo IN ('admin', 'operatore', 'supervisore', 'readonly')),
    attivo BOOLEAN DEFAULT TRUE,
    data_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by_operatore INTEGER REFERENCES operatori(id_operatore),
    updated_at TIMESTAMP,
    last_login_at TIMESTAMP,
    last_login_ip VARCHAR(45),
    disabled_at TIMESTAMP,
    disabled_by_operatore INTEGER REFERENCES operatori(id_operatore),
    disable_reason TEXT,
    -- Campi profilo utente (v6.2.1)
    data_nascita DATE,
    avatar_base64 TEXT,
    avatar_mime_type VARCHAR(50) DEFAULT 'image/jpeg'
);

-- USER_SESSIONS (sessioni JWT)
CREATE TABLE IF NOT EXISTS user_sessions (
    id_session SERIAL PRIMARY KEY,
    id_operatore INTEGER NOT NULL REFERENCES operatori(id_operatore),
    token_hash VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    revoked_at TIMESTAMP,
    revoked_by_operatore INTEGER REFERENCES operatori(id_operatore),
    ip_address VARCHAR(45),
    user_agent TEXT
);

CREATE INDEX IF NOT EXISTS idx_sessions_operatore ON user_sessions(id_operatore);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON user_sessions(token_hash);
CREATE INDEX IF NOT EXISTS idx_sessions_expires ON user_sessions(expires_at);

-- VENDOR (produttori farmaceutici)
CREATE TABLE IF NOT EXISTS vendor (
    id_vendor SERIAL PRIMARY KEY,
    codice_vendor VARCHAR(50) NOT NULL UNIQUE,
    ragione_sociale VARCHAR(255),
    partita_iva_vendor VARCHAR(16),
    linea_offerta VARCHAR(100),
    note_estrazione TEXT,
    attivo BOOLEAN DEFAULT TRUE,
    data_inserimento TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ANAGRAFICA_FARMACIE
CREATE TABLE IF NOT EXISTS anagrafica_farmacie (
    id_farmacia SERIAL PRIMARY KEY,
    min_id VARCHAR(9) NOT NULL UNIQUE,
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
    attiva BOOLEAN DEFAULT TRUE,
    fonte_dati VARCHAR(50),
    data_import TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_farmacie_min_id ON anagrafica_farmacie(min_id);
CREATE INDEX IF NOT EXISTS idx_farmacie_piva ON anagrafica_farmacie(partita_iva);
CREATE INDEX IF NOT EXISTS idx_farmacie_citta ON anagrafica_farmacie USING gin(citta gin_trgm_ops);

-- ANAGRAFICA_PARAFARMACIE
CREATE TABLE IF NOT EXISTS anagrafica_parafarmacie (
    id_parafarmacia SERIAL PRIMARY KEY,
    codice_sito VARCHAR(20) NOT NULL UNIQUE,
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
    latitudine DECIMAL(10, 8),
    longitudine DECIMAL(11, 8),
    attiva BOOLEAN DEFAULT TRUE,
    fonte_dati VARCHAR(50),
    data_import TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_parafarm_codice ON anagrafica_parafarmacie(codice_sito);
CREATE INDEX IF NOT EXISTS idx_parafarm_piva ON anagrafica_parafarmacie(partita_iva);

-- ACQUISIZIONI (upload PDF)
CREATE TABLE IF NOT EXISTS acquisizioni (
    id_acquisizione SERIAL PRIMARY KEY,
    nome_file_originale VARCHAR(255) NOT NULL,
    nome_file_storage VARCHAR(255) NOT NULL,
    percorso_storage TEXT,
    hash_file VARCHAR(64),
    hash_contenuto_pdf VARCHAR(64),
    dimensione_bytes INTEGER,
    mime_type VARCHAR(100) DEFAULT 'application/pdf',
    id_vendor INTEGER REFERENCES vendor(id_vendor),
    vendor_rilevato_auto BOOLEAN DEFAULT TRUE,
    stato VARCHAR(20) DEFAULT 'CARICATO'
        CHECK (stato IN ('CARICATO', 'IN_ELABORAZIONE', 'ELABORATO', 'ERRORE', 'SCARTATO')),
    num_ordini_estratti INTEGER DEFAULT 0,
    messaggio_errore TEXT,
    is_duplicato BOOLEAN DEFAULT FALSE,
    id_acquisizione_originale INTEGER REFERENCES acquisizioni(id_acquisizione),
    id_operatore_upload INTEGER DEFAULT 1,
    data_upload TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_elaborazione TIMESTAMP,
    origine VARCHAR(20) DEFAULT 'MANUALE',
    id_email INTEGER
);

CREATE INDEX IF NOT EXISTS idx_acquisizioni_hash ON acquisizioni(hash_file);
CREATE INDEX IF NOT EXISTS idx_acquisizioni_stato ON acquisizioni(stato);

-- ORDINI_TESTATA
CREATE TABLE IF NOT EXISTS ordini_testata (
    id_testata SERIAL PRIMARY KEY,
    id_acquisizione INTEGER NOT NULL REFERENCES acquisizioni(id_acquisizione),
    id_vendor INTEGER NOT NULL REFERENCES vendor(id_vendor),
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
    id_farmacia_lookup INTEGER REFERENCES anagrafica_farmacie(id_farmacia),
    id_parafarmacia_lookup INTEGER REFERENCES anagrafica_parafarmacie(id_parafarmacia),
    lookup_method VARCHAR(20),
    lookup_source VARCHAR(20) DEFAULT 'FARMACIA',
    lookup_score INTEGER,
    chiave_univoca_ordine VARCHAR(64) UNIQUE,
    is_ordine_duplicato BOOLEAN DEFAULT FALSE,
    id_testata_originale INTEGER REFERENCES ordini_testata(id_testata),
    stato VARCHAR(20) DEFAULT 'ESTRATTO',
    data_estrazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_validazione TIMESTAMP,
    validato_da VARCHAR(50),
    righe_totali INTEGER DEFAULT 0,
    righe_confermate INTEGER DEFAULT 0,
    righe_in_supervisione INTEGER DEFAULT 0,
    data_ultimo_aggiornamento TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_testata_acquisizione ON ordini_testata(id_acquisizione);
CREATE INDEX IF NOT EXISTS idx_testata_vendor ON ordini_testata(id_vendor);
CREATE INDEX IF NOT EXISTS idx_testata_stato ON ordini_testata(stato);

-- ORDINI_DETTAGLIO
CREATE TABLE IF NOT EXISTS ordini_dettaglio (
    id_dettaglio SERIAL PRIMARY KEY,
    id_testata INTEGER NOT NULL REFERENCES ordini_testata(id_testata) ON DELETE CASCADE,
    n_riga INTEGER NOT NULL,
    codice_aic VARCHAR(10),
    codice_originale VARCHAR(20),
    codice_materiale VARCHAR(20),
    descrizione VARCHAR(100),
    tipo_posizione VARCHAR(20) DEFAULT '',
    q_venduta INTEGER DEFAULT 0,
    q_sconto_merce INTEGER DEFAULT 0,
    q_omaggio INTEGER DEFAULT 0,
    data_consegna_riga DATE,
    sconto_1 DECIMAL(6, 2) DEFAULT 0,
    sconto_2 DECIMAL(6, 2) DEFAULT 0,
    sconto_3 DECIMAL(6, 2) DEFAULT 0,
    sconto_4 DECIMAL(6, 2) DEFAULT 0,
    prezzo_netto DECIMAL(10, 2) DEFAULT 0,
    prezzo_scontare DECIMAL(10, 2) DEFAULT 0,
    prezzo_pubblico DECIMAL(10, 2) DEFAULT 0,
    prezzo_listino DECIMAL(10, 2) DEFAULT 0,
    valore_netto DECIMAL(12, 2) DEFAULT 0,
    aliquota_iva DECIMAL(5, 2) DEFAULT 10,
    scorporo_iva CHAR(1) DEFAULT 'N',
    note_allestimento TEXT,
    is_espositore BOOLEAN DEFAULT FALSE,
    is_child BOOLEAN DEFAULT FALSE,
    is_no_aic BOOLEAN DEFAULT FALSE,
    tipo_riga VARCHAR(20) DEFAULT '',
    id_parent_espositore INTEGER,
    espositore_metadata JSONB,
    stato_riga VARCHAR(20) DEFAULT 'ESTRATTO',
    richiede_supervisione BOOLEAN DEFAULT FALSE,
    id_supervisione INTEGER,
    confermato_da VARCHAR(50),
    data_conferma TIMESTAMP,
    note_supervisione TEXT,
    modificato_manualmente BOOLEAN DEFAULT FALSE,
    valori_originali JSONB,
    q_originale INTEGER DEFAULT 0,
    q_evasa INTEGER DEFAULT 0,
    q_da_evadere INTEGER DEFAULT 0,
    q_esportata INTEGER DEFAULT 0,
    q_residua INTEGER DEFAULT 0,
    num_esportazioni INTEGER DEFAULT 0,
    ultima_esportazione TIMESTAMP,
    id_ultima_esportazione INTEGER
);

CREATE INDEX IF NOT EXISTS idx_dettaglio_testata ON ordini_dettaglio(id_testata);
CREATE INDEX IF NOT EXISTS idx_dettaglio_aic ON ordini_dettaglio(codice_aic);
CREATE INDEX IF NOT EXISTS idx_dettaglio_stato ON ordini_dettaglio(stato_riga);

-- ANOMALIE
CREATE TABLE IF NOT EXISTS anomalie (
    id_anomalia SERIAL PRIMARY KEY,
    id_testata INTEGER REFERENCES ordini_testata(id_testata) ON DELETE CASCADE,
    id_dettaglio INTEGER REFERENCES ordini_dettaglio(id_dettaglio) ON DELETE CASCADE,
    id_acquisizione INTEGER REFERENCES acquisizioni(id_acquisizione),
    tipo_anomalia VARCHAR(50) NOT NULL,
    livello VARCHAR(20) DEFAULT 'ATTENZIONE',
    codice_anomalia VARCHAR(20),
    descrizione TEXT,
    valore_anomalo TEXT,
    stato VARCHAR(20) DEFAULT 'APERTA',
    id_operatore_gestione INTEGER REFERENCES operatori(id_operatore),
    note_risoluzione TEXT,
    data_rilevazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_risoluzione TIMESTAMP,
    richiede_supervisione BOOLEAN DEFAULT FALSE,
    pattern_signature VARCHAR(100)
);

CREATE INDEX IF NOT EXISTS idx_anomalie_tipo ON anomalie(tipo_anomalia, stato);
CREATE INDEX IF NOT EXISTS idx_anomalie_testata ON anomalie(id_testata);

-- SUPERVISIONE_ESPOSITORE
CREATE TABLE IF NOT EXISTS supervisione_espositore (
    id_supervisione SERIAL PRIMARY KEY,
    id_testata INTEGER NOT NULL REFERENCES ordini_testata(id_testata) ON DELETE CASCADE,
    id_anomalia INTEGER REFERENCES anomalie(id_anomalia) ON DELETE SET NULL,
    codice_anomalia VARCHAR(20) NOT NULL,
    codice_espositore VARCHAR(20),
    descrizione_espositore VARCHAR(255),
    pezzi_attesi INTEGER DEFAULT 0,
    pezzi_trovati INTEGER DEFAULT 0,
    valore_calcolato DECIMAL(10, 2) DEFAULT 0,
    pattern_signature VARCHAR(100),
    stato VARCHAR(20) DEFAULT 'PENDING',
    operatore VARCHAR(50),
    timestamp_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    timestamp_decisione TIMESTAMP,
    note TEXT,
    modifiche_manuali_json JSONB
);

CREATE INDEX IF NOT EXISTS idx_supervisione_testata ON supervisione_espositore(id_testata);
CREATE INDEX IF NOT EXISTS idx_supervisione_stato ON supervisione_espositore(stato);

-- CRITERI_ORDINARI_ESPOSITORE
CREATE TABLE IF NOT EXISTS criteri_ordinari_espositore (
    pattern_signature VARCHAR(100) PRIMARY KEY,
    pattern_descrizione TEXT,
    vendor VARCHAR(50) NOT NULL,
    codice_anomalia VARCHAR(20) NOT NULL,
    codice_espositore VARCHAR(20),
    pezzi_per_unita INTEGER,
    tipo_scostamento VARCHAR(20),
    fascia_scostamento VARCHAR(20),
    count_approvazioni INTEGER DEFAULT 0,
    is_ordinario BOOLEAN DEFAULT FALSE,
    data_prima_occorrenza TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_promozione TIMESTAMP,
    operatori_approvatori TEXT
);

-- LOG_CRITERI_APPLICATI
CREATE TABLE IF NOT EXISTS log_criteri_applicati (
    id_log SERIAL PRIMARY KEY,
    id_testata INTEGER REFERENCES ordini_testata(id_testata) ON DELETE SET NULL,
    id_supervisione INTEGER,
    pattern_signature VARCHAR(100) NOT NULL,
    azione VARCHAR(50),
    applicato_automaticamente BOOLEAN DEFAULT FALSE,
    operatore VARCHAR(50),
    note TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- TRACCIATI
CREATE TABLE IF NOT EXISTS tracciati (
    id_tracciato SERIAL PRIMARY KEY,
    nome_file VARCHAR(255) NOT NULL,
    tipo VARCHAR(20) DEFAULT 'CSV',
    num_righe INTEGER DEFAULT 0,
    id_operatore INTEGER REFERENCES operatori(id_operatore),
    note TEXT,
    data_generazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- TRACCIATI_DETTAGLIO
CREATE TABLE IF NOT EXISTS tracciati_dettaglio (
    id SERIAL PRIMARY KEY,
    id_tracciato INTEGER NOT NULL REFERENCES tracciati(id_tracciato) ON DELETE CASCADE,
    id_testata INTEGER REFERENCES ordini_testata(id_testata),
    id_dettaglio INTEGER REFERENCES ordini_dettaglio(id_dettaglio)
);

-- LOG_OPERAZIONI
CREATE TABLE IF NOT EXISTS log_operazioni (
    id_log SERIAL PRIMARY KEY,
    tipo_operazione VARCHAR(50) NOT NULL,
    entita VARCHAR(50),
    id_entita INTEGER,
    descrizione TEXT,
    dati_json JSONB,
    id_operatore INTEGER REFERENCES operatori(id_operatore),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ESPORTAZIONI
CREATE TABLE IF NOT EXISTS esportazioni (
    id_esportazione SERIAL PRIMARY KEY,
    nome_tracciato_generato VARCHAR(255),
    data_tracciato DATE,
    nome_file_to_t VARCHAR(255),
    nome_file_to_d VARCHAR(255),
    num_testate INTEGER DEFAULT 0,
    num_dettagli INTEGER DEFAULT 0,
    stato VARCHAR(20) DEFAULT 'GENERATO',
    note TEXT,
    data_generazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ESPORTAZIONI_DETTAGLIO
CREATE TABLE IF NOT EXISTS esportazioni_dettaglio (
    id SERIAL PRIMARY KEY,
    id_esportazione INTEGER NOT NULL REFERENCES esportazioni(id_esportazione) ON DELETE CASCADE,
    id_testata INTEGER REFERENCES ordini_testata(id_testata)
);

CREATE INDEX IF NOT EXISTS idx_esportazioni_det ON esportazioni_dettaglio(id_esportazione);

-- EMAIL_ACQUISIZIONI (per Gmail monitor)
CREATE TABLE IF NOT EXISTS email_acquisizioni (
    id_email SERIAL PRIMARY KEY,
    message_id VARCHAR(255) UNIQUE NOT NULL,
    gmail_id VARCHAR(100),
    subject VARCHAR(500),
    sender_email VARCHAR(255) NOT NULL,
    sender_name VARCHAR(255),
    received_date TIMESTAMP NOT NULL,
    attachment_filename VARCHAR(255) NOT NULL,
    attachment_size INTEGER,
    attachment_hash VARCHAR(64) NOT NULL,
    id_acquisizione INTEGER REFERENCES acquisizioni(id_acquisizione),
    stato VARCHAR(20) DEFAULT 'DA_PROCESSARE'
        CHECK (stato IN ('DA_PROCESSARE', 'PROCESSATA', 'ERRORE', 'DUPLICATO')),
    data_elaborazione TIMESTAMP,
    errore_messaggio TEXT,
    num_retry INTEGER DEFAULT 0,
    label_applicata VARCHAR(100),
    marcata_come_letta BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_email_message_id ON email_acquisizioni(message_id);
CREATE INDEX IF NOT EXISTS idx_email_hash ON email_acquisizioni(attachment_hash);
CREATE INDEX IF NOT EXISTS idx_email_stato ON email_acquisizioni(stato);

-- =============================================================================
-- SESSIONE_ATTIVITA (Tracking produttività operatori)
-- =============================================================================
CREATE TABLE IF NOT EXISTS sessione_attivita (
    id SERIAL PRIMARY KEY,
    id_operatore INTEGER NOT NULL REFERENCES operatori(id_operatore),
    id_session INTEGER REFERENCES user_sessions(id_session),
    sezione VARCHAR(50) NOT NULL,
    ultimo_heartbeat TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    durata_secondi INTEGER DEFAULT 0,
    data_riferimento DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sessione_attivita_operatore ON sessione_attivita(id_operatore, data_riferimento);
CREATE INDEX IF NOT EXISTS idx_sessione_attivita_session ON sessione_attivita(id_session, sezione);

-- =============================================================================
-- VISTE
-- =============================================================================

-- V_ORDINI_COMPLETI
CREATE OR REPLACE VIEW v_ordini_completi AS
SELECT
    ot.id_testata,
    v.codice_vendor AS vendor,
    ot.numero_ordine_vendor AS numero_ordine,
    ot.data_ordine,
    ot.data_consegna,
    ot.ragione_sociale_1 AS ragione_sociale,
    ot.indirizzo,
    ot.cap,
    ot.citta,
    ot.provincia,
    ot.partita_iva_estratta AS partita_iva,
    ot.codice_ministeriale_estratto AS codice_ministeriale,
    ot.codice_ministeriale_estratto AS min_id,
    ot.lookup_method,
    ot.lookup_score,
    ot.stato,
    ot.data_estrazione,
    ot.data_validazione,
    ot.validato_da,
    ot.righe_totali,
    ot.righe_confermate,
    ot.righe_in_supervisione,
    ot.id_farmacia_lookup,
    ot.id_parafarmacia_lookup,
    f.min_id AS anag_min_id,
    p.codice_sito AS anag_codice_sito,
    a.nome_file_originale AS pdf_file,
    a.data_upload,
    COUNT(od.id_dettaglio) AS num_righe_calc,
    SUM(CASE WHEN od.is_espositore THEN 1 ELSE 0 END) AS num_espositori
FROM ordini_testata ot
JOIN vendor v ON ot.id_vendor = v.id_vendor
JOIN acquisizioni a ON ot.id_acquisizione = a.id_acquisizione
LEFT JOIN anagrafica_farmacie f ON ot.id_farmacia_lookup = f.id_farmacia
LEFT JOIN anagrafica_parafarmacie p ON ot.id_parafarmacia_lookup = p.id_parafarmacia
LEFT JOIN ordini_dettaglio od ON ot.id_testata = od.id_testata
GROUP BY ot.id_testata, v.codice_vendor, f.min_id, p.codice_sito, a.nome_file_originale, a.data_upload;

-- V_DETTAGLI_COMPLETI
CREATE OR REPLACE VIEW v_dettagli_completi AS
SELECT
    od.id_dettaglio,
    od.id_testata,
    od.n_riga,
    od.codice_aic,
    od.codice_originale,
    od.codice_materiale,
    od.descrizione,
    od.tipo_posizione,
    od.q_venduta,
    od.q_sconto_merce,
    od.q_omaggio,
    od.data_consegna_riga,
    od.sconto_1,
    od.sconto_2,
    od.sconto_3,
    od.sconto_4,
    od.prezzo_netto,
    od.prezzo_pubblico,
    od.prezzo_listino,
    od.valore_netto,
    od.aliquota_iva,
    od.is_espositore,
    od.is_child,
    od.is_no_aic,
    od.tipo_riga,
    od.id_parent_espositore,
    od.espositore_metadata,
    od.stato_riga,
    od.richiede_supervisione,
    od.id_supervisione,
    od.confermato_da,
    od.data_conferma,
    od.note_supervisione,
    od.modificato_manualmente,
    od.q_originale,
    od.q_esportata,
    od.q_residua,
    od.num_esportazioni,
    od.ultima_esportazione,
    od.id_ultima_esportazione,
    ot.numero_ordine_vendor AS numero_ordine,
    v.codice_vendor AS vendor
FROM ordini_dettaglio od
JOIN ordini_testata ot ON od.id_testata = ot.id_testata
JOIN vendor v ON ot.id_vendor = v.id_vendor;

-- V_RIGHE_ESPORTABILI
CREATE OR REPLACE VIEW v_righe_esportabili AS
SELECT
    od.id_dettaglio,
    od.id_testata,
    od.n_riga,
    od.codice_aic,
    od.descrizione,
    od.q_venduta,
    od.q_originale,
    od.q_esportata,
    od.q_residua,
    od.stato_riga,
    od.is_child,
    od.num_esportazioni,
    ot.numero_ordine_vendor AS numero_ordine,
    v.codice_vendor AS vendor,
    ot.ragione_sociale_1 AS ragione_sociale
FROM ordini_dettaglio od
JOIN ordini_testata ot ON od.id_testata = ot.id_testata
JOIN vendor v ON ot.id_vendor = v.id_vendor
WHERE od.stato_riga IN ('CONFERMATO', 'PARZIALMENTE_ESP')
    AND NOT od.is_child
    AND (od.q_residua > 0 OR (od.q_residua = 0 AND od.num_esportazioni = 0));

-- V_SUPERVISIONE_PENDING
CREATE OR REPLACE VIEW v_supervisione_pending AS
SELECT
    se.id_supervisione,
    se.id_testata,
    se.codice_anomalia,
    se.codice_espositore,
    se.descrizione_espositore,
    se.pezzi_attesi,
    se.pezzi_trovati,
    se.valore_calcolato,
    se.pattern_signature,
    se.stato,
    se.timestamp_creazione,
    ot.numero_ordine_vendor AS numero_ordine,
    v.codice_vendor AS vendor,
    ot.ragione_sociale_1 AS ragione_sociale,
    ot.citta,
    a.nome_file_originale AS pdf_file,
    COALESCE(coe.count_approvazioni, 0) AS count_pattern,
    COALESCE(coe.is_ordinario, FALSE) AS pattern_ordinario
FROM supervisione_espositore se
JOIN ordini_testata ot ON se.id_testata = ot.id_testata
JOIN vendor v ON ot.id_vendor = v.id_vendor
JOIN acquisizioni a ON ot.id_acquisizione = a.id_acquisizione
LEFT JOIN criteri_ordinari_espositore coe ON se.pattern_signature = coe.pattern_signature
WHERE se.stato = 'PENDING'
ORDER BY se.timestamp_creazione DESC;

-- V_RIGHE_CONFERMABILI
CREATE OR REPLACE VIEW v_righe_confermabili AS
SELECT
    od.id_dettaglio, od.id_testata, od.n_riga, od.codice_aic, od.descrizione,
    od.q_venduta, od.prezzo_netto, od.tipo_riga, od.stato_riga, od.richiede_supervisione,
    ot.numero_ordine_vendor, v.codice_vendor AS vendor
FROM ordini_dettaglio od
JOIN ordini_testata ot ON od.id_testata = ot.id_testata
JOIN vendor v ON ot.id_vendor = v.id_vendor
WHERE od.stato_riga = 'ESTRATTO' AND NOT od.richiede_supervisione;

-- V_RIGHE_IN_SUPERVISIONE
CREATE OR REPLACE VIEW v_righe_in_supervisione AS
SELECT
    od.id_dettaglio, od.id_testata, od.n_riga, od.codice_aic, od.descrizione,
    od.tipo_riga, od.stato_riga, od.id_supervisione,
    se.stato AS stato_supervisione, se.codice_anomalia,
    ot.numero_ordine_vendor, v.codice_vendor AS vendor
FROM ordini_dettaglio od
JOIN ordini_testata ot ON od.id_testata = ot.id_testata
JOIN vendor v ON ot.id_vendor = v.id_vendor
LEFT JOIN supervisione_espositore se ON od.id_supervisione = se.id_supervisione
WHERE od.richiede_supervisione AND od.stato_riga IN ('ESTRATTO', 'IN_SUPERVISIONE');

-- V_PRODUTTIVITA_OPERATORE
CREATE OR REPLACE VIEW v_produttivita_operatore AS
SELECT
    o.id_operatore,
    o.username,
    o.nome,
    o.cognome,
    o.ruolo,
    COALESCE(DATE(l.timestamp), CURRENT_DATE) as data,
    COUNT(CASE WHEN l.tipo_operazione = 'UPDATE_STATO' AND l.descrizione LIKE '%CONFERMATO%' THEN 1 END) as ordini_confermati,
    COUNT(CASE WHEN l.tipo_operazione IN ('MODIFICA_RIGA', 'USER_UPDATE') THEN 1 END) as righe_modificate,
    COUNT(CASE WHEN l.tipo_operazione IN ('SUPERVISIONE_APPROVE', 'SUPERVISIONE_REJECT', 'SUPERVISIONE_MODIFY') THEN 1 END) as anomalie_verificate,
    COUNT(CASE WHEN l.tipo_operazione = 'REGISTRA_EVASIONE' THEN 1 END) as righe_confermate,
    COUNT(CASE WHEN l.tipo_operazione = 'GENERA_TRACCIATI' THEN 1 END) as tracciati_generati
FROM operatori o
LEFT JOIN log_operazioni l ON o.id_operatore = l.id_operatore
WHERE o.ruolo IN ('operatore', 'supervisore')
GROUP BY o.id_operatore, o.username, o.nome, o.cognome, o.ruolo, DATE(l.timestamp);

-- =============================================================================
-- DATI INIZIALI
-- =============================================================================

-- Operatore SYSTEM
INSERT INTO operatori (id_operatore, username, nome, ruolo)
VALUES (1, 'SYSTEM', 'Sistema', 'admin')
ON CONFLICT (username) DO NOTHING;

-- Vendor supportati
INSERT INTO vendor (codice_vendor, ragione_sociale, partita_iva_vendor, note_estrazione) VALUES
    ('ANGELINI', 'Angelini Pharma S.p.A.', NULL, 'ID MIN diretto, sconti a cascata, espositori v3.1'),
    ('BAYER', 'Bayer S.p.A.', NULL, 'Formato SAP'),
    ('CODIFI', 'Codifi S.r.l.', NULL, 'Multi-cliente'),
    ('CHIESI', 'Chiesi Farmaceutici S.p.A.', '02944970348', 'Escludere P.IVA vendor'),
    ('MENARINI', 'Menarini S.r.l.', NULL, 'Parent/Child'),
    ('OPELLA', 'Opella Healthcare Italy S.r.l.', NULL, 'AIC 7-9 cifre'),
    ('DOC_GENERICI', 'DOC Generici S.r.l.', NULL, 'Transfer Order via Grossisti, doppio indirizzo, NO prezzi'),
    ('GENERIC', 'Vendor Generico', NULL, 'Estrattore generico per vendor non riconosciuti')
ON CONFLICT (codice_vendor) DO NOTHING;

-- =============================================================================
-- FINE SCHEMA
-- =============================================================================
