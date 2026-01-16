# =============================================================================
# SERV.O v8.1 - SUPERVISIONE PREZZO
# =============================================================================
# Endpoint per gestione supervisione prezzo (PRICE-A01)
# =============================================================================

import json
from fastapi import APIRouter, HTTPException, Query

from ...database_pg import get_db
from ...services.supervisione import sblocca_ordine_se_completo
from .schemas import PrezzoRigheRequest, ApprovaPrezzoRequest, DecisioneRifiuta


router = APIRouter(prefix="/prezzo", tags=["Supervisione Prezzo"])


# =============================================================================
# ENDPOINT SUPERVISIONE PREZZO
# =============================================================================

@router.get("/pending", summary="Lista supervisioni prezzo pending")
async def get_prezzo_pending():
    """
    Ritorna lista supervisioni prezzo in attesa.

    Le supervisioni prezzo riguardano ordini con righe in vendita
    senza prezzo (PRICE-A01).
    """
    db = get_db()

    rows = db.execute("""
        SELECT sp.*,
               ot.numero_ordine_vendor,
               ot.ragione_sociale_1,
               ot.data_ordine
        FROM supervisione_prezzo sp
        JOIN ordini_testata ot ON sp.id_testata = ot.id_testata
        WHERE sp.stato = 'PENDING'
        ORDER BY sp.timestamp_creazione DESC
    """).fetchall()

    return {
        "count": len(rows),
        "tipo": "prezzo",
        "supervisioni": [dict(r) for r in rows]
    }


@router.get("/{id_supervisione}", summary="Dettaglio supervisione prezzo")
async def get_supervisione_prezzo_detail(id_supervisione: int):
    """
    Ritorna dettagli supervisione prezzo con righe coinvolte.

    Include:
    - Dati ordine
    - Lista righe senza prezzo con dettagli (AIC, descrizione, quantita)
    - Suggerimenti prezzi da listino vendor se disponibili
    """
    db = get_db()

    # Recupera supervisione
    sup = db.execute("""
        SELECT sp.*,
               ot.numero_ordine_vendor,
               ot.ragione_sociale_1,
               ot.data_ordine,
               ot.min_id
        FROM supervisione_prezzo sp
        JOIN ordini_testata ot ON sp.id_testata = ot.id_testata
        WHERE sp.id_supervisione = %s
    """, (id_supervisione,)).fetchone()

    if not sup:
        raise HTTPException(status_code=404, detail="Supervisione prezzo non trovata")

    result = dict(sup)

    # Parse righe dettaglio JSON
    righe = []
    if result.get('righe_dettaglio_json'):
        righe = json.loads(result['righe_dettaglio_json']) if isinstance(result['righe_dettaglio_json'], str) else result['righe_dettaglio_json']

    # Arricchisci righe con suggerimenti da listino
    for riga in righe:
        aic = riga.get('codice_aic')
        if aic:
            # Cerca nel listino vendor
            listino = db.execute("""
                SELECT prezzo_netto, prezzo_pubblico
                FROM listini_vendor
                WHERE codice_aic = %s AND attivo = TRUE
                LIMIT 1
            """, (aic,)).fetchone()

            if listino:
                riga['suggerimento_listino'] = dict(listino)

            # Cerca in ordini precedenti
            storico = db.execute("""
                SELECT prezzo_netto, prezzo_pubblico, COUNT(*) as occorrenze
                FROM ordini_dettaglio
                WHERE codice_aic = %s AND prezzo_netto > 0
                GROUP BY prezzo_netto, prezzo_pubblico
                ORDER BY occorrenze DESC
                LIMIT 1
            """, (aic,)).fetchone()

            if storico:
                riga['suggerimento_storico'] = dict(storico)

    result['righe_dettaglio'] = righe

    return result


@router.put("/{id_supervisione}/righe", summary="Aggiorna prezzi righe")
async def aggiorna_prezzi_righe(id_supervisione: int, req: PrezzoRigheRequest):
    """
    Aggiorna prezzi per righe specifiche.

    Permette di inserire manualmente i prezzi per ogni riga senza prezzo.
    Ricalcola automaticamente il valore_netto (prezzo_netto * q_venduta).

    Non approva automaticamente - usare endpoint /approve dopo.
    """
    db = get_db()

    # Verifica supervisione esiste e e pending
    sup = db.execute("""
        SELECT * FROM supervisione_prezzo
        WHERE id_supervisione = %s AND stato = 'PENDING'
    """, (id_supervisione,)).fetchone()

    if not sup:
        raise HTTPException(status_code=404, detail="Supervisione non trovata o gia processata")

    sup = dict(sup)

    # Aggiorna prezzi per ogni riga
    righe_aggiornate = 0
    for riga in req.righe_modificate:
        updates = []
        params = []

        if riga.prezzo_netto is not None:
            updates.append("prezzo_netto = %s")
            params.append(riga.prezzo_netto)

        if riga.prezzo_pubblico is not None:
            updates.append("prezzo_pubblico = %s")
            params.append(riga.prezzo_pubblico)

        if updates:
            # Aggiorna anche valore_netto
            updates.append("valore_netto = COALESCE(%s, prezzo_netto) * COALESCE(q_venduta, 0)")
            params.append(riga.prezzo_netto)

            params.append(riga.id_dettaglio)

            db.execute(f"""
                UPDATE ordini_dettaglio
                SET {', '.join(updates)}
                WHERE id_dettaglio = %s
            """, tuple(params))
            righe_aggiornate += 1

    # Aggiorna JSON nella supervisione
    righe_json = sup.get('righe_dettaglio_json')
    if righe_json:
        righe_list = json.loads(righe_json) if isinstance(righe_json, str) else righe_json

        # Aggiorna stato righe nel JSON
        aggiornamenti_map = {r.id_dettaglio: r for r in req.righe_modificate}
        for riga in righe_list:
            id_det = riga.get('id_dettaglio')
            if id_det and id_det in aggiornamenti_map:
                upd = aggiornamenti_map[id_det]
                if upd.prezzo_netto is not None:
                    riga['prezzo_inserito'] = upd.prezzo_netto
                if upd.prezzo_pubblico is not None:
                    riga['prezzo_pubblico_inserito'] = upd.prezzo_pubblico

        db.execute("""
            UPDATE supervisione_prezzo
            SET righe_dettaglio_json = %s::jsonb
            WHERE id_supervisione = %s
        """, (json.dumps(righe_list), id_supervisione))

    db.commit()

    return {
        "success": True,
        "id_supervisione": id_supervisione,
        "righe_aggiornate": righe_aggiornate,
        "operatore": req.operatore
    }


@router.post("/{id_supervisione}/upload-listino", summary="Applica listino a righe")
async def upload_listino_prezzo(id_supervisione: int, operatore: str = Query(...)):
    """
    Applica prezzi dal listino vendor alle righe senza prezzo.

    Cerca automaticamente nel listino_vendor per ogni AIC e applica
    i prezzi trovati. Ritorna lista righe ancora senza prezzo.

    Args:
        id_supervisione: ID supervisione
        operatore: Nome operatore

    Returns:
        righe_aggiornate: Numero righe con prezzo applicato
        righe_mancanti: Lista righe ancora senza prezzo (AIC non in listino)
    """
    db = get_db()

    # Verifica supervisione
    sup = db.execute("""
        SELECT sp.*, ot.vendor
        FROM supervisione_prezzo sp
        JOIN ordini_testata ot ON sp.id_testata = ot.id_testata
        WHERE sp.id_supervisione = %s AND sp.stato = 'PENDING'
    """, (id_supervisione,)).fetchone()

    if not sup:
        raise HTTPException(status_code=404, detail="Supervisione non trovata o gia processata")

    sup = dict(sup)
    vendor = sup.get('vendor', '')

    # Parse righe
    righe_json = sup.get('righe_dettaglio_json')
    if not righe_json:
        return {"success": True, "righe_aggiornate": 0, "righe_mancanti": []}

    righe = json.loads(righe_json) if isinstance(righe_json, str) else righe_json

    righe_aggiornate = []
    righe_mancanti = []

    for riga in righe:
        aic = riga.get('codice_aic')
        id_det = riga.get('id_dettaglio')

        if not aic or not id_det:
            righe_mancanti.append(riga)
            continue

        # Cerca nel listino vendor
        listino = db.execute("""
            SELECT prezzo_netto, prezzo_pubblico
            FROM listini_vendor
            WHERE codice_aic = %s AND (vendor = %s OR vendor IS NULL) AND attivo = TRUE
            ORDER BY CASE WHEN vendor = %s THEN 0 ELSE 1 END
            LIMIT 1
        """, (aic, vendor, vendor)).fetchone()

        if listino:
            prezzo_netto = listino['prezzo_netto']
            prezzo_pubblico = listino['prezzo_pubblico']

            # Aggiorna riga
            db.execute("""
                UPDATE ordini_dettaglio
                SET prezzo_netto = %s,
                    prezzo_pubblico = %s,
                    valore_netto = %s * COALESCE(q_venduta, 0)
                WHERE id_dettaglio = %s
            """, (prezzo_netto, prezzo_pubblico, prezzo_netto, id_det))

            riga['prezzo_inserito'] = prezzo_netto
            riga['prezzo_pubblico_inserito'] = prezzo_pubblico
            righe_aggiornate.append(riga)
        else:
            righe_mancanti.append(riga)

    # Aggiorna JSON supervisione
    db.execute("""
        UPDATE supervisione_prezzo
        SET righe_dettaglio_json = %s::jsonb
        WHERE id_supervisione = %s
    """, (json.dumps(righe), id_supervisione))

    db.commit()

    # Se tutte le righe hanno prezzo, approva automaticamente
    if not righe_mancanti and righe_aggiornate:
        db.execute("""
            UPDATE supervisione_prezzo
            SET stato = 'APPROVED',
                operatore = %s,
                timestamp_decisione = CURRENT_TIMESTAMP,
                azione_correttiva = 'LISTINO_APPLICATO',
                note = 'Listino applicato automaticamente'
            WHERE id_supervisione = %s
        """, (operatore, id_supervisione))

        # Risolvi anomalia
        if sup.get('id_anomalia'):
            db.execute("""
                UPDATE anomalie
                SET stato = 'RISOLTA',
                    data_risoluzione = CURRENT_TIMESTAMP,
                    note_risoluzione = %s
                WHERE id_anomalia = %s
            """, (f"Listino applicato da {operatore}", sup['id_anomalia']))

        db.commit()

        # Sblocca ordine
        sblocca_ordine_se_completo(sup['id_testata'])

        return {
            "success": True,
            "auto_approvato": True,
            "righe_aggiornate": len(righe_aggiornate),
            "righe_mancanti": []
        }

    return {
        "success": True,
        "auto_approvato": False,
        "righe_aggiornate": len(righe_aggiornate),
        "righe_mancanti": righe_mancanti
    }


@router.post("/{id_supervisione}/approve", summary="Approva supervisione prezzo")
async def approva_prezzo(id_supervisione: int, req: ApprovaPrezzoRequest):
    """
    Approva supervisione prezzo con azione correttiva.

    Azioni possibili:
    - PREZZO_INSERITO: Prezzi inseriti manualmente
    - LISTINO_APPLICATO: Prezzi applicati da listino
    - ACCETTATO_SENZA_PREZZO: Ordine accettato senza prezzi (con giustificazione)
    - RIGHE_RIMOSSE: Righe senza prezzo rimosse dall'ordine

    Effetti:
    - Supervisione -> APPROVED
    - Anomalia -> RISOLTA
    - Ordine sbloccato se non ha altre supervisioni pending
    """
    db = get_db()

    # Verifica supervisione
    sup = db.execute("""
        SELECT * FROM supervisione_prezzo
        WHERE id_supervisione = %s AND stato = 'PENDING'
    """, (id_supervisione,)).fetchone()

    if not sup:
        raise HTTPException(status_code=404, detail="Supervisione non trovata o gia processata")

    sup = dict(sup)

    # Valida azione correttiva
    azioni_valide = ['PREZZO_INSERITO', 'LISTINO_APPLICATO', 'ACCETTATO_SENZA_PREZZO', 'RIGHE_RIMOSSE']
    if req.azione_correttiva not in azioni_valide:
        raise HTTPException(
            status_code=400,
            detail=f"Azione correttiva non valida. Valori ammessi: {', '.join(azioni_valide)}"
        )

    # =========================================================================
    # WORKFLOW: Propaga prezzi alle righe ordine
    # =========================================================================
    # Se l'azione è PREZZO_INSERITO o LISTINO_APPLICATO, applica i prezzi
    # dal righe_dettaglio_json alle righe in ordini_dettaglio
    righe_aggiornate = 0
    if req.azione_correttiva in ['PREZZO_INSERITO', 'LISTINO_APPLICATO']:
        righe_json = sup.get('righe_dettaglio_json')
        if righe_json:
            righe = json.loads(righe_json) if isinstance(righe_json, str) else righe_json

            for riga in righe:
                id_det = riga.get('id_dettaglio')
                prezzo_inserito = riga.get('prezzo_inserito')
                prezzo_pubblico = riga.get('prezzo_pubblico_inserito')

                if id_det and prezzo_inserito:
                    db.execute("""
                        UPDATE ordini_dettaglio
                        SET prezzo_netto = %s,
                            prezzo_pubblico = COALESCE(%s, prezzo_pubblico),
                            valore_netto = %s * COALESCE(q_venduta, 0)
                        WHERE id_dettaglio = %s
                    """, (prezzo_inserito, prezzo_pubblico, prezzo_inserito, id_det))
                    righe_aggiornate += 1

    # Aggiorna supervisione
    db.execute("""
        UPDATE supervisione_prezzo
        SET stato = 'APPROVED',
            operatore = %s,
            timestamp_decisione = CURRENT_TIMESTAMP,
            azione_correttiva = %s,
            note = %s
        WHERE id_supervisione = %s
    """, (req.operatore, req.azione_correttiva, req.note, id_supervisione))

    # Risolvi anomalia
    if sup.get('id_anomalia'):
        db.execute("""
            UPDATE anomalie
            SET stato = 'RISOLTA',
                data_risoluzione = CURRENT_TIMESTAMP,
                note_risoluzione = %s
            WHERE id_anomalia = %s
        """, (f"{req.azione_correttiva} da {req.operatore}. {req.note or ''}", sup['id_anomalia']))

    db.commit()

    # Sblocca ordine
    sblocca_ordine_se_completo(sup['id_testata'])

    return {
        "success": True,
        "id_supervisione": id_supervisione,
        "azione": "APPROVED",
        "azione_correttiva": req.azione_correttiva,
        "operatore": req.operatore
    }


@router.post("/{id_supervisione}/reject", summary="Rifiuta supervisione prezzo")
async def rifiuta_prezzo(id_supervisione: int, decisione: DecisioneRifiuta):
    """
    Rifiuta supervisione prezzo.

    Effetti:
    - Supervisione -> REJECTED
    - Ordine rimane bloccato
    """
    db = get_db()

    # Verifica supervisione
    sup = db.execute("""
        SELECT * FROM supervisione_prezzo
        WHERE id_supervisione = %s AND stato = 'PENDING'
    """, (id_supervisione,)).fetchone()

    if not sup:
        raise HTTPException(status_code=404, detail="Supervisione non trovata o gia processata")

    sup = dict(sup)

    # Aggiorna supervisione
    db.execute("""
        UPDATE supervisione_prezzo
        SET stato = 'REJECTED',
            operatore = %s,
            timestamp_decisione = CURRENT_TIMESTAMP,
            note = %s
        WHERE id_supervisione = %s
    """, (decisione.operatore, decisione.note, id_supervisione))

    # Aggiorna anomalia
    if sup.get('id_anomalia'):
        db.execute("""
            UPDATE anomalie
            SET stato = 'RIFIUTATA',
                data_risoluzione = CURRENT_TIMESTAMP,
                note_risoluzione = %s
            WHERE id_anomalia = %s
        """, (f"Rifiutata da {decisione.operatore}: {decisione.note}", sup['id_anomalia']))

    db.commit()

    return {
        "success": True,
        "id_supervisione": id_supervisione,
        "azione": "REJECTED",
        "operatore": decisione.operatore,
        "note": decisione.note
    }


@router.post("/riapplica-listino", summary="Riapplica listino a tutte le supervisioni pending")
async def riapplica_listino_bulk(operatore: str = Query(...)):
    """
    Riapplica prezzi dal listino a TUTTE le supervisioni prezzo pending.

    Utile dopo aver caricato un nuovo listino per risolvere automaticamente
    le supervisioni PRICE-A01 esistenti.

    Per ogni supervisione:
    1. Cerca prezzi nel listino per ogni AIC
    2. Applica prezzi trovati alle righe
    3. Se tutte le righe hanno prezzo → auto-approva
    4. Se rimangono righe senza prezzo → lascia pending

    Returns:
        - supervisioni_processate: Totale supervisioni elaborate
        - auto_approvate: Supervisioni risolte automaticamente
        - ancora_pending: Supervisioni con righe ancora senza prezzo
        - dettaglio: Lista per supervisione
    """
    db = get_db()

    # Recupera tutte le supervisioni prezzo pending
    # Nota: vendor è già in supervisione_prezzo, non serve JOIN
    supervisioni = db.execute("""
        SELECT * FROM supervisione_prezzo
        WHERE stato = 'PENDING'
        ORDER BY timestamp_creazione
    """).fetchall()

    risultati = {
        "supervisioni_processate": 0,
        "auto_approvate": 0,
        "ancora_pending": 0,
        "righe_aggiornate_totali": 0,
        "dettaglio": []
    }

    for sup in supervisioni:
        sup = dict(sup)
        id_supervisione = sup['id_supervisione']
        vendor = sup.get('vendor', '')

        # Parse righe
        righe_json = sup.get('righe_dettaglio_json')
        if not righe_json:
            continue

        righe = json.loads(righe_json) if isinstance(righe_json, str) else righe_json

        righe_aggiornate = 0
        righe_mancanti = 0

        for riga in righe:
            aic = riga.get('codice_aic')
            id_det = riga.get('id_dettaglio')

            if not aic or not id_det:
                righe_mancanti += 1
                continue

            # Salta se già ha un prezzo inserito
            if riga.get('prezzo_inserito'):
                continue

            # Cerca nel listino vendor
            listino = db.execute("""
                SELECT prezzo_netto, prezzo_pubblico
                FROM listini_vendor
                WHERE codice_aic = %s AND (vendor = %s OR vendor IS NULL) AND attivo = TRUE
                ORDER BY CASE WHEN vendor = %s THEN 0 ELSE 1 END
                LIMIT 1
            """, (aic, vendor, vendor)).fetchone()

            if listino:
                prezzo_netto = listino['prezzo_netto']
                prezzo_pubblico = listino['prezzo_pubblico']

                # Aggiorna riga ordine
                db.execute("""
                    UPDATE ordini_dettaglio
                    SET prezzo_netto = %s,
                        prezzo_pubblico = %s,
                        valore_netto = %s * COALESCE(q_venduta, 0)
                    WHERE id_dettaglio = %s
                """, (prezzo_netto, prezzo_pubblico, prezzo_netto, id_det))

                riga['prezzo_inserito'] = float(prezzo_netto) if prezzo_netto else 0
                riga['prezzo_pubblico_inserito'] = float(prezzo_pubblico) if prezzo_pubblico else 0
                righe_aggiornate += 1
            else:
                righe_mancanti += 1

        risultati["supervisioni_processate"] += 1
        risultati["righe_aggiornate_totali"] += righe_aggiornate

        # Aggiorna JSON supervisione
        db.execute("""
            UPDATE supervisione_prezzo
            SET righe_dettaglio_json = %s::jsonb
            WHERE id_supervisione = %s
        """, (json.dumps(righe), id_supervisione))

        # Se tutte le righe hanno prezzo, auto-approva
        if righe_mancanti == 0 and righe_aggiornate > 0:
            db.execute("""
                UPDATE supervisione_prezzo
                SET stato = 'APPROVED',
                    operatore = %s,
                    timestamp_decisione = CURRENT_TIMESTAMP,
                    azione_correttiva = 'LISTINO_APPLICATO',
                    note = 'Listino riapplicato automaticamente (bulk)'
                WHERE id_supervisione = %s
            """, (operatore, id_supervisione))

            # Risolvi anomalia
            if sup.get('id_anomalia'):
                db.execute("""
                    UPDATE anomalie
                    SET stato = 'RISOLTA',
                        data_risoluzione = CURRENT_TIMESTAMP,
                        note_risoluzione = %s
                    WHERE id_anomalia = %s
                """, (f"Listino bulk da {operatore}", sup['id_anomalia']))

            # Sblocca ordine
            sblocca_ordine_se_completo(sup['id_testata'])

            risultati["auto_approvate"] += 1
            risultati["dettaglio"].append({
                "id_supervisione": id_supervisione,
                "numero_ordine": sup.get('numero_ordine'),
                "esito": "AUTO_APPROVATA",
                "righe_aggiornate": righe_aggiornate
            })
        else:
            risultati["ancora_pending"] += 1
            risultati["dettaglio"].append({
                "id_supervisione": id_supervisione,
                "numero_ordine": sup.get('numero_ordine'),
                "esito": "ANCORA_PENDING",
                "righe_aggiornate": righe_aggiornate,
                "righe_mancanti": righe_mancanti
            })

    db.commit()

    return {
        "success": True,
        "operatore": operatore,
        **risultati
    }
