# =============================================================================
# SERV.O v9.0 - ROUTER SUPERVISIONE
# =============================================================================
# Router principale che include tutti i sub-router per supervisione
#
# Struttura modulare:
# - espositore.py: Supervisione espositori e workflow ordine
# - listino.py: Supervisione listini e correzione prezzi
# - lookup.py: Supervisione lookup (LKP-A01/A02)
# - prezzo.py: Supervisione prezzo (PRICE-A01)
# - aic.py: Supervisione AIC (AIC-A01) - v9.0
# - patterns.py: Criteri ML e pattern matching
# - bulk.py: Operazioni bulk e pending raggruppata
# - schemas.py: Modelli Pydantic condivisi
# =============================================================================

from fastapi import APIRouter

from . import espositore, listino, lookup, prezzo, bulk, aic
from .patterns import router as criteri_router, ml_router, confronto_router


# Router principale
router = APIRouter(prefix="/supervisione", tags=["Supervisione"])

# Include sub-routers
router.include_router(bulk.router)  # /pending, /pending/count, /pending/grouped, /pattern/*/bulk
router.include_router(espositore.router)  # /{id}/approva, /{id}/rifiuta, /{id}/modifica, workflow
router.include_router(listino.router)  # /listino/*
router.include_router(lookup.router)  # /lookup/*
router.include_router(prezzo.router)  # /prezzo/*
router.include_router(aic.router)  # /aic/* - v9.0
router.include_router(criteri_router)  # /criteri/*
router.include_router(ml_router)  # /ml/*
router.include_router(confronto_router)  # /{id}/confronto-ml, /{id}/risolvi-conflitto


# Export per compatibilita con main.py
__all__ = ['router']
