# REPORT COLONNE MANCANTI NEL DATABASE
## TO_EXTRACTOR v6.2 - Analisi Schema Database

**Data analisi:** 2026-01-05
**Database analizzato:** to_extractor.db

---

## RIEPILOGO CRITICO

| Categoria | Colonne Mancanti | Priorità |
|-----------|------------------|----------|
| OPERATORI | 2 | ALTA |
| VENDOR | 1 | MEDIA |
| ORDINI_TESTATA | 4 | ALTA |
| ORDINI_DETTAGLIO | 3 | ALTA |
| ANOMALIE | 5 | MEDIA |
| TABELLE MANCANTI | 3 | CRITICA |

---

## 1. TABELLA: OPERATORI

### Colonne MANCANTI (usate nel codice ma non nel DB):

| Colonna | Usata in | Note |
|---------|----------|------|
| `password_hash` | auth/router.py | **CRITICO** - Autenticazione non funziona |
| `nome`, `cognome` | auth/router.py | DB ha solo `nome_completo` |

### Schema attuale DB:
```sql
CREATE TABLE OPERATORI (
    id_operatore, username, nome_completo, email, ruolo, attivo, data_creazione
);
```

### FIX RICHIESTO:
```sql
ALTER TABLE OPERATORI ADD COLUMN password_hash TEXT;
-- Oppure separare nome/cognome:
ALTER TABLE OPERATORI ADD COLUMN nome TEXT;
ALTER TABLE OPERATORI ADD COLUMN cognome TEXT;
```

---

## 2. TABELLA: VENDOR

### Colonne MANCANTI:

| Colonna nel Codice | Colonna nel DB | Note |
|--------------------|----------------|------|
| `codice_vendor` | `codice` | Nome diverso - richiede alias o rename |

### FIX RICHIESTO:
```sql
-- Il codice cerca 'codice_vendor' ma la colonna si chiama 'codice'
-- Opzione 1: Creare vista con alias
-- Opzione 2: Modificare il codice Python
```

---

## 3. TABELLA: ORDINI_TESTATA

### Colonne MANCANTI (usate nel frontend/backend):

| Colonna | Usata in | Note |
|---------|----------|------|
| `righe_totali` | Frontend DatabasePage.jsx, OrdineDetailPage.jsx | Conteggio righe |
| `righe_confermate` | Frontend DatabasePage.jsx | Conteggio righe confermate |
| `righe_in_supervisione` | Backend ordini.py | Conteggio supervisioni |
| `data_ultimo_aggiornamento` | Backend | Timestamp modifica |

### Mapping Frontend → DB:

| Frontend usa | DB ha | Soluzione |
|--------------|-------|-----------|
| `numero_ordine` | `numero_ordine_vendor` | Alias in query/API |
| `ragione_sociale` | `ragione_sociale_1` | Alias in query/API |

### FIX RICHIESTO:
```sql
ALTER TABLE ORDINI_TESTATA ADD COLUMN righe_totali INTEGER DEFAULT 0;
ALTER TABLE ORDINI_TESTATA ADD COLUMN righe_confermate INTEGER DEFAULT 0;
ALTER TABLE ORDINI_TESTATA ADD COLUMN righe_in_supervisione INTEGER DEFAULT 0;
ALTER TABLE ORDINI_TESTATA ADD COLUMN data_ultimo_aggiornamento TEXT;
```

---

## 4. TABELLA: ORDINI_DETTAGLIO

### Colonne MANCANTI:

| Colonna | Usata in | Note |
|---------|----------|------|
| `codice_materiale` | extractors/angelini.py, espositore.py | Codice materiale vendor |
| `tipo_posizione` | extractors/angelini.py | SC.MERCE, P.O.P., etc. |
| `q_evasa` | Frontend OrdineDetailPage.jsx | **Diverso da q_esportata** |

### Mapping Frontend → DB:

| Frontend usa | DB ha | Note |
|--------------|-------|------|
| `codice_prodotto` | `codice_aic` | Alias |
| `descrizione_prodotto` | `descrizione` | Alias |
| `q_ordinata` | `q_venduta` | Probabilmente stesso significato |
| `quantita` | `q_venduta` | Alias |

### FIX RICHIESTO:
```sql
ALTER TABLE ORDINI_DETTAGLIO ADD COLUMN codice_materiale TEXT;
ALTER TABLE ORDINI_DETTAGLIO ADD COLUMN tipo_posizione TEXT DEFAULT '';
ALTER TABLE ORDINI_DETTAGLIO ADD COLUMN q_evasa INTEGER DEFAULT 0;
```

---

## 5. TABELLA: ANOMALIE

### Colonne MANCANTI:

| Colonna nel Codice | Colonna nel DB | Note |
|--------------------|----------------|------|
| `id_acquisizione` | - | Manca collegamento |
| `livello` | `severita` | Nome diverso |
| `codice_anomalia` | - | Codice identificativo |
| `richiede_supervisione` | - | Flag supervisione |
| `pattern_signature` | - | Per ML espositori |

### Mapping Frontend → DB:

| Frontend usa | DB ha |
|--------------|-------|
| `tipo` | `tipo_anomalia` |
| `messaggio` | `descrizione` |
| `created_at` | `data_creazione` |
| `ordine_id` | `id_testata` |

### FIX RICHIESTO:
```sql
ALTER TABLE ANOMALIE ADD COLUMN id_acquisizione INTEGER REFERENCES ACQUISIZIONI(id_acquisizione);
ALTER TABLE ANOMALIE ADD COLUMN codice_anomalia TEXT;
ALTER TABLE ANOMALIE ADD COLUMN richiede_supervisione INTEGER DEFAULT 0;
ALTER TABLE ANOMALIE ADD COLUMN pattern_signature TEXT;
-- Rinominare severita → livello oppure creare alias
```

---

## 6. TABELLE COMPLETAMENTE MANCANTI

### 6.1 SUPERVISIONE_ESPOSITORE (CRITICO)

Il codice in `supervisione.py` usa questa tabella ma **NON ESISTE** nel DB.
Esiste solo `SUPERVISIONI` con schema diverso.

```sql
CREATE TABLE SUPERVISIONE_ESPOSITORE (
    id_supervisione INTEGER PRIMARY KEY AUTOINCREMENT,
    id_testata INTEGER NOT NULL REFERENCES ORDINI_TESTATA(id_testata),
    id_anomalia INTEGER REFERENCES ANOMALIE(id_anomalia),
    codice_anomalia TEXT,
    codice_espositore TEXT,
    descrizione_espositore TEXT,
    pezzi_attesi INTEGER,
    pezzi_trovati INTEGER,
    valore_calcolato REAL,
    pattern_signature TEXT,
    stato TEXT DEFAULT 'PENDING' CHECK (stato IN ('PENDING','APPROVED','REJECTED','MODIFIED')),
    operatore TEXT,
    timestamp_creazione TEXT DEFAULT (datetime('now')),
    timestamp_decisione TEXT,
    note TEXT,
    modifiche_manuali_json TEXT
);

CREATE INDEX idx_sup_esp_testata ON SUPERVISIONE_ESPOSITORE(id_testata);
CREATE INDEX idx_sup_esp_stato ON SUPERVISIONE_ESPOSITORE(stato);
CREATE INDEX idx_sup_esp_pattern ON SUPERVISIONE_ESPOSITORE(pattern_signature);
```

### 6.2 CRITERI_ORDINARI_ESPOSITORE (CRITICO)

Usata per apprendimento automatico pattern espositori.

```sql
CREATE TABLE CRITERI_ORDINARI_ESPOSITORE (
    pattern_signature TEXT PRIMARY KEY,
    pattern_descrizione TEXT,
    vendor TEXT,
    codice_anomalia TEXT,
    codice_espositore TEXT,
    pezzi_per_unita INTEGER,
    tipo_scostamento TEXT,
    fascia_scostamento TEXT,
    count_approvazioni INTEGER DEFAULT 0,
    is_ordinario INTEGER DEFAULT 0,
    data_prima_occorrenza TEXT DEFAULT (datetime('now')),
    data_promozione TEXT,
    operatori_approvatori TEXT
);

CREATE INDEX idx_criteri_ordinario ON CRITERI_ORDINARI_ESPOSITORE(is_ordinario);
CREATE INDEX idx_criteri_vendor ON CRITERI_ORDINARI_ESPOSITORE(vendor);
```

### 6.3 LOG_CRITERI_APPLICATI

Per tracciare applicazione criteri ML.

```sql
CREATE TABLE LOG_CRITERI_APPLICATI (
    id_log INTEGER PRIMARY KEY AUTOINCREMENT,
    id_testata INTEGER REFERENCES ORDINI_TESTATA(id_testata),
    id_supervisione INTEGER,
    pattern_signature TEXT,
    azione TEXT,
    applicato_automaticamente INTEGER DEFAULT 0,
    operatore TEXT,
    note TEXT,
    timestamp TEXT DEFAULT (datetime('now'))
);
```

---

## 7. TABELLA: ESPORTAZIONI

### Colonne MANCANTI:

| Colonna | Usata in | Note |
|---------|----------|------|
| `nome_tracciato_generato` | Frontend TracciatiPage.jsx | Nome del tracciato |
| `nome_file_to_t` | Frontend TracciatiPage.jsx | File TO_T |
| `nome_file_to_d` | Frontend TracciatiPage.jsx | File TO_D |
| `num_dettagli` | Frontend | DB ha `num_righe` |

### FIX RICHIESTO:
```sql
ALTER TABLE ESPORTAZIONI ADD COLUMN nome_tracciato_generato TEXT;
ALTER TABLE ESPORTAZIONI ADD COLUMN nome_file_to_t TEXT;
ALTER TABLE ESPORTAZIONI ADD COLUMN nome_file_to_d TEXT;
-- num_dettagli può usare num_righe come alias
```

---

## 8. VISTE MANCANTI

### V_RIGHE_ESPORTABILI

```sql
CREATE VIEW V_RIGHE_ESPORTABILI AS
SELECT
    d.id_dettaglio,
    d.id_testata,
    d.n_riga,
    d.codice_aic,
    d.descrizione,
    d.q_venduta,
    d.q_originale,
    d.q_esportata,
    d.q_residua,
    d.stato_riga,
    d.is_child,
    d.num_esportazioni,
    t.numero_ordine_vendor AS numero_ordine,
    v.codice AS vendor,
    t.ragione_sociale_1 AS ragione_sociale
FROM ORDINI_DETTAGLIO d
JOIN ORDINI_TESTATA t ON d.id_testata = t.id_testata
JOIN VENDOR v ON t.id_vendor = v.id_vendor
WHERE d.stato_riga IN ('CONFERMATO', 'PARZIALMENTE_ESP')
  AND d.is_child = 0;
```

---

## SCRIPT SQL COMPLETO PER FIX

```sql
-- ============================================
-- SCRIPT MIGRAZIONE DATABASE TO_EXTRACTOR v6.2
-- ============================================

-- 1. OPERATORI
ALTER TABLE OPERATORI ADD COLUMN password_hash TEXT;

-- 2. ORDINI_TESTATA
ALTER TABLE ORDINI_TESTATA ADD COLUMN righe_totali INTEGER DEFAULT 0;
ALTER TABLE ORDINI_TESTATA ADD COLUMN righe_confermate INTEGER DEFAULT 0;
ALTER TABLE ORDINI_TESTATA ADD COLUMN righe_in_supervisione INTEGER DEFAULT 0;
ALTER TABLE ORDINI_TESTATA ADD COLUMN data_ultimo_aggiornamento TEXT;

-- 3. ORDINI_DETTAGLIO
ALTER TABLE ORDINI_DETTAGLIO ADD COLUMN codice_materiale TEXT;
ALTER TABLE ORDINI_DETTAGLIO ADD COLUMN tipo_posizione TEXT DEFAULT '';
ALTER TABLE ORDINI_DETTAGLIO ADD COLUMN q_evasa INTEGER DEFAULT 0;

-- 4. ANOMALIE
ALTER TABLE ANOMALIE ADD COLUMN id_acquisizione INTEGER REFERENCES ACQUISIZIONI(id_acquisizione);
ALTER TABLE ANOMALIE ADD COLUMN codice_anomalia TEXT;
ALTER TABLE ANOMALIE ADD COLUMN richiede_supervisione INTEGER DEFAULT 0;
ALTER TABLE ANOMALIE ADD COLUMN pattern_signature TEXT;

-- 5. ESPORTAZIONI
ALTER TABLE ESPORTAZIONI ADD COLUMN nome_tracciato_generato TEXT;
ALTER TABLE ESPORTAZIONI ADD COLUMN nome_file_to_t TEXT;
ALTER TABLE ESPORTAZIONI ADD COLUMN nome_file_to_d TEXT;

-- 6. NUOVA TABELLA: SUPERVISIONE_ESPOSITORE
CREATE TABLE IF NOT EXISTS SUPERVISIONE_ESPOSITORE (
    id_supervisione INTEGER PRIMARY KEY AUTOINCREMENT,
    id_testata INTEGER NOT NULL REFERENCES ORDINI_TESTATA(id_testata),
    id_anomalia INTEGER REFERENCES ANOMALIE(id_anomalia),
    codice_anomalia TEXT,
    codice_espositore TEXT,
    descrizione_espositore TEXT,
    pezzi_attesi INTEGER,
    pezzi_trovati INTEGER,
    valore_calcolato REAL,
    pattern_signature TEXT,
    stato TEXT DEFAULT 'PENDING' CHECK (stato IN ('PENDING','APPROVED','REJECTED','MODIFIED')),
    operatore TEXT,
    timestamp_creazione TEXT DEFAULT (datetime('now')),
    timestamp_decisione TEXT,
    note TEXT,
    modifiche_manuali_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_sup_esp_testata ON SUPERVISIONE_ESPOSITORE(id_testata);
CREATE INDEX IF NOT EXISTS idx_sup_esp_stato ON SUPERVISIONE_ESPOSITORE(stato);
CREATE INDEX IF NOT EXISTS idx_sup_esp_pattern ON SUPERVISIONE_ESPOSITORE(pattern_signature);

-- 7. NUOVA TABELLA: CRITERI_ORDINARI_ESPOSITORE
CREATE TABLE IF NOT EXISTS CRITERI_ORDINARI_ESPOSITORE (
    pattern_signature TEXT PRIMARY KEY,
    pattern_descrizione TEXT,
    vendor TEXT,
    codice_anomalia TEXT,
    codice_espositore TEXT,
    pezzi_per_unita INTEGER,
    tipo_scostamento TEXT,
    fascia_scostamento TEXT,
    count_approvazioni INTEGER DEFAULT 0,
    is_ordinario INTEGER DEFAULT 0,
    data_prima_occorrenza TEXT DEFAULT (datetime('now')),
    data_promozione TEXT,
    operatori_approvatori TEXT
);

CREATE INDEX IF NOT EXISTS idx_criteri_ordinario ON CRITERI_ORDINARI_ESPOSITORE(is_ordinario);
CREATE INDEX IF NOT EXISTS idx_criteri_vendor ON CRITERI_ORDINARI_ESPOSITORE(vendor);

-- 8. NUOVA TABELLA: LOG_CRITERI_APPLICATI
CREATE TABLE IF NOT EXISTS LOG_CRITERI_APPLICATI (
    id_log INTEGER PRIMARY KEY AUTOINCREMENT,
    id_testata INTEGER REFERENCES ORDINI_TESTATA(id_testata),
    id_supervisione INTEGER,
    pattern_signature TEXT,
    azione TEXT,
    applicato_automaticamente INTEGER DEFAULT 0,
    operatore TEXT,
    note TEXT,
    timestamp TEXT DEFAULT (datetime('now'))
);

-- 9. VISTA: V_RIGHE_ESPORTABILI
CREATE VIEW IF NOT EXISTS V_RIGHE_ESPORTABILI AS
SELECT
    d.id_dettaglio,
    d.id_testata,
    d.n_riga,
    d.codice_aic,
    d.descrizione,
    d.q_venduta,
    d.q_originale,
    d.q_esportata,
    d.q_residua,
    d.stato_riga,
    d.is_child,
    d.num_esportazioni,
    t.numero_ordine_vendor AS numero_ordine,
    v.codice AS vendor,
    t.ragione_sociale_1 AS ragione_sociale
FROM ORDINI_DETTAGLIO d
JOIN ORDINI_TESTATA t ON d.id_testata = t.id_testata
JOIN VENDOR v ON t.id_vendor = v.id_vendor
WHERE d.stato_riga IN ('CONFERMATO', 'PARZIALMENTE_ESP')
  AND d.is_child = 0;

-- ============================================
-- FINE SCRIPT MIGRAZIONE
-- ============================================
```

---

## NOTE IMPORTANTI

1. **BACKUP PRIMA DI ESEGUIRE** - Fare sempre backup del DB prima della migrazione

2. **MAPPING NOMI** - Alcuni campi hanno nomi diversi nel codice vs DB:
   - `numero_ordine` → `numero_ordine_vendor`
   - `ragione_sociale` → `ragione_sociale_1`
   - `livello` → `severita`
   - `codice_vendor` → `codice`

3. **TABELLA SUPERVISIONI** - Già esiste ma con schema diverso da SUPERVISIONE_ESPOSITORE. Valutare se unificare o mantenere separate.

4. **q_evasa vs q_esportata** - Verificare se sono lo stesso concetto o diversi (evasa = preparata, esportata = inviata?)
