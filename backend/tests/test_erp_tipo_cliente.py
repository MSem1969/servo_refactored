# =============================================================================
# SERV.O - TEST TIPO CLIENTE ERP DA CATEGORIA (AGCATE) (2026-10)
# =============================================================================
# Caso reale: farmacia 15280 / parafarmacia 015280, salvata in anagrafica
# clienti SENZA zero (15280, categoria 17). La lunghezza non distingueva i
# due clienti: gli ERP-A01 della farmacia proponevano la P.IVA della
# parafarmacia, gli operatori la approvavano e alla 5a approvazione il
# pattern la applicava da solo e la scriveva sull'anagrafica (ordine 1906).
#
# - il tipo in anagrafica_clienti e' la categoria ERP (17 = parafarmacia)
# - il tipo dell'ordine e' il collegamento al Ministero
# - una P.IVA approvata o applicata da un pattern deve essere di un cliente
#   dello stesso tipo
# - il lookup Ministero prova l'altro elenco prima di dare LKP-A04
#
# I test DB girano in transazione annullata (vedi test_collisione_min_id).
# =============================================================================

from unittest.mock import MagicMock

import pytest

from tests.test_collisione_min_id import db_tx, _crea_ordine, _Row  # noqa: F401 (fixture)


FARM = '000099881'          # farmacia del Ministero (9 cifre)
CODICE_ERP = '99881'        # come lo salva l'ERP: per ENTRAMBI i clienti
PARAFARM = '099881'         # parafarmacia del Ministero (6 cifre)
PIVA_FARM = '09988100001'
PIVA_PARAFARM = '09988100002'


def _cliente(db, min_id, piva, categoria, codice):
    db.execute("""
        INSERT INTO anagrafica_clienti (codice_cliente, ragione_sociale_1, partita_iva,
                                        min_id, farmacia_categoria, deposito_riferimento)
        VALUES (%s, %s, %s, %s, %s, 'CT')
    """, (codice, f'TEST {codice}', piva, min_id, categoria))


@pytest.fixture
def omonimi_stesso_codice(db_tx):  # noqa: F811
    """Farmacia e parafarmacia con lo STESSO min_id: solo la categoria li distingue."""
    _cliente(db_tx, CODICE_ERP, PIVA_FARM, '001', 'TEST_AGF')
    _cliente(db_tx, CODICE_ERP, PIVA_PARAFARM, '017', 'TEST_AGP')
    return db_tx


class TestValidazioneDaCategoria:
    def test_farmacia_con_sua_piva_valida(self, omonimi_stesso_codice):
        from app.services.supervision.erp import valida_coerenza_erp
        assert valida_coerenza_erp(FARM, PIVA_FARM, False)['valido']

    def test_farmacia_non_prende_la_piva_della_parafarmacia(self, omonimi_stesso_codice):
        """Ordine 1906: la P.IVA ERP proposta era quella della parafarmacia."""
        from app.services.supervision.erp import valida_coerenza_erp
        r = valida_coerenza_erp(FARM, PIVA_PARAFARM, False)
        assert r['codice_anomalia'] == 'ERP-A01'
        assert r['piva_erp'] == PIVA_FARM

    def test_parafarmacia_senza_zero_trovata_dalla_categoria(self, omonimi_stesso_codice):
        from app.services.supervision.erp import valida_coerenza_erp
        assert valida_coerenza_erp(PARAFARM, PIVA_PARAFARM, True)['valido']
        r = valida_coerenza_erp(PARAFARM, PIVA_FARM, True)
        assert r['piva_erp'] == PIVA_PARAFARM

    def test_tipo_dall_ordine_vince_sul_codice_del_pdf(self, omonimi_stesso_codice):
        """Il PDF puo' scrivere la parafarmacia senza zero: 99881 sembra una farmacia."""
        from app.services.supervision.erp import valida_coerenza_erp
        assert valida_coerenza_erp(CODICE_ERP, PIVA_PARAFARM, True)['valido']
        assert not valida_coerenza_erp(CODICE_ERP, PIVA_PARAFARM, False)['valido']

    def test_categoria_4_conta_come_farmacia(self, db_tx):  # noqa: F811
        from app.services.supervision.erp import valida_coerenza_erp
        _cliente(db_tx, '99882', PIVA_FARM, '4', 'TEST_AG4')
        assert valida_coerenza_erp('000099882', PIVA_FARM, False)['valido']
        assert valida_coerenza_erp('099882', PIVA_FARM, True)['codice_anomalia'] == 'ERP-A02'


class TestPivaDelTipo:
    def test_rifiuta_la_piva_dell_omonimo_e_lo_nomina(self, omonimi_stesso_codice):
        from app.services.supervision.erp import verifica_piva_del_tipo
        motivo = verifica_piva_del_tipo(FARM, PIVA_PARAFARM, False)
        assert motivo and 'parafarmacia' in motivo and 'TEST TEST_AGP' in motivo

    def test_accetta_la_piva_del_cliente_giusto(self, omonimi_stesso_codice):
        from app.services.supervision.erp import verifica_piva_del_tipo
        assert verifica_piva_del_tipo(FARM, PIVA_FARM, False) is None

    def test_rifiuta_piva_sconosciuta(self, omonimi_stesso_codice):
        from app.services.supervision.erp import verifica_piva_del_tipo
        assert 'nessuna farmacia' in verifica_piva_del_tipo(FARM, '09988100099', False)


class TestApprovazioneErp:
    def _supervisione(self, db, numero, piva_ordine):
        from app.services.supervision.erp import crea_supervisione_erp
        id_t = _crea_ordine(db, numero, 'ANOMALIA', codice=FARM, piva=piva_ordine)
        id_sup = crea_supervisione_erp(id_t, None, FARM, piva_ordine,
                                       partita_iva_erp=PIVA_PARAFARM)
        return id_t, id_sup

    def test_approvazione_con_piva_parafarmacia_rifiutata(self, omonimi_stesso_codice):
        from app.services.supervision.erp import approva_supervisione_erp
        db = omonimi_stesso_codice
        id_t, id_sup = self._supervisione(db, 'TEST_ERP_RIF', '09988100077')

        r = approva_supervisione_erp(id_sup, 'maria', PIVA_PARAFARM)

        assert not r['success'] and 'parafarmacia' in r['error']
        assert db.execute("SELECT stato FROM supervisione_erp WHERE id_supervisione = %s",
                          (id_sup,)).fetchone()['stato'] == 'PENDING'
        assert db.execute("SELECT partita_iva_estratta FROM ordini_testata WHERE id_testata = %s",
                          (id_t,)).fetchone()['partita_iva_estratta'] == '09988100077'

    def test_approvazione_con_piva_farmacia_ok(self, omonimi_stesso_codice):
        from app.services.supervision.erp import approva_supervisione_erp
        id_t, id_sup = self._supervisione(omonimi_stesso_codice, 'TEST_ERP_OK', '09988100077')
        assert approva_supervisione_erp(id_sup, 'maria', PIVA_FARM)['success']


class TestPatternNonApplicaPivaSbagliata:
    def test_pattern_ordinario_con_piva_parafarmacia_non_applicato(self, omonimi_stesso_codice):
        """Il pattern 15280 promosso il 2026-10-20 avrebbe corretto ogni ordine nuovo."""
        from app.services.supervision.erp import calcola_pattern_signature_erp, valuta_anomalia_erp
        db = omonimi_stesso_codice
        sig = calcola_pattern_signature_erp(FARM, False)
        db.execute("DELETE FROM criteri_ordinari_erp WHERE pattern_signature = %s", (sig,))
        db.execute("""
            INSERT INTO criteri_ordinari_erp (pattern_signature, pattern_descrizione, min_id,
                                              partita_iva_corretta, count_approvazioni, is_ordinario)
            VALUES (%s, 'test', %s, %s, 6, TRUE)
        """, (sig, CODICE_ERP, PIVA_PARAFARM))
        id_t = _crea_ordine(db, 'TEST_ERP_PATTERN', 'ESTRATTO', codice=FARM, piva=PIVA_FARM)

        r = valuta_anomalia_erp(id_t, FARM, PIVA_FARM, False)

        assert not r['auto_risolto']
        assert db.execute("SELECT partita_iva_estratta FROM ordini_testata WHERE id_testata = %s",
                          (id_t,)).fetchone()['partita_iva_estratta'] == PIVA_FARM


class TestTipoClienteOrdine:
    def test_dal_collegamento_al_ministero(self, db_tx):  # noqa: F811
        from app.services.supervision.erp import tipo_cliente_ordine
        para = db_tx.execute("SELECT id_parafarmacia FROM anagrafica_parafarmacie LIMIT 1").fetchone()
        farm = db_tx.execute("SELECT id_farmacia FROM anagrafica_farmacie LIMIT 1").fetchone()
        if not para or not farm:
            pytest.skip("Anagrafica ministeriale vuota")
        id_t = _crea_ordine(db_tx, 'TEST_TIPO_ORD', 'ESTRATTO', codice=CODICE_ERP)

        assert tipo_cliente_ordine(id_t) is None
        db_tx.execute("UPDATE ordini_testata SET id_parafarmacia_lookup = %s WHERE id_testata = %s",
                      (para['id_parafarmacia'], id_t))
        assert tipo_cliente_ordine(id_t) is True
        db_tx.execute("UPDATE ordini_testata SET id_parafarmacia_lookup = NULL, "
                      "id_farmacia_lookup = %s WHERE id_testata = %s", (farm['id_farmacia'], id_t))
        assert tipo_cliente_ordine(id_t) is False


# -----------------------------------------------------------------------------
# Lookup Ministero: con P.IVA diversa si prova l'altro elenco
# -----------------------------------------------------------------------------

class _FakeDbPivaDiverse:
    """Codice presente in entrambi gli elenchi, con P.IVA diverse."""
    def execute(self, sql, params=None):
        cur = MagicMock()
        if 'COUNT(*) FROM ANAGRAFICA_FARMACIE' in sql:
            cur.fetchone.return_value = _Row(count=1)
        elif 'FROM ANAGRAFICA_PARAFARMACIE' in sql:
            cur.fetchone.return_value = _Row(id=2, partita_iva=PIVA_PARAFARM)
        elif 'FROM ANAGRAFICA_FARMACIE' in sql:
            cur.fetchone.return_value = _Row(id=1, partita_iva=PIVA_FARM)
        else:
            cur.fetchone.return_value = None
            cur.fetchall.return_value = []
        return cur


class TestLookupProvaEntrambiGliElenchi:
    @pytest.fixture(autouse=True)
    def _fake_db(self, monkeypatch):
        import app.services.lookup.matching as matching
        monkeypatch.setattr(matching, 'get_db', lambda: _FakeDbPivaDiverse())
        self.lookup = matching.lookup_farmacia

    def test_parafarmacia_scritta_senza_zero_trovata_dalla_piva(self):
        """Codice 99881 nel PDF (sembra farmacia) ma P.IVA della parafarmacia."""
        id_f, id_p, metodo, fonte, score = self.lookup(
            {'codice_ministeriale': CODICE_ERP, 'partita_iva': PIVA_PARAFARM})
        assert (id_f, id_p, metodo, fonte, score) == (None, 2, 'MIN_ID', 'PARAFARMACIA', 100)

    def test_farmacia_con_sua_piva_resta_farmacia(self):
        id_f, id_p, metodo, fonte, score = self.lookup(
            {'codice_ministeriale': FARM, 'partita_iva': PIVA_FARM})
        assert (id_f, id_p, fonte, score) == (1, None, 'FARMACIA', 100)

    def test_piva_di_nessuno_dei_due_resta_lkp_a04(self):
        """Subentro vero: score 50 sul tipo indicato dal codice, come prima."""
        id_f, id_p, metodo, fonte, score = self.lookup(
            {'codice_ministeriale': FARM, 'partita_iva': '09988100099'})
        assert (id_f, metodo, fonte, score) == (1, 'MIN_ID_PIVA_MISMATCH', 'FARMACIA', 50)
