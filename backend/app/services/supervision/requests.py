# =============================================================================
# SERV.O v7.0 - SUPERVISION REQUESTS
# =============================================================================
# Gestione richieste di supervisione per espositore e listino
# =============================================================================

import hashlib
from typing import Dict

from ...database_pg import get_db, log_operation
from .patterns import calcola_pattern_signature, normalizza_fascia_scostamento
from .ml import _assicura_pattern_esistente


def _calcola_pattern_signature_listino(vendor: str, codice_anomalia: str, codice_aic: str) -> str:
    """
    Calcola signature univoca per pattern listino.
    Pattern: VENDOR|CODICE_ANOMALIA|AIC
    """
    raw = f"{vendor}|{codice_anomalia}|{codice_aic or 'NO_AIC'}"
    return hashlib.md5(raw.encode()).hexdigest()[:16]


def _assicura_pattern_listino_esistente(pattern_sig: str, anomalia: Dict):
    """
    Assicura che un pattern listino esista nella tabella criteri.
    Crea record se non esiste.
    """
    db = get_db()

    existing = db.execute(
        "SELECT 1 FROM criteri_ordinari_listino WHERE pattern_signature = %s",
        (pattern_sig,)
    ).fetchone()

    if not existing:
        vendor = anomalia.get('vendor', 'UNKNOWN')
        codice_aic = anomalia.get('valore_anomalo', '')
        codice_anomalia = anomalia.get('codice_anomalia', '')

        descrizione = f"Listino {vendor} - {codice_anomalia} - AIC {codice_aic}"

        db.execute("""
            INSERT INTO criteri_ordinari_listino
            (pattern_signature, pattern_descrizione, vendor, codice_anomalia, codice_aic)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            pattern_sig,
            descrizione,
            vendor,
            codice_anomalia,
            codice_aic,
        ))
        db.commit()


def crea_richiesta_supervisione(
    id_testata: int,
    id_anomalia: int,
    anomalia: Dict
) -> int:
    """
    Crea nuova richiesta di supervisione per un'anomalia.

    Rileva automaticamente il tipo di anomalia (ESPOSITORE/LISTINO/LOOKUP/AIC)
    e inserisce nella tabella appropriata.

    Args:
        id_testata: ID ordine in ORDINI_TESTATA
        id_anomalia: ID anomalia in ANOMALIE
        anomalia: Dati completi anomalia

    Returns:
        ID supervisione creata
    """
    tipo_anomalia = anomalia.get('tipo_anomalia') or ''
    codice_anomalia = anomalia.get('codice_anomalia') or ''

    # v9.0: Rileva se anomalia AIC (AIC-A01)
    if tipo_anomalia == 'AIC' or codice_anomalia.startswith('AIC-'):
        from .aic import crea_supervisione_aic
        return crea_supervisione_aic(id_testata, id_anomalia, anomalia)

    # v8.0: Rileva se anomalia lookup (LKP-A01, LKP-A02, LKP-A04)
    if tipo_anomalia == 'LOOKUP' or codice_anomalia.startswith('LKP-'):
        from .lookup import crea_supervisione_lookup
        return crea_supervisione_lookup(id_testata, id_anomalia, anomalia)

    # Rileva se anomalia listino (LST-A01, LST-A02, etc.)
    if tipo_anomalia == 'LISTINO' or codice_anomalia.startswith('LST-'):
        return _crea_supervisione_listino(id_testata, id_anomalia, anomalia)

    # Default: anomalia espositore
    return _crea_supervisione_espositore(id_testata, id_anomalia, anomalia)


def _crea_supervisione_listino(
    id_testata: int,
    id_anomalia: int,
    anomalia: Dict
) -> int:
    """
    Crea supervisione per anomalia listino (LST-A01, LST-A02).
    """
    db = get_db()

    vendor = anomalia.get('vendor', 'UNKNOWN')
    codice_aic = anomalia.get('valore_anomalo', '')
    codice_anomalia = anomalia.get('codice_anomalia', '')
    n_riga = anomalia.get('n_riga')

    # Calcola pattern signature per listino
    pattern_sig = _calcola_pattern_signature_listino(vendor, codice_anomalia, codice_aic)

    # Usa id_dettaglio dall'anomalia se presente, altrimenti cerca via AIC
    id_dettaglio = anomalia.get('id_dettaglio')
    if not id_dettaglio and codice_aic:
        det_row = db.execute("""
            SELECT id_dettaglio FROM ordini_dettaglio
            WHERE id_testata = %s AND codice_aic = %s
            LIMIT 1
        """, (id_testata, codice_aic)).fetchone()
        if det_row:
            id_dettaglio = det_row['id_dettaglio']

    # Inserisci richiesta supervisione listino
    cursor = db.execute("""
        INSERT INTO supervisione_listino
        (id_testata, id_anomalia, id_dettaglio, codice_anomalia, vendor, codice_aic,
         n_riga, descrizione_prodotto, pattern_signature, stato)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'PENDING')
        RETURNING id_supervisione
    """, (
        id_testata,
        id_anomalia,
        id_dettaglio,
        codice_anomalia,
        vendor,
        codice_aic,
        n_riga,
        anomalia.get('descrizione', ''),
        pattern_sig,
    ))

    id_supervisione = cursor.fetchone()[0]
    db.commit()

    # Assicura che il pattern esista nella tabella criteri listino
    _assicura_pattern_listino_esistente(pattern_sig, anomalia)

    # Log operazione
    log_operation(
        'CREA_SUPERVISIONE',
        'SUPERVISIONE_LISTINO',
        id_supervisione,
        f"Creata supervisione listino per ordine {id_testata}, AIC {codice_aic}"
    )

    return id_supervisione


def _crea_supervisione_espositore(
    id_testata: int,
    id_anomalia: int,
    anomalia: Dict
) -> int:
    """
    Crea supervisione per anomalia espositore (ESP-A01, etc.).
    """
    db = get_db()

    # Calcola pattern signature
    pezzi_attesi = anomalia.get('pezzi_attesi', 0)
    pezzi_trovati = anomalia.get('pezzi_trovati', 0)

    if pezzi_attesi > 0:
        scostamento_pct = ((pezzi_trovati - pezzi_attesi) / pezzi_attesi) * 100
    else:
        scostamento_pct = 0

    fascia_norm = normalizza_fascia_scostamento(scostamento_pct)

    pattern_sig = calcola_pattern_signature(
        vendor='ANGELINI',
        codice_anomalia=anomalia.get('codice_anomalia', ''),
        codice_espositore=anomalia.get('espositore_codice', ''),
        pezzi_per_unita=pezzi_attesi,
        fascia_scostamento=fascia_norm
    )

    # Inserisci richiesta supervisione
    cursor = db.execute("""
        INSERT INTO supervisione_espositore
        (id_testata, id_anomalia, codice_anomalia, codice_espositore,
         descrizione_espositore, pezzi_attesi, pezzi_trovati,
         valore_calcolato, pattern_signature, stato)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'PENDING')
        RETURNING id_supervisione
    """, (
        id_testata,
        id_anomalia,
        anomalia.get('codice_anomalia', ''),
        anomalia.get('espositore_codice', ''),
        anomalia.get('valore_anomalo', ''),
        pezzi_attesi,
        pezzi_trovati,
        0.0,  # valore_calcolato viene aggiornato dopo
        pattern_sig,
    ))

    id_supervisione = cursor.fetchone()[0]
    db.commit()

    # Assicura che il pattern esista nella tabella criteri
    _assicura_pattern_esistente(pattern_sig, anomalia)

    # Log operazione
    log_operation(
        'CREA_SUPERVISIONE',
        'SUPERVISIONE_ESPOSITORE',
        id_supervisione,
        f"Creata supervisione per ordine {id_testata}, pattern {pattern_sig}"
    )

    return id_supervisione


def blocca_ordine_per_supervisione(id_testata: int):
    """
    Blocca un ordine settando stato PENDING_REVIEW.

    L'ordine non potra essere esportato finche tutte le supervisioni
    non sono state gestite.

    Args:
        id_testata: ID ordine da bloccare
    """
    db = get_db()

    db.execute("""
        UPDATE ordini_testata
        SET stato = 'PENDING_REVIEW'
        WHERE id_testata = %s
    """, (id_testata,))

    db.commit()

    log_operation(
        'BLOCCA_ORDINE',
        'ORDINI_TESTATA',
        id_testata,
        'Ordine bloccato per supervisione espositore'
    )


def sblocca_ordine_se_completo(id_testata: int):
    """
    Sblocca ordine se non ci sono piu supervisioni pending.

    v8.1: Verifica stato righe per determinare se ESTRATTO o CONFERMATO.
    - Se tutte le righe sono confermate → stato = CONFERMATO
    - Altrimenti → stato = ESTRATTO

    Args:
        id_testata: ID ordine da verificare
    """
    db = get_db()

    # Verifica supervisioni espositore pending
    pending_esp = db.execute("""
        SELECT COUNT(*) FROM supervisione_espositore
        WHERE id_testata = %s AND stato = 'PENDING'
    """, (id_testata,)).fetchone()[0]

    # Verifica supervisioni listino pending
    pending_listino = db.execute("""
        SELECT COUNT(*) FROM supervisione_listino
        WHERE id_testata = %s AND stato = 'PENDING'
    """, (id_testata,)).fetchone()[0]

    # v8.0: Verifica supervisioni lookup pending
    pending_lookup = db.execute("""
        SELECT COUNT(*) FROM supervisione_lookup
        WHERE id_testata = %s AND stato = 'PENDING'
    """, (id_testata,)).fetchone()[0]

    # v8.1: Verifica supervisioni prezzo pending
    pending_prezzo = db.execute("""
        SELECT COUNT(*) FROM supervisione_prezzo
        WHERE id_testata = %s AND stato = 'PENDING'
    """, (id_testata,)).fetchone()[0]

    # v9.0: Verifica supervisioni AIC pending
    pending_aic = db.execute("""
        SELECT COUNT(*) FROM supervisione_aic
        WHERE id_testata = %s AND stato = 'PENDING'
    """, (id_testata,)).fetchone()[0]

    total_pending = pending_esp + pending_listino + pending_lookup + pending_prezzo + pending_aic

    if total_pending == 0:
        # v8.1: Determina stato ordine in base allo stato delle righe
        # Conta righe totali e righe in stati "confermati"
        righe_stats = db.execute("""
            SELECT
                COUNT(*) AS totale,
                SUM(CASE WHEN stato_riga IN ('CONFERMATO', 'IN_TRACCIATO', 'ESPORTATO', 'ARCHIVIATO')
                    THEN 1 ELSE 0 END) AS confermate
            FROM ordini_dettaglio
            WHERE id_testata = %s
        """, (id_testata,)).fetchone()

        totale_righe = righe_stats[0] or 0
        righe_confermate = righe_stats[1] or 0

        # Se tutte le righe sono confermate → CONFERMATO, altrimenti → ESTRATTO
        nuovo_stato = 'CONFERMATO' if (totale_righe > 0 and righe_confermate == totale_righe) else 'ESTRATTO'

        db.execute("""
            UPDATE ordini_testata
            SET stato = %s
            WHERE id_testata = %s AND stato IN ('PENDING_REVIEW', 'ANOMALIA')
        """, (nuovo_stato, id_testata))
        db.commit()

        log_operation(
            'SBLOCCA_ORDINE',
            'ORDINI_TESTATA',
            id_testata,
            f'Ordine sbloccato dopo completamento supervisioni → stato {nuovo_stato} ({righe_confermate}/{totale_righe} righe confermate)'
        )
