# =============================================================================
# SERV.O v6.2 - ROUTER PRODUTTIVITÀ OPERATORI
# =============================================================================
# Endpoint per tracking produttività: tempo per sezione, contatori operazioni,
# statistiche sessione corrente e giornaliere.
# =============================================================================

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
from pydantic import BaseModel

from ..auth import (
    RuoloUtente,
    UtenteResponse,
    get_current_user,
)


def _get_db():
    from ..database_pg import get_db
    return get_db()


router = APIRouter(
    prefix="/produttivita",
    tags=["Produttività"],
    responses={
        401: {"description": "Non autenticato"},
        403: {"description": "Accesso negato"}
    }
)


# =============================================================================
# MODELLI PYDANTIC
# =============================================================================

class HeartbeatRequest(BaseModel):
    sezione: str


class TempoSezione(BaseModel):
    sezione: str
    durata_secondi: int
    durata_formattata: str


class TaskRecente(BaseModel):
    timestamp: str
    tipo_operazione: str
    descrizione: Optional[str]
    entita: Optional[str]
    id_entita: Optional[int]


class ProduttivitaOperatore(BaseModel):
    id_operatore: int
    username: str
    nome: Optional[str]
    cognome: Optional[str]
    ruolo: str
    tempo_totale_secondi: int
    tempo_formattato: str
    tempo_per_sezione: List[TempoSezione]
    ordini_validati: int
    righe_modificate: int
    anomalie_verificate: int
    righe_confermate: int
    tracciati_generati: int
    # v6.2: Stato online
    is_online: bool = False
    ultimo_heartbeat: Optional[str] = None


class ProduttivitaResponse(BaseModel):
    data_riferimento: str
    tipo: str  # 'sessione' o 'giorno'
    operatori: List[ProduttivitaOperatore]


class UltimeTaskResponse(BaseModel):
    id_operatore: int
    username: str
    tasks: List[TaskRecente]


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _format_duration(seconds: int) -> str:
    """Formatta durata in HH:MM:SS"""
    if seconds < 0:
        seconds = 0
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def _get_operatori_visibili(current_user: UtenteResponse) -> tuple:
    """
    Restituisce filtro operatori in base al ruolo.
    - Operatore: solo sé stesso
    - Supervisore: tutti gli operatori + sé stesso
    - Superuser: supervisori + operatori + sé stesso
    - Admin: superuser + supervisori + operatori
    """
    if current_user.ruolo == RuoloUtente.OPERATORE:
        return ("id_operatore = %s", [current_user.id_operatore])
    elif current_user.ruolo == RuoloUtente.SUPERVISORE:
        # Supervisore vede tutti gli operatori + sé stesso
        return ("(ruolo = 'operatore' OR id_operatore = %s)", [current_user.id_operatore])
    elif current_user.ruolo == RuoloUtente.SUPERUSER:
        # Superuser vede supervisori e operatori + sé stesso
        return ("(ruolo IN ('supervisore', 'operatore') OR id_operatore = %s)", [current_user.id_operatore])
    else:  # ADMIN
        return ("ruolo IN ('superuser', 'supervisore', 'operatore')", [])


def _get_tempo_sezioni(db, id_operatore: int, data_rif: date, id_session: int = None) -> List[TempoSezione]:
    """Recupera tempo per sezione per un operatore."""
    if id_session:
        # Sessione specifica
        cursor = db.execute("""
            SELECT sezione, SUM(durata_secondi) as totale
            FROM sessione_attivita
            WHERE id_operatore = %s AND id_session = %s
            GROUP BY sezione
            ORDER BY totale DESC
        """, (id_operatore, id_session))
    else:
        # Giorno specifico
        cursor = db.execute("""
            SELECT sezione, SUM(durata_secondi) as totale
            FROM sessione_attivita
            WHERE id_operatore = %s AND data_riferimento = %s
            GROUP BY sezione
            ORDER BY totale DESC
        """, (id_operatore, data_rif))

    return [
        TempoSezione(
            sezione=row["sezione"],
            durata_secondi=row["totale"] or 0,
            durata_formattata=_format_duration(row["totale"] or 0)
        )
        for row in cursor.fetchall()
    ]


def _get_contatori_operatore(db, id_operatore: int, data_rif: date) -> Dict[str, int]:
    """
    Recupera contatori operazioni per un operatore in una data.

    Operazioni tracciate:
    - ordini_validati: VALIDA_TRACCIATO (ordini validati con generazione tracciato)
    - righe_modificate: MODIFICA_RIGA
    - anomalie_verificate: APPROVA_SUPERVISIONE, RIFIUTA_SUPERVISIONE, MODIFICA_SUPERVISIONE
    - righe_confermate: REGISTRA_EVASIONE
    - tracciati_generati: VALIDA_TRACCIATO
    """
    cursor = db.execute("""
        SELECT
            COUNT(CASE WHEN tipo_operazione = 'VALIDA_TRACCIATO' THEN 1 END) as ordini_validati,
            COUNT(CASE WHEN tipo_operazione = 'MODIFICA_RIGA' THEN 1 END) as righe_modificate,
            COUNT(CASE WHEN tipo_operazione IN ('APPROVA_SUPERVISIONE', 'RIFIUTA_SUPERVISIONE', 'MODIFICA_SUPERVISIONE') THEN 1 END) as anomalie_verificate,
            COUNT(CASE WHEN tipo_operazione = 'REGISTRA_EVASIONE' THEN 1 END) as righe_confermate,
            COUNT(CASE WHEN tipo_operazione = 'VALIDA_TRACCIATO' THEN 1 END) as tracciati_generati
        FROM log_operazioni
        WHERE id_operatore = %s AND DATE(timestamp) = %s
    """, (id_operatore, data_rif))

    row = cursor.fetchone()
    if row:
        return dict(row)
    return {
        "ordini_validati": 0,
        "righe_modificate": 0,
        "anomalie_verificate": 0,
        "righe_confermate": 0,
        "tracciati_generati": 0
    }


def _get_session_id_corrente(db, id_operatore: int) -> Optional[int]:
    """Recupera l'ID della sessione attiva per un operatore."""
    cursor = db.execute("""
        SELECT id_session FROM user_sessions
        WHERE id_operatore = %s
          AND revoked_at IS NULL
          AND expires_at > CURRENT_TIMESTAMP
        ORDER BY created_at DESC
        LIMIT 1
    """, (id_operatore,))
    row = cursor.fetchone()
    return row["id_session"] if row else None


def _get_stato_online(db, id_operatore: int) -> tuple:
    """
    Verifica se un operatore è online (ha sessione attiva con heartbeat recente).
    Ritorna (is_online, ultimo_heartbeat)

    Un operatore è considerato online se:
    - Ha una sessione attiva non scaduta
    - Ha inviato un heartbeat negli ultimi 2 minuti
    """
    cursor = db.execute("""
        SELECT
            s.id_session,
            sa.ultimo_heartbeat
        FROM user_sessions s
        LEFT JOIN sessione_attivita sa ON s.id_session = sa.id_session
            AND sa.data_riferimento = CURRENT_DATE
        WHERE s.id_operatore = %s
          AND s.revoked_at IS NULL
          AND s.expires_at > CURRENT_TIMESTAMP
        ORDER BY sa.ultimo_heartbeat DESC NULLS LAST
        LIMIT 1
    """, (id_operatore,))

    row = cursor.fetchone()

    if not row or not row["id_session"]:
        return (False, None)

    ultimo_hb = row["ultimo_heartbeat"]
    if not ultimo_hb:
        return (False, None)

    # Converti in datetime se necessario
    if isinstance(ultimo_hb, str):
        ultimo_hb = datetime.fromisoformat(ultimo_hb.replace('Z', '+00:00'))

    # Online se heartbeat negli ultimi 2 minuti
    delta = (datetime.now() - ultimo_hb).total_seconds()
    is_online = delta < 120  # 2 minuti

    return (is_online, ultimo_hb.isoformat() if ultimo_hb else None)


# =============================================================================
# ENDPOINT: HEARTBEAT
# =============================================================================

@router.post("/heartbeat", summary="Heartbeat attività sezione")
async def registra_heartbeat(
    data: HeartbeatRequest,
    current_user: UtenteResponse = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Registra heartbeat per tracciare tempo in una sezione.
    Chiamato ogni 60 secondi dal frontend.
    """
    db = _get_db()

    # Trova sessione corrente
    id_session = _get_session_id_corrente(db, current_user.id_operatore)
    if not id_session:
        return {"success": False, "message": "Nessuna sessione attiva"}

    sezione = data.sezione.lower().strip()
    oggi = date.today()

    # Cerca record esistente per questa sessione e sezione
    cursor = db.execute("""
        SELECT id, ultimo_heartbeat, durata_secondi
        FROM sessione_attivita
        WHERE id_session = %s AND sezione = %s AND data_riferimento = %s
    """, (id_session, sezione, oggi))

    existing = cursor.fetchone()

    if existing:
        # Calcola tempo trascorso dall'ultimo heartbeat (max 90 secondi per evitare gap)
        ultimo = existing["ultimo_heartbeat"]
        if isinstance(ultimo, str):
            ultimo = datetime.fromisoformat(ultimo)

        delta = (datetime.now() - ultimo).total_seconds()
        incremento = min(int(delta), 90)  # Max 90s per heartbeat

        nuovo_totale = (existing["durata_secondi"] or 0) + incremento

        db.execute("""
            UPDATE sessione_attivita
            SET ultimo_heartbeat = CURRENT_TIMESTAMP,
                durata_secondi = %s
            WHERE id = %s
        """, (nuovo_totale, existing["id"]))
    else:
        # Nuovo record
        db.execute("""
            INSERT INTO sessione_attivita (id_operatore, id_session, sezione, ultimo_heartbeat, durata_secondi, data_riferimento)
            VALUES (%s, %s, %s, CURRENT_TIMESTAMP, 0, %s)
        """, (current_user.id_operatore, id_session, sezione, oggi))

    db.commit()

    return {"success": True, "sezione": sezione}


# =============================================================================
# ENDPOINT: PRODUTTIVITÀ SESSIONE CORRENTE
# =============================================================================

@router.get("/sessione", response_model=ProduttivitaResponse, summary="Produttività sessione corrente")
async def get_produttivita_sessione(
    current_user: UtenteResponse = Depends(get_current_user)
) -> ProduttivitaResponse:
    """
    Recupera statistiche produttività per la sessione corrente.
    Visibilità in base al ruolo.
    """
    db = _get_db()
    oggi = date.today()

    filtro, params = _get_operatori_visibili(current_user)

    # Recupera operatori visibili
    cursor = db.execute(f"""
        SELECT id_operatore, username, nome, cognome, ruolo
        FROM operatori
        WHERE attivo = TRUE AND {filtro}
        ORDER BY cognome, nome
    """, tuple(params))

    operatori_list = []
    for op in cursor.fetchall():
        id_op = op["id_operatore"]

        # Sessione corrente
        id_session = _get_session_id_corrente(db, id_op)

        # Stato online
        is_online, ultimo_hb = _get_stato_online(db, id_op)

        # Tempo per sezione
        tempo_sezioni = _get_tempo_sezioni(db, id_op, oggi, id_session)
        tempo_totale = sum(t.durata_secondi for t in tempo_sezioni)

        # Contatori
        contatori = _get_contatori_operatore(db, id_op, oggi)

        operatori_list.append(ProduttivitaOperatore(
            id_operatore=id_op,
            username=op["username"],
            nome=op["nome"],
            cognome=op["cognome"],
            ruolo=op["ruolo"],
            tempo_totale_secondi=tempo_totale,
            tempo_formattato=_format_duration(tempo_totale),
            tempo_per_sezione=tempo_sezioni,
            is_online=is_online,
            ultimo_heartbeat=ultimo_hb,
            **contatori
        ))

    return ProduttivitaResponse(
        data_riferimento=oggi.isoformat(),
        tipo="sessione",
        operatori=operatori_list
    )


# =============================================================================
# ENDPOINT: PRODUTTIVITÀ GIORNALIERA
# =============================================================================

@router.get("/giorno/{data_rif}", response_model=ProduttivitaResponse, summary="Produttività giornaliera")
async def get_produttivita_giorno(
    data_rif: date,
    current_user: UtenteResponse = Depends(get_current_user)
) -> ProduttivitaResponse:
    """
    Recupera statistiche produttività per una data specifica (dati consolidati).
    """
    db = _get_db()

    filtro, params = _get_operatori_visibili(current_user)

    # Recupera operatori visibili
    cursor = db.execute(f"""
        SELECT id_operatore, username, nome, cognome, ruolo
        FROM operatori
        WHERE attivo = TRUE AND {filtro}
        ORDER BY cognome, nome
    """, tuple(params))

    operatori_list = []
    for op in cursor.fetchall():
        id_op = op["id_operatore"]

        # Tempo per sezione (giornaliero)
        tempo_sezioni = _get_tempo_sezioni(db, id_op, data_rif)
        tempo_totale = sum(t.durata_secondi for t in tempo_sezioni)

        # Contatori
        contatori = _get_contatori_operatore(db, id_op, data_rif)

        operatori_list.append(ProduttivitaOperatore(
            id_operatore=id_op,
            username=op["username"],
            nome=op["nome"],
            cognome=op["cognome"],
            ruolo=op["ruolo"],
            tempo_totale_secondi=tempo_totale,
            tempo_formattato=_format_duration(tempo_totale),
            tempo_per_sezione=tempo_sezioni,
            **contatori
        ))

    return ProduttivitaResponse(
        data_riferimento=data_rif.isoformat(),
        tipo="giorno",
        operatori=operatori_list
    )


# =============================================================================
# ENDPOINT: ULTIME TASK
# =============================================================================

@router.get("/ultime-task", response_model=UltimeTaskResponse, summary="Ultime task operatore")
async def get_ultime_task(
    id_operatore: Optional[int] = Query(None),
    limit: int = Query(10, ge=1, le=50),
    current_user: UtenteResponse = Depends(get_current_user)
) -> UltimeTaskResponse:
    """
    Recupera le ultime N operazioni di un operatore.
    Se id_operatore non specificato, usa l'utente corrente.
    """
    db = _get_db()

    target_id = id_operatore or current_user.id_operatore

    # Verifica permessi
    if target_id != current_user.id_operatore:
        if current_user.ruolo == RuoloUtente.OPERATORE:
            raise HTTPException(status_code=403, detail="Non puoi vedere le task di altri operatori")

        # Verifica che l'operatore target sia visibile
        filtro, params = _get_operatori_visibili(current_user)
        cursor = db.execute(f"""
            SELECT 1 FROM operatori WHERE id_operatore = %s AND {filtro}
        """, tuple([target_id] + params))
        if not cursor.fetchone():
            raise HTTPException(status_code=403, detail="Operatore non accessibile")

    # Recupera info operatore
    cursor = db.execute("""
        SELECT username FROM operatori WHERE id_operatore = %s
    """, (target_id,))
    op_row = cursor.fetchone()
    if not op_row:
        raise HTTPException(status_code=404, detail="Operatore non trovato")

    # Recupera ultime task
    cursor = db.execute("""
        SELECT timestamp, tipo_operazione, descrizione, entita, id_entita
        FROM log_operazioni
        WHERE id_operatore = %s
        ORDER BY timestamp DESC
        LIMIT %s
    """, (target_id, limit))

    tasks = []
    for row in cursor.fetchall():
        ts = row["timestamp"]
        if isinstance(ts, datetime):
            ts = ts.strftime("%H:%M:%S")
        elif isinstance(ts, str) and len(ts) > 10:
            ts = ts[11:19]  # Estrai HH:MM:SS

        tasks.append(TaskRecente(
            timestamp=ts,
            tipo_operazione=row["tipo_operazione"],
            descrizione=row["descrizione"],
            entita=row["entita"],
            id_entita=row["id_entita"]
        ))

    return UltimeTaskResponse(
        id_operatore=target_id,
        username=op_row["username"],
        tasks=tasks
    )
