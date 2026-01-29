# =============================================================================
# SERV.O v11.4 - AIC QUERIES
# =============================================================================
# Funzioni di query e contatori per AIC
# =============================================================================

from typing import Dict, List

from ....database_pg import get_db


def conta_anomalie_aic_aperte() -> int:
    """Conta anomalie AIC ancora aperte."""
    db = get_db()
    row = db.execute("""
        SELECT COUNT(*) AS cnt
        FROM anomalie
        WHERE codice_anomalia = 'AIC-A01' AND stato = 'APERTA'
    """).fetchone()
    return row['cnt'] if row else 0


def conta_supervisioni_aic_pending() -> int:
    """Conta supervisioni AIC ancora pending."""
    db = get_db()
    row = db.execute("""
        SELECT COUNT(*) AS cnt
        FROM supervisione_aic
        WHERE stato = 'PENDING'
    """).fetchone()
    return row['cnt'] if row else 0


def search_aic_suggestions(descrizione: str, vendor: str = None, limit: int = 10) -> List[Dict]:
    """
    Cerca suggerimenti AIC basati sulla descrizione prodotto.
    Usa listini_vendor per trovare corrispondenze.

    Args:
        descrizione: Descrizione prodotto da cercare
        vendor: Filtro vendor opzionale
        limit: Numero massimo risultati

    Returns:
        Lista di {codice_aic, descrizione, vendor, prezzo}
    """
    db = get_db()

    desc_pattern = f"%{descrizione.upper()}%"

    query = """
        SELECT DISTINCT
            codice_aic,
            descrizione,
            vendor,
            prezzo_netto
        FROM listini_vendor
        WHERE UPPER(descrizione) LIKE %s
          AND codice_aic IS NOT NULL
          AND LENGTH(codice_aic) = 9
    """
    params = [desc_pattern]

    if vendor:
        query += " AND vendor = %s"
        params.append(vendor)

    query += " ORDER BY descrizione LIMIT %s"
    params.append(limit)

    rows = db.execute(query, params).fetchall()

    return [dict(r) for r in rows]


def get_storico_modifiche_aic(
    limit: int = 100,
    codice_aic: str = None,
    operatore_filter: str = None
) -> List[Dict]:
    """
    Recupera storico modifiche AIC dalla tabella audit.

    Args:
        limit: Numero massimo di record
        codice_aic: Filtra per codice AIC specifico
        operatore_filter: Filtra per operatore

    Returns:
        Lista di modifiche con dettagli
    """
    db = get_db()

    query = """
        SELECT
            am.id_modifica,
            am.timestamp,
            am.entita,
            am.id_entita,
            am.campo_modificato,
            am.valore_precedente,
            am.valore_nuovo,
            am.fonte_modifica,
            am.id_testata,
            am.username_operatore,
            am.motivazione,
            od.descrizione,
            ot.numero_ordine_vendor
        FROM audit_modifiche am
        LEFT JOIN ordini_dettaglio od ON am.id_entita = od.id_dettaglio
        LEFT JOIN ordini_testata ot ON am.id_testata = ot.id_testata
        WHERE am.campo_modificato = 'codice_aic'
    """
    params = []

    if codice_aic:
        query += " AND (am.valore_precedente = %s OR am.valore_nuovo = %s)"
        params.extend([codice_aic, codice_aic])

    if operatore_filter:
        query += " AND am.username_operatore = %s"
        params.append(operatore_filter)

    query += " ORDER BY am.timestamp DESC LIMIT %s"
    params.append(limit)

    rows = db.execute(query, params).fetchall()
    return [dict(r) for r in rows]
