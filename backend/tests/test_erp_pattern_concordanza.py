# =============================================================================
# SERV.O - TEST PATTERN ERP: CONCORDANZA E CODICI AMBIGUI (2026-11)
# =============================================================================
# Caso reale: farmacia 14330 (anomalia 9329, ordini 3386/7097/7102/7103).
# L'ERP ha DUE clienti farmacia con lo stesso codice: il vecchio titolare
# (COVELLI, 01532460803) e il subentrante (SAN GIROLAMO SNC, 02904990807).
# Il Ministero ha una P.IVA errata di una cifra, quindi ogni ordine apre ERP-A01.
# Gli operatori hanno approvato ora l'una ora l'altra: il pattern contava 4/5
# e alla quinta sarebbe diventato automatico con l'ultima approvata.
#
# 1. contano solo le approvazioni concordanti: una P.IVA diversa riporta a 1
# 2. con piu' clienti ERP per lo stesso codice il pattern non diventa
#    automatico, e uno gia' automatico non viene applicato
#
# I test DB girano in transazione annullata (vedi test_collisione_min_id).
# =============================================================================

import pytest

from tests.test_collisione_min_id import db_tx, _crea_ordine  # noqa: F401 (fixture)


FARM = '000099891'
CODICE_ERP = '99891'
PIVA_NUOVO = '09989100001'      # subentrante (quella giusta)
PIVA_VECCHIO = '09989100002'    # vecchio titolare, mai chiuso nell'ERP
PIVA_MINISTERO = '09989100099'  # errata: e' quella che arriva sul tracciato


def _cliente(db, piva, codice, rs2):
    db.execute("""
        INSERT INTO anagrafica_clienti (codice_cliente, ragione_sociale_1, ragione_sociale_2,
                                        partita_iva, min_id, farmacia_categoria,
                                        deposito_riferimento)
        VALUES (%s, 'FARM.', %s, %s, %s, '001', 'CS')
    """, (codice, rs2, piva, CODICE_ERP))


def _sig():
    from app.services.supervision.erp import calcola_pattern_signature_erp
    return calcola_pattern_signature_erp(FARM, False)


def _pattern(db):
    return db.execute("SELECT * FROM criteri_ordinari_erp WHERE pattern_signature = %s",
                      (_sig(),)).fetchone()


@pytest.fixture
def un_cliente(db_tx):  # noqa: F811
    db_tx.execute("DELETE FROM criteri_ordinari_erp WHERE pattern_signature = %s", (_sig(),))
    _cliente(db_tx, PIVA_NUOVO, 'TEST_N', 'SAN GIROLAMO SNC')
    return db_tx


@pytest.fixture
def due_clienti(un_cliente):
    _cliente(un_cliente, PIVA_VECCHIO, 'TEST_V', 'COVELLI')
    return un_cliente


_n = iter(range(10_000))


def _approva(db, piva, operatore='maria'):
    from app.services.supervision.erp import approva_supervisione_erp, crea_supervisione_erp
    id_t = _crea_ordine(db, f'TEST_CONC_{next(_n)}', 'ANOMALIA', codice=FARM, piva=PIVA_MINISTERO)
    id_sup = crea_supervisione_erp(id_t, None, FARM, PIVA_MINISTERO, is_parafarmacia=False)
    r = approva_supervisione_erp(id_sup, operatore, piva)
    assert r['success'], r
    return r


class TestConcordanza:
    def test_approvazioni_concordanti_promuovono(self, un_cliente):
        for _ in range(5):
            r = _approva(un_cliente, PIVA_NUOVO)
        assert r['count_approvazioni'] == 5
        assert not r['pattern_azzerato'] and not r['promozione_bloccata']
        p = _pattern(un_cliente)
        assert p['is_ordinario'] and p['partita_iva_corretta'] == PIVA_NUOVO

    def test_approvazione_discordante_riparte_da_uno(self, due_clienti):
        """Caso 14330: 0290 (maria), poi 0153 (maria) contava 2/5."""
        _approva(due_clienti, PIVA_NUOVO)
        _approva(due_clienti, PIVA_NUOVO)
        r = _approva(due_clienti, PIVA_VECCHIO, 'francesca')

        assert r['count_approvazioni'] == 1
        assert r['pattern_azzerato'] and r['piva_precedente'] == PIVA_NUOVO
        p = _pattern(due_clienti)
        assert p['partita_iva_corretta'] == PIVA_VECCHIO
        assert p['operatori_approvatori'] == 'francesca'

    def test_sequenza_alternata_14330_non_arriva_mai_alla_soglia(self, due_clienti):
        for piva in (PIVA_NUOVO, PIVA_VECCHIO, PIVA_VECCHIO, PIVA_NUOVO, PIVA_NUOVO):
            r = _approva(due_clienti, piva)
        assert r['count_approvazioni'] == 2
        assert not _pattern(due_clienti)['is_ordinario']


class TestCodiceAmbiguo:
    def test_validazione_elenca_tutti_i_clienti(self, due_clienti):
        from app.services.supervision.erp import valida_coerenza_erp
        r = valida_coerenza_erp(FARM, PIVA_MINISTERO, False)
        assert r['codice_anomalia'] == 'ERP-A01'
        assert r['ambiguo'] and len(r['clienti_erp']) == 2
        assert PIVA_NUOVO in r['messaggio'] and PIVA_VECCHIO in r['messaggio']
        assert 'COVELLI' in r['messaggio'] and 'SAN GIROLAMO' in r['messaggio']

    def test_un_solo_cliente_non_e_ambiguo(self, un_cliente):
        from app.services.supervision.erp import valida_coerenza_erp, motivo_codice_ambiguo
        assert not valida_coerenza_erp(FARM, PIVA_MINISTERO, False)['ambiguo']
        assert motivo_codice_ambiguo(FARM, False) is None

    def test_soglia_raggiunta_ma_promozione_bloccata(self, due_clienti):
        for _ in range(5):
            r = _approva(due_clienti, PIVA_NUOVO)
        assert r['count_approvazioni'] == 5
        assert r['promozione_bloccata'] and PIVA_VECCHIO in r['promozione_bloccata']
        assert not r['rettifica_eseguita']
        assert not _pattern(due_clienti)['is_ordinario']

    def test_pattern_gia_automatico_torna_manuale(self, due_clienti):
        """Promosso quando l'ERP aveva un solo cliente, poi e' comparso il secondo."""
        due_clienti.execute("""
            INSERT INTO criteri_ordinari_erp (pattern_signature, pattern_descrizione, min_id,
                                              partita_iva_corretta, count_approvazioni,
                                              is_ordinario, data_promozione)
            VALUES (%s, 'test', %s, %s, 5, TRUE, CURRENT_TIMESTAMP)
        """, (_sig(), CODICE_ERP, PIVA_NUOVO))
        r = _approva(due_clienti, PIVA_NUOVO)
        assert r['count_approvazioni'] == 6 and r['promozione_bloccata']
        assert not _pattern(due_clienti)['is_ordinario']

    def test_pattern_automatico_non_applicato(self, due_clienti):
        from app.services.supervision.erp import valuta_anomalia_erp
        due_clienti.execute("""
            INSERT INTO criteri_ordinari_erp (pattern_signature, pattern_descrizione, min_id,
                                              partita_iva_corretta, count_approvazioni, is_ordinario)
            VALUES (%s, 'test', %s, %s, 5, TRUE)
        """, (_sig(), CODICE_ERP, PIVA_VECCHIO))
        id_t = _crea_ordine(due_clienti, 'TEST_CONC_AUTO', 'ESTRATTO', codice=FARM,
                            piva=PIVA_MINISTERO)

        assert not valuta_anomalia_erp(id_t, FARM, PIVA_MINISTERO, False)['auto_risolto']
        assert due_clienti.execute(
            "SELECT partita_iva_estratta FROM ordini_testata WHERE id_testata = %s", (id_t,)
        ).fetchone()['partita_iva_estratta'] == PIVA_MINISTERO


class TestMessaggio:
    def test_nessuna_nota_se_il_pattern_avanza(self):
        from app.services.supervision.erp import descrivi_esito_pattern_erp
        assert descrivi_esito_pattern_erp({'count_approvazioni': 3}) is None

    def test_nota_per_azzeramento_e_blocco(self):
        from app.services.supervision.erp import descrivi_esito_pattern_erp
        assert '0123' in descrivi_esito_pattern_erp(
            {'pattern_azzerato': True, 'piva_precedente': '0123'})
        assert 'NON resa automatica' in descrivi_esito_pattern_erp(
            {'promozione_bloccata': 'due clienti'})
