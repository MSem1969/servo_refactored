# =============================================================================
# TO_EXTRACTOR v6.2 - ROUTER GESTIONE UTENTI
# =============================================================================
# Endpoint per CRUD utenti: creazione, modifica, disabilitazione, listing.
# Gestisce anche cambio password e visualizzazione log attività.
# =============================================================================

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from typing import Optional
import json

from ..auth import (
    RuoloUtente,
    CreaUtenteRequest,
    ModificaUtenteRequest,
    ProfiloUpdateRequest,
    CambioPasswordRequest,
    DisabilitaUtenteRequest,
    UtenteResponse,
    UtenteListResponse,
    LogAttivitaResponse,
    LogAttivitaListResponse,
    hash_password,
    verify_password,
    hash_token_for_storage,
    puo_creare_ruolo,
    puo_disabilitare_utente,
    get_current_user,
    require_admin_or_supervisor,
    get_client_ip,
    get_user_agent
)


def _get_db():
    from ..database_pg import get_db
    return get_db()


router = APIRouter(
    prefix="/utenti",
    tags=["Gestione Utenti"],
    responses={
        401: {"description": "Non autenticato"},
        403: {"description": "Accesso negato"},
        404: {"description": "Utente non trovato"}
    }
)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _log_user_action(db, operator_id, operator_username, action, target_id,
                     target_description, success, error_message, details, ip_address, user_agent):
    try:
        db.execute(
            """INSERT INTO LOG_OPERAZIONI (
                tipo_operazione, action_category, entita, id_entita,
                descrizione, dati_json, id_operatore, username_snapshot,
                success, error_message, ip_address, user_agent
            ) VALUES (%s, 'USER_MGMT', 'operatore', %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (action, target_id, target_description, json.dumps(details) if details else None,
             operator_id, operator_username, success, error_message, ip_address, user_agent)
        )
        db.commit()
    except Exception as e:
        print(f"Warning: impossibile loggare azione utente: {e}")


def _get_user_by_id(db, user_id):
    cursor = db.execute(
        """SELECT id_operatore, username, nome, cognome, email, ruolo, attivo,
           data_creazione, created_by_operatore, last_login_at, disabled_at,
           disabled_by_operatore, disable_reason, updated_at,
           data_nascita, avatar_base64, avatar_mime_type
           FROM OPERATORI WHERE id_operatore = %s""", (user_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


def _username_exists(db, username):
    cursor = db.execute("SELECT 1 FROM OPERATORI WHERE LOWER(username) = LOWER(%s)", (username,))
    return cursor.fetchone() is not None


def _email_exists(db, email, exclude_id=None):
    # v6.2: Email può essere condivisa tra utenti (es. stessa azienda)
    # Rimosso vincolo unicità
    return False


def _revoke_all_user_sessions(db, user_id, revoked_by):
    db.execute("UPDATE USER_SESSIONS SET revoked_at = CURRENT_TIMESTAMP, revoked_by_operatore = %s WHERE id_operatore = %s AND revoked_at IS NULL", (revoked_by, user_id))
    db.commit()


def _row_to_utente_response(row):
    # Normalizza ruolo a minuscolo per compatibilità con enum
    ruolo_value = row["ruolo"].lower() if row["ruolo"] else "operatore"
    return UtenteResponse(
        id_operatore=row["id_operatore"], username=row["username"],
        nome=row["nome"], cognome=row["cognome"], email=row["email"],
        ruolo=RuoloUtente(ruolo_value), attivo=bool(row["attivo"]),
        data_creazione=row["data_creazione"], created_by_operatore=row["created_by_operatore"],
        last_login_at=row["last_login_at"], disabled_at=row["disabled_at"],
        disabled_by_operatore=row["disabled_by_operatore"], disable_reason=row["disable_reason"],
        # Campi profilo (v6.2.1)
        data_nascita=row.get("data_nascita"),
        avatar_base64=row.get("avatar_base64"),
        avatar_mime_type=row.get("avatar_mime_type")
    )


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("", response_model=UtenteListResponse, summary="Lista utenti")
async def list_utenti(
    request: Request,
    ruolo: Optional[RuoloUtente] = Query(None),
    attivo: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: UtenteResponse = Depends(require_admin_or_supervisor)
) -> UtenteListResponse:
    db = _get_db()
    conditions, params = [], []

    # v6.2.1: Filtra utenti visibili in base al ruolo corrente
    if current_user.ruolo == RuoloUtente.ADMIN:
        # Admin vede tutti (escluso se stesso opzionalmente)
        conditions.append("ruolo IN ('admin', 'supervisore', 'operatore', 'readonly')")
    else:
        # Supervisore vede solo utenti di livello inferiore (operatore, readonly)
        conditions.append("ruolo IN ('operatore', 'readonly')")

    if ruolo:
        conditions.append("ruolo = %s")
        params.append(ruolo.value)
    if attivo is not None:
        conditions.append("attivo = %s")
        params.append(attivo)
    if search:
        pattern = f"%{search}%"
        conditions.append("(LOWER(username) LIKE LOWER(%s) OR LOWER(nome) LIKE LOWER(%s) OR LOWER(cognome) LIKE LOWER(%s) OR LOWER(email) LIKE LOWER(%s))")
        params.extend([pattern] * 4)

    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    print(f"📊 list_utenti: WHERE={where}, params={params}")
    total = db.execute(f"SELECT COUNT(*) as total FROM OPERATORI {where}", tuple(params)).fetchone()["total"]
    print(f"📊 list_utenti: total={total}")

    offset = (page - 1) * page_size
    pages = (total + page_size - 1) // page_size if total > 0 else 1

    cursor = db.execute(
        f"""SELECT id_operatore, username, nome, cognome, email, ruolo, attivo,
            data_creazione, created_by_operatore, last_login_at, disabled_at,
            disabled_by_operatore, disable_reason, updated_at,
            data_nascita, avatar_base64, avatar_mime_type
            FROM OPERATORI {where} ORDER BY data_creazione DESC LIMIT %s OFFSET %s""",
        tuple(params + [page_size, offset]))

    rows = cursor.fetchall()
    print(f"📊 list_utenti: found {len(rows)} rows")
    items = [_row_to_utente_response(dict(row)) for row in rows]
    return UtenteListResponse(items=items, total=total, page=page, page_size=page_size, pages=pages)


@router.patch("/me/profilo", response_model=UtenteResponse, summary="Aggiorna profilo personale")
async def update_profilo(
    request: Request,
    profilo_data: ProfiloUpdateRequest,
    current_user: UtenteResponse = Depends(get_current_user)
) -> UtenteResponse:
    """
    Aggiorna il profilo personale dell'utente corrente.

    Permette di modificare:
    - nome, cognome
    - data_nascita
    - avatar (immagine base64)

    Solo l'utente può modificare il proprio profilo.
    """
    db = _get_db()
    ip, user_agent = get_client_ip(request), get_user_agent(request)
    user_id = current_user.id_operatore

    # Raccogli campi da aggiornare
    updates, params, old_values = [], [], {}
    target_user = _get_user_by_id(db, user_id)

    if profilo_data.nome is not None:
        old_values["nome"] = target_user["nome"]
        updates.append("nome = %s")
        params.append(profilo_data.nome)

    if profilo_data.cognome is not None:
        old_values["cognome"] = target_user["cognome"]
        updates.append("cognome = %s")
        params.append(profilo_data.cognome)

    if profilo_data.data_nascita is not None:
        old_values["data_nascita"] = str(target_user.get("data_nascita")) if target_user.get("data_nascita") else None
        updates.append("data_nascita = %s")
        params.append(profilo_data.data_nascita)

    # Avatar: stringa vuota = rimuovi, None = non modificare
    if profilo_data.avatar_base64 is not None:
        old_values["avatar_base64"] = "***" if target_user.get("avatar_base64") else None
        if profilo_data.avatar_base64 == "":
            # Rimuovi avatar
            updates.append("avatar_base64 = NULL")
            updates.append("avatar_mime_type = NULL")
        else:
            updates.append("avatar_base64 = %s")
            params.append(profilo_data.avatar_base64)
            # Estrai mime type dall'header base64
            if profilo_data.avatar_base64.startswith("data:"):
                mime_type = profilo_data.avatar_base64.split(";")[0].replace("data:", "")
                updates.append("avatar_mime_type = %s")
                params.append(mime_type)

    if not updates:
        return _row_to_utente_response(target_user)

    updates.append("updated_at = CURRENT_TIMESTAMP")
    params.append(user_id)
    db.execute(f"UPDATE OPERATORI SET {', '.join(updates)} WHERE id_operatore = %s", tuple(params))
    db.commit()

    _log_user_action(
        db, current_user.id_operatore, current_user.username,
        "PROFILO_UPDATE", user_id,
        f"Aggiornato profilo personale",
        True, None,
        {"old_values": old_values, "fields_updated": list(old_values.keys())},
        ip, user_agent
    )

    return _row_to_utente_response(_get_user_by_id(db, user_id))


@router.get("/{user_id}", response_model=UtenteResponse, summary="Dettaglio utente")
async def get_utente(user_id: int, current_user: UtenteResponse = Depends(require_admin_or_supervisor)) -> UtenteResponse:
    db = _get_db()
    user_data = _get_user_by_id(db, user_id)
    if not user_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utente non trovato")
    
    # v6.2.1: Supervisore può vedere operatori e readonly (livello inferiore)
    if current_user.ruolo == RuoloUtente.SUPERVISORE:
        if user_data["ruolo"] not in ("operatore", "readonly"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Non hai accesso a questo utente")

    return _row_to_utente_response(user_data)


@router.post("", response_model=UtenteResponse, status_code=status.HTTP_201_CREATED, summary="Crea utente")
async def create_utente(request: Request, user_data: CreaUtenteRequest,
                        current_user: UtenteResponse = Depends(require_admin_or_supervisor)) -> UtenteResponse:
    db = _get_db()
    ip, user_agent = get_client_ip(request), get_user_agent(request)
    
    if not puo_creare_ruolo(current_user.ruolo, user_data.ruolo):
        _log_user_action(db, current_user.id_operatore, current_user.username, "USER_CREATE_DENIED", None,
                         f"Tentativo creazione {user_data.ruolo.value}", False, "Permessi insufficienti",
                         {"target_role": user_data.ruolo.value}, ip, user_agent)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Non puoi creare utenti con ruolo {user_data.ruolo.value}")
    
    if _username_exists(db, user_data.username):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username già esistente")
    if user_data.email and _email_exists(db, user_data.email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email già esistente")
    
    cursor = db.execute(
        """INSERT INTO OPERATORI (username, password_hash, nome, cognome, email, ruolo, attivo, created_by_operatore, data_creazione, updated_at)
           VALUES (%s, %s, %s, %s, %s, %s, TRUE, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
           RETURNING id_operatore""",
        (user_data.username.lower(), hash_password(user_data.password), user_data.nome, user_data.cognome,
         user_data.email, user_data.ruolo.value.lower(), current_user.id_operatore))
    new_user_id = cursor.fetchone()["id_operatore"]
    db.commit()
    _log_user_action(db, current_user.id_operatore, current_user.username, "USER_CREATE", new_user_id,
                     f"Creato utente {user_data.username}", True, None,
                     {"new_username": user_data.username, "new_role": user_data.ruolo.value}, ip, user_agent)
    
    return _row_to_utente_response(_get_user_by_id(db, new_user_id))


@router.patch("/{user_id}", response_model=UtenteResponse, summary="Modifica utente")
async def update_utente(user_id: int, request: Request, update_data: ModificaUtenteRequest,
                        current_user: UtenteResponse = Depends(get_current_user)) -> UtenteResponse:
    db = _get_db()
    ip, user_agent = get_client_ip(request), get_user_agent(request)
    
    target_user = _get_user_by_id(db, user_id)
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utente non trovato")
    
    is_self = (user_id == current_user.id_operatore)
    if not is_self:
        if current_user.ruolo not in [RuoloUtente.ADMIN, RuoloUtente.SUPERVISORE]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Non hai i permessi")
        # v6.2.1: Supervisore può modificare operatori e readonly (livello inferiore)
        if current_user.ruolo == RuoloUtente.SUPERVISORE:
            if target_user["ruolo"] not in ("operatore", "readonly"):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Non puoi modificare questo utente")
        elif current_user.ruolo == RuoloUtente.ADMIN and target_user["ruolo"] == "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Non puoi modificare altri admin")
    
    if update_data.email and _email_exists(db, update_data.email, exclude_id=user_id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email già esistente")
    
    updates, params, old_values = [], [], {}
    if update_data.nome is not None:
        old_values["nome"] = target_user["nome"]
        updates.append("nome = %s")
        params.append(update_data.nome)
    if update_data.cognome is not None:
        old_values["cognome"] = target_user["cognome"]
        updates.append("cognome = %s")
        params.append(update_data.cognome)
    if update_data.email is not None:
        old_values["email"] = target_user["email"]
        updates.append("email = %s")
        params.append(update_data.email)

    if not updates:
        return _row_to_utente_response(target_user)

    updates.append("updated_at = CURRENT_TIMESTAMP")
    params.append(user_id)
    db.execute(f"UPDATE OPERATORI SET {', '.join(updates)} WHERE id_operatore = %s", tuple(params))
    db.commit()
    
    _log_user_action(db, current_user.id_operatore, current_user.username, "USER_UPDATE", user_id,
                     f"Modificato utente {target_user['username']}", True, None,
                     {"old_values": old_values, "new_values": update_data.dict(exclude_none=True)}, ip, user_agent)
    
    return _row_to_utente_response(_get_user_by_id(db, user_id))


@router.post("/{user_id}/cambio-password", status_code=status.HTTP_204_NO_CONTENT, summary="Cambio password")
async def change_password(user_id: int, request: Request, password_data: CambioPasswordRequest,
                          current_user: UtenteResponse = Depends(get_current_user)):
    db = _get_db()
    ip, user_agent = get_client_ip(request), get_user_agent(request)
    
    target_user = _get_user_by_id(db, user_id)
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utente non trovato")
    
    is_self = (user_id == current_user.id_operatore)
    if not is_self:
        if current_user.ruolo == RuoloUtente.ADMIN:
            if target_user["ruolo"] == "admin":
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Non puoi cambiare password ad altri admin")
        # v6.2.1: Supervisore può cambiare password a operatori e readonly
        elif current_user.ruolo == RuoloUtente.SUPERVISORE:
            if target_user["ruolo"] not in ("operatore", "readonly"):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Non puoi cambiare password a questo utente")
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Non hai i permessi")
    
    if is_self:
        if not password_data.vecchia_password:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Vecchia password richiesta")
        row = db.execute("SELECT password_hash FROM OPERATORI WHERE id_operatore = %s", (user_id,)).fetchone()
        if not verify_password(password_data.vecchia_password, row["password_hash"]):
            _log_user_action(db, current_user.id_operatore, current_user.username, "PASSWORD_CHANGE_FAILED",
                             user_id, f"Cambio password fallito", False, "Vecchia password errata", None, ip, user_agent)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Vecchia password non corretta")

    db.execute("UPDATE OPERATORI SET password_hash = %s, updated_at = CURRENT_TIMESTAMP WHERE id_operatore = %s",
               (hash_password(password_data.nuova_password), user_id))
    db.commit()

    if is_self:
        auth_header = request.headers.get("Authorization", "")
        current_token_hash = hash_token_for_storage(auth_header.replace("Bearer ", ""))
        db.execute("UPDATE USER_SESSIONS SET revoked_at = CURRENT_TIMESTAMP, revoked_by_operatore = %s WHERE id_operatore = %s AND token_hash != %s AND revoked_at IS NULL",
                   (current_user.id_operatore, user_id, current_token_hash))
    else:
        _revoke_all_user_sessions(db, user_id, current_user.id_operatore)
    db.commit()
    
    _log_user_action(db, current_user.id_operatore, current_user.username, "PASSWORD_CHANGE", user_id,
                     f"Password cambiata per {target_user['username']}", True, None, {"is_self": is_self}, ip, user_agent)


@router.post("/{user_id}/disabilita", response_model=UtenteResponse, summary="Disabilita utente")
async def disable_utente(user_id: int, request: Request, disable_data: DisabilitaUtenteRequest,
                         current_user: UtenteResponse = Depends(require_admin_or_supervisor)) -> UtenteResponse:
    db = _get_db()
    ip, user_agent = get_client_ip(request), get_user_agent(request)
    
    target_user = _get_user_by_id(db, user_id)
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utente non trovato")
    if not target_user["attivo"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Utente già disabilitato")
    
    can_disable = puo_disabilitare_utente(current_user.ruolo, current_user.id_operatore,
                                           RuoloUtente(target_user["ruolo"]), user_id, target_user["created_by_operatore"])
    if not can_disable:
        _log_user_action(db, current_user.id_operatore, current_user.username, "USER_DISABLE_DENIED", user_id,
                         f"Disabilitazione negata", False, "Permessi insufficienti", {"target_role": target_user["ruolo"]}, ip, user_agent)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Non puoi disabilitare questo utente")
    
    db.execute("UPDATE OPERATORI SET attivo = FALSE, disabled_at = CURRENT_TIMESTAMP, disabled_by_operatore = %s, disable_reason = %s, updated_at = CURRENT_TIMESTAMP WHERE id_operatore = %s",
               (current_user.id_operatore, disable_data.motivo, user_id))
    _revoke_all_user_sessions(db, user_id, current_user.id_operatore)
    db.commit()
    
    _log_user_action(db, current_user.id_operatore, current_user.username, "USER_DISABLE", user_id,
                     f"Disabilitato utente {target_user['username']}", True, None,
                     {"target_username": target_user["username"], "reason": disable_data.motivo}, ip, user_agent)
    
    return _row_to_utente_response(_get_user_by_id(db, user_id))


@router.post("/{user_id}/riabilita", response_model=UtenteResponse, summary="Riabilita utente")
async def enable_utente(user_id: int, request: Request,
                        current_user: UtenteResponse = Depends(require_admin_or_supervisor)) -> UtenteResponse:
    db = _get_db()
    ip, user_agent = get_client_ip(request), get_user_agent(request)
    
    target_user = _get_user_by_id(db, user_id)
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utente non trovato")
    if target_user["attivo"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Utente già attivo")
    
    can_enable = puo_disabilitare_utente(current_user.ruolo, current_user.id_operatore,
                                          RuoloUtente(target_user["ruolo"]), user_id, target_user["created_by_operatore"])
    if not can_enable:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Non puoi riabilitare questo utente")
    
    db.execute("UPDATE OPERATORI SET attivo = TRUE, disabled_at = NULL, disabled_by_operatore = NULL, disable_reason = NULL, updated_at = CURRENT_TIMESTAMP WHERE id_operatore = %s", (user_id,))
    db.commit()
    
    _log_user_action(db, current_user.id_operatore, current_user.username, "USER_ENABLE", user_id,
                     f"Riabilitato utente {target_user['username']}", True, None, {"target_username": target_user["username"]}, ip, user_agent)
    
    return _row_to_utente_response(_get_user_by_id(db, user_id))


@router.get("/{user_id}/logs", response_model=LogAttivitaListResponse, summary="Log attività utente")
async def get_user_logs(user_id: int, action_category: Optional[str] = Query(None),
                        page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
                        current_user: UtenteResponse = Depends(require_admin_or_supervisor)) -> LogAttivitaListResponse:
    db = _get_db()
    
    target_user = _get_user_by_id(db, user_id)
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utente non trovato")
    
    if current_user.ruolo == RuoloUtente.SUPERVISORE:
        is_own = (user_id == current_user.id_operatore)
        is_own_operator = (target_user["ruolo"] == "operatore" and target_user["created_by_operatore"] == current_user.id_operatore)
        if not (is_own or is_own_operator):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Non hai accesso ai log di questo utente")
    
    conditions, params = ["id_operatore = %s"], [user_id]
    if action_category:
        conditions.append("action_category = %s")
        params.append(action_category)

    where = " AND ".join(conditions)
    count = db.execute(f"SELECT COUNT(*) as total FROM LOG_OPERAZIONI WHERE {where}", tuple(params)).fetchone()["total"]

    offset = (page - 1) * page_size
    cursor = db.execute(
        f"""SELECT id_log, tipo_operazione, action_category, entita, id_entita, descrizione,
            id_operatore, username_snapshot, success, error_message, ip_address, timestamp
            FROM LOG_OPERAZIONI WHERE {where} ORDER BY timestamp DESC LIMIT %s OFFSET %s""",
        tuple(params + [page_size, offset]))
    
    items = []
    for row in cursor.fetchall():
        r = dict(row)
        items.append(LogAttivitaResponse(
            id_log=r["id_log"], tipo_operazione=r["tipo_operazione"], action_category=r["action_category"],
            entita=r["entita"], id_entita=r["id_entita"], descrizione=r["descrizione"],
            success=bool(r["success"]) if r["success"] is not None else True,
            error_message=r["error_message"], ip_address=r["ip_address"], timestamp=r["timestamp"],
            id_operatore=r["id_operatore"], username_snapshot=r["username_snapshot"]
        ))
    
    return LogAttivitaListResponse(items=items, total=count, page=page, page_size=page_size)
