"""
EXTRACTOR_TO - Estrattore DOMPE v1.0
=====================================
Formato: PROPOSTA D'ORDINE Dompé

Peculiarità:
- AIC in sotto-riga "Cod. AIC/Paraf XXXXX" (senza zero-padding, può avere suffisso /M)
- Primo codice nella cella ARTICOLO è codice interno (ignorato)
- Cliente in sezione "CLIENTE DESTINATARIO MERCE" (no MIN_ID nel documento)
- Consegne multiple con date in header colonna (come BAYER)
- Ordini multi-pagina: pagina 2+ senza header ripetuto
- Struttura tabella: 17 colonne pag.1, ~14 colonne pag.2+
- Riga "ALLESTIMENTO" con PP=0 è espositore/display (flag informativo)
"""

import re
import pdfplumber
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from ....utils import parse_date, parse_decimal, parse_int, format_piva


ESPOSITORE_KEYWORDS = ['ALLESTIMENTO', 'BANCO', 'DBOX', 'FSTAND', 'EXPO', 'DISPLAY', 'ESPOSITORE']


def _is_espositore(descrizione: str) -> bool:
    """Verifica se il prodotto è un espositore (solo flag informativo)."""
    desc_upper = descrizione.upper()
    return any(kw in desc_upper for kw in ESPOSITORE_KEYWORDS)


def _parse_aic_from_cell(cell_text: str) -> Optional[str]:
    """
    Estrae e normalizza il codice AIC dalla cella ARTICOLO Dompé.

    Formato: "Cod. AIC/Paraf XXXXX" oppure "Cod. AIC/Paraf XXXXX/M"
    - Rimuove suffisso /M (farmaco mutuabile)
    - Zero-padding a 9 cifre

    Returns:
        Codice AIC a 9 cifre o None
    """
    if not cell_text:
        return None

    match = re.search(r'Cod\.\s*AIC/Paraf\s+(\S+)', cell_text)
    if not match:
        return None

    raw = match.group(1).strip()

    # Rimuovi suffisso /M (mutuabile)
    raw = re.sub(r'/[A-Za-z]+$', '', raw)

    # Rimuovi caratteri non numerici
    digits = re.sub(r'[^\d]', '', raw)

    if not digits:
        return None

    # Zero-padding a 9 cifre
    return digits.zfill(9)


def _parse_description_from_cell(cell_text: str) -> str:
    """
    Estrae descrizione prodotto dalla cella ARTICOLO Dompé.

    Formato: "CODICE_INTERNO DESCRIZIONE\nCod. AIC/Paraf XXXXX"
    Il codice interno (8 cifre) viene ignorato.
    """
    if not cell_text:
        return ''

    # Prendi solo la prima riga (prima di \n)
    first_line = cell_text.split('\n')[0].strip()

    # Rimuovi codice interno iniziale (5-8 cifre)
    desc = re.sub(r'^\d{5,8}\s+', '', first_line)

    return desc.strip()[:40]


def _extract_dates_from_header(table_rows: list) -> List[Tuple[str, Optional[str]]]:
    """
    Estrae le date consegna dalla riga header della tabella Dompé.

    La riga 6 (indice 6) contiene le date nelle colonne 11+ (pagina 1, 17 cols).
    Formato date: "18 mar\n2026" oppure "05/05/\n26"
    """
    dates = []

    # Cerca la riga header con le date (subito dopo la riga ARTICOLO)
    for row in table_rows:
        if not row or len(row) < 12:
            continue
        # La riga date ha None in col[0] e date in col[11+]
        if row[0] is not None:
            continue

        for col_idx in range(11, len(row)):
            cell = row[col_idx]
            if not cell or cell.strip() == '-':
                continue

            # Normalizza: rimuovi newline, unisci
            date_text = cell.replace('\n', ' ').strip()

            # Formato "05/05/26" → "05/05/2026"
            m = re.match(r'(\d{2})/(\d{2})/\s*(\d{2})$', date_text)
            if m:
                year = '20' + m.group(3)
                date_text = f"{m.group(1)}/{m.group(2)}/{year}"

            parsed = parse_date(date_text)
            if parsed:
                dates.append((date_text, parsed))

        break  # Solo la prima riga date

    return dates


def _extract_header_from_table(table: list) -> Dict:
    """Estrae dati testata dal blocco header della tabella pagina 1."""
    header = {}

    for row in table:
        if not row or len(row) < 11:
            continue

        # CLIENTE DESTINATARIO MERCE (col[10] nella riga CLIENTE COMMITTENTE)
        if row[0] and 'CLIENTE' in str(row[0]) and 'COMMITTENTE' in str(row[0]):
            cliente_cell = row[10] if len(row) > 10 and row[10] else ''
            if cliente_cell:
                cl_lines = cliente_cell.split('\n')
                # Formato fisso: [0]=codice, [1]=ragione_sociale, [2]=P.IVA, [3]=indirizzo, [4]=città, [5]=(PROV)
                for i, cl_line in enumerate(cl_lines):
                    cl_line = cl_line.strip()
                    if i == 0 and re.match(r'^\d{10}$', cl_line):
                        header['codice_cliente'] = cl_line
                    elif 'P.IVA:' in cl_line:
                        m = re.search(r'P\.IVA:\s*(\d{11})', cl_line)
                        if m:
                            header['partita_iva'] = format_piva(m.group(1))
                    elif re.match(r'^\([A-Z]{2}\)$', cl_line):
                        header['provincia'] = cl_line[1:3]
                        # La riga prima della provincia è la città
                        if i > 0 and not header.get('citta'):
                            prev = cl_lines[i - 1].strip()
                            if prev and 'P.IVA' not in prev and not re.match(r'^\d{10}$', prev):
                                header['citta'] = prev
                    elif not header.get('ragione_sociale') and not re.match(r'^\d', cl_line) and 'P.IVA' not in cl_line:
                        header['ragione_sociale'] = cl_line[:50]
                # Indirizzo: la riga dopo P.IVA e prima di città
                for i, cl_line in enumerate(cl_lines):
                    cl_line = cl_line.strip()
                    if 'P.IVA:' in cl_line and i + 1 < len(cl_lines):
                        next_line = cl_lines[i + 1].strip()
                        if next_line and next_line != header.get('citta') and not re.match(r'^\([A-Z]', next_line):
                            header['indirizzo'] = next_line[:50]
                        break

        # COLLABORATORE
        if row[0] and 'COLLABORATORE' in str(row[0]) and row[1]:
            header['nome_agente'] = str(row[1]).strip()

        # N. PROP. D'ORDINE
        if row[0] and "PROP" in str(row[0]) and "ORDINE" in str(row[0]) and row[1]:
            header['numero_ordine'] = str(row[1]).strip()

        # DATA ACQUISIZIONE
        if row[0] and 'DATA ACQUISIZIONE' in str(row[0]) and row[1]:
            header['data_ordine'] = parse_date(str(row[1]).strip())

    return header


def _extract_products_page1(table: list, date_columns: list) -> List[Dict]:
    """Estrae prodotti dalla tabella pagina 1 (17 colonne)."""
    products = []
    in_products = False

    for row in table:
        if not row or len(row) < 12:
            continue

        # Rileva inizio sezione prodotti (dopo riga ARTICOLO)
        if row[0] and 'ARTICOLO' in str(row[0]):
            in_products = True
            continue

        # Skip riga date header
        if row[0] is None and in_products:
            continue

        if not in_products:
            continue

        cell0 = str(row[0] or '').strip()
        if not cell0:
            continue

        # Deve iniziare con codice numerico (5-8 cifre)
        if not re.match(r'^\d{5,8}\s+', cell0):
            continue

        aic = _parse_aic_from_cell(cell0)
        descrizione = _parse_description_from_cell(cell0)

        # Quantità e prezzi
        prezzo_pubblico = float(parse_decimal(row[2])) if row[2] else 0.0
        aliquota_str = str(row[3] or '').replace('%', '').strip()
        aliquota_iva = parse_int(aliquota_str) if aliquota_str else 10
        q_totale = parse_int(row[4]) if row[4] else 0
        q_merce_sconto = parse_int(row[5]) if row[5] else 0
        prezzo_netto = float(parse_decimal(row[8])) if row[8] else 0.0
        valore_netto = float(parse_decimal(row[9])) if row[9] else 0.0

        # Quantità per data consegna (colonne 11+)
        num_dc = max(1, len(date_columns))
        date_quantities = []
        for col_idx in range(11, 11 + num_dc):
            if col_idx < len(row) and row[col_idx] and str(row[col_idx]).strip():
                qty = parse_int(row[col_idx])
            else:
                qty = 0
            date_quantities.append(qty)

        products.append({
            'aic': aic,
            'aic_raw': re.search(r'Cod\.\s*AIC/Paraf\s+(\S+)', cell0).group(1) if aic else '',
            'descrizione': descrizione,
            'prezzo_pubblico': prezzo_pubblico,
            'aliquota_iva': aliquota_iva,
            'q_totale': q_totale,
            'q_merce_sconto': q_merce_sconto,
            'prezzo_netto': prezzo_netto,
            'valore_netto': valore_netto,
            'date_quantities': date_quantities,
        })

    return products


def _extract_products_page2(table: list, num_date_columns: int) -> List[Dict]:
    """
    Estrae prodotti da tabelle pagina 2+ (colonne ridotte, ~14 cols).
    Salta le righe "blob" dove tutto il contenuto è in col[0].
    """
    products = []

    for row in table:
        if not row:
            continue

        # Skip righe blob (tutto in col[0], altri cols None)
        non_none_cols = sum(1 for c in row if c is not None and str(c).strip())
        if non_none_cols < 3:
            continue

        cell0 = str(row[0] or '').strip()
        if not cell0 or not re.match(r'^\d{5,8}\s+', cell0):
            continue

        if 'Cod.' not in cell0 and 'AIC' not in cell0:
            continue

        aic = _parse_aic_from_cell(cell0)
        descrizione = _parse_description_from_cell(cell0)

        # Page 2: colonne compresse (no spacer cols)
        # [0]=articolo, [1]=PP, [2]=%IVA, [3]=Q.tà, [4]=M.Sc., [5]=Reint, [6]=P.zzo, [7]=Totale, [8+]=date
        prezzo_pubblico = float(parse_decimal(row[1])) if len(row) > 1 and row[1] else 0.0
        aliquota_str = str(row[2] or '').replace('%', '').strip() if len(row) > 2 else ''
        aliquota_iva = parse_int(aliquota_str) if aliquota_str else 10
        q_totale = parse_int(row[3]) if len(row) > 3 and row[3] else 0
        q_merce_sconto = parse_int(row[4]) if len(row) > 4 and row[4] else 0
        prezzo_netto = float(parse_decimal(row[6])) if len(row) > 6 and row[6] else 0.0
        valore_netto = float(parse_decimal(row[7])) if len(row) > 7 and row[7] else 0.0

        # Date quantities partono da col[8] su pagina 2
        date_quantities = []
        for col_idx in range(8, 8 + num_date_columns):
            if col_idx < len(row) and row[col_idx] and str(row[col_idx]).strip():
                qty = parse_int(row[col_idx])
            else:
                qty = 0
            date_quantities.append(qty)

        aic_raw_match = re.search(r'Cod\.\s*AIC/Paraf\s+(\S+)', cell0)
        products.append({
            'aic': aic,
            'aic_raw': aic_raw_match.group(1) if aic_raw_match else '',
            'descrizione': descrizione,
            'prezzo_pubblico': prezzo_pubblico,
            'aliquota_iva': aliquota_iva,
            'q_totale': q_totale,
            'q_merce_sconto': q_merce_sconto,
            'prezzo_netto': prezzo_netto,
            'valore_netto': valore_netto,
            'date_quantities': date_quantities,
        })

    return products


def _extract_products_from_text(text: str, num_date_columns: int) -> List[Dict]:
    """
    Fallback: estrae prodotti dal testo raw (per pagine dove la tabella non è strutturata).
    Cerca pattern "Cod. AIC/Paraf XXXXX" e ricostruisce i dati dalla riga precedente.
    """
    products = []
    lines = text.split('\n')

    for i, line in enumerate(lines):
        aic_match = re.search(r'Cod\.\s*AIC/Paraf\s+(\S+)', line)
        if not aic_match:
            continue

        aic_raw = aic_match.group(1)
        aic_clean = re.sub(r'/[A-Za-z]+$', '', aic_raw)
        aic_digits = re.sub(r'[^\d]', '', aic_clean)
        aic = aic_digits.zfill(9) if aic_digits else None

        # La riga precedente contiene: cod_interno DESCRIZIONE PP IVA QTY ... TOTALE date_qtys
        if i > 0:
            prev_line = lines[i - 1].strip()
            # Pattern: codice_interno DESCRIZIONE numeri...
            m = re.match(r'(\d{5,8})\s+(.+?)\s+([\d,]+)\s+(\d+)%\s+(\d+)\s+([\d,]+)\s+([\d,]+)\s+(.*)', prev_line)
            if m:
                descrizione = m.group(2).strip()[:40]
                prezzo_pubblico = float(parse_decimal(m.group(3)))
                aliquota_iva = int(m.group(4))
                q_totale = parse_int(m.group(5))
                prezzo_netto = float(parse_decimal(m.group(6)))
                valore_netto = float(parse_decimal(m.group(7)))

                # Rimanenti numeri sono le quantità per data
                remainder = m.group(8).strip()
                nums = [parse_int(n) for n in re.findall(r'\d+', remainder)]

                date_quantities = nums[:num_date_columns] if nums else [q_totale]
                while len(date_quantities) < num_date_columns:
                    date_quantities.append(0)

                products.append({
                    'aic': aic,
                    'aic_raw': aic_raw,
                    'descrizione': descrizione,
                    'prezzo_pubblico': prezzo_pubblico,
                    'aliquota_iva': aliquota_iva,
                    'q_totale': q_totale,
                    'q_merce_sconto': 0,
                    'prezzo_netto': prezzo_netto,
                    'valore_netto': valore_netto,
                    'date_quantities': date_quantities,
                })

    return products


def extract_dompe(text: str, lines: List[str], pdf_path: str = None) -> List[Dict]:
    """
    Estrae dati da PDF DOMPE (formato Proposta d'Ordine).

    Particolarità DOMPE:
    - AIC in sotto-riga "Cod. AIC/Paraf" con zero-padding a 9 cifre
    - Codice interno (prima colonna) ignorato
    - Date consegna multiple negli header colonna
    - Ordini multi-pagina senza header ripetuto
    - ALLESTIMENTO = espositore (flag informativo)
    """
    data = {
        'vendor': 'DOMPE',
        'righe': [],
        'anomalie': [],
    }

    # ========================================
    # ESTRAZIONE DA TABELLA PDF
    # ========================================
    page1_table = None
    page2_tables = []
    date_columns = []

    if pdf_path:
        try:
            with pdfplumber.open(pdf_path) as pdf:
                # Pagina 1: header + prodotti + date
                if pdf.pages:
                    tables = pdf.pages[0].extract_tables()
                    if tables:
                        page1_table = tables[0]

                # Pagine successive: solo prodotti
                for page_idx in range(1, len(pdf.pages)):
                    tables = pdf.pages[page_idx].extract_tables()
                    if tables:
                        page2_tables.append(tables[0])
        except Exception as e:
            print(f"[DOMPE] PDF extraction error: {e}")

    if not page1_table:
        # Fallback: ritorna dati minimi
        data['_stats'] = {'extraction_method': 'failed', 'error': 'no table found'}
        return [data]

    # ========================================
    # HEADER
    # ========================================
    header = _extract_header_from_table(page1_table)
    data['numero_ordine'] = header.get('numero_ordine', '')
    data['data_ordine'] = header.get('data_ordine', '')
    data['ragione_sociale'] = header.get('ragione_sociale', '')
    data['partita_iva'] = header.get('partita_iva', '')
    data['indirizzo'] = header.get('indirizzo', '')
    data['citta'] = header.get('citta', '')
    data['provincia'] = header.get('provincia', '')
    data['nome_agente'] = header.get('nome_agente', '')

    # ========================================
    # DATE CONSEGNA
    # ========================================
    date_columns = _extract_dates_from_header(page1_table)

    # Escludi data ordine (stessa fix di Bayer)
    data_ordine = data.get('data_ordine')
    if data_ordine and date_columns:
        date_columns = [d for d in date_columns if d[1] != data_ordine]

    num_date_columns = max(1, len(date_columns))

    # Data consegna default (prima data consegna trovata)
    if date_columns:
        data['data_consegna'] = date_columns[0][1]

    # ========================================
    # ESTRAZIONE PRODOTTI
    # ========================================
    all_products = []

    # Pagina 1: estrazione tabellare (17 colonne)
    page1_products = _extract_products_page1(page1_table, date_columns)
    all_products.extend(page1_products)

    # Pagine 2+: estrazione tabellare (colonne ridotte)
    page2_product_count = 0
    for p2_table in page2_tables:
        p2_products = _extract_products_page2(p2_table, num_date_columns)
        if p2_products:
            all_products.extend(p2_products)
            page2_product_count += len(p2_products)

    # Fallback testo per pagine 2+ se non trovati prodotti via tabella
    if page2_tables and page2_product_count == 0 and pdf_path:
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_idx in range(1, len(pdf.pages)):
                    page_text = pdf.pages[page_idx].extract_text() or ''
                    text_products = _extract_products_from_text(page_text, num_date_columns)
                    all_products.extend(text_products)
        except Exception as e:
            print(f"[DOMPE] Text fallback error: {e}")

    # Deduplicazione (stessa AIC + stessa q_totale potrebbe essere estratta da tabella e testo)
    seen = set()
    unique_products = []
    for p in all_products:
        key = (p.get('aic'), p.get('q_totale'), p.get('prezzo_netto'))
        if key not in seen:
            seen.add(key)
            unique_products.append(p)

    # ========================================
    # GENERA RIGHE ORDINE
    # ========================================
    righe = []
    anomalie = []
    n_riga = 0

    for product in unique_products:
        aic = product.get('aic')
        is_espositore = _is_espositore(product['descrizione'])

        # Quantità sconto merce
        q_merce_sconto = product.get('q_merce_sconto', 0)

        # Verifica date quantities
        date_quantities = product.get('date_quantities', [])
        has_date_quantities = any(qty > 0 for qty in date_quantities)

        # FALLBACK: nessuna quantità nelle colonne date → riga singola
        if not has_date_quantities and product.get('q_totale', 0) > 0:
            n_riga += 1
            qty = product['q_totale']

            riga = {
                'n_riga': n_riga,
                'codice_aic': aic or '',
                'codice_originale': product.get('aic_raw', ''),
                'descrizione': product['descrizione'],
                'q_venduta': qty,
                'q_sconto_merce': q_merce_sconto,
                'merce_sconto_extra': 0,
                'q_omaggio': 0,
                'prezzo_netto': product['prezzo_netto'],
                'prezzo_pubblico': product['prezzo_pubblico'],
                'aliquota_iva': product['aliquota_iva'],
                'valore_netto': product['valore_netto'],
                'data_consegna': data.get('data_consegna'),
                'is_espositore': is_espositore,
                'tipo_riga': 'PRODOTTO_STANDARD',
            }
            righe.append(riga)

            # Anomalia AIC non conforme
            if aic and len(aic) != 9:
                anomalie.append({
                    'tipo': 'AIC', 'codice': 'AIC-A01', 'livello': 'ERRORE',
                    'messaggio': f"AIC non conforme: {product.get('aic_raw', '')} ({len(aic)} cifre)",
                    'n_riga': n_riga, 'codice_aic': product.get('aic_raw', ''),
                    'descrizione': product['descrizione'],
                })
            continue

        # Righe separate per ogni data consegna con quantità > 0
        for date_idx, qty in enumerate(date_quantities):
            if qty <= 0:
                continue

            n_riga += 1

            if date_idx < len(date_columns):
                data_consegna = date_columns[date_idx][1]
            else:
                data_consegna = data.get('data_consegna')

            riga = {
                'n_riga': n_riga,
                'codice_aic': aic or '',
                'codice_originale': product.get('aic_raw', ''),
                'descrizione': product['descrizione'],
                'q_venduta': qty,
                'q_sconto_merce': q_merce_sconto,
                'merce_sconto_extra': 0,
                'q_omaggio': 0,
                'prezzo_netto': product['prezzo_netto'],
                'prezzo_pubblico': product['prezzo_pubblico'],
                'aliquota_iva': product['aliquota_iva'],
                'valore_netto': product['prezzo_netto'] * qty,
                'data_consegna': data_consegna,
                'is_espositore': is_espositore,
                'tipo_riga': 'PRODOTTO_STANDARD',
            }
            righe.append(riga)

            if aic and len(aic) != 9:
                anomalie.append({
                    'tipo': 'AIC', 'codice': 'AIC-A01', 'livello': 'ERRORE',
                    'messaggio': f"AIC non conforme: {product.get('aic_raw', '')} ({len(aic)} cifre)",
                    'n_riga': n_riga, 'codice_aic': product.get('aic_raw', ''),
                    'descrizione': product['descrizione'],
                })

    data['righe'] = righe
    data['anomalie'] = anomalie

    data['_stats'] = {
        'extraction_method': 'table',
        'date_columns': len(date_columns),
        'date_values': [d[0] for d in date_columns],
        'righe_totali': len(righe),
        'prodotti_estratti': len(unique_products),
        'prodotti_page1': len(page1_products),
        'prodotti_page2': page2_product_count,
        'anomalie_aic': len([a for a in anomalie if a['codice'] == 'AIC-A01']),
        'espositori': len([r for r in righe if r.get('is_espositore')]),
    }

    return [data]
