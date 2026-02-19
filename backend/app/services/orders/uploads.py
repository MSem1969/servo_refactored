# =============================================================================
# ORDERS UPLOADS - Query functions for PDF uploads
# =============================================================================

from typing import Dict, Any, List
from ...database_pg import get_db


def get_recent_uploads(limit: int = 10) -> List[Dict]:
    """Ritorna ultimi PDF caricati."""
    db = get_db()
    rows = db.execute("""
        SELECT a.*, v.codice_vendor as vendor
        FROM ACQUISIZIONI a
        LEFT JOIN VENDOR v ON a.id_vendor = v.id_vendor
        ORDER BY a.data_upload DESC
        LIMIT %s
    """, (limit,)).fetchall()
    return [dict(row) for row in rows]


def get_upload_stats() -> Dict[str, Any]:
    """Statistiche upload."""
    db = get_db()

    return {
        'totale': db.execute("SELECT COUNT(*) FROM ACQUISIZIONI").fetchone()[0],
        'oggi': db.execute(
            "SELECT COUNT(*) FROM ACQUISIZIONI WHERE data_upload::date = CURRENT_DATE"
        ).fetchone()[0],
        'elaborati': db.execute(
            "SELECT COUNT(*) FROM ACQUISIZIONI WHERE stato = 'ELABORATO'"
        ).fetchone()[0],
        'errori': db.execute(
            "SELECT COUNT(*) FROM ACQUISIZIONI WHERE stato = 'ERRORE'"
        ).fetchone()[0],
        'duplicati': db.execute(
            "SELECT COUNT(*) FROM ACQUISIZIONI WHERE stato = 'SCARTATO'"
        ).fetchone()[0],
    }


def get_upload_errors(limit: int = 50) -> List[Dict]:
    """Acquisizioni in stato ERRORE con dettagli vendor."""
    db = get_db()
    rows = db.execute("""
        SELECT a.id_acquisizione, a.nome_file_originale, a.nome_file_storage,
               a.messaggio_errore, a.data_upload, a.dimensione_bytes,
               v.codice_vendor as vendor
        FROM ACQUISIZIONI a
        LEFT JOIN VENDOR v ON a.id_vendor = v.id_vendor
        WHERE a.stato = 'ERRORE'
        ORDER BY a.data_upload DESC
        LIMIT %s
    """, (limit,)).fetchall()
    return [dict(row) for row in rows]


def get_vendors() -> List[Dict]:
    """Lista vendor disponibili."""
    db = get_db()
    rows = db.execute("""
        SELECT id_vendor, codice_vendor, ragione_sociale, attivo
        FROM VENDOR
        WHERE attivo = TRUE
        ORDER BY codice_vendor
    """).fetchall()
    return [dict(row) for row in rows]
