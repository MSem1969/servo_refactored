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
    1. Stato != PENDING_REVIEW e != ANOMALIA
    2. Nessuna supervisione PENDING (su tutte le tabelle)
    3. Nessuna anomalia bloccante aperta (ERRORE, CRITICO)

    Args:
        id_testata: ID ordine

    Returns:
        True se ordine puo essere esportato
    """
    db = get_db()

    # Verifica stato ordine
    ordine = db.execute(
        "SELECT stato FROM ORDINI_TESTATA WHERE id_testata = %s",
        (id_testata,)
    ).fetchone()

    if not ordine or ordine['stato'] in ('PENDING_REVIEW', 'ANOMALIA'):
        return False

    # v11.4: Verifica supervisioni pending su TUTTE le tabelle (inclusa prezzo)
    pending = db.execute("""
        SELECT
            (SELECT COUNT(*) FROM supervisione_espositore WHERE id_testata = %s AND stato = 'PENDING') +
            (SELECT COUNT(*) FROM supervisione_listino WHERE id_testata = %s AND stato = 'PENDING') +
            (SELECT COUNT(*) FROM supervisione_lookup WHERE id_testata = %s AND stato = 'PENDING') +
            (SELECT COUNT(*) FROM supervisione_aic WHERE id_testata = %s AND stato = 'PENDING') +
            (SELECT COUNT(*) FROM supervisione_prezzo WHERE id_testata = %s AND stato = 'PENDING') as total
    """, (id_testata, id_testata, id_testata, id_testata, id_testata)).fetchone()

    if pending and pending['total'] > 0:
        return False

    # v10.4: Verifica anomalie bloccanti aperte
    anomalie_aperte = db.execute("""
        SELECT COUNT(*) as cnt FROM anomalie
        WHERE id_testata = %s
        AND stato IN ('APERTA', 'IN_GESTIONE')
        AND livello IN ('ERRORE', 'CRITICO')
    """, (id_testata,)).fetchone()

    if anomalie_aperte and anomalie_aperte['cnt'] > 0:
        return False

    return True


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
