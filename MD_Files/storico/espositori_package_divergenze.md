# `services/espositori/` — package rimosso: divergenze rispetto a `espositore.py`

**Rimosso il 2026-07-28** (refactoring Fase 1, branch `feat/ddt-module`).

## Perché è stato rimosso

Nella directory `backend/app/services/` convivevano due implementazioni della logica espositori:

| | righe | import nel repo | stato |
|---|---|---|---|
| `espositore.py` (monolite) | 919 | usato da `pdf_processor.py` | **codice in esercizio** |
| `espositori/` (package, 5 file) | 810 | **zero** | mai eseguito |

Il package era stato creato come split del monolite ma **non è mai stato agganciato**: nessun
modulo lo importava. Nel frattempo il monolite ha continuato a evolvere, quindi le due versioni
si sono **divergenziate**: il package non è una copia più pulita, è un fork più vecchio e con
regole diverse. Lasciarlo in repo era una trappola per chi in futuro lo avrebbe scambiato per
"la versione nuova".

Recupero: `git show <commit-precedente>:backend/app/services/espositori/processing.py` ecc.

## Divergenze funzionali principali (MENARINI)

### 1. Criterio di chiusura dell'espositore

**`espositore.py` (in vigore)** — chiusura guidata dal solo confronto di valore, tolleranza 2%:

```python
if vendor.upper() == 'MENARINI':
    if menarini_netto_parent > 0:
        tolleranza = menarini_netto_parent * 0.02  # 2%
        if ctx.espositore_attivo.valore_netto_accumulato >= menarini_netto_parent - tolleranza:
            should_close = True
```

**`espositori/processing.py` (rimosso)** — tolleranza 5% più due criteri di fallback assenti
nel monolite (chiusura sui pezzi attesi, e chiusura di emergenza oltre 20 child all'80% del
valore):

```python
tolleranza = menarini_netto_parent * 0.05  # 5%
if diff >= -tolleranza: should_close = True
if not should_close and ctx.espositore_attivo.pezzi_per_unita:
    pezzi_attesi = pezzi_per_unita * quantita_parent
    if pezzi_accumulati >= pezzi_attesi: should_close = True
if not should_close and len(righe_child) > 20:
    if valore_netto_accumulato / menarini_netto_parent >= 0.80: should_close = True
```

### 2. Identificazione del parent

Il monolite identifica il parent MENARINI dal **solo** `Cod. Min. == '--'`. Il package usava
`'--'` **più** una lista di keyword (`BANCO|DBOX|FSTAND|EXPO|DISPLAY|ESPOSITORE|CESTA`), che è
il criterio ANGELINI e produceva falsi positivi su MENARINI.

### 3. Anomalia da scostamento di valore

`Espositore.verifica_scostamento_valore()` — fasce ZERO/BASSO/MEDIO/ALTO/CRITICO calcolate sullo
scostamento percentuale tra somma dei netti child e netto dichiarato dal parent — esiste **solo
nel monolite**. Il package classificava ancora sui pezzi (`pezzi_accumulati != pezzi_attesi_totali`),
criterio non significativo per MENARINI.

## Conclusione

Il monolite contiene il comportamento corretto e più recente. Il package non conteneva nulla di
recuperabile sul piano funzionale; il suo unico valore era la suddivisione in moduli
(`constants` / `models` / `detection` / `processing`), da riprendere semmai come schema per una
futura riorganizzazione di `espositore.py`.
