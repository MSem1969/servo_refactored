# =============================================================================
# SERV.O v7.0 - SUPERVISION MACHINE LEARNING
# =============================================================================
# Gestione pattern ML e criteri ordinari per espositore e listino
# =============================================================================

import hashlib
from typing import Dict, Optional, Tuple

from ...database_pg import get_db, log_operation
from .constants import SOGLIA_PROMOZIONE
from .patterns import (
    calcola_pattern_signature,
    normalizza_fascia_scostamento,
    genera_descrizione_pattern,
)


def _calcola_pattern_signature_listino(vendor: str, codice_anomalia: str, codice_aic: str) -> str:
    """
    Calcola signature univoca per pattern listino.
    Pattern: VENDOR|CODICE_ANOMALIA|AIC
    """
    raw = f"{vendor}|{codice_anomalia}|{codice_aic or 'NO_AIC'}"
    return hashlib.md5(raw.encode()).hexdigest()[:16]


def _assicura_pattern_esistente(pattern_signature: str, anomalia: Dict):
    """
    Assicura che un pattern esista nella tabella criteri.

    Se non esiste, lo crea con count_approvazioni = 0.

    Args:
        pattern_signature: Signature pattern
        anomalia: Dati anomalia per metadati
    """
    db = get_db()

    existing = db.execute(
        "SELECT 1 FROM CRITERI_ORDINARI_ESPOSITORE WHERE pattern_signature = ?",
        (pattern_signature,)
    ).fetchone()

    if not existing:
        db.execute("""
            INSERT INTO CRITERI_ORDINARI_ESPOSITORE
            (pattern_signature, pattern_descrizione, vendor, codice_anomalia,
             codice_espositore, pezzi_per_unita, tipo_scostamento, fascia_scostamento)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            pattern_signature,
            genera_descrizione_pattern(anomalia),
            'ANGELINI',
            anomalia.get('codice_anomalia', ''),
            anomalia.get('espositore_codice', ''),
            anomalia.get('pezzi_attesi', 0),
            'DIFETTO' if anomalia.get('pezzi_trovati', 0) < anomalia.get('pezzi_attesi', 0) else 'ECCESSO',
            anomalia.get('fascia_scostamento', ''),
        ))
        db.commit()


def registra_approvazione_pattern(pattern_signature: str, operatore: str):
    """
    Registra approvazione per un pattern.

    Incrementa contatore e, se raggiunta soglia, promuove a ordinario.

    Args:
        pattern_signature: Signature pattern
        operatore: Username operatore
    """
    db = get_db()

    # Incrementa contatore
    db.execute("""
        UPDATE CRITERI_ORDINARI_ESPOSITORE
        SET count_approvazioni = count_approvazioni + 1,
            operatori_approvatori = COALESCE(operatori_approvatori || ', ', '') || ?
        WHERE pattern_signature = ?
    """, (operatore, pattern_signature))

    # Verifica promozione
    row = db.execute(
        "SELECT count_approvazioni FROM CRITERI_ORDINARI_ESPOSITORE WHERE pattern_signature = ?",
        (pattern_signature,)
    ).fetchone()

    if row and row[0] >= SOGLIA_PROMOZIONE:
        # Promuovi a ordinario
        db.execute("""
            UPDATE CRITERI_ORDINARI_ESPOSITORE
            SET is_ordinario = TRUE, data_promozione = datetime('now')
            WHERE pattern_signature = ? AND is_ordinario = FALSE
        """, (pattern_signature,))

        log_operation(
            'PROMOZIONE_PATTERN',
            'CRITERI_ORDINARI_ESPOSITORE',
            None,
            f"Pattern {pattern_signature} promosso a ordinario dopo {SOGLIA_PROMOZIONE} approvazioni"
        )

    db.commit()


def registra_rifiuto_pattern(pattern_signature: str):
    """
    Registra rifiuto per un pattern.

    Reset contatore approvazioni a 0 (un rifiuto invalida apprendimento).
    Supporta pattern espositore, listino, lookup e aic.

    Args:
        pattern_signature: Signature pattern
    """
    db = get_db()

    # Reset espositore
    db.execute("""
        UPDATE criteri_ordinari_espositore
        SET count_approvazioni = 0,
            is_ordinario = FALSE,
            data_promozione = NULL
        WHERE pattern_signature = %s
    """, (pattern_signature,))

    # Reset listino
    db.execute("""
        UPDATE criteri_ordinari_listino
        SET count_approvazioni = 0,
            is_ordinario = FALSE,
            data_promozione = NULL
        WHERE pattern_signature = %s
    """, (pattern_signature,))

    # Reset lookup
    db.execute("""
        UPDATE criteri_ordinari_lookup
        SET count_approvazioni = 0,
            is_ordinario = FALSE,
            data_promozione = NULL
        WHERE pattern_signature = %s
    """, (pattern_signature,))

    # v11.3: Reset AIC
    db.execute("""
        UPDATE criteri_ordinari_aic
        SET count_approvazioni = 0,
            is_ordinario = FALSE,
            data_promozione = NULL
        WHERE pattern_signature = %s
    """, (pattern_signature,))

    db.commit()

    log_operation(
        'RESET_PATTERN',
        'CRITERI_ORDINARI',
        None,
        f"Pattern {pattern_signature} resettato dopo rifiuto"
    )


def verifica_pattern_ordinario(pattern_signature: str) -> bool:
    """
    Verifica se un pattern espositore e stato promosso a ordinario.

    Args:
        pattern_signature: Signature pattern

    Returns:
        True se pattern e ordinario (applicabile automaticamente)
    """
    db = get_db()

    row = db.execute("""
        SELECT is_ordinario FROM CRITERI_ORDINARI_ESPOSITORE
        WHERE pattern_signature = ? AND is_ordinario = TRUE
    """, (pattern_signature,)).fetchone()

    return row is not None


def verifica_pattern_listino_ordinario(pattern_signature: str) -> bool:
    """
    Verifica se un pattern listino e stato promosso a ordinario.

    Args:
        pattern_signature: Signature pattern listino

    Returns:
        True se pattern e ordinario (applicabile automaticamente)
    """
    db = get_db()

    row = db.execute("""
        SELECT is_ordinario FROM CRITERI_ORDINARI_LISTINO
        WHERE pattern_signature = ? AND is_ordinario = TRUE
    """, (pattern_signature,)).fetchone()

    return row is not None


def registra_approvazione_pattern_listino(pattern_signature: str, operatore: str):
    """
    Registra approvazione per un pattern listino.

    Incrementa contatore e, se raggiunta soglia, promuove a ordinario.

    Args:
        pattern_signature: Signature pattern
        operatore: Username operatore
    """
    db = get_db()

    # Incrementa contatore
    db.execute("""
        UPDATE CRITERI_ORDINARI_LISTINO
        SET count_approvazioni = count_approvazioni + 1,
            operatori_approvatori = COALESCE(operatori_approvatori || ', ', '') || ?
        WHERE pattern_signature = ?
    """, (operatore, pattern_signature))

    # Verifica promozione
    row = db.execute(
        "SELECT count_approvazioni FROM CRITERI_ORDINARI_LISTINO WHERE pattern_signature = ?",
        (pattern_signature,)
    ).fetchone()

    if row and row[0] >= SOGLIA_PROMOZIONE:
        # Promuovi a ordinario
        db.execute("""
            UPDATE CRITERI_ORDINARI_LISTINO
            SET is_ordinario = TRUE, data_promozione = datetime('now')
            WHERE pattern_signature = ? AND is_ordinario = FALSE
        """, (pattern_signature,))

        log_operation(
            'PROMOZIONE_PATTERN',
            'CRITERI_ORDINARI_LISTINO',
            None,
            f"Pattern listino {pattern_signature} promosso a ordinario dopo {SOGLIA_PROMOZIONE} approvazioni"
        )

    db.commit()


def valuta_anomalia_con_apprendimento(
    id_testata: int,
    anomalia: Dict
) -> Tuple[bool, Optional[str]]:
    """
    Valuta anomalia usando criteri appresi.

    Se pattern e ordinario (>= 5 approvazioni), applica automaticamente
    senza richiedere supervisione umana.

    Gestisce sia anomalie espositore (ESP-*) che listino (LST-*).

    Args:
        id_testata: ID ordine
        anomalia: Dati anomalia

    Returns:
        Tuple (applicato_auto, pattern_signature)
        - applicato_auto: True se gestito automaticamente
        - pattern_signature: Signature per riferimento
    """
    tipo_anomalia = anomalia.get('tipo_anomalia') or ''
    codice_anomalia = anomalia.get('codice_anomalia') or ''

    # Rileva se anomalia listino
    if tipo_anomalia == 'LISTINO' or codice_anomalia.startswith('LST-'):
        return _valuta_anomalia_listino(id_testata, anomalia)
    else:
        return _valuta_anomalia_espositore(id_testata, anomalia)


def _valuta_anomalia_listino(
    id_testata: int,
    anomalia: Dict
) -> Tuple[bool, Optional[str]]:
    """
    Valuta anomalia listino usando criteri appresi.
    """
    vendor = anomalia.get('vendor', 'UNKNOWN')
    codice_aic = anomalia.get('valore_anomalo', '')
    codice_anomalia = anomalia.get('codice_anomalia', '')

    pattern_sig = _calcola_pattern_signature_listino(vendor, codice_anomalia, codice_aic)

    # Verifica se ordinario
    if verifica_pattern_listino_ordinario(pattern_sig):
        # Applica automaticamente
        log_criterio_applicato(
            id_testata=id_testata,
            id_dettaglio=None,
            pattern_signature=pattern_sig,
            automatico=True,
            operatore='SISTEMA'
        )

        log_operation(
            'APPLICA_CRITERIO_AUTO',
            'ORDINI_TESTATA',
            id_testata,
            f"Criterio listino ordinario {pattern_sig} applicato automaticamente"
        )

        return True, pattern_sig

    # Pattern non ordinario: richiede supervisione
    return False, pattern_sig


def _valuta_anomalia_espositore(
    id_testata: int,
    anomalia: Dict
) -> Tuple[bool, Optional[str]]:
    """
    Valuta anomalia espositore usando criteri appresi.
    """
    # Calcola pattern
    pezzi_attesi = anomalia.get('pezzi_attesi', 0)
    pezzi_trovati = anomalia.get('pezzi_trovati', 0)

    if pezzi_attesi > 0:
        scostamento_pct = ((pezzi_trovati - pezzi_attesi) / pezzi_attesi) * 100
    else:
        scostamento_pct = 0

    fascia_norm = normalizza_fascia_scostamento(scostamento_pct)

    pattern_sig = calcola_pattern_signature(
        vendor='ANGELINI',
        codice_anomalia=anomalia.get('codice_anomalia', ''),
        codice_espositore=anomalia.get('espositore_codice', ''),
        pezzi_per_unita=pezzi_attesi,
        fascia_scostamento=fascia_norm
    )

    # Verifica se ordinario
    if verifica_pattern_ordinario(pattern_sig):
        # Applica automaticamente
        log_criterio_applicato(
            id_testata=id_testata,
            id_dettaglio=None,
            pattern_signature=pattern_sig,
            automatico=True,
            operatore='SISTEMA'
        )

        log_operation(
            'APPLICA_CRITERIO_AUTO',
            'ORDINI_TESTATA',
            id_testata,
            f"Criterio ordinario {pattern_sig} applicato automaticamente"
        )

        return True, pattern_sig

    # Pattern non ordinario: richiede supervisione
    return False, pattern_sig


def log_criterio_applicato(
    id_testata: int,
    id_dettaglio: Optional[int],
    pattern_signature: str,
    automatico: bool = True,
    operatore: str = 'SISTEMA'
):
    """
    Registra applicazione criterio per audit trail.

    Args:
        id_testata: ID ordine
        id_dettaglio: ID dettaglio (opzionale)
        pattern_signature: Pattern applicato
        automatico: True se applicato automaticamente
        operatore: Username operatore
    """
    db = get_db()

    db.execute("""
        INSERT INTO LOG_CRITERI_APPLICATI
        (id_testata, id_dettaglio, pattern_signature, applicato_automaticamente, operatore)
        VALUES (?, ?, ?, ?, ?)
    """, (id_testata, id_dettaglio, pattern_signature, 1 if automatico else 0, operatore))

    db.commit()
