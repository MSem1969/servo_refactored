"""
EXTRACTOR_TO - Estrattore VIATRIS v11.5
=======================================
Estrattore per ordini VIATRIS (Transfer Order)

Struttura documento:
- Header: OR{numero_ordine}
- Sezione CLIENTE: agente, data, ragione sociale, indirizzo, P.IVA (ITxxxxxxxxxx)
- Sezione DESTINAZIONE MERCE: nome, MIN_ID (Fxxxxx), indirizzo
- Tabella prodotti: descrizione + AIC, prezzi, quantità, sconti, data consegna

v11.3: Implementazione iniziale
v11.5: Riscrittura parsing prodotti (right-to-left, €-count strategy)
     - Fix sconto estratto dalla descrizione (BUG 1)
     - Fix righe con PP/PP.Netto come trattino (BUG 2)
     - Fix SC.MER → q_sconto_merce (BUG 3)
     - Fix prezzo_scontare = PP.Netto (BUG 4)
"""

import re
from typing import Dict, List, Optional, Tuple

from ....utils import parse_date


def _normalize_aic_viatris(codice: str) -> Tuple[str, str, bool, bool]:
    """
    Normalizza AIC per VIATRIS.

    Args:
        codice: Codice AIC (9 cifre)

    Returns:
        Tuple (aic_normalizzato, aic_originale, is_espositore, is_child)
    """
    codice = str(codice).strip() if codice else ''
    aic_orig = codice

    # Estrae solo cifre
    aic_digits = re.sub(r'[^\d]', '', codice)

    # Padding a 9 cifre se necessario
    if aic_digits and len(aic_digits) < 9:
        aic_digits = aic_digits.zfill(9)

    return aic_digits, aic_orig, False, False


def _parse_price(price_str: str) -> float:
    """
    Converte stringa prezzo in float.
    Gestisce formato europeo: "71,94 €" -> 71.94
    """
    if not price_str:
        return 0.0

    # Rimuove simbolo euro e spazi
    price_str = price_str.replace('€', '').strip()

    # Converte virgola in punto
    price_str = price_str.replace('.', '').replace(',', '.')

    try:
        return float(price_str)
    except ValueError:
        return 0.0


def _parse_percentage(perc_str: str) -> float:
    """
    Converte stringa percentuale in float.
    "38,35%" -> 38.35
    """
    if not perc_str:
        return 0.0

    perc_str = perc_str.replace('%', '').strip()
    perc_str = perc_str.replace(',', '.')

    try:
        return float(perc_str)
    except ValueError:
        return 0.0


def _parse_product_line(product_line: str) -> Optional[Dict]:
    """
    Parsa una riga prodotto VIATRIS usando strategia right-to-left basata sul conteggio €.

    Formato riga (caso normale, 4 €):
        {DESCR} {PP €} {PP.Netto €} {Q.TA} {SC.MER} {SC.NET%|blank} {P.CESS.UNIT €} {P.CESS.TOT €} {DATA}

    Formato riga (caso trattino, 2 €):
        {DESCR} {-} {-} {Q.TA} {SC.MER} {SC.NET%|blank} {P.CESS.UNIT €} {P.CESS.TOT €} {DATA}

    Returns:
        Dict con campi estratti, o None se parsing fallisce
    """
    # 1. Estrai data consegna dalla fine
    data_match = re.search(r'(\d{2}/\d{2}/\d{4})\s*$', product_line)
    if not data_match:
        return None
    data_consegna = parse_date(data_match.group(1))
    line_no_date = product_line[:data_match.start()].strip()

    # 2. Trova tutte le posizioni dei prezzi con €
    euro_matches = list(re.finditer(r'([\d.,]+)\s*€', line_no_date))
    n_euro = len(euro_matches)

    if n_euro < 2:
        return None

    # 3. Estrai prezzi in base al conteggio €
    if n_euro >= 4:
        # Caso normale: PP, PP.Netto, P.CESS.UNIT, P.CESS.TOT
        pp = _parse_price(euro_matches[0].group(1))
        pp_netto = _parse_price(euro_matches[1].group(1))
        p_cess_unit = _parse_price(euro_matches[-2].group(1))
        p_cess_tot = _parse_price(euro_matches[-1].group(1))
        # Sezione media: tra PP.Netto € e P.CESS.UNIT €
        mid_start = euro_matches[1].end()
        mid_end = euro_matches[-2].start()
        # Descrizione: tutto prima del primo prezzo
        desc_end = euro_matches[0].start()
    elif n_euro == 3:
        # 3 €: PP presente, PP.Netto trattino, P.CESS.UNIT, P.CESS.TOT
        # oppure PP trattino, PP.Netto presente... gestisci come: primo=PP, ultimi due=P.CESS
        pp = _parse_price(euro_matches[0].group(1))
        pp_netto = 0.0
        p_cess_unit = _parse_price(euro_matches[-2].group(1))
        p_cess_tot = _parse_price(euro_matches[-1].group(1))
        mid_start = euro_matches[0].end()
        mid_end = euro_matches[-2].start()
        desc_end = euro_matches[0].start()
    else:
        # Caso trattino (2 €): solo P.CESS.UNIT e P.CESS.TOT
        pp = 0.0
        pp_netto = 0.0
        p_cess_unit = _parse_price(euro_matches[0].group(1))
        p_cess_tot = _parse_price(euro_matches[1].group(1))
        # Sezione media: tra i trattini e P.CESS.UNIT
        # Cerchiamo i trattini isolati (dash come placeholder prezzo)
        # La descrizione finisce prima del primo trattino isolato
        # Pattern: cerchiamo " - " o " -  - " prima del P.CESS area
        before_pcess = line_no_date[:euro_matches[0].start()].rstrip()
        # Cerchiamo l'ultimo pattern di trattini (separatori prezzo)
        dash_match = re.search(r'\s+(-\s+-|-)\s+', before_pcess)
        if dash_match:
            desc_end_pos = dash_match.start()
            mid_start = dash_match.end()
        else:
            # Fallback: cerchiamo la sezione numerica prima dei prezzi
            desc_end_pos = 0
            mid_start = 0
        mid_end = euro_matches[0].start()
        desc_end = desc_end_pos

    # 4. Estrai descrizione (pulita da trailing numerici/spazi)
    desc_raw = line_no_date[:desc_end].strip()
    # Rimuovi trailing noise (numeri sparsi alla fine della descrizione)
    desc_raw = re.sub(r'\s+[\d.,]+\s*$', '', desc_raw).strip()
    descrizione = desc_raw

    # 5. Estrai Q.TA, SC.MER e SC.NET% dalla sezione media
    mid_section = line_no_date[mid_start:mid_end].strip()

    q_venduta = 0
    q_sconto_merce = 0
    sconto_perc = 0.0

    # Cerchiamo lo sconto % SOLO nella sezione media (non nella descrizione!)
    sconto_in_mid = re.search(r'([\d,]+)\s*%', mid_section)
    if sconto_in_mid:
        sconto_perc = _parse_percentage(sconto_in_mid.group(1))
        # Rimuoviamo lo sconto dalla sezione per estrarre le quantità
        mid_for_qty = mid_section[:sconto_in_mid.start()].strip()
    else:
        mid_for_qty = mid_section.strip()

    # Estraiamo i numeri interi dalla sezione media (Q.TA e SC.MER)
    qty_nums = re.findall(r'\b(\d+)\b', mid_for_qty)
    if len(qty_nums) >= 2:
        q_venduta = int(qty_nums[0])
        q_sconto_merce = int(qty_nums[1])
    elif len(qty_nums) == 1:
        q_venduta = int(qty_nums[0])

    return {
        'descrizione': descrizione,
        'prezzo_pubblico': pp,
        'prezzo_pubblico_netto': pp_netto,
        'q_venduta': q_venduta,
        'q_sconto_merce': q_sconto_merce,
        'sconto_perc': sconto_perc,
        'prezzo_unitario': p_cess_unit,
        'prezzo_totale': p_cess_tot,
        'data_consegna': data_consegna,
    }


def extract_viatris(text: str, lines: List[str], pdf_path: str = None) -> List[Dict]:
    """
    Estrattore VIATRIS v11.5.

    Args:
        text: Testo completo del PDF
        lines: Linee del testo
        pdf_path: Percorso file PDF (opzionale)

    Returns:
        Lista con dizionario ordine estratto
    """
    data = {'vendor': 'VIATRIS', 'righe': []}

    # =========================================================================
    # 1. NUMERO ORDINE - Pattern OR{numeri}
    # =========================================================================
    m = re.search(r'\bOR(\d+)\b', text)
    if m:
        data['numero_ordine'] = m.group(1)

    # =========================================================================
    # 2. SEZIONE CLIENTE
    # =========================================================================

    # Data ordine - DATA{DD/MM/YYYY}
    m = re.search(r'DATA\s*(\d{2}/\d{2}/\d{4})', text)
    if m:
        data['data_ordine'] = parse_date(m.group(1))

    # Agente - AGENTE{nome} AREA
    m = re.search(r'AGENTE\s*([A-Z\s]+?)\s*AREA', text)
    if m:
        data['nome_agente'] = m.group(1).strip()

    # Ragione sociale cliente - DENOMINAZIONE SOCIALE{nome}
    m = re.search(r'DENOMINAZIONE\s+SOCIALE\s*([^\n]+?)(?=\s*INDIRIZZO|\n)', text)
    if m:
        # Questa è la ragione sociale del cliente, non della destinazione
        pass  # La prendiamo dalla sezione DESTINAZIONE MERCE

    # P.IVA - P.IVAIT{11cifre}
    m = re.search(r'P\.IVA\s*IT(\d{11})', text)
    if m:
        data['partita_iva'] = m.group(1)

    # =========================================================================
    # 3. SEZIONE DESTINAZIONE MERCE (dati rilevanti per l'ordine)
    # =========================================================================

    # MIN_ID - TRACC. F{numero} (con spazio opzionale tra TRACC. e F)
    m = re.search(r'TRACC\.\s*F(\d+)', text)
    if m:
        data['codice_ministeriale'] = m.group(1)

    # Ragione sociale destinazione - NOME{ragione_sociale} TRACC.
    m = re.search(r'DESTINAZIONE\s+MERCE\s*\n?\s*NOME\s*([^\n]+?)\s*TRACC\.', text, re.DOTALL)
    if m:
        data['ragione_sociale'] = m.group(1).strip()[:50]

    # Indirizzo destinazione - dopo NOME...TRACC. sulla riga INDIRIZZO
    # Pattern: INDIRIZZO{indirizzo} TEL.
    dest_section = re.search(
        r'DESTINAZIONE\s+MERCE.*?INDIRIZZO\s*([^\n]+?)\s*(?:TEL\.|FAX)',
        text, re.DOTALL | re.I
    )
    if dest_section:
        data['indirizzo'] = dest_section.group(1).strip()[:50]

    # CAP, Città, Provincia dalla sezione destinazione
    # Cerchiamo la seconda occorrenza di CAP (quella della destinazione)
    cap_matches = list(re.finditer(r'CAP\s*(\d{5})\s*CITT[AÀ]\s*([A-Z\s]+?)\s*PROV\.?\s*([A-Z]{2})', text, re.I))
    if len(cap_matches) >= 2:
        # Seconda occorrenza = destinazione
        dest_match = cap_matches[1]
        data['cap'] = dest_match.group(1)
        data['citta'] = dest_match.group(2).strip()[:50]
        data['provincia'] = dest_match.group(3).strip()
    elif len(cap_matches) == 1:
        # Una sola occorrenza, usiamo quella
        data['cap'] = cap_matches[0].group(1)
        data['citta'] = cap_matches[0].group(2).strip()[:50]
        data['provincia'] = cap_matches[0].group(3).strip()

    # =========================================================================
    # 4. TABELLA PRODOTTI
    # =========================================================================
    # La tabella ha prodotti su 2 righe:
    # Riga 1: Descrizione + prezzi + quantità + sconti + data
    # Riga 2: AIC: XXXXXXXXX
    #
    # Formato riga (caso normale, 4 €):
    #   {DESCR} {PP €} {PP.Netto €} {Q.TA} {SC.MER} {SC.NET%} {P.CESS.UNIT €} {P.CESS.TOT €} {DATA}
    # Formato riga (caso trattino, 2 €):
    #   {DESCR} {-} {-} {Q.TA} {SC.MER} {SC.NET%} {P.CESS.UNIT €} {P.CESS.TOT €} {DATA}

    aic_pattern = r'AIC:\s*(\d{7,9})'
    aic_matches = list(re.finditer(aic_pattern, text))

    n_riga = 0
    for aic_match in aic_matches:
        aic_code = aic_match.group(1)
        aic_pos = aic_match.start()

        # Trova la riga del prodotto che precede l'AIC
        text_before_aic = text[:aic_pos]
        lines_before = text_before_aic.split('\n')

        product_line = None
        for line in reversed(lines_before):
            line = line.strip()
            # La riga prodotto contiene almeno un prezzo (€) e una data
            if '€' in line and re.search(r'\d{2}/\d{2}/\d{4}', line):
                product_line = line
                break
            # Caso trattino: contiene trattini come prezzi + data
            if re.search(r'\s-\s', line) and '€' in line and re.search(r'\d{2}/\d{2}/\d{4}', line):
                product_line = line
                break

        if not product_line:
            continue

        # Parsing con _parse_product_line (strategia right-to-left, €-count)
        parsed = _parse_product_line(product_line)
        if not parsed:
            continue

        # Normalizza AIC
        aic_norm, aic_orig, is_esp, is_child = _normalize_aic_viatris(aic_code)

        n_riga += 1
        data['righe'].append({
            'n_riga': n_riga,
            'codice_aic': aic_norm,
            'codice_originale': aic_orig,
            'descrizione': parsed['descrizione'][:40],
            'q_venduta': parsed['q_venduta'],
            'q_omaggio': 0,  # VIATRIS non ha colonna omaggio separata
            'q_sconto_merce': parsed['q_sconto_merce'],  # SC.MER → q_sconto_merce
            'prezzo_pubblico': parsed['prezzo_pubblico'],
            'prezzo_netto': parsed['prezzo_unitario'],  # P.CESS UNITARIO
            'prezzo_scontare': parsed['prezzo_pubblico_netto'],  # PP.Netto
            'sconto1': parsed['sconto_perc'],
            'data_consegna_riga': parsed['data_consegna'],
            'is_espositore': is_esp,
            'is_child': is_child,
        })

    # =========================================================================
    # 5. DATA CONSEGNA TESTATA (prima riga se presente)
    # =========================================================================
    if data['righe'] and data['righe'][0].get('data_consegna_riga'):
        data['data_consegna'] = data['righe'][0]['data_consegna_riga']

    return [data] if data.get('righe') or data.get('numero_ordine') else []
