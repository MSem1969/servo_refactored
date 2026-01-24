-- =============================================================================
-- SERV.O v10.0 - PERMISSIONS MATRIX
-- =============================================================================
-- Tabella per gestione permessi editabili per ruolo
-- =============================================================================

-- Tabella sezioni applicazione
CREATE TABLE IF NOT EXISTS app_sezioni (
    codice_sezione VARCHAR(50) PRIMARY KEY,
    nome_display VARCHAR(100) NOT NULL,
    descrizione TEXT,
    icona VARCHAR(50),
    ordine_menu INT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Inserisci sezioni predefinite
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

-- Tabella permessi per ruolo
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

-- Inserisci permessi default per ADMIN (tutto abilitato)
INSERT INTO permessi_ruolo (ruolo, codice_sezione, can_view, can_edit) VALUES
    ('admin', 'dashboard', TRUE, TRUE),
    ('admin', 'upload', TRUE, TRUE),
    ('admin', 'database', TRUE, TRUE),
    ('admin', 'supervisione', TRUE, TRUE),
    ('admin', 'tracciati', TRUE, TRUE),
    ('admin', 'export', TRUE, TRUE),
    ('admin', 'anagrafica', TRUE, TRUE),
    ('admin', 'crm', TRUE, TRUE),
    ('admin', 'backup', TRUE, TRUE),
    ('admin', 'settings', TRUE, TRUE),
    ('admin', 'utenti', TRUE, TRUE)
ON CONFLICT (ruolo, codice_sezione) DO NOTHING;

-- Inserisci permessi default per SUPERUSER
INSERT INTO permessi_ruolo (ruolo, codice_sezione, can_view, can_edit) VALUES
    ('superuser', 'dashboard', TRUE, TRUE),
    ('superuser', 'upload', TRUE, TRUE),
    ('superuser', 'database', TRUE, TRUE),
    ('superuser', 'supervisione', TRUE, TRUE),
    ('superuser', 'tracciati', TRUE, TRUE),
    ('superuser', 'export', TRUE, TRUE),
    ('superuser', 'anagrafica', TRUE, TRUE),
    ('superuser', 'crm', TRUE, TRUE),
    ('superuser', 'backup', FALSE, FALSE),
    ('superuser', 'settings', TRUE, FALSE),
    ('superuser', 'utenti', TRUE, TRUE)
ON CONFLICT (ruolo, codice_sezione) DO NOTHING;

-- Inserisci permessi default per SUPERVISORE
INSERT INTO permessi_ruolo (ruolo, codice_sezione, can_view, can_edit) VALUES
    ('supervisore', 'dashboard', TRUE, TRUE),
    ('supervisore', 'upload', TRUE, TRUE),
    ('supervisore', 'database', TRUE, TRUE),
    ('supervisore', 'supervisione', TRUE, TRUE),
    ('supervisore', 'tracciati', TRUE, TRUE),
    ('supervisore', 'export', TRUE, TRUE),
    ('supervisore', 'anagrafica', TRUE, TRUE),
    ('supervisore', 'crm', TRUE, TRUE),
    ('supervisore', 'backup', FALSE, FALSE),
    ('supervisore', 'settings', TRUE, FALSE),
    ('supervisore', 'utenti', TRUE, FALSE)
ON CONFLICT (ruolo, codice_sezione) DO NOTHING;

-- Inserisci permessi default per OPERATORE
-- NOTA: Operatore non vede Dashboard, landing page sarà Upload PDF
INSERT INTO permessi_ruolo (ruolo, codice_sezione, can_view, can_edit) VALUES
    ('operatore', 'dashboard', FALSE, FALSE),
    ('operatore', 'upload', TRUE, TRUE),
    ('operatore', 'database', TRUE, TRUE),
    ('operatore', 'supervisione', FALSE, FALSE),
    ('operatore', 'tracciati', TRUE, FALSE),
    ('operatore', 'export', TRUE, FALSE),
    ('operatore', 'anagrafica', FALSE, FALSE),
    ('operatore', 'crm', FALSE, FALSE),
    ('operatore', 'backup', FALSE, FALSE),
    ('operatore', 'settings', TRUE, FALSE),
    ('operatore', 'utenti', FALSE, FALSE)
ON CONFLICT (ruolo, codice_sezione) DO NOTHING;

-- Inserisci permessi default per READONLY
INSERT INTO permessi_ruolo (ruolo, codice_sezione, can_view, can_edit) VALUES
    ('readonly', 'dashboard', TRUE, FALSE),
    ('readonly', 'upload', FALSE, FALSE),
    ('readonly', 'database', TRUE, FALSE),
    ('readonly', 'supervisione', FALSE, FALSE),
    ('readonly', 'tracciati', TRUE, FALSE),
    ('readonly', 'export', FALSE, FALSE),
    ('readonly', 'anagrafica', TRUE, FALSE),
    ('readonly', 'crm', FALSE, FALSE),
    ('readonly', 'backup', FALSE, FALSE),
    ('readonly', 'settings', TRUE, FALSE),
    ('readonly', 'utenti', FALSE, FALSE)
ON CONFLICT (ruolo, codice_sezione) DO NOTHING;

-- Indici per performance
CREATE INDEX IF NOT EXISTS idx_permessi_ruolo_ruolo ON permessi_ruolo(ruolo);
CREATE INDEX IF NOT EXISTS idx_permessi_ruolo_sezione ON permessi_ruolo(codice_sezione);
