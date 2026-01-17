# =============================================================================
# SERV.O v10.1 - ANOMALIES QUERIES
# =============================================================================
# Query functions for anomaly retrieval
# =============================================================================

from typing import Dict, Any, List, Optional
from ...database_pg import get_db


def get_anomalie(
    tipo: str = None,
    stato: str = None,
    livello: str = None,
    id_testata: int = None,
    limit: int = 100,
    offset: int = 0
) -> Dict[str, Any]:
    """
    Ritorna lista anomalie con filtri opzionali.

    Args:
        tipo: Filtra per tipo (LOOKUP, ESPOSITORE, LISTINO, etc.)
        stato: Filtra per stato (APERTA, IN_GESTIONE, RISOLTA, IGNORATA)
        livello: Filtra per livello (INFO, ATTENZIONE, ERRORE, CRITICO)
        id_testata: Filtra per ordine
        limit: Max risultati
        offset: Offset paginazione

    Returns:
        Dict con 'anomalie' (lista) e 'totale' (count)
    """
    db = get_db()

    conditions = []
    params = []

    if tipo:
        conditions.append("a.tipo_anomalia = %s")
        params.append(tipo)

    if stato:
        conditions.append("a.stato = %s")
        params.append(stato)
    else:
        # Default: solo anomalie aperte/in gestione
        conditions.append("a.stato IN ('APERTA', 'IN_GESTIONE')")

    if livello:
        conditions.append("a.livello = %s")
        params.append(livello)

    if id_testata:
        conditions.append("a.id_testata = %s")
        params.append(id_testata)

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    # Count totale
    count_query = f"""
        SELECT COUNT(*) FROM anomalie a
        WHERE {where_clause}
    """
    totale = db.execute(count_query, tuple(params)).fetchone()[0]

    # Query con join per info ordine
    query = f"""
        SELECT
            a.*,
            t.numero_ordine,
            t.ragione_sociale,
            v.codice_vendor as vendor
        FROM anomalie a
        LEFT JOIN ordini_testata t ON a.id_testata = t.id_testata
        LEFT JOIN vendor v ON t.id_vendor = v.id_vendor
        WHERE {where_clause}
        ORDER BY
            CASE a.livello
                WHEN 'CRITICO' THEN 1
                WHEN 'ERRORE' THEN 2
                WHEN 'ATTENZIONE' THEN 3
                ELSE 4
            END,
            a.data_creazione DESC
        LIMIT %s OFFSET %s
    """
    params.extend([limit, offset])

    rows = db.execute(query, tuple(params)).fetchall()
    anomalie = [dict(row) for row in rows]

    return {
        'anomalie': anomalie,
        'totale': totale,
        'limit': limit,
        'offset': offset
    }


def get_anomalie_by_ordine(id_testata: int) -> List[Dict]:
    """Ritorna tutte le anomalie di un ordine."""
    db = get_db()

    rows = db.execute("""
        SELECT
            a.*,
            d.codice_aic,
            d.descrizione_prodotto,
            d.n_riga
        FROM anomalie a
        LEFT JOIN ordini_dettaglio d ON a.id_dettaglio = d.id_dettaglio
        WHERE a.id_testata = %s
        ORDER BY
            CASE a.livello
                WHEN 'CRITICO' THEN 1
                WHEN 'ERRORE' THEN 2
                WHEN 'ATTENZIONE' THEN 3
                ELSE 4
            END,
            a.data_creazione DESC
    """, (id_testata,)).fetchall()

    return [dict(row) for row in rows]


def get_anomalie_critiche(limit: int = 10) -> List[Dict]:
    """Ritorna anomalie critiche non risolte per dashboard."""
    db = get_db()

    rows = db.execute("""
        SELECT
            a.*,
            t.numero_ordine,
            t.ragione_sociale,
            v.codice_vendor as vendor
        FROM anomalie a
        LEFT JOIN ordini_testata t ON a.id_testata = t.id_testata
        LEFT JOIN vendor v ON t.id_vendor = v.id_vendor
        WHERE a.stato IN ('APERTA', 'IN_GESTIONE')
        AND a.livello IN ('CRITICO', 'ERRORE')
        ORDER BY
            CASE a.livello WHEN 'CRITICO' THEN 1 ELSE 2 END,
            a.data_creazione DESC
        LIMIT %s
    """, (limit,)).fetchall()

    return [dict(row) for row in rows]


def get_anomalia_detail(id_anomalia: int) -> Optional[Dict]:
    """Ritorna dettaglio completo anomalia."""
    db = get_db()

    row = db.execute("""
        SELECT
            a.*,
            t.numero_ordine,
            t.ragione_sociale,
            t.min_id,
            t.partita_iva,
            t.data_ordine,
            v.codice_vendor as vendor,
            d.codice_aic,
            d.descrizione_prodotto,
            d.n_riga,
            d.q_venduta,
            d.prezzo_netto
        FROM anomalie a
        LEFT JOIN ordini_testata t ON a.id_testata = t.id_testata
        LEFT JOIN vendor v ON t.id_vendor = v.id_vendor
        LEFT JOIN ordini_dettaglio d ON a.id_dettaglio = d.id_dettaglio
        WHERE a.id_anomalia = %s
    """, (id_anomalia,)).fetchone()

    return dict(row) if row else None


def get_anomalie_stats() -> Dict[str, Any]:
    """Statistiche anomalie per dashboard."""
    db = get_db()

    stats = {
        'totale_aperte': 0,
        'per_livello': {},
        'per_tipo': {},
        'per_stato': {},
        'trend_settimana': []
    }

    # Totale aperte
    row = db.execute("""
        SELECT COUNT(*) FROM anomalie
        WHERE stato IN ('APERTA', 'IN_GESTIONE')
    """).fetchone()
    stats['totale_aperte'] = row[0] if row else 0

    # Per livello
    rows = db.execute("""
        SELECT livello, COUNT(*) as cnt
        FROM anomalie
        WHERE stato IN ('APERTA', 'IN_GESTIONE')
        GROUP BY livello
    """).fetchall()
    stats['per_livello'] = {row['livello']: row['cnt'] for row in rows}

    # Per tipo
    rows = db.execute("""
        SELECT tipo_anomalia, COUNT(*) as cnt
        FROM anomalie
        WHERE stato IN ('APERTA', 'IN_GESTIONE')
        GROUP BY tipo_anomalia
    """).fetchall()
    stats['per_tipo'] = {row['tipo_anomalia']: row['cnt'] for row in rows}

    # Per stato
    rows = db.execute("""
        SELECT stato, COUNT(*) as cnt
        FROM anomalie
        GROUP BY stato
    """).fetchall()
    stats['per_stato'] = {row['stato']: row['cnt'] for row in rows}

    # Trend ultima settimana
    rows = db.execute("""
        SELECT
            DATE(data_creazione) as giorno,
            COUNT(*) as create_count,
            SUM(CASE WHEN stato IN ('RISOLTA', 'IGNORATA') THEN 1 ELSE 0 END) as resolved_count
        FROM anomalie
        WHERE data_creazione >= CURRENT_DATE - INTERVAL '7 days'
        GROUP BY DATE(data_creazione)
        ORDER BY giorno
    """).fetchall()
    stats['trend_settimana'] = [dict(row) for row in rows]

    return stats


def count_anomalie_aperte_ordine(id_testata: int) -> int:
    """Conta anomalie aperte per un ordine specifico."""
    db = get_db()

    row = db.execute("""
        SELECT COUNT(*) FROM anomalie
        WHERE id_testata = %s AND stato IN ('APERTA', 'IN_GESTIONE')
    """, (id_testata,)).fetchone()

    return row[0] if row else 0
