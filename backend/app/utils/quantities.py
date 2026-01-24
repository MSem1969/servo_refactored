# =============================================================================
# SERV.O v7.0 - UTILS/QUANTITIES
# =============================================================================
# Funzioni per calcolo quantità (Single Source of Truth)
# =============================================================================

from typing import Dict, Any


def calcola_q_totale(riga: Dict[str, Any]) -> int:
    """
    Calcola quantità totale: venduta + sconto_merce + omaggio.

    Single source of truth per il calcolo quantità.
    Handles both dict access patterns safely.

    Args:
        riga: Dictionary con campi q_venduta, q_sconto_merce, q_omaggio

    Returns:
        Quantità totale come intero
    """
    return (
        int(riga.get('q_venduta') or 0) +
        int(riga.get('q_sconto_merce') or 0) +
        int(riga.get('q_omaggio') or 0)
    )
