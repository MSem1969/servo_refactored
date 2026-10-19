# =============================================================================
# SERV.O - TEST MOTIVAZIONE ARCHIVIAZIONE (2026-10)
# =============================================================================
# - archiviare un ordine richiede una motivazione (min. 3 caratteri), salvata
#   con autore e data in ordini_testata (migration v21)
# - archiviare l'ULTIMA riga attiva archivia l'ordine: serve la motivazione, e
#   l'ordine diventa ARCHIVIATO (prima veniva forzato a EVASO)
# - l'operatore e' l'utente autenticato, non un parametro del client (default
#   "admin")
# - al ripristino motivo/autore/data tornano NULL
#
# Girano sul DB di .env in transazione annullata (vedi test_collisione_min_id).
# =============================================================================

import asyncio
from types import SimpleNamespace

import pytest

from tests.test_collisione_min_id import db_tx, _crea_ordine  # noqa: F401 (fixture)


@pytest.fixture
def db(db_tx):  # noqa: F811
    colonne = db_tx.execute("""
        SELECT count(*) FROM information_schema.columns
        WHERE table_name = 'ordini_testata'
          AND column_name IN ('motivo_archiviazione', 'data_archiviazione', 'archiviato_da')
    """).fetchone()[0]
    if colonne < 3:
        pytest.skip("Migration v21_ordini_motivo_archiviazione.sql non applicata a questo DB")
    return db_tx


def _crea_righe(db, id_testata, n):
    return [db.execute("""
        INSERT INTO ordini_dettaglio (id_testata, n_riga, codice_aic, q_venduta, stato_riga)
        VALUES (%s, %s, '012345678', 1, 'ESTRATTO') RETURNING id_dettaglio
    """, (id_testata, i + 1)).fetchone()['id_dettaglio'] for i in range(n)]


def _testata(db, id_testata):
    return db.execute("""
        SELECT stato, motivo_archiviazione, data_archiviazione, archiviato_da,
               data_validazione, validato_da
        FROM ordini_testata WHERE id_testata = %s
    """, (id_testata,)).fetchone()


class TestArchiviaOrdine:
    @pytest.mark.parametrize("motivo", [None, '', '   ', 'ab', '  a  ', ' a\n '])
    def test_senza_motivazione_valida_non_archivia(self, db, motivo):
        from app.services.orders.commands import archivia_ordine
        id_t = _crea_ordine(db, 'TEST_ARCH_NOMOT', 'ESTRATTO')

        r = archivia_ordine(id_t, 'mario', motivo)

        assert not r.success
        assert 'motivazione' in r.error.lower()
        assert _testata(db, id_t)['stato'] == 'ESTRATTO'

    def test_salva_motivo_autore_e_data(self, db):
        from app.services.orders.commands import archivia_ordine
        id_t = _crea_ordine(db, 'TEST_ARCH_MOT', 'ESTRATTO')
        _crea_righe(db, id_t, 2)

        assert archivia_ordine(id_t, 'mario', '  ordine   duplicato ').success

        o = _testata(db, id_t)
        assert o['stato'] == 'ARCHIVIATO'
        assert o['motivo_archiviazione'] == 'ordine duplicato'
        assert o['archiviato_da'] == 'mario'
        assert o['data_archiviazione'] is not None
        # la validazione non viene sovrascritta
        assert o['validato_da'] == 'chi_ha_validato'

    def test_tre_caratteri_bastano(self, db):
        from app.services.orders.commands import archivia_ordine
        id_t = _crea_ordine(db, 'TEST_ARCH_3', 'ESTRATTO')
        assert archivia_ordine(id_t, 'mario', 'dup').success


class TestArchiviaRiga:
    def test_riga_non_ultima_non_chiede_motivazione(self, db):
        from app.services.orders.commands import archivia_riga
        id_t = _crea_ordine(db, 'TEST_RIGA_NONULT', 'ESTRATTO')
        r1, _ = _crea_righe(db, id_t, 2)

        r = archivia_riga(id_t, r1, 'mario')

        assert r.success and not r.ordine_completato
        assert _testata(db, id_t)['stato'] == 'ESTRATTO'

    def test_ultima_riga_senza_motivazione_rifiutata(self, db):
        from app.services.orders.commands import archivia_riga
        id_t = _crea_ordine(db, 'TEST_RIGA_ULT_NO', 'ESTRATTO')
        (r1,) = _crea_righe(db, id_t, 1)

        r = archivia_riga(id_t, r1, 'mario')

        assert not r.success and "ultima riga attiva" in r.error
        riga = db.execute("SELECT stato_riga FROM ordini_dettaglio WHERE id_dettaglio = %s",
                          (r1,)).fetchone()
        assert riga['stato_riga'] == 'ESTRATTO'   # nulla e' stato scritto

    def test_ultima_riga_archivia_l_ordine_non_lo_evade(self, db):
        """Prima l'ordine finiva in EVASO anche senza alcuna bolla registrata."""
        from app.services.orders.commands import archivia_riga
        id_t = _crea_ordine(db, 'TEST_RIGA_ULT_OK', 'ESTRATTO')
        r1, r2 = _crea_righe(db, id_t, 2)

        assert archivia_riga(id_t, r1, 'mario').success
        r = archivia_riga(id_t, r2, 'mario', 'cliente chiuso')

        assert r.success and r.ordine_completato
        o = _testata(db, id_t)
        assert o['stato'] == 'ARCHIVIATO'
        assert o['motivo_archiviazione'] == 'cliente chiuso'
        assert o['archiviato_da'] == 'mario'


class TestRipristino:
    def test_ripristino_riga_svuota_la_motivazione(self, db):
        from app.services.orders.commands import archivia_ordine
        from app.services.orders.fulfillment import ripristina_riga
        id_t = _crea_ordine(db, 'TEST_RIPR', 'ESTRATTO')
        r1, _ = _crea_righe(db, id_t, 2)
        assert archivia_ordine(id_t, 'mario', 'per errore').success

        ripristina_riga(id_t, r1, 'mario')

        o = _testata(db, id_t)
        assert o['stato'] != 'ARCHIVIATO'
        assert o['motivo_archiviazione'] is None
        assert o['archiviato_da'] is None
        assert o['data_archiviazione'] is None


class TestOperatoreDaUtenteAutenticato:
    def test_endpoint_usa_l_utente_autenticato(self, db):
        from app.routers.ordini import archivia_ordine, ArchiviazioneRequest
        id_t = _crea_ordine(db, 'TEST_ARCH_USER', 'ESTRATTO')

        asyncio.run(archivia_ordine(
            id_t, ArchiviazioneRequest(motivo='annullato dal cliente'),
            current_user=SimpleNamespace(username='francesca')))

        assert _testata(db, id_t)['archiviato_da'] == 'francesca'

    def test_endpoint_senza_motivazione_risponde_400(self, db):
        from fastapi import HTTPException
        from app.routers.ordini import archivia_ordine, ArchiviazioneRequest
        id_t = _crea_ordine(db, 'TEST_ARCH_400', 'ESTRATTO')

        with pytest.raises(HTTPException) as e:
            asyncio.run(archivia_ordine(
                id_t, ArchiviazioneRequest(motivo=''),
                current_user=SimpleNamespace(username='francesca')))
        assert e.value.status_code == 400
