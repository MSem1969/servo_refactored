"""
Template email HTML - Centralizzati e manutenibili.

Ogni template ha:
- subject: Oggetto email con placeholder
- body: HTML con placeholder

Placeholder usano formato {nome} per string.format()
"""

from typing import Tuple, Dict, Any

# Stile base condiviso
_BASE_STYLE = """
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    max-width: 600px;
    margin: 0 auto;
    padding: 20px;
"""

_HEADER_STYLE = "color: #2563eb; margin-bottom: 20px;"
_TEXT_STYLE = "color: #374151; line-height: 1.6;"
_LABEL_STYLE = "color: #6b7280; font-weight: 600;"
_VALUE_STYLE = "color: #111827;"
_FOOTER_STYLE = "color: #9ca3af; font-size: 12px; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e5e7eb;"

TEMPLATES = {
    'ticket_creato': {
        'subject': '[Ticket #{id}] Ticket creato - {oggetto}',
        'body': f'''
        <div style="{_BASE_STYLE}">
            <h2 style="{_HEADER_STYLE}">Nuovo Ticket Creato</h2>
            <div style="{_TEXT_STYLE}">
                <p><span style="{_LABEL_STYLE}">ID Ticket:</span> <span style="{_VALUE_STYLE}">#{id}</span></p>
                <p><span style="{_LABEL_STYLE}">Categoria:</span> <span style="{_VALUE_STYLE}">{{categoria}}</span></p>
                <p><span style="{_LABEL_STYLE}">Oggetto:</span> <span style="{_VALUE_STYLE}">{{oggetto}}</span></p>
                <p><span style="{_LABEL_STYLE}">Pagina:</span> <span style="{_VALUE_STYLE}">{{pagina_origine}}</span></p>
            </div>
            <p style="{_FOOTER_STYLE}">
                Email automatica da SERV.O. Non rispondere a questa email.
            </p>
        </div>
        '''
    },

    'stato_cambiato': {
        'subject': '[Ticket #{id}] Stato aggiornato: {stato}',
        'body': f'''
        <div style="{_BASE_STYLE}">
            <h2 style="{_HEADER_STYLE}">Aggiornamento Stato Ticket</h2>
            <div style="{_TEXT_STYLE}">
                <p><span style="{_LABEL_STYLE}">ID Ticket:</span> <span style="{_VALUE_STYLE}">#{id}</span></p>
                <p><span style="{_LABEL_STYLE}">Oggetto:</span> <span style="{_VALUE_STYLE}">{{oggetto}}</span></p>
                <p><span style="{_LABEL_STYLE}">Nuovo Stato:</span>
                    <span style="color: #059669; font-weight: 600;">{{stato}}</span>
                </p>
            </div>
            <p style="{_FOOTER_STYLE}">
                Email automatica da SERV.O. Non rispondere a questa email.
            </p>
        </div>
        '''
    },

    'nuova_risposta': {
        'subject': '[Ticket #{id}] Nuova risposta - {oggetto}',
        'body': f'''
        <div style="{_BASE_STYLE}">
            <h2 style="{_HEADER_STYLE}">Nuova Risposta al Ticket</h2>
            <div style="{_TEXT_STYLE}">
                <p><span style="{_LABEL_STYLE}">ID Ticket:</span> <span style="{_VALUE_STYLE}">#{id}</span></p>
                <p><span style="{_LABEL_STYLE}">Oggetto:</span> <span style="{_VALUE_STYLE}">{{oggetto}}</span></p>
            </div>
            <div style="background: #f3f4f6; padding: 16px; border-radius: 8px; margin: 20px 0; color: #374151;">
                {{messaggio}}
            </div>
            <p style="{_FOOTER_STYLE}">
                Email automatica da SERV.O. Non rispondere a questa email.
            </p>
        </div>
        '''
    },

    'ticket_chiuso': {
        'subject': '[Ticket #{id}] Ticket chiuso - {oggetto}',
        'body': f'''
        <div style="{_BASE_STYLE}">
            <h2 style="{_HEADER_STYLE}">Ticket Chiuso</h2>
            <div style="{_TEXT_STYLE}">
                <p><span style="{_LABEL_STYLE}">ID Ticket:</span> <span style="{_VALUE_STYLE}">#{id}</span></p>
                <p><span style="{_LABEL_STYLE}">Oggetto:</span> <span style="{_VALUE_STYLE}">{{oggetto}}</span></p>
                <p><span style="{_LABEL_STYLE}">Stato:</span>
                    <span style="color: #6b7280; font-weight: 600;">Chiuso</span>
                </p>
            </div>
            <p style="{_TEXT_STYLE}">
                Il tuo ticket e stato risolto e chiuso. Se hai ulteriori domande,
                puoi aprire un nuovo ticket.
            </p>
            <p style="{_FOOTER_STYLE}">
                Email automatica da SERV.O. Non rispondere a questa email.
            </p>
        </div>
        '''
    },

    'test': {
        'subject': '[SERV.O] Email di test',
        'body': f'''
        <div style="{_BASE_STYLE}">
            <h2 style="{_HEADER_STYLE}">Email di Test</h2>
            <div style="{_TEXT_STYLE}">
                <p>Questa e un'email di test inviata da SERV.O.</p>
                <p>Se stai leggendo questo messaggio, la configurazione SMTP funziona correttamente.</p>
            </div>
            <p style="{_FOOTER_STYLE}">
                Email automatica da SERV.O.
            </p>
        </div>
        '''
    },

    # ===== TEMPLATE ADMIN =====

    'admin_nuovo_ticket': {
        'subject': '[ADMIN] Nuovo ticket #{id} - {categoria}',
        'body': f'''
        <div style="{_BASE_STYLE}">
            <h2 style="color: #dc2626; margin-bottom: 20px;">Nuovo Ticket di Assistenza</h2>
            <div style="{_TEXT_STYLE}">
                <p><span style="{_LABEL_STYLE}">ID Ticket:</span> <span style="{_VALUE_STYLE}">#{id}</span></p>
                <p><span style="{_LABEL_STYLE}">Categoria:</span>
                    <span style="background: #dbeafe; color: #1e40af; padding: 2px 8px; border-radius: 4px;">{{categoria}}</span>
                </p>
                <p><span style="{_LABEL_STYLE}">Priorita:</span>
                    <span style="{{priorita_style}}">{{priorita}}</span>
                </p>
                <p><span style="{_LABEL_STYLE}">Utente:</span> <span style="{_VALUE_STYLE}">{{utente}}</span></p>
                <p><span style="{_LABEL_STYLE}">Oggetto:</span> <span style="{_VALUE_STYLE}">{{oggetto}}</span></p>
                <p><span style="{_LABEL_STYLE}">Pagina origine:</span> <span style="{_VALUE_STYLE}">{{pagina_origine}}</span></p>
            </div>
            <div style="background: #fef3c7; padding: 16px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #f59e0b;">
                <p style="{_LABEL_STYLE}; margin-bottom: 8px;">Contenuto richiesta:</p>
                <p style="color: #374151; margin: 0;">{{contenuto}}</p>
            </div>
            <p style="{_FOOTER_STYLE}">
                Accedi a SERV.O per gestire questo ticket.
            </p>
        </div>
        '''
    }
}


def render_template(name: str, context: Dict[str, Any]) -> Tuple[str, str]:
    """
    Renderizza template con contesto.

    Args:
        name: Nome template (chiave in TEMPLATES)
        context: Dict con valori per placeholder

    Returns:
        Tuple (subject, body_html)

    Raises:
        ValueError: Se template non trovato
    """
    template = TEMPLATES.get(name)
    if not template:
        raise ValueError(f"Template non trovato: {name}")

    # Sostituisci placeholder
    subject = template['subject'].format(**context)
    body = template['body'].format(**context)

    return subject, body


def get_template_names() -> list:
    """Ritorna lista nomi template disponibili"""
    return list(TEMPLATES.keys())
