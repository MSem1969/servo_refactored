# =============================================================================
# SERV.O v10.1 - LISTINI QUERIES
# =============================================================================
# Funzioni di query per listini
# =============================================================================

from typing import Optional, Dict, Any, List
from ...database_pg import get_db
from .parsing import normalizza_codice_aic


def get_prezzo_listino(
    codice_aic: str,
    vendor: str = None
) -> Optional[Dict[str, Any]]:
    """
    Recupera dati prezzo/sconti da listino per un codice AIC.
    Ritorna tutti i campi TO_D necessari per il tracciato.
    """
    db = get_db()
    aic_normalized = normalizza_codice_aic(codice_aic)

    if vendor:
        row = db.execute("""
            SELECT * FROM listini_vendor
            WHERE codice_aic = %s AND vendor = %s AND attivo = TRUE
        """, (aic_normalized, vendor.upper())).fetchone()
    else:
        row = db.execute("""
            SELECT * FROM listini_vendor
            WHERE codice_aic = %s AND attivo = TRUE
            ORDER BY data_import DESC
            LIMIT 1
        """, (aic_normalized,)).fetchone()

    return dict(row) if row else None


def get_listino_vendor(vendor: str, limit: int = 1000) -> List[Dict[str, Any]]:
    """Recupera tutti i prodotti del listino per un vendor."""
    db = get_db()
    rows = db.execute("""
        SELECT * FROM listini_vendor
        WHERE vendor = %s AND attivo = TRUE
        ORDER BY descrizione
        LIMIT %s
    """, (vendor.upper(), limit)).fetchall()

    return [dict(row) for row in rows]


def get_listino_stats() -> Dict[str, Any]:
    """Statistiche sui listini caricati."""
    db = get_db()

    vendor_stats = db.execute("""
        SELECT vendor,
               COUNT(*) as prodotti,
               MAX(data_import) as ultimo_import,
               MAX(fonte_file) as ultimo_file
        FROM listini_vendor
        WHERE attivo = TRUE
        GROUP BY vendor
    """).fetchall()

    result = {
        'totale_prodotti': 0,
        'vendors': {}
    }

    for row in vendor_stats:
        result['vendors'][row['vendor']] = {
            'prodotti': row['prodotti'],
            'ultimo_import': row['ultimo_import'],
            'ultimo_file': row['ultimo_file']
        }
        result['totale_prodotti'] += row['prodotti']

    return result


def search_listino(
    query: str,
    vendor: str = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """Cerca prodotti nel listino per descrizione o codice AIC."""
    db = get_db()
    search_term = f"%{query}%"

    if vendor:
        rows = db.execute("""
            SELECT * FROM listini_vendor
            WHERE vendor = %s AND attivo = TRUE
              AND (descrizione ILIKE %s OR codice_aic LIKE %s)
            ORDER BY descrizione
            LIMIT %s
        """, (vendor.upper(), search_term, search_term, limit)).fetchall()
    else:
        rows = db.execute("""
            SELECT * FROM listini_vendor
            WHERE attivo = TRUE
              AND (descrizione ILIKE %s OR codice_aic LIKE %s)
            ORDER BY vendor, descrizione
            LIMIT %s
        """, (search_term, search_term, limit)).fetchall()

    return [dict(row) for row in rows]
