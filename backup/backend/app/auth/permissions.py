# =============================================================================
# TO_EXTRACTOR v6.2 - PERMISSIONS
# =============================================================================
# Definizione centralizzata dei permessi per ruolo.
# Questo modulo è il "single source of truth" per tutte le regole di accesso.
#
# ARCHITETTURA:
# - Classe Permesso: costanti per identificare permessi
# - PERMESSI_PER_RUOLO: mapping ruolo → set di permessi
# - Funzioni helper: verifica permessi, gerarchia creazione, etc.
# =============================================================================

from typing import Dict, List, Set
from .models import RuoloUtente


# =============================================================================
# DEFINIZIONE COSTANTI PERMESSI
# =============================================================================

class Permesso:
    """
    Costanti per i permessi del sistema.
    
    Convenzione naming:
    - AREA:AZIONE o AREA:AZIONE:SCOPE
    - Esempi: "backend:full", "frontend:dashboard", "utenti:create:operatore"
    
    Aree:
    - backend: accesso diretto API/DB
    - frontend: sezioni interfaccia utente
    - utenti: gestione utenti
    - log: visualizzazione log audit
    """
    
    # =========================================================================
    # BACKEND - Accesso infrastruttura
    # =========================================================================
    BACKEND_FULL = "backend:full"           # Accesso completo backend (solo admin)
    
    # =========================================================================
    # FRONTEND - Sezioni interfaccia
    # =========================================================================
    DASHBOARD = "frontend:dashboard"
    ORDINI = "frontend:ordini"
    ANOMALIE = "frontend:anomalie"
    SUPERVISIONE = "frontend:supervisione"  # Supervisione ML espositori
    TRACCIATI = "frontend:tracciati"
    ANAGRAFICA = "frontend:anagrafica"
    LOOKUP = "frontend:lookup"
    DATABASE = "frontend:database"          # Gestione database frontend
    UPLOAD = "frontend:upload"              # Upload PDF
    
    # =========================================================================
    # GESTIONE UTENTI
    # =========================================================================
    UTENTI_VIEW_ALL = "utenti:view:all"     # Vede tutti gli utenti
    UTENTI_VIEW_OWN = "utenti:view:own"     # Vede solo i propri creati
    UTENTI_CREATE_SUPERVISOR = "utenti:create:supervisore"
    UTENTI_CREATE_OPERATOR = "utenti:create:operatore"
    UTENTI_DISABLE_ALL = "utenti:disable:all"
    UTENTI_DISABLE_OWN = "utenti:disable:own"
    
    # =========================================================================
    # LOG ATTIVITÀ
    # =========================================================================
    LOG_VIEW_ALL = "log:view:all"           # Vede tutti i log
    LOG_VIEW_OWN = "log:view:own"           # Vede solo propri + subordinati


# =============================================================================
# MAPPING RUOLO → PERMESSI
# =============================================================================

PERMESSI_PER_RUOLO: Dict[RuoloUtente, Set[str]] = {
    
    # =========================================================================
    # ADMIN - Accesso totale
    # =========================================================================
    RuoloUtente.ADMIN: {
        # Backend completo
        Permesso.BACKEND_FULL,
        
        # Tutte le sezioni frontend
        Permesso.DASHBOARD,
        Permesso.ORDINI,
        Permesso.ANOMALIE,
        Permesso.SUPERVISIONE,
        Permesso.TRACCIATI,
        Permesso.ANAGRAFICA,
        Permesso.LOOKUP,
        Permesso.DATABASE,
        Permesso.UPLOAD,
        
        # Gestione utenti completa
        Permesso.UTENTI_VIEW_ALL,
        Permesso.UTENTI_CREATE_SUPERVISOR,
        Permesso.UTENTI_CREATE_OPERATOR,
        Permesso.UTENTI_DISABLE_ALL,
        
        # Log completi
        Permesso.LOG_VIEW_ALL,
    },
    
    # =========================================================================
    # SUPERVISORE - Frontend completo, gestione operatori propri
    # =========================================================================
    RuoloUtente.SUPERVISORE: {
        # NO backend diretto
        
        # Tutte le sezioni frontend
        Permesso.DASHBOARD,
        Permesso.ORDINI,
        Permesso.ANOMALIE,
        Permesso.SUPERVISIONE,
        Permesso.TRACCIATI,
        Permesso.ANAGRAFICA,
        Permesso.LOOKUP,
        Permesso.DATABASE,
        Permesso.UPLOAD,
        
        # Gestione utenti limitata (solo operatori propri)
        Permesso.UTENTI_VIEW_OWN,
        Permesso.UTENTI_CREATE_OPERATOR,
        Permesso.UTENTI_DISABLE_OWN,
        
        # Log propri + subordinati
        Permesso.LOG_VIEW_OWN,
    },
    
    # =========================================================================
    # OPERATORE - Solo Database e Upload
    # =========================================================================
    RuoloUtente.OPERATORE: {
        # NO backend
        
        # Solo Database e Upload
        Permesso.DATABASE,
        Permesso.UPLOAD,
        
        # NO gestione utenti
        # NO log
    },
    
    # =========================================================================
    # READONLY - Solo visualizzazione (legacy)
    # =========================================================================
    RuoloUtente.READONLY: {
        # NO backend
        
        # Solo visualizzazione (no azioni modificanti)
        Permesso.DASHBOARD,
        Permesso.ORDINI,
        Permesso.ANOMALIE,
        Permesso.TRACCIATI,
        Permesso.ANAGRAFICA,
        Permesso.LOOKUP,
        
        # NO Database (potrebbe modificare)
        # NO Upload (modifica dati)
        # NO Supervisione ML (approva/rifiuta)
        # NO gestione utenti
        # NO log
    },
}


# =============================================================================
# FUNZIONI HELPER - PERMESSI
# =============================================================================

def get_permessi_ruolo(ruolo: RuoloUtente) -> List[str]:
    """
    Ritorna lista permessi per un dato ruolo.
    
    Args:
        ruolo: RuoloUtente enum
        
    Returns:
        Lista di stringhe permesso (ordinata per consistenza)
        
    Uso:
        permessi = get_permessi_ruolo(RuoloUtente.SUPERVISORE)
        # ['frontend:dashboard', 'frontend:ordini', ...]
    """
    permessi = PERMESSI_PER_RUOLO.get(ruolo, set())
    return sorted(list(permessi))


def ha_permesso(ruolo: RuoloUtente, permesso: str) -> bool:
    """
    Verifica se un ruolo ha un determinato permesso.
    
    Args:
        ruolo: RuoloUtente enum
        permesso: stringa permesso da verificare
        
    Returns:
        True se il ruolo ha il permesso, False altrimenti
        
    Uso:
        if ha_permesso(user.ruolo, Permesso.BACKEND_FULL):
            # Accesso consentito
    """
    permessi = PERMESSI_PER_RUOLO.get(ruolo, set())
    return permesso in permessi


# =============================================================================
# FUNZIONI HELPER - GERARCHIA CREAZIONE
# =============================================================================

def puo_creare_ruolo(ruolo_creatore: RuoloUtente, ruolo_da_creare: RuoloUtente) -> bool:
    """
    Verifica se un ruolo può crearne un altro.
    
    Regole gerarchia:
    - admin può creare: supervisore, operatore
    - supervisore può creare: solo operatore
    - operatore: non può creare nessuno
    - readonly: non può creare nessuno
    
    Args:
        ruolo_creatore: ruolo di chi vuole creare
        ruolo_da_creare: ruolo che si vuole creare
        
    Returns:
        True se la creazione è permessa
        
    Uso:
        if not puo_creare_ruolo(current_user.ruolo, new_user.ruolo):
            raise HTTPException(403, "Non autorizzato")
    """
    if ruolo_creatore == RuoloUtente.ADMIN:
        # Admin può creare supervisori e operatori (non altri admin)
        return ruolo_da_creare in [RuoloUtente.SUPERVISORE, RuoloUtente.OPERATORE]
    
    if ruolo_creatore == RuoloUtente.SUPERVISORE:
        # Supervisore può creare solo operatori
        return ruolo_da_creare == RuoloUtente.OPERATORE
    
    # Operatore e readonly non possono creare nessuno
    return False


def get_ruoli_creabili(ruolo_creatore: RuoloUtente) -> List[RuoloUtente]:
    """
    Ritorna lista ruoli che un dato ruolo può creare.
    
    Args:
        ruolo_creatore: ruolo di chi vuole creare
        
    Returns:
        Lista di RuoloUtente che può creare
        
    Uso nel frontend per popolare dropdown ruoli:
        ruoli_disponibili = get_ruoli_creabili(current_user.ruolo)
    """
    if ruolo_creatore == RuoloUtente.ADMIN:
        return [RuoloUtente.SUPERVISORE, RuoloUtente.OPERATORE]
    
    if ruolo_creatore == RuoloUtente.SUPERVISORE:
        return [RuoloUtente.OPERATORE]
    
    return []


# =============================================================================
# FUNZIONI HELPER - GERARCHIA DISABILITAZIONE
# =============================================================================

def puo_disabilitare_utente(
    ruolo_disabilitante: RuoloUtente,
    id_disabilitante: int,
    ruolo_target: RuoloUtente,
    id_target: int,
    created_by_target: int
) -> bool:
    """
    Verifica se un utente può disabilitarne un altro.
    
    Regole:
    1. Nessuno può disabilitare se stesso
    2. Nessuno può disabilitare un admin
    3. Admin può disabilitare: supervisori e operatori (tutti)
    4. Supervisore può disabilitare: solo operatori creati da lui
    5. Operatore e readonly: non possono disabilitare nessuno
    
    Args:
        ruolo_disabilitante: ruolo di chi vuole disabilitare
        id_disabilitante: id di chi vuole disabilitare
        ruolo_target: ruolo dell'utente da disabilitare
        id_target: id dell'utente da disabilitare
        created_by_target: id di chi ha creato l'utente target
        
    Returns:
        True se la disabilitazione è permessa
        
    Uso:
        if not puo_disabilitare_utente(...):
            raise HTTPException(403, "Non autorizzato")
    """
    # Regola 1: non si può disabilitare se stessi
    if id_disabilitante == id_target:
        return False
    
    # Regola 2: non si può disabilitare un admin
    if ruolo_target == RuoloUtente.ADMIN:
        return False
    
    # Regola 3: Admin può disabilitare supervisori e operatori
    if ruolo_disabilitante == RuoloUtente.ADMIN:
        return ruolo_target in [RuoloUtente.SUPERVISORE, RuoloUtente.OPERATORE, RuoloUtente.READONLY]
    
    # Regola 4: Supervisore può disabilitare solo operatori creati da lui
    if ruolo_disabilitante == RuoloUtente.SUPERVISORE:
        return (
            ruolo_target == RuoloUtente.OPERATORE and 
            created_by_target == id_disabilitante
        )
    
    # Regola 5: Operatore e readonly non possono disabilitare nessuno
    return False


# =============================================================================
# HOME PAGE PER RUOLO
# =============================================================================

HOME_PAGE_PER_RUOLO: Dict[RuoloUtente, str] = {
    RuoloUtente.ADMIN: "/dashboard",
    RuoloUtente.SUPERVISORE: "/dashboard",
    RuoloUtente.OPERATORE: "/database",     # Operatore va diretto a Database
    RuoloUtente.READONLY: "/dashboard",
}


def get_home_page(ruolo: RuoloUtente) -> str:
    """
    Ritorna la home page appropriata per un dato ruolo.
    
    Usato dopo login per redirect automatico.
    
    Args:
        ruolo: RuoloUtente enum
        
    Returns:
        Path della home page (es. "/dashboard", "/database")
    """
    return HOME_PAGE_PER_RUOLO.get(ruolo, "/dashboard")


# =============================================================================
# SEZIONI FRONTEND VISIBILI PER RUOLO
# =============================================================================

SEZIONI_FRONTEND: Dict[RuoloUtente, List[str]] = {
    RuoloUtente.ADMIN: [
        "dashboard", "ordini", "anomalie", "supervisione",
        "tracciati", "anagrafica", "lookup", "database", 
        "upload", "utenti", "logs"
    ],
    RuoloUtente.SUPERVISORE: [
        "dashboard", "ordini", "anomalie", "supervisione",
        "tracciati", "anagrafica", "lookup", "database",
        "upload", "utenti", "logs"
    ],
    RuoloUtente.OPERATORE: [
        "database", "upload"
    ],
    RuoloUtente.READONLY: [
        "dashboard", "ordini", "anomalie", 
        "tracciati", "anagrafica", "lookup"
    ],
}


def get_sezioni_visibili(ruolo: RuoloUtente) -> List[str]:
    """
    Ritorna le sezioni frontend visibili per un ruolo.
    
    Usato dal frontend per:
    - Costruire menu dinamico
    - Verificare accesso a route
    
    Args:
        ruolo: RuoloUtente enum
        
    Returns:
        Lista nomi sezioni visibili (es. ["dashboard", "ordini", ...])
    """
    return SEZIONI_FRONTEND.get(ruolo, [])


def puo_accedere_sezione(ruolo: RuoloUtente, sezione: str) -> bool:
    """
    Verifica se un ruolo può accedere a una sezione.
    
    Args:
        ruolo: RuoloUtente enum
        sezione: nome sezione (es. "dashboard", "utenti")
        
    Returns:
        True se può accedere
    """
    sezioni = SEZIONI_FRONTEND.get(ruolo, [])
    return sezione in sezioni
