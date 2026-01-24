# =============================================================================
# SERV.O v10.1 - LISTINI PARSING
# =============================================================================
# Funzioni di parsing valori per listini
# =============================================================================

import math
from typing import Optional, Tuple
from datetime import datetime


def parse_decimal_it(value: str) -> Optional[float]:
    """
    Converte valore decimale italiano (virgola) in float.
    Es: "38,35" -> 38.35
    """
    if not value or value.strip() == '' or value.strip() == '0':
        return None
    try:
        cleaned = value.strip().replace(',', '.')
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def parse_prezzo_intero(value: str, decimals: int = 2) -> Optional[float]:
    """
    Converte prezzo in formato intero con decimali impliciti.
    Es: "00013590" con 2 decimali -> 135.90
    """
    if not value or value.strip() == '' or value.strip() == '0':
        return None
    try:
        cleaned = value.strip().lstrip('0') or '0'
        val_int = int(cleaned)
        divisor = 10 ** decimals
        return val_int / divisor
    except (ValueError, TypeError):
        return None


def parse_data_yyyymmdd(value: str) -> Optional[str]:
    """
    Converte data formato YYYYMMDD in formato ISO YYYY-MM-DD.
    Es: "20180206" -> "2018-02-06"
    """
    if not value or len(value) != 8:
        return None
    try:
        year = value[:4]
        month = value[4:6]
        day = value[6:8]
        datetime(int(year), int(month), int(day))
        return f"{year}-{month}-{day}"
    except (ValueError, TypeError):
        return None


def normalizza_codice_aic(codice: str) -> str:
    """
    Normalizza codice AIC a 9 cifre con zero padding.
    Es: "39887070" -> "039887070"
    """
    if not codice:
        return ''
    cleaned = ''.join(c for c in str(codice).strip() if c.isdigit())
    return cleaned.zfill(9)


def ceil_decimal(value: float, decimals: int = 2) -> float:
    """
    Arrotonda per eccesso a N decimali.
    Es: 123.541 con 2 decimali -> 123.55
    """
    if value is None:
        return None
    multiplier = 10 ** decimals
    return math.ceil(value * multiplier) / multiplier


def arrotonda_per_ordine(valore: float, decimali: int = 3) -> Optional[float]:
    """
    Arrotonda valore per inserimento in ordine.
    Usa arrotondamento ordinario (standard) a N decimali.

    Args:
        valore: Valore da arrotondare
        decimali: Numero decimali (default 3 per ordini)

    Returns:
        Valore arrotondato o None se input None
    """
    if valore is None:
        return None
    return round(valore, decimali)


def scorporo_iva(prezzo_ivato: float, aliquota_iva: float, decimali: int = 5) -> Optional[float]:
    """
    Calcola prezzo netto da prezzo IVA inclusa.
    Formula: prezzo_ivato / ((100 + IVA) / 100)

    Args:
        prezzo_ivato: Prezzo con IVA inclusa
        aliquota_iva: Aliquota IVA (es: 10, 22)
        decimali: Numero decimali per arrotondamento (default 5 per calcoli interni)

    Returns:
        Prezzo senza IVA arrotondato a N decimali
    """
    if prezzo_ivato is None or prezzo_ivato <= 0:
        return None
    if aliquota_iva is None or aliquota_iva < 0:
        aliquota_iva = 0

    divisore = (100 + aliquota_iva) / 100
    prezzo_netto = prezzo_ivato / divisore

    return round(prezzo_netto, decimali)


def calcola_prezzo_netto(
    prezzo_scontare: float,
    sconto_1: float = None,
    sconto_2: float = None,
    sconto_3: float = None,
    sconto_4: float = None,
    formula: str = 'SCONTO_CASCATA'
) -> Tuple[Optional[float], str]:
    """
    Calcola NetVendorPrice (prezzo_netto) applicando sconti al PriceToDiscount.

    Formule supportate:
    - SCONTO_CASCATA: prezzo * (1-s1/100) * (1-s2/100) * (1-s3/100) * (1-s4/100)
    - SCONTO_SOMMA: prezzo * (1 - (s1+s2+s3+s4)/100)
    """
    if prezzo_scontare is None or prezzo_scontare <= 0:
        return None, ''

    s1 = sconto_1 or 0
    s2 = sconto_2 or 0
    s3 = sconto_3 or 0
    s4 = sconto_4 or 0

    if formula == 'SCONTO_CASCATA':
        prezzo = prezzo_scontare
        for s in [s1, s2, s3, s4]:
            if s > 0:
                prezzo = prezzo * (1 - s / 100)
        formula_str = f"PtD * (1-{s1}/100) * (1-{s2}/100) * (1-{s3}/100) * (1-{s4}/100)"
    elif formula == 'SCONTO_SOMMA':
        sconto_totale = s1 + s2 + s3 + s4
        prezzo = prezzo_scontare * (1 - sconto_totale / 100)
        formula_str = f"PtD * (1 - ({s1}+{s2}+{s3}+{s4})/100)"
    else:
        return None, f"Formula non supportata: {formula}"

    return round(prezzo, 2), formula_str
