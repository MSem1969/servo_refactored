# SERV.O - Istruzioni Progetto

## Panoramica

Sistema estrazione ordini farmaceutici da PDF → tracciati ministeriali TO_T/TO_D.

**Stack:** FastAPI + PostgreSQL + React + Vite + TailwindCSS + React Query

---

## Comandi

```bash
# Backend
cd backend && source venv/bin/activate && uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend && npm run dev
```

---

## Architettura

```
backend/app/
├── services/
│   ├── extraction/vendors/    # Estrattori PDF per vendor
│   ├── export/                # Generazione tracciati EDI
│   ├── supervision/           # ML supervision + propagazione
│   ├── tracking/              # Tracking operatore (ML)
│   ├── anagrafica/            # Sync ministero + import
│   └── anomalies/             # Resolver anomalie
├── routers/                   # API endpoints
└── utils/

frontend/src/
├── api/           # Client API
├── components/    # Componenti feature
├── hooks/         # React Query hooks
├── pages/         # Pagine (OrdineDetail/, Database/)
└── context/       # Auth, UI state
```

---

## Formato Tracciati EDI

### TO_T - TESTATA

| Pos | Campo | Lung. | Obbl. | Descrizione |
|-----|-------|-------|-------|-------------|
| 1-10 | Vendor | 10 | Y | Codice produttore |
| 11-40 | VendorOrderNumber | 30 | Y | Numero ordine |
| 41-60 | CustomerTraceabilityCode | 20 | Y | MIN_ID farmacia |
| 61-76 | VAT code | 16 | Y | P.IVA cliente |
| 77-126 | CustomerName1 | 50 | Y | Ragione sociale |
| 127-176 | CustomerName2 | 50 | N | Ragione sociale 2 |
| 177-226 | Address | 50 | N | Indirizzo |
| 227-236 | CodeCity | 10 | N | CAP |
| 237-286 | City | 50 | N | Città |
| 287-289 | Province | 3 | N | Provincia |
| 290-299 | OrderDate | 10 | Y | Data ordine (GG/MM/AAAA) |
| 300-309 | EstDeliveryDate | 10 | Y | Data consegna |
| 310-359 | AgentName | 50 | N | Nome agente |
| 360-372 | Payment1 | 13 | N | Data + giorni dilazione |
| 373-416 | Payment2/3 | 44 | N | Altri pagamenti |
| 417-456 | OfferCodes | 40 | N | Codici offerta |
| 457 | ForceCheck | 1 | N | S/N |
| 458-657 | OrderAnnotation | 200 | Y | Note ordine |
| 658-857 | BOT_Annotation | 200 | Y | Note DDT |

### TO_D - DETTAGLIO

| Pos | Campo | Lung. | Obbl. | Campo DB |
|-----|-------|-------|-------|----------|
| 1-30 | VendorNumberOrder | 30 | Y | numero_ordine |
| 31-35 | LineNumber | 5 | Y | n_riga |
| 36-56 | ProductCode | 21 | Y | codice_aic (10 cifre + 11 spazi) |
| 57-62 | SalesQuantity | 6 | Y | q_venduta |
| 63-68 | QuantityDiscountPieces | 6 | N | **sempre 0** |
| 69-74 | QuantityFreePieces | 6 | N | **q_sconto_merce + q_omaggio** |
| 75-84 | ExtDeliveryDate | 10 | N | data_consegna |
| 85-108 | Discount1-4 | 24 | Y | sconto_1/2/3/4 (3+2 dec) |
| 109-118 | NetVendorPrice | 10 | Y | prezzo_netto (7+2 dec) |
| 119-128 | PriceToDiscount | 10 | Y | prezzo_scontare |
| 129-133 | VAT | 5 | N | aliquota_iva |
| 134 | NetVATPrice | 1 | Y | scorporo_iva (S/N) |
| 135-144 | PriceForFinalSale | 10 | Y | prezzo_pubblico |
| 145-344 | NoteAllestimento | 200 | Y | note_allestimento |

**REGOLA OMAGGIO:** `QuantityFreePieces = q_sconto_merce + q_omaggio` (QuantityDiscountPieces sempre 0)

---

## Database - Campi Quantità

| Campo DB | Tracciato | Note |
|----------|-----------|------|
| q_venduta | SalesQuantity | Quantità venduta |
| q_sconto_merce | → FreePieces | Sommato a omaggio |
| q_omaggio | → FreePieces | Pezzi gratuiti |
| q_evasa | - | Export parziali |
| **q_totale** | - | = q_venduta + q_sconto_merce + q_omaggio |

**Vista:** Usare `min_id` su `V_ORDINI_COMPLETI` (non `codice_ministeriale`)

---

## Stati Ordine e Riga

**REGOLA:** Stati ORDINE e RIGA sono **INDIPENDENTI**. Stato ordine = riepilogo, non modifica righe.

### Stati Riga (ORDINI_DETTAGLIO.stato_riga)

| Stato | Immutabile | Condizione |
|-------|------------|------------|
| **ARCHIVIATO** | SI | Azione utente |
| **EVASO** | SI | q_evasa >= q_totale |
| **PARZIALE** | NO | 0 < q_evasa < q_totale |
| **CONFERMATO** | NO | Conferma utente |
| **ESTRATTO** | NO | Default |

### Stati Ordine (ORDINI_TESTATA.stato)

`ARCHIVIATO` | `EVASO` | `PARZ_EVASO` | `CONFERMATO` | `ANOMALIA` | `ESTRATTO`

### Operazioni Protette

- **ARCHIVIATO/EVASO**: bloccati da CONFERMA/RIPRISTINA singola
- **Generazione tracciato**: esclude ARCHIVIATO/EVASO

---

## Anomalie

### GRAVI (Bloccanti)

| Codice | Tipo | Descrizione |
|--------|------|-------------|
| **ESP-A01** | ESPOSITORE | Pezzi child < attesi (>=20%) |
| **ESP-A02** | ESPOSITORE | Pezzi child > attesi (>=20%) |
| **ESP-A03** | ESPOSITORE | Espositore senza child |
| **ESP-A04/05** | ESPOSITORE | Chiusura forzata |
| **ESP-A06** | ESPOSITORE | Conflitto ML vs estrazione |
| **LKP-A01** | LOOKUP | Score < 80% |
| **LKP-A02** | LOOKUP | Farmacia non trovata |
| **LKP-A04** | LOOKUP | P.IVA mismatch (subentro) |
| **LKP-A05** | LOOKUP | Cliente non in anagrafica_clienti |
| **EXT-A01** | ESTRAZIONE | Vendor non riconosciuto |

### ORDINARIE (Non Bloccanti)

| Codice | Descrizione |
|--------|-------------|
| **LKP-A03** | Score 80-95% |
| **DOCGEN-A08** | Quantità >200 pezzi |

### Soglie Lookup

| Score | Risultato |
|-------|-----------|
| >= 95% | OK |
| 80-95% | LKP-A03 (warning) |
| < 80% | LKP-A01 (bloccante) |
| 0 | LKP-A02 (bloccante) |
| 50 | LKP-A04 (P.IVA mismatch) |

---

## Vendor Supportati

| Vendor | Stato | Note |
|--------|-------|------|
| **ANGELINI** | Attivo | MIN_ID diretto, sconti cascata, espositore 6 cifre |
| **BAYER** | Attivo | Formato SAP |
| **CODIFI** | Attivo | Multi-cliente (N ordini/PDF) |
| **MENARINI** | Attivo | Espositore `--`, chiusura su somma netto |
| **DOC_GENERICI** | Attivo | Transfer Order, NO prezzi |
| **CHIESI** | In attesa | Escludere P.IVA 02944970348 |
| **OPELLA** | In attesa | AIC 7-9 cifre |

**Detection:** Solo contenuto PDF (nome file ignorato)

---

## Espositori

- **PARENT_ESPOSITORE**: Contenitore (FSTAND, BANCO, EXPO, etc.)
- **CHILD_ESPOSITORE**: Prodotti contenuti
- **Tracciato EDI**: Solo parent, child esclusi

| Vendor | Chiusura |
|--------|----------|
| ANGELINI | pezzi_accumulati >= pezzi_attesi |
| MENARINI | somma_netto_child >= netto_parent |

---

## Propagazione Anomalie

Livelli: `SINGOLO` | `ORDINE` | `GLOBALE`

```
POST /api/v10/anomalie/dettaglio/{id}/correggi-aic
{
    "codice_aic": "012345678",
    "livello_propagazione": "ORDINE",
    "operatore": "mario.rossi"
}
```

Effetti: aggiorna righe → chiude anomalie → approva supervisioni → incrementa ML

---

## Modifica Header Manuale (v11.3)

`PATCH /api/v10/ordini/{id_testata}/header`

Quando `lookup_method = 'MANUALE'`:
- Valori testata hanno **priorità** su anagrafica
- Vista `V_ORDINI_COMPLETI` usa CASE per priorità

---

## Sync Anagrafica Ministero

```
POST /api/v10/admin/sync/farmacie
POST /api/v10/admin/sync/parafarmacie
POST /api/v10/admin/sync/all
```

- Download condizionale (ETag)
- Sync incrementale (INSERT/UPDATE)
- Traccia subentri → genera LKP-A04

---

## Tracking Operatore

Tabella `operatore_azioni_log`: chi, cosa, quando, contesto, client.

```python
from ..services.tracking import track_from_user, Sezione, Azione

track_from_user(current_user, Sezione.DATABASE, Azione.CONFIRM,
                request=request, entita='ordine', id_entita=123)
```

---

## Convenzioni

- **Python:** snake_case, type hints
- **JS:** camelCase, JSX
- **Git:** `feat:`, `fix:`, `refactor:`
- **Encoding:** UTF-8, CRLF per tracciati

---

## Checklist Sviluppo

1. Esiste già soluzione simile?
2. Pattern si ripeterà? → Generalizza
3. Caso isolato? → Documenta eccezione
4. Uniforma: error handling, response format, componenti UI
