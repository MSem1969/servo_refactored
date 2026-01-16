# =============================================================================
# SERV.O v7.0 - UTILS/HASHING
# =============================================================================
# Funzioni per calcolo hash
# =============================================================================

import hashlib


def compute_file_hash(file_content: bytes) -> str:
    """
    Calcola SHA-256 del contenuto file.

    Args:
        file_content: Contenuto binario del file

    Returns:
        Hash SHA-256 in formato esadecimale
    """
    return hashlib.sha256(file_content).hexdigest()


def compute_string_hash(text: str) -> str:
    """Calcola SHA-256 di una stringa."""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()
