> ⏳ **FASE 2 - IN ATTESA**: Questo vendor sarà implementato dopo il completamento dei test sulla Fase 1.

# 📋 REGOLE ESTRAZIONE: MENARINI

**Vendor**: A. MENARINI Industrie Farmaceutiche Riunite S.r.l.
**Versione**: 1.2
**Data**: 6 Gennaio 2026
**Identificativo**: Transfer Order MENARINI

---

## 🔍 IDENTIFICAZIONE DOCUMENTO

### ⚠️ IMPORTANTE: Detection Basata su Contenuto PDF
Il nome del file **NON** deve essere usato come criterio di identificazione vendor.
La detection deve basarsi **ESCLUSIVAMENTE** sul contenuto del PDF.

### Pattern di Riconoscimento (SOLO contenuto PDF)
```
MUST contain: "A. MENARINI"
AND (
    "Transfer Order" OR
    "Ordine N.:"
)
```

### Esempio Nome File (solo per riferimento, NON usato per detection)
- `TO_1717144_20251022.pdf`
- `TO_MENARINI_20251022.pdf`

---

## 📄 STRUTTURA DOCUMENTO

### Layout
- **Tipo**: Colonne verticali con header multi-sezione
- **Header**: 2 sezioni con offset differenti
- **Tabella**: Colonne verticali raggruppate
- **Particolarità**: Sistema PARENT/CHILD con indentazione

### Mappa Righe (pdftotext)
```
SEZIONE 1 (righe 5-14 etichette, 16-25 valori) - OFFSET 11
├── Riga 5:  "Cliente"           → Riga 16: valore
├── Riga 6:  "Indirizzo"         → Riga 17: valore
├── Riga 7:  "Località"          → Riga 18: valore
├── Riga 8:  "Partita IVA"       → Riga 19: valore
├── Riga 9:  "Rep"               → Riga 20: valore (agente)
└── Riga 13: "Tipo Pagamento"    → Riga 24: valore

SEZIONE 2 (righe 36-41 etichette, 43-48 valori) - OFFSET 7
├── Riga 36: "Cod. Cliente"      → Riga 43: valore
├── Riga 37: "CAP"               → Riga 44: valore
├── Riga 38: "Città"             → Riga 45: valore
└── Riga 56: "Provincia"         → Riga 58: valore (OFFSET 2)
```

---

## 📐 REGOLE ESTRAZIONE HEADER

### MENARINI-H01: Numero Ordine
```
Pattern: "Ordine\s+N\.?:?\s*\n?\s*(\S+)"
Formato tipico: "25004775000034_20251017"
Output: PDF_ORDINI.numero_ordine (testo integrale)
Note: Contiene data nel suffisso _YYYYMMDD
```

### MENARINI-H02: Data Ordine (da numero ordine)
```
Pattern: numero_ordine contiene "_(\d{8})$"
Estrazione: ultimi 8 caratteri dopo underscore
Output: PDF_ORDINI.data_ordine_raw = "20251017"
```

### MENARINI-H03: Data Ordine (da campo)
```
Posizione: Indice "Data Ordine" + OFFSET 7
Pattern: "(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"
Output: PDF_ORDINI.data_ordine_raw
Priorità: usa questo se presente, altrimenti da numero ordine
```

### MENARINI-H04: Data Consegna
```
Posizione: Indice "Data Consegna" + OFFSET 11
Pattern: "(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"
Output: PDF_ORDINI.data_consegna_raw
```

### MENARINI-H05: Cliente (Ragione Sociale)
```
Posizione: Indice "Cliente" + OFFSET 11
Validazione: non inizia con "Cod."
Output: PDF_ORDINI.ragione_sociale_raw
Limite: 50 caratteri
```

### MENARINI-H06: Indirizzo
```
Posizione: Indice "Indirizzo" + OFFSET 11
Output: PDF_ORDINI.indirizzo_raw
Limite: 50 caratteri
```

### MENARINI-H07: Località
```
Posizione: Indice "Località" + OFFSET 11
Output: PDF_ORDINI.localita (campo ausiliario)
Note: usare come fallback per città se campo Città vuoto
```

### MENARINI-H08: P.IVA Cliente
```
Posizione: Indice "Partita IVA" + OFFSET 11
Validazione: re.match(r'^\d{11}$', valore)
Output: PDF_ORDINI.partita_iva
```

### MENARINI-H09: Rep (Agente)
```
Posizione: Indice "Rep" + OFFSET 11
Validazione: re.match(r'^[A-Z][A-Z\s]+$', valore)
Output: PDF_ORDINI.nome_agente
```

### MENARINI-H10: Tipo Pagamento (Dilazione)
```
Posizione: Indice "Tipo Pagamento" + OFFSET 11
Pattern: "R\.?B\.?\s*(\d+)\s*GG\.?" (es: "R.B. 90GG.")
Estrazione: gruppo 1 = numero giorni
Output: PDF_ORDINI.condizioni_pagamento = "90 gg"
```

### MENARINI-H11: Codice Cliente
```
Posizione: Indice "Cod. Cliente" + OFFSET 7
Pattern: "[A-Z]?\d{5,6}" (es: "P03896")
Output: PDF_ORDINI.codice_cliente
```

### MENARINI-H12: CAP
```
Posizione: Indice "CAP" + OFFSET 7
Validazione: re.match(r'^\d{5}$', valore)
Output: PDF_ORDINI.cap_raw
```

### MENARINI-H13: Città
```
Posizione: Indice "Città" + OFFSET 7
Output: PDF_ORDINI.citta_raw
Fallback: se vuoto, usa valore da "Località"
```

### MENARINI-H14: Provincia
```
Posizione: Indice "Provincia" + OFFSET 2 (diverso!)
Validazione: re.match(r'^[A-Z]{2}$', valore)
Output: PDF_ORDINI.provincia_raw
```

---

## 📊 REGOLE ESTRAZIONE TABELLA PRODOTTI

### Struttura Colonne Verticali
```
Righe 27-N:  Descrizioni prodotto (tra "Prodotto" e "Totale:")
Righe 75-N:  AIC (9 cifre con 0 iniziale)
Righe 78-N:  Quantità
Righe 81-N:  Prezzi lordi (formato: "8,83 €")
Righe 84-N:  Sconti (formato: "20,00%")
Righe 91-N:  Prezzi netti (formato: "7,06 €")
```

### ⚠️ SISTEMA PARENT/CHILD

#### Definizione
```
PARENT: Riga prodotto NON indentata
  - Può avere AIC valido → prodotto normale
  - Può NON avere AIC → anomalia (es: kit/bundle)

CHILD: Riga prodotto INDENTATA (spazi/tab iniziali)
  - Ha sempre AIC valido
  - Rappresenta componente di un PARENT
  - VA IGNORATA nell'estrazione
```

#### Riconoscimento Indentazione
```python
# Riga indentata = CHILD
is_indented = line.startswith('  ') or line.startswith('\t')
```

### MENARINI-T01: Parsing Descrizioni
```
Inizio: dopo riga "Prodotto"
Fine: riga "Totale:"
Per ogni riga:
  - Verifica indentazione
  - Se indentata → flag_child = True
  - Raccogli descrizione (max 40 char)
Output: lista di tuple (descrizione, is_indented, line_index)
```

### MENARINI-T02: Codice AIC
```
Pattern: re.match(r'^0\d{8}$', valore)
SOLO accettato: 9 cifre che iniziano con 0
Output: TO_RAW.codice_raw
```

### MENARINI-T03: Quantità
```
Pattern: re.match(r'^\d+$', valore) AND valore != '0'
Validazione: int(valore) < 1000
Output: TO_RAW.quantita_raw
```

### MENARINI-T04: Prezzo Lordo
```
Pattern: "(\d+[,]\d{2})\s*€"
Conversione: float(valore.replace(',', '.'))
Output: TO_RAW.prezzo_listino_raw
```

### MENARINI-T05: Sconto Percentuale
```
Pattern: "(\d+[,]\d{2})%"
Conversione: float(valore.replace(',', '.'))
Output: TO_RAW.sconto1_raw
```

### MENARINI-T06: Prezzo Netto
```
Pattern: "(\d+[,]\d{2})\s*€" (dopo gli sconti)
Posizione: seconda sequenza di prezzi
Output: TO_RAW.prezzo_netto_raw
```

### MENARINI-T07: Logica Associazione Dati
```python
# Approccio posizionale
n_prodotti = len([p for p in prodotti_raw if not p.is_indented])

# Dopo gli AIC, raccogli tutti i numeri
all_numbers = [...]  # quantità
all_prices = [...]   # prezzi (lordi poi netti)
all_pct = [...]      # sconti

# Assegna per posizione
for i, parent in enumerate(parents_only):
    qty = all_numbers[i]
    sconto = all_pct[i]
    prezzo_lordo = all_prices[i]
    prezzo_netto = all_prices[n_prodotti + i]
```

---

## ⚠️ GESTIONE ANOMALIE

### MENARINI-A01: Riga Child
```
Condizione: is_indented = True
Azione: INSERIRE in TO_RAW con flag_child = True
In Fase 4: ESCLUDERE da TO_D
Log: ANOMALIE_LOG.tipo = 'CHILD', livello = 'INFO'
```

### MENARINI-A02: Parent Senza AIC
```
Condizione: is_indented = False AND codice_raw vuoto/invalido
Azione: INSERIRE in TO_RAW con flag_no_aic = True
Log: ANOMALIE_LOG.tipo = 'AIC', livello = 'CRITICO'
Descrizione: "Prodotto parent senza codice AIC - richiede intervento manuale"
```

### MENARINI-A03: ID MIN Mancante
```
Condizione: PDF non contiene CodTracciaturaCliente
Azione: Segnalare per lookup in Fase 3
Log: ANOMALIE_LOG.tipo = 'LOOKUP', livello = 'ATTENZIONE'
Note: MENARINI non fornisce ID MIN direttamente, richiede lookup P.IVA
```

---

## 🧪 TEST CASES

### TC-MENARINI-01: Ordine Standard
```
Input: TO_1717144_20251022.pdf
Expected:
  - numero_ordine: "25004775000034_20251017"
  - data_ordine_raw: "17/10/2025" o "20251017"
  - data_consegna_raw: "17/10/2025"
  - partita_iva: "04170230876"
  - ragione_sociale_raw: "FARM S GIORGIO DI STEFANO DR C"
  - indirizzo_raw: "PIAZZA CAVOUR 39"
  - cap_raw: "95129"
  - citta_raw: "CATANIA"
  - provincia_raw: "CT"
  - condizioni_pagamento: "90 gg"
  - codice_cliente: "P03896"
```

### TC-MENARINI-02: Verifica Prodotti
```
Input: TO_1717144_20251022.pdf
Expected n_righe: 2 (se non ci sono child)
  - Riga 1: AIC 044460018, Q:12, sconto 20%
  - Riga 2: AIC 044460020, Q:6, sconto 20%
```

### TC-MENARINI-03: Parent/Child
```
Input: Documento con prodotti indentati
Expected:
  - Righe indentate: flag_child = True
  - Righe non indentate senza AIC: flag_no_aic = True
  - Solo righe parent con AIC in output finale
```

---

## 🔑 LOOKUP FARMACIA

### ⚠️ IMPORTANTE: Fase di Lookup
Il lookup della farmacia **NON** avviene in fase di estrazione, ma in fase di **popolamento del database**.

### Particolarità MENARINI: No ID MIN Diretto
```
MENARINI NON fornisce l'ID MIN nel documento.
È necessario eseguire lookup completo per indirizzo.
```

### Indirizzo Concatenato per Lookup
```
Formato: {Indirizzo} + {Numero Civico} + {CAP} + {Località} + {Provincia}
Esempio: "PIAZZA CAVOUR 39 95129 CATANIA CT"

Campi utilizzati (estratti dal PDF):
- indirizzo_raw → Indirizzo + Numero Civico
- cap_raw → CAP
- citta_raw / localita → Località
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

### Nota Località vs Città
```
MENARINI ha campi separati per "Località" e "Città".
Per lookup, usare "Città" come riferimento principale.
Se "Città" vuoto, usare "Località" come fallback.
```

---

## 📝 NOTE IMPLEMENTAZIONE

### Dipendenze
```python
import re
from typing import List, Dict, Tuple
```

### Funzione Estrattore
```python
def extract_menarini(text: str, lines: List[str]) -> Dict:
    """
    Estrattore MENARINI v1.1
    Applica SOLO regole MENARINI-*.
    Gestisce sistema PARENT/CHILD.
    """
    data = {
        'vendor': 'MENARINI',
        'righe': []
    }
    # ... implementazione regole MENARINI-*
    return data
```

### Gestione Parent/Child
```python
# Fase 1: Raccogli descrizioni con flag indentazione
prodotti_raw = []
for i, line in enumerate(lines):
    if in_product_section:
        is_indented = line.startswith('  ') or line.startswith('\t')
        prodotti_raw.append((line.strip()[:40], is_indented, i))

# Fase 2: Costruisci righe - SOLO parent
for desc, is_indented, idx in prodotti_raw:
    if is_indented:
        # Child: registra ma non includere in output finale
        data['righe'].append({
            'descrizione': desc,
            'flag_child': True,
            # ...
        })
    else:
        # Parent: includi in output
        data['righe'].append({
            'descrizione': desc,
            'flag_child': False,
            'flag_no_aic': not has_valid_aic,
            # ...
        })
```

---

**Documento**: REGOLE_MENARINI.md
**Versione**: 1.2
**Ultima modifica**: 6 Gennaio 2026
**Nota**: v1.2 - Rimossi riferimenti filename, aggiunta sezione LOOKUP
