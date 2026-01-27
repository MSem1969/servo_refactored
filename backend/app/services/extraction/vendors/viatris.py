"""
EXTRACTOR_TO - Estrattore VIATRIS v11.3
=======================================
Estrattore per ordini VIATRIS (Transfer Order)

Struttura documento:
- Header: OR{numero_ordine}
- Sezione CLIENTE: agente, data, ragione sociale, indirizzo, P.IVA (ITxxxxxxxxxx)
- Sezione DESTINAZIONE MERCE: nome, MIN_ID (Fxxxxx), indirizzo
- Tabella prodotti: descrizione + AIC, prezzi, quantità, sconti, data consegna

v11.3: Implementazione iniziale
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


def extract_viatris(text: str, lines: List[str], pdf_path: str = None) -> List[Dict]:
    """
    Estrattore VIATRIS v11.3.

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

    # MIN_ID - TRACC.F{numero}
    m = re.search(r'TRACC\.F(\d+)', text)
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
    # La tabella ha prodotti su più righe:
    # Riga 1: Descrizione + prezzi + quantità + sconti + data
    # Riga 2: AIC: XXXXXXXXX

    # Pattern per estrarre righe prodotto
    # Cerchiamo pattern: descrizione seguita da prezzo (€) e poi AIC sulla riga successiva

    # Prima troviamo tutte le occorrenze di AIC
    aic_pattern = r'AIC:\s*(\d{9})'
    aic_matches = list(re.finditer(aic_pattern, text))

    n_riga = 0
    for aic_match in aic_matches:
        aic_code = aic_match.group(1)
        aic_pos = aic_match.start()

        # Trova la riga del prodotto che precede l'AIC
        # Cerchiamo all'indietro dal punto AIC per trovare la riga dati
        text_before_aic = text[:aic_pos]

        # Pattern per riga prodotto: descrizione + PP + PP.Netto + Q.TA + SC.MER + SC.NET + P.CESS + P.CESS + DATA
        # Es: "CETIRIZINA 10 MG 20 CPR 71,94 € 65,40 € 20 0 38,35% 2,0160 € 40,32 € 26/01/2026"

        # Troviamo l'ultima riga completa prima dell'AIC
        # La riga contiene: descrizione, poi valori numerici con € e %

        # Split per linee e prendiamo l'ultima non vuota prima dell'AIC
        lines_before = text_before_aic.split('\n')

        product_line = None
        for line in reversed(lines_before):
            line = line.strip()
            # La riga prodotto contiene almeno un prezzo (€) e una data
            if '€' in line and re.search(r'\d{2}/\d{2}/\d{4}', line):
                product_line = line
                break

        if not product_line:
            continue

        # Estrai dati dalla riga prodotto
        # Pattern più specifico per parsing
        # Formato: {descrizione} {PP €} {PP.Netto €} {Q.TA} {SC.MER} {SC%} {P.CESS €} {P.CESS TOT €} {DATA}

        # Estrai data consegna (alla fine)
        data_consegna_match = re.search(r'(\d{2}/\d{2}/\d{4})\s*$', product_line)
        data_consegna = parse_date(data_consegna_match.group(1)) if data_consegna_match else None

        # Estrai prezzi (cerchiamo tutti i numeri con €)
        prezzi = re.findall(r'([\d,\.]+)\s*€', product_line)

        # Estrai percentuale sconto
        sconto_match = re.search(r'([\d,]+)\s*%', product_line)
        sconto_perc = _parse_percentage(sconto_match.group(1)) if sconto_match else 0

        # Estrai quantità e sconto merce
        # Dopo PP.Netto € ci sono Q.TA e SC.MER (due numeri interi)
        # Pattern: {prezzo €} {qty} {sc_mer} {sconto%}
        qty_pattern = re.search(r'€\s*(\d+)\s+(\d+)\s+[\d,]+\s*%', product_line)

        q_venduta = 0
        q_omaggio = 0

        if qty_pattern:
            q_venduta = int(qty_pattern.group(1))
            q_omaggio = int(qty_pattern.group(2))

        # Descrizione: tutto prima del primo prezzo
        first_price_pos = product_line.find('€')
        if first_price_pos > 0:
            # Troviamo l'inizio del primo numero prima del €
            desc_end = first_price_pos
            while desc_end > 0 and (product_line[desc_end-1].isdigit() or product_line[desc_end-1] in ',. '):
                desc_end -= 1
            descrizione = product_line[:desc_end].strip()
        else:
            descrizione = product_line[:30]

        # Prezzi
        prezzo_pubblico = _parse_price(prezzi[0]) if len(prezzi) > 0 else 0
        prezzo_pubblico_netto = _parse_price(prezzi[1]) if len(prezzi) > 1 else 0
        prezzo_unitario = _parse_price(prezzi[2]) if len(prezzi) > 2 else 0
        prezzo_totale = _parse_price(prezzi[3]) if len(prezzi) > 3 else 0

        # Normalizza AIC
        aic_norm, aic_orig, is_esp, is_child = _normalize_aic_viatris(aic_code)

        n_riga += 1
        data['righe'].append({
            'n_riga': n_riga,
            'codice_aic': aic_norm,
            'codice_originale': aic_orig,
            'descrizione': descrizione[:40],
            'q_venduta': q_venduta,
            'q_omaggio': q_omaggio,
            'q_sconto_merce': 0,  # VIATRIS usa q_omaggio per sconto merce
            'prezzo_pubblico': prezzo_pubblico,
            'prezzo_netto': prezzo_unitario,  # Prezzo unitario scontato
            'sconto1': sconto_perc,
            'data_consegna_riga': data_consegna,
            'is_espositore': is_esp,
            'is_child': is_child,
        })

    # =========================================================================
    # 5. DATA CONSEGNA TESTATA (prima riga se presente)
    # =========================================================================
    if data['righe'] and data['righe'][0].get('data_consegna_riga'):
        data['data_consegna'] = data['righe'][0]['data_consegna_riga']

    return [data] if data.get('righe') or data.get('numero_ordine') else []
