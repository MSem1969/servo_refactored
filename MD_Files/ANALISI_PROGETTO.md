# ANALISI PROGETTO TO_EXTRACTOR v6.2

> Documento generato automaticamente - Analisi struttura e mappatura componenti

---

## 1. ORGANIZZAZIONE FRONTEND E BACKEND

### ARCHITETTURA GENERALE

```
┌─────────────────────────┐        ┌─────────────────────────┐
│      FRONTEND           │        │       BACKEND           │
│   React 18 + Vite 5     │  ◄───► │   FastAPI + SQLite      │
│   Tailwind CSS          │  REST  │   Python 3.10+          │
│   Porta: 5173           │  JSON  │   Porta: 8000           │
└─────────────────────────┘        └─────────────────────────┘
```

### STRUTTURA DIRECTORY

```
/USABILITA_FRONTEND-v6.1/
├── backend/                              # Backend FastAPI (Python)
│   ├── app/
│   │   ├── main.py                       # Entry point applicazione
│   │   ├── config.py                     # Configurazione globale
│   │   ├── database.py                   # Gestione DB SQLite
│   │   ├── models.py                     # Modelli Pydantic
│   │   ├── utils.py                      # Utility functions
│   │   ├── auth/                         # Autenticazione (v6.2)
│   │   │   ├── security.py
│   │   │   ├── models.py
│   │   │   ├── permissions.py
│   │   │   ├── dependencies.py
│   │   │   └── router.py
│   │   ├── routers/                      # API REST endpoints
│   │   │   ├── upload.py
│   │   │   ├── ordini.py
│   │   │   ├── anagrafica.py
│   │   │   ├── tracciati.py
│   │   │   ├── anomalie.py
│   │   │   ├── dashboard.py
│   │   │   ├── lookup.py
│   │   │   ├── supervisione.py
│   │   │   └── utenti.py
│   │   ├── services/                     # Business logic
│   │   │   ├── pdf_processor.py
│   │   │   ├── ordini.py
│   │   │   ├── tracciati.py
│   │   │   ├── lookup.py
│   │   │   ├── anagrafica.py
│   │   │   ├── supervisione.py
│   │   │   ├── espositore.py
│   │   │   └── extractors/               # Parser per vendor
│   │   │       ├── base.py
│   │   │       ├── angelini.py
│   │   │       ├── bayer.py
│   │   │       ├── chiesi.py
│   │   │       ├── codifi.py
│   │   │       ├── menarini.py
│   │   │       └── opella.py
│   │   └── scripts/
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── create_database_v6_2.sql
│   └── extractor_to.db
│
├── frontend/                             # Frontend React + Vite
│   ├── src/
│   │   ├── main.jsx                      # Entry point
│   │   ├── App.jsx                       # Componente principale
│   │   ├── api.js                        # Client API con JWT
│   │   ├── index.css                     # Stili globali
│   │   ├── common/                       # Componenti riusabili
│   │   │   ├── Button.jsx
│   │   │   ├── ErrorBox.jsx
│   │   │   ├── Loading.jsx
│   │   │   ├── StatusBadge.jsx
│   │   │   ├── VendorBadge.jsx
│   │   │   └── index.js
│   │   ├── layout/                       # Componenti layout
│   │   │   ├── Layout.jsx
│   │   │   ├── Header.jsx
│   │   │   ├── Sidebar.jsx
│   │   │   └── index.js
│   │   ├── UploadPage.jsx
│   │   ├── DatabasePage.jsx
│   │   ├── SupervisionePage.jsx
│   │   ├── TracciatiPage.jsx
│   │   └── SettingsPage.jsx
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── index.html
│   └── Dockerfile
│
├── docker-compose.yml
├── run.py
├── start.sh
├── start.bat
└── README.md
```

### Frontend

| Tecnologia | Versione | Scopo |
|------------|----------|-------|
| React | 18.2.0 | Framework UI |
| Vite | 5.0.8 | Build tool |
| Tailwind CSS | 3.3.6 | Styling |
| Axios | 1.6.2 | HTTP client |

**Entry Point**: `main.jsx` → `App.jsx`

**API Client**: `api.js` (axios + JWT interceptor)

### Backend

| Tecnologia | Scopo |
|------------|-------|
| FastAPI | Framework web asincrono |
| Python 3.10+ | Linguaggio |
| SQLite3 | Database |
| Pydantic | Validazione modelli |
| PyJWT | Token JWT |
| BCrypt | Hashing password |
| pdfplumber/PyPDF2 | Parsing PDF |
| uvicorn | Server ASGI |

**Entry Point**: `main.py` (FastAPI)

---

## 2. FILE INTERFACCIA UTENTE (Frontend)

| File | Percorso | Scopo |
|------|----------|-------|
| `App.jsx` | `/frontend/src/` | Router principale, LoginPage, DashboardPage |
| `UploadPage.jsx` | `/frontend/src/` | Drag & drop upload PDF |
| `DatabasePage.jsx` | `/frontend/src/` | Visualizzazione ordini con filtri e selezione multipla |
| `SupervisionePage.jsx` | `/frontend/src/` | Workflow ML supervisione anomalie |
| `TracciatiPage.jsx` | `/frontend/src/` | Generazione e download TO_T/TO_D |
| `SettingsPage.jsx` | `/frontend/src/` | Configurazioni, import anagrafica, gestione database |
| `api.js` | `/frontend/src/` | Client API centralizzato con JWT |
| `Header.jsx` | `/frontend/src/layout/` | Navbar con menu utente e notifiche |
| `Sidebar.jsx` | `/frontend/src/layout/` | Menu navigazione laterale |
| `Layout.jsx` | `/frontend/src/layout/` | Layout principale applicazione |
| `Button.jsx` | `/frontend/src/common/` | Componente bottone riutilizzabile |
| `StatusBadge.jsx` | `/frontend/src/common/` | Badge stato ordini |
| `VendorBadge.jsx` | `/frontend/src/common/` | Badge vendor |
| `Loading.jsx` | `/frontend/src/common/` | Componenti loading/spinner |
| `ErrorBox.jsx` | `/frontend/src/common/` | Visualizzazione errori |

---

## 3. FILE LOGICA BACKEND

### Routers (API Endpoints)

| File | Percorso | Endpoints Principali |
|------|----------|---------------------|
| `auth.py` | `/backend/app/routers/` | `/auth/login`, `/auth/logout`, `/auth/me`, `/auth/me/permissions` |
| `upload.py` | `/backend/app/routers/` | `/upload`, `/upload/multiple`, `/upload/stats` |
| `ordini.py` | `/backend/app/routers/` | `/ordini`, `/ordini/{id}`, `/ordini/{id}/righe`, `/ordini/batch/stato` |
| `anagrafica.py` | `/backend/app/routers/` | `/anagrafica/farmacie/import`, `/anagrafica/parafarmacie/import`, `/anagrafica/search` |
| `tracciati.py` | `/backend/app/routers/` | `/tracciati/genera`, `/tracciati/preview/{id}`, `/tracciati/pronti`, `/tracciati/download/{file}` |
| `supervisione.py` | `/backend/app/routers/` | `/supervisione/pending`, `/supervisione/{id}/approva`, `/supervisione/{id}/rifiuta` |
| `lookup.py` | `/backend/app/routers/` | `/lookup/batch`, `/lookup/manuale/{id}`, `/lookup/pending` |
| `dashboard.py` | `/backend/app/routers/` | `/dashboard`, `/dashboard/ordini-recenti`, `/dashboard/vendor-stats` |
| `anomalie.py` | `/backend/app/routers/` | `/anomalie`, `/anomalie/{id}`, `/anomalie/batch/risolvi` |
| `utenti.py` | `/backend/app/routers/` | `/utenti`, `/utenti/{id}`, `/utenti/{id}/cambio-password` |

### Services (Business Logic)

| File | Percorso | Funzione |
|------|----------|----------|
| `pdf_processor.py` | `/backend/app/services/` | Parsing PDF, detect vendor, estrazione dati |
| `ordini.py` | `/backend/app/services/` | Gestione ordini, conferma righe, workflow |
| `tracciati.py` | `/backend/app/services/` | Generazione TO_T (477 char), TO_D (405 char) |
| `lookup.py` | `/backend/app/services/` | Fuzzy matching P.IVA + indirizzo |
| `supervisione.py` | `/backend/app/services/` | Workflow ML, pattern recognition, apprendimento |
| `anagrafica.py` | `/backend/app/services/` | Import CSV farmacie/parafarmacie |
| `espositore.py` | `/backend/app/services/` | Gestione espositori ANGELINI |

### Extractors (PDF per Vendor)

| File | Percorso | Vendor | Note |
|------|----------|--------|------|
| `base.py` | `/backend/app/services/extractors/` | - | Classe base estrattore |
| `angelini.py` | `/backend/app/services/extractors/` | ANGELINI | Espositori parent-child, sconti a cascata |
| `bayer.py` | `/backend/app/services/extractors/` | BAYER | Formato SAP |
| `codifi.py` | `/backend/app/services/extractors/` | CODIFI | Multi-cliente (N ordini per PDF) |
| `chiesi.py` | `/backend/app/services/extractors/` | CHIESI | Esclusione P.IVA vendor |
| `menarini.py` | `/backend/app/services/extractors/` | MENARINI | Parent/Child con coordinate X |
| `opella.py` | `/backend/app/services/extractors/` | OPELLA | AIC 7-9 cifre |

### Autenticazione

| File | Percorso | Funzione |
|------|----------|----------|
| `security.py` | `/backend/app/auth/` | Hash password bcrypt, JWT generation/verification |
| `permissions.py` | `/backend/app/auth/` | Role-based access control |
| `models.py` | `/backend/app/auth/` | Modelli Pydantic per auth |
| `dependencies.py` | `/backend/app/auth/` | Dipendenze FastAPI per protezione endpoint |
| `router.py` | `/backend/app/auth/` | Endpoint login, logout, me |

---

## 4. MAPPA BOTTONI FRONTEND → FUNZIONI BACKEND

### LOGIN PAGE (`App.jsx:22-92`)

| Bottone | Funzione Frontend | API Backend | Metodo |
|---------|-------------------|-------------|--------|
| "ACCEDI" | `authApi.login(username, password)` | `/api/v1/auth/login` | POST |

### DASHBOARD (`App.jsx:97-224`)

| Bottone | Funzione Frontend | API Backend | Note |
|---------|-------------------|-------------|------|
| "Upload PDF" | `navigateTo("upload")` | - | Navigazione |
| "Database" | `navigateTo("database")` | - | Navigazione |
| "Tracciati" | `navigateTo("tracciati")` | - | Navigazione |
| "Supervisione" | `navigateTo("supervisione")` | - | Navigazione |
| Stats (caricamento) | `dashboardApi.getStats()` | `/api/v1/dashboard` | GET |

### UPLOAD PAGE (`UploadPage.jsx`)

| Bottone/Azione | Funzione Frontend | API Backend | Metodo |
|----------------|-------------------|-------------|--------|
| Drop Zone (click/drag) | `uploadApi.uploadPdf(file, onProgress)` | `/api/v1/upload` | POST |
| "Ricarica Stats" | `uploadApi.getStats()` | `/api/v1/upload/stats` | GET |
| "Pulisci Lista" | `clearFiles()` | - | Locale |
| "Pulisci" (console) | `setLogs([])` | - | Locale |

### DATABASE PAGE (`DatabasePage.jsx`)

| Bottone/Azione | Funzione Frontend | API Backend | Metodo |
|----------------|-------------------|-------------|--------|
| Checkbox "Seleziona tutti" | `selectAll()` | - | Locale |
| Filtro Vendor (select) | `setFilters({vendor})` | - | Locale |
| Filtro Stato (select) | `setFilters({stato})` | - | Locale |
| Input ricerca | `setFilters({q})` | - | Locale |
| "Ricarica" | `ordiniApi.getList(filters)` | `/api/v1/ordini` | GET |
| "Pulisci filtri" | `clearFilters()` | - | Locale |
| "Elimina (N)" | `ordiniApi.batchDelete(ids)` | `/api/v1/ordini/batch` | DELETE |
| "Valida (N)" | `handleBatchValidate()` | `/api/v1/ordini/batch/stato` | POST |
| "Dettaglio" (icona occhio) | `onOpenOrdine(id)` | - | Navigazione |
| "Righe" (icona clipboard) | `ordiniApi.getRighe(id)` | `/api/v1/ordini/{id}/righe` | GET |
| Tab "Ordini" | `setActiveTab('ordini')` | - | Locale |
| Tab "Anomalie" | `setActiveTab('anomalie')` | - | Locale |
| Tab "Dettaglio" | `setActiveTab('righe')` | - | Locale |

### SUPERVISIONE PAGE (`SupervisionePage.jsx`)

| Bottone/Azione | Funzione Frontend | API Backend | Metodo |
|----------------|-------------------|-------------|--------|
| "Torna all'Ordine" | `onReturnToOrdine(id)` | - | Navigazione |
| "Approva (+1 ML)" | `supervisioneApi.approva(id, operatore)` | `/api/v1/supervisione/{id}/approva` | POST |
| "Approva e Torna" | `supervisioneApi.approvaETorna(id, operatore)` | `/api/v1/supervisione/{id}/completa-e-torna` | POST |
| "Rifiuta (Reset ML)" | `supervisioneApi.rifiuta(id, operatore, note)` | `/api/v1/supervisione/{id}/rifiuta` | POST |
| "Modifica" | `supervisioneApi.modifica(id, operatore, modifiche)` | `/api/v1/supervisione/{id}/modifica` | POST |
| "Lascia Sospeso" | `supervisioneApi.lasciaSospeso(id, operatore)` | `/api/v1/supervisione/{id}/lascia-sospeso` | POST |
| "Reset" Pattern ML | `supervisioneApi.resetPattern(signature)` | `/api/v1/supervisione/criteri/{signature}/reset` | POST |
| Tab "In Attesa" | `setActiveTab('pending')` | - | Locale |
| Tab "Pattern ML" | `setActiveTab('patterns')` | - | Locale |
| Tab "Approvate" | `setActiveTab('approved')` | - | Locale |
| Tab "Analytics" | `setActiveTab('stats')` | - | Locale |
| Caricamento dati | `supervisioneApi.getPending()` | `/api/v1/supervisione/pending` | GET |
| Caricamento criteri | `supervisioneApi.getCriteriOrdinari()` | `/api/v1/supervisione/criteri/ordinari` | GET |
| Caricamento stats | `supervisioneApi.getCriteriStats()` | `/api/v1/supervisione/criteri/stats` | GET |

### TRACCIATI PAGE (`TracciatiPage.jsx`)

| Bottone/Azione | Funzione Frontend | API Backend | Metodo |
|----------------|-------------------|-------------|--------|
| "Genera Tracciati" | `tracciatiApi.genera(ordiniIds)` | `/api/v1/tracciati/genera` | POST |
| "Deseleziona Tutti" | `setSelected([])` | - | Locale |
| "Ricarica" | `loadData()` | `/api/v1/tracciati/pronti` + `/api/v1/tracciati/storico` | GET |
| "Pulisci File" | `tracciatiApi.eliminaFile()` | `/api/v1/tracciati/files` | DELETE |
| "Preview" (icona occhio) | `tracciatiApi.getPreview(id)` | `/api/v1/tracciati/preview/{id}` | GET |
| "Export singolo" (icona upload) | `tracciatiApi.genera([id])` | `/api/v1/tracciati/genera` | POST |
| "Download TO_T" | `handleDownload(filename)` | `/api/v1/tracciati/download/{filename}` | GET |
| "Download TO_D" | `handleDownload(filename)` | `/api/v1/tracciati/download/{filename}` | GET |
| "Genera Questo Tracciato" | `tracciatiApi.genera([id])` | `/api/v1/tracciati/genera` | POST |
| "Chiudi Preview" | `setPreview(null)` | - | Locale |
| Checkbox selezione | `toggleSelect(id)` | - | Locale |
| Checkbox "Seleziona tutti" | `selectAll()` | - | Locale |
| Tab "Ordini Pronti" | `setActiveTab('pronti')` | - | Locale |
| Tab "Storico Export" | `setActiveTab('storico')` | - | Locale |
| Tab "Preview" | `setActiveTab('preview')` | - | Locale |

### SETTINGS PAGE (`SettingsPage.jsx`)

| Bottone/Azione | Funzione Frontend | API Backend | Metodo |
|----------------|-------------------|-------------|--------|
| "Reset Default" | `handleReset()` | - | localStorage |
| "Salva Tutto" | `handleSave()` | - | localStorage |
| "Seleziona CSV Farmacie" | `anagraficaApi.importFarmacie(file, onProgress)` | `/api/v1/anagrafica/farmacie/import` | POST |
| "Seleziona CSV Parafarmacie" | `anagraficaApi.importParafarmacie(file, onProgress)` | `/api/v1/anagrafica/parafarmacie/import` | POST |
| "Backup Manuale" | `handleDatabaseAction("backup")` | - | TODO API |
| "Pulisci Farmacie" | `anagraficaApi.clearFarmacie()` | `/api/v1/anagrafica/farmacie` | DELETE |
| "Pulisci Parafarmacie" | `anagraficaApi.clearParafarmacie()` | `/api/v1/anagrafica/parafarmacie` | DELETE |
| "Pulisci Ordini" | `handleDatabaseAction("clear_ordini")` | - | TODO API |
| "RESET COMPLETO SISTEMA" | `handleDatabaseAction("reset_complete")` | - | TODO API |
| "Download Log" | `handleDownloadLogs()` | - | Locale (genera file) |
| Toggle Auto-Validazione | `setSettings({autoValidate})` | - | localStorage |
| Toggle ML Auto Approve | `setSettings({mlAutoApprove})` | - | localStorage |
| Toggle Notifiche Email | `setSettings({emailNotifications})` | - | localStorage |
| Toggle Backup Automatico | `setSettings({autoBackup})` | - | localStorage |
| Toggle Debug Mode | `setSettings({debugMode})` | - | localStorage |
| Slider ML Confidence | `setSettings({mlMinConfidence})` | - | localStorage |
| Select Log Level | `setSettings({logLevel})` | - | localStorage |
| Tab "Generale" | `setActiveTab('general')` | - | Locale |
| Tab "Automazione" | `setActiveTab('automation')` | - | Locale |
| Tab "Database" | `setActiveTab('database')` | - | Locale |
| Tab "Sistema" | `setActiveTab('system')` | - | Locale |

### HEADER/LAYOUT (`layout/`, `App.jsx`)

| Bottone/Azione | Funzione Frontend | API Backend | Metodo |
|----------------|-------------------|-------------|--------|
| Menu laterale (items) | `navigateTo(page)` | - | Navigazione |
| "Logout" | `authApi.logout()` | `/api/v1/auth/logout` | POST |
| Click notifica | `handleNotificationClick(notification)` | - | Navigazione |
| Verifica auth (startup) | `authApi.getMe()` | `/api/v1/auth/me` | GET |

---

## 5. RIEPILOGO API ENDPOINTS

### Autenticazione

```
POST /api/v1/auth/login           → Login utente
POST /api/v1/auth/logout          → Logout utente
GET  /api/v1/auth/me              → Info utente corrente
GET  /api/v1/auth/me/permissions  → Permessi utente
GET  /api/v1/auth/me/sessions     → Sessioni attive
DELETE /api/v1/auth/me/sessions/{id} → Revoca sessione
```

### Upload

```
POST /api/v1/upload               → Upload singolo PDF
POST /api/v1/upload/multiple      → Upload multiplo PDF
GET  /api/v1/upload/stats         → Statistiche upload
GET  /api/v1/upload/recent        → Upload recenti
GET  /api/v1/upload/vendors       → Lista vendor supportati
```

### Ordini

```
GET  /api/v1/ordini               → Lista ordini con filtri
GET  /api/v1/ordini/{id}          → Dettaglio ordine
GET  /api/v1/ordini/{id}/righe    → Righe ordine
PUT  /api/v1/ordini/{id}/stato    → Aggiorna stato ordine
DELETE /api/v1/ordini/{id}        → Elimina ordine
POST /api/v1/ordini/batch/stato   → Aggiorna stato batch
DELETE /api/v1/ordini/batch       → Elimina batch ordini
POST /api/v1/ordini/{id}/righe/{id_riga}/conferma → Conferma riga
POST /api/v1/ordini/{id}/conferma-tutto → Conferma ordine completo
POST /api/v1/ordini/{id}/valida   → Valida e genera tracciato
```

### Supervisione

```
GET  /api/v1/supervisione/pending       → Supervisioni in attesa
GET  /api/v1/supervisione/pending/count → Conteggio pending
GET  /api/v1/supervisione/{id}          → Dettaglio supervisione
POST /api/v1/supervisione/{id}/approva  → Approva supervisione
POST /api/v1/supervisione/{id}/rifiuta  → Rifiuta supervisione
POST /api/v1/supervisione/{id}/modifica → Modifica supervisione
POST /api/v1/supervisione/{id}/completa-e-torna → Approva e ritorna
POST /api/v1/supervisione/{id}/lascia-sospeso → Lascia sospeso
GET  /api/v1/supervisione/criteri/ordinari → Criteri ML ordinari
GET  /api/v1/supervisione/criteri/stats → Stats criteri ML
POST /api/v1/supervisione/criteri/{signature}/reset → Reset pattern ML
```

### Tracciati

```
POST /api/v1/tracciati/genera          → Genera tracciati TO_T/TO_D
POST /api/v1/tracciati/genera/{id}     → Genera singolo tracciato
GET  /api/v1/tracciati/preview/{id}    → Preview tracciato
GET  /api/v1/tracciati/pronti          → Ordini pronti per export
GET  /api/v1/tracciati/storico         → Storico esportazioni
GET  /api/v1/tracciati/files           → Lista file tracciati
DELETE /api/v1/tracciati/files         → Elimina file tracciati
GET  /api/v1/tracciati/download/{file} → Download file tracciato
```

### Anagrafica

```
POST /api/v1/anagrafica/farmacie/import      → Import CSV farmacie
POST /api/v1/anagrafica/parafarmacie/import  → Import CSV parafarmacie
GET  /api/v1/anagrafica/stats                → Statistiche anagrafica
GET  /api/v1/anagrafica/search               → Ricerca anagrafica
GET  /api/v1/anagrafica/farmacie/{id}        → Dettaglio farmacia
GET  /api/v1/anagrafica/farmacie/piva/{piva} → Farmacie per P.IVA
DELETE /api/v1/anagrafica/farmacie           → Elimina tutte le farmacie
DELETE /api/v1/anagrafica/parafarmacie       → Elimina tutte le parafarmacie
```

### Lookup

```
POST /api/v1/lookup/test              → Test lookup singolo
POST /api/v1/lookup/batch             → Lookup batch
PUT  /api/v1/lookup/manuale/{id}      → Assegnazione manuale
GET  /api/v1/lookup/pending           → Ordini senza lookup
GET  /api/v1/lookup/search/farmacie   → Ricerca farmacie
GET  /api/v1/lookup/search/parafarmacie → Ricerca parafarmacie
GET  /api/v1/lookup/stats             → Statistiche lookup
```

### Dashboard

```
GET /api/v1/dashboard                 → Statistiche complete
GET /api/v1/dashboard/summary         → Riepilogo
GET /api/v1/dashboard/ordini-recenti  → Ultimi ordini
GET /api/v1/dashboard/anomalie-critiche → Anomalie critiche
GET /api/v1/dashboard/vendor-stats    → Stats per vendor
GET /api/v1/dashboard/anagrafica-stats → Stats anagrafica
```

### Anomalie

```
GET  /api/v1/anomalie                 → Lista anomalie
GET  /api/v1/anomalie/ordine/{id}     → Anomalie per ordine
PUT  /api/v1/anomalie/{id}            → Aggiorna anomalia
POST /api/v1/anomalie/batch/risolvi   → Risolvi batch
POST /api/v1/anomalie/batch/ignora    → Ignora batch
GET  /api/v1/anomalie/tipi            → Tipi anomalie
GET  /api/v1/anomalie/livelli         → Livelli anomalie
GET  /api/v1/anomalie/stati           → Stati anomalie
```

### Utenti (v6.2)

```
GET  /api/v1/utenti                   → Lista utenti
GET  /api/v1/utenti/{id}              → Dettaglio utente
POST /api/v1/utenti                   → Crea utente
PATCH /api/v1/utenti/{id}             → Modifica utente
POST /api/v1/utenti/{id}/cambio-password → Cambio password
POST /api/v1/utenti/{id}/disabilita   → Disabilita utente
POST /api/v1/utenti/{id}/riabilita    → Riabilita utente
GET  /api/v1/utenti/{id}/logs         → Log attività utente
```

---

## 6. WORKFLOW APPLICAZIONE

```
1. CARICA ANAGRAFICA
   └─ Import CSV farmacie (FRM_FARMA_*.csv)
   └─ Import CSV parafarmacie (FRM_PFARMA_*.csv)

2. UPLOAD PDF ORDINI
   └─ Frontend drag & drop
   └─ Backend detect vendor + estrazione

3. LOOKUP FARMACIE
   └─ Matching P.IVA + fuzzy indirizzo (threshold 60)
   └─ Risoluzione manuale anomalie

4. SUPERVISIONE RIGHE (v6.1)
   └─ ESTRATTO → IN_SUPERVISIONE → SUPERVISIONATO → CONFERMATO → IN_TRACCIATO
   └─ Gestione espositori
   └─ Pattern ML con apprendimento automatico

5. GENERAZIONE TRACCIATI
   └─ TO_T (477 char) - Testata
   └─ TO_D (405 char) - Dettaglio
   └─ Download file

6. EXPORT
   └─ File .txt formattato MISE
```

---

## 7. DATABASE SCHEMA

### Tabelle Principali

| Tabella | Scopo |
|---------|-------|
| `VENDOR` | Anagrafica vendor supportati |
| `OPERATORI` | Utenti sistema (v6.2) |
| `ANAGRAFICA_FARMACIE` | Farmacie con MIN_ID |
| `ANAGRAFICA_PARAFARMACIE` | Parafarmacie |
| `ACQUISIZIONI` | PDF caricati |
| `ORDINI_TESTATA` | Header ordini (TO_T) |
| `ORDINI_DETTAGLIO` | Righe ordini (TO_D) |
| `ANOMALIE` | Log anomalie |
| `ESPORTAZIONI` | Storico generazioni |
| `SESSION` | Sessioni utenti (v6.2) |
| `AUDIT_LOG` | Log azioni (v6.2) |

---

## 8. RUOLI UTENTE (v6.2)

| Ruolo | Permessi |
|-------|----------|
| `admin` | Accesso completo, gestione utenti |
| `supervisore` | Supervisione, approvazione anomalie, gestione utenti limitata |
| `operatore` | Upload, visualizzazione, conferma righe |
| `readonly` | Solo visualizzazione |

---

## 9. VENDOR SUPPORTATI

| Vendor | Estrattore | Note |
|--------|------------|------|
| ANGELINI | `angelini.py` | Espositori parent-child (ESP01-ESP06), sconti a cascata (35+10+5), padding 500 |
| BAYER | `bayer.py` | Formato SAP |
| CODIFI | `codifi.py` | Multi-cliente (N ordini per PDF) |
| CHIESI | `chiesi.py` | Esclusione P.IVA vendor 02944970348 |
| MENARINI | `menarini.py` | Parent/Child con coordinate X |
| OPELLA | `opella.py` | AIC 7-9 cifre, colonne separate |

---

## 10. NOTE TECNICHE

### Autenticazione JWT

- Token salvato in `localStorage` con chiave `to_extractor_token`
- Interceptor Axios aggiunge header `Authorization: Bearer {token}`
- Gestione automatica 401 → redirect login

### Fuzzy Matching Lookup

- Threshold default: 60%
- Matching su P.IVA + indirizzo
- Fallback su ragione sociale

### Tracciati MISE

- **TO_T**: 477 caratteri (testata ordine)
- **TO_D**: 405 caratteri (dettaglio righe)
- Formato fixed-width

### Machine Learning Supervisione

- Pattern recognition su anomalie espositori
- Soglia promozione automatica: 5 approvazioni
- Reset pattern su rifiuto

---

*Documento generato automaticamente - TO_EXTRACTOR v6.2*
