# =============================================================================
# SERV.O - WRITE GUARD MIDDLEWARE
# =============================================================================
# Chokepoint unico di sicurezza per le operazioni di SCRITTURA.
#
# Obiettivo: garantire l'INVIOLABILITÀ dei contenuti per gli utenti READ ONLY
# (e chiudere il buco degli endpoint senza autenticazione) a livello di
# middleware globale, senza dipendere dal fatto che ogni singolo endpoint
# dichiari la dependency corretta.
#
# Regole (solo per metodi non-sicuri: POST/PUT/PATCH/DELETE su /api/v1):
#   1. Path pubblici (login, recupero password)      -> passa (nessun token).
#   2. Nessun token valido                           -> 401.
#   3. Token valido con ruolo 'readonly':
#        - path in whitelist self-service            -> passa.
#        - altrimenti                                 -> 403.
#   4. Qualsiasi altro ruolo autenticato             -> passa (i controlli
#        granulari restano a carico degli endpoint).
#
# Metodi sicuri (GET/HEAD/OPTIONS) non vengono mai bloccati: la sola lettura
# è sempre consentita e i preflight CORS (OPTIONS) passano.
#
# Killswitch: env WRITE_GUARD_ENABLED=false disabilita il middleware.
# =============================================================================

import os
import re

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from .security import decode_access_token
from .models import RuoloUtente

API_PREFIX = "/api/v1"

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

# Operazioni di scrittura consentite SENZA autenticazione (pre-login).
PUBLIC_WRITE_PATHS = {
    f"{API_PREFIX}/auth/login",
    f"{API_PREFIX}/auth/forgot-password",
    f"{API_PREFIX}/auth/reset-password",
}

# Header e prefisso path su cui un servizio interno fidato (es. mail_monitor)
# puo' scrivere usando il token condiviso INTERNAL_API_TOKEN. Scoped al solo
# upload per principio di minimo privilegio: un token trapelato non potrebbe
# eliminare/modificare ordini.
INTERNAL_TOKEN_HEADER = "X-Internal-Token"
INTERNAL_TOKEN_ALLOWED_PREFIX = f"{API_PREFIX}/upload"

# Self-service consentito anche a 'readonly' (richiede comunque token valido).
# Nota: cambio-password e' ulteriormente protetto dall'endpoint stesso, che
# consente a un non-admin di cambiare solo la PROPRIA password (is_self).
READONLY_ALLOWED_EXACT = {
    f"{API_PREFIX}/auth/logout",
    f"{API_PREFIX}/auth/me/sessions/revoke-others",
    f"{API_PREFIX}/utenti/me/profilo",
    f"{API_PREFIX}/produttivita/heartbeat",
}
READONLY_ALLOWED_REGEX = [
    re.compile(rf"^{re.escape(API_PREFIX)}/utenti/\d+/cambio-password$"),
    re.compile(rf"^{re.escape(API_PREFIX)}/ordini/\d+/view$"),  # tracking visualizzazione, non modifica contenuti
]


def _readonly_allowed(path: str) -> bool:
    if path in READONLY_ALLOWED_EXACT:
        return True
    return any(rx.match(path) for rx in READONLY_ALLOWED_REGEX)


def _extract_payload(request: Request):
    """Decodifica il token Bearer dall'header Authorization. None se assente/invalido."""
    auth = request.headers.get("Authorization", "")
    if not auth.lower().startswith("bearer "):
        return None
    token = auth[7:].strip()
    if not token:
        return None
    try:
        return decode_access_token(token)
    except Exception:
        return None


class WriteGuardMiddleware(BaseHTTPMiddleware):
    """Blocca le scritture per utenti readonly e impone il login sui metodi non-sicuri."""

    def __init__(self, app):
        super().__init__(app)
        self.enabled = os.getenv("WRITE_GUARD_ENABLED", "true").lower() not in ("false", "0", "no")
        # Token condiviso per servizi interni fidati (es. mail_monitor che fa
        # POST /upload senza JWT). Vuoto = bypass disabilitato.
        self.internal_token = os.getenv("INTERNAL_API_TOKEN", "")

    async def dispatch(self, request: Request, call_next):
        if not self.enabled:
            return await call_next(request)

        method = request.method.upper()
        if method in SAFE_METHODS:
            return await call_next(request)

        path = request.url.path
        # Guardia attiva solo sulle rotte API; lascia passare il resto (static, ecc.)
        if not path.startswith(API_PREFIX):
            return await call_next(request)

        if path in PUBLIC_WRITE_PATHS:
            return await call_next(request)

        # Servizio interno fidato (es. mail_monitor) verso l'upload: bypass via
        # token condiviso. Attivo solo se INTERNAL_API_TOKEN e' configurato e
        # combacia, e solo sul prefisso upload.
        if (self.internal_token
                and path.startswith(INTERNAL_TOKEN_ALLOWED_PREFIX)
                and request.headers.get(INTERNAL_TOKEN_HEADER) == self.internal_token):
            return await call_next(request)

        payload = _extract_payload(request)
        if payload is None:
            print(f"🔒 WriteGuard: 401 {method} {path} (token assente/invalido)")
            return JSONResponse(
                status_code=401,
                content={"detail": "Autenticazione richiesta per questa operazione"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        if payload.ruolo == RuoloUtente.READONLY and not _readonly_allowed(path):
            print(f"🔒 WriteGuard: 403 {method} {path} (utente readonly '{payload.username}')")
            return JSONResponse(
                status_code=403,
                content={"detail": "Utente in sola lettura: operazione di modifica non consentita"},
            )

        return await call_next(request)
