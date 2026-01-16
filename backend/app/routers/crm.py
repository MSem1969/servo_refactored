# =============================================================================
# SERV.O v8.1 - CRM ROUTER
# =============================================================================
# Endpoint per sistema CRM/Ticketing.
# =============================================================================

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.responses import FileResponse
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, EmailStr, Field
import os

from ..auth.dependencies import get_current_user, require_admin
from ..auth.models import UtenteResponse
from ..database_pg import get_db
from ..services.crm import (
    TicketStatus,
    TicketCategory,
    TicketPriority,
    get_tickets,
    get_ticket_detail,
    create_ticket,
    update_ticket_status,
    get_ticket_stats,
    get_messages,
    add_message,
    send_ticket_notification,
    save_attachment,
    get_attachments,
    get_attachment,
    delete_attachment
)
from ..services.crm.notifications import (
    notify_ticket_created,
    notify_status_changed,
    notify_new_reply
)


router = APIRouter(prefix="/crm", tags=["crm"])


# =============================================================================
# MODELLI REQUEST
# =============================================================================

class CreateTicketRequest(BaseModel):
    """Request creazione ticket"""
    categoria: str = Field(..., description="suggerimento o bug_report")
    oggetto: str = Field(..., min_length=5, max_length=200)
    contenuto: str = Field(..., min_length=10)
    pagina_origine: Optional[str] = None
    pagina_dettaglio: Optional[str] = None
    email_notifica: Optional[EmailStr] = None
    priorita: Optional[str] = "normale"


class UpdateStatusRequest(BaseModel):
    """Request cambio stato ticket"""
    stato: str = Field(..., description="aperto, in_lavorazione, chiuso")


class AddMessageRequest(BaseModel):
    """Request nuovo messaggio"""
    contenuto: str = Field(..., min_length=1)


class UpdateTicketRequest(BaseModel):
    """Request aggiornamento ticket"""
    priorita: Optional[str] = None
    email_notifica: Optional[EmailStr] = None


# =============================================================================
# ENDPOINTS TICKETS
# =============================================================================

@router.get("/tickets")
async def list_tickets(
    stato: Optional[str] = None,
    categoria: Optional[str] = None,
    priorita: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    current_user: UtenteResponse = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Lista ticket.
    - Admin: vede tutti i ticket
    - User: vede solo i propri ticket
    """
    try:
        db = get_db()
        is_admin = current_user.ruolo in ['admin', 'superuser']

        filters = {}
        if stato:
            filters['stato'] = stato
        if categoria:
            filters['categoria'] = categoria
        if priorita:
            filters['priorita'] = priorita
        if search:
            filters['search'] = search

        tickets = get_tickets(
            db,
            filters=filters,
            user_id=current_user.id_operatore,
            is_admin=is_admin,
            limit=limit,
            offset=offset
        )

        return {"success": True, "data": tickets, "count": len(tickets)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tickets")
async def create_new_ticket(
    data: CreateTicketRequest,
    current_user: UtenteResponse = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Crea nuovo ticket.
    Qualsiasi utente autenticato puo creare ticket.
    """
    try:
        # Validazione categoria
        if data.categoria not in TicketCategory.ALL:
            raise HTTPException(
                status_code=400,
                detail=f"Categoria non valida. Valori: {TicketCategory.ALL}"
            )

        # Validazione priorita
        if data.priorita and data.priorita not in TicketPriority.ALL:
            raise HTTPException(
                status_code=400,
                detail=f"Priorita non valida. Valori: {TicketPriority.ALL}"
            )

        db = get_db()
        result = create_ticket(db, data.dict(), current_user.id_operatore)

        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('error', 'Errore creazione'))

        # Prepara dati per notifiche email
        # v8.1: Aggiunto id_operatore per risoluzione email dinamica dal profilo
        ticket_data = {
            'id_ticket': result['id_ticket'],
            'id_operatore': current_user.id_operatore,
            'oggetto': data.oggetto,
            'categoria': data.categoria,
            'priorita': data.priorita,
            'pagina_origine': data.pagina_origine,
            'contenuto': data.contenuto,
            'email_notifica': data.email_notifica,
            'username': f"{current_user.nome} {current_user.cognome}"
        }

        # Invia notifiche (utente + admin)
        notify_ticket_created(db, ticket_data)

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tickets/{ticket_id}")
async def get_ticket(
    ticket_id: int,
    current_user: UtenteResponse = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Dettaglio ticket con messaggi.
    - Admin: vede qualsiasi ticket
    - User: vede solo propri ticket
    """
    try:
        db = get_db()
        is_admin = current_user.ruolo in ['admin', 'superuser']

        ticket = get_ticket_detail(
            db,
            ticket_id,
            user_id=current_user.id_operatore,
            is_admin=is_admin
        )

        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket non trovato")

        return {"success": True, "data": ticket}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/tickets/{ticket_id}/stato")
async def change_ticket_status(
    ticket_id: int,
    data: UpdateStatusRequest,
    current_user: UtenteResponse = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Cambia stato ticket.
    Richiede: Admin

    Transizioni valide:
    - aperto -> in_lavorazione, chiuso
    - in_lavorazione -> aperto, chiuso
    - chiuso -> aperto (riapertura)
    """
    try:
        # Validazione stato
        if data.stato not in TicketStatus.ALL:
            raise HTTPException(
                status_code=400,
                detail=f"Stato non valido. Valori: {TicketStatus.ALL}"
            )

        db = get_db()
        result = update_ticket_status(
            db,
            ticket_id,
            data.stato,
            current_user.id_operatore
        )

        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('error', 'Errore'))

        # Invia notifica email
        if result.get('email_notifica'):
            notify_status_changed(db, result)

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/tickets/{ticket_id}")
async def update_ticket(
    ticket_id: int,
    data: UpdateTicketRequest,
    current_user: UtenteResponse = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Aggiorna campi ticket (priorita, email_notifica).
    - Admin: puo modificare qualsiasi ticket
    - User: puo modificare solo propri ticket
    """
    try:
        from ..services.crm.tickets import update_ticket as update_ticket_fn

        db = get_db()
        is_admin = current_user.ruolo in ['admin', 'superuser']

        result = update_ticket_fn(
            db,
            ticket_id,
            data.dict(exclude_none=True),
            current_user.id_operatore,
            is_admin
        )

        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('error', 'Errore'))

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# ENDPOINTS MESSAGGI
# =============================================================================

@router.get("/tickets/{ticket_id}/messaggi")
async def list_messages(
    ticket_id: int,
    current_user: UtenteResponse = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Lista messaggi di un ticket.
    """
    try:
        db = get_db()
        is_admin = current_user.ruolo in ['admin', 'superuser']

        messages = get_messages(
            db,
            ticket_id,
            user_id=current_user.id_operatore,
            is_admin=is_admin
        )

        return {"success": True, "data": messages}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tickets/{ticket_id}/messaggi")
async def create_message(
    ticket_id: int,
    data: AddMessageRequest,
    current_user: UtenteResponse = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Aggiunge messaggio a ticket.
    - Admin: messaggio marcato come risposta admin
    - User: messaggio normale
    """
    try:
        db = get_db()
        is_admin = current_user.ruolo in ['admin', 'superuser']

        result = add_message(
            db,
            ticket_id,
            current_user.id_operatore,
            data.contenuto,
            is_admin=is_admin
        )

        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('error', 'Errore'))

        # Se admin risponde, notifica utente
        if is_admin and result.get('email_notifica'):
            notify_new_reply(db, result, data.contenuto)

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# ENDPOINTS STATISTICHE
# =============================================================================

@router.get("/stats")
async def get_crm_stats(
    current_user: UtenteResponse = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Statistiche ticket.
    - Admin: statistiche globali
    - User: statistiche propri ticket
    """
    try:
        db = get_db()
        is_admin = current_user.ruolo in ['admin', 'superuser']

        stats = get_ticket_stats(
            db,
            user_id=current_user.id_operatore,
            is_admin=is_admin
        )

        return {"success": True, "data": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# ENDPOINTS COSTANTI (per UI)
# =============================================================================

@router.get("/constants")
async def get_constants() -> Dict[str, Any]:
    """
    Ritorna costanti CRM per UI (stati, categorie, priorita).
    Endpoint pubblico per popolare dropdown.
    """
    return {
        "success": True,
        "data": {
            "stati": [
                {"value": s, "label": TicketStatus.LABELS.get(s, s)}
                for s in TicketStatus.ALL
            ],
            "categorie": [
                {"value": c, "label": TicketCategory.LABELS.get(c, c)}
                for c in TicketCategory.ALL
            ],
            "priorita": [
                {"value": p, "label": TicketPriority.LABELS.get(p, p)}
                for p in TicketPriority.ALL
            ]
        }
    }


# =============================================================================
# ENDPOINTS ALLEGATI
# =============================================================================

@router.post("/tickets/{ticket_id}/allegati")
async def upload_attachment(
    ticket_id: int,
    file: UploadFile = File(...),
    current_user: UtenteResponse = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Upload allegato per un ticket.
    Max 10 MB. Formati: png, jpg, pdf, txt, doc, docx, xls, xlsx
    """
    try:
        db = get_db()

        # Leggi contenuto file
        file_data = await file.read()

        result = save_attachment(
            db,
            ticket_id,
            file_data,
            file.filename,
            file.content_type,
            current_user.id_operatore
        )

        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('error', 'Errore upload'))

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tickets/{ticket_id}/allegati")
async def list_attachments(
    ticket_id: int,
    current_user: UtenteResponse = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Lista allegati di un ticket.
    """
    try:
        db = get_db()
        attachments = get_attachments(db, ticket_id)
        return {"success": True, "data": attachments}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/allegati/{allegato_id}/download")
async def download_attachment(
    allegato_id: int,
    current_user: UtenteResponse = Depends(get_current_user)
):
    """
    Download allegato.
    """
    try:
        db = get_db()
        allegato = get_attachment(db, allegato_id)

        if not allegato:
            raise HTTPException(status_code=404, detail="Allegato non trovato")

        if not os.path.exists(allegato['path_file']):
            raise HTTPException(status_code=404, detail="File non trovato su disco")

        return FileResponse(
            path=allegato['path_file'],
            filename=allegato['nome_originale'],
            media_type=allegato['mime_type']
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/allegati/{allegato_id}")
async def remove_attachment(
    allegato_id: int,
    current_user: UtenteResponse = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Elimina allegato (solo proprietario o admin).
    """
    try:
        db = get_db()
        is_admin = current_user.ruolo in ['admin', 'superuser']

        result = delete_attachment(
            db,
            allegato_id,
            current_user.id_operatore,
            is_admin
        )

        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('error', 'Errore'))

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
