# Feature: Modifica Manuale Header Ordine

**Data creazione:** 25/01/2026
**Priorità:** Media
**Stato:** Da implementare

---

## Problema

Quando un ordine viene estratto da PDF senza dati farmacia (P.IVA, MIN_ID, ragione sociale mancanti o errati), l'operatore non ha modo di correggere manualmente questi campi nell'header dell'ordine.

### Caso d'uso reale

1. PDF estratto senza indicazione della farmacia
2. Operatore consulta manualmente l'archivio farmacie del Ministero
3. Identifica la farmacia corretta
4. **PROBLEMA**: Non può inserire i dati nell'header dell'ordine
5. **PROBLEMA**: Non può assegnare il deposito di riferimento (se non c'è anomalia LKP-A05)

---

## Soluzione Proposta

### 1. Backend - Nuovo Endpoint

**File:** `backend/app/routers/ordini.py`

```python
# =============================================================================
# MODIFICA HEADER ORDINE
# =============================================================================

class ModificaHeaderRequest(BaseModel):
    """Request per modifica manuale header ordine."""
    partita_iva: Optional[str] = None
    min_id: Optional[str] = None
    ragione_sociale: Optional[str] = None
    deposito_riferimento: Optional[str] = None
    indirizzo: Optional[str] = None
    cap: Optional[str] = None
    localita: Optional[str] = None
    provincia: Optional[str] = None
    operatore: str
    note: Optional[str] = None


@router.patch("/{id_testata}/header", summary="Modifica header ordine")
async def modifica_header_ordine(
    id_testata: int,
    request: ModificaHeaderRequest,
    current_user: UtenteResponse = Depends(get_current_user)
):
    """
    Modifica manualmente i campi dell'header (testata) di un ordine.

    ## Campi modificabili

    - `partita_iva`: P.IVA cliente
    - `min_id`: Codice ministeriale farmacia
    - `ragione_sociale`: Nome farmacia
    - `deposito_riferimento`: Codice deposito (CT, PE, etc.)
    - `indirizzo`, `cap`, `localita`, `provincia`: Dati indirizzo

    ## Comportamento

    1. Salva valori originali in `valori_originali_header` (JSON) per audit
    2. Aggiorna solo i campi forniti (non nulli)
    3. Registra modifica in `log_operazioni`
    4. Se cambiano P.IVA o MIN_ID, ricalcola lookup_method e lookup_score

    ## Permessi

    Richiede ruolo: OPERATORE, SUPERVISORE, ADMIN
    """
    db = get_db()

    # 1. Verifica esistenza ordine
    ordine = db.execute("""
        SELECT * FROM ordini_testata WHERE id_testata = %s
    """, (id_testata,)).fetchone()

    if not ordine:
        raise HTTPException(status_code=404, detail="Ordine non trovato")

    # 2. Verifica stato ordine (non modificabile se EVASO/ARCHIVIATO)
    if ordine['stato'] in ('EVASO', 'ARCHIVIATO'):
        raise HTTPException(
            status_code=400,
            detail=f"Ordine in stato {ordine['stato']} non modificabile"
        )

    # 3. Salva valori originali per audit
    valori_originali = {
        'partita_iva': ordine['partita_iva'],
        'min_id': ordine['min_id'],
        'ragione_sociale': ordine['ragione_sociale'],
        'deposito_riferimento': ordine.get('deposito_riferimento'),
        'indirizzo': ordine.get('indirizzo'),
        'cap': ordine.get('cap'),
        'localita': ordine.get('localita'),
        'provincia': ordine.get('provincia'),
    }

    # 4. Costruisci UPDATE dinamico (solo campi forniti)
    updates = []
    params = []
    campi_modificati = []

    field_mapping = {
        'partita_iva': request.partita_iva,
        'min_id': request.min_id,
        'ragione_sociale': request.ragione_sociale,
        'deposito_riferimento': request.deposito_riferimento,
        'indirizzo': request.indirizzo,
        'cap': request.cap,
        'localita': request.localita,
        'provincia': request.provincia,
    }

    for field, value in field_mapping.items():
        if value is not None:
            updates.append(f"{field} = %s")
            params.append(value.strip() if isinstance(value, str) else value)
            campi_modificati.append(field)

    if not updates:
        raise HTTPException(status_code=400, detail="Nessun campo da modificare")

    # 5. Aggiungi metadati modifica
    updates.append("lookup_method = 'MANUALE'")
    updates.append("data_modifica_header = NOW()")
    updates.append("operatore_modifica_header = %s")
    params.append(request.operatore)

    # Salva valori originali come JSON
    updates.append("valori_originali_header = %s")
    params.append(json.dumps(valori_originali))

    params.append(id_testata)  # WHERE clause

    # 6. Esegui UPDATE
    db.execute(f"""
        UPDATE ordini_testata
        SET {', '.join(updates)}
        WHERE id_testata = %s
    """, tuple(params))

    # 7. Log operazione
    db.execute("""
        INSERT INTO log_operazioni (
            tipo_operazione, id_riferimento, tabella_riferimento,
            operatore, dettagli, timestamp
        ) VALUES (
            'MODIFICA_HEADER', %s, 'ordini_testata',
            %s, %s, NOW()
        )
    """, (
        id_testata,
        request.operatore,
        json.dumps({
            'campi_modificati': campi_modificati,
            'valori_originali': valori_originali,
            'note': request.note
        })
    ))

    # 8. Se P.IVA o MIN_ID modificati, risolvi eventuali anomalie LKP
    if request.partita_iva or request.min_id:
        db.execute("""
            UPDATE anomalie
            SET stato = 'RISOLTA',
                note_risoluzione = %s,
                data_risoluzione = NOW()
            WHERE id_testata = %s
              AND codice_anomalia IN ('LKP-A01', 'LKP-A02', 'LKP-A04', 'LKP-A05')
              AND stato = 'APERTA'
        """, (
            f"Header modificato manualmente da {request.operatore}",
            id_testata
        ))

    db.commit()

    return {
        "success": True,
        "message": f"Header ordine {id_testata} aggiornato",
        "data": {
            "id_testata": id_testata,
            "campi_modificati": campi_modificati,
            "valori_originali": valori_originali
        }
    }
```

### 2. Migrazione Database

**File:** `backend/migrations/v12_modifica_header.sql`

```sql
-- =============================================================================
-- SERV.O v12 - MODIFICA HEADER ORDINE
-- =============================================================================
-- Aggiunge colonne per tracciare modifiche manuali all'header
-- =============================================================================

-- Colonne audit su ordini_testata
ALTER TABLE ordini_testata
ADD COLUMN IF NOT EXISTS valori_originali_header JSONB;

ALTER TABLE ordini_testata
ADD COLUMN IF NOT EXISTS data_modifica_header TIMESTAMP;

ALTER TABLE ordini_testata
ADD COLUMN IF NOT EXISTS operatore_modifica_header VARCHAR(100);

-- Indice per query su ordini modificati manualmente
CREATE INDEX IF NOT EXISTS idx_ordini_modifica_header
ON ordini_testata(data_modifica_header)
WHERE data_modifica_header IS NOT NULL;

-- Commenti
COMMENT ON COLUMN ordini_testata.valori_originali_header IS
'JSON con valori originali prima della modifica manuale';

COMMENT ON COLUMN ordini_testata.data_modifica_header IS
'Timestamp ultima modifica manuale header';

COMMENT ON COLUMN ordini_testata.operatore_modifica_header IS
'Username operatore che ha modificato header';
```

### 3. Frontend - Modal Modifica Header

**File:** `frontend/src/components/ModificaHeaderModal.jsx`

```jsx
import { useState, useEffect } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { ordiniApi } from '../api/ordini';

export default function ModificaHeaderModal({ ordine, isOpen, onClose }) {
  const queryClient = useQueryClient();

  const [formData, setFormData] = useState({
    partita_iva: '',
    min_id: '',
    ragione_sociale: '',
    deposito_riferimento: '',
    indirizzo: '',
    cap: '',
    localita: '',
    provincia: '',
    note: ''
  });

  useEffect(() => {
    if (ordine) {
      setFormData({
        partita_iva: ordine.partita_iva || '',
        min_id: ordine.min_id || '',
        ragione_sociale: ordine.ragione_sociale || '',
        deposito_riferimento: ordine.deposito || '',
        indirizzo: ordine.indirizzo || '',
        cap: ordine.cap || '',
        localita: ordine.localita || '',
        provincia: ordine.provincia || '',
        note: ''
      });
    }
  }, [ordine]);

  const mutation = useMutation({
    mutationFn: (data) => ordiniApi.modificaHeader(ordine.id_testata, data),
    onSuccess: () => {
      queryClient.invalidateQueries(['ordine', ordine.id_testata]);
      onClose();
    }
  });

  const handleSubmit = (e) => {
    e.preventDefault();

    // Invia solo campi modificati
    const payload = { operatore: 'current_user' }; // TODO: da auth context

    Object.entries(formData).forEach(([key, value]) => {
      if (value && value !== (ordine[key] || '')) {
        payload[key] = value;
      }
    });

    if (formData.note) payload.note = formData.note;

    mutation.mutate(payload);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b">
          <h2 className="text-xl font-semibold">
            Modifica Header Ordine #{ordine?.id_testata}
          </h2>
          <p className="text-sm text-gray-500 mt-1">
            Modifica manuale dei dati farmacia
          </p>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* Dati Farmacia */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">P.IVA</label>
              <input
                type="text"
                value={formData.partita_iva}
                onChange={(e) => setFormData({...formData, partita_iva: e.target.value})}
                className="w-full border rounded px-3 py-2"
                maxLength={16}
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">MIN_ID (Cod. Ministeriale)</label>
              <input
                type="text"
                value={formData.min_id}
                onChange={(e) => setFormData({...formData, min_id: e.target.value})}
                className="w-full border rounded px-3 py-2"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Ragione Sociale</label>
            <input
              type="text"
              value={formData.ragione_sociale}
              onChange={(e) => setFormData({...formData, ragione_sociale: e.target.value})}
              className="w-full border rounded px-3 py-2"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Deposito di Riferimento</label>
            <select
              value={formData.deposito_riferimento}
              onChange={(e) => setFormData({...formData, deposito_riferimento: e.target.value})}
              className="w-full border rounded px-3 py-2"
            >
              <option value="">-- Seleziona --</option>
              <option value="CT">CT - Catania (SOFAD)</option>
              <option value="CL">CL - Caltanissetta (SOFAD)</option>
              <option value="PE">PE - Pescara (SAFAR)</option>
              <option value="CB">CB - Campobasso (SAFAR)</option>
              <option value="001">001 - Deposito Default (FARVI)</option>
            </select>
          </div>

          {/* Indirizzo */}
          <div className="border-t pt-4 mt-4">
            <h3 className="text-sm font-medium text-gray-700 mb-3">Indirizzo (opzionale)</h3>
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2">
                <input
                  type="text"
                  placeholder="Indirizzo"
                  value={formData.indirizzo}
                  onChange={(e) => setFormData({...formData, indirizzo: e.target.value})}
                  className="w-full border rounded px-3 py-2"
                />
              </div>
              <div>
                <input
                  type="text"
                  placeholder="CAP"
                  value={formData.cap}
                  onChange={(e) => setFormData({...formData, cap: e.target.value})}
                  className="w-full border rounded px-3 py-2"
                  maxLength={5}
                />
              </div>
              <div>
                <input
                  type="text"
                  placeholder="Località"
                  value={formData.localita}
                  onChange={(e) => setFormData({...formData, localita: e.target.value})}
                  className="w-full border rounded px-3 py-2"
                />
              </div>
              <div>
                <input
                  type="text"
                  placeholder="Provincia"
                  value={formData.provincia}
                  onChange={(e) => setFormData({...formData, provincia: e.target.value})}
                  className="w-full border rounded px-3 py-2 uppercase"
                  maxLength={2}
                />
              </div>
            </div>
          </div>

          {/* Note */}
          <div>
            <label className="block text-sm font-medium mb-1">Note modifica</label>
            <textarea
              value={formData.note}
              onChange={(e) => setFormData({...formData, note: e.target.value})}
              className="w-full border rounded px-3 py-2"
              rows={2}
              placeholder="Motivazione della modifica manuale..."
            />
          </div>

          {/* Warning */}
          <div className="bg-amber-50 border border-amber-200 rounded p-3 text-sm">
            <strong>Attenzione:</strong> La modifica manuale sovrascrive i dati estratti dal PDF.
            I valori originali verranno salvati per audit.
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-3 pt-4 border-t">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border rounded hover:bg-gray-50"
            >
              Annulla
            </button>
            <button
              type="submit"
              disabled={mutation.isPending}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
            >
              {mutation.isPending ? 'Salvataggio...' : 'Salva Modifiche'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
```

### 4. API Client Frontend

**File:** `frontend/src/api/ordini.js` (aggiungere)

```javascript
// Modifica header ordine
modificaHeader: async (idTestata, data) => {
  const response = await api.patch(`/ordini/${idTestata}/header`, data);
  return response.data;
},
```

### 5. Integrazione in OrdineDetail

**File:** `frontend/src/pages/OrdineDetail/OrdineHeader.jsx` (modificare)

Aggiungere pulsante "Modifica Header" accanto ai dati farmacia:

```jsx
<button
  onClick={() => setShowModificaHeader(true)}
  className="text-blue-600 hover:text-blue-800 text-sm"
  title="Modifica dati farmacia"
>
  <PencilIcon className="w-4 h-4" />
</button>
```

---

## Checklist Implementazione

- [ ] Backend: Creare endpoint `PATCH /ordini/{id_testata}/header`
- [ ] Backend: Aggiungere validazione campi (P.IVA 11-16 char, provincia 2 char, etc.)
- [ ] Database: Eseguire migrazione v12_modifica_header.sql
- [ ] Frontend: Creare componente ModificaHeaderModal
- [ ] Frontend: Aggiungere metodo `modificaHeader` in ordiniApi
- [ ] Frontend: Integrare modal in OrdineHeader con pulsante modifica
- [ ] Test: Verificare salvataggio e ripristino valori originali
- [ ] Test: Verificare risoluzione automatica anomalie LKP
- [ ] Documentazione: Aggiornare CLAUDE.md con nuovo endpoint

---

## Note Aggiuntive

### Ricerca Farmacia nel Ministero

L'operatore può consultare l'archivio ministeriale per trovare i dati corretti:
- **Farmacie**: https://www.dati.salute.gov.it/dati/dettaglioDataset.jsp?menu=dati&idPag=5
- **Parafarmacie**: https://www.dati.salute.gov.it/dati/dettaglioDataset.jsp?menu=dati&idPag=7

### Lookup Automatico (futuro)

In futuro si potrebbe aggiungere un bottone "Cerca nel Ministero" che:
1. Prende ragione_sociale parziale o indirizzo
2. Cerca nelle tabelle `farmacie`/`parafarmacie`
3. Propone match con score di similarità
4. L'operatore seleziona il match corretto
