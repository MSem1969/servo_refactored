"""
EXTRACTOR_TO - Estrattore OPELLA v11.2
======================================
Convertito da SERV.O_v6_0_DB_def.ipynb - Cella 10

v11.2: Gestione AIC con zeri iniziali troncati
- OPELLA visualizza solo i digit significativi (es. 12345 invece di 000012345)
- Padding automatico a 9 cifre per codici < 9 caratteri
"""

import re
from typing import Dict, List, Tuple

from ....utils import parse_date


def _normalize_aic_opella(codice: str, descrizione: str = '') -> Tuple[str, str, bool, bool]:
    """
    Normalizza AIC specifico per OPELLA con padding a 9 cifre.

    OPELLA tronca gli zeri iniziali nei codici AIC.
    Esempio: 12345 -> 000012345

    Args:
        codice: Codice AIC originale (può essere < 9 cifre)
        descrizione: Descrizione prodotto (per rilevare espositore)

    Returns:
        Tuple (aic_padded, aic_originale, is_espositore, is_child)
    """
    codice = str(codice).strip() if codice else ''
    aic_orig = codice
    is_espositore = False
    is_child = False

    # Rileva espositore da codice o descrizione
    esp_pattern = r'(ESP|EXP|BANCO|EXPO|DISPLAY)'
    if re.search(esp_pattern, codice.upper()) or \
       re.search(esp_pattern, descrizione.upper()):
        is_espositore = True

    # Estrae solo cifre
    aic_digits = re.sub(r'[^\d]', '', codice)

    # v11.2: Padding a 9 cifre con zeri iniziali (specifico OPELLA)
    if aic_digits and len(aic_digits) < 9:
        aic_padded = aic_digits.zfill(9)
    else:
        aic_padded = aic_digits

    return aic_padded, aic_orig, is_espositore, is_child

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
                    # Estrai le righe successive solo dalla colonna destra fino a "IT"
                    dest_data = []
                    for y_key in sorted(rows_by_y.keys()):
                        if y_key > dest_y:
                            right_words = [w for w in rows_by_y[y_key] if w['x0'] >= X_THRESHOLD]
                            if right_words:
                                right_words = sorted(right_words, key=lambda w: w['x0'])
                                line_text = ' '.join([w['text'] for w in right_words]).strip()
                                if line_text:
                                    dest_data.append(line_text)
                                    # Termina quando troviamo "IT" da solo
                                    if line_text.strip() == 'IT':
                                        break

                    # v11.3: Analisi semantica del blocco destinatario
                    # Pattern per identificare tipo di riga
                    INDIRIZZO_PATTERN = r'^(VIA|V\.|CORSO|C\.SO|PIAZZA|P\.ZZA|PIAZZALE|P\.LE|VIALE|V\.LE|LARGO|VICOLO|CONTRADA|LOC\.|LOCALITA|FRAZIONE|FRAZ\.|STRADA|S\.DA|VIA\s|C/O)\s'
                    CAP_CITTA_PATTERN = r'^(\d{5})\s+(.+)'
                    PROVINCIA_PATTERN = r'^([A-Z]{2})$'

                    ragione_sociale_parts = []
                    indirizzo = None
                    cap = None
                    citta = None
                    provincia = None

                    for i, line in enumerate(dest_data):
                        line_upper = line.upper().strip()

                        # Salta "DESTINATARIO" o simili
                        if 'DESTINATARIO' in line_upper:
                            continue

                        # Fine blocco con "IT"
                        if line_upper == 'IT':
                            # Provincia potrebbe essere nella riga precedente se non già trovata
                            break

                        # Pattern provincia (2 lettere da sole, es. "NA", "RM")
                        if re.match(PROVINCIA_PATTERN, line_upper) and len(line_upper) == 2:
                            provincia = line_upper
                            continue

                        # Pattern CAP + Città (es. "80100 NAPOLI")
                        m_cap = re.match(CAP_CITTA_PATTERN, line)
                        if m_cap:
                            cap = m_cap.group(1)
                            resto = m_cap.group(2).strip()
                            # Controlla se c'è provincia alla fine (es. "NAPOLI NA")
                            m_prov = re.match(r'(.+?)\s+([A-Z]{2})$', resto)
                            if m_prov:
                                citta = m_prov.group(1).strip()
                                provincia = m_prov.group(2)
                            else:
                                citta = resto
                            continue

                        # Pattern indirizzo (Via, Corso, etc.)
                        if re.match(INDIRIZZO_PATTERN, line_upper):
                            indirizzo = line
                            continue

                        # Altrimenti è parte della ragione sociale
                        # (solo se non abbiamo ancora trovato indirizzo/cap)
                        if not indirizzo and not cap:
                            ragione_sociale_parts.append(line)

                    # Componi ragione sociale
                    if ragione_sociale_parts:
                        data['ragione_sociale'] = ' '.join(ragione_sociale_parts).strip()[:100]
                    if indirizzo:
                        data['indirizzo'] = indirizzo.strip()[:50]
                    if cap:
                        data['cap'] = cap
                    if citta:
                        data['citta'] = citta.strip()[:50]
                    if provincia:
                        data['provincia'] = provincia

                # === TABELLA PRODOTTI ===
                tables = page.extract_tables()
                if tables:
                    n = 0
                    for row in tables[0]:
                        if not row or not row[0]:
                            continue
                        row_text = row[0] if isinstance(row, list) else str(row)
                        # v11.2: Regex aggiornata per accettare AIC da 1 a 9 cifre (OPELLA tronca zeri)
                        m = re.match(
                            r'^(\d+)\s+(\d{1,9})\s+(.+?)\s+(\d+)\s+UNT\s+([\d,]+)\s+([\d,\.]+)',
                            row_text
                        )
                        if m:
                            n += 1
                            codice_raw = m.group(2)
                            desc = m.group(3).strip()[:40]
                            qty = int(m.group(4))
                            pu = float(m.group(5).replace(',', '.'))
                            totale = float(m.group(6).replace('.', '').replace(',', '.'))

                            # v11.2: Usa normalizzazione OPELLA con padding a 9 cifre
                            aic_norm, aic_orig, is_esp, is_child = _normalize_aic_opella(codice_raw, desc)

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

    # Estrazione destinatario da testo con analisi semantica
    INDIRIZZO_PATTERN = r'^(VIA|V\.|CORSO|C\.SO|PIAZZA|P\.ZZA|PIAZZALE|P\.LE|VIALE|V\.LE|LARGO|VICOLO|CONTRADA|LOC\.|LOCALITA|FRAZIONE|FRAZ\.|STRADA|S\.DA|VIA\s|C/O)\s'
    CAP_CITTA_PATTERN = r'^(\d{5})\s+(.+)'
    PROVINCIA_PATTERN = r'^([A-Z]{2})$'

    for i, line in enumerate(lines):
        if 'DESTINATARIO' in line.upper():
            ragione_sociale_parts = []
            indirizzo = None
            cap = None
            citta = None
            provincia = None

            # Analizza righe successive fino a "IT" o max 10 righe
            for j in range(i+1, min(i+12, len(lines))):
                current_line = lines[j].strip()
                if not current_line:
                    continue

                # Estrai parte destra se c'è separazione con spazi multipli
                parts = re.split(r'\s{3,}', current_line)
                if len(parts) >= 2:
                    current_line = parts[-1].strip()

                line_upper = current_line.upper()

                # Fine blocco
                if line_upper == 'IT':
                    break

                # Provincia
                if re.match(PROVINCIA_PATTERN, line_upper) and len(line_upper) == 2:
                    provincia = line_upper
                    continue

                # CAP + Città
                m_cap = re.match(CAP_CITTA_PATTERN, current_line)
                if m_cap:
                    cap = m_cap.group(1)
                    resto = m_cap.group(2).strip()
                    m_prov = re.match(r'(.+?)\s+([A-Z]{2})$', resto)
                    if m_prov:
                        citta = m_prov.group(1).strip()
                        provincia = m_prov.group(2)
                    else:
                        citta = resto
                    continue

                # Indirizzo
                if re.match(INDIRIZZO_PATTERN, line_upper):
                    indirizzo = current_line
                    continue

                # Ragione sociale (se non abbiamo ancora trovato indirizzo/cap)
                if not indirizzo and not cap:
                    if 'FARMACIA' in line_upper or 'F.CIA' in line_upper or \
                       'SNC' in line_upper or 'SRL' in line_upper or 'SAS' in line_upper or \
                       'DR.' in line_upper or 'DOTT.' in line_upper or current_line:
                        ragione_sociale_parts.append(current_line)

            if ragione_sociale_parts:
                data['ragione_sociale'] = ' '.join(ragione_sociale_parts).strip()[:100]
            if indirizzo:
                data['indirizzo'] = indirizzo[:50]
            if cap:
                data['cap'] = cap
            if citta:
                data['citta'] = citta[:50]
            if provincia:
                data['provincia'] = provincia
            break

    # Estrazione righe prodotto
    n = 0
    for line in lines:
        line_stripped = line.strip()
        # v11.2: Regex aggiornata per accettare AIC da 1 a 9 cifre (OPELLA tronca zeri)
        m = re.match(
            r'^(\d+)\s+(\d{1,9})\s+(.+?)\s+(\d+)\s+UNT\s+([\d,]+)\s+([\d,\.]+)',
            line_stripped
        )
        if m:
            n += 1
            codice_raw = m.group(2)
            desc = m.group(3).strip()[:40]
            qty = int(m.group(4))
            pu = float(m.group(5).replace(',', '.'))
            totale = float(m.group(6).replace('.', '').replace(',', '.'))

            # v11.2: Usa normalizzazione OPELLA con padding a 9 cifre
            aic_norm, aic_orig, is_esp, is_child = _normalize_aic_opella(codice_raw, desc)

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
