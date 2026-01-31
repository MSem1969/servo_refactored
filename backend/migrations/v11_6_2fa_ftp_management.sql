-- =============================================================================
-- SERV.O v11.6 - 2FA SYSTEM + FTP MANAGEMENT
-- =============================================================================
-- Sistema 2FA via Email OTP + Gestione avanzata endpoint FTP
-- Requisito NIS-2 compliance
-- =============================================================================

-- =============================================================================
-- SISTEMA 2FA (Email OTP)
-- =============================================================================

-- Tabella token OTP
CREATE TABLE IF NOT EXISTS otp_tokens (
    id SERIAL PRIMARY KEY,
    id_operatore INTEGER REFERENCES operatori(id_operatore) ON DELETE CASCADE,
    codice VARCHAR(6) NOT NULL,
    tipo_operazione VARCHAR(50) NOT NULL,  -- 'FTP_VIEW_PASSWORD', 'FTP_EDIT', 'ADMIN_ACTION', etc.
    riferimento_id INTEGER,                 -- ID risorsa correlata (es. id endpoint FTP)
    scadenza TIMESTAMP NOT NULL,
    utilizzato BOOLEAN DEFAULT FALSE,
    ip_richiesta VARCHAR(45),              -- IPv4 o IPv6
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    verified_at TIMESTAMP
);

-- Indici OTP
CREATE INDEX IF NOT EXISTS idx_otp_operatore ON otp_tokens(id_operatore);
CREATE INDEX IF NOT EXISTS idx_otp_codice ON otp_tokens(codice) WHERE utilizzato = FALSE;
CREATE INDEX IF NOT EXISTS idx_otp_scadenza ON otp_tokens(scadenza) WHERE utilizzato = FALSE;

-- Log 2FA per audit
CREATE TABLE IF NOT EXISTS otp_audit_log (
    id SERIAL PRIMARY KEY,
    id_operatore INTEGER REFERENCES operatori(id_operatore),
    tipo_operazione VARCHAR(50) NOT NULL,
    esito VARCHAR(20) NOT NULL,            -- 'SUCCESS', 'FAILED', 'EXPIRED', 'INVALID'
    ip_address VARCHAR(45),
    user_agent TEXT,
    dettagli TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_otp_audit_operatore ON otp_audit_log(id_operatore);
CREATE INDEX IF NOT EXISTS idx_otp_audit_created ON otp_audit_log(created_at DESC);

-- =============================================================================
-- GESTIONE AVANZATA FTP ENDPOINTS
-- =============================================================================

-- Nuova tabella endpoint FTP (sostituisce ftp_vendor_mapping)
CREATE TABLE IF NOT EXISTS ftp_endpoints (
    id SERIAL PRIMARY KEY,

    -- Identificazione
    nome VARCHAR(100) NOT NULL,            -- Es: "SOFAD Catania - Angelini"
    descrizione TEXT,

    -- Mapping
    vendor_code VARCHAR(50) NOT NULL,      -- Es: ANGELINI, DOC_GENERICI
    deposito VARCHAR(10),                  -- Es: CT, CL (NULL = tutti)

    -- Connessione FTP
    ftp_host VARCHAR(100) NOT NULL,
    ftp_port INTEGER DEFAULT 21,
    ftp_path VARCHAR(255) NOT NULL,        -- Es: ./ANGELINI
    ftp_username VARCHAR(100) NOT NULL,
    ftp_password_encrypted TEXT NOT NULL,  -- AES-256 encrypted
    ftp_passive_mode BOOLEAN DEFAULT FALSE,
    ftp_timeout INTEGER DEFAULT 30,

    -- Stato
    attivo BOOLEAN DEFAULT TRUE,
    ordine INTEGER DEFAULT 0,              -- Per ordinamento UI

    -- Retry config
    max_tentativi INTEGER DEFAULT 3,
    intervallo_retry_sec INTEGER DEFAULT 60,

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES operatori(id_operatore),
    updated_by INTEGER REFERENCES operatori(id_operatore),

    -- Constraint: un solo endpoint per vendor+deposito
    UNIQUE(vendor_code, deposito)
);

-- Indici FTP endpoints
CREATE INDEX IF NOT EXISTS idx_ftp_endpoints_vendor ON ftp_endpoints(vendor_code);
CREATE INDEX IF NOT EXISTS idx_ftp_endpoints_deposito ON ftp_endpoints(deposito);
CREATE INDEX IF NOT EXISTS idx_ftp_endpoints_attivo ON ftp_endpoints(attivo) WHERE attivo = TRUE;

-- Log operazioni FTP per endpoint (estende ftp_log esistente)
ALTER TABLE ftp_log ADD COLUMN IF NOT EXISTS id_endpoint INTEGER REFERENCES ftp_endpoints(id);
CREATE INDEX IF NOT EXISTS idx_ftp_log_endpoint ON ftp_log(id_endpoint);

-- =============================================================================
-- CONFIGURAZIONE GLOBALE 2FA
-- =============================================================================

-- Aggiungi colonne 2FA a operatori
ALTER TABLE operatori ADD COLUMN IF NOT EXISTS email_2fa VARCHAR(255);
ALTER TABLE operatori ADD COLUMN IF NOT EXISTS twofa_enabled BOOLEAN DEFAULT FALSE;
ALTER TABLE operatori ADD COLUMN IF NOT EXISTS twofa_required_for TEXT[];  -- Array operazioni che richiedono 2FA

-- =============================================================================
-- MIGRAZIONE DATI DA VECCHIA STRUTTURA
-- =============================================================================

-- Se esistono dati in ftp_vendor_mapping, NON migrarli automaticamente
-- perché non hanno password. L'admin dovrà ricrearli manualmente.

-- Disabilita la vecchia tabella (la terremo per riferimento)
-- ALTER TABLE ftp_vendor_mapping RENAME TO ftp_vendor_mapping_old;

-- =============================================================================
-- FUNZIONI UTILITY
-- =============================================================================

-- Funzione per pulire OTP scaduti (da chiamare periodicamente)
CREATE OR REPLACE FUNCTION cleanup_expired_otp()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM otp_tokens
    WHERE scadenza < NOW() - INTERVAL '1 hour'
       OR (utilizzato = TRUE AND created_at < NOW() - INTERVAL '1 day');
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- COMMENTI
-- =============================================================================

COMMENT ON TABLE otp_tokens IS 'Token OTP per autenticazione a due fattori via email';
COMMENT ON TABLE otp_audit_log IS 'Log audit per tutte le operazioni 2FA';
COMMENT ON TABLE ftp_endpoints IS 'Configurazione endpoint FTP per vendor/deposito con credenziali criptate';

COMMENT ON COLUMN ftp_endpoints.ftp_password_encrypted IS 'Password criptata con AES-256, chiave in FTP_ENCRYPTION_KEY env';
COMMENT ON COLUMN otp_tokens.tipo_operazione IS 'Tipo: FTP_VIEW_PASSWORD, FTP_EDIT, ADMIN_ACTION, etc.';
COMMENT ON COLUMN operatori.twofa_required_for IS 'Array di operazioni che richiedono 2FA per questo operatore';
