# =============================================================================
# SERV.O v7.0 - LISTINI ROUTER
# =============================================================================
# Endpoint per import e ricerca listini prezzi vendor
# =============================================================================

from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from typing import Dict, Any, Optional

from ..services.listini import (
    import_listino_csv,
    get_prezzo_listino,
    get_listino_vendor,
    get_listino_stats,
    search_listino,
    aggiorna_prezzi_netti,
    VENDOR_CSV_MAPPINGS,
)


router = APIRouter(prefix="/listini")


# =============================================================================
# IMPORT CSV
# =============================================================================

@router.post("/import")
async def import_listino(
    file: UploadFile = File(..., description="File CSV listino prezzi"),
    vendor: str = Query("CODIFI", description="Codice vendor (es: CODIFI)"),
    clear_existing: bool = Query(True, description="Elimina listino esistente prima di importare"),
    calcola_prezzi: bool = Query(True, description="Calcola prezzi vendita dopo import"),
    formula: str = Query("SCONTO_CASCATA", description="Formula calcolo: SCONTO_CASCATA o SCONTO_SOMMA")
) -> Dict[str, Any]:
    """
    Importa listino prezzi da file CSV per un vendor.

    Vendor supportati: CODIFI

    Per CODIFI il formato atteso prevede le colonne:
    - AFCODI: Codice AIC
    - CVDPRO: Descrizione prodotto
    - CVPVEN: Prezzo vendita da CSV
    - AFPEU1: Prezzo pubblico (formato XXXXXXYY con 2 decimali impliciti)
    - CVSCO1: Sconto % 1 (formato italiano con virgola)
    - CVSCO2: Sconto % 2
    - AFAIVA: Aliquota IVA (intero)
    - AFDVA1: Data decorrenza (YYYYMMDD)
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Nome file mancante")

    if not file.filename.lower().endswith('.csv'):
        raise HTTPException(status_code=400, detail="Solo file CSV accettati")

    vendor_upper = vendor.upper()
    if vendor_upper not in VENDOR_CSV_MAPPINGS:
        raise HTTPException(
            status_code=400,
            detail=f"Vendor {vendor_upper} non supportato. Vendor disponibili: {list(VENDOR_CSV_MAPPINGS.keys())}"
        )

    try:
        content = await file.read()
        success, result = import_listino_csv(
            csv_content=content,
            vendor=vendor_upper,
            filename=file.filename,
            clear_existing=clear_existing
        )

        if not success:
            raise HTTPException(status_code=400, detail=result.get('error', 'Errore import'))

        # NOTE: aggiorna_prezzi_netti NON più chiamata dopo import
        # perché import_listino_csv già calcola prezzo_scontare (scorporo IVA)
        # e prezzo_netto (con sconti a cascata) correttamente.
        # La funzione aggiorna_prezzi_netti usava prezzo_pubblico (con IVA)
        # sovrascrivendo erroneamente i valori già calcolati.

        return {
            "success": True,
            "data": result,
            "message": f"Importati {result['imported']:,} prodotti per {vendor_upper}"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# STATISTICHE
# =============================================================================

@router.get("/stats")
async def listino_stats() -> Dict[str, Any]:
    """
    Ritorna statistiche sui listini caricati.
    """
    try:
        stats = get_listino_stats()
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
    q: str = Query(..., min_length=2, description="Testo da cercare (descrizione o AIC)"),
    vendor: str = Query(None, description="Filtra per vendor"),
    limit: int = Query(50, ge=1, le=200)
) -> Dict[str, Any]:
    """
    Cerca prodotti nel listino per descrizione o codice AIC.
    """
    try:
        results = search_listino(query=q, vendor=vendor, limit=limit)

        return {
            "success": True,
            "data": results,
            "count": len(results),
            "query": q
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# LOOKUP PREZZO
# =============================================================================

@router.get("/prezzo/{codice_aic}")
async def get_prezzo(
    codice_aic: str,
    vendor: str = Query(None, description="Filtra per vendor specifico")
) -> Dict[str, Any]:
    """
    Recupera prezzo e sconti per un codice AIC dal listino.
    """
    try:
        prezzo = get_prezzo_listino(codice_aic, vendor)

        if not prezzo:
            raise HTTPException(
                status_code=404,
                detail=f"Codice AIC {codice_aic} non trovato nel listino"
            )

        return {
            "success": True,
            "data": prezzo
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# LISTINO PER VENDOR
# =============================================================================

@router.get("/vendor/{vendor}")
async def get_listino_by_vendor(
    vendor: str,
    limit: int = Query(1000, ge=1, le=10000)
) -> Dict[str, Any]:
    """
    Recupera tutti i prodotti del listino per un vendor.
    """
    try:
        products = get_listino_vendor(vendor, limit)

        return {
            "success": True,
            "data": products,
            "count": len(products),
            "vendor": vendor.upper()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# RICALCOLO PREZZI
# =============================================================================

@router.post("/calcola-prezzi")
async def calcola_prezzi(
    vendor: str = Query(..., description="Codice vendor"),
    formula: str = Query("SCONTO_CASCATA", description="Formula: SCONTO_CASCATA o SCONTO_SOMMA")
) -> Dict[str, Any]:
    """
    Ricalcola NetVendorPrice (prezzo_netto) per tutti i prodotti di un vendor.
    Applica gli sconti (Discount1-4) al PriceToDiscount.

    Formule disponibili:
    - SCONTO_CASCATA: PtD * (1-s1/100) * (1-s2/100) * (1-s3/100) * (1-s4/100)
    - SCONTO_SOMMA: PtD * (1 - (s1+s2+s3+s4)/100)
    """
    if formula not in ('SCONTO_CASCATA', 'SCONTO_SOMMA'):
        raise HTTPException(status_code=400, detail="Formula non valida")

    try:
        result = aggiorna_prezzi_netti(vendor, formula)

        return {
            "success": True,
            "data": result,
            "message": f"Aggiornati {result['updated']:,} prezzi per {vendor.upper()}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# VENDOR SUPPORTATI
# =============================================================================

@router.get("/vendors")
async def get_supported_vendors() -> Dict[str, Any]:
    """
    Ritorna lista dei vendor supportati per import listini.
    """
    return {
        "success": True,
        "data": {
            "vendors": list(VENDOR_CSV_MAPPINGS.keys()),
            "mappings": {
                vendor: list(mapping.values())
                for vendor, mapping in VENDOR_CSV_MAPPINGS.items()
            }
        }
    }
