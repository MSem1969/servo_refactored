# =============================================================================
# SERV.O - SYNC ANAGRAFICA CLIENTI DA ERP (FTP)
# =============================================================================
# Preleva (RETR) l'estrazione ERP ANAG_TOT_V_AAAA_MM_GG.csv dalla cartella
# FTP condivisa, la importa con import_anagrafica_clienti (replace completo)
# e ritorna le differenze rispetto all'anagrafica precedente.
#
# - file del giorno; se assente, il piu' recente presente in cartella;
# - un file gia' importato non viene reimportato (salvo forza=True);
# - blocco se il file ha oltre SOGLIA_CALO clienti in meno del DB: un'estrazione
#   interrotta svuoterebbe l'anagrafica (salvo forza=True).
# =============================================================================

import io
import os
import re
import ftplib
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from ...database_pg import get_db
from .legacy import import_anagrafica_clienti, _leggi_tracciato_clienti_erp

FTP_DIR = os.getenv('CLIENTI_SYNC_FTP_DIR', 'transfer')
ARCHIVE_DIR = os.getenv('CLIENTI_SYNC_ARCHIVE_DIR', 'data/anagrafica_clienti')
SOGLIA_CALO = float(os.getenv('CLIENTI_SYNC_SOGLIA_CALO', '0.10'))
SYNC_STATE_KEY = 'clienti_erp'

FILE_RE = re.compile(r'^ANAG_TOT_V_(\d{4})_(\d{2})_(\d{2})\.csv$', re.IGNORECASE)

# Campi confrontati per il report differenze (colonne di anagrafica_clienti)
CAMPI_CONFRONTO = [
    ('ragione_sociale_1', 'Rag. sociale 1'),
    ('ragione_sociale_2', 'Rag. sociale 2'),
    ('indirizzo', 'Indirizzo'),
    ('cap', 'CAP'),
    ('localita', 'Località'),
    ('provincia', 'Provincia'),
    ('partita_iva', 'P.IVA'),
    ('email', 'Email'),
    ('farmacia_categoria', 'Categoria'),
    ('codice_farmacia', 'Cod. farmacia'),
    ('farma_status', 'Status'),
    ('codice_pagamento', 'Pagamento'),
    ('min_id', 'MIN_ID'),
    ('deposito_riferimento', 'Deposito'),
]


@dataclass
class SyncClientiResult:
    esito: str = 'ERRORE'           # IMPORTATO | NESSUN_FILE_NUOVO | BLOCCATO | ERRORE
    messaggio: str = ''
    file: Optional[str] = None
    data_file: Optional[date] = None
    file_del_giorno: bool = False
    righe_file: int = 0
    totale_prima: int = 0
    totale_dopo: int = 0
    nuovi: List[Dict[str, Any]] = field(default_factory=list)
    eliminati: List[Dict[str, Any]] = field(default_factory=list)
    modificati: List[Dict[str, Any]] = field(default_factory=list)
    import_result: Dict[str, Any] = field(default_factory=dict)
    durata_secondi: float = 0.0

    @property
    def success(self) -> bool:
        return self.esito in ('IMPORTATO', 'NESSUN_FILE_NUOVO')


# =============================================================================
# FTP
# =============================================================================

def _credenziali_ftp() -> Dict[str, Any]:
    """
    Host/utente da ftp_config; password dall'endpoint dello stesso utente
    (sezione FTP delle Impostazioni, cifrata), in subordine env FTP_PASSWORD.
    """
    db = get_db()
    config = db.execute("""
        SELECT ftp_host, ftp_port, ftp_username, ftp_passive_mode, ftp_timeout
        FROM ftp_config WHERE ftp_enabled = TRUE LIMIT 1
    """).fetchone()
    if not config:
        raise ValueError('Nessuna configurazione FTP attiva (ftp_config)')

    password = None
    endpoint = db.execute("""
        SELECT ftp_password_encrypted FROM ftp_endpoints
        WHERE ftp_host = %s AND ftp_username = %s AND ftp_password_encrypted IS NOT NULL
        ORDER BY attivo DESC, updated_at DESC NULLS LAST
        LIMIT 1
    """, (config['ftp_host'], config['ftp_username'])).fetchone()
    if endpoint:
        from ..crypto import decrypt_password
        password = decrypt_password(endpoint['ftp_password_encrypted'])
    password = password or os.environ.get('FTP_PASSWORD')
    if not password:
        raise ValueError(f"Password FTP non trovata per l'utente {config['ftp_username']}")

    return {
        'host': config['ftp_host'],
        'port': config['ftp_port'] or 21,
        'username': config['ftp_username'],
        'password': password,
        'passive': bool(config['ftp_passive_mode']),
        'timeout': config['ftp_timeout'] or 30,
    }


def scegli_file(nomi: List[str], oggi: date) -> Tuple[Optional[str], Optional[date]]:
    """File con la data di oggi; altrimenti il piu' recente (mai date future)."""
    candidati = []
    for nome in nomi:
        m = FILE_RE.match(os.path.basename(nome))
        if not m:
            continue
        try:
            d = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            continue
        if d <= oggi:
            candidati.append((d, os.path.basename(nome)))
    if not candidati:
        return None, None
    d, nome = max(candidati)
    return nome, d


def _scarica_da_ftp(oggi: date) -> Tuple[Optional[str], Optional[date], Optional[bytes], List[str]]:
    """Ritorna (nome, data, contenuto, elenco cartella)."""
    cred = _credenziali_ftp()
    ftp = ftplib.FTP(timeout=cred['timeout'])
    try:
        ftp.connect(cred['host'], cred['port'])
        ftp.login(cred['username'], cred['password'])
        ftp.set_pasv(cred['passive'])
        ftp.cwd(FTP_DIR)
        nomi = ftp.nlst()
        nome, data_file = scegli_file(nomi, oggi)
        if not nome:
            return None, None, None, nomi
        buf = io.BytesIO()
        ftp.retrbinary(f'RETR {nome}', buf.write)
        return nome, data_file, buf.getvalue(), nomi
    finally:
        try:
            ftp.quit()
        except Exception:
            ftp.close()


# =============================================================================
# STATO E DIFFERENZE
# =============================================================================

def _ultimo_file_importato() -> Optional[str]:
    db = get_db()
    try:
        row = db.execute(
            "SELECT last_url FROM sync_state WHERE key = %s", (SYNC_STATE_KEY,)
        ).fetchone()
        return row['last_url'] if row else None
    except Exception:
        db.rollback()
        return None


def _salva_stato(nome_file: str, totale: int):
    from .sync_ministero import _ensure_sync_state_table
    _ensure_sync_state_table()
    db = get_db()
    db.execute("""
        INSERT INTO sync_state (key, last_sync, last_url, records_count)
        VALUES (%s, CURRENT_TIMESTAMP, %s, %s)
        ON CONFLICT (key) DO UPDATE SET
            last_sync = EXCLUDED.last_sync,
            last_url = EXCLUDED.last_url,
            records_count = EXCLUDED.records_count
    """, (SYNC_STATE_KEY, nome_file, totale))
    db.commit()


def _snapshot_clienti() -> Dict[str, Dict[str, str]]:
    db = get_db()
    colonne = ', '.join(c for c, _ in CAMPI_CONFRONTO)
    rows = db.execute(f"SELECT codice_cliente, {colonne} FROM anagrafica_clienti").fetchall()
    return {
        r['codice_cliente']: {c: (r[c] or '').strip() for c, _ in CAMPI_CONFRONTO}
        for r in rows
    }


def calcola_differenze(prima: Dict[str, Dict[str, str]], dopo: Dict[str, Dict[str, str]]):
    """Ritorna (nuovi, eliminati, modificati) ordinati per codice cliente."""
    def scheda(codice, valori):
        return {'codice_cliente': codice, **valori}

    nuovi = [scheda(c, dopo[c]) for c in sorted(dopo.keys() - prima.keys())]
    eliminati = [scheda(c, prima[c]) for c in sorted(prima.keys() - dopo.keys())]
    modificati = []
    for c in sorted(prima.keys() & dopo.keys()):
        cambi = [
            {'campo': etichetta, 'prima': prima[c][campo], 'dopo': dopo[c][campo]}
            for campo, etichetta in CAMPI_CONFRONTO
            if prima[c][campo] != dopo[c][campo]
        ]
        if cambi:
            modificati.append({
                'codice_cliente': c,
                'ragione_sociale': dopo[c]['ragione_sociale_2'] or dopo[c]['ragione_sociale_1'],
                'cambi': cambi,
            })
    return nuovi, eliminati, modificati


def _archivia(nome: str, contenuto: bytes):
    try:
        os.makedirs(ARCHIVE_DIR, exist_ok=True)
        with open(os.path.join(ARCHIVE_DIR, nome), 'wb') as f:
            f.write(contenuto)
    except Exception as e:
        print(f"⚠️ Sync clienti: archiviazione {nome} non riuscita: {e}")


# =============================================================================
# SYNC
# =============================================================================

def sync_clienti_erp(forza: bool = False, oggi: Optional[date] = None) -> SyncClientiResult:
    """
    Preleva e importa l'anagrafica clienti ERP.

    Args:
        forza: reimporta anche un file gia' importato e ignora la soglia di calo
               (per il primo allineamento o un recupero manuale).
        oggi: data di riferimento (test).
    """
    inizio = datetime.now()
    oggi = oggi or date.today()
    res = SyncClientiResult()

    try:
        nome, data_file, contenuto, elenco = _scarica_da_ftp(oggi)
        if not nome:
            res.messaggio = (
                f"Nessun file ANAG_TOT_V_AAAA_MM_GG.csv nella cartella FTP '{FTP_DIR}' "
                f"({len(elenco)} file presenti). Anagrafica clienti NON modificata."
            )
            return res

        res.file, res.data_file = nome, data_file
        res.file_del_giorno = data_file == oggi

        if not forza and nome == _ultimo_file_importato():
            res.esito = 'NESSUN_FILE_NUOVO'
            res.totale_prima = res.totale_dopo = len(_snapshot_clienti())
            res.messaggio = (
                ("" if res.file_del_giorno else "File di oggi non presente. ")
                + f"Il file piu' recente ({nome}) e' gia' stato importato: "
                "anagrafica clienti invariata."
            )
            return res

        _archivia(nome, contenuto)

        letto = _leggi_tracciato_clienti_erp(contenuto)
        if letto is None:
            res.messaggio = f"{nome}: formato non riconosciuto. Anagrafica clienti NON modificata."
            return res
        res.righe_file = len(letto[0])

        prima = _snapshot_clienti()
        res.totale_prima = len(prima)

        if not forza and prima and res.righe_file < len(prima) * (1 - SOGLIA_CALO):
            calo = 1 - res.righe_file / len(prima)
            res.esito = 'BLOCCATO'
            res.messaggio = (
                f"{nome} contiene {res.righe_file:,} clienti contro i {len(prima):,} in anagrafica "
                f"(-{calo:.0%}, soglia {SOGLIA_CALO:.0%}): import BLOCCATO, anagrafica NON modificata. "
                "Verificare l'estrazione ERP; se il calo e' corretto importare il file "
                "manualmente da Impostazioni o con la sync forzata."
            )
            return res

        res.import_result = import_anagrafica_clienti(csv_content=contenuto, fonte=nome)
        if 'error' in res.import_result:
            res.messaggio = f"Import di {nome} fallito: {res.import_result['error']}"
            return res

        dopo = _snapshot_clienti()
        res.totale_dopo = len(dopo)
        res.nuovi, res.eliminati, res.modificati = calcola_differenze(prima, dopo)
        _salva_stato(nome, res.totale_dopo)

        res.esito = 'IMPORTATO'
        res.messaggio = (
            f"Importato {nome}: {len(res.nuovi)} nuovi, {len(res.eliminati)} eliminati, "
            f"{len(res.modificati)} modificati."
        )
        if not res.file_del_giorno:
            res.messaggio += f" ATTENZIONE: file del {data_file:%d/%m/%Y}, non di oggi."
        return res

    except Exception as e:
        res.esito = 'ERRORE'
        res.messaggio = f"Errore sync clienti: {e}"
        return res
    finally:
        res.durata_secondi = (datetime.now() - inizio).total_seconds()
