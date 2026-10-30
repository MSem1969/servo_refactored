"""
Sync anagrafica clienti ERP da FTP: scelta file, soglia di calo, differenze, mail.
FTP e DB simulati.
"""

from datetime import date
from unittest.mock import patch

import pytest

from app.services.anagrafica import sync_clienti as sc
from app.services.scheduler import clienti_scheduler

OGGI = date(2026, 10, 30)


def _riga(codice, piva='01234567890', deposito='BA'):
    # il tracciato ERP si riconosce dal codice cliente numerico
    codice = codice if codice.isdigit() else f'{ord(codice):07d}'
    campi = [codice, 'FARM.', f'FARMACIA {codice}', 'VIA ROMA 1', '70100', 'BARI', 'BA',
             piva, 'x@y.it', '001', '\x00', '\x00', '303', '12701', deposito]
    return ';'.join(campi)


def _file(*codici):
    return '\r\n'.join(_riga(c) for c in codici).encode('cp850')


def _cliente(**kw):
    base = {c: '' for c, _ in sc.CAMPI_CONFRONTO}
    base.update(ragione_sociale_2='FARMACIA', partita_iva='01234567890', deposito_riferimento='BA')
    base.update(kw)
    return base


# --- scelta file -------------------------------------------------------------

def test_sceglie_il_file_di_oggi():
    nomi = ['ANAG_TOT_V_2026_10_29.csv', 'ANAG_TOT_V_2026_10_30.csv', 'altro.csv']
    assert sc.scegli_file(nomi, OGGI) == ('ANAG_TOT_V_2026_10_30.csv', OGGI)


def test_senza_file_di_oggi_prende_il_piu_recente_mai_futuro():
    nomi = ['ANAG_TOT_V_2026_10_27.csv', 'ANAG_TOT_V_2026_10_29.csv', 'ANAG_TOT_V_2026_11_02.csv']
    assert sc.scegli_file(nomi, OGGI) == ('ANAG_TOT_V_2026_10_29.csv', date(2026, 10, 29))


def test_nessun_file_valido():
    assert sc.scegli_file(['ANAG_TOT_V_2026_13_45.csv', 'x.txt'], OGGI) == (None, None)


# --- differenze --------------------------------------------------------------

def test_calcola_differenze():
    prima = {'A': _cliente(), 'B': _cliente(), 'C': _cliente(partita_iva='111')}
    dopo = {'A': _cliente(), 'C': _cliente(partita_iva='222'), 'D': _cliente()}
    nuovi, eliminati, modificati = sc.calcola_differenze(prima, dopo)
    assert [c['codice_cliente'] for c in nuovi] == ['D']
    assert [c['codice_cliente'] for c in eliminati] == ['B']
    assert modificati == [{
        'codice_cliente': 'C', 'ragione_sociale': 'FARMACIA',
        'cambi': [{'campo': 'P.IVA', 'prima': '111', 'dopo': '222'}],
    }]


# --- flusso ------------------------------------------------------------------

@pytest.fixture
def ambiente():
    """FTP, DB e import simulati; ritorna i mock per le asserzioni."""
    stato = {'snapshot': [], 'ultimo': None}

    with patch.object(sc, '_scarica_da_ftp') as ftp, \
         patch.object(sc, '_snapshot_clienti', side_effect=lambda: stato['snapshot'].pop(0)), \
         patch.object(sc, '_ultimo_file_importato', side_effect=lambda: stato['ultimo']), \
         patch.object(sc, '_salva_stato') as salva, \
         patch.object(sc, '_archivia'), \
         patch.object(sc, 'import_anagrafica_clienti', return_value={'importate': 3}) as imp:
        yield {'ftp': ftp, 'stato': stato, 'salva': salva, 'import': imp}


def test_import_con_differenze(ambiente):
    ambiente['ftp'].return_value = ('ANAG_TOT_V_2026_10_30.csv', OGGI, _file('A', 'C', 'D'), [])
    ambiente['stato']['snapshot'] = [
        {'A': _cliente(), 'B': _cliente(), 'C': _cliente()},
        {'A': _cliente(), 'C': _cliente(deposito_riferimento='CT'), 'D': _cliente()},
    ]
    res = sc.sync_clienti_erp(oggi=OGGI)
    assert res.esito == 'IMPORTATO' and res.file_del_giorno
    assert (len(res.nuovi), len(res.eliminati), len(res.modificati)) == (1, 1, 1)
    ambiente['salva'].assert_called_once_with('ANAG_TOT_V_2026_10_30.csv', 3)

    subject, body = clienti_scheduler._format_email(res)
    assert 'Aggiornamenti' in subject
    assert 'Clienti eliminati (1)' in body and 'Deposito' in body
    allegato = clienti_scheduler._allegato_differenze(res)
    testo = allegato['content'].decode('utf-8-sig')
    assert 'ELIMINATO;B' in testo and 'MODIFICATO;C' in testo


def test_file_gia_importato_non_si_reimporta(ambiente):
    ambiente['ftp'].return_value = ('ANAG_TOT_V_2026_10_29.csv', date(2026, 10, 29), _file('A'), [])
    ambiente['stato']['ultimo'] = 'ANAG_TOT_V_2026_10_29.csv'
    ambiente['stato']['snapshot'] = [{'A': _cliente()}]
    res = sc.sync_clienti_erp(oggi=OGGI)
    assert res.esito == 'NESSUN_FILE_NUOVO' and res.success
    assert 'File di oggi non presente' in res.messaggio
    ambiente['import'].assert_not_called()


def test_calo_oltre_soglia_blocca(ambiente):
    ambiente['ftp'].return_value = ('ANAG_TOT_V_2026_10_30.csv', OGGI, _file(*'ABCDEFGH'), [])
    ambiente['stato']['snapshot'] = [{c: _cliente() for c in 'ABCDEFGHIJ'}]  # -20%
    res = sc.sync_clienti_erp(oggi=OGGI)
    assert res.esito == 'BLOCCATO' and not res.success
    ambiente['import'].assert_not_called()
    assert 'BLOCCATA' in clienti_scheduler._format_email(res)[0]


def test_forza_ignora_soglia(ambiente):
    ambiente['ftp'].return_value = ('ANAG_TOT_V_2026_10_30.csv', OGGI, _file(*'ABCDEFGH'), [])
    ambiente['stato']['snapshot'] = [
        {c: _cliente() for c in 'ABCDEFGHIJ'},
        {c: _cliente() for c in 'ABCDEFGH'},
    ]
    res = sc.sync_clienti_erp(forza=True, oggi=OGGI)
    assert res.esito == 'IMPORTATO' and len(res.eliminati) == 2
    ambiente['import'].assert_called_once()


def test_nessun_file_in_cartella(ambiente):
    ambiente['ftp'].return_value = (None, None, None, ['altro.csv'])
    res = sc.sync_clienti_erp(oggi=OGGI)
    assert res.esito == 'ERRORE' and 'NON modificata' in res.messaggio
    ambiente['import'].assert_not_called()


def test_errore_ftp_non_tocca_anagrafica(ambiente):
    ambiente['ftp'].side_effect = OSError('connessione rifiutata')
    res = sc.sync_clienti_erp(oggi=OGGI)
    assert res.esito == 'ERRORE' and 'connessione rifiutata' in res.messaggio
    ambiente['import'].assert_not_called()
