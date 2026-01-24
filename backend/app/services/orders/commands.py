# =============================================================================
# SERV.O v11.0 - ORDERS COMMANDS
# =============================================================================
# Funzioni di modifica per ordini, righe e anomalie
# Estratto da ordini.py per modularità
# v11.0: Aggiunta archiviazione centralizzata
# =============================================================================

import json
from typing import Dict, Any, Optional
from datetime import datetime
from decimal import Decimal
from dataclasses import dataclass

from ...database_pg import get_db, log_operation, log_modifica


def _json_serializer(obj):
    """Converte tipi non serializzabili per JSON."""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    if hasattr(obj, 'isoformat'):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


# =============================================================================
# ORDINI - MODIFICA
# =============================================================================

def update_ordine_stato(id_testata: int, nuovo_stato: str) -> bool:
    """
    Aggiorna SOLO lo stato dell'ordine (testata).

    NOTA: Lo stato ordine NON influenza lo stato delle singole righe.
    Le righe mantengono il proprio stato indipendente (EVASO, PARZIALE, ARCHIVIATO, etc.)

    Stati validi: ESTRATTO, CONFERMATO, ANOMALIA, PARZ_EVASO, EVASO, ARCHIVIATO
    """
    stati_validi = ['ESTRATTO', 'CONFERMATO', 'ANOMALIA', 'PARZ_EVASO', 'EVASO', 'ARCHIVIATO']
    if nuovo_stato not in stati_validi:
        return False

    db = get_db()

    db.execute(
        "UPDATE ORDINI_TESTATA SET stato = ? WHERE id_testata = ?",
        (nuovo_stato, id_testata)
    )

    # RIMOSSO: Non sincronizzare più stato ordine -> stato righe
    # Lo stato delle righe è indipendente e basato su q_evasa/q_totale

    db.commit()

    log_operation('UPDATE_STATO', 'ORDINI_TESTATA', id_testata,
                 f"Stato cambiato in {nuovo_stato}")
    return True


def delete_ordine(id_testata: int) -> bool:
    """Elimina un ordine e tutti i dati correlati."""
    db = get_db()

    ordine = db.execute(
        "SELECT numero_ordine_vendor FROM ORDINI_TESTATA WHERE id_testata = ?",
        (id_testata,)
    ).fetchone()

    if not ordine:
        return False

    db.execute("DELETE FROM ANOMALIE WHERE id_testata = ?", (id_testata,))
    db.execute("DELETE FROM ORDINI_DETTAGLIO WHERE id_testata = ?", (id_testata,))
    db.execute("DELETE FROM ESPORTAZIONI_DETTAGLIO WHERE id_testata = ?", (id_testata,))
    db.execute("DELETE FROM ORDINI_TESTATA WHERE id_testata = ?", (id_testata,))

    db.commit()

    log_operation('DELETE', 'ORDINI_TESTATA', id_testata,
                 f"Eliminato ordine {ordine['numero_ordine_vendor']}")
    return True


def modifica_riga_dettaglio(
    id_testata: int,
    id_dettaglio: int,
    modifiche: Dict[str, Any],
    operatore: str,
    note: Optional[str] = None
) -> Dict[str, Any]:
    """Modifica valori di una riga, salvando backup originale."""
    CAMPI_MODIFICABILI = {
        'codice_aic', 'descrizione',
        'q_venduta', 'q_sconto_merce', 'q_omaggio',
        'prezzo_netto', 'prezzo_pubblico',
        'sconto_1', 'sconto_2', 'sconto_3', 'sconto_4',
        'note_allestimento'
    }

    campi_invalidi = set(modifiche.keys()) - CAMPI_MODIFICABILI
    if campi_invalidi:
        return {'success': False, 'error': f'Campi non modificabili: {campi_invalidi}'}

    db = get_db()
    now = datetime.now().isoformat()

    riga = db.execute("""
        SELECT * FROM ORDINI_DETTAGLIO
        WHERE id_dettaglio = ? AND id_testata = ?
    """, (id_dettaglio, id_testata)).fetchone()

    if not riga:
        return {'success': False, 'error': 'Riga non trovata'}

    riga_dict = dict(riga)

    if not riga_dict.get('valori_originali'):
        valori_originali = {k: riga_dict.get(k) for k in CAMPI_MODIFICABILI}
        valori_originali['_timestamp_backup'] = now
        valori_originali['_operatore_backup'] = operatore
    else:
        valori_originali = None

    set_clauses = []
    params = []
    for campo, valore in modifiche.items():
        set_clauses.append(f"{campo} = ?")
        params.append(valore)

    set_clauses.append("modificato_manualmente = TRUE")
    set_clauses.append("data_conferma = ?")
    params.append(now)

    if valori_originali:
        set_clauses.append("valori_originali = ?")
        params.append(json.dumps(valori_originali, ensure_ascii=False, default=_json_serializer))

    if note:
        set_clauses.append("note_supervisione = COALESCE(note_supervisione || ' | ', '') || ?")
        params.append(f"[{operatore}] {note}")

    params.extend([id_dettaglio, id_testata])

    db.execute(f"""
        UPDATE ORDINI_DETTAGLIO
        SET {', '.join(set_clauses)}
        WHERE id_dettaglio = ? AND id_testata = ?
    """, params)

    db.commit()
    return {'success': True}


# =============================================================================
# ANOMALIE - MODIFICA
# =============================================================================

def _sblocca_ordine_se_anomalie_risolte(id_testata: int) -> bool:
    """Sblocca ordine quando tutte le anomalie sono risolte/ignorate."""
    db = get_db()

    anomalie_aperte = db.execute("""
        SELECT COUNT(*) as cnt FROM anomalie
        WHERE id_testata = ? AND stato IN ('APERTA', 'IN_GESTIONE')
    """, (id_testata,)).fetchone()

    supervisioni_pending = db.execute("""
        SELECT COUNT(*) as cnt FROM supervisione_espositore
        WHERE id_testata = ? AND stato = 'PENDING'
    """, (id_testata,)).fetchone()

    anomalie_cnt = anomalie_aperte['cnt'] if anomalie_aperte else 0
    supervisioni_cnt = supervisioni_pending['cnt'] if supervisioni_pending else 0

    if anomalie_cnt == 0 and supervisioni_cnt == 0:
        result = db.execute("""
            UPDATE ordini_testata
            SET stato = 'ESTRATTO'
            WHERE id_testata = ? AND stato IN ('ANOMALIA', 'PENDING_REVIEW')
            RETURNING id_testata
        """, (id_testata,)).fetchone()

        db.commit()

        if result:
            log_operation(
                'SBLOCCO_ORDINE',
                'ORDINI_TESTATA',
                id_testata,
                'Ordine sbloccato - tutte le anomalie risolte'
            )
            return True

    return False


def update_anomalia_stato(
    id_anomalia: int,
    nuovo_stato: str,
    note: str = None
) -> bool:
    """
    Aggiorna stato anomalia.
    Stati validi: APERTA, IN_GESTIONE, RISOLTA, IGNORATA
    """
    stati_validi = ['APERTA', 'IN_GESTIONE', 'RISOLTA', 'IGNORATA']
    if nuovo_stato not in stati_validi:
        return False

    db = get_db()

    anomalia = db.execute(
        "SELECT tipo_anomalia, id_testata FROM anomalie WHERE id_anomalia = ?",
        (id_anomalia,)
    ).fetchone()

    if nuovo_stato in ('RISOLTA', 'IGNORATA'):
        db.execute("""
            UPDATE anomalie
            SET stato = ?,
                data_risoluzione = CURRENT_TIMESTAMP,
                note_risoluzione = ?
            WHERE id_anomalia = ?
        """, (nuovo_stato, note, id_anomalia))

        sup_stato = 'APPROVED' if nuovo_stato == 'RISOLTA' else 'REJECTED'
        db.execute("""
            UPDATE supervisione_espositore
            SET stato = ?,
                timestamp_decisione = CURRENT_TIMESTAMP,
                note = COALESCE(note || ' - ', '') || 'Risolto da anomalia'
            WHERE id_anomalia = ? AND stato = 'PENDING'
        """, (sup_stato, id_anomalia))
    else:
        db.execute(
            "UPDATE anomalie SET stato = ? WHERE id_anomalia = ?",
            (nuovo_stato, id_anomalia)
        )

    db.commit()

    if anomalia and nuovo_stato == 'RISOLTA':
        tipo = anomalia['tipo_anomalia']
        id_testata = anomalia['id_testata']

        if tipo == 'ESPOSITORE' and id_testata:
            try:
                from ..ml_pattern_matching import registra_pattern_da_anomalia_risolta
                registra_pattern_da_anomalia_risolta(id_anomalia, id_testata)
            except Exception as e:
                log_operation(
                    'ERRORE_ML_PATTERN',
                    'ANOMALIE',
                    id_anomalia,
                    f"Errore registrazione pattern ML: {str(e)}"
                )

    if anomalia and nuovo_stato in ('RISOLTA', 'IGNORATA'):
        id_testata = anomalia['id_testata']
        if id_testata:
            _sblocca_ordine_se_anomalie_risolte(id_testata)

    return True


def create_anomalia(
    id_testata: int = None,
    id_dettaglio: int = None,
    id_acquisizione: int = None,
    tipo: str = 'ALTRO',
    livello: str = 'ATTENZIONE',
    descrizione: str = '',
    valore_anomalo: str = None
) -> int:
    """Crea nuova anomalia manualmente."""
    db = get_db()

    cursor = db.execute("""
        INSERT INTO ANOMALIE
        (id_testata, id_dettaglio, id_acquisizione, tipo_anomalia,
         livello, descrizione, valore_anomalo, stato)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'APERTA')
    """, (id_testata, id_dettaglio, id_acquisizione, tipo,
          livello, descrizione, valore_anomalo))

    db.commit()
    return cursor.lastrowid


# =============================================================================
# v11.0 - ARCHIVIAZIONE CENTRALIZZATA
# =============================================================================

@dataclass
class ArchiviazioneResult:
    """Risultato di un'operazione di archiviazione."""
    success: bool
    id_testata: int = None
    id_dettaglio: int = None
    stato_ordine: str = None
    stato_riga: str = None
    righe_archiviate: int = 0
    anomalie_archiviate: int = 0  # v11.0
    ordine_completato: bool = False
    error: str = ''

    def to_dict(self) -> Dict[str, Any]:
        return {
            'success': self.success,
            'id_testata': self.id_testata,
            'id_dettaglio': self.id_dettaglio,
            'stato_ordine': self.stato_ordine,
            'stato_riga': self.stato_riga,
            'righe_archiviate': self.righe_archiviate,
            'ordine_completato': self.ordine_completato,
            'error': self.error
        }


def archivia_ordine(id_testata: int, operatore: str) -> ArchiviazioneResult:
    """
    Archivia un ordine impostando stato ARCHIVIATO.

    COMPORTAMENTO:
    - Ordine → ARCHIVIATO (freeze manuale)
    - Tutte le righe non EVASO/ARCHIVIATO → ARCHIVIATO
    - Può essere usato per ESTRATTO, CONFERMATO, PARZ_EVASO

    STATI NON ARCHIVIABILI:
    - ARCHIVIATO: già freezato
    - EVASO: completato naturalmente

    Args:
        id_testata: ID ordine
        operatore: Nome operatore che archivia

    Returns:
        ArchiviazioneResult con dettagli operazione
    """
    db = get_db()
    now = datetime.now().isoformat()

    # Verifica stato ordine
    ordine = db.execute("""
        SELECT stato FROM ORDINI_TESTATA WHERE id_testata = %s
    """, (id_testata,)).fetchone()

    if not ordine:
        return ArchiviazioneResult(success=False, error="Ordine non trovato")

    if ordine['stato'] == 'ARCHIVIATO':
        return ArchiviazioneResult(success=False, error="Ordine già archiviato")

    if ordine['stato'] == 'EVASO':
        return ArchiviazioneResult(success=False, error="Ordine già evaso, non archiviabile")

    # Conta righe da archiviare
    righe_da_archiviare = db.execute("""
        SELECT COUNT(*) FROM ORDINI_DETTAGLIO
        WHERE id_testata = %s AND stato_riga NOT IN ('EVASO', 'ARCHIVIATO')
    """, (id_testata,)).fetchone()[0]

    # Aggiorna stato ordine a ARCHIVIATO
    stato_precedente = ordine['stato']
    db.execute("""
        UPDATE ORDINI_TESTATA
        SET stato = 'ARCHIVIATO',
            data_validazione = %s,
            validato_da = %s
        WHERE id_testata = %s
    """, (now, operatore, id_testata))

    # Audit trail ordine
    log_modifica(
        entita='ORDINI_TESTATA',
        id_entita=id_testata,
        campo_modificato='stato',
        valore_precedente=stato_precedente,
        valore_nuovo='ARCHIVIATO',
        fonte_modifica='ARCHIVIAZIONE_ORDINE',
        id_testata=id_testata,
        username_operatore=operatore
    )

    # Aggiorna tutte le righe non ancora EVASO/ARCHIVIATO a ARCHIVIATO
    db.execute("""
        UPDATE ORDINI_DETTAGLIO
        SET stato_riga = 'ARCHIVIATO',
            data_conferma = %s,
            confermato_da = %s,
            q_da_evadere = 0
        WHERE id_testata = %s
          AND stato_riga NOT IN ('EVASO', 'ARCHIVIATO')
    """, (now, operatore, id_testata))

    # v11.0: Archivia tutte le anomalie aperte dell'ordine
    anomalie_archiviate = db.execute("""
        UPDATE anomalie
        SET stato = 'ARCHIVIATA',
            risolto_da = %s,
            data_risoluzione = %s,
            note_risoluzione = COALESCE(note_risoluzione || ' | ', '') || 'Archiviata con ordine'
        WHERE id_testata = %s
          AND stato IN ('APERTA', 'IN_GESTIONE')
        RETURNING id_anomalia
    """, (operatore, now, id_testata)).fetchall()

    # v11.0: Archivia tutte le supervisioni pending dell'ordine
    for table in ['supervisione_espositore', 'supervisione_listino', 'supervisione_lookup',
                  'supervisione_aic', 'supervisione_prezzo']:
        try:
            db.execute(f"""
                UPDATE {table}
                SET stato = 'ARCHIVED',
                    operatore = %s,
                    timestamp_decisione = CURRENT_TIMESTAMP,
                    note = COALESCE(note || ' | ', '') || 'Archiviata con ordine'
                WHERE id_testata = %s AND stato = 'PENDING'
            """, (operatore, id_testata))
        except Exception:
            pass  # Tabella potrebbe non esistere

    db.commit()

    # Log operazione
    num_anomalie = len(anomalie_archiviate) if anomalie_archiviate else 0
    log_operation(
        'ARCHIVIA_ORDINE',
        'ORDINI_TESTATA',
        id_testata,
        f"Ordine archiviato. Righe: {righe_da_archiviare}, Anomalie: {num_anomalie}. Operatore: {operatore}"
    )

    return ArchiviazioneResult(
        success=True,
        id_testata=id_testata,
        stato_ordine='ARCHIVIATO',
        righe_archiviate=righe_da_archiviare,
        anomalie_archiviate=num_anomalie
    )


def archivia_riga(id_testata: int, id_dettaglio: int, operatore: str) -> ArchiviazioneResult:
    """
    Archivia una singola riga impostando stato ARCHIVIATO.

    COMPORTAMENTO:
    - La riga viene "freezata": non è più modificabile
    - Le quantità da evadere vengono azzerate
    - Solo procedure di ripristino possono sbloccarla
    - Può archiviare righe: ESTRATTO, CONFERMATO, PARZIALE

    STATI NON ARCHIVIABILI:
    - EVASO: già processata completamente
    - ARCHIVIATO: già freezata

    NOTA: Quando tutte le righe sono EVASO/ARCHIVIATO, l'ordine diventa EVASO.

    Args:
        id_testata: ID ordine
        id_dettaglio: ID riga
        operatore: Nome operatore che archivia

    Returns:
        ArchiviazioneResult con dettagli operazione
    """
    db = get_db()
    now = datetime.now().isoformat()

    # Verifica stato riga
    riga = db.execute("""
        SELECT stato_riga FROM ORDINI_DETTAGLIO
        WHERE id_dettaglio = %s AND id_testata = %s
    """, (id_dettaglio, id_testata)).fetchone()

    if not riga:
        return ArchiviazioneResult(success=False, error="Riga non trovata")

    if riga['stato_riga'] == 'ARCHIVIATO':
        return ArchiviazioneResult(success=False, error="Riga già archiviata")

    if riga['stato_riga'] == 'EVASO':
        return ArchiviazioneResult(success=False, error="Riga già evasa, non archiviabile")

    stato_precedente = riga['stato_riga']

    # Aggiorna stato riga a ARCHIVIATO (freeze)
    db.execute("""
        UPDATE ORDINI_DETTAGLIO
        SET stato_riga = 'ARCHIVIATO',
            data_conferma = %s,
            confermato_da = %s,
            q_da_evadere = 0
        WHERE id_dettaglio = %s AND id_testata = %s
    """, (now, operatore, id_dettaglio, id_testata))

    # Audit trail riga
    log_modifica(
        entita='ORDINI_DETTAGLIO',
        id_entita=id_dettaglio,
        campo_modificato='stato_riga',
        valore_precedente=stato_precedente,
        valore_nuovo='ARCHIVIATO',
        fonte_modifica='ARCHIVIAZIONE_RIGA',
        id_testata=id_testata,
        username_operatore=operatore
    )

    # Verifica se tutte le righe sono EVASO o ARCHIVIATO -> ordine diventa EVASO
    righe_attive = db.execute("""
        SELECT COUNT(*) FROM ORDINI_DETTAGLIO
        WHERE id_testata = %s AND stato_riga NOT IN ('EVASO', 'ARCHIVIATO')
    """, (id_testata,)).fetchone()[0]

    ordine_completato = False
    if righe_attive == 0:
        # Tutte le righe sono EVASO o ARCHIVIATO → ordine EVASO (completato)
        ordine_row = db.execute("""
            SELECT stato FROM ORDINI_TESTATA WHERE id_testata = %s
        """, (id_testata,)).fetchone()

        if ordine_row and ordine_row['stato'] != 'EVASO':
            stato_ordine_precedente = ordine_row['stato']
            db.execute("""
                UPDATE ORDINI_TESTATA
                SET stato = 'EVASO',
                    data_validazione = %s,
                    validato_da = %s
                WHERE id_testata = %s
            """, (now, operatore, id_testata))

            log_modifica(
                entita='ORDINI_TESTATA',
                id_entita=id_testata,
                campo_modificato='stato',
                valore_precedente=stato_ordine_precedente,
                valore_nuovo='EVASO',
                fonte_modifica='AUTO_COMPLETAMENTO',
                id_testata=id_testata,
                username_operatore=operatore
            )
            ordine_completato = True

    db.commit()

    # Log operazione
    log_operation(
        'ARCHIVIA_RIGA',
        'ORDINI_DETTAGLIO',
        id_dettaglio,
        f"Riga archiviata. Ordine: {id_testata}. Operatore: {operatore}"
    )

    return ArchiviazioneResult(
        success=True,
        id_testata=id_testata,
        id_dettaglio=id_dettaglio,
        stato_riga='ARCHIVIATO',
        ordine_completato=ordine_completato
    )
