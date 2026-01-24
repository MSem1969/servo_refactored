# =============================================================================
# SERV.O v8.1 - ECCEZIONI CENTRALIZZATE
# =============================================================================
# Sistema di eccezioni custom per gestione errori uniforme
# =============================================================================

from fastapi import HTTPException
from typing import Optional, Dict, Any


class ServoException(Exception):
    """
    Eccezione base per SERV.O.

    Tutte le eccezioni custom devono estendere questa classe.
    Fornisce conversione automatica a HTTPException.
    """
    status_code: int = 500
    code: str = "INTERNAL_ERROR"
    detail: str = "Errore interno del server"

    def __init__(self, detail: Optional[str] = None, extra: Dict[str, Any] = None):
        self.detail = detail or self.__class__.detail
        self.extra = extra or {}
        super().__init__(self.detail)

    def to_http_exception(self) -> HTTPException:
        """Converte in HTTPException per FastAPI."""
        return HTTPException(
            status_code=self.status_code,
            detail={
                "code": self.code,
                "message": self.detail,
                **self.extra
            }
        )

    def to_dict(self) -> Dict[str, Any]:
        """Converte in dizionario per logging."""
        return {
            "code": self.code,
            "status_code": self.status_code,
            "message": self.detail,
            **self.extra
        }


# =============================================================================
# ECCEZIONI HTTP STANDARD
# =============================================================================

class NotFoundError(ServoException):
    """Risorsa non trovata (404)."""
    status_code = 404
    code = "NOT_FOUND"
    detail = "Risorsa non trovata"


class ValidationError(ServoException):
    """Errore di validazione dati (400)."""
    status_code = 400
    code = "VALIDATION_ERROR"
    detail = "Errore di validazione"


class ConflictError(ServoException):
    """Conflitto con stato attuale (409)."""
    status_code = 409
    code = "CONFLICT"
    detail = "Conflitto con lo stato attuale della risorsa"


class UnauthorizedError(ServoException):
    """Autenticazione richiesta (401)."""
    status_code = 401
    code = "UNAUTHORIZED"
    detail = "Autenticazione richiesta"


class ForbiddenError(ServoException):
    """Permessi insufficienti (403)."""
    status_code = 403
    code = "FORBIDDEN"
    detail = "Permessi insufficienti"


class BadRequestError(ServoException):
    """Richiesta malformata (400)."""
    status_code = 400
    code = "BAD_REQUEST"
    detail = "Richiesta non valida"


# =============================================================================
# ECCEZIONI DOMINIO - ORDINI
# =============================================================================

class OrdineNotFoundError(NotFoundError):
    """Ordine non trovato."""
    code = "ORDINE_NOT_FOUND"
    detail = "Ordine non trovato"


class OrdineGiaEsportatoError(ConflictError):
    """Ordine già esportato, non modificabile."""
    code = "ORDINE_GIA_ESPORTATO"
    detail = "Ordine già esportato e non modificabile"


class OrdineStatoInvalidoError(ConflictError):
    """Transizione di stato ordine non valida."""
    code = "ORDINE_STATO_INVALIDO"
    detail = "Transizione di stato non valida per questo ordine"


class RigaNotFoundError(NotFoundError):
    """Riga ordine non trovata."""
    code = "RIGA_NOT_FOUND"
    detail = "Riga ordine non trovata"


# =============================================================================
# ECCEZIONI DOMINIO - SUPERVISIONE
# =============================================================================

class SupervisioneNotFoundError(NotFoundError):
    """Supervisione non trovata."""
    code = "SUPERVISIONE_NOT_FOUND"
    detail = "Supervisione non trovata"


class SupervisioneGiaProcessataError(ConflictError):
    """Supervisione già processata."""
    code = "SUPERVISIONE_GIA_PROCESSATA"
    detail = "Supervisione già approvata o rifiutata"


class PatternNotFoundError(NotFoundError):
    """Pattern ML non trovato."""
    code = "PATTERN_NOT_FOUND"
    detail = "Pattern ML non trovato"


# =============================================================================
# ECCEZIONI DOMINIO - ANOMALIE
# =============================================================================

class AnomaliaNotFoundError(NotFoundError):
    """Anomalia non trovata."""
    code = "ANOMALIA_NOT_FOUND"
    detail = "Anomalia non trovata"


class AnomaliaGiaRisoltaError(ConflictError):
    """Anomalia già risolta."""
    code = "ANOMALIA_GIA_RISOLTA"
    detail = "Anomalia già risolta o ignorata"


# =============================================================================
# ECCEZIONI DOMINIO - LOOKUP/ANAGRAFICA
# =============================================================================

class FarmaciaNotFoundError(NotFoundError):
    """Farmacia non trovata in anagrafica."""
    code = "FARMACIA_NOT_FOUND"
    detail = "Farmacia non trovata in anagrafica"


class LookupFailedError(ServoException):
    """Lookup farmacia fallito."""
    status_code = 422
    code = "LOOKUP_FAILED"
    detail = "Impossibile identificare la farmacia"


# =============================================================================
# ECCEZIONI DOMINIO - ESTRAZIONE PDF
# =============================================================================

class ExtractionError(ServoException):
    """Errore durante estrazione PDF."""
    status_code = 422
    code = "EXTRACTION_ERROR"
    detail = "Errore durante l'estrazione del PDF"


class VendorNotRecognizedError(ExtractionError):
    """Vendor non riconosciuto nel PDF."""
    code = "VENDOR_NOT_RECOGNIZED"
    detail = "Impossibile riconoscere il vendor dal PDF"


class PDFCorruptError(ExtractionError):
    """PDF corrotto o non leggibile."""
    code = "PDF_CORRUPT"
    detail = "Il file PDF è corrotto o non leggibile"


# =============================================================================
# ECCEZIONI DOMINIO - EXPORT TRACCIATI
# =============================================================================

class ExportError(ServoException):
    """Errore durante export tracciato."""
    status_code = 422
    code = "EXPORT_ERROR"
    detail = "Errore durante la generazione del tracciato"


class NessunaRigaEsportabileError(ExportError):
    """Nessuna riga da esportare."""
    code = "NESSUNA_RIGA_ESPORTABILE"
    detail = "Nessuna riga con quantità da esportare"


class DatiMancantiError(ExportError):
    """Dati obbligatori mancanti per export."""
    code = "DATI_MANCANTI"
    detail = "Dati obbligatori mancanti per la generazione del tracciato"


# =============================================================================
# ECCEZIONI DOMINIO - AUTENTICAZIONE
# =============================================================================

class InvalidCredentialsError(UnauthorizedError):
    """Credenziali non valide."""
    code = "INVALID_CREDENTIALS"
    detail = "Username o password non validi"


class TokenExpiredError(UnauthorizedError):
    """Token JWT scaduto."""
    code = "TOKEN_EXPIRED"
    detail = "Token di autenticazione scaduto"


class TokenInvalidError(UnauthorizedError):
    """Token JWT non valido."""
    code = "TOKEN_INVALID"
    detail = "Token di autenticazione non valido"


class UserDisabledError(ForbiddenError):
    """Utente disabilitato."""
    code = "USER_DISABLED"
    detail = "Account utente disabilitato"


class InsufficientRoleError(ForbiddenError):
    """Ruolo insufficiente per l'operazione."""
    code = "INSUFFICIENT_ROLE"
    detail = "Ruolo insufficiente per questa operazione"


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def raise_not_found(resource: str, id_value: Any = None) -> None:
    """
    Solleva eccezione NotFoundError con messaggio personalizzato.

    Args:
        resource: Nome risorsa (es. "Ordine", "Supervisione")
        id_value: ID risorsa opzionale

    Raises:
        NotFoundError
    """
    detail = f"{resource} non trovato"
    if id_value is not None:
        detail = f"{resource} con ID {id_value} non trovato"
    raise NotFoundError(detail=detail).to_http_exception()


def raise_validation_error(message: str, field: str = None) -> None:
    """
    Solleva eccezione ValidationError.

    Args:
        message: Messaggio di errore
        field: Campo che ha causato l'errore

    Raises:
        ValidationError
    """
    extra = {"field": field} if field else {}
    raise ValidationError(detail=message, extra=extra).to_http_exception()


def raise_conflict(message: str, current_state: str = None) -> None:
    """
    Solleva eccezione ConflictError.

    Args:
        message: Messaggio di errore
        current_state: Stato attuale della risorsa

    Raises:
        ConflictError
    """
    extra = {"current_state": current_state} if current_state else {}
    raise ConflictError(detail=message, extra=extra).to_http_exception()
