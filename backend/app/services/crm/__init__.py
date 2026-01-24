"""
Sistema CRM/Ticketing - SERV.O v8.1

Gestisce ticket utenti, messaggi e notifiche.
"""

from .constants import TicketStatus, TicketCategory, TicketPriority
from .tickets import (
    get_tickets,
    get_ticket_detail,
    create_ticket,
    update_ticket_status,
    get_ticket_stats
)
from .messages import (
    get_messages,
    add_message
)
from .notifications import send_ticket_notification
from .attachments import (
    save_attachment,
    get_attachments,
    get_attachment,
    delete_attachment
)

__all__ = [
    # Constants
    'TicketStatus',
    'TicketCategory',
    'TicketPriority',
    # Tickets
    'get_tickets',
    'get_ticket_detail',
    'create_ticket',
    'update_ticket_status',
    'get_ticket_stats',
    # Messages
    'get_messages',
    'add_message',
    # Notifications
    'send_ticket_notification',
    # Attachments
    'save_attachment',
    'get_attachments',
    'get_attachment',
    'delete_attachment',
]
