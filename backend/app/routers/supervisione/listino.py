# =============================================================================
# SERV.O v8.1 - SUPERVISIONE LISTINO
# =============================================================================
# Endpoint per gestione supervisione listini e correzione prezzi
# =============================================================================

from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from ...database_pg import get_db
from ...services.supervision.requests import _calcola_pattern_signature_listino
from ...services.supervisione import sblocca_ordine_se_completo
from .schemas import CorrezioneListinoRequest, ArchiviazioneListinoRequest


router = APIRouter(prefix="/listino", tags=["Supervisione Listino"])


# =============================================================================
# ENDPOINT SUPERVISIONE LISTINO
# =============================================================================

@router.get("/{id_supervisione}", summary="Dettaglio supervisione listino")
async def get_supervisione_listino_detail(id_supervisione: int):
    """
    Ritorna dettagli completi di una supervisione listino.

    Include:
    - Dati anomalia (AIC, descrizione, vendor)
    - Dati riga ordine corrente
    - Pattern esistenti per lo stesso AIC
    - Suggerimenti prezzo da altre fonti
    """
    db = get_db()

    # Recupera supervisione con dati ordine
    row = db.execute("""
        SELECT sl.*,
               od.descrizione AS descrizione_riga,
               od.q_venduta, od.prezzo_netto AS prezzo_netto_attuale,
               od.prezzo_pubblico AS prezzo_pubblico_attuale,
               od.sconto_1 AS sconto_1_attuale, od.sconto_2 AS sconto_2_attuale,
               od.sconto_3 AS sconto_3_attuale, od.sconto_4 AS sconto_4_attuale,
               od.aliquota_iva AS aliquota_iva_attuale,
               ot.numero_ordine_vendor, ot.ragione_sociale_1,
               col.count_approvazioni AS pattern_count,
               col.is_ordinario AS pattern_ordinario,
               col.prezzo_netto_pattern, col.sconto_1_pattern, col.sconto_2_pattern
        FROM supervisione_listino sl
        LEFT JOIN ordini_dettaglio od ON sl.id_dettaglio = od.id_dettaglio
        LEFT JOIN ordini_testata ot ON sl.id_testata = ot.id_testata
        LEFT JOIN criteri_ordinari_listino col ON sl.pattern_signature = col.pattern_signature
        WHERE sl.id_supervisione = %s
    """, (id_supervisione,)).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Supervisione listino non trovata")

    result = dict(row)

    # Cerca prezzi in altri listini o ordini precedenti
    if result.get('codice_aic'):
        # Cerca nel listino vendor
        listino_row = db.execute("""
            SELECT prezzo_netto, prezzo_pubblico, sconto_1, sconto_2, aliquota_iva
            FROM listini_vendor
            WHERE codice_aic = %s AND attivo = TRUE
            LIMIT 1
        """, (result['codice_aic'],)).fetchone()

        if listino_row:
            result['suggerimento_listino'] = dict(listino_row)

        # Cerca in ordini precedenti con stesso AIC e prezzi compilati
        ordini_prec = db.execute("""
            SELECT prezzo_netto, prezzo_pubblico, sconto_1, sconto_2, aliquota_iva,
                   COUNT(*) as occorrenze
            FROM ordini_dettaglio
            WHERE codice_aic = %s AND prezzo_netto > 0
            GROUP BY prezzo_netto, prezzo_pubblico, sconto_1, sconto_2, aliquota_iva
            ORDER BY occorrenze DESC
            LIMIT 3
        """, (result['codice_aic'],)).fetchall()

        if ordini_prec:
            result['suggerimenti_storici'] = [dict(r) for r in ordini_prec]

    return result


@router.post("/{id_supervisione}/correggi", summary="Correggi prezzi listino")
async def correggi_listino(id_supervisione: int, req: CorrezioneListinoRequest):
    """
    Corregge i prezzi di una riga con anomalia listino.

    Effetti:
    - Aggiorna prezzi/sconti nella riga ordine
    - Marca supervisione come CORRETTA
    - Se applica_a_listino=True, aggiunge AIC al listino vendor
    - Incrementa pattern per apprendimento automatico
    """
    db = get_db()

    # Recupera supervisione
    sup = db.execute("""
        SELECT sl.*, od.id_dettaglio, od.codice_aic
        FROM supervisione_listino sl
        LEFT JOIN ordini_dettaglio od ON sl.id_dettaglio = od.id_dettaglio
        WHERE sl.id_supervisione = %s AND sl.stato = 'PENDING'
    """, (id_supervisione,)).fetchone()

    if not sup:
        raise HTTPException(status_code=404, detail="Supervisione non trovata o gia processata")

    sup = dict(sup)

    # Costruisci aggiornamenti per la riga
    updates = []
    params = []

    if req.descrizione is not None:
        updates.append("descrizione_prodotto = %s")
        params.append(req.descrizione)
    if req.prezzo_netto is not None:
        updates.append("prezzo_netto = %s")
        params.append(req.prezzo_netto)
    if req.prezzo_pubblico is not None:
        updates.append("prezzo_pubblico = %s")
        params.append(req.prezzo_pubblico)
    if req.prezzo_scontare is not None:
        updates.append("prezzo_scontare = %s")
        params.append(req.prezzo_scontare)
    if req.sconto_1 is not None:
        updates.append("sconto_1 = %s")
        params.append(req.sconto_1)
    if req.sconto_2 is not None:
        updates.append("sconto_2 = %s")
        params.append(req.sconto_2)
    if req.sconto_3 is not None:
        updates.append("sconto_3 = %s")
        params.append(req.sconto_3)
    if req.sconto_4 is not None:
        updates.append("sconto_4 = %s")
        params.append(req.sconto_4)
    if req.aliquota_iva is not None:
        updates.append("aliquota_iva = %s")
        params.append(req.aliquota_iva)
    if req.scorporo_iva is not None:
        updates.append("scorporo_iva = %s")
        params.append(req.scorporo_iva)

    # Marca come modificato manualmente e confermato
    updates.append("stato_riga = 'CONFERMATO'")
    updates.append("modificato_manualmente = TRUE")
    updates.append("confermato_da = %s")
    params.append(req.operatore)
    updates.append("data_conferma = CURRENT_TIMESTAMP")

    if updates and sup.get('id_dettaglio'):
        params.append(sup['id_dettaglio'])
        # v9.1: ESCLUDI righe ARCHIVIATO - stato finale immutabile
        db.execute(f"""
            UPDATE ordini_dettaglio
            SET {', '.join(updates)}
            WHERE id_dettaglio = %s
              AND stato_riga != 'ARCHIVIATO'
        """, tuple(params))

    # Aggiorna supervisione
    # NOTA: supervisione_listino ha solo prezzo_proposto, non sconto_X_proposto
    db.execute("""
        UPDATE supervisione_listino
        SET stato = 'CORRETTA',
            azione = 'CORREGGI',
            operatore = %s,
            timestamp_decisione = CURRENT_TIMESTAMP,
            note = %s,
            prezzo_proposto = %s
        WHERE id_supervisione = %s
    """, (req.operatore, req.note, req.prezzo_netto, id_supervisione))

    # Se richiesto, aggiungi al listino vendor
    if req.applica_a_listino and sup.get('codice_aic') and sup.get('vendor'):
        descrizione = req.descrizione or sup.get('descrizione_prodotto', '')
        db.execute("""
            INSERT INTO listini_vendor (
                vendor, codice_aic, descrizione,
                prezzo_netto, prezzo_pubblico, prezzo_scontare,
                sconto_1, sconto_2, sconto_3, sconto_4,
                aliquota_iva, scorporo_iva, data_decorrenza, fonte_file
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'CORREZIONE_MANUALE')
            ON CONFLICT (vendor, codice_aic) DO UPDATE SET
                descrizione = COALESCE(EXCLUDED.descrizione, listini_vendor.descrizione),
                prezzo_netto = EXCLUDED.prezzo_netto,
                prezzo_pubblico = EXCLUDED.prezzo_pubblico,
                prezzo_scontare = EXCLUDED.prezzo_scontare,
                sconto_1 = EXCLUDED.sconto_1,
                sconto_2 = EXCLUDED.sconto_2,
                sconto_3 = EXCLUDED.sconto_3,
                sconto_4 = EXCLUDED.sconto_4,
                aliquota_iva = EXCLUDED.aliquota_iva,
                scorporo_iva = EXCLUDED.scorporo_iva,
                data_decorrenza = EXCLUDED.data_decorrenza,
                data_import = CURRENT_TIMESTAMP
        """, (
            sup['vendor'], sup['codice_aic'], descrizione,
            req.prezzo_netto, req.prezzo_pubblico, req.prezzo_scontare,
            req.sconto_1, req.sconto_2, req.sconto_3, req.sconto_4,
            req.aliquota_iva, req.scorporo_iva, req.data_decorrenza
        ))

    # Aggiorna/crea pattern per apprendimento
    pattern_sig = _calcola_pattern_signature_listino(
        sup.get('vendor', ''),
        sup.get('codice_anomalia', ''),
        sup.get('codice_aic', '')
    )
    pattern_descrizione = req.descrizione or sup.get('descrizione_prodotto', '')

    db.execute("""
        INSERT INTO criteri_ordinari_listino
            (pattern_signature, pattern_descrizione, vendor, codice_anomalia, codice_aic,
             count_approvazioni, prezzo_netto_pattern, sconto_1_pattern, sconto_2_pattern,
             prezzo_pubblico_pattern, aliquota_iva_pattern, azione_pattern)
        VALUES (%s, %s, %s, %s, %s, 1, %s, %s, %s, %s, %s, 'CORREGGI')
        ON CONFLICT (pattern_signature) DO UPDATE SET
            count_approvazioni = criteri_ordinari_listino.count_approvazioni + 1,
            prezzo_netto_pattern = EXCLUDED.prezzo_netto_pattern,
            sconto_1_pattern = EXCLUDED.sconto_1_pattern,
            sconto_2_pattern = EXCLUDED.sconto_2_pattern,
            is_ordinario = CASE WHEN criteri_ordinari_listino.count_approvazioni >= 4 THEN TRUE ELSE FALSE END,
            data_promozione = CASE WHEN criteri_ordinari_listino.count_approvazioni >= 4 THEN CURRENT_TIMESTAMP ELSE NULL END
    """, (pattern_sig, f"AIC {sup.get('codice_aic')} - {pattern_descrizione}",
          sup.get('vendor', ''), sup.get('codice_anomalia', ''), sup.get('codice_aic', ''),
          req.prezzo_netto, req.sconto_1, req.sconto_2, req.prezzo_pubblico, req.aliquota_iva))

    # Risolvi anomalia
    db.execute("""
        UPDATE anomalie
        SET stato = 'RISOLTA',
            data_risoluzione = CURRENT_TIMESTAMP,
            note_risoluzione = %s
        WHERE id_anomalia = %s
    """, (f"Correzione manuale da {req.operatore}", sup.get('id_anomalia')))

    # Se aggiunto al listino, correggi TUTTE le supervisioni pending con stesso AIC/vendor
    ordini_aggiornati = [sup['id_testata']]
    if req.applica_a_listino and sup.get('codice_aic') and sup.get('vendor'):
        altre_sup = db.execute("""
            SELECT sl.id_supervisione, sl.id_testata, sl.id_anomalia, sl.id_dettaglio
            FROM supervisione_listino sl
            WHERE sl.codice_aic = %s AND sl.vendor = %s
              AND sl.stato = 'PENDING' AND sl.id_supervisione != %s
        """, (sup['codice_aic'], sup['vendor'], id_supervisione)).fetchall()

        for altra in altre_sup:
            # Aggiorna supervisione
            db.execute("""
                UPDATE supervisione_listino
                SET stato = 'CORRETTA', azione = 'CORREGGI_BULK',
                    operatore = %s, timestamp_decisione = CURRENT_TIMESTAMP,
                    note = %s
                WHERE id_supervisione = %s
            """, (req.operatore, f"Correzione automatica da listino (AIC {sup['codice_aic']})", altra[0]))

            # Aggiorna riga ordine se esiste
            # v9.1: ESCLUDI righe ARCHIVIATO - stato finale immutabile
            if altra[3]:  # id_dettaglio
                db.execute("""
                    UPDATE ordini_dettaglio
                    SET stato_riga = 'CONFERMATO',
                        prezzo_netto = COALESCE(%s, prezzo_netto),
                        prezzo_pubblico = COALESCE(%s, prezzo_pubblico),
                        modificato_manualmente = TRUE,
                        confermato_da = %s,
                        data_conferma = CURRENT_TIMESTAMP
                    WHERE id_dettaglio = %s
                      AND stato_riga != 'ARCHIVIATO'
                """, (req.prezzo_netto, req.prezzo_pubblico, req.operatore, altra[3]))

            # Risolvi anomalia collegata
            if altra[2]:  # id_anomalia
                db.execute("""
                    UPDATE anomalie
                    SET stato = 'RISOLTA', data_risoluzione = CURRENT_TIMESTAMP,
                        note_risoluzione = %s
                    WHERE id_anomalia = %s
                """, (f"Correzione automatica da listino ({req.operatore})", altra[2]))

            if altra[1] not in ordini_aggiornati:
                ordini_aggiornati.append(altra[1])

    db.commit()

    # Sblocca tutti gli ordini aggiornati
    for id_ord in ordini_aggiornati:
        sblocca_ordine_se_completo(id_ord)

    return {
        "success": True,
        "id_supervisione": id_supervisione,
        "azione": "CORRETTA",
        "operatore": req.operatore,
        "aggiunto_a_listino": req.applica_a_listino,
        "pattern_signature": pattern_sig
    }


@router.post("/{id_supervisione}/archivia", summary="Archivia riga listino")
async def archivia_listino(id_supervisione: int, req: ArchiviazioneListinoRequest):
    """
    Archivia una riga con anomalia listino (esclude da export).

    Usare quando la riga non deve essere inclusa nel tracciato finale
    (es: prodotto non gestito, errore estrazione, etc.)

    Effetti:
    - Marca riga come ARCHIVIATA (esclusa da export)
    - Marca supervisione come ARCHIVIATA
    - Crea pattern se archiviazione ricorrente per stesso AIC
    """
    db = get_db()

    # Recupera supervisione
    sup = db.execute("""
        SELECT sl.*, od.id_dettaglio
        FROM supervisione_listino sl
        LEFT JOIN ordini_dettaglio od ON sl.id_dettaglio = od.id_dettaglio
        WHERE sl.id_supervisione = %s AND sl.stato = 'PENDING'
    """, (id_supervisione,)).fetchone()

    if not sup:
        raise HTTPException(status_code=404, detail="Supervisione non trovata o gia processata")

    sup = dict(sup)

    # Archivia la riga ordine
    if sup.get('id_dettaglio'):
        db.execute("""
            UPDATE ordini_dettaglio
            SET stato_riga = 'ARCHIVIATO',
                note_supervisione = %s,
                confermato_da = %s,
                data_conferma = CURRENT_TIMESTAMP,
                q_da_evadere = 0
            WHERE id_dettaglio = %s
        """, (f"Archiviato: {req.motivo}", req.operatore, sup['id_dettaglio']))

    # Aggiorna supervisione
    db.execute("""
        UPDATE supervisione_listino
        SET stato = 'ARCHIVIATA',
            azione = 'ARCHIVIA',
            operatore = %s,
            timestamp_decisione = CURRENT_TIMESTAMP,
            note = %s
        WHERE id_supervisione = %s
    """, (req.operatore, f"{req.motivo}. {req.note or ''}", id_supervisione))

    # Crea/aggiorna pattern per archiviazione
    pattern_sig = _calcola_pattern_signature_listino(
        sup.get('vendor', ''),
        sup.get('codice_anomalia', '') + '_ARCH',
        sup.get('codice_aic', '')
    )

    db.execute("""
        INSERT INTO criteri_ordinari_listino
            (pattern_signature, pattern_descrizione, vendor, codice_anomalia, codice_aic,
             count_approvazioni, azione_pattern)
        VALUES (%s, %s, %s, %s, %s, 1, 'ARCHIVIA')
        ON CONFLICT (pattern_signature) DO UPDATE SET
            count_approvazioni = criteri_ordinari_listino.count_approvazioni + 1,
            is_ordinario = CASE WHEN criteri_ordinari_listino.count_approvazioni >= 4 THEN TRUE ELSE FALSE END,
            data_promozione = CASE WHEN criteri_ordinari_listino.count_approvazioni >= 4 THEN CURRENT_TIMESTAMP ELSE NULL END
    """, (pattern_sig, f"Archivia AIC {sup.get('codice_aic')} - {req.motivo}",
          sup.get('vendor', ''), sup.get('codice_anomalia', ''), sup.get('codice_aic', '')))

    # Risolvi anomalia
    db.execute("""
        UPDATE anomalie
        SET stato = 'RISOLTA',
            data_risoluzione = CURRENT_TIMESTAMP,
            note_risoluzione = %s
        WHERE id_anomalia = %s
    """, (f"Archiviata da {req.operatore}: {req.motivo}", sup.get('id_anomalia')))

    db.commit()

    # Sblocca ordine se tutte le supervisioni sono state gestite
    sblocca_ordine_se_completo(sup['id_testata'])

    return {
        "success": True,
        "id_supervisione": id_supervisione,
        "azione": "ARCHIVIATA",
        "operatore": req.operatore,
        "motivo": req.motivo,
        "pattern_signature": pattern_sig
    }


@router.get("/pattern/{codice_aic}", summary="Pattern per AIC")
async def get_pattern_listino(codice_aic: str, vendor: Optional[str] = None):
    """
    Ritorna pattern appresi per un codice AIC.

    Usato per suggerire automaticamente correzioni basate su decisioni precedenti.
    """
    db = get_db()

    query = """
        SELECT * FROM criteri_ordinari_listino
        WHERE codice_aic = %s
    """
    params = [codice_aic]

    if vendor:
        query += " AND vendor = %s"
        params.append(vendor)

    query += " ORDER BY count_approvazioni DESC"

    rows = db.execute(query, tuple(params)).fetchall()

    return {
        "codice_aic": codice_aic,
        "count": len(rows),
        "patterns": [dict(r) for r in rows]
    }


# =============================================================================
# v10.0: RIAPPLICA LISTINO BULK PER SUPERVISIONI LST-A01
# =============================================================================

@router.post("/riapplica-listino", summary="Riapplica listino a supervisioni LST pending")
async def riapplica_listino_bulk(operatore: str = Query(..., description="Username operatore")):
    """
    Riapplica prezzi dal listino a TUTTE le supervisioni listino (LST-A01) pending.

    Utile dopo aver caricato un nuovo listino per risolvere automaticamente
    le supervisioni LST-A01 esistenti per DOC_GENERICI e altri vendor.

    Per ogni supervisione:
    1. Cerca prezzi nel listino generale per l'AIC
    2. Applica prezzi trovati alla riga ordine
    3. Se prezzo trovato → auto-approva supervisione
    4. Se prezzo non trovato → lascia pending

    Returns:
        - supervisioni_processate: Totale supervisioni elaborate
        - auto_approvate: Supervisioni risolte automaticamente
        - ancora_pending: Supervisioni ancora senza prezzo nel listino
    """
    db = get_db()

    # Recupera tutte le supervisioni listino pending
    # NOTA: Usa COALESCE per codice_aic perché se sl.id_dettaglio è NULL,
    # la LEFT JOIN non trova match e od.codice_aic sarebbe NULL.
    # sl.codice_aic contiene sempre il valore corretto dalla supervisione.
    supervisioni = db.execute("""
        SELECT sl.*,
               od.id_dettaglio AS od_id_dettaglio,
               COALESCE(od.codice_aic, sl.codice_aic) AS codice_aic,
               od.descrizione AS od_descrizione
        FROM supervisione_listino sl
        LEFT JOIN ordini_dettaglio od ON sl.id_dettaglio = od.id_dettaglio
        WHERE sl.stato = 'PENDING'
        ORDER BY sl.timestamp_creazione
    """).fetchall()

    risultati = {
        "supervisioni_processate": 0,
        "auto_approvate": 0,
        "ancora_pending": 0,
        "dettaglio": []
    }

    righe_aggiornate = 0

    for sup in supervisioni:
        sup = dict(sup)
        id_supervisione = sup['id_supervisione']
        codice_aic = sup.get('codice_aic')
        id_testata = sup.get('id_testata')
        # Preferisci od_id_dettaglio (dalla JOIN), fallback su sl.id_dettaglio
        id_dettaglio = sup.get('od_id_dettaglio') or sup.get('id_dettaglio')

        if not codice_aic:
            risultati["ancora_pending"] += 1
            continue

        # Se non abbiamo id_dettaglio, proviamo a trovarlo via id_testata + codice_aic
        if not id_dettaglio and id_testata and codice_aic:
            det_row = db.execute("""
                SELECT id_dettaglio FROM ordini_dettaglio
                WHERE id_testata = %s AND codice_aic = %s
                LIMIT 1
            """, (id_testata, codice_aic)).fetchone()
            if det_row:
                id_dettaglio = det_row['id_dettaglio']

        risultati["supervisioni_processate"] += 1

        # Cerca nel listino generale (senza filtro vendor)
        listino = db.execute("""
            SELECT prezzo_netto, prezzo_pubblico, prezzo_scontare,
                   sconto_1, sconto_2, sconto_3, sconto_4, aliquota_iva, scorporo_iva
            FROM listini_vendor
            WHERE codice_aic = %s AND attivo = TRUE
            ORDER BY data_import DESC
            LIMIT 1
        """, (codice_aic,)).fetchone()

        if listino:
            listino = dict(listino)

            # Aggiorna riga ordine con prezzi dal listino (senza confermare)
            if id_dettaglio:
                cursor = db.execute("""
                    UPDATE ordini_dettaglio
                    SET prezzo_netto = COALESCE(%s, prezzo_netto),
                        prezzo_pubblico = COALESCE(%s, prezzo_pubblico),
                        prezzo_scontare = COALESCE(%s, prezzo_scontare),
                        sconto_1 = COALESCE(%s, sconto_1),
                        sconto_2 = COALESCE(%s, sconto_2),
                        sconto_3 = COALESCE(%s, sconto_3),
                        sconto_4 = COALESCE(%s, sconto_4),
                        aliquota_iva = COALESCE(%s, aliquota_iva),
                        scorporo_iva = COALESCE(%s, scorporo_iva)
                    WHERE id_dettaglio = %s
                """, (
                    listino.get('prezzo_netto'), listino.get('prezzo_pubblico'),
                    listino.get('prezzo_scontare'),
                    listino.get('sconto_1'), listino.get('sconto_2'),
                    listino.get('sconto_3'), listino.get('sconto_4'),
                    listino.get('aliquota_iva'), listino.get('scorporo_iva'),
                    id_dettaglio
                ))
                righe_aggiornate += cursor.rowcount

            # Auto-approva supervisione
            db.execute("""
                UPDATE supervisione_listino
                SET stato = 'CORRETTA',
                    azione = 'CORREGGI_BULK',
                    operatore = %s,
                    timestamp_decisione = CURRENT_TIMESTAMP,
                    note = 'Listino riapplicato automaticamente (bulk)',
                    prezzo_proposto = %s
                WHERE id_supervisione = %s
            """, (operatore, listino.get('prezzo_netto'), id_supervisione))

            # Risolvi anomalia collegata
            if sup.get('id_anomalia'):
                db.execute("""
                    UPDATE anomalie
                    SET stato = 'RISOLTA',
                        data_risoluzione = CURRENT_TIMESTAMP,
                        note_risoluzione = %s
                    WHERE id_anomalia = %s
                """, (f"Listino bulk da {operatore}", sup['id_anomalia']))

            # Sblocca ordine se tutte le supervisioni sono state gestite
            sblocca_ordine_se_completo(sup['id_testata'])

            risultati["auto_approvate"] += 1
            risultati["dettaglio"].append({
                "id_supervisione": id_supervisione,
                "codice_aic": codice_aic,
                "esito": "AUTO_APPROVATA",
                "prezzo_applicato": listino.get('prezzo_netto')
            })
        else:
            risultati["ancora_pending"] += 1
            risultati["dettaglio"].append({
                "id_supervisione": id_supervisione,
                "codice_aic": codice_aic,
                "esito": "ANCORA_PENDING",
                "motivo": "AIC non trovato nel listino"
            })

    db.commit()

    return {
        "success": True,
        "operatore": operatore,
        "righe_aggiornate": righe_aggiornate,
        **risultati
    }
