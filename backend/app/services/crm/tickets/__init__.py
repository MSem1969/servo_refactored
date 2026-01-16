"""
Gestione Ticket CRM - Queries e Commands.
"""

from .queries import get_tickets, get_ticket_detail, get_ticket_stats
from .commands import create_ticket, update_ticket_status, update_ticket

__all__ = [
    'get_tickets',
    'get_ticket_detail',
    'get_ticket_stats',
    'create_ticket',
    'update_ticket_status',
    'update_ticket',
]
