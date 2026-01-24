# =============================================================================
# SERV.O v9.0 - SUPERVISION BULK OPERATIONS
# =============================================================================
# Operazioni bulk per supervisioni raggruppate per pattern
# v9.0: Aggiunto supporto AIC
# =============================================================================

from typing import Dict, List, Optional

from ...database_pg import get_db, log_operation
from .decisions import approva_supervisione, rifiuta_supervisione
from .lookup import approva_supervisione_lookup, rifiuta_supervisione_lookup
from .ml import registra_approvazione_pattern, registra_approvazione_pattern_listino


def get_supervisioni_grouped_pending() -> List[Dict]:
    """
    Recupera supervisioni pending raggruppate per pattern.

    Usa la view v_supervisione_grouped_pending per aggregare
    tutte le supervisioni (espositore, listino, lookup) per pattern_signature.

    Returns:
        Lista di gruppi, ciascuno con:
        - pattern_signature
        - tipo_supervisione
        - total_count
        - affected_order_ids
        - supervision_ids
        - pattern_count (approvazioni ML)
        - pattern_ordinario
    """
    db = get_db()

    rows = db.execute("""
        SELECT * FROM v_supervisione_grouped_pending
        ORDER BY total_count DESC, first_occurrence ASC
    """).fetchall()

    return [dict(row) for row in rows]


def approva_pattern_bulk(
    pattern_signature: str,
    operatore: str,
    note: str = None
) -> Dict:
    """
    Approva TUTTE le supervisioni pending con un dato pattern.

    v10.5: Il contatore ML viene incrementato per OGNI supervisione approvata,
    non più una sola volta. Così 15 supervisioni = +15 sul contatore ML.

    Effetti:
    1. Approva ogni supervisione singolarmente
    2. Sblocca gli ordini coinvolti
    3. Incrementa il contatore pattern di N (numero supervisioni approvate)

    Args:
        pattern_signature: Signature pattern da approvare
        operatore: Username operatore
        note: Note opzionali

    Returns:
        Dict con conteggio per tipo:
        {
            "espositore": N,
            "listino": N,
            "lookup": N,
            "total": N,
            "orders_affected": [list of id_testata]
        }
    """
    db = get_db()
    results = {
        'espositore': 0,
        'listino': 0,
        'lookup': 0,
        'aic': 0,  # v9.0
        'total': 0,
        'orders_affected': set()
    }

    # 1. Trova e approva supervisioni ESPOSITORE
    esp_rows = db.execute("""
        SELECT id_supervisione, id_testata FROM supervisione_espositore
        WHERE pattern_signature = %s AND stato = 'PENDING'
    """, (pattern_signature,)).fetchall()

    for row in esp_rows:
        # Approva senza incrementare pattern (lo facciamo una volta sola dopo)
        _approva_supervisione_senza_pattern(
            'espositore',
            row['id_supervisione'],
            operatore,
            note
        )
        results['espositore'] += 1
        results['orders_affected'].add(row['id_testata'])

    # 2. Trova e approva supervisioni LISTINO
    lst_rows = db.execute("""
        SELECT id_supervisione, id_testata FROM supervisione_listino
        WHERE pattern_signature = %s AND stato = 'PENDING'
    """, (pattern_signature,)).fetchall()

    for row in lst_rows:
        _approva_supervisione_senza_pattern(
            'listino',
            row['id_supervisione'],
            operatore,
            note
        )
        results['listino'] += 1
        results['orders_affected'].add(row['id_testata'])

    # 3. Trova e approva supervisioni LOOKUP
    lkp_rows = db.execute("""
        SELECT id_supervisione, id_testata FROM supervisione_lookup
        WHERE pattern_signature = %s AND stato = 'PENDING'
    """, (pattern_signature,)).fetchall()

    for row in lkp_rows:
        _approva_supervisione_senza_pattern(
            'lookup',
            row['id_supervisione'],
            operatore,
            note
        )
        results['lookup'] += 1
        results['orders_affected'].add(row['id_testata'])

    # 4. Trova e approva supervisioni AIC (v9.0)
    aic_rows = db.execute("""
        SELECT id_supervisione, id_testata FROM supervisione_aic
        WHERE pattern_signature = %s AND stato = 'PENDING'
    """, (pattern_signature,)).fetchall()

    for row in aic_rows:
        _approva_supervisione_senza_pattern(
            'aic',
            row['id_supervisione'],
            operatore,
            note
        )
        results['aic'] += 1
        results['orders_affected'].add(row['id_testata'])

    results['total'] = results['espositore'] + results['listino'] + results['lookup'] + results['aic']
    results['orders_affected'] = list(results['orders_affected'])

    # v10.5: Incrementa pattern per OGNI supervisione approvata
    if results['total'] > 0:
        _incrementa_pattern_per_bulk(pattern_signature, operatore, results['total'])

    # 5. Sblocca tutti gli ordini coinvolti
    from .requests import sblocca_ordine_se_completo
    for id_testata in results['orders_affected']:
        sblocca_ordine_se_completo(id_testata)

    # Log operazione bulk
    log_operation(
        'APPROVA_PATTERN_BULK',
        'SUPERVISIONE',
        None,
        f"Pattern {pattern_signature}: approvate {results['total']} supervisioni "
        f"({results['espositore']} ESP, {results['listino']} LST, {results['lookup']} LKP, {results['aic']} AIC), "
        f"{len(results['orders_affected'])} ordini sbloccati",
        operatore=operatore
    )

    return results


def rifiuta_pattern_bulk(
    pattern_signature: str,
    operatore: str,
    note: str
) -> Dict:
    """
    Rifiuta TUTTE le supervisioni pending con un dato pattern.

    Effetti:
    1. Rifiuta ogni supervisione singolarmente
    2. Reset del pattern ML a 0

    Args:
        pattern_signature: Signature pattern da rifiutare
        operatore: Username operatore
        note: Motivo rifiuto (obbligatorio)

    Returns:
        Dict con conteggio per tipo
    """
    db = get_db()
    results = {
        'espositore': 0,
        'listino': 0,
        'lookup': 0,
        'aic': 0,  # v9.0
        'total': 0,
        'orders_affected': set()
    }

    # 1. Rifiuta supervisioni ESPOSITORE
    esp_rows = db.execute("""
        SELECT id_supervisione, id_testata FROM supervisione_espositore
        WHERE pattern_signature = %s AND stato = 'PENDING'
    """, (pattern_signature,)).fetchall()

    for row in esp_rows:
        _rifiuta_supervisione_senza_reset(
            'espositore',
            row['id_supervisione'],
            operatore,
            note
        )
        results['espositore'] += 1
        results['orders_affected'].add(row['id_testata'])

    # 2. Rifiuta supervisioni LISTINO
    lst_rows = db.execute("""
        SELECT id_supervisione, id_testata FROM supervisione_listino
        WHERE pattern_signature = %s AND stato = 'PENDING'
    """, (pattern_signature,)).fetchall()

    for row in lst_rows:
        _rifiuta_supervisione_senza_reset(
            'listino',
            row['id_supervisione'],
            operatore,
            note
        )
        results['listino'] += 1
        results['orders_affected'].add(row['id_testata'])

    # 3. Rifiuta supervisioni LOOKUP
    lkp_rows = db.execute("""
        SELECT id_supervisione, id_testata FROM supervisione_lookup
        WHERE pattern_signature = %s AND stato = 'PENDING'
    """, (pattern_signature,)).fetchall()

    for row in lkp_rows:
        _rifiuta_supervisione_senza_reset(
            'lookup',
            row['id_supervisione'],
            operatore,
            note
        )
        results['lookup'] += 1
        results['orders_affected'].add(row['id_testata'])

    # 4. Rifiuta supervisioni AIC (v9.0)
    aic_rows = db.execute("""
        SELECT id_supervisione, id_testata FROM supervisione_aic
        WHERE pattern_signature = %s AND stato = 'PENDING'
    """, (pattern_signature,)).fetchall()

    for row in aic_rows:
        _rifiuta_supervisione_senza_reset(
            'aic',
            row['id_supervisione'],
            operatore,
            note
        )
        results['aic'] += 1
        results['orders_affected'].add(row['id_testata'])

    results['total'] = results['espositore'] + results['listino'] + results['lookup'] + results['aic']
    results['orders_affected'] = list(results['orders_affected'])

    # 5. Reset pattern UNA SOLA VOLTA
    if results['total'] > 0:
        _reset_pattern_una_volta(pattern_signature)

    # 5. Sblocca ordini (il rifiuto sblocca comunque)
    from .requests import sblocca_ordine_se_completo
    for id_testata in results['orders_affected']:
        sblocca_ordine_se_completo(id_testata)

    log_operation(
        'RIFIUTA_PATTERN_BULK',
        'SUPERVISIONE',
        None,
        f"Pattern {pattern_signature}: rifiutate {results['total']} supervisioni, "
        f"motivo: {note}",
        operatore=operatore
    )

    return results


def _approva_supervisione_senza_pattern(
    tipo: str,
    id_supervisione: int,
    operatore: str,
    note: str = None
):
    """
    Approva supervisione SENZA incrementare il pattern.
    Usato internamente per bulk approval.
    """
    db = get_db()

    if tipo == 'espositore':
        db.execute("""
            UPDATE supervisione_espositore
            SET stato = 'APPROVED',
                operatore = %s,
                timestamp_decisione = CURRENT_TIMESTAMP,
                note = COALESCE(note, '') || %s
            WHERE id_supervisione = %s
        """, (operatore, f" [BULK] {note or ''}", id_supervisione))

    elif tipo == 'listino':
        db.execute("""
            UPDATE supervisione_listino
            SET stato = 'APPROVED',
                operatore = %s,
                timestamp_decisione = CURRENT_TIMESTAMP,
                note = COALESCE(note, '') || %s
            WHERE id_supervisione = %s
        """, (operatore, f" [BULK] {note or ''}", id_supervisione))

    elif tipo == 'lookup':
        db.execute("""
            UPDATE supervisione_lookup
            SET stato = 'APPROVED',
                operatore = %s,
                timestamp_decisione = CURRENT_TIMESTAMP,
                note = COALESCE(note, '') || %s
            WHERE id_supervisione = %s
        """, (operatore, f" [BULK] {note or ''}", id_supervisione))

    elif tipo == 'aic':  # v9.0
        db.execute("""
            UPDATE supervisione_aic
            SET stato = 'APPROVED',
                operatore = %s,
                timestamp_decisione = CURRENT_TIMESTAMP,
                note = COALESCE(note, '') || %s
            WHERE id_supervisione = %s
        """, (operatore, f" [BULK] {note or ''}", id_supervisione))

    db.commit()


def _rifiuta_supervisione_senza_reset(
    tipo: str,
    id_supervisione: int,
    operatore: str,
    note: str
):
    """
    Rifiuta supervisione SENZA resettare il pattern.
    Usato internamente per bulk rejection.
    """
    db = get_db()

    if tipo == 'espositore':
        db.execute("""
            UPDATE supervisione_espositore
            SET stato = 'REJECTED',
                operatore = %s,
                timestamp_decisione = CURRENT_TIMESTAMP,
                note = %s
            WHERE id_supervisione = %s
        """, (operatore, f"[BULK] {note}", id_supervisione))

    elif tipo == 'listino':
        db.execute("""
            UPDATE supervisione_listino
            SET stato = 'REJECTED',
                operatore = %s,
                timestamp_decisione = CURRENT_TIMESTAMP,
                note = %s
            WHERE id_supervisione = %s
        """, (operatore, f"[BULK] {note}", id_supervisione))

    elif tipo == 'lookup':
        db.execute("""
            UPDATE supervisione_lookup
            SET stato = 'REJECTED',
                operatore = %s,
                timestamp_decisione = CURRENT_TIMESTAMP,
                note = %s
            WHERE id_supervisione = %s
        """, (operatore, f"[BULK] {note}", id_supervisione))

    elif tipo == 'aic':  # v9.0
        db.execute("""
            UPDATE supervisione_aic
            SET stato = 'REJECTED',
                operatore = %s,
                timestamp_decisione = CURRENT_TIMESTAMP,
                note = %s
            WHERE id_supervisione = %s
        """, (operatore, f"[BULK] {note}", id_supervisione))

    db.commit()


def _incrementa_pattern_per_bulk(pattern_signature: str, operatore: str, count: int = 1):
    """
    v10.5: Incrementa contatore pattern per il numero di supervisioni approvate.

    Args:
        pattern_signature: Firma del pattern
        operatore: Username operatore
        count: Numero di supervisioni approvate (default 1)
    """
    from .constants import SOGLIA_PROMOZIONE
    db = get_db()

    # Prova su criteri_ordinari_espositore
    result = db.execute("""
        UPDATE criteri_ordinari_espositore
        SET count_approvazioni = count_approvazioni + %s,
            operatori_approvatori = COALESCE(operatori_approvatori || ', ', '') || %s
        WHERE pattern_signature = %s
        RETURNING count_approvazioni
    """, (count, f"{operatore}(x{count})", pattern_signature)).fetchone()

    if result:
        if result[0] >= SOGLIA_PROMOZIONE:
            db.execute("""
                UPDATE criteri_ordinari_espositore
                SET is_ordinario = TRUE, data_promozione = CURRENT_TIMESTAMP
                WHERE pattern_signature = %s AND is_ordinario = FALSE
            """, (pattern_signature,))
        db.commit()
        return

    # Prova su criteri_ordinari_listino
    result = db.execute("""
        UPDATE criteri_ordinari_listino
        SET count_approvazioni = count_approvazioni + %s,
            operatori_approvatori = COALESCE(operatori_approvatori || ', ', '') || %s
        WHERE pattern_signature = %s
        RETURNING count_approvazioni
    """, (count, f"{operatore}(x{count})", pattern_signature)).fetchone()

    if result:
        if result[0] >= SOGLIA_PROMOZIONE:
            db.execute("""
                UPDATE criteri_ordinari_listino
                SET is_ordinario = TRUE, data_promozione = CURRENT_TIMESTAMP
                WHERE pattern_signature = %s AND is_ordinario = FALSE
            """, (pattern_signature,))
        db.commit()
        return

    # Prova su criteri_ordinari_lookup
    result = db.execute("""
        UPDATE criteri_ordinari_lookup
        SET count_approvazioni = count_approvazioni + %s,
            operatori_approvatori = COALESCE(operatori_approvatori || ', ', '') || %s
        WHERE pattern_signature = %s
        RETURNING count_approvazioni
    """, (count, f"{operatore}(x{count})", pattern_signature)).fetchone()

    if result:
        if result[0] >= SOGLIA_PROMOZIONE:
            db.execute("""
                UPDATE criteri_ordinari_lookup
                SET is_ordinario = TRUE, data_promozione = CURRENT_TIMESTAMP
                WHERE pattern_signature = %s AND is_ordinario = FALSE
            """, (pattern_signature,))
        db.commit()
        return

    # v9.0: Prova su criteri_ordinari_aic
    result = db.execute("""
        UPDATE criteri_ordinari_aic
        SET count_approvazioni = count_approvazioni + %s,
            operatori_approvatori = COALESCE(operatori_approvatori || ', ', '') || %s
        WHERE pattern_signature = %s
        RETURNING count_approvazioni
    """, (count, f"{operatore}(x{count})", pattern_signature)).fetchone()

    if result:
        if result[0] >= SOGLIA_PROMOZIONE:
            db.execute("""
                UPDATE criteri_ordinari_aic
                SET is_ordinario = TRUE, data_promozione = CURRENT_TIMESTAMP
                WHERE pattern_signature = %s AND is_ordinario = FALSE
            """, (pattern_signature,))
        db.commit()


def _reset_pattern_una_volta(pattern_signature: str):
    """
    Resetta contatore pattern in tutte le tabelle criteri.
    Chiamato una sola volta per bulk rejection.
    """
    db = get_db()

    # Reset in tutte le tabelle (solo una avra effetto)
    db.execute("""
        UPDATE criteri_ordinari_espositore
        SET count_approvazioni = 0, is_ordinario = FALSE, data_promozione = NULL
        WHERE pattern_signature = %s
    """, (pattern_signature,))

    db.execute("""
        UPDATE criteri_ordinari_listino
        SET count_approvazioni = 0, is_ordinario = FALSE, data_promozione = NULL
        WHERE pattern_signature = %s
    """, (pattern_signature,))

    db.execute("""
        UPDATE criteri_ordinari_lookup
        SET count_approvazioni = 0, is_ordinario = FALSE, data_promozione = NULL
        WHERE pattern_signature = %s
    """, (pattern_signature,))

    # v9.0: Reset AIC pattern
    db.execute("""
        UPDATE criteri_ordinari_aic
        SET count_approvazioni = 0, is_ordinario = FALSE, data_promozione = NULL
        WHERE pattern_signature = %s
    """, (pattern_signature,))

    db.commit()

    log_operation(
        'RESET_PATTERN_BULK',
        'SUPERVISIONE',
        None,
        f"Pattern {pattern_signature} resettato dopo rifiuto bulk"
    )
