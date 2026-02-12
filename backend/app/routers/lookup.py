# =============================================================================
# SERV.O v6.0 - LOOKUP ROUTER
# =============================================================================
# Endpoint per lookup farmacia manuale e batch
# =============================================================================

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from ..services.lookup import (
    lookup_farmacia,
    run_lookup_batch,
    lookup_manuale,
    get_pending_lookup,
    search_farmacie,
    search_parafarmacie,
    get_alternative_lookup_by_piva,
)


router = APIRouter(prefix="/lookup")


# =============================================================================
# MODELLI
# =============================================================================

class LookupRequest(BaseModel):
    partita_iva: Optional[str] = None
    ragione_sociale: Optional[str] = None
    indirizzo: Optional[str] = None
    citta: Optional[str] = None
    cap: Optional[str] = None


class LookupManualeRequest(BaseModel):
    id_farmacia: Optional[int] = None
    id_parafarmacia: Optional[int] = None
    min_id_manuale: Optional[str] = None  # v6.2: MIN_ID inserito manualmente
    operatore: Optional[str] = None  # v11.5: Operatore per audit e supervisione
    deposito_riferimento: Optional[str] = None  # v11.6: Deposito selezionato dall'operatore


# =============================================================================
# LOOKUP TEST
# =============================================================================

@router.post("/test")
async def test_lookup(request: LookupRequest) -> Dict[str, Any]:
    """
    Testa il lookup farmacia con i dati forniti.
    
    Utile per verificare se un ordine troverà corrispondenza.
    
    Ritorna metodo lookup, source (FARMACIA/PARAFARMACIA) e score.
    """
    try:
        data = {
            'partita_iva': request.partita_iva,
            'ragione_sociale': request.ragione_sociale,
            'indirizzo': request.indirizzo,
            'citta': request.citta,
            'cap': request.cap,
        }
        
        id_farm, id_parafarm, method, source, score = lookup_farmacia(data)
        
        result = {
            "found": method != 'NESSUNO',
            "method": method,
            "source": source,
            "score": score,
            "id_farmacia": id_farm,
            "id_parafarmacia": id_parafarm,
        }
        
        # Se trovato, aggiungi dettagli
        if id_farm:
            from ..services.anagrafica import get_farmacia_by_id
            farmacia = get_farmacia_by_id(id_farm)
            if farmacia:
                result["match"] = {
                    "min_id": farmacia.get('min_id'),
                    "ragione_sociale": farmacia.get('ragione_sociale'),
                    "indirizzo": farmacia.get('indirizzo'),
                    "citta": farmacia.get('citta'),
                    "provincia": farmacia.get('provincia'),
                }
        elif id_parafarm:
            from ..services.anagrafica import get_parafarmacia_by_id
            parafarmacia = get_parafarmacia_by_id(id_parafarm)
            if parafarmacia:
                result["match"] = {
                    "codice_sito": parafarmacia.get('codice_sito'),
                    "ragione_sociale": parafarmacia.get('sito_logistico'),
                    "indirizzo": parafarmacia.get('indirizzo'),
                    "citta": parafarmacia.get('citta'),
                    "provincia": parafarmacia.get('provincia'),
                }
        
        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# LOOKUP BATCH
# =============================================================================

@router.post("/batch")
async def esegui_lookup_batch(
    limit: int = Query(100, ge=1, le=1000, description="Max ordini da processare")
) -> Dict[str, Any]:
    """
    Esegue lookup batch su ordini con lookup_method = 'NESSUNO'.
    
    Utile per ritentare lookup dopo aver aggiornato l'anagrafica.
    """
    try:
        stats = run_lookup_batch(limit)
        
        return {
            "success": True,
            "data": stats,
            "message": f"Processati {stats['processati']}, successi {stats['successi']}, falliti {stats['falliti']}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# LOOKUP MANUALE
# =============================================================================

@router.put("/manuale/{id_testata}")
async def assegna_manuale(
    id_testata: int,
    request: LookupManualeRequest
) -> Dict[str, Any]:
    """
    Assegna manualmente una farmacia/parafarmacia a un ordine.

    Richiede:
    - id_farmacia OPPURE id_parafarmacia (da ricerca database)
    - OPPURE min_id_manuale (inserimento diretto codice ministeriale)
    """
    # v6.2: Supporto MIN_ID manuale
    if request.min_id_manuale:
        # Inserimento manuale del codice ministeriale
        try:
            success = lookup_manuale(
                id_testata=id_testata,
                id_farmacia=None,
                id_parafarmacia=None,
                min_id_manuale=request.min_id_manuale,
                operatore=request.operatore,
                deposito_riferimento=request.deposito_riferimento
            )

            if not success:
                raise HTTPException(status_code=404, detail="Ordine non trovato")

            return {
                "success": True,
                "message": f"MIN_ID {request.min_id_manuale} assegnato manualmente"
            }
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # Assegnazione da database (farmacia o parafarmacia)
    if not request.id_farmacia and not request.id_parafarmacia:
        raise HTTPException(
            status_code=400,
            detail="Specificare id_farmacia, id_parafarmacia, oppure min_id_manuale"
        )

    if request.id_farmacia and request.id_parafarmacia:
        raise HTTPException(
            status_code=400,
            detail="Specificare solo id_farmacia OPPURE id_parafarmacia, non entrambi"
        )

    try:
        success = lookup_manuale(
            id_testata=id_testata,
            id_farmacia=request.id_farmacia,
            id_parafarmacia=request.id_parafarmacia,
            operatore=request.operatore,
            deposito_riferimento=request.deposito_riferimento
        )

        if not success:
            raise HTTPException(status_code=404, detail="Ordine non trovato")

        return {
            "success": True,
            "message": "Assegnazione completata"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# ORDINI PENDENTI
# =============================================================================

@router.get("/pending")
async def ordini_pendenti(
    limit: int = Query(50, ge=1, le=200)
) -> Dict[str, Any]:
    """
    Ritorna ordini in attesa di lookup (lookup_method = 'NESSUNO').
    """
    try:
        ordini = get_pending_lookup(limit)
        return {
            "success": True,
            "data": ordini,
            "count": len(ordini)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# RICERCA ANAGRAFICA (per assegnazione manuale)
# =============================================================================

@router.get("/search/farmacie")
async def cerca_farmacie(
    q: str = Query(..., min_length=2, description="Testo da cercare"),
    limit: int = Query(20, ge=1, le=100)
) -> Dict[str, Any]:
    """
    Ricerca farmacie per assegnazione manuale.
    
    Cerca in: ragione_sociale, città, P.IVA, MIN_ID
    """
    try:
        farmacie = search_farmacie(q, limit)
        return {
            "success": True,
            "data": farmacie,
            "count": len(farmacie)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search/parafarmacie")
async def cerca_parafarmacie(
    q: str = Query(..., min_length=2, description="Testo da cercare"),
    limit: int = Query(20, ge=1, le=100)
) -> Dict[str, Any]:
    """
    Ricerca parafarmacie per assegnazione manuale.
    
    Cerca in: sito_logistico, città, P.IVA, codice_sito
    """
    try:
        parafarmacie = search_parafarmacie(q, limit)
        return {
            "success": True,
            "data": parafarmacie,
            "count": len(parafarmacie)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# v6.2.5: ALTERNATIVE LOOKUP PER P.IVA (multipunto)
# =============================================================================

@router.get("/alternative/{id_testata}")
async def get_lookup_alternatives(id_testata: int) -> Dict[str, Any]:
    """
    Restituisce le alternative di lookup per un ordine con P.IVA ambigua/multipunto.

    Quando la P.IVA è stata rilevata correttamente ma corrisponde a più
    farmacie/parafarmacie (PIVA_AMBIGUA, PIVA_MULTIPUNTO), questo endpoint
    restituisce SOLO le alternative con la stessa P.IVA estratta dall'ordine.

    Ogni alternativa include:
    - Dati anagrafici (indirizzo, città, ecc.)
    - fuzzy_score: score di matching con i dati ordine (0-100)
    - is_selected: se è la farmacia attualmente assegnata

    Le alternative sono ordinate per fuzzy_score decrescente.

    Args:
        id_testata: ID dell'ordine

    Returns:
        - ordine_data: dati estratti dall'ordine
        - farmacie: lista farmacie con stessa P.IVA
        - parafarmacie: lista parafarmacie con stessa P.IVA
        - totale_alternative: numero totale
        - piva_bloccata: P.IVA usata per il filtro
    """
    try:
        result = get_alternative_lookup_by_piva(id_testata)

        if not result.get('success', True):
            if result.get('error') == 'Ordine non trovato':
                raise HTTPException(status_code=404, detail="Ordine non trovato")
            return {
                "success": False,
                "error": result.get('error', 'Errore sconosciuto'),
                "data": result
            }

        return {
            "success": True,
            "data": result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# STATISTICHE
# =============================================================================

@router.get("/stats")
async def lookup_statistics() -> Dict[str, Any]:
    """
    Ritorna statistiche lookup.
    """
    from ..database_pg import get_db

    db = get_db()

    stats = {}
    rows = db.execute("""
        SELECT lookup_method, COUNT(*) as count 
        FROM ORDINI_TESTATA 
        GROUP BY lookup_method
    """).fetchall()
    
    for row in rows:
        stats[row['lookup_method'] or 'NULL'] = row['count']
    
    # Calcola percentuali
    total = sum(stats.values())
    percentages = {}
    if total > 0:
        for method, count in stats.items():
            percentages[method] = round(count / total * 100, 1)
    
    # Ordini pendenti
    pending = db.execute("""
        SELECT COUNT(*) FROM ORDINI_TESTATA 
        WHERE lookup_method = 'NESSUNO' OR lookup_method IS NULL
    """).fetchone()[0]
    
    return {
        "success": True,
        "data": {
            "by_method": stats,
            "percentages": percentages,
            "pending": pending,
            "total": total
        }
    }
