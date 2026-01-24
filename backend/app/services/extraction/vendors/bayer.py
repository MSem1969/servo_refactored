"""
EXTRACTOR_TO - Estrattore BAYER v11.0
=====================================
Convertito da SERV.O_v6_0_DB_def.ipynb - Cella 7
Regole: REGOLE_BAYER.md

v11.0: Aggiunto supporto espositori parent/child (logica simile ad ANGELINI)
"""

import re
from typing import Dict, List

from ....utils import parse_date, parse_decimal, parse_int, normalize_aic_simple, format_piva
from ...espositore import elabora_righe_ordine


def extract_bayer(text: str, lines: List[str], pdf_path: str = None) -> List[Dict]:
    """
    Estrae dati da PDF BAYER (formato SAP).

    Particolarità:
    - Formato SAP standard
    - Codici materiale SAP interni
    - v11.0: Supporto espositori parent/child
    """
    data = {
        'vendor': 'BAYER',
        'righe_raw': [],
        'righe': [],
        'anomalie_espositore': [],
    }

    # Numero ordine
    for i, line in enumerate(lines):
        if "NUM. PROP" in line and i > 0:
            data['numero_ordine'] = lines[i-1].strip()
            break

    # Data ordine
    for i, line in enumerate(lines):
        if "DATA ACQUISIZIONE" in line and i > 0:
            data['data_ordine'] = parse_date(lines[i-1].strip())
            break

    # Ragione sociale e P.IVA (secondo blocco SAP)
    sap_count = 0
    for i, line in enumerate(lines):
        if '(SAP:' in line:
            sap_count += 1
            if sap_count == 2 and i+1 < len(lines):
                data['ragione_sociale'] = lines[i+1].strip()[:50]
                if i+2 < len(lines) and 'P.IVA:' in lines[i+2]:
                    m = re.search(r'P\.IVA:\s*(\d{11})', lines[i+2])
                    if m:
                        data['partita_iva'] = format_piva(m.group(1))
                break

    # Indirizzo, CAP, Città, Provincia
    # v6.2: Aggiunta estrazione CAP per indirizzo concatenato
    for i, line in enumerate(lines):
        if line.strip() == 'CLIENTE' and i+3 < len(lines):
            data['indirizzo'] = lines[i+1].strip()[:50]
            citta_line = lines[i+2].strip()
            # v6.2: Estrai CAP da città (formato: "00100 ROMA" o "ROMA")
            cap_citta = re.match(r'^(\d{5})\s+(.+)$', citta_line)
            if cap_citta:
                data['cap'] = cap_citta.group(1)
                data['citta'] = cap_citta.group(2).strip()
            else:
                data['citta'] = citta_line
            prov = lines[i+3].strip()
            if re.match(r'^\([A-Z]{2}\)$', prov):
                data['provincia'] = prov[1:3]
            break

    # Agente
    m = re.search(r'COLLABORATORE\s+([A-Z][A-Z\s]+)', text)
    if m:
        data['nome_agente'] = m.group(1).strip()

    # Dilazione
    m = re.search(r'(\d+)\s*gg', text)
    if m:
        data['gg_dilazione'] = int(m.group(1))

    # Data consegna
    m = re.search(r'(\d{1,2}\s+\w{3}\s+\d{4})', text)
    if m:
        data['data_consegna'] = parse_date(m.group(1))

    # v11.0: Righe prodotto - raccogliamo in righe_raw prima dell'elaborazione espositore
    righe_raw = []
    for line in lines:
        line_stripped = line.strip()
        m = re.match(
            r'^(\d{7,9})\s+(.+?)\s+(\d+)\s+€\s*([\d,\.]+)\s+(\d+)\s+(\d+)\s*gg',
            line_stripped
        )
        if m:
            codice_raw = m.group(1)
            desc = m.group(2).strip()[:40]
            aic_norm = normalize_aic_simple(codice_raw)

            righe_raw.append({
                'codice_aic': aic_norm,
                'codice_originale': codice_raw,
                'descrizione': desc,
                'quantita': parse_int(m.group(3)),
                'prezzo_netto': float(parse_decimal(m.group(4))),
                'aliquota_iva': 10,  # Default IVA
                'valore_netto': float(parse_decimal(m.group(4))) * parse_int(m.group(3)),
            })

    data['righe_raw'] = righe_raw

    # v11.0: Elabora con logica espositori (parent/child)
    if righe_raw:
        ctx = elabora_righe_ordine(righe_raw, vendor='BAYER')
        data['righe'] = ctx.righe_output
        data['anomalie_espositore'] = ctx.anomalie
        data['_stats'] = {
            'righe_raw': len(righe_raw),
            'righe_output': len(ctx.righe_output),
            'espositori': ctx.espositori_elaborati,
            'chiusure_normali': ctx.chiusure_normali,
            'chiusure_forzate': ctx.chiusure_forzate,
            'anomalie': len(ctx.anomalie),
        }

    return [data]
