# SERV.O - Istruzioni Progetto

## Panoramica

Sistema estrazione ordini farmaceutici da PDF → tracciati ministeriali TO_T/TO_D.

**Stack:** FastAPI + PostgreSQL + React + Vite + TailwindCSS + React Query

**Documentazione correlata:**
- [SCHEMA_DB_SERVO.md](./SCHEMA_DB_SERVO.md) - Schema completo database (55 tabelle, 8 viste)
- [RECOVERY.md](./RECOVERY.md) - Guida disaster recovery e backup
- [MD_Files/storico/](./MD_Files/storico/) - Piani e changelog storici (archivio)

---

## Comandi

```bash
# Backend
cd backend && source venv/bin/activate && uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend && npm run dev

# Test (rete di sicurezza per refactoring - eseguirli PRIMA e DOPO ogni modifica)
cd backend && source venv/bin/activate && TEST_ADMIN_PASSWORD=<pwd-admin> pytest
cd frontend && npm run test:run
```

> **`TEST_ADMIN_PASSWORD` è necessaria**: senza, i ~25 test di integrazione si
> auto-skippano silenziosamente, perché il default storico `admin123` non
> corrisponde più alla password dell'utente admin. Vale anche `TEST_ADMIN_USER`.

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
├── common/        # Componenti UI riusabili (Table, FormField, StatusBadge...)
├── components/    # Componenti feature
├── hooks/         # Hook GLOBALI: solo useCrm, useEmail, useSessionTracking, utils/
├── layout/        # Header, Sidebar, Layout
└── pages/         # Pagine + i loro hook locali (pages/*/hooks/)
```

> **Dove stanno davvero gli hook React Query.** In `pages/*/hooks/`
> (`useDatabasePage`, `useOrdineDetail`, `useSupervisione`), non in `hooks/`.
> Il barrel globale `hooks/` conteneva 9 moduli duplicati e orfani, rimossi nel
> refactoring 2026-07. Non c'è un `context/`: l'autenticazione è gestita con
> `useState` in `App.jsx`, non via React Context.

**Migrazioni DB:** unico meccanismo è `backend/migrations/*.sql`, applicate a mano
con `psql -f`. Alembic è stato rimosso (mai applicato).

---

## Formato Tracciati EDI

**REGOLE GENERALI:**
- **UPPERCASE**: Tutti i campi testo devono essere in MAIUSCOLO
- **Allineamento**: Campi stringa allineati a sinistra (ljust), numeri a destra (zfill)
- **Encoding**: UTF-8, terminatore riga CRLF

### TO_T - TESTATA (869 caratteri)

| Pos | Campo | Lung. | Obbl. | Formato | Note |
|-----|-------|-------|-------|---------|------|
| 1-10 | Vendor | 10 | Y | String | `{PREFIX}_{DISTRIB}` es: HAL_FARVI |
| 11-40 | VendorOrderNumber | 30 | Y | String | Numero ordine, ljust |
| 41-60 | CustomerTraceabilityCode | 20 | Y | String | **Pos 41: spazio, Pos 42+: MIN_ID senza zeri anteposti, resto spazi** (es: `00001` → ` 1`, `00991` → ` 991`, `10905` → ` 10905`) |
| 61-76 | VAT code | 16 | Y | String | P.IVA, ljust |
| 77-126 | CustomerName1 | 50 | Y | String | Ragione sociale, **UPPERCASE** |
| 127-176 | CustomerName2 | 50 | N | String | Ragione sociale 2, **UPPERCASE** |
| 177-226 | Address | 50 | N | String | Indirizzo, **UPPERCASE** |
| 227-236 | CodeCity | 10 | N | String | CAP |
| 237-286 | City | 50 | N | String | Città, **UPPERCASE** |
| 287-289 | Province | 3 | N | String | Provincia, **UPPERCASE** |
| 290-299 | OrderDate | 10 | Y | Date | GG/MM/AAAA |
| 300-309 | EstDeliveryDate | 10 | Y | Date | GG/MM/AAAA (**se vuota: data stimata**, vedi sotto) |
| 310-359 | AgentName | 50 | N | String | Nome agente, **UPPERCASE** |
| 360-369 | DataPagamento1 | 10 | N | Date | GG/MM/AAAA o spazi |
| 370-379 | ImportoPagamento1 | 10 | N | Float 7.2 | **`0000000.00`** (7 int + "." + 2 dec) |
| 380-382 | GgDilazionePagamento1 | 3 | N | Int 3.0 | Es: `090` per 90 giorni |
| 383-392 | DataPagamento2 | 10 | N | Date | GG/MM/AAAA o spazi |
| 393-402 | ImportoPagamento2 | 10 | N | Float 7.2 | **`0000000.00`** |
| 403-405 | GgDilazionePagamento2 | 3 | N | Int 3.0 | Default `000` |
| 406-415 | DataPagamento3 | 10 | N | Date | GG/MM/AAAA o spazi |
| 416-425 | ImportoPagamento3 | 10 | N | Float 7.2 | **`0000000.00`** |
| 426-428 | GgDilazionePagamento3 | 3 | N | Int 3.0 | Default `000` |
| 429-448 | CodOffertaCliente | 20 | N | String | Codice offerta cliente |
| 449-468 | CodOffertaVendor | 20 | N | String | **Default: `1000` zfill** (zeri anteposti: `00000000000000001000`) |
| 469 | ForceCheck | 1 | N | Char | **Default ` ` (spazio)**, oppure S/N |
| 470-669 | OrderAnnotation | 200 | N | String | **Default: `STANDARD`** |
| 670-869 | BOT_Annotation | 200 | N | String | Note DDT |

**FORMATO FLOAT 7.2:** 10 caratteri totali = 7 interi + "." + 2 decimali → `0000000.00`

**ESEMPIO TRACCIATO VALIDO:**
```
HAL_FARVI 271952954                      10905              00407890672     PATRONI DR. PIERLUIGI                                                                               CORSO S. GIORGIO 83                               64100     TERAMO                                            TE 20/01/202623/01/2026GRILLO FABIO                                                          0000000.00090          0000000.00000          0000000.00000                                        00000000000000001099 STANDARD
```

### TO_D - DETTAGLIO

| Pos | Campo | Lung. | Obbl. | Campo DB |
|-----|-------|-------|-------|----------|
| 1-30 | VendorNumberOrder | 30 | Y | numero_ordine |
| 31-35 | LineNumber | 5 | Y | n_riga |
| 36-56 | ProductCode | 21 | Y | codice_aic (10 cifre + 11 spazi) |
| 57-62 | SalesQuantity | 6 | Y | q_venduta |
| 63-68 | QuantityDiscountPieces | 6 | N | **sempre 0** |
| 69-74 | QuantityFreePieces | 6 | N | **q_sconto_merce + q_omaggio** |
| 75-84 | ExtDeliveryDate | 10 | N | data_consegna_riga (se vuota: **data stimata**) |
| 85-108 | Discount1-4 | 24 | Y | sconto_1/2/3/4 (3+2 dec) |
| 109-118 | NetVendorPrice | 10 | Y | prezzo_netto (7+2 dec) |
| 119-128 | PriceToDiscount | 10 | Y | prezzo_scontare |
| 129-133 | VAT | 5 | N | aliquota_iva |
| 134 | NetVATPrice | 1 | Y | scorporo_iva (S/N) |
| 135-144 | PriceForFinalSale | 10 | Y | prezzo_pubblico |
| 145-344 | NoteAllestimento | 200 | Y | note_allestimento |

**REGOLA OMAGGIO:** `QuantityFreePieces = q_sconto_merce + q_omaggio` (QuantityDiscountPieces sempre 0)

### Data di consegna stimata (2026-08)

Circa il **36% degli ordini** non ha data di consegna nel PDF (DOC_GENERICI e AVAS non
la espongono mai; VIATRIS la omette sulla consegna "Immediata"). In quel caso la data
**non viene scritta in DB** — `data_consegna` resta `NULL` — ma viene stimata in lettura:

```
data consegna stimata = data_ordine + 3 giorni lavorativi
```

Sabato e domenica sono esclusi; **le festività non sono gestite**. Se manca anche
`data_ordine`, ultima rete = data odierna.

**Una sola regola, tre implementazioni che devono restare allineate:**

| Dove | Cosa |
|---|---|
| `config.GG_CONSEGNA_LAVORATIVI_DEFAULT` | il numero (3) |
| `utils/dates.py::add_business_days` | tracciati TO_T e TO_D |
| `add_business_days(date,int)` SQL (migration `v16`) | `ORDER BY` lista ordini |
| `pages/Database/utils.js::GG_CONSEGNA_LAVORATIVI` | badge urgenza + ri-sort client |

Cambiando il numero vanno aggiornati `config.py` **e** `utils.js`. Le tre implementazioni
sono verificate equivalenti su 2800 combinazioni data×N.

> **La soglia `MAX_GIORNI_CONSEGNA = 30` non usa la stima.** `_verifica_data_consegna`
> (`orders/fulfillment.py`) legge `data_consegna_riga` grezza da DB: se è `NULL` la riga
> resta confermabile. È voluto — bloccare una conferma per una data inventata da noi
> sarebbe sbagliato, tanto più che **la data di consegna non è modificabile da UI**
> (non è in `CAMPI_MODIFICABILI` né in `PATCH /header`).

#### Ordini multi-data e filtro dei report (2026-08)

Un ordine **può avere date di consegna diverse riga per riga**: DOMPE e BAYER le
espongono negli header di colonna e gli estrattori creano righe separate (regola
`BAYER-DC02`). Non esiste alcuno split in più ordini.

`v_ordini_completi.data_consegna` è `MIN(data_consegna_riga)` sulle righe **non**
`EVASO`/`ARCHIVIATO`: giusto per il badge di urgenza (mostra la prossima scadenza),
sbagliato per i report, che attribuivano tutte le righe al periodo più imminente e
cambiavano risultato a ogni evasione.

→ I report filtrano quindi su **`ordini_dettaglio.data_consegna_riga`**
(`routers/report.py::_condizioni_periodo`), mai su `t.data_consegna`. Dove
`ordini_dettaglio` non è in scope (tendine dei filtri) si usa un **unico** `EXISTS`
con entrambi gli estremi — due `EXISTS` separati accetterebbero un ordine con una
riga prima e una dopo il periodo, ma nessuna dentro.

Gli ordini **senza alcuna data** restano esclusi dai report per consegna, come prima.

### VALIDAZIONE QUANTITÀ (v11.5 - CRITICA)

**REGOLE VINCOLANTI:**
1. `SalesQuantity + QuantityFreePieces` **NON DEVE MAI** superare `q_da_evadere`
2. Se `q_venduta = 0`, allora `SalesQuantity = 0` (anche se ci sono omaggi)
3. I valori originali (q_venduta, q_sconto_merce, q_omaggio) **NON vengono sovrascritti** da q_da_evadere

**Evasione Totale (`q_da_evadere >= q_totale`):**
- SalesQuantity = q_venduta (valore originale)
- QuantityFreePieces = q_sconto_merce + q_omaggio (valori originali)

**Evasione Parziale (`q_da_evadere < q_totale`):**
- Le quantità vengono proporzionate mantenendo il rapporto originale
- `ratio = q_da_evadere / q_totale`
- Gli arrotondamenti vengono distribuiti preferibilmente su q_venduta

**Validazione:**
- Il generatore blocca con errore se `totale_tracciato > q_da_evadere`
- Il formatter TO_D effettua doppio controllo di sicurezza

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

`ARCHIVIATO` | `EVASO` | `PARZ_EVASO` | `CONFERMATO` | `ANOMALIA` | `ESTRATTO` | `VALIDATO` | `ESPORTATO` | `PARZ_ESPORTATO`

### EVASO / PARZ_EVASO da bolla (2026-06)

Lo stato `EVASO`/`PARZ_EVASO` è guidato dalla **registrazione della bolla**
(`esportazioni_dettaglio.data_evasione` o `numero_bolla` ≠ NULL), NON dal
conteggio righe evase. Regola (in `_calcola_stato_ordine`, fulfillment.py):

| Stato prima della bolla | → dopo bolla |
|-------------------------|--------------|
| `PARZ_ESPORTATO` | **PARZ_EVASO** |
| `ESPORTATO` o qualunque altro stato (incl. `ARCHIVIATO`) | **EVASO** |
| `PARZ_EVASO` / `EVASO` | invariati (idempotente) |

→ **`PARZ_EVASO` esiste solo** come transizione `PARZ_ESPORTATO → PARZ_EVASO`.
L'unico meccanismo di evasione è la bolla (l'endpoint `righe/{id}/evasione`
imposta solo `q_da_evadere`, non evade). Lo stato è ricalcolato in modo
centralizzato da `_aggiorna_contatori_ordine` (`ha_evasione` via EXISTS su
`esportazioni_dettaglio`).

### Operazioni Protette

- **ARCHIVIATO**: bloccato da CONFERMA singola (ma ripristinabile)
- **EVASO**: bloccato da CONFERMA singola
- **Generazione tracciato**: esclude ARCHIVIATO/EVASO

### Archiviazione: anomalie e supervisioni seguono l'ordine (2026-08)

Un ordine archiviato non sarà mai esportato: le sue **anomalie aperte diventano
`ARCHIVIATA`** e le sue **supervisioni pending diventano `ARCHIVED`**
(`orders/commands.py::archivia_anomalie_e_supervisioni`).

Vale su **tutti** i percorsi che portano ad `ARCHIVIATO`, non solo
`archivia_ordine`: un ordine ci arriva anche archiviando le righe una per una,
perché `_calcola_stato_ordine` ritorna `ARCHIVIATO` quando non restano righe
attive. Quel percorso non archiviava nulla → 74 supervisioni LOOKUP rimaste
`PENDING` in produzione su ordini archiviati (bonifica: migration `v17`).

### `ANOMALIA` sopravvive al ricalcolo (2026-08)

`_calcola_stato_ordine` non conosceva lo stato `ANOMALIA` e ogni ricalcolo dei
contatori lo sovrascriveva: bastava confermare una riga perché un ordine con
anomalia bloccante aperta risultasse `ESTRATTO`/`CONFERMATO` — a posto nella
lista, ma non generabile (4 casi in produzione, migration `v18`).

Ora `_calcola_stato_ordine` accetta `ha_blocchi_aperti` (anomalie
`ERRORE`/`CRITICO` aperte **o** supervisioni `PENDING`, una sola query in
`_ordine_ha_blocchi_aperti`) e ritorna `ANOMALIA` **solo** per gli stati
pre-tracciato. `ARCHIVIATO`/`EVASO` hanno la precedenza; gli stati
post-tracciato non retrocedono, perché per arrivarci l'ordine era già pulito.

> **`supervisione_aic` è l'unica tabella supervisione con un CHECK sullo stato.**
> Non ammetteva `ARCHIVED`: `archivia_ordine` falliva lì da gennaio 2026, con
> l'errore nascosto da un `except: pass`. Vincolo esteso nella migration `v17`.
> Aggiungendo stati nuovi, ricordarsi di quel CHECK.

### Ordine senza righe ≠ ordine archiviato (2026-09)

`_calcola_stato_ordine` trattava `righe_attive == 0` come "tutte le righe sono
state archiviate" → `ARCHIVIATO`. Ma con **zero righe in assoluto** non c'è
niente da archiviare: è un'estrazione fallita. L'ordine veniva chiuso d'ufficio
e — dalla regola di archiviazione — anche le sue anomalie e supervisioni:
spariva dai radar senza che nessuno sapesse perché (caso reale: DOC_GENERICI
`0698002291`, unica riga scartata dal parser).

Ora `totale == 0` mantiene lo stato corrente (`ANOMALIA` se ci sono blocchi
aperti) e l'inserimento apre **`EXT-A02`** (`ERRORE`, bloccante) su qualunque
ordine creato con 0 righe, per qualunque vendor.

### RIPRISTINA Singola Riga (v11.5 - HARD RESET)

Il bottone RIPRISTINA su singola riga effettua un **HARD RESET**:
- Azzera `q_evasa` e `q_da_evadere`
- La riga torna a stato `ESTRATTO`
- L'ordine passa a `PARZ_EVASO` (se aveva altre righe evase) o `ESTRATTO`

**Stati ripristinabili:** ARCHIVIATO, CONFERMATO, IN_TRACCIATO, PARZIALE, **EVASO**

**ATTENZIONE:** I tracciati già generati NON vengono annullati. L'operatore è responsabile di gestire eventuali discrepanze.

---

## Anomalie

### GRAVI (Bloccanti)

| Codice | Tipo | Descrizione |
|--------|------|-------------|
| **ESP-A01** | ESPOSITORE | Child sotto l'atteso (>=20%) — pezzi, **valore** per MENARINI |
| **ESP-A02** | ESPOSITORE | Child sopra l'atteso (>=20%) — pezzi, **valore** per MENARINI |
| **ESP-A03** | ESPOSITORE | Espositore senza child |
| **ESP-A04/05** | ESPOSITORE | Chiusura forzata |
| **ESP-A06** | ESPOSITORE | Conflitto ML vs estrazione |
| **LKP-A01** | LOOKUP | Score < 80% |
| **LKP-A02** | LOOKUP | Farmacia non trovata |
| **LKP-A04** | LOOKUP | P.IVA mismatch (subentro) |
| **LKP-A05** | LOOKUP | Cliente non in anagrafica_clienti |
| **EXT-A01** | ESTRAZIONE | Vendor non riconosciuto → **apre ticket CRM automatico** |
| **EXT-A02** | ESTRAZIONE | Nessuna riga prodotto estratta dal PDF |

### ORDINARIE (Non Bloccanti)

| Codice | Descrizione |
|--------|-------------|
| **LKP-A03** | Score 80-95% |
| **ESP-A08** | Blocco espositore MENARINI senza riga materiale, o con più di una |
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
| **AVAS** | Attivo | Transfer Order Avas Pharmaceuticals, prefix EDI `AVA`. Detection: `AVAS PHARMACEUTICALS`/`@avaspharma.com`/P.IVA `09190500968`. P.netto unitario già scontato → sconti a 0 (come ZENTIVA); P.IVA cliente dopo label `P.Iva Cliente` (evita P.IVA vendor); dati testata da `Sede Dest.` |
| **CODIFI** | Attivo | Multi-cliente (N ordini/PDF) |
| **MENARINI** | Attivo | Espositore `--`, blocco parent+materiale+child (vedi sez. Espositori) |
| **DOC_GENERICI** | Attivo | Transfer Order, NO prezzi. Riga prodotto = AIC + N.pz; **classe e condizione sono testo libero** (`A-A`, `3-3`, `ACCORDO TO`, `TO EMATONIL`…), mai usate come filtro |
| **CHIESI** | In attesa | Escludere P.IVA 02944970348 |
| **COOPER** | Attivo | — |
| **RECKITT** | Attivo | — |
| **VIATRIS** | Attivo | Transfer Order, OR+numero, TRACC.F+MIN_ID |
| **PERRIGO** | Attivo | — |
| **DOMPE** | Attivo | AIC/Paraf nel corpo cella; skip righe senza AIC; netto=0 → omaggio; supporto multi-data |
| **ZENTIVA** | Attivo | Transfer Order, numero ordine `O-NNNNNN` da nome file (SAP Nr. Ordine vuoto), prefix EDI `ZEN`. Detection: stringa `ZENTIVA`/email `@zentiva.com`, **oppure** fallback strutturale (`RIEPILOGO CONSEGNA`+`REFERIMENTO`+`TRANSFER`) per i T.O. col contatto `@iqvia.com` che non contengono mai "ZENTIVA" |
| ~~OPELLA~~ | Escluso | PDF ignorati (vedi `config.VENDORS_ESCLUSI`). Ordini storici mantenuti |
| ~~BAYER~~ | Escluso | PDF ignorati (vedi `config.VENDORS_ESCLUSI`). Ordini storici mantenuti |

**Detection:** Solo contenuto PDF (nome file ignorato)
**Esclusione:** `config.VENDORS_ESCLUSI` (env `VENDORS_ESCLUSI=OPELLA,BAYER,UNKNOWN`). PDF rilevati con uno di questi vendor non vengono salvati né su disco né in DB e non generano ticket CRM.

### Vendor Non Riconosciuto

I PDF il cui vendor non viene riconosciuto (`detect_vendor` ritorna `UNKNOWN`) sono inclusi di default in `VENDORS_ESCLUSI` → **non vengono gestiti**: nessuna acquisizione, nessun ordine, nessuna anomalia EXT-A01, nessun ticket CRM.

Gli ordini storici con `codice_vendor='GENERIC'` (creati prima di questa scelta) restano consultabili in DB come prima.

Se in futuro si vorrà tornare al comportamento precedente (ordine elaborato con estrattore generico + ticket CRM), basta rimuovere `UNKNOWN` dall'env `VENDORS_ESCLUSI`.

---

## Espositori

- **PARENT_ESPOSITORE**: Contenitore (FSTAND, BANCO, EXPO, etc.)
- **CHILD_ESPOSITORE**: Prodotti contenuti
- **Tracciato EDI**: Solo parent, child esclusi

| Vendor | Chiusura |
|--------|----------|
| ANGELINI | pezzi_accumulati >= pezzi_attesi |
| MENARINI | fine del blocco (parent successivo o fine documento) |

### MENARINI: un espositore, tre righe di PDF (2026-09)

Un espositore MENARINI non sta su una riga sola, e i dati che servono a farne una
riga d'ordine sono **su righe diverse**:

| Prodotto | Cod. Min. | Q.tà | Prezzo | Totale Netto | |
|---|---|---|---|---|---|
| `LAILA ANSIA EXPO BANCO GIOV` | `--` | 1 | 98,44 | **78,75** | parent: prezzo, **nessun codice** |
| `LAILA 80MG 14CPR CP` | 044460018 | 4 | 8,83 | 28,26 | child (prodotto reale) |
| `LAILA EXPO BANCO GIOVANI 2026` | **87AB54** | 1 | 0,00 | 0,00 | materiale: **codice**, nessun prezzo |
| `LAILA 80MG 28CPR CP` | 044460020 | 4 | 15,78 | 50,50 | child |

Il **blocco** va dalla riga `--` alla successiva (o a fine tabella) e contiene sempre
esattamente **una** riga materiale, ma **in posizione libera**: in testa, in mezzo o in
coda ai child (38/38 blocchi sui PDF campione, 6 dei quali con materiale in coda).

→ Codice materiale e prezzi vengono **uniti sul parent in estrazione**
(`vendors/menarini.py::_segmenta_blocchi_espositore`), prima che la state machine degli
espositori giri: è l'unico punto in cui la posizione della riga materiale è irrilevante.
La riga materiale **non viene emessa** — è il contenitore a prezzo 0, non una riga d'ordine.

Sul parent finiscono i valori **dichiarati** dal PDF, non ricalcolati:
`prezzo_netto` = Totale Netto / q.tà, `prezzo_pubblico` = Prezzo / q.tà. Ricalcolare il
netto dalla somma dei child sbagliava di un centesimo (78,76 contro 78,75) e azzerava il
prezzo di vendita dell'espositore.

> **La chiusura per valore era il bug, non la regola.** Chiudere l'espositore quando la
> somma dei netto child raggiungeva il netto del parent dipendeva dall'ordine delle righe:
> perdeva il codice materiale nel 16% dei blocchi e sarebbe bastato un child sotto il 2%
> del totale in ultima posizione per lasciarlo orfano. Il confronto di valore resta, ma
> **solo come verifica** (`verifica_scostamento_valore` → ESP-A01/A02, tolleranza 2%).

I child MENARINI sono salvati in DB con `is_child=TRUE` e `id_parent_espositore`, come per
ANGELINI: restano fuori da tracciato, AIC-A01, LST-A01, contatori, conferma ed evasione
(tutte quelle query filtrano su `is_child`), ma rendono visibile la composizione.

> **`87AB54` non è un AIC**: è il codice materiale Menarini. Il parent resta quindi senza
> codice ministeriale e apre `AIC-A01` + supervisione. Il merge non la elimina, la rende
> **una sola per espositore** e con `pattern_signature` stabile: al primo AIC assegnato a
> mano, `criteri_ordinari_aic` lo applica da solo agli ordini successivi.

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

## Supervisione Prezzo — INCOMPIUTA (congelata)

**Non estendere né rimuovere** finché il perimetro del modulo DDT non è definito.
Decisione presa nel refactoring del 2026-07-28.

Stato di fatto rilevato:

| Elemento | Situazione |
|---|---|
| Tabella `supervisione_prezzo` | **0 righe** in dev e in prod, pur avendo 28 riferimenti SQL nel backend |
| `routers/supervisione/prezzo.py` | 631 righe, **7 endpoint** |
| Consumo dal frontend | **1 solo** endpoint: `POST /supervisione/prezzo/riapplica-listino` (`api/supervisione.js`) |

Gli altri 6 endpoint (`pending`, `{id}`, `{id}/righe`, `{id}/upload-listino`,
`{id}/approve`, `{id}/reject`) non hanno alcun consumatore. La feature è stata
costruita a metà e mai esercitata: il codice resta in repo perché rimuoverlo
sarebbe una perdita irreversibile, ma **non va considerato funzionante**.

---

## Endpoint di sola manutenzione (nessun consumatore frontend)

Questi 13 endpoint non sono chiamati da nessuna pagina: sono **strumenti admin
legittimi**, da invocare a mano. Sono elencati qui perché ogni audit del codice
li ri-segnala come "morti" — non lo sono.

| Endpoint | Uso |
|---|---|
| `GET dashboard/upload-stats` | Statistiche upload |
| `POST listini/calcola-prezzi` | Ricalcolo prezzi da listino |
| `POST admin/sync/scheduler/run-now` | Forza sync anagrafica ministero |
| `POST anagrafica/clienti/revisiona-depositi` | Revisione massiva depositi |
| `POST ordini/{id}/sblocca-supervisioni` | Sblocco manuale supervisioni |
| `POST ordini/{id}/fix-stati`, `POST ordini/fix-stati-tutti` | Ricalcolo stati righe/ordine |
| `GET tracciati/ftp/health-check` | Diagnostica FTP |
| `POST upload/detect-vendor` | Test detection vendor su PDF |
| `POST upload/reprocess/{id}` | Ri-elaborazione acquisizione |
| `GET supervisione/espositore/{id}` | Dettaglio supervisione espositore |
| `POST supervisione/prezzo/{id}/{upload-listino,approve,reject}` | Vedi sezione precedente |

### Generazione tracciato: un solo percorso (2026-08)

La generazione avviene **solo** in `POST /ordini/{id}/valida` →
`services/export/generator.py::valida_e_genera_tracciato`, che legge da
`ORDINI_DETTAGLIO`.

Esisteva un secondo percorso — `generate_tracciati_per_ordine`, dietro
`POST /tracciati/genera`, `POST /tracciati/genera/{id}` e
`GET /tracciati/preview/{id}` — **rimosso**. Non era codice morto innocuo:
interrogava la vista `v_dettagli_completi`, che **non esiste in nessun DB**, e la
sua contabilità export divergeva da quella reale:

| | Percorso reale | Percorso rimosso |
|---|---|---|
| Stato ordine | `VALIDATO`, poi `ESPORTATO` dopo FTP | `ESPORTATO` subito, saltando l'FTP |
| Righe `esportazioni` | una per ordine, nomi file veri | una per N ordini, nomi fittizi (`"3 file TO_T"`) |
| `q_esportata` / `q_da_evadere` | valorizzati e azzerati | mai toccati |
| Anomalie INFO/ATTENZIONE | chiuse | no |
| Clone parziale | creato | no |

Poiché `esportazioni.stato_ftp` ha `DEFAULT 'PENDING'`, quelle righe sarebbero
entrate nella coda FTP con nomi file inesistenti. Era raggiungibile via API da
qualunque utente autenticato: a proteggerlo c'era solo l'assenza della vista.

> **Non ricreare `v_dettagli_completi`.** Un test lo impedisce
> (`tests/test_export.py::test_nessun_riferimento_alla_vista_inesistente`).

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

## Export FTP Tracciati (v11.5)

### Configurazione

| Parametro | Valore |
|-----------|--------|
| **Host** | 85.39.189.15 |
| **Porta** | 21 |
| **Username** | sofadto |
| **Password** | Variabile ambiente `FTP_PASSWORD` (Coolify) |
| **Modalità** | Attiva (IP whitelistato) |

### Mapping Vendor → Path FTP

| Vendor | Path FTP |
|--------|----------|
| ANGELINI | ./ANGELINI |
| DOC_GENERICI | ./DOC |
| CODIFI | ./CODIFI |
| Altri vendor | **Skip FTP** (solo locale) |

### Flusso Batch (ogni 10 minuti)

1. Cerca esportazioni con `stato_ftp = 'PENDING'` o `'RETRY'`
2. Per ogni esportazione:
   - Verifica mapping vendor
   - Upload coppia TO_T + TO_D
   - Aggiorna stato: `SENT` / `RETRY` / `FAILED`
3. Se `FAILED` dopo 3 tentativi → **Alert email**

### API Endpoints

```
GET  /api/v1/tracciati/ftp/status     # Stato FTP e scheduler
POST /api/v1/tracciati/ftp/send       # Invio manuale
GET  /api/v1/tracciati/ftp/pending    # Esportazioni in attesa
GET  /api/v1/tracciati/ftp/log        # Log operazioni
POST /api/v1/tracciati/ftp/reset/{id} # Reset per retry
```

### Stati FTP (`esportazioni.stato_ftp`)

| Stato | Descrizione |
|-------|-------------|
| PENDING | In attesa di invio |
| SENDING | Invio in corso |
| SENT | Inviato con successo |
| RETRY | Fallito, in attesa retry |
| FAILED | Fallito dopo max tentativi |
| SKIPPED | Vendor non mappato |
| ALERT_SENT | Alert email inviato |
| SUPERSEDED | Sostituita da una riemissione (vedi sezione Riemissione) |

### Tabelle Database

- `ftp_config` - Configurazione connessione
- `ftp_vendor_mapping` - Mapping vendor → path
- `ftp_log` - Log operazioni FTP
- `esportazioni.stato_ftp` - Stato invio

---

## Riemissione tracciato (edit + ritrasmissione)

Quando l'ERP scarta un tracciato per errore di formato/contenuto, un admin può
editare il testo raw di TO_T/TO_D e generare una nuova esportazione che sostituisce
la precedente, senza toccare i dati dell'ordine in DB.

### Regole

- **Solo admin** può eseguire edit e ritrasmissione (verifica lato endpoint e UI).
- **Dati ordine intoccati**: l'ordine resta `ESPORTATO/PARZ_ESPORTATO`, `q_evasa`
  invariata. La riemissione opera solo a livello tracciato.
- **Numero ordine suffissato**: la riemissione applica sempre `.N` (con `force=True`
  in `_apply_export_suffix`). Su un clone parziale già suffissato (es. `ORD001.2`)
  applica un ulteriore tail (`ORD001.2.3`). N proviene dal conteggio totale di
  `esportazioni_dettaglio` per quell'`id_testata` (incluse le esportazioni SUPERSEDED).
- **Nessun limite** al numero di riemissioni per ordine.
- **Originale SUPERSEDED**: la riga in `esportazioni` cambia `stato_ftp` a `SUPERSEDED`
  e popola `data_riemissione`. I suoi file vengono spostati in `outputs/archive/`.
- **Nuova esportazione**: nuova riga con `is_riemissione=TRUE`, `riemessa_da_id`
  pointing al parent, `stato_ftp='PENDING'`. Pronta per ritrasmissione FTP.
- **Ritrasmissione**: rinomina i file con nuovo timestamp prima dell'upload (evita
  collisioni di nome sul ricevente) e riusa il sender FTP standard.

### Endpoint API

```
GET  /api/v1/tracciati/{id_esportazione}/raw          # Carica testo TO_T/TO_D + metadati
POST /api/v1/tracciati/{id_esportazione}/riemetti     # Crea riemissione (body: to_t_content, to_d_content, note)
POST /api/v1/tracciati/{id_esportazione}/ritrasmetti  # Rinomina + invia FTP
```

### Audit

Le azioni vengono tracciate su `operatore_azioni_log` con:
- `sezione = TRACCIATI`
- `azione = RIEMETTI_TRACCIATO` | `RITRASMETTI_TRACCIATO`

E un log dedicato su `ftp_log.azione`:
- `RIEMISSIONE` (sull'esportazione originale al momento della sostituzione)
- `RITRASMISSIONE` (sull'esportazione al momento dell'invio FTP)

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

### ⚠️ Trappola: nomi di campo diversi fra estrattore e INSERT

Le righe grezze degli estrattori sono `dict` senza schema: un campo scritto con un
nome e riletto con un altro non da' errore, **da' zero**. Era il caso degli sconti:
`espositore.py::_crea_riga_output` leggeva `sconto_pct` — chiave che **nessun**
estrattore valorizza — e scriveva `sconto_1`, mentre `_insert_detail_row` legge
`sconto1`. Doppio buco silenzioso: in DB **249 righe ANGELINI, 86 COOPER e 53
MENARINI con `sconto_1 = 0`** a fronte di sconti reali del 20-70% nel PDF, e
`Discount1-4` a `000.00` nei tracciati ANGELINI (vendor FTP).

Nomi in uso oggi: gli estrattori scrivono **`scontoN`**, COOPER **`sconto_N`**, le
colonne DB sono **`sconto_N`**. `_insert_detail_row` accetta entrambe le grafie e
`_crea_riga_output` normalizza via `_sconto()`.

> Quando si aggiunge un campo a una riga, verificare **da dove viene riletto**
> (`_crea_riga_output`, `_insert_detail_row`) e non solo dove viene scritto.
> Una query di controllo per vendor (`count(*) FILTER (WHERE campo <> 0)`) rivela
> in un secondo se un campo non arriva mai in fondo.

### ⚠️ Trappola: `modulo.py` e `modulo/` nella stessa directory

Se in una directory coesistono `x.py` e il package `x/`, **Python carica sempre il
package**: `x.py` diventa irraggiungibile, ma continua a sembrare vivo a chi legge
il repo e a `grep`. Durante il refactoring 2026-07 questo aveva prodotto **1.414
righe di codice fantasma** in due punti (`services/listini.py` e
`services/supervision/aic.py`), entrambi ombreggiati e mai eseguiti.

Verifica in un secondo, invece di dedurlo dagli import:

```bash
python -c "import app.services.listini as m; print(m.__file__)"
```

**Corollario:** anche i test possono puntare al modulo sbagliato.
`tests/test_espositori.py` testava il package inattivo `services/espositori/`
mentre in produzione girava `espositore.py` — 21 test verdi su codice mai
eseguito. Quando si sposta o si duplica un modulo, controllare **da dove
importano i test**, non solo l'applicazione.

---

## Debug e Fix (METODOLOGIA)

**Approccio retroattivo:** In fase di debug e fix, verificare SEMPRE prioritariamente gli impatti dei commit precedenti rispetto a una fase in cui il sistema funzionava.

### Domande chiave all'utente

1. **"Prima funzionava?"** - Stabilire se è una regressione o un bug preesistente
2. **"Da quando non funziona?"** - Identificare il timeframe per correlare con i commit

### Processo di debug

1. **Analisi retroattiva dei commit** (`git log`, `git show`, `git diff`)
   - Confrontare il codice attuale con la versione funzionante
   - Verificare ogni modifica nel file/funzione coinvolta
   - Attenzione a "fix" che introducono nuovi bug (es. fix per problema A che rompe funzionalità B)

2. **Se l'analisi retroattiva non evidenzia problemi** → Verifica generale
   - Controllare log del backend
   - Query dirette sul database per verificare lo stato
   - Test delle API isolate (curl, python -c)

### Esempio reale

Il fix per "idle in transaction" faceva rollback su `TRANSACTION_STATUS_INTRANS` (transazione attiva normale), annullando tutti gli UPDATE. La correzione: rollback solo su `TRANSACTION_STATUS_INERROR`.

---

## Comunicazione con l'Utente (FONDAMENTALE)

**Principio guida:** Ogni volta che il sistema impedisce un'operazione per SCELTA (non per errore), DEVE comunicarlo chiaramente all'utente.

### Regole

1. **Mai operazioni silenziose** - Se un'azione non viene eseguita, l'utente deve sapere PERCHÉ
2. **Distinguere errori da blocchi voluti** - Errore di sistema ≠ Regola di business
3. **Messaggi chiari e azionabili** - Spiegare cosa è successo E come risolvere
4. **Contesto completo** - Mostrare quante righe/elementi sono stati bloccati e perché

### Esempi

```
❌ SBAGLIATO: (silenzio, nessuna riga confermata)
❌ SBAGLIATO: "Errore nella conferma"
✅ CORRETTO: "5 righe NON confermate: data consegna oltre 30 giorni. Modificare la data per confermarle."
```

### Implementazione

- **Backend**: Restituire sempre dettagli strutturati (es. `righe_bloccate_data_consegna: [...]`)
- **Frontend**: Mostrare alert/toast con messaggio esplicativo
- **Log**: Registrare il motivo del blocco per audit
