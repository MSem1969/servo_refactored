# =============================================================================
# SERV.O v8.1 - SUPERVISIONE BULK
# =============================================================================
# Endpoint per operazioni bulk e gestione pending raggruppata per pattern
# =============================================================================

from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from ...database_pg import (
    get_db,
    get_supervisione_pending,
    get_supervisione_listino_pending,
    get_supervisione_lookup_pending,
    count_supervisioni_espositore_pending,
    count_supervisioni_listino_pending,
    count_supervisioni_lookup_pending,
)
from .schemas import DecisioneApprova, DecisioneRifiuta


router = APIRouter(tags=["Supervisione Pending/Bulk"])


# =============================================================================
# ENDPOINT SUPERVISIONI PENDING
# =============================================================================

@router.get("/pending", summary="Lista supervisioni in attesa")
async def get_pending(tipo: Optional[str] = Query(None, description="Tipo: 'espositore', 'listino', 'lookup', 'prezzo', 'aic' o None per tutti")):
    """
    Ritorna lista di tutte le supervisioni in attesa di revisione.

    Include informazioni su ordine, pattern, e conteggio approvazioni pattern.
    Supporta anomalie espositore, listino, lookup (v8.0), prezzo (v8.1) e aic (v9.0).

    Parametri:
    - tipo: filtra per tipo (espositore/listino/lookup/prezzo/aic) o ritorna tutti se None
    """
    db = get_db()

    if tipo == 'espositore':
        supervisioni = get_supervisione_pending()
        return {
            "count": len(supervisioni),
            "tipo": "espositore",
            "supervisioni": supervisioni
        }
    elif tipo == 'listino':
        supervisioni = get_supervisione_listino_pending()
        return {
            "count": len(supervisioni),
            "tipo": "listino",
            "supervisioni": supervisioni
        }
    elif tipo == 'lookup':
        supervisioni = get_supervisione_lookup_pending()
        return {
            "count": len(supervisioni),
            "tipo": "lookup",
            "supervisioni": supervisioni
        }
    elif tipo == 'prezzo':
        rows = db.execute("""
            SELECT sp.*,
                   ot.numero_ordine_vendor,
                   ot.ragione_sociale_1,
                   ot.data_ordine
            FROM supervisione_prezzo sp
            JOIN ordini_testata ot ON sp.id_testata = ot.id_testata
            WHERE sp.stato = 'PENDING'
            ORDER BY sp.timestamp_creazione DESC
        """).fetchall()
        return {
            "count": len(rows),
            "tipo": "prezzo",
            "supervisioni": [dict(r) for r in rows]
        }
    elif tipo == 'aic':
        rows = db.execute("""
            SELECT sa.*,
                   ot.numero_ordine_vendor as numero_ordine,
                   ot.ragione_sociale_1 as ragione_sociale,
                   ot.data_ordine
            FROM supervisione_aic sa
            JOIN ordini_testata ot ON sa.id_testata = ot.id_testata
            WHERE sa.stato = 'PENDING'
            ORDER BY sa.timestamp_creazione DESC
        """).fetchall()
        return {
            "count": len(rows),
            "tipo": "aic",
            "supervisioni": [dict(r) for r in rows]
        }
    else:
        # Ritorna tutti i tipi
        esp_supervisioni = get_supervisione_pending()
        listino_supervisioni = get_supervisione_listino_pending()
        lookup_supervisioni = get_supervisione_lookup_pending()

        prezzo_rows = db.execute("""
            SELECT sp.*,
                   ot.numero_ordine_vendor,
                   ot.ragione_sociale_1,
                   ot.data_ordine
            FROM supervisione_prezzo sp
            JOIN ordini_testata ot ON sp.id_testata = ot.id_testata
            WHERE sp.stato = 'PENDING'
            ORDER BY sp.timestamp_creazione DESC
        """).fetchall()
        prezzo_supervisioni = [dict(r) for r in prezzo_rows]

        # v9.0: Aggiungi AIC
        aic_rows = db.execute("""
            SELECT sa.*,
                   ot.numero_ordine_vendor as numero_ordine,
                   ot.ragione_sociale_1 as ragione_sociale,
                   ot.data_ordine
            FROM supervisione_aic sa
            JOIN ordini_testata ot ON sa.id_testata = ot.id_testata
            WHERE sa.stato = 'PENDING'
            ORDER BY sa.timestamp_creazione DESC
        """).fetchall()
        aic_supervisioni = [dict(r) for r in aic_rows]

        # Aggiungi tipo per identificazione frontend
        for s in esp_supervisioni:
            s['tipo_supervisione'] = 'espositore'
        for s in listino_supervisioni:
            s['tipo_supervisione'] = 'listino'
        for s in lookup_supervisioni:
            s['tipo_supervisione'] = 'lookup'
        for s in prezzo_supervisioni:
            s['tipo_supervisione'] = 'prezzo'
        for s in aic_supervisioni:
            s['tipo_supervisione'] = 'aic'

        all_supervisioni = esp_supervisioni + listino_supervisioni + lookup_supervisioni + prezzo_supervisioni + aic_supervisioni

        return {
            "count": len(all_supervisioni),
            "count_espositore": len(esp_supervisioni),
            "count_listino": len(listino_supervisioni),
            "count_lookup": len(lookup_supervisioni),
            "count_prezzo": len(prezzo_supervisioni),
            "count_aic": len(aic_supervisioni),
            "supervisioni": all_supervisioni
        }


@router.get("/pending/count", summary="Conteggio supervisioni pending")
async def get_pending_count():
    """Ritorna conteggio delle supervisioni pending per tipo."""
    db = get_db()

    count_prezzo = db.execute("""
        SELECT COUNT(*) FROM supervisione_prezzo WHERE stato = 'PENDING'
    """).fetchone()[0]

    count_aic = db.execute("""
        SELECT COUNT(*) FROM supervisione_aic WHERE stato = 'PENDING'
    """).fetchone()[0]

    count_esp = count_supervisioni_espositore_pending()
    count_lst = count_supervisioni_listino_pending()
    count_lkp = count_supervisioni_lookup_pending()

    return {
        "count": count_esp + count_lst + count_lkp + count_prezzo + count_aic,
        "count_espositore": count_esp,
        "count_listino": count_lst,
        "count_lookup": count_lkp,
        "count_prezzo": count_prezzo,
        "count_aic": count_aic,
    }


# =============================================================================
# ENDPOINT RAGGRUPPAMENTO PER PATTERN
# =============================================================================

@router.get("/pending/grouped", summary="Supervisioni raggruppate per pattern")
async def get_pending_grouped():
    """
    Ritorna supervisioni pending raggruppate per pattern_signature.

    Ogni gruppo include:
    - pattern_signature: Identificativo univoco pattern
    - tipo_supervisione: espositore/listino/lookup
    - total_count: Numero supervisioni nel gruppo
    - affected_order_ids: Lista ID ordini coinvolti
    - affected_orders_preview: Preview numeri ordine (es: "123, 456, 789")
    - pattern_count: Contatore approvazioni ML
    - pattern_ordinario: Se il pattern e automatico

    Usato per approvazione bulk: approvando un pattern si risolvono
    tutte le supervisioni con quel pattern.
    """
    from ...services.supervision.bulk import get_supervisioni_grouped_pending

    groups = get_supervisioni_grouped_pending()

    return {
        "count": len(groups),
        "total_supervisioni": sum(g.get('total_count', 0) for g in groups),
        "groups": groups
    }


# =============================================================================
# ENDPOINT BULK OPERATIONS
# =============================================================================

@router.post("/pattern/{pattern_signature}/approva-bulk", summary="Approva bulk per pattern")
async def approva_pattern_bulk(pattern_signature: str, decisione: DecisioneApprova):
    """
    Approva TUTTE le supervisioni pending con un dato pattern.

    Effetti:
    - Stato di tutte le supervisioni -> APPROVED
    - Pattern ML incrementato di 1 (non N per N supervisioni)
    - Tutti gli ordini coinvolti vengono sbloccati se non hanno altre supervisioni pending

    Args:
        pattern_signature: Signature del pattern da approvare
        decisione: Operatore e note opzionali

    Returns:
        Conteggio per tipo (espositore, listino, lookup) e lista ordini sbloccati
    """
    from ...services.supervision.bulk import approva_pattern_bulk as do_approva_bulk

    results = do_approva_bulk(
        pattern_signature,
        decisione.operatore,
        decisione.note
    )

    if results['total'] == 0:
        raise HTTPException(
            status_code=404,
            detail=f"Nessuna supervisione pending trovata per pattern {pattern_signature}"
        )

    return {
        "success": True,
        "pattern_signature": pattern_signature,
        "azione": "APPROVED_BULK",
        "operatore": decisione.operatore,
        "approvate": results
    }


@router.post("/pattern/{pattern_signature}/rifiuta-bulk", summary="Rifiuta bulk per pattern")
async def rifiuta_pattern_bulk(pattern_signature: str, decisione: DecisioneRifiuta):
    """
    Rifiuta TUTTE le supervisioni pending con un dato pattern.

    Effetti:
    - Stato di tutte le supervisioni -> REJECTED
    - Pattern ML resettato a 0
    - Gli ordini coinvolti rimangono bloccati (richiede intervento manuale)

    Args:
        pattern_signature: Signature del pattern da rifiutare
        decisione: Operatore e note (obbligatorie per motivazione)

    Returns:
        Conteggio per tipo
    """
    from ...services.supervision.bulk import rifiuta_pattern_bulk as do_rifiuta_bulk

    results = do_rifiuta_bulk(
        pattern_signature,
        decisione.operatore,
        decisione.note
    )

    if results['total'] == 0:
        raise HTTPException(
            status_code=404,
            detail=f"Nessuna supervisione pending trovata per pattern {pattern_signature}"
        )

    return {
        "success": True,
        "pattern_signature": pattern_signature,
        "azione": "REJECTED_BULK",
        "operatore": decisione.operatore,
        "note": decisione.note,
        "rifiutate": results
    }
