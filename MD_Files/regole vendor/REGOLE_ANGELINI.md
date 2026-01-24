# 📋 REGOLE ESTRAZIONE: ANGELINI

**Vendor**: ACRAF S.p.A. (Angelini Pharma)
**Versione**: 2.1
**Data**: 6 Gennaio 2026
**Identificativo**: Transfer Order ACRAF

---

## 🔍 IDENTIFICAZIONE DOCUMENTO

### ⚠️ IMPORTANTE: Detection Basata su Contenuto PDF
Il nome del file **NON** deve essere usato come criterio di identificazione vendor.
La detection deve basarsi **ESCLUSIVAMENTE** sul contenuto del PDF.

### Pattern di Riconoscimento (SOLO contenuto PDF)
```
MUST contain: "ACRAF" OR "Angelini"
AND (
    "Transfer Order" OR
    "T.O."
)
```

### Esempio Nome File (solo per riferimento, NON usato per detection)
- `T_O__ACRAF_-_2008372205_-_CANNELLA_SAS.pdf`
- `TO_ACRAF_2008372926.pdf`

---

## 📄 STRUTTURA DOCUMENTO

### Layout
- **Tipo**: Tabella orizzontale standard
- **Header**: Blocco superiore con dati cliente
- **Tabella**: Righe orizzontali con colonne fisse
- **Particolarità**: ID MIN presente direttamente

### Sezioni
```
HEADER
├── Dati Destinatario (ragione sociale, indirizzo, CAP, città, provincia)
├── Dati Ordine (numero, data)
├── ID MIN (CodTracciaturaCliente) ← PRESENTE!
└── Condizioni pagamento

TABELLA PRODOTTI
├── Codice AIC | Descrizione | Qtà | Prezzo | Sconto1 | Sconto2 | ...
```

---

## 📐 REGOLE ESTRAZIONE HEADER

### ANGELINI-H01: Numero Ordine
```
Pattern: "N[°.]?\s*[Oo]rdine[:\s]*(\d{10})"
Formato: 10 cifre
Output: PDF_ORDINI.numero_ordine
Note: Estrazione SOLO da contenuto PDF, filename ignorato
```

### ANGELINI-H02: Data Ordine
```
Pattern: "Data\s+[Oo]rdine[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"
Output: PDF_ORDINI.data_ordine_raw
```

### ANGELINI-H03: Data Consegna
```
Pattern: "Data\s+[Cc]onsegna[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"
Output: PDF_ORDINI.data_consegna_raw
```

### ANGELINI-H04: ID MIN (CodTracciaturaCliente)
```
Pattern: "ID\s*MIN[:\s]*(\d{6,9})"
         OR "Cod[.\s]*Tracciatura[:\s]*(\d+)"
IMPORTANTE: Angelini fornisce ID MIN direttamente
Output: PDF_ORDINI.id_min (no lookup necessario!)
```

### ANGELINI-H05: Ragione Sociale
```
Pattern: "Destinatario[:\s]*([A-Z][^\n]+)"
         OR "Ragione\s+Sociale[:\s]*([^\n]+)"
Output: PDF_ORDINI.ragione_sociale_raw
Limite: 50 caratteri
```

### ANGELINI-H06: Indirizzo
```
Pattern: "Indirizzo[:\s]*([^\n]+)"
         OR "Via[/\s]*Piazza[:\s]*([^\n]+)"
Output: PDF_ORDINI.indirizzo_raw
Limite: 50 caratteri
```

### ANGELINI-H07: CAP
```
Pattern: "CAP[:\s]*(\d{5})"
         OR nel blocco indirizzo "(\d{5})\s+[A-Z]"
Output: PDF_ORDINI.cap_raw
```

### ANGELINI-H08: Città
```
Pattern: "Città[:\s]*([A-Z][A-Za-z\s]+)"
         OR "Località[:\s]*([^\n]+)"
Output: PDF_ORDINI.citta_raw
```

### ANGELINI-H09: Provincia
```
Pattern: "Prov[.\s:]*([A-Z]{2})"
         OR "\(([A-Z]{2})\)"
Output: PDF_ORDINI.provincia_raw
```

### ANGELINI-H10: P.IVA Cliente
```
Pattern: "P[.\s]*IVA[:\s]*(\d{11})"
Output: PDF_ORDINI.partita_iva
```

### ANGELINI-H11: Condizioni Pagamento
```
Pattern: "Pagamento[:\s]*(\d+)\s*(?:gg|giorni)"
         OR "Dilazione[:\s]*(\d+)"
Output: PDF_ORDINI.condizioni_pagamento = "XX gg"
```

---

## 📊 REGOLE ESTRAZIONE TABELLA PRODOTTI

### Struttura Righe
```
| Codice | Descrizione | Qtà | Prezzo | Sc1 | Sc2 | Sc3 | Sc4 | Totale |
```

### ANGELINI-T01: Identificazione Tabella
```
Inizio: riga contiene "Codice" AND "Descrizione" AND "Quantità"
Fine: riga vuota o "Totale Ordine"
```

### ANGELINI-T02: Codice AIC
```
Pattern: "^(\d{9})$" (9 cifre)
         OR "^0?(\d{8})$" (8 cifre → padding a 9)
Output: TO_RAW.codice_raw
```

### ANGELINI-T03: Descrizione
```
Posizione: seconda colonna
Limite: 40 caratteri
Output: TO_RAW.descrizione
```

### ANGELINI-T04: Quantità
```
Pattern: "(\d+)" in colonna quantità
Output: TO_RAW.quantita_raw
```

### ANGELINI-T05: Sconti Cascata
```
PARTICOLARITÀ ANGELINI: Sconti multipli separati da "+"
Esempio: "35+10+5" significa sconto1=35%, sconto2=10%, sconto3=5%

Pattern: "(\d+(?:[,\.]\d+)?)\s*\+?\s*"
Parsing:
  sconti = valore.split('+')
  sconto1 = float(sconti[0]) if len(sconti) > 0 else 0
  sconto2 = float(sconti[1]) if len(sconti) > 1 else 0
  sconto3 = float(sconti[2]) if len(sconti) > 2 else 0
  sconto4 = float(sconti[3]) if len(sconti) > 3 else 0

Output: TO_RAW.sconto1_raw, sconto2_raw, sconto3_raw, sconto4_raw
```

### ANGELINI-T06: Prezzo Netto
```
Pattern: "(\d+[,\.]\d{2})" in colonna prezzo
Output: TO_RAW.prezzo_netto_raw
```

### ANGELINI-T07: Codici Speciali
```
Pattern: contiene "ESP" OR "EXP" OR "BANCO" OR "EXPO"
Flag: TO_RAW.flag_espositore = True
Output: TO_RAW.codice_raw (testo originale, no padding)
```

---

## ⚠️ GESTIONE ANOMALIE

### ANGELINI-A01: Espositore/Banco
```
Condizione: codice contiene ESP/EXP/BANCO/EXPO
Azione: INSERIRE con flag_espositore = True
Log: ANOMALIE_LOG.tipo = 'ESPOSITORE', livello = 'ATTENZIONE'
```

### ANGELINI-A02: Sconto Cascata Invalido
```
Condizione: sconto contiene caratteri non numerici (escluso +,.)
Azione: Log warning, usa 0 come default
Log: ANOMALIE_LOG.tipo = 'VALIDAZIONE', livello = 'INFO'
```

---

## 🧪 TEST CASES

### TC-ANGELINI-01: Ordine Standard
```
Input: T_O__ACRAF_-_2008372205_-_CANNELLA_SAS.pdf
Expected:
  - numero_ordine: "2008372205"
  - id_min: presente (es: "123456789")
  - n_righe: variabile
```

### TC-ANGELINI-02: Sconti Cascata
```
Input: Riga con sconto "35+10"
Expected:
  - sconto1_raw: "35"
  - sconto2_raw: "10"
  - sconto3_raw: "0"
  - sconto4_raw: "0"
```

---

## 🔑 LOOKUP FARMACIA

### ⚠️ IMPORTANTE: Fase di Lookup
Il lookup della farmacia **NON** avviene in fase di estrazione, ma in fase di **popolamento del database**.

### Particolarità ANGELINI: ID MIN Diretto
```
A differenza di altri vendor, ANGELINI fornisce l'ID MIN direttamente nel documento.
Questo SEMPLIFICA il lookup ma NON lo elimina.
```

### Processo Lookup in Fase DB
```
1. ID MIN presente → Verifica esistenza in anagrafica
2. Se ID MIN valido → Usa direttamente
3. Se ID MIN non trovato → Fallback su indirizzo concatenato
```

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

---

## 📝 NOTE IMPLEMENTAZIONE

### Vantaggio ID MIN
```
A differenza di MENARINI, ANGELINI fornisce l'ID MIN direttamente.
Questo SEMPLIFICA il lookup (verifica esistenza anziché ricerca).
In fase DB, verificare che l'ID MIN esista nell'anagrafica.
Se non esiste, fallback su lookup per indirizzo concatenato.
```

### Funzione Estrattore
```python
def extract_angelini(text: str, lines: List[str]) -> Dict:
    """
    Estrattore ANGELINI v2.0
    Applica SOLO regole ANGELINI-*.
    """
    data = {
        'vendor': 'ANGELINI',
        'righe': []
    }
    # ... implementazione regole ANGELINI-*
    return data
```

---

**Documento**: REGOLE_ANGELINI.md
**Versione**: 2.1
**Ultima modifica**: 6 Gennaio 2026
**Nota**: v2.1 - Rimossi riferimenti filename, aggiunta sezione LOOKUP
