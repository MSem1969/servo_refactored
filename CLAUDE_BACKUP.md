# TO_EXTRACTOR v8.2 - Istruzioni Progetto

## Panoramica

Sistema di estrazione automatica ordini farmaceutici da PDF con generazione tracciati ministeriali TO_T/TO_D.

**Stack:** FastAPI + PostgreSQL + React + Vite + TailwindCSS + React Query

---

## Novità v8.2 - Tracking Operatore per ML

Sistema di tracking comportamentale operatori per future analisi Machine Learning.

### Obiettivi

- Tracciare tutte le azioni degli operatori in ogni sezione
- Raccogliere dati per analisi pattern comportamentali
- Supportare future funzionalità ML (suggerimenti report, automazioni, periodicità)

### Componenti Creati

| File | Descrizione |
|------|-------------|
| `services/tracking/__init__.py` | Esporta modulo tracking |
| `services/tracking/tracker.py` | Logica tracking con helper |
| `migrations/v8_2_operatore_tracking.sql` | Schema DB + viste analisi |

### Schema Tabella `operatore_azioni_log`

```
id_azione          SERIAL PK
├── CHI: id_operatore, username, ruolo
├── COSA: sezione, azione, entita, id_entita, parametri (JSONB), risultato (JSONB)
├── QUANDO: timestamp, giorno_settimana (0-6), ora_giorno (0-23), settimana_anno
├── CONTESTO: session_id, azione_precedente_id (per sequenze)
└── CLIENT: ip_address, user_agent
```

### Viste Analisi ML

| Vista | Utilizzo |
|-------|----------|
| `v_tracking_daily_stats` | Statistiche giornaliere per operatore |
| `v_tracking_hourly_pattern` | Pattern orari (per suggerire periodicità) |
| `v_tracking_sequences` | Sequenze azioni frequenti |
| `v_tracking_report_filters` | Combinazioni filtri report più usate |
| `v_tracking_operator_summary` | Riepilogo attività operatori |

### TODO: Migrazione Database

```bash
# Eseguire migrazione per creare tabella tracking
cd backend
psql -h localhost -U servo_user -d servo_db -f migrations/v8_2_operatore_tracking.sql
```

### TODO: Integrazione Tracking nei Router

**Completato:**
- [x] `report.py` - PREVIEW, EXPORT_EXCEL

**Da completare:**

| Router | Azioni da tracciare | Priorità |
|--------|---------------------|----------|
| `ordini.py` | VIEW, LIST, CONFIRM, CONFIRM_ALL, RESET, ARCHIVE, UPDATE | Alta |
| `upload.py` | UPLOAD (con risultato estrazione) | Alta |
| `tracciati.py` | EXPORT_TRACCIATO, PREVIEW | Alta |
| `anomalie.py` | VIEW, LIST, UPDATE, RESOLVE | Alta |
| `supervisione/*` | APPROVE, REJECT, BULK_APPROVE | Alta |
| `dashboard.py` | VIEW, REFRESH | Media |
| `anagrafica.py` | LIST, CREATE, UPDATE, DELETE | Media |
| `listini.py` | LIST, CREATE, UPDATE, DELETE | Media |
| `lookup.py` | SEARCH, UPDATE | Media |
| `crm.py` | LIST, VIEW, UPDATE | Media |
| `admin.py` | Tutte le azioni admin | Bassa |
| `utenti.py` | CREATE, UPDATE, DELETE, LOGIN, LOGOUT | Bassa |

### Esempio Integrazione

```python
# Nel router
from ..services.tracking import track_from_user, Sezione, Azione

@router.get("/endpoint")
async def my_endpoint(request: Request, current_user = Depends(get_current_user)):
    # ... logica ...

    # Tracking azione
    track_from_user(
        current_user,
        Sezione.DATABASE,      # Sezione app
        Azione.CONFIRM,        # Tipo azione
        request=request,       # Per IP/UserAgent
        entita='ordine',       # Tipo entità
        id_entita=123,         # ID specifico
        parametri={'filtro': 'valore'},  # Parametri usati
        risultato={'rows_affected': 10}  # Risultato
    )
```

### Sezioni Disponibili

`DASHBOARD`, `DATABASE`, `UPLOAD`, `REPORT`, `SUPERVISIONE`, `TRACCIATI`, `ANAGRAFICA`, `LISTINI`, `CRM`, `ADMIN`, `AUTH`, `LOOKUP`, `ANOMALIE`, `EMAIL`

### Azioni Disponibili

- **Navigazione:** `VIEW`, `LIST`, `SEARCH`, `FILTER`, `SORT`
- **CRUD:** `CREATE`, `UPDATE`, `DELETE`
- **Ordini:** `CONFIRM`, `CONFIRM_ALL`, `RESET`, `ARCHIVE`
- **Export:** `EXPORT`, `EXPORT_EXCEL`, `EXPORT_TRACCIATO`, `DOWNLOAD`, `UPLOAD`
- **Supervisione:** `APPROVE`, `REJECT`, `BULK_APPROVE`
- **Auth:** `LOGIN`, `LOGOUT`
- **Altro:** `PREVIEW`, `REFRESH`, `CLICK`

---

## Sincronizzazione Anagrafica Ministero (v8.2)

Sistema di sincronizzazione automatica anagrafica farmacie e parafarmacie dal portale Open Data del Ministero della Salute.

### URL Sorgente

```
Farmacie:     https://www.dati.salute.gov.it/.../FRM_FARMA_5_YYYYMMDD.json
Parafarmacie: https://www.dati.salute.gov.it/.../FRM_PFARMA_7_YYYYMMDD.json
```

La data nel nome file corrisponde al giorno di pubblicazione (es: 18/01/2026 → `20260118`).

### Componenti

| File | Descrizione |
|------|-------------|
| `services/anagrafica/sync_ministero.py` | Logica sincronizzazione |
| `services/anagrafica/legacy.py` | Import CSV (funzioni originali) |
| `migrations/v8_2_sync_state.sql` | Tabella stato sync |
| `routers/admin.py` | Endpoint API |

### API Endpoints

| Metodo | Endpoint | Descrizione |
|--------|----------|-------------|
| GET | `/api/v10/admin/sync/status` | Stato sync entrambe le anagrafiche |
| POST | `/api/v10/admin/sync/farmacie` | Sync solo farmacie (~36 MB) |
| POST | `/api/v10/admin/sync/parafarmacie` | Sync solo parafarmacie (~8 MB) |
| POST | `/api/v10/admin/sync/all` | Sync entrambe |
| GET | `/api/v10/admin/sync/subentri` | Lista subentri recenti |

**Parametri opzionali:**
- `force=true` - Forza download ignorando ETag
- `target_date=YYYY-MM-DD` - Data specifica (default: oggi)
- `dry_run=true` - Simula senza modificare DB

### Comportamento

1. **Download condizionale**: Usa HTTP ETag per evitare download inutili
   - Se file invariato → **304 Not Modified** (istantaneo)
   - Se file aggiornato → Download e sync incrementale

2. **Sincronizzazione incrementale**:
   - **Nuove**: Farmacie/parafarmacie non presenti → INSERT
   - **Aggiornate**: Dati modificati (indirizzo, ragione sociale) → UPDATE
   - **Subentri**: Cambio P.IVA stesso codice → UPDATE + log `SYNC_SUBENTRO`
   - **Chiuse**: Non più nel JSON attivo → `attiva = FALSE`

3. **Tracciamento subentri**: I cambi P.IVA vengono loggati in `log_operazioni` con operazione `SYNC_SUBENTRO`. Questi casi generano anomalia **LKP-A04** durante il lookup ordini.

### Tabella sync_state

```sql
CREATE TABLE sync_state (
    key VARCHAR(50) PRIMARY KEY,     -- 'farmacie_sync' | 'parafarmacie_sync'
    etag VARCHAR(100),               -- ETag HTTP per conditional request
    last_modified VARCHAR(100),      -- Header Last-Modified
    last_sync TIMESTAMP,             -- Timestamp ultima sync
    last_url TEXT,                   -- URL utilizzato
    records_count INTEGER            -- Record processati
);
```

### Esempio Utilizzo

```python
from app.services.anagrafica import sync_all, check_sync_status

# Verifica stato
status = check_sync_status()
print(status['farmacie']['needs_update'])  # True/False

# Sync completa
result = sync_all()
print(f"Farmacie: {result.farmacie.nuove} nuove, {result.farmacie.subentri} subentri")
print(f"Parafarmacie: {result.parafarmacie.nuove} nuove")
```

### Migrazione

```bash
# La tabella viene creata automaticamente, oppure manualmente:
cd backend
python3 -c "
from app.database_pg import get_db
db = get_db()
db.execute('''CREATE TABLE IF NOT EXISTS sync_state (...)''')
db.commit()
"
```

---

## Validazione Lookup Estesa (v8.2)

Nuovi controlli di validazione per rilevare scenari critici non gestiti precedentemente.

### LKP-A04: P.IVA Mismatch (Subentro/Cambio Proprietà)

**Problema:** Quando una farmacia cambia proprietario (subentro), il MIN_ID rimane invariato ma P.IVA e ragione sociale cambiano. Il lookup per MIN_ID restituiva score 100% senza verificare la corrispondenza P.IVA.

**Soluzione:** Dopo match positivo per MIN_ID, verifica che P.IVA estratta dal PDF corrisponda a quella in anagrafica. Se diversa → score 50 + anomalia LKP-A04.

**Azione correttiva:** L'operatore può:
- Modificare i dati header dell'ordine
- Archiviare l'ordine se non gestibile

### LKP-A05: Cliente Non in Anagrafica Clienti

**Problema:** Se la P.IVA estratta non è presente in `anagrafica_clienti`, il campo `deposito_riferimento` rimane vuoto, causando errori nell'export del tracciato.

**Soluzione:** Verifica esistenza cliente in `anagrafica_clienti` per P.IVA. Se assente → anomalia bloccante LKP-A05.

**Azione correttiva:** L'operatore può:
- Aggiungere il cliente in anagrafica
- Modificare P.IVA se errata nell'header
- Archiviare l'ordine se cliente non valido

---

## Correzione AIC con Propagazione (v8.2)

Sistema unificato per correzione codice AIC con propagazione gerarchica.

### Problema Risolto

Quando l'operatore correggeva un codice AIC dall'anomalia:
1. ❌ Il codice NON veniva propagato a `ordini_dettaglio.codice_aic`
2. ❌ I contatori supervisione NON si aggiornavano
3. ❌ Il tracciato EDI generato aveva AIC errato/mancante

### Soluzione: Propagazione Gerarchica

| Livello | Chi può usarlo | Effetto |
|---------|----------------|---------|
| **SINGOLO** | Operatore | Solo la riga specifica |
| **ORDINE** | Operatore/Supervisore | Tutte le righe dell'ordine con stessa descrizione |
| **GLOBALE** | Supervisore | Tutte le righe nel DB con stessa descrizione (vendor-agnostic) |

### Endpoint

```
POST /api/v10/anomalie/dettaglio/{id_anomalia}/correggi-aic
```

**Request:**
```json
{
    "codice_aic": "012345678",
    "livello_propagazione": "ORDINE",
    "operatore": "mario.rossi",
    "note": "AIC verificato su listino"
}
```

**Response:**
```json
{
    "success": true,
    "message": "AIC 012345678 applicato (ORDINE)",
    "data": {
        "codice_aic": "012345678",
        "livello_propagazione": "ORDINE",
        "righe_aggiornate": 5,
        "ordini_coinvolti": [123, 456],
        "anomalia_risolta": true
    }
}
```

### Effetti Automatici

1. **Aggiorna `codice_aic`** in `ORDINI_DETTAGLIO`
2. **Marca anomalia** come `RISOLTA`
3. **Se GLOBALE**: chiude anche altre anomalie AIC con stessa descrizione
4. **Aggiorna supervisioni** AIC collegate → `APPROVED`
5. **Incrementa pattern ML** per apprendimento automatico

### Contatori Aggiornati

```
GET /api/v10/anomalie/aic/contatori
```

Ritorna contatori per badge supervisione:
```json
{
    "anomalie_aperte": 15,
    "supervisioni_pending": 8
}
```

### File Coinvolti

| File | Ruolo |
|------|-------|
| `services/supervision/propagazione_aic.py` | Logica propagazione |
| `routers/anomalie.py` | Endpoint `/correggi-aic` |

---

## Novità v8.1

- **Stati ordine/riga indipendenti** - Lo stato ordine NON modifica più lo stato righe
- **ARCHIVIATO/EVASO immutabili** - Stati finali protetti da tutte le operazioni
- **Filtro report completo** - Tutti gli stati sempre disponibili (incluso ARCHIVIATO)
- **Validazione tracciato** - Errore chiaro se q_da_evadere = 0

## Novità v8.0

- **Supervisione raggruppata per pattern** - Vista pattern-based invece che per-ordine
- **Anomalie LKP in supervisione** - LKP-A01/A02 ora visibili e gestibili
- **Bulk approval** - Approvare un pattern risolve tutte le supervisioni correlate
- **Espositore MENARINI** - Supporto completo parent/child con chiusura su somma netto
- **Descrizione anomalie arricchita** - Include elenco prodotti child

---

## Architettura v8.0

### Backend - Struttura Modulare

```
backend/app/
├── main.py                    # FastAPI app
├── config.py                  # Configurazioni
├── models.py                  # SQLAlchemy models
├── services/
│   ├── extraction/            # PDF extraction (v7.0)
│   │   ├── base.py           # BaseExtractor
│   │   ├── detector.py       # Vendor detection
│   │   └── vendors/          # Estrattori specifici
│   ├── export/               # Tracciati EDI (v7.0)
│   │   ├── formatters/       # TO_T, TO_D formatting
│   │   ├── validators.py     # Field validation
│   │   ├── queries.py        # Query functions
│   │   └── generator.py      # Main generation
│   ├── supervision/          # ML supervision (v8.0)
│   │   ├── constants.py      # Soglie, fasce
│   │   ├── patterns.py       # Pattern signatures
│   │   ├── requests.py       # Supervision requests + routing LKP
│   │   ├── decisions.py      # Approve/reject
│   │   ├── ml.py             # ML pattern learning
│   │   ├── lookup.py         # (v8.0) Supervisione anomalie LKP
│   │   └── bulk.py           # (v8.0) Bulk approval per pattern
│   ├── tracking/             # (v8.2) Tracking operatore per ML
│   │   ├── __init__.py       # Esporta modulo
│   │   └── tracker.py        # Logica tracking + helper
│   └── anagrafica/           # (v8.2) Gestione anagrafica
│       ├── __init__.py       # Export unificato
│       ├── legacy.py         # Import CSV ministeriale
│       └── sync_ministero.py # Sync automatica da Open Data
├── routers/                   # API endpoints
└── utils/                     # Utility functions
```

### Frontend - Struttura Modulare

```
frontend/src/
├── api/                       # API client layer
├── common/                    # Shared UI components
├── components/                # Feature components
├── context/                   # React Context (v7.0)
│   ├── AuthContext.jsx       # Auth state
│   └── UIContext.jsx         # UI state
├── hooks/                     # React Query hooks (v7.0)
│   ├── useOrdini.js          # Ordini CRUD
│   ├── useAnomalies.js       # Anomalie CRUD
│   ├── useDashboard.js       # Dashboard stats
│   └── useTracciati.js       # Tracciati export
├── layout/                    # Layout components
└── pages/                     # Page components (v7.0)
    ├── OrdineDetail/         # Decomposed detail page
    │   ├── index.jsx
    │   ├── OrdineHeader.jsx
    │   ├── RigheTable.jsx
    │   ├── AnomalieTab.jsx
    │   └── hooks/
    └── Database/             # Decomposed database page
        ├── index.jsx
        ├── OrdiniTab.jsx
        ├── AnomalieTab.jsx
        └── hooks/
```

### Dipendenze Frontend (v7.0)

- **@tanstack/react-query**: Data fetching con cache
- **date-fns**: Date formatting

---

## Comandi

```bash
# Backend
cd backend && source venv/bin/activate && uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend && npm run dev
```

---

## Formato Tracciati EDI

### TO_T - TESTATA

| Pos | Campo | Tipo | Lung. | Obbl. | Descrizione |
|-----|-------|------|-------|-------|-------------|
| 1-10 | Vendor | String | 10 | Y | Codice produttore (es: HAL_FARVI) |
| 11-40 | VendorOrderNumber | String | 30 | Y | Numero ordine vendor |
| 41-60 | CustomerTraceabilityCode | String | 20 | Y | MIN_ID farmacia |
| 61-76 | VAT code | String | 16 | Y | Partita IVA cliente |
| 77-126 | CustomerName1 | String | 50 | Y | Ragione sociale |
| 127-176 | CustomerName2 | String | 50 | N | Ragione sociale (riga 2) |
| 177-226 | Address | String | 50 | N | Indirizzo |
| 227-236 | CodeCity | String | 10 | N | CAP |
| 237-286 | City | String | 50 | N | Città |
| 287-289 | Province | String | 3 | N | Provincia |
| 290-299 | OrderDate | Date | 10 | Y | Data ordine (GG/MM/AAAA) |
| 300-309 | EstDeliveryDate | Date | 10 | Y | Data consegna (GG/MM/AAAA) |
| 310-359 | AgentName | String | 50 | N | Nome agente |
| 360-369 | PaymentDate1 | Date | 10 | N | Data pagamento 1 |
| 370-372 | DelayPaymentDays | Integer | 3 | N | Giorni dilazione |
| 373-382 | PaymentDate2 | Date | 10 | N | Data pagamento 2 |
| 383-391 | PaymentAmmount2 | Float | 9 | N | Importo (7+2 dec) |
| 392-394 | DelayPaymentDays2 | Integer | 3 | N | Giorni dilazione 2 |
| 395-404 | PaymentDate3 | Date | 10 | N | Data pagamento 3 |
| 405-413 | PaymentAmmount3 | Float | 9 | N | Importo (7+2 dec) |
| 414-416 | DelayPaymentDays3 | Integer | 3 | N | Giorni dilazione 3 |
| 417-436 | OfferCodeCustomer | String | 20 | N | Codice offerta cliente |
| 437-456 | OfferCodeVendor | String | 20 | N | Codice offerta vendor |
| 457 | ForceCheck | String | 1 | N | S/N forza controllo |
| 458-657 | OrderAnnotation | String | 200 | Y | Note ordine |
| 658-857 | BOT_Annotation | String | 200 | Y | Note DDT |

### TO_D - DETTAGLIO

| Pos | Campo | Tipo | Lung. | Obbl. | Descrizione | Campo DB |
|-----|-------|------|-------|-------|-------------|----------|
| 1-30 | VendorNumberOrder | String | 30 | Y | Numero ordine | numero_ordine |
| 31-35 | LineNumber | Integer | 5 | Y | Numero riga (5 cifre) | n_riga |
| 36-56 | ProductCode | String | 21 | Y | Codice AIC (10 cifre + 11 spazi) | codice_aic |
| 57-62 | SalesQuantity | Integer | 6 | Y | Quantità venduta | q_venduta |
| 63-68 | QuantityDiscountPieces | Integer | 6 | N | Sempre 0 in produzione | - |
| 69-74 | QuantityFreePieces | Integer | 6 | N | **q_sconto_merce + q_omaggio** | q_sconto_merce + q_omaggio |
| 75-84 | ExtDeliveryDate | Date | 10 | N | Data consegna (GG/MM/AAAA) | data_consegna |
| 85-90 | Discount1 | Float | 6 | Y | Sconto % 1 (3+2 dec) | sconto_1 |
| 91-96 | Discount2 | Float | 6 | Y | Sconto % 2 | sconto_2 |
| 97-102 | Discount3 | Float | 6 | Y | Sconto % 3 | sconto_3 |
| 103-108 | Discount4 | Float | 6 | Y | Sconto % 4 | sconto_4 |
| 109-118 | NetVendorPrice | Float | 10 | Y | Prezzo netto (7+2 dec) | prezzo_netto |
| 119-128 | PriceToDiscount | Float | 10 | Y | Prezzo da scontare | prezzo_scontare |
| 129-133 | VAT | Float | 5 | N | Aliquota IVA (2+2 dec) | aliquota_iva |
| 134 | NetVATPrice | String | 1 | Y | S=Netto, N=IVA inclusa | scorporo_iva |
| 135-144 | PriceForFinalSale | Float | 10 | Y | Prezzo pubblico | prezzo_pubblico |
| 145-344 | NoteAllestimento | String | 200 | Y | Note allestimento | note_allestimento |

**NOTA PRODUCTCODE:** Schema originale prevede LineNumber 6 cifre + ProductCode 20 caratteri. Produzione usa LineNumber 5 cifre e ProductCode inizia a pos. 36 con AIC padding a 10 cifre.

---

## Regola Quantità Omaggio

**IMPORTANTE:** Nel tracciato TO_D di produzione:
- `QuantityDiscountPieces` (pos 63-68) = **sempre 0**
- `QuantityFreePieces` (pos 69-74) = **q_sconto_merce + q_omaggio**

Le quantità sconto merce vengono sommate alle quantità omaggio nel campo QuantityFreePieces. Il database le separa per tracciabilità interna.

---

## Esempio Tracciato Produzione

### TO_T:
```
HAL_FARVI 271717338                      10659              02169680697     F.CIA D'ALESSANDRO...
|--10---||---------30---------||-20-||---16---||---------50---------|...
 Vendor   VendorOrderNumber     MIN_ID  P.IVA    CustomerName1
```

### TO_D:
```
271717338                     000010034548141           00003600000000000007/11/2025...
|----------30---------|5|1|-------20-------|--6--|--6--|--6--|---10---|
VendorOrderNumber      Ln F  ProductCode     Qty   Disc  Free  Date
```

---

## Vendor Supportati

| Vendor | Stato | Particolarità |
|--------|-------|---------------|
| **ANGELINI** | Attivo | ID MIN diretto, sconti cascata (35+10+5), espositore 6 cifre |
| **BAYER** | Attivo | Formato SAP |
| **CODIFI** | Attivo | Multi-cliente (N ordini/PDF) |
| **CHIESI** | In attesa | Colonne verticali, escludere P.IVA 02944970348 |
| **MENARINI** | Attivo (v8.0) | Espositore con codice "--", chiusura su somma netto |
| **OPELLA** | In attesa | AIC 7-9 cifre |
| **DOC_GENERICI** | Attivo | Transfer Order via Grossisti, doppio indirizzo, NO prezzi |

Regole: `MD_Files/regole vendor/REGOLE_*.md`

### Vendor Detection (v6.2)

**IMPORTANTE:** La detection del vendor avviene ESCLUSIVAMENTE in base al contenuto del PDF.
Il nome del file viene IGNORATO per tutti i vendor.

DOC_GENERICI viene rilevato con score cumulativo >= 0.70:
- "TRANSFER ORDER Num." + 10 cifre = +0.25
- "Grossista" nelle prime 500 char = +0.15
- "Agente" + codice 5 cifre = +0.15
- "Ind.Fiscale" + "Ind.Consegna Merce" = +0.20
- "COD. A.I.C." presente = +0.15
- 5+ prodotti "DOC" = +0.10

---

## Database - Campi Quantità

| Campo DB | Tracciato EDI | Note |
|----------|---------------|------|
| q_venduta | SalesQuantity | Quantità venduta |
| q_sconto_merce | QuantityDiscountPieces | Pezzi sconto merce → omaggio |
| q_omaggio | QuantityFreePieces | Pezzi gratuiti → omaggio |
| q_evasa | - | Per gestione export parziali |
| **q_totale** | - | = q_venduta + q_sconto_merce + q_omaggio |

**Vista DB:** Usare `min_id` (NON `codice_ministeriale`) su `V_ORDINI_COMPLETI`

---

## Stati Ordine e Riga (v8.1)

### REGOLA FONDAMENTALE

**Lo stato dell'ORDINE (testata) e lo stato delle RIGHE (dettaglio) sono INDIPENDENTI.**

- Lo stato ordine è un RIEPILOGO, non modifica mai le righe
- Ogni riga mantiene il proprio stato basato su q_evasa/q_totale
- È possibile avere: ordine EVASO con righe ARCHIVIATO, ordine PARZ_EVASO con mix di stati

### Stati Riga (ORDINI_DETTAGLIO.stato_riga)

| Stato | Significato | Immutabile | Determinato da |
|-------|-------------|------------|----------------|
| **ARCHIVIATO** | Freezato manualmente | ✅ SI | Azione utente |
| **EVASO** | Completamente evaso | ✅ SI | q_evasa >= q_totale |
| **PARZIALE** | Parzialmente evaso | ❌ NO | q_evasa > 0 AND q_evasa < q_totale |
| **CONFERMATO** | Pronto per export | ❌ NO | Conferma utente |
| **ESTRATTO** | Stato iniziale | ❌ NO | Default |

### Stati Ordine (ORDINI_TESTATA.stato)

| Stato | Significato |
|-------|-------------|
| **ARCHIVIATO** | Ordine freezato |
| **EVASO** | Tutte righe completate (EVASO/ARCHIVIATO) |
| **PARZ_EVASO** | Alcune righe completate |
| **CONFERMATO** | Righe confermate, pronto export |
| **ANOMALIA** | Anomalie bloccanti da risolvere |
| **ESTRATTO** | Stato iniziale |

### Operazioni e Stati Protetti

| Operazione | ARCHIVIATO | EVASO | PARZIALE |
|------------|------------|-------|----------|
| CONFERMA singola | ❌ Bloccato | ❌ Bloccato | ✅ Permesso |
| CONFERMA TUTTO | ⏭️ Saltato | ⏭️ Saltato | ✅ Confermato |
| RIPRISTINA singola | ❌ Bloccato | ❌ Bloccato | ❌ Bloccato |
| RIPRISTINA TUTTO | ⏭️ Saltato | ⏭️ Saltato | ⏭️ Saltato |
| Generazione tracciato | ⏭️ Escluso | ⏭️ Escluso | ✅ Incluso |

### Calcolo q_totale

```
q_totale = q_venduta + q_sconto_merce + q_omaggio
```

Una riga è EVASO quando: `q_evasa >= q_totale AND q_totale > 0`

---

## Espositori (v8.0)

### Struttura
- `PARENT_ESPOSITORE` - Contenitore (FSTAND 24PZ, BANCO, EXPO, etc.)
- `CHILD_ESPOSITORE` - Prodotti contenuti + espositore vuoto (omaggio)
- Nel tracciato EDI: **solo parent**, child esclusi
- Nelle anomalie: **riepilogo child** incluso

### Regole per Vendor

| Vendor | Identificazione Parent | Chiusura | Note |
|--------|------------------------|----------|------|
| **ANGELINI** | Codice 6 cifre + keywords + XXPZ | `pezzi_accumulati >= pezzi_attesi` | Codice padding 500 (415734 → 500415734) |
| **MENARINI** | Codice `--` + keywords + **prezzo_netto > 0** | `somma_netto_child >= netto_parent` | Espositore vuoto: codice `--` + prezzo 0 |

### Keywords Espositore
`BANCO`, `DBOX`, `FSTAND`, `EXPO`, `DISPLAY`, `ESPOSITORE`, `CESTA`

### Esempio MENARINI
```
PARENT: AFTAMED EXPO BANCO 3+3  | --        | netto 32,89€
CHILD:  AFTAMED GEL 10ML        | 943303507 | netto 15,00€
CHILD:  AFTAMED EXPO BANCO      | --        | netto  0,00€  ← espositore vuoto
CHILD:  AFTAMED 20ML SPRAY      | 904733413 | netto 17,89€
                                  TOTALE:     32,89€ ✓
```

---

## Anomalie

### Anomalie GRAVI (Bloccanti)

Richiedono **supervisione obbligatoria** prima che l'ordine possa essere confermato.

| Codice | Tipo | Descrizione |
|--------|------|-------------|
| **ESP-A01** | ESPOSITORE | Pezzi child inferiori ad attesi (scostamento >= 20%) |
| **ESP-A02** | ESPOSITORE | Pezzi child superiori ad attesi (scostamento >= 20%) |
| **ESP-A03** | ESPOSITORE | Espositore senza righe child |
| **ESP-A04** | ESPOSITORE | Chiusura forzata per nuovo parent |
| **ESP-A05** | ESPOSITORE | Chiusura forzata a fine documento |
| **ESP-A06** | ESPOSITORE | Conflitto pattern ML vs estrazione (similarity < 50%) |
| **LKP-A01** | LOOKUP | Lookup score < 80% - verifica obbligatoria |
| **LKP-A02** | LOOKUP | Farmacia non trovata in anagrafica |
| **LKP-A04** | LOOKUP | P.IVA mismatch tra PDF e anagrafica (subentro/cambio proprietà) |
| **LKP-A05** | LOOKUP | Cliente non trovato in anagrafica clienti - deposito non determinabile |
| **EXT-A01** | ESTRAZIONE | Vendor non riconosciuto (estrattore generico) |

### Anomalie ORDINARIE (Non Bloccanti)

Segnalate ma non bloccano la conferma. Permettono modifica elementi anagrafici.

| Codice | Tipo | Descrizione |
|--------|------|-------------|
| **LKP-A03** | LOOKUP | Lookup score 80-95% - verifica consigliata |
| **DOCGEN-A08** | DOC_GENERICI | Quantità elevata (>200 pezzi) - verifica consigliata |

### Anomalie DOC_GENERICI (v6.2)

| Codice | Livello | Descrizione |
|--------|---------|-------------|
| **DOCGEN-A01** | INFO | Codice AIC non standard (integratori 9xx) - accettato |
| **DOCGEN-A03** | INFO | Assenza prezzi nel documento - comportamento normale |
| **DOCGEN-A04** | ERRORE/ATT | Totale pezzi non coerente (>5% = bloccante) |
| **DOCGEN-A08** | ERRORE/ATT | Quantità anomala (0 = bloccante, >200 = warning) |
| **DOCGEN-A09** | ERRORE | Riga prodotto malformata - bloccante |
| **DOCGEN-A10** | ERRORE | Footer mancante (multipagina) - bloccante |

### Fasce di Scostamento Espositore

| Fascia | Range | Bloccante |
|--------|-------|-----------|
| ZERO | 0% | No |
| BASSO | ±10% | No |
| MEDIO | ±20% | No |
| **ALTO** | ±50% | **Si** |
| **CRITICO** | >50% | **Si** |

### Soglie Lookup

| Score | Risultato |
|-------|-----------|
| >= 95% | OK - Nessuna anomalia |
| 80-95% | LKP-A03 - Anomalia ordinaria |
| < 80% | LKP-A01 - Anomalia grave (bloccante) |
| 0 (NESSUNO) | LKP-A02 - Anomalia grave (bloccante) |
| 50 (MIN_ID_PIVA_MISMATCH) | LKP-A04 - P.IVA diversa tra PDF e anagrafica (bloccante) |
| N/A (cliente non in anagrafica) | LKP-A05 - Cliente non trovato, deposito non determinabile (bloccante) |

---

## Convenzioni

- **Python:** snake_case, type hints
- **JS:** camelCase, JSX
- **Git:** `feat:`, `fix:`, `refactor:`
- **Encoding:** UTF-8, CRLF per tracciati

---

## Linee Guida Sviluppo - Uniformità e Razionalizzazione

### Principio Fondamentale

In fase di **refactoring** e **sviluppo**, cercare sempre la massima **uniformità** nella gestione di:
- Issues/bug
- Features
- Pattern di codice
- Componenti UI
- API endpoints

### Domanda Chiave: Generale o Specifico?

**Prima di implementare qualsiasi soluzione, chiedersi sempre:**

> *"Questa azione/soluzione è di tipo GENERALE o SPECIFICO?"*

| Tipo | Descrizione | Approccio |
|------|-------------|-----------|
| **GENERALE** | Problema/soluzione che riguarda più entità, vendor, o sezioni | Creare soluzione riutilizzabile, pattern condiviso, componente comune |
| **SPECIFICO** | Problema/soluzione isolata a un singolo caso | Implementare soluzione mirata, documentare eccezione |

### Esempi Pratici

| Scenario | Tipo | Soluzione |
|----------|------|-----------|
| Validazione AIC | GENERALE | Funzione `isValidAic()` riutilizzabile ovunque |
| Formato AIC vendor X con prefisso | SPECIFICO | Logica nel solo estrattore del vendor |
| Gestione errori API | GENERALE | Interceptor axios centralizzato |
| Errore specifico endpoint | SPECIFICO | Try/catch locale con messaggio dedicato |
| Audit trail modifiche | GENERALE | Tabella `audit_modifiche` + helper `log_modifica()` |
| Log specifico per debug | SPECIFICO | Console.log temporaneo (da rimuovere) |

### Checklist Pre-Implementazione

1. ✅ Esiste già una soluzione simile nel codebase?
2. ✅ Questo pattern si ripeterà altrove?
3. ✅ Posso generalizzare senza over-engineering?
4. ✅ Se specifico: è documentata l'eccezione?

### Aspetti da Uniformare

- **Backend:** Helper functions, error handling, response format, logging
- **Frontend:** Componenti UI, hooks, gestione stato, chiamate API
- **Database:** Naming conventions, indici, audit trail
- **API:** Struttura endpoints, parametri, response schema
