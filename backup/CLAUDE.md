# TO_EXTRACTOR v6.2 - Istruzioni Progetto

## Panoramica

Sistema di estrazione automatica ordini farmaceutici da PDF con generazione tracciati ministeriali TO_T/TO_D.

**Stack:** FastAPI + SQLite + React + Vite + TailwindCSS

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
| **ANGELINI** | Attivo | ID MIN diretto, sconti cascata (35+10+5) |
| **BAYER** | Attivo | Formato SAP |
| **CODIFI** | Attivo | Multi-cliente (N ordini/PDF) |
| **CHIESI** | In attesa | Colonne verticali, escludere P.IVA 02944970348 |
| **MENARINI** | In attesa | Parent/Child con indentazione |
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

## Espositori

- `PARENT_ESPOSITORE` - Contenitore (FSTAND 24PZ)
- `CHILD_ESPOSITORE` - Esclusi da tracciato
- Codici 6 cifre → padding 500 (415734 → 500415734)

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

---

## Convenzioni

- **Python:** snake_case, type hints
- **JS:** camelCase, JSX
- **Git:** `feat:`, `fix:`, `refactor:`
- **Encoding:** UTF-8, CRLF per tracciati
