# =============================================================================
# SERV.O v11.0 - SUPERVISIONE ESPOSITORE
# =============================================================================
# Endpoint per gestione supervisione espositori e workflow ordine
# v11.0: Auto-detect supervision type per unified approval endpoint
# =============================================================================

from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from ...database_pg import get_db
from ...services.supervisione import (
    approva_supervisione,
    rifiuta_supervisione,
    modifica_supervisione,
    get_supervisioni_per_ordine,
)
from ...services.supervision.lookup import approva_supervisione_lookup, rifiuta_supervisione_lookup
from .schemas import DecisioneApprova, DecisioneRifiuta, DecisioneModifica


router = APIRouter(tags=["Supervisione Espositore"])


def detect_supervision_type(db, id_supervisione: int) -> Optional[str]:
    """
    Rileva il tipo di supervisione cercando in tutte le tabelle.
    Ritorna: 'espositore', 'lookup', 'listino', 'prezzo', 'aic' o None
    """
    tables = [
        ('supervisione_espositore', 'espositore'),
        ('supervisione_lookup', 'lookup'),
        ('supervisione_listino', 'listino'),
        ('supervisione_prezzo', 'prezzo'),
        ('supervisione_aic', 'aic'),
    ]
    for table, tipo in tables:
        try:
            result = db.execute(
                f"SELECT 1 FROM {table} WHERE id_supervisione = %s",
                (id_supervisione,)
            ).fetchone()
            if result:
                return tipo
        except Exception:
            continue
    return None


# =============================================================================
# ENDPOINT DETTAGLIO SUPERVISIONE
# =============================================================================

@router.get("/{id_supervisione}", summary="Dettaglio supervisione")
async def get_supervisione(id_supervisione: int):
    """
    Ritorna dettagli completi di una supervisione.

    Include:
    - Dati anomalia
    - Stato attuale
    - Informazioni pattern ML
    - Storico decisioni
    """
    db = get_db()

    row = db.execute("""
        SELECT se.*, coe.count_approvazioni, coe.is_ordinario, coe.pattern_descrizione
        FROM SUPERVISIONE_ESPOSITORE se
        LEFT JOIN CRITERI_ORDINARI_ESPOSITORE coe ON se.pattern_signature = coe.pattern_signature
        WHERE se.id_supervisione = %s
    """, (id_supervisione,)).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Supervisione non trovata")

    return dict(row)


@router.get("/ordine/{id_testata}", summary="Supervisioni per ordine")
async def get_supervisioni_ordine(id_testata: int):
    """Ritorna tutte le supervisioni per un ordine specifico."""
    supervisioni = get_supervisioni_per_ordine(id_testata)
    return {
        "id_testata": id_testata,
        "count": len(supervisioni),
        "supervisioni": supervisioni
    }


# =============================================================================
# ENDPOINT DECISIONI
# =============================================================================

@router.post("/{id_supervisione}/approva", summary="Approva supervisione")
async def approva(id_supervisione: int, decisione: DecisioneApprova):
    """
    Approva una supervisione (auto-detect tipo).

    v11.0: Rileva automaticamente il tipo di supervisione e chiama
    l'handler corretto (espositore, lookup, listino, prezzo, aic).

    Effetti:
    - Stato -> APPROVED
    - Incrementa contatore pattern
    - Se pattern raggiunge soglia (5), diventa ordinario
    - Sblocca ordine se era l'ultima pending
    """
    db = get_db()
    tipo = detect_supervision_type(db, id_supervisione)

    if not tipo:
        raise HTTPException(status_code=404, detail="Supervisione non trovata")

    success = False

    if tipo == 'espositore':
        success = approva_supervisione(
            id_supervisione,
            decisione.operatore,
            decisione.note
        )
    elif tipo == 'lookup':
        # Per lookup, approva con dati esistenti (farmacia già suggerita)
        success = approva_supervisione_lookup(
            id_supervisione,
            decisione.operatore,
            min_id=None,  # Usa quello già presente nell'ordine
            id_farmacia=None,
            note=decisione.note
        )
    elif tipo in ('listino', 'prezzo', 'aic'):
        # Per altri tipi, usa endpoint specifici
        raise HTTPException(
            status_code=400,
            detail=f"Usa endpoint specifico per supervisione {tipo}"
        )

    if not success:
        raise HTTPException(status_code=500, detail="Errore durante l'approvazione")

    return {
        "success": True,
        "id_supervisione": id_supervisione,
        "tipo": tipo,
        "azione": "APPROVED",
        "operatore": decisione.operatore
    }


@router.post("/{id_supervisione}/rifiuta", summary="Rifiuta supervisione")
async def rifiuta(id_supervisione: int, decisione: DecisioneRifiuta):
    """
    Rifiuta una supervisione.

    Effetti:
    - Stato -> REJECTED
    - Reset contatore pattern a 0
    - Ordine rimane bloccato (richiede intervento manuale)
    """
    success = rifiuta_supervisione(
        id_supervisione,
        decisione.operatore,
        decisione.note
    )

    if not success:
        raise HTTPException(status_code=404, detail="Supervisione non trovata")

    return {
        "success": True,
        "id_supervisione": id_supervisione,
        "azione": "REJECTED",
        "operatore": decisione.operatore
    }


@router.post("/{id_supervisione}/modifica", summary="Modifica manuale")
async def modifica(id_supervisione: int, decisione: DecisioneModifica):
    """
    Applica modifiche manuali a un ordine in supervisione.

    Effetti:
    - Stato -> MODIFIED
    - Salva modifiche in JSON
    - NON incrementa pattern (caso speciale)
    - Sblocca ordine
    """
    success = modifica_supervisione(
        id_supervisione,
        decisione.operatore,
        decisione.modifiche,
        decisione.note
    )

    if not success:
        raise HTTPException(status_code=404, detail="Supervisione non trovata")

    return {
        "success": True,
        "id_supervisione": id_supervisione,
        "azione": "MODIFIED",
        "operatore": decisione.operatore
    }


# =============================================================================
# ENDPOINT WORKFLOW RITORNO A ORDINE
# =============================================================================

@router.post("/{id_supervisione}/completa-e-torna", summary="Approva e torna a ordine")
async def approva_e_torna(id_supervisione: int, decisione: DecisioneApprova):
    """
    Approva supervisione e aggiorna stato riga a SUPERVISIONATO.

    Usato dal workflow Ordine -> Supervisione -> Ordine.
    """
    db = get_db()

    # Ottieni id_testata dalla supervisione
    sup = db.execute(
        "SELECT id_testata FROM SUPERVISIONE_ESPOSITORE WHERE id_supervisione = %s",
        (id_supervisione,)
    ).fetchone()

    if not sup:
        raise HTTPException(status_code=404, detail="Supervisione non trovata")

    # Approva supervisione
    success = approva_supervisione(
        id_supervisione,
        decisione.operatore,
        decisione.note
    )

    if not success:
        raise HTTPException(status_code=500, detail="Errore approvazione")

    # Aggiorna stato riga a SUPERVISIONATO
    # v9.1: ESCLUDI righe ARCHIVIATO - stato finale immutabile
    db.execute("""
        UPDATE ORDINI_DETTAGLIO
        SET stato_riga = 'SUPERVISIONATO',
            note_supervisione = COALESCE(note_supervisione || ' | ', '') || %s
        WHERE id_supervisione = %s
          AND stato_riga != 'ARCHIVIATO'
    """, (f"[{decisione.operatore}] Approvato", id_supervisione))
    db.commit()

    return {
        "success": True,
        "id_supervisione": id_supervisione,
        "id_testata": sup['id_testata'],
        "azione": "APPROVED",
        "riga_stato": "SUPERVISIONATO",
        "redirect_url": f"/ordini/{sup['id_testata']}"
    }


@router.post("/{id_supervisione}/modifica-e-torna", summary="Modifica e torna a ordine")
async def modifica_e_torna(id_supervisione: int, decisione: DecisioneModifica):
    """
    Applica modifiche riga e torna a ordine.
    """
    db = get_db()

    # Ottieni id_testata dalla supervisione
    sup = db.execute(
        "SELECT id_testata FROM SUPERVISIONE_ESPOSITORE WHERE id_supervisione = %s",
        (id_supervisione,)
    ).fetchone()

    if not sup:
        raise HTTPException(status_code=404, detail="Supervisione non trovata")

    # Applica modifica
    success = modifica_supervisione(
        id_supervisione,
        decisione.operatore,
        decisione.modifiche,
        decisione.note
    )

    if not success:
        raise HTTPException(status_code=500, detail="Errore modifica")

    # Aggiorna stato riga a SUPERVISIONATO
    # v9.1: ESCLUDI righe ARCHIVIATO - stato finale immutabile
    db.execute("""
        UPDATE ORDINI_DETTAGLIO
        SET stato_riga = 'SUPERVISIONATO',
            note_supervisione = COALESCE(note_supervisione || ' | ', '') || %s
        WHERE id_supervisione = %s
          AND stato_riga != 'ARCHIVIATO'
    """, (f"[{decisione.operatore}] Modificato", id_supervisione))
    db.commit()

    return {
        "success": True,
        "id_supervisione": id_supervisione,
        "id_testata": sup['id_testata'],
        "azione": "MODIFIED",
        "campi_modificati": list(decisione.modifiche.keys()),
        "redirect_url": f"/ordini/{sup['id_testata']}"
    }


@router.post("/{id_supervisione}/lascia-sospeso", summary="Lascia sospeso e torna")
async def lascia_sospeso(id_supervisione: int, operatore: str = Query(...)):
    """
    Torna a ordine senza decisione (riga rimane IN_SUPERVISIONE).
    """
    db = get_db()

    # Ottieni id_testata dalla supervisione
    sup = db.execute(
        "SELECT id_testata FROM SUPERVISIONE_ESPOSITORE WHERE id_supervisione = %s",
        (id_supervisione,)
    ).fetchone()

    if not sup:
        raise HTTPException(status_code=404, detail="Supervisione non trovata")

    return {
        "success": True,
        "id_supervisione": id_supervisione,
        "id_testata": sup['id_testata'],
        "stato": "PENDING",
        "redirect_url": f"/ordini/{sup['id_testata']}"
    }
