# =============================================================================
# TO_EXTRACTOR v6.2 - AUTH DEPENDENCIES
# =============================================================================
# FastAPI dependencies per protezione route e estrazione utente corrente.
# Questi dependency vengono iniettati automaticamente negli endpoint protetti.
#
# COMPONENTI:
# - security_scheme: estrazione token da header
# - get_current_user: dependency principale (obbligatorio)
# - get_current_user_optional: per route che funzionano con/senza auth
# - require_permission: factory per richiedere permesso specifico
# - require_roles: factory per richiedere ruolo specifico
# - Helper per estrazione IP e User-Agent
# =============================================================================

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import sqlite3

from .models import TokenPayload, RuoloUtente, UtenteResponse
from .security import decode_access_token, hash_token_for_storage
from .permissions import ha_permesso, Permesso


# =============================================================================
# SCHEMA AUTENTICAZIONE
# =============================================================================

# HTTPBearer estrae automaticamente il token dall'header
# "Authorization: Bearer <token>"
security_scheme = HTTPBearer(
    scheme_name="JWT",
    description="Token JWT ottenuto dal login",
    auto_error=False  # Non solleva eccezione automatica, gestiamo noi per messaggi custom
)


# =============================================================================
# IMPORT DATABASE (lazy per evitare circular imports)
# =============================================================================

def _get_db():
    """Import lazy del database per evitare circular imports."""
    from ..database_pg import get_db
    return get_db()


# =============================================================================
# FUNZIONI HELPER DATABASE
# =============================================================================

def _get_user_by_id(db: sqlite3.Connection, user_id: int) -> Optional[dict]:
    """
    Recupera utente dal database per ID.
    
    Args:
        db: connessione database
        user_id: id_operatore da cercare
        
    Returns:
        Dict con dati utente o None se non trovato
        
    Campi recuperati:
        - Tutti i campi OPERATORI necessari per UtenteResponse
        - NON include password_hash per sicurezza
    """
    cursor = db.execute(
        """
        SELECT 
            id_operatore, username, nome, cognome, email,
            ruolo, attivo, data_creazione, created_by_operatore,
            last_login_at, disabled_at, disabled_by_operatore,
            disable_reason, updated_at
        FROM OPERATORI 
        WHERE id_operatore = ?
        """,
        (user_id,)
    )
    row = cursor.fetchone()
    
    if row:
        return dict(row)
    return None


def _is_session_valid(db: sqlite3.Connection, token_hash: str) -> bool:
    """
    Verifica se la sessione (token) è ancora valida nel database.
    
    Una sessione è valida se:
    1. Esiste nel database (token_hash match)
    2. Non è stata revocata (revoked_at IS NULL)
    3. Non è scaduta (expires_at > now)
    
    Args:
        db: connessione database
        token_hash: hash SHA256 del token JWT
        
    Returns:
        True se sessione valida e attiva
    """
    cursor = db.execute(
        """
        SELECT id_session 
        FROM USER_SESSIONS 
        WHERE token_hash = ? 
          AND revoked_at IS NULL 
          AND datetime(expires_at) > datetime('now')
        """,
        (token_hash,)
    )
    return cursor.fetchone() is not None


def _log_access_attempt(
    db: sqlite3.Connection,
    user_id: Optional[int],
    username: Optional[str],
    action: str,
    success: bool,
    error_message: Optional[str],
    ip_address: Optional[str],
    user_agent: Optional[str]
):
    """
    Registra tentativo di accesso nel log audit.
    
    Chiamato per:
    - Accessi negati (token mancante/invalido)
    - Utenti disabilitati che tentano accesso
    - Sessioni revocate
    
    Args:
        db: connessione database
        user_id: id utente se noto (None se token invalido)
        username: username se noto
        action: tipo azione (ACCESS_DENIED, LOGIN_FAILED, etc.)
        success: sempre False per tentativi falliti
        error_message: descrizione errore
        ip_address: IP client
        user_agent: browser/client info
    """
    try:
        db.execute(
            """
            INSERT INTO LOG_OPERAZIONI (
                tipo_operazione, action_category, entita, id_entita,
                descrizione, id_operatore, username_snapshot,
                success, error_message, ip_address, user_agent
            ) VALUES (?, 'AUTH', 'operatore', ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                action,
                user_id,
                f"Tentativo {action}",
                user_id or 0,  # 0 se utente sconosciuto
                username,
                1 if success else 0,
                error_message,
                ip_address,
                user_agent
            )
        )
        db.commit()
    except Exception as e:
        # Non bloccare il flusso se logging fallisce
        print(f"Warning: impossibile loggare tentativo accesso: {e}")


# =============================================================================
# ESTRAZIONE INFO REQUEST
# =============================================================================

def get_client_ip(request: Request) -> str:
    """
    Estrae IP client dalla request.
    
    Gestisce proxy (header X-Forwarded-For).
    
    Args:
        request: FastAPI Request object
        
    Returns:
        IP address come stringa (es. "192.168.1.100")
        
    Note:
        - X-Forwarded-For può contenere lista: "client, proxy1, proxy2"
        - Prendiamo il primo (client originale)
    """
    # Prima controlla header proxy
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Prendi il primo IP (client originale)
        return forwarded.split(",")[0].strip()
    
    # Altrimenti usa IP diretto dalla connessione
    if request.client:
        return request.client.host
    
    return "unknown"


def get_user_agent(request: Request) -> str:
    """
    Estrae User-Agent dalla request.
    
    Args:
        request: FastAPI Request object
        
    Returns:
        User-Agent string o "unknown"
        
    Uso:
        - Logging per audit
        - Identificazione dispositivi nelle sessioni
    """
    return request.headers.get("User-Agent", "unknown")


# =============================================================================
# DEPENDENCY: GET CURRENT USER (OPZIONALE)
# =============================================================================

async def get_current_user_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme)
) -> Optional[UtenteResponse]:
    """
    Dependency che estrae l'utente corrente se autenticato.
    NON solleva eccezione se non autenticato - ritorna None.
    
    Uso: endpoint che funzionano sia con che senza autenticazione.
    Es: endpoint pubblici che mostrano più info se autenticati.
    
    Args:
        request: FastAPI Request
        credentials: token Bearer estratto da header (opzionale)
        
    Returns:
        UtenteResponse se autenticato valido, None altrimenti
        
    Esempio uso:
        @router.get("/info")
        async def get_info(user: Optional[UtenteResponse] = Depends(get_current_user_optional)):
            if user:
                return {"info": "dettagliata", "user": user.username}
            return {"info": "base"}
    """
    if not credentials:
        return None
    
    db = _get_db()
    token = credentials.credentials
    
    # 1. Decodifica e valida JWT
    payload = decode_access_token(token)
    if not payload:
        return None
    
    # 2. Verifica sessione non revocata
    token_hash = hash_token_for_storage(token)
    if not _is_session_valid(db, token_hash):
        return None
    
    # 3. Recupera utente dal DB
    user_data = _get_user_by_id(db, payload.sub)
    if not user_data:
        return None
    
    # 4. Verifica utente ancora attivo
    if not user_data["attivo"]:
        return None
    
    # 5. Costruisci e ritorna response
    return UtenteResponse(
        id_operatore=user_data["id_operatore"],
        username=user_data["username"],
        nome=user_data["nome"],
        cognome=user_data["cognome"],
        email=user_data["email"],
        ruolo=RuoloUtente(user_data["ruolo"].lower()),
        attivo=bool(user_data["attivo"]),
        data_creazione=user_data["data_creazione"],
        created_by_operatore=user_data["created_by_operatore"],
        last_login_at=user_data["last_login_at"],
        disabled_at=user_data["disabled_at"],
        disabled_by_operatore=user_data["disabled_by_operatore"],
        disable_reason=user_data["disable_reason"]
    )


# =============================================================================
# DEPENDENCY: GET CURRENT USER (OBBLIGATORIO)
# =============================================================================

async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme)
) -> UtenteResponse:
    """
    Dependency che estrae l'utente corrente autenticato.
    SOLLEVA ECCEZIONE se non autenticato o token invalido.
    
    Uso: endpoint che richiedono autenticazione obbligatoria.
    È il dependency più usato per proteggere le route.
    
    Args:
        request: FastAPI Request
        credentials: token Bearer estratto da header
        
    Returns:
        UtenteResponse dell'utente autenticato
        
    Raises:
        HTTPException 401: se non autenticato o token invalido
        HTTPException 403: se utente disabilitato
        
    Esempio uso:
        @router.get("/protected")
        async def protected_endpoint(user: UtenteResponse = Depends(get_current_user)):
            return {"message": f"Ciao {user.username}"}
    """
    db = _get_db()
    ip = get_client_ip(request)
    user_agent = get_user_agent(request)
    
    # 1. Verifica presenza token
    if not credentials:
        _log_access_attempt(
            db, None, None, "ACCESS_DENIED", 
            False, "Token mancante", ip, user_agent
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token di autenticazione richiesto",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    token = credentials.credentials
    
    # 2. Decodifica e valida JWT (firma + scadenza)
    payload = decode_access_token(token)
    if not payload:
        _log_access_attempt(
            db, None, None, "ACCESS_DENIED",
            False, "Token invalido o scaduto", ip, user_agent
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido o scaduto",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # 3. Verifica sessione non revocata nel DB
    token_hash = hash_token_for_storage(token)
    if not _is_session_valid(db, token_hash):
        _log_access_attempt(
            db, payload.sub, payload.username, "ACCESS_DENIED",
            False, "Sessione revocata", ip, user_agent
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessione non valida o revocata",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # 4. Recupera utente dal DB (dati potrebbero essere cambiati)
    user_data = _get_user_by_id(db, payload.sub)
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utente non trovato",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # 5. Verifica utente ancora attivo
    if not user_data["attivo"]:
        _log_access_attempt(
            db, payload.sub, payload.username, "ACCESS_DENIED",
            False, "Utente disabilitato", ip, user_agent
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Utente disabilitato"
        )
    
    # 6. Costruisci e ritorna response
    return UtenteResponse(
        id_operatore=user_data["id_operatore"],
        username=user_data["username"],
        nome=user_data["nome"],
        cognome=user_data["cognome"],
        email=user_data["email"],
        ruolo=RuoloUtente(user_data["ruolo"].lower()),
        attivo=bool(user_data["attivo"]),
        data_creazione=user_data["data_creazione"],
        created_by_operatore=user_data["created_by_operatore"],
        last_login_at=user_data["last_login_at"],
        disabled_at=user_data["disabled_at"],
        disabled_by_operatore=user_data["disabled_by_operatore"],
        disable_reason=user_data["disable_reason"]
    )


# =============================================================================
# DEPENDENCY FACTORY: RICHIEDI PERMESSO SPECIFICO
# =============================================================================

def require_permission(permesso: str):
    """
    Factory che crea un dependency per richiedere un permesso specifico.
    
    Args:
        permesso: stringa permesso richiesto (da classe Permesso)
        
    Returns:
        Dependency function che verifica il permesso
        
    Esempio uso:
        @router.get("/admin-only")
        async def admin_endpoint(
            user: UtenteResponse = Depends(require_permission(Permesso.BACKEND_FULL))
        ):
            return {"message": "Solo admin possono vedere questo"}
    """
    async def permission_checker(
        current_user: UtenteResponse = Depends(get_current_user)
    ) -> UtenteResponse:
        """
        Verifica che l'utente corrente abbia il permesso richiesto.
        
        Raises:
            HTTPException 403: se permesso mancante
        """
        if not ha_permesso(current_user.ruolo, permesso):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permesso richiesto: {permesso}"
            )
        return current_user
    
    return permission_checker


# =============================================================================
# DEPENDENCY FACTORY: RICHIEDI UNO DEI RUOLI
# =============================================================================

def require_roles(*ruoli: RuoloUtente):
    """
    Factory che crea un dependency per richiedere uno dei ruoli specificati.
    
    Args:
        *ruoli: ruoli accettati (logica OR - basta uno)
        
    Returns:
        Dependency function che verifica il ruolo
        
    Esempio uso:
        @router.get("/supervisors-admins")
        async def endpoint(
            user: UtenteResponse = Depends(require_roles(
                RuoloUtente.ADMIN, 
                RuoloUtente.SUPERVISORE
            ))
        ):
            return {"message": "Admin o Supervisore"}
    """
    async def role_checker(
        current_user: UtenteResponse = Depends(get_current_user)
    ) -> UtenteResponse:
        """
        Verifica che l'utente corrente abbia uno dei ruoli richiesti.
        
        Raises:
            HTTPException 403: se ruolo non autorizzato
        """
        if current_user.ruolo not in ruoli:
            ruoli_str = ", ".join([r.value for r in ruoli])
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Ruolo richiesto: {ruoli_str}"
            )
        return current_user
    
    return role_checker


# =============================================================================
# DEPENDENCY: SOLO ADMIN
# =============================================================================

async def require_admin(
    current_user: UtenteResponse = Depends(get_current_user)
) -> UtenteResponse:
    """
    Dependency che richiede ruolo admin.
    
    Shortcut per require_roles(RuoloUtente.ADMIN).
    
    Raises:
        HTTPException 403: se non admin
        
    Esempio:
        @router.delete("/danger")
        async def danger(user: UtenteResponse = Depends(require_admin)):
            ...
    """
    if current_user.ruolo != RuoloUtente.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Richiesto ruolo amministratore"
        )
    return current_user


# =============================================================================
# DEPENDENCY: ADMIN O SUPERVISORE
# =============================================================================

async def require_admin_or_supervisor(
    current_user: UtenteResponse = Depends(get_current_user)
) -> UtenteResponse:
    """
    Dependency che richiede ruolo admin o supervisore.
    
    Uso comune per endpoint gestione utenti dove entrambi hanno accesso
    (con scope diversi gestiti nel router).
    
    Raises:
        HTTPException 403: se né admin né supervisore
        
    Esempio:
        @router.get("/utenti")
        async def list_users(user: UtenteResponse = Depends(require_admin_or_supervisor)):
            # Admin vede tutti, supervisore vede solo i suoi operatori
            ...
    """
    if current_user.ruolo not in [RuoloUtente.ADMIN, RuoloUtente.SUPERVISORE]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Richiesto ruolo amministratore o supervisore"
        )
    return current_user
