# =============================================================================
# SERV.O v11.0 - ORDINI ROUTER
# =============================================================================
# Endpoint per gestione ordini e conferma righe
# v11.0: Archiviazione tramite service layer
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
# v11.0: Archiviazione centralizzata
from ..services.orders.commands import (
    archivia_ordine as service_archivia_ordine,
    archivia_riga as service_archivia_riga,
)

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


class ModificaHeaderRequest(BaseModel):
    """
    Request per modifica manuale header ordine (v11.3).

    La modifica manuale ha priorità MASSIMA:
    - Sovrascrive i dati estratti dal PDF
    - Sovrascrive i dati da lookup automatico
    - Permette correzione errori anagrafica ministeriale
    """
    # Dati farmacia
    partita_iva: Optional[str] = None
    min_id: Optional[str] = None
    ragione_sociale: Optional[str] = None

    # Deposito
    deposito_riferimento: Optional[str] = None

    # Indirizzo (opzionale)
    indirizzo: Optional[str] = None
    cap: Optional[str] = None
    localita: Optional[str] = None
    provincia: Optional[str] = None

    # Metadati
    operatore: str
    note: Optional[str] = None


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


@router.get("/stats")
async def ordini_stats() -> Dict[str, Any]:
    """
    v11.3: Ritorna statistiche ordini per dashboard.

    Include:
    - totali: conteggi totali per stato
    - oggi: conteggi giornalieri per stato
    - anomalie_aperte: totale anomalie aperte
    """
    from ..database_pg import get_db
    db = get_db()

    # Stats totali per stato
    totali_per_stato = {}
    rows = db.execute("""
        SELECT stato, COUNT(*) as count
        FROM ORDINI_TESTATA
        GROUP BY stato
    """).fetchall()
    for row in rows:
        totali_per_stato[row['stato'] or 'NULL'] = row['count']

    # Stats oggi per stato
    oggi_per_stato = {}
    rows_oggi = db.execute("""
        SELECT stato, COUNT(*) as count
        FROM ORDINI_TESTATA
        WHERE data_estrazione::date = CURRENT_DATE
        GROUP BY stato
    """).fetchall()
    for row in rows_oggi:
        oggi_per_stato[row['stato'] or 'NULL'] = row['count']

    # Anomalie aperte totali e oggi
    anomalie_totali = db.execute(
        "SELECT COUNT(*) FROM ANOMALIE WHERE stato IN ('APERTA', 'IN_GESTIONE')"
    ).fetchone()[0]
    anomalie_oggi = db.execute(
        "SELECT COUNT(*) FROM ANOMALIE WHERE stato IN ('APERTA', 'IN_GESTIONE') AND data_creazione::date = CURRENT_DATE"
    ).fetchone()[0]

    return {
        "success": True,
        "data": {
            "totali": {
                "ordini": sum(totali_per_stato.values()),
                "estratto": totali_per_stato.get('ESTRATTO', 0),
                "confermato": totali_per_stato.get('CONFERMATO', 0),
                "anomalia": totali_per_stato.get('ANOMALIA', 0),
                "parz_evaso": totali_per_stato.get('PARZ_EVASO', 0),
                "evaso": totali_per_stato.get('EVASO', 0),
                "archiviato": totali_per_stato.get('ARCHIVIATO', 0),
                "anomalie_aperte": anomalie_totali,
            },
            "oggi": {
                "ordini": sum(oggi_per_stato.values()),
                "estratto": oggi_per_stato.get('ESTRATTO', 0),
                "confermato": oggi_per_stato.get('CONFERMATO', 0),
                "anomalia": oggi_per_stato.get('ANOMALIA', 0),
                "parz_evaso": oggi_per_stato.get('PARZ_EVASO', 0),
                "evaso": oggi_per_stato.get('EVASO', 0),
                "archiviato": oggi_per_stato.get('ARCHIVIATO', 0),
                "anomalie_aperte": anomalie_oggi,
            }
        }
    }


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
async def righe_ordine(
    id_testata: int,
    include_children: bool = Query(False, description="Include righe CHILD_ESPOSITORE (per EspositoreTab)")
) -> Dict[str, Any]:
    """
    Ritorna le righe dettaglio di un ordine.

    Per default esclude le righe CHILD_ESPOSITORE (mostrate aggregate nel parent).
    Con include_children=true ritorna tutte le righe (per editing espositore).
    """
    try:
        righe = get_ordine_righe(id_testata, include_children=include_children)
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

    v11.3: Blocca conferma se data_consegna > 30 giorni da oggi.
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
            # v11.3: Data consegna bloccante
            if result.get('data_consegna_bloccante'):
                return {
                    "success": False,
                    "message": result.get('error'),
                    "data_consegna_bloccante": True,
                    "data_consegna": result.get('data_consegna'),
                    "data_limite": result.get('data_limite'),
                    "giorni_mancanti": result.get('giorni_mancanti')
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

    v11.3: Esclude automaticamente righe con data_consegna > 30 giorni da oggi.
    """
    try:
        result = conferma_ordine_completo(
            id_testata=id_testata,
            operatore=request.operatore,
            forza_conferma=request.forza_conferma,
            note=request.note
        )

        # v11.3: Costruisci messaggio dettagliato
        msgs = [f"Confermate {result['confermate']} righe"]

        bloccate_supervisione = result.get('bloccate_supervisione', [])
        bloccate_data = result.get('bloccate_data_consegna', [])

        if bloccate_supervisione:
            msgs.append(f"{len(bloccate_supervisione)} richiedono supervisione")

        if bloccate_data:
            msgs.append(f"{len(bloccate_data)} bloccate per data consegna oltre 30 giorni")

        return {
            "success": True,
            "id_testata": id_testata,
            "righe_confermate": result['confermate'],
            "righe_bloccate": result['bloccate'],
            "righe_bloccate_supervisione": bloccate_supervisione,
            "righe_bloccate_data_consegna": bloccate_data,
            "righe_gia_confermate": result['gia_confermate'],
            "ordine_completo": result['ordine_completo'],
            "message": ", ".join(msgs)
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


# =============================================================================
# MODIFICA HEADER ORDINE (v11.3)
# =============================================================================

@router.patch("/{id_testata}/header")
async def modifica_header_ordine(
    id_testata: int,
    request: ModificaHeaderRequest
) -> Dict[str, Any]:
    """
    Modifica manualmente i campi dell'header (testata) di un ordine.

    ## Priorità MASSIMA

    La modifica manuale ha priorità superiore a:
    - Dati estratti dal PDF
    - Lookup automatico (PIVA, FUZZY, etc.)
    - Anagrafica ministeriale

    ## Campi modificabili

    - `partita_iva`: P.IVA cliente (11-16 caratteri)
    - `min_id`: Codice ministeriale farmacia
    - `ragione_sociale`: Nome farmacia
    - `deposito_riferimento`: Codice deposito (CT, CL, PE, CB, etc.)
    - `indirizzo`, `cap`, `localita`, `provincia`: Dati indirizzo

    ## Comportamento

    1. Salva valori originali in JSON per audit trail
    2. Aggiorna solo i campi forniti (non nulli)
    3. Imposta `lookup_method = 'MANUALE'` e `lookup_score = 100`
    4. Registra modifica in log_operazioni
    5. Risolve automaticamente anomalie LKP correlate

    ## Vincoli

    - Non modificabile se ordine in stato EVASO o ARCHIVIATO
    - Almeno un campo deve essere fornito
    """
    import json
    from ..database_pg import get_db, log_operation

    db = get_db()

    try:
        # 1. Verifica esistenza ordine
        ordine = db.execute("""
            SELECT ot.*, v.codice_vendor as vendor
            FROM ordini_testata ot
            LEFT JOIN vendor v ON ot.id_vendor = v.id_vendor
            WHERE ot.id_testata = %s
        """, (id_testata,)).fetchone()

        if not ordine:
            raise HTTPException(status_code=404, detail="Ordine non trovato")

        # 2. Verifica stato ordine
        stato = ordine['stato']
        if stato in ('EVASO', 'ARCHIVIATO'):
            raise HTTPException(
                status_code=400,
                detail=f"Ordine in stato {stato} non modificabile"
            )

        # 3. Salva valori originali per audit
        valori_originali = {
            'partita_iva': ordine.get('partita_iva') or ordine.get('partita_iva_estratta'),
            'min_id': ordine.get('min_id'),
            'ragione_sociale': ordine.get('ragione_sociale') or ordine.get('ragione_sociale_1'),
            'deposito_riferimento': ordine.get('deposito_riferimento'),
            'indirizzo': ordine.get('indirizzo'),
            'cap': ordine.get('cap'),
            'localita': ordine.get('localita') or ordine.get('citta'),
            'provincia': ordine.get('provincia'),
            'lookup_method': ordine.get('lookup_method'),
            'lookup_score': ordine.get('lookup_score'),
        }

        # 4. Costruisci UPDATE dinamico
        updates = []
        params = []
        campi_modificati = []

        field_mapping = {
            'partita_iva': request.partita_iva,
            'min_id': request.min_id,
            'ragione_sociale': request.ragione_sociale,
            'deposito_riferimento': request.deposito_riferimento,
            'indirizzo': request.indirizzo,
            'cap': request.cap,
            'localita': request.localita,
            'provincia': request.provincia,
        }

        for field, value in field_mapping.items():
            if value is not None:
                # Mapping nomi campo frontend -> colonne DB reali
                # Usa solo colonne che esistono in ordini_testata
                if field == 'partita_iva':
                    updates.append("partita_iva_estratta = %s")
                    params.append(value.strip())
                elif field == 'ragione_sociale':
                    updates.append("ragione_sociale_1 = %s")
                    params.append(value.strip())
                elif field == 'localita':
                    updates.append("citta = %s")
                    params.append(value.strip())
                else:
                    updates.append(f"{field} = %s")
                    params.append(value.strip() if isinstance(value, str) else value)

                campi_modificati.append(field)

        if not campi_modificati:
            raise HTTPException(status_code=400, detail="Nessun campo da modificare fornito")

        # 5. Aggiungi metadati modifica manuale
        # PRIORITÀ MASSIMA: lookup_method = MANUALE, score = 100
        updates.append("lookup_method = 'MANUALE'")
        updates.append("lookup_score = 100")

        # Audit trail
        updates.append("valori_originali_header = %s")
        params.append(json.dumps(valori_originali, default=str))

        updates.append("data_modifica_header = CURRENT_TIMESTAMP")

        updates.append("operatore_modifica_header = %s")
        params.append(request.operatore)

        if request.note:
            updates.append("note_modifica_header = %s")
            params.append(request.note)

        params.append(id_testata)  # WHERE clause

        # 6. Esegui UPDATE
        db.execute(f"""
            UPDATE ordini_testata
            SET {', '.join(updates)}
            WHERE id_testata = %s
        """, tuple(params))

        # 7. Risolvi anomalie LKP correlate (se P.IVA o MIN_ID modificati)
        anomalie_risolte = 0
        if request.partita_iva or request.min_id or request.deposito_riferimento:
            result = db.execute("""
                UPDATE anomalie
                SET stato = 'RISOLTA',
                    note_risoluzione = %s,
                    data_risoluzione = CURRENT_TIMESTAMP
                WHERE id_testata = %s
                  AND codice_anomalia IN ('LKP-A01', 'LKP-A02', 'LKP-A03', 'LKP-A04', 'LKP-A05')
                  AND stato IN ('APERTA', 'IN_GESTIONE')
            """, (
                f"[MANUALE] Header modificato da {request.operatore}. {request.note or ''}",
                id_testata
            ))
            anomalie_risolte = result.rowcount if hasattr(result, 'rowcount') else 0

            # Sblocca ordine se non ci sono altre anomalie
            anomalie_aperte = db.execute("""
                SELECT COUNT(*) FROM anomalie
                WHERE id_testata = %s
                  AND stato IN ('APERTA', 'IN_GESTIONE')
                  AND livello IN ('ERRORE', 'CRITICO')
            """, (id_testata,)).fetchone()[0]

            if anomalie_aperte == 0:
                db.execute("""
                    UPDATE ordini_testata
                    SET stato = 'ESTRATTO'
                    WHERE id_testata = %s AND stato = 'ANOMALIA'
                """, (id_testata,))

        # 8. Log operazione
        log_operation(
            'MODIFICA_HEADER_MANUALE',
            'ORDINI_TESTATA',
            id_testata,
            f"Modificati: {', '.join(campi_modificati)}",
            dati={
                'campi_modificati': campi_modificati,
                'valori_originali': valori_originali,
                'valori_nuovi': {k: v for k, v in field_mapping.items() if v is not None},
                'anomalie_risolte': anomalie_risolte,
                'note': request.note
            },
            operatore=request.operatore
        )

        db.commit()

        return {
            "success": True,
            "message": f"Header ordine {id_testata} aggiornato",
            "data": {
                "id_testata": id_testata,
                "campi_modificati": campi_modificati,
                "valori_originali": valori_originali,
                "lookup_method": "MANUALE",
                "lookup_score": 100,
                "anomalie_risolte": anomalie_risolte
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
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
        # v11.0: Usa service layer invece di logica diretta
        result = service_archivia_ordine(id_testata, operatore)

        if not result.success:
            status_code = 404 if 'non trovato' in result.error.lower() else 400
            raise HTTPException(status_code=status_code, detail=result.error)

        return {
            "success": True,
            "message": f"Ordine {id_testata} archiviato (frozen)",
            "stato_ordine": result.stato_ordine,
            "righe_archiviate": result.righe_archiviate
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
        # v11.0: Usa service layer invece di logica diretta
        result = service_archivia_riga(id_testata, id_dettaglio, operatore)

        if not result.success:
            status_code = 404 if 'non trovata' in result.error.lower() else 400
            raise HTTPException(status_code=status_code, detail=result.error)

        return {
            "success": True,
            "message": f"Riga {id_dettaglio} archiviata (frozen)",
            "stato_riga": result.stato_riga,
            "ordine_completato": result.ordine_completato
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


# =============================================================================
# v11.0: FIX ESPOSITORE - Correzione relazioni parent/child
# =============================================================================

class EspositoreRigaUpdate(BaseModel):
    id_dettaglio: int
    tipo_riga: str  # 'NORMAL', 'PARENT_ESPOSITORE', 'CHILD_ESPOSITORE'
    id_parent_espositore: Optional[int] = None  # Required if tipo_riga == 'CHILD_ESPOSITORE'

class FixEspositoreRequest(BaseModel):
    righe: List[EspositoreRigaUpdate]
    operatore: str
    note: Optional[str] = None


@router.put("/{id_testata}/fix-espositore")
async def fix_espositore(
    id_testata: int,
    request: FixEspositoreRequest
) -> Dict[str, Any]:
    """
    Corregge le relazioni parent/child (espositore) per le righe di un ordine.

    Permette di:
    - Impostare una riga come PARENT_ESPOSITORE
    - Impostare righe come CHILD_ESPOSITORE collegandole a un parent
    - Reimpostare righe come NORMAL (senza relazione espositore)

    Args:
        id_testata: ID ordine
        request: Lista righe con nuovo tipo e parent (se child)

    Returns:
        success, righe_aggiornate, dettagli
    """
    db = get_db()

    try:
        # Verifica ordine esiste
        ordine = db.execute(
            "SELECT id_testata, stato FROM ordini_testata WHERE id_testata = %s",
            (id_testata,)
        ).fetchone()

        if not ordine:
            raise HTTPException(status_code=404, detail="Ordine non trovato")

        # Verifica che tutte le righe appartengano all'ordine
        id_righe = [r.id_dettaglio for r in request.righe]
        placeholders = ','.join(['%s'] * len(id_righe))
        existing = db.execute(
            f"SELECT id_dettaglio FROM ordini_dettaglio WHERE id_testata = %s AND id_dettaglio IN ({placeholders})",
            (id_testata, *id_righe)
        ).fetchall()
        existing_ids = {r['id_dettaglio'] for r in existing}

        missing = set(id_righe) - existing_ids
        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"Righe non trovate nell'ordine: {list(missing)}"
            )

        # Raccogli gli ID dei parent per validazione
        parent_ids = {r.id_dettaglio for r in request.righe if r.tipo_riga == 'PARENT_ESPOSITORE'}

        # Valida che i child puntino a parent validi
        for riga in request.righe:
            if riga.tipo_riga == 'CHILD_ESPOSITORE':
                if not riga.id_parent_espositore:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Riga {riga.id_dettaglio}: CHILD_ESPOSITORE richiede id_parent_espositore"
                    )
                if riga.id_parent_espositore not in parent_ids:
                    # Verifica se il parent esiste già nel DB
                    parent_exists = db.execute(
                        "SELECT 1 FROM ordini_dettaglio WHERE id_dettaglio = %s AND id_testata = %s",
                        (riga.id_parent_espositore, id_testata)
                    ).fetchone()
                    if not parent_exists:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Riga {riga.id_dettaglio}: parent {riga.id_parent_espositore} non trovato"
                        )

        # Applica gli aggiornamenti
        righe_aggiornate = 0
        dettagli = []

        for riga in request.righe:
            if riga.tipo_riga == 'PARENT_ESPOSITORE':
                db.execute("""
                    UPDATE ordini_dettaglio
                    SET tipo_riga = 'PARENT_ESPOSITORE',
                        is_espositore = TRUE,
                        is_child = FALSE,
                        id_parent_espositore = NULL
                    WHERE id_dettaglio = %s
                """, (riga.id_dettaglio,))
                dettagli.append({
                    'id_dettaglio': riga.id_dettaglio,
                    'tipo': 'PARENT_ESPOSITORE',
                    'parent': None
                })

            elif riga.tipo_riga == 'CHILD_ESPOSITORE':
                db.execute("""
                    UPDATE ordini_dettaglio
                    SET tipo_riga = 'CHILD_ESPOSITORE',
                        is_espositore = TRUE,
                        is_child = TRUE,
                        id_parent_espositore = %s
                    WHERE id_dettaglio = %s
                """, (riga.id_parent_espositore, riga.id_dettaglio))
                dettagli.append({
                    'id_dettaglio': riga.id_dettaglio,
                    'tipo': 'CHILD_ESPOSITORE',
                    'parent': riga.id_parent_espositore
                })

            else:  # NORMAL
                db.execute("""
                    UPDATE ordini_dettaglio
                    SET tipo_riga = '',
                        is_espositore = FALSE,
                        is_child = FALSE,
                        id_parent_espositore = NULL
                    WHERE id_dettaglio = %s
                """, (riga.id_dettaglio,))
                dettagli.append({
                    'id_dettaglio': riga.id_dettaglio,
                    'tipo': 'NORMAL',
                    'parent': None
                })

            righe_aggiornate += 1

        # Log operazione
        db.execute("""
            INSERT INTO log_operazioni (tipo_operazione, entita, id_entita, descrizione, username_snapshot)
            VALUES ('FIX_ESPOSITORE', 'ordini_dettaglio', %s, %s, %s)
        """, (
            id_testata,
            f"Aggiornate {righe_aggiornate} righe: {request.note or 'Fix espositore'}",
            request.operatore
        ))

        db.commit()

        return {
            "success": True,
            "id_testata": id_testata,
            "righe_aggiornate": righe_aggiornate,
            "dettagli": dettagli,
            "message": f"Relazioni espositore aggiornate per {righe_aggiornate} righe"
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
