# =============================================================================
# SERV.O v8.2 - ANOMALIE ROUTER
# =============================================================================
# Endpoint per gestione anomalie
# Con supporto propagazione AIC
# =============================================================================

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from enum import Enum

from ..auth.dependencies import get_current_user
from ..auth.models import UtenteResponse

from ..services.ordini import (
    get_anomalie,
    get_anomalie_by_ordine,
    create_anomalia,
)
# v10.4: Usa la versione aggiornata che gestisce TUTTE le supervisioni e ML
from ..services.anomalies.commands import update_anomalia_stato
# v11.4: Usa modulo AIC rifattorizzato
from ..services.supervision.aic import (
    LivelloPropagazione as LivelloPropagazioneAIC,
    risolvi_anomalia_aic,
    propaga_aic,
    valida_codice_aic,
)
# v10.5: Propagazione generica anomalie
from ..services.anomalies.propagazione import (
    LivelloPropagazione,
    get_livello_permesso,
    conta_anomalie_identiche,
    risolvi_anomalia_con_propagazione,
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


class BatchAnomalieRequest(BaseModel):
    """Modello per operazioni batch su anomalie."""
    ids: List[int]
    note: Optional[str] = None


class RisoluzionePropagazioneRequest(BaseModel):
    """Modello per risoluzione anomalia con propagazione v10.5."""
    livello_propagazione: str = "ORDINE"  # ORDINE (default), GLOBALE (solo supervisore+)
    operatore: str
    ruolo: str = "operatore"  # Per verifica permessi
    note: Optional[str] = None


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
            {"code": "DEPOSITO", "label": "Deposito mancante", "severity": "error"},
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
    update: AnomaliaUpdate,
    current_user: UtenteResponse = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Aggiorna stato anomalia.

    Stati validi: APERTA, IN_GESTIONE, RISOLTA, IGNORATA

    v11.2: Gestione ruoli per supervisioni:
    - SUPERVISORE/ADMIN → risolve anomalia + supervisione collegata
    - OPERATORE → risolve anomalia ma supervisione resta PENDING
    """
    stati_validi = ['APERTA', 'IN_GESTIONE', 'RISOLTA', 'IGNORATA']

    if update.stato not in stati_validi:
        raise HTTPException(
            status_code=400,
            detail=f"Stato non valido. Valori accettati: {', '.join(stati_validi)}"
        )

    try:
        # v11.2: Passa ruolo per gestione supervisioni
        ruolo = current_user.ruolo if current_user.ruolo else 'operatore'
        operatore = current_user.username if current_user else 'system'

        success = update_anomalia_stato(
            id_anomalia,
            update.stato,
            update.note,
            operatore=operatore,
            ruolo=ruolo
        )

        if not success:
            raise HTTPException(status_code=404, detail="Anomalia non trovata")

        # v11.2: Informa se supervisione è stata risolta automaticamente
        sup_risolta = ruolo.lower() in ['supervisore', 'admin']

        return {
            "success": True,
            "message": f"Anomalia aggiornata a {update.stato}",
            "supervisione_risolta": sup_risolta if update.stato in ('RISOLTA', 'IGNORATA') else None
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
    request: BatchAnomalieRequest,
    nuovo_stato: str = Query(..., description="Nuovo stato da applicare"),
    current_user: UtenteResponse = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Aggiorna stato di più anomalie.

    v11.2: Se SUPERVISORE/ADMIN risolve anche le supervisioni collegate.
    """
    stati_validi = ['APERTA', 'IN_GESTIONE', 'RISOLTA', 'IGNORATA']

    if nuovo_stato not in stati_validi:
        raise HTTPException(status_code=400, detail="Stato non valido")

    ruolo = current_user.ruolo if current_user.ruolo else 'operatore'
    operatore = current_user.username if current_user else 'system'

    try:
        success_count = 0
        for id_anomalia in request.ids:
            if update_anomalia_stato(id_anomalia, nuovo_stato, request.note, operatore=operatore, ruolo=ruolo):
                success_count += 1

        return {
            "success": True,
            "data": {
                "aggiornate": success_count,
                "totale": len(request.ids)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch/risolvi")
async def risolvi_batch(
    request: BatchAnomalieRequest,
    current_user: UtenteResponse = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Risolvi più anomalie in una volta.

    v11.2: Se SUPERVISORE/ADMIN risolve anche le supervisioni collegate.
    """
    note = request.note or "Risoluzione batch"
    ruolo = current_user.ruolo if current_user.ruolo else 'operatore'
    operatore = current_user.username if current_user else 'system'

    try:
        success_count = 0
        for id_anomalia in request.ids:
            if update_anomalia_stato(id_anomalia, 'RISOLTA', note, operatore=operatore, ruolo=ruolo):
                success_count += 1

        return {
            "success": True,
            "data": {
                "aggiornate": success_count,
                "totale": len(request.ids)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch/ignora")
async def ignora_batch(
    request: BatchAnomalieRequest,
    current_user: UtenteResponse = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Ignora più anomalie in una volta.

    v11.2: Se SUPERVISORE/ADMIN risolve anche le supervisioni collegate.
    """
    note = request.note or "Ignorata"
    ruolo = current_user.ruolo if current_user.ruolo else 'operatore'
    operatore = current_user.username if current_user else 'system'

    try:
        success_count = 0
        for id_anomalia in request.ids:
            if update_anomalia_stato(id_anomalia, 'IGNORATA', note, operatore=operatore, ruolo=ruolo):
                success_count += 1

        return {
            "success": True,
            "data": {
                "aggiornate": success_count,
                "totale": len(request.ids)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# DETTAGLIO SINGOLA ANOMALIA (deve stare dopo le route specifiche)
# =============================================================================

class RigaUpdate(BaseModel):
    """Modello per aggiornamento riga parent."""
    q_venduta: Optional[int] = None
    descrizione: Optional[str] = None
    codice_originale: Optional[str] = None
    codice_aic: Optional[str] = None  # v8.2: Codice AIC corretto
    prezzo_netto: Optional[float] = None
    note_allestimento: Optional[str] = None


class CorrezioneAICRequest(BaseModel):
    """Richiesta correzione codice AIC con propagazione."""
    codice_aic: str  # Codice AIC corretto (9 cifre)
    livello_propagazione: str = 'ORDINE'  # ORDINE (default), GLOBALE (solo supervisore+)
    operatore: str  # Username operatore
    note: Optional[str] = None


class CorrezioneDepositoRequest(BaseModel):
    """Richiesta assegnazione manuale deposito per LKP-A05."""
    deposito_riferimento: str  # Codice deposito da anagrafica_clienti.riferimento
    id_cliente: Optional[int] = None  # ID cliente selezionato (opzionale)
    operatore: str  # Username operatore
    note: Optional[str] = None


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
        # v11.0: Aggiunto descrizione_prodotto da ordini_dettaglio
        anomalia = db.execute("""
            SELECT
                an.*,
                v.codice_vendor AS vendor,
                ot.numero_ordine_vendor AS numero_ordine,
                ot.ragione_sociale_1 AS ragione_sociale,
                ot.data_ordine,
                a.nome_file_originale AS pdf_file,
                od.descrizione AS descrizione_prodotto
            FROM anomalie an
            LEFT JOIN ordini_testata ot ON an.id_testata = ot.id_testata
            LEFT JOIN vendor v ON ot.id_vendor = v.id_vendor
            LEFT JOIN acquisizioni a ON COALESCE(an.id_acquisizione, ot.id_acquisizione) = a.id_acquisizione
            LEFT JOIN ordini_dettaglio od ON an.id_dettaglio = od.id_dettaglio
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

        # FALLBACK: Se righe_child è vuoto ma riga_parent ha espositore_metadata,
        # estrai child_dettaglio dal JSON (per vendor che non creano id_parent_espositore)
        if riga_parent and not righe_child and riga_parent.get('espositore_metadata'):
            try:
                import json
                esp_meta = riga_parent['espositore_metadata']
                # PostgreSQL JSONB restituisce già dict, TEXT restituisce stringa
                if isinstance(esp_meta, str):
                    metadata = json.loads(esp_meta)
                else:
                    metadata = esp_meta  # Già dict

                child_dettaglio = metadata.get('child_dettaglio', [])
                if child_dettaglio:
                    # Converti child_dettaglio in formato compatibile con righe_child
                    righe_child = [
                        {
                            'id_dettaglio': None,  # Non esiste nel DB come riga separata
                            'n_riga': idx + 1,
                            'codice_originale': c.get('codice', ''),
                            'codice_aic': c.get('aic', ''),
                            'descrizione': c.get('descrizione', ''),
                            'q_venduta': c.get('quantita', 0),
                            'prezzo_netto': c.get('prezzo_netto', 0),
                            'prezzo_pubblico': c.get('prezzo_netto', 0),
                            'valore_netto': c.get('valore_netto', 0),
                            'from_metadata': True  # Flag per indicare origine
                        }
                        for idx, c in enumerate(child_dettaglio)
                    ]
            except (json.JSONDecodeError, TypeError, KeyError):
                pass  # Ignora errori parsing

        # Per anomalie LOOKUP, includi dati ordine per ricerca manuale
        ordine_data = None
        tipo_anomalia = anomalia_dict.get('tipo_anomalia') or ''
        codice_anomalia = anomalia_dict.get('codice_anomalia') or ''

        if tipo_anomalia in ('LOOKUP', 'DEPOSITO') or (codice_anomalia and (codice_anomalia.startswith('LKP-') or codice_anomalia.startswith('DEP-'))):
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
                        lookup_score,
                        deposito_riferimento
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

        # v8.2: Supporto codice_aic con validazione
        if update.codice_aic is not None:
            valido, result = valida_codice_aic(update.codice_aic)
            if not valido:
                raise HTTPException(status_code=400, detail=result)
            updates.append("codice_aic = ?")
            params.append(result)

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
    note: Optional[str] = "Risolta da dettaglio",
    current_user: UtenteResponse = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Risolve un'anomalia singola (senza propagazione).

    v11.2: Se SUPERVISORE/ADMIN risolve anche le supervisioni collegate.
    NOTA: Per risolvere con propagazione, usare /dettaglio/{id}/risolvi-propaga
    """
    ruolo = current_user.ruolo if current_user.ruolo else 'operatore'
    operatore = current_user.username if current_user else 'system'

    try:
        success = update_anomalia_stato(id_anomalia, 'RISOLTA', note, operatore=operatore, ruolo=ruolo)

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


# =============================================================================
# RISOLUZIONE CON PROPAGAZIONE (v10.5)
# =============================================================================

@router.get("/dettaglio/{id_anomalia}/conta-identiche", summary="Conta anomalie identiche")
async def conta_anomalie_identiche_endpoint(id_anomalia: int) -> Dict[str, Any]:
    """
    Conta quante anomalie identiche esistono per ogni livello di propagazione.

    Utile per mostrare nel frontend quante anomalie verrebbero risolte.

    Returns:
        {
            "ordine": N,
            "globale": M
        }
    """
    try:
        conteggi = conta_anomalie_identiche(id_anomalia)
        return {
            "success": True,
            "data": conteggi
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dettaglio/{id_anomalia}/livelli-permessi", summary="Livelli propagazione permessi")
async def get_livelli_permessi(
    id_anomalia: int,
    ruolo: str = Query("operatore", description="Ruolo utente")
) -> Dict[str, Any]:
    """
    Ritorna i livelli di propagazione permessi per il ruolo specificato.

    - **Operatore**: Solo ORDINE (stesso ordine, stesso vendor)
    - **Supervisore/Admin**: ORDINE, GLOBALE (stesso vendor)

    Utile per configurare il dropdown nel frontend.
    """
    try:
        livelli = get_livello_permesso(ruolo)
        conteggi = conta_anomalie_identiche(id_anomalia)

        return {
            "success": True,
            "data": {
                "livelli_permessi": livelli,
                "conteggi": conteggi,
                "ruolo": ruolo
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dettaglio/{id_anomalia}/risolvi-propaga", summary="Risolvi con propagazione")
async def risolvi_anomalia_con_propagazione_endpoint(
    id_anomalia: int,
    request: RisoluzionePropagazioneRequest
) -> Dict[str, Any]:
    """
    Risolve un'anomalia con propagazione gerarchica (v10.6).

    ## Livelli di propagazione:

    - **ORDINE**: Tutte le anomalie identiche dello stesso ordine (default)
    - **GLOBALE**: Tutte le anomalie identiche stesso vendor (solo Supervisore+)

    ## Vincoli ruolo:

    - **Operatore**: Solo livello ORDINE (stesso ordine, stesso vendor)
    - **Supervisore/Admin**: Tutti i livelli disponibili incluso GLOBALE

    ## Effetti:

    1. Risolve tutte le anomalie secondo il livello di propagazione
    2. Approva le supervisioni collegate
    3. Incrementa il contatore ML per OGNI anomalia risolta
    4. Sblocca gli ordini quando tutte le anomalie sono risolte

    ## Esempio:

    ```json
    {
        "livello_propagazione": "GLOBALE",
        "operatore": "mario.rossi",
        "ruolo": "supervisore",
        "note": "Verificato su listino ufficiale"
    }
    ```

    **ML Pattern:** Se risolvi 3 anomalie identiche con GLOBALE,
    il contatore ML viene incrementato di 3 (non di 1).
    """
    # Valida livello propagazione
    try:
        livello = LivelloPropagazione(request.livello_propagazione.upper())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Livello propagazione non valido. Valori: ORDINE, GLOBALE"
        )

    try:
        result = risolvi_anomalia_con_propagazione(
            id_anomalia=id_anomalia,
            livello=livello,
            operatore=request.operatore,
            ruolo=request.ruolo,
            note=request.note
        )

        if not result.get('success'):
            raise HTTPException(
                status_code=400,
                detail=result.get('error', 'Errore durante risoluzione')
            )

        return {
            "success": True,
            "message": f"Risolte {result['anomalie_risolte']} anomalie ({livello.value})",
            "data": {
                "anomalie_risolte": result['anomalie_risolte'],
                "ordini_coinvolti": result['ordini_coinvolti'],
                "supervisioni_approvate": result.get('supervisioni_approvate', 0),
                "ml_pattern_incrementato": result['ml_pattern_incrementato'],
                "livello_propagazione": result['livello']
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# CORREZIONE AIC CON PROPAGAZIONE (v8.2)
# =============================================================================

@router.post("/dettaglio/{id_anomalia}/correggi-aic", summary="Correggi AIC con propagazione")
async def correggi_aic_anomalia(
    id_anomalia: int,
    request: CorrezioneAICRequest,
    current_user: UtenteResponse = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Corregge il codice AIC di un'anomalia con propagazione gerarchica (v10.6).

    **IMPORTANTE:** Questo endpoint risolve l'anomalia E propaga il codice AIC
    secondo il livello specificato.

    ## Livelli di propagazione (basati sul ruolo):

    - **ORDINE**: Tutte le righe dello stesso ordine con descrizione simile (default, tutti i ruoli)
    - **GLOBALE**: Tutte le anomalie aperte stesso vendor con stessa descrizione (solo supervisore+)

    ## Restrizioni per ruolo:

    - **Operatore**: Solo ORDINE (stesso ordine)
    - **Supervisore/Admin/Superuser**: Tutti i livelli incluso GLOBALE

    ## Effetti:

    1. Aggiorna `codice_aic` in ORDINI_DETTAGLIO (solo righe con anomalie aperte)
    2. Marca anomalia come RISOLTA
    3. Se GLOBALE: chiude anche altre anomalie AIC stesso vendor con stessa descrizione
    4. Aggiorna supervisioni AIC collegate
    5. Aggiorna pattern ML per apprendimento automatico

    Args:
        id_anomalia: ID dell'anomalia AIC da correggere
        request: Dati correzione con codice AIC e livello propagazione

    Returns:
        Risultato con numero righe aggiornate e ordini coinvolti
    """
    # Valida livello propagazione
    try:
        livello = LivelloPropagazioneAIC(request.livello_propagazione.upper())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Livello propagazione non valido. Valori: ORDINE, GLOBALE"
        )

    # v10.6: Controllo ruoli per livello propagazione
    # Operatore: solo ORDINE (stesso ordine)
    # Supervisore+: tutti i livelli incluso GLOBALE
    ruolo = current_user.ruolo.upper() if current_user.ruolo else 'OPERATORE'
    ruoli_superiori = ['SUPERVISORE', 'ADMIN', 'SUPERUSER']

    if livello == LivelloPropagazioneAIC.GLOBALE and ruolo not in ruoli_superiori:
        raise HTTPException(
            status_code=403,
            detail="Propagazione GLOBALE riservata a supervisori e ruoli superiori"
        )

    try:
        result = risolvi_anomalia_aic(
            id_anomalia=id_anomalia,
            codice_aic=request.codice_aic,
            livello=livello,
            operatore=request.operatore,
            note=request.note
        )

        if not result.get('success'):
            raise HTTPException(
                status_code=400,
                detail=result.get('error', 'Errore durante correzione AIC')
            )

        return {
            "success": True,
            "message": f"AIC {result['codice_aic']} applicato ({livello.value})",
            "data": {
                "codice_aic": result['codice_aic'],
                "livello_propagazione": result['livello'],
                "righe_aggiornate": result['righe_aggiornate'],
                "ordini_coinvolti": result['ordini_coinvolti'],
                "anomalia_risolta": result.get('anomalia_risolta', True)
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/aic/contatori", summary="Contatori anomalie AIC")
async def get_contatori_aic() -> Dict[str, Any]:
    """
    Ritorna contatori anomalie AIC per dashboard supervisione.

    Utile per aggiornare i badge nella sezione ML/Supervisione.
    """
    # v11.4: Usa modulo AIC rifattorizzato
    from ..services.supervision.aic import (
        conta_anomalie_aic_aperte,
        conta_supervisioni_aic_pending
    )

    return {
        "success": True,
        "data": {
            "anomalie_aperte": conta_anomalie_aic_aperte(),
            "supervisioni_pending": conta_supervisioni_aic_pending()
        }
    }


# =============================================================================
# RISOLUZIONE LKP-A05/DEP-A01: ASSEGNAZIONE MANUALE DEPOSITO (v11.3)
# =============================================================================

@router.post("/dettaglio/{id_anomalia}/risolvi-deposito", summary="Risolvi anomalie deposito (LKP-A05, DEP-A01)")
async def risolvi_anomalia_deposito(
    id_anomalia: int,
    request: CorrezioneDepositoRequest
) -> Dict[str, Any]:
    """
    Risolve anomalie relative al deposito assegnando manualmente il deposito di riferimento.

    v11.3: Supporta sia LKP-A05 (cliente non in anagrafica) che DEP-A01 (deposito mancante).

    ## Quando usare

    - **LKP-A05**: P.IVA cliente non presente in `anagrafica_clienti`
    - **DEP-A01**: Cliente in anagrafica ma senza deposito_riferimento assegnato

    L'operatore può:
    1. Selezionare un cliente esistente dal dropdown (opzionale)
    2. Assegnare manualmente il codice deposito (qualsiasi codice valido)

    **Nota:** Solo i depositi CT e CL sono abilitati per la generazione tracciati.

    ## Effetti

    1. Aggiorna `deposito_riferimento` su ordini_testata
    2. Aggiorna `id_cliente_manuale` se fornito
    3. Marca anomalia come RISOLTA
    4. Sblocca ordine se era bloccato da questa anomalia

    ## Esempio

    ```json
    {
        "deposito_riferimento": "CT",
        "id_cliente": 123,
        "operatore": "mario.rossi",
        "note": "Deposito assegnato manualmente"
    }
    ```

    **Depositi abilitati per tracciati:** CT, CL
    """
    from ..database_pg import get_db

    if not request.deposito_riferimento or not request.deposito_riferimento.strip():
        raise HTTPException(status_code=400, detail="Codice deposito obbligatorio")

    # v11.3: Normalizza deposito in uppercase
    deposito_input = request.deposito_riferimento.strip().upper()

    db = get_db()

    # Auto-migrazione: crea colonne se non esistono (una alla volta per PostgreSQL)
    for col_def in [
        "ALTER TABLE ordini_testata ADD COLUMN IF NOT EXISTS deposito_riferimento VARCHAR(10)",
        "ALTER TABLE ordini_testata ADD COLUMN IF NOT EXISTS id_cliente_manuale INTEGER",
        "ALTER TABLE ordini_testata ADD COLUMN IF NOT EXISTS note_cliente_manuale TEXT"
    ]:
        try:
            db.execute(col_def)
            db.commit()
        except Exception:
            db.rollback()  # Rollback se errore, poi continua

    try:
        # 1. Recupera anomalia
        anomalia = db.execute("""
            SELECT a.*, a.id_testata as id_testata_anomalia
            FROM anomalie a
            WHERE a.id_anomalia = %s
        """, (id_anomalia,)).fetchone()

        if not anomalia:
            raise HTTPException(status_code=404, detail=f"Anomalia {id_anomalia} non trovata")

        # v11.0: Permetti risoluzione deposito anche per anomalie senza codice specifico
        # ma con tipo LOOKUP o descrizione che indica problema deposito
        codice_anomalia = anomalia['codice_anomalia'] or ''
        tipo_anomalia = anomalia.get('tipo_anomalia', '') or ''
        descrizione = anomalia.get('descrizione', '') or ''

        # v11.3: Accetta LKP-A05, DEP-A01, anomalie LOOKUP/DEPOSITO, o anomalie con "deposito" nella descrizione
        is_deposito_anomaly = (
            codice_anomalia == 'LKP-A05' or
            codice_anomalia == 'DEP-A01' or
            codice_anomalia.startswith('LKP-') or
            codice_anomalia.startswith('DEP-') or
            tipo_anomalia == 'LOOKUP' or
            tipo_anomalia == 'DEPOSITO' or
            'deposito' in descrizione.lower() or
            'cliente' in descrizione.lower()
        )

        if not is_deposito_anomaly:
            raise HTTPException(
                status_code=400,
                detail=f"Questo endpoint è per anomalie LOOKUP/deposito. Anomalia trovata: {codice_anomalia or tipo_anomalia or 'N/D'}"
            )

        id_testata = anomalia.get('id_testata') or anomalia.get('id_testata_anomalia')
        if not id_testata:
            raise HTTPException(status_code=400, detail="Anomalia non collegata a un ordine")

        # 2. Aggiorna ordini_testata con deposito manuale (v11.3: usa valore normalizzato)
        db.execute("""
            UPDATE ordini_testata
            SET deposito_riferimento = %s,
                id_cliente_manuale = %s,
                note_cliente_manuale = %s
            WHERE id_testata = %s
        """, (
            deposito_input,  # v11.3: uppercase, validato CT/CL
            request.id_cliente,
            request.note,
            id_testata
        ))

        # 3. Marca anomalia come RISOLTA
        db.execute("""
            UPDATE anomalie
            SET stato = 'RISOLTA',
                note_risoluzione = %s,
                data_risoluzione = NOW()
            WHERE id_anomalia = %s
        """, (
            f"Deposito {request.deposito_riferimento} assegnato manualmente da {request.operatore}. {request.note or ''}",
            id_anomalia
        ))

        # 4. Approva eventuali supervisioni lookup collegate
        db.execute("""
            UPDATE supervisione_lookup
            SET stato = 'APPROVED',
                operatore = %s,
                timestamp_decisione = NOW(),
                note = %s
            WHERE id_anomalia = %s AND stato = 'PENDING'
        """, (
            request.operatore,
            f"Deposito manuale: {request.deposito_riferimento}",
            id_anomalia
        ))

        # 5. Sblocca ordine se non ci sono altre anomalie bloccanti
        anomalie_aperte = db.execute("""
            SELECT COUNT(*) FROM anomalie
            WHERE id_testata = %s
              AND stato = 'APERTA'
              AND livello IN ('ERRORE', 'CRITICO')
        """, (id_testata,)).fetchone()[0]

        if anomalie_aperte == 0:
            # v11.4: Verifica supervisioni pending su TUTTE le tabelle
            sup_pending = db.execute("""
                SELECT COUNT(*) FROM (
                    SELECT id_supervisione FROM supervisione_espositore WHERE id_testata = %s AND stato = 'PENDING'
                    UNION ALL
                    SELECT id_supervisione FROM supervisione_listino WHERE id_testata = %s AND stato = 'PENDING'
                    UNION ALL
                    SELECT id_supervisione FROM supervisione_lookup WHERE id_testata = %s AND stato = 'PENDING'
                    UNION ALL
                    SELECT id_supervisione FROM supervisione_aic WHERE id_testata = %s AND stato = 'PENDING'
                    UNION ALL
                    SELECT id_supervisione FROM supervisione_prezzo WHERE id_testata = %s AND stato = 'PENDING'
                ) sub
            """, (id_testata, id_testata, id_testata, id_testata, id_testata)).fetchone()[0]

            if sup_pending == 0:
                db.execute("""
                    UPDATE ordini_testata
                    SET stato = 'ESTRATTO'
                    WHERE id_testata = %s AND stato IN ('ANOMALIA', 'PENDING_REVIEW')
                """, (id_testata,))

        db.commit()

        return {
            "success": True,
            "message": f"Deposito {request.deposito_riferimento} assegnato all'ordine",
            "data": {
                "id_anomalia": id_anomalia,
                "id_testata": id_testata,
                "deposito_riferimento": request.deposito_riferimento,
                "anomalia_risolta": True,
                "ordine_sbloccato": anomalie_aperte == 0
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"ERRORE risolvi-deposito: {e}")
        print(traceback.format_exc())
        db.rollback()
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {str(e)}")
