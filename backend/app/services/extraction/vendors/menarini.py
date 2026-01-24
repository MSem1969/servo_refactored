"""
EXTRACTOR_TO - Estrattore MENARINI
===================================
Convertito da SERV.O_v6_0_DB_def.ipynb - Cella 10
Regole: REGOLE_MENARINI.md

v2.0 - Supporto Espositore Parent/Child
- Parent: codice "--" + keywords (BANCO, FSTAND, etc.)
- Child: righe successive, non più filtrate
- Chiusura: basata su somma valore netto
"""

import re
from typing import Dict, List, Optional, Tuple

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

# Keywords per identificare espositori
ESPOSITORE_KEYWORDS = r'BANCO|DBOX|FSTAND|EXPO|DISPLAY|ESPOSITORE|CESTA'


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


def _is_child_per_descrizione(desc_riga: str, desc_parent_norm: str) -> bool:
    """
    v9.0: Verifica se una riga è child in base alla descrizione.

    Una riga è child se:
    - La sua descrizione normalizzata corrisponde o è contenuta nel parent
    - Es: "AFTAMED EXPO BANCO" (child) matches "AFTAMED EXPO BANCO" (parent norm)
    """
    if not desc_parent_norm or not desc_riga:
        return False

    desc_norm = _normalizza_descrizione_espositore(desc_riga)

    # Match esatto
    if desc_norm == desc_parent_norm:
        return True

    # La descrizione della riga è contenuta nel parent (senza i numeri)
    # Es: "AFTAMED EXPO BANCO" è contenuta in "AFTAMED EXPO BANCO"
    if desc_norm and desc_parent_norm:
        # Estrai la parte "nome prodotto" (primi 2-3 token)
        tokens_riga = desc_norm.split()[:3]
        tokens_parent = desc_parent_norm.split()[:3]

        # Se i primi token corrispondono, è un child (stesso prodotto base)
        if tokens_riga and tokens_parent:
            if tokens_riga[0] == tokens_parent[0]:  # Almeno il primo token uguale
                # E almeno 2 token in comune
                common = set(tokens_riga) & set(tokens_parent)
                if len(common) >= 2:
                    return True

    return False


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
    # MENARINI: espositore ha codice "--"
    if cod_min != '--':
        return False, None

    desc_upper = descrizione.upper() if descrizione else ''
    if not re.search(ESPOSITORE_KEYWORDS, desc_upper, re.I):
        return False, None

    # Estrai pezzi da pattern XXPZ o X+Y (dentro la descrizione)
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
                        cod_col = str(first_row[1] or '') if len(first_row) > 1 else ''
                        if cod_col == '--' or (cod_col.isdigit() and len(cod_col) == 9):
                            # Probabilmente è una tabella dati prodotti
                            data_table = table
                            break

                if not data_table:
                    continue

                data = {'vendor': 'MENARINI', 'righe': []}

                # Estrazione header
                m = re.search(r'Ordine\s+N\.?:?\s*(\d+)(?:_\d{8})?', page_text)
                if m:
                    data['numero_ordine'] = m.group(1).strip()

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

                n_riga = 0
                # v9.1: Tracciamento parent/child per espositori
                has_active_parent = False
                active_parent_desc_norm = ''
                seen_espositori = set()
                accumulated_child_value = 0.0

                for idx, row in enumerate(data_rows):

                    desc_raw = str(row[0] or '').strip()
                    if not desc_raw:
                        continue

                    cod_min = str(row[1] or '').strip() if len(row) > 1 else ''

                    # Debug per espositore
                    if 'SUST' in desc_raw.upper() or 'BANCO' in desc_raw.upper() or 'EXPO' in desc_raw.upper():
                        print(f"   [DEBUG] Row {idx}: desc='{desc_raw[:35]}', cod_min='{cod_min}'")

                    try:
                        qty = int(str(row[2] or '0').strip()) if len(row) > 2 else 0
                    except:
                        qty = 0

                    try:
                        prezzo = float(str(row[3] or '0').replace('€', '').replace(',', '.').strip()) if len(row) > 3 else 0.0
                    except:
                        prezzo = 0.0

                    sconto_str = str(row[4] or '--').strip() if len(row) > 4 else '--'
                    sconto1 = 0.0
                    if sconto_str != '--':
                        try:
                            sconto1 = float(sconto_str.replace('%', '').replace(',', '.'))
                        except:
                            pass

                    sm = str(row[5] or '--').strip() if len(row) > 5 else '--'
                    om = str(row[6] or '--').strip() if len(row) > 6 else '--'
                    q_sm = int(sm) if sm.isdigit() else 0
                    q_om = int(om) if om.isdigit() else 0
                    q_omaggio = q_sm + q_om

                    pn = str(row[7] or '--').replace('€', '').replace(',', '.').strip() if len(row) > 7 else '--'
                    prezzo_netto = float(pn) if pn and pn != '--' else 0.0

                    # v9.3: Totale Netto da col[8] - usato per chiusura espositore
                    tn = str(row[8] or '--').replace('€', '').replace(',', '.').strip() if len(row) > 8 else '--'
                    totale_netto = float(tn) if tn and tn != '--' else 0.0

                    descrizione = re.sub(r'\s*\([A-Z0-9]+\)\s*$', '', desc_raw).strip()[:40]

                    # v9.1: Verifica se è un candidato espositore (codice "--" + keywords)
                    is_espositore_candidate, pezzi_per_unita = _is_espositore_candidate(cod_min, descrizione)
                    desc_norm = _normalizza_descrizione_espositore(descrizione)
                    is_aic = bool(re.match(r'^\d{9}$', cod_min))

                    # v9.3: LOGICA PARENT/CHILD basata su ORDINE DI APPARIZIONE
                    if is_espositore_candidate:
                        # v9.4: LOGICA MENARINI basata su TOTALE NETTO
                        if totale_netto > 0:
                            # PARENT: espositore con valore
                            print(f"   [DEBUG v9.4] PARENT detected: '{desc_norm}' totale_netto={totale_netto}")

                            has_active_parent = True
                            active_parent_desc_norm = desc_norm
                            accumulated_child_value = 0.0

                            n_riga += 1
                            data['righe'].append({
                                'n_riga': n_riga,
                                'codice_aic': '',
                                'codice_originale': cod_min,
                                'descrizione': descrizione,
                                'descrizione_normalizzata': desc_norm,
                                'data_consegna': data.get('data_consegna'),
                                'q_venduta': qty,
                                'quantita': qty,
                                'q_omaggio': q_omaggio,
                                'sconto1': sconto1,
                                'prezzo_pubblico': prezzo,
                                'prezzo_netto': totale_netto,
                                'valore_netto': totale_netto,
                                'is_espositore': True,
                                'is_child': False,
                                'tipo_riga': 'PARENT_ESPOSITORE',
                                'pezzi_per_unita': pezzi_per_unita,
                                'prezzo_netto_parent': totale_netto,
                                'anomalia_no_aic': False,
                            })
                            continue
                        else:
                            # CHILD: espositore vuoto (Totale Netto = 0)
                            print(f"   [DEBUG v9.4] CHILD (espositore vuoto) detected: '{desc_norm}' totale_netto=0")
                            pass  # Continua sotto come child

                    # v9.5: Logica child MENARINI - TUTTI i prodotti dopo parent sono child
                    is_child_of_parent = False
                    is_espositore_vuoto = False

                    if has_active_parent:
                        # TUTTE le righe dopo un parent sono child fino a chiusura
                        is_child_of_parent = True
                        # Non-AIC = materiale espositore (escluso da tracciato)
                        if not is_aic:
                            is_espositore_vuoto = True

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
                        'anomalia_no_aic': not is_aic and not is_child_of_parent,
                    }

                    # Marca child
                    if is_child_of_parent:
                        riga_data['_belongs_to_parent'] = True
                        riga_data['tipo_riga'] = 'CHILD_ESPOSITORE'
                        riga_data['_parent_desc_norm'] = active_parent_desc_norm

                    data['righe'].append(riga_data)

                # v2.0: Elabora righe con logica espositori
                if data.get('righe'):
                    righe_raw = data['righe']
                    data['righe_raw'] = righe_raw

                    # Elabora con logica espositori MENARINI
                    ctx = elabora_righe_ordine(righe_raw, vendor='MENARINI')
                    # v9.4: Filtra righe CHILD_ESPOSITORE
                    data['righe'] = [r for r in ctx.righe_output if r.get('tipo_riga') != 'CHILD_ESPOSITORE']
                    data['anomalie_espositore'] = ctx.anomalie
                    data['_stats'] = {
                        'righe_raw': len(righe_raw),
                        'righe_output': len(ctx.righe_output),
                        'espositori': ctx.espositori_elaborati,
                        'chiusure_normali': ctx.chiusure_normali,
                        'chiusure_forzate': ctx.chiusure_forzate,
                        'anomalie': len(ctx.anomalie),
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
