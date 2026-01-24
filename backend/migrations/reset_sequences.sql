-- =============================================================================
-- RESET ALL SEQUENCES TO 1
-- =============================================================================
-- Run this after truncating/clearing tables to reset all auto-increment IDs
-- Usage: psql -h localhost -U servo_user -d servo -f reset_sequences.sql
-- =============================================================================

-- Acquisizioni
ALTER SEQUENCE acquisizioni_id_acquisizione_seq RESTART WITH 1;

-- Anagrafica (skip these if you want to preserve master data)
-- ALTER SEQUENCE anagrafica_clienti_id_cliente_seq RESTART WITH 1;
-- ALTER SEQUENCE anagrafica_farmacie_id_farmacia_seq RESTART WITH 1;
-- ALTER SEQUENCE anagrafica_parafarmacie_id_parafarmacia_seq RESTART WITH 1;

-- Anomalie
ALTER SEQUENCE anomalie_id_anomalia_seq RESTART WITH 1;

-- Audit
ALTER SEQUENCE audit_modifiche_id_audit_seq RESTART WITH 1;

-- Backup
ALTER SEQUENCE backup_history_id_backup_seq RESTART WITH 1;
ALTER SEQUENCE backup_modules_id_module_seq RESTART WITH 1;
ALTER SEQUENCE backup_operations_log_id_log_seq RESTART WITH 1;
ALTER SEQUENCE backup_schedules_id_schedule_seq RESTART WITH 1;
ALTER SEQUENCE backup_storage_id_storage_seq RESTART WITH 1;

-- CRM
ALTER SEQUENCE crm_allegati_id_allegato_seq RESTART WITH 1;
ALTER SEQUENCE crm_messaggi_id_messaggio_seq RESTART WITH 1;
ALTER SEQUENCE crm_tickets_id_ticket_seq RESTART WITH 1;

-- Email
ALTER SEQUENCE email_acquisizioni_id_email_seq RESTART WITH 1;

-- Esportazioni
ALTER SEQUENCE esportazioni_dettaglio_id_seq RESTART WITH 1;
ALTER SEQUENCE esportazioni_id_esportazione_seq RESTART WITH 1;

-- Listini
ALTER SEQUENCE listini_vendor_id_listino_seq RESTART WITH 1;

-- Log
ALTER SEQUENCE log_criteri_applicati_id_log_seq RESTART WITH 1;
ALTER SEQUENCE log_operazioni_id_log_seq RESTART WITH 1;
ALTER SEQUENCE operatore_azioni_log_id_azione_seq RESTART WITH 1;

-- Operatori (skip if you want to preserve users)
-- ALTER SEQUENCE operatori_id_operatore_seq RESTART WITH 1;

-- Ordini
ALTER SEQUENCE ordini_dettaglio_id_dettaglio_seq RESTART WITH 1;
ALTER SEQUENCE ordini_testata_id_testata_seq RESTART WITH 1;

-- Permessi
ALTER SEQUENCE permessi_ruolo_id_permesso_seq RESTART WITH 1;

-- Sessioni
ALTER SEQUENCE sessione_attivita_id_seq RESTART WITH 1;
ALTER SEQUENCE user_sessions_id_session_seq RESTART WITH 1;

-- Supervisione
ALTER SEQUENCE supervisione_aic_id_supervisione_seq RESTART WITH 1;
ALTER SEQUENCE supervisione_espositore_id_supervisione_seq RESTART WITH 1;
ALTER SEQUENCE supervisione_listino_id_supervisione_seq RESTART WITH 1;
ALTER SEQUENCE supervisione_lookup_id_supervisione_seq RESTART WITH 1;
ALTER SEQUENCE supervisione_prezzo_id_supervisione_seq RESTART WITH 1;
ALTER SEQUENCE supervisione_unificata_id_supervisione_seq RESTART WITH 1;

-- Tracciati
ALTER SEQUENCE tracciati_dettaglio_id_seq RESTART WITH 1;
ALTER SEQUENCE tracciati_id_tracciato_seq RESTART WITH 1;

-- Vendor (skip if you want to preserve vendor definitions)
-- ALTER SEQUENCE vendor_id_vendor_seq RESTART WITH 1;

-- =============================================================================
-- VERIFY RESET
-- =============================================================================
DO $$
DECLARE
    seq_record RECORD;
BEGIN
    RAISE NOTICE '=== SEQUENCES RESET COMPLETE ===';
    FOR seq_record IN
        SELECT sequencename, last_value
        FROM pg_sequences
        WHERE schemaname = 'public'
        ORDER BY sequencename
    LOOP
        RAISE NOTICE 'Sequence %: %', seq_record.sequencename, COALESCE(seq_record.last_value::text, 'NULL');
    END LOOP;
END $$;
