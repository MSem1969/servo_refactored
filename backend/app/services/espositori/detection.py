# =============================================================================
# SERV.O v10.1 - ESPOSITORI DETECTION
# =============================================================================
# Funzioni di rilevamento tipo riga e pezzi espositore
# =============================================================================

import re
from typing import Optional, Tuple


def identifica_tipo_riga(codice: str, descrizione: str, tipo_posizione: str = '', vendor: str = '') -> str:
    """
    Classifica tipo riga con priorità tipo_posizione.

    Supporta:
    - MENARINI: parent ha codice "--" + keywords espositore
    - ANGELINI: parent ha codice 6 cifre + XXPZ o keywords
    """
    codice = str(codice).strip() if codice else ''
    tipo_posizione = str(tipo_posizione).strip().upper() if tipo_posizione else ''
    descrizione = str(descrizione).upper() if descrizione else ''
    vendor = str(vendor).upper() if vendor else ''

    if 'SC.MERCE' in tipo_posizione or 'SCMERCE' in tipo_posizione:
        return 'SCONTO_MERCE'

    if 'P.O.P' in tipo_posizione or 'POP' in tipo_posizione:
        return 'MATERIALE_POP'

    # MENARINI - parent ha codice "--" + keywords
    if vendor == 'MENARINI':
        if codice == '--' and re.search(r'BANCO|DBOX|FSTAND|EXPO|DISPLAY|ESPOSITORE|CESTA', descrizione, re.I):
            return 'PARENT_ESPOSITORE'
        # Qualsiasi altra riga MENARINI è prodotto standard (child gestiti da state machine)
        return 'PRODOTTO_STANDARD'

    # ANGELINI e altri vendor: logica esistente
    codice_num = re.sub(r'[^\d]', '', codice)
    len_codice = len(codice_num)

    if len_codice == 6:
        # Espositori con XXPZ nella descrizione
        if re.search(r'\d+\s*PZ\b', descrizione):
            return 'PARENT_ESPOSITORE'
        # Espositori identificati da parole chiave (anche senza XXPZ)
        elif re.search(r'BANCO|DBOX|FSTAND|EXPO|DISPLAY|ESPOSITORE|CESTA', descrizione, re.I):
            return 'PARENT_ESPOSITORE'
        else:
            return 'PROMO_AUTONOMA'

    return 'PRODOTTO_STANDARD'


def estrai_pezzi_espositore(descrizione: str, quantita: int) -> Tuple[Optional[int], Optional[int]]:
    """
    Estrae pezzi per unità dalla descrizione.

    Supporta formato "X+Y" per MENARINI (es. "3+3" = 6 pezzi)
    """
    if not descrizione:
        return (None, None)

    descrizione = str(descrizione).upper()

    # Pattern "X+Y" per MENARINI (es. "EXPO BANCO 3+3" = 6 pezzi)
    match_sum = re.search(r'(\d+)\s*\+\s*(\d+)(?!\d)', descrizione)
    if match_sum:
        pezzi_per_unita = int(match_sum.group(1)) + int(match_sum.group(2))
        if 1 <= pezzi_per_unita <= 1000:
            return (pezzi_per_unita, pezzi_per_unita * quantita)

    patterns = [
        r'FSTAND\s*(\d+)\s*PZ',
        r'DBOX\s*(\d+)\s*PZ',
        r'EXPO\s*(\d+)\s*PZ',
        r'BANCO\s*(\d+)\s*PZ',
        r'(\d+)\s*PZ\b',
    ]

    for pattern in patterns:
        match = re.search(pattern, descrizione)
        if match:
            pezzi_per_unita = int(match.group(1))
            if 1 <= pezzi_per_unita <= 1000:
                return (pezzi_per_unita, pezzi_per_unita * quantita)

    return (None, None)
