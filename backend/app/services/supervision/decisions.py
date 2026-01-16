# =============================================================================
# SERV.O v7.0 - SUPERVISION DECISIONS
# =============================================================================
# Gestione decisioni di supervisione (approve/reject/modify)
# =============================================================================

import json
from typing import Dict

from ...database_pg import get_db, log_operation
from ..ml_pattern_matching import normalizza_descrizione_espositore, salva_sequenza_child_pattern
from .requests import sblocca_ordine_se_completo
from .ml import registra_approvazione_pattern, registra_rifiuto_pattern


def approva_supervisione(id_supervisione: int, operatore: str, note: str = None) -> bool:
    """
    Approva una richiesta di supervisione.

    Effetti:
    1. Aggiorna stato a APPROVED
    2. Registra approvazione nel pattern ML
    3. Se raggiunta soglia, promuove pattern a ordinario
    4. Sblocca ordine se era l'ultima supervisione pending
    5. v6.2: Salva sequenza child nel pattern per ML

    Args:
        id_supervisione: ID supervisione
        operatore: Username operatore
        note: Note opzionali

    Returns:
        True se successo
    """
    db = get_db()

    # Recupera dati supervisione
    sup = db.execute(
        "SELECT * FROM SUPERVISIONE_ESPOSITORE WHERE id_supervisione = ?",
        (id_supervisione,)
    ).fetchone()

    if not sup:
        return False

    sup = dict(sup)

    # Aggiorna stato supervisione
    db.execute("""
        UPDATE SUPERVISIONE_ESPOSITORE
        SET stato = 'APPROVED',
            operatore = ?,
            timestamp_decisione = CURRENT_TIMESTAMP,
            note = ?
        WHERE id_supervisione = ?
    """, (operatore, note, id_supervisione))

    # Registra approvazione pattern
    registra_approvazione_pattern(sup['pattern_signature'], operatore)

    # v6.2: Estrai e salva sequenza child per ML
    _salva_child_sequence_da_supervisione(db, sup)

    db.commit()

    # Sblocca ordine se completo
    sblocca_ordine_se_completo(sup['id_testata'])

    log_operation(
        'APPROVA_SUPERVISIONE',
        'SUPERVISIONE_ESPOSITORE',
        id_supervisione,
        f"Approvato",
        operatore=operatore
    )

    return True


def _salva_child_sequence_da_supervisione(db, sup: dict) -> None:
    """
    Estrae child confermati da supervisione e salva nel pattern ML.

    v6.2: Chiamata dopo approvazione supervisione per alimentare
    l'apprendimento ML con la sequenza child corretta.

    Args:
        db: Connessione database
        sup: Dizionario supervisione con id_testata e codice_espositore
    """
    # Trova il dettaglio espositore parent
    parent = db.execute("""
        SELECT id_dettaglio, descrizione
        FROM ordini_dettaglio
        WHERE id_testata = ?
          AND codice_originale = ?
          AND is_espositore = TRUE
        LIMIT 1
    """, (sup['id_testata'], sup['codice_espositore'])).fetchone()

    if not parent:
        return

    parent = dict(parent)

    # Estrai tutti i child di questo parent
    children = db.execute("""
        SELECT codice_aic, codice_originale, descrizione, q_venduta AS quantita
        FROM ordini_dettaglio
        WHERE id_testata = ?
          AND id_parent_espositore = ?
          AND is_child = TRUE
        ORDER BY n_riga
    """, (sup['id_testata'], parent['id_dettaglio'])).fetchall()

    if not children:
        return

    # Prepara sequenza child per salvataggio
    child_sequence = [
        {
            'aic': row['codice_aic'],
            'codice': row['codice_originale'],
            'descrizione': row['descrizione'],
            'quantita': row['quantita']
        }
        for row in children
    ]

    # Normalizza descrizione espositore
    desc_norm = normalizza_descrizione_espositore(parent['descrizione'])

    # Salva nel pattern
    salva_sequenza_child_pattern(
        pattern_signature=sup['pattern_signature'],
        child_sequence=child_sequence,
        descrizione_normalizzata=desc_norm
    )


def rifiuta_supervisione(id_supervisione: int, operatore: str, note: str = None) -> bool:
    """
    Rifiuta una richiesta di supervisione.

    Effetti:
    1. Aggiorna stato a REJECTED
    2. Reset conteggio approvazioni pattern
    3. Sblocca ordine se era l'ultima supervisione pending (v6.2.4 fix)

    Args:
        id_supervisione: ID supervisione
        operatore: Username operatore
        note: Note opzionali (obbligatorie per motivazione)

    Returns:
        True se successo
    """
    db = get_db()

    # Recupera dati supervisione
    sup = db.execute(
        "SELECT * FROM SUPERVISIONE_ESPOSITORE WHERE id_supervisione = ?",
        (id_supervisione,)
    ).fetchone()

    if not sup:
        return False

    sup = dict(sup)

    # Aggiorna stato supervisione
    db.execute("""
        UPDATE SUPERVISIONE_ESPOSITORE
        SET stato = 'REJECTED',
            operatore = ?,
            timestamp_decisione = datetime('now'),
            note = ?
        WHERE id_supervisione = ?
    """, (operatore, note, id_supervisione))

    # Reset pattern (rifiuto invalida apprendimento precedente)
    registra_rifiuto_pattern(sup['pattern_signature'])

    db.commit()

    # v6.2.4: Sblocca ordine se non ci sono piu supervisioni pending
    sblocca_ordine_se_completo(sup['id_testata'])

    log_operation(
        'RIFIUTA_SUPERVISIONE',
        'SUPERVISIONE_ESPOSITORE',
        id_supervisione,
        f"Rifiutato: {note}",
        operatore=operatore
    )

    return True


def modifica_supervisione(
    id_supervisione: int,
    operatore: str,
    modifiche: Dict,
    note: str = None
) -> bool:
    """
    Modifica manualmente i dati di un ordine in supervisione.

    Effetti:
    1. Salva modifiche in modifiche_manuali_json
    2. Aggiorna stato a MODIFIED
    3. NON conta come approvazione pattern (caso speciale)

    Args:
        id_supervisione: ID supervisione
        operatore: Username operatore
        modifiche: Dizionario modifiche applicate
        note: Note opzionali

    Returns:
        True se successo
    """
    db = get_db()

    # Recupera dati supervisione
    sup = db.execute(
        "SELECT * FROM SUPERVISIONE_ESPOSITORE WHERE id_supervisione = ?",
        (id_supervisione,)
    ).fetchone()

    if not sup:
        return False

    sup = dict(sup)

    # Aggiorna stato supervisione
    db.execute("""
        UPDATE SUPERVISIONE_ESPOSITORE
        SET stato = 'MODIFIED',
            operatore = ?,
            timestamp_decisione = datetime('now'),
            note = ?,
            modifiche_manuali_json = ?
        WHERE id_supervisione = ?
    """, (operatore, note, json.dumps(modifiche), id_supervisione))

    db.commit()

    # Sblocca ordine
    sblocca_ordine_se_completo(sup['id_testata'])

    log_operation(
        'MODIFICA_SUPERVISIONE',
        'SUPERVISIONE_ESPOSITORE',
        id_supervisione,
        f"Modificato",
        operatore=operatore
    )

    return True
