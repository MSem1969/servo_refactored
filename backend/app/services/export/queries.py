# =============================================================================
# SERV.O v7.0 - EXPORT QUERIES
# =============================================================================
# Query per tracciati e esportazioni
# =============================================================================

import os
from typing import Dict, List, Optional

from ...config import config
from ...database_pg import get_db


def get_ordini_pronti_export() -> List[Dict]:
    """
    Ritorna ordini pronti per esportazione.

    Logica:
    - Stato ESTRATTO (non ancora esportati)
    - Con lookup valido
    """
    db = get_db()
    rows = db.execute("""
        SELECT
            id_testata,
            vendor,
            numero_ordine,
            ragione_sociale,
            citta,
            lookup_method,
            lookup_score,
            num_righe_calc AS num_righe,
            stato,
            data_estrazione,
            data_validazione
        FROM V_ORDINI_COMPLETI
        WHERE stato = 'ESTRATTO'
        AND (lookup_method IS NULL OR lookup_method != 'NESSUNO')
        ORDER BY stato DESC, vendor, numero_ordine_vendor
    """).fetchall()
    return [dict(row) for row in rows]


def get_esportazioni_storico(limit: int = 20) -> List[Dict]:
    """
    Ritorna storico esportazioni con flag 'oggi'.
    """
    db = get_db()
    # La colonna e' data_generazione: 'data_esportazione' non e' mai esistita
    # su PostgreSQL (e date('now') era sintassi SQLite), quindi la query
    # falliva sempre. Altrove e' esposta con l'alias data_esportazione, che
    # qui viene mantenuto per non cambiare la forma della risposta.
    rows = db.execute("""
        SELECT
            e.*,
            e.data_generazione AS data_esportazione,
            CASE
                WHEN e.data_generazione::date = CURRENT_DATE THEN 1
                ELSE 0
            END AS oggi
        FROM ESPORTAZIONI e
        ORDER BY e.data_generazione DESC
        LIMIT ?
    """, (limit,)).fetchall()
    return [dict(row) for row in rows]


def get_file_tracciato(filename: str) -> Optional[str]:
    """
    Ritorna percorso completo file tracciato se esiste.
    """
    path = os.path.join(config.OUTPUT_DIR, filename)
    if os.path.exists(path):
        return path
    return None
