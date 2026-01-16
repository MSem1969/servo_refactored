# =============================================================================
# SERV.O v8.1 - EMAIL ROUTER
# =============================================================================
# Endpoint per configurazione e gestione email (IMAP/SMTP).
# =============================================================================

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional
from pydantic import BaseModel, EmailStr

from ..auth.dependencies import get_current_user, require_admin
from ..auth.models import UtenteResponse
from ..database_pg import get_db
from ..services.email import (
    email_config,
    EmailSender,
    get_email_log
)
from ..services.email.providers.gmail import GmailProvider


router = APIRouter(prefix="/email", tags=["email"])


# =============================================================================
# MODELLI REQUEST
# =============================================================================

class EmailConfigUpdate(BaseModel):
    """Aggiornamento configurazione email (no password!)"""
    imap_enabled: Optional[bool] = None
    imap_host: Optional[str] = None
    imap_port: Optional[int] = None
    imap_use_ssl: Optional[bool] = None
    imap_folder: Optional[str] = None
    imap_unread_only: Optional[bool] = None
    imap_mark_as_read: Optional[bool] = None
    imap_apply_label: Optional[str] = None
    imap_subject_keywords: Optional[str] = None
    imap_sender_whitelist: Optional[str] = None
    imap_max_emails_per_run: Optional[int] = None

    smtp_enabled: Optional[bool] = None
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_use_tls: Optional[bool] = None
    smtp_sender_email: Optional[str] = None
    smtp_sender_name: Optional[str] = None
    smtp_rate_limit: Optional[int] = None

    # Email notifiche admin (comma-separated)
    admin_notifica_email: Optional[str] = None


class TestEmailRequest(BaseModel):
    """Request per invio email di test"""
    destinatario: EmailStr


# =============================================================================
# ENDPOINTS CONFIGURAZIONE
# =============================================================================

@router.get("/config")
async def get_config(
    current_user: UtenteResponse = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Recupera configurazione email completa.
    NON include password - solo flag se configurate.

    Richiede: Admin
    """
    try:
        db = get_db()
        status = email_config.get_status(db)
        return {"success": True, "data": status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/config")
async def update_config(
    data: EmailConfigUpdate,
    current_user: UtenteResponse = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Aggiorna configurazione email.
    NON aggiorna password - quelle vanno nel file .env!

    Richiede: Admin
    """
    try:
        db = get_db()
        # Converti a dict escludendo None
        update_data = {k: v for k, v in data.dict().items() if v is not None}

        if not update_data:
            return {"success": True, "message": "Nessun campo da aggiornare"}

        email_config.update_settings(db, update_data, current_user.id_operatore)
        return {"success": True, "message": "Configurazione aggiornata"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config/imap")
async def get_imap_config(
    current_user: UtenteResponse = Depends(require_admin)
) -> Dict[str, Any]:
    """Recupera solo configurazione IMAP"""
    try:
        db = get_db()
        settings = email_config.get_settings(db, 'imap')
        settings['credentials_configured'] = email_config.credentials_configured('imap')
        return {"success": True, "data": settings}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config/smtp")
async def get_smtp_config(
    current_user: UtenteResponse = Depends(require_admin)
) -> Dict[str, Any]:
    """Recupera solo configurazione SMTP"""
    try:
        db = get_db()
        settings = email_config.get_settings(db, 'smtp')
        settings['credentials_configured'] = email_config.credentials_configured('smtp')
        # Fallback su credenziali IMAP
        if not settings['credentials_configured']:
            settings['credentials_configured'] = email_config.credentials_configured('imap')
            settings['using_imap_credentials'] = True
        return {"success": True, "data": settings}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# ENDPOINTS TEST
# =============================================================================

@router.post("/test/imap")
async def test_imap_connection(
    current_user: UtenteResponse = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Test connessione IMAP.
    Usa credenziali da .env + settings da database.

    Richiede: Admin
    """
    try:
        db = get_db()

        # Verifica credenziali
        if not email_config.credentials_configured('imap'):
            return {
                "success": False,
                "error": "Credenziali IMAP non configurate. Aggiungere IMAP_USER e IMAP_PASSWORD al file .env"
            }

        # Ottieni config completa
        config = email_config.get_full_config(db, 'imap')
        provider = GmailProvider(config)
        result = provider.test_imap_connection()

        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/test/smtp")
async def test_smtp_connection(
    data: Optional[TestEmailRequest] = None,
    current_user: UtenteResponse = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Test connessione SMTP.
    Se fornito destinatario, invia email di test.

    Richiede: Admin
    """
    try:
        db = get_db()

        # Verifica credenziali (SMTP o fallback IMAP)
        has_creds = email_config.credentials_configured('smtp') or email_config.credentials_configured('imap')
        if not has_creds:
            return {
                "success": False,
                "error": "Credenziali SMTP non configurate. Aggiungere SMTP_USER e SMTP_PASSWORD (o IMAP_*) al file .env"
            }

        if data and data.destinatario:
            # Invia email di test
            sender = EmailSender(db)
            result = sender.send_test_email(data.destinatario)
            if result['success']:
                result['message'] = f"Email di test inviata a {data.destinatario}"
            return result
        else:
            # Solo test connessione
            config = email_config.get_full_config(db, 'smtp')
            # Fallback credenziali IMAP
            if not config.get('smtp_user'):
                imap_config = email_config.get_full_config(db, 'imap')
                config['smtp_user'] = imap_config.get('imap_user')
                config['smtp_password'] = imap_config.get('imap_password')

            provider = GmailProvider(config)
            return provider.test_smtp_connection()

    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# ENDPOINTS LOG
# =============================================================================

@router.get("/log")
async def get_log(
    stato_invio: Optional[str] = None,
    tipo: Optional[str] = None,
    ticket_id: Optional[int] = None,
    limit: int = 100,
    offset: int = 0,
    current_user: UtenteResponse = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Recupera log email inviate.

    Richiede: Admin
    """
    try:
        db = get_db()
        filters = {}
        if stato_invio:
            filters['stato_invio'] = stato_invio
        if tipo:
            filters['tipo'] = tipo
        if ticket_id:
            filters['ticket_id'] = ticket_id

        logs = get_email_log(db, filters, limit, offset)
        return {"success": True, "data": logs, "count": len(logs)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/log/{log_id}/retry")
async def retry_email(
    log_id: int,
    current_user: UtenteResponse = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Ritenta invio email fallita.

    Richiede: Admin
    """
    try:
        from ..services.email.log import mark_for_retry
        db = get_db()

        success = mark_for_retry(db, log_id)
        if success:
            return {"success": True, "message": "Email marcata per retry"}
        else:
            return {"success": False, "error": "Email non trovata o non in stato 'failed'"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
