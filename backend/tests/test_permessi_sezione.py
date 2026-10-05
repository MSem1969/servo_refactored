# =============================================================================
# SERV.O - TEST PERMESSI DI MODIFICA PER SEZIONE
# =============================================================================
# puo_modificare_sezione legge can_edit dalla matrice permessi_ruolo
# (Impostazioni → Permessi): nessun ruolo, a parte admin, e' scritto nel codice.
# =============================================================================

import pytest

from app.auth import dependencies
from app.auth.models import RuoloUtente
from app.auth.dependencies import puo_modificare_sezione


class _Cursor:
    def __init__(self, row):
        self._row = row

    def fetchone(self):
        return self._row


class _MatriceDb:
    """Simula permessi_ruolo: {(ruolo, sezione): can_edit}."""
    def __init__(self, matrice):
        self.matrice = matrice
        self.queries = 0

    def execute(self, sql, params):
        self.queries += 1
        if params not in self.matrice:
            return _Cursor(None)
        return _Cursor({"can_edit": self.matrice[params]})


@pytest.fixture
def matrice(monkeypatch):
    db = _MatriceDb({
        ("supervisore", "tracciati"): True,
        ("operatore", "tracciati"): False,
    })
    monkeypatch.setattr(dependencies, "_get_db", lambda: db)
    return db


def test_supervisore_abilitato_da_matrice(matrice):
    assert puo_modificare_sezione(RuoloUtente.SUPERVISORE, "tracciati") is True


def test_operatore_non_abilitato_da_matrice(matrice):
    assert puo_modificare_sezione(RuoloUtente.OPERATORE, "tracciati") is False


def test_riga_assente_nega(matrice):
    assert puo_modificare_sezione(RuoloUtente.SUPERUSER, "tracciati") is False


def test_revoca_dalla_matrice_ha_effetto(matrice):
    matrice.matrice[("supervisore", "tracciati")] = False
    assert puo_modificare_sezione(RuoloUtente.SUPERVISORE, "tracciati") is False


def test_admin_sempre_abilitato_senza_query(matrice):
    assert puo_modificare_sezione(RuoloUtente.ADMIN, "tracciati") is True
    assert puo_modificare_sezione("admin", "tracciati") is True
    assert matrice.queries == 0


def test_ruolo_come_stringa(matrice):
    assert puo_modificare_sezione("supervisore", "tracciati") is True


def test_endpoint_riemissione_usano_la_matrice():
    """Nessun controllo 'solo admin' cablato sugli endpoint di riemissione."""
    from app.routers import tracciati
    assert not hasattr(tracciati, "_require_admin")
    from fastapi.routing import APIRoute
    protetti = {"/tracciati/{id_esportazione}/raw",
                "/tracciati/{id_esportazione}/riemetti",
                "/tracciati/{id_esportazione}/ritrasmetti"}
    trovati = set()
    for r in tracciati.router.routes:
        if isinstance(r, APIRoute) and r.path in protetti:
            deps = [d.call for d in r.dependant.dependencies]
            assert tracciati._require_tracciati_edit in deps, r.path
            trovati.add(r.path)
    assert trovati == protetti
