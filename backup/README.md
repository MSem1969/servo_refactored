# TO_EXTRACTOR v6.2 - Backup Progetto

Backup completo dei file critici del progetto. **Non include dati del database** (siamo in fase di test).

## Struttura Backup

```
backup/
├── backend/                 # Backend FastAPI
│   ├── app/                 # Codice applicazione
│   │   ├── auth/            # Modulo autenticazione
│   │   ├── extractors/      # Estrattori PDF legacy
│   │   ├── routers/         # Endpoint API
│   │   ├── scripts/         # Script utility
│   │   └── services/        # Servizi business logic
│   │       └── extractors/  # Estrattori PDF v6.2
│   ├── .env.example         # Template variabili ambiente
│   └── requirements.txt     # Dipendenze Python
│
├── frontend/                # Frontend React + Vite
│   ├── src/                 # Codice sorgente
│   │   ├── common/          # Componenti comuni
│   │   ├── components/      # Componenti specifici
│   │   ├── hooks/           # React hooks
│   │   └── layout/          # Layout componenti
│   ├── package.json         # Dipendenze npm
│   ├── vite.config.js       # Configurazione Vite
│   └── tailwind.config.js   # Configurazione Tailwind
│
├── gmail_monitor/           # Servizio monitoraggio Gmail
│   ├── *.py                 # Script Python
│   ├── .env.example         # Template variabili ambiente
│   └── requirements.txt     # Dipendenze Python
│
├── sql/                     # Script SQL
│   ├── create_schema.sql    # Schema DDL PostgreSQL
│   └── seed_data.sql        # Dati seed (vendor, operatori)
│
├── scripts/                 # Script di utilità
│   ├── rebuild_database.py  # Ricostruzione DB da zero
│   ├── restore_database.py  # Ripristino completo
│   ├── restore_database.sh  # Script bash ripristino
│   └── setup_environment.sh # Setup ambiente
│
├── CLAUDE.md                # Istruzioni progetto
├── run.py                   # Script avvio sviluppo
└── README.md                # Questo file
```

## Ricostruzione Database

### Prerequisiti

1. PostgreSQL installato e in esecuzione
2. Database e utente creati:

```sql
CREATE USER to_extractor_user WITH PASSWORD 'your_password';
CREATE DATABASE to_extractor OWNER to_extractor_user;
GRANT ALL PRIVILEGES ON DATABASE to_extractor TO to_extractor_user;
```

### Procedura

1. Configura le variabili ambiente:

```bash
export PG_HOST=localhost
export PG_PORT=5432
export PG_DATABASE=to_extractor
export PG_USER=to_extractor_user
export PG_PASSWORD=your_password
```

2. Installa dipendenze:

```bash
pip install psycopg2-binary bcrypt
```

3. Esegui lo script di ricostruzione:

```bash
# Prima installazione
python scripts/rebuild_database.py

# Reset completo (elimina tutto e ricrea)
python scripts/rebuild_database.py --drop-existing
```

### Credenziali Default

Dopo la ricostruzione:
- **Username:** admin
- **Password:** Password1

**IMPORTANTE:** Cambiare la password dopo il primo login!

## Ripristino Progetto Completo

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Modifica .env con le tue configurazioni
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env  # se presente
npm run dev
```

### Gmail Monitor

```bash
cd gmail_monitor
pip install -r requirements.txt
cp .env.example .env
# Configura credenziali Gmail API
python gmail_monitor.py
```

## Note

- Il backup **non include** dati del database (ordinI, anagrafiche, etc.)
- I file `.env` contengono solo template, non credenziali reali
- Le cartelle `venv`, `node_modules`, `__pycache__` sono escluse
- Le cartelle `uploads`, `outputs`, `temp`, `logs` sono escluse

## Generato

Data: 2026-01-10
Versione: v6.2
