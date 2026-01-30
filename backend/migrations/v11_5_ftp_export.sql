-- =============================================================================
-- SERV.O v11.5 - FTP EXPORT CONFIGURATION
-- =============================================================================
-- Configurazione per invio tracciati via FTP verso ERP SOFAD
-- =============================================================================

-- Tabella configurazione FTP
CREATE TABLE IF NOT EXISTS ftp_config (
    id_config SERIAL PRIMARY KEY,

    -- Connessione
    ftp_enabled BOOLEAN DEFAULT FALSE,
    ftp_host VARCHAR(100) NOT NULL,
    ftp_port INTEGER DEFAULT 21,
    ftp_username VARCHAR(100) NOT NULL,
    -- Password in variabile ambiente FTP_PASSWORD

    -- Modalita
    ftp_passive_mode BOOLEAN DEFAULT FALSE,  -- FALSE = modalita attiva
    ftp_timeout INTEGER DEFAULT 30,  -- secondi

    -- Retry
    max_tentativi INTEGER DEFAULT 3,
    intervallo_retry_secondi INTEGER DEFAULT 60,

    -- Batch
    batch_intervallo_minuti INTEGER DEFAULT 10,
    batch_enabled BOOLEAN DEFAULT TRUE,

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(100)
);

-- Tabella mapping vendor -> path FTP
CREATE TABLE IF NOT EXISTS ftp_vendor_mapping (
    id SERIAL PRIMARY KEY,
    vendor_code VARCHAR(50) NOT NULL,  -- Es: ANGELINI, DOC_GENERICI, CODIFI
    ftp_path VARCHAR(255) NOT NULL,    -- Es: ./ANGELINI, ./DOC, ./CODIFI
    deposito VARCHAR(10),              -- CT, CL o NULL per tutti
    attivo BOOLEAN DEFAULT TRUE,
    note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(vendor_code, deposito)
);

-- Aggiunta colonne a tabella esportazioni per tracciamento invio FTP
ALTER TABLE esportazioni
ADD COLUMN IF NOT EXISTS stato_ftp VARCHAR(20) DEFAULT 'PENDING',
ADD COLUMN IF NOT EXISTS data_invio_ftp TIMESTAMP,
ADD COLUMN IF NOT EXISTS tentativi_ftp INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS ultimo_errore_ftp TEXT,
ADD COLUMN IF NOT EXISTS ftp_path_remoto VARCHAR(255),
ADD COLUMN IF NOT EXISTS ftp_file_inviati TEXT;  -- JSON array dei file inviati

-- Indice per query batch
CREATE INDEX IF NOT EXISTS idx_esportazioni_stato_ftp
ON esportazioni(stato_ftp) WHERE stato_ftp IN ('PENDING', 'RETRY');

-- Tabella log invii FTP (per audit e debug)
CREATE TABLE IF NOT EXISTS ftp_log (
    id SERIAL PRIMARY KEY,
    id_esportazione INTEGER REFERENCES esportazioni(id_esportazione),
    azione VARCHAR(50) NOT NULL,  -- CONNECT, UPLOAD, DISCONNECT, ERROR
    file_name VARCHAR(255),
    ftp_path VARCHAR(255),
    esito VARCHAR(20),  -- SUCCESS, FAILED
    messaggio TEXT,
    durata_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indice per query log
CREATE INDEX IF NOT EXISTS idx_ftp_log_esportazione
ON ftp_log(id_esportazione);

CREATE INDEX IF NOT EXISTS idx_ftp_log_created
ON ftp_log(created_at DESC);

-- =============================================================================
-- DATI INIZIALI
-- =============================================================================

-- Configurazione FTP iniziale (SOFAD)
INSERT INTO ftp_config (
    ftp_enabled, ftp_host, ftp_port, ftp_username, ftp_passive_mode,
    ftp_timeout, max_tentativi, batch_intervallo_minuti, batch_enabled
) VALUES (
    TRUE,           -- Abilitato
    '85.39.189.15', -- Host SOFAD
    21,             -- Porta standard
    'sofadto',      -- Username
    FALSE,          -- Modalita ATTIVA (non passiva)
    30,             -- Timeout 30 secondi
    3,              -- Max 3 tentativi
    10,             -- Batch ogni 10 minuti
    TRUE            -- Batch abilitato
) ON CONFLICT DO NOTHING;

-- Mapping vendor -> path FTP
INSERT INTO ftp_vendor_mapping (vendor_code, ftp_path, deposito, note) VALUES
    ('ANGELINI', './ANGELINI', NULL, 'Tutti i depositi'),
    ('DOC_GENERICI', './DOC', NULL, 'Tutti i depositi'),
    ('CODIFI', './CODIFI', NULL, 'Tutti i depositi')
ON CONFLICT (vendor_code, deposito) DO NOTHING;

-- =============================================================================
-- COMMENTI
-- =============================================================================

COMMENT ON TABLE ftp_config IS 'Configurazione connessione FTP per export tracciati';
COMMENT ON TABLE ftp_vendor_mapping IS 'Mapping vendor -> path remoto FTP';
COMMENT ON TABLE ftp_log IS 'Log dettagliato operazioni FTP';

COMMENT ON COLUMN esportazioni.stato_ftp IS 'PENDING, SENDING, SENT, FAILED, RETRY, SKIPPED';
COMMENT ON COLUMN esportazioni.ftp_file_inviati IS 'JSON array: ["TO_T_xxx.txt", "TO_D_xxx.txt"]';
