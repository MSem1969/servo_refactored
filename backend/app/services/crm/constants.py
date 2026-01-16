"""
Costanti CRM - Stati, categorie, priorita, workflow.
"""


class TicketStatus:
    """Stati possibili per un ticket"""
    APERTO = 'aperto'
    IN_LAVORAZIONE = 'in_lavorazione'
    CHIUSO = 'chiuso'

    ALL = [APERTO, IN_LAVORAZIONE, CHIUSO]

    # Transizioni valide: stato_corrente -> [stati_permessi]
    TRANSITIONS = {
        APERTO: [IN_LAVORAZIONE, CHIUSO],
        IN_LAVORAZIONE: [APERTO, CHIUSO],
        CHIUSO: [APERTO]  # Riapertura
    }

    # Label per UI
    LABELS = {
        APERTO: 'Aperto',
        IN_LAVORAZIONE: 'In Lavorazione',
        CHIUSO: 'Chiuso'
    }

    # Colori per UI (Tailwind)
    COLORS = {
        APERTO: 'blue',
        IN_LAVORAZIONE: 'yellow',
        CHIUSO: 'gray'
    }


class TicketCategory:
    """Categorie ticket - Solo assistenza e miglioramenti"""
    ASSISTENZA = 'assistenza'
    MIGLIORAMENTO = 'miglioramento'

    ALL = [ASSISTENZA, MIGLIORAMENTO]

    # Label per UI
    LABELS = {
        ASSISTENZA: 'Richiesta Assistenza',
        MIGLIORAMENTO: 'Proposta Miglioramento'
    }

    # Icone per UI
    ICONS = {
        ASSISTENZA: 'help',
        MIGLIORAMENTO: 'lightbulb'
    }


class TicketPriority:
    """Priorita ticket"""
    BASSA = 'bassa'
    NORMALE = 'normale'
    ALTA = 'alta'

    ALL = [BASSA, NORMALE, ALTA]

    # Label per UI
    LABELS = {
        BASSA: 'Bassa',
        NORMALE: 'Normale',
        ALTA: 'Alta'
    }

    # Colori per UI
    COLORS = {
        BASSA: 'gray',
        NORMALE: 'blue',
        ALTA: 'red'
    }

    # Ordine per sorting (piu alto = piu importante)
    ORDER = {
        BASSA: 1,
        NORMALE: 2,
        ALTA: 3
    }


def is_valid_transition(current_status: str, new_status: str) -> bool:
    """
    Verifica se una transizione di stato e valida.

    Args:
        current_status: Stato corrente
        new_status: Nuovo stato

    Returns:
        True se transizione permessa
    """
    valid = TicketStatus.TRANSITIONS.get(current_status, [])
    return new_status in valid


def get_status_label(status: str) -> str:
    """Ritorna label leggibile per stato"""
    return TicketStatus.LABELS.get(status, status)


def get_category_label(category: str) -> str:
    """Ritorna label leggibile per categoria"""
    return TicketCategory.LABELS.get(category, category)


def get_priority_label(priority: str) -> str:
    """Ritorna label leggibile per priorita"""
    return TicketPriority.LABELS.get(priority, priority)
