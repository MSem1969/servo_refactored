# SERV.O - Disaster Recovery Guide

> Guida completa per backup e ripristino del database SERV.O v11.6

## Indice

1. [Panoramica](#panoramica)
2. [Struttura Backup](#struttura-backup)
3. [Backup Periodici](#backup-periodici)
4. [Procedura di Restore](#procedura-di-restore)
5. [Scenari di Recovery](#scenari-di-recovery)
6. [Ambiente Produzione (Coolify)](#ambiente-produzione-coolify)
7. [Checklist Post-Recovery](#checklist-post-recovery)
8. [Troubleshooting](#troubleshooting)

---

## Panoramica

### Tipi di Backup

| Tipo | Contenuto | Frequenza Consigliata | Uso |
|------|-----------|----------------------|-----|
| **Schema** | DDL (struttura) | Dopo ogni migrazione | Recovery struttura |
| **Seed** | Dati configurazione | Settimanale | Recovery config |
| **Full** | Schema + tutti i dati | Giornaliero | Disaster recovery |

### Script Disponibili

```
backend/scripts/recovery/
├── backup_schema.sh    # Dump solo struttura DDL
├── backup_seed.sh      # Dump dati configurazione
├── backup_full.sh      # Dump completo
├── restore_db.sh       # Ripristino database
└── verify_db.sh        # Verifica integrità
```

### Directory Backup

```
backend/backups/
├── schema/             # Backup struttura
│   ├── schema_latest.sql -> schema_20260131_100000.sql
│   └── schema_*.sql
├── seed/               # Backup configurazione
│   ├── seed_latest.sql -> seed_20260131_100000.sql
│   └── seed_*.sql
└── full/               # Backup completi
    ├── servo_full_latest.sql -> servo_full_20260131_100000.sql
    └── servo_full_*.sql
```

---

## Struttura Backup

### Backup Schema (DDL)

Contiene:
- CREATE TABLE statements
- CREATE INDEX statements
- CREATE VIEW statements
- Sequenze
- Constraints (PK, FK, UNIQUE, CHECK)
- Funzioni/Trigger (se presenti)

**NON contiene:** dati

```bash
# Genera backup schema
./backend/scripts/recovery/backup_schema.sh

# Opzioni
./backup_schema.sh --output custom_name.sql
./backup_schema.sh --docker container_id
./backup_schema.sh --host db.example.com --port 5432
```

### Backup Seed

Contiene dati delle tabelle di configurazione:
- `vendor` - Anagrafica vendor
- `app_sezioni` - Sezioni applicazione
- `permessi_ruolo` - Permessi per ruolo
- `email_config` - Configurazione email
- `ftp_config` - Configurazione FTP legacy
- `ftp_endpoints` - Endpoint FTP (password crittografate!)
- `ftp_vendor_mapping` - Mapping vendor-FTP
- `backup_modules` - Configurazione moduli backup
- `backup_storage` - Storage backup
- `sync_state` - Stato sync anagrafiche

Opzionali (con flag):
- `operatori` - Utenti sistema (--include-operators)
- `listini_vendor` - Listini prezzi (--include-listini)
- `anagrafica_clienti` - Clienti (--include-clienti)

```bash
# Backup seed base
./backend/scripts/recovery/backup_seed.sh

# Include operatori
./backup_seed.sh --include-operators

# Include tutto
./backup_seed.sh --all
```

### Backup Full

Contiene tutto: schema + tutti i dati.

```bash
# Backup completo
./backend/scripts/recovery/backup_full.sh

# Con compressione
./backup_full.sh --compress

# Escludi log (più veloce)
./backup_full.sh --exclude-logs
```

---

## Backup Periodici

### Configurazione Cron (Locale)

```cron
# /etc/cron.d/servo-backup

# Schema: dopo ogni deploy (manuale o CI/CD)
# Seed: ogni domenica alle 02:00
0 2 * * 0 /path/to/backend/scripts/recovery/backup_seed.sh

# Full: ogni notte alle 03:00
0 3 * * * /path/to/backend/scripts/recovery/backup_full.sh --compress --exclude-logs
```

### Configurazione Coolify (Produzione)

In Coolify, creare uno script di backup come **Scheduled Task**:

```bash
#!/bin/bash
# Backup giornaliero produzione
CONTAINER=$(docker ps -q -f name=servo-backend)
docker exec $CONTAINER /app/scripts/recovery/backup_full.sh --compress
```

### Retention Policy

| Tipo | Retention | Note |
|------|-----------|------|
| Schema | Ultimi 10 | Dopo ogni migrazione |
| Seed | Ultimi 4 | 1 mese di storico |
| Full | Ultimi 7 | 1 settimana di storico |

---

## Procedura di Restore

### 1. Restore da Backup Full (Raccomandato)

Ripristina completamente il database da un backup full.

```bash
# 1. Lista backup disponibili
ls -la backend/backups/full/

# 2. Restore
./backend/scripts/recovery/restore_db.sh \
    --input full/servo_full_latest.sql

# 3. Verifica
./backend/scripts/recovery/verify_db.sh
```

### 2. Restore Schema + Seed (Nuovo Database)

Per creare un database pulito con struttura e configurazione.

```bash
# 1. Crea database vuoto
createdb -h localhost -U servo servo_new

# 2. Restore schema
./backend/scripts/recovery/restore_db.sh \
    --input schema/schema_latest.sql \
    --database servo_new

# 3. Restore seed data
./backend/scripts/recovery/restore_db.sh \
    --input seed/seed_latest.sql \
    --database servo_new

# 4. Verifica
./backend/scripts/recovery/verify_db.sh --database servo_new
```

### 3. Restore Solo Schema (Struttura)

Per sincronizzare la struttura tra ambienti.

```bash
# Restore solo schema (ATTENZIONE: cancella dati!)
./backend/scripts/recovery/restore_db.sh \
    --input schema/schema_latest.sql \
    --schema-only
```

---

## Scenari di Recovery

### Scenario 1: Corruzione Database

**Sintomi:** Errori query, tabelle mancanti, indici corrotti

```bash
# 1. Ferma l'applicazione
docker stop servo-backend

# 2. Backup stato corrotto (per analisi)
pg_dump -h localhost -U servo servo > corrupted_$(date +%Y%m%d).sql

# 3. Drop e ricrea database
dropdb -h localhost -U servo servo
createdb -h localhost -U servo servo

# 4. Restore da ultimo backup full
./restore_db.sh --input full/servo_full_latest.sql --no-confirm

# 5. Verifica
./verify_db.sh

# 6. Riavvia applicazione
docker start servo-backend
```

### Scenario 2: Server Compromesso / Nuovo Server

**Situazione:** Migrazione a nuovo server o recovery da zero

```bash
# Sul VECCHIO server (o da backup remoto):
# 1. Copia backup più recente
scp user@old-server:/path/to/backups/full/servo_full_latest.sql ./

# Sul NUOVO server:
# 2. Installa PostgreSQL
sudo apt install postgresql-15

# 3. Crea utente e database
sudo -u postgres psql -c "CREATE USER servo WITH PASSWORD 'xxx';"
sudo -u postgres psql -c "CREATE DATABASE servo OWNER servo;"

# 4. Restore
psql -h localhost -U servo -d servo < servo_full_latest.sql

# 5. Verifica
./verify_db.sh

# 6. Configura e avvia applicazione
# ... (vedi deploy documentation)
```

### Scenario 3: Rollback dopo Migrazione Fallita

**Situazione:** Una migrazione ha rotto qualcosa

```bash
# 1. Identifica backup pre-migrazione
ls -la backend/backups/schema/ | head -10

# 2. Restore schema precedente
./restore_db.sh --input schema/schema_20260130_100000.sql

# 3. Se necessario, restore dati
./restore_db.sh --input seed/seed_latest.sql

# 4. Verifica
./verify_db.sh
```

### Scenario 4: Perdita Parziale Dati

**Situazione:** Dati cancellati per errore, serve restore selettivo

```bash
# 1. Estrai dati specifici dal backup
# Esempio: recupera ordini cancellati

# Crea database temporaneo
createdb servo_recovery

# Restore backup nel DB temporaneo
./restore_db.sh --input full/servo_full_20260130.sql --database servo_recovery

# Estrai dati necessari
psql -h localhost -U servo servo_recovery -c "
    COPY (SELECT * FROM ordini_testata WHERE id_testata BETWEEN 1000 AND 2000)
    TO '/tmp/ordini_recovery.csv' WITH CSV HEADER;
"

# Importa nel database principale
psql -h localhost -U servo servo -c "
    COPY ordini_testata FROM '/tmp/ordini_recovery.csv' WITH CSV HEADER;
"

# Cleanup
dropdb servo_recovery
```

---

## Ambiente Produzione (Coolify)

### Accesso Container Database

```bash
# Trova container PostgreSQL
docker ps | grep postgres

# Accedi al container
docker exec -it <container_id> bash

# Oppure esegui psql direttamente
docker exec -it <container_id> psql -U servo -d servo
```

### Backup da Produzione

```bash
# Trova container
CONTAINER=$(docker ps -q -f name=postgres)

# Backup full
docker exec $CONTAINER pg_dump -U servo servo > prod_backup_$(date +%Y%m%d).sql

# Backup solo schema
docker exec $CONTAINER pg_dump -U servo --schema-only servo > prod_schema_$(date +%Y%m%d).sql

# Copia in locale
docker cp $CONTAINER:/backup.sql ./backup.sql
```

### Restore in Produzione

```bash
# ATTENZIONE: Ferma prima l'applicazione!

# 1. Ferma backend
docker stop servo-backend

# 2. Trova container PostgreSQL
CONTAINER=$(docker ps -q -f name=postgres)

# 3. Copia backup nel container
docker cp ./servo_full_backup.sql $CONTAINER:/restore.sql

# 4. Esegui restore
docker exec -i $CONTAINER psql -U servo -d servo < /restore.sql

# 5. Riavvia backend
docker start servo-backend

# 6. Verifica
curl https://your-app.com/api/v10/health
```

### Sync Produzione → Locale

```bash
# 1. Dump da produzione
ssh user@prod-server "docker exec \$(docker ps -q -f name=postgres) pg_dump -U servo servo" > prod_dump.sql

# 2. Restore in locale
psql -h localhost -U servo -d servo < prod_dump.sql

# 3. Verifica
./verify_db.sh
```

---

## Checklist Post-Recovery

Dopo ogni restore, verificare:

### Funzionalità Base

- [ ] Login funzionante (almeno 1 admin)
- [ ] Dashboard carica correttamente
- [ ] Lista ordini visibile

### Integrità Dati

- [ ] `./verify_db.sh` passa senza errori
- [ ] Conteggio tabelle corretto (53 tabelle, 19 viste)
- [ ] Sequenze sincronizzate (INSERT non falliscono)

### Configurazione

- [ ] Vendor configurati
- [ ] Email config presente (se usata)
- [ ] FTP endpoints (password funzionanti)

### Applicazione

- [ ] Backend risponde (`/api/v10/health`)
- [ ] Frontend carica
- [ ] Upload PDF funziona
- [ ] Estrazione ordini funziona

### Sequenze (se necessario)

Se dopo restore gli INSERT falliscono per "duplicate key":

```sql
-- Reset tutte le sequenze
SELECT setval('ordini_testata_id_testata_seq', COALESCE((SELECT MAX(id_testata) FROM ordini_testata), 1));
SELECT setval('ordini_dettaglio_id_dettaglio_seq', COALESCE((SELECT MAX(id_dettaglio) FROM ordini_dettaglio), 1));
SELECT setval('acquisizioni_id_acquisizione_seq', COALESCE((SELECT MAX(id_acquisizione) FROM acquisizioni), 1));
-- ... ripetere per altre sequenze
```

Script automatico:

```sql
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN (
        SELECT
            c.relname AS seq_name,
            t.relname AS table_name,
            a.attname AS column_name
        FROM pg_class c
        JOIN pg_depend d ON d.objid = c.oid
        JOIN pg_class t ON t.oid = d.refobjid
        JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = d.refobjsubid
        WHERE c.relkind = 'S'
    )
    LOOP
        EXECUTE format('SELECT setval(%L, COALESCE((SELECT MAX(%I) FROM %I), 1))',
                       r.seq_name, r.column_name, r.table_name);
    END LOOP;
END $$;
```

---

## Troubleshooting

### Errore: "database does not exist"

```bash
# Crea database
createdb -h localhost -U servo servo

# Oppure con restore
./restore_db.sh --input backup.sql --create-db
```

### Errore: "permission denied"

```bash
# Verifica permessi utente
psql -h localhost -U postgres -c "GRANT ALL ON DATABASE servo TO servo;"
```

### Errore: "duplicate key" dopo restore

```bash
# Reset sequenze (vedi sezione sopra)
psql -h localhost -U servo servo -f reset_sequences.sql
```

### Errore: "relation does not exist"

Il backup potrebbe essere incompleto o corrotto.

```bash
# Verifica contenuto backup
grep "CREATE TABLE" backup.sql | wc -l  # Dovrebbe essere ~53

# Se mancano tabelle, usare backup più vecchio
ls -la backend/backups/full/
```

### Backup troppo grande / lento

```bash
# Usa compressione
./backup_full.sh --compress

# Escludi tabelle log
./backup_full.sh --exclude-logs

# Backup incrementale (richiede configurazione pg_basebackup)
```

### Password FTP non funzionano dopo restore

Le password FTP sono crittografate con AES-256. Se la chiave di encryption è cambiata, le password non saranno recuperabili.

**Soluzione:** Re-inserire le password manualmente dalla UI.

---

## Contatti Emergenza

Per emergenze di recovery contattare:
- Amministratore Sistema: [inserire contatto]
- DBA: [inserire contatto]

---

*Documento aggiornato: 2026-01-31 | SERV.O v11.6*
