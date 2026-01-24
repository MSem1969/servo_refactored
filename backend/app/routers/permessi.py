# =============================================================================
# SERV.O v10.0 - PERMISSIONS MANAGEMENT API
# =============================================================================
# Endpoint per gestione matrice permessi editabile da admin
# =============================================================================

from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from ..database_pg import get_db
from ..auth.dependencies import get_current_user, require_admin


router = APIRouter(prefix="/permessi", tags=["Permessi"])


# =============================================================================
# SCHEMAS
# =============================================================================

class SezioneResponse(BaseModel):
    codice_sezione: str
    nome_display: str
    descrizione: Optional[str]
    icona: Optional[str]
    ordine_menu: int
    is_active: bool


class PermessoResponse(BaseModel):
    ruolo: str
    codice_sezione: str
    can_view: bool
    can_edit: bool


class PermessoUpdate(BaseModel):
    can_view: bool
    can_edit: bool


class MatricePermessi(BaseModel):
    """Matrice completa permessi per tutti i ruoli."""
    sezioni: List[SezioneResponse]
    ruoli: List[str]
    permessi: Dict[str, Dict[str, PermessoResponse]]  # ruolo -> sezione -> permesso


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/sezioni", summary="Lista sezioni applicazione")
async def get_sezioni() -> List[SezioneResponse]:
    """Ritorna lista sezioni applicazione disponibili."""
    db = get_db()

    rows = db.execute("""
        SELECT codice_sezione, nome_display, descrizione, icona, ordine_menu, is_active
        FROM app_sezioni
        WHERE is_active = TRUE
        ORDER BY ordine_menu
    """).fetchall()

    return [SezioneResponse(**dict(r)) for r in rows]


@router.get("/ruoli", summary="Lista ruoli disponibili")
async def get_ruoli() -> List[str]:
    """Ritorna lista ruoli disponibili nel sistema."""
    return ['admin', 'superuser', 'supervisore', 'operatore', 'readonly']


@router.get("/matrice", summary="Matrice completa permessi")
async def get_matrice_permessi(
    current_user = Depends(require_admin)
) -> MatricePermessi:
    """
    Ritorna matrice completa permessi per tutti i ruoli.
    Solo admin può visualizzare/modificare.
    """
    db = get_db()

    # Get sezioni
    sezioni_rows = db.execute("""
        SELECT codice_sezione, nome_display, descrizione, icona, ordine_menu, is_active
        FROM app_sezioni
        WHERE is_active = TRUE
        ORDER BY ordine_menu
    """).fetchall()
    sezioni = [SezioneResponse(**dict(r)) for r in sezioni_rows]

    # Get all permessi
    permessi_rows = db.execute("""
        SELECT ruolo, codice_sezione, can_view, can_edit
        FROM permessi_ruolo
        ORDER BY ruolo, codice_sezione
    """).fetchall()

    # Build matrix
    ruoli = ['admin', 'superuser', 'supervisore', 'operatore', 'readonly']
    permessi: Dict[str, Dict[str, PermessoResponse]] = {r: {} for r in ruoli}

    for row in permessi_rows:
        ruolo = row['ruolo']
        sezione = row['codice_sezione']
        if ruolo in permessi:
            permessi[ruolo][sezione] = PermessoResponse(
                ruolo=ruolo,
                codice_sezione=sezione,
                can_view=row['can_view'],
                can_edit=row['can_edit']
            )

    return MatricePermessi(
        sezioni=sezioni,
        ruoli=ruoli,
        permessi=permessi
    )


@router.get("/ruolo/{ruolo}", summary="Permessi per ruolo specifico")
async def get_permessi_ruolo(ruolo: str) -> Dict[str, PermessoResponse]:
    """Ritorna permessi per un ruolo specifico."""
    db = get_db()

    rows = db.execute("""
        SELECT ruolo, codice_sezione, can_view, can_edit
        FROM permessi_ruolo
        WHERE ruolo = %s
    """, (ruolo,)).fetchall()

    return {
        row['codice_sezione']: PermessoResponse(
            ruolo=row['ruolo'],
            codice_sezione=row['codice_sezione'],
            can_view=row['can_view'],
            can_edit=row['can_edit']
        )
        for row in rows
    }


@router.put("/ruolo/{ruolo}/sezione/{sezione}", summary="Aggiorna permesso")
async def update_permesso(
    ruolo: str,
    sezione: str,
    update: PermessoUpdate,
    current_user = Depends(require_admin)
) -> PermessoResponse:
    """
    Aggiorna permesso per una combinazione ruolo/sezione.
    Solo admin può modificare.

    NOTA: I permessi admin non possono essere ridotti (sicurezza).
    """
    db = get_db()

    # Protezione: non permettere di rimuovere permessi admin
    if ruolo == 'admin' and (not update.can_view or not update.can_edit):
        raise HTTPException(
            status_code=400,
            detail="Non è possibile rimuovere permessi all'admin"
        )

    # Verifica che la sezione esista
    sezione_exists = db.execute(
        "SELECT 1 FROM app_sezioni WHERE codice_sezione = %s",
        (sezione,)
    ).fetchone()

    if not sezione_exists:
        raise HTTPException(status_code=404, detail=f"Sezione '{sezione}' non trovata")

    # Verifica che il ruolo sia valido
    ruoli_validi = ['admin', 'superuser', 'supervisore', 'operatore', 'readonly']
    if ruolo not in ruoli_validi:
        raise HTTPException(status_code=400, detail=f"Ruolo '{ruolo}' non valido")

    # Upsert permesso
    db.execute("""
        INSERT INTO permessi_ruolo (ruolo, codice_sezione, can_view, can_edit, updated_at, updated_by)
        VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, %s)
        ON CONFLICT (ruolo, codice_sezione)
        DO UPDATE SET
            can_view = EXCLUDED.can_view,
            can_edit = EXCLUDED.can_edit,
            updated_at = CURRENT_TIMESTAMP,
            updated_by = EXCLUDED.updated_by
    """, (ruolo, sezione, update.can_view, update.can_edit, current_user.username))

    db.commit()

    return PermessoResponse(
        ruolo=ruolo,
        codice_sezione=sezione,
        can_view=update.can_view,
        can_edit=update.can_edit
    )


@router.put("/ruolo/{ruolo}/bulk", summary="Aggiorna tutti i permessi di un ruolo")
async def update_permessi_ruolo_bulk(
    ruolo: str,
    permessi: Dict[str, PermessoUpdate],
    current_user = Depends(require_admin)
) -> Dict[str, PermessoResponse]:
    """
    Aggiorna tutti i permessi di un ruolo in una sola chiamata.

    Args:
        ruolo: Ruolo da aggiornare
        permessi: Dict con chiave = codice_sezione, valore = PermessoUpdate
    """
    db = get_db()

    # Protezione admin
    if ruolo == 'admin':
        raise HTTPException(
            status_code=400,
            detail="I permessi admin non possono essere modificati in bulk"
        )

    ruoli_validi = ['superuser', 'supervisore', 'operatore', 'readonly']
    if ruolo not in ruoli_validi:
        raise HTTPException(status_code=400, detail=f"Ruolo '{ruolo}' non valido")

    result = {}
    for sezione, update in permessi.items():
        db.execute("""
            INSERT INTO permessi_ruolo (ruolo, codice_sezione, can_view, can_edit, updated_at, updated_by)
            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, %s)
            ON CONFLICT (ruolo, codice_sezione)
            DO UPDATE SET
                can_view = EXCLUDED.can_view,
                can_edit = EXCLUDED.can_edit,
                updated_at = CURRENT_TIMESTAMP,
                updated_by = EXCLUDED.updated_by
        """, (ruolo, sezione, update.can_view, update.can_edit, current_user.username))

        result[sezione] = PermessoResponse(
            ruolo=ruolo,
            codice_sezione=sezione,
            can_view=update.can_view,
            can_edit=update.can_edit
        )

    db.commit()
    return result


@router.get("/me", summary="I miei permessi")
async def get_my_permissions(
    current_user = Depends(get_current_user)
) -> Dict[str, PermessoResponse]:
    """
    Ritorna i permessi dell'utente corrente.
    Usato dal frontend per determinare quali sezioni mostrare.
    """
    db = get_db()

    rows = db.execute("""
        SELECT ruolo, codice_sezione, can_view, can_edit
        FROM permessi_ruolo
        WHERE ruolo = %s
    """, (current_user.ruolo,)).fetchall()

    return {
        row['codice_sezione']: PermessoResponse(
            ruolo=row['ruolo'],
            codice_sezione=row['codice_sezione'],
            can_view=row['can_view'],
            can_edit=row['can_edit']
        )
        for row in rows
    }


@router.get("/sezioni-visibili", summary="Sezioni visibili per utente corrente")
async def get_sezioni_visibili(
    current_user = Depends(get_current_user)
) -> List[str]:
    """
    Ritorna lista codici sezione visibili per l'utente corrente.
    Usato dal frontend per filtrare il menu.
    """
    db = get_db()

    rows = db.execute("""
        SELECT codice_sezione
        FROM permessi_ruolo
        WHERE ruolo = %s AND can_view = TRUE
        ORDER BY codice_sezione
    """, (current_user.ruolo,)).fetchall()

    return [row['codice_sezione'] for row in rows]
