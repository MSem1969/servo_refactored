# SERV.O v11.0 - Pharmaceutical Order Extractor

Sistema di estrazione automatica ordini farmaceutici da PDF con generazione tracciati ministeriali TO_T/TO_D.

## Stack Tecnologico

- **Backend:** FastAPI + PostgreSQL + Python 3.11+
- **Frontend:** React 18 + Vite + TailwindCSS + React Query
- **Database:** PostgreSQL 15+

## Quick Start

### Prerequisiti

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+

### Setup Locale

```bash
# 1. Clona il repository
git clone https://github.com/MSem1969/servo_refactored.git
cd servo_refactored

# 2. Setup Backend
cd backend
python -m venv venv
source venv/bin/activate  # Linux/macOS
# oppure: venv\Scripts\activate  # Windows
pip install -r requirements.txt

# 3. Configura database
cp .env.example .env
# Modifica .env con le tue credenziali PostgreSQL

# 4. Setup Frontend
cd ../frontend
npm install

# 5. Avvia l'applicazione
cd ..
python run.py
```

### Setup GitHub Codespaces

1. Clicca su **Code** > **Codespaces** > **Create codespace on main**
2. Attendi il setup automatico
3. Nel terminale:

```bash
# Setup Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Configura .env con credenziali PostgreSQL

# Setup Frontend
cd ../frontend
npm install

# Avvia
cd ..
python run.py
```

4. Codespaces inoltrera automaticamente le porte
5. Clicca sulla tab **PORTS** per aprire l'applicazione

## Struttura Progetto

```
servo_refactored/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app
│   │   ├── config.py            # Configurazione
│   │   ├── models.py            # SQLAlchemy models
│   │   ├── routers/             # API endpoints
│   │   └── services/            # Business logic
│   │       ├── extraction/      # PDF extraction
│   │       ├── export/          # Tracciati EDI
│   │       ├── supervision/     # ML supervision
│   │       └── tracking/        # Operator tracking
│   ├── migrations/              # SQL migrations
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── api/                 # API client
│   │   ├── components/          # React components
│   │   ├── pages/               # Page components
│   │   ├── hooks/               # Custom hooks
│   │   └── context/             # React Context
│   ├── package.json
│   └── vite.config.js
├── run.py                       # Launcher (locale + Codespaces)
└── README.md
```

## Comandi Utili

```bash
# Avvia tutto (backend + frontend)
python run.py

# Solo Backend
cd backend && source venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Solo Frontend
cd frontend && npm run dev

# Test Backend
cd backend && pytest

# Build Frontend
cd frontend && npm run build
```

## Porte

| Servizio | Porta | URL Locale |
|----------|-------|------------|
| Backend API | 8000 | http://localhost:8000 |
| Frontend | 5174 | http://localhost:5174 |
| API Docs | 8000 | http://localhost:8000/docs |

## Variabili Ambiente (.env)

```env
# Database PostgreSQL
PG_HOST=127.0.0.1
PG_PORT=5432
PG_DATABASE=servo
PG_USER=servo_user
PG_PASSWORD=your_password

# Tipo database
DB_TYPE=postgresql

# Directory
UPLOAD_DIR=uploads
OUTPUT_DIR=outputs
```

## Funzionalita Principali

- Estrazione automatica ordini da PDF (multi-vendor)
- Generazione tracciati EDI TO_T/TO_D
- Sistema di supervisione ML per anomalie
- Gestione espositori farmaceutici
- Dashboard con statistiche real-time
- Sistema CRM integrato
- Sincronizzazione anagrafica dal Ministero della Salute

## Vendor Supportati

| Vendor | Stato |
|--------|-------|
| ANGELINI | Attivo |
| BAYER | Attivo |
| CODIFI | Attivo |
| DOC_GENERICI | Attivo |
| MENARINI | Attivo |

## License

Proprietary - All rights reserved
