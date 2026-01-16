# =============================================================================
# TO_EXTRACTOR v6.0 - DASHBOARD ROUTER
# =============================================================================
# Endpoint per dashboard e statistiche
# =============================================================================

from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from ..services.ordini import (
    get_dashboard_stats,
    get_ordini_recenti,
    get_anomalie_critiche,
)
from ..services.anagrafica import get_anagrafica_stats
from ..services.pdf_processor import get_upload_stats
from ..database_pg import get_stats, get_vendor_stats


router = APIRouter(prefix="/dashboard")


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("", response_model=None)
async def dashboard_stats() -> Dict[str, Any]:
    """
    Ritorna statistiche complete per dashboard.
    
    Include:
    - Totali (ordini, righe, anomalie, PDF)
    - Ordini per stato e vendor
    - Anomalie per tipo
    - Lookup stats
    - Trend ultimi 7 giorni
    """
    try:
        stats = get_dashboard_stats()
        return {
            "success": True,
            "data": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def dashboard_summary() -> Dict[str, Any]:
    """
    Ritorna riepilogo veloce per header dashboard.
    """
    try:
        db_stats = get_stats()
        upload_stats = get_upload_stats()
        
        return {
            "success": True,
            "data": {
                "ordini_totali": db_stats['ordini'],
                "anomalie_aperte": db_stats['anomalie_aperte'],
                "pdf_oggi": upload_stats['oggi'],
                "farmacie": db_stats['farmacie'],
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ordini-recenti")
async def ordini_recenti(limit: int = 10) -> Dict[str, Any]:
    """
    Ritorna ultimi ordini elaborati.
    """
    try:
        ordini = get_ordini_recenti(limit)
        return {
            "success": True,
            "data": ordini
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/anomalie-critiche")
async def anomalie_critiche(limit: int = 10) -> Dict[str, Any]:
    """
    Ritorna anomalie critiche/errore da gestire.
    """
    try:
        anomalie = get_anomalie_critiche(limit)
        return {
            "success": True,
            "data": anomalie
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vendor-stats")
async def vendor_statistics() -> Dict[str, Any]:
    """
    Ritorna statistiche per vendor.
    """
    try:
        stats = get_vendor_stats()
        return {
            "success": True,
            "data": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/anagrafica-stats")
async def anagrafica_statistics() -> Dict[str, Any]:
    """
    Ritorna statistiche anagrafica farmacie/parafarmacie.
    """
    try:
        stats = get_anagrafica_stats()
        return {
            "success": True,
            "data": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/upload-stats")
async def upload_statistics() -> Dict[str, Any]:
    """
    Ritorna statistiche upload PDF.
    """
    try:
        stats = get_upload_stats()
        return {
            "success": True,
            "data": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
