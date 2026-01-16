-- =============================================================================
-- SERV.O v9.0 - SISTEMA BACKUP MODULARE
-- =============================================================================
-- Migration per sistema backup configurabile via UI
-- Eseguire su PostgreSQL: psql -U to_extractor_user -d to_extractor_v2 -f v9_backup_system.sql
-- =============================================================================

-- =============================================================================
-- TABELLA: backup_storage - Destinazioni storage disponibili
-- =============================================================================
CREATE TABLE IF NOT EXISTS backup_storage (
    id_storage SERIAL PRIMARY KEY,
    nome VARCHAR(100) NOT NULL,
    tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('local', 'nas', 's3', 'gcs', 'azure')),
    path TEXT NOT NULL,
    -- Configurazione specifica per tipo (credenziali, opzioni)
    config JSONB DEFAULT '{}',
    -- Metriche spazio
    capacity_gb INTEGER,
    used_gb INTEGER,
    -- Stato
    stato VARCHAR(20) DEFAULT 'active' CHECK (stato IN ('active', 'inactive', 'error', 'full')),
    ultimo_check TIMESTAMP,
    ultimo_errore TEXT,
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES operatori(id_operatore),
    updated_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_backup_storage_tipo ON backup_storage(tipo);
CREATE INDEX IF NOT EXISTS idx_backup_storage_stato ON backup_storage(stato);

-- =============================================================================
-- TABELLA: backup_modules - Configurazione moduli backup
-- =============================================================================
CREATE TABLE IF NOT EXISTS backup_modules (
    id_module SERIAL PRIMARY KEY,
    nome VARCHAR(50) NOT NULL UNIQUE,
    -- Es: 'wal_archive', 'full_backup', 'incremental', 'offsite_sync', 'cloud', 'replica'
    tier INTEGER NOT NULL DEFAULT 1 CHECK (tier BETWEEN 1 AND 6),
    titolo VARCHAR(100) NOT NULL,
    descrizione TEXT,
    -- Stato
    enabled BOOLEAN DEFAULT FALSE,
    configured BOOLEAN DEFAULT FALSE,
    -- Configurazione modulo (JSON)
    config JSONB DEFAULT '{}',
    -- Storage associato (opzionale - alcuni moduli usano config interna)
    id_storage INTEGER REFERENCES backup_storage(id_storage),
    -- Scheduling (cron expression)
    schedule_cron VARCHAR(50),
    retention_days INTEGER DEFAULT 7,
    -- Ultimo stato
    last_run TIMESTAMP,
    last_status VARCHAR(20) CHECK (last_status IN ('success', 'failed', 'running', 'skipped')),
    last_error TEXT,
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP,
    updated_by INTEGER REFERENCES operatori(id_operatore)
);

-- Inserimento moduli predefiniti
INSERT INTO backup_modules (nome, tier, titolo, descrizione) VALUES
    ('wal_archive', 1, 'WAL Archiving', 'Archiviazione continua WAL segments per Point-in-Time Recovery (PITR). Permette di recuperare il database a qualsiasi momento nel tempo.'),
    ('full_backup', 2, 'Backup Completo', 'Backup full periodico con pg_dump. Crea un dump completo del database compresso.'),
    ('incremental', 3, 'Backup Incrementale', 'Backup incrementale con pg_basebackup. Salva solo i cambiamenti dall''ultimo backup.'),
    ('offsite_sync', 4, 'Sync Offsite', 'Sincronizzazione backup su storage remoto (NAS/server secondario) via rsync.'),
    ('cloud_backup', 5, 'Cloud Backup', 'Upload backup su cloud storage (S3, GCS, Azure Blob).'),
    ('replica', 6, 'Standby Replica', 'Replica PostgreSQL in streaming per failover automatico.')
ON CONFLICT (nome) DO NOTHING;

-- =============================================================================
-- TABELLA: backup_history - Storico esecuzioni backup
-- =============================================================================
CREATE TABLE IF NOT EXISTS backup_history (
    id_backup SERIAL PRIMARY KEY,
    id_module INTEGER NOT NULL REFERENCES backup_modules(id_module),
    id_storage INTEGER REFERENCES backup_storage(id_storage),
    -- Tipo backup
    backup_type VARCHAR(20) NOT NULL CHECK (backup_type IN ('full', 'incremental', 'wal', 'sync', 'upload')),
    -- File generato
    file_path TEXT,
    file_name VARCHAR(255),
    file_size_bytes BIGINT,
    file_checksum VARCHAR(64),
    -- Timing
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    duration_seconds INTEGER,
    -- Stato
    status VARCHAR(20) NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'success', 'failed', 'cancelled')),
    error_message TEXT,
    -- Metadata aggiuntivi
    metadata JSONB DEFAULT '{}',
    -- Trigger (manual, scheduled, pre-migration, etc.)
    triggered_by VARCHAR(50) DEFAULT 'scheduled',
    operator_id INTEGER REFERENCES operatori(id_operatore)
);

CREATE INDEX IF NOT EXISTS idx_backup_history_module ON backup_history(id_module);
CREATE INDEX IF NOT EXISTS idx_backup_history_status ON backup_history(status);
CREATE INDEX IF NOT EXISTS idx_backup_history_started ON backup_history(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_backup_history_type ON backup_history(backup_type);

-- =============================================================================
-- TABELLA: backup_operations_log - Log dettagliato operazioni
-- =============================================================================
CREATE TABLE IF NOT EXISTS backup_operations_log (
    id_log SERIAL PRIMARY KEY,
    -- Tipo operazione
    operation VARCHAR(50) NOT NULL,
    -- Es: 'module_configure', 'module_enable', 'module_disable', 'backup_start',
    --     'backup_complete', 'backup_fail', 'test_run', 'cleanup', 'restore'
    id_module INTEGER REFERENCES backup_modules(id_module),
    id_backup INTEGER REFERENCES backup_history(id_backup),
    -- Dettagli
    details JSONB,
    status VARCHAR(20) NOT NULL CHECK (status IN ('success', 'failed', 'info', 'warning')),
    message TEXT,
    -- Audit
    operator_id INTEGER REFERENCES operatori(id_operatore),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_backup_ops_log_operation ON backup_operations_log(operation);
CREATE INDEX IF NOT EXISTS idx_backup_ops_log_module ON backup_operations_log(id_module);
CREATE INDEX IF NOT EXISTS idx_backup_ops_log_created ON backup_operations_log(created_at DESC);

-- =============================================================================
-- TABELLA: backup_schedules - Job schedulati attivi
-- =============================================================================
CREATE TABLE IF NOT EXISTS backup_schedules (
    id_schedule SERIAL PRIMARY KEY,
    id_module INTEGER NOT NULL REFERENCES backup_modules(id_module),
    -- Cron expression (es: '0 2 * * *' = ogni giorno alle 2:00)
    cron_expression VARCHAR(50) NOT NULL,
    -- Stato
    active BOOLEAN DEFAULT TRUE,
    -- Prossima esecuzione (calcolata)
    next_run TIMESTAMP,
    -- Ultima esecuzione
    last_run TIMESTAMP,
    last_status VARCHAR(20),
    -- Opzioni
    options JSONB DEFAULT '{}',
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_backup_schedules_module ON backup_schedules(id_module);
CREATE INDEX IF NOT EXISTS idx_backup_schedules_next ON backup_schedules(next_run) WHERE active = TRUE;

-- =============================================================================
-- VISTA: v_backup_dashboard - Statistiche per dashboard
-- =============================================================================
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
    -- Statistiche ultimi 7 giorni
    (SELECT COUNT(*) FROM backup_history h
     WHERE h.id_module = m.id_module
     AND h.started_at > CURRENT_TIMESTAMP - INTERVAL '7 days') AS backups_7d,
    (SELECT COUNT(*) FROM backup_history h
     WHERE h.id_module = m.id_module
     AND h.status = 'failed'
     AND h.started_at > CURRENT_TIMESTAMP - INTERVAL '7 days') AS failures_7d,
    -- Ultimo backup riuscito
    (SELECT MAX(completed_at) FROM backup_history h
     WHERE h.id_module = m.id_module
     AND h.status = 'success') AS last_success,
    -- Spazio usato
    (SELECT COALESCE(SUM(file_size_bytes), 0) FROM backup_history h
     WHERE h.id_module = m.id_module
     AND h.status = 'success') AS total_bytes
FROM backup_modules m
LEFT JOIN backup_storage s ON m.id_storage = s.id_storage
ORDER BY m.tier;

-- =============================================================================
-- VISTA: v_backup_history_detail - Storico con dettagli
-- =============================================================================
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
-- FUNZIONE: Aggiorna timestamp updated_at
-- =============================================================================
CREATE OR REPLACE FUNCTION backup_update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger per backup_modules
DROP TRIGGER IF EXISTS trg_backup_modules_updated ON backup_modules;
CREATE TRIGGER trg_backup_modules_updated
    BEFORE UPDATE ON backup_modules
    FOR EACH ROW
    EXECUTE FUNCTION backup_update_timestamp();

-- Trigger per backup_storage
DROP TRIGGER IF EXISTS trg_backup_storage_updated ON backup_storage;
CREATE TRIGGER trg_backup_storage_updated
    BEFORE UPDATE ON backup_storage
    FOR EACH ROW
    EXECUTE FUNCTION backup_update_timestamp();

-- =============================================================================
-- STORAGE PREDEFINITO: Local Disk
-- =============================================================================
INSERT INTO backup_storage (nome, tipo, path, stato, created_by)
VALUES ('Local Backup', 'local', '/backup/postgresql', 'inactive', 1)
ON CONFLICT DO NOTHING;

-- =============================================================================
-- VERIFICA
-- =============================================================================
DO $$
BEGIN
    RAISE NOTICE '✅ Migration v9_backup_system completata';
    RAISE NOTICE '   Tabelle create: backup_storage, backup_modules, backup_history, backup_operations_log, backup_schedules';
    RAISE NOTICE '   Viste create: v_backup_dashboard, v_backup_history_detail';
    RAISE NOTICE '   Moduli inseriti: wal_archive, full_backup, incremental, offsite_sync, cloud_backup, replica';
END $$;
