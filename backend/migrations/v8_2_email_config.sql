-- =============================================================================
-- SERV.O v8.2 - Migrazione Tabella email_config
-- =============================================================================
-- Tabella configurazione email IMAP/SMTP
-- =============================================================================

-- Tabella configurazione email
CREATE TABLE IF NOT EXISTS email_config (
    id_config SERIAL PRIMARY KEY,

    -- IMAP Settings
    imap_enabled BOOLEAN DEFAULT FALSE,
    imap_host VARCHAR(100) DEFAULT 'imap.gmail.com',
    imap_port INTEGER DEFAULT 993,
    imap_use_ssl BOOLEAN DEFAULT TRUE,
    imap_folder VARCHAR(50) DEFAULT 'INBOX',
    imap_unread_only BOOLEAN DEFAULT TRUE,
    imap_mark_as_read BOOLEAN DEFAULT TRUE,
    imap_apply_label VARCHAR(50) DEFAULT NULL,
    imap_subject_keywords TEXT DEFAULT NULL,  -- Comma-separated
    imap_sender_whitelist TEXT DEFAULT NULL,  -- Comma-separated
    imap_max_emails_per_run INTEGER DEFAULT 50,

    -- SMTP Settings
    smtp_enabled BOOLEAN DEFAULT FALSE,
    smtp_host VARCHAR(100) DEFAULT 'smtp.gmail.com',
    smtp_port INTEGER DEFAULT 587,
    smtp_use_tls BOOLEAN DEFAULT TRUE,
    smtp_sender_email VARCHAR(100) DEFAULT NULL,
    smtp_sender_name VARCHAR(100) DEFAULT 'SERV.O Sistema',
    smtp_rate_limit INTEGER DEFAULT 10,  -- email/minuto

    -- Admin notifications
    admin_notifica_email TEXT DEFAULT NULL,  -- Comma-separated

    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by INTEGER REFERENCES operatori(id_operatore)
);

-- Inserisci configurazione default se non esiste
INSERT INTO email_config (id_config, imap_enabled, smtp_enabled)
SELECT 1, FALSE, FALSE
WHERE NOT EXISTS (SELECT 1 FROM email_config WHERE id_config = 1);

-- Indice per velocizzare lookup
CREATE INDEX IF NOT EXISTS idx_email_config_id ON email_config(id_config);

-- =============================================================================
-- Tabella log email inviate (se non esiste)
-- =============================================================================

CREATE TABLE IF NOT EXISTS email_log (
    id_log SERIAL PRIMARY KEY,

    -- Destinatario
    destinatario VARCHAR(255) NOT NULL,

    -- Contenuto
    oggetto VARCHAR(500),
    corpo TEXT,

    -- Tipo e stato
    tipo VARCHAR(50) DEFAULT 'generic',
    stato_invio VARCHAR(20) DEFAULT 'pending',

    -- Riferimenti
    ticket_id INTEGER DEFAULT NULL,

    -- Tentativi
    tentativi INTEGER DEFAULT 0,
    ultimo_errore TEXT DEFAULT NULL,

    -- Timestamp
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sent_at TIMESTAMP DEFAULT NULL,

    -- Chi ha richiesto l'invio
    richiesto_da INTEGER REFERENCES operatori(id_operatore)
);

-- Indici per query comuni
CREATE INDEX IF NOT EXISTS idx_email_log_stato ON email_log(stato_invio);
CREATE INDEX IF NOT EXISTS idx_email_log_tipo ON email_log(tipo);
CREATE INDEX IF NOT EXISTS idx_email_log_ticket ON email_log(ticket_id);
CREATE INDEX IF NOT EXISTS idx_email_log_created ON email_log(created_at DESC);

-- =============================================================================
-- GRANT (se necessario per utente servo_user)
-- =============================================================================

-- GRANT ALL PRIVILEGES ON email_config TO servo_user;
-- GRANT ALL PRIVILEGES ON email_log TO servo_user;
-- GRANT USAGE, SELECT ON SEQUENCE email_config_id_config_seq TO servo_user;
-- GRANT USAGE, SELECT ON SEQUENCE email_log_id_log_seq TO servo_user;
