"""
Provider Email - Implementazioni specifiche per ogni servizio email.

Estendere BaseEmailProvider per aggiungere nuovi provider.
"""

from .base import BaseEmailProvider
from .gmail import GmailProvider

__all__ = [
    'BaseEmailProvider',
    'GmailProvider',
]
