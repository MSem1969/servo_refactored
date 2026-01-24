# =============================================================================
# SERV.O v7.0 - EXPORT QUERIES
# =============================================================================
# Query per tracciati e esportazioni
# =============================================================================

import os
from typing import Dict, Any, List, Optional

from ...config import config
from ...database_pg import get_db
from .formatters import generate_to_t_line, generate_to_d_line


def get_tracciato_preview(id_testata: int) -> Dict[str, Any]:
    """
    Genera preview tracciato senza salvare file.

    Returns:
        Dict con preview TO_T e TO_D
    """
    db = get_db()

    # Carica testata
    ordine = db.execute(
        "SELECT * FROM V_ORDINI_COMPLETI WHERE id_testata = ?",
        (id_testata,)
    ).fetchone()

    if not ordine:
        return {'error': 'Ordine non trovato'}

    ordine_dict = dict(ordine)
    # Normalizza numero_ordine (supporta sia 'numero_ordine' che 'numero_ordine_vendor')
    ordine_dict['numero_ordine'] = ordine_dict.get('numero_ordine') or ordine_dict.get('numero_ordine_vendor') or ''

    # Carica dettagli
    dettagli = db.execute("""
        SELECT * FROM V_DETTAGLI_COMPLETI WHERE id_testata = ?
        ORDER BY n_riga
    """, (id_testata,)).fetchall()

    # Genera preview
    line_t = generate_to_t_line(ordine_dict)

    lines_d = []
    for det in dettagli:
        det_dict = dict(det)
        # Salta solo child (i parent espositore vanno inclusi!)
        if det_dict.get('is_child'):
            continue
        det_dict['numero_ordine'] = ordine_dict['numero_ordine']
        det_dict['min_id'] = ordine_dict.get('min_id') or ''
        lines_d.append(generate_to_d_line(det_dict))

    return {
        'to_t': line_t,
        'to_d': lines_d,
        'to_t_length': len(line_t),
        'to_d_count': len(lines_d),
        'ordine': {
            'numero_ordine': ordine_dict['numero_ordine'],
            'vendor': ordine_dict['vendor'],
            'ragione_sociale': ordine_dict['ragione_sociale'],
        }
    }


def get_ordini_pronti_export() -> List[Dict]:
    """
    Ritorna ordini pronti per esportazione.

    Logica:
    - Stato ESTRATTO (non ancora esportati)
    - Esclusi SCARTATO, ESPORTATO
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
    rows = db.execute("""
        SELECT
            e.*,
            CASE
                WHEN date(e.data_esportazione) = date('now') THEN 1
                ELSE 0
            END AS oggi
        FROM ESPORTAZIONI e
        ORDER BY e.data_esportazione DESC
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
