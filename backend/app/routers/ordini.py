# =============================================================================
# SERV.O v6.1 - ORDINI ROUTER
# =============================================================================
# Endpoint per gestione ordini e conferma righe
# =============================================================================

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime
import zipfile
import io
import os
from ..database_pg import get_db
from ..config import config

from ..services.ordini import (
    get_ordini,
    get_ordine_detail,
    get_ordine_righe,
    update_ordine_stato,
    delete_ordine,
    conferma_singola_riga,
    conferma_ordine_completo,
    get_riga_dettaglio,
    modifica_riga_dettaglio,
    crea_o_recupera_supervisione,
    get_stato_righe_ordine,
    registra_evasione,
    ripristina_riga,
    ripristina_ordine,
    fix_stati_righe,
)
from ..services.tracciati import valida_e_genera_tracciato

# =============================================================================
# HELPER: MAPPING CAMPI DB → FRONTEND
# =============================================================================

def _map_riga_per_frontend(riga) -> dict:
    """Mappa data_consegna_riga (DB) → data_consegna (Frontend)"""
    if not riga:
        return riga
    
    # Converti in dict se è un oggetto Row
    if hasattr(riga, 'keys'):
        mapped = {key: riga[key] for key in riga.keys()}
    elif isinstance(riga, dict):
        mapped = dict(riga)
    else:
        return riga
    
    # Applica mapping
    if 'data_consegna_riga' in mapped:
        mapped['data_consegna'] = mapped.pop('data_consegna_riga')
    if 'data_consegna_riga_raw' in mapped:
        mapped['data_consegna_raw'] = mapped.pop('data_consegna_riga_raw')
    return mapped

def _map_righe_per_frontend(righe: list) -> list:
    """Applica mapping a lista di righe"""
    if not righe:
        return righe
    return [_map_riga_per_frontend(r) for r in righe]



router = APIRouter(prefix="/ordini")



# =============================================================================
# MODELLI PYDANTIC v6.1
# =============================================================================

class ConfermaRigaRequest(BaseModel):
    operatore: str
    note: Optional[str] = None

class ConfermaOrdineRequest(BaseModel):
    operatore: str
    forza_conferma: bool = False
    note: Optional[str] = None

class ModificaRigaRequest(BaseModel):
    operatore: str
    modifiche: dict
    note: Optional[str] = None

class ValidaOrdineRequest(BaseModel):
    operatore: str
    validazione_massiva: bool = False  # True = Dashboard (conferma tutto), False = Dettaglio (solo confermate)

class RegistraEvasioneRequest(BaseModel):
    q_da_evadere: int  # v6.2.1: Quantità da esportare nel prossimo tracciato
    operatore: str

class RipristinaRequest(BaseModel):
    operatore: str


# =============================================================================
# LISTA E RICERCA
# =============================================================================

@router.get("")
async def lista_ordini(
    vendor: Optional[str] = Query(None, description="Filtra per vendor"),
    stato: Optional[str] = Query(None, description="Filtra per stato"),
    lookup_method: Optional[str] = Query(None, description="Filtra per metodo lookup"),
    data_da: Optional[str] = Query(None, description="Data ordine da (DD/MM/YYYY)"),
    data_a: Optional[str] = Query(None, description="Data ordine a (DD/MM/YYYY)"),
    q: Optional[str] = Query(None, description="Ricerca in numero ordine, ragione sociale, MIN_ID"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0)
) -> Dict[str, Any]:
    """
    Ritorna lista ordini con filtri e paginazione.

    Stati: ESTRATTO, ANOMALIA, PARZ_EVASO, EVASO, ARCHIVIATO

    Lookup methods: PIVA, PIVA+FUZZY, PIVA_AMBIGUA, FUZZY, MANUALE, NESSUNO

    Ricerca (q): cerca in numero_ordine_vendor, ragione_sociale, min_id
    """
    try:
        result = get_ordini(
            vendor=vendor,
            stato=stato,
            lookup_method=lookup_method,
            data_da=data_da,
            data_a=data_a,
            q=q,
            limit=limit,
            offset=offset
        )
        
        return {
            "success": True,
            "data": result['ordini'],
            "pagination": {
                "totale": result['totale'],
                "limit": result['limit'],
                "offset": result['offset'],
                "pages": (result['totale'] + limit - 1) // limit
            }
        }
    except Exception as e:
        import traceback
        print(f"❌ Errore lista_ordini: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stati")
async def lista_stati() -> Dict[str, Any]:
    """
    Ritorna lista stati ordine disponibili.
    """
    return {
        "success": True,
        "data": [
            {"code": "ESTRATTO", "label": "Estratto", "color": "blue"},
            {"code": "CONFERMATO", "label": "Confermato", "color": "cyan"},
            {"code": "ANOMALIA", "label": "Anomalia", "color": "red"},
            {"code": "PARZ_EVASO", "label": "Parz. Evaso", "color": "orange"},
            {"code": "EVASO", "label": "Evaso", "color": "green"},
            {"code": "ARCHIVIATO", "label": "Archiviato", "color": "gray"},
        ]
    }


@router.get("/lookup-methods")
async def lista_lookup_methods() -> Dict[str, Any]:
    """
    Ritorna lista metodi lookup disponibili.
    """
    return {
        "success": True,
        "data": [
            {"code": "PIVA", "label": "P.IVA esatta", "score": 100},
            {"code": "PIVA+FUZZY", "label": "P.IVA + Fuzzy", "score": "60-99"},
            {"code": "PIVA_AMBIGUA", "label": "P.IVA multipunto", "score": "<60"},
            {"code": "FUZZY", "label": "Solo Fuzzy", "score": "60-99"},
            {"code": "MANUALE", "label": "Assegnazione manuale", "score": 100},
            {"code": "NESSUNO", "label": "Non trovato", "score": 0},
        ]
    }


# =============================================================================
# DETTAGLIO ORDINE
# =============================================================================

@router.get("/{id_testata}")
async def dettaglio_ordine(id_testata: int) -> Dict[str, Any]:
    """
    Ritorna dettaglio completo ordine.
    
    Include:
    - Dati testata
    - Righe dettaglio
    - Anomalie associate
    - Info acquisizione PDF
    """
    try:
        ordine = get_ordine_detail(id_testata)
        
        if not ordine:
            raise HTTPException(status_code=404, detail="Ordine non trovato")
        
        return {
            "success": True,
            "data": ordine
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{id_testata}/righe")
async def righe_ordine(id_testata: int) -> Dict[str, Any]:
    """
    Ritorna solo le righe dettaglio di un ordine.
    """
    try:
        righe = get_ordine_righe(id_testata)
        return {
            "success": True,
            "data": _map_righe_per_frontend(righe),
            "count": len(righe)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# MODIFICA ORDINE
# =============================================================================

@router.put("/{id_testata}/stato")
async def cambia_stato_ordine(
    id_testata: int,
    nuovo_stato: str = Query(..., description="Nuovo stato ordine")
) -> Dict[str, Any]:
    """
    Cambia stato di un ordine.
    
    Stati validi: ESTRATTO, CONFERMATO, ANOMALIA, PARZ_EVASO, EVASO, ARCHIVIATO
    """
    stati_validi = ['ESTRATTO', 'CONFERMATO', 'ANOMALIA', 'PARZ_EVASO', 'EVASO', 'ARCHIVIATO']

    if nuovo_stato not in stati_validi:
        raise HTTPException(
            status_code=400, 
            detail=f"Stato non valido. Valori accettati: {', '.join(stati_validi)}"
        )
    
    try:
        success = update_ordine_stato(id_testata, nuovo_stato)
        
        if not success:
            raise HTTPException(status_code=404, detail="Ordine non trovato")
        
        return {
            "success": True,
            "message": f"Stato aggiornato a {nuovo_stato}"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{id_testata}/valida")
async def valida_ordine_e_genera_tracciato(
    id_testata: int,
    request: ValidaOrdineRequest
) -> Dict[str, Any]:
    """
    Valida ordine e genera tracciato TO_T/TO_D.
    
    Questo endpoint:
    1. Cambia stato ordine a VALIDATO
    2. Genera file tracciato TO_T (testata)
    3. Genera file tracciato TO_D (dettagli)
    4. Ritorna link per download file
    
    Returns:
        - success: bool
        - tracciato: {to_t: {filename, download_url}, to_d: {filename, download_url, num_righe}}
        - message: str
    """
    try:
        result = valida_e_genera_tracciato(
            id_testata,
            request.operatore,
            validazione_massiva=request.validazione_massiva
        )

        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('error', 'Errore validazione'))

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{id_testata}")
async def elimina_ordine(id_testata: int) -> Dict[str, Any]:
    """
    Elimina un ordine e tutti i dati correlati.
    
    ⚠️ Operazione irreversibile!
    """
    try:
        success = delete_ordine(id_testata)
        
        if not success:
            raise HTTPException(status_code=404, detail="Ordine non trovato")
        
        return {
            "success": True,
            "message": "Ordine eliminato"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# AZIONI BATCH
# =============================================================================

@router.post("/batch/stato")
async def cambia_stato_batch(
    ids: List[int],
    nuovo_stato: str
) -> Dict[str, Any]:
    """
    Cambia stato di più ordini.
    """
    stati_validi = ['ESTRATTO', 'CONFERMATO', 'ANOMALIA', 'PARZ_EVASO', 'EVASO', 'ARCHIVIATO']

    if nuovo_stato not in stati_validi:
        raise HTTPException(status_code=400, detail="Stato non valido")
    
    try:
        success_count = 0
        for id_testata in ids:
            if update_ordine_stato(id_testata, nuovo_stato):
                success_count += 1
        
        return {
            "success": True,
            "data": {
                "aggiornati": success_count,
                "totale": len(ids)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/batch")
async def elimina_ordini_batch(ids: List[int]) -> Dict[str, Any]:
    """
    Elimina più ordini.

    ⚠️ Operazione irreversibile!
    """
    try:
        deleted_count = 0
        for id_testata in ids:
            if delete_ordine(id_testata):
                deleted_count += 1

        return {
            "success": True,
            "data": {
                "eliminati": deleted_count,
                "totale": len(ids)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class DownloadPdfRequest(BaseModel):
    ids: List[int]


@router.post("/batch/download-pdf")
async def download_pdf_batch(request: DownloadPdfRequest):
    """
    Download PDF files for multiple orders as a ZIP archive.

    Args:
        ids: List of order IDs (id_testata)

    Returns:
        ZIP file containing all available PDFs
    """
    try:
        print(f"[DOWNLOAD-PDF] Request IDs: {request.ids}")
        db = get_db()

        # Get pdf_file paths for the requested orders (JOIN with acquisizioni for file name)
        placeholders = ','.join(['?'] * len(request.ids))
        query = f"""
            SELECT t.id_testata, t.numero_ordine_vendor, v.codice_vendor as vendor, a.nome_file_storage as pdf_file
            FROM ORDINI_TESTATA t
            LEFT JOIN acquisizioni a ON t.id_acquisizione = a.id_acquisizione
            LEFT JOIN vendor v ON t.id_vendor = v.id_vendor
            WHERE t.id_testata IN ({placeholders}) AND a.nome_file_storage IS NOT NULL
        """
        print(f"[DOWNLOAD-PDF] Query: {query}")
        rows = db.execute(query, tuple(request.ids)).fetchall()
        print(f"[DOWNLOAD-PDF] Found {len(rows) if rows else 0} orders with PDF")

        if not rows:
            raise HTTPException(status_code=404, detail="Nessun PDF trovato per gli ordini selezionati")

        # Create ZIP in memory
        zip_buffer = io.BytesIO()
        files_added = 0
        files_missing = []

        print(f"[DOWNLOAD-PDF] UPLOAD_DIR: {config.UPLOAD_DIR}")

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for row in rows:
                pdf_filename = row['pdf_file']
                pdf_path = os.path.join(config.UPLOAD_DIR, pdf_filename)
                print(f"[DOWNLOAD-PDF] Checking: {pdf_path} - exists: {os.path.exists(pdf_path)}")

                if os.path.exists(pdf_path):
                    # Create a meaningful filename: VENDOR_NUMERO_ORDINE.pdf
                    vendor = row['vendor'] or 'UNKNOWN'
                    numero = row['numero_ordine_vendor'] or str(row['id_testata'])
                    # Sanitize filename
                    safe_numero = "".join(c for c in numero if c.isalnum() or c in '-_')
                    archive_name = f"{vendor}_{safe_numero}.pdf"

                    zip_file.write(pdf_path, archive_name)
                    files_added += 1
                else:
                    files_missing.append(pdf_filename)

        if files_added == 0:
            raise HTTPException(status_code=404, detail="Nessun file PDF trovato sul server")

        zip_buffer.seek(0)

        # Generate filename with timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        zip_filename = f"ordini_pdf_{timestamp}.zip"

        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={zip_filename}",
                "X-Files-Added": str(files_added),
                "X-Files-Missing": str(len(files_missing))
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# v6.1: CONFERMA RIGHE
# =============================================================================

@router.post("/{id_testata}/righe/{id_dettaglio}/conferma")
async def conferma_riga(
    id_testata: int,
    id_dettaglio: int,
    request: ConfermaRigaRequest
) -> Dict[str, Any]:
    """
    Conferma singola riga per inserimento in tracciato.
    """
    try:
        result = conferma_singola_riga(
            id_testata=id_testata,
            id_dettaglio=id_dettaglio,
            operatore=request.operatore,
            note=request.note
        )
        
        if not result['success']:
            if result.get('richiede_supervisione'):
                return {
                    "success": False,
                    "message": "Riga richiede supervisione prima della conferma",
                    "richiede_supervisione": True,
                    "id_supervisione": result.get('id_supervisione'),
                    "tipo_anomalia": result.get('tipo_anomalia'),
                    "redirect_url": f"/supervisione/{result.get('id_supervisione')}"
                }
            raise HTTPException(status_code=400, detail=result.get('error', 'Errore conferma'))
        
        return {
            "success": True,
            "id_dettaglio": id_dettaglio,
            "stato_riga": "CONFERMATO",
            "message": "Riga confermata per tracciato"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{id_testata}/conferma-tutto")
async def conferma_ordine_completo_endpoint(
    id_testata: int,
    request: ConfermaOrdineRequest
) -> Dict[str, Any]:
    """
    Conferma tutte le righe confermabili di un ordine.
    """
    try:
        result = conferma_ordine_completo(
            id_testata=id_testata,
            operatore=request.operatore,
            forza_conferma=request.forza_conferma,
            note=request.note
        )
        
        return {
            "success": True,
            "id_testata": id_testata,
            "righe_confermate": result['confermate'],
            "righe_bloccate": result['bloccate'],
            "righe_gia_confermate": result['gia_confermate'],
            "ordine_completo": result['ordine_completo'],
            "message": f"Confermate {result['confermate']} righe" + 
                       (f", {len(result['bloccate'])} richiedono supervisione" if result['bloccate'] else "")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{id_testata}/righe/{id_dettaglio}")
async def dettaglio_riga(
    id_testata: int,
    id_dettaglio: int
) -> Dict[str, Any]:
    """
    Ritorna dettaglio completo di una riga con info supervisione.
    """
    try:
        riga = get_riga_dettaglio(id_testata, id_dettaglio)
        
        if not riga:
            raise HTTPException(status_code=404, detail="Riga non trovata")
        
        return {
            "success": True,
            "data": _map_riga_per_frontend(riga)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{id_testata}/righe/{id_dettaglio}")
async def modifica_riga(
    id_testata: int,
    id_dettaglio: int,
    request: ModificaRigaRequest
) -> Dict[str, Any]:
    """
    Modifica valori di una riga.
    """
    try:
        result = modifica_riga_dettaglio(
            id_testata=id_testata,
            id_dettaglio=id_dettaglio,
            modifiche=request.modifiche,
            operatore=request.operatore,
            note=request.note
        )
        
        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('error'))
        
        return {
            "success": True,
            "id_dettaglio": id_dettaglio,
            "campi_modificati": list(request.modifiche.keys()),
            "message": "Riga modificata con successo"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{id_testata}/righe/{id_dettaglio}/supervisione")
async def invia_a_supervisione(
    id_testata: int,
    id_dettaglio: int,
    operatore: str = Query(...)
) -> Dict[str, Any]:
    """
    Crea o recupera supervisione per una riga espositore/anomala.
    """
    try:
        result = crea_o_recupera_supervisione(
            id_testata=id_testata,
            id_dettaglio=id_dettaglio,
            operatore=operatore
        )
        
        return {
            "success": True,
            "id_supervisione": result['id_supervisione'],
            "creata_nuova": result['creata_nuova'],
            "redirect_url": f"/supervisione/{result['id_supervisione']}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{id_testata}/stato-righe")
async def stato_righe_ordine(id_testata: int) -> Dict[str, Any]:
    """
    Ritorna riepilogo stato conferma righe di un ordine.
    """
    try:
        stato = get_stato_righe_ordine(id_testata)

        return {
            "success": True,
            "id_testata": id_testata,
            "totale": stato['totale'],
            "per_stato": {
                "estratto": stato['estratto'],
                "in_supervisione": stato['in_supervisione'],
                "supervisionato": stato['supervisionato'],
                "confermato": stato['confermato'],
                "in_tracciato": stato['in_tracciato']
            },
            "richiede_supervisione": stato['richiede_supervisione'],
            "pronto_per_tracciato": stato['confermato'] == stato['totale'],
            "percentuale_completamento": round((stato['confermato'] / stato['totale']) * 100, 1) if stato['totale'] > 0 else 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# v6.2.1: EVASIONI PARZIALI
# =============================================================================

@router.post("/{id_testata}/righe/{id_dettaglio}/evasione")
async def registra_evasione_riga(
    id_testata: int,
    id_dettaglio: int,
    request: RegistraEvasioneRequest
) -> Dict[str, Any]:
    """
    v6.2.1: Imposta quantità DA EVADERE per una riga (per il prossimo tracciato).

    NUOVA LOGICA:
    - q_da_evadere: quantità che verrà esportata nel PROSSIMO tracciato
    - q_evasa: cumulativo già esportato (aggiornato SOLO dopo generazione tracciato)
    - q_residua: rimanente da evadere = q_totale - q_evasa

    Body:
        q_da_evadere: Quantità da esportare nel prossimo tracciato
        operatore: Nome operatore

    Returns:
        success, q_da_evadere, q_evasa (cumulativo), q_residua, q_totale
    """
    try:
        result = registra_evasione(
            id_testata=id_testata,
            id_dettaglio=id_dettaglio,
            q_da_evadere=request.q_da_evadere,
            operatore=request.operatore
        )

        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('error', 'Errore impostazione quantità da evadere'))

        return {
            "success": True,
            "id_dettaglio": result['id_dettaglio'],
            "q_da_evadere": result['q_da_evadere'],
            "q_evasa": result['q_evasa'],  # Cumulativo (non cambia finché non generi tracciato)
            "q_residua": result['q_residua'],
            "q_totale": result['q_totale'],
            "message": f"Da evadere: {result['q_da_evadere']} | Già evaso: {result['q_evasa']} | Residuo: {result['q_residua']}"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# ARCHIVIAZIONE ORDINI E RIGHE
# =============================================================================
# LOGICA STATI:
# - ARCHIVIATO = ordine/riga freezato manualmente (può essere ripristinato)
# - EVASO = ordine completato (tutte righe EVASO o ARCHIVIATO)
# =============================================================================

@router.post("/{id_testata}/archivia")
async def archivia_ordine(
    id_testata: int,
    operatore: str = Query(default="admin")
) -> Dict[str, Any]:
    """
    Archivia un ordine impostando stato ARCHIVIATO.

    COMPORTAMENTO:
    - Ordine → ARCHIVIATO (freeze manuale)
    - Tutte le righe non EVASO/ARCHIVIATO → ARCHIVIATO
    - Può essere usato per ESTRATTO, CONFERMATO, PARZ_EVASO

    NOTA: Diverso da EVASO che indica completamento naturale del flusso.

    Args:
        id_testata: ID ordine
        operatore: Nome operatore che archivia
    """
    try:
        db = get_db()
        now = datetime.now().isoformat()

        # Verifica stato ordine
        ordine = db.execute("""
            SELECT stato FROM ORDINI_TESTATA WHERE id_testata = ?
        """, (id_testata,)).fetchone()

        if not ordine:
            raise HTTPException(status_code=404, detail="Ordine non trovato")

        if ordine['stato'] == 'ARCHIVIATO':
            raise HTTPException(status_code=400, detail="Ordine già archiviato")

        if ordine['stato'] == 'EVASO':
            raise HTTPException(status_code=400, detail="Ordine già evaso, non archiviabile")

        # Conta righe da archiviare
        righe_da_archiviare = db.execute("""
            SELECT COUNT(*) FROM ORDINI_DETTAGLIO
            WHERE id_testata = ? AND stato_riga NOT IN ('EVASO', 'ARCHIVIATO')
        """, (id_testata,)).fetchone()[0]

        # Aggiorna stato ordine a ARCHIVIATO
        db.execute("""
            UPDATE ORDINI_TESTATA
            SET stato = 'ARCHIVIATO',
                data_validazione = ?,
                validato_da = ?
            WHERE id_testata = ?
        """, (now, operatore, id_testata))

        # Aggiorna tutte le righe non ancora EVASO/ARCHIVIATO a ARCHIVIATO
        db.execute("""
            UPDATE ORDINI_DETTAGLIO
            SET stato_riga = 'ARCHIVIATO',
                data_conferma = ?,
                confermato_da = ?,
                q_da_evadere = 0
            WHERE id_testata = ?
              AND stato_riga NOT IN ('EVASO', 'ARCHIVIATO')
        """, (now, operatore, id_testata))

        db.commit()

        return {
            "success": True,
            "message": f"Ordine {id_testata} archiviato (frozen)",
            "stato_ordine": "ARCHIVIATO",
            "righe_archiviate": righe_da_archiviare
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{id_testata}/righe/{id_dettaglio}/archivia")
async def archivia_riga(
    id_testata: int,
    id_dettaglio: int,
    operatore: str = Query(default="admin")
) -> Dict[str, Any]:
    """
    Archivia una singola riga impostando stato ARCHIVIATO.

    COMPORTAMENTO:
    - La riga viene "freezata": non è più modificabile
    - Le quantità da evadere vengono azzerate
    - Solo procedure di ripristino possono sbloccarla
    - Può archiviare righe: ESTRATTO, CONFERMATO, PARZIALE

    STATI NON ARCHIVIABILI:
    - EVASO: già processata completamente
    - ARCHIVIATO: già freezata

    NOTA: Quando tutte le righe sono EVASO/ARCHIVIATO, l'ordine diventa EVASO.

    Args:
        id_testata: ID ordine
        id_dettaglio: ID riga
        operatore: Nome operatore che archivia
    """
    try:
        db = get_db()
        now = datetime.now().isoformat()

        # Verifica stato riga
        riga = db.execute("""
            SELECT stato_riga FROM ORDINI_DETTAGLIO
            WHERE id_dettaglio = ? AND id_testata = ?
        """, (id_dettaglio, id_testata)).fetchone()

        if not riga:
            raise HTTPException(status_code=404, detail="Riga non trovata")

        if riga['stato_riga'] == 'ARCHIVIATO':
            raise HTTPException(status_code=400, detail="Riga già archiviata")

        if riga['stato_riga'] == 'EVASO':
            raise HTTPException(status_code=400, detail="Riga già evasa, non archiviabile")

        # Aggiorna stato riga a ARCHIVIATO (freeze)
        db.execute("""
            UPDATE ORDINI_DETTAGLIO
            SET stato_riga = 'ARCHIVIATO',
                data_conferma = ?,
                confermato_da = ?,
                q_da_evadere = 0
            WHERE id_dettaglio = ? AND id_testata = ?
        """, (now, operatore, id_dettaglio, id_testata))

        # Verifica se tutte le righe sono EVASO o ARCHIVIATO -> ordine diventa EVASO
        righe_attive = db.execute("""
            SELECT COUNT(*) FROM ORDINI_DETTAGLIO
            WHERE id_testata = ? AND stato_riga NOT IN ('EVASO', 'ARCHIVIATO')
        """, (id_testata,)).fetchone()[0]

        ordine_completato = False
        if righe_attive == 0:
            # Tutte le righe sono EVASO o ARCHIVIATO → ordine EVASO (completato)
            db.execute("""
                UPDATE ORDINI_TESTATA
                SET stato = 'EVASO',
                    data_validazione = ?,
                    validato_da = ?
                WHERE id_testata = ?
                  AND stato != 'EVASO'
            """, (now, operatore, id_testata))
            ordine_completato = True

        db.commit()

        return {
            "success": True,
            "message": f"Riga {id_dettaglio} archiviata (frozen)",
            "stato_riga": "ARCHIVIATO",
            "ordine_completato": ordine_completato
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# v6.2.1: RIPRISTINO CONFERME
# =============================================================================

@router.post("/{id_testata}/righe/{id_dettaglio}/ripristina")
async def ripristina_riga_endpoint(
    id_testata: int,
    id_dettaglio: int,
    request: RipristinaRequest
) -> Dict[str, Any]:
    """
    Ripristina una singola riga allo stato pre-conferma.

    Resetta q_da_evadere a 0 e stato_riga a ESTRATTO (o PARZIALE se aveva già q_evasa).
    NON modifica q_evasa (quantità già esportate in tracciati precedenti).

    Args:
        id_testata: ID ordine
        id_dettaglio: ID riga
        operatore: Nome operatore

    Returns:
        success, stato_precedente, stato_nuovo, q_da_evadere_precedente
    """
    try:
        result = ripristina_riga(
            id_testata=id_testata,
            id_dettaglio=id_dettaglio,
            operatore=request.operatore
        )

        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('error', 'Errore ripristino riga'))

        return {
            "success": True,
            "id_dettaglio": result['id_dettaglio'],
            "stato_precedente": result['stato_precedente'],
            "stato_nuovo": result['stato_nuovo'],
            "q_da_evadere_precedente": result['q_da_evadere_precedente'],
            "message": f"Riga ripristinata: {result['stato_precedente']} -> {result['stato_nuovo']}"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{id_testata}/ripristina-tutto")
async def ripristina_ordine_endpoint(
    id_testata: int,
    request: RipristinaRequest
) -> Dict[str, Any]:
    """
    Ripristina TUTTE le righe CONFERMATO di un ordine allo stato pre-conferma.

    Resetta q_da_evadere a 0 per tutte le righe con stato CONFERMATO.
    NON tocca righe già EVASO, PARZIALE o IN_SUPERVISIONE.

    Args:
        id_testata: ID ordine
        operatore: Nome operatore

    Returns:
        success, righe_ripristinate
    """
    try:
        result = ripristina_ordine(
            id_testata=id_testata,
            operatore=request.operatore
        )

        return {
            "success": True,
            "id_testata": id_testata,
            "righe_ripristinate": result['righe_ripristinate'],
            "message": result.get('message', f"Ripristinate {result['righe_ripristinate']} righe")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# v6.2.1: FIX STATI RIGHE
# =============================================================================

@router.post("/{id_testata}/fix-stati")
async def fix_stati_ordine(id_testata: int) -> Dict[str, Any]:
    """
    Corregge gli stati delle righe di un ordine in base a q_evasa e q_totale.

    Utile per correggere dati inconsistenti.
    """
    try:
        result = fix_stati_righe(id_testata)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/fix-stati-tutti")
async def fix_stati_tutti() -> Dict[str, Any]:
    """
    Corregge gli stati di TUTTE le righe in base a q_evasa e q_totale.

    Utile per correggere dati inconsistenti dopo migrazione.
    """
    try:
        result = fix_stati_righe(None)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
