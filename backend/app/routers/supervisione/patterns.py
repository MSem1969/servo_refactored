# =============================================================================
# SERV.O v8.1 - SUPERVISIONE PATTERNS/ML
# =============================================================================
# Endpoint per gestione criteri ML, pattern matching e statistiche
# =============================================================================

from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from ...database_pg import (
    get_db,
    get_criterio_by_pattern,
    get_criteri_ordinari,
    get_criteri_stats,
)
from ...services.supervisione import (
    approva_supervisione,
    modifica_supervisione,
    get_storico_criteri_applicati,
    registra_rifiuto_pattern,
)
from .schemas import RisoluzioneConflittoRequest


router = APIRouter(prefix="/criteri", tags=["Criteri ML"])


# =============================================================================
# ENDPOINT CRITERI ML
# =============================================================================

@router.get("/ordinari", summary="Lista criteri ordinari")
async def get_criteri():
    """
    Ritorna tutti i pattern promossi a criteri ordinari.

    Un pattern diventa ordinario dopo 5 approvazioni consecutive.
    I criteri ordinari vengono applicati automaticamente senza supervisione.
    """
    criteri = get_criteri_ordinari()
    return {
        "count": len(criteri),
        "criteri": criteri
    }


@router.get("/tutti", summary="Lista tutti i pattern ML")
async def get_tutti_criteri():
    """
    Ritorna TUTTI i pattern ML (ordinari + in apprendimento).

    Include pattern espositore, listino e lookup, con indicazione dello stato:
    - is_ordinario: true = automatico, false = in apprendimento
    - count_approvazioni: numero approvazioni attuali
    """
    db = get_db()

    # Pattern espositore
    criteri_esp = db.execute("""
        SELECT
            pattern_signature,
            pattern_descrizione,
            codice_espositore,
            fascia_scostamento,
            count_approvazioni,
            is_ordinario,
            data_promozione,
            'espositore' AS tipo
        FROM criteri_ordinari_espositore
        ORDER BY count_approvazioni DESC, data_promozione DESC NULLS LAST
    """).fetchall()

    # Pattern listino - v11.4: includi codice_anomalia e descrizione_prodotto
    criteri_lst = db.execute("""
        SELECT
            col.pattern_signature,
            col.pattern_descrizione,
            col.codice_aic,
            col.codice_anomalia,
            col.vendor,
            col.count_approvazioni,
            col.is_ordinario,
            col.data_promozione,
            lp.descrizione AS descrizione_prodotto,
            'listino' AS tipo
        FROM criteri_ordinari_listino col
        LEFT JOIN listino_prodotti lp ON col.codice_aic = lp.codice_aic
        ORDER BY col.count_approvazioni DESC, col.data_promozione DESC NULLS LAST
    """).fetchall()

    # Pattern lookup - v11.4: includi ragione_sociale farmacia
    criteri_lkp = db.execute("""
        SELECT
            colk.pattern_signature,
            colk.pattern_descrizione,
            colk.partita_iva_pattern,
            colk.vendor,
            colk.codice_anomalia,
            colk.count_approvazioni,
            colk.is_ordinario,
            colk.data_promozione,
            colk.min_id_default,
            af.ragione_sociale AS ragione_sociale_farmacia,
            'lookup' AS tipo
        FROM criteri_ordinari_lookup colk
        LEFT JOIN anagrafica_farmacie af ON colk.id_farmacia_default = af.id_farmacia
        ORDER BY colk.count_approvazioni DESC, colk.data_promozione DESC NULLS LAST
    """).fetchall()

    # v9.0: Pattern AIC
    criteri_aic = db.execute("""
        SELECT
            pattern_signature,
            pattern_descrizione,
            descrizione_normalizzata,
            vendor,
            codice_aic_default,
            count_approvazioni,
            is_ordinario,
            data_promozione,
            'aic' AS tipo
        FROM criteri_ordinari_aic
        ORDER BY count_approvazioni DESC, data_promozione DESC NULLS LAST
    """).fetchall()

    all_criteri = [dict(c) for c in criteri_esp] + [dict(c) for c in criteri_lst] + [dict(c) for c in criteri_lkp] + [dict(c) for c in criteri_aic]

    # Ordina per count_approvazioni decrescente
    all_criteri.sort(key=lambda x: (x.get('count_approvazioni', 0), str(x.get('data_promozione') or '')), reverse=True)

    return {
        "count": len(all_criteri),
        "count_ordinari": sum(1 for c in all_criteri if c.get('is_ordinario')),
        "count_in_apprendimento": sum(1 for c in all_criteri if not c.get('is_ordinario') and c.get('count_approvazioni', 0) > 0),
        "criteri": all_criteri
    }


@router.get("/stats", summary="Statistiche criteri ML")
async def get_stats_criteri():
    """
    Ritorna statistiche sul sistema di apprendimento.

    Include:
    - Totale pattern
    - Pattern ordinari (applicati automaticamente)
    - Pattern in apprendimento (count > 0 ma < 5)
    - Applicazioni automatiche oggi
    """
    return get_criteri_stats()


@router.get("/{pattern_signature}", summary="Dettaglio pattern")
async def get_pattern(pattern_signature: str):
    """Ritorna dettagli di un pattern specifico."""
    criterio = get_criterio_by_pattern(pattern_signature)

    if not criterio:
        raise HTTPException(status_code=404, detail="Pattern non trovato")

    return criterio


@router.post("/{pattern_signature}/reset", summary="Reset pattern")
async def reset_pattern(pattern_signature: str, operatore: str = Query(...)):
    """
    Resetta contatore approvazioni di un pattern.

    Utile se un pattern ordinario inizia a generare falsi positivi.
    """
    registra_rifiuto_pattern(pattern_signature)

    return {
        "success": True,
        "pattern_signature": pattern_signature,
        "azione": "RESET",
        "operatore": operatore
    }


@router.delete("/{pattern_signature}", summary="Cancella pattern ML")
async def delete_pattern(pattern_signature: str, operatore: str = Query(...)):
    """
    Cancella completamente un pattern ML dal sistema.

    A differenza di RESET (che azzera il contatore), DELETE rimuove
    il pattern dalla tabella. Usare con cautela - il pattern dovrà
    essere riappreso da zero.
    """
    from ...database_pg import log_operation

    db = get_db()

    # Cerca e cancella da tutte le tabelle pattern
    deleted_from = None

    result = db.execute(
        "DELETE FROM criteri_ordinari_espositore WHERE pattern_signature = %s RETURNING pattern_signature",
        (pattern_signature,)
    ).fetchone()
    if result:
        deleted_from = "espositore"

    if not deleted_from:
        result = db.execute(
            "DELETE FROM criteri_ordinari_listino WHERE pattern_signature = %s RETURNING pattern_signature",
            (pattern_signature,)
        ).fetchone()
        if result:
            deleted_from = "listino"

    if not deleted_from:
        result = db.execute(
            "DELETE FROM criteri_ordinari_lookup WHERE pattern_signature = %s RETURNING pattern_signature",
            (pattern_signature,)
        ).fetchone()
        if result:
            deleted_from = "lookup"

    if not deleted_from:
        result = db.execute(
            "DELETE FROM criteri_ordinari_aic WHERE pattern_signature = %s RETURNING pattern_signature",
            (pattern_signature,)
        ).fetchone()
        if result:
            deleted_from = "aic"

    if not deleted_from:
        raise HTTPException(status_code=404, detail="Pattern non trovato")

    db.commit()

    # Log operazione
    log_operation(
        'CANCELLAZIONE_PATTERN',
        f'criteri_ordinari_{deleted_from}',
        0,
        f"Pattern {pattern_signature[:16]}... cancellato definitivamente",
        operatore=operatore
    )

    return {
        "success": True,
        "pattern_signature": pattern_signature,
        "tipo": deleted_from,
        "azione": "CANCELLATO",
        "operatore": operatore
    }


@router.post("/{pattern_signature}/promuovi", summary="Forza promozione pattern")
async def promuovi_pattern(pattern_signature: str, operatore: str = Query(...)):
    """
    Forza promozione di un pattern a "ordinario" (automatico).

    Permette di rendere automatico un pattern anche prima delle 5 approvazioni standard.
    Supporta pattern espositore, listino, lookup e aic.
    """
    from ...database_pg import log_operation

    db = get_db()

    # Verifica che il pattern esista in una delle quattro tabelle
    criterio_esp = db.execute(
        "SELECT pattern_signature, count_approvazioni FROM criteri_ordinari_espositore WHERE pattern_signature = %s",
        (pattern_signature,)
    ).fetchone()

    criterio_lst = db.execute(
        "SELECT pattern_signature, count_approvazioni FROM criteri_ordinari_listino WHERE pattern_signature = %s",
        (pattern_signature,)
    ).fetchone()

    criterio_lkp = db.execute(
        "SELECT pattern_signature, count_approvazioni FROM criteri_ordinari_lookup WHERE pattern_signature = %s",
        (pattern_signature,)
    ).fetchone()

    # v11.3: Aggiunto supporto per criteri_ordinari_aic
    criterio_aic = db.execute(
        "SELECT pattern_signature, count_approvazioni FROM criteri_ordinari_aic WHERE pattern_signature = %s",
        (pattern_signature,)
    ).fetchone()

    if not criterio_esp and not criterio_lst and not criterio_lkp and not criterio_aic:
        raise HTTPException(status_code=404, detail="Pattern non trovato")

    # Forza promozione settando count_approvazioni = 5 e is_ordinario = true
    if criterio_esp:
        db.execute("""
            UPDATE criteri_ordinari_espositore
            SET count_approvazioni = 5, is_ordinario = true,
                data_promozione = CURRENT_TIMESTAMP
            WHERE pattern_signature = %s
        """, (pattern_signature,))
        tipo = "espositore"
    elif criterio_lst:
        db.execute("""
            UPDATE criteri_ordinari_listino
            SET count_approvazioni = 5, is_ordinario = true,
                data_promozione = CURRENT_TIMESTAMP
            WHERE pattern_signature = %s
        """, (pattern_signature,))
        tipo = "listino"
    elif criterio_lkp:
        db.execute("""
            UPDATE criteri_ordinari_lookup
            SET count_approvazioni = 5, is_ordinario = true,
                data_promozione = CURRENT_TIMESTAMP
            WHERE pattern_signature = %s
        """, (pattern_signature,))
        tipo = "lookup"
    else:
        # v11.3: Pattern AIC
        db.execute("""
            UPDATE criteri_ordinari_aic
            SET count_approvazioni = 5, is_ordinario = true,
                data_promozione = CURRENT_TIMESTAMP
            WHERE pattern_signature = %s
        """, (pattern_signature,))
        tipo = "aic"

    db.commit()

    # v11.3: Log operazione
    log_operation(
        'PROMOZIONE_FORZATA_PATTERN',
        f'criteri_ordinari_{tipo}',
        0,
        f"Pattern {pattern_signature[:16]}... promosso forzatamente a ordinario",
        operatore=operatore
    )

    return {
        "success": True,
        "pattern_signature": pattern_signature,
        "tipo": tipo,
        "azione": "PROMOZIONE_FORZATA",
        "operatore": operatore
    }


# =============================================================================
# ENDPOINT STORICO
# =============================================================================

@router.get("/storico/applicazioni", summary="Storico applicazioni criteri")
async def get_storico(limit: int = Query(50, ge=1, le=200)):
    """
    Ritorna storico delle applicazioni criteri (automatiche e manuali).

    Utile per audit trail e debug.
    """
    storico = get_storico_criteri_applicati(limit)
    return {
        "count": len(storico),
        "applicazioni": storico
    }


# =============================================================================
# ENDPOINT ML PATTERN MATCHING
# =============================================================================

# Router separato per endpoint ML (senza prefix /criteri)
ml_router = APIRouter(prefix="/ml", tags=["ML Pattern Matching"])


@ml_router.get("/stats", summary="Statistiche sistema ML")
async def get_ml_stats():
    """
    Ritorna statistiche complete del sistema ML.

    Include:
    - Pattern totali, ordinari, con sequenza child
    - Decisioni ML ultimi 30 giorni (per tipo)
    - Accuracy (decisioni con esito verificato)
    """
    from ...services.ml_pattern_matching import get_statistiche_ml

    return get_statistiche_ml()


@ml_router.get("/log", summary="Log decisioni ML")
async def get_ml_log(
    limit: int = Query(50, ge=1, le=200),
    decision: Optional[str] = Query(None, description="Filtra per decisione: APPLY_ML, APPLY_WARNING, SEND_SUPERVISION")
):
    """
    Ritorna log delle decisioni ML.

    Utile per audit e analisi del comportamento del sistema.
    """
    db = get_db()

    query = """
        SELECT lm.*, ot.numero_ordine_vendor AS numero_ordine
        FROM log_ml_decisions lm
        LEFT JOIN ordini_testata ot ON lm.id_testata = ot.id_testata
    """

    params = []
    if decision:
        query += " WHERE lm.decision = %s"
        params.append(decision)

    query += " ORDER BY lm.timestamp DESC LIMIT %s"
    params.append(limit)

    rows = db.execute(query, tuple(params)).fetchall()

    return {
        "count": len(rows),
        "log": [dict(r) for r in rows]
    }


@ml_router.post("/processa-retroattive", summary="Processa anomalie risolte retroattivamente")
async def processa_retroattive():
    """
    Processa retroattivamente le anomalie ESPOSITORE gia risolte.

    Crea pattern ML dalle anomalie storiche risolte prima dell'implementazione
    del sistema ML. Da eseguire una tantum dopo la migrazione.

    Returns:
        Statistiche del processamento
    """
    from ...services.ml_pattern_matching import processa_anomalie_risolte_retroattive

    stats = processa_anomalie_risolte_retroattive()

    return {
        "success": True,
        "message": f"Processate {stats['processate']} anomalie retroattive",
        "stats": stats
    }


# =============================================================================
# ENDPOINT CONFRONTO ML
# =============================================================================

# Router per endpoint confronto/risoluzione (senza prefix)
confronto_router = APIRouter(tags=["ML Confronto"])


@confronto_router.get("/{id_supervisione}/confronto-ml", summary="Confronto ML per supervisione")
async def get_confronto_ml(id_supervisione: int):
    """
    Ritorna confronto tra child estratti e pattern ML.

    Usato per visualizzare le differenze quando si verifica
    un conflitto ESP-A06 (similarity < 50%).

    Returns:
        - child_estratti: Lista child estratti dal PDF
        - child_pattern: Lista child dal pattern appreso
        - similarity_score: Score di similarita (0-100)
        - similarity_details: Dettagli calcolo (jaccard, lcs, qty, count)
        - decision: Decisione suggerita ML
    """
    import json
    from ...services.ml_pattern_matching import (
        calcola_similarity_sequenze,
        determina_decisione_ml,
    )

    db = get_db()

    # Recupera supervisione
    sup = db.execute("""
        SELECT se.*, coe.child_sequence_json, coe.descrizione_normalizzata
        FROM supervisione_espositore se
        LEFT JOIN criteri_ordinari_espositore coe ON se.pattern_signature = coe.pattern_signature
        WHERE se.id_supervisione = %s
    """, (id_supervisione,)).fetchone()

    if not sup:
        raise HTTPException(status_code=404, detail="Supervisione non trovata")

    sup = dict(sup)

    # Recupera child estratti dall'ordine
    parent = db.execute("""
        SELECT id_dettaglio, descrizione
        FROM ordini_dettaglio
        WHERE id_testata = %s
          AND codice_originale = %s
          AND is_espositore = TRUE
        LIMIT 1
    """, (sup['id_testata'], sup['codice_espositore'])).fetchone()

    child_estratti = []
    if parent:
        parent = dict(parent)
        children = db.execute("""
            SELECT codice_aic, codice_originale, descrizione, q_venduta AS quantita
            FROM ordini_dettaglio
            WHERE id_testata = %s
              AND id_parent_espositore = %s
              AND is_child = TRUE
            ORDER BY n_riga
        """, (sup['id_testata'], parent['id_dettaglio'])).fetchall()

        child_estratti = [
            {
                'aic': r['codice_aic'],
                'codice': r['codice_originale'],
                'descrizione': r['descrizione'],
                'quantita': r['quantita']
            }
            for r in children
        ]

    # Recupera child pattern
    child_pattern = []
    if sup.get('child_sequence_json'):
        child_pattern = json.loads(sup['child_sequence_json'])

    # Calcola similarity
    similarity_score, similarity_details = calcola_similarity_sequenze(
        child_estratti, child_pattern
    )

    # Determina decisione
    ml_decision = determina_decisione_ml(similarity_score)

    return {
        "id_supervisione": id_supervisione,
        "child_estratti": child_estratti,
        "child_pattern": child_pattern,
        "similarity_score": similarity_score,
        "similarity_details": similarity_details,
        "ml_decision": {
            "decision": ml_decision.decision,
            "reason": ml_decision.reason,
        },
        "pattern_signature": sup.get('pattern_signature'),
        "descrizione_pattern": sup.get('descrizione_normalizzata'),
    }


@confronto_router.post("/{id_supervisione}/risolvi-conflitto", summary="Risolvi conflitto ML")
async def risolvi_conflitto_ml(id_supervisione: int, req: RisoluzioneConflittoRequest):
    """
    Risolve conflitto ML tra pattern e estrazione.

    L'operatore puo scegliere:
    - PATTERN: Usa i child dal pattern appreso (corregge errore estrazione)
    - ESTRAZIONE: Usa i child estratti (pattern non valido per questo caso)
    - MANUALE: Specifica manualmente i child corretti

    La scelta aggiorna anche il pattern ML:
    - PATTERN: Incrementa confidence del pattern
    - ESTRAZIONE: Decrementa confidence o invalida pattern
    - MANUALE: Crea nuovo pattern con i dati corretti
    """
    from ...services.ml_pattern_matching import (
        aggiorna_esito_ml,
        aggiorna_statistiche_pattern,
    )

    db = get_db()

    # Recupera supervisione e log ML
    sup = db.execute("""
        SELECT se.*, lm.id_log
        FROM supervisione_espositore se
        LEFT JOIN log_ml_decisions lm ON lm.id_testata = se.id_testata
            AND lm.pattern_signature = se.pattern_signature
        WHERE se.id_supervisione = %s
    """, (id_supervisione,)).fetchone()

    if not sup:
        raise HTTPException(status_code=404, detail="Supervisione non trovata")

    sup = dict(sup)

    if req.scelta == 'PATTERN':
        # Usa pattern: l'estrazione era errata
        approva_supervisione(
            id_supervisione,
            req.operatore,
            note=f"Conflitto ML risolto: usato PATTERN. {req.note or ''}"
        )

        # Aggiorna statistiche pattern (successo)
        if sup.get('pattern_signature'):
            aggiorna_statistiche_pattern(sup['pattern_signature'], successo=True)

        # Aggiorna esito ML log
        if sup.get('id_log'):
            aggiorna_esito_ml(sup['id_log'], 'CORRECT', req.operatore)

        return {
            "success": True,
            "id_supervisione": id_supervisione,
            "scelta": "PATTERN",
            "azione": "Supervisione approvata, pattern confermato",
        }

    elif req.scelta == 'ESTRAZIONE':
        # Usa estrazione: il pattern non e valido per questo caso
        db.execute("""
            UPDATE supervisione_espositore
            SET stato = 'APPROVED',
                operatore = %s,
                timestamp_decisione = CURRENT_TIMESTAMP,
                note = %s
            WHERE id_supervisione = %s
        """, (req.operatore, f"Conflitto ML risolto: usata ESTRAZIONE. {req.note or ''}", id_supervisione))

        # Aggiorna statistiche pattern (fallimento)
        if sup.get('pattern_signature'):
            aggiorna_statistiche_pattern(sup['pattern_signature'], successo=False)

        # Aggiorna esito ML log
        if sup.get('id_log'):
            aggiorna_esito_ml(sup['id_log'], 'INCORRECT', req.operatore)

        db.commit()

        return {
            "success": True,
            "id_supervisione": id_supervisione,
            "scelta": "ESTRAZIONE",
            "azione": "Supervisione approvata, estrazione mantenuta",
        }

    elif req.scelta == 'MANUALE':
        # Modifica manuale
        if not req.modifiche_manuali:
            raise HTTPException(
                status_code=400,
                detail="Per scelta MANUALE, specificare modifiche_manuali"
            )

        modifica_supervisione(
            id_supervisione,
            req.operatore,
            req.modifiche_manuali,
            note=f"Conflitto ML risolto: modifica MANUALE. {req.note or ''}"
        )

        # Aggiorna esito ML log
        if sup.get('id_log'):
            aggiorna_esito_ml(sup['id_log'], 'MODIFIED', req.operatore)

        return {
            "success": True,
            "id_supervisione": id_supervisione,
            "scelta": "MANUALE",
            "azione": "Supervisione modificata manualmente",
            "modifiche": list(req.modifiche_manuali.keys()),
        }

    else:
        raise HTTPException(
            status_code=400,
            detail="Scelta non valida. Usare: PATTERN, ESTRAZIONE, MANUALE"
        )
