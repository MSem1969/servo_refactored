"""
Costanti sistema email - Centralizzate per manutenibilità
"""

# Provider supportati con configurazioni default
PROVIDERS = {
    'gmail': {
        'imap_host': 'imap.gmail.com',
        'imap_port': 993,
        'smtp_host': 'smtp.gmail.com',
        'smtp_port': 587,
        'use_ssl': True,
        'use_tls': True,
    },
    'outlook': {
        'imap_host': 'outlook.office365.com',
        'imap_port': 993,
        'smtp_host': 'smtp.office365.com',
        'smtp_port': 587,
        'use_ssl': True,
        'use_tls': True,
    },
    'aruba': {
        'imap_host': 'imaps.aruba.it',
        'imap_port': 993,
        'smtp_host': 'smtps.aruba.it',
        'smtp_port': 465,
        'use_ssl': True,
        'use_tls': False,
    },
}

# Rate limiting
SMTP_RATE_LIMIT = 10  # email/minuto
SMTP_RETRY_DELAY = 300  # secondi (5 minuti)
SMTP_MAX_RETRIES = 3

# Timeout connessioni
IMAP_TIMEOUT = 30  # secondi
SMTP_TIMEOUT = 30  # secondi


class EmailStatus:
    """Stati invio email"""
    PENDING = 'pending'
    SENT = 'sent'
    FAILED = 'failed'
    RETRY = 'retry'

    ALL = [PENDING, SENT, FAILED, RETRY]


class EmailType:
    """Tipi email per logging"""
    TICKET_CREATO = 'ticket_creato'
    STATO_CAMBIATO = 'stato_cambiato'
    NUOVA_RISPOSTA = 'nuova_risposta'
    TEST = 'test'
    GENERIC = 'generic'

    ALL = [TICKET_CREATO, STATO_CAMBIATO, NUOVA_RISPOSTA, TEST, GENERIC]
