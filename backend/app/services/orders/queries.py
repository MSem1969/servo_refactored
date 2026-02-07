# =============================================================================
# SERV.O v7.0 - ORDERS QUERIES
# =============================================================================
# Funzioni di query per ordini, righe e anomalie
# Estratto da ordini.py per modularità
# =============================================================================

import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from ...database_pg import get_db


# =============================================================================
# ORDINI - QUERY
# =============================================================================

def get_ordini(
    vendor: str = None,
    stato: str = None,
    lookup_method: str = None,
    data_da: str = None,
    data_a: str = None,
    q: str = None,
    limit: int = 100,
    offset: int = 0
) -> Dict[str, Any]:
    """
    Ritorna lista ordini con filtri opzionali.

    Args:
        vendor: Filtra per vendor
        stato: Filtra per stato (ESTRATTO, VALIDATO, ANOMALIA, ESPORTATO)
        lookup_method: Filtra per metodo lookup
        data_da: Data ordine da (DD/MM/YYYY)
        data_a: Data ordine a (DD/MM/YYYY)
        q: Ricerca testuale in numero_ordine, ragione_sociale, min_id
        limit: Max risultati
        offset: Offset paginazione

    Returns:
        Dict con 'ordini' (lista) e 'totale' (count)
    """
    db = get_db()

    conditions = []
    params = []

    if stato:
        conditions.append("stato = ?")
        params.append(stato)
    else:
        conditions.append("stato NOT IN ('EVASO', 'ARCHIVIATO')")

    if vendor:
        conditions.append("vendor = ?")
        params.append(vendor)

    if lookup_method:
        conditions.append("lookup_method = ?")
        params.append(lookup_method)

    if data_da:
        conditions.append("data_ordine >= ?")
        params.append(data_da)

    if data_a:
        conditions.append("data_ordine <= ?")
        params.append(data_a)

    # Ricerca testuale in numero ordine, ragione sociale, MIN_ID
    if q and q.strip():
        search_term = f"%{q.strip()}%"
        conditions.append("""(
            numero_ordine_vendor ILIKE ? OR
            ragione_sociale ILIKE ? OR
            min_id ILIKE ? OR
            partita_iva ILIKE ?
        )""")
        params.extend([search_term, search_term, search_term, search_term])

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    count_query = f"SELECT COUNT(*) FROM V_ORDINI_COMPLETI WHERE {where_clause}"
    totale = db.execute(count_query, params).fetchone()[0]

    query = f"""
        SELECT * FROM V_ORDINI_COMPLETI
        WHERE {where_clause}
        ORDER BY id_testata DESC
        LIMIT ? OFFSET ?
    """
    params.extend([limit, offset])

    rows = db.execute(query, params).fetchall()
    ordini = [dict(row) for row in rows]

    # Aggiungi deposito per ogni ordine
    # Priorità: 1) deposito manuale in testata, 2) anagrafica_clienti
    for ordine in ordini:
        id_testata = ordine.get('id_testata')
        piva = ordine.get('partita_iva')
        min_id = ordine.get('min_id')
        deposito = None

        # 1. Prima controlla deposito_riferimento assegnato manualmente
        if id_testata:
            deposito_manuale = db.execute("""
                SELECT deposito_riferimento FROM ordini_testata
                WHERE id_testata = %s AND deposito_riferimento IS NOT NULL AND deposito_riferimento != ''
            """, (id_testata,)).fetchone()
            if deposito_manuale and deposito_manuale[0]:
                deposito = deposito_manuale[0]

        # 2. Fallback: cerca in anagrafica_clienti
        if not deposito and piva:
            # Prova prima con multipunto (P.IVA + min_id)
            if min_id:
                cliente = db.execute("""
                    SELECT deposito_riferimento FROM anagrafica_clienti
                    WHERE partita_iva = %s AND min_id = %s
                    LIMIT 1
                """, (piva, min_id)).fetchone()
                if cliente:
                    deposito = cliente[0]

            # Fallback: solo P.IVA
            if not deposito:
                cliente = db.execute("""
                    SELECT deposito_riferimento FROM anagrafica_clienti
                    WHERE partita_iva = %s
                    LIMIT 1
                """, (piva,)).fetchone()
                if cliente:
                    deposito = cliente[0]

        ordine['deposito'] = deposito

    return {
        'ordini': ordini,
        'totale': totale,
        'limit': limit,
        'offset': offset
    }


def get_ordine_detail(id_testata: int) -> Optional[Dict[str, Any]]:
    """Ritorna dettaglio completo ordine con righe e anomalie."""
    db = get_db()

    ordine = db.execute(
        "SELECT * FROM V_ORDINI_COMPLETI WHERE id_testata = ?",
        (id_testata,)
    ).fetchone()

    if not ordine:
        return None

    result = dict(ordine)

    # Recupera deposito_riferimento raw da ordini_testata (per modal Modifica Header)
    testata_extra = db.execute("""
        SELECT deposito_riferimento FROM ordini_testata WHERE id_testata = %s
    """, (id_testata,)).fetchone()
    raw_deposito = testata_extra['deposito_riferimento'] if testata_extra else None
    result['deposito_riferimento'] = raw_deposito or ''

    # Recupera deposito: priorità al valore manuale, poi anagrafica_clienti
    # 1. Prima controlla deposito_riferimento assegnato manualmente
    if raw_deposito:
        deposito = raw_deposito
    else:
        # 2. Fallback: cerca in anagrafica_clienti
        piva = result.get('partita_iva')
        min_id = result.get('min_id')
        deposito = None

        if piva:
            # Prova prima con multipunto (P.IVA + min_id normalizzato)
            if min_id:
                min_id_norm = min_id.lstrip('0')
                cliente = db.execute("""
                    SELECT deposito_riferimento FROM anagrafica_clienti
                    WHERE partita_iva = %s AND LTRIM(min_id, '0') = %s
                    LIMIT 1
                """, (piva, min_id_norm)).fetchone()
                if cliente:
                    deposito = cliente['deposito_riferimento']

            # Fallback: solo P.IVA
            if not deposito:
                cliente = db.execute("""
                    SELECT deposito_riferimento FROM anagrafica_clienti
                    WHERE partita_iva = %s
                    LIMIT 1
                """, (piva,)).fetchone()
                if cliente:
                    deposito = cliente['deposito_riferimento']

    result['deposito'] = deposito

    righe = db.execute("""
        SELECT * FROM ORDINI_DETTAGLIO
        WHERE id_testata = ?
        ORDER BY n_riga
    """, (id_testata,)).fetchall()
    result['righe'] = [dict(r) for r in righe]

    anomalie = db.execute("""
        SELECT * FROM ANOMALIE
        WHERE id_testata = ?
        ORDER BY data_rilevazione DESC
    """, (id_testata,)).fetchall()
    result['anomalie'] = [dict(a) for a in anomalie]

    acquisizione = db.execute("""
        SELECT * FROM ACQUISIZIONI
        WHERE id_acquisizione = ?
    """, (result.get('id_acquisizione'),)).fetchone()
    if acquisizione:
        result['acquisizione'] = dict(acquisizione)

    return result


def get_ordine_righe(id_testata: int, include_children: bool = False) -> List[Dict]:
    """Ritorna le righe dettaglio di un ordine.

    Args:
        id_testata: ID ordine
        include_children: Se True, include anche righe CHILD_ESPOSITORE (per EspositoreTab)
    """
    db = get_db()

    if include_children:
        rows = db.execute("""
            SELECT * FROM ORDINI_DETTAGLIO
            WHERE id_testata = ?
            ORDER BY n_riga
        """, (id_testata,)).fetchall()
    else:
        rows = db.execute("""
            SELECT * FROM ORDINI_DETTAGLIO
            WHERE id_testata = ?
              AND (is_child = FALSE OR is_child IS NULL)
            ORDER BY n_riga
        """, (id_testata,)).fetchall()

    return [dict(r) for r in rows]


def get_riga_dettaglio(id_testata: int, id_dettaglio: int) -> Optional[Dict[str, Any]]:
    """Recupera dettaglio completo riga con info supervisione."""
    db = get_db()

    row = db.execute("""
        SELECT od.*,
               se.id_supervisione,
               se.stato AS stato_supervisione,
               se.codice_anomalia,
               se.pezzi_attesi,
               se.pezzi_trovati,
               se.note AS note_supervisore
        FROM ORDINI_DETTAGLIO od
        LEFT JOIN SUPERVISIONE_ESPOSITORE se ON od.id_supervisione = se.id_supervisione
        WHERE od.id_dettaglio = ? AND od.id_testata = ?
    """, (id_dettaglio, id_testata)).fetchone()

    if not row:
        return None

    result = dict(row)

    if result.get('espositore_metadata'):
        try:
            result['espositore_metadata_parsed'] = json.loads(result['espositore_metadata'])
        except:
            pass

    if result.get('valori_originali'):
        try:
            result['valori_originali_parsed'] = json.loads(result['valori_originali'])
        except:
            pass

    return result


def get_stato_righe_ordine(id_testata: int) -> Dict[str, int]:
    """Ritorna conteggio righe per stato."""
    db = get_db()

    stats = db.execute("""
        SELECT
            COUNT(*) AS totale,
            SUM(CASE WHEN stato_riga = 'ESTRATTO' THEN 1 ELSE 0 END) AS estratto,
            SUM(CASE WHEN stato_riga = 'IN_SUPERVISIONE' THEN 1 ELSE 0 END) AS in_supervisione,
            SUM(CASE WHEN stato_riga = 'SUPERVISIONATO' THEN 1 ELSE 0 END) AS supervisionato,
            SUM(CASE WHEN stato_riga = 'CONFERMATO' THEN 1 ELSE 0 END) AS confermato,
            SUM(CASE WHEN stato_riga = 'IN_TRACCIATO' THEN 1 ELSE 0 END) AS in_tracciato,
            SUM(CASE WHEN stato_riga = 'ESPORTATO' THEN 1 ELSE 0 END) AS esportato,
            SUM(CASE WHEN stato_riga = 'EVASO' THEN 1 ELSE 0 END) AS evaso,
            SUM(CASE WHEN stato_riga = 'ARCHIVIATO' THEN 1 ELSE 0 END) AS archiviato,
            SUM(CASE WHEN stato_riga IN ('PARZIALMENTE_ESP', 'PARZIALE') THEN 1 ELSE 0 END) AS parzialmente_esp,
            SUM(CASE WHEN richiede_supervisione = TRUE THEN 1 ELSE 0 END) AS richiede_supervisione
        FROM ORDINI_DETTAGLIO
        WHERE id_testata = ? AND (is_child = FALSE OR is_child IS NULL)
    """, (id_testata,)).fetchone()

    return dict(stats) if stats else {
        'totale': 0, 'estratto': 0, 'in_supervisione': 0,
        'supervisionato': 0, 'confermato': 0, 'in_tracciato': 0,
        'esportato': 0, 'parzialmente_esp': 0, 'richiede_supervisione': 0
    }


def get_ordini_recenti(limit: int = 10) -> List[Dict]:
    """Ritorna ordini più recenti."""
    db = get_db()
    rows = db.execute("""
        SELECT * FROM V_ORDINI_COMPLETI
        ORDER BY id_testata DESC
        LIMIT ?
    """, (limit,)).fetchall()
    return [dict(row) for row in rows]


# =============================================================================
# ANOMALIE - QUERY
# =============================================================================

def get_anomalie(
    tipo: str = None,
    livello: str = None,
    stato: str = None,
    limit: int = 100,
    offset: int = 0
) -> Dict[str, Any]:
    """Ritorna lista anomalie con filtri."""
    db = get_db()

    conditions = []
    params = []

    if tipo:
        conditions.append("tipo_anomalia = ?")
        params.append(tipo)

    if livello:
        conditions.append("livello = ?")
        params.append(livello)

    if stato:
        conditions.append("an.stato = ?")
        params.append(stato)
    else:
        conditions.append("an.stato IN ('APERTA', 'IN_GESTIONE')")

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    count_query = f"""
        SELECT COUNT(*) FROM ANOMALIE an
        LEFT JOIN ORDINI_TESTATA ot ON an.id_testata = ot.id_testata
        WHERE {where_clause}
    """
    totale = db.execute(count_query, params).fetchone()[0]

    query = f"""
        SELECT
            an.*,
            v.codice_vendor as vendor,
            ot.numero_ordine_vendor as numero_ordine,
            a.nome_file_originale as pdf_file
        FROM ANOMALIE an
        LEFT JOIN ORDINI_TESTATA ot ON an.id_testata = ot.id_testata
        LEFT JOIN VENDOR v ON ot.id_vendor = v.id_vendor
        LEFT JOIN ACQUISIZIONI a ON COALESCE(an.id_acquisizione, ot.id_acquisizione) = a.id_acquisizione
        WHERE {where_clause}
        ORDER BY
            CASE an.livello
                WHEN 'CRITICO' THEN 1
                WHEN 'ERRORE' THEN 2
                WHEN 'ATTENZIONE' THEN 3
                ELSE 4
            END,
            an.data_rilevazione DESC
        LIMIT ? OFFSET ?
    """
    params.extend([limit, offset])

    rows = db.execute(query, params).fetchall()

    return {
        'anomalie': [dict(row) for row in rows],
        'totale': totale,
        'limit': limit,
        'offset': offset
    }


def get_anomalie_by_ordine(id_testata: int) -> List[Dict]:
    """Ritorna anomalie di un ordine specifico."""
    db = get_db()
    rows = db.execute("""
        SELECT * FROM ANOMALIE
        WHERE id_testata = ?
        ORDER BY data_rilevazione DESC
    """, (id_testata,)).fetchall()
    return [dict(row) for row in rows]


def get_anomalie_critiche(limit: int = 10) -> List[Dict]:
    """Ritorna anomalie critiche/errore aperte."""
    db = get_db()
    rows = db.execute("""
        SELECT
            an.*,
            v.codice_vendor as vendor,
            ot.numero_ordine_vendor as numero_ordine
        FROM ANOMALIE an
        LEFT JOIN ORDINI_TESTATA ot ON an.id_testata = ot.id_testata
        LEFT JOIN VENDOR v ON ot.id_vendor = v.id_vendor
        WHERE an.stato IN ('APERTA', 'IN_GESTIONE')
        AND an.livello IN ('CRITICO', 'ERRORE')
        ORDER BY
            CASE an.livello WHEN 'CRITICO' THEN 1 ELSE 2 END,
            an.data_rilevazione DESC
        LIMIT ?
    """, (limit,)).fetchall()
    return [dict(row) for row in rows]


# =============================================================================
# DASHBOARD & STATISTICHE
# =============================================================================

def get_dashboard_stats() -> Dict[str, Any]:
    """Ritorna statistiche per dashboard."""
    db = get_db()

    ordini_per_stato = {}
    rows = db.execute("""
        SELECT stato, COUNT(*) as count
        FROM ORDINI_TESTATA
        GROUP BY stato
    """).fetchall()
    for row in rows:
        ordini_per_stato[row['stato']] = row['count']

    ordini_per_vendor = {}
    rows = db.execute("""
        SELECT v.codice_vendor, COUNT(*) as count
        FROM ORDINI_TESTATA ot
        JOIN VENDOR v ON ot.id_vendor = v.id_vendor
        GROUP BY v.codice_vendor
    """).fetchall()
    for row in rows:
        ordini_per_vendor[row['codice_vendor']] = row['count']

    anomalie_per_tipo = {}
    rows = db.execute("""
        SELECT tipo_anomalia, COUNT(*) as count
        FROM ANOMALIE
        WHERE stato IN ('APERTA', 'IN_GESTIONE')
        GROUP BY tipo_anomalia
    """).fetchall()
    for row in rows:
        anomalie_per_tipo[row['tipo_anomalia']] = row['count']

    lookup_stats = {}
    rows = db.execute("""
        SELECT lookup_method, COUNT(*) as count
        FROM ORDINI_TESTATA
        GROUP BY lookup_method
    """).fetchall()
    for row in rows:
        lookup_stats[row['lookup_method'] or 'NULL'] = row['count']

    ordini_ultimi_7gg = db.execute("""
        SELECT data_estrazione::date as giorno, COUNT(*) as count
        FROM ORDINI_TESTATA
        WHERE data_estrazione >= CURRENT_DATE - INTERVAL '7 days'
        GROUP BY data_estrazione::date
        ORDER BY giorno
    """).fetchall()

    # v11.3: Stats giornaliere (oggi)
    oggi_per_stato = {}
    rows_oggi = db.execute("""
        SELECT stato, COUNT(*) as count
        FROM ORDINI_TESTATA
        WHERE data_estrazione::date = CURRENT_DATE
        GROUP BY stato
    """).fetchall()
    for row in rows_oggi:
        oggi_per_stato[row['stato']] = row['count']

    return {
        'totali': {
            'ordini': db.execute("SELECT COUNT(*) FROM ORDINI_TESTATA").fetchone()[0],
            'righe': db.execute("SELECT COUNT(*) FROM ORDINI_DETTAGLIO").fetchone()[0],
            'anomalie_aperte': db.execute(
                "SELECT COUNT(*) FROM ANOMALIE WHERE stato IN ('APERTA', 'IN_GESTIONE')"
            ).fetchone()[0],
            'pdf_elaborati': db.execute(
                "SELECT COUNT(*) FROM ACQUISIZIONI WHERE stato = 'ELABORATO'"
            ).fetchone()[0],
        },
        # v11.3: Stats giornaliere
        'oggi': {
            'ordini': db.execute("SELECT COUNT(*) FROM ORDINI_TESTATA WHERE data_estrazione::date = CURRENT_DATE").fetchone()[0],
            'anomalie_aperte': db.execute(
                "SELECT COUNT(*) FROM ANOMALIE WHERE stato IN ('APERTA', 'IN_GESTIONE') AND data_rilevazione::date = CURRENT_DATE"
            ).fetchone()[0],
            'pdf_elaborati': db.execute(
                "SELECT COUNT(*) FROM ACQUISIZIONI WHERE stato = 'ELABORATO' AND data_acquisizione::date = CURRENT_DATE"
            ).fetchone()[0],
            'per_stato': oggi_per_stato,
        },
        'ordini_per_stato': ordini_per_stato,
        'ordini_per_vendor': ordini_per_vendor,
        'anomalie_per_tipo': anomalie_per_tipo,
        'lookup_stats': lookup_stats,
        'ordini_ultimi_7gg': [dict(r) for r in ordini_ultimi_7gg],
        'timestamp': datetime.now().isoformat()
    }
