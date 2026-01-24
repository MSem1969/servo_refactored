# 📋 REGOLE ESTRAZIONE: DOC GENERICI

**Vendor**: DOC Generici (Transfer Order Generici)  
**Versione**: 1.0  
**Data**: 6 Gennaio 2026  
**Identificativo**: Transfer Order via Grossisti  
**Nota**: Non è un vendor produttore singolo, ma ordini generici tramite distributori

---

## 🔍 IDENTIFICAZIONE DOCUMENTO

### Pattern di Riconoscimento
```
MUST contain: "TRANSFER ORDER"
AND "Num." + numero ordine 10 cifre
AND "Grossista" (riga 2)
AND "Agente" con codice numerico
AND "Ind.Fiscale Via" (riga separata)
AND "Ind.Consegna Merce Via" (riga separata successiva)
AND "COD. A.I.C." (header tabella)
AND almeno 5 prodotti con "DOC" nel nome
```

### ⚠️ IMPORTANTE: Nome File
Il nome del file **NON** deve essere usato come criterio di identificazione vendor.
La detection deve basarsi **ESCLUSIVAMENTE** sul contenuto del PDF.

### Identificazione Vendor (detect_vendor)
```python
def detect_doc_generici(text: str) -> tuple[str, float]:
    """
    Rileva Transfer Order DOC Generici
    
    Criteri cumulativi (basati SOLO su contenuto PDF):
    - "TRANSFER ORDER" + "Num." (10 cifre) = +0.25
    - "Grossista" nelle prime 200 caratteri = +0.15
    - "Agente" con codice numerico = +0.15
    - "Ind.Fiscale Via" separato da "Ind.Consegna Merce Via" = +0.20
    - "COD. A.I.C." presente = +0.15
    - 5+ prodotti con "DOC" nel nome = +0.10
    
    Threshold: confidence >= 0.70 → DOC_GENERICI
    
    NOTA: Il nome del file viene IGNORATO nella detection
    """
    score = 0.0
    
    # Check TRANSFER ORDER con numero 10 cifre
    if re.search(r'TRANSFER\s+ORDER\s+Num\.\s+\d{10}', text):
        score += 0.25
    
    # Check Grossista (caratteristica distintiva)
    if re.search(r'Grossista\s+[A-Z]', text[:200]):
        score += 0.15
    
    # Check Agente con codice
    if re.search(r'Agente\s+\d{5}', text):
        score += 0.15
    
    # Check indirizzi separati (CARATTERISTICA CHIAVE)
    if 'Ind.Fiscale Via' in text and 'Ind.Consegna Merce Via' in text:
        score += 0.20
    
    # Check header tabella
    if 'COD. A.I.C.' in text:
        score += 0.15
    
    # Check prodotti "DOC"
    doc_count = len(re.findall(r'\bDOC\b', text))
    if doc_count >= 5:
        score += 0.10
    
    return ("DOC_GENERICI", score)
```

### Differenza da Altri Vendor
- **NO vendor pharma specifico**: non è ANGELINI, BAYER, CHIESI, etc.
- **SÌ grossista/distributore**: SOFAD, FARVIMA identificati nel documento
- **SÌ doppio indirizzo separato**: "Ind.Fiscale" e "Ind.Consegna Merce" su righe distinte
- **SÌ marchio "DOC"**: prevalente in prodotti farmaci generici
- **SÌ classe prodotto**: ogni riga indica Classe A-A, C-C, I-I con significato specifico

---

## 📄 STRUTTURA DOCUMENTO

### Layout Fisso Crystal Reports
- **Tipo**: Documento generato da Crystal Reports
- **Header**: Blocco fisso con 10 righe strutturate
- **Tabella**: Righe orizzontali con 5 colonne
- **Footer**: Presente SOLO nell'ultima pagina (quando Pagina X di Y con X=Y)
- **Particolarità**:
  - NO logo/vendor specifico (è generico)
  - SÌ grossista/distributore (SOFAD, FARVIMA, etc.)
  - NO prezzi/sconti nel documento
  - SÌ agente con codice numerico
  - SÌ doppio indirizzo (fiscale + consegna) su righe separate
  - SÌ classe prodotto per ogni riga (importante per condizioni vendita)

### Sezioni
```
HEADER DOCUMENTO (10 righe fisse)
├── Riga 1: TRANSFER ORDER Num. + Data
├── Riga 2: Grossista [RAGIONE SOCIALE]
├── Riga 3: Agente [CODICE] [NOME COGNOME]
├── Riga 4: Farmacia [RAGIONE SOCIALE] P.IVA [11 CIFRE]
├── Riga 5: Ind.Fiscale Via [INDIRIZZO]
├── Riga 6: CAP [5 CIFRE] Città [CITTÀ] Prov. [XX]
├── Riga 7: Ind.Consegna Merce Via [INDIRIZZO]
├── Riga 8: CAP [5 CIFRE] Città [CITTÀ] Prov. [XX]
├── Riga 9: Telefono [NUMERO] Fax [NUMERO]
└── Riga 10: COD. A.I.C. Prodotto N.pz Classe Condizione

TABELLA PRODOTTI (5 colonne)
├── COD. A.I.C. (9 cifre) - Codice ministeriale prodotto
├── Prodotto (descrizione) - Nome commerciale + dosaggio + forma
├── N.pz (quantità) - Numero pezzi ordinati
├── Classe (codifica DOC) - A-A, C-C, I-I (vedi DOCGEN-T05)
└── Condizione (sempre "ACCORDO TO") - Riferimento a documento separato

FOOTER (solo ultima pagina)
├── Totale: XXX (somma totale pezzi ordine)
└── Pagina X di Y (dove X = Y indica ultima pagina)
```

### Esempio Header Reale
```
TRANSFER ORDER Num. 0756003038 DEL 16/12/2025
Grossista SOFAD S.R.L.
Agente 80337 MEZZATESTA NATALE
Farmacia MANTIONE MASSIMO P.IVA 04268980820
Ind.Fiscale Via VIA AUSONIA 101
CAP 90144 Città PALERMO Prov. PA
Ind.Consegna Merce Via VIA AUSONIA 101
CAP 90144 Città PALERMO Prov. PA
Telefono 091/527858 Fax
COD. A.I.C. Prodotto N.pz Classe Condizione
```

### Nota su Classe Prodotto
La colonna "Classe" indica la classificazione DOC del prodotto:
- **A-A**: Farmaco Classe A (rimborsabile SSN)
- **C-C**: Farmaco Classe C (non rimborsabile)
- **I-I**: Integratori/Dispositivi/Parafarmaco

**IMPORTANTE**: Questa classificazione trascina condizioni di vendita specificate nel documento separato "ACCORDO TO", non presente nel Transfer Order stesso.

---

## 📐 REGOLE ESTRAZIONE HEADER

### DOCGEN-H01: Numero Ordine
```
Pattern: "Num\.\s+(\d{10})\s+DEL"
Formato: 10 cifre consecutive
Output: PDF_ORDINI.numero_ordine
Validazione: lunghezza esatta 10 cifre

Esempi:
  - "0756003038"
  - "0817001064"
  - "0784009972"
```

### DOCGEN-H02: Data Ordine
```
Pattern: "DEL\s+(\d{2}/\d{2}/\d{4})"
Formato input: DD/MM/YYYY
Formato output: DD/MM/YYYY (mantenuto)
Output: PDF_ORDINI.data_ordine

Esempi:
  - "16/12/2025"
  - "19/12/2025"
```

### DOCGEN-H03: Grossista/Distributore
```
Pattern: "Grossista\s+([^\n]+)"
Posizione: Riga 2 del documento
Output: PDF_ORDINI.grossista
Limite: 80 caratteri

Esempi:
  - "SOFAD S.R.L."
  - "FARVIMA MEDICINALI S.P.A."

Note: Campo NON presente nel tracciato TO_T standard,
      ma utile per analisi interne e statistiche
```

### DOCGEN-H04: Codice + Nome Agente
```
Pattern: "Agente\s+(\d{5})\s+([^\n]+)"
Posizione: Riga 3 del documento
Output:
  - PDF_ORDINI.codice_agente = gruppo 1 (5 cifre)
  - PDF_ORDINI.nome_agente = gruppo 2
Limite nome: 50 caratteri

Esempi:
  - "80337 MEZZATESTA NATALE"
    → codice_agente = "80337"
    → nome_agente = "MEZZATESTA NATALE"
  - "77864 TOSCANO VINCENZO"
    → codice_agente = "77864"
    → nome_agente = "TOSCANO VINCENZO"
```

### DOCGEN-H05: Ragione Sociale Farmacia
```
Pattern: "Farmacia\s+([^P]+?)\s+P\.IVA"
Posizione: Riga 4, tra "Farmacia" e "P.IVA"
Output: PDF_ORDINI.ragione_sociale_raw
Limite: 80 caratteri
Normalizzazione: trim() per rimuovere spazi extra

Esempi:
  - "MANTIONE MASSIMO"
  - "FARMACIA SABATO S.R.L."
  - "ADAM FARMA DI ALESSANDRO CEVENINI &C.SAS"

Note: Può contenere forme giuridiche (S.R.L., S.A.S., S.N.C.)
```

### DOCGEN-H06: P.IVA
```
Pattern: "P\.IVA\s+(\d{11})"
Posizione: Riga 4, dopo ragione sociale
Output: PDF_ORDINI.partita_iva
Formato: 11 cifre consecutive
Validazione: checksum P.IVA italiana

Esempi:
  - "04268980820"
  - "03864320753"
  - "08113401213"

IMPORTANTE: Usata per lookup anagrafica (prima chiave)
```

### DOCGEN-H07: Indirizzo Fiscale
```
Pattern: "Ind\.Fiscale\s+Via\s+([^\n]+)"
Posizione: Riga 5
Output: PDF_ORDINI.indirizzo_fiscale
Limite: 60 caratteri

Esempi:
  - "VIA AUSONIA 101"
  - "P.ZZA ALIGHIERI 28"
  - "VIA SOLFATARA 4/D - 4E"

Note: Campo informativo, NON usato per lookup
      (si usa indirizzo_consegna)
```

### DOCGEN-H08: CAP, Città, Provincia (Fiscale)
```
Pattern: "CAP\s+(\d{5})\s+Città\s+([A-Z][A-Z\s']+?)\s+Prov\.\s+([A-Z]{2})"
Posizione: Riga 6 (PRIMA occorrenza CAP+Città+Prov)
Output:
  - PDF_ORDINI.cap_fiscale = gruppo 1 (5 cifre)
  - PDF_ORDINI.citta_fiscale = gruppo 2
  - PDF_ORDINI.provincia_fiscale = gruppo 3 (2 lettere)

Esempi:
  - "CAP 90144 Città PALERMO Prov. PA"
    → cap_fiscale = "90144"
    → citta_fiscale = "PALERMO"
    → provincia_fiscale = "PA"

Note: Campi informativi, NON usati per lookup
```

### DOCGEN-H09: Indirizzo Consegna Merce
```
Pattern: "Ind\.Consegna Merce\s+Via\s+([^\n]+)"
Posizione: Riga 7
Output: PDF_ORDINI.indirizzo_consegna
Limite: 60 caratteri

Esempi:
  - "VIA AUSONIA 101"
  - "P.ZZA ALIGHIERI 28"
  - "VIA SOLFATARA 4/D - 4E"

CRITICO PER LOOKUP: Questo indirizzo viene usato per:
  1. Lookup anagrafica ministeriale
  2. Disambiguazione farmacie multipunto
  3. Identificazione punto vendita specifico

Note: Spesso identico a indirizzo_fiscale per farmacie
      monopunto, ma DIVERSO per catene/multipunto
```

### DOCGEN-H10: CAP, Città, Provincia (Consegna)
```
Pattern: "CAP\s+(\d{5})\s+Città\s+([A-Z][A-Z\s']+?)\s+Prov\.\s+([A-Z]{2})"
Posizione: Riga 8 (SECONDA occorrenza CAP+Città+Prov)
Output:
  - PDF_ORDINI.cap = gruppo 1 (mappato in TO_T)
  - PDF_ORDINI.citta = gruppo 2 (mappato in TO_T)
  - PDF_ORDINI.provincia = gruppo 3 (mappato in TO_T)

Esempi:
  - "CAP 73013 Città GALATINA Prov. LE"
    → cap = "73013"
    → citta = "GALATINA"
    → provincia = "LE"

CRITICO PER LOOKUP: Usati insieme a indirizzo_consegna
per matching punto vendita specifico.

IMPORTANTE MAPPING:
  - Questi campi → Tracciato TO_T
  - Campi fiscali → Solo uso interno/audit
```

### DOCGEN-H11: Telefono e Fax
```
Pattern: "Telefono\s+([\d/]+)\s+Fax\s+([\d/]*)"
Posizione: Riga 9
Output:
  - PDF_ORDINI.telefono = gruppo 1
  - PDF_ORDINI.fax = gruppo 2 (può essere vuoto)

Esempi:
  - "Telefono 091/527858 Fax"
    → telefono = "091/527858"
    → fax = "" (vuoto)
  - "Telefono 0836/561147 Fax 0836/561148"
    → telefono = "0836/561147"
    → fax = "0836/561148"

Note: Campi ausiliari, NON obbligatori in TO_T
```

---

## 🔑 RIEPILOGO CAMPI CHIAVE LOOKUP

| Campo Estratto | Uso Lookup | Priorità | Mapping TO_T |
|----------------|------------|----------|--------------|
| partita_iva | Prima chiave ricerca | ALTA | ✅ PartitaIVA |
| indirizzo_consegna | Disambiguazione multipunto | CRITICA | ✅ Indirizzo |
| cap (consegna) | Matching punto vendita | ALTA | ✅ CAP |
| citta (consegna) | Matching punto vendita | MEDIA | ✅ Citta |
| provincia (consegna) | Validazione geografica | BASSA | ✅ Provincia |
| ragione_sociale | Fallback fuzzy | MEDIA | ✅ RagioneSociale1 |
| indirizzo_fiscale | Solo audit | NESSUNA | ❌ Non mappato |
| cap_fiscale | Solo audit | NESSUNA | ❌ Non mappato |

---

## 📊 REGOLE ESTRAZIONE TABELLA PRODOTTI

### Struttura Tabella
```
Header (Riga 10):
COD. A.I.C. | Prodotto | N.pz | Classe | Condizione

Righe Prodotto (da Riga 11 in poi):
[9 cifre] [descrizione variabile] [qty] [X-X] [ACCORDO TO]
```

### DOCGEN-T01: Identificazione Header Tabella
```
Pattern: "COD\.\s+A\.I\.C\.\s+Prodotto\s+N\.pz\s+Classe\s+Condizione"
Posizione: Riga 10 del documento
Azione: Marca inizio parsing righe prodotto
```

### DOCGEN-T02: Identificazione Riga Prodotto
```
Pattern generale:
"^(\d{9})\s+(.+?)\s+(\d{1,4})\s+([A-Z]-[A-Z])\s+(ACCORDO TO)$"

Struttura:
  - Gruppo 1: Codice AIC (9 cifre)
  - Gruppo 2: Descrizione prodotto (lunghezza variabile)
  - Gruppo 3: Quantità (1-4 cifre)
  - Gruppo 4: Classe (formato X-X)
  - Gruppo 5: Condizione (valore fisso)

Validazione riga:
  - MUST iniziare con 9 cifre
  - MUST terminare con "ACCORDO TO"
  - MUST contenere pattern classe [A-Z]-[A-Z]

Fine tabella:
  - Riga contiene "Totale:" (solo ultima pagina)
  - Oppure inizio nuova pagina (header ripetuto)
```

### DOCGEN-T03: Codice AIC
```
Pattern: "^(\d{9})"
Posizione: Inizio riga prodotto
Formato: Esattamente 9 cifre
Output: TO_RAW.codice_aic

Validazione:
  - Lunghezza = 9
  - Solo cifre numeriche
  - Accettare codici che NON iniziano con 0 (es. integratori)

Esempi:
  - "038423012" → Codice AIC standard (farmaco)
  - "042179010" → Codice AIC standard
  - "988951087" → Codice integratore (non inizia con 0)
  - "950405439" → Codice parafarmaco (non inizia con 0)

Normalizzazione: Nessuna (mantenere come estratto)
```

### DOCGEN-T04: Descrizione Prodotto
```
Estrazione: Testo tra codice AIC e quantità
Pattern parsing: "^\d{9}\s+(.+?)\s+\d{1,4}\s+[A-Z]-[A-Z]"
Output: TO_RAW.descrizione
Limite: 60 caratteri (troncare se necessario)

Caratteristiche tipiche:
  - Nome principio attivo o commerciale
  - Marca "DOC" o "DOC Generics" (frequente)
  - Dosaggio (es. "10 mg", "500mg")
  - Quantità confezione (es. "30 cpr", "28 cps")
  - Forma farmaceutica (es. "cpr", "cps", "fl", "bst")

Esempi:
  - "Alfuzosina DOC 10 mg 30 cpr"
  - "Amlodipina 10 mg 14 cpr"
  - "Atorv. DOC Generics 10mg 30cpr"
  - "ColecalciferoloDOC 25000UI 2FL"
  - "PERAMIND 4+1,25+5 mg 30 cpr" (farmaco combinato)
  - "ESOMEPRAZOLO 20 mg 28 CAPSULE"
  - "Acetilcisteina 600mg 30cp eff"
  - "OMEGA 3 85% 1000mg 30cps molli"
  - "Tegradoc 30 cpr in flacone" (integratore)
  - "URIPYR 30 STICK" (integratore)

Normalizzazione:
  - Trim spazi iniziali/finali
  - Rimuovere doppi spazi
  - Mantenere maiuscole/minuscole originali
  - Troncare a 60 caratteri se necessario
```

### DOCGEN-T05: Quantità (N.pz)
```
Pattern: numero intero tra descrizione e classe
Regex: "\s+(\d{1,4})\s+[A-Z]-[A-Z]\s+ACCORDO TO$"
Output: TO_RAW.quantita_raw
Range tipico: 1-200 pezzi

Validazione:
  - Deve essere numero intero positivo
  - Range ragionevole: 1 ≤ qty ≤ 999

Esempi:
  - 10, 6, 20, 4, 12, 2, 15, 1
  - Valori anomali (da segnalare): 0, >200

Mapping:
  - TO_D.QVenduta = quantita_raw
  - TO_D.QOmaggio = 0 (sempre, non applicabile)
  - TO_D.QScontoMerce = 0 (sempre, non applicabile)
```

### DOCGEN-T06: Classe Farmaco (Codifica DOC)
```
Pattern: "([A-Z]-[A-Z])\s+ACCORDO TO$"
Posizione: Penultima componente riga
Formato: X-X (lettera-lettera)
Output: TO_RAW.classe_farmaco

Valori possibili:
  - "A-A" = Farmaco Classe A (rimborsabile SSN)
  - "C-C" = Farmaco Classe C (non rimborsabile SSN)
  - "I-I" = Integratori/Dispositivi/Parafarmaco

IMPORTANTE - Significato Classi:

┌────────┬─────────────────────────────────────────────────────┐
│ Classe │ Descrizione                                         │
├────────┼─────────────────────────────────────────────────────┤
│  A-A   │ Farmaco prescrivibile SSN                           │
│        │ - Rimborsabile                                      │
│        │ - Necessita ricetta medica (RR o RNR)               │
│        │ - Condizioni vendita: vedi ACCORDO TO               │
├────────┼─────────────────────────────────────────────────────┤
│  C-C   │ Farmaco non rimborsabile                            │
│        │ - A carico del cittadino                            │
│        │ - Può essere SOP o OTC                              │
│        │ - Condizioni vendita: vedi ACCORDO TO               │
├────────┼─────────────────────────────────────────────────────┤
│  I-I   │ Integratori/Dispositivi/Parafarmaco                 │
│        │ - Non farmaco                                       │
│        │ - Vendita libera o consiglio farmacista             │
│        │ - Condizioni vendita: vedi ACCORDO TO               │
└────────┴─────────────────────────────────────────────────────┘

Relazione con Documento "ACCORDO TO":
  La classe determina le condizioni commerciali specifiche
  (sconti, dilazioni pagamento, politiche reso) definite
  nel documento separato "ACCORDO TO" non incluso nel PDF.

Note implementazione:
  - Campo NON presente nel tracciato TO_D standard
  - Conservare come campo ausiliario per analisi
  - Utile per statistiche e controlli di coerenza
```

### DOCGEN-T07: Condizione (Valore Fisso)
```
Pattern: "ACCORDO TO$"
Posizione: Fine riga prodotto
Valore: Sempre "ACCORDO TO" (costante)
Output: Campo ausiliario (non mappato)

Significato:
  Indica che il prodotto è ordinato in regime di accordo
  Transfer Order, con condizioni specificate nel documento
  separato denominato "ACCORDO TO".

Validazione:
  - Se riga non termina con "ACCORDO TO" → anomalia formato
```

---

## 📋 ESEMPIO PARSING RIGA COMPLETA

### Riga Input
```
038423012 Alfuzosina DOC 10 mg 30 cpr 10 A-A ACCORDO TO
```

### Parsing Step-by-Step
```python
# 1. Split componenti
codice_aic = "038423012"                    # Primi 9 caratteri numerici
descrizione = "Alfuzosina DOC 10 mg 30 cpr" # Testo tra AIC e quantità
quantita = 10                                # Numero prima di classe
classe = "A-A"                               # Pattern X-X
condizione = "ACCORDO TO"                    # Fine riga (costante)

# 2. Validazioni
assert len(codice_aic) == 9                  # ✓
assert codice_aic.isdigit()                  # ✓
assert 1 <= quantita <= 999                  # ✓
assert classe in ["A-A", "C-C", "I-I"]       # ✓
assert condizione == "ACCORDO TO"            # ✓

# 3. Output TO_RAW
{
    'codice_aic': '038423012',
    'descrizione': 'Alfuzosina DOC 10 mg 30 cpr',
    'quantita_raw': 10,
    'classe_farmaco': 'A-A',
    'condizione': 'ACCORDO TO'
}
```

---

## 🔄 GESTIONE MULTIPAGINA

### Pattern Footer Ultima Pagina
```
Pattern: "Totale:\s+(\d+)"
         "Pagina\s+(\d+)\s+di\s+(\d+)"

Condizione ultima pagina: Pagina X di Y dove X = Y

Esempi:
  - "Totale: 478"
  - "Pagina 2 di 2" → ULTIMA PAGINA
  - "Pagina 1 di 2" → NON ultima pagina (no totale)
```

### Algoritmo Parsing Multipagina
```python
def parse_doc_generici_multipagina(pdf_path):
    """
    Gestisce ordini su più pagine concatenando righe prodotto
    """
    all_righe = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            text = page.extract_text()
            lines = text.split('\n')
            
            # Trova header tabella
            header_idx = None
            for i, line in enumerate(lines):
                if 'COD. A.I.C.' in line and 'Prodotto' in line:
                    header_idx = i
                    break
            
            if header_idx is None:
                continue  # Pagina senza tabella
            
            # Estrai righe prodotto (dopo header)
            for line in lines[header_idx + 1:]:
                # Stop se footer ultima pagina
                if 'Totale:' in line or 'Pagina' in line:
                    break
                
                # Parse riga prodotto
                if re.match(r'^\d{9}\s+', line):
                    riga = parse_riga_prodotto(line)
                    if riga:
                        all_righe.append(riga)
    
    return all_righe
```

### Validazione Totale
```python
def valida_totale_ordine(righe, totale_atteso):
    """
    Verifica coerenza totale pezzi
    """
    somma_qty = sum(r['quantita_raw'] for r in righe)
    
    if somma_qty != totale_atteso:
        # Anomalia: totale non coincide
        return {
            'anomalia': 'TOTALE_NON_COERENTE',
            'atteso': totale_atteso,
            'calcolato': somma_qty,
            'differenza': abs(somma_qty - totale_atteso)
        }
    
    return None  # OK
```

---

## 📊 TABELLA RIEPILOGATIVA ESEMPI PARSING

| Codice AIC | Descrizione | Qty | Classe | Tipo Prodotto |
|------------|-------------|-----|--------|---------------|
| 038423012 | Alfuzosina DOC 10 mg 30 cpr | 10 | A-A | Farmaco generico SSN |
| 042325023 | Acetilcisteina 600mg 30cp eff | 2 | C-C | Farmaco SOP |
| 988951087 | Tegradoc 30 cpr in flacone | 2 | I-I | Integratore |
| 950405439 | URIPYR 30 STICK | 1 | I-I | Integratore |
| 049310016 | PERAMIND 4+1,25+5 mg 30 cpr | 4 | A-A | Farmaco combinato |
| 044915027 | OMEGA 3 85% 1000mg 30cps molli | 4 | A-A | Integratore SSN |
| 047869019 | SEVENDOC 5mg/ml+1mg/ml fl 5 ml | 2 | C-C | Collirio SOP |

---

## ⚠️ GESTIONE ANOMALIE

### DOCGEN-A01: Codice AIC Non Standard
```
Condizione: Codice AIC non inizia con 0 (tipico integratori/parafarmaci)
Esempi:
  - "988951087" (Tegradoc - integratore)
  - "950405439" (URIPYR - integratore)

Azione: ACCETTARE codice, NON segnalare anomalia
Validazione: Solo lunghezza = 9 cifre
Log: INFO - Codice AIC non standard (possibile integratore)

Note: I codici AIC di integratori e parafarmaci possono iniziare
      con cifre diverse da 0. Questo è comportamento normale.
```

### DOCGEN-A02: Indirizzo Multi-Componente
```
Condizione: Indirizzo contiene caratteri speciali o multi-numero civico
Esempi:
  - "VIA SOLFATARA 4/D - 4E"
  - "P.ZZA ALIGHIERI 28"
  - "CORSO VITTORIO EMANUELE II 123/A"

Azione: ESTRARRE intero indirizzo, mantenere formato originale
Normalizzazione: Solo trim spazi, NO rimozione caratteri
Log: Nessuno (comportamento normale)

Note: Importante per lookup, mantenere formato esatto
```

### DOCGEN-A03: Assenza Prezzi
```
Condizione: Il PDF DOC Generici NON contiene mai:
  - Prezzo unitario
  - Prezzo totale riga
  - Percentuali sconto
  - Valore ordine complessivo

Azione: NON è anomalia, è caratteristica vendor
Output campi:
  - TO_RAW.prezzo_netto = NULL
  - TO_RAW.prezzo_pubblico = NULL
  - TO_RAW.sconto1 = NULL
  - TO_RAW.valore_netto = NULL

Log: Nessuno (comportamento atteso)

Note: Le condizioni economiche sono nel documento separato "ACCORDO TO"
```

### DOCGEN-A04: Totale Pezzi Non Coerente
```
Condizione: Somma quantità righe ≠ valore "Totale:" nel footer
Esempi:
  - Totale dichiarato: 478
  - Somma calcolata: 476
  - Differenza: 2 pezzi

Azione: SEGNALARE anomalia, ma ELABORARE ordine
Livello: ATTENZIONE
Richiede supervisione: NO (differenza ≤ 5%)
                       SÌ (differenza > 5%)

Output:
  - anomalia_tipo = 'TOTALE_NON_COERENTE'
  - totale_dichiarato = valore footer
  - totale_calcolato = somma righe
  - differenza_pezzi = abs(dichiarato - calcolato)
  - differenza_pct = (differenza / dichiarato) * 100

Soglie:
  - ≤ 2% → ATTENZIONE (possibile errore parsing)
  - 2-5% → ATTENZIONE (verifica manuale consigliata)
  - > 5% → ERRORE (bloccare, richiede supervisione)

Log: ANOMALIE_LOG con dettagli differenza
```

### DOCGEN-A08: Quantità Anomala
```
Condizione: Quantità prodotto fuori range ragionevole
Esempi:
  - qty = 0 (ordine nullo)
  - qty > 200 (ordine molto grande)

Azione:
  - qty = 0 → BLOCCARE, livello ERRORE, richiede supervisione SÌ
  - qty > 200 → SEGNALARE, livello ATTENZIONE, richiede supervisione NO

Output:
  - anomalia_tipo = 'QUANTITA_ANOMALA'
  - codice_aic = prodotto interessato
  - quantita = valore estratto
  - soglia_superata = 0 o 200

Richiede supervisione:
  - qty = 0 → SÌ (sempre)
  - qty > 200 → NO (solo warning)

Log: ANOMALIE_LOG per tracciabilità
```

### DOCGEN-A09: Riga Prodotto Malformata
```
Condizione: Riga non rispetta pattern standard
Esempi:
  - Manca codice AIC
  - Manca classe farmaco
  - Non termina con "ACCORDO TO"
  - Codice AIC ≠ 9 cifre

Azione: SALTARE riga, SEGNALARE anomalia
Livello: ERRORE
Richiede supervisione: SÌ (sempre, indipendentemente da percentuale)

Output:
  - anomalia_tipo = 'RIGA_MALFORMATA'
  - riga_numero = posizione nel file
  - riga_contenuto = testo originale
  - motivo = descrizione errore parsing

Contatore:
  - righe_totali = N
  - righe_saltate = M
  - percentuale_errore = (M / N) * 100

Comportamento:
  - OGNI riga malformata richiede supervisione
  - Ordine va in stato PENDING_REVIEW
  - Supervisore può:
    * Correggere manualmente riga
    * Accettare ordine parziale (escluse righe malformate)
    * Rifiutare ordine intero

Log: ANOMALIE_LOG + dettaglio righe problematiche + notifica supervisore
```

### DOCGEN-A10: Footer Mancante (Multipagina)
```
Condizione: Ordine multipagina senza footer "Totale:" nell'ultima pagina
Esempio: "Pagina 2 di 2" presente, ma NO "Totale: XXX"

Azione: BLOCCARE ordine, stato = PENDING_REVIEW
Livello: ERRORE
Richiede supervisione: SÌ (sempre)

Output:
  - anomalia_tipo = 'FOOTER_MANCANTE'
  - num_pagine = totale pagine
  - righe_estratte = conteggio
  - totale_calcolato = somma quantità

Validazione:
  - Impossibile verificare coerenza (manca riferimento)
  - Supervisore deve:
    * Verificare manualmente PDF originale
    * Confermare totale calcolato
    * Oppure correggere conteggio

Log: ANOMALIE_LOG + notifica supervisore

Note: Footer mancante può indicare:
      - PDF corrotto/incompleto
      - Errore generazione documento
      - Ordine parziale non completato
```

---

## 📊 MATRICE DECISIONALE ANOMALIE

| Codice | Livello | Blocca Ordine | Supervisione | Azione Automatica |
|--------|---------|:-------------:|:------------:|-------------------|
| A01 | INFO | ❌ NO | ❌ NO | Accettare codice |
| A02 | INFO | ❌ NO | ❌ NO | Mantenere formato |
| A03 | INFO | ❌ NO | ❌ NO | Campi NULL |
| A04 | ATTENZIONE/ERRORE | ⚠️ Dipende | ⚠️ Dipende | Verifica % scarto |
| A08 | ERRORE/ATTENZIONE | ⚠️ Solo qty=0 | ⚠️ Solo qty=0 | Controllo soglie |
| A09 | ERRORE | ✅ SÌ | ✅ SÌ (sempre) | Salta riga + notifica |
| A10 | ERRORE | ✅ SÌ | ✅ SÌ (sempre) | Blocca + notifica |

---

## 🧪 TEST CASES

### TC-DOCGEN-01: Ordine Standard Multipagina (0756003038)
```
Input: Ordine_T_O__DOC_Generici_10_0000001863_202512161525.pdf
Caratteristiche: 2 pagine, grossista SOFAD

Expected Output:
  - vendor: "DOC_GENERICI"
  - numero_ordine: "0756003038"
  - data_ordine: "16/12/2025"
  - grossista: "SOFAD S.R.L."
  - codice_agente: "80337"
  - nome_agente: "MEZZATESTA NATALE"
  - partita_iva: "04268980820"
  - ragione_sociale: "MANTIONE MASSIMO"
  - indirizzo_fiscale: "VIA AUSONIA 101"
  - indirizzo_consegna: "VIA AUSONIA 101"
  - cap: "90144"
  - citta: "PALERMO"
  - provincia: "PA"
  - telefono: "091/527858"
  - fax: "" (vuoto)
  - n_pagine: 2
  - n_righe: 62 (pag1: 49 + pag2: 13)
  - totale_pezzi_footer: 478
  - totale_pezzi_calcolato: 478
  - anomalie: 0
  - stato: ESTRATTO

Verifica:
  ✓ Parsing corretto header su entrambe le pagine
  ✓ Concatenazione righe prodotto
  ✓ Coerenza totale pezzi
  ✓ Indirizzo fiscale = indirizzo consegna (monopunto)
```

### TC-DOCGEN-02: Ordine Singola Pagina (0817001064)
```
Input: Ordine_T_O__DOC_Generici_11_0000000418_202512161058.pdf
Caratteristiche: 1 pagina, grossista FARVIMA, include integratori

Expected Output:
  - numero_ordine: "0817001064"
  - grossista: "FARVIMA MEDICINALI S.P.A."
  - codice_agente: "77864"
  - nome_agente: "TOSCANO VINCENZO"
  - partita_iva: "03864320753"
  - ragione_sociale: "FARMACIA SABATO S.R.L."
  - indirizzo_consegna: "P.ZZA ALIGHIERI 28"
  - cap: "73013"
  - citta: "GALATINA"
  - provincia: "LE"
  - n_righe: 41
  - righe_classe_AA: 37
  - righe_classe_CC: 2
  - righe_classe_II: 2
  - anomalie: 0 (codici integratori 988951087, 950405439 accettati)

Verifica:
  ✓ Codici AIC non standard (integratori) accettati
  ✓ Mix classi farmaco (A-A, C-C, I-I)
  ✓ Footer presente con totale
```

### TC-DOCGEN-03: Indirizzo Multi-Componente (0784009972)
```
Input: Ordine_T_O__DOC_Generici_12_0000000418_202512160900.pdf
Caratteristiche: Indirizzo con doppio civico

Expected Output:
  - numero_ordine: "0784009972"
  - ragione_sociale: "ADAM FARMA DI ALESSANDRO CEVENINI &C.SAS"
  - indirizzo_consegna: "VIA SOLFATARA 4/D - 4E"
  - cap: "80078"
  - citta: "POZZUOLI"
  - provincia: "NA"
  - n_righe: 34
  - anomalie: 0

Verifica:
  ✓ Indirizzo multi-componente estratto correttamente
  ✓ Formato mantenuto (nessuna normalizzazione)
  ✓ Ragione sociale complessa con "&C.SAS"
```

### TC-DOCGEN-04: Detection Vendor Basata su Contenuto
```
Input: PDF rinominato come "ordine_generico.pdf" (nome NON indicativo)
       Contenuto: formato DOC Generici standard

Expected Output:
  - vendor: "DOC_GENERICI"
  - confidence: >= 0.70

Verifica:
  ✓ Vendor rilevato SOLO da contenuto PDF
  ✓ Nome file IGNORATO nella detection
  ✓ Pattern "TRANSFER ORDER" + "Grossista" + indirizzi separati
```

---

## 📝 NOTE IMPLEMENTAZIONE

### Differenze da Altri Vendor

```
┌─────────────────┬──────────────┬──────────────────────────────────┐
│ Caratteristica  │ DOC GENERICI │ Altri Vendor                     │
├─────────────────┼──────────────┼──────────────────────────────────┤
│ Vendor Type     │ Generico     │ Specifico (ANGELINI, BAYER...)   │
│ Grossista       │ SÌ (visibile)│ NO (ordine diretto produttore)   │
│ Agente          │ SÌ (codice)  │ SÌ (alcuni), NO (altri)          │
│ Doppio Indirizzo│ SÌ (critico) │ NO (unico indirizzo)             │
│ Lookup su       │ Ind.Consegna │ Indirizzo unico                  │
│                 │ COMPLETO     │                                  │
│ Prezzi          │ NO (mai)     │ SÌ (quasi sempre)                │
│ Classe Farmaco  │ SÌ (A/C/I)   │ NO                               │
│ Documento Accord│ SÌ (separato)│ NO                               │
│ Codici AIC 9xx  │ SÌ (normali) │ Rari                             │
└─────────────────┴──────────────┴──────────────────────────────────┘
```

### Funzione Estrattore
```python
def extract_doc_generici(pdf_path: str, text: str, 
                          lines: List[str]) -> Dict:
    """
    Estrattore DOC GENERICI v1.0
    
    Applica regole DOCGEN-H01..H11 (header)
                  DOCGEN-T01..T07 (tabella)
                  DOCGEN-A01..A10 (anomalie)
    
    Particolarità:
    - Doppio indirizzo (fiscale + consegna)
    - Lookup su indirizzo consegna COMPLETO
    - NO prezzi
    - Classe farmaco A-A/C-C/I-I
    - Supporto multipagina
    
    Returns:
        Dict con:
        - vendor: 'DOC_GENERICI'
        - dati testata
        - righe prodotto
        - anomalie rilevate
    """
    data = {
        'vendor': 'DOC_GENERICI',
        'header': {},
        'righe': [],
        'anomalie': []
    }
    
    # ... implementazione regole DOCGEN-*
    
    return data
```

---

**Documento**: REGOLE_DOC_GENERICI.md  
**Versione**: 1.0  
**Data**: 6 Gennaio 2026  
**Validato con PDF**: 9 file analizzati
