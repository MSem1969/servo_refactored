"""
EXTRACTOR_TO - Estrattore CHIESI
=================================
Convertito da TO_EXTRACTOR_v6_0_DB_def.ipynb - Cella 8
Regole: REGOLE_CHIESI.md
"""

import re
from typing import Dict, List

from ...utils import parse_date, normalize_aic, format_piva


# Pattern compilato per righe prodotto CHIESI
CHIESI_ROW_PATTERN = re.compile(
    r'^(\d{9})\s+(\S+)\s+(.+?)\s+(\d{2}/\d{2}/\d{4})\s+(\d+)\s+(\d+)\s+([\d,]+)%?\s+([\d,]+)\s+([\d,]+)\s*$'
)


def extract_chiesi(text: str, lines: List[str], pdf_path: str = None) -> List[Dict]:
    """
    Estrae dati da PDF CHIESI.
    
    IMPORTANTE: Escludere P.IVA 02944970348 (è P.IVA vendor, non cliente!)
    
    Particolarità:
    - P.IVA vendor da ignorare
    - Colonna CODICE interno da ignorare
    - Q.TA' S.M. → QOmaggio
    - Data consegna specifica per ogni riga
    """
    data = {'vendor': 'CHIESI', 'righe': []}

    # Numero ordine e data
    m = re.search(r'Numero\s+Ordine:?\s*(O-\d+)\s+del\s+(\d{2}/\d{2}/\d{4})', text, re.I)
    if m:
        data['numero_ordine'] = m.group(1)
        data['data_ordine'] = parse_date(m.group(2))

    # P.IVA (escludere P.IVA vendor 02944970348)
    for piva_match in re.finditer(r'P\.?IVA\s+(\d{11})', text):
        piva = piva_match.group(1)
        if piva != '02944970348':  # P.IVA Chiesi da escludere
            data['partita_iva'] = format_piva(piva)
            break

    # Ragione sociale
    m = re.search(r'Cliente\s+consegna\s+([A-Z][^\n]+)', text)
    if m:
        data['ragione_sociale'] = m.group(1).strip()[:50]
    else:
        m = re.search(r'Cliente\s+Fatturazione\s+([A-Z][^\n]+)', text)
        if m:
            data['ragione_sociale'] = m.group(1).strip()[:50]

    # Indirizzo
    m = re.search(r'Indirizzo\s+consegna\s+([^\n]+)', text)
    if m:
        data['indirizzo'] = m.group(1).strip()[:50]

    # CAP, Città, Provincia
    m = re.search(r'Cap\s+e\s+Localit[àa]\s+(?:IT-)?(\d{5})\s+([A-Z][A-Z\s\']+?)\s+([A-Z]{2})', text)
    if m:
        data['cap'] = m.group(1)
        data['citta'] = m.group(2).strip()
        data['provincia'] = m.group(3)

    # Agente
    m = re.search(r'Agente\s+([A-Z][A-Z\s]+?)(?:\s+Codice|\s*$)', text, re.M)
    if m:
        data['nome_agente'] = m.group(1).strip()[:50]

    # Dilazione
    m = re.search(r'Dilazione\s+(\d{2,3})R?', text)
    if m:
        data['gg_dilazione'] = int(m.group(1))

    # Righe prodotto
    n_riga = 0
    for line in lines:
        line_stripped = line.strip()
        m = CHIESI_ROW_PATTERN.match(line_stripped)
        if m:
            n_riga += 1
            codice_aic = m.group(1)
            # m.group(2) è CODICE interno - IGNORARE
            descrizione = m.group(3).strip()[:40]
            data_consegna = parse_date(m.group(4))
            q_venduta = int(m.group(5))
            q_omaggio = int(m.group(6))  # Q.TA' S.M. = Omaggio
            sconto1 = float(m.group(7).replace(',', '.'))
            prezzo_netto = float(m.group(8).replace(',', '.'))

            aic_norm, aic_orig, is_esp, is_child = normalize_aic(codice_aic, descrizione)

            data['righe'].append({
                'n_riga': n_riga,
                'codice_aic': aic_norm,
                'codice_originale': aic_orig,
                'descrizione': descrizione,
                'data_consegna': data_consegna,
                'q_venduta': q_venduta,
                'q_omaggio': q_omaggio,
                'sconto1': sconto1,
                'prezzo_netto': prezzo_netto,
                'is_espositore': is_esp,
                'is_child': is_child,
            })

    return [data]
