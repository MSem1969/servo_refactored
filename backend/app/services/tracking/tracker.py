# =============================================================================
# SERV.O v8.2 - TRACKER MODULE
# =============================================================================
# Modulo principale per tracking azioni operatore
#
# OBIETTIVO: Raccogliere dati comportamentali per future analisi ML:
# - Pattern di utilizzo individuali
# - Sequenze di azioni frequenti
# - Periodicità e timing
# - Preferenze filtri/parametri
# =============================================================================

import json
import time
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict

from ...database_pg import get_db


# =============================================================================
# COSTANTI - SEZIONI E AZIONI
# =============================================================================

class Sezione:
    """Sezioni dell'applicazione tracciate."""
    DASHBOARD = 'DASHBOARD'
    DATABASE = 'DATABASE'
    UPLOAD = 'UPLOAD'
    REPORT = 'REPORT'
    SUPERVISIONE = 'SUPERVISIONE'
    TRACCIATI = 'TRACCIATI'
    ANAGRAFICA = 'ANAGRAFICA'
    LISTINI = 'LISTINI'
    CRM = 'CRM'
    ADMIN = 'ADMIN'
    AUTH = 'AUTH'
    LOOKUP = 'LOOKUP'
    ANOMALIE = 'ANOMALIE'
    EMAIL = 'EMAIL'


class Azione:
    """Tipi di azione tracciabili."""
    # Navigazione/Visualizzazione
    VIEW = 'VIEW'                    # Visualizza pagina/dettaglio
    LIST = 'LIST'                    # Visualizza lista
    SEARCH = 'SEARCH'                # Ricerca
    FILTER = 'FILTER'                # Applica filtri
    SORT = 'SORT'                    # Ordina risultati

    # CRUD
    CREATE = 'CREATE'                # Crea nuovo record
    UPDATE = 'UPDATE'                # Modifica record
    DELETE = 'DELETE'                # Elimina record

    # Azioni specifiche ordini
    CONFIRM = 'CONFIRM'              # Conferma riga/ordine
    CONFIRM_ALL = 'CONFIRM_ALL'      # Conferma tutto
    RESET = 'RESET'                  # Ripristina stato
    ARCHIVE = 'ARCHIVE'              # Archivia

    # Export/Import
    EXPORT = 'EXPORT'                # Esporta dati
    EXPORT_EXCEL = 'EXPORT_EXCEL'    # Esporta Excel
    EXPORT_TRACCIATO = 'EXPORT_TRACCIATO'  # Genera tracciato EDI
    DOWNLOAD = 'DOWNLOAD'            # Download file
    UPLOAD = 'UPLOAD'                # Upload file

    # Supervisione
    APPROVE = 'APPROVE'              # Approva supervisione
    REJECT = 'REJECT'                # Rifiuta supervisione
    BULK_APPROVE = 'BULK_APPROVE'    # Approvazione massiva

    # Auth
    LOGIN = 'LOGIN'
    LOGOUT = 'LOGOUT'

    # Altro
    PREVIEW = 'PREVIEW'              # Anteprima
    REFRESH = 'REFRESH'              # Aggiorna dati
    CLICK = 'CLICK'                  # Click generico


# =============================================================================
# TRACKING CONTEXT - Per gestire sessioni e sequenze
# =============================================================================

# Storage per sessione corrente (per request)
_current_session: Dict[int, str] = {}  # operatore_id -> session_id
_last_action: Dict[int, int] = {}       # operatore_id -> last_action_id


def get_session_id(id_operatore: int) -> str:
    """
    Ottiene o crea session ID per l'operatore.

    Session = gruppo di azioni consecutive (timeout 30 min).
    """
    if id_operatore not in _current_session:
        _current_session[id_operatore] = str(uuid.uuid4())[:12]
    return _current_session[id_operatore]


def _get_last_action_id(id_operatore: int) -> Optional[int]:
    """Ottiene ID ultima azione dell'operatore."""
    return _last_action.get(id_operatore)


def _set_last_action_id(id_operatore: int, action_id: int):
    """Imposta ID ultima azione dell'operatore."""
    _last_action[id_operatore] = action_id


@dataclass
class TrackingContext:
    """
    Contesto per tracking di un'azione.

    Usato per passare informazioni tra start e end di un'azione.
    """
    id_operatore: int
    username: str
    ruolo: str
    sezione: str
    azione: str
    entita: Optional[str] = None
    id_entita: Optional[int] = None
    parametri: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    # Campi calcolati
    session_id: str = field(default='')
    start_time: float = field(default=0.0)
    action_id: Optional[int] = None

    def __post_init__(self):
        self.session_id = get_session_id(self.id_operatore)
        self.start_time = time.time()


# =============================================================================
# FUNZIONI PRINCIPALI DI TRACKING
# =============================================================================

def track_action(
    id_operatore: int,
    username: str,
    ruolo: str,
    sezione: str,
    azione: str,
    entita: Optional[str] = None,
    id_entita: Optional[int] = None,
    parametri: Optional[Dict[str, Any]] = None,
    risultato: Optional[Dict[str, Any]] = None,
    success: bool = True,
    durata_ms: Optional[int] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> Optional[int]:
    """
    Registra un'azione operatore (one-shot).

    Usa questa funzione per azioni semplici senza timing.
    Per azioni con timing, usa track_action_start/end.

    Args:
        id_operatore: ID dell'operatore
        username: Username operatore
        ruolo: Ruolo operatore
        sezione: Sezione dell'app (usa Sezione.*)
        azione: Tipo azione (usa Azione.*)
        entita: Tipo entità coinvolta (ordine, anomalia, etc.)
        id_entita: ID dell'entità
        parametri: Parametri/filtri usati (dict -> JSON)
        risultato: Risultato dell'azione (dict -> JSON)
        success: True se azione riuscita
        durata_ms: Durata in millisecondi (opzionale)
        ip_address: IP client
        user_agent: User agent browser

    Returns:
        ID del record inserito o None se errore
    """
    try:
        db = get_db()
        now = datetime.now()

        # Calcola campi temporali per analisi
        giorno_settimana = now.weekday()  # 0=Lun, 6=Dom
        ora_giorno = now.hour
        settimana_anno = now.isocalendar()[1]

        # Session e sequenza
        session_id = get_session_id(id_operatore)
        azione_precedente_id = _get_last_action_id(id_operatore)

        # Serializza JSON
        parametri_json = json.dumps(parametri, default=str) if parametri else None
        risultato_json = json.dumps(risultato, default=str) if risultato else None

        cursor = db.execute("""
            INSERT INTO operatore_azioni_log (
                id_operatore, username, ruolo,
                sezione, azione, entita, id_entita,
                parametri, risultato, success,
                durata_ms, ip_address, user_agent,
                session_id, azione_precedente_id,
                giorno_settimana, ora_giorno, settimana_anno
            ) VALUES (
                %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s,
                %s, %s,
                %s, %s, %s
            )
            RETURNING id_azione
        """, (
            id_operatore, username, ruolo,
            sezione, azione, entita, id_entita,
            parametri_json, risultato_json, success,
            durata_ms, ip_address, user_agent,
            session_id, azione_precedente_id,
            giorno_settimana, ora_giorno, settimana_anno
        ))

        db.commit()

        row = cursor.fetchone()
        action_id = row['id_azione'] if row else None

        # Aggiorna last action per sequenza
        if action_id:
            _set_last_action_id(id_operatore, action_id)

        return action_id

    except Exception as e:
        print(f"[TRACKING ERROR] {e}")
        return None


def track_action_start(
    id_operatore: int,
    username: str,
    ruolo: str,
    sezione: str,
    azione: str,
    entita: Optional[str] = None,
    id_entita: Optional[int] = None,
    parametri: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> TrackingContext:
    """
    Inizia tracking di un'azione (per misurare durata).

    Ritorna un context da passare a track_action_end.

    Usage:
        ctx = track_action_start(...)
        # ... esegui operazione ...
        track_action_end(ctx, risultato={...}, success=True)
    """
    return TrackingContext(
        id_operatore=id_operatore,
        username=username,
        ruolo=ruolo,
        sezione=sezione,
        azione=azione,
        entita=entita,
        id_entita=id_entita,
        parametri=parametri,
        ip_address=ip_address,
        user_agent=user_agent
    )


def track_action_end(
    ctx: TrackingContext,
    risultato: Optional[Dict[str, Any]] = None,
    success: bool = True
) -> Optional[int]:
    """
    Completa tracking di un'azione iniziata con track_action_start.

    Calcola automaticamente la durata.
    """
    durata_ms = int((time.time() - ctx.start_time) * 1000)

    return track_action(
        id_operatore=ctx.id_operatore,
        username=ctx.username,
        ruolo=ctx.ruolo,
        sezione=ctx.sezione,
        azione=ctx.azione,
        entita=ctx.entita,
        id_entita=ctx.id_entita,
        parametri=ctx.parametri,
        risultato=risultato,
        success=success,
        durata_ms=durata_ms,
        ip_address=ctx.ip_address,
        user_agent=ctx.user_agent
    )


@contextmanager
def tracking_context(
    id_operatore: int,
    username: str,
    ruolo: str,
    sezione: str,
    azione: str,
    **kwargs
):
    """
    Context manager per tracking automatico con timing.

    Usage:
        with tracking_context(operatore, sezione, azione) as ctx:
            # ... esegui operazione ...
            ctx.risultato = {'records': 100}
    """
    ctx = track_action_start(
        id_operatore=id_operatore,
        username=username,
        ruolo=ruolo,
        sezione=sezione,
        azione=azione,
        **kwargs
    )

    # Aggiungi attributi per il context
    ctx.risultato = None
    ctx.success = True

    try:
        yield ctx
    except Exception as e:
        ctx.success = False
        ctx.risultato = {'error': str(e)}
        raise
    finally:
        track_action_end(ctx, risultato=ctx.risultato, success=ctx.success)


# =============================================================================
# HELPER PER ESTRAZIONE DATI DA REQUEST
# =============================================================================

def extract_request_info(request) -> Dict[str, str]:
    """
    Estrae IP e User-Agent da una FastAPI Request.

    Args:
        request: FastAPI Request object

    Returns:
        Dict con ip_address e user_agent
    """
    ip_address = None
    user_agent = None

    if request:
        # IP: considera X-Forwarded-For per proxy
        if hasattr(request, 'headers'):
            ip_address = request.headers.get('X-Forwarded-For', '').split(',')[0].strip()
            if not ip_address and hasattr(request, 'client'):
                ip_address = request.client.host if request.client else None
            user_agent = request.headers.get('User-Agent', '')[:500]  # Limita lunghezza

    return {
        'ip_address': ip_address,
        'user_agent': user_agent
    }


def track_from_user(
    current_user,
    sezione: str,
    azione: str,
    request=None,
    **kwargs
) -> Optional[int]:
    """
    Helper per tracking usando current_user di FastAPI.

    Usage nei router:
        track_from_user(current_user, Sezione.REPORT, Azione.EXPORT, request=request)
    """
    req_info = extract_request_info(request) if request else {}

    return track_action(
        id_operatore=current_user.id_operatore,
        username=current_user.username,
        ruolo=current_user.ruolo.value if hasattr(current_user.ruolo, 'value') else str(current_user.ruolo),
        sezione=sezione,
        azione=azione,
        ip_address=req_info.get('ip_address'),
        user_agent=req_info.get('user_agent'),
        **kwargs
    )
