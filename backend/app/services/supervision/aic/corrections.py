# =============================================================================
# SERV.O v11.4 - AIC CORRECTIONS
# =============================================================================
# Funzioni per correzione errori AIC
# =============================================================================

from typing import Dict

from ....database_pg import get_db, log_operation, log_modifica
from .validation import valida_codice_aic


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
        operatore: Username operatore
        note: Note opzionali sulla correzione

    Returns:
        Dict con risultati: success, righe_corrette, ordini_coinvolti, error
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
