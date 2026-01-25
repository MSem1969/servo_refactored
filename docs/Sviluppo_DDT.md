# SERV.O - Piano Sviluppo Modulo DDT

**Versione**: Draft 0.1
**Data**: 2026-01-25
**Stato**: In Revisione

---

## 1. Executive Summary

Questo documento definisce la strategia di sviluppo per l'estensione della piattaforma SERV.O
alla gestione dei DDT (Documenti di Trasporto) provenienti dal magazzino logistico.

L'approccio proposto si basa su:
- **Riuso della piattaforma Transfer Order** esistente (funzioni orizzontali condivise)
- **Modellazione agentica** per la definizione dei template interpretativi
- **Esecuzione deterministica** per il processamento operativo
- **Decisione umana** per la scelta tra gestione manuale e apprendimento

---

## 2. Contesto e Obiettivi

### 2.1 Scenario Operativo

I DDT rappresentano documenti di accompagnamento merce dal magazzino logistico.
Caratteristiche distintive:

| Caratteristica | Descrizione |
|----------------|-------------|
| **Canali di ingresso** | Email (PDF nativo) + Cartaceo (scansione) |
| **Volumi** | Elevati, concentrati secondo principio di Pareto |
| **Urgenza** | Email: non critica / Cartaceo: SLA ~60 minuti |
| **Stabilità struttura** | Alta - formato stabile per vendor |
| **Varietà vendor** | Elevata - molti fornitori diversi |
| **Destinazione** | Integrazione con sistema ERP |

### 2.2 Obiettivi del Modulo

1. **Automazione processamento** DDT per vendor con template definito
2. **Flessibilità operativa** - mai bloccare il flusso di lavoro
3. **Apprendimento controllato** - creazione template su decisione umana
4. **Integrazione ERP** - output compatibile con sistema gestionale
5. **Riuso piattaforma** - leverage delle funzioni SERV.O esistenti

### 2.3 Non-Obiettivi (Fuori Scope)

- Gestione documenti non strutturati (approcci RAG)
- Apprendimento automatico senza supervisione
- Sostituzione completa dell'operatore
- Gestione documentale generica

---

## 3. Architettura Concettuale

### 3.1 Separazione Apprendimento / Esecuzione

Il sistema distingue nettamente due fasi:

```
FASE APPRENDIMENTO (Agentic AI + Supervisione Umana)
────────────────────────────────────────────────────
- Attivata su richiesta del supervisore
- AI Agent analizza struttura documento
- Definisce regioni, campi, sequenza lettura
- Produce template interpretativo
- Supervisore valida e approva

FASE ESECUZIONE (Deterministica)
────────────────────────────────
- Template già definito e validato
- Processamento automatico
- Nessun intervento AI
- Veloce, predicibile, economico
```

### 3.2 Flusso Operativo

```
[DDT Arriva]
     │
     ▼
[Identifica Vendor]
     │
     ▼
[Template Esiste?]───────────────────────────────────┐
     │                                               │
     │ SÌ                                           │ NO
     ▼                                               ▼
[Processamento Automatico]              [Notifica Supervisore]
     │                                               │
     │                              ┌────────────────┴────────────────┐
     │                              │                                 │
     │                              ▼                                 ▼
     │                    [Inserimento Manuale]            [Avvia Learning]
     │                    (documento raro/una tantum)      (vendor frequente)
     │                              │                                 │
     │                              │                                 ▼
     │                              │                      [AI Modellazione]
     │                              │                                 │
     │                              │                                 ▼
     │                              │                      [Supervisione]
     │                              │                                 │
     │                              │                                 ▼
     │                              │                      [Template Attivo]
     │                              │                                 │
     ▼                              ▼                                 ▼
[Integrazione ERP] ◄─────────────────────────────────────────────────┘
```

### 3.3 Principi Guida

| Principio | Descrizione |
|-----------|-------------|
| **Mai bloccare** | Inserimento manuale sempre disponibile |
| **Decisione umana** | Supervisore sceglie se investire in learning |
| **Pareto-driven** | Concentrare effort su vendor ad alto volume |
| **Pragmatismo** | Documento raro = manuale, zero overhead |
| **Gradualità** | Sviluppo incrementale, non big-bang |

---

## 4. Strategia di Estrazione Multi-Livello

### 4.1 Tre Engine per Tre Scenari

| Scenario | Engine | Quando |
|----------|--------|--------|
| PDF nativo (digitale) | pdfplumber | Documenti generati digitalmente |
| Misto (nativo + elementi immagine) | Tesseract | Header/logo come immagine |
| Scansione completa / Manoscritto | PaddleOCR | Documenti cartacei scansionati |

### 4.2 Selezione Engine

La selezione dell'engine appropriato può essere:
- **Definita nel template** (se nota a priori per vendor)
- **Determinata automaticamente** (analisi caratteristiche PDF)
- **Fallback progressivo** (pdfplumber → Tesseract → PaddleOCR)

---

## 5. Componente AI: Modellazione Template

### 5.1 Ruolo dell'AI Agent

L'AI Agent interviene **solo** nella fase di modellazione, con compiti:

1. **Analisi struttura documento**
   - Identificazione regioni (header, corpo, tabella, footer)
   - Riconoscimento tipi di dato (date, codici, importi, testi)
   - Mappatura campi verso schema ERP

2. **Generazione template**
   - Definizione coordinate/pattern per ogni campo
   - Regole di validazione
   - Sequenza di lettura

3. **Supporto iterativo**
   - Raffinamento su feedback supervisore
   - Gestione varianti minori

### 5.2 Confini dell'AI

| L'AI FA | L'AI NON FA |
|---------|-------------|
| Analizza documento campione | Decisioni autonome su quando apprendere |
| Propone template | Processamento in produzione |
| Suggerisce mapping campi | Gestione eccezioni non previste |
| Supporta raffinamento | Apprendimento continuo non supervisionato |

---

## 6. Integrazione con Piattaforma SERV.O

### 6.1 Funzioni Orizzontali Condivise

Il modulo DDT riutilizza le componenti esistenti:

| Componente | Riuso da SERV.O |
|------------|-----------------|
| Autenticazione/Autorizzazione | Sistema utenti esistente |
| Gestione ruoli (Operatore/Supervisore) | Matrice permessi esistente |
| Upload/Acquisizione documenti | Modulo upload PDF |
| Logging operazioni | Sistema log esistente |
| Notifiche | Sistema notifiche (se presente) |
| UI Framework | Componenti React esistenti |

### 6.2 Componenti Nuovi Specifici DDT

| Componente | Descrizione |
|------------|-------------|
| Template Registry | Repository template per vendor |
| Template Editor/Validator | UI supervisione template |
| ERP Integration Layer | Connettore verso sistema gestionale |
| DDT Manual Entry Form | Form inserimento manuale |
| Vendor Stats Tracker | Statistiche occorrenze vendor |

---

## 7. Piano di Sviluppo Incrementale

### Fase 0: Preparazione (Pre-requisito)
- Completamento piattaforma Transfer Order
- Stabilizzazione funzioni orizzontali
- Definizione interfaccia ERP

### Fase 1: MVP Manuale
- Form inserimento manuale DDT
- Integrazione ERP base
- Tracking vendor (conta occorrenze)
- Nessun template, tutto manuale

**Obiettivo**: Validare flusso end-to-end, raccogliere dati su vendor

### Fase 2: Template Engine
- Struttura template (schema JSON)
- Template Registry
- Processamento automatico con template
- Creazione manuale primi template (2-3 vendor top)

**Obiettivo**: Validare concetto template, misurare benefici

### Fase 3: AI Modellazione
- Integrazione AI Agent
- UI supervisione/validazione template
- Workflow learning completo

**Obiettivo**: Scalare creazione template a tutti i vendor

### Fase 4: Ottimizzazioni
- Multi-engine (pdfplumber/Tesseract/PaddleOCR)
- Confidence tracking
- Suggerimenti automatici
- Analytics e reporting

---

## 8. Domande Aperte e Criteri da Definire

### 8.1 Domande di Business

| # | Domanda | Impatto su Design |
|---|---------|-------------------|
| B1 | Quanti DDT/giorno previsti per canale (email vs cartaceo)? | Sizing infrastruttura |
| B2 | Quanti vendor rappresentano l'80% del volume? | Priorità template |
| B3 | SLA 60 min per cartacei è hard limit o best effort? | Strategia fallback |
| B4 | Qual è il costo di un errore di processamento? | Soglie validazione |
| B5 | Serve conservazione PDF originali? Per quanto? | Storage, compliance |

### 8.2 Domande Tecniche

| # | Domanda | Impatto su Design |
|---|---------|-------------------|
| T1 | Quale sistema ERP target? API o file-based? | Integration layer |
| T2 | Infrastruttura scan esistente? Qualità output? | Engine selection |
| T3 | Latenza accettabile verso ERP? | Sync vs Async |
| T4 | Dove deployare PaddleOCR? (stesso server / microservizio) | Architettura |
| T5 | Budget per API AI (Claude) nella fase learning? | Costi modellazione |

### 8.3 Criteri da Definire

| Criterio | Descrizione | Default Proposto |
|----------|-------------|------------------|
| **Soglia vendor frequente** | Quando suggerire learning | >5 docs in 30 giorni |
| **Confidence minima produzione** | Quando template è "pronto" | 95% su 20+ docs |
| **Timeout processamento** | Max tempo per singolo DDT | 30 secondi |
| **Retention documenti** | Conservazione PDF originali | 2 anni |
| **Fallback strategy** | Se template fallisce | Notifica + manuale |

### 8.4 Aspetti da Approfondire

1. **Complessità documento vs Complessità soluzione**
   - Definire tassonomia complessità documenti
   - Mappare complessità → engine appropriato
   - Identificare soglia "troppo complesso per automazione"

2. **Gestione varianti intra-vendor**
   - Un template per vendor o per tipo documento?
   - Come gestire varianti minori (es. DDT standard vs DDT reso)?
   - Criteri per decidere "nuovo template" vs "estensione esistente"

3. **Ciclo di vita template**
   - Stati: Draft → Testing → Production → Retired
   - Trigger per transizioni
   - Gestione versioning se vendor cambia formato

4. **Metriche di successo**
   - KPI per valutare efficacia sistema
   - Dashboard supervisore
   - Alerting su degradazione performance

---

## 9. Rischi e Mitigazioni

| Rischio | Probabilità | Impatto | Mitigazione |
|---------|-------------|---------|-------------|
| AI genera template non validi | Media | Alto | Validazione umana obbligatoria |
| Vendor cambia formato senza preavviso | Media | Medio | Monitoring confidence, alert |
| Volumi superiori alle attese | Bassa | Alto | Architettura scalabile |
| ERP non disponibile | Media | Alto | Coda retry + notifica |
| Cold start vendor urgente | Media | Medio | Manuale sempre disponibile |

---

## 10. Next Steps

- [ ] Revisione documento con stakeholder
- [ ] Risposta a domande sezione 8.1 (Business)
- [ ] Risposta a domande sezione 8.2 (Tecniche)
- [ ] Definizione criteri sezione 8.3
- [ ] Prioritizzazione Fase 1 (MVP)
- [ ] Stima effort e timeline

---

## Appendice A: Glossario

| Termine | Definizione |
|---------|-------------|
| **DDT** | Documento di Trasporto - accompagna merce |
| **Template** | Schema interpretativo per tipo documento/vendor |
| **Learning** | Processo di creazione template tramite AI |
| **Engine** | Componente estrazione testo (pdfplumber/Tesseract/PaddleOCR) |
| **Confidence** | Misura affidabilità estrazione (0-100%) |

---

## Appendice B: Riferimenti

- SERV.O Platform Documentation (CLAUDE.md)
- PaddleOCR Documentation: https://github.com/PaddlePaddle/PaddleOCR
- pdfplumber Documentation: https://github.com/jsvine/pdfplumber

---

*Documento generato durante sessione di pianificazione strategica - 2026-01-25*
*Da validare prima di procedere con implementazione.*
