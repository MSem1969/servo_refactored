# =============================================================================
# SERV.O v11.4 - AIC APPROVAL/REJECTION
# =============================================================================
# Funzioni per approvazione e rifiuto supervisioni AIC
# =============================================================================

from typing import Dict

from ....database_pg import get_db, log_operation
from .models import LivelloPropagazione
from .propagation import AICPropagator


SOGLIA_PROMOZIONE = 3


def _registra_approvazione_pattern_aic(pattern_sig: str, operatore: str, codice_aic: str):
    """
    Registra approvazione nel pattern ML AIC.
    Incrementa contatore e promuove se raggiunge soglia.
    Standalone wrapper usato da anomalies/commands.py.
    """
    db = get_db()

    db.execute("""
        UPDATE criteri_ordinari_aic
        SET count_approvazioni = count_approvazioni + 1,
            operatori_approvatori = COALESCE(operatori_approvatori || ',', '') || %s,
            codice_aic_default = COALESCE(codice_aic_default, %s)
        WHERE pattern_signature = %s
    """, (operatore, codice_aic, pattern_sig))

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
    Azzera il contatore approvazioni e rimuove stato ordinario.
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


def rifiuta_supervisione_aic(
    id_supervisione: int,
    operatore: str,
    note: str
) -> Dict:
    """
    Rifiuta supervisione AIC.
    Il rifiuto resetta il pattern ML.

    Args:
        id_supervisione: ID supervisione
        operatore: Username operatore
        note: Motivo del rifiuto (obbligatorio)

    Returns:
        Dict con success e dettagli
    """
    db = get_db()

    if not note or len(note) < 5:
        return {'success': False, 'error': "Motivo del rifiuto obbligatorio (minimo 5 caratteri)"}

    # Recupera dati supervisione
    sup = db.execute("""
        SELECT id_testata, pattern_signature, stato
        FROM supervisione_aic
        WHERE id_supervisione = %s
    """, (id_supervisione,)).fetchone()

    if not sup:
        return {'success': False, 'error': f"Supervisione AIC {id_supervisione} non trovata"}

    if sup['stato'] != 'PENDING':
        return {'success': False, 'error': f"Supervisione non in stato PENDING"}

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
    from ..requests import sblocca_ordine_se_completo
    sblocca_ordine_se_completo(sup['id_testata'])

    log_operation(
        'RIFIUTA_SUPERVISIONE',
        'SUPERVISIONE_AIC',
        id_supervisione,
        f"Rifiutata: {note[:50]}"
    )

    return {'success': True, 'id_supervisione': id_supervisione}


def approva_supervisione_aic(
    id_supervisione: int,
    operatore: str,
    codice_aic: str,
    livello_propagazione: str = 'GLOBALE',
    note: str = None
) -> Dict:
    """
    Wrapper per AICPropagator.risolvi_da_supervisione().
    Mantiene firma retrocompatibile.

    Args:
        id_supervisione: ID supervisione
        operatore: Username operatore
        codice_aic: Codice AIC da assegnare
        livello_propagazione: ORDINE o GLOBALE (default GLOBALE)
        note: Note opzionali

    Returns:
        Dict con risultato approvazione
    """
    livello = LivelloPropagazione(livello_propagazione.upper())
    result = AICPropagator().risolvi_da_supervisione(
        id_supervisione, codice_aic, livello, operatore, note
    )
    # Formato risposta originale
    return {
        'approvata': result.success,
        'righe_aggiornate': result.righe_aggiornate,
        'ordini_coinvolti': result.ordini_coinvolti,
        'codice_aic': result.codice_aic,
        'success': result.success,
        'error': result.error
    }


def approva_bulk_pattern_aic(
    pattern_signature: str,
    codice_aic: str,
    operatore: str,
    note: str = None
) -> Dict:
    """
    Wrapper per AICPropagator.approva_bulk_pattern().

    Args:
        pattern_signature: Signature del pattern
        codice_aic: Codice AIC da assegnare
        operatore: Username operatore
        note: Note opzionali

    Returns:
        Dict con risultato approvazione bulk
    """
    return AICPropagator().approva_bulk_pattern(
        pattern_signature, codice_aic, operatore, note
    ).to_dict()
