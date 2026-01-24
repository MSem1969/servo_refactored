# =============================================================================
# SERV.O v8.2 - SUPERVISIONE AIC
# =============================================================================
# Endpoint per gestione supervisione codice AIC (AIC-A01)
# Include correzione errori AIC
# =============================================================================

from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ...database_pg import get_db
from ...services.supervision.aic import (
    approva_supervisione_aic,
    rifiuta_supervisione_aic,
    search_aic_suggestions,
)
from ...services.supervision.propagazione_aic import (
    correggi_aic_errato,
    get_storico_modifiche_aic,
)


router = APIRouter(prefix="/aic", tags=["Supervisione AIC"])


# =============================================================================
# SCHEMAS
# =============================================================================

class RisoluzioneAICRequest(BaseModel):
    """Richiesta risoluzione supervisione AIC."""
    operatore: str
    codice_aic: str  # AIC assegnato (9 cifre)
    livello_propagazione: str = 'GLOBALE'  # ORDINE, GLOBALE (default GLOBALE per supervisori)
    note: Optional[str] = None


class RifiutoAICRequest(BaseModel):
    """Richiesta rifiuto supervisione AIC."""
    operatore: str
    note: str  # Obbligatorio per rifiuto


# =============================================================================
# ENDPOINT SUPERVISIONE AIC
# =============================================================================

@router.get("/pending", summary="Lista supervisioni AIC pending")
async def get_aic_pending():
    """
    Ritorna lista supervisioni AIC in attesa.

    Le supervisioni AIC riguardano prodotti senza codice AIC valido (AIC-A01).
    """
    db = get_db()

    rows = db.execute("""
        SELECT sa.*,
               ot.numero_ordine_vendor,
               ot.ragione_sociale_1,
               ot.data_ordine
        FROM supervisione_aic sa
        JOIN ordini_testata ot ON sa.id_testata = ot.id_testata
        WHERE sa.stato = 'PENDING'
        ORDER BY sa.timestamp_creazione DESC
    """).fetchall()

    return {
        "count": len(rows),
        "tipo": "aic",
        "supervisioni": [dict(r) for r in rows]
    }


@router.get("/{id_supervisione}", summary="Dettaglio supervisione AIC")
async def get_supervisione_aic_detail(id_supervisione: int):
    """
    Ritorna dettagli supervisione AIC con suggerimenti.

    Include:
    - Dati ordine e riga
    - Descrizione prodotto originale
    - Suggerimenti AIC da listino vendor
    - Storico pattern (se già approvati per descrizione simile)
    """
    db = get_db()

    # Recupera supervisione
    sup = db.execute("""
        SELECT sa.*,
               ot.numero_ordine_vendor,
               ot.ragione_sociale_1,
               ot.data_ordine,
               ot.min_id,
               od.descrizione as descrizione_dettaglio,
               od.q_venduta,
               od.prezzo_netto
        FROM supervisione_aic sa
        JOIN ordini_testata ot ON sa.id_testata = ot.id_testata
        LEFT JOIN ordini_dettaglio od ON sa.id_dettaglio = od.id_dettaglio
        WHERE sa.id_supervisione = %s
    """, (id_supervisione,)).fetchone()

    if not sup:
        raise HTTPException(status_code=404, detail="Supervisione AIC non trovata")

    result = dict(sup)

    # Cerca suggerimenti AIC
    descrizione = result.get('descrizione_prodotto') or result.get('descrizione_normalizzata') or ''
    if descrizione:
        suggerimenti = search_aic_suggestions(descrizione, result.get('vendor', ''))
        result['suggerimenti_aic'] = suggerimenti

    # Cerca pattern approvati simili
    pattern = result.get('pattern_signature')
    if pattern:
        criterio = db.execute("""
            SELECT count_approvazioni, is_ordinario, codice_aic_default
            FROM criteri_ordinari_aic
            WHERE pattern_signature = %s
        """, (pattern,)).fetchone()

        if criterio:
            result['pattern_info'] = dict(criterio)

    return result


@router.post("/{id_supervisione}/risolvi", summary="Risolvi supervisione AIC")
async def risolvi_aic(id_supervisione: int, req: RisoluzioneAICRequest):
    """
    Risolvi supervisione AIC assegnando il codice AIC.

    Effetti:
    1. Assegna codice AIC alla riga ordine
    2. Propaga AIC a TUTTE le righe con stesso (vendor, descrizione_normalizzata)
    3. Aggiorna pattern ML (incrementa contatore, può diventare ordinario)
    4. Supervisione → APPROVED
    5. Anomalia → RISOLTA
    6. Sblocca ordine se non ha altre supervisioni pending

    Args:
        id_supervisione: ID supervisione
        req: Richiesta con operatore, codice_aic e note opzionali

    Returns:
        Risultato con numero righe propagate
    """
    # Valida formato AIC
    if not req.codice_aic or len(req.codice_aic) != 9 or not req.codice_aic.isdigit():
        raise HTTPException(
            status_code=400,
            detail="Codice AIC non valido. Deve essere composto da 9 cifre."
        )

    try:
        result = approva_supervisione_aic(
            id_supervisione=id_supervisione,
            operatore=req.operatore,
            codice_aic=req.codice_aic,
            livello_propagazione=req.livello_propagazione,
            note=req.note
        )

        if not result.get('success'):
            raise HTTPException(
                status_code=400,
                detail=result.get('error', 'Errore durante approvazione')
            )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{id_supervisione}/rifiuta", summary="Rifiuta supervisione AIC")
async def rifiuta_aic(id_supervisione: int, req: RifiutoAICRequest):
    """
    Rifiuta supervisione AIC.

    Effetti:
    - Supervisione → REJECTED
    - Pattern ML → Reset contatore (apprendimento ripartirà da zero)
    - Ordine rimane bloccato

    Args:
        id_supervisione: ID supervisione
        req: Richiesta con operatore e note (obbligatorie)
    """
    if not req.note or len(req.note) < 5:
        raise HTTPException(
            status_code=400,
            detail="Note obbligatorie per rifiuto (minimo 5 caratteri)"
        )

    try:
        result = rifiuta_supervisione_aic(
            id_supervisione=id_supervisione,
            operatore=req.operatore,
            note=req.note
        )

        if not result.get('success'):
            raise HTTPException(
                status_code=400,
                detail=result.get('error', 'Errore durante rifiuto')
            )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search-aic", summary="Cerca suggerimenti AIC")
async def search_aic(
    descrizione: str = Query(..., min_length=3),
    vendor: Optional[str] = None
):
    """
    Cerca codici AIC suggeriti per una descrizione prodotto.

    Fonti di ricerca:
    1. Listino vendor (listini_vendor)
    2. Ordini precedenti (ordini_dettaglio)
    3. Pattern ML approvati (criteri_ordinari_aic)

    Args:
        descrizione: Testo descrizione prodotto (min 3 caratteri)
        vendor: Filtro opzionale per vendor

    Returns:
        Lista suggerimenti ordinati per rilevanza
    """
    suggerimenti = search_aic_suggestions(descrizione, vendor)

    return {
        "query": descrizione,
        "vendor": vendor,
        "count": len(suggerimenti),
        "suggerimenti": suggerimenti
    }


class BulkAICRequest(BaseModel):
    """Richiesta approvazione bulk pattern AIC."""
    operatore: str
    codice_aic: str  # AIC da assegnare a tutte le supervisioni del pattern
    note: Optional[str] = None


@router.post("/pattern/{pattern_signature}/approva-bulk", summary="Approva bulk pattern AIC")
async def approva_pattern_aic_bulk(pattern_signature: str, req: BulkAICRequest):
    """
    Approva TUTTE le supervisioni AIC pending con un dato pattern,
    assegnando lo stesso codice AIC a tutte.

    Effetti:
    1. Assegna codice AIC a tutte le righe delle supervisioni
    2. Propaga AIC a righe simili (vendor + descrizione)
    3. Approva tutte le supervisioni del pattern → APPROVED
    4. Incrementa pattern ML (può diventare ordinario)
    5. Chiude anomalie correlate
    6. Sblocca ordini coinvolti

    Args:
        pattern_signature: Signature del pattern da approvare
        req: Richiesta con operatore, codice_aic e note opzionali

    Returns:
        Risultato con conteggio supervisioni e ordini gestiti
    """
    # Valida formato AIC
    if not req.codice_aic or len(req.codice_aic) != 9 or not req.codice_aic.isdigit():
        raise HTTPException(
            status_code=400,
            detail="Codice AIC non valido. Deve essere composto da 9 cifre."
        )

    from ...services.supervision.aic import approva_supervisione_aic, _registra_approvazione_pattern_aic
    from ...services.supervision.requests import sblocca_ordine_se_completo

    db = get_db()

    # Trova tutte le supervisioni pending con questo pattern
    rows = db.execute("""
        SELECT id_supervisione, id_testata, id_dettaglio
        FROM supervisione_aic
        WHERE pattern_signature = %s AND stato = 'PENDING'
    """, (pattern_signature,)).fetchall()

    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"Nessuna supervisione AIC pending trovata per pattern {pattern_signature}"
        )

    supervisioni_approvate = 0
    ordini_coinvolti = set()
    righe_aggiornate = 0

    # Approva ogni supervisione
    for row in rows:
        try:
            # Aggiorna supervisione
            db.execute("""
                UPDATE supervisione_aic
                SET stato = 'APPROVED',
                    operatore = %s,
                    timestamp_decisione = CURRENT_TIMESTAMP,
                    codice_aic_assegnato = %s,
                    note = %s
                WHERE id_supervisione = %s
            """, (req.operatore, req.codice_aic, f"[BULK] {req.note or ''}", row['id_supervisione']))

            # Aggiorna riga ordine
            if row['id_dettaglio']:
                db.execute("""
                    UPDATE ordini_dettaglio
                    SET codice_aic = %s
                    WHERE id_dettaglio = %s
                """, (req.codice_aic, row['id_dettaglio']))
                righe_aggiornate += 1

            supervisioni_approvate += 1
            ordini_coinvolti.add(row['id_testata'])

            # Chiudi anomalie correlate
            db.execute("""
                UPDATE anomalie
                SET stato = 'RISOLTA',
                    data_risoluzione = CURRENT_TIMESTAMP,
                    note_risoluzione = %s
                WHERE id_testata = %s
                  AND codice_anomalia = 'AIC-A01'
                  AND stato = 'APERTA'
            """, (f"AIC assegnato: {req.codice_aic} [BULK]", row['id_testata']))

        except Exception as e:
            print(f"Errore approvazione supervisione {row['id_supervisione']}: {e}")

    db.commit()

    # Incrementa pattern ML UNA SOLA VOLTA (non per ogni supervisione)
    _registra_approvazione_pattern_aic(pattern_signature, req.operatore, req.codice_aic)
    db.commit()

    # Sblocca ordini
    for id_testata in ordini_coinvolti:
        sblocca_ordine_se_completo(id_testata)

    return {
        "success": True,
        "pattern_signature": pattern_signature,
        "codice_aic": req.codice_aic,
        "supervisioni_approvate": supervisioni_approvate,
        "righe_aggiornate": righe_aggiornate,
        "ordini_coinvolti": list(ordini_coinvolti)
    }


@router.get("/stats", summary="Statistiche supervisione AIC")
async def get_aic_stats():
    """
    Ritorna statistiche supervisione AIC.

    Include:
    - Totale supervisioni per stato
    - Pattern ordinari
    - Righe propagate totali
    """
    db = get_db()

    stats = {
        "pending": 0,
        "approved": 0,
        "rejected": 0,
        "pattern_ordinari": 0,
        "totale_approvazioni": 0
    }

    # Conteggi supervisioni
    row = db.execute("""
        SELECT
            COUNT(*) FILTER (WHERE stato = 'PENDING') as pending,
            COUNT(*) FILTER (WHERE stato = 'APPROVED') as approved,
            COUNT(*) FILTER (WHERE stato = 'REJECTED') as rejected
        FROM supervisione_aic
    """).fetchone()

    if row:
        stats['pending'] = row['pending'] or 0
        stats['approved'] = row['approved'] or 0
        stats['rejected'] = row['rejected'] or 0

    # Conteggi pattern
    row = db.execute("""
        SELECT
            COUNT(*) FILTER (WHERE is_ordinario = TRUE) as ordinari,
            SUM(count_approvazioni) as totale_approvazioni
        FROM criteri_ordinari_aic
    """).fetchone()

    if row:
        stats['pattern_ordinari'] = row['ordinari'] or 0
        stats['totale_approvazioni'] = row['totale_approvazioni'] or 0

    return stats


# =============================================================================
# CORREZIONE ERRORI AIC (v8.2)
# =============================================================================

class CorreggiErroreAICRequest(BaseModel):
    """Richiesta correzione AIC errato."""
    aic_errato: str      # AIC da sostituire
    aic_corretto: str    # AIC corretto
    operatore: str
    note: Optional[str] = None


@router.post("/correggi-errore", summary="Correggi AIC errato")
async def correggi_errore_aic(req: CorreggiErroreAICRequest):
    """
    Corregge un codice AIC errato sostituendolo con quello corretto.

    Effetti:
    1. Trova TUTTE le righe ordine con l'AIC errato
    2. Sostituisce con l'AIC corretto
    3. Registra ogni modifica con audit trail (valore precedente)
    4. Permette rollback tramite storico

    Args:
        req: Richiesta con aic_errato, aic_corretto, operatore e note

    Returns:
        Risultato con numero righe corrette e dettagli
    """
    # Valida formato AIC errato
    if not req.aic_errato or len(req.aic_errato) != 9 or not req.aic_errato.isdigit():
        raise HTTPException(
            status_code=400,
            detail="AIC errato non valido. Deve essere composto da 9 cifre."
        )

    # Valida formato AIC corretto
    if not req.aic_corretto or len(req.aic_corretto) != 9 or not req.aic_corretto.isdigit():
        raise HTTPException(
            status_code=400,
            detail="AIC corretto non valido. Deve essere composto da 9 cifre."
        )

    # Non permette correzione con stesso valore
    if req.aic_errato == req.aic_corretto:
        raise HTTPException(
            status_code=400,
            detail="AIC errato e corretto non possono essere uguali."
        )

    try:
        result = correggi_aic_errato(
            aic_errato=req.aic_errato,
            aic_corretto=req.aic_corretto,
            operatore=req.operatore,
            note=req.note
        )

        if not result.get('success'):
            raise HTTPException(
                status_code=400,
                detail=result.get('error', 'Errore durante correzione')
            )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/storico-modifiche", summary="Storico modifiche AIC")
async def get_storico_aic(
    codice_aic: Optional[str] = Query(None, description="Filtro per AIC specifico"),
    limit: int = Query(50, ge=1, le=500, description="Numero massimo record")
):
    """
    Ritorna lo storico delle modifiche AIC effettuate.

    Utile per:
    - Verificare correzioni effettuate
    - Identificare pattern di errori
    - Eventuale rollback manuale

    Args:
        codice_aic: Filtro opzionale per AIC specifico
        limit: Numero massimo di record (default 50)

    Returns:
        Lista modifiche ordinate per data decrescente
    """
    storico = get_storico_modifiche_aic(codice_aic=codice_aic, limit=limit)

    return {
        "count": len(storico),
        "filtro_aic": codice_aic,
        "modifiche": storico
    }
