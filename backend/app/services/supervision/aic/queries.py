# =============================================================================
# SERV.O v11.4 - AIC QUERIES
# =============================================================================
# Funzioni di query e contatori per AIC
# v11.6: Aggiunto crea_supervisione_aic, valuta_anomalia_aic (migrato da aic.py)
# =============================================================================

from typing import Dict, List, Tuple

from ....database_pg import get_db, log_operation
from .validation import normalizza_descrizione, calcola_pattern_signature


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


# =============================================================================
# FUNZIONI MIGRATED da aic.py (v11.6)
# =============================================================================

def _assicura_pattern_aic_esistente(pattern_sig: str, vendor: str, descrizione: str):
    """
    Assicura che un pattern AIC esista nella tabella criteri.
    Crea record se non esiste.
    """
    db = get_db()

    desc_norm = normalizza_descrizione(descrizione)

    existing = db.execute(
        "SELECT 1 FROM criteri_ordinari_aic WHERE pattern_signature = %s",
        (pattern_sig,)
    ).fetchone()

    if not existing:
        pattern_desc = f"AIC {vendor} - {desc_norm[:30]}"

        db.execute("""
            INSERT INTO criteri_ordinari_aic
            (pattern_signature, pattern_descrizione, vendor, descrizione_normalizzata)
            VALUES (%s, %s, %s, %s)
        """, (
            pattern_sig,
            pattern_desc,
            vendor,
            desc_norm,
        ))
        db.commit()


def crea_supervisione_aic(
    id_testata: int,
    id_anomalia: int,
    anomalia: Dict
) -> int:
    """
    Crea nuova richiesta di supervisione per anomalia AIC.

    Args:
        id_testata: ID ordine in ORDINI_TESTATA
        id_anomalia: ID anomalia in ANOMALIE
        anomalia: Dati completi anomalia con:
            - vendor: codice vendor
            - id_dettaglio: ID riga in ORDINI_DETTAGLIO
            - n_riga: numero riga
            - descrizione_prodotto: descrizione prodotto
            - codice_originale: codice estratto dal PDF

    Returns:
        ID supervisione creata
    """
    db = get_db()

    vendor = anomalia.get('vendor', 'UNKNOWN')
    # Supporta sia 'descrizione_prodotto' (pdf_processor) che 'descrizione' (fallback)
    descrizione = anomalia.get('descrizione_prodotto', anomalia.get('descrizione', ''))
    desc_norm = normalizza_descrizione(descrizione)

    # Calcola pattern signature
    pattern_sig = calcola_pattern_signature(vendor, descrizione)

    # Inserisci richiesta supervisione AIC
    cursor = db.execute("""
        INSERT INTO supervisione_aic
        (id_testata, id_anomalia, id_dettaglio, codice_anomalia, vendor,
         n_riga, descrizione_prodotto, descrizione_normalizzata, codice_originale,
         pattern_signature, stato)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'PENDING')
        RETURNING id_supervisione
    """, (
        id_testata,
        id_anomalia,
        anomalia.get('id_dettaglio'),
        'AIC-A01',
        vendor,
        anomalia.get('n_riga'),
        descrizione[:100] if descrizione else '',
        desc_norm,
        anomalia.get('codice_originale', ''),
        pattern_sig,
    ))

    id_supervisione = cursor.fetchone()[0]
    db.commit()

    # Assicura che il pattern esista nella tabella criteri
    _assicura_pattern_aic_esistente(pattern_sig, vendor, descrizione)

    # Log operazione
    log_operation(
        'CREA_SUPERVISIONE',
        'SUPERVISIONE_AIC',
        id_supervisione,
        f"Creata supervisione AIC per ordine {id_testata}, prodotto {desc_norm[:30]}"
    )

    return id_supervisione


def valuta_anomalia_aic(id_testata: int, anomalia: Dict) -> Tuple[bool, str]:
    """
    Valuta anomalia AIC usando pattern appresi.
    Se il pattern è ordinario E ha un AIC default, applica automaticamente.

    Args:
        id_testata: ID ordine
        anomalia: Dati anomalia

    Returns:
        (applicato_auto, pattern_signature)
        - applicato_auto: True se AIC applicato automaticamente
        - pattern_signature: Signature del pattern
    """
    db = get_db()

    vendor = anomalia.get('vendor', 'UNKNOWN')
    # Supporta sia 'descrizione_prodotto' (pdf_processor) che 'descrizione' (fallback)
    descrizione = anomalia.get('descrizione_prodotto', anomalia.get('descrizione', ''))

    pattern_sig = calcola_pattern_signature(vendor, descrizione)

    # Verifica se esiste pattern ordinario con AIC default
    pattern = db.execute("""
        SELECT codice_aic_default, is_ordinario, count_approvazioni
        FROM criteri_ordinari_aic
        WHERE pattern_signature = %s
    """, (pattern_sig,)).fetchone()

    if pattern and pattern['is_ordinario'] and pattern['codice_aic_default']:
        # Pattern ordinario con AIC default: applica automaticamente
        codice_aic = pattern['codice_aic_default']
        id_dettaglio = anomalia.get('id_dettaglio')

        if id_dettaglio:
            # Aggiorna la riga con l'AIC
            db.execute("""
                UPDATE ordini_dettaglio
                SET codice_aic = %s
                WHERE id_dettaglio = %s AND (codice_aic IS NULL OR codice_aic = '' OR codice_aic !~ '^[0-9]{9}$')
            """, (codice_aic, id_dettaglio))
            db.commit()

            log_operation(
                'AUTO_APPLY_AIC',
                'ORDINI_DETTAGLIO',
                id_dettaglio,
                f"AIC {codice_aic} applicato automaticamente da pattern {pattern_sig}"
            )

            return True, pattern_sig

    return False, pattern_sig
