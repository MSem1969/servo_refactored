"""
EXTRACTOR_TO - Estrattore COOPER v11.2
======================================
Cooper Consumer Health IT SRL

Struttura PDF:
- Header: Dati Ordine (Codice Ordine, Data Ordine, Agente)
- Dati Fatturazione: Info grossista/fatturazione
- Dati Spedizione: Farmacia destinataria (MIN_ID, P.IVA, Ragione Sociale)
- Tabella Prodotti: Codice, Codice Aic, Prodotto, Formato, Fascia, IVA, etc.
- Sezione Resi: Prodotti omaggio (quantità va in q_omaggio)

Particolarità:
- AIC a 9 cifre standard
- Sezione "Resi" contiene prodotti omaggio
- Sconto merce (pz) = pezzi sconto merce aggiuntivi
"""

import re
from typing import Dict, List, Tuple

# Import pdfplumber per estrazione tabelle
try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False


def _fix_concatenated_text(text: str) -> str:
    """
    Aggiunge spazi in testo concatenato da PDF.

    Gestisce casi come:
    - "FARMACIADALESSANDROdottssa" → "FARMACIA D'ALESSANDRO DOTT.SSA"
    - "SANVITOALTAGLIAMENTO" → "SAN VITO AL TAGLIAMENTO"
    - "VIAGARIBALDIn.15" → "VIA GARIBALDI N. 15"
    """
    if not text:
        return text

    result = text.upper()

    # Fix apostrofi comuni nei nomi italiani
    apostrophe_fixes = [
        (r"DALESSANDRO", "D'ALESSANDRO"),
        (r"DANGELO", "D'ANGELO"),
        (r"DAMICO", "D'AMICO"),
        (r"DANDREA", "D'ANDREA"),
        (r"DANTONIO", "D'ANTONIO"),
        (r"LAQUILA", "L'AQUILA"),
    ]
    for pattern, replacement in apostrophe_fixes:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

    # Keywords da separare con spazio prima (ordine importante: più lunghe prima)
    keywords_before = [
        'PARAFARMACIA', 'FARMACIA', 'DOTT\\.SSA', 'DOTTSSA', 'DOTT\\.', 'DOTT',
        'DELLA', 'DELLO', 'DEGLI', 'DELLE', 'DALLA', 'DALLO',
        'SRLS', 'S\\.R\\.L\\.S\\.', 'SRL', 'S\\.R\\.L\\.',
        'S\\.N\\.C\\.', 'SNC', 'S\\.A\\.S\\.', 'SAS', 'S\\.P\\.A\\.', 'SPA',
        'SANTA', 'SANTO', 'SANT', 'SAN',
        'VIALE', 'VICOLO', 'PIAZZA', 'LARGO', 'CORSO', 'VIA',
        'CONTRADA', 'LOCALITA', 'FRAZIONE',
    ]

    # Aggiungi spazio prima delle keywords (se precedute da lettera)
    for kw in keywords_before:
        pattern = rf'([A-Za-z])({kw})(?=[A-Z\s]|$)'
        result = re.sub(pattern, r'\1 \2', result)

    # Keywords da separare con spazio dopo
    keywords_after = ['DEL', 'DI', 'AL', 'DAL', 'N\\.', 'NR\\.', 'NUM\\.']
    for kw in keywords_after:
        # Aggiungi spazio dopo se seguito da lettera o numero
        pattern = rf'({kw})([A-Z0-9])'
        result = re.sub(pattern, r'\1 \2', result)

    # Aggiungi spazio tra minuscola seguita da maiuscola (CamelCase)
    result = re.sub(r'([a-z])([A-Z])', r'\1 \2', result)

    # Aggiungi spazio tra lettera e numero (es. "VIA15" → "VIA 15")
    result = re.sub(r'([A-Za-z])(\d)', r'\1 \2', result)

    # Normalizza spazi multipli
    result = re.sub(r'\s+', ' ', result).strip()

    return result


def _fix_locality_name(text: str) -> str:
    """
    Corregge nomi di località concatenati.

    Es: "SANVITOALTAGLIAMENTO" → "SAN VITO AL TAGLIAMENTO"
    """
    if not text:
        return text

    # Prima applica fix generale
    result = _fix_concatenated_text(text)

    # Pattern specifici per località italiane
    locality_fixes = [
        (r'SANVITO', 'SAN VITO'),
        (r'SANTAGATA', "SANT'AGATA"),
        (r'SANTANGELO', "SANT'ANGELO"),
        (r'SANTAGOSTINO', "SANT'AGOSTINO"),
        (r'MONTEGROTTO', 'MONTEGROTTO'),
        (r'PORTOGRUARO', 'PORTOGRUARO'),
        (r'TAGLIAMENTO', 'TAGLIAMENTO'),
    ]

    for pattern, replacement in locality_fixes:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

    return result.strip()


def extract_cooper(text: str, lines: List[str], pdf_path: str = None) -> List[Dict]:
    """
    Estrattore COOPER v11.2.

    Usa pdfplumber per estrazione accurata con spacing corretto.
    """
    data = {'vendor': 'COOPER', 'righe': []}

    # v11.2: Estrai testo direttamente dal PDF con x_tolerance=1 per spacing corretto
    # NOTA: Per COOPER, x_tolerance=1 preserva gli spazi, valori più alti li rimuovono!
    if pdf_path and PDFPLUMBER_AVAILABLE:
        try:
            with pdfplumber.open(pdf_path) as pdf:
                text_parts = []
                for page in pdf.pages:
                    page_text = page.extract_text(x_tolerance=1, y_tolerance=1) or ""
                    text_parts.append(page_text)
                text = "\n".join(text_parts)
        except Exception as e:
            print(f"   ⚠️ Errore lettura PDF COOPER: {e}")

    # === HEADER: Codice Ordine, Data Ordine ===
    # v11.2: Estrai solo parte dopo "PAD-" (es: "BRETAM-PAD-000296/01" → "000296/01")
    m = re.search(r'Codice\s*Ordine:\s*([A-Z0-9\-/]+)', text, re.I)
    if m:
        raw_ordine = m.group(1).strip()
        # Estrai parte dopo PAD-
        if 'PAD-' in raw_ordine.upper():
            idx = raw_ordine.upper().find('PAD-')
            data['numero_ordine'] = raw_ordine[idx + 4:]  # Tutto dopo "PAD-"
        else:
            data['numero_ordine'] = raw_ordine

    m = re.search(r'Data\s*Ordine:\s*(\d{2}/\d{2}/\d{4})', text, re.I)
    if m:
        data['data_ordine'] = _parse_date(m.group(1))

    m = re.search(r'Data\s*di\s*consegna\s*prevista:\s*(\d{2}/\d{2}/\d{4})', text, re.I)
    if m:
        data['data_consegna'] = _parse_date(m.group(1))

    m = re.search(r'Agente:\s*([A-Z]+?)(?:\s*Telefono:|\s*Tel)', text, re.I)
    if m:
        data['agente'] = m.group(1).strip()[:50]

    # === DATI SPEDIZIONE (Destinatario farmacia) ===
    _extract_spedizione_fallback(text, data)

    # === TABELLA PRODOTTI ===
    if pdf_path and PDFPLUMBER_AVAILABLE:
        try:
            righe = _extract_products_from_pdf(pdf_path)
            data['righe'] = righe
        except Exception as e:
            print(f"   ⚠️ Errore estrazione COOPER con PDF: {e}")
            data['righe'] = _extract_products_from_text(lines)
    else:
        data['righe'] = _extract_products_from_text(lines)

    return [data] if data.get('righe') or data.get('numero_ordine') else []


def _extract_spedizione_fallback(text: str, data: Dict):
    """
    Estrazione campi spedizione con pattern flessibili.

    Gestisce sia testo con spazi normali che testo senza spazi
    (es. "DatiSpedizione" invece di "Dati Spedizione")
    """
    # Trova la sezione Dati Spedizione (con o senza spazi)
    spedizione_start = -1
    for pattern in ['DatiSpedizione', 'Dati Spedizione', 'DATI SPEDIZIONE']:
        idx = text.find(pattern)
        if idx != -1:
            spedizione_start = idx
            break

    if spedizione_start == -1:
        return

    # Prendi solo la parte dopo "Dati Spedizione"
    spedizione_text = text[spedizione_start:spedizione_start + 1500]

    # Pattern flessibili (con o senza spazi)
    m = re.search(r'Codice\s*Ministeriale:\s*(\d+)', spedizione_text, re.I)
    if m:
        data['min_id'] = m.group(1).strip()

    # Ragione Sociale - v11.2: usa testo originale (spacing corretto da x_tolerance)
    # Pattern più ampio per catturare con o senza spazi
    m = re.search(r'Ragione\s*Sociale:\s*(.+?)(?:Partita|P\.?\s*IVA|\n|$)', spedizione_text, re.I)
    if m:
        raw_rs = m.group(1).strip()
        # Solo se non ci sono spazi, applica fix
        if ' ' not in raw_rs and len(raw_rs) > 15:
            raw_rs = _fix_concatenated_text(raw_rs)
        data['ragione_sociale'] = raw_rs[:50]

    m = re.search(r'Partita\s*IVA:\s*(\d{11})', spedizione_text, re.I)
    if m:
        data['partita_iva'] = m.group(1).strip()

    # Indirizzo - v11.2: usa testo originale
    m = re.search(r'Indirizzo:\s*(.+?)(?:Località|CAP|\n|$)', spedizione_text, re.I)
    if m:
        raw_ind = m.group(1).strip()
        # Solo se non ci sono spazi, applica fix
        if ' ' not in raw_ind and len(raw_ind) > 10:
            raw_ind = _fix_concatenated_text(raw_ind)
        data['indirizzo'] = raw_ind[:50]

    m = re.search(r'CAP:\s*(\d{5})', spedizione_text, re.I)
    if m:
        data['cap'] = m.group(1).strip()

    # Località con provincia tra parentesi
    # v11.2: Pattern più flessibile, accetta spazi
    m = re.search(r'Località:\s*([A-Za-z\s]+?)\s*\(([A-Z]{2})\)', spedizione_text, re.I)
    if m:
        raw_citta = m.group(1).strip()
        # Solo se non ci sono spazi, applica fix
        if ' ' not in raw_citta and len(raw_citta) > 8:
            raw_citta = _fix_locality_name(raw_citta)
        data['citta'] = raw_citta[:50]
        data['provincia'] = m.group(2).strip().upper()


def _extract_products_from_pdf(pdf_path: str) -> List[Dict]:
    """Estrae prodotti usando pdfplumber per parsing tabelle accurato."""
    righe = []
    n_riga = 0
    in_resi_section = False

    # v11.2: Table settings con spacing corretto
    # NOTA: Per COOPER, x_tolerance=1 preserva gli spazi originali del PDF
    table_settings = {
        "text_x_tolerance": 1,
        "text_y_tolerance": 1,
    }

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables(table_settings=table_settings)

            for table in tables:
                if not table:
                    continue

                for row in table:
                    if not row or len(row) < 5:
                        continue

                    # Controllo sezione RESI
                    row_text = ' '.join([str(c) for c in row if c]).upper()
                    if 'RESI' in row_text and len(row_text) < 20:
                        in_resi_section = True
                        continue

                    # Skip header rows
                    if any(h in row_text for h in ['CODICE AIC', 'PRODOTTO', 'FORMATO', 'Q.TÀ VENDITA']):
                        continue

                    # Skip totale row
                    if 'TOTALE' in row_text:
                        continue

                    # Parse product row
                    riga = _parse_product_row(row, in_resi_section)
                    if riga:
                        n_riga += 1
                        riga['n_riga'] = n_riga
                        righe.append(riga)

    return righe


def _parse_product_row(row: List, is_resi: bool = False) -> Dict:
    """
    Parse una riga prodotto dalla tabella.

    Colonne attese (righe normali):
    0: Codice (interno)
    1: Codice Aic
    2: Prodotto
    3: Formato
    4: Fascia
    5: IVA
    6: Imballo (pz)
    7: Q.tà vendita
    8: Sconto merce (pz)
    9: Sconto (%)
    10: Prezzo Totale
    11: Prezzo Unitario

    Colonne RESI (formato ridotto):
    0: Codice (interno)
    1: Codice Aic
    2: Prodotto
    3: Formato (vuoto)
    4: Fascia
    5-6: vuoti
    7: Quantità (questa è la quantità omaggio!)
    """
    try:
        # Pulisci celle
        cells = [str(c).strip() if c else '' for c in row]

        # Cerca colonna con AIC (9 cifre)
        aic_idx = -1
        for i, cell in enumerate(cells):
            if re.match(r'^\d{9}$', cell):
                aic_idx = i
                break

        if aic_idx == -1:
            # Prova con AIC più corto (padding necessario)
            for i, cell in enumerate(cells):
                if re.match(r'^\d{6,9}$', cell):
                    aic_idx = i
                    break

        if aic_idx == -1:
            return None

        codice_aic = cells[aic_idx].zfill(9)
        codice_interno = cells[aic_idx - 1] if aic_idx > 0 else ''

        # Descrizione (colonna dopo AIC)
        descrizione = cells[aic_idx + 1] if aic_idx + 1 < len(cells) else ''
        descrizione = descrizione.replace('\n', ' ')[:60]

        # === GESTIONE SPECIALE RESI ===
        # Le righe RESI hanno formato ridotto: solo quantità in posizione ~7
        if is_resi:
            # Cerca quantità DOPO la posizione AIC (esclude codici prodotto)
            # La quantità è tipicamente 1-3 cifre, non 6-9 come i codici AIC
            q_omaggio = 0
            for i in range(aic_idx + 2, len(cells)):  # Cerca dopo descrizione
                cell = cells[i]
                if cell and re.match(r'^\d{1,4}$', cell):  # Max 4 cifre per quantità
                    val = int(cell)
                    if 0 < val <= 9999:  # Range ragionevole per quantità
                        q_omaggio = val
                        break

            return {
                'codice_aic': codice_aic,
                'codice_originale': cells[aic_idx],
                'codice_interno': codice_interno,
                'descrizione': descrizione,
                'q_venduta': 0,
                'q_sconto_merce': 0,
                'q_omaggio': q_omaggio,
                'sconto_1': 0.0,
                'prezzo_netto': 0.0,
                'prezzo_totale': 0.0,
                'aliquota_iva': 10.0,
                'is_espositore': False,
                'is_child': False,
            }

        # === RIGHE NORMALI ===
        q_vendita = 0
        q_sconto_merce = 0
        q_omaggio = 0  # Righe normali: sempre 0 (RESI gestito sopra con early return)
        sconto_pct = 0.0
        prezzo_totale = 0.0
        prezzo_unitario = 0.0
        aliquota_iva = 10.0

        # Analizza celle dopo la descrizione
        numeric_cells = []
        for i in range(aic_idx + 2, len(cells)):
            cell = cells[i]
            # Pulisci e converti
            cell_clean = cell.replace(',', '.').replace('€', '').strip()
            try:
                val = float(cell_clean)
                numeric_cells.append((i, val, cell))
            except:
                pass

        # Mapping basato sulla posizione tipica COOPER
        # IVA, Imballo, Q.tà vendita, Sconto merce, Sconto %, Prezzo Totale, Prezzo Unitario
        if len(numeric_cells) >= 7:
            aliquota_iva = numeric_cells[0][1]
            # imballo = numeric_cells[1][1]  # Non ci serve
            q_vendita = int(numeric_cells[2][1])
            q_sconto_merce = int(numeric_cells[3][1])
            sconto_pct = numeric_cells[4][1]
            prezzo_totale = numeric_cells[5][1]
            prezzo_unitario = numeric_cells[6][1]
        elif len(numeric_cells) >= 3:
            # Formato con meno colonne
            q_vendita = int(numeric_cells[0][1]) if numeric_cells else 0

        return {
            'codice_aic': codice_aic,
            'codice_originale': cells[aic_idx],
            'codice_interno': codice_interno,
            'descrizione': descrizione,
            'q_venduta': q_vendita,
            'q_sconto_merce': q_sconto_merce,
            'q_omaggio': q_omaggio,
            'sconto_1': sconto_pct,
            'prezzo_netto': prezzo_unitario,
            'prezzo_totale': prezzo_totale,
            'aliquota_iva': aliquota_iva,
            'is_espositore': False,
            'is_child': False,
        }

    except Exception as e:
        print(f"   ⚠️ Errore parsing riga COOPER: {e}")
        return None


def _extract_products_from_text(lines: List[str]) -> List[Dict]:
    """Fallback: estrazione prodotti da testo."""
    righe = []
    n_riga = 0
    in_resi_section = False

    for line in lines:
        line_upper = line.upper().strip()

        # Controllo sezione RESI
        if line_upper == 'RESI' or line_upper.startswith('RESI '):
            in_resi_section = True
            continue

        # Skip header/footer
        if any(h in line_upper for h in ['CODICE AIC', 'CONDIZIONI GENERALI', 'PAGINA']):
            continue

        # Cerca pattern: codice_interno AIC descrizione ...numeri...
        m = re.match(
            r'^([A-Za-z0-9]+)\s+(\d{6,9})\s+(.+?)\s+'
            r'(\d+[,.]?\d*)\s+'  # IVA o primo numero
            r'(\d+)\s+'          # Imballo o qty
            r'(\d+)\s+'          # Q.tà vendita
            r'(\d+)\s+'          # Sconto merce
            r'(\d+[,.]?\d*)\s+'  # Sconto %
            r'(\d+[,.]?\d*)\s+'  # Prezzo totale
            r'(\d+[,.]?\d*)',    # Prezzo unitario
            line
        )

        if m:
            n_riga += 1
            codice_aic = m.group(2).zfill(9)
            q_vendita = int(m.group(6))

            if in_resi_section:
                q_omaggio = q_vendita
                q_vendita = 0
            else:
                q_omaggio = 0

            righe.append({
                'n_riga': n_riga,
                'codice_aic': codice_aic,
                'codice_originale': m.group(2),
                'codice_interno': m.group(1),
                'descrizione': m.group(3).strip()[:60],
                'q_venduta': q_vendita,
                'q_sconto_merce': int(m.group(7)),
                'q_omaggio': q_omaggio,
                'sconto_1': float(m.group(8).replace(',', '.')),
                'prezzo_netto': float(m.group(10).replace(',', '.')),
                'prezzo_totale': float(m.group(9).replace(',', '.')),
                'aliquota_iva': float(m.group(4).replace(',', '.')),
                'is_espositore': False,
                'is_child': False,
            })

    return righe


def _parse_date(date_str: str) -> str:
    """Converte data da DD/MM/YYYY a YYYY-MM-DD."""
    if not date_str:
        return None
    try:
        parts = date_str.split('/')
        if len(parts) == 3:
            return f"{parts[2]}-{parts[1]}-{parts[0]}"
    except:
        pass
    return None


# === DETECTION ===
def detect_cooper(text: str, filename: str = '') -> float:
    """
    Rileva se il PDF è un ordine COOPER.

    Returns:
        Score 0.0-1.0
    """
    score = 0.0
    text_upper = text.upper()

    # Pattern primari (alta confidenza)
    if 'COOPER CONSUMER HEALTH' in text_upper:
        score += 0.40

    if 'DE SALUTE SRL' in text_upper or 'SORESINA' in text_upper:
        score += 0.15

    # Pattern struttura documento
    if 'DATI ORDINE' in text_upper and 'DATI SPEDIZIONE' in text_upper:
        score += 0.15

    if 'CODICE ORDINE:' in text_upper:
        score += 0.10

    # Prodotti tipici COOPER
    cooper_products = ['BETADINE', 'SAUGELLA', 'ARMOLIPID', 'AUDISPRAY', 'AFTIR', 'SARGENOR', 'FOILLE']
    product_matches = sum(1 for p in cooper_products if p in text_upper)
    if product_matches >= 3:
        score += 0.15
    elif product_matches >= 1:
        score += 0.05

    # Filename hint
    if 'COOPER' in filename.upper():
        score += 0.05

    return min(score, 1.0)
