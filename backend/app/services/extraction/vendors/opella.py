"""
EXTRACTOR_TO - Estrattore OPELLA
=================================
Convertito da SERV.O_v6_0_DB_def.ipynb - Cella 10
"""

import re
from typing import Dict, List

from ....utils import parse_date, normalize_aic

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


def extract_opella(text: str, lines: List[str], pdf_path: str = None) -> List[Dict]:
    """
    Estrattore OPELLA v2.0.
    
    Usa coordinate X per separare GROSSISTA/DESTINATARIO.
    """
    data = {'vendor': 'OPELLA', 'righe': []}

    # === HEADER: Numero ordine, date, termini pagamento ===
    m = re.search(r'Numero\s+ordine\s+cliente:?\s*(\d+)', text, re.I)
    if m:
        data['numero_ordine'] = m.group(1)

    m = re.search(r'Data:?\s*(\d{2}\.\d{2}\.\d{4})', text)
    if m:
        data['data_ordine'] = parse_date(m.group(1))

    m = re.search(r'Termini\s+di\s+pagamento:?\s*(\d+)\s*gg', text, re.I)
    if m:
        data['gg_dilazione'] = int(m.group(1))

    m = re.search(r'Data\s+di\s+consegna\s+richiesta:?\s*(\d{2}\.\d{2}\.\d{4})', text, re.I)
    if m:
        data['data_consegna'] = parse_date(m.group(1))

    # === DESTINATARIO: Estrazione con coordinate X se pdf_path disponibile ===
    if pdf_path and PDFPLUMBER_AVAILABLE:
        try:
            with pdfplumber.open(pdf_path) as pdf:
                page = pdf.pages[0]
                # v10.6: x_tolerance per spacing corretto
                words = page.extract_words(x_tolerance=5)

                # Raggruppa parole per Y
                rows_by_y = {}
                for w in words:
                    y_key = round(w['top'], 0)
                    if y_key not in rows_by_y:
                        rows_by_y[y_key] = []
                    rows_by_y[y_key].append(w)

                # Soglia X per colonna DESTINATARIO (destra)
                X_THRESHOLD = 300

                # Trova la riga con DESTINATARIO
                dest_y = None
                for y_key in sorted(rows_by_y.keys()):
                    row_text = ' '.join([w['text'] for w in rows_by_y[y_key]])
                    if 'DESTINATARIO' in row_text:
                        dest_y = y_key
                        break

                if dest_y:
                    # Estrai le righe successive solo dalla colonna destra
                    dest_data = []
                    for y_key in sorted(rows_by_y.keys()):
                        if y_key > dest_y and len(dest_data) < 6:
                            right_words = [w for w in rows_by_y[y_key] if w['x0'] >= X_THRESHOLD]
                            if right_words:
                                right_words = sorted(right_words, key=lambda w: w['x0'])
                                line_text = ' '.join([w['text'] for w in right_words])
                                dest_data.append(line_text)

                    # Parse dest_data
                    if len(dest_data) >= 2:
                        data['ragione_sociale'] = dest_data[1].strip()[:50]
                    if len(dest_data) >= 3:
                        data['indirizzo'] = dest_data[2].strip()[:50]
                    if len(dest_data) >= 5:
                        # CAP CITTA PROV
                        m = re.match(r'(\d{5})\s+(.+?)\s+([A-Z]{2})$', dest_data[4].strip())
                        if m:
                            data['cap'] = m.group(1)
                            data['citta'] = m.group(2).strip()[:50]
                            data['provincia'] = m.group(3)

                # === TABELLA PRODOTTI ===
                tables = page.extract_tables()
                if tables:
                    n = 0
                    for row in tables[0]:
                        if not row or not row[0]:
                            continue
                        row_text = row[0] if isinstance(row, list) else str(row)
                        m = re.match(
                            r'^(\d+)\s+(\d{6,9})\s+(.+?)\s+(\d+)\s+UNT\s+([\d,]+)\s+([\d,\.]+)',
                            row_text
                        )
                        if m:
                            n += 1
                            codice_raw = m.group(2)
                            desc = m.group(3).strip()[:40]
                            qty = int(m.group(4))
                            pu = float(m.group(5).replace(',', '.'))
                            totale = float(m.group(6).replace('.', '').replace(',', '.'))

                            aic_norm, aic_orig, is_esp, is_child = normalize_aic(codice_raw, desc)

                            data['righe'].append({
                                'n_riga': n,
                                'codice_aic': aic_norm,
                                'codice_originale': aic_orig,
                                'descrizione': desc,
                                'q_venduta': qty,
                                'prezzo_pubblico': pu,
                                'prezzo_netto': round(totale / qty, 2) if qty > 0 else 0,
                                'is_espositore': is_esp,
                                'is_child': is_child,
                            })

        except Exception as e:
            print(f"   ⚠️ Errore estrazione OPELLA con PDF: {e}")
            return _extract_opella_text_fallback(text, lines)

    else:
        return _extract_opella_text_fallback(text, lines)

    return [data] if data.get('righe') or data.get('numero_ordine') else _extract_opella_text_fallback(text, lines)


def _extract_opella_text_fallback(text: str, lines: List[str]) -> List[Dict]:
    """Fallback OPELLA quando pdf_path non è disponibile."""
    data = {'vendor': 'OPELLA', 'righe': []}

    m = re.search(r'Numero\s+ordine\s+cliente:?\s*(\d+)', text, re.I)
    if m:
        data['numero_ordine'] = m.group(1)

    m = re.search(r'Data:?\s*(\d{2}\.\d{2}\.\d{4})', text)
    if m:
        data['data_ordine'] = parse_date(m.group(1))

    m = re.search(r'Termini\s+di\s+pagamento:?\s*(\d+)\s*gg', text, re.I)
    if m:
        data['gg_dilazione'] = int(m.group(1))

    m = re.search(r'Data\s+di\s+consegna\s+richiesta:?\s*(\d{2}\.\d{2}\.\d{4})', text, re.I)
    if m:
        data['data_consegna'] = parse_date(m.group(1))

    # Estrazione destinatario da testo (meno precisa)
    for i, line in enumerate(lines):
        if 'DESTINATARIO DELLA MERCE' in line:
            for j in range(i+1, min(i+6, len(lines))):
                if 'FARMACIA' in lines[j] or 'F.CIA' in lines[j]:
                    parts = re.split(r'\s{3,}', lines[j])
                    if len(parts) >= 2:
                        data['ragione_sociale'] = parts[-1].strip()[:50]
                    else:
                        data['ragione_sociale'] = lines[j].strip()[:50]
                    break
            for j in range(i+1, min(i+8, len(lines))):
                m = re.search(r'(\d{5})\s+([A-Z\']+)\s+([A-Z]{2})\s*$', lines[j])
                if m:
                    data['cap'] = m.group(1)
                    data['citta'] = m.group(2)
                    data['provincia'] = m.group(3)
                    break
            break

    # Estrazione righe prodotto
    n = 0
    for line in lines:
        line_stripped = line.strip()
        m = re.match(
            r'^(\d+)\s+(\d{6,9})\s+(.+?)\s+(\d+)\s+UNT\s+([\d,]+)\s+([\d,\.]+)',
            line_stripped
        )
        if m:
            n += 1
            codice_raw = m.group(2)
            desc = m.group(3).strip()[:40]
            qty = int(m.group(4))
            pu = float(m.group(5).replace(',', '.'))
            totale = float(m.group(6).replace('.', '').replace(',', '.'))

            aic_norm, aic_orig, is_esp, is_child = normalize_aic(codice_raw, desc)

            data['righe'].append({
                'n_riga': n,
                'codice_aic': aic_norm,
                'codice_originale': aic_orig,
                'descrizione': desc,
                'q_venduta': qty,
                'prezzo_pubblico': pu,
                'prezzo_netto': round(totale / qty, 2) if qty > 0 else 0,
                'is_espositore': is_esp,
                'is_child': is_child,
            })

    return [data]
