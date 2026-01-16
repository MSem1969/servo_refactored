# =============================================================================
# SERV.O v7.0 - UTILS/KEYS
# =============================================================================
# Funzioni per generazione chiavi univoche
# =============================================================================


def generate_order_key(vendor: str, numero_ordine: str, codice_ministeriale: str) -> str:
    """
    Genera chiave univoca per ordine.

    Format: VENDOR_NUMORDINE_CODMIN
    """
    vendor = (vendor or 'UNKNOWN').upper()
    numero = (numero_ordine or 'ND').strip()
    cod_min = (codice_ministeriale or 'NOMIN').strip()

    return f"{vendor}_{numero}_{cod_min}"
