"""
Gestione Ticket CRM - Queries e Commands.
v11.4: Aggiunta funzione crea_ticket_sistema per notifiche automatiche.
"""

from .queries import get_tickets, get_ticket_detail, get_ticket_stats
from .commands import create_ticket, update_ticket_status, update_ticket, crea_ticket_sistema

__all__ = [
    'get_tickets',
    'get_ticket_detail',
    'get_ticket_stats',
    'create_ticket',
    'update_ticket_status',
    'update_ticket',
    'crea_ticket_sistema',
]
