-- ============================================================
-- MIGRAZIONE: Configurazione Email & Fix CRM Categories
-- ============================================================
-- Eseguire con: psql -h localhost -U to_extractor_user -d to_extractor -f backup/sql/migration_email_config.sql
-- ============================================================

BEGIN;

-- ============================================================
-- 1. FIX CATEGORIA CRM TICKETS (assistenza/miglioramento)
-- ============================================================
-- Prima rimuovi il vincolo esistente
ALTER TABLE crm_tickets DROP CONSTRAINT IF EXISTS crm_tickets_categoria_check;

-- Aggiungi il nuovo vincolo con le categorie corrette
ALTER TABLE crm_tickets
ADD CONSTRAINT crm_tickets_categoria_check
CHECK (categoria IN ('assistenza', 'miglioramento'));

-- Aggiorna eventuali record esistenti con vecchi valori
UPDATE crm_tickets SET categoria = 'assistenza' WHERE categoria = 'bug_report';
UPDATE crm_tickets SET categoria = 'miglioramento' WHERE categoria = 'suggerimento';

-- ============================================================
-- 2. ABILITA SMTP CONFIGURATION
-- ============================================================
-- Aggiorna configurazione email per abilitare SMTP
UPDATE email_config
SET
    smtp_enabled = TRUE,
    smtp_host = 'smtp.gmail.com',
    smtp_port = 587,
    smtp_use_tls = TRUE,
    smtp_sender_name = 'TO_EXTRACTOR',
    smtp_sender_email = '',
    updated_at = CURRENT_TIMESTAMP
WHERE id_config = 1;

-- Se non esiste il record, crealo
INSERT INTO email_config (
    id_config,
    smtp_enabled, smtp_host, smtp_port, smtp_use_tls, smtp_sender_name,
    imap_enabled, imap_host, imap_port, imap_use_ssl
)
SELECT
    1,
    TRUE, 'smtp.gmail.com', 587, TRUE, 'TO_EXTRACTOR',
    FALSE, 'imap.gmail.com', 993, TRUE
WHERE NOT EXISTS (SELECT 1 FROM email_config WHERE id_config = 1);

-- ============================================================
-- 3. AGGIUNGI CAMPO admin_notifica_email (opzionale)
-- ============================================================
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'email_config' AND column_name = 'admin_notifica_email'
    ) THEN
        ALTER TABLE email_config ADD COLUMN admin_notifica_email VARCHAR(200);
        RAISE NOTICE 'Campo admin_notifica_email aggiunto';
    END IF;
END $$;

COMMIT;

-- ============================================================
-- VERIFICA
-- ============================================================
DO $$
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Migrazione Email Config completata!';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Prossimi passi:';
    RAISE NOTICE '1. Modifica backend/.env con SMTP_USER e SMTP_PASSWORD';
    RAISE NOTICE '2. Configura smtp_sender_email da Settings > Email';
    RAISE NOTICE '3. (Opzionale) Configura admin_notifica_email';
    RAISE NOTICE '4. Testa la connessione SMTP dalla UI';
END $$;
