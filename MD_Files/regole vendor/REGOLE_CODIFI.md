# 📋 REGOLE ESTRAZIONE: CODIFI

**Vendor**: CODIFI S.R.L.
**Versione**: 2.1
**Data**: 6 Gennaio 2026
**Identificativo**: Transfer Order CODIFI
**Particolarità**: ⚠️ DOCUMENTI MULTI-CLIENTE

---

## 🔍 IDENTIFICAZIONE DOCUMENTO

### ⚠️ IMPORTANTE: Detection Basata su Contenuto PDF
Il nome del file **NON** deve essere usato come criterio di identificazione vendor.
La detection deve basarsi **ESCLUSIVAMENTE** sul contenuto del PDF.

### Pattern di Riconoscimento (SOLO contenuto PDF)
```
MUST contain: "CODIFI" OR "CODIFI S.R.L."
AND "Transfer Order"
```

### Esempio Nome File (solo per riferimento, NON usato per detection)
- `TO_CODIFI_20251022.pdf`
- `CODIFI_MULTICLIENTE.pdf`

---

## ⚠️ PARTICOLARITÀ: MULTI-CLIENTE

### Descrizione
```
Un singolo PDF CODIFI può contenere ORDINI PER PIÙ FARMACIE.
Ogni sezione "DESTINATARIO" indica un nuovo ordine.
```

### Struttura Multi-Ordine
```
PDF CODIFI
├── ORDINE 1
│   ├── Header (destinatario 1)
│   └── Tabella prodotti
├── --- SEPARATORE ---
├── ORDINE 2
│   ├── Header (destinatario 2)
│   └── Tabella prodotti
├── --- SEPARATORE ---
└── ORDINE N
    ├── Header (destinatario N)
    └── Tabella prodotti
```

### Pattern Separatore
```
Pattern: "={10,}" OR "─{10,}" OR "Destinatario" (nuovo blocco)
```

---

## 📄 STRUTTURA DOCUMENTO

### Layout Singolo Ordine
- **Tipo**: Blocchi ripetuti per ogni cliente
- **Header**: Dati destinatario
- **Tabella**: Righe prodotto standard

### Sezioni per Ordine
```
BLOCCO ORDINE
├── "Destinatario:" + dati farmacia
├── Numero ordine CODIFI
├── Data
└── Tabella prodotti

TABELLA
├── Codice | Descrizione | Qtà | Prezzo | Sconto | Totale
```

---

## 📐 REGOLE ESTRAZIONE - SEGMENTAZIONE

### CODIFI-S01: Identificazione Blocchi
```python
def segment_codifi(text: str, lines: List[str]) -> List[Dict]:
    """
    Segmenta documento CODIFI in blocchi per cliente.
    Restituisce lista di dizionari, uno per ordine.
    """
    blocks = []
    current_block = {'lines': [], 'start': 0}
    
    for i, line in enumerate(lines):
        # Nuovo blocco se trova "Destinatario"
        if re.match(r'^Destinatario', line, re.I):
            if current_block['lines']:
                blocks.append(current_block)
            current_block = {'lines': [], 'start': i}
        current_block['lines'].append(line)
    
    if current_block['lines']:
        blocks.append(current_block)
    
    return blocks
```

### CODIFI-S02: Estrazione per Blocco
```
Per ogni blocco identificato:
1. Estrarre header (regole CODIFI-H*)
2. Estrarre prodotti (regole CODIFI-T*)
3. Creare record PDF_ORDINI separato
4. Tutti i record condividono stesso filename ma id_pdf diverso
```

---

## 📐 REGOLE ESTRAZIONE HEADER

### CODIFI-H01: Destinatario (Ragione Sociale)
```
Pattern: "Destinatario[:\s]*([^\n]+)"
Output: PDF_ORDINI.ragione_sociale_raw
Limite: 50 caratteri
```

### CODIFI-H02: Indirizzo
```
Pattern: riga dopo "Destinatario" che inizia con via/piazza/corso
         OR "Indirizzo[:\s]*([^\n]+)"
Output: PDF_ORDINI.indirizzo_raw
```

### CODIFI-H03: CAP/Città/Provincia
```
Pattern: "(\d{5})\s+([A-Z][a-zA-Z\s]+)\s*\(?([A-Z]{2})\)?"
Gruppi:
  1 = cap_raw
  2 = citta_raw
  3 = provincia_raw
Output: campi corrispondenti
```

### CODIFI-H04: P.IVA
```
Pattern: "P[.\s]*IVA[:\s]*(\d{11})"
Output: PDF_ORDINI.partita_iva
```

### CODIFI-H05: Numero Ordine
```
Pattern: "Ordine\s+(?:n[°.]?|N\.?)[:\s]*([A-Z0-9\-]+)"
         OR "Rif[.\s:]*([^\n]+)"
Output: PDF_ORDINI.numero_ordine
```

### CODIFI-H06: Data Ordine
```
Pattern: "Data[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"
Output: PDF_ORDINI.data_ordine_raw
```

### CODIFI-H07: Condizioni Pagamento
```
Pattern: "Pagamento[:\s]*(\d+)\s*(?:gg|giorni)"
         OR "(\d+)\s*GG"
Output: PDF_ORDINI.condizioni_pagamento = "XX gg"
```

---

## 📊 REGOLE ESTRAZIONE TABELLA PRODOTTI

### CODIFI-T01: Identificazione Tabella
```
Inizio: riga contiene "Codice" AND "Descrizione"
Fine: riga vuota OR nuovo "Destinatario" OR "Totale"
```

### CODIFI-T02: Codice AIC
```
Pattern: "^(\d{9})$" (9 cifre)
         OR "^0?(\d{8})$" (8 cifre → padding)
Output: TO_RAW.codice_raw
```

### CODIFI-T03: Descrizione
```
Posizione: colonna descrizione
Limite: 40 caratteri
Output: TO_RAW.descrizione
```

### CODIFI-T04: Quantità
```
Pattern: "(\d+)" in colonna quantità
Output: TO_RAW.quantita_raw
```

### CODIFI-T05: Prezzo
```
Pattern: "(\d+[,\.]\d{2})"
Output: TO_RAW.prezzo_netto_raw
```

### CODIFI-T06: Sconto
```
Pattern: "(\d+[,\.]\d*)\s*%?"
Output: TO_RAW.sconto1_raw
```

---

## ⚠️ GESTIONE ANOMALIE

### CODIFI-A01: Multi-Cliente Non Segmentato
```
Condizione: trovato solo 1 blocco ma testo suggerisce più clienti
Azione: Log warning per verifica manuale
Log: ANOMALIE_LOG.tipo = 'VALIDAZIONE', livello = 'ATTENZIONE'
```

### CODIFI-A02: Blocco Senza P.IVA
```
Condizione: blocco cliente senza P.IVA riconoscibile
Azione: INSERIRE con partita_iva = NULL
Log: ANOMALIE_LOG.tipo = 'LOOKUP', livello = 'CRITICO'
```

### CODIFI-A03: Ordini Duplicati
```
Condizione: stesso numero ordine in blocchi diversi
Azione: Aggiungere suffisso "_N" al numero ordine
Log: ANOMALIE_LOG.tipo = 'VALIDAZIONE', livello = 'INFO'
```

---

## 🧪 TEST CASES

### TC-CODIFI-01: Documento Singolo Cliente
```
Input: PDF con 1 solo destinatario
Expected:
  - 1 record in PDF_ORDINI
  - segment_codifi restituisce 1 blocco
```

### TC-CODIFI-02: Documento Multi-Cliente
```
Input: PDF con 3 destinatari
Expected:
  - 3 record in PDF_ORDINI
  - Stesso filename, id_pdf diversi
  - n_righe specifico per ogni blocco
```

### TC-CODIFI-03: Segmentazione Corretta
```
Input: PDF multi-cliente
Expected per ogni blocco:
  - Header completo
  - Prodotti associati al cliente corretto
  - Nessun mix di dati tra clienti
```

---

## 🔑 LOOKUP FARMACIA

### ⚠️ IMPORTANTE: Fase di Lookup
Il lookup della farmacia **NON** avviene in fase di estrazione, ma in fase di **popolamento del database**.

### Indirizzo Concatenato per Lookup
```
Formato: {Indirizzo} + {Numero Civico} + {CAP} + {Località} + {Provincia}
Esempio: "VIA ROMA 123 00100 ROMA RM"

Campi utilizzati (estratti dal PDF per ogni blocco cliente):
- indirizzo_raw → Indirizzo + Numero Civico
- cap_raw → CAP
- citta_raw → Località
- provincia_raw → Provincia

Match: Confronto fuzzy con dati anagrafica farmacie
Soglia: >= 80% per match valido
```

### Processo Lookup in Fase DB
```
1. Prima chiave: P.IVA (se presente) → Ricerca diretta
2. Se P.IVA non trovata → Lookup per indirizzo concatenato
3. Match fuzzy su: indirizzo + CAP + città + provincia
4. Risultato: MIN_ID della farmacia corrispondente
```

### Nota Multi-Cliente
```
IMPORTANTE: Per documenti CODIFI multi-cliente, il lookup viene
eseguito SEPARATAMENTE per ogni blocco cliente identificato.
Ogni blocco può avere esito lookup diverso.
```

---

## 📝 NOTE IMPLEMENTAZIONE

### Wrapper Multi-Cliente
```python
def extract_codifi(text: str, lines: List[str]) -> List[Dict]:
    """
    Estrattore CODIFI v2.0
    RESTITUISCE LISTA (non singolo dict) per supporto multi-cliente.
    """
    # Segmenta
    blocks = segment_codifi(text, lines)
    
    results = []
    for block in blocks:
        block_text = '\n'.join(block['lines'])
        block_lines = block['lines']
        
        # Estrai dati per questo blocco
        data = extract_codifi_single(block_text, block_lines)
        data['vendor'] = 'CODIFI'
        results.append(data)
    
    return results  # Lista di dict!


def extract_codifi_single(text: str, lines: List[str]) -> Dict:
    """Estrae dati da singolo blocco CODIFI."""
    data = {'righe': []}
    # ... implementazione regole CODIFI-H*, CODIFI-T*
    return data
```

### Gestione in Workflow
```python
# Nel main extraction loop:
if vendor == 'CODIFI':
    orders_data = extract_codifi(text, lines)  # Lista
else:
    orders_data = [extractor(text, lines)]     # Singolo → Lista

# Ora orders_data è sempre una lista
for data in orders_data:
    id_pdf = db.add_pdf_ordine(id_estrazione, data)
    db.add_to_raw(id_pdf, data['righe'])
```

---

**Documento**: REGOLE_CODIFI.md
**Versione**: 2.1
**Ultima modifica**: 6 Gennaio 2026
**Nota**: v2.1 - Rimossi riferimenti filename, aggiunta sezione LOOKUP
