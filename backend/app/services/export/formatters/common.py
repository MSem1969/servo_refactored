# =============================================================================
# SERV.O v7.0 - EXPORT FORMATTERS COMMON
# =============================================================================
# Funzioni comuni di formattazione per tracciati EDI
# =============================================================================

import re
from datetime import date, datetime

# Lunghezza righe secondo schema EDI
TO_T_LENGTH = 857   # Testata (calcolato da schema)
TO_D_LENGTH = 344   # Dettaglio (calcolato da schema)

# Codice produttore default
DEFAULT_VENDOR_CODE = "HAL_FARVI"


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
