> ⏳ **FASE 2 - IN ATTESA**: Questo vendor sarà implementato dopo il completamento dei test sulla Fase 1.

# 📋 REGOLE ESTRAZIONE: CHIESI

**Vendor**: Chiesi Italia S.p.A.
**Versione**: 3.2
**Data**: 6 Gennaio 2026
**P.IVA Vendor**: 02944970348 (da escludere)

---

## 🔍 IDENTIFICAZIONE DOCUMENTO

### ⚠️ IMPORTANTE: Detection Basata su Contenuto PDF
Il nome del file **NON** deve essere usato come criterio di identificazione vendor.
La detection deve basarsi **ESCLUSIVAMENTE** sul contenuto del PDF.

### Pattern di Riconoscimento (SOLO contenuto PDF)
```
MUST contain: "Chiesi Italia S.p.A."
AND (
    "Conferma Ordine" OR
    contains "P.IVA 02944970348"
)
```

### Esempio Nome File (solo per riferimento, NON usato per detection)
- `O-426505_ANALYZED.pdf`
- `O-426505.pdf`

---

## 📄 STRUTTURA DOCUMENTO

### Layout
- **Tipo**: Colonne verticali
- **Header**: 2 sezioni con offset fissi
- **Tabella**: Colonne verticali (non righe orizzontali)

### Mappa Righe (pdftotext)
```
SEZIONE 1 (righe 4-11 etichette, 13-20 valori) - OFFSET 9
├── Riga 4:  "Agente"            → Riga 13: valore
├── Riga 9:  "Cliente consegna"  → Riga 18: valore
├── Riga 10: "Indirizzo consegna"→ Riga 19: valore
└── Riga 11: "Dilazione"         → Riga 20: valore

SEZIONE 2 (righe 23-30 etichette, 26-33 valori) - OFFSET 3
├── Riga 23: "Codice cliente"    → Riga 26: valore
├── Riga 29: "P.IVA"             → Riga 32: valore
└── Riga 30: "Cap e Località"    → Riga 33: valore
```

---

## 📐 REGOLE ESTRAZIONE HEADER

### CHIESI-H01: Numero Ordine
```
Pattern: text "Ordine\s+N[°.:]*\s*(\S+)"
Output: TO_RAW.numero_ordine (testo integrale)
Normalizzazione: nessuna (solo in Fase 4)
Note: Estrazione SOLO da contenuto PDF, filename ignorato
```

### CHIESI-H02: Data Ordine
```
Pattern: "Data\s+ordine[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"
         OR "(\d{4}-\d{2}-\d{2})" (ISO format)
Output: PDF_ORDINI.data_ordine_raw (formato originale)
```

### CHIESI-H03: Agente
```
Posizione: Indice "Agente" + OFFSET 9
Validazione: re.match(r'^[A-Z][A-Z\s]+$', valore)
Output: PDF_ORDINI.nome_agente
```

### CHIESI-H04: Cliente Consegna (Ragione Sociale)
```
Posizione: Indice "Cliente consegna" + OFFSET 9
Output: PDF_ORDINI.ragione_sociale_raw
Limite: 50 caratteri
```

### CHIESI-H05: Indirizzo Consegna
```
Posizione: Indice "Indirizzo consegna" + OFFSET 9
Output: PDF_ORDINI.indirizzo_raw
Limite: 50 caratteri
```

### CHIESI-H06: P.IVA Cliente
```
Posizione: Indice "P.IVA" + OFFSET 3
Validazione: re.match(r'^\d{11}$', valore)
ESCLUSIONE: valore != '02944970348' (P.IVA Chiesi)
Output: PDF_ORDINI.partita_iva
```

### CHIESI-H07: CAP e Località
```
Posizione: Indice "Cap e Località" + OFFSET 3
Pattern: "IT-?(\d{5})\s+([A-Z\s]+)\s+([A-Z]{2})"
Output:
  - PDF_ORDINI.cap_raw = gruppo 1
  - PDF_ORDINI.citta_raw = gruppo 2
  - PDF_ORDINI.provincia_raw = gruppo 3
```

### CHIESI-H08: Dilazione Pagamento
```
Posizione: Indice "Dilazione" + OFFSET 9
Pattern: primi 3 caratteri numerici di "060R"
Calcolo: int(valore[:3]) → giorni
Output: PDF_ORDINI.condizioni_pagamento = "60 gg"
```

### CHIESI-H09: Codice Cliente
```
Posizione: Indice "Codice cliente" + OFFSET 3
Pattern: "00\d{8}" (10 cifre con prefisso 00)
Output: PDF_ORDINI.codice_cliente
```

---

## 📊 REGOLE ESTRAZIONE TABELLA PRODOTTI

### Struttura Colonne Verticali
```
Riga 43: "AIC/PARAF"      → Righe 45-56:  lista AIC
Riga 59: "CODICE"         → Righe 60-71:  codici interni
Riga 73: "PRODOTTO"       → Righe 74-85:  descrizioni
Righe 87-100:             → "DATA CONSEGNA"
Righe 102-115:            → "Q.TA'" (quantità)
Righe 117-132:            → "Q.TA' SCONTO S.M." (omaggi)
Righe 133-144:            → percentuali sconto
Righe 146-160:            → "PREZZO CESSIONE"
Righe 162-176:            → "TOTALE"
```

### CHIESI-T01: Parsing Sezioni
```python
# State machine per sezioni
section = None
for i, line in enumerate(lines):
    ls = line.strip()
    if ls == 'AIC/PARAF': section = 'aic'; continue
    elif ls == 'CODICE': section = 'codice'; continue
    elif ls == 'PRODOTTO': section = 'prodotto'; continue
    elif ls == 'DATA CONSEGNA': section = 'data'; continue
    elif ls == "Q.TA'": section = 'qty'; continue
    elif ls == "Q.TA' SCONTO S.M.": section = 'omaggio'; continue
    elif ls == 'PREZZO CESSIONE': section = 'prezzo'; continue
    # ... raccogliere valori per sezione
```

### CHIESI-T02: Codice AIC
```
Pattern: re.match(r'^[09]\d{8}$', valore)
Accettati:
  - 9 cifre che iniziano con 0 → AIC standard
  - 9 cifre che iniziano con 9 → Parafarmaco
Output: TO_RAW.codice_raw (senza padding)
Flag: TO_RAW.flag_espositore = False
```

### CHIESI-T03: Codice Espositore
```
Pattern: contiene "ESP" OR "EXP" OR "EXPO"
         OR re.match(r'^[A-Z]{2,3}\d+$', valore)
Output: TO_RAW.codice_raw (testo originale)
Flag: TO_RAW.flag_espositore = True
Note: NON applicare padding a 9 cifre
```

### CHIESI-T04: Descrizione Prodotto
```
Sezione: 'prodotto'
Limite: 40 caratteri
Output: TO_RAW.descrizione
```

### CHIESI-T05: Data Consegna
```
Sezione: 'data'
Pattern: "(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"
Output: TO_RAW.data_consegna_raw (formato originale)
```

### CHIESI-T06: Quantità Venduta
```
Sezione: 'qty'
Pattern: re.match(r'^\d+$', valore) AND int(valore) < 10000
Output: TO_RAW.quantita_raw
```

### CHIESI-T07: Quantità Omaggio (Sconto Merce)
```
Sezione: 'omaggio'
Pattern: re.match(r'^\d+$', valore)
Default: 0 se vuoto
Output: TO_RAW.quantita_omaggio_raw
```

### CHIESI-T08: Sconto Percentuale
```
Pattern: "(\d+[,.]?\d*)\s*%?"
Conversione: float(valore.replace(',', '.').replace('%', ''))
Output: TO_RAW.sconto1_raw
```

### CHIESI-T09: Prezzo Cessione
```
Pattern: "(\d+[,.]?\d*)\s*€?"
Conversione: float(valore.replace(',', '.').replace('€', ''))
Output: TO_RAW.prezzo_netto_raw
```

---

## ⚠️ GESTIONE ANOMALIE

### CHIESI-A01: P.IVA Vendor
```
Condizione: P.IVA == '02944970348'
Azione: IGNORARE (è P.IVA Chiesi, non cliente)
Log: ANOMALIE_LOG.tipo = 'PIVA_VENDOR'
```

### CHIESI-A02: Espositore
```
Condizione: flag_espositore = True
Azione: INSERIRE in TO_RAW con flag
Log: ANOMALIE_LOG.tipo = 'ESPOSITORE', livello = 'ATTENZIONE'
```

### CHIESI-A03: Codice Non Riconosciuto
```
Condizione: codice non match AIC né espositore
Azione: INSERIRE con flag_no_aic = True
Log: ANOMALIE_LOG.tipo = 'AIC', livello = 'CRITICO'
```

---

## 🧪 TEST CASES

### TC-CHIESI-01: Ordine Standard
```
Input: O-426505_ANALYZED.pdf
Expected:
  - numero_ordine: "O-426505"
  - partita_iva: "13027670960" (NON 02944970348)
  - ragione_sociale_raw: "P.FCIA AERIALS PHARMA S.A.S."
  - indirizzo_raw: "VIA LORENTEGGIO 44"
  - cap_raw: "20146"
  - citta_raw: "MILANO"
  - provincia_raw: "MI"
  - condizioni_pagamento: "60 gg"
  - n_righe: 12
```

### TC-CHIESI-02: Verifica AIC
```
Input: Prima riga prodotto
Expected:
  - codice_raw: "049582012"
  - flag_espositore: False
  - flag_no_aic: False
```

### TC-CHIESI-03: Verifica Quantità e Prezzo
```
Input: Prima riga prodotto
Expected:
  - quantita_raw: "24"
  - sconto1_raw: "35.00" (o "35,00")
  - prezzo_netto_raw: valore estratto
```

---

## 🔑 LOOKUP FARMACIA

### ⚠️ IMPORTANTE: Fase di Lookup
Il lookup della farmacia **NON** avviene in fase di estrazione, ma in fase di **popolamento del database**.

### Indirizzo Concatenato per Lookup
```
Formato: {Indirizzo} + {Numero Civico} + {CAP} + {Località} + {Provincia}
Esempio: "VIA LORENTEGGIO 44 20146 MILANO MI"

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
1. Prima chiave: P.IVA (se presente e != P.IVA vendor) → Ricerca diretta
2. Se P.IVA non trovata → Lookup per indirizzo concatenato
3. Match fuzzy su: indirizzo + CAP + città + provincia
4. Risultato: MIN_ID della farmacia corrispondente
```

### Nota P.IVA Vendor
```
IMPORTANTE: Escludere P.IVA 02944970348 (è P.IVA Chiesi, non cliente)
Se rilevata, ignorare e usare lookup per indirizzo.
```

---

## 📝 NOTE IMPLEMENTAZIONE

### Dipendenze
```python
import re
from typing import List, Dict
```

### Funzione Estrattore
```python
def extract_chiesi(text: str, lines: List[str]) -> Dict:
    """
    Estrattore CHIESI v3.1
    Applica SOLO regole CHIESI-*.
    """
    data = {
        'vendor': 'CHIESI',
        'righe': []
    }
    # ... implementazione regole CHIESI-*
    return data
```

---

**Documento**: REGOLE_CHIESI.md
**Versione**: 3.2
**Ultima modifica**: 6 Gennaio 2026
**Nota**: v3.2 - Rimossi riferimenti filename, aggiunta sezione LOOKUP
