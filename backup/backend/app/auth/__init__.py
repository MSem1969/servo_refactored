# =============================================================================
# TO_EXTRACTOR v6.2 - AUTH PACKAGE
# =============================================================================
# Package per autenticazione e autorizzazione.
# Esporta tutti i componenti pubblici per uso in altri moduli.
#
# USO:
#   from app.auth import (
#       RuoloUtente, UtenteResponse,
#       get_current_user, require_admin,
#       hash_password, verify_password,
#       auth_router
#   )
# =============================================================================

# =============================================================================
# MODELS
# =============================================================================
from .models import (
    # Enumerazioni
    RuoloUtente,
    CategoriaAzione,
    
    # Request models
    LoginRequest,
    LoginResponse,
    CreaUtenteRequest,
    ModificaUtenteRequest,
    ProfiloUpdateRequest,
    CambioPasswordRequest,
    DisabilitaUtenteRequest,
    
    # Response models
    UtenteResponse,
    UtenteListResponse,
    SessioneResponse,
    SessioniAttiveResponse,
    LogAttivitaResponse,
    LogAttivitaListResponse,
    
    # Internal
    TokenPayload
)

# =============================================================================
# SECURITY
# =============================================================================
from .security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    hash_token_for_storage,
    get_token_expiration_seconds,
    generate_temp_password,
    is_password_strong
)

# =============================================================================
# PERMISSIONS
# =============================================================================
from .permissions import (
    Permesso,
    get_permessi_ruolo,
    ha_permesso,
    puo_creare_ruolo,
    get_ruoli_creabili,
    puo_disabilitare_utente,
    get_home_page,
    get_sezioni_visibili,
    puo_accedere_sezione
)

# =============================================================================
# DEPENDENCIES
# =============================================================================
from .dependencies import (
    get_current_user,
    get_current_user_optional,
    require_permission,
    require_roles,
    require_admin,
    require_admin_or_supervisor,
    get_client_ip,
    get_user_agent
)

# =============================================================================
# ROUTER
# =============================================================================
from .router import router as auth_router


# =============================================================================
# __all__ - Lista esplicita export pubblici
# =============================================================================
__all__ = [
    # Models - Enumerazioni
    "RuoloUtente",
    "CategoriaAzione",
    
    # Models - Request
    "LoginRequest",
    "LoginResponse",
    "CreaUtenteRequest",
    "ModificaUtenteRequest",
    "ProfiloUpdateRequest",
    "CambioPasswordRequest",
    "DisabilitaUtenteRequest",
    
    # Models - Response
    "UtenteResponse",
    "UtenteListResponse",
    "SessioneResponse",
    "SessioniAttiveResponse",
    "LogAttivitaResponse",
    "LogAttivitaListResponse",
    "TokenPayload",
    
    # Security
    "hash_password",
    "verify_password",
    "create_access_token",
    "decode_access_token",
    "hash_token_for_storage",
    "get_token_expiration_seconds",
    "generate_temp_password",
    "is_password_strong",
    
    # Permissions
    "Permesso",
    "get_permessi_ruolo",
    "ha_permesso",
    "puo_creare_ruolo",
    "get_ruoli_creabili",
    "puo_disabilitare_utente",
    "get_home_page",
    "get_sezioni_visibili",
    "puo_accedere_sezione",
    
    # Dependencies
    "get_current_user",
    "get_current_user_optional",
    "require_permission",
    "require_roles",
    "require_admin",
    "require_admin_or_supervisor",
    "get_client_ip",
    "get_user_agent",
    
    # Router
    "auth_router"
]
