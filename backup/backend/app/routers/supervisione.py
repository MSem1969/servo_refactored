# =============================================================================
# TO_EXTRACTOR v6.1 - ROUTER SUPERVISIONE
# =============================================================================
# Endpoint API per gestione supervisione espositori e criteri ML
# v6.1: Aggiunto workflow ritorno a ordine
# =============================================================================

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..database_pg import (
    get_db,
    get_supervisione_pending,
    get_supervisione_by_testata,
    count_supervisioni_pending,
    get_criterio_by_pattern,
    get_criteri_ordinari,
    get_criteri_stats,
)
from ..services.supervisione import (
    approva_supervisione,
    rifiuta_supervisione,
    modifica_supervisione,
    get_supervisioni_per_ordine,
    get_storico_criteri_applicati,
)
from ..services.ordini import (
    get_stato_righe_ordine,
)


router = APIRouter(prefix="/supervisione", tags=["Supervisione"])


# =============================================================================
# MODELLI PYDANTIC
# =============================================================================

class DecisioneBase(BaseModel):
    """Base per decisioni supervisione."""
    operatore: str
    note: Optional[str] = None


class DecisioneApprova(DecisioneBase):
    """Richiesta approvazione."""
    pass


class DecisioneRifiuta(DecisioneBase):
    """Richiesta rifiuto (note obbligatorie)."""
    note: str  # Override per renderlo obbligatorio


class DecisioneModifica(DecisioneBase):
    """Richiesta modifica manuale."""
    modifiche: dict


class SupervisioneResponse(BaseModel):
    """Risposta singola supervisione."""
    id_supervisione: int
    id_testata: int
    codice_anomalia: str
    codice_espositore: Optional[str]
    descrizione_espositore: Optional[str]
    pezzi_attesi: int
    pezzi_trovati: int
    valore_calcolato: float
    pattern_signature: Optional[str]
    stato: str
    operatore: Optional[str]
    timestamp_creazione: str
    timestamp_decisione: Optional[str]
    note: Optional[str]
    
    class Config:
        from_attributes = True


# =============================================================================
# ENDPOINT SUPERVISIONI PENDING
# =============================================================================

@router.get("/pending", summary="Lista supervisioni in attesa")
async def get_pending():
    """
    Ritorna lista di tutte le supervisioni in attesa di revisione.
    
    Include informazioni su ordine, pattern, e conteggio approvazioni pattern.
    """
    supervisioni = get_supervisione_pending()
    return {
        "count": len(supervisioni),
        "supervisioni": supervisioni
    }


@router.get("/pending/count", summary="Conteggio supervisioni pending")
async def get_pending_count():
    """Ritorna solo il conteggio delle supervisioni pending."""
    return {"count": count_supervisioni_pending()}


# =============================================================================
# ENDPOINT DETTAGLIO SUPERVISIONE
# =============================================================================

@router.get("/{id_supervisione}", summary="Dettaglio supervisione")
async def get_supervisione(id_supervisione: int):
    """
    Ritorna dettagli completi di una supervisione.
    
    Include:
    - Dati anomalia
    - Stato attuale
    - Informazioni pattern ML
    - Storico decisioni
    """
    db = get_db()
    
    row = db.execute("""
        SELECT se.*, coe.count_approvazioni, coe.is_ordinario, coe.pattern_descrizione
        FROM SUPERVISIONE_ESPOSITORE se
        LEFT JOIN CRITERI_ORDINARI_ESPOSITORE coe ON se.pattern_signature = coe.pattern_signature
        WHERE se.id_supervisione = %s
    """, (id_supervisione,)).fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Supervisione non trovata")
    
    return dict(row)


@router.get("/ordine/{id_testata}", summary="Supervisioni per ordine")
async def get_supervisioni_ordine(id_testata: int):
    """Ritorna tutte le supervisioni per un ordine specifico."""
    supervisioni = get_supervisioni_per_ordine(id_testata)
    return {
        "id_testata": id_testata,
        "count": len(supervisioni),
        "supervisioni": supervisioni
    }


# =============================================================================
# ENDPOINT DECISIONI
# =============================================================================

@router.post("/{id_supervisione}/approva", summary="Approva supervisione")
async def approva(id_supervisione: int, decisione: DecisioneApprova):
    """
    Approva una supervisione.
    
    Effetti:
    - Stato → APPROVED
    - Incrementa contatore pattern
    - Se pattern raggiunge soglia (5), diventa ordinario
    - Sblocca ordine se era l'ultima pending
    """
    success = approva_supervisione(
        id_supervisione,
        decisione.operatore,
        decisione.note
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Supervisione non trovata")
    
    return {
        "success": True,
        "id_supervisione": id_supervisione,
        "azione": "APPROVED",
        "operatore": decisione.operatore
    }


@router.post("/{id_supervisione}/rifiuta", summary="Rifiuta supervisione")
async def rifiuta(id_supervisione: int, decisione: DecisioneRifiuta):
    """
    Rifiuta una supervisione.
    
    Effetti:
    - Stato → REJECTED
    - Reset contatore pattern a 0
    - Ordine rimane bloccato (richiede intervento manuale)
    """
    success = rifiuta_supervisione(
        id_supervisione,
        decisione.operatore,
        decisione.note
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Supervisione non trovata")
    
    return {
        "success": True,
        "id_supervisione": id_supervisione,
        "azione": "REJECTED",
        "operatore": decisione.operatore
    }


@router.post("/{id_supervisione}/modifica", summary="Modifica manuale")
async def modifica(id_supervisione: int, decisione: DecisioneModifica):
    """
    Applica modifiche manuali a un ordine in supervisione.
    
    Effetti:
    - Stato → MODIFIED
    - Salva modifiche in JSON
    - NON incrementa pattern (caso speciale)
    - Sblocca ordine
    """
    success = modifica_supervisione(
        id_supervisione,
        decisione.operatore,
        decisione.modifiche,
        decisione.note
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Supervisione non trovata")
    
    return {
        "success": True,
        "id_supervisione": id_supervisione,
        "azione": "MODIFIED",
        "operatore": decisione.operatore
    }


# =============================================================================
# v6.1: ENDPOINT WORKFLOW RITORNO A ORDINE
# =============================================================================

@router.post("/{id_supervisione}/completa-e-torna", summary="Approva e torna a ordine")
async def approva_e_torna(id_supervisione: int, decisione: DecisioneApprova):
    """
    Approva supervisione e aggiorna stato riga a SUPERVISIONATO.
    
    Usato dal workflow Ordine → Supervisione → Ordine.
    """
    db = get_db()
    
    # Ottieni id_testata dalla supervisione
    sup = db.execute(
        "SELECT id_testata FROM SUPERVISIONE_ESPOSITORE WHERE id_supervisione = %s",
        (id_supervisione,)
    ).fetchone()
    
    if not sup:
        raise HTTPException(status_code=404, detail="Supervisione non trovata")
    
    # Approva supervisione
    success = approva_supervisione(
        id_supervisione,
        decisione.operatore,
        decisione.note
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Errore approvazione")
    
    # Aggiorna stato riga a SUPERVISIONATO
    db.execute("""
        UPDATE ORDINI_DETTAGLIO
        SET stato_riga = 'SUPERVISIONATO',
            note_supervisione = COALESCE(note_supervisione || ' | ', '') || %s
        WHERE id_supervisione = %s
    """, (f"[{decisione.operatore}] Approvato", id_supervisione))
    db.commit()
    
    return {
        "success": True,
        "id_supervisione": id_supervisione,
        "id_testata": sup['id_testata'],
        "azione": "APPROVED",
        "riga_stato": "SUPERVISIONATO",
        "redirect_url": f"/ordini/{sup['id_testata']}"
    }


@router.post("/{id_supervisione}/modifica-e-torna", summary="Modifica e torna a ordine")
async def modifica_e_torna(id_supervisione: int, decisione: DecisioneModifica):
    """
    Applica modifiche riga e torna a ordine.
    """
    db = get_db()
    
    # Ottieni id_testata dalla supervisione
    sup = db.execute(
        "SELECT id_testata FROM SUPERVISIONE_ESPOSITORE WHERE id_supervisione = %s",
        (id_supervisione,)
    ).fetchone()
    
    if not sup:
        raise HTTPException(status_code=404, detail="Supervisione non trovata")
    
    # Applica modifica
    success = modifica_supervisione(
        id_supervisione,
        decisione.operatore,
        decisione.modifiche,
        decisione.note
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Errore modifica")
    
    # Aggiorna stato riga a SUPERVISIONATO
    db.execute("""
        UPDATE ORDINI_DETTAGLIO
        SET stato_riga = 'SUPERVISIONATO',
            note_supervisione = COALESCE(note_supervisione || ' | ', '') || %s
        WHERE id_supervisione = %s
    """, (f"[{decisione.operatore}] Modificato", id_supervisione))
    db.commit()
    
    return {
        "success": True,
        "id_supervisione": id_supervisione,
        "id_testata": sup['id_testata'],
        "azione": "MODIFIED",
        "campi_modificati": list(decisione.modifiche.keys()),
        "redirect_url": f"/ordini/{sup['id_testata']}"
    }


@router.post("/{id_supervisione}/lascia-sospeso", summary="Lascia sospeso e torna")
async def lascia_sospeso(id_supervisione: int, operatore: str = Query(...)):
    """
    Torna a ordine senza decisione (riga rimane IN_SUPERVISIONE).
    """
    db = get_db()
    
    # Ottieni id_testata dalla supervisione
    sup = db.execute(
        "SELECT id_testata FROM SUPERVISIONE_ESPOSITORE WHERE id_supervisione = %s",
        (id_supervisione,)
    ).fetchone()
    
    if not sup:
        raise HTTPException(status_code=404, detail="Supervisione non trovata")
    
    return {
        "success": True,
        "id_supervisione": id_supervisione,
        "id_testata": sup['id_testata'],
        "stato": "PENDING",
        "redirect_url": f"/ordini/{sup['id_testata']}"
    }


# =============================================================================
# ENDPOINT CRITERI ML
# =============================================================================

@router.get("/criteri/ordinari", summary="Lista criteri ordinari")
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


@router.get("/criteri/stats", summary="Statistiche criteri ML")
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


@router.get("/criteri/{pattern_signature}", summary="Dettaglio pattern")
async def get_pattern(pattern_signature: str):
    """Ritorna dettagli di un pattern specifico."""
    criterio = get_criterio_by_pattern(pattern_signature)
    
    if not criterio:
        raise HTTPException(status_code=404, detail="Pattern non trovato")
    
    return criterio


@router.post("/criteri/{pattern_signature}/reset", summary="Reset pattern")
async def reset_pattern(pattern_signature: str, operatore: str = Query(...)):
    """
    Resetta contatore approvazioni di un pattern.
    
    Utile se un pattern ordinario inizia a generare falsi positivi.
    """
    from ..services.supervisione import registra_rifiuto_pattern
    
    registra_rifiuto_pattern(pattern_signature)
    
    return {
        "success": True,
        "pattern_signature": pattern_signature,
        "azione": "RESET",
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
# v6.2: ENDPOINT ML PATTERN MATCHING
# =============================================================================

class RisoluzioneConflittoRequest(BaseModel):
    """Richiesta risoluzione conflitto ML."""
    operatore: str
    scelta: str  # 'PATTERN', 'ESTRAZIONE', 'MANUALE'
    modifiche_manuali: Optional[dict] = None
    note: Optional[str] = None


@router.get("/{id_supervisione}/confronto-ml", summary="Confronto ML per supervisione")
async def get_confronto_ml(id_supervisione: int):
    """
    v6.2: Ritorna confronto tra child estratti e pattern ML.

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
    from ..services.ml_pattern_matching import (
        calcola_similarity_sequenze,
        determina_decisione_ml,
        cerca_pattern_per_espositore,
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


@router.post("/{id_supervisione}/risolvi-conflitto", summary="Risolvi conflitto ML")
async def risolvi_conflitto_ml(id_supervisione: int, req: RisoluzioneConflittoRequest):
    """
    v6.2: Risolve conflitto ML tra pattern e estrazione.

    L'operatore puo' scegliere:
    - PATTERN: Usa i child dal pattern appreso (corregge errore estrazione)
    - ESTRAZIONE: Usa i child estratti (pattern non valido per questo caso)
    - MANUALE: Specifica manualmente i child corretti

    La scelta aggiorna anche il pattern ML:
    - PATTERN: Incrementa confidence del pattern
    - ESTRAZIONE: Decrementa confidence o invalida pattern
    - MANUALE: Crea nuovo pattern con i dati corretti
    """
    import json
    from ..services.ml_pattern_matching import (
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
        # Approva supervisione con nota
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
        # Usa estrazione: il pattern non e' valido per questo caso
        # Approva supervisione ma non incrementa pattern
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
        # Modifica manuale: richiede modifiche_manuali
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


@router.get("/ml/stats", summary="Statistiche sistema ML")
async def get_ml_stats():
    """
    v6.2: Ritorna statistiche complete del sistema ML.

    Include:
    - Pattern totali, ordinari, con sequenza child
    - Decisioni ML ultimi 30 giorni (per tipo)
    - Accuracy (decisioni con esito verificato)
    """
    from ..services.ml_pattern_matching import get_statistiche_ml

    return get_statistiche_ml()


@router.get("/ml/log", summary="Log decisioni ML")
async def get_ml_log(
    limit: int = Query(50, ge=1, le=200),
    decision: Optional[str] = Query(None, description="Filtra per decisione: APPLY_ML, APPLY_WARNING, SEND_SUPERVISION")
):
    """
    v6.2: Ritorna log delle decisioni ML.

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


@router.post("/ml/processa-retroattive", summary="Processa anomalie risolte retroattivamente")
async def processa_retroattive():
    """
    v6.2: Processa retroattivamente le anomalie ESPOSITORE già risolte.

    Crea pattern ML dalle anomalie storiche risolte prima dell'implementazione
    del sistema ML. Da eseguire una tantum dopo la migrazione.

    Returns:
        Statistiche del processamento
    """
    from ..services.ml_pattern_matching import processa_anomalie_risolte_retroattive

    stats = processa_anomalie_risolte_retroattive()

    return {
        "success": True,
        "message": f"Processate {stats['processate']} anomalie retroattive",
        "stats": stats
    }
