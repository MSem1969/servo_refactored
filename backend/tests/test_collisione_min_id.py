# =============================================================================
# SERV.O - TEST COLLISIONE MIN_ID FARMACIA / PARAFARMACIA (2026-10)
# =============================================================================
# Tolti gli zeri, farmacia 14706 e parafarmacia 014706 coincidono. Le query
# LTRIM(min_id,'0') ... LIMIT 1 prendevano a caso uno dei due clienti:
# falsi ERP-A01 (caso reale: ordine DOC_GENERICI 0746002040), deposito
# sbagliato, rettifica P.IVA estesa al cliente omonimo.
#
# Contiene anche i test dei fix collegati emersi dallo stesso caso:
#  - il sender FTP ricontrolla l'ordine prima di trasmettere (stato BLOCCATO)
#  - la ricerca tracciati elenca gli ordini con esportazione anche se ARCHIVIATI
#  - l'archiviazione non sovrascrive data_validazione / validato_da
#
# I test "DB" girano sul database configurato in .env dentro una transazione
# annullata a fine test (commit neutralizzato): non lasciano dati.
# =============================================================================

import asyncio
import hashlib
from unittest.mock import MagicMock

import pytest

from app.utils.codes import (
    codice_cliente_canonico,
    filtro_min_id_cliente,
    is_codice_parafarmacia,
)
from app.services.supervision.erp import calcola_pattern_signature_erp
from app.services.anomalies.propagazione import calcola_chiave_anomalia as _chiave_raggr


# Codici di prova: non esistono in anagrafica (verificato) e coincidono senza zeri
FARM = '000099871'      # farmacia, come arriva dal PDF / anagrafica ministero
PARAFARM = '099871'     # parafarmacia omonima
PIVA_FARM = '09987100001'
PIVA_PARAFARM = '09987100002'


# =============================================================================
# 1. Funzioni di codice (pure)
# =============================================================================

class TestCodiciFarmaciaParafarmacia:
    @pytest.mark.parametrize("codice,atteso", [
        ('000014706', '14706'),   # farmacia 9 cifre (ministero)
        ('14706', '14706'),       # farmacia come in anagrafica_clienti
        ('014706', '014706'),     # parafarmacia: lo zero resta
        ('015418', '015418'),
        ('', ''),
    ])
    def test_codice_canonico(self, codice, atteso):
        assert codice_cliente_canonico(codice) == atteso

    def test_tipo_esplicito_vince_sulla_lunghezza(self):
        assert codice_cliente_canonico('15418', is_parafarmacia=True) == '015418'
        assert codice_cliente_canonico('015418', is_parafarmacia=False) == '15418'

    def test_is_codice_parafarmacia(self):
        assert is_codice_parafarmacia('014706')
        assert not is_codice_parafarmacia('000014706')
        assert not is_codice_parafarmacia('14706')
        assert not is_codice_parafarmacia('')

    def test_filtro_distingue_i_tipi(self):
        sql_f, par_f = filtro_min_id_cliente('000014706')
        sql_p, par_p = filtro_min_id_cliente('014706')
        assert par_f == par_p == ['14706']          # stessa chiave...
        assert '<= 5' in sql_f and '= 6' in sql_p   # ...ma tipi diversi
        assert sql_f != sql_p


class TestFirmeNonCollidono:
    def test_firma_erp_farmacia_invariata(self):
        """La firma farmacia resta quella storica: i pattern appresi non si perdono."""
        storica = hashlib.md5(b"ERP|14706").hexdigest()[:16]
        assert calcola_pattern_signature_erp('000014706') == storica
        assert calcola_pattern_signature_erp('14706') == storica

    def test_firma_erp_parafarmacia_distinta(self):
        assert calcola_pattern_signature_erp('014706') != calcola_pattern_signature_erp('000014706')

    def test_chiave_propagazione_erp_distinta(self):
        farm = {'codice_anomalia': 'ERP-A01', 'tipo_anomalia': 'ERP', 'codice_ministeriale': '000014706'}
        para = {'codice_anomalia': 'ERP-A01', 'tipo_anomalia': 'ERP', 'codice_ministeriale': '014706'}
        assert _chiave_raggr(farm) != _chiave_raggr(para)


# =============================================================================
# 2. Lookup su anagrafica ministero: prima l'elenco del tipo del codice
# =============================================================================

class _Row(dict):
    """Riga che supporta sia row['col'] sia row[0], come HybridRow."""
    def __getitem__(self, k):
        if isinstance(k, int):
            return list(self.values())[k]
        return super().__getitem__(k)


class _FakeLookupDb:
    """Ogni codice esiste sia come farmacia (id 1) sia come parafarmacia (id 2)."""
    def execute(self, sql, params=None):
        cur = MagicMock()
        if 'COUNT(*) FROM ANAGRAFICA_FARMACIE' in sql:
            cur.fetchone.return_value = _Row(count=1)
        elif 'FROM ANAGRAFICA_PARAFARMACIE' in sql:
            cur.fetchone.return_value = _Row(id=2, partita_iva='')
        elif 'FROM ANAGRAFICA_FARMACIE' in sql:
            cur.fetchone.return_value = _Row(id=1, partita_iva='')
        else:
            cur.fetchone.return_value = None
            cur.fetchall.return_value = []
        return cur


class TestLookupMinistero:
    @pytest.fixture(autouse=True)
    def _fake_db(self, monkeypatch):
        import app.services.lookup.matching as matching
        monkeypatch.setattr(matching, 'get_db', lambda: _FakeLookupDb())
        self.lookup = matching.lookup_farmacia

    def test_codice_farmacia_trova_farmacia(self):
        id_f, id_p, metodo, fonte, score = self.lookup({'codice_ministeriale': '000014706'})
        assert (id_f, id_p, fonte, score) == (1, None, 'FARMACIA', 100)

    def test_codice_parafarmacia_trova_parafarmacia(self):
        """Prima del fix un codice 014706 veniva agganciato alla farmacia 000014706."""
        id_f, id_p, metodo, fonte, score = self.lookup({'codice_ministeriale': '014706'})
        assert (id_f, id_p, fonte, score) == (None, 2, 'PARAFARMACIA', 100)


# =============================================================================
# 3. Test su DB (transazione annullata)
# =============================================================================

@pytest.fixture
def db_tx(monkeypatch):
    from app.database_pg import get_db
    try:
        db = get_db()
        db.execute("SELECT 1").fetchone()
    except Exception as e:  # pragma: no cover - dipende dall'ambiente
        pytest.skip(f"Database non disponibile: {e}")
    db.rollback()
    # Nessun commit durante il test: tutto viene annullato alla fine
    monkeypatch.setattr(db, 'commit', lambda: None)
    yield db
    db.rollback()


def _inserisci_cliente(db, min_id, piva, deposito, codice):
    db.execute("""
        INSERT INTO anagrafica_clienti (codice_cliente, ragione_sociale_1, partita_iva,
                                        min_id, deposito_riferimento)
        VALUES (%s, %s, %s, %s, %s)
    """, (codice, f'TEST {codice}', piva, min_id, deposito))


@pytest.fixture
def clienti_omonimi(db_tx):
    """Farmacia 99871 e parafarmacia 099871: stesso codice senza zeri, clienti diversi."""
    _inserisci_cliente(db_tx, '99871', PIVA_FARM, 'CT', 'TEST_F1')
    _inserisci_cliente(db_tx, PARAFARM, PIVA_PARAFARM, 'PE', 'TEST_P1')
    return db_tx


class TestValidazioneErp:
    def _valida(self, min_id, piva):
        from app.services.supervision.erp import valida_coerenza_erp
        return valida_coerenza_erp(min_id, piva)

    def test_farmacia_con_sua_piva_valida(self, clienti_omonimi):
        """Caso 0746002040: prima veniva bloccato a caso con la P.IVA della parafarmacia."""
        r = self._valida(FARM, PIVA_FARM)
        assert r['valido'], r['messaggio']

    def test_parafarmacia_con_sua_piva_valida(self, clienti_omonimi):
        """Caso SO00001521001459: parafarmacia confrontata con la farmacia omonima."""
        r = self._valida(PARAFARM, PIVA_PARAFARM)
        assert r['valido'], r['messaggio']

    def test_farmacia_con_piva_della_parafarmacia_bloccata(self, clienti_omonimi):
        r = self._valida(FARM, PIVA_PARAFARM)
        assert not r['valido']
        assert r['codice_anomalia'] == 'ERP-A01'
        assert r['piva_erp'] == PIVA_FARM

    def test_parafarmacia_con_piva_della_farmacia_bloccata(self, clienti_omonimi):
        r = self._valida(PARAFARM, PIVA_FARM)
        assert r['codice_anomalia'] == 'ERP-A01'
        assert r['piva_erp'] == PIVA_PARAFARM

    def test_tipo_assente_non_ripiega_sull_omonimo(self, db_tx):
        """Se in anagrafica c'e' solo la farmacia, la parafarmacia omonima non e' trovata."""
        _inserisci_cliente(db_tx, '99872', PIVA_FARM, 'CT', 'TEST_F2')
        r = self._valida('099872', PIVA_FARM)
        assert r['codice_anomalia'] == 'ERP-A02'

    def test_duplicati_stesso_tipo_basta_una_piva(self, db_tx):
        """Subentri: piu' righe per lo stesso codice; vale se una ha la P.IVA dell'ordine."""
        _inserisci_cliente(db_tx, '99873', '09987300001', 'CT', 'TEST_F3')
        _inserisci_cliente(db_tx, '99873', '09987300002', 'CT', 'TEST_F4')
        assert self._valida('000099873', '09987300002')['valido']
        assert self._valida('000099873', '09987300001')['valido']


class TestRettificaAnagrafica:
    def test_rettifica_non_tocca_il_cliente_omonimo(self, clienti_omonimi):
        from app.services.supervision.erp import _rettifica_anagrafica_clienti
        db = clienti_omonimi

        assert _rettifica_anagrafica_clienti(FARM, '09987100009', 'test', 5)

        righe = {r['codice_cliente']: r['partita_iva'] for r in db.execute(
            "SELECT codice_cliente, partita_iva FROM anagrafica_clienti "
            "WHERE codice_cliente IN ('TEST_F1', 'TEST_P1')").fetchall()}
        assert righe == {'TEST_F1': '09987100009', 'TEST_P1': PIVA_PARAFARM}


# -----------------------------------------------------------------------------
# Ordini ed esportazioni di prova
# -----------------------------------------------------------------------------

def _crea_ordine(db, numero, stato, codice=FARM, piva=PIVA_FARM):
    acq = db.execute("SELECT id_acquisizione FROM acquisizioni ORDER BY id_acquisizione LIMIT 1").fetchone()
    vendor = db.execute("SELECT id_vendor FROM vendor ORDER BY id_vendor LIMIT 1").fetchone()
    if not acq or not vendor:
        pytest.skip("Servono almeno un'acquisizione e un vendor nel DB di test")
    return db.execute("""
        INSERT INTO ordini_testata (id_acquisizione, id_vendor, numero_ordine_vendor, stato,
                                    codice_ministeriale_estratto, partita_iva_estratta,
                                    data_validazione, validato_da)
        VALUES (%s, %s, %s, %s, %s, %s, '2026-10-15 12:42:00', 'chi_ha_validato')
        RETURNING id_testata
    """, (acq['id_acquisizione'], vendor['id_vendor'], numero, stato, codice, piva)).fetchone()['id_testata']


def _crea_esportazione(db, id_testata, stato_ftp='PENDING'):
    id_exp = db.execute("""
        INSERT INTO esportazioni (nome_tracciato_generato, nome_file_to_t, nome_file_to_d,
                                  num_testate, num_dettagli, stato, stato_ftp)
        VALUES ('TEST', 'TO_T_TEST.txt', 'TO_D_TEST.txt', 1, 1, 'GENERATO', %s)
        RETURNING id_esportazione
    """, (stato_ftp,)).fetchone()['id_esportazione']
    db.execute("INSERT INTO esportazioni_dettaglio (id_esportazione, id_testata) VALUES (%s, %s)",
               (id_exp, id_testata))
    return id_exp


def _v20_applicata(db) -> bool:
    row = db.execute("""
        SELECT pg_get_constraintdef(oid) AS def FROM pg_constraint
        WHERE conname = 'esportazioni_stato_ftp_check'
    """).fetchone()
    return row is None or 'BLOCCATO' in row['def']


class TestSenderRicontrollaOrdine:
    @pytest.fixture
    def sender(self, db_tx):
        if not _v20_applicata(db_tx):
            pytest.skip("Migration v20_stato_ftp_bloccato.sql non applicata a questo DB")
        from app.services.ftp.sender import FTPSender
        s = FTPSender()
        s._vendor_mapping = {}
        return s

    @pytest.mark.parametrize("stato", ['ARCHIVIATO', 'ANOMALIA'])
    def test_ordine_bloccato_non_viene_trasmesso(self, db_tx, sender, stato):
        id_t = _crea_ordine(db_tx, f'TEST_FTP_{stato}', stato)
        id_exp = _crea_esportazione(db_tx, id_t)
        ftp = MagicMock()

        r = sender.send_export(id_exp, ftp)

        assert r.get('blocked') and not r['success']
        ftp.upload_file.assert_not_called()
        exp = db_tx.execute("SELECT stato_ftp, ultimo_errore_ftp FROM esportazioni "
                            "WHERE id_esportazione = %s", (id_exp,)).fetchone()
        assert exp['stato_ftp'] == 'BLOCCATO'
        assert f'TEST_FTP_{stato}' in exp['ultimo_errore_ftp']

    def test_anomalia_bloccante_aperta_blocca(self, db_tx, sender):
        id_t = _crea_ordine(db_tx, 'TEST_FTP_ERP', 'VALIDATO')
        db_tx.execute("""
            INSERT INTO anomalie (id_testata, tipo_anomalia, livello, codice_anomalia, descrizione, stato)
            VALUES (%s, 'ERP', 'ERRORE', 'ERP-A01', 'test', 'APERTA')
        """, (id_t,))
        id_exp = _crea_esportazione(db_tx, id_t)
        assert sender.send_export(id_exp, MagicMock()).get('blocked')

    def test_ordine_pulito_prosegue(self, db_tx, sender):
        """Senza blocchi il sender va avanti (qui: vendor non mappato -> SKIPPED)."""
        id_t = _crea_ordine(db_tx, 'TEST_FTP_OK', 'VALIDATO')
        id_exp = _crea_esportazione(db_tx, id_t)
        r = sender.send_export(id_exp, MagicMock())
        assert r.get('skipped') and not r.get('blocked')


class TestRicercaTracciati:
    def _ricerca(self, numero):
        from app.routers.tracciati import ricerca_tracciati
        return asyncio.run(ricerca_tracciati(
            numero_ordine=numero, ragione_sociale=None, vendor=None,
            data_da=None, data_a=None, stato=None, limit=50))

    def test_ordine_archiviato_con_tracciato_inviato_resta_in_elenco(self, db_tx):
        """Caso 0746002040: inviato il 15/10, archiviato il 19/10, sparito dalla ricerca."""
        id_t = _crea_ordine(db_tx, 'TEST_RIC_ARCH', 'ARCHIVIATO')
        _crea_esportazione(db_tx, id_t, stato_ftp='SENT')
        res = self._ricerca('TEST_RIC_ARCH')
        assert [r['id_testata'] for r in res['data']] == [id_t]
        assert res['data'][0]['esportazione']['stato_ftp'] == 'SENT'

    def test_ordine_archiviato_senza_tracciato_resta_escluso(self, db_tx):
        _crea_ordine(db_tx, 'TEST_RIC_NOEXP', 'ARCHIVIATO')
        assert self._ricerca('TEST_RIC_NOEXP')['data'] == []


class TestArchiviazioneConservaValidazione:
    def test_archivia_non_sovrascrive_data_validazione(self, db_tx):
        from app.services.orders.commands import archivia_ordine
        id_t = _crea_ordine(db_tx, 'TEST_ARCH_VAL', 'ESPORTATO')

        assert archivia_ordine(id_t, 'chi_archivia', 'cliente chiuso').success

        o = db_tx.execute("SELECT stato, data_validazione, validato_da FROM ordini_testata "
                          "WHERE id_testata = %s", (id_t,)).fetchone()
        assert o['stato'] == 'ARCHIVIATO'
        assert o['validato_da'] == 'chi_ha_validato'
        assert str(o['data_validazione']).startswith('2026-10-15 12:42')
