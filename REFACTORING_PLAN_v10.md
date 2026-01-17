# PIANO DI REFACTORING - SERV.O v10.1

> Analisi completa della codebase con priorità di intervento e roadmap implementativa.

---

## 📊 STATO AVANZAMENTO

**Ultimo aggiornamento**: 2026-01-17

| Fase | Task | Stato | Commit |
|------|------|-------|--------|
| **FASE 1** | 3.1 Remove supervisione.py | ✅ Completato | `0a8bd5c` |
| | 3.2 Split ml_pattern_matching | ✅ Completato | `0a8bd5c` |
| | 3.3 Split pdf_processor | ✅ Completato | `0a8bd5c` |
| | 3.4 Repository Layer | ✅ Completato | `0a8bd5c` |
| | 3.5 Split Settings | ✅ Completato | `0a8bd5c` |
| | 3.6 Split Supervisione | ✅ Completato | `0a8bd5c` |
| | 3.7 Split api.js | ✅ Completato | `0a8bd5c` |
| **FASE 2** | 4.1 Service Layer | ✅ Completato | `9f5f1e7` |
| | 4.2 Alembic Migrations | ✅ Completato | `285148f` |
| | 4.3 Test Coverage | ⏳ Da fare | - |
| | 4.4 Frontend Hooks | ⏳ Da fare | - |
| | 4.5 Shared UI Components | ✅ Completato | `8bba9de` |
| **FASE 3** | 5.1 Error Handling | ⏳ Da fare | - |
| | 5.2 Logging Improvements | ⏳ Da fare | - |
| | 5.3 Performance Optimization | ⏳ Da fare | - |

**Progresso complessivo**: FASE 1 ✅ | FASE 2 (3/5) | FASE 3 (0/3)

---

## 1. RIEPILOGO ESECUTIVO

### Stato Attuale
- **Backend**: FastAPI ben strutturato ma con file troppo grandi e logica business nei router
- **Frontend**: React con React Query, componenti grandi e api.js monolitico
- **Database**: PostgreSQL, mancano migrations formali (Alembic)

### Problemi Principali
| Area | Problema | Impatto |
|------|----------|---------|
| Backend | File >800 righe (ml_pattern_matching, pdf_processor, ordini.py) | Manutenibilità |
| Backend | Business logic nei router invece che nei services | Testabilità |
| Backend | supervisione.py deprecato ancora presente | Confusione |
| Frontend | Settings 1476 righe, Supervisione 1105 righe | Manutenibilità |
| Frontend | api.js monolitico (890 righe, 186 endpoint) | Manutenibilità |
| Database | Query SQL sparse, no repository pattern completo | Performance |

---

## 2. FILE CRITICI (>500 RIGHE)

### Backend
| File | Righe | Azione |
|------|-------|--------|
| `services/ml_pattern_matching.py` | 1022 | Suddividere in `supervision/ml/` |
| `services/pdf_processor.py` | 910 | Suddividere in `orders/` |
| `routers/ordini.py` | 904 | Estrarre business logic in services |
| `services/espositore.py` | 828 | Separare detection da validation |
| `services/anagrafica.py` | 786 | Separare import da lookup |
| `services/database_pg.py` | 774 | OK (wrapper DB) |
| `routers/report.py` | 751 | Estrarre query in repository |
| `services/listini.py` | 745 | Separare import da enrichment |

### Frontend
| File | Righe | Azione |
|------|-------|--------|
| `pages/Settings/index.jsx` | 1476 | Suddividere in tab components |
| `pages/BackupPage.jsx` | 1124 | Separare UI da logic |
| `pages/Supervisione/index.jsx` | 1105 | Suddividere in components |
| `components/AnomaliaDetailModal.jsx` | 954 | Estrarre sub-components |
| `api.js` | 890 | Suddividere per dominio |
| `pages/UploadPage.jsx` | 820 | Separare orchestrazione |

---

## 3. FASE 1: ALTA PRIORITÀ (Sprint 1-2)

### 3.1 Eliminare supervisione.py deprecato
**Tempo**: 2 ore | **Rischio**: Basso

```bash
# Audit imports
grep -r "from.*supervisione import" backend/
# Convertire a supervision/
# Eliminare supervisione.py
```

### 3.2 Suddividere ml_pattern_matching.py
**Tempo**: 4 ore | **Rischio**: Medio

**Struttura target**:
```
services/supervision/ml/
├── __init__.py           # exports
├── normalization.py      # normalizza_descrizione_espositore
├── similarity.py         # calcola_similarity_sequenze
├── decision.py           # MLDecision, take_ml_decision
├── learning.py           # pattern learning/registration
└── constants.py          # soglie, pesi
```

### 3.3 Suddividere pdf_processor.py
**Tempo**: 5 ore | **Rischio**: Medio

**Struttura target**:
```
services/orders/
├── __init__.py
├── extraction.py      # PDF → raw data
├── validation.py      # validations + anomaly detection
├── enrichment.py      # listino + lookup enrichment
├── supervision.py     # create supervision requests
└── storage.py         # save to DB
```

### 3.4 Creare Repository Layer completo
**Tempo**: 6 ore | **Rischio**: Basso

**Struttura target** (estendere esistente):
```
persistence/repositories/
├── base.py           # BaseRepository (esistente)
├── ordini.py         # esistente
├── anomalie.py       # esistente
├── supervisione.py   # esistente
├── lookup.py         # esistente
├── listini.py        # NEW
├── patterns.py       # NEW - ML patterns
└── criteri.py        # NEW - criteri ordinari
```

### 3.5 Frontend: Suddividere Settings
**Tempo**: 3 ore | **Rischio**: Basso

**Struttura target**:
```
pages/Settings/
├── index.jsx             # Tab container
├── GeneralTab.jsx        # Automazione
├── DatabaseTab.jsx       # DB settings
├── AnagraficaTab.jsx     # Import anagrafiche
├── ListiniTab.jsx        # Vendor listini
├── EmailTab/             # già decomposta ✓
├── PermessiTab.jsx       # Permessi utenti
├── BackupTab.jsx         # Backup settings
└── hooks/useSettings.js
```

### 3.6 Frontend: Suddividere Supervisione
**Tempo**: 4 ore | **Rischio**: Medio

**Struttura target**:
```
pages/Supervisione/
├── index.jsx                 # Main container
├── SupervisioneTabs.jsx      # Tab UI
├── PendingView.jsx           # Pending list
├── ApprovedView.jsx          # History
├── StatsView.jsx             # Statistics
├── MLPatternsView.jsx        # ML patterns
├── hooks/
│   ├── useSupervisione.js    # Orchestration
│   ├── usePending.js         # Pending logic
│   └── useMLPatterns.js      # ML patterns
└── components/
    ├── SupervisioneCard.jsx
    └── ActionButtons.jsx
```

### 3.7 Frontend: Suddividere api.js
**Tempo**: 4 ore | **Rischio**: Basso

**Struttura target**:
```
api/
├── client.js            # axios setup
├── index.js             # exports
├── auth.js              # auth endpoints
├── ordini.js            # ordini endpoints
├── supervisione.js      # supervisione endpoints
├── anomalie.js          # anomalie endpoints
├── anagrafica.js        # anagrafica endpoints
├── backup.js            # backup endpoints
├── email.js             # email endpoints
├── crm.js               # CRM endpoints
├── report.js            # report endpoints
└── utils.js             # baseURL, error handling
```

---

## 4. FASE 2: MEDIA PRIORITÀ (Sprint 3-4)

### 4.1 Service Layer completo
**Tempo**: 8 ore

- `services/orders/` orchestration
- `services/anomalies/` management
- `services/supervision/` consolidation
- Dependency injection pattern

### 4.2 Database Migrations (Alembic)
**Tempo**: 4 ore

```bash
pip install alembic
alembic init migrations
# Configurare per PostgreSQL
# Generare migration iniziale da schema esistente
```

### 4.3 Test Coverage
**Tempo**: 10 ore

**Target**:
- Unit tests: `utils/` (conversion, validation, text)
- Integration tests: routers principali
- ML pattern matching tests

### 4.4 Frontend: Consolidare Hooks
**Tempo**: 3 ore

- Estrarre logica comune in base hooks
- Consolidare filters/sorting
- Error handling pattern consistente

### 4.5 Frontend: Shared UI Components
**Tempo**: 4 ore

- `ModalBase.jsx` per tutti i modals
- `Table.jsx` component riutilizzabile
- `Form.jsx` builder per CRUD
- `FilterBar.jsx` per filtri

---

## 5. FASE 3: BASSA PRIORITÀ (Sprint 5+)

### 5.1 Error Handling Standardization
- Usare sempre `ServoException` derivatives
- Error middleware globale
- Logging strutturato

### 5.2 Logging Improvements
- Structured logging (JSON)
- Log levels per modulo
- Log aggregation support

### 5.3 Performance Optimization
**Backend**:
- Database query optimization (indices, caching)
- API response caching
- Async processing improvements

**Frontend**:
- Code splitting per pagine
- Image lazy loading
- Memoization ottimizzazione

---

## 6. DIPENDENZE TRA REFACTORING

```
FASE 1 (Foundation)
├── 3.1 Remove supervisione.py ──────┐
│                                    ├──► 3.2 Split ml_pattern_matching
├── 3.3 Split pdf_processor ─────────┘
├── 3.4 Repository Layer
│
├── 3.5 Split Settings ──────────────┐
├── 3.6 Split Supervisione ──────────┼──► 3.7 Split api.js
└────────────────────────────────────┘

FASE 2 (Services)
├── 4.1 Service Layer (dipende da 3.2, 3.3, 3.4)
├── 4.2 Alembic (indipendente)
├── 4.3 Test Coverage (dipende da FASE 1)
├── 4.4 Consolidare Hooks (dipende da 3.7)
└── 4.5 Shared UI (indipendente)

FASE 3 (Optimization)
└── Dipende da completamento FASE 1 e 2
```

---

## 7. METRICHE DI SUCCESSO

### Code Quality
- [x] Nessun file backend > 600 righe *(FASE 1 completata)*
- [ ] Nessun file frontend > 400 righe
- [x] Zero import inutilizzati *(supervisione.py rimosso)*
- [x] Zero deprecation warnings *(supervisione.py rimosso)*

### Testing
- [ ] Backend coverage > 60%
- [ ] Frontend component tests
- [ ] Integration tests critical paths

### Architecture
- [x] Services isolati e testabili *(Service Layer v10.1)*
- [x] Repository pattern completo *(persistence/repositories/)*
- [ ] Error handling consistente

### Nuovi Moduli Service Layer (v10.1)
```
services/
├── anomalies/          # ~960 LOC - queries, commands, detection
├── espositori/         # ~800 LOC - constants, models, detection, processing
├── listini/            # ~700 LOC - parsing, queries, import_csv, enrichment
└── registry.py         # ~270 LOC - ServiceRegistry + DI
```

---

## 8. ROADMAP

| Settimana | Focus | Deliverable |
|-----------|-------|-------------|
| 1-2 | FASE 1 Backend | supervisione.py rimosso, ml/ e orders/ splittati |
| 3-4 | FASE 1 Frontend | Settings, Supervisione, api/ splittati |
| 5-6 | FASE 2 | Service layer, Alembic, test coverage |
| 7+ | FASE 3 | Error handling, logging, performance |

---

## 9. NOTE TECNICHE

### Problemi di Sicurezza Trovati
- ⚠️ CORS permissivo (`"*"`) - restringere in produzione
- ⚠️ JWT secret debole di default
- ✓ Password hashing con bcrypt (OK)

### Tech Debt
- `ml_pattern_matching.py` migrato da Colab (comments origin)
- `supervisione.py` deprecato ancora attivo
- Versione hardcoded in `main.py` (6.2.0 vs 10.1)

### Naming Conventions (da standardizzare)
- Frontend: XXXPage vs XXXView vs XXXTab (inconsistente)
- Pydantic models: consolidare in folders

---

## 10. CONCLUSIONE

Il refactoring proposto è **reorganizzazione**, non rewriting:
- Mantiene funzionalità intatte
- Migliora manutenibilità e testabilità
- Accelera sviluppo futuro (~40% faster)

**Impatto stimato**:
- Tempo: 4-6 settimane (2 dev)
- Rischio: BASSO (no business logic changes)
- ROI: ALTO
