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


# ---------------------------------------------------------------------------
# can_view, propagazione GLOBALE, gerarchia della matrice
# ---------------------------------------------------------------------------

class _MatriceViewEditDb:
    """permessi_ruolo completa: {(ruolo, sezione): (can_view, can_edit)}."""
    def __init__(self, matrice):
        self.matrice = matrice

    def execute(self, sql, params):
        ruolo, sezione = params
        if (ruolo, sezione) not in self.matrice:
            return _Cursor(None)
        v, e = self.matrice[(ruolo, sezione)]
        return _Cursor({"can_view": v, "can_edit": e})


@pytest.fixture
def matrice_ve(monkeypatch):
    db = _MatriceViewEditDb({
        ("supervisore", "backup"): (True, False),
        ("supervisore", "supervisione"): (True, True),
        ("operatore", "supervisione"): (True, False),
    })
    monkeypatch.setattr(dependencies, "_get_db", lambda: db)
    return db


def test_view_ed_edit_distinti(matrice_ve):
    from app.auth.dependencies import puo_vedere_sezione
    assert puo_vedere_sezione("supervisore", "backup") is True
    assert puo_modificare_sezione("supervisore", "backup") is False


def test_ruolo_maiuscolo_normalizzato(matrice_ve):
    assert puo_modificare_sezione("SUPERVISORE", "supervisione") is True


def test_propagazione_globale_segue_matrice(matrice_ve):
    from app.services.anomalies.propagazione import get_livello_permesso
    assert get_livello_permesso("supervisore") == ["ORDINE", "GLOBALE"]
    assert get_livello_permesso("operatore") == ["ORDINE"]
    # Concedere can_edit su supervisione all'operatore gli apre il GLOBALE
    matrice_ve.matrice[("operatore", "supervisione")] = (True, True)
    assert get_livello_permesso("operatore") == ["ORDINE", "GLOBALE"]


class _User:
    def __init__(self, ruolo):
        self.ruolo = RuoloUtente(ruolo)
        self.username = ruolo


def test_matrice_gerarchica_ruoli_gestibili():
    from app.routers.permessi import _ruoli_gestibili
    assert _ruoli_gestibili(_User("admin")) == ["superuser", "supervisore", "operatore", "readonly"]
    assert _ruoli_gestibili(_User("superuser")) == ["supervisore", "operatore", "readonly"]
    assert _ruoli_gestibili(_User("supervisore")) == ["operatore", "readonly"]
    assert _ruoli_gestibili(_User("operatore")) == []


def test_matrice_non_si_modifica_un_pari_o_superiore():
    from fastapi import HTTPException
    from app.routers.permessi import _verifica_ruolo_gestibile
    _verifica_ruolo_gestibile(_User("supervisore"), "operatore")
    for target in ("supervisore", "superuser", "admin"):
        with pytest.raises(HTTPException) as e:
            _verifica_ruolo_gestibile(_User("supervisore"), target)
        assert e.value.status_code == 403


def test_non_si_concede_un_permesso_che_non_si_ha(matrice_ve):
    from fastapi import HTTPException
    from app.routers.permessi import _verifica_concessione, PermessoUpdate
    sup = _User("supervisore")
    # backup: il supervisore ha view ma non edit
    _verifica_concessione(matrice_ve, sup, "operatore", "backup",
                          PermessoUpdate(can_view=True, can_edit=False))
    with pytest.raises(HTTPException) as e:
        _verifica_concessione(matrice_ve, sup, "operatore", "backup",
                              PermessoUpdate(can_view=True, can_edit=True))
    assert e.value.status_code == 403


def test_si_puo_lasciare_o_togliere_un_permesso_che_non_si_ha(matrice_ve):
    from app.routers.permessi import _verifica_concessione, PermessoUpdate
    sup = _User("supervisore")
    # l'operatore ha gia' backup edit (dato dall'admin): il supervisore non lo blocca
    matrice_ve.matrice[("operatore", "backup")] = (True, True)
    _verifica_concessione(matrice_ve, sup, "operatore", "backup",
                          PermessoUpdate(can_view=True, can_edit=True))
    _verifica_concessione(matrice_ve, sup, "operatore", "backup",
                          PermessoUpdate(can_view=False, can_edit=False))


# ---------------------------------------------------------------------------
# Guardia: nessun controllo di ruolo cablato per abilitare azioni di sezione
# ---------------------------------------------------------------------------

def test_nessun_controllo_di_ruolo_cablato_nei_router_di_sezione():
    """I permessi si regolano dalla matrice (CLAUDE.md, sezione Permessi)."""
    import pathlib, re
    base = pathlib.Path(__file__).resolve().parents[1] / "app"
    vietati = re.compile(
        r"require_admin\b|_require_admin|_check_admin_role|"
        r"ruolo\s*(?:==|!=)\s*['\"]admin['\"]|"
        r"ruolo[^\n]*\s(?:not\s+)?in\s*[\[(]\s*['\"](?:admin|supervisore|SUPERVISORE)",
    )
    file_di_sezione = [
        "routers/tracciati.py", "routers/backup.py", "routers/email.py",
        "routers/ftp_endpoints.py", "routers/crm.py", "routers/anomalie.py",
        "routers/admin.py", "services/anomalies/propagazione.py",
        "services/anomalies/resolver.py",
    ]
    trovati = []
    for rel in file_di_sezione:
        for n, riga in enumerate((base / rel).read_text().splitlines(), 1):
            if vietati.search(riga) and not riga.lstrip().startswith("#"):
                trovati.append(f"{rel}:{n}: {riga.strip()}")
    assert not trovati, "Controlli di ruolo cablati:\n" + "\n".join(trovati)
