-- =============================================================================
-- SERV.O v10.5 - RESET DATABASE
-- =============================================================================
-- Script per azzerare i dati operativi mantenendo la struttura e le anagrafiche
-- Eseguire con: PGPASSWORD=servo_pwd psql -h localhost -U servo_user -d servo -f migrations/reset_database.sql
-- =============================================================================
--
-- TABELLE MANTENUTE (NON AZZERATE):
-- - operatori (utenti sistema)
-- - permessi_ruolo (configurazione permessi)
-- - app_sezioni (configurazione sezioni app)
-- - anagrafica_clienti (anagrafica clienti caricata)
-- - anagrafica_farmacie (anagrafica ministero)
-- - anagrafica_parafarmacie (anagrafica ministero)
-- - listini_vendor (listini caricati)
-- - vendor (configurazione vendor)
-- - sync_state (stato sincronizzazione)
-- - alembic_version (migrazioni DB)
-- - backup_* (configurazione backup)
--
-- =============================================================================

-- Disabilita vincoli FK temporaneamente
SET session_replication_role = replica;

-- =============================================================================
-- 1. AZZERA TABELLE ML (Pattern Learning)
-- =============================================================================
TRUNCATE TABLE criteri_ordinari_espositore CASCADE;
TRUNCATE TABLE criteri_ordinari_listino CASCADE;
TRUNCATE TABLE criteri_ordinari_lookup CASCADE;
TRUNCATE TABLE criteri_ordinari_aic CASCADE;
TRUNCATE TABLE log_criteri_applicati CASCADE;

-- =============================================================================
-- 2. AZZERA TABELLE SUPERVISIONE
-- =============================================================================
TRUNCATE TABLE supervisione_espositore CASCADE;
TRUNCATE TABLE supervisione_listino CASCADE;
TRUNCATE TABLE supervisione_lookup CASCADE;
TRUNCATE TABLE supervisione_aic CASCADE;
TRUNCATE TABLE supervisione_prezzo CASCADE;

-- =============================================================================
-- 3. AZZERA TABELLE ANOMALIE
-- =============================================================================
TRUNCATE TABLE anomalie CASCADE;

-- =============================================================================
-- 4. AZZERA TABELLE ORDINI
-- =============================================================================
TRUNCATE TABLE ordini_dettaglio CASCADE;
TRUNCATE TABLE ordini_testata CASCADE;

-- =============================================================================
-- 5. AZZERA TABELLE ACQUISIZIONI
-- =============================================================================
TRUNCATE TABLE acquisizioni CASCADE;
TRUNCATE TABLE email_acquisizioni CASCADE;

-- =============================================================================
-- 6. AZZERA TABELLE TRACCIATI/ESPORTAZIONI
-- =============================================================================
TRUNCATE TABLE tracciati_dettaglio CASCADE;
TRUNCATE TABLE tracciati CASCADE;
TRUNCATE TABLE esportazioni_dettaglio CASCADE;
TRUNCATE TABLE esportazioni CASCADE;

-- =============================================================================
-- 7. AZZERA TABELLE CRM
-- =============================================================================
TRUNCATE TABLE crm_allegati CASCADE;
TRUNCATE TABLE crm_messaggi CASCADE;
TRUNCATE TABLE crm_tickets CASCADE;

-- =============================================================================
-- 8. AZZERA LOG E AUDIT
-- =============================================================================
TRUNCATE TABLE log_operazioni CASCADE;
TRUNCATE TABLE audit_modifiche CASCADE;

-- =============================================================================
-- 9. AZZERA SESSIONI (mantiene utenti, azzera sessioni attive)
-- =============================================================================
TRUNCATE TABLE sessione_attivita CASCADE;
TRUNCATE TABLE user_sessions CASCADE;

-- =============================================================================
-- 10. AZZERA TRACKING OPERATORE (opzionale - decommentare se necessario)
-- =============================================================================
-- TRUNCATE TABLE operatore_azioni_log CASCADE;

-- Riabilita vincoli FK
SET session_replication_role = DEFAULT;

-- =============================================================================
-- 11. RESET SEQUENZE (ID ripartono da 1)
-- =============================================================================
ALTER SEQUENCE IF EXISTS anomalie_id_anomalia_seq RESTART WITH 1;
ALTER SEQUENCE IF EXISTS ordini_testata_id_testata_seq RESTART WITH 1;
ALTER SEQUENCE IF EXISTS ordini_dettaglio_id_dettaglio_seq RESTART WITH 1;
ALTER SEQUENCE IF EXISTS acquisizioni_id_acquisizione_seq RESTART WITH 1;
ALTER SEQUENCE IF EXISTS tracciati_id_tracciato_seq RESTART WITH 1;
ALTER SEQUENCE IF EXISTS esportazioni_id_esportazione_seq RESTART WITH 1;
ALTER SEQUENCE IF EXISTS crm_tickets_id_ticket_seq RESTART WITH 1;
ALTER SEQUENCE IF EXISTS crm_messaggi_id_messaggio_seq RESTART WITH 1;
ALTER SEQUENCE IF EXISTS supervisione_espositore_id_supervisione_seq RESTART WITH 1;
ALTER SEQUENCE IF EXISTS supervisione_listino_id_supervisione_seq RESTART WITH 1;
ALTER SEQUENCE IF EXISTS supervisione_lookup_id_supervisione_seq RESTART WITH 1;
ALTER SEQUENCE IF EXISTS supervisione_aic_id_supervisione_seq RESTART WITH 1;

-- =============================================================================
-- VERIFICA RESET
-- =============================================================================
SELECT 'Database reset completato!' AS status;
SELECT '----------------------------------------' AS separator;

SELECT 'TABELLE AZZERATE:' AS info;
SELECT 'ML Patterns (criteri_ordinari_*)' AS tabella,
       (SELECT COUNT(*) FROM criteri_ordinari_espositore) +
       (SELECT COUNT(*) FROM criteri_ordinari_listino) +
       (SELECT COUNT(*) FROM criteri_ordinari_lookup) +
       (SELECT COUNT(*) FROM criteri_ordinari_aic) AS records
UNION ALL
SELECT 'Supervisione (*)',
       (SELECT COUNT(*) FROM supervisione_espositore) +
       (SELECT COUNT(*) FROM supervisione_listino) +
       (SELECT COUNT(*) FROM supervisione_lookup) +
       (SELECT COUNT(*) FROM supervisione_aic)
UNION ALL
SELECT 'Anomalie', (SELECT COUNT(*) FROM anomalie)
UNION ALL
SELECT 'Ordini (testata)', (SELECT COUNT(*) FROM ordini_testata)
UNION ALL
SELECT 'Ordini (dettaglio)', (SELECT COUNT(*) FROM ordini_dettaglio)
UNION ALL
SELECT 'Acquisizioni', (SELECT COUNT(*) FROM acquisizioni)
UNION ALL
SELECT 'Tracciati', (SELECT COUNT(*) FROM tracciati)
UNION ALL
SELECT 'CRM Tickets', (SELECT COUNT(*) FROM crm_tickets);

SELECT '----------------------------------------' AS separator;
SELECT 'TABELLE MANTENUTE:' AS info;
SELECT 'Operatori (utenti)' AS tabella, (SELECT COUNT(*) FROM operatori) AS records
UNION ALL
SELECT 'Anagrafica Clienti', (SELECT COUNT(*) FROM anagrafica_clienti)
UNION ALL
SELECT 'Anagrafica Farmacie', (SELECT COUNT(*) FROM anagrafica_farmacie)
UNION ALL
SELECT 'Anagrafica Parafarmacie', (SELECT COUNT(*) FROM anagrafica_parafarmacie)
UNION ALL
SELECT 'Listini Vendor', (SELECT COUNT(*) FROM listini_vendor)
UNION ALL
SELECT 'Vendor', (SELECT COUNT(*) FROM vendor);
