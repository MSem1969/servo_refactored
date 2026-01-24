# =============================================================================
# SERV.O v8.2 - SUPERVISIONE LOOKUP
# =============================================================================
# Endpoint per gestione supervisione lookup (LKP-A01/A02/A04)
# =============================================================================

from fastapi import APIRouter, HTTPException

from ...database_pg import get_db
from .schemas import RisoluzioneLookupRequest, DecisioneRifiuta


router = APIRouter(prefix="/lookup", tags=["Supervisione Lookup"])


# =============================================================================
# ENDPOINT SUPERVISIONE LOOKUP
# =============================================================================

@router.get("/{id_supervisione}", summary="Dettaglio supervisione lookup")
async def get_supervisione_lookup_detail(id_supervisione: int):
    """
    Ritorna dettagli supervisione lookup con suggerimenti farmacia.

    Include:
    - Dati anomalia (P.IVA estratta, metodo, score)
    - Suggerimenti farmacie simili dall'anagrafica
    - Pattern ML se esistente
    """
    db = get_db()

    # Recupera supervisione lookup
    sup = db.execute("""
        SELECT slk.*, colk.pattern_descrizione, colk.count_approvazioni, colk.is_ordinario
        FROM supervisione_lookup slk
        LEFT JOIN criteri_ordinari_lookup colk ON slk.pattern_signature = colk.pattern_signature
        WHERE slk.id_supervisione = %s
    """, (id_supervisione,)).fetchone()

    if not sup:
        raise HTTPException(status_code=404, detail="Supervisione lookup non trovata")

    sup = dict(sup)

    # Cerca farmacie suggerite per P.IVA parziale o simile
    suggerimenti = []
    if sup.get('partita_iva_estratta'):
        piva = sup['partita_iva_estratta']
        rows = db.execute("""
            SELECT id_farmacia, min_id, ragione_sociale, partita_iva, indirizzo, citta, provincia
            FROM anagrafica_farmacie
            WHERE partita_iva LIKE %s OR partita_iva = %s
            ORDER BY similarity(partita_iva, %s) DESC
            LIMIT 10
        """, (f"{piva}%", piva, piva)).fetchall()
        suggerimenti = [dict(r) for r in rows]

    return {
        **sup,
        "suggerimenti_farmacie": suggerimenti
    }


@router.post("/{id_supervisione}/risolvi", summary="Risolvi supervisione lookup")
async def risolvi_lookup(id_supervisione: int, req: RisoluzioneLookupRequest):
    """
    Risolve supervisione lookup assegnando farmacia.

    Effetti:
    - Supervisione -> APPROVED
    - Ordine aggiornato con MIN ID e id_farmacia selezionata
    - Pattern ML incrementato
    - Ordine sbloccato se non ha altre supervisioni pending
    """
    from ...services.supervision.lookup import approva_supervisione_lookup

    success = approva_supervisione_lookup(
        id_supervisione,
        req.operatore,
        req.min_id,
        req.id_farmacia,
        req.note
    )

    if not success:
        raise HTTPException(status_code=404, detail="Supervisione lookup non trovata")

    return {
        "success": True,
        "id_supervisione": id_supervisione,
        "azione": "APPROVED",
        "operatore": req.operatore,
        "min_id_assegnato": req.min_id
    }


@router.post("/{id_supervisione}/rifiuta", summary="Rifiuta supervisione lookup")
async def rifiuta_lookup(id_supervisione: int, decisione: DecisioneRifiuta):
    """
    Rifiuta supervisione lookup.

    Effetti:
    - Supervisione -> REJECTED
    - Pattern ML resettato
    - Ordine sbloccato
    """
    from ...services.supervision.lookup import rifiuta_supervisione_lookup

    success = rifiuta_supervisione_lookup(
        id_supervisione,
        decisione.operatore,
        decisione.note
    )

    if not success:
        raise HTTPException(status_code=404, detail="Supervisione lookup non trovata")

    return {
        "success": True,
        "id_supervisione": id_supervisione,
        "azione": "REJECTED",
        "operatore": decisione.operatore,
        "note": decisione.note
    }
