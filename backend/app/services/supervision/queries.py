# =============================================================================
# SERV.O v7.0 - SUPERVISION QUERIES
# =============================================================================
# Query per supervisione e storico
# =============================================================================

from typing import Dict, List

from ...database_pg import get_db


def può_emettere_tracciato(id_testata: int) -> bool:
    """
    Verifica se un ordine puo essere esportato come tracciato.

    Condizioni:
    1. Stato != PENDING_REVIEW
    2. Nessuna supervisione PENDING

    Args:
        id_testata: ID ordine

    Returns:
        True se ordine puo essere esportato
    """
    db = get_db()

    # Verifica stato ordine
    ordine = db.execute(
        "SELECT stato FROM ORDINI_TESTATA WHERE id_testata = ?",
        (id_testata,)
    ).fetchone()

    if not ordine or ordine['stato'] == 'PENDING_REVIEW':
        return False

    # Verifica supervisioni pending
    pending = db.execute("""
        SELECT COUNT(*) FROM SUPERVISIONE_ESPOSITORE
        WHERE id_testata = ? AND stato = 'PENDING'
    """, (id_testata,)).fetchone()[0]

    return pending == 0


def get_supervisioni_per_ordine(id_testata: int) -> List[Dict]:
    """
    Ritorna tutte le supervisioni per un ordine.

    Args:
        id_testata: ID ordine

    Returns:
        Lista supervisioni
    """
    db = get_db()

    rows = db.execute("""
        SELECT se.*, coe.count_approvazioni, coe.is_ordinario
        FROM SUPERVISIONE_ESPOSITORE se
        LEFT JOIN CRITERI_ORDINARI_ESPOSITORE coe
            ON se.pattern_signature = coe.pattern_signature
        WHERE se.id_testata = ?
        ORDER BY se.timestamp_creazione DESC
    """, (id_testata,)).fetchall()

    return [dict(row) for row in rows]


def get_storico_criteri_applicati(limit: int = 50) -> List[Dict]:
    """
    Ritorna storico applicazioni criteri.

    Args:
        limit: Numero massimo risultati

    Returns:
        Lista log applicazioni
    """
    db = get_db()

    rows = db.execute("""
        SELECT
            lca.*,
            coe.pattern_descrizione,
            ot.numero_ordine_vendor AS numero_ordine,
            v.codice_vendor AS vendor
        FROM LOG_CRITERI_APPLICATI lca
        LEFT JOIN CRITERI_ORDINARI_ESPOSITORE coe
            ON lca.pattern_signature = coe.pattern_signature
        LEFT JOIN ORDINI_TESTATA ot ON lca.id_testata = ot.id_testata
        LEFT JOIN VENDOR v ON ot.id_vendor = v.id_vendor
        ORDER BY lca.timestamp DESC
        LIMIT ?
    """, (limit,)).fetchall()

    return [dict(row) for row in rows]
