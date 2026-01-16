"""
EXTRACTOR_TO - Estrattore MENARINI
===================================
Convertito da TO_EXTRACTOR_v6_0_DB_def.ipynb - Cella 10
Regole: REGOLE_MENARINI.md
"""

import re
from typing import Dict, List

from ...utils import parse_date, format_piva

# Import pdfplumber opzionale
try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False


def extract_menarini(text: str, lines: List[str], pdf_path: str = None) -> List[Dict]:
    """
    Estrattore MENARINI v1.7.
    
    Usa coordinate X per distinguere parent/child:
    - X0 < 28 → PARENT → INCLUDERE
    - X0 >= 28 → CHILD → IGNORARE
    """
    if not pdf_path or not PDFPLUMBER_AVAILABLE:
        return _extract_menarini_text_fallback(text, lines)

    all_orders = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                page_text = page.extract_text() or ""
                words = page.extract_words()
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

                for table in tables:
                    if not table or len(table) < 2:
                        continue
                    header = table[0]
                    if not header or 'Prodotto' not in str(header):
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

                    # Estrazione righe dalla tabella
                    data_rows = [r for r in table[1:] if r and r[0] and not str(r[0]).strip().startswith('Totale')]

                    n_riga = 0
                    for idx, row in enumerate(data_rows):
                        desc_raw = str(row[0] or '').strip()
                        if not desc_raw:
                            continue

                        # Verifica se è child usando coordinate X
                        is_child = False
                        if idx < len(product_coords):
                            is_child = product_coords[idx]['is_child']

                        if is_child:
                            continue  # Ignora righe child

                        cod_min = str(row[1] or '').strip() if len(row) > 1 else ''

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

                        descrizione = re.sub(r'\s*\([A-Z0-9]+\)\s*$', '', desc_raw).strip()[:40]
                        is_espositore = (cod_min == '--' or not re.match(r'^\d{9}$', cod_min))

                        n_riga += 1
                        data['righe'].append({
                            'n_riga': n_riga,
                            'codice_aic': '' if is_espositore else cod_min,
                            'codice_originale': cod_min if cod_min != '--' else '',
                            'descrizione': descrizione,
                            'data_consegna': data.get('data_consegna'),
                            'q_venduta': qty,
                            'q_omaggio': q_omaggio,
                            'sconto1': sconto1,
                            'prezzo_pubblico': prezzo,
                            'prezzo_netto': prezzo_netto,
                            'is_espositore': is_espositore,
                            'is_child': False,
                            'anomalia_no_aic': is_espositore,
                        })

                    if data.get('righe'):
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
