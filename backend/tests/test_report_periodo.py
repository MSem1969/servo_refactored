# =============================================================================
# SERV.O - TEST FILTRO PERIODO REPORT
# =============================================================================
# Il filtro per data consegna deve usare la data della SINGOLA RIGA, non
# v_ordini_completi.data_consegna (che e' il MIN delle righe aperte).
# =============================================================================

from app.routers.report import _condizioni_periodo


class TestCondizioniPeriodo:

    def test_tipo_ordine_usa_data_testata(self):
        conds, params = _condizioni_periodo("ordine", "2026-06-01", "2026-06-30")
        assert conds == ["t.data_ordine >= %s", "t.data_ordine <= %s"]
        assert params == ["2026-06-01", "2026-06-30"]

    def test_consegna_usa_la_data_di_riga(self):
        """
        Regressione: si filtrava su t.data_consegna, cioe' il MIN delle righe
        aperte. Su un ordine multi-data (DOMPE, BAYER) questo attribuiva TUTTE
        le righe al periodo piu' imminente e cambiava valore a ogni evasione.
        """
        conds, params = _condizioni_periodo("consegna", "2026-06-01", "2026-06-30")
        assert conds == ["d.data_consegna_riga >= %s", "d.data_consegna_riga <= %s"]
        assert params == ["2026-06-01", "2026-06-30"]
        assert not any("t.data_consegna" in c for c in conds)

    def test_consegna_senza_riga_in_scope_usa_un_solo_exists(self):
        """
        Due EXISTS separati accetterebbero un ordine con una riga PRIMA del
        periodo e una DOPO, ma nessuna dentro. Deve essercene uno solo, con
        entrambi i limiti.
        """
        conds, params = _condizioni_periodo(
            "consegna", "2026-06-01", "2026-06-30", riga_in_scope=False
        )
        assert len(conds) == 1
        sql = conds[0]
        assert sql.count("EXISTS") == 1
        assert "od_dc.id_testata = t.id_testata" in sql
        assert "od_dc.data_consegna_riga >= %s" in sql
        assert "od_dc.data_consegna_riga <= %s" in sql
        assert params == ["2026-06-01", "2026-06-30"]

    def test_un_solo_estremo(self):
        conds, params = _condizioni_periodo("consegna", "2026-06-01", None)
        assert conds == ["d.data_consegna_riga >= %s"]
        assert params == ["2026-06-01"]

        conds, params = _condizioni_periodo("consegna", None, "2026-06-30")
        assert conds == ["d.data_consegna_riga <= %s"]
        assert params == ["2026-06-30"]

    def test_nessuna_data_nessuna_condizione(self):
        for tipo in ("ordine", "consegna"):
            for scope in (True, False):
                conds, params = _condizioni_periodo(tipo, None, None, riga_in_scope=scope)
                assert conds == []
                assert params == []

    def test_ordine_ignora_riga_in_scope(self):
        """Il filtro per data ordine e' sempre a livello testata."""
        a = _condizioni_periodo("ordine", "2026-06-01", "2026-06-30", riga_in_scope=True)
        b = _condizioni_periodo("ordine", "2026-06-01", "2026-06-30", riga_in_scope=False)
        assert a == b
