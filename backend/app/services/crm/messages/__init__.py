"""
Gestione Messaggi CRM - Queries e Commands.
"""

from .queries import get_messages
from .commands import add_message

__all__ = [
    'get_messages',
    'add_message',
]
