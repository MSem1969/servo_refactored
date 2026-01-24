# PIANO DI REFACTORING v11 - SERVO_RF

**Data**: 2026-01-24
**Repository**: `/home/jobseminara/servo_rf`
**Obiettivo**: Unificazione, centralizzazione, riduzione codice duplicato

---

## METODOLOGIA DI LAVORO

### REGOLA FONDAMENTALE: STEP BY STEP

> **OGNI MODIFICA VA TESTATA IMMEDIATAMENTE PRIMA DI PASSARE AL TASK SUCCESSIVO**

1. **Un task alla volta** - Non iniziare il task N+1 finché il task N non è completato E testato
2. **Test immediato** - Dopo ogni modifica, verificare che:
   - L'applicazione si avvia senza errori
   - La funzionalità modificata funziona correttamente
   - Le funzionalità correlate non sono state compromesse
3. **Commit incrementali** - Ogni task completato = un commit (locale, no push)
4. **Rollback rapido** - Se un test fallisce, rollback immediato prima di procedere

### AGENTI DI TEST E VALIDAZIONE

Per garantire qualità e coerenza, creeremo agenti Claude specializzati:

#### Agente: `test-runner`
**Scopo**: Eseguire test automatici dopo ogni modifica
**Responsabilità**:
- Verificare che il backend si avvii (`uvicorn app.main:app`)
- Verificare che il frontend compili (`npm run build`)
- Eseguire test esistenti (`pytest`, `npm test`)
- Riportare errori in modo strutturato

#### Agente: `ui-validator`
**Scopo**: Validare UX/UI e identificare elementi non funzionanti
**Responsabilità**:
- Inventariare TUTTI i button presenti nel frontend
- Verificare che ogni button abbia un handler onClick funzionante
- Identificare button "morti" (senza funzione) → DA ELIMINARE
- Verificare coerenza visiva dei componenti

#### Agente: `button-auditor`
**Scopo**: Audit completo dei button nel codebase
**Output atteso**:
```
BUTTON AUDIT REPORT
├── Button con onClick valido: [lista]
├── Button senza onClick: [lista] → ELIMINARE
├── Button con onClick vuoto/placeholder: [lista] → COMPLETARE o ELIMINARE
└── Button duplicati (stesso scopo): [lista] → UNIFICARE
```

---

## PRINCIPI GUIDA

1. **Unificazione UI**: Stesso modal per stesse funzionalità in contesti diversi
2. **Centralizzazione logica DB**: Ogni tabella modificata da UN SOLO punto
3. **Librerie interne**: Funzioni riutilizzabili invece di duplicazioni
4. **Tracciabilità**: Audit trail consistente su tutte le modifiche
5. **Preparazione futura**: Struttura pronta per watermark e OCR
6. **Zero button morti**: Ogni elemento UI deve avere una funzione

---

## TIER 0 - PREPARAZIONE (Prima di tutto)

### 0.1 Audit Button Frontend

**PRIMA DI QUALSIASI REFACTORING**, eseguire audit completo dei button.

**Azione**:
1. Lanciare agente `button-auditor` su `frontend/src/`
2. Generare report di tutti i button
3. Marcare per eliminazione quelli senza funzione
4. Documentare quelli da completare

**Comando agente**:
```
Cerca tutti i <button>, <Button>, onClick in frontend/src/
Per ogni occorrenza verifica:
- Ha onClick definito?
- onClick chiama una funzione reale?
- La funzione fa qualcosa di utile?
Output: lista button con stato (FUNZIONANTE/MORTO/INCOMPLETO)
```

### 0.2 Git Commit Baseline

**Azione**:
```bash
cd /home/jobseminara/servo_rf
git add -A
git commit -m "feat: baseline v10.6 - pre-refactoring snapshot"
```

**NON fare push** (come richiesto)

---

## TIER 1 - CRITICO (Priorità Massima)

### 1.1 Centralizzare Propagazione AIC

**Problema**: Propagazione AIC implementata in 3+ punti con logica duplicata
**Impatto**: Doppio UPDATE DB, inconsistenza audit trail

**File da modificare**:
- `backend/app/services/supervision/propagazione_aic.py` - MANTENERE come unico punto
- `backend/app/services/supervision/aic.py` - RIMUOVERE logica duplicata
- `backend/app/routers/anomalie.py` - RIMUOVERE logica, chiamare solo service
- `backend/app/routers/supervisione/aic.py` - RIMUOVERE logica, chiamare solo service

**Soluzione**:
```python
# services/supervision/aic_unified.py (NUOVO)
class AICPropagator:
    """Unico punto di propagazione AIC"""

    def propaga(self, codice_aic: str, livello: str, id_dettaglio: int,
                operatore: str, note: str = None) -> PropagationResult:
        """Entry point unico per tutte le propagazioni AIC"""

    def risolvi_da_anomalia(self, id_anomalia: int, codice_aic: str,
                            livello: str, operatore: str) -> ResolutionResult:
        """Chiamato da /anomalie/{id}/correggi-aic"""

    def risolvi_da_supervisione(self, id_supervisione: int, codice_aic: str,
                                 livello: str, operatore: str) -> ResolutionResult:
        """Chiamato da /supervisione/aic/{id}/risolvi"""
```

**TEST DOPO COMPLETAMENTO**:
- [ ] Backend avvia senza errori
- [ ] Endpoint `/anomalie/{id}/correggi-aic` funziona
- [ ] Endpoint `/supervisione/aic/{id}/risolvi` funziona
- [ ] Propagazione AIC aggiorna correttamente `ordini_dettaglio`

**Stima**:
- LOC da rimuovere: ~400
- LOC nuovo service: ~200
- File modificati: 4

---

### 1.2 Spostare Logica DB dai Router ai Service

**Problema**: Logica di modifica DB direttamente nei router (bypassa service/repository)
**Impatto**: Nessun pattern centralizzato, audit trail inconsistente

**File da modificare**:
- `backend/app/routers/ordini.py` - RIMUOVERE UPDATE diretti (linee 725-887)
- `backend/app/routers/anomalie.py` - RIMUOVERE UPDATE diretti (linee 590-594, 967-990)
- `backend/app/services/orders/commands.py` - AGGIUNGERE funzioni archiviazione

**Soluzione**:
```python
# services/orders/commands.py (ESTENDERE)
def archivia_ordine(id_testata: int, operatore: str) -> ArchiviazioneResult:
    """Archivia ordine + tutte le righe non evase"""

def archivia_riga(id_dettaglio: int, operatore: str) -> ArchiviazioneResult:
    """Archivia singola riga + aggiorna stato ordine"""
```

**TEST DOPO COMPLETAMENTO**:
- [ ] Archiviazione ordine funziona da UI
- [ ] Archiviazione riga funziona da UI
- [ ] Stato ordine/righe aggiornato correttamente
- [ ] Log operazioni registrato

**Stima**:
- LOC da spostare: ~300
- File modificati: 3

---

### 1.3 Unificare Tabelle Supervisione (Database)

**Problema**: 5 tabelle supervisione_* con schema quasi identico
**Impatto**: Manutenzione 5x, query duplicate, indici ridondanti

**Migrazioni da creare**:
- `backend/migrations/v11_supervisione_unificata.sql`

**Schema proposto**:
```sql
CREATE TABLE supervisione_unificata (
    id_supervisione SERIAL PRIMARY KEY,
    tipo_supervisione VARCHAR(20) NOT NULL
        CHECK (tipo_supervisione IN ('AIC', 'LISTINO', 'PREZZO', 'LOOKUP', 'ESPOSITORE')),
    id_testata INTEGER REFERENCES ordini_testata(id_testata) ON DELETE CASCADE,
    id_anomalia INTEGER REFERENCES anomalie(id_anomalia) ON DELETE SET NULL,
    id_dettaglio INTEGER REFERENCES ordini_dettaglio(id_dettaglio) ON DELETE SET NULL,
    codice_anomalia VARCHAR(20),
    vendor VARCHAR(50),

    -- Dati comuni
    stato VARCHAR(20) DEFAULT 'PENDING'
        CHECK (stato IN ('PENDING', 'APPROVED', 'REJECTED', 'MODIFIED')),
    operatore VARCHAR(100),
    timestamp_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    timestamp_decisione TIMESTAMP,
    note TEXT,

    -- Pattern ML
    pattern_signature TEXT,

    -- Dati specifici per tipo (JSONB per flessibilità)
    payload JSONB DEFAULT '{}'
);

-- Indici ottimizzati (4 invece di 15+)
CREATE INDEX idx_sup_tipo_stato ON supervisione_unificata(tipo_supervisione, stato);
CREATE INDEX idx_sup_testata ON supervisione_unificata(id_testata);
CREATE INDEX idx_sup_pattern ON supervisione_unificata(pattern_signature) WHERE pattern_signature IS NOT NULL;
CREATE INDEX idx_sup_payload ON supervisione_unificata USING GIN(payload);
```

**TEST DOPO COMPLETAMENTO**:
- [ ] Migrazione eseguita senza errori
- [ ] Query supervisione funzionano
- [ ] Vista supervisione in frontend carica correttamente
- [ ] Approva/Rifiuta funziona per tutti i tipi

**Stima**:
- Tabelle da deprecare: 5
- Indici da rimuovere: ~15
- Query da aggiornare: ~30

---

### 1.4 Eliminare Button Morti (Frontend)

**Problema**: Button senza funzione identificati in audit
**Impatto**: UX confusa, codice morto

**Azione**: Basandosi sul report dell'audit (0.1), eliminare tutti i button senza onClick funzionante.

**TEST DOPO COMPLETAMENTO**:
- [ ] Nessun button senza handler nel codebase
- [ ] UI funziona senza errori console
- [ ] Tutti i button rimanenti hanno azione visibile

---

## TIER 2 - ALTO (Priorità Alta)

### 2.1 Unificare Modal Correzione AIC (Frontend)

**Problema**: Correzione AIC implementata 2x (AnomaliaDetailModal vs AssegnaAicModal)
**Impatto**: Logica duplicata, UI inconsistente, manutenzione doppia

**File da modificare**:
- `frontend/src/components/AnomaliaDetailModal.jsx` - RIMUOVERE AicCorrectionSection
- `frontend/src/pages/Supervisione/AssegnaAicModal.jsx` - ESTENDERE per supportare entrambi i contesti
- `frontend/src/components/AicAssignmentModal.jsx` - NUOVO componente unificato

**Soluzione**:
```jsx
// components/AicAssignmentModal.jsx (NUOVO)
export function AicAssignmentModal({
  isOpen,
  onClose,
  mode,           // 'ANOMALIA' | 'SUPERVISIONE_SINGOLA' | 'SUPERVISIONE_BULK'
  anomalia,       // per mode ANOMALIA
  supervisione,   // per mode SUPERVISIONE_*
  operatore,
  onSuccess
}) {
  // Logica unificata con tutte le features:
  // - Ricerca AIC con suggerimenti
  // - Livelli propagazione (ORDINE/GLOBALE)
  // - Pattern ML info
  // - Note
}
```

**TEST DOPO COMPLETAMENTO**:
- [ ] Modal AIC funziona da AnomaliaDetailModal
- [ ] Modal AIC funziona da SupervisionePage
- [ ] Propagazione livelli funziona
- [ ] Ricerca AIC funziona

**Stima**:
- LOC da rimuovere: ~500 (da AnomaliaDetailModal)
- LOC nuovo componente: ~300
- File modificati: 3

---

### 2.2 Usare ModalBase Ovunque (Frontend)

**Problema**: ModalBase e Modal esistono ma NON sono usati (7 overlay custom)
**Impatto**: UI inconsistente, animazioni mancanti, accessibilità

**File da modificare**:
- `frontend/src/pages/Supervisione/ArchiviazioneListinoModal.jsx`
- `frontend/src/pages/Supervisione/CorrezioneLisinoModal.jsx`
- `frontend/src/pages/OrdineDetail/PdfModal.jsx`
- `frontend/src/pages/OrdineDetail/RigaEditModal.jsx`
- `frontend/src/components/AnomaliaDetailModal.jsx`

**Pattern da applicare**:
```jsx
// PRIMA (overlay custom)
<div className="fixed inset-0 bg-black/50 z-50 flex">
  <div className="bg-white rounded-xl...">

// DOPO (usando ModalBase)
<ModalBase
  isOpen={isOpen}
  onClose={onClose}
  title="Titolo"
  size="lg"
>
  {children}
</ModalBase>
```

**TEST DOPO COMPLETAMENTO** (per ogni modal):
- [ ] Modal si apre correttamente
- [ ] ESC chiude il modal
- [ ] Click overlay chiude il modal
- [ ] Animazioni funzionano
- [ ] Contenuto renderizza correttamente

**Stima**:
- File da modificare: 7
- LOC da rimuovere (overlay code): ~100
- Beneficio: Consistenza UI + animazioni + ESC handling

---

### 2.3 Creare Hooks per Supervisione (Frontend)

**Problema**: 50% delle operazioni supervisione senza hook (chiamate API dirette)
**Impatto**: try/catch + alert() scatter, nessuna invalidation centralizzata

**File da creare**:
- `frontend/src/hooks/useSupervisione.js`

**Hooks da implementare**:
```javascript
// hooks/useSupervisione.js (NUOVO)
export function useApprovaSupervisione() {
  return useMutation({
    mutationFn: ({ id, operatore, note }) => supervisioneApi.approva(id, operatore, note),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['supervisione'] });
      queryClient.invalidateQueries({ queryKey: ['anomalie'] });
    }
  });
}

export function useRifiutaSupervisione() { ... }
export function useApprovaBulk() { ... }
export function useRifiutaBulk() { ... }
export function useRisolviAic() { ... }
export function useRisolviLookup() { ... }
export function useCorreggiListino() { ... }
```

**TEST DOPO COMPLETAMENTO**:
- [ ] Tutti i nuovi hooks funzionano
- [ ] Invalidation aggiorna correttamente le liste
- [ ] Errori gestiti uniformemente

**Stima**:
- Hooks da creare: 8
- LOC nuovo file: ~200
- Beneficio: Invalidation centralizzata, error handling uniforme

---

### 2.4 Centralizzare Risoluzione Anomalie (Backend)

**Problema**: 4 endpoint diversi per risolvere anomalie con logiche separate
**Impatto**: Confusione percorsi, inconsistenza

**File da modificare**:
- `backend/app/services/anomalies/resolver.py` - NUOVO service unificato
- `backend/app/routers/anomalie.py` - Semplificare endpoint

**Soluzione**:
```python
# services/anomalies/resolver.py (NUOVO)
class AnomaliaResolver:
    """Risoluzione centralizzata anomalie con routing per tipo"""

    def risolvi(self, id_anomalia: int, params: ResolutionParams) -> ResolutionResult:
        anomalia = self._get_anomalia(id_anomalia)

        # Routing basato su tipo/codice
        if anomalia.codice.startswith('AIC-'):
            return self._risolvi_aic(anomalia, params)
        elif anomalia.codice.startswith('LKP-A05'):
            return self._risolvi_deposito(anomalia, params)
        elif anomalia.codice.startswith('ESP-'):
            return self._risolvi_espositore(anomalia, params)
        else:
            return self._risolvi_generico(anomalia, params)
```

**TEST DOPO COMPLETAMENTO**:
- [ ] Risoluzione anomalie AIC funziona
- [ ] Risoluzione anomalie LKP-A05 funziona
- [ ] Risoluzione anomalie ESP funziona
- [ ] Risoluzione anomalie generiche funziona

**Stima**:
- LOC nuovo service: ~250
- Endpoint da consolidare: 4 → 1
- Beneficio: Single entry point, logica chiara

---

## TIER 3 - MEDIO (Priorità Media)

### 3.1 Estrarre RigaEditForm Component (Frontend)

**Problema**: Editing riga duplicato in RigaEditModal e AnomaliaDetailModal
**Impatto**: Logica form duplicata

**File da creare**:
- `frontend/src/components/RigaEditForm.jsx`

**TEST DOPO COMPLETAMENTO**:
- [ ] RigaEditForm funziona in RigaEditModal
- [ ] RigaEditForm funziona in AnomaliaDetailModal
- [ ] Validazione form funziona

**Stima**:
- LOC da estrarre: ~150
- File che useranno il componente: 2

---

### 3.2 Consolidare URLSearchParams Building (Frontend)

**Problema**: Pattern URLSearchParams ripetuto 4x in file API diversi
**Impatto**: Codice duplicato

**File da modificare**:
- `frontend/src/api/ordini.js` - Usare buildQueryParams
- `frontend/src/api/anomalie.js` - Usare buildQueryParams
- `frontend/src/api/crm.js` - Usare buildQueryParams

**TEST DOPO COMPLETAMENTO**:
- [ ] Tutte le chiamate API con filtri funzionano
- [ ] Nessuna duplicazione URLSearchParams

**Stima**:
- LOC da rimuovere: ~60
- Beneficio: Single source of truth

---

### 3.3 Consolidare Pattern Learning Tables (Database)

**Problema**: 3 tabelle criteri_ordinari_* con schema simile
**Impatto**: Query ML duplicate

**Migrazione**:
```sql
CREATE TABLE criteri_ordinari_pattern (
    pattern_id SERIAL PRIMARY KEY,
    tipo_pattern VARCHAR(20) CHECK (tipo_pattern IN ('AIC', 'LISTINO', 'LOOKUP')),
    vendor VARCHAR(50) NOT NULL,
    pattern_signature TEXT NOT NULL,
    count_approvazioni INTEGER DEFAULT 0,
    is_ordinario BOOLEAN DEFAULT FALSE,
    payload JSONB DEFAULT '{}',
    timestamp_creazione TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    timestamp_ultimo_uso TIMESTAMP,
    UNIQUE(tipo_pattern, pattern_signature)
);
```

**TEST DOPO COMPLETAMENTO**:
- [ ] Migrazione eseguita
- [ ] Pattern ML funziona per AIC
- [ ] Pattern ML funziona per LISTINO
- [ ] Pattern ML funziona per LOOKUP

**Stima**:
- Tabelle da deprecare: 3
- Query da aggiornare: ~15

---

### 3.4 Ottimizzare Indici operatore_azioni_log (Database)

**Problema**: 10 indici su tabella INSERT-heavy
**Impatto**: Performance degradata su INSERT

**Azione**: Ridurre da 10 a 4 indici selettivi

**TEST DOPO COMPLETAMENTO**:
- [ ] INSERT performance migliorata
- [ ] Query di analisi ancora funzionanti

---

## TIER 4 - BASSO (Futuro)

### 4.1 Documentazione Schema Database
### 4.2 Test E2E per Modal Flows
### 4.3 Storybook per Componenti UI
### 4.4 Migrazione completa ad Alembic

---

## DIPENDENZE TRA TASK

```
TIER 0.1 (Button Audit) ─────────────────────────────────────────────┐
         │                                                            │
         ▼                                                            │
TIER 0.2 (Git baseline) ─────────────────────────────────────────────┤
                                                                      │
TIER 1.1 (AIC Propagation) ──────┬────────────────────────────────────┤
                                 │                                    │
TIER 1.2 (Router → Service) ─────┼────────────────────────────────────┤
                                 │                                    │
                                 ▼                                    │
TIER 2.4 (Anomalia Resolver) ────┼────────────────────────────────────┤
                                 │                                    │
TIER 1.3 (DB Supervisione) ──────┴───► TIER 2.3 (Hooks Supervisione)  │
                                                      │               │
TIER 1.4 (Button morti) ◄─────────────────────────────┘               │
                                                                      │
TIER 2.1 (AIC Modal) ◄────────────────────────────────────────────────┘
         │
         ▼
TIER 2.2 (ModalBase) ────────────────────────────────────────────────┐
         │                                                            │
         ▼                                                            │
TIER 3.1 (RigaEditForm) ◄─────────────────────────────────────────────┘
```

---

## WORKFLOW DI ESECUZIONE

### Per ogni TASK:

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. LEGGI il task e comprendi cosa modificare                    │
├─────────────────────────────────────────────────────────────────┤
│ 2. IMPLEMENTA le modifiche                                      │
├─────────────────────────────────────────────────────────────────┤
│ 3. TESTA immediatamente:                                        │
│    □ Backend avvia? (uvicorn app.main:app --reload)            │
│    □ Frontend compila? (npm run build)                          │
│    □ Funzionalità modificata funziona?                          │
│    □ Funzionalità correlate OK?                                 │
├─────────────────────────────────────────────────────────────────┤
│ 4. TEST FALLITO? → Rollback immediato, fix, ri-testa           │
├─────────────────────────────────────────────────────────────────┤
│ 5. TEST OK? → Commit locale                                     │
│    git add -A && git commit -m "refactor: [descrizione task]"   │
├─────────────────────────────────────────────────────────────────┤
│ 6. PASSA al task successivo                                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## STIMA IMPATTO TOTALE

| Metrica | Prima | Dopo | Riduzione |
|---------|-------|------|-----------|
| **LOC Backend duplicati** | ~1200 | ~200 | -83% |
| **LOC Frontend duplicati** | ~800 | ~200 | -75% |
| **Tabelle supervisione** | 5 | 1 | -80% |
| **Indici DB** | ~80 | ~50 | -37% |
| **Endpoint anomalie** | 4 | 1 | -75% |
| **Modal implementazioni AIC** | 2 | 1 | -50% |
| **Overlay custom** | 7 | 0 | -100% |
| **Button morti** | ? | 0 | -100% |

---

## CHECKLIST ESECUZIONE

### TIER 0 (Preparazione - OBBLIGATORIO)
- [ ] 0.1 Audit button frontend → Report generato
- [ ] 0.2 Git commit baseline

### TIER 1 (Eseguire per primo)
- [ ] 1.1 Centralizzare propagazione AIC → TEST OK
- [ ] 1.2 Spostare logica DB dai router → TEST OK
- [ ] 1.3 Creare migrazione supervisione_unificata → TEST OK
- [ ] 1.4 Eliminare button morti → TEST OK

### TIER 2 (Dopo TIER 1)
- [ ] 2.1 Creare AicAssignmentModal unificato → TEST OK
- [ ] 2.2 Applicare ModalBase a tutti i modal → TEST OK
- [ ] 2.3 Creare hooks useSupervisione → TEST OK
- [ ] 2.4 Creare AnomaliaResolver centralizzato → TEST OK

### TIER 3 (Dopo TIER 2)
- [ ] 3.1 Estrarre RigaEditForm → TEST OK
- [ ] 3.2 Consolidare URLSearchParams → TEST OK
- [ ] 3.3 Unificare criteri_ordinari_* → TEST OK
- [ ] 3.4 Ottimizzare indici tracking → TEST OK

---

## NOTE OPERATIVE

1. **NO PUSH su GitHub** - Lavoro solo locale come richiesto
2. **Test incrementali** - Verificare dopo ogni TIER
3. **Backup DB** prima di migrazioni schema
4. **Docker** - Considerare per ambiente isolato PostgreSQL
5. **Agenti test** - Usare per validazione automatica

---

*Piano generato da analisi automatica con agenti Claude - 2026-01-24*
