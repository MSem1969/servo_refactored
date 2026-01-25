# =============================================================================
# SERV.O v10.1 - ANOMALIES COMMANDS
# =============================================================================
# Command functions for anomaly mutations
# =============================================================================

from typing import Dict, Any, List, Optional
from ...database_pg import get_db


def create_anomalia(
    id_testata: int = None,
    id_dettaglio: int = None,
    id_acquisizione: int = None,
    tipo: str = 'ALTRO',
    codice: str = None,
    livello: str = 'ATTENZIONE',
    descrizione: str = '',
    dati_originali: Dict = None,
    valore_anomalo: str = None
) -> int:
    """
    Crea nuova anomalia con deduplicazione automatica.

    v10.5: Verifica se esiste già un'anomalia identica (stesso ordine/riga/codice)
    ancora aperta. Se esiste, ritorna l'ID esistente senza creare duplicati.

    Args:
        id_testata: ID ordine (opzionale)
        id_dettaglio: ID riga dettaglio (opzionale)
        id_acquisizione: ID acquisizione (opzionale)
        tipo: Tipo anomalia (LOOKUP, ESPOSITORE, LISTINO, VALIDAZIONE, etc.)
        codice: Codice anomalia (es. ESP-A01, LKP-A02)
        livello: Livello gravità (INFO, ATTENZIONE, ERRORE, CRITICO)
        descrizione: Descrizione testuale
        dati_originali: JSON con dati originali
        valore_anomalo: Valore che ha causato l'anomalia

    Returns:
        ID della nuova anomalia (o esistente se duplicato)
    """
    db = get_db()

    # v10.5: Deduplicazione - cerca anomalia identica già aperta
    if codice:
        existing = _find_existing_anomaly(
            db, id_testata, id_dettaglio, id_acquisizione, codice
        )
        if existing:
            # Anomalia già esistente, ritorna ID senza creare duplicato
            return existing

    import json
    dati_json = json.dumps(dati_originali) if dati_originali else None

    cursor = db.execute("""
        INSERT INTO ANOMALIE
        (id_testata, id_dettaglio, id_acquisizione, tipo_anomalia,
         codice, livello, descrizione, dati_originali, valore_anomalo, stato)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'APERTA')
        RETURNING id_anomalia
    """, (id_testata, id_dettaglio, id_acquisizione, tipo,
          codice, livello, descrizione, dati_json, valore_anomalo))

    result = cursor.fetchone()
    db.commit()

    # Aggiorna stato ordine se necessario
    if id_testata and livello in ('ERRORE', 'CRITICO'):
        _update_ordine_stato_anomalia(id_testata)

    return result[0] if result else None


def _find_existing_anomaly(
    db,
    id_testata: int,
    id_dettaglio: int,
    id_acquisizione: int,
    codice: str
) -> Optional[int]:
    """
    v10.5: Cerca anomalia esistente con stessi parametri chiave.

    Cerca anomalie APERTE o IN_GESTIONE con stesso:
    - id_testata (o entrambi NULL)
    - id_dettaglio (o entrambi NULL)
    - id_acquisizione (o entrambi NULL)
    - codice anomalia

    Returns:
        ID anomalia esistente o None
    """
    # Costruisci query dinamica per gestire NULL correttamente
    conditions = ["codice = %s", "stato IN ('APERTA', 'IN_GESTIONE')"]
    params = [codice]

    if id_testata is not None:
        conditions.append("id_testata = %s")
        params.append(id_testata)
    else:
        conditions.append("id_testata IS NULL")

    if id_dettaglio is not None:
        conditions.append("id_dettaglio = %s")
        params.append(id_dettaglio)
    else:
        conditions.append("id_dettaglio IS NULL")

    if id_acquisizione is not None:
        conditions.append("id_acquisizione = %s")
        params.append(id_acquisizione)
    else:
        conditions.append("id_acquisizione IS NULL")

    query = f"""
        SELECT id_anomalia FROM anomalie
        WHERE {' AND '.join(conditions)}
        ORDER BY data_rilevazione DESC
        LIMIT 1
    """

    result = db.execute(query, params).fetchone()
    return result['id_anomalia'] if result else None


def update_anomalia_stato(
    id_anomalia: int,
    nuovo_stato: str,
    note: str = None,
    operatore: str = None,
    ruolo: str = None
) -> bool:
    """
    Aggiorna stato anomalia con gestione ruoli per supervisioni.

    v11.2: Gestione ruoli per risoluzione supervisioni:
    - SUPERVISORE/ADMIN → risolve anomalia + supervisione collegata
    - OPERATORE → risolve anomalia ma supervisione resta PENDING

    Args:
        id_anomalia: ID anomalia
        nuovo_stato: Nuovo stato (APERTA, IN_GESTIONE, RISOLTA, IGNORATA)
        note: Note risoluzione
        operatore: Username operatore (opzionale)
        ruolo: Ruolo operatore (operatore/supervisore/admin) - determina se aggiornare supervisioni

    Returns:
        True se aggiornato con successo
    """
    stati_validi = ['APERTA', 'IN_GESTIONE', 'RISOLTA', 'IGNORATA']
    if nuovo_stato not in stati_validi:
        return False

    # v11.2: Determina se l'utente può risolvere supervisioni
    ruoli_supervisione = ['supervisore', 'admin']
    puo_risolvere_supervisioni = ruolo and ruolo.lower() in ruoli_supervisione

    db = get_db()

    # Recupera info anomalia
    anomalia = db.execute(
        "SELECT tipo_anomalia, id_testata FROM anomalie WHERE id_anomalia = %s",
        (id_anomalia,)
    ).fetchone()

    if not anomalia:
        return False

    # Aggiorna stato
    # NOTA: id_operatore_gestione è INTEGER, operatore è username string
    # Includiamo l'operatore nella nota invece di usare la colonna FK
    if nuovo_stato in ('RISOLTA', 'IGNORATA'):
        nota_anomalia = f"Operatore: {operatore} ({ruolo or 'N/D'}) - {note or ''}"
        db.execute("""
            UPDATE anomalie
            SET stato = %s,
                data_risoluzione = CURRENT_TIMESTAMP,
                note_risoluzione = %s
            WHERE id_anomalia = %s
        """, (nuovo_stato, nota_anomalia, id_anomalia))

        # v11.2: Aggiorna supervisioni SOLO se SUPERVISORE o ADMIN
        if puo_risolvere_supervisioni:
            # v10.4: Recupera pattern signatures PRIMA di aggiornare (per ML learning)
            sup_esp = db.execute("""
                SELECT pattern_signature FROM supervisione_espositore
                WHERE id_anomalia = %s AND stato = 'PENDING'
            """, (id_anomalia,)).fetchall()

            sup_lst = db.execute("""
                SELECT pattern_signature FROM supervisione_listino
                WHERE id_anomalia = %s AND stato = 'PENDING'
            """, (id_anomalia,)).fetchall()

            sup_lkp = db.execute("""
                SELECT pattern_signature FROM supervisione_lookup
                WHERE id_anomalia = %s AND stato = 'PENDING'
            """, (id_anomalia,)).fetchall()

            sup_aic = db.execute("""
                SELECT pattern_signature, codice_aic_assegnato FROM supervisione_aic
                WHERE id_anomalia = %s AND stato = 'PENDING'
            """, (id_anomalia,)).fetchall()

            # Aggiorna supervisioni collegate su TUTTE le tabelle
            sup_stato = 'APPROVED' if nuovo_stato == 'RISOLTA' else 'REJECTED'
            nota_sup = f'Risolto da anomalia ({ruolo}): {note or ""}'

            db.execute("""
                UPDATE supervisione_espositore
                SET stato = %s,
                    operatore = %s,
                    timestamp_decisione = CURRENT_TIMESTAMP,
                    note = COALESCE(note || ' - ', '') || %s
                WHERE id_anomalia = %s AND stato = 'PENDING'
            """, (sup_stato, operatore, nota_sup, id_anomalia))

            db.execute("""
                UPDATE supervisione_listino
                SET stato = %s,
                    operatore = %s,
                    timestamp_decisione = CURRENT_TIMESTAMP,
                    note = COALESCE(note || ' - ', '') || %s
                WHERE id_anomalia = %s AND stato = 'PENDING'
            """, (sup_stato, operatore, nota_sup, id_anomalia))

            db.execute("""
                UPDATE supervisione_lookup
                SET stato = %s,
                    operatore = %s,
                    timestamp_decisione = CURRENT_TIMESTAMP,
                    note = COALESCE(note || ' - ', '') || %s
                WHERE id_anomalia = %s AND stato = 'PENDING'
            """, (sup_stato, operatore, nota_sup, id_anomalia))

            db.execute("""
                UPDATE supervisione_aic
                SET stato = %s,
                    operatore = %s,
                    timestamp_decisione = CURRENT_TIMESTAMP,
                    note = COALESCE(note || ' - ', '') || %s
                WHERE id_anomalia = %s AND stato = 'PENDING'
            """, (sup_stato, operatore, nota_sup, id_anomalia))

            db.commit()

            # v10.4: Registra approvazioni pattern ML (solo se RISOLTA)
            # IMPORTANTE: Deduplica pattern per evitare conteggi multipli
            if nuovo_stato == 'RISOLTA':
                from ..supervision.ml import registra_approvazione_pattern, registra_approvazione_pattern_listino
                from ..supervision.lookup import registra_approvazione_pattern_lookup
                from ..supervision.aic import _registra_approvazione_pattern_aic

                # Deduplica pattern signatures
                seen_esp = set()
                for row in sup_esp:
                    ps = row['pattern_signature']
                    if ps and ps not in seen_esp:
                        seen_esp.add(ps)
                        registra_approvazione_pattern(ps, operatore)

                seen_lst = set()
                for row in sup_lst:
                    ps = row['pattern_signature']
                    if ps and ps not in seen_lst:
                        seen_lst.add(ps)
                        registra_approvazione_pattern_listino(ps, operatore)

                seen_lkp = set()
                for row in sup_lkp:
                    ps = row['pattern_signature']
                    if ps and ps not in seen_lkp:
                        seen_lkp.add(ps)
                        registra_approvazione_pattern_lookup(ps, operatore)

                seen_aic = set()
                for row in sup_aic:
                    ps = row['pattern_signature']
                    aic = row.get('codice_aic_assegnato')
                    if ps and aic and ps not in seen_aic:
                        seen_aic.add(ps)
                        _registra_approvazione_pattern_aic(ps, operatore, aic)
        else:
            # OPERATORE: solo commit anomalia, supervisioni restano PENDING
            db.commit()

    else:
        # NOTA: id_operatore_gestione è INTEGER - non possiamo inserire username
        db.execute(
            "UPDATE anomalie SET stato = %s WHERE id_anomalia = %s",
            (nuovo_stato, id_anomalia)
        )
        db.commit()

    # Sblocca ordine se tutte le anomalie sono risolte
    if nuovo_stato in ('RISOLTA', 'IGNORATA') and anomalia['id_testata']:
        _sblocca_ordine_se_possibile(anomalia['id_testata'])

    return True


def resolve_anomalia(
    id_anomalia: int,
    operatore: str,
    note: str = None,
    dati_corretti: Dict = None,
    ruolo: str = None
) -> bool:
    """
    Risolve un'anomalia con dati corretti opzionali.

    v11.2: Aggiunto ruolo per gestione supervisioni.
    - SUPERVISORE/ADMIN → risolve anomalia + supervisione collegata
    - OPERATORE → risolve anomalia ma supervisione resta PENDING

    Args:
        id_anomalia: ID anomalia
        operatore: Username operatore
        note: Note risoluzione
        dati_corretti: Dati corretti (JSON)
        ruolo: Ruolo operatore (per risoluzione supervisioni)

    Returns:
        True se risolto con successo
    """
    # v11.2: Determina se l'utente può risolvere supervisioni
    ruoli_supervisione = ['supervisore', 'admin']
    puo_risolvere_supervisioni = ruolo and ruolo.lower() in ruoli_supervisione

    db = get_db()

    import json
    dati_json = json.dumps(dati_corretti) if dati_corretti else None

    # NOTA: id_operatore_gestione è INTEGER, operatore è username string
    # Includiamo l'operatore nella nota invece di usare la colonna FK
    db.execute("""
        UPDATE anomalie
        SET stato = 'RISOLTA',
            data_risoluzione = CURRENT_TIMESTAMP,
            note_risoluzione = %s
        WHERE id_anomalia = %s
    """, (f"Operatore: {operatore} ({ruolo or 'N/D'}) - {note or ''}", id_anomalia))

    # v11.2: Aggiorna supervisioni SOLO se SUPERVISORE o ADMIN
    if puo_risolvere_supervisioni:
        # v10.4: Aggiorna supervisioni collegate su TUTTE le tabelle e registra pattern ML
        nota_sup = f'Risolto da anomalia ({ruolo}): {note or ""}'

        # Recupera pattern signatures PRIMA di aggiornare (per ML learning)
        sup_esp = db.execute("""
            SELECT pattern_signature FROM supervisione_espositore
            WHERE id_anomalia = %s AND stato = 'PENDING'
        """, (id_anomalia,)).fetchall()

        sup_lst = db.execute("""
            SELECT pattern_signature FROM supervisione_listino
            WHERE id_anomalia = %s AND stato = 'PENDING'
        """, (id_anomalia,)).fetchall()

        sup_lkp = db.execute("""
            SELECT pattern_signature FROM supervisione_lookup
            WHERE id_anomalia = %s AND stato = 'PENDING'
        """, (id_anomalia,)).fetchall()

        sup_aic = db.execute("""
            SELECT pattern_signature, codice_aic_assegnato FROM supervisione_aic
            WHERE id_anomalia = %s AND stato = 'PENDING'
        """, (id_anomalia,)).fetchall()

        # Aggiorna supervisioni
        db.execute("""
            UPDATE supervisione_espositore
            SET stato = 'APPROVED', operatore = %s, timestamp_decisione = CURRENT_TIMESTAMP,
                note = COALESCE(note || ' - ', '') || %s
            WHERE id_anomalia = %s AND stato = 'PENDING'
        """, (operatore, nota_sup, id_anomalia))

        db.execute("""
            UPDATE supervisione_listino
            SET stato = 'APPROVED', operatore = %s, timestamp_decisione = CURRENT_TIMESTAMP,
                note = COALESCE(note || ' - ', '') || %s
            WHERE id_anomalia = %s AND stato = 'PENDING'
        """, (operatore, nota_sup, id_anomalia))

        db.execute("""
            UPDATE supervisione_lookup
            SET stato = 'APPROVED', operatore = %s, timestamp_decisione = CURRENT_TIMESTAMP,
                note = COALESCE(note || ' - ', '') || %s
            WHERE id_anomalia = %s AND stato = 'PENDING'
        """, (operatore, nota_sup, id_anomalia))

        db.execute("""
            UPDATE supervisione_aic
            SET stato = 'APPROVED', operatore = %s, timestamp_decisione = CURRENT_TIMESTAMP,
                note = COALESCE(note || ' - ', '') || %s
            WHERE id_anomalia = %s AND stato = 'PENDING'
        """, (operatore, nota_sup, id_anomalia))

        db.commit()

        # v10.4: Registra approvazioni pattern ML
        # IMPORTANTE: Deduplica pattern per evitare conteggi multipli
        from ..supervision.ml import registra_approvazione_pattern, registra_approvazione_pattern_listino
        from ..supervision.lookup import registra_approvazione_pattern_lookup
        from ..supervision.aic import _registra_approvazione_pattern_aic

        seen_esp = set()
        for row in sup_esp:
            ps = row['pattern_signature']
            if ps and ps not in seen_esp:
                seen_esp.add(ps)
                registra_approvazione_pattern(ps, operatore)

        seen_lst = set()
        for row in sup_lst:
            ps = row['pattern_signature']
            if ps and ps not in seen_lst:
                seen_lst.add(ps)
                registra_approvazione_pattern_listino(ps, operatore)

        seen_lkp = set()
        for row in sup_lkp:
            ps = row['pattern_signature']
            if ps and ps not in seen_lkp:
                seen_lkp.add(ps)
                registra_approvazione_pattern_lookup(ps, operatore)

        seen_aic = set()
        for row in sup_aic:
            ps = row['pattern_signature']
            aic = row.get('codice_aic_assegnato')
            if ps and aic and ps not in seen_aic:
                seen_aic.add(ps)
                _registra_approvazione_pattern_aic(ps, operatore, aic)
    else:
        # OPERATORE: solo commit anomalia, supervisioni restano PENDING
        db.commit()

    # Recupera id_testata per sblocco
    anomalia = db.execute(
        "SELECT id_testata FROM anomalie WHERE id_anomalia = %s",
        (id_anomalia,)
    ).fetchone()

    if anomalia and anomalia['id_testata']:
        _sblocca_ordine_se_possibile(anomalia['id_testata'])

    return True


def ignore_anomalia(
    id_anomalia: int,
    operatore: str,
    note: str = None,
    ruolo: str = None
) -> bool:
    """
    Ignora un'anomalia (soft delete).

    v11.2: Aggiunto ruolo per gestione supervisioni.

    Args:
        id_anomalia: ID anomalia
        operatore: Username operatore
        note: Motivo
        ruolo: Ruolo operatore (per risoluzione supervisioni)

    Returns:
        True se ignorato con successo
    """
    return update_anomalia_stato(id_anomalia, 'IGNORATA', note=note, operatore=operatore, ruolo=ruolo)


def resolve_batch(
    anomalie_ids: List[int],
    operatore: str,
    note: str = None,
    ruolo: str = None
) -> Dict[str, Any]:
    """
    Risolve multiple anomalie in batch.

    v11.2: Aggiunto ruolo per gestione supervisioni.

    Returns:
        Dict con risultati {success: int, failed: int, errors: []}
    """
    result = {'success': 0, 'failed': 0, 'errors': []}

    for id_anomalia in anomalie_ids:
        try:
            if update_anomalia_stato(id_anomalia, 'RISOLTA', note=note, operatore=operatore, ruolo=ruolo):
                result['success'] += 1
            else:
                result['failed'] += 1
                result['errors'].append(f"Anomalia {id_anomalia}: aggiornamento fallito")
        except Exception as e:
            result['failed'] += 1
            result['errors'].append(f"Anomalia {id_anomalia}: {str(e)}")

    return result


def ignore_batch(
    anomalie_ids: List[int],
    operatore: str,
    note: str = None,
    ruolo: str = None
) -> Dict[str, Any]:
    """
    Ignora multiple anomalie in batch.

    v11.2: Aggiunto ruolo per gestione supervisioni.

    Returns:
        Dict con risultati {success: int, failed: int, errors: []}
    """
    result = {'success': 0, 'failed': 0, 'errors': []}

    for id_anomalia in anomalie_ids:
        try:
            if update_anomalia_stato(id_anomalia, 'IGNORATA', note=note, operatore=operatore, ruolo=ruolo):
                result['success'] += 1
            else:
                result['failed'] += 1
                result['errors'].append(f"Anomalia {id_anomalia}: aggiornamento fallito")
        except Exception as e:
            result['failed'] += 1
            result['errors'].append(f"Anomalia {id_anomalia}: {str(e)}")

    return result


# =============================================================================
# HELPER FUNCTIONS (Internal)
# =============================================================================

def _update_ordine_stato_anomalia(id_testata: int):
    """Aggiorna stato ordine a ANOMALIA se ci sono anomalie gravi."""
    db = get_db()

    db.execute("""
        UPDATE ordini_testata
        SET stato = 'ANOMALIA'
        WHERE id_testata = %s
        AND stato NOT IN ('EVASO', 'ARCHIVIATO')
    """, (id_testata,))

    db.commit()


def _sblocca_ordine_se_possibile(id_testata: int) -> bool:
    """Sblocca ordine quando tutte le anomalie BLOCCANTI e supervisioni sono risolte."""
    db = get_db()

    # Conta solo anomalie BLOCCANTI ancora aperte (ERRORE, CRITICO)
    # Le anomalie INFO e ATTENZIONE non bloccano l'ordine
    anomalie_aperte = db.execute("""
        SELECT COUNT(*) as cnt FROM anomalie
        WHERE id_testata = %s
        AND stato IN ('APERTA', 'IN_GESTIONE')
        AND livello IN ('ERRORE', 'CRITICO')
    """, (id_testata,)).fetchone()

    # Conta supervisioni ESPOSITORE pending
    sup_espositore = db.execute("""
        SELECT COUNT(*) as cnt FROM supervisione_espositore
        WHERE id_testata = %s AND stato = 'PENDING'
    """, (id_testata,)).fetchone()

    # Conta supervisioni LISTINO pending
    sup_listino = db.execute("""
        SELECT COUNT(*) as cnt FROM supervisione_listino
        WHERE id_testata = %s AND stato = 'PENDING'
    """, (id_testata,)).fetchone()

    # Conta supervisioni LOOKUP pending
    sup_lookup = db.execute("""
        SELECT COUNT(*) as cnt FROM supervisione_lookup
        WHERE id_testata = %s AND stato = 'PENDING'
    """, (id_testata,)).fetchone()

    # Conta supervisioni AIC pending
    sup_aic = db.execute("""
        SELECT COUNT(*) as cnt FROM supervisione_aic
        WHERE id_testata = %s AND stato = 'PENDING'
    """, (id_testata,)).fetchone()

    anomalie_cnt = anomalie_aperte['cnt'] if anomalie_aperte else 0
    sup_esp_cnt = sup_espositore['cnt'] if sup_espositore else 0
    sup_lst_cnt = sup_listino['cnt'] if sup_listino else 0
    sup_lkp_cnt = sup_lookup['cnt'] if sup_lookup else 0
    sup_aic_cnt = sup_aic['cnt'] if sup_aic else 0

    total_blocking = anomalie_cnt + sup_esp_cnt + sup_lst_cnt + sup_lkp_cnt + sup_aic_cnt

    if total_blocking == 0:
        result = db.execute("""
            UPDATE ordini_testata
            SET stato = 'ESTRATTO'
            WHERE id_testata = %s AND stato IN ('ANOMALIA', 'PENDING_REVIEW')
            RETURNING id_testata
        """, (id_testata,)).fetchone()

        db.commit()
        return result is not None

    return False


def _registra_pattern_ml(id_anomalia: int, id_testata: int):
    """Registra pattern ML da anomalia risolta."""
    try:
        from ..ml_pattern_matching import registra_pattern_da_anomalia_risolta
        registra_pattern_da_anomalia_risolta(id_anomalia, id_testata)
    except Exception as e:
        # Log error but don't fail
        print(f"[ML] Errore registrazione pattern: {e}")
