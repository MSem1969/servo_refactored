"""
EXTRACTOR_TO - Estrattore MENARINI
===================================
Convertito da SERV.O_v6_0_DB_def.ipynb - Cella 10
Regole: REGOLE_MENARINI.md

Espositore MENARINI: un espositore occupa PIU' righe di tabella e i dati che
servono a farne una riga d'ordine stanno su righe diverse.

    LAILA ANSIA EXPO BANCO GIOV  | --     | 1 | 98,44 | -- | 78,75   <- parent: prezzo, NIENTE codice
    LAILA 80MG 14CPR CP          | 044460018 | 4 | 8,83 | ... | 28,26   <- child (prodotto reale)
    LAILA EXPO BANCO GIOVANI 2026| 87AB54 | 1 |  0,00 | 0,00 | 0,00   <- materiale: codice, NIENTE prezzo
    LAILA 80MG 28CPR CP          | 044460020 | 4 | 15,78 | ... | 50,50   <- child

Il blocco va dalla riga "--" alla successiva (o a fine tabella) e contiene
sempre esattamente una riga materiale, ma in posizione LIBERA (in testa, in
mezzo o in coda ai child). Il merge codice+prezzo si fa quindi qui, sul blocco:
e' l'unico punto in cui quella posizione e' irrilevante.
"""

import re
from typing import Dict, List, Optional, Set, Tuple

from ....utils import parse_date, format_piva
from ...espositore import elabora_righe_ordine

# Import pdfplumber opzionale
try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

# Import ftfy per fix encoding
try:
    import ftfy
    FTFY_AVAILABLE = True
except ImportError:
    FTFY_AVAILABLE = False

def _normalizza_descrizione_espositore(descrizione: str) -> str:
    """
    Normalizza descrizione per confronto parent/child.

    Rimuove suffissi come "3+3", quantità, e normalizza spazi.
    Es: "AFTAMED EXPO BANCO 3+3" -> "AFTAMED EXPO BANCO"
    """
    if not descrizione:
        return ''
    desc = descrizione.upper().strip()
    # Rimuove pattern pezzi (3+3, 24PZ, etc.)
    desc = re.sub(r'\s*\d+\s*\+\s*\d+\s*$', '', desc)
    desc = re.sub(r'\s*\d+\s*PZ\s*$', '', desc)
    # Rimuove spazi multipli
    desc = re.sub(r'\s+', ' ', desc).strip()
    return desc


def _is_espositore_candidate(cod_min: str, descrizione: str) -> Tuple[bool, Optional[int]]:
    """
    Verifica se la riga è un CANDIDATO espositore MENARINI (parent o child vuoto).

    Args:
        cod_min: Codice ministeriale (es. "--" per espositore)
        descrizione: Descrizione prodotto

    Returns:
        (is_candidate, pezzi_per_unita)

    v9.1 REGOLE:
    - Candidato ha codice "--" E keywords espositore
    - La distinzione parent/child viene fatta in base alla POSIZIONE:
      - Prima occorrenza di una descrizione = PARENT
      - Occorrenze successive stessa descrizione = CHILD (espositore vuoto)
    """
    # MENARINI: l'UNICO elemento distintivo del parent espositore e' il
    # Cod. Min. "--". Le keyword descrittive (BANCO/EXPO/CESTA/...) NON sono
    # affidabili: molti espositori reali (es. AVANCASSA, CESTONE) non le
    # contengono e venivano persi. Basare il riconoscimento sulle keyword era
    # il criterio ANGELINI applicato erroneamente a MENARINI.
    if cod_min != '--':
        return False, None

    desc_upper = descrizione.upper() if descrizione else ''

    # Estrai pezzi da pattern XXPZ o X+Y (dentro la descrizione), se presenti.
    # Non e' piu' usato come criterio di chiusura (che avviene per valore),
    # ma resta come metadato informativo.
    pezzi_per_unita = None

    # Pattern X+Y (es. "3+3")
    match_sum = re.search(r'(\d+)\s*\+\s*(\d+)', desc_upper)
    if match_sum:
        pezzi_per_unita = int(match_sum.group(1)) + int(match_sum.group(2))
    else:
        # Pattern XXPZ
        pezzi_match = re.search(r'(\d+)\s*PZ', desc_upper)
        if pezzi_match:
            pezzi_per_unita = int(pezzi_match.group(1))

    return True, pezzi_per_unita


# =============================================================================
# BLOCCO ESPOSITORE: segmentazione e merge parent + riga materiale
# =============================================================================

# Colonne della tabella prodotti MENARINI
COL_DESCRIZIONE = 0
COL_COD_MIN = 1
COL_QUANTITA = 2
COL_PREZZO = 3
COL_TOTALE_NETTO = 8

_RE_AIC = re.compile(r'^\d{9}$')


def _cella(row: List, idx: int) -> str:
    """Valore testuale di una cella, stringa vuota se la colonna non c'e'."""
    if not row or idx >= len(row):
        return ''
    return str(row[idx] or '').strip()


def _importo(valore: str) -> float:
    """Converte un importo in formato italiano ("1.234,56 €") in float."""
    testo = str(valore or '').replace('€', '').replace('.', '').replace(',', '.').strip()
    if not testo or testo == '--':
        return 0.0
    try:
        return float(testo)
    except ValueError:
        return 0.0


def _intero(valore: str) -> int:
    testo = str(valore or '').strip()
    try:
        return int(testo)
    except ValueError:
        return 0


def _is_riga_parent(cod_min: str, totale_netto: float) -> bool:
    """
    Parent espositore: Cod. Min. "--" **e** un valore.

    Il solo "--" non basta, perche' anche la riga dell'espositore vuoto puo'
    averlo (quando Menarini non stampa il codice materiale): senza il vincolo
    sul valore lo stesso espositore veniva spezzato in due parent distinti.
    """
    return cod_min == '--' and totale_netto > 0


def _is_riga_materiale(cod_min: str, totale_netto: float) -> bool:
    """
    Riga "espositore vuoto": e' il contenitore fisico, non un prodotto.

    Il discriminante e' il **valore a zero**, non il codice: nella maggior parte
    dei PDF la riga porta il codice materiale Menarini (es. 87AB54), ma esiste
    la variante in cui porta "--" e ripete la descrizione del parent
    (es. "AFTAMED EXPO BANCO 3+3 INVERNO", ordine 25990648000426).
    """
    if _RE_AIC.match(cod_min):
        return False
    return totale_netto == 0.0


def _segmenta_blocchi_espositore(
    data_rows: List[List]
) -> Tuple[Dict[int, Dict], Dict[int, int], Set[int], List[Dict]]:
    """
    Segmenta le righe della tabella in blocchi espositore e appaia ogni parent
    con la sua riga materiale, ovunque essa si trovi nel blocco.

    Un blocco va dal parent (Cod. Min. "--" con valore) al parent successivo o
    a fine tabella. Su 98 blocchi nei PDF campione ognuno contiene esattamente
    una riga materiale, ma la sua posizione e' libera: appaiarla in chiusura
    d'espositore (per valore) la perdeva nel 16% dei casi.

    Returns:
        (blocchi, parent_di, indici_materiale, anomalie)
        - blocchi: {idx_parent: {'codice', 'descrizione', 'idx_materiale'}}
        - parent_di: {idx_child: idx_parent}
        - indici_materiale: indici delle righe "espositore vuoto"
        - anomalie: ESP-A08 sui blocchi senza codice materiale o con piu' righe
    """
    indici_parent = [
        idx for idx, row in enumerate(data_rows)
        if _is_riga_parent(
            _cella(row, COL_COD_MIN),
            _importo(_cella(row, COL_TOTALE_NETTO)),
        )
    ]

    blocchi: Dict[int, Dict] = {}
    parent_di: Dict[int, int] = {}
    indici_materiale: Set[int] = set()
    anomalie: List[Dict] = []

    for pos, idx_parent in enumerate(indici_parent):
        fine = indici_parent[pos + 1] if pos + 1 < len(indici_parent) else len(data_rows)
        materiali = [
            idx for idx in range(idx_parent + 1, fine)
            if _is_riga_materiale(
                _cella(data_rows[idx], COL_COD_MIN),
                _importo(_cella(data_rows[idx], COL_TOTALE_NETTO)),
            )
        ]

        desc_parent = _cella(data_rows[idx_parent], COL_DESCRIZIONE)[:40]
        idx_materiale = materiali[0] if materiali else None
        # "--" non e' un codice: e' la variante in cui Menarini non lo stampa
        codice = _cella(data_rows[idx_materiale], COL_COD_MIN) if materiali else ''
        if codice == '--':
            codice = ''

        blocchi[idx_parent] = {
            'codice': codice,
            'descrizione': _cella(data_rows[idx_materiale], COL_DESCRIZIONE)[:40] if materiali else '',
            'idx_materiale': idx_materiale,
        }

        for idx in range(idx_parent + 1, fine):
            parent_di[idx] = idx_parent
        indici_materiale.update(materiali)

        # Senza codice il parent resta identificato dal solo "--" e l'operatore
        # deve saperlo: non e' un dato che possiamo ricavare altrove.
        if not codice:
            motivo = (
                "non espone alcuna riga contenitore"
                if not materiali else
                "espone la riga contenitore senza codice materiale ('--')"
            )
            anomalie.append({
                'tipo_anomalia': 'ESPOSITORE',
                'livello': 'ATTENZIONE',
                'codice_anomalia': 'ESP-A08',
                'descrizione': (
                    f"Espositore '{desc_parent}' {motivo}: "
                    f"il codice della riga d'ordine resta '--'"
                ),
                'valore_anomalo': desc_parent,
                'richiede_supervisione': False,
            })
        elif len(materiali) > 1:
            codici = ', '.join(_cella(data_rows[i], COL_COD_MIN) for i in materiali)
            anomalie.append({
                'tipo_anomalia': 'ESPOSITORE',
                'livello': 'ATTENZIONE',
                'codice_anomalia': 'ESP-A08',
                'descrizione': (
                    f"Espositore '{desc_parent}' con {len(materiali)} righe materiale "
                    f"({codici}): assegnato il primo"
                ),
                'valore_anomalo': desc_parent,
                'richiede_supervisione': False,
            })

    return blocchi, parent_di, indici_materiale, anomalie


def extract_menarini(text: str, lines: List[str], pdf_path: str = None) -> List[Dict]:
    """
    Estrattore MENARINI v2.0.

    v2.0: Supporto espositore parent/child
    - NON filtra più i child
    - Rileva parent con codice "--" + keywords
    - Traccia relazioni parent/child per elaborazione espositore
    """
    if not pdf_path or not PDFPLUMBER_AVAILABLE:
        return _extract_menarini_text_fallback(text, lines)

    all_orders = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                # v10.6: x_tolerance per spacing corretto, ftfy per encoding
                page_text = page.extract_text(x_tolerance=5) or ""
                if FTFY_AVAILABLE:
                    page_text = ftfy.fix_text(page_text)
                words = page.extract_words(x_tolerance=5)
                tables = page.extract_tables()

                # Raggruppa parole per Y (riga)
                rows_by_y = {}
                for w in words:
                    y_key = round(w['top'], 0)
                    if y_key not in rows_by_y:
                        rows_by_y[y_key] = []
                    rows_by_y[y_key].append(w)

                # Identifica coordinate X dei prodotti
                product_coords = []
                for y_key in sorted(rows_by_y.keys()):
                    row_words = sorted(rows_by_y[y_key], key=lambda w: w['x0'])
                    if row_words:
                        first_text = row_words[0]['text'].upper()
                        x0 = row_words[0]['x0']
                        # Keyword prodotti MENARINI
                        keywords = ['AFTAMED', 'FASTUM', 'SUSTENIUM', 'NEBUL', 
                                    'MOMENT', 'VIVIN', 'GLORIA', 'COLLIRIO']
                        if any(kw in first_text for kw in keywords):
                            is_child = (x0 >= 28)  # Soglia indentazione
                            product_coords.append({'y': y_key, 'is_child': is_child, 'x0': x0})

                # v9.5: Gestisce caso header e dati in tabelle separate
                # pdfplumber a volte separa header (Tabella N) e dati (Tabella N+1)
                data_table = None

                for tidx, table in enumerate(tables):
                    if not table:
                        continue

                    # Caso 1: Tabella con header "Prodotto" e >= 2 righe
                    header = table[0]
                    if header and 'Prodotto' in str(header) and len(table) >= 2:
                        data_table = table[1:]  # Salta header
                        break

                    # Caso 2: Tabella solo header "Prodotto" seguita da tabella dati
                    if header and 'Prodotto' in str(header) and len(table) == 1:
                        # Cerca la prossima tabella con dati
                        if tidx + 1 < len(tables) and tables[tidx + 1]:
                            next_table = tables[tidx + 1]
                            # Verifica che non sia un'altra tabella header
                            if next_table[0] and 'Prodotto' not in str(next_table[0]):
                                data_table = next_table
                                break

                    # Caso 3: Tabella dati senza header (cerca per contenuto)
                    # Cerca righe con codice AIC (9 cifre) o "--" nella seconda colonna
                    if len(table) >= 1 and len(table[0]) >= 2:
                        first_row = table[0]
                        desc_col = str(first_row[0] or '').strip().lower()
                        cod_col = str(first_row[1] or '') if len(first_row) > 1 else ''
                        # Skip tabella spuria "Note Cliente" (overflow note legali su pagina extra)
                        if desc_col == 'note cliente':
                            continue
                        if cod_col == '--' or (cod_col.isdigit() and len(cod_col) == 9):
                            # Probabilmente è una tabella dati prodotti
                            data_table = table
                            break

                if not data_table:
                    continue

                # Skip pagine di overflow (note legali su pagina extra senza
                # header ordine): se manca "Ordine N." nel testo non e' un
                # ordine reale.
                m_ord = re.search(r'Ordine\s+N\.?:?\s*(\d+)(?:_\d{8})?', page_text)
                if not m_ord:
                    continue

                data = {'vendor': 'MENARINI', 'righe': []}

                # Estrazione header
                data['numero_ordine'] = m_ord.group(1).strip()

                m = re.search(r'Cliente\s+(.+?)\s+Cod\.?\s*Cliente', page_text)
                if m:
                    data['ragione_sociale'] = m.group(1).strip()[:50]

                m = re.search(r'Partita\s+IVA\s+(\d{11})', page_text)
                if m:
                    data['partita_iva'] = format_piva(m.group(1))

                m = re.search(r'Indirizzo\s+(.+?)\s+CAP\s+(\d{5})', page_text)
                if m:
                    data['indirizzo'] = m.group(1).strip()[:50]
                    data['cap'] = m.group(2)

                m = re.search(r"Città\s+([A-Z][A-Z\s/'-]+?)\s+Provincia\s+([A-Z]{2})", page_text)
                if m:
                    data['citta'] = m.group(1).strip()[:50]
                    data['provincia'] = m.group(2)

                m = re.search(r'Rep\s+([A-Z][A-Z\s]+?)\s+Tipo\s+Ordine', page_text)
                if m:
                    data['nome_agente'] = m.group(1).strip()[:50]

                m = re.search(r'Data\s+Ordine\s+(\d{2}/\d{2}/\d{4})', page_text)
                if m:
                    data['data_ordine'] = parse_date(m.group(1))

                m = re.search(r'Data\s+Consegna\s+(\d{2}/\d{2}/\d{4})', page_text)
                if m:
                    data['data_consegna'] = parse_date(m.group(1))

                m = re.search(r'(\d+)\s*GG', page_text, re.I)
                data['gg_dilazione'] = int(m.group(1)) if m else 90

                # Estrazione righe dalla tabella (già senza header)
                data_rows = [r for r in data_table if r and r[0] and not str(r[0]).strip().startswith('Totale')]

                # Appaia ogni parent con la sua riga materiale prima di emettere
                # le righe: cosi' la posizione del materiale nel blocco non conta.
                blocchi, parent_di, indici_materiale, anomalie_blocchi = \
                    _segmenta_blocchi_espositore(data_rows)

                n_riga = 0

                for idx, row in enumerate(data_rows):

                    desc_raw = _cella(row, COL_DESCRIZIONE)
                    if not desc_raw:
                        continue

                    cod_min = _cella(row, COL_COD_MIN)
                    qty = _intero(_cella(row, COL_QUANTITA))
                    prezzo = _importo(_cella(row, COL_PREZZO))

                    sconto_str = _cella(row, 4) or '--'
                    sconto1 = 0.0
                    if sconto_str != '--':
                        try:
                            sconto1 = float(sconto_str.replace('%', '').replace(',', '.'))
                        except ValueError:
                            pass

                    sm = _cella(row, 5)
                    om = _cella(row, 6)
                    q_sm = int(sm) if sm.isdigit() else 0
                    q_om = int(om) if om.isdigit() else 0
                    q_omaggio = q_sm + q_om

                    prezzo_netto = _importo(_cella(row, 7))
                    totale_netto = _importo(_cella(row, COL_TOTALE_NETTO))

                    descrizione = re.sub(r'\s*\([A-Z0-9]+\)\s*$', '', desc_raw).strip()[:40]
                    desc_norm = _normalizza_descrizione_espositore(descrizione)
                    is_aic = bool(_RE_AIC.match(cod_min))

                    # PARENT ESPOSITORE: identificato dal solo Cod. Min. "--",
                    # completato col codice materiale del blocco e valorizzato
                    # con i prezzi DICHIARATI dal PDF (non ricalcolati).
                    if idx in blocchi:
                        _, pezzi_per_unita = _is_espositore_candidate(cod_min, descrizione)
                        blocco = blocchi[idx]
                        codice_materiale = blocco['codice']
                        divisore = qty if qty > 0 else 1

                        n_riga += 1
                        data['righe'].append({
                            'n_riga': n_riga,
                            'codice_aic': '',
                            'codice_originale': codice_materiale or cod_min,
                            'codice_materiale': codice_materiale,
                            'descrizione': descrizione,
                            'descrizione_normalizzata': desc_norm,
                            'descrizione_materiale': blocco['descrizione'],
                            'data_consegna': data.get('data_consegna'),
                            'q_venduta': qty,
                            'quantita': qty,
                            'q_omaggio': q_omaggio,
                            'sconto1': sconto1,
                            'prezzo_pubblico': round(prezzo / divisore, 2),
                            'prezzo_netto': round(totale_netto / divisore, 2),
                            'valore_netto': totale_netto,
                            'is_espositore': True,
                            'is_child': False,
                            'tipo_riga': 'PARENT_ESPOSITORE',
                            'pezzi_per_unita': pezzi_per_unita,
                            'prezzo_netto_parent': round(totale_netto / divisore, 2),
                            'anomalia_no_aic': False,
                        })
                        continue

                    is_child_of_parent = idx in parent_di
                    is_espositore_vuoto = idx in indici_materiale

                    n_riga += 1
                    riga_data = {
                        'n_riga': n_riga,
                        'codice_aic': cod_min if is_aic else '',
                        'codice_originale': cod_min,
                        'descrizione': descrizione,
                        'data_consegna': data.get('data_consegna'),
                        'q_venduta': qty,
                        'quantita': qty,
                        'q_omaggio': q_omaggio,
                        'sconto1': sconto1,
                        'prezzo_pubblico': prezzo,
                        'prezzo_netto': prezzo_netto,
                        'valore_netto': totale_netto,
                        'is_espositore': False,
                        'is_child': is_child_of_parent,
                        'is_espositore_vuoto': is_espositore_vuoto,
                        # Il tipo e' sempre esplicito: identifica_tipo_riga
                        # classificherebbe come PARENT qualunque riga "--",
                        # compresa quella del contenitore vuoto.
                        'tipo_riga': 'CHILD_ESPOSITORE' if is_child_of_parent else 'PRODOTTO_STANDARD',
                        'anomalia_no_aic': not is_aic and not is_child_of_parent,
                    }

                    # Marca child
                    if is_child_of_parent:
                        riga_data['_belongs_to_parent'] = True
                        riga_data['_parent_desc_norm'] = _normalizza_descrizione_espositore(
                            _cella(data_rows[parent_di[idx]], COL_DESCRIZIONE)
                        )

                    data['righe'].append(riga_data)

                # v2.0: Elabora righe con logica espositori
                if data.get('righe'):
                    righe_raw = data['righe']
                    data['righe_raw'] = righe_raw

                    # Elabora con logica espositori MENARINI
                    ctx = elabora_righe_ordine(righe_raw, vendor='MENARINI')
                    # I child restano nell'output: vanno salvati in DB con
                    # is_child=TRUE (fuori da tracciato, AIC, listino e contatori)
                    # per rendere visibile la composizione dell'espositore.
                    data['righe'] = ctx.righe_output
                    data['anomalie_espositore'] = anomalie_blocchi + ctx.anomalie
                    data['_stats'] = {
                        'righe_raw': len(righe_raw),
                        'righe_output': len(ctx.righe_output),
                        'espositori': ctx.espositori_elaborati,
                        'chiusure_normali': ctx.chiusure_normali,
                        'chiusure_forzate': ctx.chiusure_forzate,
                        'anomalie': len(data['anomalie_espositore']),
                    }

                    all_orders.append(data)

    except Exception as e:
        print(f"   ⚠️ Errore estrazione MENARINI: {e}")
        return _extract_menarini_text_fallback(text, lines)

    return all_orders if all_orders else _extract_menarini_text_fallback(text, lines)


def _extract_menarini_text_fallback(text: str, lines: List[str]) -> List[Dict]:
    """Fallback MENARINI quando pdf_path non è disponibile."""
    data = {'vendor': 'MENARINI', 'righe': []}

    m = re.search(r'Ordine\s+N\.?:?\s*(\d+)(?:_\d{8})?', text)
    if m:
        data['numero_ordine'] = m.group(1).strip()

    m = re.search(r'Cliente\s+(.+?)\s+Cod\.?\s*Cliente', text)
    if m:
        data['ragione_sociale'] = m.group(1).strip()[:50]

    m = re.search(r'Partita\s+IVA\s+(\d{11})', text)
    if m:
        data['partita_iva'] = format_piva(m.group(1))

    m = re.search(r'Indirizzo\s+(.+?)\s+CAP\s+(\d{5})', text)
    if m:
        data['indirizzo'] = m.group(1).strip()[:50]
        data['cap'] = m.group(2)

    m = re.search(r"Città\s+([A-Z][A-Z\s/'-]+?)\s+Provincia\s+([A-Z]{2})", text)
    if m:
        data['citta'] = m.group(1).strip()[:50]
        data['provincia'] = m.group(2)

    m = re.search(r'Data\s+Ordine\s+(\d{2}/\d{2}/\d{4})', text)
    if m:
        data['data_ordine'] = parse_date(m.group(1))

    m = re.search(r'Data\s+Consegna\s+(\d{2}/\d{2}/\d{4})', text)
    if m:
        data['data_consegna'] = parse_date(m.group(1))

    m = re.search(r'(\d+)\s*GG', text, re.I)
    data['gg_dilazione'] = int(m.group(1)) if m else 90

    n_riga = 0
    for line in lines:
        line_stripped = line.strip()
        m = re.search(r'(\d{9})\s+(\d+)\s+', line_stripped)
        if m:
            cod_min = m.group(1)
            qty = int(m.group(2))

            if line.startswith('  ') or line.startswith('\t'):
                continue

            desc_match = re.match(r'^(.+?)\s+\d{9}', line_stripped)
            descrizione = desc_match.group(1).strip()[:40] if desc_match else ''

            n_riga += 1
            is_espositore = (cod_min == '--' or not re.match(r'^\d{9}$', cod_min))

            data['righe'].append({
                'n_riga': n_riga,
                'codice_aic': '' if is_espositore else cod_min,
                'codice_originale': cod_min,
                'descrizione': descrizione,
                'q_venduta': qty,
                'is_espositore': is_espositore,
                'is_child': False,
                'anomalia_no_aic': is_espositore,
            })

    return [data] if data.get('righe') or data.get('numero_ordine') else [{'vendor': 'MENARINI', 'righe': []}]
