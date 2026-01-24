> ⏳ **FASE 2 - IN ATTESA**: Questo vendor sarà implementato dopo il completamento dei test sulla Fase 1.

# 📋 REGOLE ESTRAZIONE: OPELLA

**Vendor**: Opella Healthcare Italy S.r.l. (ex Sanofi Consumer)
**Versione**: 1.1
**Data**: 6 Gennaio 2026
**Identificativo**: "Informazioni sull'ordine"

---

## 🔍 IDENTIFICAZIONE DOCUMENTO

### ⚠️ IMPORTANTE: Detection Basata su Contenuto PDF
Il nome del file **NON** deve essere usato come criterio di identificazione vendor.
La detection deve basarsi **ESCLUSIVAMENTE** sul contenuto del PDF.

### Pattern di Riconoscimento (SOLO contenuto PDF)
```
MUST contain: "Opella" OR "Informazioni sull'ordine"
AND "Healthcare"
```

### Esempio Nome File (solo per riferimento, NON usato per detection)
- `OPELLA_20251022.pdf`
- `Opella_Healthcare_TO.pdf`

---

## 📄 STRUTTURA DOCUMENTO

### Layout
- **Tipo**: Formato "Informazioni sull'ordine"
- **Header**: Box informativi con etichette
- **Tabella**: Griglia prodotti standard

### Sezioni
```
INTESTAZIONE
├── Logo Opella
├── "Informazioni sull'ordine"
└── Numero documento

DATI CLIENTE
├── Ragione sociale
├── Indirizzo completo
└── Riferimenti (P.IVA, etc.)

DETTAGLI ORDINE
├── Data ordine
├── Data consegna richiesta
└── Condizioni

TABELLA PRODOTTI
├── Articolo | Descrizione | Qtà | Prezzo Unit. | Importo
```

---

## 📐 REGOLE ESTRAZIONE HEADER

### OPELLA-H01: Numero Ordine
```
Pattern: "Ordine\s+(?:n[°.]?|N\.?)[:\s]*(\S+)"
         OR "Documento[:\s]*(\S+)"
Output: PDF_ORDINI.numero_ordine
```

### OPELLA-H02: Data Ordine
```
Pattern: "Data\s+ordine[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"
         OR "Emesso\s+il[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"
Output: PDF_ORDINI.data_ordine_raw
```

### OPELLA-H03: Data Consegna
```
Pattern: "Consegna\s+richiesta[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"
         OR "Data\s+consegna[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"
Output: PDF_ORDINI.data_consegna_raw
```

### OPELLA-H04: Ragione Sociale
```
Pattern: dopo "Cliente:" OR "Destinatario:" → prima riga non vuota
         OR "Ragione\s+Sociale[:\s]*([^\n]+)"
Output: PDF_ORDINI.ragione_sociale_raw
Limite: 50 caratteri
```

### OPELLA-H05: Indirizzo
```
Pattern: riga contenente via/piazza/corso dopo ragione sociale
         OR "Indirizzo[:\s]*([^\n]+)"
Output: PDF_ORDINI.indirizzo_raw
Limite: 50 caratteri
```

### OPELLA-H06: CAP
```
Pattern: "(\d{5})" prima di città
         OR "CAP[:\s]*(\d{5})"
Output: PDF_ORDINI.cap_raw
```

### OPELLA-H07: Città
```
Pattern: dopo CAP, prima di provincia
         OR "Città[:\s]*([A-Za-z\s]+)"
Output: PDF_ORDINI.citta_raw
```

### OPELLA-H08: Provincia
```
Pattern: "\(([A-Z]{2})\)" OR "Prov[.\s:]*([A-Z]{2})"
Output: PDF_ORDINI.provincia_raw
```

### OPELLA-H09: P.IVA
```
Pattern: "P[.\s]*IVA[:\s]*(?:IT)?(\d{11})"
         OR "Partita\s+IVA[:\s]*(\d{11})"
Output: PDF_ORDINI.partita_iva
```

### OPELLA-H10: Condizioni Pagamento
```
Pattern: "Pagamento[:\s]*([^\n]+)"
         OR "Termini[:\s]*(\d+)\s*(?:gg|giorni)"
Output: PDF_ORDINI.condizioni_pagamento
```

---

## 📊 REGOLE ESTRAZIONE TABELLA PRODOTTI

### OPELLA-T01: Identificazione Tabella
```
Inizio: riga contiene "Articolo" OR "Codice" AND "Descrizione"
Fine: "Totale" OR riga vuota dopo ultimo prodotto
```

### OPELLA-T02: Codice Articolo/AIC
```
Pattern: "^(\d{9})$" (AIC 9 cifre)
         OR "^(\d{6,8})$" (codice interno → verifica mapping)
Output: TO_RAW.codice_raw

Se codice < 9 cifre:
  - Cercare AIC in descrizione
  - Oppure flag_no_aic = True se non trovato
```

### OPELLA-T03: Descrizione
```
Posizione: colonna "Descrizione" o "Prodotto"
Limite: 40 caratteri
Output: TO_RAW.descrizione
```

### OPELLA-T04: Quantità
```
Pattern: "(\d+)" in colonna Qtà/Quantità
Output: TO_RAW.quantita_raw
```

### OPELLA-T05: Prezzo Unitario
```
Pattern: "(\d+[,\.]\d{2,4})\s*(?:EUR|€)?"
Output: TO_RAW.prezzo_netto_raw
```

### OPELLA-T06: Sconto
```
Pattern: "(\d+[,\.]\d*)\s*%"
Default: 0 se non presente
Output: TO_RAW.sconto1_raw
```

### OPELLA-T07: Importo Riga
```
Pattern: "(\d+[,\.]\d{2})" in ultima colonna
Uso: verifica coerenza (prezzo * qtà * (1-sconto))
Output: (non salvato, solo validazione)
```

---

## ⚠️ GESTIONE ANOMALIE

### OPELLA-A01: Codice Non AIC
```
Condizione: codice articolo non corrisponde a formato AIC
Azione: Cercare AIC nella descrizione
        Se non trovato: flag_no_aic = True
Log: ANOMALIE_LOG.tipo = 'AIC', livello = 'ATTENZIONE'
```

### OPELLA-A02: Formato "Informazioni" Non Standard
```
Condizione: documento non segue layout atteso
Azione: Fallback a parsing generico
Log: ANOMALIE_LOG.tipo = 'VALIDAZIONE', livello = 'INFO'
```

---

## 🧪 TEST CASES

### TC-OPELLA-01: Ordine Standard
```
Input: OPELLA_Healthcare_TO.pdf
Expected:
  - Identificazione corretta vendor = 'OPELLA'
  - Header completo
  - Tabella prodotti estratta
```

### TC-OPELLA-02: Codice Articolo vs AIC
```
Input: Riga con codice interno 6 cifre
Expected:
  - Tentativo ricerca AIC in descrizione
  - Se non trovato: flag_no_aic = True
```

---

## 🔑 LOOKUP FARMACIA

### ⚠️ IMPORTANTE: Fase di Lookup
Il lookup della farmacia **NON** avviene in fase di estrazione, ma in fase di **popolamento del database**.

### Indirizzo Concatenato per Lookup
```
Formato: {Indirizzo} + {Numero Civico} + {CAP} + {Località} + {Provincia}
Esempio: "VIA ROMA 123 00100 ROMA RM"

Campi utilizzati (estratti dal PDF):
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

---

## 📝 NOTE IMPLEMENTAZIONE

### Riconoscimento Layout
```python
def is_opella_format(text: str) -> bool:
    """Verifica se il documento è formato Opella."""
    indicators = [
        'Informazioni sull\'ordine',
        'Opella Healthcare',
        'Opella Italy'
    ]
    return any(ind.lower() in text.lower() for ind in indicators)
```

### Funzione Estrattore
```python
def extract_opella(text: str, lines: List[str]) -> Dict:
    """
    Estrattore OPELLA v1.0
    Applica SOLO regole OPELLA-*.
    """
    data = {
        'vendor': 'OPELLA',
        'righe': []
    }
    # ... implementazione regole OPELLA-*
    return data
```

### AIC nella Descrizione
```python
def find_aic_in_description(desc: str) -> str:
    """Cerca AIC 9 cifre nella descrizione."""
    match = re.search(r'\b(0\d{8})\b', desc)
    return match.group(1) if match else ''
```

---

**Documento**: REGOLE_OPELLA.md
**Versione**: 1.1
**Ultima modifica**: 6 Gennaio 2026
**Nota**: v1.1 - Rimossi riferimenti filename, aggiunta sezione LOOKUP
