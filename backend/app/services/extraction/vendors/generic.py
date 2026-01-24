"""
EXTRACTOR_TO - Estrattore Generico
===================================
Per vendor non riconosciuti
"""

import re
from typing import Dict, List

from ....utils import normalize_aic, format_piva


def extract_generic(text: str, lines: List[str], pdf_path: str = None) -> List[Dict]:
    """Estrattore generico per vendor sconosciuti."""
    data = {'vendor': 'UNKNOWN', 'righe': []}
    
    # Cerca numero ordine
    m = re.search(r'(?:N[°.r]?|Numero)\s*(?:Ordine|Order)[:\s]*(\S+)', text, re.I)
    if m:
        data['numero_ordine'] = m.group(1)
    
    # Cerca P.IVA
    m = re.search(r'P\.?\s*IVA[:\s]*(\d{11})', text, re.I)
    if m:
        data['partita_iva'] = format_piva(m.group(1))
    
    # Cerca tutti i codici AIC nel testo
    n = 0
    for aic in re.findall(r'\b(0\d{8})\b', text):
        n += 1
        aic_norm, aic_orig, is_esp, is_child = normalize_aic(aic, '')
        data['righe'].append({
            'n_riga': n,
            'codice_aic': aic_norm,
            'codice_originale': aic_orig,
            'q_venduta': 1,
            'is_espositore': is_esp,
            'is_child': is_child,
        })
    
    return [data]
