# =============================================================================
# SERV.O v11.4 - SUPERVISION AIC SERVICE (PARZIALMENTE DEPRECATO)
# =============================================================================
# NOTA: Questo file è in fase di migrazione verso aic_unified.py
#
# FUNZIONI MIGRATE (v11.4):
# - rifiuta_supervisione_aic -> aic_unified.py
# - search_aic_suggestions -> aic_unified.py
# - _reset_pattern_aic -> aic_unified.py
#
# FUNZIONI ANCORA QUI (da migrare in futuro):
# - crea_supervisione_aic (usato da pdf_processor.py)
# - valuta_anomalia_aic (usato da pdf_processor.py)
# - _registra_approvazione_pattern_aic (usato da anomalies/commands.py)
# - normalizza_descrizione_prodotto, calcola_pattern_signature_aic, etc.
#
# Per nuove funzionalità AIC, usare aic_unified.py
# =============================================================================

import re
import hashlib
from typing import Dict, Optional, Tuple, List

from ...database_pg import get_db, log_operation
from .constants import SOGLIA_PROMOZIONE


def normalizza_descrizione_prodotto(descrizione: str) -> str:
    """
    Normalizza descrizione prodotto per pattern matching.
    - Uppercase
    - Rimuovi spazi extra
    - Rimuovi caratteri speciali
    - Tronca a 50 caratteri
    """
    if not descrizione:
        return ''
    # Uppercase e rimuovi spazi multipli
    desc = ' '.join(str(descrizione).upper().split())
    # Rimuovi caratteri speciali ma mantieni lettere, numeri e spazi
    desc = re.sub(r'[^\w\s]', '', desc)
    return desc[:50]


def calcola_pattern_signature_aic(vendor: str, descrizione: str) -> str:
    """
    Calcola signature univoca per pattern AIC.
    Pattern: VENDOR|DESCRIZIONE_NORMALIZZATA

    Args:
        vendor: Codice vendor (es. MENARINI)
        descrizione: Descrizione prodotto

    Returns:
        Hash MD5 troncato a 16 caratteri
    """
    desc_norm = normalizza_descrizione_prodotto(descrizione)
    raw = f"{vendor or 'UNKNOWN'}|{desc_norm}"
    return hashlib.md5(raw.encode()).hexdigest()[:16]


def _assicura_pattern_aic_esistente(pattern_sig: str, vendor: str, descrizione: str):
    """
    Assicura che un pattern AIC esista nella tabella criteri.
    Crea record se non esiste.
    """
    db = get_db()

    desc_norm = normalizza_descrizione_prodotto(descrizione)

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
            - descrizione: descrizione prodotto
            - codice_originale: codice estratto dal PDF

    Returns:
        ID supervisione creata
    """
    db = get_db()

    vendor = anomalia.get('vendor', 'UNKNOWN')
    # Supporta sia 'descrizione_prodotto' (pdf_processor) che 'descrizione' (fallback)
    descrizione = anomalia.get('descrizione_prodotto', anomalia.get('descrizione', ''))
    desc_norm = normalizza_descrizione_prodotto(descrizione)

    # Calcola pattern signature
    pattern_sig = calcola_pattern_signature_aic(vendor, descrizione)

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

    pattern_sig = calcola_pattern_signature_aic(vendor, descrizione)

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
                WHERE id_dettaglio = %s AND (codice_aic IS NULL OR codice_aic = '')
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


def approva_supervisione_aic(
    id_supervisione: int,
    operatore: str,
    codice_aic: str,
    livello_propagazione: str = 'GLOBALE',
    note: str = None
) -> Dict:
    """
    Approva supervisione AIC e propaga il codice assegnato.

    Args:
        id_supervisione: ID supervisione
        operatore: Username operatore
        codice_aic: Codice AIC assegnato (9 cifre)
        livello_propagazione: ORDINE, GLOBALE (default GLOBALE)
        note: Note opzionali

    Returns:
        Dict con risultati: {approvata, righe_aggiornate, ordini_coinvolti}
    """
    db = get_db()

    # Valida formato AIC
    codice_aic = str(codice_aic).strip()
    if not re.match(r'^\d{9}$', codice_aic):
        raise ValueError(f"Codice AIC non valido: deve essere di 9 cifre")

    # Recupera dati supervisione
    sup = db.execute("""
        SELECT id_testata, id_dettaglio, pattern_signature, vendor,
               descrizione_normalizzata, stato
        FROM supervisione_aic
        WHERE id_supervisione = %s
    """, (id_supervisione,)).fetchone()

    if not sup:
        raise ValueError(f"Supervisione AIC {id_supervisione} non trovata")

    if sup['stato'] != 'PENDING':
        raise ValueError(f"Supervisione non in stato PENDING")

    # Aggiorna supervisione
    db.execute("""
        UPDATE supervisione_aic
        SET stato = 'APPROVED',
            operatore = %s,
            timestamp_decisione = CURRENT_TIMESTAMP,
            note = %s,
            codice_aic_assegnato = %s
        WHERE id_supervisione = %s
    """, (operatore, note, codice_aic, id_supervisione))

    righe_aggiornate = 0
    ordini_coinvolti = set()

    # Aggiorna la riga specifica
    if sup['id_dettaglio']:
        db.execute("""
            UPDATE ordini_dettaglio
            SET codice_aic = %s
            WHERE id_dettaglio = %s
        """, (codice_aic, sup['id_dettaglio']))
        righe_aggiornate += 1
        ordini_coinvolti.add(sup['id_testata'])

    # Propagazione in base al livello
    livello = livello_propagazione.upper() if livello_propagazione else 'GLOBALE'

    if livello == 'ORDINE':
        # Propaga solo all'ordine corrente
        count = db.execute("""
            UPDATE ordini_dettaglio
            SET codice_aic = %s
            WHERE id_testata = %s
              AND descrizione = (SELECT descrizione FROM ordini_dettaglio WHERE id_dettaglio = %s)
              AND id_dettaglio != %s
              AND (codice_aic IS NULL OR codice_aic = '' OR codice_aic = 'NO_AIC')
            RETURNING id_dettaglio
        """, (codice_aic, sup['id_testata'], sup['id_dettaglio'], sup['id_dettaglio'])).rowcount
        righe_aggiornate += count

    elif livello == 'GLOBALE':
        # Propaga a tutte le righe simili in tutto il database
        count, orders = propaga_aic_a_righe_simili(
            sup['vendor'],
            sup['descrizione_normalizzata'],
            codice_aic,
            operatore,
            exclude_dettaglio=sup['id_dettaglio']
        )
        righe_aggiornate += count
        ordini_coinvolti.update(orders)

        # Approva anche altre supervisioni pending con stesso pattern
        altre_sup = db.execute("""
            UPDATE supervisione_aic
            SET stato = 'APPROVED',
                operatore = %s,
                timestamp_decisione = CURRENT_TIMESTAMP,
                note = %s,
                codice_aic_assegnato = %s
            WHERE pattern_signature = %s
              AND stato = 'PENDING'
              AND id_supervisione != %s
            RETURNING id_supervisione, id_testata
        """, (operatore, f"Auto-approvato da pattern {sup['pattern_signature']}",
              codice_aic, sup['pattern_signature'], id_supervisione)).fetchall()

        for row in altre_sup:
            ordini_coinvolti.add(row['id_testata'])
    # Se livello non è ORDINE né GLOBALE: nessuna propagazione aggiuntiva

    # Aggiorna pattern ML
    _registra_approvazione_pattern_aic(sup['pattern_signature'], operatore, codice_aic)

    db.commit()

    # Sblocca ordini se non ci sono altre supervisioni pending
    from .requests import sblocca_ordine_se_completo
    for id_testata in ordini_coinvolti:
        sblocca_ordine_se_completo(id_testata)

        # Chiudi anomalie correlate
        db.execute("""
            UPDATE anomalie
            SET stato = 'RISOLTA',
                data_risoluzione = CURRENT_TIMESTAMP,
                note_risoluzione = %s
            WHERE id_testata = %s
              AND codice_anomalia = 'AIC-A01'
              AND stato = 'APERTA'
        """, (f"AIC assegnato: {codice_aic}", id_testata))

    db.commit()

    log_operation(
        'APPROVA_SUPERVISIONE',
        'SUPERVISIONE_AIC',
        id_supervisione,
        f"Approvata con AIC {codice_aic}, {righe_aggiornate} righe aggiornate"
    )

    return {
        'approvata': True,
        'righe_aggiornate': righe_aggiornate,
        'ordini_coinvolti': list(ordini_coinvolti),
        'codice_aic': codice_aic
    }


def rifiuta_supervisione_aic(
    id_supervisione: int,
    operatore: str,
    note: str
) -> bool:
    """
    Rifiuta supervisione AIC.
    Il rifiuto resetta il pattern ML.

    Args:
        id_supervisione: ID supervisione
        operatore: Username operatore
        note: Motivo del rifiuto (obbligatorio)

    Returns:
        True se rifiutata con successo
    """
    db = get_db()

    if not note or len(note) < 5:
        raise ValueError("Motivo del rifiuto obbligatorio (minimo 5 caratteri)")

    # Recupera dati supervisione
    sup = db.execute("""
        SELECT id_testata, pattern_signature, stato
        FROM supervisione_aic
        WHERE id_supervisione = %s
    """, (id_supervisione,)).fetchone()

    if not sup:
        raise ValueError(f"Supervisione AIC {id_supervisione} non trovata")

    if sup['stato'] != 'PENDING':
        raise ValueError(f"Supervisione non in stato PENDING")

    # Aggiorna supervisione
    db.execute("""
        UPDATE supervisione_aic
        SET stato = 'REJECTED',
            operatore = %s,
            timestamp_decisione = CURRENT_TIMESTAMP,
            note = %s
        WHERE id_supervisione = %s
    """, (operatore, note, id_supervisione))

    # Reset pattern ML
    _reset_pattern_aic(sup['pattern_signature'])

    db.commit()

    # Sblocca ordine
    from .requests import sblocca_ordine_se_completo
    sblocca_ordine_se_completo(sup['id_testata'])

    log_operation(
        'RIFIUTA_SUPERVISIONE',
        'SUPERVISIONE_AIC',
        id_supervisione,
        f"Rifiutata: {note[:50]}"
    )

    return True


def propaga_aic_a_righe_simili(
    vendor: str,
    descrizione_normalizzata: str,
    codice_aic: str,
    operatore: str,
    exclude_dettaglio: int = None
) -> Tuple[int, List[int]]:
    """
    Propaga AIC a tutte le righe con stessa (vendor, descrizione normalizzata).

    Args:
        vendor: Codice vendor
        descrizione_normalizzata: Descrizione normalizzata per matching
        codice_aic: Codice AIC da assegnare
        operatore: Username operatore
        exclude_dettaglio: ID dettaglio da escludere (già aggiornato)

    Returns:
        (count_righe_aggiornate, lista_id_testata_coinvolti)
    """
    db = get_db()

    # Trova tutte le righe che matchano il pattern
    query = """
        SELECT od.id_dettaglio, od.id_testata
        FROM ordini_dettaglio od
        JOIN ordini_testata ot ON od.id_testata = ot.id_testata
        JOIN acquisizioni acq ON ot.id_acquisizione = acq.id_acquisizione
        JOIN vendor v ON acq.id_vendor = v.id_vendor
        WHERE v.codice_vendor = %s
          AND (od.codice_aic IS NULL OR od.codice_aic = '' OR LENGTH(od.codice_aic) != 9)
          AND UPPER(REGEXP_REPLACE(LEFT(od.descrizione, 50), '[^\\w\\s]', '', 'g')) = %s
    """
    params = [vendor, descrizione_normalizzata]

    if exclude_dettaglio:
        query += " AND od.id_dettaglio != %s"
        params.append(exclude_dettaglio)

    righe = db.execute(query, params).fetchall()

    ordini_coinvolti = set()
    count = 0

    for riga in righe:
        db.execute("""
            UPDATE ordini_dettaglio
            SET codice_aic = %s
            WHERE id_dettaglio = %s
        """, (codice_aic, riga['id_dettaglio']))
        count += 1
        ordini_coinvolti.add(riga['id_testata'])

    if count > 0:
        log_operation(
            'PROPAGA_AIC',
            'ORDINI_DETTAGLIO',
            0,
            f"AIC {codice_aic} propagato a {count} righe ({vendor}, {descrizione_normalizzata[:20]})"
        )

    return count, list(ordini_coinvolti)


def _registra_approvazione_pattern_aic(pattern_sig: str, operatore: str, codice_aic: str):
    """
    Registra approvazione nel pattern ML AIC.
    Incrementa contatore e promuove se raggiunge soglia.
    """
    db = get_db()

    # Incrementa contatore
    db.execute("""
        UPDATE criteri_ordinari_aic
        SET count_approvazioni = count_approvazioni + 1,
            operatori_approvatori = COALESCE(operatori_approvatori || ',', '') || %s,
            codice_aic_default = COALESCE(codice_aic_default, %s)
        WHERE pattern_signature = %s
    """, (operatore, codice_aic, pattern_sig))

    # Verifica se promuovere a ordinario
    pattern = db.execute("""
        SELECT count_approvazioni, is_ordinario
        FROM criteri_ordinari_aic
        WHERE pattern_signature = %s
    """, (pattern_sig,)).fetchone()

    if pattern and not pattern['is_ordinario'] and pattern['count_approvazioni'] >= SOGLIA_PROMOZIONE:
        db.execute("""
            UPDATE criteri_ordinari_aic
            SET is_ordinario = TRUE,
                data_promozione = CURRENT_TIMESTAMP
            WHERE pattern_signature = %s
        """, (pattern_sig,))

        log_operation(
            'PROMOZIONE_PATTERN',
            'CRITERI_ORDINARI_AIC',
            0,
            f"Pattern {pattern_sig} promosso a ordinario dopo {SOGLIA_PROMOZIONE} approvazioni"
        )


def _reset_pattern_aic(pattern_sig: str):
    """
    Reset pattern ML AIC dopo rifiuto.
    """
    db = get_db()

    db.execute("""
        UPDATE criteri_ordinari_aic
        SET count_approvazioni = 0,
            is_ordinario = FALSE,
            data_promozione = NULL,
            codice_aic_default = NULL
        WHERE pattern_signature = %s
    """, (pattern_sig,))


def get_supervisioni_aic_pending(limit: int = 100) -> List[Dict]:
    """
    Recupera supervisioni AIC pending.

    Returns:
        Lista di supervisioni con dettagli
    """
    db = get_db()

    rows = db.execute("""
        SELECT
            saic.id_supervisione,
            saic.id_testata,
            saic.id_dettaglio,
            saic.codice_anomalia,
            saic.vendor,
            saic.n_riga,
            saic.descrizione_prodotto,
            saic.descrizione_normalizzata,
            saic.codice_originale,
            saic.pattern_signature,
            saic.stato,
            saic.timestamp_creazione,
            ot.numero_ordine_vendor,
            ot.ragione_sociale_1,
            COALESCE(coaic.count_approvazioni, 0) AS pattern_count,
            COALESCE(coaic.is_ordinario, FALSE) AS pattern_ordinario
        FROM supervisione_aic saic
        JOIN ordini_testata ot ON saic.id_testata = ot.id_testata
        LEFT JOIN criteri_ordinari_aic coaic ON saic.pattern_signature = coaic.pattern_signature
        WHERE saic.stato = 'PENDING'
        ORDER BY saic.timestamp_creazione DESC
        LIMIT %s
    """, (limit,)).fetchall()

    return [dict(r) for r in rows]


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


# =============================================================================
# NOTA: Le funzioni seguenti sono ANCHE in aic_unified.py (v11.4)
# =============================================================================
# Per nuovo codice, importare da aic_unified.py.
# Queste versioni locali sono mantenute per retrocompatibilità con moduli
# che le importano direttamente da qui (pdf_processor.py, anomalies/commands.py)
#
# Funzioni duplicate (preferire aic_unified.py):
# - rifiuta_supervisione_aic
# - search_aic_suggestions
# - _reset_pattern_aic
# =============================================================================
