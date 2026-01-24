# ANALISI COLLEGAMENTI MANCANTI - TO_EXTRACTOR v6.2

> Report dei problemi di collegamento Frontend ↔ Backend

---

## 1. BOTTONI FRONTEND NON COLLEGATI CORRETTAMENTE AL BACKEND

### 1.1 ERRORE CRITICO: Nome funzione errato

| File | Linea | Problema | Soluzione |
|------|-------|----------|-----------|
| `TracciatiPage.jsx` | 180 | Chiama `tracciatiApi.eliminaFile(true)` | La funzione in `api.js` si chiama `deleteFiles()` non `eliminaFile()` |

**Codice errato:**
```javascript
// TracciatiPage.jsx:180
const res = await tracciatiApi.eliminaFile(true);
```

**Codice corretto:**
```javascript
const res = await tracciatiApi.deleteFiles();
```

---

### 1.2 FUNZIONI BACKEND MANCANTI (Bottoni con TODO)

| File | Linea | Bottone | Problema |
|------|-------|---------|----------|
| `SettingsPage.jsx` | 783-784 | "Backup Manuale" | `handleDatabaseAction("backup")` usa solo `setTimeout`, nessun endpoint backend |
| `SettingsPage.jsx` | 802-804 | "Pulisci Ordini" | `handleDatabaseAction("clear_ordini")` - endpoint non esiste |
| `SettingsPage.jsx` | 848-855 | "RESET COMPLETO SISTEMA" | `handleDatabaseAction("reset_complete")` - endpoint non esiste |

**Endpoints backend mancanti da creare:**
- `POST /api/v1/database/backup` - Backup manuale database
- `DELETE /api/v1/ordini/all` - Elimina tutti gli ordini
- `POST /api/v1/database/reset` - Reset completo sistema

---

### 1.3 PAGINE PLACEHOLDER (Non implementate)

| File | Componente | Problema |
|------|------------|----------|
| `App.jsx:229-242` | `UtentiPage` | Bottone "Nuovo Utente" non collegato, pagina placeholder |
| `App.jsx:438` | Pagina "Lookup" | Ritorna solo `PlaceholderPage`, nessuna funzionalità |
| `DatabasePage.jsx:565-573` | Tab "Anomalie" | Solo testo placeholder, nessuna integrazione con `anomalieApi` |

---

### 1.4 SIMULAZIONI DA SOSTITUIRE CON API REALI

| File | Linea | Funzione | Problema |
|------|-------|----------|----------|
| `DatabasePage.jsx` | 212-237 | `handleBatchValidate()` | Usa `setTimeout` invece di chiamare API reale |
| `SettingsPage.jsx` | 99-114 | `handleSave()` | Salva solo in `localStorage`, non sincronizza con backend |
| `SettingsPage.jsx` | 66-92 | `loadSettings()` | Carica solo da `localStorage`, non da backend |

---

### 1.5 FUNZIONI API.JS DEFINITE MA MAI CHIAMATE DAI COMPONENTI

| API Module | Funzione | Endpoint | Usata? |
|------------|----------|----------|--------|
| `ordiniApi` | `confermaRiga()` | `POST /ordini/{id}/righe/{id}/conferma` | NO |
| `ordiniApi` | `confermaOrdineCompleto()` | `POST /ordini/{id}/conferma-tutto` | NO |
| `ordiniApi` | `getStatoRighe()` | `GET /ordini/{id}/stato-righe` | NO |
| `ordiniApi` | `getRigaDettaglio()` | `GET /ordini/{id}/righe/{id}` | NO |
| `ordiniApi` | `modificaRiga()` | `PUT /ordini/{id}/righe/{id}` | NO |
| `ordiniApi` | `inviaASupervisione()` | `POST /ordini/{id}/righe/{id}/supervisione` | NO |
| `ordiniApi` | `validaEGeneraTracciato()` | `POST /ordini/{id}/valida` | NO |
| `lookupApi` | Tutte le funzioni | `/lookup/*` | NO (pagina placeholder) |
| `anomalieApi` | Tutte le funzioni | `/anomalie/*` | NO (tab placeholder) |
| `utentiApi` | Tutte le funzioni | `/utenti/*` | NO (pagina placeholder) |
| `supervisioneApi` | `getDetail()` | `GET /supervisione/{id}` | NO |
| `supervisioneApi` | `getByOrdine()` | `GET /supervisione/ordine/{id}` | NO |
| `dashboardApi` | `getSummary()` | `GET /dashboard/summary` | NO |
| `dashboardApi` | `getAnomalieCritiche()` | `GET /dashboard/anomalie-critiche` | NO |
| `dashboardApi` | `getVendorStats()` | `GET /dashboard/vendor-stats` | NO |
| `dashboardApi` | `getAnagraficaStats()` | `GET /dashboard/anagrafica-stats` | NO |

---

## 2. FUNZIONI BACKEND NON CHIAMATE DAL FRONTEND

### 2.1 Endpoints esistenti senza chiamate frontend

| Router | Endpoint | Metodo | Scopo | Priorita |
|--------|----------|--------|-------|----------|
| `upload.py` | `/upload/detect-vendor` | POST | Rileva vendor senza elaborare PDF | MEDIA |
| `dashboard.py` | `/dashboard/upload-stats` | GET | Statistiche upload dedicate | BASSA |
| `anagrafica.py` | `/anagrafica/farmacie/min/{min_id}` | GET | Ricerca per codice ministeriale | MEDIA |
| `anagrafica.py` | `/anagrafica/parafarmacie/{id}` | GET | Dettaglio parafarmacia | MEDIA |
| `anomalie.py` | `/anomalie` | POST | Crea anomalia manuale | BASSA |
| `anomalie.py` | `/anomalie/batch/stato` | POST | Cambio stato batch generico | BASSA |

### 2.2 Funzioni api.js da aggiungere

```javascript
// Da aggiungere in api.js

// uploadApi
detectVendor: (file) => {
  const formData = new FormData()
  formData.append('file', file)
  return api.post('/upload/detect-vendor', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }).then(r => r.data)
},

// anagraficaApi
getFarmaciaByMinId: (minId) => api.get(`/anagrafica/farmacie/min/${minId}`).then(r => r.data),
getParafarmacia: (id) => api.get(`/anagrafica/parafarmacie/${id}`).then(r => r.data),

// anomalieApi
create: (data) => api.post('/anomalie', data).then(r => r.data),
batchUpdateStato: (ids, stato, note) => api.post('/anomalie/batch/stato', { ids, nuovo_stato: stato, note }).then(r => r.data),
```

---

## 3. PIANO DI INTERVENTO

### FASE 1: FIX CRITICI (Priorita ALTA) - Stimato: 2-4 ore

#### 1.1 Correggere errore nome funzione
**File:** `frontend/src/TracciatiPage.jsx`
**Linea:** 180
```javascript
// PRIMA (ERRATO)
const res = await tracciatiApi.eliminaFile(true);

// DOPO (CORRETTO)
const res = await tracciatiApi.deleteFiles();
```

#### 1.2 Implementare handleBatchValidate con API reale
**File:** `frontend/src/DatabasePage.jsx`
**Linee:** 212-237

```javascript
const handleBatchValidate = async () => {
  if (selected.length === 0) return;

  const conferma = window.confirm(
    `Validare ${selected.length} ordini selezionati?`
  );
  if (!conferma) return;

  setValidatingBatch(true);
  try {
    // Chiama API reale invece di setTimeout
    for (const id of selected) {
      await ordiniApi.validaEGeneraTracciato(id, 'admin');
    }
    alert(`Validati ${selected.length} ordini!`);
    setSelected([]);
    loadOrdini();
  } catch (err) {
    alert('Errore validazione: ' + err.message);
  } finally {
    setValidatingBatch(false);
  }
};
```

---

### FASE 2: BACKEND MANCANTE (Priorita ALTA) - Stimato: 4-6 ore

#### 2.1 Creare router per operazioni database admin
**File da creare:** `backend/app/routers/admin.py`

```python
from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.post("/backup")
async def backup_database() -> Dict[str, Any]:
    """Crea backup del database."""
    # Implementare logica backup
    pass

@router.delete("/ordini/all")
async def clear_all_ordini(confirm: str = Query(...)) -> Dict[str, Any]:
    """Elimina tutti gli ordini."""
    if confirm != "CONFERMA":
        raise HTTPException(400, "Conferma non valida")
    # Implementare logica pulizia
    pass

@router.post("/reset")
async def reset_sistema(confirm: str = Query(...)) -> Dict[str, Any]:
    """Reset completo sistema (preserva anagrafiche)."""
    if confirm != "RESET COMPLETO":
        raise HTTPException(400, "Conferma non valida")
    # Implementare logica reset
    pass

@router.get("/settings")
async def get_settings() -> Dict[str, Any]:
    """Recupera impostazioni sistema."""
    pass

@router.put("/settings")
async def save_settings(settings: dict) -> Dict[str, Any]:
    """Salva impostazioni sistema."""
    pass
```

#### 2.2 Registrare router in main.py
**File:** `backend/app/main.py`
```python
from .routers import admin
app.include_router(admin.router, prefix="/api/v1")
```

#### 2.3 Aggiungere funzioni in api.js
**File:** `frontend/src/api.js`

```javascript
// Aggiungere adminApi
export const adminApi = {
  backup: () => api.post('/admin/backup').then(r => r.data),
  clearOrdini: (confirm) => api.delete(`/admin/ordini/all?confirm=${confirm}`).then(r => r.data),
  resetSistema: (confirm) => api.post(`/admin/reset?confirm=${confirm}`).then(r => r.data),
  getSettings: () => api.get('/admin/settings').then(r => r.data),
  saveSettings: (settings) => api.put('/admin/settings', settings).then(r => r.data),
}
```

---

### FASE 3: IMPLEMENTARE PAGINE PLACEHOLDER (Priorita MEDIA) - Stimato: 8-12 ore

#### 3.1 Implementare LookupPage
**File da creare:** `frontend/src/LookupPage.jsx`

Funzionalita:
- Lista ordini pending lookup (`lookupApi.getPending()`)
- Ricerca farmacie/parafarmacie (`lookupApi.searchFarmacie()`, `lookupApi.searchParafarmacie()`)
- Assegnazione manuale (`lookupApi.manuale()`)
- Lookup batch (`lookupApi.batch()`)
- Statistiche lookup (`lookupApi.getStats()`)

#### 3.2 Implementare tab Anomalie in DatabasePage
**File:** `frontend/src/DatabasePage.jsx`

Funzionalita:
- Lista anomalie con filtri (`anomalieApi.getList()`)
- Aggiornamento stato (`anomalieApi.update()`)
- Risoluzione batch (`anomalieApi.batchRisolvi()`)

#### 3.3 Implementare UtentiPage completa
**File:** `frontend/src/UtentiPage.jsx` (da creare separatamente)

Funzionalita:
- Lista utenti (`utentiApi.getList()`)
- Creazione utente (`utentiApi.create()`)
- Modifica utente (`utentiApi.update()`)
- Cambio password (`utentiApi.changePassword()`)
- Disabilita/Riabilita (`utentiApi.disable()`, `utentiApi.enable()`)

---

### FASE 4: DETTAGLIO ORDINE (Priorita MEDIA) - Stimato: 6-8 ore

#### 4.1 Implementare pagina dettaglio ordine completa
**File:** Modificare sezione `ordine-detail` in `App.jsx`

Funzionalita:
- Visualizzazione righe ordine (`ordiniApi.getRighe()`)
- Stato conferma righe (`ordiniApi.getStatoRighe()`)
- Conferma singola riga (`ordiniApi.confermaRiga()`)
- Conferma ordine completo (`ordiniApi.confermaOrdineCompleto()`)
- Modifica riga (`ordiniApi.modificaRiga()`)
- Invio a supervisione (`ordiniApi.inviaASupervisione()`)
- Validazione e generazione tracciato (`ordiniApi.validaEGeneraTracciato()`)
- Anomalie ordine (`anomalieApi.getByOrdine()`)

---

### FASE 5: SINCRONIZZAZIONE SETTINGS (Priorita BASSA) - Stimato: 2-3 ore

#### 5.1 Collegare SettingsPage al backend

**Modifiche in SettingsPage.jsx:**

```javascript
// loadSettings
const loadSettings = useCallback(async () => {
  try {
    setLoading(true);
    const res = await adminApi.getSettings();
    if (res.success) {
      setSettings(res.data);
    }
  } catch (err) {
    // Fallback a localStorage
    const savedSettings = localStorage.getItem("to_extractor_settings");
    if (savedSettings) {
      setSettings(prev => ({ ...prev, ...JSON.parse(savedSettings) }));
    }
  } finally {
    setLoading(false);
  }
}, []);

// handleSave
const handleSave = async () => {
  setSaving(true);
  try {
    await adminApi.saveSettings(settings);
    localStorage.setItem("to_extractor_settings", JSON.stringify(settings));
    alert("Impostazioni salvate!");
  } catch (err) {
    alert("Errore: " + err.message);
  } finally {
    setSaving(false);
  }
};
```

---

## 4. RIEPILOGO PRIORITA

| Fase | Descrizione | Priorita | Effort | Impatto |
|------|-------------|----------|--------|---------|
| 1 | Fix critici (errore nome funzione, batch validate) | ALTA | 2-4h | ALTO |
| 2 | Backend mancante (admin router) | ALTA | 4-6h | ALTO |
| 3 | Pagine placeholder (Lookup, Anomalie, Utenti) | MEDIA | 8-12h | MEDIO |
| 4 | Dettaglio ordine completo | MEDIA | 6-8h | MEDIO |
| 5 | Sincronizzazione settings | BASSA | 2-3h | BASSO |

**Tempo totale stimato: 22-33 ore**

---

## 5. CHECKLIST IMPLEMENTAZIONE

### Fase 1 - Fix Critici
- [ ] Correggere `tracciatiApi.eliminaFile` → `tracciatiApi.deleteFiles` in TracciatiPage.jsx
- [ ] Implementare `handleBatchValidate` con chiamata API reale in DatabasePage.jsx
- [ ] Testare funzionalita corrette

### Fase 2 - Backend Admin
- [ ] Creare `backend/app/routers/admin.py`
- [ ] Implementare endpoint `/admin/backup`
- [ ] Implementare endpoint `/admin/ordini/all` (DELETE)
- [ ] Implementare endpoint `/admin/reset`
- [ ] Implementare endpoint `/admin/settings` (GET/PUT)
- [ ] Registrare router in main.py
- [ ] Aggiungere `adminApi` in api.js
- [ ] Collegare SettingsPage ai nuovi endpoint

### Fase 3 - Pagine Placeholder
- [ ] Creare LookupPage.jsx completa
- [ ] Implementare tab Anomalie in DatabasePage
- [ ] Creare UtentiPage.jsx completa
- [ ] Aggiornare App.jsx per usare nuove pagine

### Fase 4 - Dettaglio Ordine
- [ ] Implementare visualizzazione righe
- [ ] Implementare conferma righe
- [ ] Implementare modifica righe
- [ ] Implementare invio a supervisione
- [ ] Implementare validazione ordine
- [ ] Collegare anomalie ordine

### Fase 5 - Settings
- [ ] Collegare loadSettings a backend
- [ ] Collegare handleSave a backend
- [ ] Mantenere fallback localStorage

---

*Report generato automaticamente - TO_EXTRACTOR v6.2*
