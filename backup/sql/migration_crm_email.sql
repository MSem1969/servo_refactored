-- =============================================================================
-- TO_EXTRACTOR v8.1 - Migrazione CRM & Email
-- =============================================================================
-- Aggiunge tabelle per sistema CRM/Ticketing e configurazione email unificata.
-- Eseguire su database esistente.
-- =============================================================================

-- ============================================================
-- CONFIGURAZIONE EMAIL UNIFICATA (IMAP + SMTP)
-- ============================================================
-- Gestisce sia ricezione email (IMAP) che invio (SMTP)
-- Le credenziali (password) vanno nel file .env, NON qui!
-- ============================================================

CREATE TABLE IF NOT EXISTS email_config (
    id_config SERIAL PRIMARY KEY,

    -- ========== SEZIONE IMAP (Ricezione - Gmail Monitor) ==========
    imap_enabled BOOLEAN DEFAULT FALSE,
    imap_host VARCHAR(100) DEFAULT 'imap.gmail.com',
    imap_port INTEGER DEFAULT 993,
    imap_use_ssl BOOLEAN DEFAULT TRUE,
    imap_folder VARCHAR(50) DEFAULT 'INBOX',
    imap_unread_only BOOLEAN DEFAULT TRUE,
    imap_mark_as_read BOOLEAN DEFAULT TRUE,
    imap_apply_label VARCHAR(50) DEFAULT 'Processed',
    imap_subject_keywords TEXT,          -- JSON array o CSV: "Transfer Order, Ordine"
    imap_sender_whitelist TEXT,          -- JSON array o CSV: "vendor1@mail.com"
    imap_max_emails_per_run INTEGER DEFAULT 50,
    imap_max_attachment_mb INTEGER DEFAULT 50,
    imap_min_attachment_kb INTEGER DEFAULT 10,

    -- ========== SEZIONE SMTP (Invio - CRM Notifiche) ==========
    smtp_enabled BOOLEAN DEFAULT FALSE,
    smtp_host VARCHAR(100) DEFAULT 'smtp.gmail.com',
    smtp_port INTEGER DEFAULT 587,
    smtp_use_tls BOOLEAN DEFAULT TRUE,
    smtp_sender_email VARCHAR(100),      -- Email mittente (es: noreply@azienda.com)
    smtp_sender_name VARCHAR(100) DEFAULT 'TO_EXTRACTOR',
    smtp_rate_limit INTEGER DEFAULT 10,  -- Max email/minuto

    -- ========== METADATI ==========
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by INTEGER REFERENCES operatori(id_operatore)
);

-- Inserisce configurazione default (singleton)
INSERT INTO email_config (id_config)
SELECT 1 WHERE NOT EXISTS (SELECT 1 FROM email_config WHERE id_config = 1);

-- Commento tabella
COMMENT ON TABLE email_config IS 'Configurazione email unificata IMAP/SMTP - credenziali in .env';

-- ============================================================
-- TABELLE CRM
-- ============================================================

-- TICKET
CREATE TABLE IF NOT EXISTS crm_tickets (
    id_ticket SERIAL PRIMARY KEY,
    id_operatore INTEGER REFERENCES operatori(id_operatore),
    categoria VARCHAR(20) NOT NULL CHECK (categoria IN ('suggerimento', 'bug_report')),
    oggetto VARCHAR(200) NOT NULL,
    pagina_origine VARCHAR(50),          -- es: 'dashboard', 'ordine-detail'
    pagina_dettaglio VARCHAR(200),       -- es: 'Ordine #12345'
    stato VARCHAR(20) DEFAULT 'aperto' CHECK (stato IN ('aperto', 'in_lavorazione', 'chiuso')),
    priorita VARCHAR(10) DEFAULT 'normale' CHECK (priorita IN ('bassa', 'normale', 'alta')),
    email_notifica VARCHAR(100),         -- Email esterna per notifiche (opzionale)
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

-- MESSAGGI (thread conversazione)
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

-- LOG EMAIL INVIATE
CREATE TABLE IF NOT EXISTS email_log (
    id_log SERIAL PRIMARY KEY,
    id_ticket INTEGER REFERENCES crm_tickets(id_ticket),
    destinatario VARCHAR(100) NOT NULL,
    oggetto VARCHAR(200) NOT NULL,
    tipo VARCHAR(30) NOT NULL,           -- 'ticket_creato', 'stato_cambiato', 'nuova_risposta', 'test'
    stato_invio VARCHAR(20) DEFAULT 'pending' CHECK (stato_invio IN ('pending', 'sent', 'failed', 'retry')),
    errore TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sent_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_email_log_ticket ON email_log(id_ticket);
CREATE INDEX IF NOT EXISTS idx_email_log_stato ON email_log(stato_invio);
CREATE INDEX IF NOT EXISTS idx_email_log_created ON email_log(created_at DESC);

COMMENT ON TABLE email_log IS 'Log email inviate dal sistema';

-- ============================================================
-- FUNZIONE TRIGGER PER updated_at
-- ============================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger per crm_tickets
DROP TRIGGER IF EXISTS update_crm_tickets_updated_at ON crm_tickets;
CREATE TRIGGER update_crm_tickets_updated_at
    BEFORE UPDATE ON crm_tickets
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger per email_config
DROP TRIGGER IF EXISTS update_email_config_updated_at ON email_config;
CREATE TRIGGER update_email_config_updated_at
    BEFORE UPDATE ON email_config
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- GRANT PERMESSI (se necessario)
-- ============================================================
-- GRANT ALL ON email_config TO app_user;
-- GRANT ALL ON crm_tickets TO app_user;
-- GRANT ALL ON crm_messaggi TO app_user;
-- GRANT ALL ON email_log TO app_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;

-- ============================================================
-- VERIFICA
-- ============================================================
DO $$
BEGIN
    RAISE NOTICE 'Migrazione CRM & Email completata!';
    RAISE NOTICE 'Tabelle create: email_config, crm_tickets, crm_messaggi, email_log';
END $$;
