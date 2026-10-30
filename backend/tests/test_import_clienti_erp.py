"""
Import anagrafica clienti dall'estrazione ERP (ANAG_TOT_V_*.csv).

Formato: nessuna intestazione, separatore ';', cp850, campi vuoti = byte NUL,
email che puo' contenere ';'. Test sul solo parser, senza DB.
"""

from unittest.mock import MagicMock, patch

from app.services.anagrafica import legacy
from app.services.anagrafica.legacy import (
    COLONNE_CLIENTI_ERP,
    _leggi_tracciato_clienti_erp,
)


def _riga(*campi):
    return ';'.join(campi).encode('cp850')


RIGA_BASE = _riga(
    '0030605', 'FARM.', 'DE PACE LICIGNANO SNC', 'VIA 95° REGGIMENTO FANTERIA,53',
    '73100', 'LECCE', 'LE', '02658310756', 'farmaciadpl@gmail.com', '001',
    '\x00', '\x00', '303', '13231', 'BA',
)


def test_tracciato_posizionale_cp850_e_nul():
    df, enc, scartate = _leggi_tracciato_clienti_erp(RIGA_BASE + b'\r\n')
    assert enc == 'cp850'
    assert scartate == []
    r = df.iloc[0]
    assert list(df.columns) == COLONNE_CLIENTI_ERP
    assert r['AGCANA'] == '0030605'
    assert r['AGINDI'] == 'VIA 95° REGGIMENTO FANTERIA,53'  # virgola nel campo: non e' un separatore
    assert r['AGCFAR'] == '' and r['AGCSTA'] == ''          # NUL → vuoto
    assert r['AGTIDD'] == '13231' and r['AGDRIF'] == 'BA'


def test_email_con_punto_e_virgola_non_sposta_i_campi():
    riga = _riga(
        '2914937', 'FARM.', 'INCO.FARMA SPA', 'VIA TADDEO', '80100', 'NAPOLI', 'NA',
        '05029881215', 'a@libero.it', 'b@libero.it', '004', '\x00', '\x00', 'G09', '17977', 'NO',
    )
    vuota = _riga(
        '0034841', '\x00', 'CONAD', 'VIA BURE', '51100', 'PISTOIA', 'PT',
        '01977130473', 'x@conad.it', '', '017', '\x00', '\x00', '105', '008979', 'RO',
    )
    df, _, scartate = _leggi_tracciato_clienti_erp(riga + b'\r\n' + vuota)
    assert scartate == []
    assert df.iloc[0]['AGMAIL'] == 'a@libero.it;b@libero.it'
    assert df.iloc[0]['AGCATE'] == '004' and df.iloc[0]['AGDRIF'] == 'NO'
    assert df.iloc[1]['AGMAIL'] == 'x@conad.it'
    assert df.iloc[1]['AGCATE'] == '017'
    assert df.iloc[1]['AGTIDD'] == '008979'  # zeri iniziali conservati (parafarmacia)


def test_virgolette_non_bilanciate_sono_testo():
    riga = _riga(
        '2916786', 'FARM.', 'PINNIZZOTTO DELLA "F.CIA DELLA', 'V.LE SAN MARTINO 183',
        '98123', 'MESSINA', 'ME', '02929120836', 'r@virgilio.it', '001',
        '', '', '303', '15143', 'CT',
    )
    df, _, _ = _leggi_tracciato_clienti_erp(riga + b'\r\n' + RIGA_BASE)
    assert len(df) == 2
    assert df.iloc[0]['AGRSO2'] == 'PINNIZZOTTO DELLA "F.CIA DELLA'


def test_riga_troncata_scartata_e_segnalata():
    df, _, scartate = _leggi_tracciato_clienti_erp(RIGA_BASE + b'\r\n0030606;FARM.;TRONCA\r\n')
    assert len(df) == 1
    assert scartate == [2]


def test_utf8_letto_come_utf8():
    df, enc, _ = _leggi_tracciato_clienti_erp(RIGA_BASE.decode('cp850').encode('utf-8'))
    assert enc == 'utf-8'
    assert df.iloc[0]['AGINDI'] == 'VIA 95° REGGIMENTO FANTERIA,53'


def test_csv_con_intestazione_non_e_tracciato_erp():
    csv = b'AGCANA,AGRSO1,AGRSO2,AGINDI,AGCAP,AGLOCA,AGPROV,AGPIVA,AGMAIL,AGCATE,AGCFAR,AGCSTA,AGCPAG,AGTIDD,AGDRIF\r\n'
    assert _leggi_tracciato_clienti_erp(csv) is None


def test_file_senza_codici_non_svuota_anagrafica():
    """Colonne non riconosciute → errore PRIMA del DELETE, anagrafica intatta."""
    db = MagicMock()
    with patch.object(legacy, 'get_db', return_value=db):
        res = legacy.import_anagrafica_clienti(csv_content=b'foo;bar;baz\r\n1;2;3\r\n')
    assert 'NON modificata' in res['error']
    sql = ' '.join(str(c.args[0]) for c in db.execute.call_args_list)
    assert 'DELETE' not in sql
