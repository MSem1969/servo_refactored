# =============================================================================
# SERV.O v10.1 - ANOMALIES COMMANDS
# =============================================================================
# Command functions for anomaly mutations
# =============================================================================

from typing import Dict, Any, List, Optional
from ...database_pg import get_db


def create_anomalia(
    id_testata: int = None,
    id_dettaglio: int = None,
    id_acquisizione: int = None,
    tipo: str = 'ALTRO',
    codice: str = None,
    livello: str = 'ATTENZIONE',
    descrizione: str = '',
    dati_originali: Dict = None,
    valore_anomalo: str = None
) -> int:
    """
    Crea nuova anomalia.

    Args:
        id_testata: ID ordine (opzionale)
        id_dettaglio: ID riga dettaglio (opzionale)
        id_acquisizione: ID acquisizione (opzionale)
        tipo: Tipo anomalia (LOOKUP, ESPOSITORE, LISTINO, VALIDAZIONE, etc.)
        codice: Codice anomalia (es. ESP-A01, LKP-A02)
        livello: Livello gravità (INFO, ATTENZIONE, ERRORE, CRITICO)
        descrizione: Descrizione testuale
        dati_originali: JSON con dati originali
        valore_anomalo: Valore che ha causato l'anomalia

    Returns:
        ID della nuova anomalia
    """
    db = get_db()

    import json
    dati_json = json.dumps(dati_originali) if dati_originali else None

    cursor = db.execute("""
        INSERT INTO ANOMALIE
        (id_testata, id_dettaglio, id_acquisizione, tipo_anomalia,
         codice, livello, descrizione, dati_originali, valore_anomalo, stato)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'APERTA')
        RETURNING id_anomalia
    """, (id_testata, id_dettaglio, id_acquisizione, tipo,
          codice, livello, descrizione, dati_json, valore_anomalo))

    result = cursor.fetchone()
    db.commit()

    # Aggiorna stato ordine se necessario
    if id_testata and livello in ('ERRORE', 'CRITICO'):
        _update_ordine_stato_anomalia(id_testata)

    return result[0] if result else None


def update_anomalia_stato(
    id_anomalia: int,
    nuovo_stato: str,
    operatore: str = None,
    note: str = None
) -> bool:
    """
    Aggiorna stato anomalia.

    Args:
        id_anomalia: ID anomalia
        nuovo_stato: Nuovo stato (APERTA, IN_GESTIONE, RISOLTA, IGNORATA)
        operatore: Username operatore
        note: Note risoluzione

    Returns:
        True se aggiornato con successo
    """
    stati_validi = ['APERTA', 'IN_GESTIONE', 'RISOLTA', 'IGNORATA']
    if nuovo_stato not in stati_validi:
        return False

    db = get_db()

    # Recupera info anomalia
    anomalia = db.execute(
        "SELECT tipo_anomalia, id_testata FROM anomalie WHERE id_anomalia = %s",
        (id_anomalia,)
    ).fetchone()

    if not anomalia:
        return False

    # Aggiorna stato
    if nuovo_stato in ('RISOLTA', 'IGNORATA'):
        db.execute("""
            UPDATE anomalie
            SET stato = %s,
                operatore = %s,
                data_risoluzione = CURRENT_TIMESTAMP,
                note_risoluzione = %s
            WHERE id_anomalia = %s
        """, (nuovo_stato, operatore, note, id_anomalia))

        # Aggiorna supervisioni collegate
        sup_stato = 'APPROVED' if nuovo_stato == 'RISOLTA' else 'REJECTED'
        db.execute("""
            UPDATE supervisione_espositore
            SET stato = %s,
                operatore = %s,
                data_decisione = CURRENT_TIMESTAMP,
                note = COALESCE(note || ' - ', '') || %s
            WHERE id_anomalia = %s AND stato = 'PENDING'
        """, (sup_stato, operatore, f'Risolto da anomalia: {note or ""}', id_anomalia))

    else:
        db.execute(
            "UPDATE anomalie SET stato = %s, operatore = %s WHERE id_anomalia = %s",
            (nuovo_stato, operatore, id_anomalia)
        )

    db.commit()

    # ML pattern learning per anomalie risolte
    if nuovo_stato == 'RISOLTA' and anomalia['tipo_anomalia'] == 'ESPOSITORE':
        _registra_pattern_ml(id_anomalia, anomalia['id_testata'])

    # Sblocca ordine se tutte le anomalie sono risolte
    if nuovo_stato in ('RISOLTA', 'IGNORATA') and anomalia['id_testata']:
        _sblocca_ordine_se_possibile(anomalia['id_testata'])

    return True


def resolve_anomalia(
    id_anomalia: int,
    operatore: str,
    note: str = None,
    dati_corretti: Dict = None
) -> bool:
    """
    Risolve un'anomalia con dati corretti opzionali.

    Args:
        id_anomalia: ID anomalia
        operatore: Username operatore
        note: Note risoluzione
        dati_corretti: Dati corretti (JSON)

    Returns:
        True se risolto con successo
    """
    db = get_db()

    import json
    dati_json = json.dumps(dati_corretti) if dati_corretti else None

    db.execute("""
        UPDATE anomalie
        SET stato = 'RISOLTA',
            operatore = %s,
            data_risoluzione = CURRENT_TIMESTAMP,
            note_risoluzione = %s,
            dati_corretti = %s
        WHERE id_anomalia = %s
    """, (operatore, note, dati_json, id_anomalia))

    db.commit()

    # Recupera id_testata per sblocco
    anomalia = db.execute(
        "SELECT id_testata FROM anomalie WHERE id_anomalia = %s",
        (id_anomalia,)
    ).fetchone()

    if anomalia and anomalia['id_testata']:
        _sblocca_ordine_se_possibile(anomalia['id_testata'])

    return True


def ignore_anomalia(
    id_anomalia: int,
    operatore: str,
    note: str = None
) -> bool:
    """
    Ignora un'anomalia (soft delete).

    Args:
        id_anomalia: ID anomalia
        operatore: Username operatore
        note: Motivo

    Returns:
        True se ignorato con successo
    """
    return update_anomalia_stato(id_anomalia, 'IGNORATA', operatore, note)


def resolve_batch(
    anomalie_ids: List[int],
    operatore: str,
    note: str = None
) -> Dict[str, Any]:
    """
    Risolve multiple anomalie in batch.

    Returns:
        Dict con risultati {success: int, failed: int, errors: []}
    """
    result = {'success': 0, 'failed': 0, 'errors': []}

    for id_anomalia in anomalie_ids:
        try:
            if update_anomalia_stato(id_anomalia, 'RISOLTA', operatore, note):
                result['success'] += 1
            else:
                result['failed'] += 1
                result['errors'].append(f"Anomalia {id_anomalia}: aggiornamento fallito")
        except Exception as e:
            result['failed'] += 1
            result['errors'].append(f"Anomalia {id_anomalia}: {str(e)}")

    return result


def ignore_batch(
    anomalie_ids: List[int],
    operatore: str,
    note: str = None
) -> Dict[str, Any]:
    """
    Ignora multiple anomalie in batch.

    Returns:
        Dict con risultati {success: int, failed: int, errors: []}
    """
    result = {'success': 0, 'failed': 0, 'errors': []}

    for id_anomalia in anomalie_ids:
        try:
            if update_anomalia_stato(id_anomalia, 'IGNORATA', operatore, note):
                result['success'] += 1
            else:
                result['failed'] += 1
                result['errors'].append(f"Anomalia {id_anomalia}: aggiornamento fallito")
        except Exception as e:
            result['failed'] += 1
            result['errors'].append(f"Anomalia {id_anomalia}: {str(e)}")

    return result


# =============================================================================
# HELPER FUNCTIONS (Internal)
# =============================================================================

def _update_ordine_stato_anomalia(id_testata: int):
    """Aggiorna stato ordine a ANOMALIA se ci sono anomalie gravi."""
    db = get_db()

    db.execute("""
        UPDATE ordini_testata
        SET stato = 'ANOMALIA'
        WHERE id_testata = %s
        AND stato NOT IN ('EVASO', 'ARCHIVIATO')
    """, (id_testata,))

    db.commit()


def _sblocca_ordine_se_possibile(id_testata: int) -> bool:
    """Sblocca ordine quando tutte le anomalie sono risolte/ignorate."""
    db = get_db()

    # Conta anomalie ancora aperte
    anomalie_aperte = db.execute("""
        SELECT COUNT(*) as cnt FROM anomalie
        WHERE id_testata = %s AND stato IN ('APERTA', 'IN_GESTIONE')
    """, (id_testata,)).fetchone()

    # Conta supervisioni pending
    supervisioni_pending = db.execute("""
        SELECT COUNT(*) as cnt FROM supervisione_espositore
        WHERE id_testata = %s AND stato = 'PENDING'
    """, (id_testata,)).fetchone()

    anomalie_cnt = anomalie_aperte['cnt'] if anomalie_aperte else 0
    supervisioni_cnt = supervisioni_pending['cnt'] if supervisioni_pending else 0

    if anomalie_cnt == 0 and supervisioni_cnt == 0:
        result = db.execute("""
            UPDATE ordini_testata
            SET stato = 'ESTRATTO'
            WHERE id_testata = %s AND stato IN ('ANOMALIA', 'PENDING_REVIEW')
            RETURNING id_testata
        """, (id_testata,)).fetchone()

        db.commit()
        return result is not None

    return False


def _registra_pattern_ml(id_anomalia: int, id_testata: int):
    """Registra pattern ML da anomalia risolta."""
    try:
        from ..ml_pattern_matching import registra_pattern_da_anomalia_risolta
        registra_pattern_da_anomalia_risolta(id_anomalia, id_testata)
    except Exception as e:
        # Log error but don't fail
        print(f"[ML] Errore registrazione pattern: {e}")
