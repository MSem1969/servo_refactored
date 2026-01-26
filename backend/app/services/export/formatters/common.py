# =============================================================================
# SERV.O v7.0 - EXPORT FORMATTERS COMMON
# =============================================================================
# Funzioni comuni di formattazione per tracciati EDI
# =============================================================================

import re
from datetime import date, datetime

# Lunghezza righe secondo schema EDI
TO_T_LENGTH = 869   # Testata (v11.3: corretto da 857)
TO_D_LENGTH = 344   # Dettaglio (calcolato da schema)

# Codice produttore default (fallback)
DEFAULT_VENDOR_CODE = "HAL_FARVI"

# =============================================================================
# MAPPING VENDOR → PREFISSO 3 CARATTERI
# =============================================================================
VENDOR_PREFIX_MAP = {
    'ANGELINI': 'ANG',
    'BAYER': 'BAY',
    'CHIESI': 'CHI',
    'CODIFI': 'COD',
    'COOPER': 'COP',
    'DOC_GENERICI': 'DOC',
    'MENARINI': 'MEN',
    'OPELLA': 'OPE',
    'RECKITT': 'REC',
}

# =============================================================================
# MAPPING DEPOSITO → DISTRIBUTORE
# =============================================================================
# CT, CL → SOFAD
# PE, CB → SAFAR
# Altri  → FARVI
DEPOSITO_DISTRIBUTORE_MAP = {
    'CT': 'SOFAD',
    'CL': 'SOFAD',
    'PE': 'SAFAR',
    'CB': 'SAFAR',
}
DEFAULT_DISTRIBUTORE = 'FARVI'


def get_vendor_code(vendor: str, deposito: str = None) -> str:
    """
    Genera il codice vendor per il tracciato TO_T (posizione 1-10).

    Combina:
    - Prefisso vendor (3 caratteri): ANG, BAY, CHI, COD, COP, DOC, MEN, OPE, REC
    - Distributore (5 caratteri): FARVI, SOFAD, SAFAR

    Logica distributore basata su deposito:
    - CT, CL → SOFAD
    - PE, CB → SAFAR
    - Altri  → FARVI

    Args:
        vendor: Nome vendor (ANGELINI, BAYER, etc.)
        deposito: Codice deposito (CT, CL, PE, CB, etc.)

    Returns:
        Codice vendor formato "{PREFIX}_{DISTRIBUTORE}" (es: ANG_FARVI, BAY_SOFAD)
    """
    # Ottieni prefisso vendor (3 char)
    vendor_upper = (vendor or '').upper().strip()
    prefix = VENDOR_PREFIX_MAP.get(vendor_upper)

    if not prefix:
        # Fallback: primi 3 caratteri del vendor o 'HAL'
        prefix = vendor_upper[:3] if vendor_upper else 'HAL'

    # Ottieni distributore da deposito
    deposito_upper = (deposito or '').upper().strip()
    distributore = DEPOSITO_DISTRIBUTORE_MAP.get(deposito_upper, DEFAULT_DISTRIBUTORE)

    # Combina: PREFIX_DISTRIBUTORE
    return f"{prefix}_{distributore}"


def format_date_edi(date_val) -> str:
    """
    Formatta data per tracciato EDI: GG/MM/AAAA (10 caratteri).
    Accetta stringhe o oggetti datetime.date (PostgreSQL).
    """
    if not date_val:
        return ' ' * 10

    # PostgreSQL restituisce datetime.date - converti in stringa DD/MM/YYYY
    if isinstance(date_val, (date, datetime)):
        return date_val.strftime('%d/%m/%Y')

    # Da qui in poi è una stringa
    date_str = str(date_val)

    # Già in formato DD/MM/YYYY
    if re.match(r'^\d{2}/\d{2}/\d{4}$', date_str):
        return date_str

    # YYYY-MM-DD (ISO da PostgreSQL come stringa) -> DD/MM/YYYY
    m = re.match(r'^(\d{4})-(\d{2})-(\d{2})$', date_str)
    if m:
        return f"{m.group(3)}/{m.group(2)}/{m.group(1)}"

    # DD.MM.YYYY -> DD/MM/YYYY
    m = re.match(r'^(\d{2})\.(\d{2})\.(\d{4})$', date_str)
    if m:
        return f"{m.group(1)}/{m.group(2)}/{m.group(3)}"

    # YYYYMMDD -> DD/MM/YYYY
    m = re.match(r'^(\d{4})(\d{2})(\d{2})$', date_str)
    if m:
        return f"{m.group(3)}/{m.group(2)}/{m.group(1)}"

    # DD-MM-YYYY -> DD/MM/YYYY
    m = re.match(r'^(\d{2})-(\d{2})-(\d{4})$', date_str)
    if m:
        return f"{m.group(1)}/{m.group(2)}/{m.group(3)}"

    return date_str.ljust(10)[:10]


def format_float_edi(value: float, int_digits: int, dec_digits: int) -> str:
    """
    Formatta float per EDI: int_digits.dec_digits con punto decimale.
    Esempio: format_float_edi(8.56, 7, 2) -> "0000008.56"
    """
    if value is None:
        value = 0.0
    try:
        value = float(value)
    except:
        value = 0.0

    total_len = int_digits + dec_digits + 1  # +1 per il punto
    formatted = f"{value:0{total_len}.{dec_digits}f}"
    return formatted[:total_len]


def format_int_edi(value: int, digits: int) -> str:
    """
    Formatta intero per EDI: zero-padded a sinistra.
    """
    if value is None:
        value = 0
    try:
        value = int(value)
    except:
        value = 0
    return str(value).zfill(digits)[:digits]
