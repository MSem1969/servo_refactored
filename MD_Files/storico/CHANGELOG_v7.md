# Changelog TO_EXTRACTOR v6.2 -> v7.0

## Data: 2026-01-10

---

## Riepilogo

Refactoring full-stack con focus su modularizzazione e modernizzazione.

### Obiettivi Raggiunti

- Backend: Decomposizione servizi monolitici in package modulari
- Frontend: Implementazione React Query + Context API
- Frontend: Decomposizione pagine monolitiche (1500+ LOC) in componenti riutilizzabili
- Mantenimento retrocompatibilita tramite deprecation wrappers

---

## Backend Changes

### FASE 1-3: Riorganizzazione Servizi

#### services/extraction/ (NEW)
Unificazione estrattori PDF in package modulare:
- `base.py` - BaseExtractor class
- `detector.py` - Vendor detection logic
- `vendors/` - Estrattori specifici per vendor

#### services/export/ (NEW)
Decomposizione `tracciati.py` (1106 LOC):
- `formatters/common.py` - Funzioni formattazione EDI comuni
- `formatters/to_t.py` - Generazione linee TO_T (857 chars)
- `formatters/to_d.py` - Generazione linee TO_D (344 chars)
- `validators.py` - Validazione campi tracciati
- `queries.py` - Query database per tracciati
- `generator.py` - Logica principale generazione

#### services/supervision/ (NEW)
Decomposizione `supervisione.py` (861 LOC):
- `constants.py` - Soglie, fasce scostamento
- `patterns.py` - Pattern signature calculations
- `requests.py` - Gestione richieste supervisione
- `decisions.py` - Approvazione/rifiuto/modifica
- `ml.py` - Machine learning pattern management
- `queries.py` - Query per supervisione

#### Deprecation Wrappers
I file originali (`tracciati.py`, `supervisione.py`) mantengono import per retrocompatibilita ma emettono DeprecationWarning.

### FASE 6: Data Lineage & Audit System (v7.0)

Implementazione sistema completo di tracciabilità dati per garantire integrità e responsabilità.

#### Nuove Colonne ORDINI_TESTATA
Campi estratti (immutabili dopo estrazione):
- `ragione_sociale_1_estratta` - Ragione sociale originale da PDF
- `ragione_sociale_2_estratta` - Seconda riga ragione sociale
- `indirizzo_estratto` - Indirizzo originale da PDF
- `cap_estratto` - CAP originale
- `citta_estratta` - Città originale
- `provincia_estratta` - Provincia originale
- `data_ordine_estratta` - Data ordine originale
- `data_consegna_estratta` - Data consegna originale

Campi tracciabilità:
- `fonte_anagrafica` - Origine dati correnti: `ESTRATTO`, `LOOKUP_FARMACIA`, `LOOKUP_PARAFARMACIA`, `MANUALE`
- `data_modifica_anagrafica` - Timestamp ultima modifica anagrafica
- `operatore_modifica_anagrafica` - Username operatore modifica

#### Nuove Colonne ORDINI_DETTAGLIO
- `descrizione_estratta` - Descrizione originale da PDF
- `fonte_codice_aic` - Origine codice: `ESTRATTO`, `NORMALIZZATO`, `MANUALE`
- `fonte_quantita` - Origine quantità: `ESTRATTO`, `SUPERVISIONE`, `MANUALE`
- `operatore_ultima_modifica` - Username ultima modifica
- `data_ultima_modifica` - Timestamp ultima modifica

#### Nuova Tabella AUDIT_MODIFICHE
Tabella centrale per audit trail completo:

```sql
CREATE TABLE AUDIT_MODIFICHE (
    id_audit INTEGER PRIMARY KEY,
    entita TEXT NOT NULL,           -- TESTATA, DETTAGLIO, ANOMALIA, SUPERVISIONE
    id_entita INTEGER NOT NULL,
    id_testata INTEGER,             -- Riferimento ordine
    campo_modificato TEXT NOT NULL,
    valore_precedente TEXT,
    valore_nuovo TEXT,
    fonte_modifica TEXT NOT NULL,   -- ESTRAZIONE, LOOKUP_AUTO, LOOKUP_MANUALE, etc.
    id_operatore INTEGER,
    username_operatore TEXT,
    motivazione TEXT,
    id_sessione TEXT,               -- Per raggruppare modifiche correlate
    timestamp TEXT DEFAULT (datetime('now'))
);
```

Fonti modifica supportate:
- `ESTRAZIONE` - Prima estrazione da PDF
- `LOOKUP_AUTO` - Lookup automatico farmacia
- `LOOKUP_MANUALE` - Assegnazione manuale farmacia
- `SUPERVISIONE` - Modifica da supervisione espositore
- `CONFERMA_RIGA` - Conferma quantità da evadere
- `VALIDAZIONE` - Validazione ordine
- `MODIFICA_MANUALE` - Modifica manuale operatore
- `ARCHIVIAZIONE` - Archiviazione ordine/riga
- `RIPRISTINO` - Ripristino da archiviazione
- `SISTEMA` - Operazione automatica sistema

#### Nuove Viste
- `V_AUDIT_COMPLETO` - Storico modifiche con join a ordini e operatori
- `V_FONTE_DATI_TESTATA` - Confronto dati estratti vs correnti con flag modifiche

#### Nuove Funzioni Utility (database.py)
- `log_modifica()` - Registra singola modifica
- `log_modifiche_batch()` - Registra multiple modifiche con stesso id_sessione
- `get_audit_by_testata()` - Storico modifiche per ordine
- `get_audit_by_dettaglio()` - Storico modifiche per riga
- `get_audit_by_operatore()` - Storico modifiche per operatore
- `get_fonte_dati_testata()` - Confronto estratto vs corrente

#### Integrazione Servizi
- `pdf_processor.py` - Popola automaticamente campi `*_estratta` durante estrazione
- `lookup.py` - Registra audit quando lookup modifica header ordine

---

## Frontend Changes

### FASE 4.1: Dipendenze Moderne

Aggiunte dipendenze:
- `@tanstack/react-query` - Data fetching con cache automatica
- `date-fns` - Date formatting

Configurazione in `main.jsx`:
```javascript
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5,  // 5 minuti
      cacheTime: 1000 * 60 * 30, // 30 minuti
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});
```

### FASE 4.2: Context API

Nuovi context per stato globale:
- `context/AuthContext.jsx` - Autenticazione, utente corrente, permessi
- `context/UIContext.jsx` - Stato UI (sidebar, modals, notifications)

### FASE 4.3: React Query Hooks

Nuovi hooks per data fetching:

#### hooks/useOrdini.js
- `useOrdini(filters)` - Lista ordini
- `useOrdine(id)` - Dettaglio ordine
- `useOrdineRighe(id)` - Righe ordine
- `useConfermaRiga()` - Mutation conferma riga
- `useValidaEGeneraTracciato()` - Mutation validazione
- `useBatchUpdateStato()` - Mutation batch

#### hooks/useAnomalies.js
- `useAnomalies(filters)` - Lista anomalie
- `useAnomalieByOrdine(id)` - Anomalie per ordine
- `useRisolviAnomalia()` - Mutation risoluzione
- `useBatchRisolviAnomalie()` - Mutation batch

#### hooks/useDashboard.js
- `useDashboardStats()` - Statistiche dashboard
- `useOrdiniRecenti()` - Ordini recenti
- `useAnomalieCritiche()` - Anomalie critiche

#### hooks/useTracciati.js
- `useOrdiniProntiExport()` - Ordini pronti
- `useTracciatiStorico()` - Storico export
- `useGeneraTracciati()` - Mutation generazione

### FASE 4.4: Decomposizione OrdineDetailPage

Da 1510 LOC a componenti modulari:

```
pages/OrdineDetail/
├── index.jsx              # Container (~200 LOC)
├── OrdineHeader.jsx       # Header ordine + stato
├── RigheTable.jsx         # Tabella righe + editing inline
├── RigaEditModal.jsx      # Modal modifica riga
├── AnomalieTab.jsx        # Tab anomalie + supervisioni
├── PdfModal.jsx           # Visualizzatore PDF
├── utils.js               # Helper functions
└── hooks/
    └── useOrdineDetail.js # Custom hook logica
```

### FASE 4.5: Decomposizione DatabasePage

Da 1237 LOC a componenti modulari:

```
pages/Database/
├── index.jsx              # Container (~250 LOC)
├── StatsCards.jsx         # Cards statistiche
├── OrdiniTab.jsx          # Tab ordini + filtri
├── AnomalieTab.jsx        # Tab anomalie
├── DeliveryBadge.jsx      # Badge urgenza consegna
├── utils.js               # Helper functions
└── hooks/
    └── useDatabasePage.js # Custom hook logica
```

---

## Breaking Changes

Nessuno. Tutte le API rimangono compatibili.

---

## Migration Guide

### Backend
I vecchi import continuano a funzionare ma emettono warning:
```python
# Vecchio (deprecated)
from app.services.tracciati import valida_e_genera_tracciato

# Nuovo (raccomandato)
from app.services.export import valida_e_genera_tracciato
```

### Frontend
Gli import delle pagine cambiano:
```javascript
// Vecchio
import OrdineDetailPage from './pages/OrdineDetailPage';
import DatabasePage from './pages/DatabasePage';

// Nuovo
import OrdineDetailPage from './pages/OrdineDetail';
import DatabasePage from './pages/Database';
```

---

## Metrics

### Lines of Code

| Componente | Prima | Dopo | Delta |
|------------|-------|------|-------|
| OrdineDetailPage.jsx | 1510 | ~200 (container) | -87% |
| DatabasePage.jsx | 1237 | ~250 (container) | -80% |
| tracciati.py | 1106 | wrapper | modularizzato |
| supervisione.py | 861 | wrapper | modularizzato |

### File Structure

| Metrica | Prima | Dopo |
|---------|-------|------|
| Backend packages | 5 | 8 |
| Frontend hooks | 1 | 5 |
| Componenti riutilizzabili | ~20 | ~35 |

---

## Testing

- Build frontend: OK
- Import backend: OK
- Retrocompatibilita: OK
