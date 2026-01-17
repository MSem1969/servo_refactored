-- =============================================================================
-- SERV.O v10.1 - PostgreSQL Schema DDL COMPLETO
-- =============================================================================
-- Schema consolidato che include:
-- - Base schema (v6.2)
-- - Migration v7: Supervisione Listino
-- - Migration v8: Supervisione Lookup, Prezzo
-- - Migration v9: Backup System
-- - Migration v10: Supervisione AIC, Permissions Matrix, Anagrafica Clienti
-- - CRM & Email system
-- - ML Pattern Sequence
-- =============================================================================

-- Estensioni PostgreSQL
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- Per ricerche fuzzy

-- =============================================================================
-- PARTE 1: TABELLE PRINCIPALI
-- =============================================================================

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

-- OPERATORI (utenti sistema)
CREATE TABLE IF NOT EXISTS operatori (
    id_operatore SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) DEFAULT '',
    nome VARCHAR(100),
    cognome VARCHAR(100),
    email VARCHAR(255) UNIQUE,
    ruolo VARCHAR(20) DEFAULT 'operatore'
        CHECK (ruolo IN ('admin', 'operatore', 'supervisore', 'superuser', 'readonly')),
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

-- ANAGRAFICA_CLIENTI (v10 - NON azzerare durante RESET)
CREATE TABLE IF NOT EXISTS anagrafica_clienti (
    id_cliente SERIAL PRIMARY KEY,
    codice_cliente VARCHAR(20) NOT NULL UNIQUE,
    ragione_sociale_1 VARCHAR(100),
    ragione_sociale_2 VARCHAR(100),
    indirizzo VARCHAR(200),
    cap VARCHAR(10),
    localita VARCHAR(100),
    provincia VARCHAR(3),
    partita_iva VARCHAR(16),
    email VARCHAR(200),
    categoria VARCHAR(10),
    codice_farmacia VARCHAR(20),
    codice_stato VARCHAR(10),
    codice_pagamento VARCHAR(10),
    id_tipo VARCHAR(20),
    riferimento VARCHAR(10),
    data_import TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_aggiornamento TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_clienti_codice ON anagrafica_clienti(codice_cliente);
CREATE INDEX IF NOT EXISTS idx_clienti_piva ON anagrafica_clienti(partita_iva);
CREATE INDEX IF NOT EXISTS idx_clienti_localita ON anagrafica_clienti(localita);
CREATE INDEX IF NOT EXISTS idx_clienti_provincia ON anagrafica_clienti(provincia);

COMMENT ON TABLE anagrafica_clienti IS 'Anagrafica clienti esterna - NON azzerare durante RESET';

-- =============================================================================
-- PARTE 2: ORDINI E ACQUISIZIONI
-- =============================================================================

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
CREATE INDEX IF NOT EXISTS idx_acquisizioni_data ON acquisizioni(data_upload);

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
CREATE INDEX IF NOT EXISTS idx_testata_data_ordine ON ordini_testata(data_ordine);

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
    id_ultima_esportazione INTEGER,
    -- v10: AIC inserito manualmente
    codice_aic_inserito TEXT
);

CREATE INDEX IF NOT EXISTS idx_dettaglio_testata ON ordini_dettaglio(id_testata);
CREATE INDEX IF NOT EXISTS idx_dettaglio_aic ON ordini_dettaglio(codice_aic);
CREATE INDEX IF NOT EXISTS idx_dettaglio_stato ON ordini_dettaglio(stato_riga);
CREATE INDEX IF NOT EXISTS idx_dettaglio_parent ON ordini_dettaglio(id_parent_espositore);

-- =============================================================================
-- PARTE 3: ANOMALIE E SUPERVISIONE
-- =============================================================================

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
CREATE INDEX IF NOT EXISTS idx_anomalie_pattern ON anomalie(pattern_signature);

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
    stato VARCHAR(20) DEFAULT 'PENDING'
        CHECK (stato IN ('PENDING', 'APPROVED', 'REJECTED', 'MODIFIED')),
    operatore VARCHAR(50),
    timestamp_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    timestamp_decisione TIMESTAMP,
    note TEXT,
    modifiche_manuali_json JSONB
);

CREATE INDEX IF NOT EXISTS idx_supervisione_testata ON supervisione_espositore(id_testata);
CREATE INDEX IF NOT EXISTS idx_supervisione_stato ON supervisione_espositore(stato);
CREATE INDEX IF NOT EXISTS idx_supervisione_pattern ON supervisione_espositore(pattern_signature);

-- SUPERVISIONE_LISTINO (v7)
CREATE TABLE IF NOT EXISTS supervisione_listino (
    id_supervisione SERIAL PRIMARY KEY,
    id_testata INTEGER NOT NULL REFERENCES ordini_testata(id_testata) ON DELETE CASCADE,
    id_anomalia INTEGER REFERENCES anomalie(id_anomalia) ON DELETE SET NULL,
    codice_anomalia TEXT NOT NULL,
    vendor TEXT NOT NULL,
    codice_aic TEXT,
    n_riga INTEGER,
    descrizione_prodotto TEXT,
    pattern_signature TEXT,
    stato TEXT DEFAULT 'PENDING'
        CHECK (stato IN ('PENDING', 'APPROVED', 'REJECTED', 'MODIFIED')),
    operatore TEXT,
    timestamp_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    timestamp_decisione TIMESTAMP,
    note TEXT,
    prezzo_proposto NUMERIC(10,2),
    sconto_1_proposto NUMERIC(5,2),
    sconto_2_proposto NUMERIC(5,2)
);

CREATE INDEX IF NOT EXISTS idx_sup_listino_testata ON supervisione_listino(id_testata);
CREATE INDEX IF NOT EXISTS idx_sup_listino_stato ON supervisione_listino(stato);
CREATE INDEX IF NOT EXISTS idx_sup_listino_vendor ON supervisione_listino(vendor);

-- SUPERVISIONE_LOOKUP (v8)
CREATE TABLE IF NOT EXISTS supervisione_lookup (
    id_supervisione SERIAL PRIMARY KEY,
    id_testata INTEGER NOT NULL REFERENCES ordini_testata(id_testata) ON DELETE CASCADE,
    id_anomalia INTEGER REFERENCES anomalie(id_anomalia) ON DELETE SET NULL,
    codice_anomalia TEXT NOT NULL,
    vendor TEXT NOT NULL,
    partita_iva_estratta TEXT,
    lookup_method TEXT,
    lookup_score INTEGER,
    pattern_signature TEXT,
    stato TEXT DEFAULT 'PENDING'
        CHECK (stato IN ('PENDING', 'APPROVED', 'REJECTED')),
    operatore TEXT,
    timestamp_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    timestamp_decisione TIMESTAMP,
    note TEXT,
    min_id_assegnato TEXT,
    id_farmacia_selezionata INTEGER REFERENCES anagrafica_farmacie(id_farmacia),
    id_parafarmacia_selezionata INTEGER REFERENCES anagrafica_parafarmacie(id_parafarmacia)
);

CREATE INDEX IF NOT EXISTS idx_sup_lookup_testata ON supervisione_lookup(id_testata);
CREATE INDEX IF NOT EXISTS idx_sup_lookup_stato ON supervisione_lookup(stato);
CREATE INDEX IF NOT EXISTS idx_sup_lookup_pattern ON supervisione_lookup(pattern_signature);

-- SUPERVISIONE_PREZZO (v8.1)
CREATE TABLE IF NOT EXISTS supervisione_prezzo (
    id_supervisione SERIAL PRIMARY KEY,
    id_testata INTEGER REFERENCES ordini_testata(id_testata) ON DELETE CASCADE,
    id_anomalia INTEGER REFERENCES anomalie(id_anomalia) ON DELETE SET NULL,
    codice_anomalia VARCHAR(20) DEFAULT 'PRICE-A01',
    vendor VARCHAR(50),
    numero_ordine VARCHAR(50),
    numero_righe_coinvolte INTEGER DEFAULT 0,
    righe_dettaglio_json JSONB,
    stato VARCHAR(20) DEFAULT 'PENDING'
        CHECK (stato IN ('PENDING', 'APPROVED', 'REJECTED', 'MODIFIED')),
    operatore VARCHAR(100),
    timestamp_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    timestamp_decisione TIMESTAMP,
    note TEXT,
    azione_correttiva VARCHAR(50)
        CHECK (azione_correttiva IN ('PREZZO_INSERITO', 'LISTINO_APPLICATO', 'ACCETTATO_SENZA_PREZZO', 'RIGHE_RIMOSSE'))
);

CREATE INDEX IF NOT EXISTS idx_sup_prezzo_testata ON supervisione_prezzo(id_testata);
CREATE INDEX IF NOT EXISTS idx_sup_prezzo_stato ON supervisione_prezzo(stato);
CREATE INDEX IF NOT EXISTS idx_sup_prezzo_vendor ON supervisione_prezzo(vendor);

COMMENT ON TABLE supervisione_prezzo IS 'Supervisione per anomalie PRICE-A01: prodotti in vendita senza prezzo';

-- SUPERVISIONE_AIC (v10)
CREATE TABLE IF NOT EXISTS supervisione_aic (
    id_supervisione SERIAL PRIMARY KEY,
    id_testata INTEGER NOT NULL REFERENCES ordini_testata(id_testata) ON DELETE CASCADE,
    id_anomalia INTEGER REFERENCES anomalie(id_anomalia) ON DELETE SET NULL,
    id_dettaglio INTEGER REFERENCES ordini_dettaglio(id_dettaglio) ON DELETE SET NULL,
    codice_anomalia TEXT NOT NULL DEFAULT 'AIC-A01',
    vendor TEXT NOT NULL,
    n_riga INTEGER,
    descrizione_prodotto TEXT,
    descrizione_normalizzata TEXT,
    codice_originale TEXT,
    pattern_signature TEXT,
    stato TEXT DEFAULT 'PENDING'
        CHECK (stato IN ('PENDING', 'APPROVED', 'REJECTED')),
    operatore TEXT,
    timestamp_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    timestamp_decisione TIMESTAMP,
    note TEXT,
    codice_aic_assegnato TEXT
);

CREATE INDEX IF NOT EXISTS idx_sup_aic_testata ON supervisione_aic(id_testata);
CREATE INDEX IF NOT EXISTS idx_sup_aic_stato ON supervisione_aic(stato);
CREATE INDEX IF NOT EXISTS idx_sup_aic_pattern ON supervisione_aic(pattern_signature);
CREATE INDEX IF NOT EXISTS idx_sup_aic_vendor_desc ON supervisione_aic(vendor, descrizione_normalizzata);

-- =============================================================================
-- PARTE 4: CRITERI ML ORDINARI
-- =============================================================================

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
    operatori_approvatori TEXT,
    -- v8: ML pattern sequence columns
    descrizione_normalizzata VARCHAR(255),
    child_sequence_json JSONB,
    num_child_attesi INTEGER DEFAULT 0,
    total_applications INTEGER DEFAULT 0,
    successful_applications INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_criteri_vendor ON criteri_ordinari_espositore(vendor);
CREATE INDEX IF NOT EXISTS idx_criteri_descrizione ON criteri_ordinari_espositore(descrizione_normalizzata);
CREATE INDEX IF NOT EXISTS idx_criteri_ordinario ON criteri_ordinari_espositore(is_ordinario) WHERE is_ordinario = TRUE;

COMMENT ON COLUMN criteri_ordinari_espositore.descrizione_normalizzata IS 'Descrizione espositore normalizzata per matching';
COMMENT ON COLUMN criteri_ordinari_espositore.child_sequence_json IS 'Sequenza child appresa in formato JSON';

-- CRITERI_ORDINARI_LISTINO (v7)
CREATE TABLE IF NOT EXISTS criteri_ordinari_listino (
    pattern_signature TEXT PRIMARY KEY,
    pattern_descrizione TEXT,
    vendor TEXT NOT NULL,
    codice_anomalia TEXT NOT NULL,
    codice_aic TEXT,
    count_approvazioni INTEGER DEFAULT 0,
    is_ordinario BOOLEAN DEFAULT FALSE,
    data_prima_occorrenza TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_promozione TIMESTAMP,
    operatori_approvatori TEXT
);

-- CRITERI_ORDINARI_LOOKUP (v8)
CREATE TABLE IF NOT EXISTS criteri_ordinari_lookup (
    pattern_signature TEXT PRIMARY KEY,
    pattern_descrizione TEXT,
    vendor TEXT NOT NULL,
    codice_anomalia TEXT NOT NULL,
    partita_iva_pattern TEXT,
    count_approvazioni INTEGER DEFAULT 0,
    is_ordinario BOOLEAN DEFAULT FALSE,
    data_prima_occorrenza TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_promozione TIMESTAMP,
    operatori_approvatori TEXT,
    min_id_default TEXT,
    id_farmacia_default INTEGER REFERENCES anagrafica_farmacie(id_farmacia)
);

-- CRITERI_ORDINARI_AIC (v10)
CREATE TABLE IF NOT EXISTS criteri_ordinari_aic (
    pattern_signature TEXT PRIMARY KEY,
    pattern_descrizione TEXT,
    vendor TEXT NOT NULL,
    descrizione_normalizzata TEXT NOT NULL,
    count_approvazioni INTEGER DEFAULT 0,
    is_ordinario BOOLEAN DEFAULT FALSE,
    data_prima_occorrenza TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_promozione TIMESTAMP,
    operatori_approvatori TEXT,
    codice_aic_default TEXT
);

CREATE INDEX IF NOT EXISTS idx_crit_aic_vendor_desc ON criteri_ordinari_aic(vendor, descrizione_normalizzata);
CREATE INDEX IF NOT EXISTS idx_crit_aic_ordinario ON criteri_ordinari_aic(is_ordinario) WHERE is_ordinario = TRUE;

-- =============================================================================
-- PARTE 5: LISTINI VENDOR (v7)
-- =============================================================================

CREATE TABLE IF NOT EXISTS listini_vendor (
    id_listino SERIAL PRIMARY KEY,
    vendor TEXT NOT NULL,
    codice_aic TEXT NOT NULL,
    descrizione TEXT,
    sconto_1 NUMERIC(5,2),
    sconto_2 NUMERIC(5,2),
    sconto_3 NUMERIC(5,2),
    sconto_4 NUMERIC(5,2),
    prezzo_netto NUMERIC(10,2),
    prezzo_scontare NUMERIC(10,2),
    prezzo_pubblico NUMERIC(10,2),
    aliquota_iva NUMERIC(5,2),
    scorporo_iva TEXT DEFAULT 'S',
    prezzo_csv_originale NUMERIC(10,2),
    prezzo_pubblico_csv NUMERIC(10,2),
    data_decorrenza DATE,
    attivo BOOLEAN DEFAULT TRUE,
    data_import TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fonte_file TEXT,
    UNIQUE(vendor, codice_aic)
);

CREATE INDEX IF NOT EXISTS idx_listini_vendor ON listini_vendor(vendor);
CREATE INDEX IF NOT EXISTS idx_listini_aic ON listini_vendor(codice_aic);
CREATE INDEX IF NOT EXISTS idx_listini_vendor_aic ON listini_vendor(vendor, codice_aic);

-- =============================================================================
-- PARTE 6: ESPORTAZIONI E TRACCIATI
-- =============================================================================

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

-- =============================================================================
-- PARTE 7: LOG E AUDIT
-- =============================================================================

-- LOG_OPERAZIONI
CREATE TABLE IF NOT EXISTS log_operazioni (
    id_log SERIAL PRIMARY KEY,
    tipo_operazione VARCHAR(50) NOT NULL,
    entita VARCHAR(50),
    id_entita INTEGER,
    descrizione TEXT,
    dati_json JSONB,
    id_operatore INTEGER REFERENCES operatori(id_operatore),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    action_category VARCHAR(50)
);

CREATE INDEX IF NOT EXISTS idx_log_operazioni_tipo ON log_operazioni(tipo_operazione);
CREATE INDEX IF NOT EXISTS idx_log_operazioni_timestamp ON log_operazioni(timestamp DESC);

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

CREATE INDEX IF NOT EXISTS idx_log_criteri_timestamp ON log_criteri_applicati(timestamp DESC);

-- LOG_ML_DECISIONS (v8 - ML Pattern Sequence)
CREATE TABLE IF NOT EXISTS log_ml_decisions (
    id_log SERIAL PRIMARY KEY,
    id_testata INTEGER REFERENCES ordini_testata(id_testata) ON DELETE SET NULL,
    id_dettaglio INTEGER REFERENCES ordini_dettaglio(id_dettaglio) ON DELETE SET NULL,
    pattern_signature VARCHAR(100),
    descrizione_espositore VARCHAR(255),
    child_sequence_estratta JSONB,
    child_sequence_pattern JSONB,
    similarity_score DECIMAL(5,2) NOT NULL,
    decision VARCHAR(20) NOT NULL,
    decision_reason TEXT,
    final_outcome VARCHAR(20),
    operatore VARCHAR(50),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ml_decisions_testata ON log_ml_decisions(id_testata);
CREATE INDEX IF NOT EXISTS idx_ml_decisions_pattern ON log_ml_decisions(pattern_signature);
CREATE INDEX IF NOT EXISTS idx_ml_decisions_decision ON log_ml_decisions(decision);
CREATE INDEX IF NOT EXISTS idx_ml_decisions_timestamp ON log_ml_decisions(timestamp DESC);

COMMENT ON TABLE log_ml_decisions IS 'Log delle decisioni ML per pattern espositori';
COMMENT ON COLUMN log_ml_decisions.decision IS 'APPLY_ML: automatico, APPLY_WARNING: con warning, SEND_SUPERVISION: supervisione';

-- AUDIT_MODIFICHE
CREATE TABLE IF NOT EXISTS audit_modifiche (
    id_audit SERIAL PRIMARY KEY,
    entita VARCHAR(50) NOT NULL,
    id_entita INTEGER NOT NULL,
    id_testata INTEGER,
    campo_modificato VARCHAR(100) NOT NULL,
    valore_precedente TEXT,
    valore_nuovo TEXT,
    fonte_modifica VARCHAR(50),
    id_operatore INTEGER REFERENCES operatori(id_operatore),
    username_operatore VARCHAR(50),
    motivazione TEXT,
    id_sessione VARCHAR(50),
    ip_address VARCHAR(45),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_entita ON audit_modifiche(entita, id_entita);
CREATE INDEX IF NOT EXISTS idx_audit_testata ON audit_modifiche(id_testata);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_modifiche(timestamp DESC);

-- SESSIONE_ATTIVITA (Tracking produttività)
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
-- PARTE 8: EMAIL E CRM (v8.1)
-- =============================================================================

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

-- EMAIL_CONFIG (configurazione unificata IMAP/SMTP)
CREATE TABLE IF NOT EXISTS email_config (
    id_config SERIAL PRIMARY KEY,
    -- IMAP (Ricezione)
    imap_enabled BOOLEAN DEFAULT FALSE,
    imap_host VARCHAR(100) DEFAULT 'imap.gmail.com',
    imap_port INTEGER DEFAULT 993,
    imap_use_ssl BOOLEAN DEFAULT TRUE,
    imap_folder VARCHAR(50) DEFAULT 'INBOX',
    imap_unread_only BOOLEAN DEFAULT TRUE,
    imap_mark_as_read BOOLEAN DEFAULT TRUE,
    imap_apply_label VARCHAR(50) DEFAULT 'Processed',
    imap_subject_keywords TEXT,
    imap_sender_whitelist TEXT,
    imap_max_emails_per_run INTEGER DEFAULT 50,
    imap_max_attachment_mb INTEGER DEFAULT 50,
    imap_min_attachment_kb INTEGER DEFAULT 10,
    -- SMTP (Invio)
    smtp_enabled BOOLEAN DEFAULT FALSE,
    smtp_host VARCHAR(100) DEFAULT 'smtp.gmail.com',
    smtp_port INTEGER DEFAULT 587,
    smtp_use_tls BOOLEAN DEFAULT TRUE,
    smtp_sender_email VARCHAR(100),
    smtp_sender_name VARCHAR(100) DEFAULT 'SERV.O',
    smtp_rate_limit INTEGER DEFAULT 10,
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by INTEGER REFERENCES operatori(id_operatore)
);

COMMENT ON TABLE email_config IS 'Configurazione email unificata IMAP/SMTP - credenziali in .env';

-- CRM_TICKETS
CREATE TABLE IF NOT EXISTS crm_tickets (
    id_ticket SERIAL PRIMARY KEY,
    id_operatore INTEGER REFERENCES operatori(id_operatore),
    categoria VARCHAR(20) NOT NULL CHECK (categoria IN ('suggerimento', 'bug_report')),
    oggetto VARCHAR(200) NOT NULL,
    pagina_origine VARCHAR(50),
    pagina_dettaglio VARCHAR(200),
    stato VARCHAR(20) DEFAULT 'aperto' CHECK (stato IN ('aperto', 'in_lavorazione', 'chiuso')),
    priorita VARCHAR(10) DEFAULT 'normale' CHECK (priorita IN ('bassa', 'normale', 'alta')),
    email_notifica VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP,
    closed_by INTEGER REFERENCES operatori(id_operatore)
);

CREATE INDEX IF NOT EXISTS idx_crm_tickets_operatore ON crm_tickets(id_operatore);
CREATE INDEX IF NOT EXISTS idx_crm_tickets_stato ON crm_tickets(stato);
CREATE INDEX IF NOT EXISTS idx_crm_tickets_categoria ON crm_tickets(categoria);
CREATE INDEX IF NOT EXISTS idx_crm_tickets_created ON crm_tickets(created_at DESC);

COMMENT ON TABLE crm_tickets IS 'Ticket CRM - suggerimenti e bug report utenti';

-- CRM_MESSAGGI
CREATE TABLE IF NOT EXISTS crm_messaggi (
    id_messaggio SERIAL PRIMARY KEY,
    id_ticket INTEGER NOT NULL REFERENCES crm_tickets(id_ticket) ON DELETE CASCADE,
    id_operatore INTEGER REFERENCES operatori(id_operatore),
    contenuto TEXT NOT NULL,
    is_admin_reply BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_crm_messaggi_ticket ON crm_messaggi(id_ticket);
CREATE INDEX IF NOT EXISTS idx_crm_messaggi_created ON crm_messaggi(created_at);

COMMENT ON TABLE crm_messaggi IS 'Messaggi thread ticket CRM';

-- EMAIL_LOG
CREATE TABLE IF NOT EXISTS email_log (
    id_log SERIAL PRIMARY KEY,
    id_ticket INTEGER REFERENCES crm_tickets(id_ticket),
    destinatario VARCHAR(100) NOT NULL,
    oggetto VARCHAR(200) NOT NULL,
    tipo VARCHAR(30) NOT NULL,
    stato_invio VARCHAR(20) DEFAULT 'pending' CHECK (stato_invio IN ('pending', 'sent', 'failed', 'retry')),
    errore TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sent_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_email_log_ticket ON email_log(id_ticket);
CREATE INDEX IF NOT EXISTS idx_email_log_stato ON email_log(stato_invio);
CREATE INDEX IF NOT EXISTS idx_email_log_created ON email_log(created_at DESC);

COMMENT ON TABLE email_log IS 'Log email inviate dal sistema';

-- =============================================================================
-- PARTE 9: BACKUP SYSTEM (v9)
-- =============================================================================

-- BACKUP_STORAGE
CREATE TABLE IF NOT EXISTS backup_storage (
    id_storage SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('local', 'nas', 's3', 'gcs', 'azure')),
    path TEXT NOT NULL,
    config JSONB DEFAULT '{}',
    capacity_gb INTEGER,
    used_gb INTEGER,
    stato VARCHAR(20) DEFAULT 'active' CHECK (stato IN ('active', 'inactive', 'error', 'full')),
    ultimo_check TIMESTAMP,
    ultimo_errore TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES operatori(id_operatore),
    updated_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_backup_storage_tipo ON backup_storage(tipo);
CREATE INDEX IF NOT EXISTS idx_backup_storage_stato ON backup_storage(stato);

-- BACKUP_MODULES
CREATE TABLE IF NOT EXISTS backup_modules (
    id_module SERIAL PRIMARY KEY,
    nome VARCHAR(50) NOT NULL UNIQUE,
    tier INTEGER NOT NULL DEFAULT 1 CHECK (tier BETWEEN 1 AND 6),
    titolo VARCHAR(100) NOT NULL,
    descrizione TEXT,
    enabled BOOLEAN DEFAULT FALSE,
    configured BOOLEAN DEFAULT FALSE,
    config JSONB DEFAULT '{}',
    id_storage INTEGER REFERENCES backup_storage(id_storage),
    schedule_cron VARCHAR(50),
    retention_days INTEGER DEFAULT 7,
    last_run TIMESTAMP,
    last_status VARCHAR(20) CHECK (last_status IN ('success', 'failed', 'running', 'skipped')),
    last_error TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    updated_by INTEGER REFERENCES operatori(id_operatore)
);

-- BACKUP_HISTORY
CREATE TABLE IF NOT EXISTS backup_history (
    id_backup SERIAL PRIMARY KEY,
    id_module INTEGER NOT NULL REFERENCES backup_modules(id_module),
    id_storage INTEGER REFERENCES backup_storage(id_storage),
    backup_type VARCHAR(20) NOT NULL CHECK (backup_type IN ('full', 'incremental', 'wal', 'sync', 'upload')),
    file_path TEXT,
    file_name VARCHAR(255),
    file_size_bytes BIGINT,
    file_checksum VARCHAR(64),
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    duration_seconds INTEGER,
    status VARCHAR(20) NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'success', 'failed', 'cancelled')),
    error_message TEXT,
    metadata JSONB DEFAULT '{}',
    triggered_by VARCHAR(50) DEFAULT 'scheduled',
    operator_id INTEGER REFERENCES operatori(id_operatore)
);

CREATE INDEX IF NOT EXISTS idx_backup_history_module ON backup_history(id_module);
CREATE INDEX IF NOT EXISTS idx_backup_history_status ON backup_history(status);
CREATE INDEX IF NOT EXISTS idx_backup_history_started ON backup_history(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_backup_history_type ON backup_history(backup_type);

-- BACKUP_OPERATIONS_LOG
CREATE TABLE IF NOT EXISTS backup_operations_log (
    id_log SERIAL PRIMARY KEY,
    operation VARCHAR(50) NOT NULL,
    id_module INTEGER REFERENCES backup_modules(id_module),
    id_backup INTEGER REFERENCES backup_history(id_backup),
    details JSONB,
    status VARCHAR(20) NOT NULL CHECK (status IN ('success', 'failed', 'info', 'warning')),
    message TEXT,
    operator_id INTEGER REFERENCES operatori(id_operatore),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_backup_ops_log_operation ON backup_operations_log(operation);
CREATE INDEX IF NOT EXISTS idx_backup_ops_log_module ON backup_operations_log(id_module);
CREATE INDEX IF NOT EXISTS idx_backup_ops_log_created ON backup_operations_log(created_at DESC);

-- BACKUP_SCHEDULES
CREATE TABLE IF NOT EXISTS backup_schedules (
    id_schedule SERIAL PRIMARY KEY,
    id_module INTEGER NOT NULL REFERENCES backup_modules(id_module),
    cron_expression VARCHAR(50) NOT NULL,
    active BOOLEAN DEFAULT TRUE,
    next_run TIMESTAMP,
    last_run TIMESTAMP,
    last_status VARCHAR(20),
    options JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_backup_schedules_module ON backup_schedules(id_module);
CREATE INDEX IF NOT EXISTS idx_backup_schedules_next ON backup_schedules(next_run) WHERE active = TRUE;

-- =============================================================================
-- PARTE 10: PERMISSIONS MATRIX (v10)
-- =============================================================================

-- APP_SEZIONI
CREATE TABLE IF NOT EXISTS app_sezioni (
    codice_sezione VARCHAR(50) PRIMARY KEY,
    nome_display VARCHAR(100) NOT NULL,
    descrizione TEXT,
    icona VARCHAR(50),
    ordine_menu INT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- PERMESSI_RUOLO
CREATE TABLE IF NOT EXISTS permessi_ruolo (
    id_permesso SERIAL PRIMARY KEY,
    ruolo VARCHAR(20) NOT NULL,
    codice_sezione VARCHAR(50) NOT NULL REFERENCES app_sezioni(codice_sezione),
    can_view BOOLEAN DEFAULT FALSE,
    can_edit BOOLEAN DEFAULT FALSE,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(100),
    UNIQUE(ruolo, codice_sezione)
);

CREATE INDEX IF NOT EXISTS idx_permessi_ruolo_ruolo ON permessi_ruolo(ruolo);
CREATE INDEX IF NOT EXISTS idx_permessi_ruolo_sezione ON permessi_ruolo(codice_sezione);

-- =============================================================================
-- PARTE 11: VISTE
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

-- V_SUPERVISIONE_LISTINO_PENDING
CREATE OR REPLACE VIEW v_supervisione_listino_pending AS
SELECT
    sl.id_supervisione,
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
    COALESCE(col.is_ordinario, FALSE) AS pattern_ordinario
FROM supervisione_listino sl
JOIN ordini_testata ot ON sl.id_testata = ot.id_testata
JOIN acquisizioni a ON ot.id_acquisizione = a.id_acquisizione
LEFT JOIN criteri_ordinari_listino col ON sl.pattern_signature = col.pattern_signature
WHERE sl.stato = 'PENDING'
ORDER BY sl.timestamp_creazione DESC;

-- V_SUPERVISIONE_LOOKUP_PENDING
CREATE OR REPLACE VIEW v_supervisione_lookup_pending AS
SELECT
    slk.id_supervisione,
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
    COALESCE(colk.is_ordinario, FALSE) AS pattern_ordinario,
    colk.pattern_descrizione
FROM supervisione_lookup slk
JOIN ordini_testata ot ON slk.id_testata = ot.id_testata
JOIN acquisizioni a ON ot.id_acquisizione = a.id_acquisizione
LEFT JOIN criteri_ordinari_lookup colk ON slk.pattern_signature = colk.pattern_signature
WHERE slk.stato = 'PENDING'
ORDER BY slk.timestamp_creazione DESC;

-- V_SUPERVISIONE_GROUPED_PENDING (raggruppata per pattern)
CREATE OR REPLACE VIEW v_supervisione_grouped_pending AS
WITH all_supervisions AS (
    -- Espositore
    SELECT
        se.pattern_signature,
        'espositore' AS tipo_supervisione,
        se.codice_anomalia,
        v.codice_vendor AS vendor,
        se.id_supervisione,
        se.id_testata,
        se.stato,
        ot.numero_ordine_vendor,
        ot.ragione_sociale_1,
        se.timestamp_creazione,
        COALESCE(coe.count_approvazioni, 0) AS pattern_count,
        COALESCE(coe.is_ordinario, FALSE) AS pattern_ordinario,
        coe.pattern_descrizione
    FROM supervisione_espositore se
    JOIN ordini_testata ot ON se.id_testata = ot.id_testata
    JOIN vendor v ON ot.id_vendor = v.id_vendor
    LEFT JOIN criteri_ordinari_espositore coe ON se.pattern_signature = coe.pattern_signature
    WHERE se.stato = 'PENDING'

    UNION ALL

    -- Listino
    SELECT
        sl.pattern_signature,
        'listino' AS tipo_supervisione,
        sl.codice_anomalia,
        sl.vendor,
        sl.id_supervisione,
        sl.id_testata,
        sl.stato,
        ot.numero_ordine_vendor,
        ot.ragione_sociale_1,
        sl.timestamp_creazione,
        COALESCE(col.count_approvazioni, 0) AS pattern_count,
        COALESCE(col.is_ordinario, FALSE) AS pattern_ordinario,
        col.pattern_descrizione
    FROM supervisione_listino sl
    JOIN ordini_testata ot ON sl.id_testata = ot.id_testata
    LEFT JOIN criteri_ordinari_listino col ON sl.pattern_signature = col.pattern_signature
    WHERE sl.stato = 'PENDING'

    UNION ALL

    -- Lookup
    SELECT
        slk.pattern_signature,
        'lookup' AS tipo_supervisione,
        slk.codice_anomalia,
        slk.vendor,
        slk.id_supervisione,
        slk.id_testata,
        slk.stato,
        ot.numero_ordine_vendor,
        ot.ragione_sociale_1,
        slk.timestamp_creazione,
        COALESCE(colk.count_approvazioni, 0) AS pattern_count,
        COALESCE(colk.is_ordinario, FALSE) AS pattern_ordinario,
        colk.pattern_descrizione
    FROM supervisione_lookup slk
    JOIN ordini_testata ot ON slk.id_testata = ot.id_testata
    LEFT JOIN criteri_ordinari_lookup colk ON slk.pattern_signature = colk.pattern_signature
    WHERE slk.stato = 'PENDING'

    UNION ALL

    -- Prezzo
    SELECT
        sp.codice_anomalia || '_' || sp.id_testata AS pattern_signature,
        'prezzo' AS tipo_supervisione,
        sp.codice_anomalia,
        sp.vendor,
        sp.id_supervisione,
        sp.id_testata,
        sp.stato,
        ot.numero_ordine_vendor,
        ot.ragione_sociale_1,
        sp.timestamp_creazione,
        0 AS pattern_count,
        FALSE AS pattern_ordinario,
        NULL AS pattern_descrizione
    FROM supervisione_prezzo sp
    JOIN ordini_testata ot ON sp.id_testata = ot.id_testata
    WHERE sp.stato = 'PENDING'

    UNION ALL

    -- AIC
    SELECT
        saic.pattern_signature,
        'aic' AS tipo_supervisione,
        saic.codice_anomalia,
        saic.vendor,
        saic.id_supervisione,
        saic.id_testata,
        saic.stato,
        ot.numero_ordine_vendor,
        ot.ragione_sociale_1,
        saic.timestamp_creazione,
        COALESCE(coaic.count_approvazioni, 0) AS pattern_count,
        COALESCE(coaic.is_ordinario, FALSE) AS pattern_ordinario,
        coaic.pattern_descrizione
    FROM supervisione_aic saic
    JOIN ordini_testata ot ON saic.id_testata = ot.id_testata
    LEFT JOIN criteri_ordinari_aic coaic ON saic.pattern_signature = coaic.pattern_signature
    WHERE saic.stato = 'PENDING'
)
SELECT
    pattern_signature,
    tipo_supervisione,
    codice_anomalia,
    vendor,
    COUNT(*) AS total_count,
    ARRAY_AGG(DISTINCT id_testata) AS affected_order_ids,
    ARRAY_AGG(id_supervisione) AS supervision_ids,
    MAX(pattern_count) AS pattern_count,
    BOOL_OR(pattern_ordinario) AS pattern_ordinario,
    MAX(pattern_descrizione) AS pattern_descrizione,
    ARRAY_AGG(DISTINCT numero_ordine_vendor) AS affected_orders_preview,
    ARRAY_AGG(DISTINCT ragione_sociale_1) AS affected_clients_preview,
    MIN(timestamp_creazione) AS first_occurrence
FROM all_supervisions
WHERE pattern_signature IS NOT NULL
GROUP BY pattern_signature, tipo_supervisione, codice_anomalia, vendor
ORDER BY first_occurrence DESC;

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

-- V_BACKUP_DASHBOARD
CREATE OR REPLACE VIEW v_backup_dashboard AS
SELECT
    m.id_module,
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
    (SELECT COUNT(*) FROM backup_history h
     WHERE h.id_module = m.id_module
     AND h.started_at > CURRENT_TIMESTAMP - INTERVAL '7 days') AS backups_7d,
    (SELECT COUNT(*) FROM backup_history h
     WHERE h.id_module = m.id_module
     AND h.status = 'failed'
     AND h.started_at > CURRENT_TIMESTAMP - INTERVAL '7 days') AS failures_7d,
    (SELECT MAX(completed_at) FROM backup_history h
     WHERE h.id_module = m.id_module
     AND h.status = 'success') AS last_success,
    (SELECT COALESCE(SUM(file_size_bytes), 0) FROM backup_history h
     WHERE h.id_module = m.id_module
     AND h.status = 'success') AS total_bytes
FROM backup_modules m
LEFT JOIN backup_storage s ON m.id_storage = s.id_storage
ORDER BY m.tier;

-- V_BACKUP_HISTORY_DETAIL
CREATE OR REPLACE VIEW v_backup_history_detail AS
SELECT
    h.id_backup,
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

-- =============================================================================
-- PARTE 12: FUNZIONI E TRIGGERS
-- =============================================================================

-- Funzione per aggiornare updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers per updated_at
DROP TRIGGER IF EXISTS update_crm_tickets_updated_at ON crm_tickets;
CREATE TRIGGER update_crm_tickets_updated_at
    BEFORE UPDATE ON crm_tickets
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_email_config_updated_at ON email_config;
CREATE TRIGGER update_email_config_updated_at
    BEFORE UPDATE ON email_config
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Funzione per backup timestamp
CREATE OR REPLACE FUNCTION backup_update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_backup_modules_updated ON backup_modules;
CREATE TRIGGER trg_backup_modules_updated
    BEFORE UPDATE ON backup_modules
    FOR EACH ROW
    EXECUTE FUNCTION backup_update_timestamp();

DROP TRIGGER IF EXISTS trg_backup_storage_updated ON backup_storage;
CREATE TRIGGER trg_backup_storage_updated
    BEFORE UPDATE ON backup_storage
    FOR EACH ROW
    EXECUTE FUNCTION backup_update_timestamp();

-- =============================================================================
-- PARTE 13: DATI INIZIALI (SEED DATA)
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

-- Email config singleton
INSERT INTO email_config (id_config)
SELECT 1 WHERE NOT EXISTS (SELECT 1 FROM email_config WHERE id_config = 1);

-- Backup modules predefiniti
INSERT INTO backup_modules (nome, tier, titolo, descrizione) VALUES
    ('wal_archive', 1, 'WAL Archiving', 'Archiviazione continua WAL segments per Point-in-Time Recovery (PITR).'),
    ('full_backup', 2, 'Backup Completo', 'Backup full periodico con pg_dump.'),
    ('incremental', 3, 'Backup Incrementale', 'Backup incrementale con pg_basebackup.'),
    ('offsite_sync', 4, 'Sync Offsite', 'Sincronizzazione backup su storage remoto via rsync.'),
    ('cloud_backup', 5, 'Cloud Backup', 'Upload backup su cloud storage (S3, GCS, Azure).'),
    ('replica', 6, 'Standby Replica', 'Replica PostgreSQL in streaming per failover.')
ON CONFLICT (nome) DO NOTHING;

-- Storage predefinito
INSERT INTO backup_storage (nome, tipo, path, stato, created_by)
VALUES ('Local Backup', 'local', '/backup/postgresql', 'inactive', 1)
ON CONFLICT DO NOTHING;

-- Sezioni applicazione
INSERT INTO app_sezioni (codice_sezione, nome_display, descrizione, icona, ordine_menu) VALUES
    ('dashboard', 'Dashboard', 'Panoramica generale del sistema', 'LayoutDashboard', 1),
    ('upload', 'Upload PDF', 'Caricamento documenti PDF', 'Upload', 2),
    ('database', 'Database Ordini', 'Gestione ordini e dettagli', 'Database', 3),
    ('supervisione', 'Supervisione ML', 'Supervisione anomalie machine learning', 'Brain', 4),
    ('tracciati', 'Tracciati EDI', 'Generazione tracciati ministeriali', 'FileText', 5),
    ('export', 'Export Report', 'Esportazione report e statistiche', 'Download', 6),
    ('anagrafica', 'Anagrafica', 'Gestione anagrafiche clienti', 'Users', 7),
    ('crm', 'CRM', 'Customer relationship management', 'MessageSquare', 8),
    ('backup', 'Backup', 'Gestione backup database', 'HardDrive', 9),
    ('settings', 'Impostazioni', 'Configurazione sistema', 'Settings', 10),
    ('utenti', 'Utenti', 'Gestione utenti e permessi', 'UserCog', 11)
ON CONFLICT (codice_sezione) DO NOTHING;

-- Permessi default per ruoli
INSERT INTO permessi_ruolo (ruolo, codice_sezione, can_view, can_edit) VALUES
    -- Admin
    ('admin', 'dashboard', TRUE, TRUE), ('admin', 'upload', TRUE, TRUE),
    ('admin', 'database', TRUE, TRUE), ('admin', 'supervisione', TRUE, TRUE),
    ('admin', 'tracciati', TRUE, TRUE), ('admin', 'export', TRUE, TRUE),
    ('admin', 'anagrafica', TRUE, TRUE), ('admin', 'crm', TRUE, TRUE),
    ('admin', 'backup', TRUE, TRUE), ('admin', 'settings', TRUE, TRUE),
    ('admin', 'utenti', TRUE, TRUE),
    -- Superuser
    ('superuser', 'dashboard', TRUE, TRUE), ('superuser', 'upload', TRUE, TRUE),
    ('superuser', 'database', TRUE, TRUE), ('superuser', 'supervisione', TRUE, TRUE),
    ('superuser', 'tracciati', TRUE, TRUE), ('superuser', 'export', TRUE, TRUE),
    ('superuser', 'anagrafica', TRUE, TRUE), ('superuser', 'crm', TRUE, TRUE),
    ('superuser', 'backup', FALSE, FALSE), ('superuser', 'settings', TRUE, FALSE),
    ('superuser', 'utenti', TRUE, TRUE),
    -- Supervisore
    ('supervisore', 'dashboard', TRUE, TRUE), ('supervisore', 'upload', TRUE, TRUE),
    ('supervisore', 'database', TRUE, TRUE), ('supervisore', 'supervisione', TRUE, TRUE),
    ('supervisore', 'tracciati', TRUE, TRUE), ('supervisore', 'export', TRUE, TRUE),
    ('supervisore', 'anagrafica', TRUE, TRUE), ('supervisore', 'crm', TRUE, TRUE),
    ('supervisore', 'backup', FALSE, FALSE), ('supervisore', 'settings', TRUE, FALSE),
    ('supervisore', 'utenti', TRUE, FALSE),
    -- Operatore
    ('operatore', 'dashboard', TRUE, FALSE), ('operatore', 'upload', TRUE, TRUE),
    ('operatore', 'database', TRUE, TRUE), ('operatore', 'supervisione', FALSE, FALSE),
    ('operatore', 'tracciati', TRUE, FALSE), ('operatore', 'export', TRUE, FALSE),
    ('operatore', 'anagrafica', FALSE, FALSE), ('operatore', 'crm', FALSE, FALSE),
    ('operatore', 'backup', FALSE, FALSE), ('operatore', 'settings', TRUE, FALSE),
    ('operatore', 'utenti', FALSE, FALSE),
    -- Readonly
    ('readonly', 'dashboard', TRUE, FALSE), ('readonly', 'upload', FALSE, FALSE),
    ('readonly', 'database', TRUE, FALSE), ('readonly', 'supervisione', FALSE, FALSE),
    ('readonly', 'tracciati', TRUE, FALSE), ('readonly', 'export', FALSE, FALSE),
    ('readonly', 'anagrafica', TRUE, FALSE), ('readonly', 'crm', FALSE, FALSE),
    ('readonly', 'backup', FALSE, FALSE), ('readonly', 'settings', TRUE, FALSE),
    ('readonly', 'utenti', FALSE, FALSE)
ON CONFLICT (ruolo, codice_sezione) DO NOTHING;

-- =============================================================================
-- FINE SCHEMA v10.1
-- =============================================================================

DO $$
BEGIN
    RAISE NOTICE '=============================================================================';
    RAISE NOTICE 'SERV.O v10.1 - Schema PostgreSQL creato con successo';
    RAISE NOTICE '=============================================================================';
    RAISE NOTICE 'Tabelle principali: vendor, operatori, anagrafica_*, ordini_*, anomalie';
    RAISE NOTICE 'Supervisione: espositore, listino, lookup, prezzo, aic';
    RAISE NOTICE 'Criteri ML: espositore, listino, lookup, aic';
    RAISE NOTICE 'Sistema: email_config, crm_*, backup_*, app_sezioni, permessi_ruolo';
    RAISE NOTICE 'Viste: v_ordini_completi, v_supervisione_*, v_backup_*';
    RAISE NOTICE '=============================================================================';
END $$;
