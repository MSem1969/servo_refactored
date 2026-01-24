# =============================================================================
# SERV.O v6.0 - UPLOAD ROUTER
# =============================================================================
# Endpoint per upload e elaborazione PDF
# =============================================================================

import os
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse, FileResponse
from typing import Dict, Any, List, Optional

from ..config import config
from ..services.pdf_processor import (
    process_pdf,
    get_recent_uploads,
    get_upload_stats,
)
from ..services.extraction import detect_vendor, get_supported_vendors


router = APIRouter(prefix="/upload")


# =============================================================================
# UPLOAD ENDPOINTS
# =============================================================================

@router.post("")
async def upload_pdf(
    file: UploadFile = File(...),
    auto_process: bool = Form(True)
) -> Dict[str, Any]:
    """
    Upload singolo PDF e elaborazione.
    
    Args:
        file: File PDF da caricare
        auto_process: Se True, elabora immediatamente (default: True)
        
    Returns:
        Risultato elaborazione con statistiche
    """
    # Validazione file
    if not file.filename:
        raise HTTPException(status_code=400, detail="Nome file mancante")
    
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Solo file PDF accettati")
    
    # Leggi contenuto
    try:
        content = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Errore lettura file: {str(e)}")
    
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="File vuoto")
    
    if len(content) > config.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400, 
            detail=f"File troppo grande (max {config.MAX_FILE_SIZE // 1024 // 1024}MB)"
        )
    
    # Elabora PDF
    try:
        result = process_pdf(file.filename, content)
        
        return {
            "success": result['status'] == 'OK',
            "data": result,
            "message": _get_result_message(result)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/multiple")
async def upload_multiple_pdfs(
    files: List[UploadFile] = File(...)
) -> Dict[str, Any]:
    """
    Upload multiplo di PDF.
    
    Args:
        files: Lista di file PDF
        
    Returns:
        Lista risultati elaborazione
    """
    if not files:
        raise HTTPException(status_code=400, detail="Nessun file caricato")
    
    results = []
    totals = {'ok': 0, 'duplicati': 0, 'errori': 0, 'ordini': 0, 'righe': 0}
    
    for file in files:
        if not file.filename or not file.filename.lower().endswith('.pdf'):
            results.append({
                'filename': file.filename or 'unknown',
                'status': 'ERRORE',
                'error': 'Non è un file PDF'
            })
            totals['errori'] += 1
            continue
        
        try:
            content = await file.read()
            result = process_pdf(file.filename, content)
            results.append(result)
            
            if result['status'] == 'OK':
                totals['ok'] += 1
                totals['ordini'] += result['ordini']
                totals['righe'] += result['righe']
            elif result['status'] == 'DUPLICATO':
                totals['duplicati'] += 1
                totals['errori'] += 1  # Duplicati contano come errori
            else:
                totals['errori'] += 1
                
        except Exception as e:
            results.append({
                'filename': file.filename,
                'status': 'ERRORE',
                'error': str(e)
            })
            totals['errori'] += 1
    
    return {
        "success": totals['errori'] == 0,
        "data": {
            "results": results,
            "totals": totals
        },
        "message": f"Elaborati {totals['ok']} PDF, {totals['ordini']} ordini, {totals['righe']} righe"
    }


@router.post("/detect-vendor")
async def detect_vendor_endpoint(
    file: UploadFile = File(...)
) -> Dict[str, Any]:
    """
    Rileva vendor da PDF senza elaborare.
    
    Utile per preview prima dell'elaborazione.
    """
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Solo file PDF accettati")
    
    try:
        content = await file.read()
        
        # Estrai testo per detect
        import pdfplumber
        import io
        from ..services.pdf_processor import _fix_encoding_manual, FTFY_AVAILABLE
        try:
            import ftfy
        except ImportError:
            pass

        pdf_file = io.BytesIO(content)
        text = ""
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages[:2]:  # Solo prime 2 pagine
                page_text = page.extract_text(x_tolerance=5) or ""
                if FTFY_AVAILABLE:
                    page_text = ftfy.fix_text(page_text)
                page_text = _fix_encoding_manual(page_text)
                text += page_text + "\n"
        
        vendor, confidence = detect_vendor(text, file.filename)
        
        return {
            "success": True,
            "data": {
                "vendor": vendor,
                "confidence": confidence,
                "filename": file.filename,
                "size_bytes": len(content)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# QUERY ENDPOINTS
# =============================================================================

@router.get("/recent")
async def recent_uploads(limit: int = 20) -> Dict[str, Any]:
    """
    Ritorna ultimi PDF caricati.
    """
    try:
        uploads = get_recent_uploads(limit)
        return {
            "success": True,
            "data": uploads
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def upload_statistics() -> Dict[str, Any]:
    """
    Ritorna statistiche upload.
    """
    try:
        stats = get_upload_stats()
        return {
            "success": True,
            "data": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vendors")
async def supported_vendors() -> Dict[str, Any]:
    """
    Ritorna lista vendor supportati.
    """
    vendors = get_supported_vendors()
    return {
        "success": True,
        "data": {
            "vendors": vendors,
            "count": len(vendors)
        }
    }


@router.get("/pdf/{filename}")
async def get_pdf(filename: str):
    """
    Serve un PDF dalla cartella uploads.
    Usato per visualizzare il PDF originale di un ordine.
    """
    # Cerca il file nella cartella uploads
    uploads_dir = config.UPLOAD_DIR

    if not os.path.exists(uploads_dir):
        raise HTTPException(404, f"Cartella uploads non trovata")

    # Cerca file che contiene il filename (potrebbe avere prefisso UUID)
    for f in os.listdir(uploads_dir):
        if filename in f or f.endswith(filename):
            file_path = os.path.join(uploads_dir, f)
            if os.path.exists(file_path) and os.path.isfile(file_path):
                return FileResponse(
                    file_path,
                    media_type="application/pdf",
                    headers={"Content-Disposition": f"inline; filename={filename}"}
                )

    raise HTTPException(404, f"PDF non trovato: {filename}")


# =============================================================================
# HELPERS
# =============================================================================

def _get_result_message(result: Dict) -> str:
    """Genera messaggio descrittivo per risultato."""
    if result['status'] == 'OK':
        return f"Elaborato {result['vendor']}: {result['ordini']} ordini, {result['righe']} righe"
    elif result['status'] == 'DUPLICATO':
        dup_info = result.get('duplicato_info', {})
        if dup_info:
            stato = dup_info.get('stato_ordine', 'SCONOSCIUTO')
            info = dup_info.get('info_ordine', '')
            stato_desc = {
                'ESTRATTO': 'in elaborazione',
                'ANOMALIA': 'con anomalie',
                'PARZ_EVASO': 'parzialmente evaso',
                'EVASO': 'evaso',
                'ARCHIVIATO': 'archiviato'
            }.get(stato, stato)
            return f"❌ ERRORE DUPLICATO: {info} - Stato: {stato_desc}"
        return "❌ ERRORE: PDF già caricato precedentemente"
    else:
        errors = result.get('anomalie', ['Errore sconosciuto'])
        return f"Errore: {errors[0] if errors else 'sconosciuto'}"
