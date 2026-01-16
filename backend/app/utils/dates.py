# =============================================================================
# SERV.O v7.0 - UTILS/DATES
# =============================================================================
# Funzioni per parsing e formattazione date
# =============================================================================

import re


def parse_date(date_str: str) -> str:
    """
    Normalizza date in formato GG/MM/AAAA.

    Formati supportati:
    - DD/MM/YYYY, DD.MM.YYYY, DD-MM-YYYY
    - DD/MM/YY (aggiunge 20)
    - YYYY-MM-DD (ISO)
    - "1 Dec 2025" (testuale)

    Returns:
        Data in formato DD/MM/YYYY o stringa vuota se non parsabile
    """
    if not date_str:
        return ''

    date_str = str(date_str).strip()

    # Già nel formato corretto
    if re.match(r'^\d{2}/\d{2}/\d{4}$', date_str):
        return date_str

    # DD.MM.YYYY o DD-MM-YYYY
    m = re.match(r'^(\d{2})[.\-](\d{2})[.\-](\d{4})$', date_str)
    if m:
        return f"{m.group(1)}/{m.group(2)}/{m.group(3)}"

    # DD/MM/YY
    m = re.match(r'^(\d{2})[/.\-](\d{2})[/.\-](\d{2})$', date_str)
    if m:
        year = int(m.group(3))
        year = 2000 + year if year < 50 else 1900 + year
        return f"{m.group(1)}/{m.group(2)}/{year}"

    # YYYY-MM-DD (ISO)
    m = re.match(r'^(\d{4})-(\d{2})-(\d{2})$', date_str)
    if m:
        return f"{m.group(3)}/{m.group(2)}/{m.group(1)}"

    # Formato testuale "1 Dec 2025" o "01 Dic 2025"
    months = {
        'JAN': '01', 'FEB': '02', 'MAR': '03', 'APR': '04',
        'MAY': '05', 'JUN': '06', 'JUL': '07', 'AUG': '08',
        'SEP': '09', 'OCT': '10', 'NOV': '11', 'DEC': '12',
        'GEN': '01', 'FEB': '02', 'MAR': '03', 'APR': '04',
        'MAG': '05', 'GIU': '06', 'LUG': '07', 'AGO': '08',
        'SET': '09', 'OTT': '10', 'NOV': '11', 'DIC': '12',
    }
    m = re.match(r'^(\d{1,2})\s+(\w{3})\s+(\d{4})$', date_str)
    if m:
        day = int(m.group(1))
        mon = months.get(m.group(2).upper()[:3], '01')
        year = m.group(3)
        return f"{day:02d}/{mon}/{year}"

    # Non riconosciuto, ritorna originale
    return date_str


def format_date_for_tracciato(date_str: str) -> str:
    """
    Converte data in formato YYYYMMDD per tracciati.

    Args:
        date_str: Data in formato DD/MM/YYYY

    Returns:
        Data in formato YYYYMMDD
    """
    if not date_str:
        return ''

    # Normalizza prima
    date_str = parse_date(date_str)

    m = re.match(r'^(\d{2})/(\d{2})/(\d{4})$', date_str)
    if m:
        return f"{m.group(3)}{m.group(2)}{m.group(1)}"

    return ''
