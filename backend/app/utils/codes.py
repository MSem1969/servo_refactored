# =============================================================================
# SERV.O v7.0 - UTILS/CODES
# =============================================================================
# Funzioni per normalizzazione codici (AIC, P.IVA)
# =============================================================================

import re
from typing import Tuple


def normalize_aic_simple(codice: str) -> str:
    """
    Estrae codice AIC SENZA normalizzazione (v9.1).

    IMPORTANTE: Il codice viene mantenuto esattamente come estratto.
    Solo i caratteri non numerici vengono rimossi.
    La validazione (9 cifre esatte) avviene come anomalia AIC-A01.

    Args:
        codice: Codice AIC originale

    Returns:
        AIC con solo cifre (lunghezza originale, no padding)
    """
    codice = str(codice).strip() if codice else ''
    codice_num = re.sub(r'[^\d]', '', codice)

    # RIMOSSO: Normalizzazione/padding a 9 cifre
    # Il codice rimane esattamente come estratto
    return codice_num


def normalize_aic(codice: str, descrizione: str = '') -> Tuple[str, str, bool, bool]:
    """
    Estrae codice AIC SENZA normalizzazione con rilevamento espositore (v9.1).

    IMPORTANTE: Il codice viene mantenuto esattamente come estratto.
    La validazione (9 cifre esatte) avviene come anomalia AIC-A01.

    Args:
        codice: Codice AIC originale
        descrizione: Descrizione prodotto (per rilevare espositore)

    Returns:
        Tuple (aic_estratto, aic_originale, is_espositore, is_child)
    """
    codice = str(codice).strip() if codice else ''
    aic_orig = codice
    is_espositore = False
    is_child = False

    # Rileva espositore da codice o descrizione
    esp_pattern = r'(ESP|EXP|BANCO|EXPO)'
    if re.search(esp_pattern, codice.upper()) or \
       re.search(esp_pattern, descrizione.upper()):
        is_espositore = True

    # Estrae solo cifre - NESSUN PADDING
    aic_extracted = normalize_aic_simple(codice)

    return aic_extracted, aic_orig, is_espositore, is_child


def normalize_piva(piva: str) -> str:
    """
    Normalizza P.IVA rimuovendo zeri iniziali per confronto robusto.

    Args:
        piva: P.IVA originale

    Returns:
        P.IVA senza zeri iniziali (o '0' se solo zeri)
    """
    if not piva:
        return ''

    # Rimuovi caratteri non numerici
    piva_clean = re.sub(r'[^\d]', '', str(piva).strip())

    if not piva_clean:
        return ''

    # Rimuovi zeri iniziali per confronto robusto
    return piva_clean.lstrip('0') or '0'


def format_piva(piva: str) -> str:
    """
    Formatta P.IVA come stringa di 11 caratteri con zeri iniziali.

    Se la P.IVA è più corta di 11 cifre, aggiunge zeri iniziali.
    Se più lunga, tronca a 11 cifre.
    Preserva gli zeri iniziali presenti nel documento.

    Args:
        piva: P.IVA originale (può essere con o senza zeri iniziali)

    Returns:
        P.IVA formattata a 11 cifre con padding di zeri iniziali
    """
    if not piva:
        return ''

    # Rimuovi caratteri non numerici
    piva_clean = re.sub(r'[^\d]', '', str(piva).strip())

    if not piva_clean:
        return ''

    # Normalizza a 11 cifre con padding di zeri iniziali
    if len(piva_clean) < 11:
        return piva_clean.zfill(11)
    elif len(piva_clean) > 11:
        return piva_clean[:11]

    return piva_clean


def is_valid_piva(piva: str) -> bool:
    """Verifica se P.IVA ha formato valido (11 cifre)."""
    if not piva:
        return False
    piva_clean = re.sub(r'[^\d]', '', str(piva))
    return len(piva_clean) == 11


def is_valid_aic(aic: str) -> bool:
    """Verifica se codice AIC ha formato valido.

    9 caratteri: 1a posizione alfanumerica, le altre 8 numeriche
    (es. 900234567 oppure A00345891).
    """
    if not aic:
        return False
    aic_clean = str(aic).strip().upper()
    return bool(re.match(r'^[A-Z0-9][0-9]{8}$', aic_clean))


# =============================================================================
# CODICE MINISTERIALE: FARMACIA vs PARAFARMACIA
# =============================================================================
# Tolti gli zeri iniziali, il codice di una farmacia e quello di una
# parafarmacia possono coincidere (farmacia 14706 / parafarmacia 014706): sono
# due clienti diversi, con P.IVA e deposito diversi. Il tipo si riconosce dalla
# lunghezza del codice: la parafarmacia ha sempre 6 cifre (codice_sito), la
# farmacia ne ha 9 nell'anagrafica ministeriale e fino a 5 in anagrafica_clienti.

LUNGHEZZA_CODICE_PARAFARMACIA = 6


def is_codice_parafarmacia(codice: str) -> bool:
    """True se il codice e' di una parafarmacia (6 caratteri)."""
    return len(str(codice or '').strip()) == LUNGHEZZA_CODICE_PARAFARMACIA


def codice_cliente_canonico(codice: str, is_parafarmacia: bool = None) -> str:
    """
    Codice nella forma in cui lo salva anagrafica_clienti, senza perdere il tipo:
    farmacia senza zeri iniziali, parafarmacia a 6 cifre.

    Es: "000014706" -> "14706", "014706" -> "014706", "14706" -> "14706".
    Se il tipo e' noto dal chiamante (lookup su farmacia o parafarmacia),
    passarlo: vince sulla lunghezza.
    """
    raw = str(codice or '').strip()
    if not raw:
        return ''
    if is_parafarmacia is None:
        is_parafarmacia = is_codice_parafarmacia(raw)
    chiave = raw.lstrip('0') or '0'
    return chiave.zfill(LUNGHEZZA_CODICE_PARAFARMACIA) if is_parafarmacia else chiave


def filtro_min_id_cliente(codice: str, is_parafarmacia: bool = None,
                          colonna: str = 'min_id') -> Tuple[str, list]:
    """
    Condizione SQL che trova in anagrafica_clienti i soli clienti del tipo giusto.

    Sostituisce `LTRIM(min_id, '0') = %s`, che metteva insieme farmacia e
    parafarmacia omonime e ne restituiva una a caso.

    Returns:
        (frammento SQL con un placeholder %s, lista parametri)
    """
    canonico = codice_cliente_canonico(codice, is_parafarmacia)
    lunghezza = ("= %d" % LUNGHEZZA_CODICE_PARAFARMACIA
                 if is_codice_parafarmacia(canonico) else "<= 5")
    sql = (f"(length(trim({colonna})) {lunghezza} "
           f"AND LTRIM(trim({colonna}), '0') = %s)")
    return sql, [canonico.lstrip('0') or '0']
