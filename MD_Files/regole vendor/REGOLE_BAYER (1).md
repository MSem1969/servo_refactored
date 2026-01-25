# 📋 REGOLE ESTRAZIONE: BAYER

**Vendor**: Bayer S.p.A.
**Versione**: 3.0
**Data**: 25 Gennaio 2026
**Identificativo**: Transfer Order / BAYER

---

## 🔍 IDENTIFICAZIONE DOCUMENTO

### Pattern di Riconoscimento
```
MUST contain: "Bayer" OR "BAYER"
AND (
    "Transfer Order" OR
    "TRANSFER ORDER" OR
    "COOPERATIVA/ GROSSISTA" OR
    "NUM. PROP. D'ORDINE"
)

IMPORTANTE: L'identificazione avviene SOLO tramite contenuto testuale,
NON tramite nome file.
```

### Esempio Identificazione
```
Testo PDF contiene:
  "Bayer S.p.A."
  "COOPERATIVA/ GROSSISTA"
  "NUM. PROP. D'ORDINE"
→ Vendor riconosciuto: BAYER
```

---

## 📄 STRUTTURA DOCUMENTO

### Layout
- **Tipo**: Transfer Order con logo Bayer
- **Header**: 
  - Blocco COOPERATIVA/GROSSISTA (distributore)
  - Blocco CLIENTE (farmacia destinataria)
  - Dati ordine
- **Tabella**: Righe prodotti con colonne fisse
- **Particolarità**: 
  - Colonna "Merce Sconto Extra" specifica BAYER
  - Espositori con codici a 6 cifre

### Sezioni
```
LOGO BAYER + TRANSFER ORDER

COOPERATIVA/GROSSISTA (Distributore)
├── Codice (ID numerico + SAP)
├── Ragione Sociale
├── P.IVA + C.F.
├── Indirizzo + Città
└── Email

CLIENTE (Farmacia destinataria)
├── Codice (ID numerico + SAP)
├── Ragione Sociale
├── P.IVA + C.F.
├── Indirizzo + Città
└── (Email se presente)

DATI ORDINE
├── NUM. PROP. D'ORDINE (formato IT25O-XXXXX)
└── DATA ACQUISIZIONE (GG mmm AAAA)

TABELLA PRODOTTI
├── ARTICOLO (codice prodotto + descrizione)
├── Q.tà Vendita
├── Prezzo Cessione
├── Q.tà Merce Sconto
├── Merce Sconto Extra
├── CONSEGNE (colonne date - es: "5 nov 2025", "26 nov 2025")
└── CONDIZIONI PAGAMENTO PARTICOLARI
```

---

## 🗓️ DATE CONSEGNA MULTIPLE (v3.0)

### BAYER-DC01: Colonne Date nell'Header
```
PARTICOLARITÀ BAYER: Le date di consegna sono negli HEADER COLONNA.

Struttura tipica:
  CONSEGNE
  ┌─────────┬─────────┐
  │ 5 nov   │ 26 nov  │
  │ 2025    │ 2025    │
  └─────────┴─────────┘

Le quantità per riga sono posizionate sotto la colonna data corrispondente.
```

### BAYER-DC02: Stesso Prodotto con Date Diverse
```
REGOLA CRITICA: Se un prodotto ha quantità su DATE DIVERSE, creare RIGHE SEPARATE.

Esempio da PDF IT25O-20667:
  CITROSODINA GRAN. EFF 150 GR | Q.tà Vendita: 40 | 20 ott: 12 | 20 dic: 28

Risultato estrazione:
  Riga 1: CITROSODINA, qty=12, data_consegna=20/10/2025
  Riga 2: CITROSODINA, qty=28, data_consegna=20/12/2026

Ogni riga ha n_riga progressivo univoco.
```

### BAYER-DC03: Prodotto con Singola Data
```
Se un prodotto ha quantità su UNA SOLA colonna data:
  - Creare una singola riga
  - Data consegna dalla colonna che contiene la quantità

Esempio da PDF IT25O-23566:
  Supradyn Expert EspoB | Q.tà: 1 | 5 nov: vuoto | 26 nov: 1

Risultato: Riga con qty=1, data_consegna=26/11/2025
```

---

## 🎪 ESPOSITORI BAYER (v3.0)

### BAYER-ESP01: Espositori sono Prodotti AUTONOMI
```
IMPORTANTE: BAYER NON usa logica parent/child per espositori.

A differenza di ANGELINI/MENARINI:
  - Gli espositori BAYER sono prodotti AUTONOMI
  - NON ci sono righe "child" associate
  - L'espositore è un singolo articolo con il suo prezzo

Identificazione espositore (solo informativa):
  Keywords: EXPO, BANCO, DISPLAY, ESPOSITORE, CESTA, DBOX, FSTAND
  Flag: is_espositore = 1 (per tracciabilità, non per logica speciale)
```

### BAYER-ESP02: Codici AIC Espositori
```
ANOMALIA AIC: Espositori BAYER possono avere codici NON standard.

Esempi riscontrati:
  - 0091639224 (10 cifre) → Anomalia AIC-A01
  - 92035128 (8 cifre) → Anomalia AIC-A01
  - 91779360 (8 cifre) → Anomalia AIC-A01

Gestione:
  - Codice normalizzato con padding/troncamento
  - Anomalia AIC-A01 generata per revisione manuale
  - L'operatore può correggere il codice se errato
```

---

## 📐 REGOLE ESTRAZIONE HEADER

### BAYER-H01: Ragione Sociale Grossista
```
Sezione: COOPERATIVA/GROSSISTA
Posizione: Riga dopo il codice numerico/SAP
Estrazione: Prima riga testuale significativa dopo intestazione

Esempio:
  "1002338729 (SAP: 0005308522
   FARVIMA MEDICINALI S.P.A."
   
Pattern: Riga successiva a pattern "(\d{10})\s+\(SAP:"
Output: TO_RAW.grossista
Limite: 100 caratteri
```

### BAYER-H02: Ragione Sociale Cliente
```
Sezione: CLIENTE
Posizione: Riga dopo il codice numerico/SAP
Estrazione: Prima riga testuale dopo codice cliente

Esempio:
  "1002345057 (SAP: 0003346340)
   FARMACIA PICAZIO DR.NICOLETTA"

Pattern: Riga successiva a pattern "(\d{10})\s+\(SAP:"
Output: TO_RAW.ragione_sociale
Limite: 80 caratteri
```

### BAYER-H03: P.IVA Cliente
```
Sezione: CLIENTE
Pattern: "P\.IVA:\s*(\d{11})"
Validazione: 11 cifre esatte

Output: TO_RAW.partita_iva
```

### BAYER-H04: Indirizzo Cliente
```
Sezione: CLIENTE
Posizione: Riga dopo "P.IVA: ... - C.F.: ..."
Estrazione: Tutto il testo prima della riga città

Esempio:
  "P.IVA: 03011890617 - C.F.:PCZNLT61H68A243I
   VIA NAPOLI 240"

Output: TO_RAW.indirizzo
Limite: 60 caratteri
```

### BAYER-H05: Città e Provincia Cliente
```
Sezione: CLIENTE
Pattern città: Riga prima della parentesi provincia
Pattern provincia: "\(([A-Z]{2})\)"

Esempio:
  "ARZANO
   (NA)"

Output: 
  - TO_RAW.citta = "ARZANO"
  - TO_RAW.provincia = "NA"

Limiti:
  - citta: 50 caratteri
  - provincia: 2 caratteri
```

### BAYER-H06: Numero Ordine
```
Pattern: "NUM\.\s+PROP\.\s+D'ORDINE\s+(IT25O-\d+)"
Formato: IT25O-XXXXX (5 cifre)

Esempio: "NUM. PROP. D'ORDINE  IT25O-24440"

Output: TO_RAW.numero_ordine
```

### BAYER-H07: Data Ordine
```
Pattern: "DATA\s+ACQUISIZIONE\s+(\d{1,2})\s+(\w{3,9})\s+(\d{4})"
Formato input: "GG mmm AAAA"

Esempio: "DATA ACQUISIZIONE  7 nov 2025"

Conversione mesi italiani:
  gen→01, feb→02, mar→03, apr→04, mag→05, giu→06,
  lug→07, ago→08, set→09, ott→10, nov→11, dic→12

Output: TO_RAW.data_ordine
Formato output: DD/MM/YYYY
```

---

## 📊 REGOLE ESTRAZIONE TABELLA PRODOTTI

### BAYER-T01: Identificazione Tabella
```
Header tabella: riga contiene "ARTICOLO" AND "Q.tà Vendita" AND "Prezzo Cessione"
Inizio righe: dopo header tabella
Fine righe: fine documento o riga vuota
```

### BAYER-T02: Codice Prodotto (AIC)
```
Posizione: Prima colonna (ARTICOLO)
Pattern: "^(\d{6,9})$"

Gestione lunghezza:
  - 9 cifre → AIC standard (es: 025833068)
  - 8 cifre → padding con 0 a sinistra (es: 25833068 → 025833068)
  - 7 cifre → padding con 00 a sinistra (es: 2583306 → 002583306)
  - 6 cifre → ESPOSITORE (padding speciale)

IMPORTANTE: Espositori con codici a 6 cifre
Normalizzazione espositori (come ANGELINI):
  - Codice originale 6 cifre (es: 091639) → salvare in codice_originale
  - Codice normalizzato: padding con "5" iniziale → 500091639 (9 cifre)

Output:
  - TO_RAW.codice_aic = codice normalizzato (9 cifre)
  - TO_RAW.codice_originale = codice come da PDF
  - TO_RAW.is_espositore = 1 (se 6 cifre originali)

Esempio espositore:
  Input PDF: "0091639224" (10 cifre → probabilmente errore OCR)
  Se realmente 6 cifre: "091639"
  → codice_aic = "500091639"
  → codice_originale = "091639"
  → is_espositore = 1
```

### BAYER-T03: Descrizione Prodotto
```
Posizione: Dopo codice AIC, stessa riga o riga successiva
Estrazione: Tutto il testo tra codice e colonna quantità

Pattern espositori (identificazione aggiuntiva):
  - "Expo Banco" → espositore da banco
  - "ExpoB Mix" → confezione multipla
  - "Promo IT" → articolo promozionale

Output: TO_RAW.descrizione
Limite: 60 caratteri
```

### BAYER-T04: Quantità Vendita
```
Posizione: Colonna "Q.tà Vendita"
Pattern: "(\d+)"

Output: TO_RAW.q_venduta
```

### BAYER-T05: Prezzo Cessione
```
Posizione: Colonna "Prezzo Cessione"
Pattern: "€\s*([\d,]+)"
Formato: virgola come separatore decimale

Conversione: sostituire virgola con punto
Esempio: "€ 9,47" → 9.47

Output: TO_RAW.prezzo_netto
```

### BAYER-T06: Quantità Sconto Merce
```
Posizione: Colonna "Q.tà Merce Sconto"
Pattern: "(\d+)"

IMPORTANTE: Questa quantità va mappata come sconto merce.
La conversione a omaggio avviene in fase di generazione tracciato.

Output: TO_RAW.q_sconto_merce
```

### BAYER-T07: Merce Sconto Extra
```
Posizione: Colonna "Merce Sconto Extra"
Pattern: "(\d+)"

IMPORTANTE: Questa quantità rappresenta sconto merce aggiuntivo.
Va mappata separatamente, la gestione finale avviene in fase tracciato.

Output: TO_RAW.merce_sconto_extra (campo aggiuntivo BAYER)

NOTA: Alcuni ordini hanno questa colonna valorizzata, altri no.
      Default: 0 se colonna vuota o assente.
```

### BAYER-T08: Condizioni Pagamento
```
Posizione: Colonna "CONDIZIONI PAGAMENTO PARTICOLARI"
Pattern: "(\d+)\s*gg"
Estrazione: Solo valore numerico

Esempio: "60 gg" → 60

Output: TO_RAW.gg_dilazione
Default: 60 (se non trovato)
```

---

## ⚠️ GESTIONE ANOMALIE

### BAYER-A01: Ragione Sociale Grossista Non Trovata
```
Condizione: sezione COOPERATIVA/GROSSISTA non parsabile
Azione: Log warning, procedere con campo vuoto
Log: 
  - tipo_anomalia = 'GROSSISTA_MISSING'
  - livello = 'ATTENZIONE'
  - richiede_supervisione = 0
```

### BAYER-A02: P.IVA Cliente Assente
```
Condizione: P.IVA non trovata in sezione CLIENTE
Azione: Log error, lookup impossibile
Log: 
  - tipo_anomalia = 'PIVA_MISSING'
  - livello = 'ERRORE'
  - richiede_supervisione = 1
  - dettagli = 'Impossibile eseguire lookup anagrafica'
Blocco: Ordine passa in stato PENDING_REVIEW
```

### BAYER-A03: Codice AIC Formato Anomalo
```
Condizione: codice prodotto < 6 cifre o > 9 cifre
Azione: Log error, segnalare per verifica manuale
Log: 
  - tipo_anomalia = 'AIC_FORMATO'
  - livello = 'ATTENZIONE'
  - richiede_supervisione = 1
  - dettagli = codice estratto + lunghezza
```

### BAYER-A04: Numero Ordine Mancante
```
Condizione: pattern "NUM. PROP. D'ORDINE" non trovato
Azione: Log error, ordine non processabile
Log: 
  - tipo_anomalia = 'NUMERO_ORDINE_MISSING'
  - livello = 'ERRORE'
  - richiede_supervisione = 1
Blocco: Ordine non inserito in database
```

### BAYER-A05: Sconto Merce Extra Anomalo
```
Condizione: merce_sconto_extra > q_venduta * 5
Azione: Log warning, possibile errore OCR o dato anomalo
Log: 
  - tipo_anomalia = 'SCONTO_EXTRA_ANOMALO'
  - livello = 'ATTENZIONE'
  - richiede_supervisione = 1
  - dettagli = valore estratto
```

---

## 🧪 TEST CASES

### TC-BAYER-01: Ordine Standard Senza Sconti
```
Input: PDF IT25O-24440 (FARMACIA PICAZIO)

Expected Header:
  - grossista: "FARVIMA MEDICINALI S.P.A."
  - numero_ordine: "IT25O-24440"
  - ragione_sociale: "FARMACIA PICAZIO DR.NICOLETTA"
  - partita_iva: "03011890617"
  - indirizzo: "VIA NAPOLI 240"
  - citta: "ARZANO"
  - provincia: "NA"
  - data_ordine: "07/11/2025"
  - gg_dilazione: 60

Expected Righe (3):
  1. codice_aic: "025833068", codice_originale: "025833068"
     descrizione: "GYNO-CANESTEN CREMA VAG. 2% 30g"
     q_venduta: 32, q_sconto_merce: 0, merce_sconto_extra: 0
     prezzo_netto: 9.47, is_espositore: 0
  
  2. codice_aic: "050590037", codice_originale: "050590037"
     descrizione: "Iberogast N SOLU BT 100ml IT"
     q_venduta: 3, q_sconto_merce: 0, merce_sconto_extra: 0
     prezzo_netto: 16.44, is_espositore: 0
  
  3. codice_aic: "050590025", codice_originale: "050590025"
     descrizione: "Iberogast N SOLU BT 50ml IT"
     q_venduta: 3, q_sconto_merce: 0, merce_sconto_extra: 0
     prezzo_netto: 8.86, is_espositore: 0
```

### TC-BAYER-02: Ordine Con Sconto Merce
```
Input: PDF IT25O-24438 (FARMACIA DEL CASSANO)

Expected Righe (estratto):
  - codice_aic: "022760019"
    descrizione: "CANESTEN CREMA 1% 30g"
    q_venduta: 36
    q_sconto_merce: 0
    merce_sconto_extra: 0
    prezzo_netto: 8.54
```

### TC-BAYER-03: Ordine Con Date Consegna Multiple (v3.0)
```
Input: PDF IT25O-20667 (NUOVA FARMACIA BARONE SCALA)
Date colonne: "20 ott 2025", "20 dic 2026"

Expected Righe CITROSODINA (prodotto con 2 date):
  Riga 1:
    - codice_aic: "938181462"
    - descrizione: "CITROSODINA GRAN. EFF 150 GR"
    - quantita: 12
    - data_consegna: 20/10/2025

  Riga 2:
    - codice_aic: "938181462"
    - descrizione: "CITROSODINA GRAN. EFF 150 GR"
    - quantita: 28
    - data_consegna: 20/12/2026

Expected Righe Geffer (prodotto con 2 date):
  Riga 1: qty=12, data=20/10/2025
  Riga 2: qty=36, data=20/12/2026

Expected Righe GYNO-CANESTEN (prodotto con 2 date):
  Riga 1: qty=6, data=20/10/2025
  Riga 2: qty=30, data=20/12/2026

TOTALE RIGHE ORDINE: 11 (8 prodotti, 3 con date multiple)
```

### TC-BAYER-04: Espositore BAYER (v3.0)
```
Input: Riga "0091639224 Aspirina C20 TAEF Expo Banco 20 pz DP IT"

COMPORTAMENTO v3.0:
  - codice_aic: normalizzato (padding/troncamento)
  - codice_originale: "0091639224"
  - is_espositore: 1 (flag informativo per keyword "Expo Banco")
  - tipo_riga: "PRODOTTO_STANDARD" (NON parent/child!)
  - quantita: 1
  - prezzo_netto: 123.30
  - data_consegna: dalla colonna appropriata

ANOMALIA GENERATA:
  - codice: AIC-A01
  - messaggio: "AIC non conforme: 0091639224 (10 cifre invece di 9)"
  - livello: ERRORE
  - Richiede revisione manuale operatore

IMPORTANTE: L'espositore è un prodotto AUTONOMO, non ha righe child associate.
```

### TC-BAYER-05: Prodotto con Data Consegna Singola ma Diversa (v3.0)
```
Input: PDF IT25O-23566 (FARMACIA CROCE VERDE)
Date colonne: "5 nov 2025", "26 nov 2025"

Expected:
  - La maggior parte dei prodotti ha qty sotto "5 nov 2025"
  - Supradyn Expert EspoB Mix ha qty=1 sotto "26 nov 2025"

Risultato estrazione Supradyn Expert EspoB:
  - n_riga: (progressivo)
  - codice_aic: "92035128" (8 cifre → anomalia AIC-A01)
  - descrizione: "Supradyn Expert EspoB Mix 9p"
  - quantita: 1
  - data_consegna: 26/11/2025 (NON 05/11/2025!)
  - is_espositore: 1

IMPORTANTE: L'estrazione tabellare garantisce la corretta
            mappatura colonna → data consegna.
```

---

## 📝 NOTE IMPLEMENTAZIONE

### Differenze Chiave da Altri Vendor (v3.0)

```
1. DUE SOGGETTI:
   - COOPERATIVA/GROSSISTA (distributore intermedio)
   - CLIENTE (farmacia destinataria finale)
   - Estratti entrambi, solo grossista ha prefisso speciale

2. DATE CONSEGNA NEGLI HEADER COLONNA (v3.0):
   - Le date sono nelle intestazioni colonna della tabella
   - Possono esserci 1 o 2 colonne data (es: "5 nov 2025", "26 nov 2025")
   - Ogni prodotto ha quantità sotto la colonna della sua data consegna
   - Se stesso prodotto ha qty su più date → RIGHE SEPARATE

3. ESPOSITORI AUTONOMI (v3.0):
   - BAYER NON usa logica parent/child per espositori
   - Espositori sono prodotti AUTONOMI con prezzo proprio
   - Flag is_espositore = 1 solo informativo
   - Codici non standard (6-10 cifre) generano anomalia AIC-A01

4. ESTRAZIONE TABELLARE (v3.0):
   - Usa pdfplumber table extraction per mappare correttamente le colonne
   - Fallback su text extraction se tabella non disponibile
   - Garantisce corretta associazione qty → data consegna

5. IDENTIFICAZIONE VENDOR:
   - SOLO da contenuto testuale
   - Pattern multipli: "Bayer" + "COOPERATIVA/ GROSSISTA" + "NUM. PROP. D'ORDINE"
   - Nome file NON considerato

6. CAMPI NON ESTRATTI:
   - COLLABORATORE (agente)
   - TELEFONO
   - BANCA/AGENZIA
   - Codici SAP (presenti ma non mappati)
```

### Funzione Estrattore

```python
def extract_bayer(text: str, lines: List[str], pdf_path: str = None) -> Dict:
    """
    Estrattore BAYER v2.0
    
    Estrae:
    - Header: grossista, cliente (dati completi), numero ordine, data
    - Righe: codice AIC, descrizione, quantità, prezzo, sconti
    
    Particolarità:
    - Espositori codice 6 cifre → padding "5" come ANGELINI
    - Sconto Extra mappato separatamente
    - Grossista con identificazione dedicata
    
    Returns:
        Dict con chiave 'vendor' = 'BAYER' e dati ordine
    """
    data = {
        'vendor': 'BAYER',
        'righe': []
    }
    
    # Estrai header
    data['grossista'] = estrai_grossista(text, lines)
    cliente = estrai_cliente_completo(text, lines)
    data.update(cliente)  # ragione_sociale, partita_iva, indirizzo, etc.
    
    data['numero_ordine'] = estrai_numero_ordine(text)
    data['data_ordine'] = estrai_data_ordine(text)
    data['gg_dilazione'] = estrai_condizioni_pagamento(text) or 60
    
    # Estrai righe tabella
    for riga_text in estrai_righe_tabella_bayer(text, lines, pdf_path):
        codice_raw = estrai_codice_prodotto(riga_text)
        
        # Gestione espositori (6 cifre)
        if len(codice_raw) == 6:
            codice_aic = f"500{codice_raw}"  # Padding con 5
            is_espositore = 1
        else:
            codice_aic = normalizza_aic_standard(codice_raw)
            is_espositore = 0
        
        riga = {
            'codice_aic': codice_aic,
            'codice_originale': codice_raw,
            'descrizione': estrai_descrizione(riga_text),
            'q_venduta': estrai_quantita_vendita(riga_text),
            'q_sconto_merce': estrai_merce_sconto(riga_text) or 0,
            'merce_sconto_extra': estrai_sconto_extra(riga_text) or 0,
            'prezzo_netto': estrai_prezzo_cessione(riga_text),
            'is_espositore': is_espositore
        }
        
        data['righe'].append(riga)
    
    return data
```

### Pattern Regex Essenziali

```python
# Identificazione vendor
PATTERN_VENDOR = r'(BAYER|Bayer).*(COOPERATIVA/\s*GROSSISTA|NUM\.\s+PROP\.\s+D\'ORDINE)'

# Header
PATTERN_NUMERO_ORDINE = r'NUM\.\s+PROP\.\s+D\'ORDINE\s+(IT25O-\d+)'
PATTERN_DATA_ORDINE = r'DATA\s+ACQUISIZIONE\s+(\d{1,2})\s+(\w{3,9})\s+(\d{4})'
PATTERN_PIVA = r'P\.IVA:\s*(\d{11})'
PATTERN_PROVINCIA = r'\(([A-Z]{2})\)'

# Tabella
PATTERN_CODICE_AIC = r'^(\d{6,9})'
PATTERN_PREZZO = r'€\s*([\d,]+)'
PATTERN_QUANTITA = r'(\d+)'
PATTERN_GG_DILAZIONE = r'(\d+)\s*gg'
```

---

## 🔄 WORKFLOW PROCESSING

```
1. UPLOAD PDF
   └─ detect_vendor()
      ├─ Cerca: "Bayer" OR "BAYER"
      ├─ Cerca: "COOPERATIVA/ GROSSISTA"
      ├─ Cerca: "NUM. PROP. D'ORDINE"
      └─ Return: "BAYER" se match

2. ESTRAZIONE
   └─ extract_bayer()
      ├─ Estrae grossista (ragione sociale)
      ├─ Estrae cliente (tutti i campi)
      ├─ Estrae righe con gestione espositori
      └─ Gestisce q_sconto_merce + merce_sconto_extra

3. INSERIMENTO DATABASE
   └─ INSERT ORDINI_TESTATA + ORDINI_DETTAGLIO
   └─ Campi specifici BAYER:
      ├─ grossista (con prefisso BAY_)
      ├─ merce_sconto_extra (campo aggiuntivo)
      ├─ codice_originale (per espositori)
      └─ is_espositore (flag)

4. LOOKUP CLIENTE
   └─ Usa partita_iva per lookup MIN_ID

5. GENERAZIONE TRACCIATO
   └─ In questa fase:
      ├─ q_sconto_merce → mappato come QOmaggio
      ├─ merce_sconto_extra → sommato a QOmaggio
      └─ Totale omaggi = q_sconto_merce + merce_sconto_extra
```

---

**Documento**: REGOLE_BAYER.md
**Versione**: 3.0
**Ultima modifica**: 25 Gennaio 2026
**Stato**: ✅ CONFERMATO

---

## 📜 CHANGELOG

### v3.0 (25 Gennaio 2026)
- **DATE CONSEGNA MULTIPLE**: Supporto colonne date nell'header tabella
- **RIGHE SEPARATE**: Stesso prodotto con date diverse → righe ordine separate
- **ESPOSITORI AUTONOMI**: Rimossa logica parent/child (non applicabile a BAYER)
- **ESTRAZIONE TABELLARE**: Usa pdfplumber tables per mappatura colonne accurate
- **ANOMALIA AIC-A01**: Codici non standard (≠9 cifre) segnalati per revisione

### v2.0 (06 Gennaio 2026)
- Prima versione documentata
- Supporto base per Transfer Order BAYER
