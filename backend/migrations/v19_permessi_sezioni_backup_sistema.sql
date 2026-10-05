-- =============================================================================
-- v19 - Sezioni 'backup' e 'sistema' nella matrice permessi
-- =============================================================================
-- Backup, configurazione email/FTP e impostazioni di sistema erano cablati
-- "solo admin" nel codice. Ora sono regolati dalla matrice permessi
-- (Impostazioni → Permessi), su due sezioni dedicate:
--
--   backup   → tab Backup + /backup/*            (view = consulta, edit = esegue/configura)
--   sistema  → tab Generale/Automazione/Email/FTP/Database/Sistema,
--              /email/*, endpoint FTP              (view = consulta, edit = modifica)
--
-- Le righe nascono a FALSE per tutti i ruoli non admin: al deploy NULLA cambia
-- (admin ha sempre accesso pieno, a prescindere dalla matrice). Si abilitano
-- poi da dashboard.
--
-- Garantisce inoltre la sezione 'admin' (Amministrazione), che il menu ora usa
-- per la pagina Impostazioni: nei DB nati dal seed v10 si chiamava 'settings'
-- e i suoi permessi vengono copiati.
--
-- Idempotente. Applicare con:
--   psql -U servo -d servo -f v19_permessi_sezioni_backup_sistema.sql
-- =============================================================================

BEGIN;

-- WHERE NOT EXISTS invece di ON CONFLICT: funziona anche sui restore locali
-- che hanno perso i vincoli UNIQUE/PK.
INSERT INTO app_sezioni (codice_sezione, nome_display, descrizione, icona, ordine_menu, is_active)
SELECT v.* FROM (VALUES
    ('admin',   'Amministrazione', 'Pagina Impostazioni (cambio password, utenti, permessi)', 'Settings',  10, TRUE),
    ('backup',  'Backup',          'Consultazione ed esecuzione backup database',            'HardDrive', 11, TRUE),
    ('sistema', 'Sistema',         'Configurazione sistema: generale, email, FTP, database', 'Cog',       12, TRUE)
) AS v(codice_sezione, nome_display, descrizione, icona, ordine_menu, is_active)
WHERE NOT EXISTS (SELECT 1 FROM app_sezioni s WHERE s.codice_sezione = v.codice_sezione);

UPDATE app_sezioni SET is_active = TRUE
WHERE codice_sezione IN ('admin', 'backup', 'sistema') AND is_active IS NOT TRUE;

-- Permessi 'admin' ereditati da 'settings' dove esiste solo quest'ultima
INSERT INTO permessi_ruolo (ruolo, codice_sezione, can_view, can_edit, updated_at, updated_by)
SELECT p.ruolo, 'admin', p.can_view, p.can_edit, CURRENT_TIMESTAMP, 'migration_v19'
FROM permessi_ruolo p
WHERE p.codice_sezione = 'settings'
  AND NOT EXISTS (SELECT 1 FROM permessi_ruolo x
                  WHERE x.ruolo = p.ruolo AND x.codice_sezione = 'admin');

-- backup / sistema: chiusi per tutti i ruoli non admin
INSERT INTO permessi_ruolo (ruolo, codice_sezione, can_view, can_edit, updated_at, updated_by)
SELECT r.ruolo, s.sezione, FALSE, FALSE, CURRENT_TIMESTAMP, 'migration_v19'
FROM (VALUES ('superuser'), ('supervisore'), ('operatore'), ('readonly')) AS r(ruolo)
CROSS JOIN (VALUES ('backup'), ('sistema')) AS s(sezione)
WHERE NOT EXISTS (SELECT 1 FROM permessi_ruolo x
                  WHERE x.ruolo = r.ruolo AND x.codice_sezione = s.sezione);

\echo '--- Matrice sezioni admin/backup/sistema ---'
SELECT ruolo, codice_sezione, can_view, can_edit
FROM permessi_ruolo
WHERE codice_sezione IN ('admin', 'backup', 'sistema')
ORDER BY codice_sezione, ruolo;

COMMIT;
