"""
Sistema Email Unificato - SERV.O v8.1

Gestisce configurazione, invio e ricezione email.
Supporta Gmail (default) con estensibilità per altri provider.
"""

from .config import email_config, EmailConfigService
from .sender import EmailSender
from .templates import render_template, TEMPLATES
from .log import log_email_sent, log_email_failed, get_email_log

__all__ = [
    'email_config',
    'EmailConfigService',
    'EmailSender',
    'render_template',
    'TEMPLATES',
    'log_email_sent',
    'log_email_failed',
    'get_email_log',
]
