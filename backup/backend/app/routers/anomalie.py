# =============================================================================
# TO_EXTRACTOR v6.0 - ANOMALIE ROUTER
# =============================================================================
# Endpoint per gestione anomalie
# =============================================================================

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from ..services.ordini import (
    get_anomalie,
    get_anomalie_by_ordine,
    update_anomalia_stato,
    create_anomalia,
)


router = APIRouter(prefix="/anomalie")


# =============================================================================
# MODELLI
# =============================================================================

class AnomaliaUpdate(BaseModel):
    stato: str
    note: Optional[str] = None


class AnomaliaCreate(BaseModel):
    id_testata: Optional[int] = None
    id_dettaglio: Optional[int] = None
    id_acquisizione: Optional[int] = None
    tipo: str = "ALTRO"
    livello: str = "ATTENZIONE"
    descrizione: str
    valore_anomalo: Optional[str] = None


# =============================================================================
# LISTA E FILTRI
# =============================================================================

@router.get("")
async def lista_anomalie(
    tipo: Optional[str] = Query(None, description="Tipo anomalia"),
    livello: Optional[str] = Query(None, description="Livello: INFO, ATTENZIONE, ERRORE, CRITICO"),
    stato: Optional[str] = Query(None, description="Stato: APERTA, IN_GESTIONE, RISOLTA, IGNORATA"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0)
) -> Dict[str, Any]:
    """
    Ritorna lista anomalie con filtri.
    
    Tipi: LOOKUP, ESPOSITORE, CHILD, NO_AIC, PIVA_MULTIPUNTO, 
          VALIDAZIONE, DUPLICATO_PDF, DUPLICATO_ORDINE, ALTRO
          
    Livelli: INFO, ATTENZIONE, ERRORE, CRITICO
    
    Stati: APERTA, IN_GESTIONE, RISOLTA, IGNORATA
    """
    try:
        result = get_anomalie(
            tipo=tipo,
            livello=livello,
            stato=stato,
            limit=limit,
            offset=offset
        )
        
        return {
            "success": True,
            "data": result['anomalie'],
            "pagination": {
                "totale": result['totale'],
                "limit": result['limit'],
                "offset": result['offset']
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tipi")
async def lista_tipi() -> Dict[str, Any]:
    """
    Ritorna lista tipi anomalia.
    """
    return {
        "success": True,
        "data": [
            {"code": "LOOKUP", "label": "Lookup farmacia fallito", "severity": "error"},
            {"code": "ESPOSITORE", "label": "Riga espositore/banco", "severity": "info"},
            {"code": "CHILD", "label": "Riga child (ignorata)", "severity": "info"},
            {"code": "NO_AIC", "label": "Codice AIC mancante", "severity": "warning"},
            {"code": "PIVA_MULTIPUNTO", "label": "P.IVA multipunto", "severity": "warning"},
            {"code": "VALIDAZIONE", "label": "Errore validazione dati", "severity": "warning"},
            {"code": "DUPLICATO_PDF", "label": "PDF duplicato", "severity": "warning"},
            {"code": "DUPLICATO_ORDINE", "label": "Ordine duplicato", "severity": "warning"},
            {"code": "ALTRO", "label": "Altro", "severity": "info"},
        ]
    }


@router.get("/livelli")
async def lista_livelli() -> Dict[str, Any]:
    """
    Ritorna lista livelli anomalia.
    """
    return {
        "success": True,
        "data": [
            {"code": "INFO", "label": "Informazione", "color": "blue"},
            {"code": "ATTENZIONE", "label": "Attenzione", "color": "yellow"},
            {"code": "ERRORE", "label": "Errore", "color": "red"},
            {"code": "CRITICO", "label": "Critico", "color": "purple"},
        ]
    }


@router.get("/stati")
async def lista_stati() -> Dict[str, Any]:
    """
    Ritorna lista stati anomalia.
    """
    return {
        "success": True,
        "data": [
            {"code": "APERTA", "label": "Aperta", "color": "red"},
            {"code": "IN_GESTIONE", "label": "In gestione", "color": "yellow"},
            {"code": "RISOLTA", "label": "Risolta", "color": "green"},
            {"code": "IGNORATA", "label": "Ignorata", "color": "gray"},
        ]
    }


# =============================================================================
# DETTAGLIO E MODIFICA
# =============================================================================

@router.get("/ordine/{id_testata}")
async def anomalie_ordine(id_testata: int) -> Dict[str, Any]:
    """
    Ritorna anomalie di un ordine specifico.
    """
    try:
        anomalie = get_anomalie_by_ordine(id_testata)
        return {
            "success": True,
            "data": anomalie,
            "count": len(anomalie)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{id_anomalia}")
async def aggiorna_anomalia(
    id_anomalia: int,
    update: AnomaliaUpdate
) -> Dict[str, Any]:
    """
    Aggiorna stato anomalia.
    
    Stati validi: APERTA, IN_GESTIONE, RISOLTA, IGNORATA
    """
    stati_validi = ['APERTA', 'IN_GESTIONE', 'RISOLTA', 'IGNORATA']
    
    if update.stato not in stati_validi:
        raise HTTPException(
            status_code=400,
            detail=f"Stato non valido. Valori accettati: {', '.join(stati_validi)}"
        )
    
    try:
        success = update_anomalia_stato(id_anomalia, update.stato, update.note)
        
        if not success:
            raise HTTPException(status_code=404, detail="Anomalia non trovata")
        
        return {
            "success": True,
            "message": f"Anomalia aggiornata a {update.stato}"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
async def crea_anomalia(anomalia: AnomaliaCreate) -> Dict[str, Any]:
    """
    Crea nuova anomalia manualmente.
    """
    tipi_validi = ['LOOKUP', 'ESPOSITORE', 'CHILD', 'NO_AIC', 'PIVA_MULTIPUNTO',
                   'VALIDAZIONE', 'DUPLICATO_PDF', 'DUPLICATO_ORDINE', 'ALTRO']
    livelli_validi = ['INFO', 'ATTENZIONE', 'ERRORE', 'CRITICO']
    
    if anomalia.tipo not in tipi_validi:
        raise HTTPException(status_code=400, detail="Tipo non valido")
    
    if anomalia.livello not in livelli_validi:
        raise HTTPException(status_code=400, detail="Livello non valido")
    
    try:
        id_anomalia = create_anomalia(
            id_testata=anomalia.id_testata,
            id_dettaglio=anomalia.id_dettaglio,
            id_acquisizione=anomalia.id_acquisizione,
            tipo=anomalia.tipo,
            livello=anomalia.livello,
            descrizione=anomalia.descrizione,
            valore_anomalo=anomalia.valore_anomalo
        )
        
        return {
            "success": True,
            "data": {"id_anomalia": id_anomalia},
            "message": "Anomalia creata"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# AZIONI BATCH
# =============================================================================

@router.post("/batch/stato")
async def aggiorna_stato_batch(
    ids: List[int],
    nuovo_stato: str,
    note: Optional[str] = None
) -> Dict[str, Any]:
    """
    Aggiorna stato di più anomalie.
    """
    stati_validi = ['APERTA', 'IN_GESTIONE', 'RISOLTA', 'IGNORATA']
    
    if nuovo_stato not in stati_validi:
        raise HTTPException(status_code=400, detail="Stato non valido")
    
    try:
        success_count = 0
        for id_anomalia in ids:
            if update_anomalia_stato(id_anomalia, nuovo_stato, note):
                success_count += 1
        
        return {
            "success": True,
            "data": {
                "aggiornate": success_count,
                "totale": len(ids)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch/risolvi")
async def risolvi_batch(
    ids: List[int],
    note: Optional[str] = "Risoluzione batch"
) -> Dict[str, Any]:
    """
    Risolvi più anomalie in una volta.
    """
    return await aggiorna_stato_batch(ids, 'RISOLTA', note)


@router.post("/batch/ignora")
async def ignora_batch(
    ids: List[int],
    note: Optional[str] = "Ignorata"
) -> Dict[str, Any]:
    """
    Ignora più anomalie in una volta.
    """
    return await aggiorna_stato_batch(ids, 'IGNORATA', note)


# =============================================================================
# DETTAGLIO SINGOLA ANOMALIA (deve stare dopo le route specifiche)
# =============================================================================

class RigaUpdate(BaseModel):
    """Modello per aggiornamento riga parent."""
    q_venduta: Optional[int] = None
    descrizione: Optional[str] = None
    codice_originale: Optional[str] = None
    prezzo_netto: Optional[float] = None
    note_allestimento: Optional[str] = None


@router.get("/dettaglio/{id_anomalia}")
async def dettaglio_anomalia(id_anomalia: int) -> Dict[str, Any]:
    """
    Ritorna dettaglio completo anomalia con riga parent e righe child.

    Utile per visualizzare espositori con le relative righe componenti.
    """
    from ..database_pg import get_db

    try:
        db = get_db()

        # Recupera anomalia
        anomalia = db.execute("""
            SELECT
                an.*,
                v.codice_vendor AS vendor,
                ot.numero_ordine_vendor AS numero_ordine,
                ot.ragione_sociale_1 AS ragione_sociale,
                ot.data_ordine,
                a.nome_file_originale AS pdf_file
            FROM anomalie an
            LEFT JOIN ordini_testata ot ON an.id_testata = ot.id_testata
            LEFT JOIN vendor v ON ot.id_vendor = v.id_vendor
            LEFT JOIN acquisizioni a ON COALESCE(an.id_acquisizione, ot.id_acquisizione) = a.id_acquisizione
            WHERE an.id_anomalia = ?
        """, (id_anomalia,)).fetchone()

        if not anomalia:
            raise HTTPException(status_code=404, detail="Anomalia non trovata")

        anomalia_dict = dict(anomalia)

        # Se c'è id_dettaglio, recupera riga parent e relative child
        riga_parent = None
        righe_child = []

        if anomalia_dict.get('id_dettaglio'):
            # Recupera riga parent
            parent = db.execute("""
                SELECT * FROM ORDINI_DETTAGLIO
                WHERE id_dettaglio = ?
            """, (anomalia_dict['id_dettaglio'],)).fetchone()

            if parent:
                riga_parent = dict(parent)

                # Recupera righe child collegate
                children = db.execute("""
                    SELECT * FROM ORDINI_DETTAGLIO
                    WHERE id_parent_espositore = ?
                    ORDER BY n_riga
                """, (anomalia_dict['id_dettaglio'],)).fetchall()

                righe_child = [dict(c) for c in children]

        # Se non c'è id_dettaglio ma c'è id_testata, cerca espositori nell'ordine
        elif anomalia_dict.get('id_testata'):
            # Cerca righe espositore parent nell'ordine
            espositori = db.execute("""
                SELECT od.*,
                       (SELECT COUNT(*) FROM ORDINI_DETTAGLIO c WHERE c.id_parent_espositore = od.id_dettaglio) AS num_children
                FROM ORDINI_DETTAGLIO od
                WHERE od.id_testata = ? AND od.is_espositore = TRUE AND (od.is_child = FALSE OR od.is_child IS NULL)
                ORDER BY od.n_riga
            """, (anomalia_dict['id_testata'],)).fetchall()

            if espositori:
                # Prendi il primo espositore come parent di riferimento
                riga_parent = dict(espositori[0])

                # Recupera i suoi children
                children = db.execute("""
                    SELECT * FROM ORDINI_DETTAGLIO
                    WHERE id_parent_espositore = ?
                    ORDER BY n_riga
                """, (riga_parent['id_dettaglio'],)).fetchall()

                righe_child = [dict(c) for c in children]

        # Per anomalie LOOKUP, includi dati ordine per ricerca manuale
        ordine_data = None
        tipo_anomalia = anomalia_dict.get('tipo_anomalia', '')
        codice_anomalia = anomalia_dict.get('codice_anomalia', '')

        if tipo_anomalia == 'LOOKUP' or (codice_anomalia and codice_anomalia.startswith('LKP-')):
            if anomalia_dict.get('id_testata'):
                ordine = db.execute("""
                    SELECT
                        partita_iva_estratta AS partita_iva,
                        codice_ministeriale_estratto AS codice_ministeriale,
                        ragione_sociale_1 AS ragione_sociale,
                        indirizzo,
                        cap,
                        citta,
                        provincia,
                        lookup_method,
                        lookup_score
                    FROM ORDINI_TESTATA
                    WHERE id_testata = ?
                """, (anomalia_dict['id_testata'],)).fetchone()

                if ordine:
                    ordine_data = dict(ordine)

        return {
            "success": True,
            "data": {
                "anomalia": anomalia_dict,
                "riga_parent": riga_parent,
                "righe_child": righe_child,
                "totale_child": len(righe_child),
                "ordine_data": ordine_data
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/dettaglio/{id_anomalia}/riga")
async def modifica_riga_anomalia(
    id_anomalia: int,
    update: RigaUpdate
) -> Dict[str, Any]:
    """
    Modifica la riga parent associata a un'anomalia.

    Permette di correggere quantità, descrizione, codice o note.
    """
    from ..database_pg import get_db

    try:
        db = get_db()

        # Recupera anomalia per ottenere id_dettaglio
        anomalia = db.execute(
            "SELECT id_dettaglio, id_testata FROM ANOMALIE WHERE id_anomalia = ?",
            (id_anomalia,)
        ).fetchone()

        if not anomalia:
            raise HTTPException(status_code=404, detail="Anomalia non trovata")

        id_dettaglio = anomalia['id_dettaglio']

        if not id_dettaglio:
            raise HTTPException(status_code=400, detail="Anomalia non collegata a una riga specifica")

        # Costruisci query di update dinamica
        updates = []
        params = []

        if update.q_venduta is not None:
            updates.append("q_venduta = ?")
            params.append(update.q_venduta)

        if update.descrizione is not None:
            updates.append("descrizione = ?")
            params.append(update.descrizione)

        if update.codice_originale is not None:
            updates.append("codice_originale = ?")
            params.append(update.codice_originale)

        if update.prezzo_netto is not None:
            updates.append("prezzo_netto = ?")
            params.append(update.prezzo_netto)

        if update.note_allestimento is not None:
            updates.append("note_allestimento = ?")
            params.append(update.note_allestimento)

        if not updates:
            raise HTTPException(status_code=400, detail="Nessun campo da aggiornare")

        # Esegui update
        params.append(id_dettaglio)
        db.execute(
            f"UPDATE ORDINI_DETTAGLIO SET {', '.join(updates)} WHERE id_dettaglio = ?",
            params
        )
        db.commit()

        return {
            "success": True,
            "message": "Riga aggiornata",
            "id_dettaglio": id_dettaglio
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dettaglio/{id_anomalia}/risolvi")
async def risolvi_anomalia_dettaglio(
    id_anomalia: int,
    note: Optional[str] = "Risolta da dettaglio"
) -> Dict[str, Any]:
    """
    Risolve un'anomalia dopo aver verificato/modificato la riga.
    """
    try:
        success = update_anomalia_stato(id_anomalia, 'RISOLTA', note)

        if not success:
            raise HTTPException(status_code=404, detail="Anomalia non trovata")

        return {
            "success": True,
            "message": "Anomalia risolta"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
