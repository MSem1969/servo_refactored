# =============================================================================
# SERV.O v6.2 - AUTH ROUTER
# =============================================================================
# Endpoint per autenticazione: login, logout, info utente, sessioni.
#
# ENDPOINT:
# - POST /auth/login         - Login con username/password
# - POST /auth/logout        - Logout (revoca sessione)
# - GET  /auth/me            - Info utente corrente
# - GET  /auth/me/permissions - Permessi e sezioni visibili
# - GET  /auth/me/sessions   - Lista sessioni attive
# - DELETE /auth/me/sessions/{id} - Revoca sessione specifica
# - POST /auth/me/sessions/revoke-others - Revoca altre sessioni
# =============================================================================

from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import Optional
from datetime import datetime

from .models import (
    LoginRequest, LoginResponse, UtenteResponse,
    SessioneResponse, SessioniAttiveResponse, RuoloUtente,
    ForgotPasswordRequest, ForgotPasswordResponse,
    ResetPasswordRequest, ResetPasswordResponse
)
from .security import (
    verify_password, create_access_token,
    hash_token_for_storage, get_token_expiration_seconds,
    hash_password
)
import secrets
import os
from .dependencies import (
    get_current_user, get_client_ip, get_user_agent
)
from .permissions import get_home_page, get_sezioni_visibili, get_permessi_ruolo


# =============================================================================
# IMPORT DATABASE (lazy)
# =============================================================================

def _get_db():
    """Import lazy del database."""
    from ..database_pg import get_db
    return get_db()


# =============================================================================
# ROUTER SETUP
# =============================================================================

router = APIRouter(
    prefix="/auth",
    tags=["Autenticazione"],
    responses={
        401: {"description": "Non autenticato"},
        403: {"description": "Accesso negato"}
    }
)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _get_user_by_username(db, username: str) -> Optional[dict]:
    """
    Recupera utente per username (case-insensitive).

    Include password_hash per verifica login e campi profilo.
    """
    cursor = db.execute(
        """
        SELECT
            id_operatore, username, password_hash, nome, cognome,
            email, ruolo, attivo, data_creazione, created_by_operatore,
            last_login_at, disabled_at, disabled_by_operatore, disable_reason,
            data_nascita, avatar_base64, avatar_mime_type
        FROM OPERATORI
        WHERE LOWER(username) = LOWER(%s)
        """,
        (username,)
    )
    row = cursor.fetchone()
    return dict(row) if row else None


def _create_session(
    db,
    user_id: int,
    token_hash: str,
    expires_at: datetime,
    ip_address: str,
    user_agent: str
) -> int:
    """
    Crea record sessione nel database.

    Returns:
        id_session creato
    """
    cursor = db.execute(
        """
        INSERT INTO USER_SESSIONS (
            id_operatore, token_hash, expires_at, ip_address, user_agent
        ) VALUES (%s, %s, %s, %s, %s)
        RETURNING id_session
        """,
        (user_id, token_hash, expires_at.isoformat(), ip_address, user_agent)
    )
    row = cursor.fetchone()
    db.commit()
    return row[0] if row else None


def _update_last_login(db, user_id: int, ip_address: str):
    """Aggiorna timestamp e IP ultimo login."""
    db.execute(
        """
        UPDATE OPERATORI
        SET last_login_at = NOW(),
            last_login_ip = %s,
            updated_at = NOW()
        WHERE id_operatore = %s
        """,
        (ip_address, user_id)
    )
    db.commit()


def _log_auth_action(
    db,
    user_id: Optional[int],
    username: Optional[str],
    action: str,
    success: bool,
    error_message: Optional[str],
    ip_address: str,
    user_agent: str,
    session_id: Optional[int] = None
):
    """Registra azione di autenticazione nel log."""
    try:
        db.execute(
            """
            INSERT INTO LOG_OPERAZIONI (
                tipo_operazione, action_category, entita, id_entita,
                descrizione, id_operatore, username_snapshot,
                success, error_message, ip_address, user_agent, session_id
            ) VALUES (%s, 'AUTH', 'operatore', %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                action,
                user_id,
                f"{action}: {username or 'unknown'}",
                user_id or 0,
                username,
                success,  # BOOLEAN column
                error_message,
                ip_address,
                user_agent,
                session_id
            )
        )
        db.commit()
    except Exception as e:
        print(f"Warning: impossibile loggare azione auth: {e}")


def _revoke_session_by_hash(
    db,
    token_hash: str,
    revoked_by: int
):
    """Revoca una sessione specifica tramite hash."""
    db.execute(
        """
        UPDATE USER_SESSIONS
        SET revoked_at = NOW(),
            revoked_by_operatore = %s
        WHERE token_hash = %s AND revoked_at IS NULL
        """,
        (revoked_by, token_hash)
    )
    db.commit()


# =============================================================================
# ENDPOINT: LOGIN
# =============================================================================

@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Login utente",
    description="""
    Autentica un utente con username e password.
    
    Ritorna un JWT token da usare per le richieste successive
    nell'header Authorization: Bearer <token>.
    
    Il token ha validità di 8 ore.
    
    **Errori possibili:**
    - 401: Credenziali non valide
    - 403: Utente disabilitato
    """
)
async def login(
    request: Request,
    login_data: LoginRequest
) -> LoginResponse:
    """
    Endpoint di login.

    Flusso:
    1. Cerca utente per username (case-insensitive)
    2. Verifica password contro hash
    3. Verifica utente attivo
    4. Genera JWT token
    5. Crea sessione nel DB
    6. Aggiorna ultimo login
    7. Log dell'operazione
    """
    import traceback
    print(f"\n=== LOGIN ATTEMPT: {login_data.username} ===")
    print(f"Password ricevuta: '{login_data.password}' (len={len(login_data.password)})")

    try:
        db = _get_db()
        ip = get_client_ip(request)
        user_agent = get_user_agent(request)

        # 1. Cerca utente per username
        print(f"[1] Cercando utente: {login_data.username}")
        user = _get_user_by_username(db, login_data.username)
        print(f"[1] Utente trovato: {user is not None}")
    except Exception as e:
        print(f"[ERROR] Errore iniziale: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Errore DB: {e}")

    if not user:
        print(f"[2] Utente NON trovato!")
        # Log tentativo fallito (utente non esiste)
        _log_auth_action(
            db, None, login_data.username, "LOGIN_FAILED",
            False, "Utente non trovato", ip, user_agent
        )
        # Messaggio generico per sicurezza (non rivelare se username esiste)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenziali non valide"
        )
    
    # 2. Verifica password
    # Se password_hash è vuoto o None, login fallisce
    print(f"[2] Verifico password...")
    print(f"[2] Hash: {user['password_hash'][:30]}...")
    try:
        pwd_ok = verify_password(login_data.password, user["password_hash"])
        print(f"[2] Password OK: {pwd_ok}")
        # Test diretto bcrypt
        import bcrypt
        direct_ok = bcrypt.checkpw(login_data.password.encode('utf-8'), user["password_hash"].encode('utf-8'))
        print(f"[2] Bcrypt diretto: {direct_ok}")
    except Exception as e:
        print(f"[2] ERRORE verify_password: {e}")
        traceback.print_exc()
        pwd_ok = False

    if not user["password_hash"] or not pwd_ok:
        print(f"[2] Password FALLITA!")
        _log_auth_action(
            db, user["id_operatore"], user["username"], "LOGIN_FAILED",
            False, "Password errata", ip, user_agent
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenziali non valide"
        )
    
    # 3. Verifica utente attivo
    if not user["attivo"]:
        _log_auth_action(
            db, user["id_operatore"], user["username"], "LOGIN_FAILED",
            False, "Utente disabilitato", ip, user_agent
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Utente disabilitato"
        )
    
    # 4. Genera token JWT
    # Accetta ruoli sia maiuscoli che minuscoli
    ruolo = RuoloUtente(user["ruolo"].lower())
    token, jti, expires_at = create_access_token(
        user_id=user["id_operatore"],
        username=user["username"],
        ruolo=ruolo
    )
    
    # 5. Crea sessione nel DB
    token_hash = hash_token_for_storage(token)
    session_id = _create_session(
        db, user["id_operatore"], token_hash, 
        expires_at, ip, user_agent
    )
    
    # 6. Aggiorna ultimo login
    _update_last_login(db, user["id_operatore"], ip)
    
    # 7. Log successo
    _log_auth_action(
        db, user["id_operatore"], user["username"], "LOGIN",
        True, None, ip, user_agent, session_id
    )
    
    # 8. Costruisci response
    user_response = UtenteResponse(
        id_operatore=user["id_operatore"],
        username=user["username"],
        nome=user["nome"],
        cognome=user["cognome"],
        email=user["email"],
        ruolo=ruolo,
        attivo=True,
        data_creazione=user["data_creazione"],
        created_by_operatore=user["created_by_operatore"],
        last_login_at=datetime.now(),
        disabled_at=None,
        disabled_by_operatore=None,
        disable_reason=None,
        # Campi profilo (v6.2.1)
        data_nascita=user.get("data_nascita"),
        avatar_base64=user.get("avatar_base64"),
        avatar_mime_type=user.get("avatar_mime_type")
    )
    
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        expires_in=get_token_expiration_seconds(),
        user=user_response
    )


# =============================================================================
# ENDPOINT: LOGOUT
# =============================================================================

@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout utente",
    description="Revoca il token corrente. L'utente dovrà rifare login."
)
async def logout(
    request: Request,
    current_user: UtenteResponse = Depends(get_current_user)
):
    """
    Endpoint di logout.
    
    Revoca la sessione corrente nel database.
    Il token non sarà più valido anche se non scaduto.
    """
    db = _get_db()
    ip = get_client_ip(request)
    user_agent = get_user_agent(request)
    
    # Estrai token dall'header
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.replace("Bearer ", "")
    token_hash = hash_token_for_storage(token)
    
    # Revoca sessione
    _revoke_session_by_hash(db, token_hash, current_user.id_operatore)
    
    # Log
    _log_auth_action(
        db, current_user.id_operatore, current_user.username,
        "LOGOUT", True, None, ip, user_agent
    )
    
    return None


# =============================================================================
# ENDPOINT: ME (INFO UTENTE CORRENTE)
# =============================================================================

@router.get(
    "/me",
    response_model=UtenteResponse,
    summary="Info utente corrente",
    description="Ritorna le informazioni dell'utente autenticato."
)
async def get_me(
    current_user: UtenteResponse = Depends(get_current_user)
) -> UtenteResponse:
    """Ritorna dati utente corrente."""
    return current_user


# =============================================================================
# ENDPOINT: PERMESSI UTENTE CORRENTE
# =============================================================================

@router.get(
    "/me/permissions",
    summary="Permessi utente corrente",
    description="Ritorna permessi, sezioni visibili e home page per l'utente."
)
async def get_my_permissions(
    current_user: UtenteResponse = Depends(get_current_user)
) -> dict:
    """
    Ritorna informazioni sui permessi dell'utente corrente.
    
    Utile per il frontend per decidere cosa mostrare:
    - Menu dinamico basato su sezioni_visibili
    - Redirect a home_page dopo login
    - Controllo permessi granulari
    """
    return {
        "ruolo": current_user.ruolo.value,
        "permissions": get_permessi_ruolo(current_user.ruolo),
        "sezioni_visibili": get_sezioni_visibili(current_user.ruolo),
        "home_page": get_home_page(current_user.ruolo)
    }


# =============================================================================
# ENDPOINT: SESSIONI ATTIVE
# =============================================================================

@router.get(
    "/me/sessions",
    response_model=SessioniAttiveResponse,
    summary="Sessioni attive",
    description="Lista le sessioni attive dell'utente corrente."
)
async def get_my_sessions(
    request: Request,
    current_user: UtenteResponse = Depends(get_current_user)
) -> SessioniAttiveResponse:
    """
    Ritorna lista sessioni attive dell'utente.
    
    Permette all'utente di vedere da dove è connesso
    e identificare la sessione corrente.
    """
    db = _get_db()
    
    # Token corrente per identificare sessione attuale
    auth_header = request.headers.get("Authorization", "")
    current_token = auth_header.replace("Bearer ", "")
    current_token_hash = hash_token_for_storage(current_token)
    
    # Query sessioni attive
    cursor = db.execute(
        """
        SELECT id_session, created_at, expires_at, ip_address, user_agent, token_hash
        FROM USER_SESSIONS
        WHERE id_operatore = %s
          AND revoked_at IS NULL
          AND expires_at > NOW()
        ORDER BY created_at DESC
        """,
        (current_user.id_operatore,)
    )
    
    sessioni = []
    for row in cursor.fetchall():
        row_dict = dict(row)
        sessioni.append(SessioneResponse(
            id_session=row_dict["id_session"],
            created_at=row_dict["created_at"],
            expires_at=row_dict["expires_at"],
            ip_address=row_dict["ip_address"],
            user_agent=row_dict["user_agent"],
            is_current=(row_dict["token_hash"] == current_token_hash)
        ))
    
    return SessioniAttiveResponse(
        sessioni=sessioni,
        totale=len(sessioni)
    )


# =============================================================================
# ENDPOINT: REVOCA SESSIONE SPECIFICA
# =============================================================================

@router.delete(
    "/me/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoca sessione",
    description="Revoca una sessione specifica dell'utente."
)
async def revoke_session(
    session_id: int,
    request: Request,
    current_user: UtenteResponse = Depends(get_current_user)
):
    """
    Revoca una sessione specifica.
    
    L'utente può revocare solo le proprie sessioni.
    """
    db = _get_db()
    ip = get_client_ip(request)
    user_agent = get_user_agent(request)
    
    # Verifica che la sessione appartenga all'utente
    cursor = db.execute(
        """
        SELECT id_session, token_hash
        FROM USER_SESSIONS
        WHERE id_session = %s AND id_operatore = %s AND revoked_at IS NULL
        """,
        (session_id, current_user.id_operatore)
    )
    session = cursor.fetchone()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sessione non trovata"
        )
    
    session_dict = dict(session)
    
    # Revoca
    _revoke_session_by_hash(db, session_dict["token_hash"], current_user.id_operatore)
    
    # Log
    _log_auth_action(
        db, current_user.id_operatore, current_user.username,
        "SESSION_REVOKE", True, f"Revocata sessione {session_id}",
        ip, user_agent
    )
    
    return None


# =============================================================================
# ENDPOINT: REVOCA TUTTE LE ALTRE SESSIONI
# =============================================================================

@router.post(
    "/me/sessions/revoke-others",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoca altre sessioni",
    description="Revoca tutte le sessioni tranne quella corrente."
)
async def revoke_other_sessions(
    request: Request,
    current_user: UtenteResponse = Depends(get_current_user)
):
    """
    Revoca tutte le sessioni dell'utente tranne quella corrente.
    
    Utile se l'utente sospetta accessi non autorizzati.
    """
    db = _get_db()
    ip = get_client_ip(request)
    user_agent = get_user_agent(request)
    
    # Token corrente da preservare
    auth_header = request.headers.get("Authorization", "")
    current_token = auth_header.replace("Bearer ", "")
    current_token_hash = hash_token_for_storage(current_token)
    
    # Revoca tutte tranne corrente
    cursor = db.execute(
        """
        UPDATE USER_SESSIONS
        SET revoked_at = NOW(),
            revoked_by_operatore = %s
        WHERE id_operatore = %s
          AND token_hash != %s
          AND revoked_at IS NULL
        """,
        (current_user.id_operatore, current_user.id_operatore, current_token_hash)
    )
    revoked_count = cursor.rowcount
    db.commit()
    
    # Log
    _log_auth_action(
        db, current_user.id_operatore, current_user.username,
        "SESSION_REVOKE_ALL", True, f"Revocate {revoked_count} sessioni",
        ip, user_agent
    )

    return None


# =============================================================================
# HELPER FUNCTIONS - PASSWORD RESET
# =============================================================================

def _ensure_password_reset_table(db):
    """Crea tabella password_reset_tokens se non esiste (auto-migrazione)."""
    try:
        db.execute("""
            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                id SERIAL PRIMARY KEY,
                id_operatore INTEGER NOT NULL REFERENCES operatori(id_operatore),
                token_hash VARCHAR(255) NOT NULL UNIQUE,
                expires_at TIMESTAMP NOT NULL,
                used_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ip_address VARCHAR(45),
                user_agent TEXT
            )
        """)
        db.execute("""
            CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_hash
            ON password_reset_tokens(token_hash)
        """)
        db.execute("""
            CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_expires
            ON password_reset_tokens(expires_at)
        """)
        db.commit()
    except Exception:
        pass


def _get_user_by_email(db, email: str) -> Optional[dict]:
    """Recupera utente per email (case-insensitive)."""
    cursor = db.execute(
        """
        SELECT id_operatore, username, email, nome, cognome, attivo
        FROM OPERATORI
        WHERE LOWER(email) = LOWER(%s)
        """,
        (email,)
    )
    row = cursor.fetchone()
    return dict(row) if row else None


def _create_reset_token(db, user_id: int, ip: str, user_agent: str) -> str:
    """
    Crea token di reset password.

    Returns:
        Token in chiaro (da inviare via email)
    """
    # Genera token sicuro
    token = secrets.token_urlsafe(32)
    token_hash = hash_token_for_storage(token)

    # Token valido per 1 ora
    from datetime import timedelta
    expires_at = datetime.now() + timedelta(hours=1)

    # Invalida eventuali token precedenti per lo stesso utente
    db.execute(
        "UPDATE password_reset_tokens SET used_at = NOW() WHERE id_operatore = %s AND used_at IS NULL",
        (user_id,)
    )

    # Crea nuovo token
    db.execute(
        """
        INSERT INTO password_reset_tokens (id_operatore, token_hash, expires_at, ip_address, user_agent)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (user_id, token_hash, expires_at.isoformat(), ip, user_agent)
    )
    db.commit()

    return token


def _validate_reset_token(db, token: str) -> Optional[dict]:
    """
    Valida token di reset.

    Returns:
        Dict con info utente se token valido, None altrimenti
    """
    token_hash = hash_token_for_storage(token)

    cursor = db.execute(
        """
        SELECT prt.id, prt.id_operatore, o.username, o.email
        FROM password_reset_tokens prt
        JOIN operatori o ON o.id_operatore = prt.id_operatore
        WHERE prt.token_hash = %s
          AND prt.used_at IS NULL
          AND prt.expires_at > NOW()
          AND o.attivo = TRUE
        """,
        (token_hash,)
    )
    row = cursor.fetchone()
    return dict(row) if row else None


def _mark_token_used(db, token: str):
    """Marca token come usato."""
    token_hash = hash_token_for_storage(token)
    db.execute(
        "UPDATE password_reset_tokens SET used_at = NOW() WHERE token_hash = %s",
        (token_hash,)
    )
    db.commit()


def _revoke_all_user_sessions(db, user_id: int, revoked_by: int):
    """Revoca tutte le sessioni di un utente."""
    db.execute(
        """
        UPDATE USER_SESSIONS
        SET revoked_at = NOW(), revoked_by_operatore = %s
        WHERE id_operatore = %s AND revoked_at IS NULL
        """,
        (revoked_by, user_id)
    )
    db.commit()


def _get_frontend_url() -> str:
    """Ottiene URL frontend per costruire link reset."""
    # Prima cerca nelle variabili d'ambiente
    frontend_url = os.environ.get('FRONTEND_URL')
    if frontend_url:
        return frontend_url.rstrip('/')

    # Fallback: prova a costruirlo dal VITE_API_URL o altri hints
    api_url = os.environ.get('VITE_API_URL', '')
    if 'api-' in api_url:
        # Es: https://api-sofad.aiservo.net -> https://sofad.aiservo.net
        return api_url.replace('api-', '').rstrip('/')

    # Default per sviluppo locale
    return 'http://localhost:5173'


# =============================================================================
# ENDPOINT: FORGOT PASSWORD (Richiesta reset)
# =============================================================================

@router.post(
    "/forgot-password",
    response_model=ForgotPasswordResponse,
    summary="Richiesta reset password",
    description="""
    Invia un'email con link per reimpostare la password.

    Per sicurezza, ritorna sempre successo anche se l'email non esiste.
    Il link scade dopo 1 ora.
    """
)
async def forgot_password(
    request: Request,
    data: ForgotPasswordRequest
) -> ForgotPasswordResponse:
    """
    Endpoint per richiesta reset password.

    Flusso:
    1. Cerca utente per email
    2. Se esiste e attivo, genera token e invia email
    3. Ritorna sempre successo (sicurezza)
    """
    db = _get_db()
    ip = get_client_ip(request)
    user_agent = get_user_agent(request)

    # Auto-migrazione tabella
    _ensure_password_reset_table(db)

    # Cerca utente
    user = _get_user_by_email(db, data.email)

    if user and user["attivo"]:
        try:
            # Genera token
            token = _create_reset_token(db, user["id_operatore"], ip, user_agent)

            # Costruisci URL reset
            frontend_url = _get_frontend_url()
            reset_url = f"{frontend_url}?reset_token={token}"

            # Invia email
            try:
                from ..services.email.sender import EmailSender
                sender = EmailSender(db)

                if sender.is_configured(db):
                    result = sender.send_from_template(
                        'password_reset',
                        {
                            'username': user["username"],
                            'reset_url': reset_url
                        },
                        to=user["email"]
                    )

                    if result.get('success'):
                        _log_auth_action(
                            db, user["id_operatore"], user["username"],
                            "PASSWORD_RESET_REQUEST", True,
                            f"Email inviata a {data.email}", ip, user_agent
                        )
                    else:
                        print(f"[WARN] Errore invio email reset: {result.get('error')}")
                else:
                    print(f"[WARN] Email non configurata - Token reset: {token}")
                    # Log comunque per debug
                    _log_auth_action(
                        db, user["id_operatore"], user["username"],
                        "PASSWORD_RESET_REQUEST", True,
                        f"Token generato (email non configurata)", ip, user_agent
                    )
            except Exception as e:
                print(f"[ERROR] Errore invio email: {e}")
                # Non fallire - ritorna comunque successo

        except Exception as e:
            print(f"[ERROR] Errore generazione token: {e}")

    else:
        # Log tentativo con email non esistente (per audit)
        _log_auth_action(
            db, None, None, "PASSWORD_RESET_REQUEST", False,
            f"Email non trovata: {data.email}", ip, user_agent
        )

    # Ritorna sempre successo (non rivelare se email esiste)
    return ForgotPasswordResponse()


# =============================================================================
# ENDPOINT: RESET PASSWORD (Esegui reset con token)
# =============================================================================

@router.post(
    "/reset-password",
    response_model=ResetPasswordResponse,
    summary="Reset password con token",
    description="""
    Reimposta la password usando il token ricevuto via email.

    Il token è valido per 1 ora dalla richiesta.
    Dopo il reset, tutte le sessioni attive vengono revocate.
    """
)
async def reset_password(
    request: Request,
    data: ResetPasswordRequest
) -> ResetPasswordResponse:
    """
    Endpoint per reset password con token.

    Flusso:
    1. Valida token (esistente, non usato, non scaduto)
    2. Aggiorna password utente
    3. Marca token come usato
    4. Revoca tutte le sessioni
    5. Invia email conferma (opzionale)
    """
    db = _get_db()
    ip = get_client_ip(request)
    user_agent = get_user_agent(request)

    # Auto-migrazione tabella
    _ensure_password_reset_table(db)

    # Valida token
    token_info = _validate_reset_token(db, data.token)

    if not token_info:
        _log_auth_action(
            db, None, None, "PASSWORD_RESET_FAILED", False,
            "Token non valido o scaduto", ip, user_agent
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token non valido o scaduto. Richiedi un nuovo link di reset."
        )

    user_id = token_info["id_operatore"]
    username = token_info["username"]
    email = token_info["email"]

    try:
        # Aggiorna password
        db.execute(
            "UPDATE OPERATORI SET password_hash = %s, updated_at = NOW() WHERE id_operatore = %s",
            (hash_password(data.nuova_password), user_id)
        )

        # Marca token come usato
        _mark_token_used(db, data.token)

        # Revoca tutte le sessioni
        _revoke_all_user_sessions(db, user_id, user_id)

        db.commit()

        # Log successo
        _log_auth_action(
            db, user_id, username, "PASSWORD_RESET", True,
            "Password reimpostata via token", ip, user_agent
        )

        # Invia email conferma (best effort)
        try:
            from ..services.email.sender import EmailSender
            sender = EmailSender(db)
            if sender.is_configured(db) and email:
                sender.send_from_template(
                    'password_reset_success',
                    {'username': username},
                    to=email
                )
        except Exception as e:
            print(f"[WARN] Errore invio email conferma: {e}")

        return ResetPasswordResponse()

    except Exception as e:
        db.rollback()
        _log_auth_action(
            db, user_id, username, "PASSWORD_RESET_FAILED", False,
            f"Errore: {str(e)}", ip, user_agent
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Errore durante il reset della password. Riprova."
        )
