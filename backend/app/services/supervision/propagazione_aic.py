# =============================================================================
# SERV.O v10.6 - PROPAGAZIONE AIC
# =============================================================================
# Servizio unificato per propagazione codice AIC corretto
#
# GERARCHIA DI PROPAGAZIONE:
# - ORDINE: Tutte le righe dell'ordine con stessa descrizione normalizzata
#           che hanno anomalie AIC aperte (default per tutti gli utenti)
# - GLOBALE: Tutte le righe stesso vendor con stessa descrizione che hanno
#            anomalie AIC aperte (solo supervisori e superiori)
#
# AUDIT TRAIL:
# - Ogni modifica viene registrata con valore precedente per rollback
# - Funzione correggi_aic_errato per correggere errori di digitazione
# =============================================================================

import re
from typing import Dict, List, Optional, Tuple
from enum import Enum

from ...database_pg import get_db, log_operation, log_modifica


class LivelloPropagazione(str, Enum):
    """Livelli di propagazione AIC."""
    ORDINE = 'ORDINE'      # Tutte le righe dell'ordine con stessa descrizione (default)
    GLOBALE = 'GLOBALE'    # Tutte le anomalie aperte stesso vendor con stessa descrizione


def normalizza_descrizione(descrizione: str) -> str:
    """
    Normalizza descrizione per matching.
    - Uppercase
    - Rimuovi spazi multipli
    - Rimuovi caratteri speciali
    - Tronca a 50 caratteri
    """
    if not descrizione:
        return ''
    desc = ' '.join(str(descrizione).upper().split())
    desc = re.sub(r'[^\w\s]', '', desc)
    return desc[:50]


def valida_codice_aic(codice_aic: str) -> Tuple[bool, str]:
    """
    Valida formato codice AIC.

    Args:
        codice_aic: Codice da validare

    Returns:
        (valido, messaggio_errore)
    """
    if not codice_aic:
        return False, "Codice AIC mancante"

    codice = str(codice_aic).strip()

    if not codice.isdigit():
        return False, "Codice AIC deve contenere solo cifre"

    if len(codice) != 9:
        return False, f"Codice AIC deve essere di 9 cifre (ricevuto: {len(codice)})"

    return True, codice


def propaga_aic(
    id_dettaglio: int,
    codice_aic: str,
    livello: LivelloPropagazione,
    operatore: str,
    note: str = None
) -> Dict:
    """
    Propaga codice AIC secondo il livello richiesto.

    Args:
        id_dettaglio: ID riga origine
        codice_aic: Codice AIC corretto (9 cifre)
        livello: Livello di propagazione (ORDINE, GLOBALE)
        operatore: Username operatore che effettua la correzione
        note: Note opzionali

    Returns:
        Dict con risultati:
        {
            'success': bool,
            'righe_aggiornate': int,
            'ordini_coinvolti': list,
            'descrizione_normalizzata': str,
            'error': str (se fallito)
        }
    """
    # Valida AIC
    valido, result = valida_codice_aic(codice_aic)
    if not valido:
        return {'success': False, 'error': result}

    codice_aic = result  # Codice pulito

    db = get_db()

    # Recupera dati riga origine con vendor
    riga = db.execute("""
        SELECT od.id_dettaglio, od.id_testata, od.descrizione, od.codice_aic AS aic_precedente,
               ot.numero_ordine_vendor, ot.id_vendor
        FROM ordini_dettaglio od
        JOIN ordini_testata ot ON od.id_testata = ot.id_testata
        WHERE od.id_dettaglio = %s
    """, (id_dettaglio,)).fetchone()

    if not riga:
        return {'success': False, 'error': f"Riga {id_dettaglio} non trovata"}

    desc_norm = normalizza_descrizione(riga['descrizione'])
    id_testata = riga['id_testata']
    id_vendor = riga['id_vendor']
    aic_precedente = riga['aic_precedente']

    righe_aggiornate = 0
    ordini_coinvolti = set()

    try:
        if livello == LivelloPropagazione.ORDINE:
            # Aggiorna tutte le righe dell'ordine con stessa descrizione
            righe_aggiornate, ordini = _aggiorna_righe_ordine(
                db, id_testata, desc_norm, codice_aic, operatore
            )
            ordini_coinvolti.update(ordini)

        elif livello == LivelloPropagazione.GLOBALE:
            # v10.6: Aggiorna righe con anomalie aperte, stesso vendor, stessa descrizione
            righe_aggiornate, ordini = _aggiorna_righe_globale(
                db, desc_norm, codice_aic, operatore, id_vendor
            )
            ordini_coinvolti.update(ordini)

        db.commit()

        # Log operazione
        log_operation(
            'PROPAGA_AIC',
            'ORDINI_DETTAGLIO',
            id_dettaglio,
            f"AIC {codice_aic} propagato ({livello.value}): {righe_aggiornate} righe, "
            f"{len(ordini_coinvolti)} ordini. Operatore: {operatore}",
            dati={
                'codice_aic': codice_aic,
                'aic_precedente': aic_precedente,
                'livello': livello.value,
                'descrizione_normalizzata': desc_norm,
                'righe_aggiornate': righe_aggiornate,
            },
            operatore=operatore
        )

        return {
            'success': True,
            'righe_aggiornate': righe_aggiornate,
            'ordini_coinvolti': list(ordini_coinvolti),
            'descrizione_normalizzata': desc_norm,
            'codice_aic': codice_aic,
            'livello': livello.value
        }

    except Exception as e:
        db.rollback()
        return {'success': False, 'error': str(e)}


def _aggiorna_riga_singola(
    db,
    id_dettaglio: int,
    codice_aic: str,
    operatore: str,
    fonte: str = 'PROPAGAZIONE_AIC'
) -> int:
    """Aggiorna singola riga con audit trail."""
    # Recupera valore precedente
    row = db.execute("""
        SELECT codice_aic, id_testata FROM ordini_dettaglio WHERE id_dettaglio = %s
    """, (id_dettaglio,)).fetchone()

    if not row:
        return 0

    aic_precedente = row['codice_aic']
    id_testata = row['id_testata']

    # Aggiorna
    db.execute("""
        UPDATE ordini_dettaglio
        SET codice_aic = %s
        WHERE id_dettaglio = %s
    """, (codice_aic, id_dettaglio))

    # Audit trail
    log_modifica(
        entita='ORDINI_DETTAGLIO',
        id_entita=id_dettaglio,
        campo_modificato='codice_aic',
        valore_precedente=aic_precedente,
        valore_nuovo=codice_aic,
        fonte_modifica=fonte,
        id_testata=id_testata,
        username_operatore=operatore
    )

    return 1


def _aggiorna_righe_ordine(
    db,
    id_testata: int,
    desc_norm: str,
    codice_aic: str,
    operatore: str,
    fonte: str = 'PROPAGAZIONE_AIC_ORDINE'
) -> Tuple[int, List[int]]:
    """
    Aggiorna tutte le righe dell'ordine con stessa descrizione normalizzata.
    v10.6: Solo righe che hanno anomalie AIC aperte.
    Con audit trail per ogni riga.
    """
    # Trova righe da aggiornare: stesso ordine, stessa descrizione, AIC mancante/diverso
    # SOLO righe che hanno anomalie AIC aperte collegate
    righe = db.execute("""
        SELECT DISTINCT od.id_dettaglio, od.codice_aic
        FROM ordini_dettaglio od
        JOIN anomalie a ON a.id_dettaglio = od.id_dettaglio
        WHERE od.id_testata = %s
          AND UPPER(REGEXP_REPLACE(LEFT(od.descrizione, 50), '[^\\w\\s]', '', 'g')) = %s
          AND (od.codice_aic IS NULL OR od.codice_aic = '' OR od.codice_aic != %s)
          AND a.codice_anomalia = 'AIC-A01'
          AND a.stato IN ('APERTA', 'ERRORE', 'ATTENZIONE', 'INFO')
    """, (id_testata, desc_norm, codice_aic)).fetchall()

    if not righe:
        return 0, []

    # Aggiorna e logga ogni riga
    for riga in righe:
        db.execute("""
            UPDATE ordini_dettaglio SET codice_aic = %s WHERE id_dettaglio = %s
        """, (codice_aic, riga['id_dettaglio']))

        log_modifica(
            entita='ORDINI_DETTAGLIO',
            id_entita=riga['id_dettaglio'],
            campo_modificato='codice_aic',
            valore_precedente=riga['codice_aic'],
            valore_nuovo=codice_aic,
            fonte_modifica=fonte,
            id_testata=id_testata,
            username_operatore=operatore
        )

    return len(righe), [id_testata]


def _aggiorna_righe_globale(
    db,
    desc_norm: str,
    codice_aic: str,
    operatore: str,
    id_vendor: int = None,
    fonte: str = 'PROPAGAZIONE_AIC_GLOBALE'
) -> Tuple[int, List[int]]:
    """
    Aggiorna le righe con stessa descrizione normalizzata per lo stesso vendor.
    v10.6: Vendor-specific (AIC è specifico per vendor).
    Con audit trail per ogni riga.

    Args:
        db: Database connection
        desc_norm: Descrizione normalizzata
        codice_aic: Codice AIC corretto
        operatore: Username operatore
        id_vendor: ID vendor per filtrare (obbligatorio per propagazione corretta)
        fonte: Fonte modifica per audit trail
    """
    if not id_vendor:
        # Se non c'è vendor, non propagare globalmente (safety)
        return 0, []

    # Trova righe da aggiornare: stesso vendor, stessa descrizione, AIC mancante/diverso
    # SOLO righe che hanno anomalie aperte collegate
    righe = db.execute("""
        SELECT DISTINCT od.id_dettaglio, od.id_testata, od.codice_aic
        FROM ordini_dettaglio od
        JOIN ordini_testata ot ON od.id_testata = ot.id_testata
        JOIN anomalie a ON a.id_dettaglio = od.id_dettaglio
        WHERE ot.id_vendor = %s
          AND UPPER(REGEXP_REPLACE(LEFT(od.descrizione, 50), '[^\\w\\s]', '', 'g')) = %s
          AND (od.codice_aic IS NULL OR od.codice_aic = '' OR od.codice_aic != %s)
          AND a.codice_anomalia = 'AIC-A01'
          AND a.stato IN ('APERTA', 'ERRORE', 'ATTENZIONE', 'INFO')
    """, (id_vendor, desc_norm, codice_aic)).fetchall()

    if not righe:
        return 0, []

    ordini_coinvolti = set()

    # Aggiorna e logga ogni riga
    for riga in righe:
        db.execute("""
            UPDATE ordini_dettaglio SET codice_aic = %s WHERE id_dettaglio = %s
        """, (codice_aic, riga['id_dettaglio']))

        log_modifica(
            entita='ORDINI_DETTAGLIO',
            id_entita=riga['id_dettaglio'],
            campo_modificato='codice_aic',
            valore_precedente=riga['codice_aic'],
            valore_nuovo=codice_aic,
            fonte_modifica=fonte,
            id_testata=riga['id_testata'],
            username_operatore=operatore
        )

        ordini_coinvolti.add(riga['id_testata'])

    return len(righe), list(ordini_coinvolti)


def risolvi_anomalia_aic(
    id_anomalia: int,
    codice_aic: str,
    livello: LivelloPropagazione,
    operatore: str,
    note: str = None
) -> Dict:
    """
    Risolve anomalia AIC con propagazione.

    Effetti:
    1. Propaga codice AIC secondo livello
    2. Marca anomalia come RISOLTA
    3. Aggiorna eventuali supervisioni collegate
    4. Aggiorna contatori ML

    Args:
        id_anomalia: ID anomalia
        codice_aic: Codice AIC corretto
        livello: Livello propagazione
        operatore: Username operatore
        note: Note opzionali

    Returns:
        Risultato propagazione + stato anomalia
    """
    db = get_db()

    # Recupera anomalia
    anomalia = db.execute("""
        SELECT a.id_anomalia, a.id_testata, a.id_dettaglio, a.codice_anomalia,
               a.stato, a.valore_anomalo,
               od.descrizione
        FROM anomalie a
        LEFT JOIN ordini_dettaglio od ON a.id_dettaglio = od.id_dettaglio
        WHERE a.id_anomalia = %s
    """, (id_anomalia,)).fetchone()

    if not anomalia:
        return {'success': False, 'error': f"Anomalia {id_anomalia} non trovata"}

    if anomalia['stato'] == 'RISOLTA':
        return {'success': False, 'error': "Anomalia già risolta"}

    id_dettaglio = anomalia['id_dettaglio']

    if not id_dettaglio:
        return {'success': False, 'error': "Anomalia non collegata a una riga specifica"}

    # Propaga AIC
    result = propaga_aic(
        id_dettaglio=id_dettaglio,
        codice_aic=codice_aic,
        livello=livello,
        operatore=operatore,
        note=note
    )

    if not result['success']:
        return result

    # Marca anomalia come RISOLTA
    db.execute("""
        UPDATE anomalie
        SET stato = 'RISOLTA',
            data_risoluzione = CURRENT_TIMESTAMP,
            note_risoluzione = %s
        WHERE id_anomalia = %s
    """, (
        f"AIC corretto: {codice_aic} ({livello.value}). {note or ''}".strip(),
        id_anomalia
    ))

    # Chiudi anomalie AIC collegate secondo il livello
    desc_norm = result['descrizione_normalizzata']

    if livello == LivelloPropagazione.ORDINE:
        # Chiudi solo anomalie dello stesso ordine
        db.execute("""
            UPDATE anomalie a
            SET stato = 'RISOLTA',
                data_risoluzione = CURRENT_TIMESTAMP,
                note_risoluzione = %s
            FROM ordini_dettaglio od
            WHERE a.id_dettaglio = od.id_dettaglio
              AND od.id_testata = %s
              AND a.codice_anomalia = 'AIC-A01'
              AND a.stato IN ('APERTA', 'ERRORE', 'ATTENZIONE', 'INFO')
              AND UPPER(REGEXP_REPLACE(LEFT(od.descrizione, 50), '[^\\w\\s]', '', 'g')) = %s
        """, (f"AIC propagato: {codice_aic} [ORDINE da {operatore}]", anomalia['id_testata'], desc_norm))

    elif livello == LivelloPropagazione.GLOBALE:
        # v10.6: Chiudi anomalie stesso vendor, stessa descrizione
        # Recupera id_vendor dall'ordine
        vendor_row = db.execute("""
            SELECT id_vendor FROM ordini_testata WHERE id_testata = %s
        """, (anomalia['id_testata'],)).fetchone()

        if vendor_row:
            db.execute("""
                UPDATE anomalie a
                SET stato = 'RISOLTA',
                    data_risoluzione = CURRENT_TIMESTAMP,
                    note_risoluzione = %s
                FROM ordini_dettaglio od
                JOIN ordini_testata ot ON od.id_testata = ot.id_testata
                WHERE a.id_dettaglio = od.id_dettaglio
                  AND ot.id_vendor = %s
                  AND a.codice_anomalia = 'AIC-A01'
                  AND a.stato IN ('APERTA', 'ERRORE', 'ATTENZIONE', 'INFO')
                  AND UPPER(REGEXP_REPLACE(LEFT(od.descrizione, 50), '[^\\w\\s]', '', 'g')) = %s
            """, (f"AIC propagato: {codice_aic} [GLOBALE da {operatore}]", vendor_row['id_vendor'], desc_norm))

    # Aggiorna supervisioni collegate
    _aggiorna_supervisioni_collegate(db, anomalia, codice_aic, operatore, livello, result)

    db.commit()

    result['anomalia_risolta'] = True
    result['id_anomalia'] = id_anomalia

    return result


def _aggiorna_supervisioni_collegate(
    db,
    anomalia: Dict,
    codice_aic: str,
    operatore: str,
    livello: LivelloPropagazione,
    result: Dict
):
    """
    Aggiorna supervisioni AIC collegate e pattern ML.
    """
    # Aggiorna supervisione specifica se esiste
    db.execute("""
        UPDATE supervisione_aic
        SET stato = 'APPROVED',
            operatore = %s,
            timestamp_decisione = CURRENT_TIMESTAMP,
            codice_aic_assegnato = %s,
            note = %s
        WHERE id_anomalia = %s AND stato = 'PENDING'
    """, (operatore, codice_aic, f"Risolto da anomalie ({livello.value})", anomalia['id_anomalia']))

    # Se GLOBALE, aggiorna tutte le supervisioni con stessa descrizione
    if livello == LivelloPropagazione.GLOBALE:
        desc_norm = result['descrizione_normalizzata']

        # Trova e approva supervisioni con stessa descrizione normalizzata
        db.execute("""
            UPDATE supervisione_aic
            SET stato = 'APPROVED',
                operatore = %s,
                timestamp_decisione = CURRENT_TIMESTAMP,
                codice_aic_assegnato = %s,
                note = %s
            WHERE descrizione_normalizzata = %s
              AND stato = 'PENDING'
        """, (operatore, codice_aic, f"Auto-approvato da propagazione GLOBALE", desc_norm))

        # Aggiorna pattern ML
        from .aic import _registra_approvazione_pattern_aic, calcola_pattern_signature_aic

        # Per propagazione globale, aggiorna pattern per ogni vendor coinvolto
        vendors = db.execute("""
            SELECT DISTINCT v.codice_vendor
            FROM ordini_dettaglio od
            JOIN ordini_testata ot ON od.id_testata = ot.id_testata
            JOIN vendor v ON ot.id_vendor = v.id_vendor
            WHERE UPPER(REGEXP_REPLACE(LEFT(od.descrizione, 50), '[^\\w\\s]', '', 'g')) = %s
        """, (desc_norm,)).fetchall()

        for v in vendors:
            pattern_sig = calcola_pattern_signature_aic(v['codice_vendor'], desc_norm)
            try:
                _registra_approvazione_pattern_aic(pattern_sig, operatore, codice_aic)
            except Exception:
                pass  # Ignora errori su pattern inesistenti


# =============================================================================
# CORREZIONE AIC ERRATO
# =============================================================================

def correggi_aic_errato(
    aic_errato: str,
    aic_corretto: str,
    operatore: str,
    note: str = None
) -> Dict:
    """
    Corregge un AIC errato sostituendolo con quello corretto in tutto il database.

    Utile quando un operatore ha digitato un AIC sbagliato e questo è stato
    propagato a multiple righe.

    Args:
        aic_errato: Codice AIC errato da sostituire
        aic_corretto: Codice AIC corretto
        operatore: Username operatore (deve essere supervisore)
        note: Note opzionali sulla correzione

    Returns:
        Dict con risultati:
        {
            'success': bool,
            'righe_corrette': int,
            'ordini_coinvolti': list,
            'error': str (se fallito)
        }
    """
    # Valida entrambi i codici
    valido_err, msg_err = valida_codice_aic(aic_errato)
    if not valido_err:
        return {'success': False, 'error': f"AIC errato non valido: {msg_err}"}

    valido_corr, aic_corretto_clean = valida_codice_aic(aic_corretto)
    if not valido_corr:
        return {'success': False, 'error': f"AIC corretto non valido: {aic_corretto_clean}"}

    aic_errato = msg_err  # Codice pulito
    aic_corretto = aic_corretto_clean

    if aic_errato == aic_corretto:
        return {'success': False, 'error': "AIC errato e corretto sono identici"}

    db = get_db()

    try:
        # Trova tutte le righe con l'AIC errato
        righe = db.execute("""
            SELECT id_dettaglio, id_testata, descrizione
            FROM ordini_dettaglio
            WHERE codice_aic = %s
        """, (aic_errato,)).fetchall()

        if not righe:
            return {
                'success': False,
                'error': f"Nessuna riga trovata con AIC {aic_errato}"
            }

        ordini_coinvolti = set()
        righe_corrette = 0

        # Correggi ogni riga con audit trail
        for riga in righe:
            db.execute("""
                UPDATE ordini_dettaglio
                SET codice_aic = %s
                WHERE id_dettaglio = %s
            """, (aic_corretto, riga['id_dettaglio']))

            # Audit trail
            log_modifica(
                entita='ORDINI_DETTAGLIO',
                id_entita=riga['id_dettaglio'],
                campo_modificato='codice_aic',
                valore_precedente=aic_errato,
                valore_nuovo=aic_corretto,
                fonte_modifica='CORREZIONE_AIC_ERRATO',
                id_testata=riga['id_testata'],
                username_operatore=operatore,
                motivazione=note or f"Correzione AIC errato {aic_errato} -> {aic_corretto}"
            )

            ordini_coinvolti.add(riga['id_testata'])
            righe_corrette += 1

        db.commit()

        # Log operazione generale
        log_operation(
            'CORREGGI_AIC_ERRATO',
            'ORDINI_DETTAGLIO',
            0,
            f"Corretto AIC {aic_errato} -> {aic_corretto}: {righe_corrette} righe, "
            f"{len(ordini_coinvolti)} ordini. Operatore: {operatore}",
            dati={
                'aic_errato': aic_errato,
                'aic_corretto': aic_corretto,
                'righe_corrette': righe_corrette,
                'ordini_coinvolti': list(ordini_coinvolti),
                'note': note
            },
            operatore=operatore
        )

        return {
            'success': True,
            'aic_errato': aic_errato,
            'aic_corretto': aic_corretto,
            'righe_corrette': righe_corrette,
            'ordini_coinvolti': list(ordini_coinvolti)
        }

    except Exception as e:
        db.rollback()
        return {'success': False, 'error': str(e)}


def get_storico_modifiche_aic(
    limit: int = 100,
    aic_filter: str = None,
    operatore_filter: str = None
) -> List[Dict]:
    """
    Recupera storico modifiche AIC dalla tabella audit.

    Args:
        limit: Numero massimo di record
        aic_filter: Filtra per codice AIC specifico
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

    if aic_filter:
        query += " AND (am.valore_precedente = %s OR am.valore_nuovo = %s)"
        params.extend([aic_filter, aic_filter])

    if operatore_filter:
        query += " AND am.username_operatore = %s"
        params.append(operatore_filter)

    query += " ORDER BY am.timestamp DESC LIMIT %s"
    params.append(limit)

    rows = db.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def conta_anomalie_aic_aperte() -> int:
    """
    Conta anomalie AIC ancora aperte.
    Utile per aggiornare contatori in supervisione.
    """
    db = get_db()
    row = db.execute("""
        SELECT COUNT(*) AS cnt
        FROM anomalie
        WHERE codice_anomalia = 'AIC-A01' AND stato = 'APERTA'
    """).fetchone()
    return row['cnt'] if row else 0


def conta_supervisioni_aic_pending() -> int:
    """
    Conta supervisioni AIC ancora pending.
    """
    db = get_db()
    row = db.execute("""
        SELECT COUNT(*) AS cnt
        FROM supervisione_aic
        WHERE stato = 'PENDING'
    """).fetchone()
    return row['cnt'] if row else 0
