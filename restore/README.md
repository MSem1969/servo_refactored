# TO_EXTRACTOR v6.2 - Backup Completo

Questa directory contiene **TUTTI** gli elementi necessari per ripristinare l'applicazione TO_EXTRACTOR da zero.

## Contenuto

```
backup/
├── README.md                       # Questo file
├── run.py                          # Script avvio applicazione
├── backend/
│   ├── app/                        # Codice sorgente backend completo
│   │   ├── auth/                   # Autenticazione JWT
│   │   ├── extractors/             # Estrattori PDF per vendor
│   │   ├── routers/                # API endpoints
│   │   └── services/               # Business logic
│   └── requirements.txt            # Dipendenze Python
├── frontend/
│   ├── src/                        # Codice sorgente React
│   ├── dist/                       # Frontend compilato (pronto per deploy)
│   ├── package.json                # Dipendenze Node.js
│   └── *.config.js                 # Configurazioni Vite/Tailwind
├── gmail_monitor/                  # Monitor email Gmail
├── config/
│   ├── CLAUDE.md                   # Documentazione progetto
│   └── .env.example                # Template variabili ambiente
├── scripts/
│   ├── restore_database.sh         # Script bash per ripristino DB
│   ├── restore_database.py         # Script Python per ripristino DB
│   └── setup_environment.sh        # Setup ambiente completo
└── sql/
    ├── create_schema.sql           # Schema database completo
    ├── seed_data.sql               # Vendor e operatori
    └── migrations/                 # Migrazioni incrementali
        ├── 001_add_profile_fields.sql
        ├── 002_add_q_da_evadere.sql
        └── 003_ml_pattern_sequence.sql
```

## Prerequisiti

### PostgreSQL
```bash
# Crea database e utente
sudo -u postgres psql << EOF
CREATE USER to_extractor_user WITH PASSWORD 'your_secure_password';
CREATE DATABASE to_extractor OWNER to_extractor_user;
GRANT ALL PRIVILEGES ON DATABASE to_extractor TO to_extractor_user;
EOF
```

### Variabili Ambiente
```bash
export PG_HOST=localhost
export PG_PORT=5432
export PG_DATABASE=to_extractor
export PG_USER=to_extractor_user
export PG_PASSWORD=your_secure_password
```

## Ripristino Completo

### Opzione 1: Script Bash
```bash
chmod +x backup/scripts/restore_database.sh
./backup/scripts/restore_database.sh --full
```

### Opzione 2: Script Python
```bash
pip install psycopg2-binary bcrypt
python backup/scripts/restore_database.py --mode full
```

### Opzione 3: Manuale
```bash
# 1. Schema
psql -h localhost -U to_extractor_user -d to_extractor -f backup/sql/create_schema.sql

# 2. Migrazioni
for f in backup/sql/migrations/*.sql; do
    psql -h localhost -U to_extractor_user -d to_extractor -f "$f"
done

# 3. Seed data
psql -h localhost -U to_extractor_user -d to_extractor -f backup/sql/seed_data.sql
```

## Modalita di Ripristino

| Modalita | Descrizione |
|----------|-------------|
| `--full` | Ripristino completo (schema + migrations + seed + reset password) |
| `--schema-only` | Solo schema e migrazioni (database vuoto) |
| `--seed-only` | Solo dati seed (richiede schema esistente) |
| `--reset-passwords` | Solo reset password utenti |

## Credenziali Default

Dopo il ripristino, gli utenti avranno queste password di default:

| Username | Password | Ruolo |
|----------|----------|-------|
| admin | Password1 | admin |
| SYSTEM | System123 | admin |

**IMPORTANTE**: Cambiare le password dopo il primo login!

## Struttura Database

### Tabelle Principali
- `vendor` - Fornitori supportati (ANGELINI, BAYER, etc.)
- `operatori` - Utenti del sistema
- `ordini_testata` - Testate ordini
- `ordini_dettaglio` - Righe ordini
- `anomalie` - Anomalie rilevate
- `supervisione_espositore` - Supervisioni ML

### Viste
- `v_ordini_completi` - Ordini con dati farmacia
- `v_dettagli_completi` - Righe con info prodotto
- `v_supervisione_pending` - Supervisioni in attesa

## Backup Periodico

Per creare un backup completo del database:
```bash
pg_dump -h localhost -U to_extractor_user -d to_extractor \
    --no-owner --no-privileges \
    -f backup_$(date +%Y%m%d).sql
```

## Note

- I file di upload (PDF) NON sono inclusi nel backup
- Le password degli operatori vengono resettate a valori di default
- I dati transazionali (ordini, anomalie) NON sono inclusi - solo configurazione
