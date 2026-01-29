# =============================================================================
# SERV.O v11.4 - SUPERVISIONE ANAGRAFICA ROUTER
# =============================================================================
# Gestione supervisione per problemi anagrafica/header:
# - LKP-A01/A02/A03/A04/A05: Problemi lookup farmacia
# - DEP-A01: Deposito mancante
# - P.IVA, MIN_ID, Ragione Sociale mancanti/errati
# =============================================================================

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from datetime import datetime

from ...database_pg import get_db, log_operation

router = APIRouter(prefix="/anagrafica", tags=["Supervisione Anagrafica"])


# =============================================================================
# SCHEMAS
# =============================================================================

class CorrezioneAnagraficaRequest(BaseModel):
    """Request per correzione anagrafica da operatore."""
    piva: Optional[str] = None
    min_id: Optional[str] = None
    ragione_sociale: Optional[str] = None
    indirizzo: Optional[str] = None
    cap: Optional[str] = None
    citta: Optional[str] = None
    provincia: Optional[str] = None
    deposito: Optional[str] = None
    id_farmacia: Optional[int] = None
    note: Optional[str] = None
    operatore: str


class ApprovazioneAnagraficaRequest(BaseModel):
    """Request per approvazione/propagazione da supervisore."""
    # Campi correzione (supervisore può modificare)
    piva: Optional[str] = None
    min_id: Optional[str] = None
    ragione_sociale: Optional[str] = None
    indirizzo: Optional[str] = None
    cap: Optional[str] = None
    citta: Optional[str] = None
    provincia: Optional[str] = None
    deposito: Optional[str] = None
    id_farmacia: Optional[int] = None
    note: Optional[str] = None
    operatore: str
    # Propagazione
    livello_propagazione: str = "ORDINE"  # ORDINE o GLOBALE


# =============================================================================
# ENDPOINTS: LISTA E DETTAGLIO
# =============================================================================

@router.get("/pending", summary="Lista supervisioni anagrafica pending")
async def lista_pending(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0)
) -> Dict[str, Any]:
    """
    Ritorna lista supervisioni anagrafica in stato PENDING.
    Include info su correzione operatore se presente.
    """
    db = get_db()

    try:
        supervisioni = db.execute("""
            SELECT
                sa.*,
                ot.numero_ordine,
                ot.data_ordine,
                v.codice_vendor as vendor_codice,
                CASE WHEN sa.operatore_correzione IS NOT NULL THEN true ELSE false END as ha_correzione
            FROM supervisione_anagrafica sa
            JOIN ordini_testata ot ON sa.id_testata = ot.id_testata
            LEFT JOIN vendor v ON ot.id_vendor = v.id_vendor
            WHERE sa.stato = 'PENDING'
            ORDER BY sa.created_at DESC
            LIMIT %s OFFSET %s
        """, (limit, offset)).fetchall()

        total = db.execute(
            "SELECT COUNT(*) FROM supervisione_anagrafica WHERE stato = 'PENDING'"
        ).fetchone()[0]

        return {
            "success": True,
            "data": [dict(s) for s in supervisioni],
            "total": total,
            "limit": limit,
            "offset": offset
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/grouped", summary="Supervisioni anagrafica raggruppate per pattern")
async def lista_grouped() -> Dict[str, Any]:
    """
    Ritorna supervisioni raggruppate per pattern_signature.
    Utile per vista "Per Pattern" nella UI.
    """
    db = get_db()

    try:
        groups = db.execute("""
            SELECT
                sa.pattern_signature,
                sa.codice_anomalia,
                sa.vendor,
                MAX(sa.ragione_sociale_estratta) as ragione_sociale_sample,
                MAX(sa.piva_estratta) as piva_sample,
                COUNT(*) as total_count,
                COUNT(DISTINCT sa.id_testata) as ordini_count,
                ARRAY_AGG(DISTINCT sa.id_testata) as affected_order_ids,
                ARRAY_AGG(DISTINCT ot.numero_ordine) as affected_orders_preview,
                MAX(sa.operatore_correzione) as operatore_correzione,
                MAX(sa.data_correzione) as data_correzione,
                BOOL_OR(sa.operatore_correzione IS NOT NULL) as ha_correzione
            FROM supervisione_anagrafica sa
            JOIN ordini_testata ot ON sa.id_testata = ot.id_testata
            WHERE sa.stato = 'PENDING'
            GROUP BY sa.pattern_signature, sa.codice_anomalia, sa.vendor
            ORDER BY total_count DESC
        """).fetchall()

        return {
            "success": True,
            "data": [dict(g) for g in groups],
            "total_patterns": len(groups)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{id_supervisione}", summary="Dettaglio supervisione anagrafica")
async def get_dettaglio(id_supervisione: int) -> Dict[str, Any]:
    """
    Ritorna dettaglio completo di una supervisione anagrafica.
    Include dati ordine, correzione operatore, suggerimenti lookup.
    """
    db = get_db()

    try:
        sup = db.execute("""
            SELECT
                sa.*,
                ot.numero_ordine,
                ot.data_ordine,
                ot.partita_iva_estratta as piva_ordine,
                ot.min_id as min_id_ordine,
                ot.ragione_sociale_1 as ragione_sociale_ordine,
                ot.deposito_riferimento as deposito_ordine,
                ot.citta,
                ot.provincia,
                v.codice_vendor as vendor_codice,
                v.nome_vendor
            FROM supervisione_anagrafica sa
            JOIN ordini_testata ot ON sa.id_testata = ot.id_testata
            LEFT JOIN vendor v ON ot.id_vendor = v.id_vendor
            WHERE sa.id_supervisione = %s
        """, (id_supervisione,)).fetchone()

        if not sup:
            raise HTTPException(status_code=404, detail="Supervisione non trovata")

        # Cerca suggerimenti farmacia se abbiamo P.IVA o MIN_ID
        suggerimenti = []
        piva = sup.get('piva_estratta') or sup.get('piva_ordine')
        min_id = sup.get('min_id_estratto') or sup.get('min_id_ordine')

        if piva:
            farmacie = db.execute("""
                SELECT id_farmacia, min_id, partita_iva, ragione_sociale, citta, provincia
                FROM anagrafica_farmacie
                WHERE partita_iva = %s
                LIMIT 5
            """, (piva,)).fetchall()
            suggerimenti.extend([{**dict(f), 'match_type': 'PIVA'} for f in farmacie])

        if min_id and len(suggerimenti) < 5:
            farmacie = db.execute("""
                SELECT id_farmacia, min_id, partita_iva, ragione_sociale, citta, provincia
                FROM anagrafica_farmacie
                WHERE min_id = %s OR LTRIM(min_id, '0') = LTRIM(%s, '0')
                LIMIT 5
            """, (min_id, min_id)).fetchall()
            for f in farmacie:
                if not any(s['id_farmacia'] == f['id_farmacia'] for s in suggerimenti):
                    suggerimenti.append({**dict(f), 'match_type': 'MIN_ID'})

        return {
            "success": True,
            "data": dict(sup),
            "suggerimenti_farmacia": suggerimenti[:5]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# ENDPOINTS: CORREZIONE OPERATORE
# =============================================================================

@router.post("/{id_supervisione}/correzione", summary="Salva correzione operatore")
async def salva_correzione(
    id_supervisione: int,
    request: CorrezioneAnagraficaRequest
) -> Dict[str, Any]:
    """
    Salva correzione effettuata dall'operatore.
    NON approva la supervisione, la lascia in PENDING per revisione supervisore.

    Se l'operatore è supervisore e vuole approvare direttamente,
    deve usare l'endpoint /approva.
    """
    db = get_db()

    try:
        # Verifica esistenza
        sup = db.execute(
            "SELECT * FROM supervisione_anagrafica WHERE id_supervisione = %s",
            (id_supervisione,)
        ).fetchone()

        if not sup:
            raise HTTPException(status_code=404, detail="Supervisione non trovata")

        if sup['stato'] != 'PENDING':
            raise HTTPException(status_code=400, detail=f"Supervisione in stato {sup['stato']}, non modificabile")

        # Salva correzione
        db.execute("""
            UPDATE supervisione_anagrafica SET
                piva_corretta = COALESCE(%s, piva_corretta),
                min_id_corretto = COALESCE(%s, min_id_corretto),
                ragione_sociale_corretta = COALESCE(%s, ragione_sociale_corretta),
                indirizzo_corretto = COALESCE(%s, indirizzo_corretto),
                cap_corretto = COALESCE(%s, cap_corretto),
                citta_corretta = COALESCE(%s, citta_corretta),
                provincia_corretta = COALESCE(%s, provincia_corretta),
                deposito_corretto = COALESCE(%s, deposito_corretto),
                id_farmacia_assegnata = COALESCE(%s, id_farmacia_assegnata),
                operatore_correzione = %s,
                data_correzione = CURRENT_TIMESTAMP,
                note_correzione = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id_supervisione = %s
        """, (
            request.piva,
            request.min_id,
            request.ragione_sociale,
            request.indirizzo,
            request.cap,
            request.citta,
            request.provincia,
            request.deposito,
            request.id_farmacia,
            request.operatore,
            request.note,
            id_supervisione
        ))

        # Aggiorna anche l'ordine con i valori corretti
        _applica_correzione_ordine(db, sup['id_testata'], request)

        log_operation(
            'CORREZIONE_ANAGRAFICA',
            'SUPERVISIONE_ANAGRAFICA',
            id_supervisione,
            f"Correzione salvata da {request.operatore}",
            operatore=request.operatore
        )

        db.commit()

        return {
            "success": True,
            "message": "Correzione salvata. In attesa di approvazione supervisore.",
            "data": {
                "id_supervisione": id_supervisione,
                "operatore_correzione": request.operatore,
                "stato": "PENDING"
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# ENDPOINTS: APPROVAZIONE SUPERVISORE
# =============================================================================

@router.post("/{id_supervisione}/approva", summary="Approva e propaga correzione")
async def approva_supervisione(
    id_supervisione: int,
    request: ApprovazioneAnagraficaRequest
) -> Dict[str, Any]:
    """
    Approva supervisione (supervisore).

    Se livello_propagazione = GLOBALE, applica la correzione a tutti
    gli ordini con lo stesso pattern.

    Il supervisore può modificare i valori prima di approvare.
    """
    db = get_db()

    try:
        # Verifica esistenza
        sup = db.execute(
            "SELECT * FROM supervisione_anagrafica WHERE id_supervisione = %s",
            (id_supervisione,)
        ).fetchone()

        if not sup:
            raise HTTPException(status_code=404, detail="Supervisione non trovata")

        if sup['stato'] != 'PENDING':
            raise HTTPException(status_code=400, detail=f"Supervisione già in stato {sup['stato']}")

        # Determina valori finali (supervisore può sovrascrivere)
        valori_finali = {
            'piva': request.piva or sup.get('piva_corretta') or sup.get('piva_estratta'),
            'min_id': request.min_id or sup.get('min_id_corretto') or sup.get('min_id_estratto'),
            'ragione_sociale': request.ragione_sociale or sup.get('ragione_sociale_corretta') or sup.get('ragione_sociale_estratta'),
            'indirizzo': request.indirizzo or sup.get('indirizzo_corretto'),
            'cap': request.cap or sup.get('cap_corretto'),
            'citta': request.citta or sup.get('citta_corretta'),
            'provincia': request.provincia or sup.get('provincia_corretta'),
            'deposito': request.deposito or sup.get('deposito_corretto'),
            'id_farmacia': request.id_farmacia or sup.get('id_farmacia_assegnata'),
        }

        ordini_aggiornati = 0
        supervisioni_approvate = 0

        if request.livello_propagazione == 'GLOBALE' and sup.get('pattern_signature'):
            # Propaga a tutti gli ordini con stesso pattern
            pattern_sups = db.execute("""
                SELECT id_supervisione, id_testata
                FROM supervisione_anagrafica
                WHERE pattern_signature = %s AND stato = 'PENDING'
            """, (sup['pattern_signature'],)).fetchall()

            for ps in pattern_sups:
                # Aggiorna supervisione
                db.execute("""
                    UPDATE supervisione_anagrafica SET
                        piva_corretta = %s,
                        min_id_corretto = %s,
                        ragione_sociale_corretta = %s,
                        deposito_corretto = %s,
                        id_farmacia_assegnata = %s,
                        stato = 'APPROVED',
                        operatore_approvazione = %s,
                        data_approvazione = CURRENT_TIMESTAMP,
                        note_approvazione = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id_supervisione = %s
                """, (
                    valori_finali['piva'],
                    valori_finali['min_id'],
                    valori_finali['ragione_sociale'],
                    valori_finali['deposito'],
                    valori_finali['id_farmacia'],
                    request.operatore,
                    request.note,
                    ps['id_supervisione']
                ))
                supervisioni_approvate += 1

                # Aggiorna ordine
                _applica_correzione_ordine_dict(db, ps['id_testata'], valori_finali, request.operatore)
                ordini_aggiornati += 1

                # Risolvi anomalie correlate
                _risolvi_anomalie_correlate(db, ps['id_testata'], request.operatore)

        else:
            # Solo questo ordine
            db.execute("""
                UPDATE supervisione_anagrafica SET
                    piva_corretta = %s,
                    min_id_corretto = %s,
                    ragione_sociale_corretta = %s,
                    deposito_corretto = %s,
                    id_farmacia_assegnata = %s,
                    stato = 'APPROVED',
                    operatore_approvazione = %s,
                    data_approvazione = CURRENT_TIMESTAMP,
                    note_approvazione = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id_supervisione = %s
            """, (
                valori_finali['piva'],
                valori_finali['min_id'],
                valori_finali['ragione_sociale'],
                valori_finali['deposito'],
                valori_finali['id_farmacia'],
                request.operatore,
                request.note,
                id_supervisione
            ))
            supervisioni_approvate = 1

            _applica_correzione_ordine_dict(db, sup['id_testata'], valori_finali, request.operatore)
            ordini_aggiornati = 1

            _risolvi_anomalie_correlate(db, sup['id_testata'], request.operatore)

        log_operation(
            'APPROVA_SUPERVISIONE_ANAGRAFICA',
            'SUPERVISIONE_ANAGRAFICA',
            id_supervisione,
            f"Approvate {supervisioni_approvate} supervisioni, {ordini_aggiornati} ordini ({request.livello_propagazione})",
            operatore=request.operatore
        )

        db.commit()

        return {
            "success": True,
            "message": f"Approvate {supervisioni_approvate} supervisioni, aggiornati {ordini_aggiornati} ordini",
            "data": {
                "supervisioni_approvate": supervisioni_approvate,
                "ordini_aggiornati": ordini_aggiornati,
                "livello_propagazione": request.livello_propagazione
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{id_supervisione}/rifiuta", summary="Rifiuta supervisione")
async def rifiuta_supervisione(
    id_supervisione: int,
    operatore: str = Query(...),
    note: str = Query(None)
) -> Dict[str, Any]:
    """Rifiuta supervisione anagrafica."""
    db = get_db()

    try:
        result = db.execute("""
            UPDATE supervisione_anagrafica SET
                stato = 'REJECTED',
                operatore_approvazione = %s,
                data_approvazione = CURRENT_TIMESTAMP,
                note_approvazione = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id_supervisione = %s AND stato = 'PENDING'
            RETURNING id_supervisione
        """, (operatore, note, id_supervisione))

        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Supervisione non trovata o già processata")

        db.commit()

        return {
            "success": True,
            "message": "Supervisione rifiutata"
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _applica_correzione_ordine(db, id_testata: int, request: CorrezioneAnagraficaRequest):
    """Applica correzione all'ordine (solo campi forniti)."""
    updates = []
    params = []

    if request.piva:
        updates.append("partita_iva_estratta = %s")
        params.append(request.piva)
    if request.min_id:
        updates.append("min_id = %s")
        params.append(request.min_id)
    if request.ragione_sociale:
        updates.append("ragione_sociale_1 = %s")
        params.append(request.ragione_sociale)
    if request.deposito:
        updates.append("deposito_riferimento = %s")
        params.append(request.deposito)
    if request.indirizzo:
        updates.append("indirizzo = %s")
        params.append(request.indirizzo)
    if request.cap:
        updates.append("cap = %s")
        params.append(request.cap)
    if request.citta:
        updates.append("citta = %s")
        params.append(request.citta)
    if request.provincia:
        updates.append("provincia = %s")
        params.append(request.provincia)

    if updates:
        updates.append("lookup_method = 'MANUALE'")
        updates.append("lookup_score = 100")
        params.append(id_testata)

        db.execute(f"""
            UPDATE ordini_testata SET
                {', '.join(updates)}
            WHERE id_testata = %s
        """, tuple(params))


def _applica_correzione_ordine_dict(db, id_testata: int, valori: dict, operatore: str):
    """Applica correzione all'ordine da dict."""
    updates = []
    params = []

    if valori.get('piva'):
        updates.append("partita_iva_estratta = %s")
        params.append(valori['piva'])
    if valori.get('min_id'):
        updates.append("min_id = %s")
        params.append(valori['min_id'])
    if valori.get('ragione_sociale'):
        updates.append("ragione_sociale_1 = %s")
        params.append(valori['ragione_sociale'])
    if valori.get('deposito'):
        updates.append("deposito_riferimento = %s")
        params.append(valori['deposito'])

    if updates:
        updates.append("lookup_method = 'MANUALE'")
        updates.append("lookup_score = 100")
        params.append(id_testata)

        db.execute(f"""
            UPDATE ordini_testata SET
                {', '.join(updates)}
            WHERE id_testata = %s
        """, tuple(params))


def _risolvi_anomalie_correlate(db, id_testata: int, operatore: str):
    """Risolve anomalie LKP e DEP correlate all'ordine."""
    db.execute("""
        UPDATE anomalie SET
            stato = 'RISOLTA',
            note_risoluzione = %s,
            data_risoluzione = CURRENT_TIMESTAMP
        WHERE id_testata = %s
        AND codice_anomalia IN ('LKP-A01', 'LKP-A02', 'LKP-A03', 'LKP-A04', 'LKP-A05', 'DEP-A01')
        AND stato IN ('APERTA', 'IN_GESTIONE')
    """, (f"[SUPERVISIONE] Approvato da {operatore}", id_testata))

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
