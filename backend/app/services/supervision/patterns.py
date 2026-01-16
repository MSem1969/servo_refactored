# =============================================================================
# SERV.O v7.0 - SUPERVISION PATTERNS
# =============================================================================
# Gestione pattern signature per machine learning
# =============================================================================

import hashlib
from typing import Dict

from .constants import FASCE_NORMALIZZATE


def calcola_pattern_signature(
    vendor: str,
    codice_anomalia: str,
    codice_espositore: str,
    pezzi_per_unita: int,
    fascia_scostamento: str
) -> str:
    """
    Calcola signature univoca per un pattern anomalia.

    La signature permette di identificare anomalie "simili" che possono
    essere gestite automaticamente dopo sufficiente apprendimento.

    Componenti signature:
    - vendor: Es. "ANGELINI"
    - codice_anomalia: Es. "ESP-A01"
    - codice_espositore: Codice prodotto parent
    - pezzi_per_unita: Pezzi attesi per unita espositore
    - fascia_scostamento: Fascia normalizzata (BASSO, MEDIO, etc.)

    Args:
        vendor: Codice vendor
        codice_anomalia: Codice tipo anomalia
        codice_espositore: Codice prodotto espositore
        pezzi_per_unita: Pezzi per unita
        fascia_scostamento: Fascia scostamento

    Returns:
        SHA256 hash troncato a 16 caratteri
    """
    # Normalizza componenti
    componenti = [
        vendor.upper().strip(),
        codice_anomalia.upper().strip(),
        codice_espositore.strip(),
        str(pezzi_per_unita),
        fascia_scostamento.upper().strip(),
    ]

    # Concatena e calcola hash
    stringa_pattern = '|'.join(componenti)
    hash_full = hashlib.sha256(stringa_pattern.encode('utf-8')).hexdigest()

    # Tronca a 16 caratteri per leggibilita
    return hash_full[:16].upper()


def normalizza_fascia_scostamento(percentuale: float) -> str:
    """
    Normalizza percentuale scostamento in fascia discreta.

    Questo permette di raggruppare scostamenti simili nello stesso pattern,
    aumentando le possibilita di apprendimento.

    Args:
        percentuale: Scostamento in percentuale (es: -12.5)

    Returns:
        Fascia normalizzata (es: "-20/-10%")
    """
    if percentuale == 0:
        return 'ZERO'

    for (low, high), label in FASCE_NORMALIZZATE.items():
        if low <= percentuale < high:
            return label

    # Fuori range
    if percentuale < -50:
        return '<-50%'
    else:
        return '>+50%'


def genera_descrizione_pattern(anomalia: Dict) -> str:
    """
    Genera descrizione leggibile del pattern.

    Args:
        anomalia: Dati anomalia

    Returns:
        Descrizione pattern
    """
    codice = anomalia.get('codice_anomalia', '')
    esp = anomalia.get('espositore_codice', '')
    pezzi_a = anomalia.get('pezzi_attesi', 0)
    pezzi_t = anomalia.get('pezzi_trovati', 0)
    fascia = anomalia.get('fascia_scostamento', '')

    return f"{codice} su espositore {esp} (attesi {pezzi_a}, trovati {pezzi_t}, fascia {fascia})"
