# =============================================================================
# SERV.O v7.0 - UTILS/CONVERSIONS
# =============================================================================
# Funzioni per parsing e conversione numeri
# =============================================================================

import re
from decimal import Decimal, InvalidOperation


def parse_decimal(value: str) -> Decimal:
    """
    Converte stringa in Decimal.

    Gestisce:
    - Virgola come separatore decimale (italiano)
    - Punto come separatore migliaia
    - Simboli € e EUR
    """
    if not value:
        return Decimal('0')

    value = str(value).strip()

    # Rimuovi simboli valuta e spazi
    value = value.replace('€', '').replace('EUR', '').replace(' ', '')

    # Rimuovi caratteri non numerici eccetto , . -
    value = re.sub(r'[^\d,.\-]', '', value)

    if not value:
        return Decimal('0')

    # Gestisci formato italiano (1.234,56) vs americano (1,234.56)
    if ',' in value and '.' in value:
        # Se virgola dopo punto → italiano (1.234,56)
        if value.rfind(',') > value.rfind('.'):
            value = value.replace('.', '').replace(',', '.')
        else:
            # Americano (1,234.56)
            value = value.replace(',', '')
    elif ',' in value:
        # Solo virgola → italiano
        value = value.replace(',', '.')

    try:
        return Decimal(value)
    except InvalidOperation:
        return Decimal('0')


def parse_int(value: str) -> int:
    """
    Converte stringa in intero.
    Rimuove tutti i caratteri non numerici.
    """
    if not value:
        return 0

    value = re.sub(r'[^\d]', '', str(value))
    return int(value) if value else 0


def parse_float(value: str) -> float:
    """Converte stringa in float usando parse_decimal."""
    return float(parse_decimal(value))
