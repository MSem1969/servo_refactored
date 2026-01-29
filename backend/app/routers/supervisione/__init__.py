# =============================================================================
# SERV.O v11.4 - ROUTER SUPERVISIONE
# =============================================================================
# Router principale che include tutti i sub-router per supervisione
#
# Struttura modulare:
# - espositore.py: Supervisione espositori e workflow ordine
# - listino.py: Supervisione listini e correzione prezzi (deprecato, usa prezzo)
# - prezzo.py: Supervisione prezzo unificata (PRICE + LISTINO)
# - anagrafica.py: Supervisione anagrafica (LKP + DEP) - v11.4 NUOVO
# - aic.py: Supervisione AIC (AIC-A01)
# - patterns.py: Criteri ML e pattern matching
# - bulk.py: Operazioni bulk e pending raggruppata
# - schemas.py: Modelli Pydantic condivisi
#
# v11.4: Aggiunto anagrafica.py, deprecato lookup.py
# =============================================================================

from fastapi import APIRouter

from . import espositore, listino, lookup, prezzo, bulk, aic, anagrafica
from .patterns import router as criteri_router, ml_router, confronto_router


# Router principale
router = APIRouter(prefix="/supervisione", tags=["Supervisione"])

# Include sub-routers
router.include_router(bulk.router)  # /pending, /pending/count, /pending/grouped, /pattern/*/bulk
router.include_router(espositore.router)  # /{id}/approva, /{id}/rifiuta, /{id}/modifica, workflow
router.include_router(listino.router)  # /listino/* (legacy, usa prezzo)
router.include_router(lookup.router)  # /lookup/* (legacy, usa anagrafica)
router.include_router(prezzo.router)  # /prezzo/*
router.include_router(aic.router)  # /aic/*
router.include_router(anagrafica.router)  # /anagrafica/* - v11.4
router.include_router(criteri_router)  # /criteri/*
router.include_router(ml_router)  # /ml/*
router.include_router(confronto_router)  # /{id}/confronto-ml, /{id}/risolvi-conflitto


# Export per compatibilita con main.py
__all__ = ['router']
