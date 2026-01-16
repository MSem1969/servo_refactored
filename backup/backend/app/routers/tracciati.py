# =============================================================================
# TO_EXTRACTOR v6.0 - TRACCIATI ROUTER
# =============================================================================
# Endpoint per generazione e download tracciati TO_T/TO_D
# =============================================================================

import os
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from typing import Dict, Any, List, Optional

from ..config import config
from ..services.tracciati import (
    generate_tracciati_per_ordine,
    get_tracciato_preview,
    get_ordini_pronti_export,
    get_esportazioni_storico,
    get_file_tracciato,
)


router = APIRouter(prefix="/tracciati")


# =============================================================================
# GENERAZIONE TRACCIATI
# =============================================================================

@router.post("/genera")
async def genera_tracciati(
    ordini_ids: Optional[List[int]] = None
) -> Dict[str, Any]:
    """
    Genera tracciati TO_T e TO_D per gli ordini.
    
    Args:
        ordini_ids: Lista ID ordini da esportare (opzionale, default: tutti pronti)
        
    Returns:
        Lista file generati con path per download
    """
    try:
        results = generate_tracciati_per_ordine(
            output_dir=config.OUTPUT_DIR,
            ordini_ids=ordini_ids
        )
        
        if not results:
            return {
                "success": False,
                "message": "Nessun ordine pronto per esportazione",
                "data": []
            }
        
        # Prepara response con URL download
        files_info = []
        for r in results:
            files_info.append({
                "id_testata": r['id_testata'],
                "numero_ordine": r['numero_ordine'],
                "vendor": r['vendor'],
                "files": {
                    "to_t": {
                        "filename": r['file_to_t'],
                        "download_url": f"/api/v1/tracciati/download/{r['file_to_t']}"
                    },
                    "to_d": {
                        "filename": r['file_to_d'],
                        "download_url": f"/api/v1/tracciati/download/{r['file_to_d']}"
                    }
                },
                "num_righe": r['num_righe']
            })
        
        return {
            "success": True,
            "data": files_info,
            "totale_ordini": len(results),
            "totale_righe": sum(r['num_righe'] for r in results),
            "message": f"Generati {len(results)} tracciati"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/genera/{id_testata}")
async def genera_tracciato_singolo(id_testata: int) -> Dict[str, Any]:
    """
    Genera tracciato per un singolo ordine.
    """
    try:
        results = generate_tracciati_per_ordine(
            output_dir=config.OUTPUT_DIR,
            ordini_ids=[id_testata]
        )
        
        if not results:
            raise HTTPException(
                status_code=404, 
                detail="Ordine non trovato o non pronto per esportazione"
            )
        
        r = results[0]
        return {
            "success": True,
            "data": {
                "id_testata": r['id_testata'],
                "numero_ordine": r['numero_ordine'],
                "vendor": r['vendor'],
                "to_t": {
                    "filename": r['file_to_t'],
                    "download_url": f"/api/v1/tracciati/download/{r['file_to_t']}"
                },
                "to_d": {
                    "filename": r['file_to_d'],
                    "download_url": f"/api/v1/tracciati/download/{r['file_to_d']}"
                },
                "num_righe": r['num_righe']
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# PREVIEW
# =============================================================================

@router.get("/preview/{id_testata}")
async def preview_tracciato(id_testata: int) -> Dict[str, Any]:
    """
    Preview tracciato senza generare file.
    
    Utile per verificare contenuto prima dell'export.
    """
    try:
        preview = get_tracciato_preview(id_testata)
        
        if 'error' in preview:
            raise HTTPException(status_code=404, detail=preview['error'])
        
        return {
            "success": True,
            "data": preview
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# DOWNLOAD
# =============================================================================

@router.get("/download/{filename}")
async def download_tracciato(filename: str):
    """
    Download file tracciato.
    
    Supporta sia TO_T che TO_D.
    """
    file_path = get_file_tracciato(filename)
    
    if not file_path:
        raise HTTPException(status_code=404, detail="File non trovato")
    
    # Determina tipo file
    media_type = "text/plain"
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type=media_type
    )


# =============================================================================
# QUERY
# =============================================================================

@router.get("/pronti")
async def ordini_pronti() -> Dict[str, Any]:
    """
    Ritorna ordini pronti per esportazione.
    
    Sono esclusi:
    - Ordini già esportati
    - Ordini scartati
    - Ordini senza lookup valido
    """
    try:
        ordini = get_ordini_pronti_export()
        return {
            "success": True,
            "data": ordini,
            "count": len(ordini)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/storico")
async def storico_esportazioni(
    limit: int = Query(20, ge=1, le=100)
) -> Dict[str, Any]:
    """
    Ritorna storico esportazioni.
    """
    try:
        storico = get_esportazioni_storico(limit)
        return {
            "success": True,
            "data": storico
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ricerca")
async def ricerca_tracciati(
    numero_ordine: Optional[str] = Query(None, description="Numero ordine (parziale)"),
    ragione_sociale: Optional[str] = Query(None, description="Ragione sociale cliente (parziale)"),
    vendor: Optional[str] = Query(None, description="Vendor"),
    data_da: Optional[str] = Query(None, description="Data esportazione da (YYYY-MM-DD)"),
    data_a: Optional[str] = Query(None, description="Data esportazione a (YYYY-MM-DD)"),
    stato: Optional[str] = Query(None, description="Stato ordine (EVASO, PARZ_EVASO, ecc)"),
    limit: int = Query(50, ge=1, le=200)
) -> Dict[str, Any]:
    """
    Ricerca tracciati esportati con filtri.

    Ritorna ordini esportati con info su:
    - Ordine (numero, vendor, data)
    - Cliente (ragione sociale, città)
    - Esportazione (data, file generati)
    """
    try:
        from ..database_pg import get_db
        db = get_db()

        # Query base: ordini esportati con info esportazione
        query = """
            SELECT
                t.id_testata,
                t.numero_ordine_vendor AS numero_ordine,
                v.codice_vendor AS vendor,
                t.data_ordine,
                t.stato,
                t.ragione_sociale_1 AS ragione_sociale,
                t.citta,
                t.provincia,
                COALESCE(f.min_id, p.codice_sito) AS min_id,
                t.data_validazione,
                t.validato_da,
                e.id_esportazione,
                e.data_generazione AS data_esportazione,
                e.nome_file_to_t,
                e.nome_file_to_d,
                e.num_testate,
                e.num_dettagli,
                COALESCE(e.data_generazione, t.data_validazione) AS sort_date,
                (SELECT COUNT(*) FROM ordini_dettaglio d WHERE d.id_testata = t.id_testata AND (d.is_child = FALSE OR d.is_child IS NULL)) as num_righe
            FROM ordini_testata t
            LEFT JOIN vendor v ON t.id_vendor = v.id_vendor
            LEFT JOIN anagrafica_farmacie f ON t.id_farmacia_lookup = f.id_farmacia
            LEFT JOIN anagrafica_parafarmacie p ON t.id_parafarmacia_lookup = p.id_parafarmacia
            LEFT JOIN esportazioni_dettaglio ed ON t.id_testata = ed.id_testata
            LEFT JOIN esportazioni e ON ed.id_esportazione = e.id_esportazione
            WHERE t.stato IN ('EVASO', 'PARZ_EVASO', 'ESPORTATO', 'ARCHIVIATO')
        """
        params = []

        # Filtri
        if numero_ordine:
            query += " AND t.numero_ordine_vendor LIKE ?"
            params.append(f"%{numero_ordine}%")

        if ragione_sociale:
            query += " AND t.ragione_sociale_1 LIKE ?"
            params.append(f"%{ragione_sociale}%")

        if vendor:
            query += " AND v.codice_vendor = ?"
            params.append(vendor)

        if data_da:
            query += " AND (e.data_generazione >= ? OR t.data_validazione >= ?)"
            params.extend([data_da, data_da])

        if data_a:
            query += " AND (e.data_generazione <= ? OR t.data_validazione <= ?)"
            params.extend([data_a, data_a])

        if stato:
            query += " AND t.stato = ?"
            params.append(stato)

        query += " ORDER BY sort_date DESC NULLS LAST LIMIT ?"
        params.append(limit)

        rows = db.execute(query, params).fetchall()

        # Formatta risultati
        results = []
        for row in rows:
            r = dict(row)
            results.append({
                "id_testata": r["id_testata"],
                "numero_ordine": r["numero_ordine"],
                "vendor": r["vendor"],
                "data_ordine": r["data_ordine"],
                "stato": r["stato"],
                "cliente": {
                    "ragione_sociale": r["ragione_sociale"],
                    "citta": r["citta"],
                    "provincia": r["provincia"],
                    "min_id": r["min_id"]
                },
                "esportazione": {
                    "id": r["id_esportazione"],
                    "data": r["data_esportazione"] or r["data_validazione"],
                    "file_to_t": r["nome_file_to_t"],
                    "file_to_d": r["nome_file_to_d"]
                },
                "num_righe": r["num_righe"],
                "validato_da": r["validato_da"]
            })

        return {
            "success": True,
            "data": results,
            "count": len(results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/files")
async def lista_files_tracciato() -> Dict[str, Any]:
    """
    Lista tutti i file tracciato nella directory output.
    """
    try:
        files = []
        if os.path.exists(config.OUTPUT_DIR):
            for f in os.listdir(config.OUTPUT_DIR):
                if f.startswith('TO_') and f.endswith('.TXT'):
                    path = os.path.join(config.OUTPUT_DIR, f)
                    files.append({
                        "filename": f,
                        "size": os.path.getsize(path),
                        "modified": os.path.getmtime(path),
                        "download_url": f"/api/v1/tracciati/download/{f}",
                        "tipo": "TO_T" if "TO_T" in f else "TO_D"
                    })
        
        # Ordina per data modifica (più recenti prima)
        files.sort(key=lambda x: x['modified'], reverse=True)
        
        return {
            "success": True,
            "data": files,
            "count": len(files)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# PULIZIA
# =============================================================================

@router.delete("/files")
async def elimina_files_tracciato(
    confirm: bool = Query(False, description="Conferma eliminazione")
) -> Dict[str, Any]:
    """
    Elimina tutti i file tracciato dalla directory output.
    
    ⚠️ Operazione irreversibile! Richiede confirm=true
    """
    if not confirm:
        raise HTTPException(
            status_code=400, 
            detail="Specificare confirm=true per confermare"
        )
    
    try:
        deleted = 0
        if os.path.exists(config.OUTPUT_DIR):
            for f in os.listdir(config.OUTPUT_DIR):
                if f.startswith('TO_') and f.endswith('.TXT'):
                    os.remove(os.path.join(config.OUTPUT_DIR, f))
                    deleted += 1
        
        return {
            "success": True,
            "message": f"Eliminati {deleted} file"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
