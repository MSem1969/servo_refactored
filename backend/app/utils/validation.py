# =============================================================================
# SERV.O v7.0 - UTILS/VALIDATION
# =============================================================================
# Funzioni di validazione
# =============================================================================

from typing import List, Optional


def validate_stato(stato: str, stati_validi: List[str], nome_campo: str = "stato") -> Optional[str]:
    """
    Validate state value against allowed list.

    Args:
        stato: Value to validate
        stati_validi: List of valid values
        nome_campo: Field name for error message

    Returns:
        Error message if invalid, None if valid
    """
    if stato and stato not in stati_validi:
        return f"{nome_campo} non valido. Valori ammessi: {', '.join(stati_validi)}"
    return None


def validate_file_extension(filename: str, allowed_extensions: List[str]) -> Optional[str]:
    """
    Validate file extension.

    Args:
        filename: File name to check
        allowed_extensions: List of allowed extensions (e.g., ['.pdf', '.csv'])

    Returns:
        Error message if invalid, None if valid
    """
    if not filename:
        return "Nome file mancante"

    ext = filename.lower().split('.')[-1] if '.' in filename else ''
    allowed = [e.lstrip('.').lower() for e in allowed_extensions]

    if ext not in allowed:
        return f"Formato non supportato. Formati ammessi: {', '.join(allowed_extensions)}"
    return None
