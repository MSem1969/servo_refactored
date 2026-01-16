# =============================================================================
# TO_EXTRACTOR v6.0 - ANAGRAFICA ROUTER
# =============================================================================
# Endpoint per import e ricerca anagrafica farmacie/parafarmacie
# =============================================================================

from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from typing import Dict, Any, Optional

from ..services.anagrafica import (
    import_anagrafica_farmacie,
    import_anagrafica_parafarmacie,
    get_anagrafica_stats,
    search_anagrafica,
    get_farmacia_by_id,
    get_parafarmacia_by_id,
    get_farmacia_by_min_id,
    get_farmacia_by_piva,
    clear_anagrafica_farmacie,
    clear_anagrafica_parafarmacie,
)


router = APIRouter(prefix="/anagrafica")


# =============================================================================
# IMPORT CSV
# =============================================================================

@router.post("/farmacie/import")
async def import_farmacie(
    file: UploadFile = File(..., description="File CSV farmacie (FRM_FARMA_*.csv)")
) -> Dict[str, Any]:
    """
    Importa anagrafica farmacie da CSV ministeriale.
    
    Formato atteso: CSV con separatore ; (punto e virgola)
    Colonne: cod_farmacia, p_iva, descrizione_farmacia, indirizzo, cap, 
             comune, sigla_provincia, regione, data_inizio_validita, data_fine_validita
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Nome file mancante")
    
    if not file.filename.lower().endswith('.csv'):
        raise HTTPException(status_code=400, detail="Solo file CSV accettati")
    
    try:
        content = await file.read()
        result = import_anagrafica_farmacie(csv_content=content, fonte=file.filename)
        
        if 'error' in result:
            raise HTTPException(status_code=400, detail=result['error'])
        
        return {
            "success": True,
            "data": result,
            "message": f"Importate {result['importate']:,} farmacie"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/parafarmacie/import")
async def import_parafarmacie(
    file: UploadFile = File(..., description="File CSV parafarmacie (FRM_PFARMA_*.csv)")
) -> Dict[str, Any]:
    """
    Importa anagrafica parafarmacie da CSV ministeriale.
    
    Formato atteso: CSV con separatore ; (punto e virgola)
    Colonne: codice_identificativo_sito, sito_logistico, partita_iva, indirizzo, 
             cap, comune, sigla_provincia, regione, latitudine, longitudine
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Nome file mancante")
    
    if not file.filename.lower().endswith('.csv'):
        raise HTTPException(status_code=400, detail="Solo file CSV accettati")
    
    try:
        content = await file.read()
        result = import_anagrafica_parafarmacie(csv_content=content, fonte=file.filename)
        
        if 'error' in result:
            raise HTTPException(status_code=400, detail=result['error'])
        
        return {
            "success": True,
            "data": result,
            "message": f"Importate {result['importate']:,} parafarmacie"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# STATISTICHE
# =============================================================================

@router.get("/stats")
async def anagrafica_stats() -> Dict[str, Any]:
    """
    Ritorna statistiche anagrafica.
    """
    try:
        stats = get_anagrafica_stats()
        return {
            "success": True,
            "data": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# RICERCA
# =============================================================================

@router.get("/search")
async def search(
    q: str = Query(..., min_length=2, description="Testo da cercare"),
    tipo: str = Query("all", description="Tipo: farmacie, parafarmacie, all"),
    limit: int = Query(20, ge=1, le=100)
) -> Dict[str, Any]:
    """
    Ricerca in anagrafica farmacie e/o parafarmacie.
    
    Cerca in: ragione_sociale, città, P.IVA, codice ministeriale
    """
    if tipo not in ('farmacie', 'parafarmacie', 'all'):
        raise HTTPException(status_code=400, detail="Tipo non valido")
    
    try:
        result = search_anagrafica(query=q, tipo=tipo, limit=limit)
        
        total = len(result.get('farmacie', [])) + len(result.get('parafarmacie', []))
        
        return {
            "success": True,
            "data": result,
            "count": total,
            "query": q
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# FARMACIE - DETTAGLIO
# =============================================================================

@router.get("/farmacie/{id_farmacia}")
async def get_farmacia(id_farmacia: int) -> Dict[str, Any]:
    """
    Ritorna dettaglio farmacia per ID.
    """
    try:
        farmacia = get_farmacia_by_id(id_farmacia)
        
        if not farmacia:
            raise HTTPException(status_code=404, detail="Farmacia non trovata")
        
        return {
            "success": True,
            "data": farmacia
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/farmacie/min/{min_id}")
async def get_farmacia_by_min(min_id: str) -> Dict[str, Any]:
    """
    Ritorna farmacia per codice ministeriale (MIN_ID).
    """
    try:
        farmacia = get_farmacia_by_min_id(min_id)
        
        if not farmacia:
            raise HTTPException(status_code=404, detail="Farmacia non trovata")
        
        return {
            "success": True,
            "data": farmacia
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/farmacie/piva/{piva}")
async def get_farmacie_by_partita_iva(piva: str) -> Dict[str, Any]:
    """
    Ritorna farmacie per P.IVA (può essere multipunto).
    """
    try:
        farmacie = get_farmacia_by_piva(piva)
        
        return {
            "success": True,
            "data": farmacie,
            "count": len(farmacie),
            "multipunto": len(farmacie) > 1
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# PARAFARMACIE - DETTAGLIO
# =============================================================================

@router.get("/parafarmacie/{id_parafarmacia}")
async def get_parafarmacia(id_parafarmacia: int) -> Dict[str, Any]:
    """
    Ritorna dettaglio parafarmacia per ID.
    """
    try:
        parafarmacia = get_parafarmacia_by_id(id_parafarmacia)
        
        if not parafarmacia:
            raise HTTPException(status_code=404, detail="Parafarmacia non trovata")
        
        return {
            "success": True,
            "data": parafarmacia
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# PULIZIA (ADMIN)
# =============================================================================

@router.delete("/farmacie")
async def clear_farmacie(
    confirm: bool = Query(False, description="Conferma eliminazione")
) -> Dict[str, Any]:
    """
    Elimina tutte le farmacie dall'anagrafica.
    
    ⚠️ Operazione irreversibile! Richiede confirm=true
    """
    if not confirm:
        raise HTTPException(
            status_code=400, 
            detail="Specificare confirm=true per confermare"
        )
    
    try:
        count = clear_anagrafica_farmacie()
        return {
            "success": True,
            "message": f"Eliminate {count:,} farmacie"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/parafarmacie")
async def clear_parafarmacie(
    confirm: bool = Query(False, description="Conferma eliminazione")
) -> Dict[str, Any]:
    """
    Elimina tutte le parafarmacie dall'anagrafica.
    
    ⚠️ Operazione irreversibile! Richiede confirm=true
    """
    if not confirm:
        raise HTTPException(
            status_code=400, 
            detail="Specificare confirm=true per confermare"
        )
    
    try:
        count = clear_anagrafica_parafarmacie()
        return {
            "success": True,
            "message": f"Eliminate {count:,} parafarmacie"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
